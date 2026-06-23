# -*- coding: utf-8 -*-
"""FAZ 36 — Viral Sharing / Growth Engine tests.

Covers:
  01-05  Analysis engine — create, get, feed
  06-08  Analysis likes
  09-11  Analysis comments
  12-14  Shares & view counting
  15-18  Trending & leaderboard
  19-21  Analyst stats
  22-26  Feature flags
  27-30  Analysis deletion & edge cases
  31-35  Blueprint API routes
  36-40  Public analysis page & leaderboard page
  41-45  Discover integration (feature flags, trending, leaderboard)
"""
import json
import os
import sqlite3
import sys
import unittest

# ── project root on sys.path ──
_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

# ── isolate test data ──
_TEST_DIR = os.path.join(_PROJECT, ".test_data_faz36_growth")
os.makedirs(_TEST_DIR, exist_ok=True)

import app.core.analysis_engine as ae

import app.core.db_manager as _dm
_dm._DB_DIR = _TEST_DIR
ae._DB_DIR = _TEST_DIR
ae._DB_PATH = os.path.join(_TEST_DIR, "analysis.db")
ae._USERS_DB = os.path.join(_TEST_DIR, "users.db")

# Re-init DB with new paths
ae._init_db()


def _uid(n=1):
    return f"testuser{n}"


