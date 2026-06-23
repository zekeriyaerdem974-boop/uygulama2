# -*- coding: utf-8 -*-
"""FAZ 16 Tests — Multi-Market Trading Terminal.

Tests:
  - Backend: yahoo_client, stocks_data, bist_data, forex_data, commodities_data
  - API: /api/stocks/*, /api/bist/*, /api/forex/*, /api/commodities/*
  - Frontend: market tabs in trade.html, market state in trade.js, CSS
  - News: market-aware news endpoints
  - Live server verification
"""
import json
import os
import re
import sys
import unittest

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

LIVE = "http://127.0.0.1:34000"


def _live_ok():
    try:
        r = requests.get(f"{LIVE}/trade", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
# 1. Backend Core Module Structure
# ══════════════════════════════════════════════════════════════════════════
class TestCoreModuleStructure(unittest.TestCase):
    """Verify new core data modules exist and have correct interface."""

    def test_yahoo_client_exists(self):
        path = os.path.join(BASE, "app", "core", "yahoo_client.py")
        self.assertTrue(os.path.isfile(path))

    def test_stocks_data_exists(self):
        path = os.path.join(BASE, "app", "core", "stocks_data.py")
        self.assertTrue(os.path.isfile(path))

    def test_bist_data_exists(self):
        path = os.path.join(BASE, "app", "core", "bist_data.py")
        self.assertTrue(os.path.isfile(path))

    def test_forex_data_exists(self):
        path = os.path.join(BASE, "app", "core", "forex_data.py")
        self.assertTrue(os.path.isfile(path))

    def test_commodities_data_exists(self):
        path = os.path.join(BASE, "app", "core", "commodities_data.py")
        self.assertTrue(os.path.isfile(path))

    def test_stocks_data_has_methods(self):
        src = open(os.path.join(BASE, "app", "core", "stocks_data.py")).read()
        self.assertIn("get_symbols", src)
        self.assertIn("get_ticker_single", src)
        self.assertIn("get_klines", src)
        self.assertIn("StocksDataService", src)

    def test_bist_data_has_symbols(self):
        src = open(os.path.join(BASE, "app", "core", "bist_data.py")).read()
        self.assertIn("THYAO.IS", src)
        self.assertIn("ASELS.IS", src)
        self.assertIn("GARAN.IS", src)

    def test_forex_data_has_symbols(self):
        src = open(os.path.join(BASE, "app", "core", "forex_data.py")).read()
        self.assertIn("EURUSD=X", src)
        self.assertIn("USDTRY=X", src)
        self.assertIn("GBPUSD=X", src)

    def test_commodities_data_has_symbols(self):
        src = open(os.path.join(BASE, "app", "core", "commodities_data.py")).read()
        self.assertIn("GC=F", src)
        self.assertIn("SI=F", src)
        self.assertIn("CL=F", src)

    def test_yahoo_client_has_functions(self):
        src = open(os.path.join(BASE, "app", "core", "yahoo_client.py")).read()
        self.assertIn("def get_ticker", src)
        self.assertIn("def get_klines", src)
        self.assertIn("def get_symbols_info", src)


# ══════════════════════════════════════════════════════════════════════════
# 2. Blueprint Structure
# ══════════════════════════════════════════════════════════════════════════
class TestBlueprintStructure(unittest.TestCase):
    """Verify markets blueprint exists and is registered."""

    def test_markets_blueprint_init(self):
        path = os.path.join(BASE, "app", "blueprints", "markets", "__init__.py")
        self.assertTrue(os.path.isfile(path))
        src = open(path).read()
        self.assertIn("markets_bp", src)

    def test_markets_routes_file(self):
        path = os.path.join(BASE, "app", "blueprints", "markets", "routes.py")
        self.assertTrue(os.path.isfile(path))

    def test_markets_registered_in_monolith(self):
        src = open(os.path.join(BASE, "legacy_monolith.py")).read()
        self.assertIn("from app.blueprints.markets import markets_bp", src)
        self.assertIn("app.register_blueprint(markets_bp)", src)

    def test_routes_have_all_endpoints(self):
        src = open(os.path.join(BASE, "app", "blueprints", "markets", "routes.py")).read()
        for market in ["stocks", "bist", "forex", "commodities"]:
            self.assertIn(f"/api/{market}/symbols", src)
            self.assertIn(f"/api/{market}/ticker", src)
            self.assertIn(f"/api/{market}/klines", src)


# ══════════════════════════════════════════════════════════════════════════
# 3. Frontend — HTML Market Tabs
# ══════════════════════════════════════════════════════════════════════════
class TestTradeHtml(unittest.TestCase):
    """Verify trade.html has market tabs."""

    @classmethod
    def setUpClass(cls):
        cls.html = open(os.path.join(BASE, "templates", "trade.html")).read()

    def test_market_tab_bar_exists(self):
        self.assertIn('market-tab-bar', self.html)

    def test_crypto_tab(self):
        self.assertIn('data-market="crypto"', self.html)

    def test_stocks_tab(self):
        self.assertIn('data-market="stocks"', self.html)

    def test_bist_tab(self):
        self.assertIn('data-market="bist"', self.html)

    def test_forex_tab(self):
        self.assertIn('data-market="forex"', self.html)

    def test_commodities_tab(self):
        self.assertIn('data-market="commodities"', self.html)

    def test_market_badge_in_watchlist(self):
        self.assertIn('wlMarketBadge', self.html)

    def test_crypto_is_default_active(self):
        # The crypto tab should have 'active' class
        m = re.search(r'market-tab active.*?data-market="(\w+)"', self.html)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "crypto")


