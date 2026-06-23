# -*- coding: utf-8 -*-
"""FAZ 64 — Simulator Live Price + AI Market Agent Runtime Fix Tests.

55+ tests covering:
 A) AI Agent Brief — Auth fallback to market-summary
 B) AI Agent Brief — Public rendering with login notice
 C) AI Agent Portfolio/Watchlist — Auth message
 D) AI Agent Ask — Auth error handling
 E) AI Agent Backend — Endpoint auth configuration
 F) Simulator — fetchPrice force parameter
 G) Simulator — Initial price load tracking
 H) Simulator — WS first tick tracking
 I) Simulator — Retry mechanism for initial price
 J) Simulator — Symbol change resets FAZ 64 flags
 K) Simulator — DOM price display robustness
 L) Backend runtime — price & market-summary endpoints
 N-P) SSR Price — template, route, live
 Q) FAZ 64B — REST not throttled on WS connect
 R) FAZ 64B — Preset buttons price fallback + async retry
 S) FAZ 64B — Journal save addEventListener pattern
 T) FAZ 64B — Cache-bust version updated
"""
import json
import os
import re
import sys
import time
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

JS_FILE = os.path.join(BASE, "static", "js", "simulator.js")
CSS_FILE = os.path.join(BASE, "static", "css", "simulator.css")
HTML_SIM = os.path.join(BASE, "templates", "simulator.html")
HTML_AI = os.path.join(BASE, "templates", "ai_agent.html")
ROUTES_AI = os.path.join(BASE, "app", "blueprints", "ai_agent", "routes.py")
ROUTES_SIM = os.path.join(BASE, "app", "blueprints", "simulator", "routes.py")
AUTH_FILE = os.path.join(BASE, "app", "blueprints", "auth", "routes.py")
AGENT_CORE = os.path.join(BASE, "app", "core", "ai_market_agent.py")
STREAM_PY = os.path.join(BASE, "app", "core", "market_stream.py")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _get_ai_html():
    return _read(HTML_AI)


def _get_sim_js():
    return _read(JS_FILE)


# ══════════════════════════════════════════════════════════════════
# A) AI Agent — loadBrief() auth fallback
# ══════════════════════════════════════════════════════════════════

class TestAIBriefAuthFallback(unittest.TestCase):
    """loadBrief() must fall back to /api/ai/market-summary on auth failure."""

    @classmethod
    def setUpClass(cls):
        cls.html = _get_ai_html()

    def test_loadbrief_function_exists(self):
        self.assertIn("async function loadBrief()", self.html)

    def test_loadbrief_tries_brief_endpoint_first(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 1500]
        brief_idx = fn.index("/api/ai/brief")
        self.assertGreater(brief_idx, 0)

    def test_loadbrief_falls_back_to_market_summary(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 1500]
        self.assertIn("/api/ai/market-summary", fn)

    def test_fallback_triggers_on_not_ok(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 1500]
        # After first fetch, if not ok, should try market-summary
        brief_pos = fn.index("/api/ai/brief")
        not_ok_pos = fn.index("!res.ok", brief_pos)
        summary_pos = fn.index("/api/ai/market-summary", not_ok_pos)
        self.assertGreater(summary_pos, not_ok_pos)

    def test_isPublic_flag_set_on_fallback(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 1500]
        self.assertIn("isPublic = true", fn)

    def test_isPublic_flag_initial_false(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 1500]
        self.assertIn("isPublic = false", fn)

    def test_market_summary_called_second(self):
        """market-summary URL appears AFTER brief URL in loadBrief."""
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 1500]
        pos_brief = fn.index("/api/ai/brief")
        pos_summary = fn.index("/api/ai/market-summary")
        self.assertGreater(pos_summary, pos_brief)

    def test_second_failure_shows_generic_error(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 2000]
        # After fallback also fails, show a proper generic error
        self.assertIn("Piyasa verileri yüklenemedi", fn)

    def test_no_old_error_message(self):
        """Old 'Brifing yüklenemedi' error message must be removed."""
        self.assertNotIn("Brifing yüklenemedi. Giriş yapmanız gerekebilir.", self.html)


# ══════════════════════════════════════════════════════════════════
# B) AI Agent — Public mode login notice
# ══════════════════════════════════════════════════════════════════

