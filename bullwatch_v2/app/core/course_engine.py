# -*- coding: utf-8 -*-
"""Courses / Lessons / Education Engine — FAZ 33.

SQLite-backed course & lesson system.

Public API:
  create_course(...)              → dict
  update_course(...)              → dict
  publish_course(course_id, uid)  → dict
  list_courses(...)               → list[dict]
  get_course(slug)                → dict | None
  get_course_by_id(course_id)     → dict | None
  add_lesson(...)                 → dict
  update_lesson(...)              → dict
  list_lessons(course_id)         → list[dict]
  enroll_user(course_id, uid)     → dict
  get_my_courses(uid)             → list[dict]
  progress_course(course_id, uid) → dict
  featured_courses(limit)         → list[dict]
  get_mentor_courses(mentor_uid)  → list[dict]
  course_stats()                  → dict
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import List, Optional

_logger = logging.getLogger("zkr_analiz.courses")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "courses.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()

VALID_LEVELS = {"beginner", "intermediate", "advanced"}
VALID_MARKETS = {"crypto", "stocks", "bist", "forex", "commodities"}
VALID_PRICING = {"free", "paid", "subscription"}
VALID_CONTENT_TYPES = {"video", "article", "chart_case", "mixed"}


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("courses.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS courses (
            id              TEXT PRIMARY KEY,
            mentor_user_id  TEXT NOT NULL,
            title           TEXT NOT NULL,
            slug            TEXT NOT NULL UNIQUE,
            description     TEXT,
            level           TEXT NOT NULL DEFAULT 'beginner',
            market          TEXT NOT NULL DEFAULT '',
            pricing_model   TEXT NOT NULL DEFAULT 'free',
            price           REAL NOT NULL DEFAULT 0.0,
            thumbnail_url   TEXT,
            students_count  INTEGER NOT NULL DEFAULT 0,
            rating          REAL NOT NULL DEFAULT 0.0,
            is_published    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id              TEXT PRIMARY KEY,
            course_id       TEXT NOT NULL,
            title           TEXT NOT NULL,
            content_type    TEXT NOT NULL DEFAULT 'article',
            video_url       TEXT,
            content         TEXT,
            order_index     INTEGER NOT NULL DEFAULT 0,
            duration_minutes INTEGER NOT NULL DEFAULT 0,
            is_preview      INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS course_enrollments (
            id              TEXT PRIMARY KEY,
            course_id       TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active',
            progress_pct    REAL NOT NULL DEFAULT 0.0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            UNIQUE(course_id, user_id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE INDEX IF NOT EXISTS idx_courses_mentor ON courses(mentor_user_id);
        CREATE INDEX IF NOT EXISTS idx_courses_slug ON courses(slug);
        CREATE INDEX IF NOT EXISTS idx_courses_published ON courses(is_published);
        CREATE INDEX IF NOT EXISTS idx_courses_market ON courses(market);
        CREATE INDEX IF NOT EXISTS idx_courses_level ON courses(level);
        CREATE INDEX IF NOT EXISTS idx_lessons_course ON lessons(course_id);
        CREATE INDEX IF NOT EXISTS idx_lessons_order ON lessons(course_id, order_index);
        CREATE INDEX IF NOT EXISTS idx_enroll_course ON course_enrollments(course_id);
        CREATE INDEX IF NOT EXISTS idx_enroll_user ON course_enrollments(user_id);
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


def _make_slug(title: str, existing_id: str | None = None) -> str:
    """Generate a URL-friendly slug from title."""
    slug = title.lower().strip()
    # Turkish chars
    tr_map = {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
              "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u"}
    for k, v in tr_map.items():
        slug = slug.replace(k, v)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    if not slug:
        slug = "kurs"
    # Ensure unique
    conn = _get_conn()
    try:
        base = slug
        counter = 1
        while True:
            row = conn.execute("SELECT id FROM courses WHERE slug = ?", (slug,)).fetchone()
            if not row or (existing_id and row["id"] == existing_id):
                break
            slug = f"{base}-{counter}"
            counter += 1
        return slug
    finally:
        conn.close()


def _enrich_course(course: dict) -> dict:
    """Add computed fields to a course."""
    course["mentor_username"] = _get_username(course["mentor_user_id"])
    # Get mentor display name
    course["mentor_display_name"] = course["mentor_username"]
    try:
        from app.core.mentor_engine import get_profile_by_user_id
        mp = get_profile_by_user_id(course["mentor_user_id"])
        if mp:
            course["mentor_display_name"] = mp.get("display_name", course["mentor_username"])
    except Exception:
        pass
    # Mentor reputation (FAZ 35)
    course["mentor_reputation"] = 0
    course["mentor_trust_level"] = ""
    try:
        from app.core.reputation_engine import get_reputation
        rep = get_reputation(course["mentor_user_id"])
        if rep:
            course["mentor_reputation"] = rep.get("score", 0)
            course["mentor_trust_level"] = rep.get("trust_level", "")
    except Exception:
        pass
    # Lesson count
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM lessons WHERE course_id = ?",
            (course["id"],)
        ).fetchone()
        course["lesson_count"] = row["c"] if row else 0
        # Total duration
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_minutes),0) as d FROM lessons WHERE course_id = ?",
            (course["id"],)
        ).fetchone()
        course["total_duration"] = row["d"] if row else 0
    finally:
        conn.close()
    return course


# ══════════════════════════════════════════════════════════════════
# COURSE CRUD
# ══════════════════════════════════════════════════════════════════

def create_course(
    mentor_user_id: str,
    title: str,
    description: str = "",
    level: str = "beginner",
    market: str = "",
    pricing_model: str = "free",
    price: float = 0.0,
    thumbnail_url: str = "",
) -> dict:
    """Create a new course. Only mentors should call this (checked at route level)."""
    if not title or not title.strip():
        raise ValueError("Kurs başlığı gerekli")

    if level not in VALID_LEVELS:
        raise ValueError(f"Geçersiz seviye: {level}")

    if market and market not in VALID_MARKETS:
        raise ValueError(f"Geçersiz market: {market}")

    if pricing_model not in VALID_PRICING:
        pricing_model = "free"

    slug = _make_slug(title)
    now = _now_iso()
    course_id = _gen_id()

    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT INTO courses
                    (id, mentor_user_id, title, slug, description, level, market,
                     pricing_model, price, thumbnail_url, students_count, rating,
                     is_published, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0, 0, ?, ?)
            """, (course_id, mentor_user_id, title.strip(), slug,
                  description.strip(), level, market, pricing_model,
                  price, thumbnail_url.strip(), now, now))
            conn.commit()

            row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
            result = _enrich_course(_row_to_dict(row))
            _logger.info("Course created: %s by %s", course_id, mentor_user_id)
            return result
        finally:
            conn.close()