# ══════════════════════════════════════════════════════════════════════════
# 4. Frontend — JavaScript Market State
# ══════════════════════════════════════════════════════════════════════════
class TestTradeJs(unittest.TestCase):
    """Verify trade.js has market state management."""

    @classmethod
    def setUpClass(cls):
        cls.js = open(os.path.join(BASE, "static", "js", "trade.js")).read()

    def test_market_config_exists(self):
        self.assertIn('MARKET_CONFIG', self.js)

    def test_market_config_has_all_markets(self):
        for m in ['crypto', 'stocks', 'bist', 'forex', 'commodities']:
            self.assertIn(f"  {m}:", self.js)

    def test_active_market_variable(self):
        self.assertIn("activeMarket", self.js)

    def test_market_tab_manager(self):
        self.assertIn("marketTabManager", self.js)

    def test_switch_market_function(self):
        self.assertIn("switchMarket", self.js)

    def test_default_symbols_correct(self):
        self.assertIn("defaultSymbol: 'BTCUSDT'", self.js)
        self.assertIn("defaultSymbol: 'AAPL'", self.js)
        self.assertIn("defaultSymbol: 'THYAO.IS'", self.js)
        self.assertIn("defaultSymbol: 'EURUSD=X'", self.js)
        self.assertIn("defaultSymbol: 'GC=F'", self.js)

    def test_market_aware_klines_endpoint(self):
        self.assertIn("mc.klinesEndpoint", self.js)

    def test_market_aware_signals(self):
        self.assertIn("mc.hasSignals", self.js)

    def test_market_aware_orderflow(self):
        self.assertIn("mc.hasOrderflow", self.js)

    def test_market_aware_liquidation(self):
        self.assertIn("mc.hasLiquidation", self.js)

    def test_localstorage_market_key(self):
        self.assertIn("bw_active_market", self.js)

    def test_news_market_aware(self):
        self.assertIn("setMarketDefault", self.js)
        self.assertIn("mc.newsType", self.js)

    def test_unavailable_messages(self):
        self.assertIn("only available for Crypto market", self.js)


# ══════════════════════════════════════════════════════════════════════════
# 5. Frontend — CSS Market Styles
# ══════════════════════════════════════════════════════════════════════════
class TestTradeCss(unittest.TestCase):
    """Verify trade.css has market tab styles."""

    @classmethod
    def setUpClass(cls):
        cls.css = open(os.path.join(BASE, "static", "css", "trade.css")).read()

    def test_market_tab_bar_styles(self):
        self.assertIn('.market-tab-bar', self.css)

    def test_market_tab_styles(self):
        self.assertIn('.market-tab', self.css)

    def test_market_dots(self):
        for dot in ['crypto-dot', 'stocks-dot', 'bist-dot', 'forex-dot', 'comm-dot']:
            self.assertIn(dot, self.css)

    def test_market_badges(self):
        for badge in ['badge-crypto', 'badge-stocks', 'badge-bist', 'badge-forex', 'badge-commodities']:
            self.assertIn(badge, self.css)

    def test_panel_unavailable(self):
        self.assertIn('.panel-unavailable', self.css)


# ══════════════════════════════════════════════════════════════════════════
# 6. News Service — Market-Aware
# ══════════════════════════════════════════════════════════════════════════
class TestNewsMarketAware(unittest.TestCase):
    """Verify news service supports market-specific news."""

    def test_news_service_has_market_methods(self):
        src = open(os.path.join(BASE, "app", "core", "news_service.py")).read()
        self.assertIn("fetch_stocks_news", src)
        self.assertIn("fetch_bist_news", src)
        self.assertIn("fetch_forex_news", src)
        self.assertIn("fetch_commodities_news", src)

    def test_google_news_market_fetchers(self):
        src = open(os.path.join(BASE, "app", "core", "news_service.py")).read()
        self.assertIn("fetch_google_news_stocks", src)
        self.assertIn("fetch_google_news_bist", src)
        self.assertIn("fetch_google_news_forex", src)
        self.assertIn("fetch_google_news_commodities", src)

    def test_news_routes_support_market_types(self):
        src = open(os.path.join(BASE, "app", "blueprints", "news", "routes.py")).read()
        for t in ['stocks', 'bist', 'forex', 'commodities']:
            self.assertIn(f'"{t}"', src)


