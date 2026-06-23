# -*- coding: utf-8 -*-
"""Smart Alert Engine — FAZ 40.

User-configurable smart alerts that go beyond simple price alerts.
Supports condition-based alerts triggered by the opportunity engine:
  - opportunity_detected: triggers when any opportunity matches criteria
  - confidence_threshold: triggers when opportunity confidence ≥ threshold
  - market_event: triggers on specific market events (volume_spike, momentum, etc.)
  - multi_condition: triggers when multiple conditions are met simultaneously

LEGAL_SAFE_MODE: Alerts notify about market observations, not trading actions.

Public API:
    create_smart_alert(user_id, data) -> dict
    get_user_alerts(user_id)          -> list[dict]
    delete_smart_alert(user_id, alert_id) -> bool
    update_smart_alert(user_id, alert_id, data) -> dict | None
    evaluate_alerts(opportunities)     -> list[dict]  (returns triggered alerts)
    get_triggered_alerts(user_id)      -> list[dict]
    clear_triggered(user_id)           -> None
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.smart_alert_engine")

# ── Database ──────────────────────────────────────────────────────
_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
_DB_PATH = os.path.join(_DB_DIR, "opportunities.db")  # share DB with opportunity engine
_lock = threading.Lock()

# ── Alert Types ───────────────────────────────────────────────────
SMART_ALERT_TYPES = {
    "opportunity_any": "Herhangi bir fırsat tespit edildiğinde",
    "opportunity_symbol": "Belirli sembol için fırsat tespit edildiğinde",
    "confidence_high": "Yüksek güvenilirlikli fırsat tespit edildiğinde (≥80)",
    "event_volume_spike": "Hacim artışı tespit edildiğinde",
    "event_momentum_shift": "Momentum değişimi tespit edildiğinde",
    "event_volatility_spike": "Volatilite artışı tespit edildiğinde",
    "event_rsi_extreme": "RSI aşırı bölge tespit edildiğinde",
    "event_breakout": "Kırılım hareketi tespit edildiğinde",
    "event_whale_activity": "Büyük hacim hareketi tespit edildiğinde",
    "market_crypto": "Kripto piyasasında fırsat tespit edildiğinde",
    "market_stocks": "Hisse piyasasında fırsat tespit edildiğinde",
    "market_forex": "Forex piyasasında fırsat tespit edildiğinde",
}


# ══════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("opportunities.db")


def _init_db():
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS smart_alerts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                symbol TEXT,
                market TEXT,
                min_confidence INTEGER DEFAULT 50,
                event_types TEXT,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_triggered_at TEXT,
                trigger_count INTEGER DEFAULT 0,
                cooldown_minutes INTEGER DEFAULT 60
            );
            CREATE INDEX IF NOT EXISTS idx_sa_user ON smart_alerts(user_id);
            CREATE INDEX IF NOT EXISTS idx_sa_active ON smart_alerts(active);

            CREATE TABLE IF NOT EXISTS smart_alert_triggers (
                id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                opportunity_id TEXT,
                message TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0,
                triggered_at TEXT NOT NULL,
                FOREIGN KEY (alert_id) REFERENCES smart_alerts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_sat_user ON smart_alert_triggers(user_id);
            CREATE INDEX IF NOT EXISTS idx_sat_alert ON smart_alert_triggers(alert_id);
            CREATE INDEX IF NOT EXISTS idx_sat_read ON smart_alert_triggers(read);
        """)
        conn.commit()
    finally:
        conn.close()


# Init DB on module load
try:
    _init_db()
except Exception as e:
    _logger.warning("Smart alert DB init deferred: %s", e)


# ══════════════════════════════════════════════════════════════════════
# CRUD
# ══════════════════════════════════════════════════════════════════════

