# -*- coding: utf-8 -*-
"""FAZ 17 Tests — Multi-Market Screener.

Tests:
  - Screener engine imports and structure
  - Filter registry
  - Indicator computation
  - Filter logic
  - API endpoint response format
  - Frontend page loading
  - Live market scans

Run:
    python -m pytest tests/test_faz17_screener.py -v
"""
from __future__ import annotations

import math
import pytest
import requests

BASE = "http://127.0.0.1:34000"


# ══════════════════════════════════════════════════════════════════════
# Offline Tests — No server required
# ══════════════════════════════════════════════════════════════════════

class TestScreenerEngine:
    """Test screener engine module structure."""

    def test_import_engine(self):
        from app.core.screener_engine import ScreenerEngine
        assert ScreenerEngine is not None

    def test_import_filters(self):
        from app.core.screener_engine import get_available_filters
        filters = get_available_filters()
        assert isinstance(filters, list)
        assert len(filters) > 0

    def test_filter_has_required_keys(self):
        from app.core.screener_engine import get_available_filters
        for f in get_available_filters():
            assert "name" in f
            assert "desc" in f
            assert "category" in f

    def test_filter_categories_present(self):
        from app.core.screener_engine import get_available_filters
        cats = {f["category"] for f in get_available_filters()}
        assert "trend" in cats
        assert "momentum" in cats
        assert "volume" in cats
        assert "volatility" in cats

    def test_minimum_filter_count(self):
        from app.core.screener_engine import get_available_filters
        assert len(get_available_filters()) >= 10

    def test_scan_limits_defined(self):
        from app.core.screener_engine import _SCAN_LIMITS
        assert _SCAN_LIMITS["crypto"] == 150
        assert _SCAN_LIMITS["stocks"] == 100
        assert _SCAN_LIMITS["bist"] == 80
        assert _SCAN_LIMITS["forex"] == 20
        assert _SCAN_LIMITS["commodities"] == 20


