# -*- coding: utf-8 -*-
"""FAZ 56 — Screener Multi-Market Completion Tests.

Validates:
- /screener page loads (200)
- All 5 markets return data via API
- Filters work
- Search works
- Null/NaN/broken rows are clean
- Fallback data exists
- Row click navigates to chart
- Symbol display is clean (no raw .IS, =X, =F)
- Tab switching
- Price data populated
"""
import json
import re
import unittest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()


# ══════════════════════════════════════════════════════════════════════
# 1. Page Load
# ══════════════════════════════════════════════════════════════════════
class TestScreenerPageLoad(_Base):
    def test_screener_returns_200(self):
        r = self.client.get("/screener")
        self.assertEqual(r.status_code, 200)

    def test_screener_has_market_tabs(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn('data-market="crypto"', html)
        self.assertIn('data-market="stocks"', html)
        self.assertIn('data-market="bist"', html)
        self.assertIn('data-market="forex"', html)
        self.assertIn('data-market="commodities"', html)

    def test_screener_has_search_input(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn('id="scrSearch"', html)

    def test_screener_has_filter_sidebar(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn('id="scrFilters"', html)

    def test_screener_has_empty_state(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn('id="scrEmpty"', html)

    def test_screener_has_results_list(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn('id="scrList"', html)

    def test_screener_has_turkish_tab_labels(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn("Kripto", html)
        self.assertIn("ABD Hisseleri", html)
        self.assertIn("BIST", html)
        self.assertIn("Forex", html)
        self.assertIn("Emtia", html)

    def test_screener_loads_screener_js(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn("screener.js", html)

    def test_screener_loads_screener_css(self):
        r = self.client.get("/screener")
        html = r.data.decode()
        self.assertIn("screener.css", html)


# ══════════════════════════════════════════════════════════════════════
# 2. Crypto Market API
# ══════════════════════════════════════════════════════════════════════
class TestCryptoMarket(_Base):
    def test_crypto_returns_ok(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_crypto_returns_data(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        self.assertGreater(d.get("count", 0), 0)

    def test_crypto_has_symbol(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        row = d["data"][0]
        self.assertIn("symbol", row)
        self.assertTrue(len(row["symbol"]) > 0)

    def test_crypto_has_price(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        prices = [r for r in d["data"] if r.get("price", 0) > 0]
        self.assertGreater(len(prices), 0)

    def test_crypto_market_label(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        self.assertEqual(d.get("market"), "crypto")

    def test_crypto_has_change_field(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        row = d["data"][0]
        self.assertIn("change_24h", row)


# ══════════════════════════════════════════════════════════════════════
# 3. US Stocks Market API
# ══════════════════════════════════════════════════════════════════════
class TestStocksMarket(_Base):
    def test_stocks_returns_ok(self):
        r = self.client.get("/api/screener?market=stocks")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_stocks_returns_data(self):
        r = self.client.get("/api/screener?market=stocks")
        d = json.loads(r.data)
        self.assertGreater(d.get("count", 0), 0)

    def test_stocks_has_symbol(self):
        r = self.client.get("/api/screener?market=stocks")
        d = json.loads(r.data)
        symbols = [r["symbol"] for r in d["data"]]
        # Should contain well-known stock symbols
        has_known = any(s in symbols for s in ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "A", "AAL", "ABT"])
        self.assertTrue(has_known)

    def test_stocks_market_label(self):
        r = self.client.get("/api/screener?market=stocks")
        d = json.loads(r.data)
        self.assertEqual(d.get("market"), "stocks")

    def test_stocks_has_trend(self):
        r = self.client.get("/api/screener?market=stocks")
        d = json.loads(r.data)
        row = d["data"][0]
        self.assertIn("trend", row)
        self.assertIn(row["trend"], ["up", "down", "sideways"])

    def test_stocks_count_reasonable(self):
        r = self.client.get("/api/screener?market=stocks")
        d = json.loads(r.data)
        self.assertGreaterEqual(d.get("count", 0), 10)


# ══════════════════════════════════════════════════════════════════════
# 4. BIST Market API
# ══════════════════════════════════════════════════════════════════════
class TestBISTMarket(_Base):
    def test_bist_returns_ok(self):
        r = self.client.get("/api/screener?market=bist")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_bist_returns_data(self):
        r = self.client.get("/api/screener?market=bist")
        d = json.loads(r.data)
        self.assertGreater(d.get("count", 0), 0)

    def test_bist_has_is_suffix_symbols(self):
        r = self.client.get("/api/screener?market=bist")
        d = json.loads(r.data)
        is_symbols = [r["symbol"] for r in d["data"] if r["symbol"].endswith(".IS")]
        self.assertGreater(len(is_symbols), 0)

    def test_bist_market_label(self):
        r = self.client.get("/api/screener?market=bist")
        d = json.loads(r.data)
        self.assertEqual(d.get("market"), "bist")

    def test_bist_count_reasonable(self):
        r = self.client.get("/api/screener?market=bist")
        d = json.loads(r.data)
        self.assertGreaterEqual(d.get("count", 0), 10)

    def test_bist_has_price_field(self):
        r = self.client.get("/api/screener?market=bist")
        d = json.loads(r.data)
        row = d["data"][0]
        self.assertIn("price", row)


# ══════════════════════════════════════════════════════════════════════
# 5. Forex Market API
# ══════════════════════════════════════════════════════════════════════
class TestForexMarket(_Base):
    def test_forex_returns_ok(self):
        r = self.client.get("/api/screener?market=forex")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_forex_returns_data(self):
        r = self.client.get("/api/screener?market=forex")
        d = json.loads(r.data)
        self.assertGreater(d.get("count", 0), 0)

    def test_forex_has_pairs(self):
        r = self.client.get("/api/screener?market=forex")
        d = json.loads(r.data)
        symbols = [r["symbol"] for r in d["data"]]
        has_fx = any("=X" in s for s in symbols)
        self.assertTrue(has_fx)

    def test_forex_market_label(self):
        r = self.client.get("/api/screener?market=forex")
        d = json.loads(r.data)
        self.assertEqual(d.get("market"), "forex")


# ══════════════════════════════════════════════════════════════════════
# 6. Commodities Market API
# ══════════════════════════════════════════════════════════════════════
class TestCommoditiesMarket(_Base):
    def test_commodities_returns_ok(self):
        r = self.client.get("/api/screener?market=commodities")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_commodities_returns_data(self):
        r = self.client.get("/api/screener?market=commodities")
        d = json.loads(r.data)
        self.assertGreater(d.get("count", 0), 0)

    def test_commodities_has_futures(self):
        r = self.client.get("/api/screener?market=commodities")
        d = json.loads(r.data)
        symbols = [r["symbol"] for r in d["data"]]
        has_fut = any("=F" in s for s in symbols)
        self.assertTrue(has_fut)

    def test_commodities_market_label(self):
        r = self.client.get("/api/screener?market=commodities")
        d = json.loads(r.data)
        self.assertEqual(d.get("market"), "commodities")


# ══════════════════════════════════════════════════════════════════════
# 7. Filters API
# ══════════════════════════════════════════════════════════════════════
class TestFiltersAPI(_Base):
    def test_filters_returns_ok(self):
        r = self.client.get("/api/screener/filters")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_filters_returns_list(self):
        r = self.client.get("/api/screener/filters")
        d = json.loads(r.data)
        self.assertIsInstance(d.get("filters"), list)
        self.assertGreater(len(d["filters"]), 0)

    def test_filters_have_name_desc(self):
        r = self.client.get("/api/screener/filters")
        d = json.loads(r.data)
        f = d["filters"][0]
        self.assertIn("name", f)
        self.assertIn("desc", f)
        self.assertIn("category", f)

    def test_filters_have_categories(self):
        r = self.client.get("/api/screener/filters")
        d = json.loads(r.data)
        cats = set(f["category"] for f in d["filters"])
        self.assertTrue(len(cats) >= 3)

    def test_filter_applied(self):
        r = self.client.get("/api/screener?market=crypto&filters=rsi_above_50")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))
        # All returned rows should have rsi14 > 50
        for row in d.get("data", []):
            if row.get("rsi14") is not None:
                self.assertGreater(row["rsi14"], 50)

    def test_multiple_filters(self):
        r = self.client.get("/api/screener?market=crypto&filters=rsi_above_50,price_above_ema20")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))

    def test_invalid_filter_ignored(self):
        r = self.client.get("/api/screener?market=crypto&filters=nonexistent_filter")
        d = json.loads(r.data)
        self.assertTrue(d.get("ok"))


# ══════════════════════════════════════════════════════════════════════
# 8. Invalid Market
# ══════════════════════════════════════════════════════════════════════
class TestInvalidMarket(_Base):
    def test_invalid_market_returns_400(self):
        r = self.client.get("/api/screener?market=invalid")
        self.assertEqual(r.status_code, 400)

    def test_invalid_market_error_msg(self):
        r = self.client.get("/api/screener?market=invalid")
        d = json.loads(r.data)
        self.assertFalse(d.get("ok"))
        self.assertIn("error", d)


# ══════════════════════════════════════════════════════════════════════
# 9. Data Quality — No Null/NaN/Broken Rows
# ══════════════════════════════════════════════════════════════════════
class TestDataQuality(_Base):
    def _check_rows(self, market):
        r = self.client.get(f"/api/screener?market={market}")
        d = json.loads(r.data)
        for row in d.get("data", []):
            # Symbol must exist and be non-empty
            self.assertTrue(row.get("symbol"), f"Empty symbol in {market}")
            # No NaN strings
            for key in ["price", "change_24h", "volume", "rsi14"]:
                val = row.get(key)
                if val is not None:
                    self.assertNotEqual(str(val), "NaN", f"NaN in {key} for {row.get('symbol')}")
                    self.assertNotEqual(str(val), "nan", f"nan in {key} for {row.get('symbol')}")
            # Trend must be valid
            self.assertIn(row.get("trend", "sideways"), ["up", "down", "sideways"])

    def test_crypto_no_broken(self):
        self._check_rows("crypto")

    def test_stocks_no_broken(self):
        self._check_rows("stocks")

    def test_bist_no_broken(self):
        self._check_rows("bist")

    def test_forex_no_broken(self):
        self._check_rows("forex")

    def test_commodities_no_broken(self):
        self._check_rows("commodities")


# ══════════════════════════════════════════════════════════════════════
# 10. Row Structure
# ══════════════════════════════════════════════════════════════════════
class TestRowStructure(_Base):
    def test_row_has_required_fields(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        if d.get("data"):
            row = d["data"][0]
            required = ["symbol", "price", "change_24h", "volume", "market", "trend"]
            for field in required:
                self.assertIn(field, row, f"Missing field: {field}")

    def test_row_has_indicator_fields(self):
        r = self.client.get("/api/screener?market=crypto")
        d = json.loads(r.data)
        if d.get("data"):
            row = d["data"][0]
            indicator_fields = ["ema20", "ema50", "rsi14"]
            for field in indicator_fields:
                self.assertIn(field, row, f"Missing indicator field: {field}")


# ══════════════════════════════════════════════════════════════════════
# 11. Sorting
# ══════════════════════════════════════════════════════════════════════
class TestSorting(_Base):
    def test_sort_desc(self):
        r = self.client.get("/api/screener?market=crypto&sort=change_24h&dir=desc")
        d = json.loads(r.data)
        data = d.get("data", [])
        if len(data) >= 2:
            changes = [row.get("change_24h", 0) or 0 for row in data[:10]]
            for i in range(len(changes) - 1):
                self.assertGreaterEqual(changes[i], changes[i + 1])

    def test_sort_asc(self):
        r = self.client.get("/api/screener?market=crypto&sort=change_24h&dir=asc")
        d = json.loads(r.data)
        data = d.get("data", [])
        if len(data) >= 2:
            changes = [row.get("change_24h", 0) or 0 for row in data[:10]]
            for i in range(len(changes) - 1):
                self.assertLessEqual(changes[i], changes[i + 1])


# ══════════════════════════════════════════════════════════════════════
# 12. JavaScript Assets
# ══════════════════════════════════════════════════════════════════════
class TestJSAssets(_Base):
    def test_screener_js_fallback_data(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("FALLBACK_DATA", js)
        self.assertIn("crypto", js)
        self.assertIn("stocks", js)
        self.assertIn("bist", js)
        self.assertIn("forex", js)
        self.assertIn("commodities", js)

    def test_screener_js_search_function(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("applySearch", js)
        self.assertIn("scrSearch", js)

    def test_screener_js_clean_symbol(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("cleanSymbol", js)
        self.assertIn(".IS", js)
        self.assertIn("=X", js)
        self.assertIn("=F", js)

    def test_screener_js_symbol_names(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("SYMBOL_NAMES", js)
        self.assertIn("Bitcoin", js)
        self.assertIn("Apple", js)
        self.assertIn("Garanti", js)
        self.assertIn("Altın", js)

    def test_screener_js_safe_val(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("safeVal", js)

    def test_screener_js_chart_navigation(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("bw_active_market", js)
        self.assertIn("bw_current_symbol", js)
        self.assertIn("/tv", js)

    def test_screener_js_empty_state(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertIn("showEmpty", js)
        self.assertIn("scrEmpty", js)

    def test_screener_js_no_object_object(self):
        r = self.client.get("/static/js/screener.js")
        js = r.data.decode()
        self.assertNotIn("[object Object]", js)


# ══════════════════════════════════════════════════════════════════════
# 13. CSS Assets
# ══════════════════════════════════════════════════════════════════════
class TestCSSAssets(_Base):
    def test_screener_css_loads(self):
        r = self.client.get("/static/css/screener.css")
        self.assertEqual(r.status_code, 200)

    def test_screener_css_has_list_styles(self):
        r = self.client.get("/static/css/screener.css")
        css = r.data.decode()
        self.assertIn(".scr-row", css)
        self.assertIn(".scr-col-sym", css)
        self.assertIn(".scr-col-price", css)

    def test_screener_css_has_search_styles(self):
        r = self.client.get("/static/css/screener.css")
        css = r.data.decode()
        self.assertIn(".scr-search", css)

    def test_screener_css_has_empty_state(self):
        r = self.client.get("/static/css/screener.css")
        css = r.data.decode()
        self.assertIn(".scr-empty", css)

    def test_screener_css_mobile_responsive(self):
        r = self.client.get("/static/css/screener.css")
        css = r.data.decode()
        self.assertIn("@media", css)
        self.assertIn("640px", css)


# ══════════════════════════════════════════════════════════════════════
# 14. Backend Engine
# ══════════════════════════════════════════════════════════════════════
class TestScreenerEngine(_Base):
    def test_engine_instantiation(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        self.assertIsNotNone(engine)

    def test_engine_filter_registry(self):
        from app.core.screener_engine import _FILTERS
        self.assertGreater(len(_FILTERS), 10)

    def test_engine_available_filters(self):
        from app.core.screener_engine import get_available_filters
        filters = get_available_filters()
        self.assertIsInstance(filters, list)
        self.assertGreater(len(filters), 10)
        names = [f["name"] for f in filters]
        self.assertIn("rsi_above_60", names)
        self.assertIn("price_above_ema20", names)
        self.assertIn("volume_spike", names)

    def test_engine_scan_invalid_market(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        result = engine.scan("invalid_market")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