class TestAIBriefPublicNotice(unittest.TestCase):
    """When in public mode, show login notice and skip user-specific sections."""

    @classmethod
    def setUpClass(cls):
        cls.html = _get_ai_html()

    def test_login_notice_shown_in_public_mode(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 2500]
        self.assertIn("Genel Piyasa Özeti", fn)

    def test_login_link_in_notice(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 2500]
        self.assertIn('href="/login"', fn)

    def test_login_notice_mentions_personalized(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 2500]
        # Turkish text about personalized briefing
        self.assertIn("Kişiselleştirilmiş", fn)

    def test_portfolio_section_skipped_in_public(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 4000]
        # Portfolio check includes !isPublic guard
        self.assertIn("!isPublic && d.portfolio", fn)

    def test_watchlist_section_skipped_in_public(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 4000]
        # Watchlist check includes !isPublic guard
        self.assertIn("!isPublic && d.watchlist", fn)

    def test_opportunities_fetched_publicly(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 4000]
        # In public mode, opportunities fetched from public endpoint
        self.assertIn("/api/ai/opportunities", fn)

    def test_sentiment_rendered_in_public_mode(self):
        """Sentiment section uses d.sentiment which exists in both brief & market-summary."""
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 4000]
        self.assertIn("d.sentiment", fn)

    def test_highlights_rendered_in_public_mode(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 4000]
        self.assertIn("d.highlights", fn)

    def test_timestamp_rendered_in_public_mode(self):
        idx = self.html.index("async function loadBrief()")
        fn = self.html[idx:idx + 4000]
        self.assertIn("d.generated_at", fn)


# ══════════════════════════════════════════════════════════════════
# C) AI Agent — Portfolio/Watchlist auth messages
# ══════════════════════════════════════════════════════════════════

class TestAIPortfolioWatchlistAuth(unittest.TestCase):
    """Portfolio and watchlist tabs show proper auth message instead of generic error."""

    @classmethod
    def setUpClass(cls):
        cls.html = _get_ai_html()

    def test_portfolio_shows_login_message(self):
        """loadPortfolio error shows login-required message."""
        self.assertIn("Giriş Gerekli", self.html)

    def test_portfolio_has_login_link(self):
        # Find portfolio loading section
        idx = self.html.index("async function loadPortfolio()")
        fn = self.html[idx:idx + 800]
        self.assertIn('href="/login"', fn)

    def test_watchlist_shows_login_message(self):
        """loadWatchlist error shows login-required message."""
        idx = self.html.index("async function loadWatchlist()")
        fn = self.html[idx:idx + 800]
        self.assertIn("Giriş Gerekli", fn)

    def test_watchlist_has_login_link(self):
        idx = self.html.index("async function loadWatchlist()")
        fn = self.html[idx:idx + 800]
        self.assertIn('href="/login"', fn)

    def test_old_portfolio_error_removed(self):
        self.assertNotIn("Portföy analizi yüklenemedi.", self.html)

    def test_old_watchlist_error_removed(self):
        self.assertNotIn("İzleme listesi yüklenemedi.", self.html)


# ══════════════════════════════════════════════════════════════════
# D) AI Agent — Ask AI auth handling
# ══════════════════════════════════════════════════════════════════

class TestAIAskAuth(unittest.TestCase):
    """Ask AI section handles auth errors gracefully."""

    @classmethod
    def setUpClass(cls):
        cls.html = _get_ai_html()

    def test_ask_auth_error_shows_login_message(self):
        idx = self.html.index("async function doAsk(")
        fn = self.html[idx:idx + 800]
        self.assertIn("giriş yapmanız gerekiyor", fn.lower())

    def test_ask_checks_error_text(self):
        idx = self.html.index("async function doAsk(")
        fn = self.html[idx:idx + 800]
        self.assertIn("Giriş yapmanız gerekiyor", fn)


# ══════════════════════════════════════════════════════════════════
# E) AI Agent Backend — Endpoint auth configuration
# ══════════════════════════════════════════════════════════════════

