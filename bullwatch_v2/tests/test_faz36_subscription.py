# -*- coding: utf-8 -*-
"""FAZ 36 — Subscription Logic / Access Control tests.

Covers:
  01-06  Plan definitions & queries
  07-12  User subscription management
  13-18  Feature gating (boolean features)
  19-24  Limit-based gating (alerts, strategies)
  25-30  Copilot usage tracking & limits
  31-36  Enforce limit (universal)
  37-42  Edge cases & plan switching
  43-45  Usage queries
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

# ── project root on sys.path ──
_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

# ── isolate test data ──
_TEST_DIR = os.path.join(_PROJECT, ".test_data_faz36")
os.makedirs(_TEST_DIR, exist_ok=True)

import app.core.subscription_engine as se

import app.core.db_manager as _dm
_dm._DB_DIR = _TEST_DIR
se._DB_DIR = _TEST_DIR
se._DB_PATH = os.path.join(_TEST_DIR, "subscriptions.db")
se._USERS_DB = os.path.join(_TEST_DIR, "users.db")


def _create_test_users_db():
    """Create a minimal users.db for testing."""
    conn = sqlite3.connect(se._USERS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT,
            username TEXT,
            password_hash TEXT,
            created_at TEXT,
            plan TEXT DEFAULT 'free',
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        ("user1", "user1@test.com", "testuser1", "hash", "2025-01-01"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        ("user2", "user2@test.com", "testuser2", "hash", "2025-01-01"),
    )
    conn.commit()
    conn.close()


def _reset_db():
    """Reset test databases."""
    for f in os.listdir(_TEST_DIR):
        fp = os.path.join(_TEST_DIR, f)
        if os.path.isfile(fp):
            os.remove(fp)
    _create_test_users_db()
    se._init_db()


class TestFAZ36Plans(unittest.TestCase):
    """01-06: Plan definitions and queries."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_01_plans_defined(self):
        """Three plans exist: free, pro, pro_plus."""
        self.assertIn("free", se.PLANS)
        self.assertIn("pro", se.PLANS)
        self.assertIn("pro_plus", se.PLANS)

    def test_02_get_plan_free(self):
        """Free plan has correct limits."""
        p = se.get_plan("free")
        self.assertEqual(p["max_alerts"], 5)
        self.assertEqual(p["max_active_strategies"], 1)
        self.assertEqual(p["max_saved_strategies"], 3)
        self.assertFalse(p["can_use_premium_courses"])
        self.assertFalse(p["can_use_advanced_screener"])

    def test_03_get_plan_pro(self):
        """Pro plan has correct limits."""
        p = se.get_plan("pro")
        self.assertEqual(p["max_alerts"], 999)
        self.assertEqual(p["max_active_strategies"], 10)
        self.assertTrue(p["can_use_premium_courses"])
        self.assertTrue(p["can_use_advanced_screener"])

    def test_04_get_plan_pro_plus(self):
        """Pro+ plan has correct limits."""
        p = se.get_plan("pro_plus")
        self.assertEqual(p["max_active_strategies"], 999)
        self.assertTrue(p["can_use_premium_courses"])
        self.assertTrue(p["can_use_advanced_copilot"])

    def test_05_get_all_plans(self):
        """get_all_plans returns 3 plans from DB."""
        plans = se.get_all_plans()
        self.assertEqual(len(plans), 3)
        codes = [p["code"] for p in plans]
        self.assertIn("free", codes)
        self.assertIn("pro", codes)
        self.assertIn("pro_plus", codes)

    def test_06_get_plan_limits(self):
        """get_plan_limits returns limit dict."""
        limits = se.get_plan_limits("pro")
        self.assertIn("max_alerts", limits)
        self.assertIn("can_use_premium_courses", limits)
        self.assertEqual(limits["max_alerts"], 999)

        none_limits = se.get_plan_limits("nonexistent")
        self.assertIsNone(none_limits)