def create_smart_alert(user_id: str, data: dict) -> dict:
    """Create a new smart alert for a user.

    Args:
        user_id: The user creating the alert
        data: {
            alert_type: str (one of SMART_ALERT_TYPES keys),
            name: str (display name),
            symbol: str (optional, for symbol-specific alerts),
            market: str (optional, filter by market),
            min_confidence: int (optional, default 50),
            event_types: str (optional, comma-separated event types),
            cooldown_minutes: int (optional, default 60),
        }
    """
    alert_type = (data.get("alert_type") or "").strip()
    if alert_type not in SMART_ALERT_TYPES:
        raise ValueError(f"Invalid alert_type: {alert_type}")

    name = (data.get("name") or SMART_ALERT_TYPES.get(alert_type, "Smart Alert")).strip()
    if not name:
        raise ValueError("name is required")

    alert = {
        "id": str(uuid.uuid4())[:8],
        "user_id": user_id,
        "alert_type": alert_type,
        "symbol": (data.get("symbol") or "").strip().upper() or None,
        "market": (data.get("market") or "").strip().lower() or None,
        "min_confidence": int(data.get("min_confidence", 50)),
        "event_types": (data.get("event_types") or "").strip() or None,
        "name": name,
        "active": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_triggered_at": None,
        "trigger_count": 0,
        "cooldown_minutes": int(data.get("cooldown_minutes", 60)),
    }

    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                """INSERT INTO smart_alerts
                   (id, user_id, alert_type, symbol, market, min_confidence,
                    event_types, name, active, created_at, last_triggered_at,
                    trigger_count, cooldown_minutes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert["id"], alert["user_id"], alert["alert_type"],
                    alert["symbol"], alert["market"], alert["min_confidence"],
                    alert["event_types"], alert["name"], alert["active"],
                    alert["created_at"], alert["last_triggered_at"],
                    alert["trigger_count"], alert["cooldown_minutes"],
                ),
            )
            conn.commit()
        finally:
            conn.close()

    _logger.info("Smart alert created: %s for user %s", alert["id"], user_id)
    return alert


def get_user_alerts(user_id: str) -> List[dict]:
    """Get all smart alerts for a user."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM smart_alerts WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_smart_alert(user_id: str, alert_id: str) -> bool:
    """Delete a smart alert. Only the owning user can delete."""
    with _lock:
        conn = _get_db()
        try:
            cur = conn.execute(
                "DELETE FROM smart_alerts WHERE id = ? AND user_id = ?",
                (alert_id, user_id),
            )
            conn.commit()
            deleted = cur.rowcount > 0
            if deleted:
                # Clean up triggers
                conn.execute(
                    "DELETE FROM smart_alert_triggers WHERE alert_id = ?",
                    (alert_id,),
                )
                conn.commit()
            return deleted
        finally:
            conn.close()


def update_smart_alert(user_id: str, alert_id: str, data: dict) -> Optional[dict]:
    """Update a smart alert's configuration."""
    with _lock:
        conn = _get_db()
        try:
            row = conn.execute(
                "SELECT * FROM smart_alerts WHERE id = ? AND user_id = ?",
                (alert_id, user_id),
            ).fetchone()
            if not row:
                return None

            updates = {}
            if "name" in data:
                updates["name"] = data["name"]
            if "active" in data:
                updates["active"] = 1 if data["active"] else 0
            if "min_confidence" in data:
                updates["min_confidence"] = int(data["min_confidence"])
            if "symbol" in data:
                updates["symbol"] = (data["symbol"] or "").strip().upper() or None
            if "market" in data:
                updates["market"] = (data["market"] or "").strip().lower() or None
            if "event_types" in data:
                updates["event_types"] = data["event_types"]
            if "cooldown_minutes" in data:
                updates["cooldown_minutes"] = int(data["cooldown_minutes"])

            if not updates:
                return dict(row)

            set_parts = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [alert_id, user_id]
            conn.execute(
                f"UPDATE smart_alerts SET {set_parts} WHERE id = ? AND user_id = ?",
                vals,
            )
            conn.commit()

            updated = conn.execute(
                "SELECT * FROM smart_alerts WHERE id = ?", (alert_id,),
            ).fetchone()
            return dict(updated) if updated else None
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════════
# EVALUATION
# ══════════════════════════════════════════════════════════════════════

def evaluate_alerts(opportunities: List[dict]) -> List[dict]:
    """Evaluate all active smart alerts against current opportunities.

    Returns list of triggered alert dicts with the matched opportunity.
    """
    if not opportunities:
        return []

    conn = _get_db()
    try:
        alerts = conn.execute(
            "SELECT * FROM smart_alerts WHERE active = 1",
        ).fetchall()
        alerts = [dict(a) for a in alerts]
    finally:
        conn.close()

    if not alerts:
        return []

    triggered = []
    now = datetime.now(timezone.utc)

    for alert in alerts:
        # Check cooldown
        last_trigger = alert.get("last_triggered_at")
        cooldown = alert.get("cooldown_minutes", 60)
        if last_trigger:
            try:
                last_dt = datetime.fromisoformat(last_trigger.replace("Z", "+00:00"))
                elapsed_min = (now - last_dt).total_seconds() / 60
                if elapsed_min < cooldown:
                    continue
            except (ValueError, TypeError):
                pass

        # Find matching opportunities
        matched_opp = _match_alert(alert, opportunities)
        if matched_opp:
            trigger = _trigger_smart_alert(alert, matched_opp)
            if trigger:
                triggered.append(trigger)

    return triggered


