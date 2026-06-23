# -*- coding: utf-8 -*-
"""Social Trading Feed Engine — FAZ 31.

SQLite-backed social feed: posts, comments, likes, user follows.

Public API:
  create_post(...)                → dict
  get_post(post_id)               → dict | None
  get_feed(limit, offset)         → list[dict]
  get_user_feed(user_id, ...)     → list[dict]
  get_following_feed(user_id, .) → list[dict]
  delete_post(post_id, user_id)   → bool
  add_comment(post_id, uid, ..)   → dict
  get_comments(post_id)           → list[dict]
  toggle_like(post_id, user_id)   → dict
  follow_user(follower, target)   → bool
  unfollow_user(follower, target)  → bool
  get_user_profile(username)      → dict | None
  get_followers(user_id)          → list[str]
  get_following(user_id)          → list[str]
  get_trending(limit)             → list[dict]
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.social")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "social.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("social.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            content         TEXT NOT NULL,
            symbol          TEXT,
            market          TEXT,
            timeframe       TEXT,
            chart_snapshot   TEXT,
            created_at      TEXT NOT NULL,
            likes_count     INTEGER NOT NULL DEFAULT 0,
            comments_count  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS comments (
            id          TEXT PRIMARY KEY,
            post_id     TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS likes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            post_id     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            UNIQUE(user_id, post_id)
        );

        CREATE TABLE IF NOT EXISTS follows (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_user_id    TEXT NOT NULL,
            following_user_id   TEXT NOT NULL,
            created_at          TEXT NOT NULL,
            UNIQUE(follower_user_id, following_user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id);
        CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_posts_symbol ON posts(symbol);
        CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
        CREATE INDEX IF NOT EXISTS idx_likes_post ON likes(post_id);
        CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id);
        CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_user_id);
        CREATE INDEX IF NOT EXISTS idx_follows_following ON follows(following_user_id);
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

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())[:12]


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


def _enrich_posts(posts: list, viewer_id: str | None = None) -> list:
    """Add username and viewer-specific info to posts."""
    if not posts:
        return posts

    user_ids = list({p["user_id"] for p in posts})
    name_map: Dict[str, str] = {}
    if os.path.exists(_USERS_DB):
        try:
            conn = sqlite3.connect(_USERS_DB, timeout=5)
            conn.row_factory = sqlite3.Row
            ph = ",".join("?" * len(user_ids))
            rows = conn.execute(f"SELECT id, username FROM users WHERE id IN ({ph})", user_ids).fetchall()
            conn.close()
            for r in rows:
                name_map[r["id"]] = r["username"]
        except Exception:
            pass

    liked_set = set()
    if viewer_id:
        post_ids = [p["id"] for p in posts]
        conn = _get_conn()
        try:
            ph = ",".join("?" * len(post_ids))
            rows = conn.execute(
                f"SELECT post_id FROM likes WHERE user_id = ? AND post_id IN ({ph})",
                [viewer_id] + post_ids
            ).fetchall()
            liked_set = {r["post_id"] for r in rows}
        finally:
            conn.close()

    # Check which users are mentors
    mentor_set = set()
    try:
        from app.core.mentor_engine import get_mentor_ids
        mentor_set = get_mentor_ids(user_ids)
    except Exception:
        pass

    for p in posts:
        p["username"] = name_map.get(p["user_id"], "Anonim")
        p["is_liked"] = p["id"] in liked_set
        p["is_mentor"] = p["user_id"] in mentor_set
        p["trust_level"] = ""
        p["reputation_score"] = 0

    # Add reputation info (FAZ 35)
    try:
        from app.core.reputation_engine import get_reputation
        for p in posts:
            rep = get_reputation(p["user_id"])
            if rep:
                p["trust_level"] = rep.get("trust_level", "")
                p["reputation_score"] = rep.get("score", 0)
    except Exception:
        pass

    return posts


# ══════════════════════════════════════════════════════════════════
# POSTS
# ══════════════════════════════════════════════════════════════════

def create_post(
    user_id: str,
    content: str,
    symbol: str | None = None,
    market: str | None = None,
    timeframe: str | None = None,
    chart_snapshot: str | None = None,
) -> dict:
    """Create a new social post."""
    if not content or not content.strip():
        raise ValueError("İçerik gerekli")

    post_id = _gen_id()
    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT INTO posts (id, user_id, content, symbol, market, timeframe,
                                   chart_snapshot, created_at, likes_count, comments_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (post_id, user_id, content.strip(), symbol, market, timeframe,
                  chart_snapshot, now))
            conn.commit()

            row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
            result = _row_to_dict(row)
            result["username"] = _get_username(user_id)
            result["is_liked"] = False
            _logger.info("Post created: %s by user %s", post_id, user_id)
            return result
        finally:
            conn.close()


def get_post(post_id: str, viewer_id: str | None = None) -> Optional[dict]:
    """Get a single post with details."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return None
        posts = _enrich_posts([_row_to_dict(row)], viewer_id)
        return posts[0]
    finally:
        conn.close()