class TestAIEndpointAuth(unittest.TestCase):
    """Verify auth configuration of AI agent endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.routes = _read(ROUTES_AI)

    def test_brief_requires_login(self):
        idx = self.routes.index('"/api/ai/brief"')
        # login_required appears between route decorator and function def
        region = self.routes[idx:idx + 100]
        self.assertIn("@login_required", region)

    def test_market_summary_no_login(self):
        idx = self.routes.index('"/api/ai/market-summary"')
        fn_start = self.routes.index("def api_market_summary", idx)
        region = self.routes[idx:fn_start]
        self.assertNotIn("@login_required", region)

    def test_opportunities_no_login(self):
        idx = self.routes.index('"/api/ai/opportunities"')
        fn_start = self.routes.index("def api_ai_opportunities", idx)
        region = self.routes[idx:fn_start]
        self.assertNotIn("@login_required", region)

    def test_portfolio_requires_login(self):
        idx = self.routes.index('"/api/ai/portfolio"')
        region = self.routes[idx:idx + 100]
        self.assertIn("@login_required", region)

    def test_watchlist_requires_login(self):
        idx = self.routes.index('"/api/ai/watchlist"')
        region = self.routes[idx:idx + 100]
        self.assertIn("@login_required", region)

    def test_ask_requires_login(self):
        idx = self.routes.index('"/api/ai/ask"')
        region = self.routes[idx:idx + 100]
        self.assertIn("@login_required", region)

    def test_page_route_no_login(self):
        idx = self.routes.index('"/ai-agent"')
        fn_start = self.routes.index("def ai_agent_page", idx)
        region = self.routes[idx:fn_start]
        self.assertNotIn("@login_required", region)


# ══════════════════════════════════════════════════════════════════
# F) Simulator — fetchPrice force parameter
# ══════════════════════════════════════════════════════════════════

class TestFetchPriceForce(unittest.TestCase):
    """fetchPrice accepts force parameter to bypass WS guard."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_fetchprice_accepts_force_param(self):
        self.assertIn("async function fetchPrice(force)", self.js)

    def test_force_bypasses_ws_guard(self):
        """FAZ 64C: WS guard removed entirely — force param still accepted but no guard to bypass."""
        idx = self.js.index("async function fetchPrice(force)")
        fn = self.js[idx:idx + 1200]
        # WS guard removed in 64C, fetchPrice always runs REST
        self.assertNotIn("_wsPriceSource", fn)

    def test_force_bypasses_second_ws_guard(self):
        """FAZ 64C: No WS guard checks exist in fetchPrice anymore."""
        idx = self.js.index("async function fetchPrice(force)")
        fn = self.js[idx:idx + 1200]
        count = fn.count("_wsPriceSource")
        self.assertEqual(count, 0,
                         "No WS guard checks should exist in fetchPrice")

    def test_force_default_is_falsy(self):
        """When called without args, force is undefined (falsy)."""
        # startPriceFetch calls fetchPrice() without args
        self.assertIn("fetchPrice()", self.js)

    def test_ws_timeout_calls_force_true(self):
        """WS onopen timeout calls fetchPrice(true)."""
        idx = self.js.index("function connectSimWS()")
        fn = self.js[idx:idx + 2000]
        self.assertIn("fetchPrice(true)", fn)


# ══════════════════════════════════════════════════════════════════
# G) Simulator — Initial price load tracking
# ══════════════════════════════════════════════════════════════════

class TestInitialPriceTracking(unittest.TestCase):
    """_initialPriceLoaded flag tracks if first price was obtained."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_initial_price_loaded_var_exists(self):
        self.assertIn("_initialPriceLoaded", self.js)

    def test_initial_price_loaded_starts_false(self):
        self.assertIn("_initialPriceLoaded = false", self.js)

    def test_initial_price_set_true_on_success(self):
        idx = self.js.index("async function fetchPrice(force)")
        fn = self.js[idx:idx + 1200]
        self.assertIn("_initialPriceLoaded = true", fn)

    def test_loading_text_shown_initially(self):
        idx = self.js.index("async function fetchPrice(force)")
        fn = self.js[idx:idx + 600]
        self.assertIn("Yükleniyor...", fn)

    def test_loading_text_only_when_no_price(self):
        idx = self.js.index("async function fetchPrice(force)")
        fn = self.js[idx:idx + 600]
        self.assertIn("!_initialPriceLoaded && livePrice <= 0", fn)

    def test_retry_after_3s_if_not_loaded(self):
        """FAZ 64C: Init section includes 2s retry timeout."""
        idx = self.js.index("// INIT")
        init_section = self.js[idx:idx + 900]
        self.assertIn("2000", init_section)
        self.assertIn("_initialPriceLoaded", init_section)


# ══════════════════════════════════════════════════════════════════
# H) Simulator — WS first tick tracking
# ══════════════════════════════════════════════════════════════════

class TestWSFirstTickTracking(unittest.TestCase):
    """_wsFirstTickReceived tracks if WS ever delivered a price tick."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_ws_first_tick_var_exists(self):
        self.assertIn("_wsFirstTickReceived", self.js)

    def test_ws_first_tick_starts_false(self):
        self.assertRegex(self.js, r"_wsFirstTickReceived\s*=\s*false")

    def test_ws_first_tick_set_true_on_tick(self):
        idx = self.js.index("function _handleSimWSTick(")
        fn = self.js[idx:idx + 600]
        self.assertIn("_wsFirstTickReceived = true", fn)

    def test_ws_first_tick_reset_on_connect(self):
        """onopen resets _wsFirstTickReceived to false."""
        idx = self.js.index("function connectSimWS()")
        fn = self.js[idx:idx + 2000]
        self.assertIn("_wsFirstTickReceived = false", fn)

    def test_ws_timeout_checks_first_tick(self):
        """5s timeout in onopen checks _wsFirstTickReceived."""
        idx = self.js.index("function connectSimWS()")
        fn = self.js[idx:idx + 2000]
        self.assertIn("!_wsFirstTickReceived", fn)
        self.assertIn("5000", fn)


