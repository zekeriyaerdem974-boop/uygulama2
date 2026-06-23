# -*- coding: utf-8 -*-
"""FAZ 35 — Reputation / Rating / Trust System Tests.

36 tests covering:
  - mentor rating CRUD & validation
  - course rating CRUD & validation
  - strategy rating CRUD & validation
  - reputation calculation & scoring
  - trust level computation
  - badge assignment
  - top analysts / mentors / strategies
  - reputation stats
  - discover integration
"""
import os
import sys
import sqlite3
import uuid
import unittest

# Ensure project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Isolate test DB
_TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".test_data_faz35")
os.makedirs(_TEST_DIR, exist_ok=True)

# Patch data dirs in engines BEFORE importing them
import app.core.db_manager as _dm
_dm._DB_DIR = _TEST_DIR
import app.core.reputation_engine as re_eng
re_eng._DB_DIR = _TEST_DIR
re_eng._DB_PATH = os.path.join(_TEST_DIR, "reputation.db")
re_eng._USERS_DB = os.path.join(_TEST_DIR, "users.db")
re_eng._MENTORS_DB = os.path.join(_TEST_DIR, "mentors.db")
re_eng._COURSES_DB = os.path.join(_TEST_DIR, "courses.db")
re_eng._MARKETPLACE_DB = os.path.join(_TEST_DIR, "marketplace.db")
re_eng._SOCIAL_DB = os.path.join(_TEST_DIR, "social.db")


def _uid():
    return str(uuid.uuid4())[:12]


def _setup_users_db(*users):
    """Create a minimal users.db with given (id, username) tuples."""
    db = os.path.join(_TEST_DIR, "users.db")
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT)")
    for uid, uname in users:
        conn.execute("INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)", (uid, uname))
    conn.commit()
    conn.close()


def _setup_mentors_db(user_id, display_name, markets="crypto", rating=0.0, followers_count=0):
    """Create a minimal mentor_profiles entry."""
    db = os.path.join(_TEST_DIR, "mentors.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentor_profiles (
            id TEXT PRIMARY KEY, user_id TEXT UNIQUE, display_name TEXT,
            markets TEXT DEFAULT '', rating REAL DEFAULT 0.0,
            followers_count INTEGER DEFAULT 0, students_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, is_verified INTEGER DEFAULT 0,
            headline TEXT DEFAULT '', bio TEXT DEFAULT '',
            experience_years INTEGER DEFAULT 0, specialties TEXT DEFAULT '',
            languages TEXT DEFAULT '', pricing_model TEXT DEFAULT 'free',
            monthly_price REAL DEFAULT 0.0, created_at TEXT, updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentor_follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, mentor_user_id TEXT,
            created_at TEXT, UNIQUE(user_id, mentor_user_id)
        )
    """)
    conn.execute("INSERT OR REPLACE INTO mentor_profiles (id, user_id, display_name, markets, rating, followers_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                 (_uid(), user_id, display_name, markets, rating, followers_count))
    conn.commit()
    conn.close()


def _setup_courses_db(course_id, mentor_user_id, title="Test Course"):
    """Create a minimal courses entry."""
    db = os.path.join(_TEST_DIR, "courses.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY, mentor_user_id TEXT, title TEXT,
            slug TEXT, description TEXT DEFAULT '', level TEXT DEFAULT 'beginner',
            market TEXT DEFAULT 'crypto', pricing_model TEXT DEFAULT 'free',
            price REAL DEFAULT 0, students_count INTEGER DEFAULT 0,
            rating REAL DEFAULT 0, is_published INTEGER DEFAULT 1,
            created_at TEXT, updated_at TEXT
        )
    """)
    conn.execute("INSERT OR REPLACE INTO courses (id, mentor_user_id, title, slug, created_at, updated_at) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                 (course_id, mentor_user_id, title, title.lower().replace(" ", "-")))
    conn.commit()
    conn.close()


def _setup_marketplace_db(strategy_id, user_id, title="Test Strategy"):
    """Create a minimal published_strategies entry."""
    db = os.path.join(_TEST_DIR, "marketplace.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS published_strategies (
            id TEXT PRIMARY KEY, user_id TEXT, title TEXT,
            slug TEXT, description TEXT DEFAULT '', strategy_code TEXT DEFAULT '',
            market TEXT DEFAULT 'crypto', default_symbol TEXT DEFAULT '',
            tags TEXT DEFAULT '', risk_level TEXT DEFAULT 'medium',
            is_active INTEGER DEFAULT 1, created_at TEXT, updated_at TEXT
        )
    """)
    conn.execute("INSERT OR REPLACE INTO published_strategies (id, user_id, title, slug, created_at, updated_at) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                 (strategy_id, user_id, title, title.lower().replace(" ", "-")))
    conn.commit()
    conn.close()


def _setup_social_db(user_id, post_count=3, likes_per_post=2):
    """Create minimal posts."""
    db = os.path.join(_TEST_DIR, "social.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY, user_id TEXT, content TEXT,
            symbol TEXT, market TEXT, timeframe TEXT,
            chart_snapshot TEXT, created_at TEXT,
            likes_count INTEGER DEFAULT 0, comments_count INTEGER DEFAULT 0
        )
    """)
    for i in range(post_count):
        conn.execute("INSERT INTO posts (id, user_id, content, created_at, likes_count) VALUES (?, ?, ?, datetime('now'), ?)",
                     (_uid(), user_id, f"Post {i}", likes_per_post))
    conn.commit()
    conn.close()


class TestReputationEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Clean up test DBs
        for f in os.listdir(_TEST_DIR):
            os.remove(os.path.join(_TEST_DIR, f))

        # Re-initialize reputation DB
        conn = re_eng._get_conn()
        re_eng._ensure_tables(conn)
        conn.close()

        # Setup test users
        cls.mentor_uid = _uid()
        cls.user1_uid = _uid()
        cls.user2_uid = _uid()
        cls.user3_uid = _uid()
        cls.course_id = _uid()
        cls.strategy_id = _uid()

        _setup_users_db(
            (cls.mentor_uid, "test_mentor"),
            (cls.user1_uid, "test_user1"),
            (cls.user2_uid, "test_user2"),
            (cls.user3_uid, "test_user3"),
        )

        _setup_mentors_db(cls.mentor_uid, "Test Mentor", markets="crypto,bist", followers_count=12)
        _setup_courses_db(cls.course_id, cls.mentor_uid, "Kripto 101")
        _setup_marketplace_db(cls.strategy_id, cls.mentor_uid, "EMA Cross")
        _setup_social_db(cls.mentor_uid, post_count=6, likes_per_post=3)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(_TEST_DIR, ignore_errors=True)

    # ── MENTOR RATING ──────────────────────────────────────────

    def test_01_rate_mentor(self):
        result = re_eng.rate_mentor(self.user1_uid, self.mentor_uid, 5, "Harika mentor!")
        self.assertEqual(result["rating"], 5)
        self.assertEqual(result["avg_rating"], 5.0)
        self.assertEqual(result["rating_count"], 1)

    def test_02_rate_mentor_update(self):
        result = re_eng.rate_mentor(self.user1_uid, self.mentor_uid, 4, "İyi ama eksikler var")
        self.assertEqual(result["rating"], 4)
        self.assertEqual(result["avg_rating"], 4.0)

    def test_03_rate_mentor_second_user(self):
        result = re_eng.rate_mentor(self.user2_uid, self.mentor_uid, 5, "Mükemmel!")
        self.assertEqual(result["avg_rating"], 4.5)
        self.assertEqual(result["rating_count"], 2)

    def test_04_rate_mentor_self_raises(self):
        with self.assertRaises(ValueError):
            re_eng.rate_mentor(self.mentor_uid, self.mentor_uid, 5)

    def test_05_rate_mentor_invalid_rating(self):
        with self.assertRaises(ValueError):
            re_eng.rate_mentor(self.user1_uid, self.mentor_uid, 6)

    def test_06_rate_mentor_zero_invalid(self):
        with self.assertRaises(ValueError):
            re_eng.rate_mentor(self.user1_uid, self.mentor_uid, 0)

    def test_07_get_mentor_ratings(self):
        ratings = re_eng.get_mentor_ratings(self.mentor_uid)
        self.assertEqual(len(ratings), 2)
        self.assertTrue(all(r.get("username") for r in ratings))

    def test_08_get_mentor_avg_rating(self):
        avg = re_eng.get_mentor_avg_rating(self.mentor_uid)
        self.assertEqual(avg["avg_rating"], 4.5)
        self.assertEqual(avg["rating_count"], 2)

    # ── COURSE RATING ──────────────────────────────────────────

    def test_09_rate_course(self):
        result = re_eng.rate_course(self.user1_uid, self.course_id, 5, "Çok faydalı!")
        self.assertEqual(result["rating"], 5)
        self.assertEqual(result["avg_rating"], 5.0)

    def test_10_rate_course_second_user(self):
        result = re_eng.rate_course(self.user2_uid, self.course_id, 4)
        self.assertEqual(result["avg_rating"], 4.5)
        self.assertEqual(result["rating_count"], 2)

    def test_11_rate_course_invalid(self):
        with self.assertRaises(ValueError):
            re_eng.rate_course(self.user1_uid, self.course_id, 10)

    def test_12_get_course_ratings(self):
        ratings = re_eng.get_course_ratings(self.course_id)
        self.assertEqual(len(ratings), 2)

    def test_13_get_course_avg_rating(self):
        avg = re_eng.get_course_avg_rating(self.course_id)
        self.assertEqual(avg["avg_rating"], 4.5)

    # ── STRATEGY RATING ────────────────────────────────────────

    def test_14_rate_strategy(self):
        result = re_eng.rate_strategy(self.user1_uid, self.strategy_id, 5, "Çalışıyor!")
        self.assertEqual(result["rating"], 5)
        self.assertEqual(result["avg_rating"], 5.0)

    def test_15_rate_strategy_second_user(self):
        result = re_eng.rate_strategy(self.user2_uid, self.strategy_id, 3)
        self.assertEqual(result["avg_rating"], 4.0)

    def test_16_rate_strategy_invalid(self):
        with self.assertRaises(ValueError):
            re_eng.rate_strategy(self.user1_uid, self.strategy_id, -1)

    def test_17_get_strategy_ratings(self):
        ratings = re_eng.get_strategy_ratings(self.strategy_id)
        self.assertEqual(len(ratings), 2)

    def test_18_get_strategy_avg_rating(self):
        avg = re_eng.get_strategy_avg_rating(self.strategy_id)
        self.assertEqual(avg["avg_rating"], 4.0)

    # ── REPUTATION CALCULATION ─────────────────────────────────

    def test_19_calculate_user_score(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        self.assertIn("score", result)
        self.assertIn("trust_level", result)
        self.assertIn("badges", result)
        self.assertGreater(result["score"], 0)

    def test_20_mentor_rating_component(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        # Mentor avg rating is 4.5, * 20 = 90
        self.assertEqual(result["mentor_rating"], 90.0)

    def test_21_course_rating_component(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        # Course avg rating is 4.5, * 20 = 90
        self.assertEqual(result["course_rating"], 90.0)

    def test_22_strategy_score_component(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        # Strategy avg rating is 4.0, * 20 = 80
        self.assertEqual(result["strategy_score"], 80.0)

    def test_23_followers_score_component(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        # 12 followers, log10(13) * 33 ≈ 36.8
        self.assertGreater(result["followers_score"], 30)

    def test_24_social_score_component(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        # 6 posts + 18 likes = 24, log10(25) * 30 ≈ 41.9
        self.assertGreater(result["social_score"], 30)

    def test_25_score_range(self):
        result = re_eng.calculate_user_score(self.mentor_uid)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    # ── TRUST LEVEL ────────────────────────────────────────────

    def test_26_trust_level_beginner(self):
        self.assertEqual(re_eng.compute_trust_level(0), "Beginner Analyst")
        self.assertEqual(re_eng.compute_trust_level(10), "Beginner Analyst")

    def test_27_trust_level_trusted(self):
        self.assertEqual(re_eng.compute_trust_level(30), "Trusted Analyst")
        self.assertEqual(re_eng.compute_trust_level(50), "Trusted Analyst")

    def test_28_trust_level_top(self):
        self.assertEqual(re_eng.compute_trust_level(60), "Top Analyst")
        self.assertEqual(re_eng.compute_trust_level(80), "Top Analyst")

    def test_29_trust_level_elite(self):
        self.assertEqual(re_eng.compute_trust_level(85), "Elite Mentor")
        self.assertEqual(re_eng.compute_trust_level(100), "Elite Mentor")

    # ── BADGES ─────────────────────────────────────────────────

    def test_30_badges_include_crypto(self):
        badges = re_eng.compute_badges(self.mentor_uid)
        self.assertIn("top_crypto", badges)

    def test_31_badges_include_bist(self):
        badges = re_eng.compute_badges(self.mentor_uid)
        self.assertIn("bist_expert", badges)

    def test_32_badges_include_strategy_master(self):
        badges = re_eng.compute_badges(self.mentor_uid)
        self.assertIn("strategy_master", badges)

    def test_33_badges_include_community_leader(self):
        badges = re_eng.compute_badges(self.mentor_uid)
        self.assertIn("community_leader", badges)

    # ── QUERIES ────────────────────────────────────────────────

    def test_34_get_reputation(self):
        rep = re_eng.get_reputation(self.mentor_uid)
        self.assertIsNotNone(rep)
        self.assertEqual(rep["user_id"], self.mentor_uid)
        self.assertIsInstance(rep["badges"], list)

    def test_35_list_top_analysts(self):
        analysts = re_eng.list_top_analysts(10)
        self.assertGreaterEqual(len(analysts), 1)
        self.assertEqual(analysts[0]["user_id"], self.mentor_uid)

    def test_36_reputation_stats(self):
        stats = re_eng.reputation_stats()
        self.assertGreaterEqual(stats["total_users_rated"], 1)
        self.assertEqual(stats["mentor_ratings_count"], 2)
        self.assertEqual(stats["course_ratings_count"], 2)
        self.assertEqual(stats["strategy_ratings_count"], 2)

    def test_37_top_mentors(self):
        mentors = re_eng.list_top_mentors(10)
        self.assertGreaterEqual(len(mentors), 1)

    def test_38_top_strategies(self):
        strategies = re_eng.list_top_strategies(10)
        self.assertGreaterEqual(len(strategies), 1)

    def test_39_user_without_data(self):
        new_uid = _uid()
        result = re_eng.calculate_user_score(new_uid)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["trust_level"], "Beginner Analyst")

    def test_40_badge_defs_complete(self):
        self.assertIn("top_crypto", re_eng.BADGE_DEFS)
        self.assertIn("bist_expert", re_eng.BADGE_DEFS)
        self.assertIn("strategy_master", re_eng.BADGE_DEFS)
        self.assertIn("top_mentor", re_eng.BADGE_DEFS)
        self.assertIn("community_leader", re_eng.BADGE_DEFS)


if __name__ == "__main__":
    unittest.main()
