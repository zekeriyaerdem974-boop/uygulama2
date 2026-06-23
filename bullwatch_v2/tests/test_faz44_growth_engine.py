"""
ZKR Analiz Pro — FAZ 44 Growth Engine / Invite / Referral Tests
Covers: referral_engine, share_engine, invite blueprint routes,
        fraud detection, leaderboard, rewards, copilot endpoint,
        share generation, template/layout integration, compliance.
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import requests

BASE_URL = "http://127.0.0.1:34000"


def _read(rel_path):
    with open(os.path.join(BASE, rel_path), "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════
# 1. Referral Engine — Core Module
# ═══════════════════════════════════════════════════════════════
class TestReferralEngineModule(unittest.TestCase):
    """referral_engine.py file structure and module-level checks."""

    def setUp(self):
        self.src = _read("app/core/referral_engine.py")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/core/referral_engine.py")))

    def test_has_generate_invite_code(self):
        self.assertIn("def generate_invite_code(", self.src)

    def test_has_register_referral(self):
        self.assertIn("def register_referral(", self.src)

    def test_has_get_referral_stats(self):
        self.assertIn("def get_referral_stats(", self.src)

    def test_has_calculate_referral_rewards(self):
        self.assertIn("def calculate_referral_rewards(", self.src)

    def test_has_get_invite_code(self):
        self.assertIn("def get_invite_code(", self.src)

    def test_has_validate_invite_code(self):
        self.assertIn("def validate_invite_code(", self.src)

    def test_has_get_top_inviters(self):
        self.assertIn("def get_top_inviters(", self.src)

    def test_has_get_recent_referrals(self):
        self.assertIn("def get_recent_referrals(", self.src)

    def test_has_get_growth_stats(self):
        self.assertIn("def get_growth_stats(", self.src)

    def test_has_fraud_detection(self):
        self.assertIn("self-referral", self.src.lower())

    def test_has_ip_duplicate_check(self):
        self.assertIn("ip_hash", self.src)

    def test_has_reward_tiers(self):
        self.assertIn("REWARD_TIERS", self.src)

    def test_has_banned_words(self):
        self.assertIn("BANNED_WORDS", self.src)

    def test_has_sanitize_text(self):
        self.assertIn("_sanitize_text", self.src)

    def test_code_prefix_constant(self):
        self.assertIn('CODE_PREFIX = "BW"', self.src)

    def test_db_path(self):
        self.assertIn("referral_engine.db", self.src)

    def test_wal_mode(self):
        dm_src = open(os.path.join(BASE, "app/core/db_manager.py")).read()
        self.assertIn("journal_mode", dm_src)
        self.assertIn("WAL", dm_src)

    def test_thread_lock(self):
        self.assertIn("threading.Lock()", self.src)


# ═══════════════════════════════════════════════════════════════
# 2. Referral Engine — Functional Tests
# ═══════════════════════════════════════════════════════════════
class TestReferralEngineFunctional(unittest.TestCase):
    """Functional tests using the actual engine with temp DB."""

    @classmethod
    def setUpClass(cls):
        import app.core.referral_engine as eng
        import app.core.db_manager as _dm
        cls._orig_db_path = eng._DB_PATH
        cls._orig_db_dir = _dm._DB_DIR
        cls._tmpdir = tempfile.mkdtemp()
        eng._DB_PATH = os.path.join(cls._tmpdir, "test_referral.db")
        _dm._DB_DIR = cls._tmpdir
        cls.eng = eng

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        cls.eng._DB_PATH = cls._orig_db_path
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_generate_code_returns_string(self):
        code = self.eng.generate_invite_code("test_user_1")
        self.assertIsInstance(code, str)
        self.assertTrue(len(code) > 0)

    def test_code_starts_with_prefix(self):
        code = self.eng.generate_invite_code("test_user_2")
        self.assertTrue(code.startswith("BW"))

    def test_code_length(self):
        code = self.eng.generate_invite_code("test_user_3")
        self.assertEqual(len(code), 2 + self.eng.CODE_LENGTH)  # BW + 6

    def test_get_invite_code_creates_if_missing(self):
        code = self.eng.get_invite_code("test_user_new_1")
        self.assertIsNotNone(code)
        self.assertTrue(code.startswith("BW"))

    def test_get_invite_code_returns_same(self):
        c1 = self.eng.get_invite_code("test_user_same_1")
        c2 = self.eng.get_invite_code("test_user_same_1")
        self.assertEqual(c1, c2)

    def test_validate_code_valid(self):
        code = self.eng.generate_invite_code("validate_user_1")
        result = self.eng.validate_invite_code(code)
        self.assertIsNotNone(result)
        self.assertEqual(result["code"], code)
        self.assertEqual(result["user_id"], "validate_user_1")

    def test_validate_code_invalid(self):
        result = self.eng.validate_invite_code("INVALID_CODE_XYZ")
        self.assertIsNone(result)

    def test_validate_empty_code(self):
        result = self.eng.validate_invite_code("")
        self.assertIsNone(result)

    def test_generate_empty_user(self):
        code = self.eng.generate_invite_code("")
        self.assertEqual(code, "")

    def test_register_referral_success(self):
        code = self.eng.generate_invite_code("referrer_A")
        result = self.eng.register_referral(code, "new_user_A", "1.2.3.4")
        self.assertIsNotNone(result)
        self.assertEqual(result["referrer_id"], "referrer_A")
        self.assertEqual(result["referred_id"], "new_user_A")

    def test_register_self_referral_blocked(self):
        code = self.eng.generate_invite_code("self_ref_user")
        result = self.eng.register_referral(code, "self_ref_user", "5.6.7.8")
        self.assertIsNone(result)

    def test_register_duplicate_referred_blocked(self):
        code = self.eng.generate_invite_code("dup_referrer")
        self.eng.register_referral(code, "dup_referred_1", "10.0.0.1")
        result = self.eng.register_referral(code, "dup_referred_1", "10.0.0.2")
        self.assertIsNone(result)

    def test_register_invalid_code(self):
        result = self.eng.register_referral("FAKECODE", "new_user_B", "1.1.1.1")
        self.assertIsNone(result)

    def test_ip_fraud_detection(self):
        code = self.eng.generate_invite_code("ip_fraud_user")
        # Register 5 referrals from same IP — should succeed
        for i in range(5):
            self.eng.register_referral(code, f"ip_victim_{i}", "192.168.1.100")
        # 6th should be blocked
        result = self.eng.register_referral(code, "ip_victim_6", "192.168.1.100")
        self.assertIsNone(result)

    def test_get_referral_stats(self):
        code = self.eng.generate_invite_code("stats_user")
        self.eng.register_referral(code, "stats_ref_1", "10.10.10.1")
        stats = self.eng.get_referral_stats("stats_user")
        self.assertIn("referrals", stats)
        self.assertGreaterEqual(stats["referrals"], 1)

    def test_get_stats_empty_user(self):
        stats = self.eng.get_referral_stats("")
        self.assertEqual(stats["referrals"], 0)

    def test_calculate_rewards_empty(self):
        rewards = self.eng.calculate_referral_rewards("nonexistent_user_rewards")
        self.assertIsInstance(rewards, list)

    def test_top_inviters_returns_list(self):
        data = self.eng.get_top_inviters(5)
        self.assertIsInstance(data, list)

    def test_recent_referrals_returns_list(self):
        data = self.eng.get_recent_referrals(5)
        self.assertIsInstance(data, list)

    def test_growth_stats_returns_dict(self):
        data = self.eng.get_growth_stats()
        self.assertIsInstance(data, dict)
        self.assertIn("total_referrals", data)
        self.assertIn("total_codes", data)

    def test_reward_tier_structure(self):
        for tier in self.eng.REWARD_TIERS:
            self.assertEqual(len(tier), 4)
            self.assertIsInstance(tier[0], int)
            self.assertIsInstance(tier[1], str)

    def test_max_codes_per_user(self):
        uid = "max_codes_user"
        codes = set()
        for _ in range(5):
            c = self.eng.generate_invite_code(uid)
            codes.add(c)
        self.assertLessEqual(len(codes), self.eng.MAX_CODES_PER_USER)


# ═══════════════════════════════════════════════════════════════
# 3. Share Engine — Module
# ═══════════════════════════════════════════════════════════════
class TestShareEngineModule(unittest.TestCase):
    """share_engine.py file structure checks."""

    def setUp(self):
        self.src = _read("app/core/share_engine.py")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/core/share_engine.py")))

    def test_has_generate_share_url(self):
        self.assertIn("def generate_share_url(", self.src)

    def test_has_generate_share_card(self):
        self.assertIn("def generate_share_card(", self.src)

    def test_has_get_share_stats(self):
        self.assertIn("def get_share_stats(", self.src)

    def test_has_track_share_click(self):
        self.assertIn("def track_share_click(", self.src)

    def test_has_get_share_by_id(self):
        self.assertIn("def get_share_by_id(", self.src)

    def test_has_content_types(self):
        self.assertIn("CONTENT_TYPES", self.src)

    def test_content_type_analysis(self):
        self.assertIn('"analysis"', self.src)

    def test_content_type_portfolio(self):
        self.assertIn('"portfolio"', self.src)

    def test_content_type_mentor(self):
        self.assertIn('"mentor"', self.src)

    def test_content_type_strategy(self):
        self.assertIn('"strategy"', self.src)

    def test_db_path(self):
        self.assertIn("share_engine.db", self.src)

    def test_has_banned_words(self):
        self.assertIn("BANNED_WORDS", self.src)


# ═══════════════════════════════════════════════════════════════
# 4. Share Engine — Functional Tests
# ═══════════════════════════════════════════════════════════════
class TestShareEngineFunctional(unittest.TestCase):
    """Functional tests using actual share engine with temp DB."""

    @classmethod
    def setUpClass(cls):
        import app.core.share_engine as eng
        import app.core.db_manager as _dm
        cls._orig_db_path = eng._DB_PATH
        cls._orig_db_dir = _dm._DB_DIR
        cls._tmpdir = tempfile.mkdtemp()
        eng._DB_PATH = os.path.join(cls._tmpdir, "test_share.db")
        _dm._DB_DIR = cls._tmpdir
        cls.eng = eng

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        cls.eng._DB_PATH = cls._orig_db_path
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_generate_share_url(self):
        url = self.eng.generate_share_url("analysis", "btc_1", "user1", "BTC Analysis", "description")
        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith("/share/"))

    def test_generate_share_card(self):
        self.eng.generate_share_url("analysis", "btc_2", "user2", "Test", "Desc")
        card = self.eng.generate_share_card("analysis", "btc_2", "user2")
        self.assertIsInstance(card, dict)
        self.assertIn("title", card)
        self.assertIn("icon", card)
        self.assertIn("platforms", card)

    def test_share_card_has_platforms(self):
        self.eng.generate_share_url("portfolio", "p1", "user3", "Portfolio Snapshot", "")
        card = self.eng.generate_share_card("portfolio", "p1", "user3")
        platforms = card.get("platforms", {})
        self.assertIn("twitter", platforms)
        self.assertIn("telegram", platforms)
        self.assertIn("whatsapp", platforms)

    def test_track_share_click(self):
        url = self.eng.generate_share_url("analysis", "click_test", "user4", "Title", "")
        share_id = url.split("/share/")[-1]
        result = self.eng.track_share_click(share_id)
        self.assertTrue(result)

    def test_get_share_by_id(self):
        url = self.eng.generate_share_url("mentor", "m1", "user5", "Mentor", "Desc")
        share_id = url.split("/share/")[-1]
        data = self.eng.get_share_by_id(share_id)
        self.assertIsNotNone(data)
        self.assertEqual(data["content_type"], "mentor")

    def test_get_nonexistent_share(self):
        data = self.eng.get_share_by_id("nonexistent_id_xyz")
        self.assertIsNone(data)

    def test_share_stats(self):
        self.eng.generate_share_url("strategy", "s1", "user6", "Strat", "")
        stats = self.eng.get_share_stats("strategy", "s1")
        self.assertIsInstance(stats, dict)

    def test_content_types_dict(self):
        ct = self.eng.CONTENT_TYPES
        self.assertIn("analysis", ct)
        self.assertIn("portfolio", ct)
        self.assertIn("mentor", ct)
        self.assertIn("strategy", ct)
        self.assertIn("course", ct)
        self.assertIn("activity", ct)

    def test_content_type_has_label_and_icon(self):
        for key, val in self.eng.CONTENT_TYPES.items():
            self.assertIn("label", val)
            self.assertIn("icon", val)
            self.assertIn("base_path", val)


# ═══════════════════════════════════════════════════════════════
# 5. Invite Blueprint — File Structure
# ═══════════════════════════════════════════════════════════════
class TestInviteBlueprintStructure(unittest.TestCase):
    """Blueprint file structure checks."""

    def test_init_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/blueprints/invite/__init__.py")))

    def test_routes_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/blueprints/invite/routes.py")))

    def test_init_has_blueprint(self):
        src = _read("app/blueprints/invite/__init__.py")
        self.assertIn("invite_bp", src)
        self.assertIn("Blueprint", src)

    def test_routes_has_invite_page(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/invite", src)

    def test_routes_has_api_code(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/code", src)

    def test_routes_has_api_stats(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/stats", src)

    def test_routes_has_api_rewards(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/rewards", src)

    def test_routes_has_api_top_inviters(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/top-inviters", src)

    def test_routes_has_share_generate(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/share/generate", src)

    def test_routes_has_share_redirect(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/share/<share_id>", src)

    def test_routes_has_register_referral(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/register-referral", src)

    def test_routes_has_growth_stats(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/growth-stats", src)

    def test_routes_has_recent(self):
        src = _read("app/blueprints/invite/routes.py")
        self.assertIn("/api/invite/recent", src)


# ═══════════════════════════════════════════════════════════════
# 6. Monolith Registration
# ═══════════════════════════════════════════════════════════════
class TestMonolithRegistration(unittest.TestCase):
    """Check that invite_bp is imported and registered."""

    def setUp(self):
        self.src = _read("legacy_monolith.py")

    def test_import_invite_bp(self):
        self.assertIn("from app.blueprints.invite import invite_bp", self.src)

    def test_register_invite_bp(self):
        self.assertIn("app.register_blueprint(invite_bp)", self.src)


# ═══════════════════════════════════════════════════════════════
# 7. Template — invite.html
# ═══════════════════════════════════════════════════════════════
class TestInviteTemplate(unittest.TestCase):
    """invite.html template structure checks."""

    def setUp(self):
        self.src = _read("templates/invite.html")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "templates/invite.html")))

    def test_extends_layout(self):
        self.assertIn("extends", self.src)
        self.assertIn("layout_terminal.html", self.src)

    def test_has_invite_code_display(self):
        self.assertIn("invCode", self.src)

    def test_has_copy_button(self):
        self.assertIn("copyInviteLink", self.src)

    def test_has_share_twitter(self):
        self.assertIn("twitter", self.src.lower())

    def test_has_share_telegram(self):
        self.assertIn("telegram", self.src.lower())

    def test_has_share_whatsapp(self):
        self.assertIn("whatsapp", self.src.lower())

    def test_has_stats_section(self):
        self.assertIn("inv-stats", self.src)

    def test_has_rewards_section(self):
        self.assertIn("inv-rewards", self.src)

    def test_has_leaderboard_section(self):
        self.assertIn("inv-lb", self.src)

    def test_has_recent_section(self):
        self.assertIn("inv-recent", self.src)

    def test_has_progress_bar(self):
        self.assertIn("inv-progress", self.src)

    def test_has_reward_tiers_js(self):
        self.assertIn("REWARD_TIERS", self.src)

    def test_no_banned_words(self):
        lower = self.src.lower()
        for word in ["buy now", "sell now", "trade now", "stop loss", "take profit"]:
            self.assertNotIn(word, lower)


# ═══════════════════════════════════════════════════════════════
# 8. Layout — Sidebar Navigation
# ═══════════════════════════════════════════════════════════════
class TestLayoutSidebar(unittest.TestCase):
    """Check layout_terminal.html has invite nav item."""

    def setUp(self):
        self.src = _read("templates/layout_terminal.html")

    def test_has_invite_nav_item(self):
        self.assertIn('/invite"', self.src)

    def test_invite_nav_in_social_section(self):
        # In the rebuilt layout, invite is in sidebar footer (after main nav)
        invite_idx = self.src.find('/invite"')
        nav_idx = self.src.find('tl-nav')
        self.assertGreater(invite_idx, nav_idx)

    def test_invite_tooltip(self):
        self.assertIn("Invite", self.src)


# ═══════════════════════════════════════════════════════════════
# 9. Discover — Community Growth Widget
# ═══════════════════════════════════════════════════════════════
class TestDiscoverGrowthWidget(unittest.TestCase):
    """Check discover.html has community growth widget."""

    def setUp(self):
        self.src = _read("templates/discover.html")

    def test_has_community_growth_section(self):
        self.assertIn("Community Growth", self.src)

    def test_has_growth_members_element(self):
        self.assertIn("disc-growth-members", self.src)

    def test_has_growth_today_element(self):
        self.assertIn("disc-growth-today", self.src)

    def test_has_growth_week_element(self):
        self.assertIn("disc-growth-week", self.src)

    def test_has_growth_api_call(self):
        self.assertIn("/api/invite/growth-stats", self.src)

    def test_has_invite_link(self):
        self.assertIn("Invite Friends", self.src)


# ═══════════════════════════════════════════════════════════════
# 10. Share Card JS Component
# ═══════════════════════════════════════════════════════════════
class TestShareCardJS(unittest.TestCase):
    """share_card.js component checks."""

    def setUp(self):
        self.src = _read("static/js/components/share_card.js")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/js/components/share_card.js")))

    def test_has_share_card_namespace(self):
        self.assertIn("ShareCard", self.src)

    def test_has_open_method(self):
        self.assertIn("ShareCard.open", self.src)

    def test_has_api_call(self):
        self.assertIn("/api/share/generate", self.src)

    def test_has_clipboard(self):
        self.assertIn("clipboard", self.src.lower())

    def test_has_twitter(self):
        self.assertIn("twitter", self.src.lower())

    def test_has_telegram(self):
        self.assertIn("telegram", self.src.lower())

    def test_has_whatsapp(self):
        self.assertIn("whatsapp", self.src.lower())

    def test_has_escape_function(self):
        self.assertIn("_esc", self.src)


# ═══════════════════════════════════════════════════════════════
# 11. Copilot Referral Endpoint
# ═══════════════════════════════════════════════════════════════
class TestCopilotReferralEndpoint(unittest.TestCase):
    """Check copilot routes has referral endpoint."""

    def setUp(self):
        self.src = _read("app/blueprints/copilot/routes.py")

    def test_has_referral_route(self):
        self.assertIn("/api/copilot/referrals", self.src)

    def test_referral_route_is_post(self):
        idx = self.src.find("/api/copilot/referrals")
        context = self.src[max(0, idx-100):idx+50]
        self.assertIn("POST", context)

    def test_uses_referral_engine(self):
        self.assertIn("referral_engine", self.src)

    def test_uses_copilot_limit(self):
        self.assertIn("_check_copilot_limit", self.src)


# ═══════════════════════════════════════════════════════════════
# 12. Compliance & Security
# ═══════════════════════════════════════════════════════════════
class TestComplianceSecurity(unittest.TestCase):
    """LEGAL_SAFE_MODE compliance checks."""

    def test_referral_engine_banned_words(self):
        src = _read("app/core/referral_engine.py")
        self.assertIn("BANNED_WORDS", src)
        self.assertIn("_sanitize_text", src)

    def test_share_engine_banned_words(self):
        src = _read("app/core/share_engine.py")
        self.assertIn("BANNED_WORDS", src)

    def test_no_trading_advice_in_template(self):
        src = _read("templates/invite.html").lower()
        for phrase in ["guaranteed returns", "free money", "get rich"]:
            self.assertNotIn(phrase, src)

    def test_referral_engine_has_ip_hashing(self):
        src = _read("app/core/referral_engine.py")
        self.assertIn("hashlib.sha256", src)


# ═══════════════════════════════════════════════════════════════
# 13. Live HTTP Endpoints (server must be running on :34000)
# ═══════════════════════════════════════════════════════════════
class TestLiveHTTPEndpoints(unittest.TestCase):
    """Live endpoint tests — requires server running on port 34000."""

    def _get(self, path, **kw):
        return requests.get(f"{BASE_URL}{path}", timeout=8, **kw)

    def _post(self, path, json_body=None, **kw):
        return requests.post(f"{BASE_URL}{path}", json=json_body, timeout=8, **kw)

    # -- HTML pages --
    def test_invite_page_200(self):
        r = self._get("/invite")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Invite", r.text)

    # -- API endpoints --
    def test_api_invite_code(self):
        r = self._get("/api/invite/code")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))

    def test_api_invite_stats(self):
        r = self._get("/api/invite/stats")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))
        self.assertIn("data", d)

    def test_api_invite_rewards(self):
        r = self._get("/api/invite/rewards")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))

    def test_api_top_inviters(self):
        r = self._get("/api/invite/top-inviters?limit=5")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))

    def test_api_leaderboard_referrals_alias(self):
        r = self._get("/api/leaderboard/referrals")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))

    def test_api_recent_referrals(self):
        r = self._get("/api/invite/recent?limit=5")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))

    def test_api_growth_stats(self):
        r = self._get("/api/invite/growth-stats")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))
        self.assertIn("data", d)

    def test_api_register_referral_validation(self):
        """POST without required fields should return 400."""
        r = self._post("/api/invite/register-referral", {})
        self.assertEqual(r.status_code, 400)

    def test_api_share_generate(self):
        r = self._post("/api/share/generate", {
            "content_type": "analysis",
            "content_id": "test_123",
            "title": "Test Share",
            "description": "A test share"
        })
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d.get("ok"))
        self.assertIn("data", d)

    def test_api_share_generate_validation(self):
        r = self._post("/api/share/generate", {})
        self.assertEqual(r.status_code, 400)

    def test_api_share_nonexistent(self):
        r = self._get("/api/share/nonexistent_id_xyz")
        self.assertEqual(r.status_code, 404)

    def test_share_redirect_nonexistent(self):
        """Share redirect for nonexistent ID should go to /discover."""
        r = self._get("/share/nonexistent_redirect", allow_redirects=False)
        self.assertIn(r.status_code, [301, 302])
        self.assertIn("/discover", r.headers.get("Location", ""))

    def test_invite_code_redirect(self):
        """Invite code landing should redirect to /register."""
        r = self._get("/invite/TESTCODE123", allow_redirects=False)
        self.assertIn(r.status_code, [301, 302])
        self.assertIn("/register", r.headers.get("Location", ""))

    def test_copilot_referrals_endpoint(self):
        r = self._post("/api/copilot/referrals", {"user_id": "test_user"})
        self.assertIn(r.status_code, [200, 429])

    def test_discover_page_has_growth_widget(self):
        r = self._get("/discover")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Community Growth", r.text)

    # -- End-to-end flow --
    def test_api_full_referral_flow(self):
        """Generate code, then register a referral via API."""
        # Get invite code
        r1 = self._get("/api/invite/code")
        d1 = r1.json()
        self.assertTrue(d1.get("ok"))
        code = d1.get("code", "")
        self.assertTrue(len(code) > 0)

        # Try register (may fail due to fraud detection, but endpoint should work)
        r2 = self._post("/api/invite/register-referral", {
            "invite_code": code,
            "new_user_id": f"e2e_test_user_{os.urandom(4).hex()}"
        })
        self.assertIn(r2.status_code, [200, 400])


# ═══════════════════════════════════════════════════════════════
# 14. Fraud Detection Tests
# ═══════════════════════════════════════════════════════════════
class TestFraudDetection(unittest.TestCase):
    """Fraud detection logic tests."""

    @classmethod
    def setUpClass(cls):
        import app.core.referral_engine as eng
        import app.core.db_manager as _dm
        cls._orig_db_path = eng._DB_PATH
        cls._orig_db_dir = _dm._DB_DIR
        cls._tmpdir = tempfile.mkdtemp()
        eng._DB_PATH = os.path.join(cls._tmpdir, "test_fraud.db")
        _dm._DB_DIR = cls._tmpdir
        cls.eng = eng

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        cls.eng._DB_PATH = cls._orig_db_path
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_self_referral_returns_none(self):
        code = self.eng.generate_invite_code("fraud_self")
        result = self.eng.register_referral(code, "fraud_self")
        self.assertIsNone(result)

    def test_duplicate_user_returns_none(self):
        code = self.eng.generate_invite_code("fraud_dup_ref")
        self.eng.register_referral(code, "fraud_dup_target")
        result = self.eng.register_referral(code, "fraud_dup_target")
        self.assertIsNone(result)

    def test_ip_limit_enforced(self):
        code = self.eng.generate_invite_code("fraud_ip_ref")
        same_ip = "10.99.99.99"
        for i in range(5):
            self.eng.register_referral(code, f"fraud_ip_user_{i}", same_ip)
        result = self.eng.register_referral(code, "fraud_ip_user_blocked", same_ip)
        self.assertIsNone(result)

    def test_different_ips_allowed(self):
        code = self.eng.generate_invite_code("fraud_multi_ip")
        for i in range(6):
            result = self.eng.register_referral(code, f"fraud_diff_ip_{i}", f"1.1.1.{i}")
            if i < 5:  # unique IPs should all succeed
                self.assertIsNotNone(result)


# ═══════════════════════════════════════════════════════════════
# 15. Reward System Tests
# ═══════════════════════════════════════════════════════════════
class TestRewardSystem(unittest.TestCase):
    """Reward tier and grant tests."""

    @classmethod
    def setUpClass(cls):
        import app.core.referral_engine as eng
        import app.core.db_manager as _dm
        cls._orig_db_path = eng._DB_PATH
        cls._orig_db_dir = _dm._DB_DIR
        cls._tmpdir = tempfile.mkdtemp()
        eng._DB_PATH = os.path.join(cls._tmpdir, "test_rewards.db")
        _dm._DB_DIR = cls._tmpdir
        cls.eng = eng

    @classmethod
    def tearDownClass(cls):
        import app.core.db_manager as _dm
        cls.eng._DB_PATH = cls._orig_db_path
        _dm._DB_DIR = cls._orig_db_dir
        import shutil
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_first_referral_grants_pro_trial(self):
        code = self.eng.generate_invite_code("reward_user_1")
        self.eng.register_referral(code, "reward_referred_1", "20.0.0.1")
        rewards = self.eng.calculate_referral_rewards("reward_user_1")
        # Should have at least the first tier reward
        self.assertGreaterEqual(len(rewards), 1)
        types = [r["reward_type"] for r in rewards]
        self.assertIn("pro_trial", types)

    def test_three_referrals_grants_credits(self):
        code = self.eng.generate_invite_code("reward_user_3")
        for i in range(3):
            self.eng.register_referral(code, f"reward3_ref_{i}", f"30.0.0.{i}")
        rewards = self.eng.calculate_referral_rewards("reward_user_3")
        types = [r["reward_type"] for r in rewards]
        self.assertIn("copilot_credits", types)

    def test_no_duplicate_rewards(self):
        code = self.eng.generate_invite_code("no_dup_rew")
        self.eng.register_referral(code, "no_dup_ref_1", "40.0.0.1")
        r1 = self.eng.calculate_referral_rewards("no_dup_rew")
        self.eng.register_referral(code, "no_dup_ref_2", "40.0.0.2")
        r2 = self.eng.calculate_referral_rewards("no_dup_rew")
        # Pro trial should only appear once
        pro_count = sum(1 for r in r2 if r["reward_type"] == "pro_trial")
        self.assertEqual(pro_count, 1)

    def test_reward_tiers_ascending(self):
        tiers = self.eng.REWARD_TIERS
        mins = [t[0] for t in tiers]
        self.assertEqual(mins, sorted(mins))


if __name__ == "__main__":
    unittest.main()