class TestFAZ36UserSubscriptions(unittest.TestCase):
    """07-12: User subscription management."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_07_default_free_plan(self):
        """New user defaults to free plan."""
        plan = se.get_user_plan("user1")
        self.assertEqual(plan["plan_code"], "free")
        self.assertEqual(plan["plan_name"], "Free")
        self.assertEqual(plan["status"], "active")

    def test_08_set_plan_pro(self):
        """Set user plan to pro."""
        result = se.set_user_plan("user1", "pro", "admin")
        self.assertTrue(result["ok"])
        self.assertEqual(result["subscription"]["plan_code"], "pro")
        self.assertEqual(result["subscription"]["source"], "admin")

    def test_09_get_plan_after_change(self):
        """User plan reflects change."""
        plan = se.get_user_plan("user1")
        self.assertEqual(plan["plan_code"], "pro")
        self.assertEqual(plan["plan_name"], "Pro")

    def test_10_set_plan_pro_plus(self):
        """Upgrade user to pro_plus."""
        result = se.set_user_plan("user1", "pro_plus", "manual")
        self.assertTrue(result["ok"])
        plan = se.get_user_plan("user1")
        self.assertEqual(plan["plan_code"], "pro_plus")

    def test_11_invalid_plan(self):
        """Setting invalid plan returns error."""
        result = se.set_user_plan("user1", "enterprise")
        self.assertFalse(result["ok"])
        self.assertIn("Geçersiz", result["error"])

    def test_12_subscription_info(self):
        """get_subscription_info returns history."""
        info = se.get_subscription_info("user1")
        self.assertIn("current", info)
        self.assertIn("history", info)
        self.assertGreater(len(info["history"]), 0)


class TestFAZ36FeatureGating(unittest.TestCase):
    """13-18: Feature gating (boolean features)."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_13_free_no_premium_courses(self):
        """Free user cannot access premium courses."""
        result = se.can_use_feature("user1", "premium_courses")
        self.assertFalse(result["allowed"])
        self.assertIn("Pro", result["reason"])

    def test_14_free_no_advanced_screener(self):
        """Free user cannot use advanced screener."""
        result = se.can_use_feature("user1", "advanced_screener")
        self.assertFalse(result["allowed"])

    def test_15_free_no_advanced_backtest(self):
        """Free user cannot use advanced backtest."""
        result = se.can_use_feature("user1", "advanced_backtest")
        self.assertFalse(result["allowed"])

    def test_16_pro_has_premium_courses(self):
        """Pro user can access premium courses."""
        se.set_user_plan("user2", "pro", "admin")
        result = se.can_use_feature("user2", "premium_courses")
        self.assertTrue(result["allowed"])

    def test_17_pro_has_advanced_screener(self):
        """Pro user can use advanced screener."""
        result = se.can_use_feature("user2", "advanced_screener")
        self.assertTrue(result["allowed"])

    def test_18_can_access_premium_helpers(self):
        """Helper functions work correctly."""
        r1 = se.can_access_premium_course("user1")
        self.assertFalse(r1["allowed"])
        r2 = se.can_access_premium_room("user2")
        self.assertTrue(r2["allowed"])
        r3 = se.can_access_premium_strategy("user1")
        self.assertFalse(r3["allowed"])
        r4 = se.can_use_advanced_screener("user2")
        self.assertTrue(r4["allowed"])
        r5 = se.can_use_advanced_backtest("user1")
        self.assertFalse(r5["allowed"])
        r6 = se.can_use_advanced_copilot("user2")
        self.assertTrue(r6["allowed"])


class TestFAZ36LimitGating(unittest.TestCase):
    """19-24: Limit-based gating."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_19_free_can_create_alert(self):
        """Free user (0 alerts) can create alert."""
        result = se.can_create_alert("user1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["max"], 5)

    def test_20_free_can_activate_strategy(self):
        """Free user (0 active) can activate strategy."""
        result = se.can_activate_strategy("user1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["max"], 1)

    def test_21_free_can_save_strategy(self):
        """Free user (0 saved) can save strategy."""
        result = se.can_save_strategy("user1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["max"], 3)

    def test_22_pro_higher_limits(self):
        """Pro user has higher limits."""
        se.set_user_plan("user2", "pro", "admin")
        r = se.can_create_alert("user2")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["max"], 999)

    def test_23_pro_higher_strategy_limits(self):
        """Pro user can activate 10 strategies."""
        r = se.can_activate_strategy("user2")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["max"], 10)

    def test_24_pro_higher_saved_limits(self):
        """Pro user can save 20 strategies."""
        r = se.can_save_strategy("user2")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["max"], 20)


class TestFAZ36CopilotUsage(unittest.TestCase):
    """25-30: Copilot usage tracking & limits."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_25_initial_copilot_check(self):
        """Free user starts with 0 usage."""
        result = se._check_copilot_limit("user1")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["current"], 0)
        self.assertEqual(result["max"], 10)

    def test_26_increment_copilot(self):
        """Increment copilot usage."""
        result = se.increment_copilot_usage("user1")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["limit"], 10)
        self.assertEqual(result["remaining"], 9)

    def test_27_multiple_increments(self):
        """Multiple increments accumulate."""
        for _ in range(8):
            se.increment_copilot_usage("user1")
        result = se.increment_copilot_usage("user1")
        self.assertEqual(result["count"], 10)
        self.assertEqual(result["remaining"], 0)

    def test_28_copilot_limit_reached(self):
        """After 10 uses, limit is reached."""
        result = se._check_copilot_limit("user1")
        self.assertFalse(result["allowed"])
        self.assertIn("limitine", result["reason"])

    def test_29_pro_higher_copilot_limit(self):
        """Pro user has 100/day copilot limit."""
        se.set_user_plan("user2", "pro", "admin")
        result = se._check_copilot_limit("user2")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["max"], 100)

    def test_30_pro_plus_copilot(self):
        """Pro+ user has 999/day copilot limit."""
        se.set_user_plan("user2", "pro_plus", "admin")
        result = se._check_copilot_limit("user2")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["max"], 999)


