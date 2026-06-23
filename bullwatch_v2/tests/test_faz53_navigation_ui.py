# -*- coding: utf-8 -*-
"""FAZ 53 — Core UI Fixes / Navigation / Missing Modules Stabilization Tests.

Tests:
  - Sidebar navigation order & links
  - TradingView branding CSS removal
  - /chart route & chart controls
  - /copilot full page route
  - /settings page (public, no 401)
  - Portfolio demo fallback
  - Alert panel compact CSS
  - All navigation routes return 200
  - Chart controls JS integrity
  - Copilot template structure
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TESTING", "1")

from app import create_app


class _Base(unittest.TestCase):
    """Shared app/client setup."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()


# ════════════════════════════════════════════════════════════════════════
# 1. Navigation Route Accessibility (17 tests)
# ════════════════════════════════════════════════════════════════════════

class TestNavigationRoutes(_Base):
    """Every sidebar route must return 200."""

    def _get(self, path):
        r = self.client.get(path)
        self.assertIn(r.status_code, (200, 302),
                       f"{path} returned {r.status_code}")
        return r

    def test_root(self):
        self._get("/")

    def test_discover(self):
        self._get("/discover")

    def test_activity(self):
        self._get("/activity")

    def test_tv(self):
        self._get("/tv")

    def test_chart(self):
        r = self._get("/chart")
        self.assertEqual(r.status_code, 200)

    def test_trade(self):
        self._get("/trade")

    def test_screener(self):
        self._get("/screener")

    def test_opportunities(self):
        self._get("/opportunities")

    def test_portfolio(self):
        self._get("/portfolio")

    def test_copilot(self):
        r = self._get("/copilot")
        self.assertEqual(r.status_code, 200)

    def test_simulator(self):
        self._get("/simulator")

    def test_alerts(self):
        self._get("/alerts")

    def test_marketplace(self):
        self._get("/marketplace")

    def test_mentors(self):
        self._get("/mentors")

    def test_courses(self):
        self._get("/courses")

    def test_rooms(self):
        self._get("/rooms")

    def test_settings(self):
        r = self._get("/settings")
        self.assertEqual(r.status_code, 200,
                         "/settings must be public (not 401)")


# ════════════════════════════════════════════════════════════════════════
# 2. Sidebar Navigation (8 tests)
# ════════════════════════════════════════════════════════════════════════

class TestSidebarNavigation(_Base):
    """Sidebar in layout_terminal.html has correct links and order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tpl_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "layout_terminal.html",
        )
        with open(tpl_path, encoding="utf-8") as f:
            cls.sidebar_html = f.read()

    def test_sidebar_contains_discover(self):
        self.assertIn('href="/discover"', self.sidebar_html)

    def test_sidebar_contains_chart(self):
        self.assertIn('href="/tv"', self.sidebar_html)

    def test_sidebar_contains_copilot(self):
        self.assertIn('href="/copilot"', self.sidebar_html)

    def test_sidebar_contains_settings(self):
        self.assertIn('href="/settings"', self.sidebar_html)

    def test_sidebar_contains_portfolio(self):
        self.assertIn('href="/portfolio"', self.sidebar_html)

    def test_sidebar_contains_screener(self):
        self.assertIn('href="/screener"', self.sidebar_html)

    def test_sidebar_contains_trade(self):
        self.assertIn('href="/trade"', self.sidebar_html)

    def test_sidebar_order(self):
        """Key links appear in correct order."""
        order = ["/discover", "/activity", "/tv", "/trade",
                 "/screener", "/opportunities", "/portfolio",
                 "/copilot", "/simulator", "/alerts",
                 "/marketplace", "/settings"]
        positions = []
        for link in order:
            pos = self.sidebar_html.find(f'href="{link}"')
            self.assertGreater(pos, -1, f"{link} not in sidebar")
            positions.append(pos)
        self.assertEqual(positions, sorted(positions),
                         "Sidebar links are not in the required order")


# ════════════════════════════════════════════════════════════════════════
# 3. TradingView Branding CSS (3 tests)
# ════════════════════════════════════════════════════════════════════════

class TestTVBrandingCSS(_Base):
    """TradingView branding should be hidden via CSS."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        css_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "css", "components.css",
        )
        with open(css_path, encoding="utf-8") as f:
            cls.css = f.read()

    def test_tv_branding_hidden(self):
        self.assertIn(".tv-branding", self.css)

    def test_tv_watermark_hidden(self):
        self.assertIn(".tv-watermark", self.css)

    def test_chart_marketing_logo_hidden(self):
        self.assertIn(".chart-marketing-logo", self.css)