def delete_post(post_id: str, user_id: str) -> bool:
    """Delete a post (only by owner)."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "DELETE FROM posts WHERE id = ? AND user_id = ?",
                (post_id, user_id)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_feed(
    limit: int = 20,
    offset: int = 0,
    symbol: str | None = None,
    viewer_id: str | None = None,
) -> list:
    """Get global feed, newest first."""
    conn = _get_conn()
    try:
        if symbol:
            rows = conn.execute(
                "SELECT * FROM posts WHERE symbol = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (symbol, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM posts ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_posts(posts, viewer_id)
    finally:
        conn.close()


def get_user_feed(user_id: str, limit: int = 20, offset: int = 0,
                  viewer_id: str | None = None) -> list:
    """Get posts by a specific user."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (user_id, limit, offset)
        ).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_posts(posts, viewer_id)
    finally:
        conn.close()


def get_following_feed(user_id: str, limit: int = 20, offset: int = 0) -> list:
    """Get feed from followed users."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT p.* FROM posts p
            JOIN follows f ON f.following_user_id = p.user_id
            WHERE f.follower_user_id = ?
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset)).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_posts(posts, user_id)
    finally:
        conn.close()


def get_trending(limit: int = 10) -> list:
    """Get trending posts (most liked in last 48h)."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM posts
            WHERE datetime(created_at) >= datetime('now', '-48 hours')
            ORDER BY likes_count DESC, comments_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        posts = [_row_to_dict(r) for r in rows]
        return _enrich_posts(posts)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# COMMENTS
# ══════════════════════════════════════════════════════════════════

def add_comment(post_id: str, user_id: str, content: str) -> dict:
    """Add a comment to a post."""
    if not content or not content.strip():
        raise ValueError("Yorum içeriği gerekli")

    comment_id = _gen_id()
    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            # Verify post exists
            post = conn.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
            if not post:
                raise ValueError("Post bulunamadı")

            conn.execute(
                "INSERT INTO comments (id, post_id, user_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (comment_id, post_id, user_id, content.strip(), now)
            )
            conn.execute(
                "UPDATE posts SET comments_count = comments_count + 1 WHERE id = ?",
                (post_id,)
            )
            conn.commit()

            result = {
                "id": comment_id,
                "post_id": post_id,
                "user_id": user_id,
                "content": content.strip(),
                "created_at": now,
                "username": _get_username(user_id),
            }
            _logger.info("Comment added: %s on post %s", comment_id, post_id)
            return result
        finally:
            conn.close()