def _create_test_users_db():
    conn = sqlite3.connect(ae._USERS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, email TEXT, username TEXT,
            password_hash TEXT, created_at TEXT, plan TEXT DEFAULT 'free',
            is_active INTEGER DEFAULT 1
        )
    """)
    for i in range(1, 6):
        conn.execute(
            "INSERT OR IGNORE INTO users (id, email, username, password_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"testuser{i}", f"testuser{i}@test.com", f"analyst{i}", "hash", "2025-01-01"),
        )
    conn.commit()
    conn.close()


def _reset_analysis_db():
    """Clear analysis tables for a clean test slate."""
    conn = ae._get_conn()
    try:
        conn.execute("DELETE FROM analysis_likes")
        conn.execute("DELETE FROM analysis_comments")
        conn.execute("DELETE FROM analysis_posts")
        conn.commit()
    finally:
        conn.close()


class TestAnalysisCreate(unittest.TestCase):
    """01-05: Analysis creation and retrieval."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()

    def test_01_create_analysis(self):
        a = ae.create_analysis(
            user_id=_uid(1), content="BTC analizi — yükseliş trendi",
            title="BTC Analiz", symbol="BTCUSDT", market="crypto",
            timeframe="4h", direction="long",
        )
        self.assertEqual(a["content"], "BTC analizi — yükseliş trendi")
        self.assertEqual(a["title"], "BTC Analiz")
        self.assertEqual(a["symbol"], "BTCUSDT")
        self.assertEqual(a["direction"], "long")
        self.assertEqual(a["likes_count"], 0)
        self.assertIn("id", a)

    def test_02_create_analysis_minimal(self):
        a = ae.create_analysis(user_id=_uid(2), content="Kısa görüş")
        self.assertEqual(a["content"], "Kısa görüş")
        self.assertIsNone(a["symbol"])

    def test_03_create_analysis_empty_content_raises(self):
        with self.assertRaises(ValueError):
            ae.create_analysis(user_id=_uid(1), content="")

    def test_04_get_analysis(self):
        a = ae.create_analysis(user_id=_uid(1), content="Test get")
        fetched = ae.get_analysis(a["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["content"], "Test get")
        self.assertEqual(fetched["username"], "analyst1")

    def test_05_get_analysis_not_found(self):
        result = ae.get_analysis("nonexistent-id")
        self.assertIsNone(result)


class TestAnalysisFeed(unittest.TestCase):
    """06-08: Feed retrieval."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()
        for i in range(5):
            ae.create_analysis(
                user_id=_uid(1), content=f"Feed post {i}",
                symbol="ETHUSDT", market="crypto",
            )
        ae.create_analysis(
            user_id=_uid(2), content="Other user post",
            symbol="BTCUSDT", market="crypto",
        )

    def test_06_feed_returns_all(self):
        feed = ae.get_analysis_feed(limit=50)
        self.assertGreaterEqual(len(feed), 6)

    def test_07_feed_filter_by_symbol(self):
        feed = ae.get_analysis_feed(symbol="BTCUSDT")
        self.assertTrue(all(a["symbol"] == "BTCUSDT" for a in feed))

    def test_08_user_analyses(self):
        user_posts = ae.get_user_analyses(_uid(1))
        self.assertTrue(all(a["user_id"] == _uid(1) for a in user_posts))


class TestAnalysisLikes(unittest.TestCase):
    """09-11: Like toggling."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()
        cls.analysis = ae.create_analysis(user_id=_uid(1), content="Likeable")

    def test_09_like(self):
        r = ae.toggle_analysis_like(self.analysis["id"], _uid(2))
        self.assertTrue(r["liked"])
        self.assertEqual(r["likes_count"], 1)

    def test_10_unlike(self):
        r = ae.toggle_analysis_like(self.analysis["id"], _uid(2))
        self.assertFalse(r["liked"])
        self.assertEqual(r["likes_count"], 0)

    def test_11_like_again(self):
        r = ae.toggle_analysis_like(self.analysis["id"], _uid(2))
        self.assertTrue(r["liked"])
        self.assertEqual(r["likes_count"], 1)


class TestAnalysisComments(unittest.TestCase):
    """12-14: Comments."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()
        cls.analysis = ae.create_analysis(user_id=_uid(1), content="Commentable")

    def test_12_add_comment(self):
        c = ae.add_analysis_comment(self.analysis["id"], _uid(2), "Harika analiz!")
        self.assertEqual(c["content"], "Harika analiz!")
        self.assertEqual(c["username"], "analyst2")

    def test_13_get_comments(self):
        comments = ae.get_analysis_comments(self.analysis["id"])
        self.assertGreaterEqual(len(comments), 1)

    def test_14_empty_comment_raises(self):
        with self.assertRaises(ValueError):
            ae.add_analysis_comment(self.analysis["id"], _uid(2), "")


class TestSharesAndViews(unittest.TestCase):
    """15-17: Shares and view counting."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()
        cls.analysis = ae.create_analysis(user_id=_uid(1), content="Viewable")

    def test_15_increment_views(self):
        ae.get_analysis(self.analysis["id"], increment_views=True)
        ae.get_analysis(self.analysis["id"], increment_views=True)
        a = ae.get_analysis(self.analysis["id"])
        self.assertEqual(a["views_count"], 2)

    def test_16_increment_shares(self):
        r = ae.increment_shares(self.analysis["id"])
        self.assertEqual(r["shares_count"], 1)

    def test_17_increment_shares_twice(self):
        ae.increment_shares(self.analysis["id"])
        a = ae.get_analysis(self.analysis["id"])
        self.assertEqual(a["shares_count"], 2)


class TestTrendingLeaderboard(unittest.TestCase):
    """18-21: Trending analyses and leaderboard."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()
        # Create analyses with varying engagement
        for i in range(1, 4):
            a = ae.create_analysis(
                user_id=_uid(i), content=f"Analysis by user {i}",
                symbol="BTCUSDT",
            )
            # Give different likes
            for j in range(i):
                ae.toggle_analysis_like(a["id"], _uid(j + 1 if j + 1 != i else 4))

    def test_18_trending_returns_results(self):
        trending = ae.get_trending_analyses(limit=10)
        self.assertGreater(len(trending), 0)

    def test_19_trending_sorted_by_engagement(self):
        trending = ae.get_trending_analyses(limit=10)
        if len(trending) >= 2:
            # Higher engagement should come first
            scores = [t["likes_count"] * 3 + t["views_count"] for t in trending]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_20_leaderboard_returns_results(self):
        lb = ae.get_leaderboard(limit=10)
        self.assertGreater(len(lb), 0)

    def test_21_leaderboard_has_username(self):
        lb = ae.get_leaderboard(limit=10)
        for entry in lb:
            self.assertIn("username", entry)
            self.assertIn("analysis_count", entry)
            self.assertIn("score", entry)


class TestAnalystStats(unittest.TestCase):
    """22-24: Analyst stats."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()
        _reset_analysis_db()
        ae.create_analysis(user_id=_uid(1), content="Stats test 1")
        a = ae.create_analysis(user_id=_uid(1), content="Stats test 2")
        ae.toggle_analysis_like(a["id"], _uid(2))

    def test_22_get_stats(self):
        stats = ae.get_analyst_stats(_uid(1))
        self.assertEqual(stats["analysis_count"], 2)
        self.assertEqual(stats["total_likes"], 1)

    def test_23_stats_empty_user(self):
        stats = ae.get_analyst_stats("nonexistent")
        self.assertEqual(stats["analysis_count"], 0)

    def test_24_stats_has_all_fields(self):
        stats = ae.get_analyst_stats(_uid(1))
        for key in ["analysis_count", "total_likes", "total_views", "total_comments", "total_shares"]:
            self.assertIn(key, stats)


class TestFeatureFlags(unittest.TestCase):
    """25-30: Feature flag system."""

    def test_25_default_flags(self):
        features = ae.list_features()
        names = [f["name"] for f in features]
        self.assertIn("courses", names)
        self.assertIn("live_rooms", names)
        self.assertIn("subscriptions", names)
        self.assertIn("analysis_sharing", names)

    def test_26_courses_disabled_by_default(self):
        self.assertFalse(ae.feature_enabled("courses"))

    def test_27_live_rooms_disabled_by_default(self):
        self.assertFalse(ae.feature_enabled("live_rooms"))

    def test_28_subscriptions_disabled_by_default(self):
        self.assertFalse(ae.feature_enabled("subscriptions"))

    def test_29_analysis_sharing_enabled(self):
        self.assertTrue(ae.feature_enabled("analysis_sharing"))

    def test_30_set_feature(self):
        ae.set_feature("courses", True)
        self.assertTrue(ae.feature_enabled("courses"))
        ae.set_feature("courses", False)
        self.assertFalse(ae.feature_enabled("courses"))


class TestAnalysisDeletion(unittest.TestCase):
    """31-33: Deletion and edge cases."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()

    def test_31_delete_own_analysis(self):
        a = ae.create_analysis(user_id=_uid(1), content="Delete me")
        deleted = ae.delete_analysis(a["id"], _uid(1))
        self.assertTrue(deleted)
        self.assertIsNone(ae.get_analysis(a["id"]))

    def test_32_cannot_delete_others_analysis(self):
        a = ae.create_analysis(user_id=_uid(1), content="Not yours")
        deleted = ae.delete_analysis(a["id"], _uid(2))
        self.assertFalse(deleted)
        self.assertIsNotNone(ae.get_analysis(a["id"]))

    def test_33_delete_nonexistent(self):
        deleted = ae.delete_analysis("nonexistent", _uid(1))
        self.assertFalse(deleted)


class TestAnalysisChartImage(unittest.TestCase):
    """34-35: Chart image storage."""

    @classmethod
    def setUpClass(cls):
        _create_test_users_db()

    def test_34_analysis_with_chart_image(self):
        a = ae.create_analysis(
            user_id=_uid(1), content="With chart",
            chart_image="/static/media/chart_test123.png",
        )
        self.assertEqual(a["chart_image"], "/static/media/chart_test123.png")

    def test_35_analysis_without_chart(self):
        a = ae.create_analysis(user_id=_uid(1), content="No chart")
        self.assertIsNone(a["chart_image"])


class TestBlueprintRoutes(unittest.TestCase):
    """36-45: Blueprint API routes via Flask test client."""

    @classmethod
    def setUpClass(cls):
        from legacy_monolith import app
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-faz36"
        cls.app = app
        cls.client = app.test_client()

        # Ensure test users exist
        _create_test_users_db()
        _reset_analysis_db()

    def _login(self, user_id="testuser1"):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["username"] = f"analyst{user_id[-1]}"

    def test_36_create_via_api(self):
        self._login()
        r = self.client.post("/api/analysis/create", json={
            "content": "API test analysis",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "direction": "long",
        })
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertIn("analysis", d)
        self.__class__.analysis_id = d["analysis"]["id"]

    def test_37_get_feed_via_api(self):
        r = self.client.get("/api/analysis/feed")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertIn("analyses", d)

    def test_38_get_single_via_api(self):
        r = self.client.get(f"/api/analysis/{self.analysis_id}")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["analysis"]["content"], "API test analysis")

    def test_39_like_via_api(self):
        self._login("testuser2")
        r = self.client.post("/api/analysis/like", json={
            "analysis_id": self.analysis_id,
        })
        d = r.get_json()
        self.assertTrue(d["liked"])

    def test_40_comment_via_api(self):
        self._login("testuser2")
        r = self.client.post("/api/analysis/comment", json={
            "analysis_id": self.analysis_id,
            "content": "Great analysis!",
        })
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["comment"]["content"], "Great analysis!")

    def test_41_trending_via_api(self):
        r = self.client.get("/api/analysis/trending")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertIn("analyses", d)

    def test_42_leaderboard_via_api(self):
        r = self.client.get("/api/analysis/leaderboard")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertIn("leaderboard", d)

    def test_43_features_via_api(self):
        r = self.client.get("/api/analysis/features")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertIn("features", d)
        names = [f["name"] for f in d["features"]]
        self.assertIn("courses", names)

    def test_44_feature_check_via_api(self):
        r = self.client.get("/api/analysis/feature/courses")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertFalse(d["enabled"])

    def test_45_analysis_page_loads(self):
        r = self.client.get(f"/analysis/{self.analysis_id}")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Analiz", r.data)

    def test_46_leaderboard_page_loads(self):
        r = self.client.get("/leaderboard")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Liderlik", r.data)

    def test_47_share_increments(self):
        r = self.client.post("/api/analysis/share", json={
            "analysis_id": self.analysis_id,
        })
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertGreaterEqual(d["shares_count"], 1)

    def test_48_user_stats_via_api(self):
        r = self.client.get("/api/analysis/user-stats/testuser1")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertIn("stats", d)
        self.assertGreaterEqual(d["stats"]["analysis_count"], 1)

    def test_49_create_requires_login(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        r = self.client.post("/api/analysis/create", json={"content": "Unauthorized"})
        self.assertEqual(r.status_code, 401)

    def test_50_delete_via_api(self):
        self._login("testuser1")
        a = ae.create_analysis(user_id="testuser1", content="Delete via API")
        r = self.client.delete(f"/api/analysis/{a['id']}")
        d = r.get_json()
        self.assertTrue(d["ok"])


if __name__ == "__main__":
    unittest.main()
