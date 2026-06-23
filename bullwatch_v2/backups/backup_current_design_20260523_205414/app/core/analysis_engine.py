# -*- coding: utf-8 -*-
"""Analysis / Growth Engine — FAZ 36 (Viral Sharing).

SQLite-backed analysis sharing: analysis posts, public pages,
leaderboard, trending, feature flags.

Public API:
  create_analysis(...)            → dict
  get_analysis(analysis_id)       → dict | None
  get_analysis_feed(...)          → list[dict]
  get_user_analyses(user_id, ..)  → list[dict]
  toggle_analysis_like(...)       → dict
  add_analysis_comment(...)       → dict
  get_analysis_comments(id)       → list[dict]
  delete_analysis(id, user_id)    → bool
  get_trending_analyses(limit)    → list[dict]
  get_leaderboard(limit)          → list[dict]
  get_analyst_stats(user_id)      → dict
  feature_enabled(feature_name)   → bool
  set_feature(name, enabled)      → dict
  list_features()                 → list[dict]
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.analysis")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "analysis.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("analysis.db")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())[:12]


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_posts (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            title           TEXT NOT NULL DEFAULT '',
            content         TEXT NOT NULL,
            symbol          TEXT,
            market          TEXT,
            timeframe       TEXT,
            direction       TEXT,
            chart_image     TEXT,
            is_public       INTEGER NOT NULL DEFAULT 1,
            views_count     INTEGER NOT NULL DEFAULT 0,
            likes_count     INTEGER NOT NULL DEFAULT 0,
            comments_count  INTEGER NOT NULL DEFAULT 0,
            shares_count    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analysis_comments (
            id          TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (analysis_id) REFERENCES analysis_posts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analysis_likes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            analysis_id TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (analysis_id) REFERENCES analysis_posts(id) ON DELETE CASCADE,
            UNIQUE(user_id, analysis_id)
        );

        CREATE TABLE IF NOT EXISTS platform_features (
            name        TEXT PRIMARY KEY,
            enabled     INTEGER NOT NULL DEFAULT 1,
            updated_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_ap_user ON analysis_posts(user_id);
        CREATE INDEX IF NOT EXISTS idx_ap_created ON analysis_posts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ap_symbol ON analysis_posts(symbol);
        CREATE INDEX IF NOT EXISTS idx_ap_likes ON analysis_posts(likes_count DESC);
        CREATE INDEX IF NOT EXISTS idx_ac_analysis ON analysis_comments(analysis_id);
        CREATE INDEX IF NOT EXISTS idx_al_analysis ON analysis_likes(analysis_id);
        CREATE INDEX IF NOT EXISTS idx_al_user ON analysis_likes(user_id);
    """)

    # Seed default feature flags
    defaults = [
        ("courses", 0),
        ("live_rooms", 0),
        ("subscriptions", 0),
        ("marketplace", 1),
        ("social_feed", 1),
        ("mentors", 1),
        ("analysis_sharing", 1),
        ("leaderboard", 1),
    ]
    now = _now_iso()
    for name, enabled in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO platform_features (name, enabled, updated_at) VALUES (?, ?, ?)",
            (name, enabled, now)
        )
    conn.commit()


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

