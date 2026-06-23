# -*- coding: utf-8 -*-
"""Market Activity Stream Engine — FAZ 42.

Aggregates events from multiple sources into a unified real-time
activity stream that shows "the pulse of the market".

Sources:
  - opportunity_engine  (volume_spike, momentum_shift, etc.)
  - news_impact_engine  (news_impact, macro_impact)
  - alert_engine        (smart alerts)
  - strategy_live_engine (strategy_activity)
  - social_engine       (social_trending, mentor_post)
  - live_room_engine    (mentor_live_room)
  - market_stream       (asset_activity)

Public API:
  push_event(event_dict)            → str (event_id)
  get_events(filters)               → list[dict]
  get_trending_symbols(hours, limit) → list[dict]
  get_event(event_id)               → dict|None
  get_events_for_symbol(symbol)     → list[dict]
  get_events_for_market(market)     → list[dict]
  mark_viewed(user_id, event_ids)   → int
  get_unread_count(user_id, since)  → int
  collect_all()                     → int (events collected)
  activity_collect_loop()           → background loop
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.activity_stream")

# ── Database ──────────────────────────────────────────────────────
_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
_DB_PATH = os.path.join(_DB_DIR, "activity_stream.db")
_lock = threading.Lock()

# ── Constants ─────────────────────────────────────────────────────
COLLECT_INTERVAL = 60  # seconds between collection cycles
MAX_EVENTS = 5000      # max stored events
DEDUP_WINDOW = 300     # 5 minutes dedup window
CACHE_KEY = "activity_stream_latest"

SEVERITY_LEVELS = ("low", "medium", "high", "critical")

EVENT_TYPES = {
    "volume_spike":        {"icon": "📊", "label": "Volume Spike",        "color": "#3b82f6"},
    "volatility_spike":    {"icon": "⚡", "label": "Volatility Spike",    "color": "#f59e0b"},
    "momentum_shift":      {"icon": "🚀", "label": "Momentum Shift",      "color": "#10b981"},
    "sector_rotation":     {"icon": "🔄", "label": "Sector Rotation",     "color": "#ec4899"},
    "news_impact":         {"icon": "📰", "label": "News Impact",         "color": "#6366f1"},
    "macro_impact":        {"icon": "🌍", "label": "Macro Impact",        "color": "#8b5cf6"},
    "asset_activity":      {"icon": "💹", "label": "Asset Activity",      "color": "#14b8a6"},
    "mentor_post":         {"icon": "🎓", "label": "Mentor Post",         "color": "#f97316"},
    "mentor_live_room":    {"icon": "🔴", "label": "Mentor Live Room",    "color": "#ef4444"},
    "strategy_activity":   {"icon": "⚙️", "label": "Strategy Activity",   "color": "#06b6d4"},
    "social_trending":     {"icon": "🔥", "label": "Social Trending",     "color": "#eab308"},
    "portfolio_risk_change": {"icon": "🛡️", "label": "Portfolio Risk",    "color": "#dc2626"},
}

# ── Compliance — neutral language ─────────────────────────────────
BANNED_WORDS = {"BUY", "SELL", "ENTRY", "EXIT", "TAKE PROFIT", "STOP LOSS", "TRADE NOW"}

# ── Dedup cache ───────────────────────────────────────────────────
_dedup_cache: Dict[str, float] = {}
_dedup_lock = threading.Lock()

# ── WebSocket listeners ───────────────────────────────────────────
_ws_listeners: List[Any] = []
_ws_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("activity_stream.db")


def _init_db():
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activity_stream_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                market TEXT NOT NULL DEFAULT '',
                symbol TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                confidence INTEGER NOT NULL DEFAULT 50,
                severity TEXT NOT NULL DEFAULT 'low',
                source TEXT NOT NULL DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ase_type ON activity_stream_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_ase_market ON activity_stream_events(market);
            CREATE INDEX IF NOT EXISTS idx_ase_symbol ON activity_stream_events(symbol);
            CREATE INDEX IF NOT EXISTS idx_ase_severity ON activity_stream_events(severity);
            CREATE INDEX IF NOT EXISTS idx_ase_created ON activity_stream_events(created_at);
            CREATE INDEX IF NOT EXISTS idx_ase_source ON activity_stream_events(source);

            CREATE TABLE IF NOT EXISTS user_activity_views (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                viewed_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES activity_stream_events(id)
            );
            CREATE INDEX IF NOT EXISTS idx_uav_user ON user_activity_views(user_id);
            CREATE INDEX IF NOT EXISTS idx_uav_event ON user_activity_views(event_id);
        """)
        conn.commit()
    finally:
        conn.close()


