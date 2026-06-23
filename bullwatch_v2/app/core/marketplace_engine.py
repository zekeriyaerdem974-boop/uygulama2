# -*- coding: utf-8 -*-
"""Marketplace Engine — FAZ 29.

SQLite-backed strategy marketplace: publish, follow, metrics.

Public API:
  publish_strategy(...)           → dict
  unpublish_strategy(pub_id, uid) → bool
  get_published(pub_id)           → dict | None
  get_published_by_slug(slug)     → dict | None
  list_published(filters)         → list[dict]
  follow_strategy(pub_id, uid)    → bool
  unfollow_strategy(pub_id, uid)  → bool
  get_followers(pub_id)           → list[str]
  get_following(uid)              → list[dict]
  get_my_published(uid)           → list[dict]
  update_metrics(pub_id, metrics) → bool
  get_strategy_metrics(pub_id)    → dict
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.marketplace")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "marketplace.db")

_lock = threading.Lock()

_SLUG_RE = re.compile(r"[^a-z0-9]+")


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("marketplace.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS published_strategies (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            title           TEXT NOT NULL,
            slug            TEXT UNIQUE NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            strategy_code   TEXT NOT NULL,
            market          TEXT NOT NULL DEFAULT 'crypto',
            default_symbol  TEXT NOT NULL DEFAULT 'BTCUSDT',
            default_interval TEXT NOT NULL DEFAULT '1h',
            visibility      TEXT NOT NULL DEFAULT 'public',
            price_plan      TEXT NOT NULL DEFAULT 'free',
            is_live_enabled INTEGER NOT NULL DEFAULT 0,
            tags            TEXT NOT NULL DEFAULT '[]',
            risk_level      TEXT NOT NULL DEFAULT 'medium',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            is_active       INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS strategy_follows (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pub_id      TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (pub_id) REFERENCES published_strategies(id),
            UNIQUE(pub_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS strategy_metrics (
            pub_id          TEXT PRIMARY KEY,
            total_backtests INTEGER NOT NULL DEFAULT 0,
            win_rate        REAL NOT NULL DEFAULT 0,
            profit_factor   REAL NOT NULL DEFAULT 0,
            net_profit      REAL NOT NULL DEFAULT 0,
            max_drawdown    REAL NOT NULL DEFAULT 0,
            avg_trade       REAL NOT NULL DEFAULT 0,
            followers_count INTEGER NOT NULL DEFAULT 0,
            live_signal_count INTEGER NOT NULL DEFAULT 0,
            last_signal_time TEXT,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY (pub_id) REFERENCES published_strategies(id)
        );

        CREATE INDEX IF NOT EXISTS idx_pub_user ON published_strategies(user_id);
        CREATE INDEX IF NOT EXISTS idx_pub_slug ON published_strategies(slug);
        CREATE INDEX IF NOT EXISTS idx_pub_visibility ON published_strategies(visibility, is_active);
        CREATE INDEX IF NOT EXISTS idx_follow_pub ON strategy_follows(pub_id);
        CREATE INDEX IF NOT EXISTS idx_follow_user ON strategy_follows(user_id);
    """)


def _init_db():
    conn = _get_conn()
    try:
        _ensure_tables(conn)
    finally:
        conn.close()


_init_db()


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _make_slug(title: str) -> str:
    base = _SLUG_RE.sub("-", title.lower().strip()).strip("-")[:60]
    return base or "strategy"


