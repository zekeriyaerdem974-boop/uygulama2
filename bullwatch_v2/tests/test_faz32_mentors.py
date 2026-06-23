# -*- coding: utf-8 -*-
"""FAZ 32 — Mentor Profile tests.

Tests mentor_engine core functions.
Run: python -m pytest tests/test_faz32_mentors.py -v
"""
from __future__ import annotations

import os
import sys
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMentorEngine(unittest.TestCase):
    """Unit tests for mentor_engine.py — uses temp DB."""

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp()
        cls._db_path = os.path.join(cls._tmpdir, "mentors.db")
        cls._users_db = os.path.join(cls._tmpdir, "users.db")

        # Create a fake users.db
        conn = sqlite3.connect(cls._users_db)
        conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT)")
        conn.execute("INSERT INTO users VALUES ('user1', 'alice')")
        conn.execute("INSERT INTO users VALUES ('user2', 'bob')")
        conn.execute("INSERT INTO users VALUES ('user3', 'charlie')")
        conn.commit()
        conn.close()

        import app.core.db_manager as _dm
        cls._orig_db_dir = _dm._DB_DIR
        _dm._DB_DIR = cls._tmpdir
        import app.core.mentor_engine as _me
        _me._DB_PATH = cls._db_path
        _me._USERS_DB = cls._users_db
        _me._init_db()
        cls.me = _me

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def setUp(self):
        conn = sqlite3.connect(self._db_path)
        for table in ("mentor_follows", "mentor_profiles"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()

    # ── Profile CRUD ──────────────────────────────────────────

    def test_create_profile(self):
        p = self.me.create_or_update_profile(
            user_id="user1",
            display_name="CryptoMaster",
            headline="5 Yıllık Kripto Analizci",
            bio="Bitcoin ve altcoin analizleri",
            experience_years=5,
            markets="crypto,bist",
            specialties="Teknik Analiz, DeFi",
            languages="Türkçe, İngilizce",
            pricing_model="free",
        )
        self.assertTrue(p["id"])
        self.assertEqual(p["display_name"], "CryptoMaster")
        self.assertEqual(p["headline"], "5 Yıllık Kripto Analizci")
        self.assertEqual(p["username"], "alice")
        self.assertIn("crypto", p["markets_list"])
        self.assertIn("bist", p["markets_list"])
        self.assertEqual(p["pricing_model"], "free")

    def test_update_profile(self):
        self.me.create_or_update_profile("user1", "OldName", markets="crypto")
        updated = self.me.create_or_update_profile(
            "user1", "NewName", headline="Updated", markets="bist"
        )
        self.assertEqual(updated["display_name"], "NewName")
        self.assertEqual(updated["headline"], "Updated")
        self.assertIn("bist", updated["markets_list"])

    def test_create_profile_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.me.create_or_update_profile("user1", "")

    def test_create_profile_invalid_market_raises(self):
        with self.assertRaises(ValueError):
            self.me.create_or_update_profile("user1", "Test", markets="invalid_market")

    def test_get_profile_by_username(self):
        self.me.create_or_update_profile("user1", "Alice Mentor", markets="crypto")
        profile = self.me.get_profile("alice")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["display_name"], "Alice Mentor")

    def test_get_profile_not_found(self):
        self.assertIsNone(self.me.get_profile("nonexistent"))

    def test_get_profile_by_user_id(self):
        self.me.create_or_update_profile("user1", "Test Mentor")
        profile = self.me.get_profile_by_user_id("user1")
        self.assertIsNotNone(profile)

    # ── List Mentors ──────────────────────────────────────────

    def test_list_mentors(self):
        self.me.create_or_update_profile("user1", "A1", markets="crypto")
        self.me.create_or_update_profile("user2", "B2", markets="bist")
        mentors = self.me.list_mentors()
        self.assertEqual(len(mentors), 2)

    def test_list_mentors_filter_market(self):
        self.me.create_or_update_profile("user1", "Crypto Guy", markets="crypto")
        self.me.create_or_update_profile("user2", "BIST Guy", markets="bist")
        cryptos = self.me.list_mentors(market="crypto")
        self.assertEqual(len(cryptos), 1)
        self.assertEqual(cryptos[0]["display_name"], "Crypto Guy")

    def test_list_mentors_search(self):
        self.me.create_or_update_profile("user1", "CryptoMaster", headline="Bitcoin expert")
        self.me.create_or_update_profile("user2", "StockGuru", headline="Hisse analiz")
        found = self.me.list_mentors(search="Bitcoin")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["display_name"], "CryptoMaster")

    def test_list_mentors_sort_experience(self):
        self.me.create_or_update_profile("user1", "Junior", experience_years=1)
        self.me.create_or_update_profile("user2", "Senior", experience_years=10)
        mentors = self.me.list_mentors(sort="experience")
        self.assertEqual(mentors[0]["display_name"], "Senior")

    # ── Follow / Unfollow ─────────────────────────────────────

    def test_follow_mentor(self):
        self.me.create_or_update_profile("user1", "Alice Mentor")
        self.me.follow_mentor("user2", "user1")
        profile = self.me.get_profile("alice", viewer_id="user2")
        self.assertTrue(profile["is_following"])
        self.assertEqual(profile["followers_count"], 1)

    def test_unfollow_mentor(self):
        self.me.create_or_update_profile("user1", "Alice Mentor")
        self.me.follow_mentor("user2", "user1")
        self.me.unfollow_mentor("user2", "user1")
        profile = self.me.get_profile("alice", viewer_id="user2")
        self.assertFalse(profile["is_following"])
        self.assertEqual(profile["followers_count"], 0)

    def test_follow_self_raises(self):
        self.me.create_or_update_profile("user1", "Self")
        with self.assertRaises(ValueError):
            self.me.follow_mentor("user1", "user1")

    def test_follow_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.me.follow_mentor("user2", "user1")

    # ── Featured ──────────────────────────────────────────────

    def test_featured_mentors(self):
        self.me.create_or_update_profile("user1", "Top Mentor", markets="crypto")
        self.me.create_or_update_profile("user2", "Other Mentor", markets="bist")
        featured = self.me.featured_mentors(limit=5)
        self.assertEqual(len(featured), 2)

    # ── Mentor Detection ──────────────────────────────────────

    def test_is_mentor(self):
        self.assertFalse(self.me.is_mentor("user1"))
        self.me.create_or_update_profile("user1", "Mentor Now")
        self.assertTrue(self.me.is_mentor("user1"))

    def test_get_mentor_ids(self):
        self.me.create_or_update_profile("user1", "M1")
        self.me.create_or_update_profile("user2", "M2")
        ids = self.me.get_mentor_ids(["user1", "user2", "user3"])
        self.assertEqual(ids, {"user1", "user2"})

    # ── Stats ─────────────────────────────────────────────────

    def test_mentor_stats(self):
        self.me.create_or_update_profile("user1", "Stats Test", experience_years=3)
        stats = self.me.mentor_stats("user1")
        self.assertEqual(stats["experience_years"], 3)
        self.assertEqual(stats["followers_count"], 0)

    # ── Pricing ───────────────────────────────────────────────

    def test_pricing_paid(self):
        p = self.me.create_or_update_profile(
            "user1", "Paid Mentor",
            pricing_model="paid", monthly_price=99.0
        )
        self.assertEqual(p["pricing_model"], "paid")
        self.assertEqual(p["monthly_price"], 99.0)

    def test_pricing_subscription(self):
        p = self.me.create_or_update_profile(
            "user1", "Sub Mentor",
            pricing_model="subscription", monthly_price=49.0
        )
        self.assertEqual(p["pricing_model"], "subscription")

    def test_invalid_pricing_defaults_to_free(self):
        p = self.me.create_or_update_profile(
            "user1", "Bad Pricing", pricing_model="invalid"
        )
        self.assertEqual(p["pricing_model"], "free")

    # ── is_own / viewer ───────────────────────────────────────

    def test_profile_viewer_own(self):
        self.me.create_or_update_profile("user1", "Own Profile")
        # get_profile doesn't have is_own_profile, but is_following should be False for self
        profile = self.me.get_profile("alice", viewer_id="user1")
        self.assertFalse(profile["is_following"])

    def test_multiple_followers(self):
        self.me.create_or_update_profile("user1", "Popular")
        self.me.follow_mentor("user2", "user1")
        self.me.follow_mentor("user3", "user1")
        profile = self.me.get_profile("alice")
        self.assertEqual(profile["followers_count"], 2)


if __name__ == "__main__":
    unittest.main()