def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _get_username(user_id: str) -> str:
    if not os.path.exists(_USERS_DB):
        return "Anonim"
    try:
        conn = sqlite3.connect(_USERS_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return row["username"] if row else "Anonim"
    except Exception:
        return "Anonim"


def _get_user_id_by_username(username: str) -> Optional[str]:
    if not os.path.exists(_USERS_DB):
        return None
    try:
        conn = sqlite3.connect(_USERS_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        return row["id"] if row else None
    except Exception:
        return None


def _enrich_analyses(analyses: list, viewer_id: str | None = None) -> list:
    """Add username and viewer-specific info to analyses."""
    if not analyses:
        return analyses

    user_ids = list({a["user_id"] for a in analyses})
    name_map: Dict[str, str] = {}
    if os.path.exists(_USERS_DB):
        try:
            conn = sqlite3.connect(_USERS_DB, timeout=5)
            conn.row_factory = sqlite3.Row
            ph = ",".join("?" * len(user_ids))
            rows = conn.execute(
                f"SELECT id, username FROM users WHERE id IN ({ph})", user_ids
            ).fetchall()
            conn.close()
            for r in rows:
                name_map[r["id"]] = r["username"]
        except Exception:
            pass

    liked_set = set()
    if viewer_id:
        analysis_ids = [a["id"] for a in analyses]
        conn = _get_conn()
        try:
            ph = ",".join("?" * len(analysis_ids))
            rows = conn.execute(
                f"SELECT analysis_id FROM analysis_likes WHERE user_id = ? AND analysis_id IN ({ph})",
                [viewer_id] + analysis_ids
            ).fetchall()
            liked_set = {r["analysis_id"] for r in rows}
        finally:
            conn.close()

    # Reputation info
    rep_map: Dict[str, dict] = {}
    try:
        from app.core.reputation_engine import get_reputation
        for uid in user_ids:
            rep = get_reputation(uid)
            if rep:
                rep_map[uid] = rep
    except Exception:
        pass

    for a in analyses:
        a["username"] = name_map.get(a["user_id"], "Anonim")
        a["is_liked"] = a["id"] in liked_set
        rep = rep_map.get(a["user_id"], {})
        a["trust_level"] = rep.get("trust_level", "")
        a["reputation_score"] = rep.get("score", 0)

    return analyses


# ══════════════════════════════════════════════════════════════════
# ANALYSIS POSTS
# ══════════════════════════════════════════════════════════════════

def create_analysis(
    user_id: str,
    content: str,
    title: str = "",
    symbol: str | None = None,
    market: str | None = None,
    timeframe: str | None = None,
    direction: str | None = None,
    chart_image: str | None = None,
    is_public: bool = True,
) -> dict:
    """Create a new analysis post."""
    if not content or not content.strip():
        raise ValueError("İçerik gerekli")

    analysis_id = _gen_id()
    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT INTO analysis_posts
                  (id, user_id, title, content, symbol, market, timeframe, direction,
                   chart_image, is_public, views_count, likes_count, comments_count,
                   shares_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?, ?)
            """, (analysis_id, user_id, (title or "").strip(), content.strip(),
                  symbol, market, timeframe, direction, chart_image,
                  1 if is_public else 0, now, now))
            conn.commit()

            row = conn.execute(
                "SELECT * FROM analysis_posts WHERE id = ?", (analysis_id,)
            ).fetchone()
            result = _row_to_dict(row)
            result["username"] = _get_username(user_id)
            result["is_liked"] = False
            result["trust_level"] = ""
            result["reputation_score"] = 0
            _logger.info("Analysis created: %s by user %s", analysis_id, user_id)
            return result
        finally:
            conn.close()


def get_analysis(analysis_id: str, viewer_id: str | None = None,
                 increment_views: bool = False) -> Optional[dict]:
    """Get a single analysis with details."""
    conn = _get_conn()
    try:
        if increment_views:
            conn.execute(
                "UPDATE analysis_posts SET views_count = views_count + 1 WHERE id = ?",
                (analysis_id,)
            )
            conn.commit()

        row = conn.execute(
            "SELECT * FROM analysis_posts WHERE id = ?", (analysis_id,)
        ).fetchone()
        if not row:
            return None
        analyses = _enrich_analyses([_row_to_dict(row)], viewer_id)
        return analyses[0]
    finally:
        conn.close()


def delete_analysis(analysis_id: str, user_id: str) -> bool:
    """Delete analysis (only by owner)."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "DELETE FROM analysis_posts WHERE id = ? AND user_id = ?",
                (analysis_id, user_id)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_analysis_feed(
    limit: int = 20,
    offset: int = 0,
    symbol: str | None = None,
    viewer_id: str | None = None,
) -> list:
    """Get global analysis feed, newest first."""
    conn = _get_conn()
    try:
        if symbol:
            rows = conn.execute(
                "SELECT * FROM analysis_posts WHERE symbol = ? AND is_public = 1 "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (symbol, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM analysis_posts WHERE is_public = 1 "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_analyses(posts, viewer_id)
    finally:
        conn.close()


def get_user_analyses(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    viewer_id: str | None = None,
) -> list:
    """Get analyses by a specific user."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM analysis_posts WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset)
        ).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_analyses(posts, viewer_id)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# LIKES
# ══════════════════════════════════════════════════════════════════

def toggle_analysis_like(analysis_id: str, user_id: str) -> dict:
    """Toggle like on an analysis."""
    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM analysis_likes WHERE user_id = ? AND analysis_id = ?",
                (user_id, analysis_id)
            ).fetchone()

            if existing:
                conn.execute(
                    "DELETE FROM analysis_likes WHERE user_id = ? AND analysis_id = ?",
                    (user_id, analysis_id)
                )
                conn.execute(
                    "UPDATE analysis_posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?",
                    (analysis_id,)
                )
                liked = False
            else:
                conn.execute(
                    "INSERT INTO analysis_likes (user_id, analysis_id, created_at) VALUES (?, ?, ?)",
                    (user_id, analysis_id, _now_iso())
                )
                conn.execute(
                    "UPDATE analysis_posts SET likes_count = likes_count + 1 WHERE id = ?",
                    (analysis_id,)
                )
                liked = True

            conn.commit()
            row = conn.execute(
                "SELECT likes_count FROM analysis_posts WHERE id = ?", (analysis_id,)
            ).fetchone()
            return {
                "ok": True,
                "liked": liked,
                "likes_count": row["likes_count"] if row else 0,
            }
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# COMMENTS
# ══════════════════════════════════════════════════════════════════

def add_analysis_comment(analysis_id: str, user_id: str, content: str) -> dict:
    """Add a comment to an analysis."""
    if not content or not content.strip():
        raise ValueError("Yorum gerekli")

    comment_id = _gen_id()
    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO analysis_comments (id, analysis_id, user_id, content, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (comment_id, analysis_id, user_id, content.strip(), now)
            )
            conn.execute(
                "UPDATE analysis_posts SET comments_count = comments_count + 1 WHERE id = ?",
                (analysis_id,)
            )
            conn.commit()

            return {
                "id": comment_id,
                "analysis_id": analysis_id,
                "user_id": user_id,
                "username": _get_username(user_id),
                "content": content.strip(),
                "created_at": now,
            }
        finally:
            conn.close()


def get_analysis_comments(analysis_id: str, limit: int = 50) -> list:
    """Get comments for an analysis."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM analysis_comments WHERE analysis_id = ? "
            "ORDER BY created_at ASC LIMIT ?",
            (analysis_id, limit)
        ).fetchall()
        comments = [_row_to_dict(r) for r in rows]

        user_ids = list({c["user_id"] for c in comments})
        name_map: Dict[str, str] = {}
        if user_ids and os.path.exists(_USERS_DB):
            try:
                uconn = sqlite3.connect(_USERS_DB, timeout=5)
                uconn.row_factory = sqlite3.Row
                ph = ",".join("?" * len(user_ids))
                urows = uconn.execute(
                    f"SELECT id, username FROM users WHERE id IN ({ph})", user_ids
                ).fetchall()
                uconn.close()
                for r in urows:
                    name_map[r["id"]] = r["username"]
            except Exception:
                pass

        for c in comments:
            c["username"] = name_map.get(c["user_id"], "Anonim")

        return comments
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# SHARES
# ══════════════════════════════════════════════════════════════════

def increment_shares(analysis_id: str) -> dict:
    """Increment share counter for an analysis."""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE analysis_posts SET shares_count = shares_count + 1 WHERE id = ?",
                (analysis_id,)
            )
            conn.commit()
            row = conn.execute(
                "SELECT shares_count FROM analysis_posts WHERE id = ?", (analysis_id,)
            ).fetchone()
            return {"ok": True, "shares_count": row["shares_count"] if row else 0}
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# TRENDING & LEADERBOARD
# ══════════════════════════════════════════════════════════════════

def get_trending_analyses(limit: int = 10) -> list:
    """Get trending analyses — most liked + viewed in recent period."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM analysis_posts WHERE is_public = 1 "
            "ORDER BY (likes_count * 3 + views_count + comments_count * 2 + shares_count * 5) DESC, "
            "created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_analyses(posts)
    finally:
        conn.close()


def get_leaderboard(limit: int = 20) -> list:
    """Get analyst leaderboard — users ranked by analysis engagement."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT user_id,
                   COUNT(*) as analysis_count,
                   COALESCE(SUM(likes_count), 0) as total_likes,
                   COALESCE(SUM(views_count), 0) as total_views,
                   COALESCE(SUM(comments_count), 0) as total_comments,
                   COALESCE(SUM(shares_count), 0) as total_shares
            FROM analysis_posts
            WHERE is_public = 1
            GROUP BY user_id
            ORDER BY (SUM(likes_count) * 3 + SUM(views_count) + SUM(comments_count) * 2 + SUM(shares_count) * 5) DESC
            LIMIT ?
        """, (limit,)).fetchall()

        results = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            d["score"] = d["total_likes"] * 3 + d["total_views"] + d["total_comments"] * 2 + d["total_shares"] * 5

            # Get reputation info
            try:
                from app.core.reputation_engine import get_reputation
                rep = get_reputation(d["user_id"])
                d["trust_level"] = rep.get("trust_level", "") if rep else ""
                d["reputation_score"] = rep.get("score", 0) if rep else 0
            except Exception:
                d["trust_level"] = ""
                d["reputation_score"] = 0

            results.append(d)

        return results
    finally:
        conn.close()


def get_analyst_stats(user_id: str) -> dict:
    """Get analysis stats for a user."""
    conn = _get_conn()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as analysis_count,
                   COALESCE(SUM(likes_count), 0) as total_likes,
                   COALESCE(SUM(views_count), 0) as total_views,
                   COALESCE(SUM(comments_count), 0) as total_comments,
                   COALESCE(SUM(shares_count), 0) as total_shares
            FROM analysis_posts
            WHERE user_id = ?
        """, (user_id,)).fetchone()
        return _row_to_dict(row) if row else {
            "analysis_count": 0, "total_likes": 0, "total_views": 0,
            "total_comments": 0, "total_shares": 0,
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ══════════════════════════════════════════════════════════════════

def feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT enabled FROM platform_features WHERE name = ?",
            (feature_name,)
        ).fetchone()
        # Default to True for unknown features
        return bool(row["enabled"]) if row else True
    finally:
        conn.close()


def set_feature(name: str, enabled: bool) -> dict:
    """Enable or disable a platform feature."""
    now = _now_iso()
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO platform_features (name, enabled, updated_at) "
                "VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET enabled = ?, updated_at = ?",
                (name, 1 if enabled else 0, now, 1 if enabled else 0, now)
            )
            conn.commit()
            return {"ok": True, "feature": name, "enabled": enabled}
        finally:
            conn.close()


def list_features() -> list:
    """List all feature flags."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM platform_features ORDER BY name"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()
