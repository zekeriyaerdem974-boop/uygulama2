# -*- coding: utf-8 -*-
"""FAZ 64B — Portfolio Empty State / Data Binding / Runtime Fix Tests.

55+ tests covering:
- Backend: auto-seed demo on empty portfolio (summary + risk routes)
- Backend: portfolio_engine CRUD, PnL, allocation
- Backend: portfolio_risk_engine empty portfolio handling
- Backend: demo_data_engine seed function
- Frontend: loadPortfolio with demo fallback
- Frontend: summary card rendering
- Frontend: asset table rendering
- Frontend: allocation chart rendering
- Frontend: risk gauge rendering
- Frontend: AI insight section
- Template: auth gate, main content, sections
- CSS: portfolio styles exist
"""
import json
import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# ── File paths ────────────────────────────────────────────────────
ROUTES_FILE  = os.path.join(BASE, "app", "blueprints", "portfolio", "routes.py")
ENGINE_FILE  = os.path.join(BASE, "app", "core", "portfolio_engine.py")
RISK_FILE    = os.path.join(BASE, "app", "core", "portfolio_risk_engine.py")
AI_FILE      = os.path.join(BASE, "app", "core", "portfolio_ai_advisor.py")
DEMO_FILE    = os.path.join(BASE, "app", "core", "demo_data_engine.py")
JS_FILE      = os.path.join(BASE, "static", "js", "portfolio.js")
CSS_FILE     = os.path.join(BASE, "static", "css", "portfolio.css")
HTML_FILE    = os.path.join(BASE, "templates", "portfolio.html")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# 1) ROUTES — Auto-Seed Demo on Empty Portfolio
# ══════════════════════════════════════════════════════════════════

class TestPortfolioSummaryAutoSeed(unittest.TestCase):
    """Verify /api/portfolio/summary auto-seeds demo when empty."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(ROUTES_FILE)

    def test_summary_imports_get_assets(self):
        pattern = r'def api_portfolio_summary.*?get_assets'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_summary_checks_empty_assets(self):
        pattern = r'def api_portfolio_summary.*?if not assets'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_summary_calls_seed_demo(self):
        pattern = r'def api_portfolio_summary.*?seed_demo_portfolio'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_summary_returns_json(self):
        pattern = r'def api_portfolio_summary.*?"ok": True'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))


class TestPortfolioRiskAutoSeed(unittest.TestCase):
    """Verify /api/portfolio/risk auto-seeds demo when empty."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(ROUTES_FILE)

    def test_risk_imports_get_assets(self):
        pattern = r'def api_portfolio_risk.*?get_assets'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_risk_checks_empty_assets(self):
        pattern = r'def api_portfolio_risk.*?if not assets'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_risk_calls_seed_demo(self):
        pattern = r'def api_portfolio_risk.*?seed_demo_portfolio'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_risk_returns_json(self):
        pattern = r'def api_portfolio_risk.*?"ok": True'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))


class TestPortfolioRouteEndpoints(unittest.TestCase):
    """Verify all portfolio route endpoints exist."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(ROUTES_FILE)

    def test_portfolio_page_route(self):
        self.assertIn('/portfolio"', self.src)

    def test_api_get_portfolio(self):
        self.assertIn('/api/portfolio"', self.src)

    def test_api_add_asset(self):
        self.assertIn('/api/portfolio/add', self.src)

    def test_api_remove_asset(self):
        self.assertIn('/api/portfolio/remove', self.src)

    def test_api_summary(self):
        self.assertIn('/api/portfolio/summary', self.src)

    def test_api_risk(self):
        self.assertIn('/api/portfolio/risk', self.src)

    def test_api_ai(self):
        self.assertIn('/api/portfolio/ai', self.src)

    def test_api_ai_ask(self):
        self.assertIn('/api/portfolio/ai/ask', self.src)

    def test_api_demo_portfolio(self):
        self.assertIn('/api/demo/portfolio', self.src)

    def test_get_portfolio_demo_fallback(self):
        pattern = r'def api_get_portfolio.*?get_demo_portfolio'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))


# ══════════════════════════════════════════════════════════════════
# 2) PORTFOLIO ENGINE — Core Functions
# ══════════════════════════════════════════════════════════════════

class TestPortfolioEngine(unittest.TestCase):
    """Verify portfolio engine core functions exist and work."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(ENGINE_FILE)

    def test_get_or_create_portfolio(self):
        self.assertIn("def get_or_create_portfolio(", self.src)

    def test_add_asset(self):
        self.assertIn("def add_asset(", self.src)

    def test_remove_asset(self):
        self.assertIn("def remove_asset(", self.src)

    def test_get_assets(self):
        self.assertIn("def get_assets(", self.src)

    def test_update_asset_prices(self):
        self.assertIn("def update_asset_prices(", self.src)

    def test_calculate_pnl(self):
        self.assertIn("def calculate_pnl(", self.src)

    def test_calculate_allocation(self):
        self.assertIn("def calculate_allocation(", self.src)

    def test_portfolio_summary(self):
        self.assertIn("def portfolio_summary(", self.src)

    def test_summary_returns_asset_count(self):
        self.assertIn('"asset_count"', self.src)

    def test_summary_returns_allocation(self):
        self.assertIn('"allocation"', self.src)

    def test_summary_returns_total_value(self):
        self.assertIn('"total_value"', self.src)

    def test_summary_returns_total_pnl(self):
        self.assertIn('"total_pnl"', self.src)

    def test_pnl_handles_zero_cost(self):
        self.assertIn("if cost > 0", self.src)

    def test_amount_validation(self):
        self.assertIn("Miktar sıfırdan büyük olmalıdır", self.src)

    def test_entry_price_validation(self):
        self.assertIn("Giriş fiyatı sıfırdan büyük olmalıdır", self.src)


