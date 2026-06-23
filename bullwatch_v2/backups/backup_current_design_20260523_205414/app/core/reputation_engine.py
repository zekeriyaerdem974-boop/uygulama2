# -*- coding: utf-8 -*-
"""Reputation / Rating / Trust System Engine — FAZ 35.

SQLite-backed reputation, rating and badge system.

Public API:
  rate_mentor(user_id, mentor_user_id, rating, review)          → dict
  rate_course(user_id, course_id, rating, review)                → dict
  rate_strategy(user_id, strategy_id, rating, review)            → dict
  get_mentor_ratings(mentor_user_id, limit, offset)              → list
  get_course_ratings(course_id, limit, offset)                   → list
  get_strategy_ratings(strategy_id, limit, offset)               → list
  calculate_user_score(user_id)                                  → dict
  compute_trust_level(score)                                     → str
  compute_badges(user_id)                                        → list
  get_reputation(user_id)                                        → dict | None
  list_top_analysts(limit)                                       → list
  list_top_mentors(limit)                                        → list
  list_top_strategies(limit)                                     → list
  reputation_stats()                                             → dict
"""
from __future__ import annotations

import logging
import math
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.reputation")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "reputation.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")
_MENTORS_DB = os.path.join(_DB_DIR, "mentors.db")
_COURSES_DB = os.path.join(_DB_DIR, "courses.db")
_MARKETPLACE_DB = os.path.join(_DB_DIR, "marketplace.db")
_SOCIAL_DB = os.path.join(_DB_DIR, "social.db")

_lock = threading.Lock()

# ══════════════════════════════════════════════════════════════════
# TRUST LEVELS
# ══════════════════════════════════════════════════════════════════

TRUST_LEVELS = [
    (0, "Beginner Analyst"),
    (30, "Trusted Analyst"),
    (60, "Top Analyst"),
    (85, "Elite Mentor"),
]

# ══════════════════════════════════════════════════════════════════
# BADGE DEFINITIONS
# ══════════════════════════════════════════════════════════════════

BADGE_DEFS = {
    "top_crypto":       {"name": "Top Crypto Analyst",  "icon": "₿", "desc": "Kripto alanında uzman"},
    "bist_expert":      {"name": "BIST Expert",         "icon": "🏛", "desc": "BIST piyasasında uzman"},
    "strategy_master":  {"name": "Strategy Master",     "icon": "🎯", "desc": "Başarılı strateji üreticisi"},
    "top_mentor":       {"name": "Top Mentor",          "icon": "🏆", "desc": "En yüksek puanlı mentor"},
    "community_leader": {"name": "Community Leader",    "icon": "👥", "desc": "Topluluk lideri"},
}

# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("reputation.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_reputation (
            user_id         TEXT PRIMARY KEY,
            score           REAL NOT NULL DEFAULT 0.0,
            accuracy_score  REAL NOT NULL DEFAULT 0.0,
            mentor_rating   REAL NOT NULL DEFAULT 0.0,
            course_rating   REAL NOT NULL DEFAULT 0.0,
            strategy_score  REAL NOT NULL DEFAULT 0.0,
            followers_score REAL NOT NULL DEFAULT 0.0,
            social_score    REAL NOT NULL DEFAULT 0.0,
            trust_level     TEXT NOT NULL DEFAULT 'Beginner Analyst',
            badges          TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mentor_ratings (
            id              TEXT PRIMARY KEY,
            mentor_user_id  TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            rating          INTEGER NOT NULL,
            review          TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            UNIQUE(mentor_user_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS course_ratings (
            id              TEXT PRIMARY KEY,
            course_id       TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            rating          INTEGER NOT NULL,
            review          TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            UNIQUE(course_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS strategy_ratings (
            id              TEXT PRIMARY KEY,
            strategy_id     TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            rating          INTEGER NOT NULL,
            review          TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            UNIQUE(strategy_id, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_mr_mentor ON mentor_ratings(mentor_user_id);
        CREATE INDEX IF NOT EXISTS idx_mr_user   ON mentor_ratings(user_id);
        CREATE INDEX IF NOT EXISTS idx_cr_course ON course_ratings(course_id);
        CREATE INDEX IF NOT EXISTS idx_cr_user   ON course_ratings(user_id);
        CREATE INDEX IF NOT EXISTS idx_sr_strat  ON strategy_ratings(strategy_id);
        CREATE INDEX IF NOT EXISTS idx_sr_user   ON strategy_ratings(user_id);
        CREATE INDEX IF NOT EXISTS idx_ur_score  ON user_reputation(score DESC);
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


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


# ══════════════════════════════════════════════════════════════════
# RATING — MENTOR
# ══════════════════════════════════════════════════════════════════

def rate_mentor(user_id: str, mentor_user_id: str, rating: int, review: str = "") -> dict:
    """Rate a mentor (1-5). One rating per user per mentor."""
    if user_id == mentor_user_id:
        raise ValueError("Kendinizi puanlayamazsınız")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("Puan 1 ile 5 arasında olmalı")

    now = _now_iso()
    rid = _gen_id()

    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM mentor_ratings WHERE mentor_user_id = ? AND user_id = ?",
                (mentor_user_id, user_id)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE mentor_ratings SET rating = ?, review = ?, created_at = ? "
                    "WHERE mentor_user_id = ? AND user_id = ?",
                    (rating, review.strip(), now, mentor_user_id, user_id)
                )
                rid = existing["id"]
            else:
                conn.execute(
                    "INSERT INTO mentor_ratings (id, mentor_user_id, user_id, rating, review, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (rid, mentor_user_id, user_id, rating, review.strip(), now)
                )

            conn.commit()

            # Calculate average rating for mentor
            avg_row = conn.execute(
                "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM mentor_ratings WHERE mentor_user_id = ?",
                (mentor_user_id,)
            ).fetchone()
            avg_rating = round(avg_row["avg_r"] or 0, 2)
            rating_count = avg_row["cnt"]

            # Update mentor_profiles.rating in mentors.db
            _update_mentor_db_rating(mentor_user_id, avg_rating)

            result = {
                "id": rid,
                "mentor_user_id": mentor_user_id,
                "user_id": user_id,
                "rating": rating,
                "review": review.strip(),
                "created_at": now,
                "avg_rating": avg_rating,
                "rating_count": rating_count,
            }
            _logger.info("Mentor rated: %s -> %s rating=%d", user_id, mentor_user_id, rating)
            return result
        finally:
            conn.close()

    # Recalculate mentor's reputation
    _recalculate_reputation(mentor_user_id)


def _update_mentor_db_rating(mentor_user_id: str, avg_rating: float):
    """Sync rating to mentor_profiles table in mentors.db."""
    if not os.path.exists(_MENTORS_DB):
        return
    try:
        conn = sqlite3.connect(_MENTORS_DB, timeout=5)
        conn.execute(
            "UPDATE mentor_profiles SET rating = ? WHERE user_id = ?",
            (avg_rating, mentor_user_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _logger.warning("Failed to sync mentor rating: %s", e)


def get_mentor_ratings(mentor_user_id: str, limit: int = 20, offset: int = 0) -> list:
    """Get ratings for a mentor."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM mentor_ratings WHERE mentor_user_id = ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (mentor_user_id, limit, offset)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            result.append(d)
        return result
    finally:
        conn.close()


def get_mentor_avg_rating(mentor_user_id: str) -> dict:
    """Get average rating and count for a mentor."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM mentor_ratings WHERE mentor_user_id = ?",
            (mentor_user_id,)
        ).fetchone()
        return {
            "avg_rating": round(row["avg_r"] or 0, 2),
            "rating_count": row["cnt"],
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# RATING — COURSE
# ══════════════════════════════════════════════════════════════════

def rate_course(user_id: str, course_id: str, rating: int, review: str = "") -> dict:
    """Rate a course (1-5). One rating per user per course."""
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("Puan 1 ile 5 arasında olmalı")

    now = _now_iso()
    rid = _gen_id()

    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM course_ratings WHERE course_id = ? AND user_id = ?",
                (course_id, user_id)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE course_ratings SET rating = ?, review = ?, created_at = ? "
                    "WHERE course_id = ? AND user_id = ?",
                    (rating, review.strip(), now, course_id, user_id)
                )
                rid = existing["id"]
            else:
                conn.execute(
                    "INSERT INTO course_ratings (id, course_id, user_id, rating, review, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (rid, course_id, user_id, rating, review.strip(), now)
                )

            conn.commit()

            avg_row = conn.execute(
                "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM course_ratings WHERE course_id = ?",
                (course_id,)
            ).fetchone()
            avg_rating = round(avg_row["avg_r"] or 0, 2)
            rating_count = avg_row["cnt"]

            # Sync rating to courses.db
            _update_course_db_rating(course_id, avg_rating)

            result = {
                "id": rid,
                "course_id": course_id,
                "user_id": user_id,
                "rating": rating,
                "review": review.strip(),
                "created_at": now,
                "avg_rating": avg_rating,
                "rating_count": rating_count,
            }
            _logger.info("Course rated: %s -> %s rating=%d", user_id, course_id, rating)
            return result
        finally:
            conn.close()


def _update_course_db_rating(course_id: str, avg_rating: float):
    """Sync rating to courses table in courses.db."""
    if not os.path.exists(_COURSES_DB):
        return
    try:
        conn = sqlite3.connect(_COURSES_DB, timeout=5)
        conn.execute(
            "UPDATE courses SET rating = ? WHERE id = ?",
            (avg_rating, course_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _logger.warning("Failed to sync course rating: %s", e)


def get_course_ratings(course_id: str, limit: int = 20, offset: int = 0) -> list:
    """Get ratings for a course."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM course_ratings WHERE course_id = ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (course_id, limit, offset)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            result.append(d)
        return result
    finally:
        conn.close()


def get_course_avg_rating(course_id: str) -> dict:
    """Get average rating and count for a course."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM course_ratings WHERE course_id = ?",
            (course_id,)
        ).fetchone()
        return {
            "avg_rating": round(row["avg_r"] or 0, 2),
            "rating_count": row["cnt"],
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# RATING — STRATEGY
# ══════════════════════════════════════════════════════════════════

def rate_strategy(user_id: str, strategy_id: str, rating: int, review: str = "") -> dict:
    """Rate a strategy (1-5). One rating per user per strategy."""
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        raise ValueError("Puan 1 ile 5 arasında olmalı")

    now = _now_iso()
    rid = _gen_id()

    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM strategy_ratings WHERE strategy_id = ? AND user_id = ?",
                (strategy_id, user_id)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE strategy_ratings SET rating = ?, review = ?, created_at = ? "
                    "WHERE strategy_id = ? AND user_id = ?",
                    (rating, review.strip(), now, strategy_id, user_id)
                )
                rid = existing["id"]
            else:
                conn.execute(
                    "INSERT INTO strategy_ratings (id, strategy_id, user_id, rating, review, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (rid, strategy_id, user_id, rating, review.strip(), now)
                )

            conn.commit()

            avg_row = conn.execute(
                "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM strategy_ratings WHERE strategy_id = ?",
                (strategy_id,)
            ).fetchone()

            result = {
                "id": rid,
                "strategy_id": strategy_id,
                "user_id": user_id,
                "rating": rating,
                "review": review.strip(),
                "created_at": now,
                "avg_rating": round(avg_row["avg_r"] or 0, 2),
                "rating_count": avg_row["cnt"],
            }
            _logger.info("Strategy rated: %s -> %s rating=%d", user_id, strategy_id, rating)
            return result
        finally:
            conn.close()


def get_strategy_ratings(strategy_id: str, limit: int = 20, offset: int = 0) -> list:
    """Get ratings for a strategy."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM strategy_ratings WHERE strategy_id = ? "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (strategy_id, limit, offset)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            result.append(d)
        return result
    finally:
        conn.close()


def get_strategy_avg_rating(strategy_id: str) -> dict:
    """Get average rating and count for a strategy."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM strategy_ratings WHERE strategy_id = ?",
            (strategy_id,)
        ).fetchone()
        return {
            "avg_rating": round(row["avg_r"] or 0, 2),
            "rating_count": row["cnt"],
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# REPUTATION CALCULATION
# ══════════════════════════════════════════════════════════════════

def calculate_user_score(user_id: str) -> dict:
    """Calculate and persist a comprehensive reputation score for a user.

    Components (weighted to 100):
      - mentor_rating   (25%): avg mentor rating * 20  (5.0 → 100)
      - course_rating   (15%): avg course rating * 20
      - strategy_score  (20%): avg strategy rating * 20
      - followers_score (15%): log-scaled followers
      - social_score    (15%): log-scaled likes + posts
      - accuracy_score  (10%): placeholder for future signal accuracy
    """
    mentor_rating_raw = 0.0
    course_rating_raw = 0.0
    strategy_score_raw = 0.0
    followers_score_raw = 0.0
    social_score_raw = 0.0
    accuracy_score_raw = 0.0

    # --- Mentor rating ---
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT AVG(rating) as avg_r FROM mentor_ratings WHERE mentor_user_id = ?",
            (user_id,)
        ).fetchone()
        if row and row["avg_r"]:
            mentor_rating_raw = _clamp(row["avg_r"] * 20, 0, 100)  # 5.0 → 100
    finally:
        conn.close()

    # --- Course rating (for courses owned by this user) ---
    if os.path.exists(_COURSES_DB):
        try:
            cconn = sqlite3.connect(_COURSES_DB, timeout=5)
            cconn.row_factory = sqlite3.Row
            course_ids = [r["id"] for r in cconn.execute(
                "SELECT id FROM courses WHERE mentor_user_id = ?", (user_id,)
            ).fetchall()]
            cconn.close()

            if course_ids:
                conn = _get_conn()
                try:
                    ph = ",".join("?" * len(course_ids))
                    row = conn.execute(
                        f"SELECT AVG(rating) as avg_r FROM course_ratings WHERE course_id IN ({ph})",
                        course_ids
                    ).fetchone()
                    if row and row["avg_r"]:
                        course_rating_raw = _clamp(row["avg_r"] * 20, 0, 100)
                finally:
                    conn.close()
        except Exception:
            pass

    # --- Strategy rating (for strategies owned by this user) ---
    if os.path.exists(_MARKETPLACE_DB):
        try:
            mconn = sqlite3.connect(_MARKETPLACE_DB, timeout=5)
            mconn.row_factory = sqlite3.Row
            strat_ids = [r["id"] for r in mconn.execute(
                "SELECT id FROM published_strategies WHERE user_id = ?", (user_id,)
            ).fetchall()]
            mconn.close()

            if strat_ids:
                conn = _get_conn()
                try:
                    ph = ",".join("?" * len(strat_ids))
                    row = conn.execute(
                        f"SELECT AVG(rating) as avg_r FROM strategy_ratings WHERE strategy_id IN ({ph})",
                        strat_ids
                    ).fetchone()
                    if row and row["avg_r"]:
                        strategy_score_raw = _clamp(row["avg_r"] * 20, 0, 100)
                finally:
                    conn.close()
        except Exception:
            pass

    # --- Followers score (log-scaled) ---
    if os.path.exists(_MENTORS_DB):
        try:
            mconn = sqlite3.connect(_MENTORS_DB, timeout=5)
            mconn.row_factory = sqlite3.Row
            row = mconn.execute(
                "SELECT followers_count FROM mentor_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if row and row["followers_count"]:
                # log scaling: 10 followers → ~50, 100 → ~80, 1000 → ~100
                followers_score_raw = _clamp(math.log10(max(row["followers_count"], 1) + 1) * 33, 0, 100)
            mconn.close()
        except Exception:
            pass

    # --- Social score (posts + likes, log-scaled) ---
    if os.path.exists(_SOCIAL_DB):
        try:
            sconn = sqlite3.connect(_SOCIAL_DB, timeout=5)
            sconn.row_factory = sqlite3.Row
            row = sconn.execute(
                "SELECT COUNT(*) as c, COALESCE(SUM(likes_count),0) as l "
                "FROM posts WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            posts_count = row["c"] or 0
            likes_count = row["l"] or 0
            activity = posts_count + likes_count
            if activity > 0:
                social_score_raw = _clamp(math.log10(activity + 1) * 30, 0, 100)
            sconn.close()
        except Exception:
            pass

    # --- Weighted score ---
    score = (
        mentor_rating_raw * 0.25 +
        course_rating_raw * 0.15 +
        strategy_score_raw * 0.20 +
        followers_score_raw * 0.15 +
        social_score_raw * 0.15 +
        accuracy_score_raw * 0.10
    )
    score = round(_clamp(score, 0, 100), 1)

    trust_level = compute_trust_level(score)
    badges = compute_badges(user_id)
    badges_str = ",".join(badges)

    now = _now_iso()

    with _lock:
        conn = _get_conn()
        try:
            existing = conn.execute(
                "SELECT 1 FROM user_reputation WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if existing:
                conn.execute("""
                    UPDATE user_reputation SET
                        score = ?, accuracy_score = ?, mentor_rating = ?,
                        course_rating = ?, strategy_score = ?,
                        followers_score = ?, social_score = ?,
                        trust_level = ?, badges = ?, updated_at = ?
                    WHERE user_id = ?
                """, (score, accuracy_score_raw, mentor_rating_raw,
                      course_rating_raw, strategy_score_raw,
                      followers_score_raw, social_score_raw,
                      trust_level, badges_str, now, user_id))
            else:
                conn.execute("""
                    INSERT INTO user_reputation
                        (user_id, score, accuracy_score, mentor_rating,
                         course_rating, strategy_score, followers_score,
                         social_score, trust_level, badges, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, score, accuracy_score_raw, mentor_rating_raw,
                      course_rating_raw, strategy_score_raw,
                      followers_score_raw, social_score_raw,
                      trust_level, badges_str, now, now))

            conn.commit()
        finally:
            conn.close()

    return {
        "user_id": user_id,
        "username": _get_username(user_id),
        "score": score,
        "accuracy_score": accuracy_score_raw,
        "mentor_rating": mentor_rating_raw,
        "course_rating": course_rating_raw,
        "strategy_score": strategy_score_raw,
        "followers_score": followers_score_raw,
        "social_score": social_score_raw,
        "trust_level": trust_level,
        "badges": badges,
    }


def _recalculate_reputation(user_id: str):
    """Recalculate reputation asynchronously (best-effort)."""
    try:
        calculate_user_score(user_id)
    except Exception as e:
        _logger.warning("Reputation recalc failed for %s: %s", user_id, e)


# ══════════════════════════════════════════════════════════════════
# TRUST LEVEL
# ══════════════════════════════════════════════════════════════════

def compute_trust_level(score: float) -> str:
    """Map a score (0-100) to a trust level."""
    level = TRUST_LEVELS[0][1]
    for threshold, name in TRUST_LEVELS:
        if score >= threshold:
            level = name
    return level


# ══════════════════════════════════════════════════════════════════
# BADGES
# ══════════════════════════════════════════════════════════════════

def compute_badges(user_id: str) -> list:
    """Determine which badges a user qualifies for."""
    badges = []

    # --- Top Crypto Analyst ---
    if os.path.exists(_MENTORS_DB):
        try:
            mconn = sqlite3.connect(_MENTORS_DB, timeout=5)
            mconn.row_factory = sqlite3.Row
            row = mconn.execute(
                "SELECT markets FROM mentor_profiles WHERE user_id = ? AND is_active = 1",
                (user_id,)
            ).fetchone()
            if row and "crypto" in (row["markets"] or ""):
                badges.append("top_crypto")
            if row and "bist" in (row["markets"] or ""):
                badges.append("bist_expert")
            mconn.close()
        except Exception:
            pass

    # --- Strategy Master (has published strategies with rating >= 4) ---
    conn = _get_conn()
    try:
        strat_row = conn.execute(
            "SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM strategy_ratings "
            "WHERE strategy_id IN (SELECT id FROM strategy_ratings WHERE user_id = ?)",
            (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if os.path.exists(_MARKETPLACE_DB):
        try:
            mconn = sqlite3.connect(_MARKETPLACE_DB, timeout=5)
            mconn.row_factory = sqlite3.Row
            row = mconn.execute(
                "SELECT COUNT(*) as c FROM published_strategies WHERE user_id = ? AND is_active = 1",
                (user_id,)
            ).fetchone()
            if row and row["c"] >= 1:
                badges.append("strategy_master")
            mconn.close()
        except Exception:
            pass

    # --- Top Mentor (rating >= 4.0) ---
    if os.path.exists(_MENTORS_DB):
        try:
            mconn = sqlite3.connect(_MENTORS_DB, timeout=5)
            mconn.row_factory = sqlite3.Row
            row = mconn.execute(
                "SELECT rating FROM mentor_profiles WHERE user_id = ? AND is_active = 1",
                (user_id,)
            ).fetchone()
            if row and (row["rating"] or 0) >= 4.0:
                badges.append("top_mentor")
            mconn.close()
        except Exception:
            pass

    # --- Community Leader (followers >= 5 or social posts >= 5) ---
    has_followers = False
    if os.path.exists(_MENTORS_DB):
        try:
            mconn = sqlite3.connect(_MENTORS_DB, timeout=5)
            mconn.row_factory = sqlite3.Row
            row = mconn.execute(
                "SELECT followers_count FROM mentor_profiles WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if row and (row["followers_count"] or 0) >= 5:
                has_followers = True
            mconn.close()
        except Exception:
            pass

    has_posts = False
    if os.path.exists(_SOCIAL_DB):
        try:
            sconn = sqlite3.connect(_SOCIAL_DB, timeout=5)
            sconn.row_factory = sqlite3.Row
            row = sconn.execute(
                "SELECT COUNT(*) as c FROM posts WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row and row["c"] >= 5:
                has_posts = True
            sconn.close()
        except Exception:
            pass

    if has_followers or has_posts:
        badges.append("community_leader")

    return badges


# ══════════════════════════════════════════════════════════════════
# REPUTATION QUERIES
# ══════════════════════════════════════════════════════════════════

def get_reputation(user_id: str) -> Optional[dict]:
    """Get stored reputation for a user."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM user_reputation WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        d["username"] = _get_username(user_id)
        d["badges"] = [b for b in d.get("badges", "").split(",") if b]
        return d
    finally:
        conn.close()


def list_top_analysts(limit: int = 10) -> list:
    """Get top analysts by reputation score."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM user_reputation ORDER BY score DESC LIMIT ?",
            (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            d["badges"] = [b for b in d.get("badges", "").split(",") if b]
            result.append(d)
        return result
    finally:
        conn.close()


def list_top_mentors(limit: int = 10) -> list:
    """Get top mentors by mentor rating component."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM user_reputation WHERE mentor_rating > 0 "
            "ORDER BY mentor_rating DESC LIMIT ?",
            (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            d["badges"] = [b for b in d.get("badges", "").split(",") if b]
            result.append(d)
        return result
    finally:
        conn.close()


def list_top_strategies(limit: int = 10) -> list:
    """Get users with top strategy scores."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM user_reputation WHERE strategy_score > 0 "
            "ORDER BY strategy_score DESC LIMIT ?",
            (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["username"] = _get_username(d["user_id"])
            d["badges"] = [b for b in d.get("badges", "").split(",") if b]
            result.append(d)
        return result
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════════════

def reputation_stats() -> dict:
    """Overall reputation system statistics."""
    conn = _get_conn()
    try:
        ur = conn.execute("SELECT COUNT(*) as c FROM user_reputation").fetchone()["c"]
        mr = conn.execute("SELECT COUNT(*) as c FROM mentor_ratings").fetchone()["c"]
        cr = conn.execute("SELECT COUNT(*) as c FROM course_ratings").fetchone()["c"]
        sr = conn.execute("SELECT COUNT(*) as c FROM strategy_ratings").fetchone()["c"]

        avg_row = conn.execute(
            "SELECT AVG(score) as avg_s FROM user_reputation"
        ).fetchone()

        return {
            "total_users_rated": ur,
            "mentor_ratings_count": mr,
            "course_ratings_count": cr,
            "strategy_ratings_count": sr,
            "avg_reputation_score": round(avg_row["avg_s"] or 0, 1),
        }
    finally:
        conn.close()
