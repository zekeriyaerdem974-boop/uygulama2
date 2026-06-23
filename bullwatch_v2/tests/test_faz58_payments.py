# -*- coding: utf-8 -*-
"""FAZ 58 — Monetization / Payment Integration / iyzico Tests.

Validates:
  01. File existence — payment_engine.py
  02. File existence — payment blueprint __init__.py
  03. File existence — payment blueprint routes.py
  04. File existence — pricing.html updated
  05. File existence — account_plan.html updated
  06. Engine — PLAN_PRICES constant
  07. Engine — Pro price is 149.99 TRY
  08. Engine — Pro+ price is 299.99 TRY
  09. Engine — PAYMENT_STATUSES constant
  10. Engine — get_plan_price returns dict
  11. Engine — get_plan_price returns None for invalid
  12. Engine — get_all_prices returns both plans
  13. Engine — create_checkout_session function exists
  14. Engine — verify_payment function exists
  15. Engine — activate_subscription function exists
  16. Engine — get_payment function exists
  17. Engine — get_user_payments function exists
  18. Engine — get_payment_by_token function exists
  19. Engine — _generate_demo_token helper
  20. Engine — _create_iyzico_checkout helper
  21. Engine — _verify_iyzico_payment helper
  22. Engine — _verify_demo_payment helper
  23. Engine — _complete_payment helper
  24. Engine — _fail_payment helper
  25. Engine — _store_callback_data helper
  26. Engine — _generate_iyzico_auth helper
  27. Engine — _update_payment_token helper
  28. Engine — _generate_random_string helper
  29. Engine — iyzico env vars defined
  30. Engine — CALLBACK_URL config
  31. Engine — payments table schema
  32. Engine — payments table indexes
  33. Demo — create_checkout_session returns demo URL
  34. Demo — demo token is 32 chars hex
  35. Demo — verify_payment auto-succeeds
  36. Demo — verify_payment activates subscription
  37. Demo — duplicate verify returns already_processed
  38. Demo — invalid token returns error
  39. Engine — get_payment returns None for missing
  40. Engine — get_user_payments empty for new user
  41. Engine — get_payment_by_token returns None for missing
  42. Engine — invalid plan_code rejected
  43. Subscription — valid_sources includes 'iyzico'
  44. Subscription — set_user_plan accepts source=iyzico
  45. Routes — '/api/payment/prices' endpoint defined
  46. Routes — '/api/payment/create' endpoint defined
  47. Routes — '/api/payment/callback' endpoint defined
  48. Routes — '/api/payment/verify' endpoint defined
  49. Routes — '/api/payment/status' endpoint defined
  50. Routes — '/api/payment/history' endpoint defined
  51. Routes — '/api/payment/demo-checkout' endpoint defined
  52. Routes — '/api/payment/demo-complete' endpoint defined
  53. Routes — _require_login helper defined
  54. API — GET /api/payment/prices returns plan data
  55. API — POST /api/payment/create requires login
  56. API — POST /api/payment/create requires plan_code
  57. API — POST /api/payment/create rejects invalid plan
  58. API — POST /api/payment/create success (demo)
  59. API — GET /api/payment/history requires login
  60. API — GET /api/payment/verify requires token
  61. API — payment status check requires login
  62. API — status check enforces ownership
  63. Template — pricing.html has ₺149.99 price
  64. Template — pricing.html has ₺299.99 price
  65. Template — pricing.html has buyPlan function
  66. Template — pricing.html has payment-banner
  67. Template — pricing.html has payment status JS
  68. Template — pricing.html no 'Yakında' buttons
  69. Template — pricing.html Güvenli Ödeme note
  70. Template — account_plan.html has payment history section
  71. Template — account_plan.html loads /api/payment/history
  72. Template — account_plan.html payment status display
  73. Blueprint — payment_bp registered in legacy_monolith
  74. Blueprint — payment_bp import in legacy_monolith
  75. Backward — subscription /api/subscription/me still works
"""
import inspect
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

# ── isolate test data dir ──
_TEST_DIR = os.path.join(_PROJECT, ".test_data_faz58")
os.makedirs(_TEST_DIR, exist_ok=True)

# ── patch DB paths BEFORE importing engines ──
import app.core.db_manager as _dm
_dm._DB_DIR = _TEST_DIR

import app.core.subscription_engine as se
se._DB_DIR = _TEST_DIR
se._DB_PATH = os.path.join(_TEST_DIR, "subscriptions.db")
se._USERS_DB = os.path.join(_TEST_DIR, "users.db")

import app.core.payment_engine as pe
pe._DB_DIR = _TEST_DIR
pe._DB_PATH = os.path.join(_TEST_DIR, "payments.db")