# ══════════════════════════════════════════════════════════════════
# I) Simulator — Retry mechanism
# ══════════════════════════════════════════════════════════════════

class TestSimulatorRetryMechanism(unittest.TestCase):
    """Verify retry logic ensures price is always displayed."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_init_retry_timeout_exists(self):
        idx = self.js.index("// INIT")
        init = self.js[idx:idx + 900]
        self.assertIn("setTimeout", init)

    def test_init_retry_calls_fetchprice(self):
        idx = self.js.index("// INIT")
        init = self.js[idx:idx + 900]
        self.assertIn("fetchPrice(true)", init)

    def test_init_retry_checks_conditions(self):
        idx = self.js.index("// INIT")
        init = self.js[idx:idx + 900]
        self.assertIn("!_initialPriceLoaded", init)
        self.assertIn("livePrice <= 0", init)

    def test_ws_onopen_timeout_forces_rest_fetch(self):
        idx = self.js.index("function connectSimWS()")
        fn = self.js[idx:idx + 2000]
        # Must have setTimeout that calls fetchPrice(true)
        self.assertIn("fetchPrice(true)", fn)

    def test_error_logging_in_fetchprice(self):
        """fetchPrice logs errors instead of silently ignoring them."""
        idx = self.js.index("async function fetchPrice(force)")
        fn = self.js[idx:idx + 2000]
        self.assertIn("console.warn", fn)

    def test_ws_onclose_still_does_immediate_fetch(self):
        idx = self.js.index("function connectSimWS()")
        fn = self.js[idx:idx + 3000]
        onclose_idx = fn.index("onclose")
        onclose_region = fn[onclose_idx:onclose_idx + 500]
        self.assertIn("fetchPrice()", onclose_region)


# ══════════════════════════════════════════════════════════════════
# J) Simulator — Symbol change resets FAZ 64 flags
# ══════════════════════════════════════════════════════════════════

class TestSymbolChangeResets(unittest.TestCase):
    """Symbol and market change handlers reset FAZ 64 tracking vars."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_symbol_input_resets_ws_first_tick(self):
        idx = self.js.index('$symbol.addEventListener("input"')
        handler = self.js[idx:idx + 500]
        self.assertIn("_wsFirstTickReceived = false", handler)

    def test_symbol_input_resets_initial_loaded(self):
        idx = self.js.index('$symbol.addEventListener("input"')
        handler = self.js[idx:idx + 500]
        self.assertIn("_initialPriceLoaded = false", handler)

    def test_market_change_resets_ws_first_tick(self):
        idx = self.js.index('$market.addEventListener("change"')
        handler = self.js[idx:idx + 500]
        self.assertIn("_wsFirstTickReceived = false", handler)

    def test_market_change_resets_initial_loaded(self):
        idx = self.js.index('$market.addEventListener("change"')
        handler = self.js[idx:idx + 500]
        self.assertIn("_initialPriceLoaded = false", handler)

    def test_symbol_input_also_resets_ws_price_source(self):
        idx = self.js.index('$symbol.addEventListener("input"')
        handler = self.js[idx:idx + 500]
        self.assertIn("_wsPriceSource = false", handler)

    def test_market_change_also_resets_ws_price_source(self):
        idx = self.js.index('$market.addEventListener("change"')
        handler = self.js[idx:idx + 500]
        self.assertIn("_wsPriceSource = false", handler)


# ══════════════════════════════════════════════════════════════════
# K) Simulator — DOM price display
# ══════════════════════════════════════════════════════════════════