# ════════════════════════════════════════════════════════════════════════
# 4. Chart Page & Controls (8 tests)
# ════════════════════════════════════════════════════════════════════════

class TestChartPage(_Base):
    """Chart page at /chart and /tv must work, controls bar must exist."""

    def test_chart_route_exists(self):
        r = self.client.get("/chart")
        self.assertEqual(r.status_code, 200)

    def test_chart_renders_tv_template(self):
        r = self.client.get("/chart")
        html = r.data.decode()
        self.assertIn("ZKR Analiz", html)

    def test_tv_route_exists(self):
        r = self.client.get("/tv")
        self.assertEqual(r.status_code, 200)

    def test_chart_controls_bar_in_template(self):
        tpl = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "tv.html",
        )
        with open(tpl, encoding="utf-8") as f:
            html = f.read()
        self.assertIn("chartControlsBar", html)

    def test_chart_controls_js_exists(self):
        js = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "js", "chart_controls.js",
        )
        self.assertTrue(os.path.isfile(js))

    def test_chart_controls_js_has_symbols(self):
        js = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "js", "chart_controls.js",
        )
        with open(js, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("BTCUSDT", content)
        self.assertIn("ETHUSDT", content)

    def test_chart_controls_js_has_timeframes(self):
        js = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "js", "chart_controls.js",
        )
        with open(js, encoding="utf-8") as f:
            content = f.read()
        for tf in ("1m", "5m", "15m", "1h", "4h", "1d", "1w"):
            self.assertIn(tf, content)

    def test_chart_controls_js_has_indicators(self):
        js = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "js", "chart_controls.js",
        )
        with open(js, encoding="utf-8") as f:
            content = f.read()
        for ind in ("RSI", "MACD", "Bollinger"):
            self.assertIn(ind, content)


# ════════════════════════════════════════════════════════════════════════
# 5. Copilot Full Page (7 tests)
# ════════════════════════════════════════════════════════════════════════

