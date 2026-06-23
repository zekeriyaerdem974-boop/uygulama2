# -*- coding: utf-8 -*-
"""FAZ 31 — Social Trading Feed tests.

Tests social_engine core functions and API endpoints via curl.
Run: python tests/test_faz31_social.py
"""
from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSocialEngine(unittest.TestCase):
    """Unit tests for social_engine.py — uses temp DB."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp()
        cls._db_path = os.path.join(cls._tmpdir, "social.db")
        cls._users_db = os.path.join(cls._tmpdir, "users.db")

        # Create a fake users.db
        conn = sqlite3.connect(cls._users_db)
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT)")
        conn.execute("INSERT INTO users VALUES ('user1', 'alice')")
        conn.execute("INSERT INTO users VALUES ('user2', 'bob')")
        conn.commit()
        conn.close()

        # Patch DB paths before importing the engine
        import app.core.db_manager as _dm
        cls._orig_db_dir = _dm._DB_DIR
        _dm._DB_DIR = cls._tmpdir
        import app.core.social_engine as _se
        _se._DB_PATH = cls._db_path
        _se._USERS_DB = cls._users_db
        _se._init_db()
        cls.se = _se

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def setUp(self):
        """Clean tables between tests."""
        conn = sqlite3.connect(self._db_path)
        for table in ("likes", "comments", "follows", "posts"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()

    # ── Posts ──────────────────────────────────────────────────

    def test_create_post(self):
        p = self.se.create_post("user1", "BTC yukarı gidecek", symbol="BTCUSDT")
        self.assertTrue(p["id"])
        self.assertEqual(p["content"], "BTC yukarı gidecek")
        self.assertEqual(p["symbol"], "BTCUSDT")
        self.assertEqual(p["username"], "alice")
        self.assertEqual(p["likes_count"], 0)
        self.assertFalse(p["is_liked"])

    def test_create_post_empty_content_raises(self):
        with self.assertRaises(ValueError):
            self.se.create_post("user1", "")

    def test_get_post(self):
        p = self.se.create_post("user1", "test post")
        fetched = self.se.get_post(p["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["content"], "test post")

    def test_get_post_not_found(self):
        self.assertIsNone(self.se.get_post("nonexistent"))

    def test_delete_post(self):
        p = self.se.create_post("user1", "to delete")
        self.assertTrue(self.se.delete_post(p["id"], "user1"))
        self.assertIsNone(self.se.get_post(p["id"]))

    def test_delete_post_wrong_user(self):
        p = self.se.create_post("user1", "only mine")
        self.assertFalse(self.se.delete_post(p["id"], "user2"))

    # ── Feed ──────────────────────────────────────────────────

    def test_get_feed(self):
        self.se.create_post("user1", "first")
        self.se.create_post("user2", "second")
        feed = self.se.get_feed()
        self.assertEqual(len(feed), 2)
        # newest first
        self.assertEqual(feed[0]["content"], "second")

    def test_get_feed_by_symbol(self):
        self.se.create_post("user1", "p1", symbol="BTCUSDT")
        self.se.create_post("user1", "p2", symbol="ETHUSDT")
        feed = self.se.get_feed(symbol="BTCUSDT")
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["symbol"], "BTCUSDT")

    def test_get_user_feed(self):
        self.se.create_post("user1", "a1")
        self.se.create_post("user2", "b1")
        feed = self.se.get_user_feed("user1")
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["content"], "a1")

    def test_get_following_feed(self):
        self.se.create_post("user2", "followed content")
        self.se.follow_user("user1", "user2")
        feed = self.se.get_following_feed("user1")
        self.assertEqual(len(feed), 1)
        self.assertEqual(feed[0]["content"], "followed content")

    def test_get_trending(self):
        p = self.se.create_post("user1", "hot take", symbol="BTCUSDT")
        self.se.toggle_like(p["id"], "user2")
        trending = self.se.get_trending(limit=5)
        self.assertGreaterEqual(len(trending), 1)
        self.assertEqual(trending[0]["id"], p["id"])

    # ── Comments ──────────────────────────────────────────────

    def test_add_comment(self):
        p = self.se.create_post("user1", "main post")
        c = self.se.add_comment(p["id"], "user2", "nice analysis")
        self.assertTrue(c["id"])
        self.assertEqual(c["content"], "nice analysis")
        self.assertEqual(c["username"], "bob")
        # Post comments_count updated
        updated = self.se.get_post(p["id"])
        self.assertEqual(updated["comments_count"], 1)

    def test_add_comment_empty_raises(self):
        p = self.se.create_post("user1", "some post")
        with self.assertRaises(ValueError):
            self.se.add_comment(p["id"], "user2", "")

    def test_get_comments(self):
        p = self.se.create_post("user1", "post")
        self.se.add_comment(p["id"], "user2", "c1")
        self.se.add_comment(p["id"], "user1", "c2")
        comments = self.se.get_comments(p["id"])
        self.assertEqual(len(comments), 2)
        self.assertEqual(comments[0]["content"], "c1")

    # ── Likes ──────────────────────────────────────────────────

    def test_toggle_like_on(self):
        p = self.se.create_post("user1", "like me")
        result = self.se.toggle_like(p["id"], "user2")
        self.assertTrue(result["liked"])
        self.assertEqual(result["likes_count"], 1)

    def test_toggle_like_off(self):
        p = self.se.create_post("user1", "like and unlike")
        self.se.toggle_like(p["id"], "user2")  # like
        result = self.se.toggle_like(p["id"], "user2")  # unlike
        self.assertFalse(result["liked"])
        self.assertEqual(result["likes_count"], 0)

    def test_is_liked_in_feed(self):
        p = self.se.create_post("user1", "test liked flag")
        self.se.toggle_like(p["id"], "user2")
        feed = self.se.get_feed(viewer_id="user2")
        self.assertTrue(feed[0]["is_liked"])
        feed2 = self.se.get_feed(viewer_id="user1")
        self.assertFalse(feed2[0]["is_liked"])

    # ── Follows ────────────────────────────────────────────────

    def test_follow_user(self):
        self.se.follow_user("user1", "user2")
        self.assertTrue(self.se.is_following_user("user1", "user2"))
        self.assertFalse(self.se.is_following_user("user2", "user1"))

    def test_unfollow_user(self):
        self.se.follow_user("user1", "user2")
        self.se.unfollow_user("user1", "user2")
        self.assertFalse(self.se.is_following_user("user1", "user2"))

    def test_follow_self_raises(self):
        with self.assertRaises(ValueError):
            self.se.follow_user("user1", "user1")

    def test_followers_and_following(self):
        self.se.follow_user("user1", "user2")
        self.assertIn("user1", self.se.get_followers("user2"))
        self.assertIn("user2", self.se.get_following("user1"))
        self.assertEqual(self.se.get_followers_count("user2"), 1)
        self.assertEqual(self.se.get_following_count("user1"), 1)

    # ── User Profile ──────────────────────────────────────────

    def test_get_user_profile(self):
        self.se.create_post("user1", "post1")
        self.se.create_post("user1", "post2")
        p = self.se.create_post("user1", "post3")
        self.se.toggle_like(p["id"], "user2")

        profile = self.se.get_user_profile("alice", viewer_id="user2")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["username"], "alice")
        self.assertEqual(profile["post_count"], 3)
        self.assertEqual(profile["total_likes"], 1)
        self.assertFalse(profile["is_following"])
        self.assertFalse(profile["is_own_profile"])

    def test_get_user_profile_own(self):
        profile = self.se.get_user_profile("alice", viewer_id="user1")
        self.assertIsNotNone(profile)
        self.assertTrue(profile["is_own_profile"])

    def test_get_user_profile_not_found(self):
        self.assertIsNone(self.se.get_user_profile("nonexistent"))

    def test_get_user_profile_with_follow(self):
        self.se.follow_user("user2", "user1")
        profile = self.se.get_user_profile("alice", viewer_id="user2")
        self.assertTrue(profile["is_following"])


if __name__ == "__main__":
    unittest.main()