def _match_alert(alert: dict, opportunities: List[dict]) -> Optional[dict]:
    """Check if any opportunity matches the alert criteria."""
    alert_type = alert.get("alert_type", "")
    min_conf = alert.get("min_confidence", 50)
    symbol = alert.get("symbol")
    market = alert.get("market")
    event_types_str = alert.get("event_types") or ""
    event_types = [e.strip() for e in event_types_str.split(",") if e.strip()] if event_types_str else []

    for opp in opportunities:
        opp_conf = opp.get("confidence", 0)
        opp_sym = opp.get("symbol", "")
        opp_mkt = opp.get("market", "")
        opp_evt = opp.get("event_type", "")

        # Confidence filter
        if opp_conf < min_conf:
            continue

        # Market filter
        if market and opp_mkt != market:
            continue

        # Symbol filter
        if symbol and opp_sym != symbol:
            continue

        # Type-specific matching
        if alert_type == "opportunity_any":
            return opp
        elif alert_type == "opportunity_symbol":
            if symbol and opp_sym == symbol:
                return opp
        elif alert_type == "confidence_high":
            if opp_conf >= 80:
                return opp
        elif alert_type.startswith("event_"):
            target_event = alert_type.replace("event_", "")
            if opp_evt == target_event:
                return opp
        elif alert_type.startswith("market_"):
            target_market = alert_type.replace("market_", "")
            if opp_mkt == target_market:
                return opp

        # Event types filter (for custom alerts)
        if event_types and opp_evt in event_types:
            return opp

    return None


def _trigger_smart_alert(alert: dict, opportunity: dict) -> Optional[dict]:
    """Record a trigger event for a smart alert."""
    opp_id = opportunity.get("id", "")
    opp_desc = opportunity.get("description", "")
    opp_sym = opportunity.get("symbol", "")

    message = f"🔔 {alert.get('name', 'Smart Alert')}: {opp_sym} — {opp_desc}"

    trigger = {
        "id": str(uuid.uuid4())[:8],
        "alert_id": alert["id"],
        "user_id": alert["user_id"],
        "opportunity_id": opp_id,
        "message": message,
        "read": 0,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "opportunity": opportunity,
    }

    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                """INSERT INTO smart_alert_triggers
                   (id, alert_id, user_id, opportunity_id, message, read, triggered_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    trigger["id"], trigger["alert_id"], trigger["user_id"],
                    trigger["opportunity_id"], trigger["message"],
                    trigger["read"], trigger["triggered_at"],
                ),
            )
            # Update alert trigger stats
            conn.execute(
                """UPDATE smart_alerts
                   SET last_triggered_at = ?, trigger_count = trigger_count + 1
                   WHERE id = ?""",
                (trigger["triggered_at"], alert["id"]),
            )
            conn.commit()
        finally:
            conn.close()

    _logger.info("Smart alert triggered: %s for user %s",
                 alert["id"], alert["user_id"])
    return trigger


def get_triggered_alerts(user_id: str, unread_only: bool = False,
                         limit: int = 50) -> List[dict]:
    """Get triggered alerts for a user."""
    conn = _get_db()
    try:
        query = """SELECT * FROM smart_alert_triggers
                   WHERE user_id = ?"""
        params: list = [user_id]
        if unread_only:
            query += " AND read = 0"
        query += " ORDER BY triggered_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_alerts_read(user_id: str, trigger_ids: List[str] = None) -> int:
    """Mark triggered alerts as read. If no IDs given, mark all as read."""
    with _lock:
        conn = _get_db()
        try:
            if trigger_ids:
                placeholders = ",".join("?" for _ in trigger_ids)
                cur = conn.execute(
                    f"""UPDATE smart_alert_triggers SET read = 1
                        WHERE user_id = ? AND id IN ({placeholders})""",
                    [user_id] + trigger_ids,
                )
            else:
                cur = conn.execute(
                    "UPDATE smart_alert_triggers SET read = 1 WHERE user_id = ?",
                    (user_id,),
                )
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()


def get_unread_count(user_id: str) -> int:
    """Get count of unread triggered alerts for a user."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM smart_alert_triggers WHERE user_id = ? AND read = 0",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def clear_triggered(user_id: str) -> None:
    """Clear all triggered alerts for a user."""
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                "DELETE FROM smart_alert_triggers WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()