class TestSimulatorPriceDisplay(unittest.TestCase):
    """Verify DOM elements and CSS for price display."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(HTML_SIM)
        cls.css = _read(CSS_FILE)
        cls.js = _get_sim_js()

    def test_live_price_element_exists(self):
        self.assertIn('id="sim-live-price"', self.html)

    def test_live_price_default_text(self):
        # Template uses conditional: shows SSR price or em-dash fallback
        self.assertRegex(self.html, r'id="sim-live-price"')
        self.assertIn('{% else %}\u2014{% endif %}', self.html)

    def test_css_loaded_class(self):
        self.assertIn(".sim-tp-price-value.loaded", self.css)

    def test_css_flash_up_class(self):
        self.assertIn(".sim-tp-price-value.flash-up", self.css)

    def test_css_flash_down_class(self):
        self.assertIn(".sim-tp-price-value.flash-down", self.css)

    def test_live_price_dom_ref(self):
        self.assertIn('$livePrice   = $("sim-live-price")', self.js)

    def test_price_display_visible_css(self):
        self.assertIn(".sim-tp-price-display", self.css)

    def test_fmtPrice_function_exists(self):
        self.assertIn("function fmtPrice(n)", self.js)


# ══════════════════════════════════════════════════════════════════
# L) Backend — Runtime endpoint tests
# ══════════════════════════════════════════════════════════════════

class TestBackendEndpoints(unittest.TestCase):
    """Test backend endpoints at runtime (requires running server)."""

    SERVER_URL = "http://localhost:34000"

    @classmethod
    def setUpClass(cls):
        import urllib.request
        try:
            r = urllib.request.urlopen(cls.SERVER_URL + "/simulator", timeout=3)
            cls.server_up = r.status == 200
        except Exception:
            cls.server_up = False

    def _get(self, path):
        import urllib.request
        req = urllib.request.Request(self.SERVER_URL + path)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def _get_status(self, path):
        import urllib.request
        req = urllib.request.Request(self.SERVER_URL + path)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    # ── Price endpoint ──────────────────────────────────────────

    @unittest.skipUnless(True, "requires running server")
    def test_price_endpoint_returns_200(self):
        if not self.server_up:
            self.skipTest("Server not running")
        status = self._get_status("/api/simulator/price?symbol=BTCUSDT&market=crypto")
        self.assertEqual(status, 200)

    def test_price_endpoint_returns_ok(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/simulator/price?symbol=BTCUSDT&market=crypto")
        self.assertTrue(data["ok"])

    def test_price_endpoint_returns_positive_price(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/simulator/price?symbol=BTCUSDT&market=crypto")
        self.assertGreater(data["price"], 0)

    def test_price_endpoint_returns_symbol(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/simulator/price?symbol=BTCUSDT&market=crypto")
        self.assertEqual(data["symbol"], "BTCUSDT")

    # ── Market summary endpoint ─────────────────────────────────

    def test_market_summary_returns_200(self):
        if not self.server_up:
            self.skipTest("Server not running")
        status = self._get_status("/api/ai/market-summary")
        self.assertEqual(status, 200)

    def test_market_summary_returns_ok(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/ai/market-summary")
        self.assertTrue(data["ok"])

    def test_market_summary_has_sentiment(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/ai/market-summary")
        self.assertIn("sentiment", data["data"])

    def test_market_summary_has_highlights(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/ai/market-summary")
        self.assertIn("highlights", data["data"])

    def test_market_summary_has_generated_at(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/ai/market-summary")
        self.assertIn("generated_at", data["data"])

    # ── Brief endpoint auth ──────────────────────────────────────

    def test_brief_endpoint_requires_auth(self):
        if not self.server_up:
            self.skipTest("Server not running")
        status = self._get_status("/api/ai/brief")
        self.assertEqual(status, 401)

    # ── Opportunities endpoint ───────────────────────────────────

    def test_opportunities_no_auth_required(self):
        if not self.server_up:
            self.skipTest("Server not running")
        status = self._get_status("/api/ai/opportunities?limit=5")
        self.assertEqual(status, 200)

    def test_opportunities_returns_data(self):
        if not self.server_up:
            self.skipTest("Server not running")
        data = self._get("/api/ai/opportunities?limit=5")
        self.assertTrue(data["ok"])
        self.assertIsInstance(data["data"], list)

    # ── Page accessibility ──────────────────────────────────────

    def test_simulator_page_accessible(self):
        if not self.server_up:
            self.skipTest("Server not running")
        status = self._get_status("/simulator")
        self.assertEqual(status, 200)

    def test_ai_agent_page_accessible(self):
        if not self.server_up:
            self.skipTest("Server not running")
        status = self._get_status("/ai-agent")
        self.assertEqual(status, 200)


# ══════════════════════════════════════════════════════════════════
# M) AI Agent — fetchJSON helper
# ══════════════════════════════════════════════════════════════════

class TestFetchJSONHelper(unittest.TestCase):
    """fetchJSON function properly handles errors."""

    @classmethod
    def setUpClass(cls):
        cls.html = _get_ai_html()

    def test_fetchjson_exists(self):
        self.assertIn("async function fetchJSON(url", self.html)

    def test_fetchjson_catches_errors(self):
        idx = self.html.index("async function fetchJSON(url")
        fn = self.html[idx:idx + 300]
        self.assertIn("catch", fn)

    def test_fetchjson_returns_ok_false_on_error(self):
        idx = self.html.index("async function fetchJSON(url")
        fn = self.html[idx:idx + 300]
        self.assertIn("ok: false", fn)


# ══════════════════════════════════════════════════════════════════
# N) Simulator — Server-Side Rendered Price (FAZ 64 SSR)
# ══════════════════════════════════════════════════════════════════

class TestSSRPrice(unittest.TestCase):
    """Verify server-side rendered initial price for instant display."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(HTML_SIM)
        cls.js = _get_sim_js()

    def test_template_has_initial_price_conditional(self):
        """Template uses initial_price Jinja2 variable."""
        self.assertIn("{% if initial_price %}", self.html)

    def test_template_formats_price_with_dollar(self):
        """SSR price uses dollar format."""
        self.assertIn('"${:,.2f}".format(initial_price)', self.html)

    def test_template_fallback_to_dash(self):
        """When no initial_price, shows em-dash."""
        self.assertIn("{% else %}\u2014{% endif %}", self.html)

    def test_template_loaded_class_conditional(self):
        """Applies 'loaded' CSS class when price is available."""
        self.assertIn("{% if initial_price %} loaded{% endif %}", self.html)

    def test_js_reads_ssr_price(self):
        """JS checks window.__SIM_INITIAL_PRICE__ on init."""
        self.assertIn("window.__SIM_INITIAL_PRICE__", self.js)

    def test_js_uses_ssr_price_for_live_price(self):
        """JS sets livePrice from SSR value."""
        idx = self.js.index("// INIT")
        init = self.js[idx:idx + 500]
        self.assertIn("livePrice = window.__SIM_INITIAL_PRICE__", init)

    def test_js_caches_ssr_price(self):
        """JS caches SSR price as lastGoodPrice."""
        idx = self.js.index("// INIT")
        init = self.js[idx:idx + 500]
        self.assertIn("lastGoodPrice = livePrice", init)

    def test_js_marks_initial_price_loaded(self):
        """SSR price sets _initialPriceLoaded = true."""
        idx = self.js.index("// INIT")
        init = self.js[idx:idx + 500]
        self.assertIn("_initialPriceLoaded = true", init)

    def test_inline_script_passes_price(self):
        """Template includes inline script setting __SIM_INITIAL_PRICE__."""
        self.assertIn("window.__SIM_INITIAL_PRICE__", self.html)

    def test_cache_bust_version(self):
        """Script tag includes cache-busting version parameter."""
        self.assertIn("simulator.js') }}?v=", self.html)