try:
    _init_db()
except Exception as e:
    _logger.warning("Activity stream DB init deferred: %s", e)


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dedup_key(event_type: str, symbol: str, source: str) -> str:
    """Create a dedup fingerprint for an event."""
    raw = f"{event_type}:{symbol}:{source}"
    return hashlib.md5(raw.encode()).hexdigest()


def _is_duplicate(event_type: str, symbol: str, source: str) -> bool:
    """Check if same event was pushed recently (within DEDUP_WINDOW)."""
    key = _dedup_key(event_type, symbol, source)
    now = time.time()
    with _dedup_lock:
        # Clean expired entries
        expired = [k for k, v in _dedup_cache.items() if now - v > DEDUP_WINDOW]
        for k in expired:
            del _dedup_cache[k]
        if key in _dedup_cache:
            return True
        _dedup_cache[key] = now
        return False


def _severity_from_confidence(confidence: int) -> str:
    """Derive severity from confidence score."""
    if confidence >= 85:
        return "critical"
    elif confidence >= 70:
        return "high"
    elif confidence >= 50:
        return "medium"
    return "low"


def _sanitize_text(text: str) -> str:
    """Remove banned financial advice language."""
    if not text:
        return text
    result = text
    for word in BANNED_WORDS:
        # Case-insensitive replacement
        import re
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub("***", result)
    return result


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if "metadata_json" in d:
        try:
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        del d["metadata_json"]
    return d


def _trim_old_events():
    """Remove old events beyond MAX_EVENTS limit."""
    with _lock:
        conn = _get_db()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM activity_stream_events"
            ).fetchone()[0]
            if count > MAX_EVENTS:
                excess = count - MAX_EVENTS
                conn.execute(
                    "DELETE FROM activity_stream_events WHERE id IN "
                    "(SELECT id FROM activity_stream_events ORDER BY created_at ASC LIMIT ?)",
                    (excess,)
                )
                conn.commit()
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# CORE API
# ══════════════════════════════════════════════════════════════════

def push_event(event: dict) -> Optional[str]:
    """Push a normalized event into the activity stream.
    
    Returns event_id on success, None if duplicate.
    """
    event_type = event.get("event_type", "asset_activity")
    symbol = event.get("symbol", "")
    source = event.get("source", "")
    title = _sanitize_text(event.get("title", ""))
    summary = _sanitize_text(event.get("summary", ""))
    market = event.get("market", "")
    confidence = int(event.get("confidence", 50))
    severity = event.get("severity") or _severity_from_confidence(confidence)
    metadata = event.get("metadata", {})

    # Validate event type
    if event_type not in EVENT_TYPES:
        _logger.warning("Unknown event type: %s", event_type)
        return None

    # Validate severity
    if severity not in SEVERITY_LEVELS:
        severity = "low"

    # Dedup check
    if _is_duplicate(event_type, symbol, source):
        _logger.debug("Duplicate event skipped: %s %s %s", event_type, symbol, source)
        return None

    event_id = event.get("id") or str(uuid.uuid4())
    created_at = event.get("created_at") or _now_iso()

    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activity_stream_events
                   (id, event_type, market, symbol, title, summary,
                    confidence, severity, source, metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, event_type, market, symbol, title, summary,
                 confidence, severity, source,
                 json.dumps(metadata, ensure_ascii=False),
                 created_at)
            )
            conn.commit()
        finally:
            conn.close()

    # Broadcast to WebSocket listeners
    _broadcast_event({
        "id": event_id,
        "event_type": event_type,
        "market": market,
        "symbol": symbol,
        "title": title,
        "summary": summary,
        "confidence": confidence,
        "severity": severity,
        "source": source,
        "created_at": created_at,
        "metadata": metadata,
    })

    # Trigger notification for high/critical events
    if severity in ("high", "critical"):
        _notify_event(event_id, event_type, symbol, title, severity)

    return event_id