def _unique_slug(conn: sqlite3.Connection, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while True:
        row = conn.execute(
            "SELECT 1 FROM published_strategies WHERE slug = ?", (slug,)
        ).fetchone()
        if not row:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            import json
            d["tags"] = json.loads(d["tags"])
        except Exception:
            d["tags"] = []
    return d


def _gen_id() -> str:
    return str(uuid.uuid4())[:12]


# ══════════════════════════════════════════════════════════════════
# PUBLISH / UNPUBLISH
# ══════════════════════════════════════════════════════════════════

def publish_strategy(
    user_id: str,
    title: str,
    description: str,
    strategy_code: str,
    market: str = "crypto",
    default_symbol: str = "BTCUSDT",
    default_interval: str = "1h",
    visibility: str = "public",
    price_plan: str = "free",
    tags: list | None = None,
    risk_level: str = "medium",
    metrics: dict | None = None,
) -> dict:
    """Publish a strategy to the marketplace."""
    import json

    if not title or not title.strip():
        raise ValueError("Başlık gerekli")
    if not strategy_code or not strategy_code.strip():
        raise ValueError("Strateji kodu gerekli")
    if visibility not in ("public", "private", "unlisted"):
        raise ValueError("Geçersiz görünürlük")
    if price_plan not in ("free", "premium", "subscription"):
        raise ValueError("Geçersiz fiyat planı")

    pub_id = _gen_id()
    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            slug = _unique_slug(conn, _make_slug(title))
            tags_json = json.dumps(tags or [])

            conn.execute("""
                INSERT INTO published_strategies
                (id, user_id, title, slug, description, strategy_code,
                 market, default_symbol, default_interval, visibility,
                 price_plan, is_live_enabled, tags, risk_level, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """, (pub_id, user_id, title.strip(), slug, description.strip(),
                  strategy_code.strip(), market, default_symbol, default_interval,
                  visibility, price_plan, tags_json, risk_level, now, now))

            # Initialize metrics
            m = metrics or {}
            conn.execute("""
                INSERT INTO strategy_metrics
                (pub_id, total_backtests, win_rate, profit_factor, net_profit,
                 max_drawdown, avg_trade, followers_count, live_signal_count,
                 last_signal_time, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, ?)
            """, (pub_id,
                  m.get("total_backtests", 0),
                  m.get("win_rate", 0),
                  m.get("profit_factor", 0),
                  m.get("net_profit", 0),
                  m.get("max_drawdown", 0),
                  m.get("avg_trade", 0),
                  now))

            conn.commit()

            row = conn.execute(
                "SELECT * FROM published_strategies WHERE id = ?", (pub_id,)
            ).fetchone()
            result = _row_to_dict(row)
            _logger.info("Strategy published: %s '%s' by user %s",
                         pub_id, title, user_id)
            return result
        finally:
            conn.close()


def unpublish_strategy(pub_id: str, user_id: str) -> bool:
    """Unpublish (soft-delete) a strategy."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "UPDATE published_strategies SET is_active = 0, updated_at = ? "
                "WHERE id = ? AND user_id = ?",
                (_now_iso(), pub_id, user_id)
            )
            conn.commit()
            ok = cur.rowcount > 0
            if ok:
                _logger.info("Strategy unpublished: %s by %s", pub_id, user_id)
            return ok
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# QUERY
# ══════════════════════════════════════════════════════════════════

def get_published(pub_id: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM published_strategies WHERE id = ? AND is_active = 1",
            (pub_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_published_by_slug(slug: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM published_strategies WHERE slug = ? AND is_active = 1",
            (slug,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_published(
    visibility: str = "public",
    market: str | None = None,
    tag: str | None = None,
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> List[dict]:
    """List published strategies with optional filters."""
    conn = _get_conn()
    try:
        clauses = ["ps.is_active = 1", "ps.visibility = ?"]
        params: list = [visibility]

        if market:
            clauses.append("ps.market = ?")
            params.append(market)
        if tag:
            clauses.append("ps.tags LIKE ?")
            params.append(f'%"{tag}"%')
        if search:
            clauses.append("(ps.title LIKE ? OR ps.description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = " AND ".join(clauses)

        order_map = {
            "newest": "ps.created_at DESC",
            "popular": "COALESCE(sm.followers_count, 0) DESC",
            "performance": "COALESCE(sm.win_rate, 0) DESC",
            "signals": "COALESCE(sm.live_signal_count, 0) DESC",
        }
        order = order_map.get(sort, "ps.created_at DESC")

        params.extend([limit, offset])

        rows = conn.execute(f"""
            SELECT ps.*, sm.win_rate, sm.profit_factor, sm.net_profit,
                   sm.max_drawdown, sm.followers_count, sm.live_signal_count,
                   sm.last_signal_time, sm.total_backtests, sm.avg_trade
            FROM published_strategies ps
            LEFT JOIN strategy_metrics sm ON sm.pub_id = ps.id
            WHERE {where}
            ORDER BY {order}
            LIMIT ? OFFSET ?
        """, params).fetchall()

        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_my_published(user_id: str) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT ps.*, sm.win_rate, sm.profit_factor, sm.net_profit,
                   sm.max_drawdown, sm.followers_count, sm.live_signal_count,
                   sm.last_signal_time, sm.total_backtests, sm.avg_trade
            FROM published_strategies ps
            LEFT JOIN strategy_metrics sm ON sm.pub_id = ps.id
            WHERE ps.user_id = ? AND ps.is_active = 1
            ORDER BY ps.created_at DESC
        """, (user_id,)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# FOLLOW / UNFOLLOW
# ══════════════════════════════════════════════════════════════════

def follow_strategy(pub_id: str, user_id: str) -> bool:
    """Follow a published strategy."""
    with _lock:
        conn = _get_conn()
        try:
            # Check strategy exists
            strat = conn.execute(
                "SELECT user_id FROM published_strategies WHERE id = ? AND is_active = 1",
                (pub_id,)
            ).fetchone()
            if not strat:
                raise ValueError("Strateji bulunamadı")
            if strat["user_id"] == user_id:
                raise ValueError("Kendi stratejinizi takip edemezsiniz")

            conn.execute(
                "INSERT OR IGNORE INTO strategy_follows (pub_id, user_id, created_at) "
                "VALUES (?, ?, ?)",
                (pub_id, user_id, _now_iso())
            )
            # Update follower count
            count = conn.execute(
                "SELECT COUNT(*) as c FROM strategy_follows WHERE pub_id = ?",
                (pub_id,)
            ).fetchone()["c"]
            conn.execute(
                "UPDATE strategy_metrics SET followers_count = ?, updated_at = ? WHERE pub_id = ?",
                (count, _now_iso(), pub_id)
            )
            conn.commit()
            _logger.info("User %s followed strategy %s", user_id, pub_id)
            return True
        except sqlite3.IntegrityError:
            return True  # Already following
        finally:
            conn.close()


def unfollow_strategy(pub_id: str, user_id: str) -> bool:
    """Unfollow a published strategy."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "DELETE FROM strategy_follows WHERE pub_id = ? AND user_id = ?",
                (pub_id, user_id)
            )
            if cur.rowcount > 0:
                count = conn.execute(
                    "SELECT COUNT(*) as c FROM strategy_follows WHERE pub_id = ?",
                    (pub_id,)
                ).fetchone()["c"]
                conn.execute(
                    "UPDATE strategy_metrics SET followers_count = ?, updated_at = ? WHERE pub_id = ?",
                    (count, _now_iso(), pub_id)
                )
                conn.commit()
                _logger.info("User %s unfollowed strategy %s", user_id, pub_id)
            return True
        finally:
            conn.close()


def get_followers(pub_id: str) -> List[str]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT user_id FROM strategy_follows WHERE pub_id = ?", (pub_id,)
        ).fetchall()
        return [r["user_id"] for r in rows]
    finally:
        conn.close()


def get_following(user_id: str) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT ps.*, sm.win_rate, sm.profit_factor, sm.net_profit,
                   sm.max_drawdown, sm.followers_count, sm.live_signal_count,
                   sm.last_signal_time, sm.total_backtests, sm.avg_trade
            FROM strategy_follows sf
            JOIN published_strategies ps ON ps.id = sf.pub_id
            LEFT JOIN strategy_metrics sm ON sm.pub_id = ps.id
            WHERE sf.user_id = ? AND ps.is_active = 1
            ORDER BY sf.created_at DESC
        """, (user_id,)).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def is_following(pub_id: str, user_id: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM strategy_follows WHERE pub_id = ? AND user_id = ?",
            (pub_id, user_id)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════

def update_metrics(pub_id: str, metrics: dict) -> bool:
    """Update performance metrics for a published strategy."""
    with _lock:
        conn = _get_conn()
        try:
            sets = []
            params = []
            for key in ("total_backtests", "win_rate", "profit_factor",
                        "net_profit", "max_drawdown", "avg_trade",
                        "live_signal_count", "last_signal_time"):
                if key in metrics:
                    sets.append(f"{key} = ?")
                    params.append(metrics[key])
            if not sets:
                return False
            sets.append("updated_at = ?")
            params.append(_now_iso())
            params.append(pub_id)
            conn.execute(
                f"UPDATE strategy_metrics SET {', '.join(sets)} WHERE pub_id = ?",
                params
            )
            conn.commit()
            return True
        finally:
            conn.close()


def get_strategy_metrics(pub_id: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM strategy_metrics WHERE pub_id = ?", (pub_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_publisher_username(user_id: str) -> str:
    """Get username for a publisher from users.db."""
    users_db = os.path.join(_DB_DIR, "users.db")
    if not os.path.exists(users_db):
        return "Anonim"
    try:
        conn = sqlite3.connect(users_db, timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return row["username"] if row else "Anonim"
    except Exception:
        return "Anonim"


def enrich_with_usernames(strategies: List[dict]) -> List[dict]:
    """Add publisher_username to each strategy dict."""
    user_ids = list({s["user_id"] for s in strategies})
    if not user_ids:
        return strategies
    users_db = os.path.join(_DB_DIR, "users.db")
    name_map: Dict[str, str] = {}
    if os.path.exists(users_db):
        try:
            conn = sqlite3.connect(users_db, timeout=5)
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" * len(user_ids))
            rows = conn.execute(
                f"SELECT id, username FROM users WHERE id IN ({placeholders})",
                user_ids
            ).fetchall()
            conn.close()
            for r in rows:
                name_map[r["id"]] = r["username"]
        except Exception:
            pass
    for s in strategies:
        s["publisher_username"] = name_map.get(s["user_id"], "Anonim")

    # Add publisher reputation (FAZ 35)
    try:
        from app.core.reputation_engine import get_reputation
        for s in strategies:
            rep = get_reputation(s["user_id"])
            s["publisher_reputation"] = rep.get("score", 0) if rep else 0
            s["publisher_trust_level"] = rep.get("trust_level", "") if rep else ""
    except Exception:
        for s in strategies:
            s["publisher_reputation"] = 0
            s["publisher_trust_level"] = ""

    return strategies