def get_comments(post_id: str, limit: int = 50) -> list:
    """Get comments for a post."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY created_at ASC LIMIT ?",
            (post_id, limit)
        ).fetchall()
        comments = [_row_to_dict(r) for r in rows]

        # Enrich with usernames
        user_ids = list({c["user_id"] for c in comments})
        if user_ids and os.path.exists(_USERS_DB):
            try:
                uconn = sqlite3.connect(_USERS_DB, timeout=5)
                uconn.row_factory = sqlite3.Row
                ph = ",".join("?" * len(user_ids))
                urows = uconn.execute(f"SELECT id, username FROM users WHERE id IN ({ph})", user_ids).fetchall()
                uconn.close()
                name_map = {r["id"]: r["username"] for r in urows}
                for c in comments:
                    c["username"] = name_map.get(c["user_id"], "Anonim")
            except Exception:
                for c in comments:
                    c["username"] = "Anonim"
        else:
            for c in comments:
                c["username"] = "Anonim"

        return comments
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# LIKES
# ══════════════════════════════════════════════════════════════════

def toggle_like(post_id: str, user_id: str) -> dict:
    """Toggle like on a post. Returns {"liked": bool, "likes_count": int}."""
    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM likes WHERE user_id = ? AND post_id = ?",
                (user_id, post_id)
            ).fetchone()

            if existing:
                conn.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?",
                             (user_id, post_id))
                conn.execute("UPDATE posts SET likes_count = MAX(0, likes_count - 1) WHERE id = ?",
                             (post_id,))
                liked = False
            else:
                conn.execute(
                    "INSERT INTO likes (user_id, post_id, created_at) VALUES (?, ?, ?)",
                    (user_id, post_id, _now_iso())
                )
                conn.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?",
                             (post_id,))
                liked = True

            conn.commit()
            count = conn.execute(
                "SELECT likes_count FROM posts WHERE id = ?", (post_id,)
            ).fetchone()
            likes_count = count["likes_count"] if count else 0

            return {"liked": liked, "likes_count": likes_count}
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# FOLLOWS
# ══════════════════════════════════════════════════════════════════

def follow_user(follower_id: str, target_id: str) -> bool:
    """Follow a user."""
    if follower_id == target_id:
        raise ValueError("Kendinizi takip edemezsiniz")

    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO follows (follower_user_id, following_user_id, created_at) "
                "VALUES (?, ?, ?)",
                (follower_id, target_id, _now_iso())
            )
            conn.commit()
            return True
        finally:
            conn.close()


def unfollow_user(follower_id: str, target_id: str) -> bool:
    """Unfollow a user."""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "DELETE FROM follows WHERE follower_user_id = ? AND following_user_id = ?",
                (follower_id, target_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()


def is_following_user(follower_id: str, target_id: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM follows WHERE follower_user_id = ? AND following_user_id = ?",
            (follower_id, target_id)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_followers(user_id: str) -> list:
    """Get user IDs that follow this user."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT follower_user_id FROM follows WHERE following_user_id = ?",
            (user_id,)
        ).fetchall()
        return [r["follower_user_id"] for r in rows]
    finally:
        conn.close()


def get_following(user_id: str) -> list:
    """Get user IDs that this user follows."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT following_user_id FROM follows WHERE follower_user_id = ?",
            (user_id,)
        ).fetchall()
        return [r["following_user_id"] for r in rows]
    finally:
        conn.close()


def get_followers_count(user_id: str) -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM follows WHERE following_user_id = ?",
            (user_id,)
        ).fetchone()
        return row["c"]
    finally:
        conn.close()


def get_following_count(user_id: str) -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM follows WHERE follower_user_id = ?",
            (user_id,)
        ).fetchone()
        return row["c"]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# USER PROFILE
# ══════════════════════════════════════════════════════════════════

def get_user_profile(username: str, viewer_id: str | None = None) -> Optional[dict]:
    """Get user profile with stats."""
    user_id = _get_user_id_by_username(username)
    if not user_id:
        return None

    conn = _get_conn()
    try:
        post_count = conn.execute(
            "SELECT COUNT(*) as c FROM posts WHERE user_id = ?", (user_id,)
        ).fetchone()["c"]

        total_likes = conn.execute(
            "SELECT COALESCE(SUM(likes_count), 0) as c FROM posts WHERE user_id = ?",
            (user_id,)
        ).fetchone()["c"]

        followers_count = get_followers_count(user_id)
        following_count = get_following_count(user_id)

        is_following = False
        if viewer_id and viewer_id != user_id:
            is_following = is_following_user(viewer_id, user_id)

        return {
            "user_id": user_id,
            "username": username,
            "post_count": post_count,
            "total_likes": total_likes,
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following": is_following,
            "is_own_profile": viewer_id == user_id if viewer_id else False,
        }
    finally:
        conn.close()