class TestFAZ36EnforceLimit(unittest.TestCase):
    """31-36: Universal enforce_limit function."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_31_enforce_create_alert(self):
        """enforce_limit('create_alert') works."""
        result = se.enforce_limit("user1", "create_alert")
        self.assertTrue(result["allowed"])

    def test_32_enforce_activate_strategy(self):
        """enforce_limit('activate_strategy') works."""
        result = se.enforce_limit("user1", "activate_strategy")
        self.assertTrue(result["allowed"])

    def test_33_enforce_save_strategy(self):
        """enforce_limit('save_strategy') works."""
        result = se.enforce_limit("user1", "save_strategy")
        self.assertTrue(result["allowed"])

    def test_34_enforce_copilot(self):
        """enforce_limit('copilot') works."""
        result = se.enforce_limit("user1", "copilot")
        self.assertTrue(result["allowed"])

    def test_35_enforce_premium_courses(self):
        """enforce_limit('premium_courses') works for free user."""
        result = se.enforce_limit("user1", "premium_courses")
        self.assertFalse(result["allowed"])

    def test_36_enforce_unknown(self):
        """enforce_limit with unknown feature returns allowed."""
        result = se.enforce_limit("user1", "nonexistent_feature")
        self.assertTrue(result["allowed"])


class TestFAZ36PlanSwitching(unittest.TestCase):
    """37-42: Plan switching and edge cases."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_37_downgrade_to_free(self):
        """User can downgrade from Pro to Free."""
        se.set_user_plan("user1", "pro", "admin")
        plan = se.get_user_plan("user1")
        self.assertEqual(plan["plan_code"], "pro")

        se.set_user_plan("user1", "free", "admin")
        plan = se.get_user_plan("user1")
        self.assertEqual(plan["plan_code"], "free")

    def test_38_upgrade_path(self):
        """Full upgrade path: free → pro → pro_plus."""
        se.set_user_plan("user1", "free", "admin")
        se.set_user_plan("user1", "pro", "admin")
        se.set_user_plan("user1", "pro_plus", "admin")

        plan = se.get_user_plan("user1")
        self.assertEqual(plan["plan_code"], "pro_plus")

    def test_39_history_tracked(self):
        """Subscription history tracks all changes."""
        info = se.get_subscription_info("user1")
        self.assertGreater(len(info["history"]), 2)

    def test_40_old_subs_expired(self):
        """Old subscriptions are marked as expired."""
        info = se.get_subscription_info("user1")
        expired = [h for h in info["history"] if h["status"] == "expired"]
        self.assertGreater(len(expired), 0)

    def test_41_sync_to_users_db(self):
        """Plan change syncs to users.db."""
        se.set_user_plan("user2", "pro", "admin")
        conn = sqlite3.connect(se._USERS_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT plan FROM users WHERE id = 'user2'").fetchone()
        conn.close()
        self.assertEqual(row["plan"], "pro")

    def test_42_source_validation(self):
        """Invalid source defaults to manual."""
        result = se.set_user_plan("user1", "free", "invalid_source")
        self.assertTrue(result["ok"])
        self.assertEqual(result["subscription"]["source"], "manual")


class TestFAZ36Usage(unittest.TestCase):
    """43-45: Usage queries."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_43_get_usage(self):
        """get_usage returns structured data."""
        usage = se.get_usage("user1")
        self.assertIn("plan_code", usage)
        self.assertIn("alerts", usage)
        self.assertIn("active_strategies", usage)
        self.assertIn("saved_strategies", usage)
        self.assertIn("copilot", usage)
        self.assertEqual(usage["plan_code"], "free")

    def test_44_usage_has_used_and_max(self):
        """Usage items have used/max fields."""
        usage = se.get_usage("user1")
        self.assertIn("used", usage["alerts"])
        self.assertIn("max", usage["alerts"])

    def test_45_usage_reflects_plan(self):
        """Usage max values reflect the plan."""
        se.set_user_plan("user1", "pro", "admin")
        usage = se.get_usage("user1")
        self.assertEqual(usage["plan_code"], "pro")
        self.assertEqual(usage["alerts"]["max"], 999)
        self.assertEqual(usage["active_strategies"]["max"], 10)


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