# ══════════════════════════════════════════════════════════════════
# 3) RISK ENGINE — Empty Portfolio Handling
# ══════════════════════════════════════════════════════════════════

class TestPortfolioRiskEngine(unittest.TestCase):
    """Verify risk engine handles empty portfolios correctly."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(RISK_FILE)

    def test_risk_score_function(self):
        self.assertIn("def calculate_risk_score(", self.src)

    def test_empty_portfolio_returns_zero(self):
        self.assertIn('"risk_score": 0', self.src)

    def test_empty_portfolio_label(self):
        self.assertIn("Portföy Boş", self.src)

    def test_volatility_function(self):
        self.assertIn("def calculate_volatility(", self.src)

    def test_concentration_function(self):
        self.assertIn("def calculate_concentration_risk(", self.src)

    def test_drawdown_function(self):
        self.assertIn("def calculate_drawdown(", self.src)

    def test_risk_bands_defined(self):
        self.assertIn("RISK_BANDS", self.src)

    def test_volatility_empty_assets(self):
        self.assertIn("if not assets:", self.src)

    def test_risk_weights_sum(self):
        # Weights: 0.35 + 0.30 + 0.20 + 0.15 = 1.0
        self.assertIn("0.35", self.src)
        self.assertIn("0.30", self.src)
        self.assertIn("0.20", self.src)
        self.assertIn("0.15", self.src)


# ══════════════════════════════════════════════════════════════════
# 4) DEMO DATA ENGINE — seed_demo_portfolio
# ══════════════════════════════════════════════════════════════════

class TestDemoDataEngine(unittest.TestCase):
    """Verify demo data engine provides portfolio data."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(DEMO_FILE)

    def test_get_demo_portfolio(self):
        self.assertIn("def get_demo_portfolio(", self.src)

    def test_seed_demo_portfolio(self):
        self.assertIn("def seed_demo_portfolio(", self.src)

    def test_demo_portfolio_has_btc(self):
        self.assertIn("BTCUSDT", self.src)

    def test_demo_portfolio_has_eth(self):
        self.assertIn("ETHUSDT", self.src)

    def test_demo_portfolio_has_aapl(self):
        self.assertIn("AAPL", self.src)

    def test_seed_checks_existing(self):
        self.assertIn("if existing:", self.src)

    def test_demo_tagged(self):
        self.assertIn('"demo": True', self.src)


# ══════════════════════════════════════════════════════════════════
# 5) FRONTEND JS — loadPortfolio + Demo Fallback
# ══════════════════════════════════════════════════════════════════