# Force re-init DB with patched paths
pe._init_db()
se._init_db()


def _create_test_users_db():
    """Create minimal users.db for testing."""
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
        ("payuser1", "pay1@test.com", "payuser1", "hash", "2025-01-01"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, username, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        ("payuser2", "pay2@test.com", "payuser2", "hash", "2025-01-01"),
    )
    conn.commit()
    conn.close()


_create_test_users_db()


def _get_flask_app():
    """Get Flask app for testing routes."""
    from legacy_monolith import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-faz58"
    return app


# ══════════════════════════════════════════════════════════════════════
# SECTION 1 — File Existence (tests 01-05)
# ══════════════════════════════════════════════════════════════════════

class TestFileExistence(unittest.TestCase):
    """Tests 01-05: All FAZ 58 files exist."""

    def test_01_payment_engine_exists(self):
        path = os.path.join(_PROJECT, "app", "core", "payment_engine.py")
        self.assertTrue(os.path.isfile(path), "payment_engine.py missing")

    def test_02_payment_blueprint_init_exists(self):
        path = os.path.join(_PROJECT, "app", "blueprints", "payment", "__init__.py")
        self.assertTrue(os.path.isfile(path), "payment blueprint __init__.py missing")

    def test_03_payment_routes_exists(self):
        path = os.path.join(_PROJECT, "app", "blueprints", "payment", "routes.py")
        self.assertTrue(os.path.isfile(path), "payment routes.py missing")

    def test_04_pricing_html_exists(self):
        path = os.path.join(_PROJECT, "templates", "pricing.html")
        self.assertTrue(os.path.isfile(path), "pricing.html missing")

    def test_05_account_plan_html_exists(self):
        path = os.path.join(_PROJECT, "templates", "account_plan.html")
        self.assertTrue(os.path.isfile(path), "account_plan.html missing")


# ══════════════════════════════════════════════════════════════════════
# SECTION 2 — Engine Constants & Pricing (tests 06-12)
# ══════════════════════════════════════════════════════════════════════

class TestEngineConstants(unittest.TestCase):
    """Tests 06-12: Engine constants and pricing."""

    def test_06_plan_prices_constant(self):
        self.assertIsInstance(pe.PLAN_PRICES, dict)
        self.assertIn("pro", pe.PLAN_PRICES)
        self.assertIn("pro_plus", pe.PLAN_PRICES)

    def test_07_pro_price_149_99(self):
        self.assertEqual(pe.PLAN_PRICES["pro"]["price"], 149.99)
        self.assertEqual(pe.PLAN_PRICES["pro"]["currency"], "TRY")

    def test_08_pro_plus_price_299_99(self):
        self.assertEqual(pe.PLAN_PRICES["pro_plus"]["price"], 299.99)
        self.assertEqual(pe.PLAN_PRICES["pro_plus"]["currency"], "TRY")

    def test_09_payment_statuses_constant(self):
        self.assertIsInstance(pe.PAYMENT_STATUSES, tuple)
        self.assertIn("pending", pe.PAYMENT_STATUSES)
        self.assertIn("success", pe.PAYMENT_STATUSES)
        self.assertIn("failed", pe.PAYMENT_STATUSES)

    def test_10_get_plan_price_pro(self):
        result = pe.get_plan_price("pro")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["price"], 149.99)
        self.assertEqual(result["code"], "pro")

    def test_11_get_plan_price_invalid(self):
        result = pe.get_plan_price("nonexistent")
        self.assertIsNone(result)

    def test_12_get_all_prices_both(self):
        result = pe.get_all_prices()
        self.assertIn("pro", result)
        self.assertIn("pro_plus", result)
        self.assertEqual(len(result), 2)


# ══════════════════════════════════════════════════════════════════════
# SECTION 3 — Engine Functions Exist (tests 13-28)
# ══════════════════════════════════════════════════════════════════════

