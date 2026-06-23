# -*- coding: utf-8 -*-
"""FAZ 18 Tests — Multi-Chart Layout System.

Tests:
  - Static file existence (multichart.js, multichart.css)
  - MultiChartManager JS module structure
  - Trade HTML template changes (mcGrid, multichart assets)
  - Trade.js integration (FAZ 18 hooks)
  - CSS grid layout definitions
  - Live server: /trade page loads, layout selector present
  - Live server: 2-chart and 4-chart layouts
  - Live server: different symbols load correctly
  - Live server: indicators & patterns still work
  - Regression: existing endpoints still functional
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


# ══════════════════════════════════════════════════════════════════════
# 1. Static Files & Module Structure
# ══════════════════════════════════════════════════════════════════════


class TestMultiChartFiles(unittest.TestCase):
    """Verify multichart static files exist and have expected content."""

    def test_multichart_js_exists(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        self.assertTrue(os.path.isfile(path), "multichart.js missing")

    def test_multichart_css_exists(self):
        path = os.path.join(BASE, "static", "css", "multichart.css")
        self.assertTrue(os.path.isfile(path), "multichart.css missing")

    def test_multichart_js_defines_manager(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("MultiChartManager", content)
        self.assertIn("const MultiChartManager", content)

    def test_multichart_js_has_public_api(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        expected = [
            "init", "setLayout", "setSymbol", "setTimeframe",
            "updateAllSlots", "onWatchlistSelect",
            "isMultiMode", "getLayout", "getActiveSlotId",
            "refreshPatterns",
        ]
        for fn in expected:
            self.assertIn(fn, content, f"Missing public function: {fn}")

    def test_multichart_js_has_chart_creation(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("_createSlot", content)
        self.assertIn("_destroySlot", content)
        self.assertIn("LightweightCharts.createChart", content)

    def test_multichart_js_has_layout_options(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("mc-layout-", content)
        self.assertIn("_applyLayout", content)
        self.assertIn("setLayout", content)

    def test_multichart_js_has_indicator_overlays(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("_updateOverlays", content)
        self.assertIn("IndicatorEngine.ema", content)
        self.assertIn("IndicatorEngine.bollinger", content)

    def test_multichart_js_has_pattern_overlays(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("_updatePatterns", content)
        self.assertIn("PatternEngine.detectSwings", content)
        self.assertIn("_drawSlotSR", content)

    def test_multichart_js_has_persistence(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("bw_mc_layout", content)
        self.assertIn("bw_mc_slots", content)
        self.assertIn("_saveState", content)
        self.assertIn("_loadState", content)

    def test_multichart_js_default_symbols(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("BTCUSDT", content)
        self.assertIn("ETHUSDT", content)
        self.assertIn("AAPL", content)
        self.assertIn("THYAO.IS", content)

    def test_multichart_js_max_4_charts(self):
        path = os.path.join(BASE, "static", "js", "multichart.js")
        content = open(path, encoding="utf-8").read()
        self.assertIn("MAX_SLOTS = 4", content)


# ══════════════════════════════════════════════════════════════════════
# 2. CSS Layout Definitions
# ══════════════════════════════════════════════════════════════════════


class TestMultiChartCSS(unittest.TestCase):
    """Verify multichart CSS has expected layout rules."""

    def setUp(self):
        path = os.path.join(BASE, "static", "css", "multichart.css")
        self.css = open(path, encoding="utf-8").read()

    def test_layout_selector_styles(self):
        self.assertIn(".mc-layout-selector", self.css)
        self.assertIn(".mc-layout-btn", self.css)
        self.assertIn(".mc-layout-btn.active", self.css)

    def test_grid_layout_styles(self):
        self.assertIn(".mc-grid", self.css)
        self.assertIn(".mc-layout-2", self.css)
        self.assertIn(".mc-layout-4", self.css)

    def test_grid_2_columns(self):
        self.assertIn("grid-template-columns: 1fr 1fr", self.css)

    def test_grid_4_has_rows(self):
        self.assertIn("grid-template-rows: 1fr 1fr", self.css)

    def test_slot_styles(self):
        self.assertIn(".mc-slot", self.css)
        self.assertIn(".mc-active", self.css)
        self.assertIn(".mc-toolbar", self.css)

    def test_chart_area_styles(self):
        self.assertIn(".mc-chart-area", self.css)
        self.assertIn("background: #000", self.css)

    def test_slot_toolbar_styles(self):
        self.assertIn(".mc-sym-wrap", self.css)
        self.assertIn(".mc-tf-group", self.css)
        self.assertIn(".mc-tf-btn", self.css)

    def test_indicator_dropdown_styles(self):
        self.assertIn(".mc-ind-wrap", self.css)
        self.assertIn(".mc-ind-dropdown", self.css)
        self.assertIn(".mc-ind-open", self.css)

    def test_responsive_rules(self):
        self.assertIn("@media", self.css)
        self.assertIn("768px", self.css)


# ══════════════════════════════════════════════════════════════════════
# 3. Trade HTML Template Changes
# ══════════════════════════════════════════════════════════════════════


class TestTradeHTMLChanges(unittest.TestCase):
    """Verify trade.html includes multichart assets and grid container."""

    def setUp(self):
        path = os.path.join(BASE, "templates", "trade.html")
        self.html = open(path, encoding="utf-8").read()

    def test_multichart_css_linked(self):
        self.assertIn("multichart.css", self.html)

    def test_multichart_js_loaded(self):
        self.assertIn("multichart.js", self.html)

    def test_mc_grid_container(self):
        self.assertIn('id="mcGrid"', self.html)
        self.assertIn('class="mc-grid"', self.html)

    def test_mc_grid_initially_hidden(self):
        self.assertIn('style="display:none"', self.html)

    def test_original_chart_elements_preserved(self):
        self.assertIn('id="chartArea"', self.html)
        self.assertIn('class="chart-header"', self.html)
        self.assertIn('class="indicator-strip"', self.html)

    def test_script_load_order(self):
        """multichart.js should load after trade.js (for global access)."""
        idx_trade = self.html.index("trade.js")
        idx_mc = self.html.index("multichart.js")
        self.assertGreater(idx_mc, idx_trade,
                           "multichart.js must load after trade.js")

    def test_indicators_js_preserved(self):
        self.assertIn("indicators.js", self.html)

    def test_patterns_js_preserved(self):
        self.assertIn("patterns.js", self.html)


# ══════════════════════════════════════════════════════════════════════
# 4. Trade.js Integration
# ══════════════════════════════════════════════════════════════════════


class TestTradeJSIntegration(unittest.TestCase):
    """Verify trade.js has FAZ 18 multi-chart integration hooks."""

    def setUp(self):
        path = os.path.join(BASE, "static", "js", "trade.js")
        self.js = open(path, encoding="utf-8").read()

    def test_refreshfast_multimode_check(self):
        self.assertIn("MultiChartManager.isMultiMode()", self.js)
        self.assertIn("MultiChartManager.updateAllSlots()", self.js)

    def test_watchlist_multimode_check(self):
        self.assertIn("MultiChartManager.onWatchlistSelect", self.js)

    def test_switchmarket_multimode_check(self):
        # switchMarket should have multi-mode early return
        idx = self.js.index("async function switchMarket")
        section = self.js[idx:idx + 800]
        self.assertIn("MultiChartManager", section)

    def test_main_init_multichart(self):
        self.assertIn("MultiChartManager.init()", self.js)

    def test_polling_multimode_check(self):
        # Fast polling should skip in multi-mode
        count = self.js.count("MultiChartManager.isMultiMode()")
        self.assertGreaterEqual(count, 5, "Need at least 5 multi-mode checks")

    def test_pattern_toggle_multichart_hook(self):
        self.assertIn("MultiChartManager.refreshPatterns()", self.js)

    def test_original_chartmanager_preserved(self):
        self.assertIn("const chartManager", self.js)
        self.assertIn("chartManager.init()", self.js)
        self.assertIn("chartManager.load()", self.js)

    def test_original_indicator_manager_preserved(self):
        self.assertIn("const indicatorManager", self.js)
        self.assertIn("indicatorManager.init()", self.js)

    def test_original_pattern_manager_preserved(self):
        self.assertIn("const patternOverlayManager", self.js)
        self.assertIn("patternOverlayManager.init()", self.js)


# ══════════════════════════════════════════════════════════════════════
# 5. Live Server Tests
# ══════════════════════════════════════════════════════════════════════


@unittest.skipUnless(_live_ok(), "Live server not running on :34000")
class TestLiveTradePageMultiChart(unittest.TestCase):
    """Verify live /trade page has multi-chart elements."""

    def test_trade_page_loads(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertEqual(r.status_code, 200)

    def test_multichart_css_linked(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertIn("multichart.css", r.text)

    def test_multichart_js_loaded(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertIn("multichart.js", r.text)

    def test_mc_grid_present(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertIn('id="mcGrid"', r.text)

    def test_multichart_js_accessible(self):
        r = requests.get(f"{LIVE}/static/js/multichart.js", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn("MultiChartManager", r.text)

    def test_multichart_css_accessible(self):
        r = requests.get(f"{LIVE}/static/css/multichart.css", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn(".mc-grid", r.text)

    def test_original_chart_elements_present(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertIn('id="chartArea"', r.text)
        self.assertIn("chart-header", r.text)
        self.assertIn("indicator-strip", r.text)


# ══════════════════════════════════════════════════════════════════════
# 6. Live API Regression Tests
# ══════════════════════════════════════════════════════════════════════


@unittest.skipUnless(_live_ok(), "Live server not running on :34000")
class TestLiveAPIRegression(unittest.TestCase):
    """Ensure existing API endpoints still work after FAZ 18 changes."""

    def test_crypto_klines(self):
        r = requests.get(
            f"{LIVE}/api/market/klines",
            params={"symbol": "BTCUSDT", "interval": "15m", "limit": "10"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("candles") or js.get("ok"))

    def test_stocks_klines(self):
        r = requests.get(
            f"{LIVE}/api/stocks/klines",
            params={"symbol": "AAPL", "interval": "1d", "limit": "10"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)

    def test_bist_klines(self):
        r = requests.get(
            f"{LIVE}/api/bist/klines",
            params={"symbol": "THYAO.IS", "interval": "1d", "limit": "10"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)

    def test_forex_klines(self):
        r = requests.get(
            f"{LIVE}/api/forex/klines",
            params={"symbol": "EURUSD=X", "interval": "1d", "limit": "10"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)

    def test_commodities_klines(self):
        r = requests.get(
            f"{LIVE}/api/commodities/klines",
            params={"symbol": "GC=F", "interval": "1d", "limit": "10"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)

    def test_indicators_rsi(self):
        r = requests.get(
            f"{LIVE}/api/indicators/rsi",
            params={"symbol": "BTCUSDT", "interval": "15m", "limit": "50"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertIn("rsi", js)

    def test_indicators_macd(self):
        r = requests.get(
            f"{LIVE}/api/indicators/macd",
            params={"symbol": "BTCUSDT", "interval": "15m", "limit": "50"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertIn("macd", js)

    def test_signal_endpoint(self):
        r = requests.get(
            f"{LIVE}/api/signal",
            params={"symbol": "BTCUSDT"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)

    def test_screener_still_works(self):
        r = requests.get(
            f"{LIVE}/api/screener",
            params={"market": "crypto"},
            timeout=30,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"))


# ══════════════════════════════════════════════════════════════════════
# 7. Multi-Chart Feature Verification (Live)
# ══════════════════════════════════════════════════════════════════════


@unittest.skipUnless(_live_ok(), "Live server not running on :34000")
class TestLiveMultiChartFeatures(unittest.TestCase):
    """Verify multi-chart features work with real data."""

    def test_btc_chart_data_loads(self):
        """BTC klines for chart slot 1."""
        r = requests.get(
            f"{LIVE}/api/market/klines",
            params={"symbol": "BTCUSDT", "interval": "15m", "limit": "500"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        candles = js.get("candles", [])
        self.assertGreater(len(candles), 50)

    def test_eth_chart_data_loads(self):
        """ETH klines for chart slot 2."""
        r = requests.get(
            f"{LIVE}/api/market/klines",
            params={"symbol": "ETHUSDT", "interval": "15m", "limit": "500"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        candles = js.get("candles", [])
        self.assertGreater(len(candles), 50)

    def test_aapl_chart_data_loads(self):
        """AAPL klines for chart slot 3."""
        r = requests.get(
            f"{LIVE}/api/stocks/klines",
            params={"symbol": "AAPL", "interval": "1d", "limit": "200"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        candles = js.get("candles", [])
        self.assertGreater(len(candles), 10)

    def test_thyao_chart_data_loads(self):
        """THYAO klines for chart slot 4."""
        r = requests.get(
            f"{LIVE}/api/bist/klines",
            params={"symbol": "THYAO.IS", "interval": "1d", "limit": "200"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        candles = js.get("candles", [])
        self.assertGreater(len(candles), 10)

    def test_eurusd_chart_data_loads(self):
        """EURUSD klines for forex chart."""
        r = requests.get(
            f"{LIVE}/api/forex/klines",
            params={"symbol": "EURUSD=X", "interval": "1d", "limit": "200"},
            timeout=15,
        )
        self.assertEqual(r.status_code, 200)
        js = r.json()
        candles = js.get("candles", [])
        self.assertGreater(len(candles), 10)

    def test_multiple_symbols_concurrent(self):
        """Simulate 4-chart layout: fetch BTC, ETH, AAPL, THYAO concurrently."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        requests_list = [
            (f"{LIVE}/api/market/klines", {"symbol": "BTCUSDT", "interval": "15m", "limit": "100"}),
            (f"{LIVE}/api/market/klines", {"symbol": "ETHUSDT", "interval": "1h", "limit": "100"}),
            (f"{LIVE}/api/stocks/klines", {"symbol": "AAPL", "interval": "1d", "limit": "100"}),
            (f"{LIVE}/api/bist/klines", {"symbol": "THYAO.IS", "interval": "1d", "limit": "100"}),
        ]

        def fetch(url_params):
            url, params = url_params
            return requests.get(url, params=params, timeout=15)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(fetch, rp) for rp in requests_list]
            results = [f.result() for f in as_completed(futures)]

        for r in results:
            self.assertEqual(r.status_code, 200)
            js = r.json()
            self.assertIn("candles", js)

    def test_different_timeframes_work(self):
        """Verify different timeframes load (simulating per-chart timeframe)."""
        for tf in ["15m", "1h", "4h", "1d"]:
            r = requests.get(
                f"{LIVE}/api/market/klines",
                params={"symbol": "BTCUSDT", "interval": tf, "limit": "50"},
                timeout=15,
            )
            self.assertEqual(r.status_code, 200, f"Failed for timeframe {tf}")


if __name__ == "__main__":
    unittest.main()
