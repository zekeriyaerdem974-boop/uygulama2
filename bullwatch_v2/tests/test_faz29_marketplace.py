# -*- coding: utf-8 -*-
"""FAZ 29 — Strategy Marketplace Tests.

Tests marketplace publish, unpublish, follow, unfollow, list, detail,
my-published, following, metrics, and discover integration.
"""
import json
import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMarketplaceEngine(unittest.TestCase):
    """Test the marketplace engine directly."""

    def setUp(self):
        """Set up test database."""
        from app.core import marketplace_engine as me
        import app.core.db_manager as _dm
        # Use a test database
        self._orig_path = me._DB_PATH
        self._orig_db_dir = _dm._DB_DIR
        me._DB_PATH = os.path.join(me._DB_DIR, "marketplace_test.db")
        _dm._DB_DIR = me._DB_DIR
        # Remove old test DB
        if os.path.exists(me._DB_PATH):
            os.remove(me._DB_PATH)
        me._init_db()
        self.me = me

    def tearDown(self):
        """Clean up test database."""
        import app.core.db_manager as _dm
        if os.path.exists(self.me._DB_PATH):
            os.remove(self.me._DB_PATH)
        self.me._DB_PATH = self._orig_path
        _dm._DB_DIR = self._orig_db_dir

    def test_publish_strategy(self):
        """Test publishing a strategy."""
        s = self.me.publish_strategy(
            user_id="user1",
            title="EMA Cross",
            description="Simple EMA crossover strategy",
            strategy_code='strategy "EMA Cross"\n\nentry:\n  EMA9 crosses_above EMA21',
            market="crypto",
            default_symbol="BTCUSDT",
            default_interval="1h",
            tags=["trend", "ema"],
        )
        self.assertIsNotNone(s)
        self.assertEqual(s["title"], "EMA Cross")
        self.assertEqual(s["user_id"], "user1")
        self.assertEqual(s["visibility"], "public")
        self.assertEqual(s["market"], "crypto")
        self.assertIn("ema-cross", s["slug"])

    def test_unpublish_strategy(self):
        """Test unpublishing a strategy."""
        s = self.me.publish_strategy(
            user_id="user1", title="To Unpublish",
            description="", strategy_code="code"
        )
        ok = self.me.unpublish_strategy(s["id"], "user1")
        self.assertTrue(ok)
        # Should not be findable
        found = self.me.get_published(s["id"])
        self.assertIsNone(found)

    def test_unpublish_wrong_user(self):
        """Test that only owner can unpublish."""
        s = self.me.publish_strategy(
            user_id="user1", title="Mine",
            description="", strategy_code="code"
        )
        ok = self.me.unpublish_strategy(s["id"], "user2")
        self.assertFalse(ok)

    def test_list_published(self):
        """Test listing public strategies."""
        self.me.publish_strategy(user_id="u1", title="S1", description="", strategy_code="c1")
        self.me.publish_strategy(user_id="u2", title="S2", description="", strategy_code="c2")
        self.me.publish_strategy(user_id="u3", title="S3", description="", strategy_code="c3",
                                  visibility="private")

        public = self.me.list_published()
        self.assertEqual(len(public), 2)  # S3 is private

    def test_get_by_slug(self):
        """Test getting strategy by slug."""
        s = self.me.publish_strategy(
            user_id="u1", title="My Cool Strategy",
            description="", strategy_code="code"
        )
        found = self.me.get_published_by_slug(s["slug"])
        self.assertIsNotNone(found)
        self.assertEqual(found["title"], "My Cool Strategy")

    def test_follow_unfollow(self):
        """Test following and unfollowing a strategy."""
        s = self.me.publish_strategy(
            user_id="u1", title="Follow Me",
            description="", strategy_code="code"
        )
        # Follow
        self.me.follow_strategy(s["id"], "u2")
        self.assertTrue(self.me.is_following(s["id"], "u2"))
        followers = self.me.get_followers(s["id"])
        self.assertIn("u2", followers)

        # Check metrics updated
        m = self.me.get_strategy_metrics(s["id"])
        self.assertEqual(m["followers_count"], 1)

        # Unfollow
        self.me.unfollow_strategy(s["id"], "u2")
        self.assertFalse(self.me.is_following(s["id"], "u2"))
        m = self.me.get_strategy_metrics(s["id"])
        self.assertEqual(m["followers_count"], 0)

    def test_follow_own_strategy_fails(self):
        """Test that user can't follow own strategy."""
        s = self.me.publish_strategy(
            user_id="u1", title="Mine",
            description="", strategy_code="code"
        )
        with self.assertRaises(ValueError):
            self.me.follow_strategy(s["id"], "u1")

    def test_get_following(self):
        """Test getting followed strategies."""
        s1 = self.me.publish_strategy(user_id="u1", title="S1", description="", strategy_code="c1")
        s2 = self.me.publish_strategy(user_id="u1", title="S2", description="", strategy_code="c2")
        self.me.follow_strategy(s1["id"], "u2")
        self.me.follow_strategy(s2["id"], "u2")

        following = self.me.get_following("u2")
        self.assertEqual(len(following), 2)

    def test_my_published(self):
        """Test getting user's published strategies."""
        self.me.publish_strategy(user_id="u1", title="S1", description="", strategy_code="c1")
        self.me.publish_strategy(user_id="u1", title="S2", description="", strategy_code="c2")
        self.me.publish_strategy(user_id="u2", title="S3", description="", strategy_code="c3")

        my = self.me.get_my_published("u1")
        self.assertEqual(len(my), 2)

    def test_update_metrics(self):
        """Test updating strategy metrics."""
        s = self.me.publish_strategy(
            user_id="u1", title="Metric Test",
            description="", strategy_code="code"
        )
        self.me.update_metrics(s["id"], {
            "win_rate": 65.5,
            "profit_factor": 2.1,
            "net_profit": 15.3,
            "max_drawdown": 8.2,
        })
        m = self.me.get_strategy_metrics(s["id"])
        self.assertAlmostEqual(m["win_rate"], 65.5)
        self.assertAlmostEqual(m["profit_factor"], 2.1)

    def test_publish_validation(self):
        """Test validation on publish."""
        with self.assertRaises(ValueError):
            self.me.publish_strategy(user_id="u1", title="", description="", strategy_code="code")
        with self.assertRaises(ValueError):
            self.me.publish_strategy(user_id="u1", title="T", description="", strategy_code="")

    def test_unique_slug(self):
        """Test that duplicate titles get unique slugs."""
        s1 = self.me.publish_strategy(user_id="u1", title="Same Name", description="", strategy_code="c1")
        s2 = self.me.publish_strategy(user_id="u2", title="Same Name", description="", strategy_code="c2")
        self.assertNotEqual(s1["slug"], s2["slug"])

    def test_search_strategies(self):
        """Test search functionality."""
        self.me.publish_strategy(user_id="u1", title="EMA Cross BTC", description="crossover", strategy_code="c1")
        self.me.publish_strategy(user_id="u2", title="RSI Bounce", description="rsi reversal", strategy_code="c2")

        results = self.me.list_published(search="EMA")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "EMA Cross BTC")

    def test_tags_json(self):
        """Test tags are stored and retrieved as JSON list."""
        s = self.me.publish_strategy(
            user_id="u1", title="Tagged",
            description="", strategy_code="code",
            tags=["momentum", "crypto", "scalp"]
        )
        found = self.me.get_published(s["id"])
        self.assertEqual(found["tags"], ["momentum", "crypto", "scalp"])