class TestSSRPriceRoute(unittest.TestCase):
    """Verify server-side route passes initial_price to template."""

    @classmethod
    def setUpClass(cls):
        route_file = os.path.join(BASE, "app", "blueprints", "dashboard", "routes.py")
        cls.route_code = _read(route_file)

    def test_route_imports_fetch_current_price(self):
        self.assertIn("from app.core.paper_trading_engine import fetch_current_price", self.route_code)

    def test_route_fetches_btcusdt(self):
        self.assertIn('"BTCUSDT"', self.route_code)

    def test_route_passes_initial_price_to_template(self):
        self.assertIn("initial_price=initial_price", self.route_code)

    def test_route_handles_errors_gracefully(self):
        """Route doesn't crash if price fetch fails."""
        self.assertIn("except Exception", self.route_code)

    def test_route_rounds_price(self):
        self.assertIn("round(initial_price", self.route_code)


class TestSSRPriceLive(unittest.TestCase):
    """Live server test: verify SSR price appears in HTML response."""

    SERVER_URL = "http://localhost:34000"

    @classmethod
    def setUpClass(cls):
        import urllib.request
        try:
            r = urllib.request.urlopen(cls.SERVER_URL + "/simulator", timeout=5)
            cls.page_html = r.read().decode("utf-8")
            cls.server_up = True
        except Exception:
            cls.page_html = ""
            cls.server_up = False

    def test_ssr_price_in_html(self):
        if not self.server_up:
            self.skipTest("Server not running")
        # The live-price element should contain a dollar amount, not em-dash
        import re
        match = re.search(r'id="sim-live-price"[^>]*>\$[\d,]+\.\d{2}<', self.page_html)
        self.assertIsNotNone(match, "SSR price should be a dollar amount in HTML")

    def test_ssr_price_has_loaded_class(self):
        if not self.server_up:
            self.skipTest("Server not running")
        self.assertIn('sim-tp-price-value loaded', self.page_html)

    def test_ssr_initial_price_js_var(self):
        if not self.server_up:
            self.skipTest("Server not running")
        import re
        match = re.search(r'__SIM_INITIAL_PRICE__\s*=\s*[\d.]+', self.page_html)
        self.assertIsNotNone(match, "SSR price JS variable should be a number")

    def test_cache_bust_in_script_tag(self):
        if not self.server_up:
            self.skipTest("Server not running")
        self.assertIn('simulator.js?v=64', self.page_html)


