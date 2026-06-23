# -*- coding: utf-8 -*-
"""User Settings Engine — FAZ 52.

Manages user preferences: language, theme, timezone, notifications,
market preferences, privacy, and security settings.

Uses the users.db database via db_manager.

Public API:
  get_user_settings(user_id)               → dict
  update_user_settings(user_id, updates)   → dict
  get_default_settings()                   → dict
  delete_user_settings(user_id)            → bool
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

from app.core.db_manager import get_connection

_logger = logging.getLogger("zkr_analiz.settings_engine")

_DB_NAME = "users.db"
_lock = threading.Lock()
_tables_ensured = False


# ── Default settings ─────────────────────────────────────────────
def get_default_settings() -> Dict:
    """Return default settings for a new user."""
    return {
        "language_code": "en",
        "theme": "dark_pro",
        "timezone": "UTC",
        "region": "",
        "date_format": "YYYY-MM-DD",
        "number_format": "standard",
        "currency_display": "USD",
        "notifications_enabled": True,
        "email_notifications": False,
        "push_notifications": False,
        "ai_brief_notifications": True,
        "opportunity_alerts": True,
        "portfolio_risk_alerts": True,
        "mentor_activity_notifications": False,
        "course_update_notifications": False,
        "live_room_notifications": False,
        "referral_reward_notifications": True,
        "market_preferences": ["crypto"],
        "profile_visibility": "public",
        "portfolio_visibility": "private",
        "analysis_visibility": "public",
        "search_indexing": True,
        "two_factor_enabled": False,
    }


# ── Schema ────────────────────────────────────────────────────────
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id            TEXT PRIMARY KEY,
    language_code      TEXT DEFAULT 'en',
    theme              TEXT DEFAULT 'dark_pro',
    timezone           TEXT DEFAULT 'UTC',
    region             TEXT DEFAULT '',
    date_format        TEXT DEFAULT 'YYYY-MM-DD',
    number_format      TEXT DEFAULT 'standard',
    currency_display   TEXT DEFAULT 'USD',
    notifications_enabled    INTEGER DEFAULT 1,
    email_notifications      INTEGER DEFAULT 0,
    push_notifications       INTEGER DEFAULT 0,
    ai_brief_notifications   INTEGER DEFAULT 1,
    opportunity_alerts       INTEGER DEFAULT 1,
    portfolio_risk_alerts    INTEGER DEFAULT 1,
    mentor_activity_notifications INTEGER DEFAULT 0,
    course_update_notifications   INTEGER DEFAULT 0,
    live_room_notifications       INTEGER DEFAULT 0,
    referral_reward_notifications INTEGER DEFAULT 1,
    market_preferences   TEXT DEFAULT '["crypto"]',
    profile_visibility   TEXT DEFAULT 'public',
    portfolio_visibility TEXT DEFAULT 'private',
    analysis_visibility  TEXT DEFAULT 'public',
    search_indexing      INTEGER DEFAULT 1,
    two_factor_enabled   INTEGER DEFAULT 0,
    created_at           TEXT,
    updated_at           TEXT
)
"""

_BOOL_FIELDS = frozenset({
    "notifications_enabled", "email_notifications", "push_notifications",
    "ai_brief_notifications", "opportunity_alerts", "portfolio_risk_alerts",
    "mentor_activity_notifications", "course_update_notifications",
    "live_room_notifications", "referral_reward_notifications",
    "search_indexing", "two_factor_enabled",
})

_TEXT_FIELDS = frozenset({
    "language_code", "theme", "timezone", "region", "date_format",
    "number_format", "currency_display", "profile_visibility",
    "portfolio_visibility", "analysis_visibility",
})

_JSON_FIELDS = frozenset({"market_preferences"})

_ALL_FIELDS = _BOOL_FIELDS | _TEXT_FIELDS | _JSON_FIELDS


def _ensure_table(conn) -> None:
    """Create user_settings table if not exists."""
    global _tables_ensured
    if _tables_ensured:
        return
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    _tables_ensured = True