def update_course(
    course_id: str,
    mentor_user_id: str,
    title: str | None = None,
    description: str | None = None,
    level: str | None = None,
    market: str | None = None,
    pricing_model: str | None = None,
    price: float | None = None,
    thumbnail_url: str | None = None,
) -> dict:
    """Update an existing course. Only the owner can update."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM courses WHERE id = ? AND mentor_user_id = ?",
                (course_id, mentor_user_id)
            ).fetchone()
            if not row:
                raise ValueError("Kurs bulunamadı veya yetkiniz yok")

            current = _row_to_dict(row)
            updates = {}

            if title is not None:
                t = title.strip()
                if not t:
                    raise ValueError("Kurs başlığı gerekli")
                updates["title"] = t
                updates["slug"] = _make_slug(t, existing_id=course_id)

            if description is not None:
                updates["description"] = description.strip()
            if level is not None:
                if level not in VALID_LEVELS:
                    raise ValueError(f"Geçersiz seviye: {level}")
                updates["level"] = level
            if market is not None:
                if market and market not in VALID_MARKETS:
                    raise ValueError(f"Geçersiz market: {market}")
                updates["market"] = market
            if pricing_model is not None:
                if pricing_model not in VALID_PRICING:
                    pricing_model = "free"
                updates["pricing_model"] = pricing_model
            if price is not None:
                updates["price"] = price
            if thumbnail_url is not None:
                updates["thumbnail_url"] = thumbnail_url.strip()

            if updates:
                updates["updated_at"] = _now_iso()
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                vals = list(updates.values()) + [course_id]
                conn.execute(f"UPDATE courses SET {set_clause} WHERE id = ?", vals)
                conn.commit()

            row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
            return _enrich_course(_row_to_dict(row))
        finally:
            conn.close()


def publish_course(course_id: str, mentor_user_id: str) -> dict:
    """Publish a course (make visible)."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM courses WHERE id = ? AND mentor_user_id = ?",
                (course_id, mentor_user_id)
            ).fetchone()
            if not row:
                raise ValueError("Kurs bulunamadı veya yetkiniz yok")

            # Must have at least 1 lesson
            lcount = conn.execute(
                "SELECT COUNT(*) as c FROM lessons WHERE course_id = ?", (course_id,)
            ).fetchone()["c"]
            if lcount == 0:
                raise ValueError("En az 1 ders eklenmeli")

            now = _now_iso()
            conn.execute(
                "UPDATE courses SET is_published = 1, updated_at = ? WHERE id = ?",
                (now, course_id)
            )
            conn.commit()

            row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
            return _enrich_course(_row_to_dict(row))
        finally:
            conn.close()