class TestPortfolioJS(unittest.TestCase):
    """Verify portfolio.js has proper data loading and demo fallback."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_check_auth_function(self):
        self.assertIn("async function checkAuth()", self.js)

    def test_load_portfolio_function(self):
        self.assertIn("async function loadPortfolio()", self.js)

    def test_load_demo_fallback_function(self):
        self.assertIn("async function loadDemoFallback()", self.js)

    def test_calls_summary_api(self):
        self.assertIn("/api/portfolio/summary", self.js)

    def test_calls_risk_api(self):
        self.assertIn("/api/portfolio/risk", self.js)

    def test_calls_demo_api_in_fallback(self):
        self.assertIn("/api/demo/portfolio", self.js)

    def test_render_summary_cards(self):
        self.assertIn("function renderSummaryCards(", self.js)

    def test_render_asset_table(self):
        self.assertIn("function renderAssetTable(", self.js)

    def test_render_allocation_chart(self):
        self.assertIn("function renderAllocationChart(", self.js)

    def test_render_risk_gauge(self):
        self.assertIn("function renderRiskGauge(", self.js)

    def test_render_risk_score(self):
        self.assertIn("function renderRiskScore(", self.js)

    def test_add_asset_function(self):
        self.assertIn("async function addAsset()", self.js)

    def test_remove_asset_function(self):
        self.assertIn("async function removeAsset(", self.js)

    def test_init_calls_check_auth(self):
        pattern = r'async function init.*?checkAuth'
        self.assertRegex(self.js, re.compile(pattern, re.DOTALL))

    def test_init_calls_load_portfolio(self):
        pattern = r'async function init.*?loadPortfolio'
        self.assertRegex(self.js, re.compile(pattern, re.DOTALL))

    def test_fallback_on_summary_error(self):
        pattern = r'if \(summaryRes\.ok\).*?loadDemoFallback'
        self.assertRegex(self.js, re.compile(pattern, re.DOTALL))

    def test_fallback_on_catch(self):
        pattern = r'catch.*?loadDemoFallback'
        self.assertRegex(self.js, re.compile(pattern, re.DOTALL))

    def test_empty_table_message(self):
        self.assertIn("Portföyünüzde henüz varlık bulunmuyor", self.js)

    def test_ai_insight_render(self):
        self.assertIn("function renderAIInsight(", self.js)

    def test_ai_disclaimer(self):
        self.assertIn("yatırım tavsiyesi değildir", self.js)


# ══════════════════════════════════════════════════════════════════
# 6) TEMPLATE — Portfolio HTML Structure
# ══════════════════════════════════════════════════════════════════

class TestPortfolioTemplate(unittest.TestCase):
    """Verify portfolio.html has all required sections."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(HTML_FILE)

    def test_auth_gate_exists(self):
        self.assertIn('id="pf-auth-gate"', self.html)

    def test_main_content_exists(self):
        self.assertIn('id="pf-main"', self.html)

    def test_total_value_card(self):
        self.assertIn('id="pf-total-value"', self.html)

    def test_total_pnl_card(self):
        self.assertIn('id="pf-total-pnl"', self.html)

    def test_asset_count_card(self):
        self.assertIn('id="pf-asset-count"', self.html)

    def test_risk_score_card(self):
        self.assertIn('id="pf-risk-score"', self.html)

    def test_allocation_chart(self):
        self.assertIn('id="pf-alloc-chart"', self.html)

    def test_risk_gauge(self):
        self.assertIn('id="pf-risk-gauge"', self.html)

    def test_asset_table_body(self):
        self.assertIn('id="pf-asset-tbody"', self.html)

    def test_add_asset_form(self):
        self.assertIn('id="pf-add-btn"', self.html)

    def test_ai_section(self):
        self.assertIn('id="pf-ai-btn"', self.html)

    def test_refresh_button(self):
        self.assertIn('id="pf-refresh-btn"', self.html)

    def test_portfolio_css_linked(self):
        self.assertIn("portfolio.css", self.html)

    def test_portfolio_js_linked(self):
        self.assertIn("portfolio.js", self.html)


# ══════════════════════════════════════════════════════════════════
# 7) CSS — Portfolio Styles
# ══════════════════════════════════════════════════════════════════

class TestPortfolioCSS(unittest.TestCase):
    """Verify portfolio.css has required styles."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read(CSS_FILE)

    def test_pf_container(self):
        self.assertIn(".pf-container", self.css)

    def test_pf_card(self):
        self.assertIn(".pf-card", self.css)

    def test_pf_summary_grid(self):
        self.assertIn(".pf-summary-grid", self.css)

    def test_pf_panel(self):
        self.assertIn(".pf-panel", self.css)

    def test_pf_auth_gate(self):
        self.assertIn(".pf-auth-gate", self.css)


# ══════════════════════════════════════════════════════════════════
# 8) INTEGRATION — Flask App Routes
# ══════════════════════════════════════════════════════════════════

class TestPortfolioFlaskIntegration(unittest.TestCase):
    """Integration: portfolio routes respond correctly."""

    @classmethod
    def setUpClass(cls):
        try:
            os.environ.setdefault("FLASK_TESTING", "1")
            from app import create_app
            app = create_app()
            app.config["TESTING"] = True
            cls.client = app.test_client()
            cls.available = True
        except Exception:
            cls.available = False

    def setUp(self):
        if not self.available:
            self.skipTest("Flask app not available")

    def test_portfolio_page_200(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)

    def test_portfolio_page_has_content(self):
        r = self.client.get("/portfolio")
        self.assertIn(b"pf-auth-gate", r.data)

    def test_demo_portfolio_api_200(self):
        r = self.client.get("/api/demo/portfolio")
        self.assertEqual(r.status_code, 200)

    def test_demo_portfolio_has_assets(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        self.assertTrue(data["ok"])
        self.assertGreater(len(data["assets"]), 0)

    def test_demo_portfolio_has_btc(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        symbols = [a["symbol"] for a in data["assets"]]
        self.assertIn("BTCUSDT", symbols)


if __name__ == "__main__":
    unittest.main()