# ══════════════════════════════════════════════════════════════════
# Q) FAZ 64B — Live Price: REST not throttled on WS connect
# ══════════════════════════════════════════════════════════════════

class TestLivePriceRESTAlwaysPolls(unittest.TestCase):
    """FAZ 64C: REST always polls at 5s, no WS guard in fetchPrice."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_no_ws_guard_in_fetchprice(self):
        """fetchPrice must NOT check _wsPriceSource."""
        idx = self.js.index("async function fetchPrice(")
        fn = self.js[idx:idx + 1200]
        self.assertNotIn("_wsPriceSource", fn)

    def test_no_30s_interval_anywhere(self):
        """No 30s REST throttle should exist."""
        idx = self.js.index("async function fetchPrice(")
        fn = self.js[idx:idx + 1200]
        self.assertNotIn("30000", fn)

    def test_5s_polling_in_startpricefetch(self):
        """startPriceFetch uses 5s interval."""
        idx = self.js.index("function startPriceFetch()")
        fn = self.js[idx:idx + 200]
        self.assertIn("setInterval(fetchPrice, 5000)", fn)

    def test_fetchprice_always_fetches(self):
        """fetchPrice does REST fetch without WS guard."""
        idx = self.js.index("async function fetchPrice(")
        fn = self.js[idx:idx + 1200]
        self.assertIn("/price?symbol=", fn)

    def test_tick_handler_no_throttle(self):
        """_handleSimWSTick does NOT throttle REST anymore."""
        idx = self.js.index("function _handleSimWSTick(")
        fn = self.js[idx:idx + 800]
        self.assertNotIn("clearInterval(priceInterval)", fn)
        self.assertNotIn("setInterval(fetchPrice, 30000)", fn)

    def test_tick_handler_still_sets_liveprice(self):
        """_handleSimWSTick still updates livePrice from WS tick."""
        idx = self.js.index("function _handleSimWSTick(")
        fn = self.js[idx:idx + 800]
        self.assertIn("livePrice = price", fn)

    def test_onclose_restores_5s_polling(self):
        """WS onclose still restores fast REST polling."""
        idx = self.js.index("_simWS.onclose = function(")
        onclose = self.js[idx:idx + 400]
        self.assertIn("setInterval(fetchPrice, 5000)", onclose)


# ══════════════════════════════════════════════════════════════════
# R) FAZ 64B — % Preset Buttons: Price Fallback + Async Retry
# ══════════════════════════════════════════════════════════════════

class TestPresetButtonsPriceFallback(unittest.TestCase):
    """Preset % buttons must use lastGoodPrice fallback and async retry."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_geteffectiveprice_has_fallback(self):
        """getEffectivePrice returns lastGoodPrice when livePrice is 0."""
        idx = self.js.index("function getEffectivePrice()")
        fn = self.js[idx:idx + 400]
        self.assertIn("lastGoodPrice", fn)

    def test_geteffectiveprice_prefers_liveprice(self):
        """getEffectivePrice prefers livePrice when > 0."""
        idx = self.js.index("function getEffectivePrice()")
        fn = self.js[idx:idx + 400]
        self.assertIn("livePrice > 0", fn)

    def test_preset_handler_is_async(self):
        """Preset button click handler should be async."""
        # Find the preset button click handler (second occurrence, after clearPresetActive)
        first = self.js.index('".sim-preset-btn"')
        idx = self.js.index('".sim-preset-btn"', first + 1)
        block = self.js[idx:idx + 1200]
        self.assertIn("async function()", block)

    def test_preset_handler_retries_price(self):
        """If price is 0, preset handler calls fetchPrice(true) before error."""
        first = self.js.index('".sim-preset-btn"')
        idx = self.js.index('".sim-preset-btn"', first + 1)
        block = self.js[idx:idx + 1200]
        self.assertIn("await fetchPrice(true)", block)

    def test_preset_handler_checks_price_twice(self):
        """After retry, getEffectivePrice is called again."""
        first = self.js.index('".sim-preset-btn"')
        idx = self.js.index('".sim-preset-btn"', first + 1)
        block = self.js[idx:idx + 1200]
        # Should have getEffectivePrice called at least twice
        count = block.count("getEffectivePrice()")
        self.assertGreaterEqual(count, 2)

    def test_preset_still_shows_error_if_no_price(self):
        """If price still 0 after retry, error toast is shown."""
        first = self.js.index('".sim-preset-btn"')
        idx = self.js.index('".sim-preset-btn"', first + 1)
        block = self.js[idx:idx + 1200]
        self.assertIn("Fiyat verisi alınamadı", block)

    def test_geteffectiveprice_respects_limit_price(self):
        """For non-market orders, limit price is still preferred."""
        idx = self.js.index("function getEffectivePrice()")
        fn = self.js[idx:idx + 400]
        self.assertIn("currentType !== \"market\"", fn)
        self.assertIn("$limitPrice.value", fn)