def get_course(slug: str, viewer_id: str | None = None) -> dict | None:
    """Get course by slug."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM courses WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return None
        course = _enrich_course(_row_to_dict(row))
        # Check enrollment
        course["is_enrolled"] = False
        if viewer_id:
            erow = conn.execute(
                "SELECT status FROM course_enrollments WHERE course_id = ? AND user_id = ? AND status != 'cancelled'",
                (course["id"], viewer_id)
            ).fetchone()
            course["is_enrolled"] = erow is not None
            if erow:
                course["enrollment_status"] = erow["status"]
        return course
    finally:
        conn.close()


def get_course_by_id(course_id: str) -> dict | None:
    """Get course by ID."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not row:
            return None
        return _enrich_course(_row_to_dict(row))
    finally:
        conn.close()


def list_courses(
    market: str | None = None,
    level: str | None = None,
    pricing: str | None = None,
    mentor_user_id: str | None = None,
    sort: str = "newest",
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
    published_only: bool = True,
) -> list:
    """List courses with filtering & sorting."""
    conn = _get_conn()
    try:
        conditions = []
        params = []

        if published_only:
            conditions.append("is_published = 1")

        if market:
            conditions.append("market = ?")
            params.append(market)

        if level:
            conditions.append("level = ?")
            params.append(level)

        if pricing:
            conditions.append("pricing_model = ?")
            params.append(pricing)

        if mentor_user_id:
            conditions.append("mentor_user_id = ?")
            params.append(mentor_user_id)

        if search:
            term = f"%{search}%"
            conditions.append("(title LIKE ? OR description LIKE ?)")
            params.extend([term, term])

        where = " AND ".join(conditions) if conditions else "1=1"

        sort_map = {
            "newest": "created_at DESC",
            "popular": "students_count DESC",
            "rating": "rating DESC",
            "title": "title ASC",
        }
        order = sort_map.get(sort, "created_at DESC")

        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM courses WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
            params
        ).fetchall()

        return [_enrich_course(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# LESSON CRUD
# ══════════════════════════════════════════════════════════════════

def add_lesson(
    course_id: str,
    mentor_user_id: str,
    title: str,
    content_type: str = "article",
    video_url: str = "",
    content: str = "",
    order_index: int | None = None,
    duration_minutes: int = 0,
    is_preview: bool = False,
) -> dict:
    """Add a lesson to a course."""
    if not title or not title.strip():
        raise ValueError("Ders başlığı gerekli")

    if content_type not in VALID_CONTENT_TYPES:
        content_type = "article"

    with _lock:
        conn = _get_conn()
        try:
            # Verify ownership
            crow = conn.execute(
                "SELECT id FROM courses WHERE id = ? AND mentor_user_id = ?",
                (course_id, mentor_user_id)
            ).fetchone()
            if not crow:
                raise ValueError("Kurs bulunamadı veya yetkiniz yok")

            # Auto order_index
            if order_index is None:
                r = conn.execute(
                    "SELECT COALESCE(MAX(order_index), -1) + 1 as next_idx FROM lessons WHERE course_id = ?",
                    (course_id,)
                ).fetchone()
                order_index = r["next_idx"]

            now = _now_iso()
            lesson_id = _gen_id()

            conn.execute("""
                INSERT INTO lessons
                    (id, course_id, title, content_type, video_url, content,
                     order_index, duration_minutes, is_preview, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (lesson_id, course_id, title.strip(), content_type,
                  video_url.strip(), content.strip(), order_index,
                  duration_minutes, 1 if is_preview else 0, now, now))
            conn.commit()

            row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            _logger.info("Lesson added: %s to course %s", lesson_id, course_id)
            return _row_to_dict(row)
        finally:
            conn.close()


def update_lesson(
    lesson_id: str,
    mentor_user_id: str,
    title: str | None = None,
    content_type: str | None = None,
    video_url: str | None = None,
    content: str | None = None,
    order_index: int | None = None,
    duration_minutes: int | None = None,
    is_preview: bool | None = None,
) -> dict:
    """Update a lesson. Only the course owner can update."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("""
                SELECT l.* FROM lessons l
                JOIN courses c ON c.id = l.course_id
                WHERE l.id = ? AND c.mentor_user_id = ?
            """, (lesson_id, mentor_user_id)).fetchone()
            if not row:
                raise ValueError("Ders bulunamadı veya yetkiniz yok")

            updates = {}
            if title is not None:
                t = title.strip()
                if not t:
                    raise ValueError("Ders başlığı gerekli")
                updates["title"] = t
            if content_type is not None:
                if content_type not in VALID_CONTENT_TYPES:
                    content_type = "article"
                updates["content_type"] = content_type
            if video_url is not None:
                updates["video_url"] = video_url.strip()
            if content is not None:
                updates["content"] = content.strip()
            if order_index is not None:
                updates["order_index"] = order_index
            if duration_minutes is not None:
                updates["duration_minutes"] = duration_minutes
            if is_preview is not None:
                updates["is_preview"] = 1 if is_preview else 0

            if updates:
                updates["updated_at"] = _now_iso()
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                vals = list(updates.values()) + [lesson_id]
                conn.execute(f"UPDATE lessons SET {set_clause} WHERE id = ?", vals)
                conn.commit()

            row = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def list_lessons(course_id: str, enrolled: bool = False) -> list:
    """List lessons for a course, ordered by order_index."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM lessons WHERE course_id = ? ORDER BY order_index ASC",
            (course_id,)
        ).fetchall()
        lessons = [_row_to_dict(r) for r in rows]
        if not enrolled:
            # Mask non-preview content for non-enrolled users
            for lesson in lessons:
                if not lesson["is_preview"]:
                    lesson["content"] = None
                    lesson["video_url"] = None
        return lessons
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# ENROLLMENT
# ══════════════════════════════════════════════════════════════════

def enroll_user(course_id: str, user_id: str) -> dict:
    """Enroll a user in a course."""
    with _lock:
        conn = _get_conn()
        try:
            # Verify course exists and is published
            crow = conn.execute(
                "SELECT * FROM courses WHERE id = ? AND is_published = 1",
                (course_id,)
            ).fetchone()
            if not crow:
                raise ValueError("Kurs bulunamadı veya yayında değil")

            # Check if already enrolled
            erow = conn.execute(
                "SELECT * FROM course_enrollments WHERE course_id = ? AND user_id = ?",
                (course_id, user_id)
            ).fetchone()

            now = _now_iso()
            if erow:
                if erow["status"] == "cancelled":
                    # Re-enroll
                    conn.execute(
                        "UPDATE course_enrollments SET status = 'active', progress_pct = 0.0, updated_at = ? WHERE id = ?",
                        (now, erow["id"])
                    )
                    conn.commit()
                    enroll_id = erow["id"]
                else:
                    # Already enrolled
                    return _row_to_dict(erow)
            else:
                enroll_id = _gen_id()
                conn.execute("""
                    INSERT INTO course_enrollments
                        (id, course_id, user_id, status, progress_pct, created_at, updated_at)
                    VALUES (?, ?, ?, 'active', 0.0, ?, ?)
                """, (enroll_id, course_id, user_id, now, now))
                conn.commit()

            # Update students_count
            sc = conn.execute(
                "SELECT COUNT(*) as c FROM course_enrollments WHERE course_id = ? AND status != 'cancelled'",
                (course_id,)
            ).fetchone()["c"]
            conn.execute(
                "UPDATE courses SET students_count = ?, updated_at = ? WHERE id = ?",
                (sc, now, course_id)
            )
            conn.commit()

            row = conn.execute("SELECT * FROM course_enrollments WHERE id = ?", (enroll_id,)).fetchone()
            _logger.info("User %s enrolled in course %s", user_id, course_id)
            return _row_to_dict(row)
        finally:
            conn.close()


def get_my_courses(user_id: str) -> list:
    """Get all courses a user is enrolled in."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT c.*, ce.status as enrollment_status, ce.progress_pct
            FROM course_enrollments ce
            JOIN courses c ON c.id = ce.course_id
            WHERE ce.user_id = ? AND ce.status != 'cancelled'
            ORDER BY ce.updated_at DESC
        """, (user_id,)).fetchall()
        return [_enrich_course(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


def progress_course(course_id: str, user_id: str, progress_pct: float = 0.0) -> dict:
    """Update progress for a user in a course."""
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM course_enrollments WHERE course_id = ? AND user_id = ? AND status = 'active'",
                (course_id, user_id)
            ).fetchone()
            if not row:
                raise ValueError("Kayıt bulunamadı")

            progress_pct = max(0.0, min(100.0, progress_pct))
            now = _now_iso()
            status = "completed" if progress_pct >= 100.0 else "active"

            conn.execute(
                "UPDATE course_enrollments SET progress_pct = ?, status = ?, updated_at = ? WHERE id = ?",
                (progress_pct, status, now, row["id"])
            )
            conn.commit()

            row = conn.execute("SELECT * FROM course_enrollments WHERE id = ?", (row["id"],)).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════
# FEATURED / MENTOR / STATS
# ══════════════════════════════════════════════════════════════════

def featured_courses(limit: int = 6) -> list:
    """Get featured/top courses."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT * FROM courses
            WHERE is_published = 1
            ORDER BY students_count DESC, rating DESC, created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [_enrich_course(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


def get_mentor_courses(mentor_user_id: str, published_only: bool = False) -> list:
    """Get all courses by a mentor."""
    conn = _get_conn()
    try:
        if published_only:
            rows = conn.execute(
                "SELECT * FROM courses WHERE mentor_user_id = ? AND is_published = 1 ORDER BY created_at DESC",
                (mentor_user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM courses WHERE mentor_user_id = ? ORDER BY created_at DESC",
                (mentor_user_id,)
            ).fetchall()
        return [_enrich_course(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


def course_stats() -> dict:
    """Get overall course statistics."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) as c FROM courses WHERE is_published = 1").fetchone()["c"]
        students = conn.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM course_enrollments WHERE status != 'cancelled'"
        ).fetchone()["c"]
        mentors = conn.execute(
            "SELECT COUNT(DISTINCT mentor_user_id) as c FROM courses WHERE is_published = 1"
        ).fetchone()["c"]
        return {"total_courses": total, "total_students": students, "total_mentors": mentors}
    finally:
        conn.close()