class TestFilterLogic:
    """Test individual filter functions with synthetic data."""

    def _make_row(self, **kwargs):
        base = {
            "symbol": "TEST",
            "price": 100,
            "change_24h": 2.5,
            "volume": 1000000,
            "ema20": 98,
            "ema50": 95,
            "ema200": 90,
            "sma50": 95,
            "sma200": 90,
            "rsi14": 55,
            "atr": 3.5,
            "atr_pct": 3.5,
            "trend": "up",
            "support_distance": 5.0,
            "resistance_distance": 1.5,
            "vol_ratio": 1.2,
            "ema20_cross_ema50": False,
            "ema50_cross_ema200": False,
        }
        base.update(kwargs)
        return base

    def test_price_above_ema20_true(self):
        from app.core.screener_engine import _FILTERS
        row = self._make_row(price=100, ema20=98)
        assert _FILTERS["price_above_ema20"]["fn"](row) is True

    def test_price_above_ema20_false(self):
        from app.core.screener_engine import _FILTERS
        row = self._make_row(price=95, ema20=98)
        assert _FILTERS["price_above_ema20"]["fn"](row) is False

    def test_ema20_above_ema50(self):
        from app.core.screener_engine import _FILTERS
        row = self._make_row(ema20=98, ema50=95)
        assert _FILTERS["ema20_above_ema50"]["fn"](row) is True

    def test_rsi_above_60(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["rsi_above_60"]["fn"](self._make_row(rsi14=65)) is True
        assert _FILTERS["rsi_above_60"]["fn"](self._make_row(rsi14=50)) is False

    def test_rsi_below_30(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["rsi_below_30"]["fn"](self._make_row(rsi14=25)) is True
        assert _FILTERS["rsi_below_30"]["fn"](self._make_row(rsi14=50)) is False

    def test_volume_spike(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["volume_spike"]["fn"](self._make_row(vol_ratio=2.5)) is True
        assert _FILTERS["volume_spike"]["fn"](self._make_row(vol_ratio=1.5)) is False

    def test_price_near_resistance(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["price_near_resistance"]["fn"](self._make_row(resistance_distance=1.5)) is True
        assert _FILTERS["price_near_resistance"]["fn"](self._make_row(resistance_distance=5.0)) is False

    def test_price_near_support(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["price_near_support"]["fn"](self._make_row(support_distance=1.5)) is True
        assert _FILTERS["price_near_support"]["fn"](self._make_row(support_distance=5.0)) is False

    def test_atr_high(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["atr_high"]["fn"](self._make_row(atr_pct=4.0)) is True
        assert _FILTERS["atr_high"]["fn"](self._make_row(atr_pct=2.0)) is False

    def test_atr_low(self):
        from app.core.screener_engine import _FILTERS
        assert _FILTERS["atr_low"]["fn"](self._make_row(atr_pct=0.5)) is True
        assert _FILTERS["atr_low"]["fn"](self._make_row(atr_pct=2.0)) is False

    def test_strong_uptrend(self):
        from app.core.screener_engine import _FILTERS
        row = self._make_row(price=100, ema20=98, ema50=95, ema200=90, rsi14=60)
        assert _FILTERS["strong_uptrend"]["fn"](row) is True
        row2 = self._make_row(price=80, ema20=98, ema50=95, ema200=90, rsi14=60)
        assert _FILTERS["strong_uptrend"]["fn"](row2) is False

    def test_ema_cross(self):
        from app.core.screener_engine import _FILTERS
        row = self._make_row(ema20_cross_ema50=True)
        assert _FILTERS["ema20_cross_ema50"]["fn"](row) is True
        row2 = self._make_row(ema20_cross_ema50=False)
        assert _FILTERS["ema20_cross_ema50"]["fn"](row2) is False


class TestIndicatorComputation:
    """Test the shared _compute_indicators method."""

    def _make_klines(self, n=50, base_price=100):
        """Generate synthetic klines data."""
        import random
        random.seed(42)
        klines = []
        price = base_price
        for i in range(n):
            change = random.uniform(-2, 2)
            price += change
            h = price + random.uniform(0.5, 2)
            l = price - random.uniform(0.5, 2)
            klines.append({
                "open_time": 1700000000000 + i * 86400000,
                "open": round(price - change / 2, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(price, 2),
                "volume": round(random.uniform(100000, 1000000), 2),
            })
        return klines

    def test_compute_with_enough_data(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        klines = self._make_klines(100)
        result = engine._compute_indicators(klines, 100)
        assert result["ema20"] is not None
        assert result["ema50"] is not None
        assert result["rsi14"] is not None
        assert result["trend"] in ("up", "down", "sideways")

    def test_compute_with_insufficient_data(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        result = engine._compute_indicators([], 100)
        assert result["ema20"] is None
        assert result["rsi14"] is None

    def test_compute_ema200_needs_data(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        klines = self._make_klines(50)
        result = engine._compute_indicators(klines, 100)
        # EMA200 needs 200 bars
        assert result["ema200"] is None

    def test_compute_atr_percentage(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        klines = self._make_klines(50, base_price=100)
        result = engine._compute_indicators(klines, 100)
        assert result["atr"] is not None
        assert result["atr_pct"] is not None
        assert result["atr_pct"] > 0

    def test_compute_vol_ratio(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        klines = self._make_klines(30)
        result = engine._compute_indicators(klines, 100)
        assert result["vol_ratio"] is not None

    def test_support_resistance_distances(self):
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        klines = self._make_klines(30)
        result = engine._compute_indicators(klines, 100)
        assert result["support_distance"] is not None
        assert result["resistance_distance"] is not None


class TestScreenerBlueprint:
    """Test screener blueprint structure."""

    def test_blueprint_import(self):
        from app.blueprints.screener import screener_bp
        assert screener_bp is not None
        assert screener_bp.name == "screener"

    def test_routes_import(self):
        from app.blueprints.screener import routes
        assert routes is not None

    def test_engine_instance(self):
        from app.blueprints.screener.routes import _engine
        assert _engine is not None

    def test_cache_ttls_defined(self):
        from app.blueprints.screener.routes import _CACHE_TTLS
        assert _CACHE_TTLS["crypto"] == 60
        assert _CACHE_TTLS["stocks"] == 120
        assert _CACHE_TTLS["bist"] == 120


class TestFrontendFiles:
    """Test frontend files exist and contain expected content."""

    def test_screener_html_exists(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "screener.html")
        assert os.path.exists(path)

    def test_screener_html_has_table(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "screener.html")
        content = open(path).read()
        assert "scrTable" in content
        assert "scrBody" in content
        assert "scrMarketTabs" in content
        assert "scrFilters" in content

    def test_screener_js_exists(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "static", "js", "screener.js")
        assert os.path.exists(path)

    def test_screener_js_has_load(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "static", "js", "screener.js")
        content = open(path).read()
        assert "loadScreener" in content
        assert "renderTable" in content
        assert "/api/screener" in content

    def test_screener_css_exists(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "static", "css", "screener.css")
        assert os.path.exists(path)

    def test_screener_route_exists(self):
        from app.blueprints.dashboard.routes import screener_page
        assert callable(screener_page)


# ══════════════════════════════════════════════════════════════════════
# Live Tests — Require running server at localhost:34000
# ══════════════════════════════════════════════════════════════════════

class TestLiveScreener:
    """Live API tests — require running server."""

    def _get(self, path, **kwargs):
        return requests.get(BASE + path, params=kwargs, timeout=30)

    def test_screener_page_loads(self):
        r = self._get("/screener")
        assert r.status_code == 200
        assert "scrTable" in r.text

    def test_filters_endpoint(self):
        r = self._get("/api/screener/filters")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["count"] >= 10
        assert len(js["filters"]) >= 10

    def test_screener_crypto(self):
        r = self._get("/api/screener", market="crypto")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["market"] == "crypto"
        assert js["count"] >= 0
        assert isinstance(js["data"], list)
        if js["data"]:
            row = js["data"][0]
            assert "symbol" in row
            assert "price" in row
            assert "change_24h" in row
            assert "rsi14" in row
            assert "trend" in row

    def test_screener_stocks(self):
        r = self._get("/api/screener", market="stocks")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["market"] == "stocks"

    def test_screener_bist(self):
        r = self._get("/api/screener", market="bist")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["market"] == "bist"

    def test_screener_forex(self):
        r = self._get("/api/screener", market="forex")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["market"] == "forex"

    def test_screener_commodities(self):
        r = self._get("/api/screener", market="commodities")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["market"] == "commodities"

    def test_screener_invalid_market(self):
        r = self._get("/api/screener", market="invalid")
        assert r.status_code == 400

    def test_screener_with_filter(self):
        r = self._get("/api/screener", market="crypto", filters="rsi_above_50")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert "rsi_above_50" in js.get("filters_applied", [])

    def test_screener_with_multiple_filters(self):
        r = self._get("/api/screener", market="crypto", filters="ema20_above_ema50,rsi_above_50")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert len(js.get("filters_applied", [])) == 2

    def test_screener_crypto_has_data(self):
        """Crypto should return actual data (Binance is reliable)."""
        r = self._get("/api/screener", market="crypto")
        js = r.json()
        assert js["ok"] is True
        assert js["count"] > 0, "Crypto screener should find at least some symbols"
        row = js["data"][0]
        assert row["price"] > 0
        assert row["symbol"].endswith("USDT")

    def test_screener_response_format(self):
        r = self._get("/api/screener", market="crypto")
        js = r.json()
        assert "ok" in js
        assert "market" in js
        assert "count" in js
        assert "total_scanned" in js
        assert "data" in js
        assert "filters_applied" in js

    def test_screener_sort(self):
        r = self._get("/api/screener", market="crypto", sort="rsi14", dir="asc")
        js = r.json()
        assert js["ok"] is True

    def test_trade_page_still_works(self):
        """Ensure existing /trade page is not broken."""
        r = self._get("/trade")
        assert r.status_code == 200
        assert "ZKR Analiz" in r.text

    def test_existing_market_endpoints_intact(self):
        """Ensure existing market API endpoints still work."""
        r = self._get("/api/stocks/symbols")
        assert r.status_code == 200
        js = r.json()
        assert js["ok"] is True
        assert js["count"] > 0