class TestEngineFunctions(unittest.TestCase):
    """Tests 13-28: All required engine functions exist."""

    def test_13_create_checkout_session_exists(self):
        self.assertTrue(callable(pe.create_checkout_session))

    def test_14_verify_payment_exists(self):
        self.assertTrue(callable(pe.verify_payment))

    def test_15_activate_subscription_exists(self):
        self.assertTrue(callable(pe.activate_subscription))

    def test_16_get_payment_exists(self):
        self.assertTrue(callable(pe.get_payment))

    def test_17_get_user_payments_exists(self):
        self.assertTrue(callable(pe.get_user_payments))

    def test_18_get_payment_by_token_exists(self):
        self.assertTrue(callable(pe.get_payment_by_token))

    def test_19_generate_demo_token_exists(self):
        self.assertTrue(callable(pe._generate_demo_token))

    def test_20_create_iyzico_checkout_exists(self):
        self.assertTrue(callable(pe._create_iyzico_checkout))

    def test_21_verify_iyzico_payment_exists(self):
        self.assertTrue(callable(pe._verify_iyzico_payment))

    def test_22_verify_demo_payment_exists(self):
        self.assertTrue(callable(pe._verify_demo_payment))

    def test_23_complete_payment_exists(self):
        self.assertTrue(callable(pe._complete_payment))

    def test_24_fail_payment_exists(self):
        self.assertTrue(callable(pe._fail_payment))

    def test_25_store_callback_data_exists(self):
        self.assertTrue(callable(pe._store_callback_data))

    def test_26_generate_iyzico_auth_exists(self):
        self.assertTrue(callable(pe._generate_iyzico_auth))

    def test_27_update_payment_token_exists(self):
        self.assertTrue(callable(pe._update_payment_token))

    def test_28_generate_random_string_exists(self):
        self.assertTrue(callable(pe._generate_random_string))


# ══════════════════════════════════════════════════════════════════════
# SECTION 4 — Engine Config (tests 29-32)
# ══════════════════════════════════════════════════════════════════════

class TestEngineConfig(unittest.TestCase):
    """Tests 29-32: Configuration variables."""

    def test_29_iyzico_env_vars_defined(self):
        # Must have module-level variables
        self.assertTrue(hasattr(pe, "IYZICO_API_KEY"))
        self.assertTrue(hasattr(pe, "IYZICO_SECRET_KEY"))
        self.assertTrue(hasattr(pe, "IYZICO_BASE_URL"))

    def test_30_callback_url_config(self):
        self.assertTrue(hasattr(pe, "CALLBACK_URL"))
        self.assertIn("/api/payment/callback", pe.CALLBACK_URL)

    def test_31_payments_table_schema(self):
        conn = sqlite3.connect(pe._DB_PATH)
        cur = conn.execute("PRAGMA table_info(payments)")
        cols = {r[1] for r in cur.fetchall()}
        conn.close()
        expected = {
            "id", "user_id", "plan_code", "amount", "currency",
            "status", "provider", "provider_ref", "checkout_token",
            "callback_data", "error_message", "created_at", "completed_at",
        }
        self.assertTrue(expected.issubset(cols), f"Missing: {expected - cols}")

    def test_32_payments_table_indexes(self):
        conn = sqlite3.connect(pe._DB_PATH)
        cur = conn.execute("PRAGMA index_list(payments)")
        indexes = [r[1] for r in cur.fetchall()]
        conn.close()
        self.assertTrue(any("user" in i for i in indexes))
        self.assertTrue(any("token" in i for i in indexes))


# ══════════════════════════════════════════════════════════════════════
# SECTION 5 — Demo Mode Flow (tests 33-41)
# ══════════════════════════════════════════════════════════════════════

class TestDemoMode(unittest.TestCase):
    """Tests 33-41: Demo mode payment flow."""

    def test_33_create_checkout_returns_demo_url(self):
        result = pe.create_checkout_session("payuser1", "pro", "a@b.com")
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "demo")
        self.assertIn("/api/payment/demo-checkout", result["checkout_url"])
        self.assertIn("payment_id", result)

    def test_34_demo_token_is_32_hex(self):
        token = pe._generate_demo_token("test123")
        self.assertEqual(len(token), 32)
        # Valid hex chars
        int(token, 16)

    def test_35_verify_payment_auto_succeeds_demo(self):
        result = pe.create_checkout_session("payuser1", "pro", "a@b.com")
        token = result["checkout_token"]
        verify = pe.verify_payment(token)
        self.assertTrue(verify["ok"])
        self.assertEqual(verify["mode"], "demo")

    def test_36_verify_activates_subscription(self):
        result = pe.create_checkout_session("payuser1", "pro_plus", "a@b.com")
        token = result["checkout_token"]
        verify = pe.verify_payment(token)
        self.assertTrue(verify["ok"])
        # Check subscription was activated
        sub = se.get_user_plan("payuser1")
        self.assertIn(sub.get("plan_code"), ("pro_plus",))

    def test_37_duplicate_verify_already_processed(self):
        result = pe.create_checkout_session("payuser2", "pro", "b@b.com")
        token = result["checkout_token"]
        pe.verify_payment(token)
        verify2 = pe.verify_payment(token)
        self.assertTrue(verify2["ok"])
        self.assertTrue(verify2.get("already_processed"))

    def test_38_invalid_token_error(self):
        verify = pe.verify_payment("nonexistent_token_xyz")
        self.assertFalse(verify["ok"])

    def test_39_get_payment_missing(self):
        result = pe.get_payment("nonexistent_id")
        self.assertIsNone(result)

    def test_40_get_user_payments_empty(self):
        result = pe.get_user_payments("no_such_user_xyz")
        self.assertEqual(result, [])

    def test_41_get_payment_by_token_missing(self):
        result = pe.get_payment_by_token("no_such_token")
        self.assertIsNone(result)


