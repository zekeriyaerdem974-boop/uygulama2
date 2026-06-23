# -*- coding: utf-8 -*-
"""FAZ 33 — Courses / Lessons / Education tests.

Tests course_engine core functions.
Run: python -m pytest tests/test_faz33_courses.py -v
"""
from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCourseEngine(unittest.TestCase):
    """Unit tests for course_engine.py — uses temp DB."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp()
        cls._db_path = os.path.join(cls._tmpdir, "courses.db")
        cls._users_db = os.path.join(cls._tmpdir, "users.db")
        cls._mentors_db = os.path.join(cls._tmpdir, "mentors.db")

        # Create fake users.db
        conn = sqlite3.connect(cls._users_db)
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT)")
        conn.execute("INSERT INTO users VALUES ('mentor1', 'alice')")
        conn.execute("INSERT INTO users VALUES ('mentor2', 'bob')")
        conn.execute("INSERT INTO users VALUES ('student1', 'charlie')")
        conn.execute("INSERT INTO users VALUES ('student2', 'diana')")
        conn.commit()
        conn.close()

        # Create fake mentors.db so mentor check works
        conn = sqlite3.connect(cls._mentors_db)
        conn.execute("""CREATE TABLE mentor_profiles (
            id TEXT PRIMARY KEY, user_id TEXT UNIQUE, display_name TEXT,
            headline TEXT, bio TEXT, experience_years INTEGER DEFAULT 0,
            markets TEXT DEFAULT '', specialties TEXT DEFAULT '',
            languages TEXT DEFAULT 'Türkçe', rating REAL DEFAULT 0.0,
            followers_count INTEGER DEFAULT 0, students_count INTEGER DEFAULT 0,
            pricing_model TEXT DEFAULT 'free', monthly_price REAL DEFAULT 0.0,
            is_verified INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1,
            created_at TEXT, updated_at TEXT
        )""")
        conn.execute("""INSERT INTO mentor_profiles
            (id, user_id, display_name, is_active, created_at, updated_at)
            VALUES ('m1', 'mentor1', 'Alice Mentor', 1, '2025-01-01', '2025-01-01')""")
        conn.execute("""INSERT INTO mentor_profiles
            (id, user_id, display_name, is_active, created_at, updated_at)
            VALUES ('m2', 'mentor2', 'Bob Mentor', 1, '2025-01-01', '2025-01-01')""")
        conn.commit()
        conn.close()

        import app.core.db_manager as _dm
        cls._orig_db_dir = _dm._DB_DIR
        _dm._DB_DIR = cls._tmpdir
        import app.core.course_engine as _ce
        _ce._DB_PATH = cls._db_path
        _ce._USERS_DB = cls._users_db
        _ce._init_db()
        cls.ce = _ce

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def setUp(self):
        conn = sqlite3.connect(self._db_path)
        for table in ("course_enrollments", "lessons", "courses"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()

    # ── Course CRUD ──────────────────────────────────────────

    def test_create_course(self):
        c = self.ce.create_course(
            mentor_user_id="mentor1",
            title="Kripto Trading'e Giriş",
            description="Temel kripto eğitimi",
            level="beginner",
            market="crypto",
            pricing_model="free",
        )
        self.assertTrue(c["id"])
        self.assertEqual(c["title"], "Kripto Trading'e Giriş")
        self.assertEqual(c["level"], "beginner")
        self.assertEqual(c["market"], "crypto")
        self.assertIn("kripto", c["slug"])
        self.assertEqual(c["is_published"], 0)
        self.assertEqual(c["mentor_username"], "alice")

    def test_create_course_empty_title_raises(self):
        with self.assertRaises(ValueError):
            self.ce.create_course("mentor1", "")

    def test_create_course_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            self.ce.create_course("mentor1", "Test", level="expert")

    def test_create_course_invalid_market_raises(self):
        with self.assertRaises(ValueError):
            self.ce.create_course("mentor1", "Test", market="invalid")

    def test_update_course(self):
        c = self.ce.create_course("mentor1", "Original Title")
        updated = self.ce.update_course(c["id"], "mentor1", title="New Title")
        self.assertEqual(updated["title"], "New Title")

    def test_update_course_wrong_owner(self):
        c = self.ce.create_course("mentor1", "My Course")
        with self.assertRaises(ValueError):
            self.ce.update_course(c["id"], "mentor2", title="Hijacked")

    def test_slug_unique(self):
        c1 = self.ce.create_course("mentor1", "Trading 101")
        c2 = self.ce.create_course("mentor2", "Trading 101")
        self.assertNotEqual(c1["slug"], c2["slug"])

    # ── Publish ──────────────────────────────────────────────

    def test_publish_no_lessons_raises(self):
        c = self.ce.create_course("mentor1", "Empty Course")
        with self.assertRaises(ValueError):
            self.ce.publish_course(c["id"], "mentor1")

    def test_publish_with_lesson(self):
        c = self.ce.create_course("mentor1", "Course with Lesson")
        self.ce.add_lesson(c["id"], "mentor1", "Lesson 1", content="Hello")
        published = self.ce.publish_course(c["id"], "mentor1")
        self.assertEqual(published["is_published"], 1)

    # ── Lessons ──────────────────────────────────────────────

    def test_add_lesson(self):
        c = self.ce.create_course("mentor1", "Test Course")
        lesson = self.ce.add_lesson(
            c["id"], "mentor1", "İlk Ders",
            content_type="article",
            content="Bu bir test dersidir.",
            duration_minutes=15,
            is_preview=True,
        )
        self.assertTrue(lesson["id"])
        self.assertEqual(lesson["title"], "İlk Ders")
        self.assertEqual(lesson["content_type"], "article")
        self.assertEqual(lesson["is_preview"], 1)
        self.assertEqual(lesson["order_index"], 0)

    def test_add_lesson_wrong_owner(self):
        c = self.ce.create_course("mentor1", "My Course")
        with self.assertRaises(ValueError):
            self.ce.add_lesson(c["id"], "mentor2", "Hacked Lesson")

    def test_lesson_order_auto_increment(self):
        c = self.ce.create_course("mentor1", "Ordered Course")
        l1 = self.ce.add_lesson(c["id"], "mentor1", "Lesson 1")
        l2 = self.ce.add_lesson(c["id"], "mentor1", "Lesson 2")
        l3 = self.ce.add_lesson(c["id"], "mentor1", "Lesson 3")
        self.assertEqual(l1["order_index"], 0)
        self.assertEqual(l2["order_index"], 1)
        self.assertEqual(l3["order_index"], 2)

    def test_update_lesson(self):
        c = self.ce.create_course("mentor1", "Test")
        l = self.ce.add_lesson(c["id"], "mentor1", "Old Title")
        updated = self.ce.update_lesson(l["id"], "mentor1", title="New Title")
        self.assertEqual(updated["title"], "New Title")

    def test_list_lessons_masks_content(self):
        c = self.ce.create_course("mentor1", "Test")
        self.ce.add_lesson(c["id"], "mentor1", "Preview", content="visible", is_preview=True)
        self.ce.add_lesson(c["id"], "mentor1", "Locked", content="hidden", is_preview=False)
        lessons = self.ce.list_lessons(c["id"], enrolled=False)
        self.assertEqual(lessons[0]["content"], "visible")
        self.assertIsNone(lessons[1]["content"])

    def test_list_lessons_enrolled_sees_all(self):
        c = self.ce.create_course("mentor1", "Test")
        self.ce.add_lesson(c["id"], "mentor1", "Locked", content="secret", is_preview=False)
        lessons = self.ce.list_lessons(c["id"], enrolled=True)
        self.assertEqual(lessons[0]["content"], "secret")

    # ── Enrollment ───────────────────────────────────────────

    def test_enroll(self):
        c = self.ce.create_course("mentor1", "Enrollable Course")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        enrollment = self.ce.enroll_user(c["id"], "student1")
        self.assertEqual(enrollment["status"], "active")
        self.assertEqual(enrollment["progress_pct"], 0.0)

    def test_enroll_unpublished_raises(self):
        c = self.ce.create_course("mentor1", "Draft Course")
        with self.assertRaises(ValueError):
            self.ce.enroll_user(c["id"], "student1")

    def test_enroll_updates_students_count(self):
        c = self.ce.create_course("mentor1", "Popular Course")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        self.ce.enroll_user(c["id"], "student1")
        self.ce.enroll_user(c["id"], "student2")
        course = self.ce.get_course(c["slug"])
        self.assertEqual(course["students_count"], 2)

    def test_double_enroll_no_error(self):
        c = self.ce.create_course("mentor1", "Course")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        self.ce.enroll_user(c["id"], "student1")
        e2 = self.ce.enroll_user(c["id"], "student1")
        self.assertEqual(e2["status"], "active")

    # ── My Courses ───────────────────────────────────────────

    def test_my_courses(self):
        c1 = self.ce.create_course("mentor1", "Course A")
        self.ce.add_lesson(c1["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c1["id"], "mentor1")

        c2 = self.ce.create_course("mentor2", "Course B")
        self.ce.add_lesson(c2["id"], "mentor2", "L1", content="y")
        self.ce.publish_course(c2["id"], "mentor2")

        self.ce.enroll_user(c1["id"], "student1")
        self.ce.enroll_user(c2["id"], "student1")

        my = self.ce.get_my_courses("student1")
        self.assertEqual(len(my), 2)

    # ── Progress ─────────────────────────────────────────────

    def test_progress(self):
        c = self.ce.create_course("mentor1", "Progress Course")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        self.ce.enroll_user(c["id"], "student1")

        result = self.ce.progress_course(c["id"], "student1", 50.0)
        self.assertEqual(result["progress_pct"], 50.0)
        self.assertEqual(result["status"], "active")

    def test_progress_completes(self):
        c = self.ce.create_course("mentor1", "Complete Course")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        self.ce.enroll_user(c["id"], "student1")

        result = self.ce.progress_course(c["id"], "student1", 100.0)
        self.assertEqual(result["status"], "completed")

    def test_progress_not_enrolled_raises(self):
        c = self.ce.create_course("mentor1", "No Enroll")
        with self.assertRaises(ValueError):
            self.ce.progress_course(c["id"], "student1", 50.0)

    # ── List & Filter ────────────────────────────────────────

    def test_list_courses(self):
        c1 = self.ce.create_course("mentor1", "Crypto 101", market="crypto")
        self.ce.add_lesson(c1["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c1["id"], "mentor1")

        c2 = self.ce.create_course("mentor2", "BIST 101", market="bist")
        self.ce.add_lesson(c2["id"], "mentor2", "L1", content="y")
        self.ce.publish_course(c2["id"], "mentor2")

        all_courses = self.ce.list_courses()
        self.assertEqual(len(all_courses), 2)

    def test_list_filter_market(self):
        c1 = self.ce.create_course("mentor1", "Crypto", market="crypto")
        self.ce.add_lesson(c1["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c1["id"], "mentor1")

        c2 = self.ce.create_course("mentor2", "BIST", market="bist")
        self.ce.add_lesson(c2["id"], "mentor2", "L1", content="y")
        self.ce.publish_course(c2["id"], "mentor2")

        crypto = self.ce.list_courses(market="crypto")
        self.assertEqual(len(crypto), 1)

    def test_list_filter_level(self):
        c1 = self.ce.create_course("mentor1", "Beginner", level="beginner")
        self.ce.add_lesson(c1["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c1["id"], "mentor1")

        c2 = self.ce.create_course("mentor1", "Advanced", level="advanced")
        self.ce.add_lesson(c2["id"], "mentor1", "L2", content="y")
        self.ce.publish_course(c2["id"], "mentor1")

        beginners = self.ce.list_courses(level="beginner")
        self.assertEqual(len(beginners), 1)

    def test_featured_courses(self):
        c = self.ce.create_course("mentor1", "Featured")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        featured = self.ce.featured_courses()
        self.assertEqual(len(featured), 1)

    # ── Mentor Courses ───────────────────────────────────────

    def test_get_mentor_courses(self):
        self.ce.create_course("mentor1", "Course A")
        self.ce.create_course("mentor1", "Course B")
        self.ce.create_course("mentor2", "Course C")

        mentor1_courses = self.ce.get_mentor_courses("mentor1")
        self.assertEqual(len(mentor1_courses), 2)

    # ── Get Course Detail ────────────────────────────────────

    def test_get_course_by_slug(self):
        c = self.ce.create_course("mentor1", "Slug Test", description="Test desc")
        course = self.ce.get_course(c["slug"])
        self.assertIsNotNone(course)
        self.assertEqual(course["title"], "Slug Test")

    def test_get_course_enrollment_status(self):
        c = self.ce.create_course("mentor1", "Enroll Check")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        self.ce.enroll_user(c["id"], "student1")

        course = self.ce.get_course(c["slug"], viewer_id="student1")
        self.assertTrue(course["is_enrolled"])

        course2 = self.ce.get_course(c["slug"], viewer_id="student2")
        self.assertFalse(course2["is_enrolled"])

    # ── Pricing Models ───────────────────────────────────────

    def test_paid_course(self):
        c = self.ce.create_course("mentor1", "Paid Course", pricing_model="paid", price=199.0)
        self.assertEqual(c["pricing_model"], "paid")
        self.assertEqual(c["price"], 199.0)

    def test_subscription_course(self):
        c = self.ce.create_course("mentor1", "Sub Course", pricing_model="subscription", price=49.0)
        self.assertEqual(c["pricing_model"], "subscription")

    def test_invalid_pricing_defaults_free(self):
        c = self.ce.create_course("mentor1", "Invalid Pricing", pricing_model="invalid")
        self.assertEqual(c["pricing_model"], "free")

    # ── Course Stats ─────────────────────────────────────────

    def test_course_stats(self):
        c = self.ce.create_course("mentor1", "Stats Course")
        self.ce.add_lesson(c["id"], "mentor1", "L1", content="x")
        self.ce.publish_course(c["id"], "mentor1")
        stats = self.ce.course_stats()
        self.assertEqual(stats["total_courses"], 1)

    # ── Video Lesson ─────────────────────────────────────────

    def test_video_lesson(self):
        c = self.ce.create_course("mentor1", "Video Course")
        l = self.ce.add_lesson(
            c["id"], "mentor1", "Video Ders",
            content_type="video",
            video_url="https://youtube.com/watch?v=test123",
            duration_minutes=30,
        )
        self.assertEqual(l["content_type"], "video")
        self.assertEqual(l["video_url"], "https://youtube.com/watch?v=test123")
        self.assertEqual(l["duration_minutes"], 30)


if __name__ == "__main__":
    unittest.main()
