# -*- coding: utf-8 -*-
"""FAZ — Keşfet (Discover) Page Tests.

Validates:
  1. File existence & structure (discover.html, discover.css, discover.js)
  2. Template structure (HTML elements, sections, bottom tab bar)
  3. CSS classes & responsive design
  4. JavaScript module structure (IIFE, API calls, category config)
  5. Route registration (/discover)
  6. Live API integration (ticker, klines, news endpoints)
  7. Backward compatibility (existing routes still work)
"""
from __future__ import annotations

import os
import re
import time
import json
import pytest
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:34000"
TIMEOUT = 12


# ─── Helpers ────────────────────────────────────────────────────────
def _read(rel_path: str) -> str:
    fp = os.path.join(BASE, rel_path)
    assert os.path.isfile(fp), f"Missing file: {rel_path}"
    with open(fp, encoding="utf-8") as f:
        return f.read()


def _get(path: str, **kw) -> requests.Response:
    return requests.get(URL + path, timeout=TIMEOUT, **kw)


# ═══════════════════════════════════════════════════════════════════
# 1) FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════
class TestFileExistence:
    def test_discover_html_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/discover.html"))

    def test_discover_css_exists(self):
        assert os.path.isfile(os.path.join(BASE, "static/css/discover.css"))

    def test_discover_js_exists(self):
        assert os.path.isfile(os.path.join(BASE, "static/js/discover.js"))

    def test_route_file_updated(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert "discover" in src, "Route file should contain 'discover'"


# ═══════════════════════════════════════════════════════════════════
# 2) TEMPLATE STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestTemplateStructure:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.html = _read("templates/discover.html")
        self.layout_html = _read("templates/layout_terminal.html")
        self.full_html = self.html + self.layout_html

    def test_standalone_page(self):
        """Discover page should NOT extend old base.html."""
        assert 'extends "base.html"' not in self.html

    def test_extends_layout_terminal(self):
        assert 'extends "layout_terminal.html"' in self.html

    def test_has_design_system_css(self):
        assert "design_system.css" in self.full_html

    def test_has_discover_css_link(self):
        assert "discover.css" in self.full_html

    def test_has_discover_js_link(self):
        assert "discover.js" in self.html

    def test_has_pro_search(self):
        assert "pro-search" in self.full_html

    def test_has_dashboard_title(self):
        assert "Dashboard" in self.html

    def test_has_pro_card(self):
        assert "pro-card" in self.html

    def test_has_pro_chip(self):
        assert "pro-chip" in self.html

    def test_has_category_chips(self):
        assert "category-chips" in self.html

    def test_has_kripto_chip(self):
        assert 'data-cat="kripto"' in self.html

    def test_has_bist_chip(self):
        assert 'data-cat="bist"' in self.html

    def test_has_commodities_chip(self):
        assert 'data-cat="commodities"' in self.html

    def test_has_forex_chip(self):
        assert 'data-cat="forex"' in self.html

    def test_has_stocks_chip(self):
        assert 'data-cat="stocks"' in self.html

    def test_has_featured_cards(self):
        assert "featured-cards" in self.html

    def test_has_market_list(self):
        assert "market-list" in self.html

    def test_has_movers_section(self):
        assert "movers-scroll" in self.html

    def test_has_news_section(self):
        assert "section-news" in self.html

    def test_has_news_feed(self):
        assert "news-feed" in self.html

    def test_has_calendar_section(self):
        assert "section-calendar" in self.html

    def test_has_calendar_feed(self):
        assert "calendar-feed" in self.html

    def test_has_sidebar_navigation(self):
        assert "tl-sidebar" in self.full_html

    def test_sidebar_has_trade_link(self):
        assert 'href="/trade"' in self.full_html

    def test_sidebar_has_screener_link(self):
        assert 'href="/screener"' in self.full_html

    def test_sidebar_has_chat_link(self):
        assert 'href="/chat"' in self.full_html

    def test_tab_bar_links_trade(self):
        assert 'href="/trade"' in self.full_html

    def test_tab_bar_links_screener(self):
        assert 'href="/screener"' in self.full_html

    def test_tab_bar_links_chat(self):
        assert 'href="/chat"' in self.full_html

    def test_action_cards_news(self):
        assert "news-feed" in self.html

    def test_action_cards_calendar(self):
        assert "calendar-feed" in self.html

    def test_action_cards_quick_access(self):
        assert "featured-cards" in self.html

    def test_quick_action_cards_count(self):
        assert self.html.count("pro-card hover-lift") >= 3

    def test_viewport_meta(self):
        assert "viewport" in self.full_html

    def test_mobile_optimized(self):
        assert "maximum-scale=1" in self.full_html

    def test_apple_web_app(self):
        assert "apple-mobile-web-app-capable" in self.full_html

    def test_movers_gainers(self):
        assert "Gainers" in self.html

    def test_movers_losers(self):
        assert "Losers" in self.html

    def test_news_chips(self):
        assert "news-chips" in self.html

    def test_news_chip_crypto(self):
        assert 'data-news="crypto"' in self.html

    def test_news_chip_bist(self):
        assert 'data-news="bist"' in self.html


# ═══════════════════════════════════════════════════════════════════
# 3) CSS STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestCSSStructure:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.css = _read("static/css/discover.css")

    def test_has_action_card_style(self):
        assert "disc-action-card" in self.css

    def test_has_chip_style(self):
        assert "disc-chip" in self.css

    def test_has_chip_active(self):
        assert "disc-chip.active" in self.css

    def test_has_market_card(self):
        assert "disc-market-card" in self.css

    def test_has_market_row(self):
        assert "disc-market-row" in self.css

    def test_has_mover_card(self):
        assert "disc-mover-card" in self.css

    def test_has_news_item(self):
        assert "disc-news-item" in self.css

    def test_has_calendar_item(self):
        assert "disc-cal-item" in self.css

    def test_has_tab_bar_style(self):
        assert "disc-tab" in self.css

    def test_has_skeleton_loading(self):
        assert "disc-skeleton-card" in self.css

    def test_has_shimmer_animation(self):
        assert "shimmer" in self.css

    def test_has_sparkline_styles(self):
        assert "sparkline" in self.css

    def test_has_responsive_breakpoint(self):
        assert "@media" in self.css

    def test_has_scrollbar_hide(self):
        assert "scrollbar-hide" in self.css

    def test_has_green_color(self):
        assert "#00C853" in self.css

    def test_has_red_color(self):
        assert "#FF1744" in self.css

    def test_has_blue_color(self):
        assert "#2979FF" in self.css

    def test_has_sentiment_styles(self):
        assert "news-sentiment" in self.css

    def test_has_fade_animation(self):
        assert "fadeUp" in self.css


# ═══════════════════════════════════════════════════════════════════
# 4) JAVASCRIPT STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestJavaScriptStructure:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.js = _read("static/js/discover.js")

    def test_is_iife(self):
        assert "(function" in self.js

    def test_has_strict_mode(self):
        assert '"use strict"' in self.js

    def test_has_category_config(self):
        assert "CATEGORY_CONFIG" in self.js

    def test_config_has_kripto(self):
        assert "kripto:" in self.js or "'kripto'" in self.js or '"kripto"' in self.js

    def test_config_has_bist(self):
        assert "bist:" in self.js or "'bist'" in self.js

    def test_config_has_commodities(self):
        assert "commodities:" in self.js or "'commodities'" in self.js

    def test_config_has_forex(self):
        assert "forex:" in self.js or "'forex'" in self.js

    def test_config_has_stocks(self):
        assert "stocks:" in self.js or "'stocks'" in self.js

    def test_has_fetch_ticker(self):
        assert "fetchTicker" in self.js

    def test_has_fetch_klines(self):
        assert "fetchKlines" in self.js

    def test_has_fetch_news(self):
        assert "fetchNews" in self.js

    def test_has_render_featured(self):
        assert "renderFeaturedCards" in self.js

    def test_has_render_market_list(self):
        assert "renderMarketList" in self.js

    def test_has_render_movers(self):
        assert "renderMovers" in self.js

    def test_has_render_news(self):
        assert "renderNews" in self.js

    def test_has_render_calendar(self):
        assert "renderCalendar" in self.js

    def test_has_sparkline_draw(self):
        assert "drawSparkline" in self.js

    def test_has_search_functionality(self):
        assert "runSearch" in self.js

    def test_has_init_function(self):
        assert "function init" in self.js or "async function init" in self.js

    def test_has_auto_refresh(self):
        assert "startRefresh" in self.js

    def test_has_format_price(self):
        assert "fmtPrice" in self.js

    def test_has_format_percent(self):
        assert "fmtPct" in self.js

    def test_has_time_ago(self):
        assert "timeAgo" in self.js

    def test_uses_market_ticker_endpoint(self):
        assert "/api/market/ticker" in self.js

    def test_uses_bist_ticker_endpoint(self):
        assert "/api/bist/ticker" in self.js

    def test_uses_commodities_ticker_endpoint(self):
        assert "/api/commodities/ticker" in self.js

    def test_uses_forex_ticker_endpoint(self):
        assert "/api/forex/ticker" in self.js

    def test_uses_stocks_ticker_endpoint(self):
        assert "/api/stocks/ticker" in self.js

    def test_uses_klines_endpoint(self):
        assert "/klines" in self.js

    def test_uses_news_endpoint(self):
        assert "/api/news" in self.js

    def test_btcusdt_in_config(self):
        assert "BTCUSDT" in self.js

    def test_xu100_in_config(self):
        assert "XU100.IS" in self.js

    def test_gold_in_config(self):
        assert "GC=F" in self.js

    def test_eurusd_in_config(self):
        assert "EURUSD=X" in self.js

    def test_aapl_in_config(self):
        assert "AAPL" in self.js

    def test_no_mock_data_in_market(self):
        """Market data should come from real APIs, not mocked."""
        assert "mockPrice" not in self.js
        assert "fakeData" not in self.js

    def test_chip_switching_logic(self):
        assert "initChips" in self.js

    def test_news_chip_switching(self):
        assert "initNewsChips" in self.js

    def test_mover_toggle(self):
        assert "initMovers" in self.js

    def test_sort_functionality(self):
        assert "initSorting" in self.js


# ═══════════════════════════════════════════════════════════════════
# 5) ROUTE REGISTRATION
# ═══════════════════════════════════════════════════════════════════
class TestRouteRegistration:
    def test_route_in_dashboard(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert "/discover" in src

    def test_renders_discover_template(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert "discover.html" in src

    def test_discover_function_name(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert "def discover_page" in src or "def discover" in src


# ═══════════════════════════════════════════════════════════════════
# 6) LIVE API INTEGRATION
# ═══════════════════════════════════════════════════════════════════
class TestLiveAPIIntegration:
    def test_discover_page_returns_200(self):
        r = _get("/discover")
        assert r.status_code == 200

    def test_discover_page_html_content(self):
        r = _get("/discover")
        assert "ZKR Analiz Pro" in r.text

    def test_discover_page_has_css(self):
        r = _get("/discover")
        assert "discover.css" in r.text

    def test_discover_page_has_js(self):
        r = _get("/discover")
        assert "discover.js" in r.text

    def test_static_css_loads(self):
        r = _get("/static/css/discover.css")
        assert r.status_code == 200
        assert "disc-chip" in r.text

    def test_static_js_loads(self):
        r = _get("/static/js/discover.js")
        assert r.status_code == 200
        assert "CATEGORY_CONFIG" in r.text

    def test_crypto_ticker_api(self):
        r = _get("/api/market/ticker?symbol=BTCUSDT")
        d = r.json()
        assert d["ok"] is True
        assert d["lastPrice"] > 0

    def test_bist_ticker_api(self):
        r = _get("/api/bist/ticker?symbol=XU100.IS")
        d = r.json()
        assert d["ok"] is True
        assert d["lastPrice"] > 0

    def test_commodities_ticker_api(self):
        r = _get("/api/commodities/ticker?symbol=GC%3DF")
        d = r.json()
        assert d["ok"] is True
        assert d["lastPrice"] > 0

    def test_forex_ticker_api(self):
        r = _get("/api/forex/ticker?symbol=EURUSD%3DX")
        d = r.json()
        assert d["ok"] is True
        assert d["lastPrice"] > 0

    def test_stocks_ticker_api(self):
        r = _get("/api/stocks/ticker?symbol=AAPL")
        d = r.json()
        assert d["ok"] is True
        assert d["lastPrice"] > 0

    def test_crypto_klines_api(self):
        r = _get("/api/market/klines?symbol=BTCUSDT&interval=1d&limit=14")
        d = r.json()
        assert d["ok"] is True
        assert len(d.get("candles", [])) > 0

    def test_bist_klines_api(self):
        r = _get("/api/bist/klines?symbol=XU100.IS&interval=1d&limit=14")
        d = r.json()
        assert d["ok"] is True
        assert len(d.get("candles", [])) > 0

    def test_commodities_klines_api(self):
        r = _get("/api/commodities/klines?symbol=GC%3DF&interval=1d&limit=14")
        d = r.json()
        assert d["ok"] is True
        assert len(d.get("candles", [])) > 0

    def test_news_crypto_api(self):
        r = _get("/api/news?type=crypto")
        d = r.json()
        assert d["ok"] is True
        assert d["count"] > 0

    def test_news_bist_api(self):
        r = _get("/api/news?type=bist")
        d = r.json()
        assert d["ok"] is True

    def test_news_data_has_title(self):
        r = _get("/api/news?type=crypto")
        d = r.json()
        if d["data"]:
            assert "title" in d["data"][0]
            assert "source" in d["data"][0]


# ═══════════════════════════════════════════════════════════════════
# 7) BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════
class TestBackwardCompatibility:
    def test_home_still_works(self):
        r = _get("/")
        assert r.status_code == 200
        assert "ZKR Analiz" in r.text

    def test_trade_still_works(self):
        r = _get("/trade")
        assert r.status_code == 200

    def test_screener_still_works(self):
        r = _get("/screener")
        assert r.status_code == 200

    def test_chat_still_works(self):
        r = _get("/chat")
        assert r.status_code == 200

    def test_original_index_unchanged(self):
        """index.html should still serve the desktop dashboard."""
        r = _get("/")
        assert "index.js" in r.text or "BTC" in r.text

    def test_discover_not_replacing_home(self):
        """/ should still serve index.html, not discover.html."""
        r = _get("/")
        assert "discover.js" not in r.text