class TestCopilotPage(_Base):
    """Copilot page at /copilot must render with chat UI."""

    def test_copilot_route_200(self):
        r = self.client.get("/copilot")
        self.assertEqual(r.status_code, 200)

    def test_copilot_has_chat_area(self):
        r = self.client.get("/copilot")
        html = r.data.decode()
        self.assertIn("copilot-messages", html)

    def test_copilot_has_input(self):
        r = self.client.get("/copilot")
        html = r.data.decode()
        self.assertIn("copilot-input", html)

    def test_copilot_has_quick_actions(self):
        r = self.client.get("/copilot")
        html = r.data.decode()
        self.assertIn("copilot-actions", html)

    def test_copilot_template_exists(self):
        tpl = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "copilot.html",
        )
        self.assertTrue(os.path.isfile(tpl))

    def test_copilot_extends_layout(self):
        tpl = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "copilot.html",
        )
        with open(tpl, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("layout_terminal.html", content)

    def test_copilot_has_send_button(self):
        r = self.client.get("/copilot")
        html = r.data.decode()
        self.assertIn("copilot-send", html)


# ════════════════════════════════════════════════════════════════════════
# 6. Settings Page Public Access (4 tests)
# ════════════════════════════════════════════════════════════════════════

class TestSettingsPublic(_Base):
    """Settings page must be accessible without login."""

    def test_settings_returns_200(self):
        r = self.client.get("/settings")
        self.assertEqual(r.status_code, 200)

    def test_settings_not_401(self):
        r = self.client.get("/settings")
        self.assertNotEqual(r.status_code, 401)

    def test_settings_not_redirect(self):
        r = self.client.get("/settings")
        self.assertNotIn(r.status_code, (301, 302))

    def test_settings_renders_html(self):
        r = self.client.get("/settings")
        ct = r.content_type or ""
        self.assertIn("text/html", ct)


# ════════════════════════════════════════════════════════════════════════
# 7. Portfolio Demo Fallback (6 tests)
# ════════════════════════════════════════════════════════════════════════

class TestPortfolioDemoFallback(_Base):
    """Portfolio demo endpoint & fallback must work."""

    def test_demo_portfolio_endpoint_exists(self):
        r = self.client.get("/api/demo/portfolio")
        self.assertEqual(r.status_code, 200)

    def test_demo_portfolio_returns_json(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        self.assertIsNotNone(data)

    def test_demo_portfolio_has_assets(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        self.assertIn("assets", data)
        self.assertGreater(len(data["assets"]), 0)

    def test_demo_portfolio_asset_has_symbol(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        asset = data["assets"][0]
        self.assertIn("symbol", asset)

    def test_demo_portfolio_has_demo_flag(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        self.assertTrue(data["assets"][0].get("demo"))

    def test_demo_portfolio_has_btc(self):
        r = self.client.get("/api/demo/portfolio")
        data = r.get_json()
        symbols = [a["symbol"] for a in data["assets"]]
        self.assertTrue(any("BTC" in s for s in symbols))


# ════════════════════════════════════════════════════════════════════════
# 8. Alert Panel CSS (3 tests)
# ════════════════════════════════════════════════════════════════════════

class TestAlertPanelCSS(_Base):
    """Alert box compact CSS must be present."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        css_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "css", "alerts.css",
        )
        with open(css_path, encoding="utf-8") as f:
            cls.css = f.read()

    def test_alert_box_max_height(self):
        self.assertIn("max-height", self.css)

    def test_alert_box_overflow(self):
        self.assertIn("overflow", self.css)

    def test_alert_box_class(self):
        self.assertIn(".alert-box", self.css)


# ════════════════════════════════════════════════════════════════════════
# 9. Chart Controls CSS in tv.html (4 tests)
# ════════════════════════════════════════════════════════════════════════

class TestChartControlsCSS(_Base):
    """Chart controls CSS classes must be defined in tv.html."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tpl = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "tv.html",
        )
        with open(tpl, encoding="utf-8") as f:
            cls.html = f.read()

    def test_cc_bar_class(self):
        self.assertIn(".cc-bar", self.html)

    def test_cc_select_class(self):
        self.assertIn(".cc-select", self.html)

    def test_cc_tf_btn_class(self):
        self.assertIn(".cc-tf-btn", self.html)

    def test_cc_fs_btn_class(self):
        self.assertIn(".cc-fs-btn", self.html)


# ════════════════════════════════════════════════════════════════════════
# 10. Template File Existence (5 tests)
# ════════════════════════════════════════════════════════════════════════

class TestTemplateFiles(_Base):
    """All required template files must exist."""

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_copilot_template(self):
        self.assertTrue(os.path.isfile(
            os.path.join(self._root, "templates", "copilot.html")))

    def test_tv_template(self):
        self.assertTrue(os.path.isfile(
            os.path.join(self._root, "templates", "tv.html")))

    def test_layout_terminal_template(self):
        self.assertTrue(os.path.isfile(
            os.path.join(self._root, "templates", "layout_terminal.html")))

    def test_chart_controls_js(self):
        self.assertTrue(os.path.isfile(
            os.path.join(self._root, "static", "js", "chart_controls.js")))

    def test_components_css(self):
        self.assertTrue(os.path.isfile(
            os.path.join(self._root, "static", "css", "components.css")))


if __name__ == "__main__":
    unittest.main()
