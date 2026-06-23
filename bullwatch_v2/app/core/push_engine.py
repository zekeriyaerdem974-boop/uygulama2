"""
ZKR Analiz Pro — Push Notification Engine (FAZ 43)
Device registration, preference management, message dispatch stub.
Ready for Firebase Cloud Messaging / OneSignal integration.
"""

import json
import os
import sqlite3
import threading
import time
import logging

log = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "push_engine.db")
DB_PATH = os.path.abspath(DB_PATH)

_lock = threading.Lock()


# ── Database ─────────────────────────────────────────────────────

def _get_db():
    from app.core.db_manager import get_connection
    conn = get_connection("push_engine.db", row_factory=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT NOT NULL,
            token         TEXT NOT NULL UNIQUE,
            platform      TEXT DEFAULT 'web',
            created_at    TEXT DEFAULT (datetime('now')),
            last_active   TEXT DEFAULT (datetime('now')),
            active        INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            user_id           TEXT PRIMARY KEY,
            alerts_enabled    INTEGER DEFAULT 1,
            opportunities     INTEGER DEFAULT 1,
            activity_stream   INTEGER DEFAULT 1,
            price_alerts      INTEGER DEFAULT 1,
            quiet_start       TEXT DEFAULT '23:00',
            quiet_end         TEXT DEFAULT '07:00'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS push_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT,
            title       TEXT,
            body        TEXT,
            tag         TEXT,
            sent_at     TEXT DEFAULT (datetime('now')),
            status      TEXT DEFAULT 'queued'
        )
    """)
    conn.commit()
    return conn


# ── Device Registration ──────────────────────────────────────────

def register_device(user_id: str, token: str, platform: str = "web") -> bool:
    """Register a push notification device token."""
    with _lock:
        try:
            conn = _get_db()
            conn.execute(
                "INSERT OR REPLACE INTO devices (user_id, token, platform, last_active, active) VALUES (?, ?, ?, datetime('now'), 1)",
                (str(user_id), str(token), str(platform)),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log.error("register_device error: %s", e)
            return False


def unregister_device(token: str) -> bool:
    """Deactivate a device token."""
    with _lock:
        try:
            conn = _get_db()
            conn.execute("UPDATE devices SET active = 0 WHERE token = ?", (str(token),))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log.error("unregister_device error: %s", e)
            return False


def get_user_devices(user_id: str) -> list:
    """Get all active devices for a user."""
    with _lock:
        try:
            conn = _get_db()
            rows = conn.execute(
                "SELECT token, platform, last_active FROM devices WHERE user_id = ? AND active = 1",
                (str(user_id),),
            ).fetchall()
            conn.close()
            return [{"token": r[0], "platform": r[1], "last_active": r[2]} for r in rows]
        except Exception:
            return []


# ── Preferences ──────────────────────────────────────────────────

def get_preferences(user_id: str) -> dict:
    """Get user push notification preferences."""
    defaults = {
        "alerts_enabled": True,
        "opportunities": True,
        "activity_stream": True,
        "price_alerts": True,
        "quiet_start": "23:00",
        "quiet_end": "07:00",
    }
    with _lock:
        try:
            conn = _get_db()
            row = conn.execute(
                "SELECT alerts_enabled, opportunities, activity_stream, price_alerts, quiet_start, quiet_end FROM preferences WHERE user_id = ?",
                (str(user_id),),
            ).fetchone()
            conn.close()
            if not row:
                return defaults
            return {
                "alerts_enabled": bool(row[0]),
                "opportunities": bool(row[1]),
                "activity_stream": bool(row[2]),
                "price_alerts": bool(row[3]),
                "quiet_start": row[4] or "23:00",
                "quiet_end": row[5] or "07:00",
            }
        except Exception:
            return defaults


def update_preferences(user_id: str, prefs: dict) -> bool:
    """Update user push notification preferences."""
    with _lock:
        try:
            conn = _get_db()
            conn.execute(
                """INSERT INTO preferences (user_id, alerts_enabled, opportunities, activity_stream, price_alerts, quiet_start, quiet_end)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     alerts_enabled=excluded.alerts_enabled,
                     opportunities=excluded.opportunities,
                     activity_stream=excluded.activity_stream,
                     price_alerts=excluded.price_alerts,
                     quiet_start=excluded.quiet_start,
                     quiet_end=excluded.quiet_end""",
                (
                    str(user_id),
                    int(prefs.get("alerts_enabled", 1)),
                    int(prefs.get("opportunities", 1)),
                    int(prefs.get("activity_stream", 1)),
                    int(prefs.get("price_alerts", 1)),
                    str(prefs.get("quiet_start", "23:00")),
                    str(prefs.get("quiet_end", "07:00")),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log.error("update_preferences error: %s", e)
            return False


# ── Send Push (Stub) ─────────────────────────────────────────────

def send_push(user_id: str, title: str, body: str, tag: str = "general", url: str = "/discover") -> bool:
    """
    Send a push notification to all user devices.
    Currently a stub — logs the push and stores in push_log.
    Replace innards with Firebase / OneSignal SDK when ready.
    """
    with _lock:
        try:
            conn = _get_db()
            # Log the push
            conn.execute(
                "INSERT INTO push_log (user_id, title, body, tag, status) VALUES (?, ?, ?, ?, 'sent')",
                (str(user_id), str(title)[:200], str(body)[:500], str(tag)),
            )
            conn.commit()
            conn.close()
            log.info("Push stub: user=%s title=%s", user_id, title)
            return True
        except Exception as e:
            log.error("send_push error: %s", e)
            return False


def get_push_log(user_id: str, limit: int = 20) -> list:
    """Get push notification history for user."""
    with _lock:
        try:
            conn = _get_db()
            rows = conn.execute(
                "SELECT id, title, body, tag, sent_at, status FROM push_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (str(user_id), min(int(limit), 100)),
            ).fetchall()
            conn.close()
            return [
                {"id": r[0], "title": r[1], "body": r[2], "tag": r[3], "sent_at": r[4], "status": r[5]}
                for r in rows
            ]
        except Exception:
            return []


# ── Stats ────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Get push notification system stats."""
    with _lock:
        try:
            conn = _get_db()
            devices = conn.execute("SELECT COUNT(*) FROM devices WHERE active = 1").fetchone()[0]
            total_sent = conn.execute("SELECT COUNT(*) FROM push_log").fetchone()[0]
            conn.close()
            return {"active_devices": devices, "total_sent": total_sent}
        except Exception:
            return {"active_devices": 0, "total_sent": 0}