def _row_to_dict(row) -> Dict:
    """Convert a Row object to a settings dict with proper types."""
    d = dict(row)
    for f in _BOOL_FIELDS:
        if f in d:
            d[f] = bool(d[f])
    for f in _JSON_FIELDS:
        if f in d and isinstance(d[f], str):
            try:
                d[f] = json.loads(d[f])
            except (json.JSONDecodeError, TypeError):
                d[f] = []
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════

def get_user_settings(user_id: str) -> Dict:
    """Get settings for a user. Creates defaults if none exist."""
    conn = get_connection(_DB_NAME)
    try:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return _row_to_dict(row)

        # Create default settings
        defaults = get_default_settings()
        _insert_defaults(conn, user_id, defaults)
        return {**defaults, "user_id": user_id}
    except Exception as e:
        _logger.warning("get_user_settings error: %s", e)
        return {**get_default_settings(), "user_id": user_id}
    finally:
        conn.close()


def _insert_defaults(conn, user_id: str, defaults: Dict) -> None:
    """Insert default settings row for a user."""
    now = _now_iso()
    with _lock:
        conn.execute(
            """INSERT OR IGNORE INTO user_settings
               (user_id, language_code, theme, timezone, region,
                date_format, number_format, currency_display,
                notifications_enabled, email_notifications,
                push_notifications, ai_brief_notifications,
                opportunity_alerts, portfolio_risk_alerts,
                mentor_activity_notifications, course_update_notifications,
                live_room_notifications, referral_reward_notifications,
                market_preferences, profile_visibility,
                portfolio_visibility, analysis_visibility,
                search_indexing, two_factor_enabled,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user_id,
                defaults["language_code"],
                defaults["theme"],
                defaults["timezone"],
                defaults.get("region", ""),
                defaults.get("date_format", "YYYY-MM-DD"),
                defaults.get("number_format", "standard"),
                defaults.get("currency_display", "USD"),
                int(defaults["notifications_enabled"]),
                int(defaults["email_notifications"]),
                int(defaults["push_notifications"]),
                int(defaults["ai_brief_notifications"]),
                int(defaults["opportunity_alerts"]),
                int(defaults["portfolio_risk_alerts"]),
                int(defaults.get("mentor_activity_notifications", False)),
                int(defaults.get("course_update_notifications", False)),
                int(defaults.get("live_room_notifications", False)),
                int(defaults.get("referral_reward_notifications", True)),
                json.dumps(defaults.get("market_preferences", ["crypto"])),
                defaults.get("profile_visibility", "public"),
                defaults.get("portfolio_visibility", "private"),
                defaults.get("analysis_visibility", "public"),
                int(defaults.get("search_indexing", True)),
                int(defaults.get("two_factor_enabled", False)),
                now, now,
            ),
        )
        conn.commit()


def update_user_settings(user_id: str, updates: Dict) -> Dict:
    """Update user settings. Only known fields are accepted.

    Returns the updated settings dict.
    """
    # Filter to allowed fields only
    filtered = {}
    for key, val in updates.items():
        if key not in _ALL_FIELDS:
            continue
        if key in _BOOL_FIELDS:
            filtered[key] = int(bool(val))
        elif key in _JSON_FIELDS:
            filtered[key] = json.dumps(val) if isinstance(val, (list, dict)) else val
        else:
            filtered[key] = str(val) if val is not None else ""

    if not filtered:
        return get_user_settings(user_id)

    # Ensure row exists
    _ = get_user_settings(user_id)

    filtered["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in filtered)
    values = list(filtered.values()) + [user_id]

    conn = get_connection(_DB_NAME)
    try:
        _ensure_table(conn)
        with _lock:
            conn.execute(
                f"UPDATE user_settings SET {set_clause} WHERE user_id = ?",
                values,
            )
            conn.commit()
    except Exception as e:
        _logger.warning("update_user_settings error: %s", e)
    finally:
        conn.close()

    return get_user_settings(user_id)


def delete_user_settings(user_id: str) -> bool:
    """Delete all settings for a user (for account deletion)."""
    conn = get_connection(_DB_NAME)
    try:
        _ensure_table(conn)
        with _lock:
            conn.execute(
                "DELETE FROM user_settings WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
        return True
    except Exception as e:
        _logger.warning("delete_user_settings error: %s", e)
        return False
    finally:
        conn.close()
