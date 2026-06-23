# -*- coding: utf-8 -*-
"""Share Engine — FAZ 44.

Generates shareable URLs and card metadata for various content types:
analyses, portfolio snapshots, activity insights, mentor profiles, strategies.

Public API:
  generate_share_url(content_type, content_id, user_id)  → str
  generate_share_card(content_type, content_id)           → dict
  get_share_stats(content_type, content_id)               → dict
  track_share_click(share_id)                             → bool
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import threading
from typing import Any, Dict, Optional

_logger = logging.getLogger("zkr_analiz.share_engine")

_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
_DB_PATH = os.path.join(_DB_DIR, "share_engine.db")
_lock = threading.Lock()

# Shareable content types
CONTENT_TYPES = {
    "analysis": {"label": "Analysis", "icon": "📊", "base_path": "/analysis"},
    "portfolio": {"label": "Portfolio Snapshot", "icon": "💼", "base_path": "/portfolio"},
    "activity": {"label": "Activity Insight", "icon": "⚡", "base_path": "/activity"},
    "mentor": {"label": "Mentor Profile", "icon": "🎓", "base_path": "/mentors"},
    "strategy": {"label": "Strategy", "icon": "⚙️", "base_path": "/strategy-builder"},
    "course": {"label": "Course", "icon": "📚", "base_path": "/courses"},
}

BANNED_WORDS = {"BUY", "SELL", "ENTRY", "EXIT", "TAKE PROFIT", "STOP LOSS", "TRADE NOW"}


def _sanitize(text: str) -> str:
    if not text:
        return ""
    result = text
    for word in BANNED_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub("***", result)
    return result.strip()


def _get_db() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    conn = get_connection("share_engine.db", row_factory=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            share_id      TEXT NOT NULL UNIQUE,
            content_type  TEXT NOT NULL,
            content_id    TEXT NOT NULL,
            user_id       TEXT DEFAULT '',
            title         TEXT DEFAULT '',
            description   TEXT DEFAULT '',
            clicks        INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_share_content ON shares(content_type, content_id)")
    conn.commit()
    return conn


def _make_share_id(content_type: str, content_id: str, user_id: str = "") -> str:
    seed = f"{content_type}:{content_id}:{user_id}"
    return hashlib.sha256(seed.encode()).hexdigest()[:12]


def generate_share_url(
    content_type: str,
    content_id: str,
    user_id: str = "",
    title: str = "",
    description: str = "",
) -> str:
    """Generate a shareable URL for content."""
    if content_type not in CONTENT_TYPES:
        return ""
    content_id = str(content_id).strip()
    share_id = _make_share_id(content_type, content_id, user_id)
    ct = CONTENT_TYPES[content_type]

    with _lock:
        try:
            conn = _get_db()
            existing = conn.execute(
                "SELECT share_id FROM shares WHERE share_id = ?", (share_id,)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO shares (share_id, content_type, content_id, user_id, title, description) VALUES (?, ?, ?, ?, ?, ?)",
                    (share_id, content_type, content_id, str(user_id), _sanitize(title)[:200], _sanitize(description)[:500]),
                )
                conn.commit()
            conn.close()
        except Exception as e:
            _logger.error("generate_share_url error: %s", e)

    return f"/share/{share_id}"


def generate_share_card(content_type: str, content_id: str, user_id: str = "") -> Dict:
    """Generate share card metadata for social media previews."""
    if content_type not in CONTENT_TYPES:
        return {}
    ct = CONTENT_TYPES[content_type]
    share_url = generate_share_url(content_type, content_id, user_id)

    return {
        "content_type": content_type,
        "content_id": content_id,
        "label": ct["label"],
        "icon": ct["icon"],
        "share_url": share_url,
        "title": f"ZKR Analiz Pro — {ct['label']}",
        "description": _sanitize(f"Check out this {ct['label'].lower()} on ZKR Analiz Pro"),
        "image": "/static/icons/icon-512.png",
        "platforms": {
            "twitter": f"https://twitter.com/intent/tweet?text={ct['label']}%20on%20ZKR Analiz%20Pro&url=",
            "telegram": f"https://t.me/share/url?url=",
            "whatsapp": f"https://wa.me/?text=",
        },
    }


def get_share_stats(content_type: str, content_id: str) -> Dict:
    """Get sharing stats for content."""
    with _lock:
        try:
            conn = _get_db()
            rows = conn.execute(
                "SELECT share_id, clicks, created_at FROM shares WHERE content_type = ? AND content_id = ?",
                (content_type, str(content_id)),
            ).fetchall()
            conn.close()
            total_clicks = sum(r[1] for r in rows)
            return {
                "content_type": content_type,
                "content_id": content_id,
                "total_shares": len(rows),
                "total_clicks": total_clicks,
            }
        except Exception:
            return {"content_type": content_type, "content_id": content_id, "total_shares": 0, "total_clicks": 0}


def track_share_click(share_id: str) -> bool:
    """Track a click on a shared link."""
    if not share_id:
        return False
    with _lock:
        try:
            conn = _get_db()
            conn.execute("UPDATE shares SET clicks = clicks + 1 WHERE share_id = ?", (str(share_id),))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False


def get_share_by_id(share_id: str) -> Optional[Dict]:
    """Look up a share record by share_id."""
    if not share_id:
        return None
    with _lock:
        try:
            conn = _get_db()
            row = conn.execute(
                "SELECT share_id, content_type, content_id, user_id, title, description, clicks, created_at FROM shares WHERE share_id = ?",
                (str(share_id),),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                "share_id": row[0],
                "content_type": row[1],
                "content_id": row[2],
                "user_id": row[3],
                "title": row[4],
                "description": row[5],
                "clicks": row[6],
                "created_at": row[7],
            }
        except Exception:
            return None