# ══════════════════════════════════════════════════════════════════════════
# 7. Live Server — API Endpoints
# ══════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(_live_ok(), "Server not running on :34000")
class TestLiveEndpoints(unittest.TestCase):
    """Verify all market endpoints return valid data from live server."""

    def test_trade_page_loads(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn("market-tab-bar", r.text)

    def test_trade_page_has_market_tabs(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        for market in ['crypto', 'stocks', 'bist', 'forex', 'commodities']:
            self.assertIn(f'data-market="{market}"', r.text)

    # ── Stocks ──
    def test_stocks_symbols(self):
        r = requests.get(f"{LIVE}/api/stocks/symbols", timeout=30)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(js.get("count", 0), 0)
        symbols = [i["symbol"] for i in js["items"]]
        self.assertIn("AAPL", symbols)

    def test_stocks_ticker(self):
        r = requests.get(f"{LIVE}/api/stocks/ticker?symbol=AAPL", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(float(js.get("lastPrice", 0)), 0)

    def test_stocks_klines(self):
        r = requests.get(f"{LIVE}/api/stocks/klines?symbol=AAPL&interval=1d&limit=50", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(len(js.get("candles", [])), 0)
        self.assertIn("open", js["candles"][0])

    # ── BIST ──
    def test_bist_symbols(self):
        r = requests.get(f"{LIVE}/api/bist/symbols", timeout=30)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(js.get("count", 0), 0)
        symbols = [i["symbol"] for i in js["items"]]
        self.assertIn("THYAO.IS", symbols)

    def test_bist_klines(self):
        r = requests.get(f"{LIVE}/api/bist/klines?symbol=THYAO.IS&interval=1d&limit=50", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(len(js.get("candles", [])), 0)

    # ── Forex ──
    def test_forex_symbols(self):
        r = requests.get(f"{LIVE}/api/forex/symbols", timeout=30)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(js.get("count", 0), 0)
        symbols = [i["symbol"] for i in js["items"]]
        self.assertIn("EURUSD=X", symbols)

    def test_forex_klines(self):
        r = requests.get(f"{LIVE}/api/forex/klines?symbol=EURUSD=X&interval=1d&limit=50", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(len(js.get("candles", [])), 0)

    # ── Commodities ──
    def test_commodities_symbols(self):
        r = requests.get(f"{LIVE}/api/commodities/symbols", timeout=30)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(js.get("count", 0), 0)
        symbols = [i["symbol"] for i in js["items"]]
        self.assertIn("GC=F", symbols)

    def test_commodities_klines(self):
        r = requests.get(f"{LIVE}/api/commodities/klines?symbol=GC=F&interval=1d&limit=50", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(len(js.get("candles", [])), 0)

    # ── Market-aware news ──
    def test_news_stocks_type(self):
        r = requests.get(f"{LIVE}/api/news?type=stocks", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))

    def test_news_bist_type(self):
        r = requests.get(f"{LIVE}/api/news?type=bist", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))

    # ── Crypto still works ──
    def test_crypto_klines_still_work(self):
        r = requests.get(f"{LIVE}/api/market/klines?symbol=BTCUSDT&interval=15m&limit=50", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreater(len(js.get("candles", [])), 0)

    def test_crypto_symbols_still_work(self):
        r = requests.get(f"{LIVE}/api/market/symbols", timeout=15)
        js = r.json()
        self.assertTrue(js.get("ok"))


# ══════════════════════════════════════════════════════════════════════════
# 8. Structural Integrity
# ══════════════════════════════════════════════════════════════════════════
class TestStructuralIntegrity(unittest.TestCase):
    """Ensure existing functionality is not broken."""

    def test_existing_test_files_exist(self):
        for f in ["test_faz15.py"]:
            path = os.path.join(BASE, "tests", f)
            self.assertTrue(os.path.isfile(path), f"{f} missing")

    def test_trade_html_still_has_analysis_tabs(self):
        html = open(os.path.join(BASE, "templates", "trade.html")).read()
        for tab in ['signals', 'orderflow', 'liquidation', 'patterns', 'news', 'copilot']:
            self.assertIn(f'data-tab="{tab}"', html)

    def test_trade_js_still_has_all_managers(self):
        js = open(os.path.join(BASE, "static", "js", "trade.js")).read()
        for mgr in ['chartManager', 'indicatorManager', 'indicatorOverlayManager',
                     'patternOverlayManager', 'signalManager', 'orderflowManager',
                     'liquidationManager', 'aiManager', 'newsManager', 'watchlistManager']:
            self.assertIn(mgr, js)

    def test_no_duplicate_main(self):
        js = open(os.path.join(BASE, "static", "js", "trade.js")).read()
        count = js.count("async function main()")
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