def get_events(
    market: str = "",
    severity: str = "",
    event_type: str = "",
    symbol: str = "",
    min_confidence: int = 0,
    hours: int = 24,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    """Retrieve activity events with filters."""
    conditions = []
    params: list = []

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    conditions.append("created_at >= ?")
    params.append(cutoff)

    if market:
        conditions.append("market = ?")
        params.append(market)
    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if min_confidence > 0:
        conditions.append("confidence >= ?")
        params.append(min_confidence)

    where = " AND ".join(conditions) if conditions else "1=1"
    params.extend([limit, offset])

    conn = _get_db()
    try:
        rows = conn.execute(
            f"SELECT * FROM activity_stream_events WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_event(event_id: str) -> Optional[dict]:
    """Get a single event by ID."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM activity_stream_events WHERE id = ?",
            (event_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_events_for_symbol(
    symbol: str, hours: int = 24, limit: int = 20
) -> List[dict]:
    """Get all events for a specific symbol."""
    return get_events(symbol=symbol, hours=hours, limit=limit)


def get_events_for_market(
    market: str, hours: int = 24, limit: int = 50
) -> List[dict]:
    """Get all events for a specific market."""
    return get_events(market=market, hours=hours, limit=limit)


def get_trending_symbols(hours: int = 12, limit: int = 10) -> List[dict]:
    """Get symbols with the most activity events."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT symbol, market,
                      COUNT(*) as event_count,
                      MAX(confidence) as max_confidence,
                      MAX(CASE WHEN severity='critical' THEN 4
                               WHEN severity='high' THEN 3
                               WHEN severity='medium' THEN 2
                               ELSE 1 END) as max_severity_rank
               FROM activity_stream_events
               WHERE symbol != '' AND created_at >= ?
               GROUP BY symbol
               ORDER BY event_count DESC, max_confidence DESC
               LIMIT ?""",
            (cutoff, limit),
        ).fetchall()
        result = []
        for r in rows:
            sev_map = {4: "critical", 3: "high", 2: "medium", 1: "low"}
            result.append({
                "symbol": r["symbol"],
                "market": r["market"],
                "event_count": r["event_count"],
                "max_confidence": r["max_confidence"],
                "max_severity": sev_map.get(r["max_severity_rank"], "low"),
            })
        return result
    finally:
        conn.close()


def mark_viewed(user_id: str, event_ids: List[str]) -> int:
    """Mark events as viewed by a user."""
    if not user_id or not event_ids:
        return 0
    now = _now_iso()
    count = 0
    with _lock:
        conn = _get_db()
        try:
            for eid in event_ids:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO user_activity_views (id, user_id, event_id, viewed_at) "
                        "VALUES (?, ?, ?, ?)",
                        (str(uuid.uuid4()), user_id, eid, now)
                    )
                    count += 1
                except Exception:
                    pass
            conn.commit()
        finally:
            conn.close()
    return count


def get_unread_count(user_id: str, hours: int = 24) -> int:
    """Count events not yet viewed by user."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    conn = _get_db()
    try:
        row = conn.execute(
            """SELECT COUNT(*) FROM activity_stream_events e
               WHERE e.created_at >= ?
               AND e.id NOT IN (
                   SELECT event_id FROM user_activity_views WHERE user_id = ?
               )""",
            (cutoff, user_id)
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# EVENT COLLECTORS — normalize from each source
# ══════════════════════════════════════════════════════════════════

def _collect_from_opportunities() -> int:
    """Collect recent opportunities and push as activity events."""
    count = 0
    try:
        from app.core.opportunity_engine import get_trending_opportunities
        opps = get_trending_opportunities(limit=20)
        for opp in opps:
            evt = {
                "event_type": opp.get("event_type", "asset_activity"),
                "market": opp.get("market", "crypto"),
                "symbol": opp.get("symbol", ""),
                "title": opp.get("description", ""),
                "summary": (opp.get("details") or "")[:200],
                "confidence": opp.get("confidence", 50),
                "source": "opportunity_engine",
                "metadata": {
                    "opportunity_id": opp.get("id"),
                    "price": opp.get("price"),
                    "change_pct": opp.get("change_pct"),
                },
            }
            if push_event(evt):
                count += 1
    except Exception as e:
        _logger.debug("Opportunity collection error: %s", e)
    return count


def _collect_from_news_impact() -> int:
    """Collect recent news impacts."""
    count = 0
    try:
        from app.core.news_impact_engine import get_trending_impacts
        impacts = get_trending_impacts(limit=10)
        for imp in impacts:
            conf = imp.get("confidence_score", 50)
            evt = {
                "event_type": "news_impact",
                "market": imp.get("news_market", ""),
                "symbol": "",
                "title": imp.get("news_title", "News impact detected"),
                "summary": (imp.get("impact_summary") or "")[:200],
                "confidence": conf,
                "source": "news_impact_engine",
                "metadata": {
                    "news_id": imp.get("news_id"),
                    "time_horizon": imp.get("time_horizon"),
                    "bullish_assets": imp.get("bullish_assets", []),
                    "bearish_assets": imp.get("bearish_assets", []),
                },
            }
            # Push per impacted asset for symbol-level tracking
            bull_assets = imp.get("bullish_assets") or []
            bear_assets = imp.get("bearish_assets") or []
            all_assets = bull_assets[:3] + bear_assets[:3]
            if all_assets:
                for asset in all_assets:
                    evt_copy = dict(evt)
                    evt_copy["symbol"] = asset
                    if push_event(evt_copy):
                        count += 1
            else:
                if push_event(evt):
                    count += 1
    except Exception as e:
        _logger.debug("News impact collection error: %s", e)
    return count


def _collect_from_alerts() -> int:
    """Collect triggered smart alerts."""
    count = 0
    try:
        from app.core.alert_engine import get_triggered
        triggered = get_triggered()[:10]
        for alert in triggered:
            evt = {
                "event_type": alert.get("condition_type", "asset_activity"),
                "market": alert.get("market", "crypto"),
                "symbol": alert.get("symbol", ""),
                "title": f"Alert triggered: {alert.get('symbol', '')}",
                "summary": f"{alert.get('condition_type', '')} condition met",
                "confidence": 75,
                "severity": "high",
                "source": "alert_engine",
                "metadata": {
                    "alert_id": alert.get("id"),
                    "trigger_price": alert.get("trigger_price"),
                },
            }
            if push_event(evt):
                count += 1
    except Exception as e:
        _logger.debug("Alert collection error: %s", e)
    return count


def _collect_from_strategy_live() -> int:
    """Collect live strategy signals."""
    count = 0
    try:
        from app.core.strategy_live_engine import get_live_signals
        signals = get_live_signals(limit=10)
        for sig in signals:
            evt = {
                "event_type": "strategy_activity",
                "market": sig.get("market", "crypto"),
                "symbol": sig.get("symbol", ""),
                "title": f"Strategy signal: {sig.get('signal_type', 'activity')}",
                "summary": sig.get("message", ""),
                "confidence": sig.get("confidence", 60),
                "source": "strategy_live_engine",
                "metadata": {
                    "strategy_id": sig.get("strategy_id"),
                    "signal_type": sig.get("signal_type"),
                },
            }
            if push_event(evt):
                count += 1
    except Exception as e:
        _logger.debug("Strategy live collection error: %s", e)
    return count


def _collect_from_social() -> int:
    """Collect trending social posts."""
    count = 0
    try:
        from app.core.social_engine import get_trending
        trending = get_trending(limit=5)
        for post in trending:
            if post.get("like_count", 0) < 3:
                continue
            evt = {
                "event_type": "social_trending",
                "market": post.get("market", ""),
                "symbol": post.get("symbol", ""),
                "title": f"Trending post by {post.get('username', 'user')}",
                "summary": (post.get("content") or "")[:150],
                "confidence": min(40 + post.get("like_count", 0) * 5, 90),
                "severity": "low",
                "source": "social_engine",
                "metadata": {
                    "post_id": post.get("id"),
                    "username": post.get("username"),
                    "like_count": post.get("like_count", 0),
                },
            }
            if push_event(evt):
                count += 1
    except Exception as e:
        _logger.debug("Social collection error: %s", e)
    return count


def _collect_from_live_rooms() -> int:
    """Collect active live room sessions."""
    count = 0
    try:
        from app.core.live_room_engine import list_rooms
        rooms = list_rooms(active_only=True, limit=5)
        for room in rooms:
            evt = {
                "event_type": "mentor_live_room",
                "market": room.get("market", ""),
                "symbol": "",
                "title": f"Live now: {room.get('title', 'Mentor session')}",
                "summary": f"Hosted by {room.get('mentor_name', 'mentor')}",
                "confidence": 70,
                "severity": "medium",
                "source": "live_room_engine",
                "metadata": {
                    "room_id": room.get("id"),
                    "participant_count": room.get("participant_count", 0),
                },
            }
            if push_event(evt):
                count += 1
    except Exception as e:
        _logger.debug("Live room collection error: %s", e)
    return count


def collect_all() -> int:
    """Run all collectors and return total new events pushed."""
    total = 0
    total += _collect_from_opportunities()
    total += _collect_from_news_impact()
    total += _collect_from_alerts()
    total += _collect_from_strategy_live()
    total += _collect_from_social()
    total += _collect_from_live_rooms()
    if total > 0:
        _logger.info("Activity stream: collected %d new events", total)
    _trim_old_events()
    return total


# ══════════════════════════════════════════════════════════════════
# WEBSOCKET
# ══════════════════════════════════════════════════════════════════

def ws_register(ws) -> None:
    """Register a WebSocket listener."""
    with _ws_lock:
        _ws_listeners.append(ws)
    _logger.debug("Activity WS listener registered (total: %d)", len(_ws_listeners))


def ws_unregister(ws) -> None:
    """Unregister a WebSocket listener."""
    with _ws_lock:
        try:
            _ws_listeners.remove(ws)
        except ValueError:
            pass


def _broadcast_event(event: dict) -> None:
    """Send event to all connected WebSocket listeners."""
    payload = json.dumps({
        "type": "activity_event",
        "event": event,
    })
    dead = []
    with _ws_lock:
        listeners = list(_ws_listeners)
    for ws in listeners:
        try:
            ws.send(payload)
        except Exception:
            dead.append(ws)
    if dead:
        with _ws_lock:
            for ws in dead:
                try:
                    _ws_listeners.remove(ws)
                except ValueError:
                    pass


# ══════════════════════════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════

def _notify_event(event_id: str, event_type: str, symbol: str,
                  title: str, severity: str) -> None:
    """Push high-severity events to notification system."""
    try:
        _logger.info(
            "Activity notification: [%s] %s %s — %s",
            severity.upper(), event_type, symbol, title
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# COPILOT INTEGRATION
# ══════════════════════════════════════════════════════════════════

def get_activity_summary(hours: int = 6) -> dict:
    """Generate a summary of recent activity for Copilot."""
    events = get_events(hours=hours, limit=100)
    if not events:
        return {
            "total_events": 0,
            "summary": "No significant market activity detected recently.",
            "critical_events": [],
            "trending_symbols": [],
        }

    critical = [e for e in events if e.get("severity") == "critical"]
    high = [e for e in events if e.get("severity") == "high"]
    trending = get_trending_symbols(hours=hours, limit=5)

    # Group by market
    by_market: Dict[str, int] = {}
    for e in events:
        m = e.get("market", "unknown")
        by_market[m] = by_market.get(m, 0) + 1

    # Group by type
    by_type: Dict[str, int] = {}
    for e in events:
        t = e.get("event_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    summary_parts = [f"{len(events)} activity events in the last {hours}h."]
    if critical:
        summary_parts.append(f"{len(critical)} critical events detected.")
    if high:
        summary_parts.append(f"{len(high)} high-severity events.")
    if trending:
        top_syms = ", ".join(t["symbol"] for t in trending[:3])
        summary_parts.append(f"Most active symbols: {top_syms}.")

    return {
        "total_events": len(events),
        "critical_count": len(critical),
        "high_count": len(high),
        "summary": " ".join(summary_parts),
        "critical_events": critical[:5],
        "high_events": high[:5],
        "trending_symbols": trending,
        "by_market": by_market,
        "by_type": by_type,
    }


# ══════════════════════════════════════════════════════════════════
# BACKGROUND LOOP
# ══════════════════════════════════════════════════════════════════

def activity_collect_loop() -> None:
    """Background loop: collect events from all sources periodically."""
    time.sleep(10)  # warm-up
    while True:
        try:
            collect_all()
        except Exception as e:
            _logger.warning("Activity collect loop error: %s", e)
        time.sleep(COLLECT_INTERVAL)
