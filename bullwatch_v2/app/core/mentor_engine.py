# -*- coding: utf-8 -*-
"""Mentor / Analyst Profiles Engine — FAZ 32.

SQLite-backed mentor profile system.

Public API:
  create_or_update_profile(...)   → dict
  get_profile(username)           → dict | None
  get_profile_by_user_id(uid)     → dict | None
  list_mentors(...)               → list[dict]
  follow_mentor(uid, mentor_uid)  → bool
  unfollow_mentor(uid, mentor_uid)→ bool
  mentor_stats(mentor_uid)        → dict
  featured_mentors(limit)         → list[dict]
  is_mentor(user_id)              → bool
  get_mentor_ids(user_ids)        → set[str]
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

_logger = logging.getLogger("zkr_analiz.mentor")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "mentors.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()

VALID_MARKETS = {"crypto", "stocks", "bist", "forex", "commodities"}
VALID_PRICING = {"free", "paid", "subscription"}


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("mentors.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mentor_profiles (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL UNIQUE,
            display_name    TEXT NOT NULL,
            headline        TEXT,
            bio             TEXT,
            experience_years INTEGER NOT NULL DEFAULT 0,
            markets         TEXT NOT NULL DEFAULT '',
            specialties     TEXT NOT NULL DEFAULT '',
            languages       TEXT NOT NULL DEFAULT 'Türkçe',
            rating          REAL NOT NULL DEFAULT 0.0,
            followers_count INTEGER NOT NULL DEFAULT 0,
            students_count  INTEGER NOT NULL DEFAULT 0,
            pricing_model   TEXT NOT NULL DEFAULT 'free',
            monthly_price   REAL NOT NULL DEFAULT 0.0,
            is_verified     INTEGER NOT NULL DEFAULT 0,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mentor_follows (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            mentor_user_id  TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            UNIQUE(user_id, mentor_user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_mp_user ON mentor_profiles(user_id);
        CREATE INDEX IF NOT EXISTS idx_mp_active ON mentor_profiles(is_active);
        CREATE INDEX IF NOT EXISTS idx_mp_rating ON mentor_profiles(rating DESC);
        CREATE INDEX IF NOT EXISTS idx_mp_followers ON mentor_profiles(followers_count DESC);
        CREATE INDEX IF NOT EXISTS idx_mf_user ON mentor_follows(user_id);
        CREATE INDEX IF NOT EXISTS idx_mf_mentor ON mentor_follows(mentor_user_id);
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


def _parse_list(val: str) -> list:
    """Parse comma-separated string to list."""
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]


def _enrich_profile(profile: dict, viewer_id: str | None = None) -> dict:
    """Add computed fields to a mentor profile."""
    profile["username"] = _get_username(profile["user_id"])
    profile["markets_list"] = _parse_list(profile.get("markets", ""))
    profile["specialties_list"] = _parse_list(profile.get("specialties", ""))
    profile["languages_list"] = _parse_list(profile.get("languages", ""))
    profile["is_following"] = False

    if viewer_id and viewer_id != profile["user_id"]:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM mentor_follows WHERE user_id = ? AND mentor_user_id = ?",
                (viewer_id, profile["user_id"])
            ).fetchone()
            profile["is_following"] = row is not None
        finally:
            conn.close()

    return profile


# ══════════════════════════════════════════════════════════════════
# PROFILE CRUD
# ══════════════════════════════════════════════════════════════════

def create_or_update_profile(
    user_id: str,
    display_name: str,
    headline: str = "",
    bio: str = "",
    experience_years: int = 0,
    markets: str = "",
    specialties: str = "",
    languages: str = "Türkçe",
    pricing_model: str = "free",
    monthly_price: float = 0.0,
) -> dict:
    """Create or update a mentor profile."""
    if not display_name or not display_name.strip():
        raise ValueError("Görünen ad gerekli")

    if pricing_model not in VALID_PRICING:
        pricing_model = "free"

    # Validate markets
    market_items = [m.strip() for m in markets.split(",") if m.strip()]
    for m in market_items:
        if m not in VALID_MARKETS:
            raise ValueError(f"Geçersiz market: {m}")
    markets_clean = ",".join(market_items)

    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM mentor_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE mentor_profiles SET
                        display_name = ?, headline = ?, bio = ?,
                        experience_years = ?, markets = ?, specialties = ?,
                        languages = ?, pricing_model = ?, monthly_price = ?,
                        updated_at = ?
                    WHERE user_id = ?
                """, (display_name.strip(), headline.strip(), bio.strip(),
                      experience_years, markets_clean, specialties.strip(),
                      languages.strip(), pricing_model, monthly_price,
                      now, user_id))
                profile_id = existing["id"]
            else:
                profile_id = _gen_id()
                conn.execute("""
                    INSERT INTO mentor_profiles
                        (id, user_id, display_name, headline, bio,
                         experience_years, markets, specialties, languages,
                         rating, followers_count, students_count,
                         pricing_model, monthly_price, is_verified, is_active,
                         created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0, 0, ?, ?, 0, 1, ?, ?)
                """, (profile_id, user_id, display_name.strip(), headline.strip(),
                      bio.strip(), experience_years, markets_clean,
                      specialties.strip(), languages.strip(),
                      pricing_model, monthly_price, now, now))

            conn.commit()

            row = conn.execute(
                "SELECT * FROM mentor_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            result = _row_to_dict(row)
            result = _enrich_profile(result)
            _logger.info("Mentor profile saved: %s for user %s", profile_id, user_id)
            return result
        finally:
            conn.close()


def get_profile(username: str, viewer_id: str | None = None) -> Optional[dict]:
    """Get mentor profile by username."""
    user_id = _get_user_id_by_username(username)
    if not user_id:
        return None
    return get_profile_by_user_id(user_id, viewer_id)


def get_profile_by_user_id(user_id: str, viewer_id: str | None = None) -> Optional[dict]:
    """Get mentor profile by user_id."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM mentor_profiles WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return _enrich_profile(_row_to_dict(row), viewer_id)
    finally:
        conn.close()


def list_mentors(
    market: str | None = None,
    sort: str = "followers",
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
    viewer_id: str | None = None,
) -> list:
    """List active mentor profiles."""
    conn = _get_conn()
    try:
        conditions = ["is_active = 1"]
        params: list = []

        if market and market in VALID_MARKETS:
            conditions.append("markets LIKE ?")
            params.append(f"%{market}%")

        if search:
            conditions.append("(display_name LIKE ? OR headline LIKE ? OR specialties LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term, term])

        where = " AND ".join(conditions)

        sort_map = {
            "followers": "followers_count DESC",
            "rating": "rating DESC",
            "newest": "created_at DESC",
            "experience": "experience_years DESC",
        }
        order = sort_map.get(sort, "followers_count DESC")

        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM mentor_profiles WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
            params
        ).fetchall()

        results = []
        for r in rows:
            profile = _enrich_profile(_row_to_dict(r), viewer_id)
            results.append(profile)
        return results
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# FOLLOW / UNFOLLOW
# ══════════════════════════════════════════════════════════════════

def follow_mentor(user_id: str, mentor_user_id: str) -> bool:
    """Follow a mentor."""
    if user_id == mentor_user_id:
        raise ValueError("Kendinizi takip edemezsiniz")

    with _lock:
        conn = _get_conn()
        try:
            # Verify mentor exists
            mentor = conn.execute(
                "SELECT id FROM mentor_profiles WHERE user_id = ? AND is_active = 1",
                (mentor_user_id,)
            ).fetchone()
            if not mentor:
                raise ValueError("Mentor bulunamadı")

            conn.execute(
                "INSERT OR IGNORE INTO mentor_follows (user_id, mentor_user_id, created_at) "
                "VALUES (?, ?, ?)",
                (user_id, mentor_user_id, _now_iso())
            )
            # Update followers_count
            count = conn.execute(
                "SELECT COUNT(*) as c FROM mentor_follows WHERE mentor_user_id = ?",
                (mentor_user_id,)
            ).fetchone()["c"]
            conn.execute(
                "UPDATE mentor_profiles SET followers_count = ? WHERE user_id = ?",
                (count, mentor_user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()


def unfollow_mentor(user_id: str, mentor_user_id: str) -> bool:
    """Unfollow a mentor."""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "DELETE FROM mentor_follows WHERE user_id = ? AND mentor_user_id = ?",
                (user_id, mentor_user_id)
            )
            # Update followers_count
            count = conn.execute(
                "SELECT COUNT(*) as c FROM mentor_follows WHERE mentor_user_id = ?",
                (mentor_user_id,)
            ).fetchone()["c"]
            conn.execute(
                "UPDATE mentor_profiles SET followers_count = ? WHERE user_id = ?",
                (count, mentor_user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# STATS & FEATURED
# ══════════════════════════════════════════════════════════════════

def mentor_stats(mentor_user_id: str) -> dict:
    """Get mentor statistics."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM mentor_profiles WHERE user_id = ? AND is_active = 1",
            (mentor_user_id,)
        ).fetchone()
        if not row:
            return {}

        profile = _row_to_dict(row)

        # Count posts from social.db
        social_db = os.path.join(_DB_DIR, "social.db")
        post_count = 0
        total_likes = 0
        if os.path.exists(social_db):
            try:
                sconn = sqlite3.connect(social_db, timeout=5)
                sconn.row_factory = sqlite3.Row
                r = sconn.execute(
                    "SELECT COUNT(*) as c, COALESCE(SUM(likes_count),0) as l "
                    "FROM posts WHERE user_id = ?",
                    (mentor_user_id,)
                ).fetchone()
                post_count = r["c"]
                total_likes = r["l"]
                sconn.close()
            except Exception:
                pass

        # Count strategies from marketplace.db
        mp_db = os.path.join(_DB_DIR, "marketplace.db")
        strategy_count = 0
        if os.path.exists(mp_db):
            try:
                mconn = sqlite3.connect(mp_db, timeout=5)
                mconn.row_factory = sqlite3.Row
                r = mconn.execute(
                    "SELECT COUNT(*) as c FROM published_strategies "
                    "WHERE user_id = ? AND is_active = 1",
                    (mentor_user_id,)
                ).fetchone()
                strategy_count = r["c"]
                mconn.close()
            except Exception:
                pass

        return {
            "followers_count": profile["followers_count"],
            "students_count": profile["students_count"],
            "post_count": post_count,
            "total_likes": total_likes,
            "strategy_count": strategy_count,
            "rating": profile["rating"],
            "experience_years": profile["experience_years"],
        }
    finally:
        conn.close()


def featured_mentors(limit: int = 6) -> list:
    """Get featured/top mentors."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM mentor_profiles
            WHERE is_active = 1
            ORDER BY is_verified DESC, followers_count DESC, rating DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [_enrich_profile(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# MENTOR DETECTION (for social feed badge)
# ══════════════════════════════════════════════════════════════════

def is_mentor(user_id: str) -> bool:
    """Check if a user has an active mentor profile."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM mentor_profiles WHERE user_id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_mentor_ids(user_ids: list) -> Set[str]:
    """Given a list of user_ids, return the set that are active mentors."""
    if not user_ids:
        return set()
    conn = _get_conn()
    try:
        ph = ",".join("?" * len(user_ids))
        rows = conn.execute(
            f"SELECT user_id FROM mentor_profiles WHERE user_id IN ({ph}) AND is_active = 1",
            user_ids
        ).fetchall()
        return {r["user_id"] for r in rows}
    finally:
        conn.close()