# ══════════════════════════════════════════════════════════════════
# S) FAZ 64B — Journal Save: addEventListener Pattern
# ══════════════════════════════════════════════════════════════════

class TestJournalSaveAddeventListener(unittest.TestCase):
    """Journal prompt must use addEventListener instead of inline onclick."""

    @classmethod
    def setUpClass(cls):
        cls.js = _get_sim_js()

    def test_no_inline_onclick_in_journal(self):
        """showJournalPrompt must NOT use inline onclick for addToJournal."""
        idx = self.js.index("function showJournalPrompt(")
        fn = self.js[idx:idx + 1500]
        self.assertNotIn("onclick=\"addToJournal(", fn)

    def test_addeventlistener_for_journal_btn(self):
        """Journal add button uses addEventListener."""
        idx = self.js.index("function showJournalPrompt(")
        fn = self.js[idx:idx + 1500]
        self.assertIn("addEventListener", fn)

    def test_journal_add_btn_id(self):
        """Journal add button has dedicated ID for binding."""
        idx = self.js.index("function showJournalPrompt(")
        fn = self.js[idx:idx + 1500]
        self.assertIn("sim-journal-add-btn", fn)

    def test_dismiss_btn_addeventlistener(self):
        """Dismiss button also uses addEventListener, not inline onclick."""
        idx = self.js.index("function showJournalPrompt(")
        fn = self.js[idx:idx + 1500]
        self.assertIn("sim-journal-dismiss-btn", fn)

    def test_no_inline_onclick_dismiss(self):
        """Dismiss button must NOT use inline onclick."""
        idx = self.js.index("function showJournalPrompt(")
        fn = self.js[idx:idx + 1500]
        self.assertNotIn('onclick="this.parentElement', fn)

    def test_addtojournal_is_private_function(self):
        """addToJournal should be a private function, not on window."""
        self.assertNotIn("window.addToJournal", self.js)

    def test_addtojournal_function_exists(self):
        """addToJournal function defined in IIFE scope."""
        self.assertIn("function addToJournal(", self.js)

    def test_addtojournal_accepts_pos_object(self):
        """addToJournal takes position object, not individual args."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 100]
        self.assertIn("addToJournal(pos)", fn)

    def test_journal_posts_to_api(self):
        """addToJournal sends POST to /api/journal."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 800]
        self.assertIn('"/api/journal"', fn)

    def test_journal_sends_symbol(self):
        """Journal POST body includes symbol from pos object."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 800]
        self.assertIn("pos.symbol", fn)

    def test_journal_sends_current_price(self):
        """Journal POST body includes current_price."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 800]
        self.assertIn("pos.current_price", fn)

    def test_journal_shows_success_toast(self):
        """On success, shows toast with checkmark."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 1200]
        self.assertIn("İşlem günlüğe eklendi", fn)

    def test_journal_shows_error_toast(self):
        """On failure, shows error toast."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 1200]
        self.assertIn("Günlüğe eklenemedi", fn)

    def test_journal_sim_position_id_stringified(self):
        """sim_position_id is converted to String."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 1200]
        self.assertIn("String(pos.id", fn)

    def test_journal_catches_errors(self):
        """addToJournal has .catch handler."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 1200]
        self.assertIn(".catch(function(err)", fn)

    def test_journal_error_shows_message(self):
        """Catch handler shows error message."""
        idx = self.js.index("function addToJournal(")
        fn = self.js[idx:idx + 1200]
        self.assertIn("Günlük hatası", fn)


# ══════════════════════════════════════════════════════════════════
# T) FAZ 64B — Cache-bust version updated
# ══════════════════════════════════════════════════════════════════

class TestCacheBustVersion(unittest.TestCase):
    """Template must use updated cache-bust version."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(HTML_SIM)

    def test_cache_bust_is_64c(self):
        """Cache-bust version should be 64c."""
        self.assertIn("simulator.js') }}?v=64c", self.html)


if __name__ == "__main__":
    unittest.main()