# ══════════════════════════════════════════════════════════════════════
# SECTION 6 — Engine Validation (tests 42-44)
# ══════════════════════════════════════════════════════════════════════

class TestEngineValidation(unittest.TestCase):
    """Tests 42-44: Input validation."""

    def test_42_invalid_plan_code_rejected(self):
        result = pe.create_checkout_session("payuser1", "invalid_plan", "a@b.com")
        self.assertFalse(result["ok"])
        self.assertIn("Geçersiz", result["error"])

    def test_43_subscription_valid_sources_includes_iyzico(self):
        src = inspect.getsource(se.set_user_plan)
        self.assertIn('"iyzico"', src)

    def test_44_set_user_plan_accepts_iyzico(self):
        result = se.set_user_plan("payuser2", "pro", source="iyzico")
        self.assertTrue(result["ok"])


# ══════════════════════════════════════════════════════════════════════
# SECTION 7 — Routes Source Analysis (tests 45-53)
# ══════════════════════════════════════════════════════════════════════

class TestRoutesSource(unittest.TestCase):
    """Tests 45-53: Route definitions in source."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "app", "blueprints", "payment", "routes.py")
        with open(path, "r", encoding="utf-8") as f:
            cls.src = f.read()

    def test_45_prices_endpoint(self):
        self.assertIn("/api/payment/prices", self.src)

    def test_46_create_endpoint(self):
        self.assertIn("/api/payment/create", self.src)

    def test_47_callback_endpoint(self):
        self.assertIn("/api/payment/callback", self.src)

    def test_48_verify_endpoint(self):
        self.assertIn("/api/payment/verify", self.src)

    def test_49_status_endpoint(self):
        self.assertIn("/api/payment/status", self.src)

    def test_50_history_endpoint(self):
        self.assertIn("/api/payment/history", self.src)

    def test_51_demo_checkout_endpoint(self):
        self.assertIn("/api/payment/demo-checkout", self.src)

    def test_52_demo_complete_endpoint(self):
        self.assertIn("/api/payment/demo-complete", self.src)

    def test_53_require_login_helper(self):
        self.assertIn("def _require_login", self.src)


# ══════════════════════════════════════════════════════════════════════
# SECTION 8 — API Integration (tests 54-62)
# ══════════════════════════════════════════════════════════════════════

class TestAPIIntegration(unittest.TestCase):
    """Tests 54-62: API endpoint tests via Flask test client."""

    @classmethod
    def setUpClass(cls):
        cls.app = _get_flask_app()

    def test_54_prices_returns_plan_data(self):
        with self.app.test_client() as c:
            r = c.get("/api/payment/prices")
            self.assertEqual(r.status_code, 200)
            d = r.get_json()
            self.assertTrue(d["ok"])
            self.assertIn("pro", d["prices"])
            self.assertIn("pro_plus", d["prices"])

    def test_55_create_requires_login(self):
        with self.app.test_client() as c:
            r = c.post("/api/payment/create",
                       json={"plan_code": "pro"})
            self.assertEqual(r.status_code, 401)

    def test_56_create_requires_plan_code(self):
        with self.app.test_client() as c:
            with c.session_transaction() as s:
                s["user_id"] = "payuser1"
            r = c.post("/api/payment/create", json={})
            self.assertEqual(r.status_code, 400)

    def test_57_create_rejects_invalid_plan(self):
        with self.app.test_client() as c:
            with c.session_transaction() as s:
                s["user_id"] = "payuser1"
            r = c.post("/api/payment/create",
                       json={"plan_code": "platinum"})
            self.assertEqual(r.status_code, 400)

    def test_58_create_success_demo(self):
        with self.app.test_client() as c:
            with c.session_transaction() as s:
                s["user_id"] = "payuser1"
                s["email"] = "pay1@test.com"
                s["username"] = "payuser1"
            r = c.post("/api/payment/create",
                       json={"plan_code": "pro"})
            self.assertEqual(r.status_code, 200)
            d = r.get_json()
            self.assertTrue(d["ok"])
            self.assertIn("checkout_url", d)
            self.assertEqual(d["mode"], "demo")

    def test_59_history_requires_login(self):
        with self.app.test_client() as c:
            r = c.get("/api/payment/history")
            self.assertEqual(r.status_code, 401)

    def test_60_verify_requires_token(self):
        with self.app.test_client() as c:
            r = c.get("/api/payment/verify")
            d = r.get_json()
            self.assertFalse(d["ok"])

    def test_61_status_requires_login(self):
        with self.app.test_client() as c:
            r = c.get("/api/payment/status/some-id")
            self.assertEqual(r.status_code, 401)

    def test_62_status_enforces_ownership(self):
        # Create a payment for payuser1
        result = pe.create_checkout_session("payuser1", "pro", "x@x.com")
        pid = result["payment_id"]
        with self.app.test_client() as c:
            # Login as payuser2
            with c.session_transaction() as s:
                s["user_id"] = "payuser2"
            r = c.get(f"/api/payment/status/{pid}")
            self.assertEqual(r.status_code, 403)


# ══════════════════════════════════════════════════════════════════════
# SECTION 9 — Template Analysis (tests 63-72)
# ══════════════════════════════════════════════════════════════════════

class TestTemplates(unittest.TestCase):
    """Tests 63-72: Template content checks."""

    @classmethod
    def setUpClass(cls):
        pricing_path = os.path.join(_PROJECT, "templates", "pricing.html")
        with open(pricing_path, "r", encoding="utf-8") as f:
            cls.pricing_src = f.read()
        account_path = os.path.join(_PROJECT, "templates", "account_plan.html")
        with open(account_path, "r", encoding="utf-8") as f:
            cls.account_src = f.read()

    def test_63_pricing_has_149_99(self):
        self.assertIn("149", self.pricing_src)
        self.assertIn(".99", self.pricing_src)

    def test_64_pricing_has_299_99(self):
        self.assertIn("299", self.pricing_src)

    def test_65_pricing_has_buyPlan_function(self):
        self.assertIn("function buyPlan", self.pricing_src)

    def test_66_pricing_has_payment_banner(self):
        self.assertIn("payment-banner", self.pricing_src)

    def test_67_pricing_has_payment_status_js(self):
        self.assertIn("paymentStatus", self.pricing_src)
        self.assertIn("'success'", self.pricing_src)
        self.assertIn("'failed'", self.pricing_src)

    def test_68_pricing_no_yakinda_buttons(self):
        # Buttons should no longer say "Yakında" — they should have real text
        src_lower = self.pricing_src.lower()
        # Count occurrences of "yakında" — should not appear in button elements
        # Note: we allow "Yakında aktif olacak" to be absent
        self.assertNotIn('>Yakında<', self.pricing_src)

    def test_69_pricing_guvenli_odeme_note(self):
        self.assertIn("Güvenli Ödeme", self.pricing_src)

    def test_70_account_payment_history_section(self):
        self.assertIn("payment-history-section", self.account_src)
        self.assertIn("Ödeme Geçmişi", self.account_src)

    def test_71_account_loads_payment_history(self):
        self.assertIn("/api/payment/history", self.account_src)

    def test_72_account_payment_status_display(self):
        self.assertIn("Tamamlandı", self.account_src)
        self.assertIn("Başarısız", self.account_src)


# ══════════════════════════════════════════════════════════════════════
# SECTION 10 — Blueprint Registration & Backward Compat (tests 73-75)
# ══════════════════════════════════════════════════════════════════════

class TestBlueprintAndCompat(unittest.TestCase):
    """Tests 73-75: Blueprint registration and backward compatibility."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "legacy_monolith.py")
        with open(path, "r", encoding="utf-8") as f:
            cls.monolith_src = f.read()

    def test_73_payment_bp_registered(self):
        self.assertIn("register_blueprint(payment_bp)", self.monolith_src)

    def test_74_payment_bp_import(self):
        self.assertIn("from app.blueprints.payment import payment_bp",
                       self.monolith_src)

    def test_75_subscription_me_still_works(self):
        app = _get_flask_app()
        with app.test_client() as c:
            with c.session_transaction() as s:
                s["user_id"] = "payuser1"
            r = c.get("/api/subscription/me")
            self.assertEqual(r.status_code, 200)
            d = r.get_json()
            self.assertTrue(d.get("ok"))


# ══════════════════════════════════════════════════════════════════════
# CLEANUP
# ══════════════════════════════════════════════════════════════════════

@classmethod
def _cleanup(cls):
    if os.path.exists(_TEST_DIR):
        shutil.rmtree(_TEST_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