class TestMarketplaceAPI(unittest.TestCase):
    """Test marketplace API endpoints via Flask test client."""

    @classmethod
    def setUpClass(cls):
        """Set up Flask test client."""
        from app.core import marketplace_engine as me
        import app.core.db_manager as _dm
        cls._orig_path = me._DB_PATH
        cls._orig_db_dir = _dm._DB_DIR
        me._DB_PATH = os.path.join(me._DB_DIR, "marketplace_api_test.db")
        _dm._DB_DIR = me._DB_DIR
        if os.path.exists(me._DB_PATH):
            os.remove(me._DB_PATH)
        me._init_db()
        cls.me = me

        # Import and configure app
        from legacy_monolith import app
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        cls.app = app
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        if os.path.exists(cls.me._DB_PATH):
            os.remove(cls.me._DB_PATH)
        cls.me._DB_PATH = cls._orig_path
        _dm._DB_DIR = cls._orig_db_dir

    def _login(self):
        """Simulate login by setting session."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test-user-1"
            sess["username"] = "testuser"

    def _login_user2(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test-user-2"
            sess["username"] = "testuser2"

    def test_publish_endpoint(self):
        """Test POST /api/marketplace/publish."""
        self._login()
        r = self.client.post("/api/marketplace/publish",
                             json={
                                 "title": "API Test Strategy",
                                 "description": "Test desc",
                                 "strategy_code": 'strategy "Test"\n\nentry:\n  RSI14 above 30',
                                 "market": "crypto",
                                 "default_symbol": "BTCUSDT",
                                 "tags": ["test"],
                             })
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["strategy"]["title"], "API Test Strategy")
        self.__class__._pub_id = data["strategy"]["id"]
        self.__class__._pub_slug = data["strategy"]["slug"]

    def test_list_endpoint(self):
        """Test GET /api/marketplace/strategies."""
        r = self.client.get("/api/marketplace/strategies")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertGreaterEqual(data["count"], 0)

    def test_detail_endpoint(self):
        """Test GET /api/marketplace/strategy/<id>."""
        pub_id = getattr(self.__class__, "_pub_id", None)
        if not pub_id:
            self.skipTest("No published strategy to test")
        r = self.client.get(f"/api/marketplace/strategy/{pub_id}")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["strategy"]["title"], "API Test Strategy")

    def test_detail_by_slug(self):
        """Test GET /api/marketplace/strategy/<slug>."""
        slug = getattr(self.__class__, "_pub_slug", None)
        if not slug:
            self.skipTest("No published strategy to test")
        r = self.client.get(f"/api/marketplace/strategy/{slug}")
        data = r.get_json()
        self.assertTrue(data["ok"])

    def test_follow_endpoint(self):
        """Test POST /api/marketplace/follow."""
        pub_id = getattr(self.__class__, "_pub_id", None)
        if not pub_id:
            self.skipTest("No published strategy to test")
        self._login_user2()
        r = self.client.post("/api/marketplace/follow", json={"pub_id": pub_id})
        data = r.get_json()
        self.assertTrue(data["ok"])

    def test_following_endpoint(self):
        """Test GET /api/marketplace/following."""
        self._login_user2()
        r = self.client.get("/api/marketplace/following")
        data = r.get_json()
        self.assertTrue(data["ok"])

    def test_unfollow_endpoint(self):
        """Test POST /api/marketplace/unfollow."""
        pub_id = getattr(self.__class__, "_pub_id", None)
        if not pub_id:
            self.skipTest("No published strategy to test")
        self._login_user2()
        r = self.client.post("/api/marketplace/unfollow", json={"pub_id": pub_id})
        data = r.get_json()
        self.assertTrue(data["ok"])

    def test_my_published_endpoint(self):
        """Test GET /api/marketplace/my-published."""
        self._login()
        r = self.client.get("/api/marketplace/my-published")
        data = r.get_json()
        self.assertTrue(data["ok"])

    def test_unpublish_endpoint(self):
        """Test POST /api/marketplace/unpublish."""
        # Publish a new one to unpublish
        self._login()
        r = self.client.post("/api/marketplace/publish",
                             json={"title": "To Delete", "description": "",
                                   "strategy_code": "code"})
        pub_id = r.get_json()["strategy"]["id"]

        r = self.client.post("/api/marketplace/unpublish", json={"pub_id": pub_id})
        data = r.get_json()
        self.assertTrue(data["ok"])

    def test_marketplace_page(self):
        """Test GET /marketplace page renders."""
        r = self.client.get("/marketplace")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Marketplace", r.data)

    def test_detail_page(self):
        """Test GET /marketplace/<slug> page renders."""
        slug = getattr(self.__class__, "_pub_slug", "test")
        r = self.client.get(f"/marketplace/{slug}")
        self.assertEqual(r.status_code, 200)

    def test_auth_required(self):
        """Test that publish requires authentication."""
        # Clear session
        with self.client.session_transaction() as sess:
            sess.clear()
        r = self.client.post("/api/marketplace/publish",
                             json={"title": "No Auth", "description": "",
                                   "strategy_code": "code"})
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
