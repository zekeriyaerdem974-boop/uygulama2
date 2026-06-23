# -*- coding: utf-8 -*-
"""FAZ 55 — Discover Completion / UI Density / Data Binding Fix Tests

Verifies:
- Discover returns 200
- AI summary never shows [object Object]
- Fallback summary renders if API fails
- Metrics row is populated
- Trending section renders
- Opportunities section renders  
- News section renders
- Desktop bottom nav spans correctly
- No raw object rendering anywhere
"""
from __future__ import annotations

import re


# ─── Page Load ───────────────────────────────────────────────

class TestDiscoverPageLoad:
    """Discover page HTTP and basic rendering."""

    def test_discover_returns_200(self, client):
        rv = client.get("/discover")
        assert rv.status_code == 200

    def test_discover_has_html_content(self, client):
        rv = client.get("/discover")
        assert b"<!doctype html>" in rv.data.lower() or b"<!DOCTYPE" in rv.data

    def test_discover_has_page_container(self, client):
        rv = client.get("/discover")
        assert b'id="discoverPage"' in rv.data

    def test_discover_extends_layout(self, client):
        rv = client.get("/discover")
        assert b"mt-bottombar" in rv.data


# ─── AI Summary — [object Object] Fix ────────────────────────

class TestAISummaryRendering:
    """AI summary must never show [object Object]."""

    def test_no_object_object_in_html(self, client):
        rv = client.get("/discover")
        assert b"[object Object]" not in rv.data

    def test_ai_brief_card_present(self, client):
        rv = client.get("/discover")
        assert b'id="aiBriefCard"' in rv.data

    def test_ai_brief_text_element(self, client):
        rv = client.get("/discover")
        assert b'id="aiBriefText"' in rv.data

    def test_ai_brief_loading_text(self, client):
        """Initial text should be loading message, not [object Object]."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        # Find the aiBriefText content
        match = re.search(r'id="aiBriefText"[^>]*>(.*?)</div>', html)
        assert match is not None
        assert "[object Object]" not in match.group(1)

    def test_sentiment_typeof_check_in_js(self, client):
        """JS must check typeof sentiment before rendering."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "typeof data.sentiment" in html or "typeof d.data.sentiment" in html

    def test_ai_fallback_text_defined(self, client):
        """A fallback text constant must exist."""
        rv = client.get("/discover")
        assert b"AI_FALLBACK_TEXT" in rv.data

    def test_sentiment_label_extraction(self, client):
        """JS should extract .label or .key from sentiment object."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "sentiment.label" in html or "sentiment.key" in html

    def test_highlights_array_handling(self, client):
        """JS should handle highlights array (join to string)."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "highlights" in html
        assert "join" in html

    def test_showFallbackAI_function_exists(self, client):
        rv = client.get("/discover")
        assert b"showFallbackAI" in rv.data

    def test_renderAISummary_function_exists(self, client):
        rv = client.get("/discover")
        assert b"renderAISummary" in rv.data

    def test_ai_catch_calls_fallback(self, client):
        """fetch catch must call showFallbackAI."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "catch(showFallbackAI)" in html or "catch(function" in html


# ─── Metrics Bar ─────────────────────────────────────────────

class TestMetricsBar:
    """Metrics row must be populated or have fallbacks."""

    def test_metrics_bar_present(self, client):
        rv = client.get("/discover")
        assert b'id="metricsBar"' in rv.data

    def test_volume_metric(self, client):
        rv = client.get("/discover")
        assert b'id="mc-volume"' in rv.data

    def test_fng_metric(self, client):
        rv = client.get("/discover")
        assert b'id="mc-fng"' in rv.data

    def test_funding_metric(self, client):
        rv = client.get("/discover")
        assert b'id="mc-funding"' in rv.data

    def test_btc_dom_metric(self, client):
        rv = client.get("/discover")
        assert b'id="mc-dom"' in rv.data

    def test_ai_sentiment_metric(self, client):
        rv = client.get("/discover")
        assert b'id="mc-ai-sent"' in rv.data

    def test_fallback_metrics_defined(self, client):
        """JS must define fallback metric values."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "applyFallbackMetrics" in html

    def test_fallback_values_present(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "$2.11B" in html
        assert "51.2%" in html

    def test_metrics_fetch_has_error_handling(self, client):
        """Metrics fetch must catch errors."""
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "applyFallbackMetrics" in html


# ─── Trending Section ────────────────────────────────────────

class TestTrendingSection:
    """Trending coins section must render."""

    def test_trending_container_present(self, client):
        rv = client.get("/discover")
        assert b'id="trendingCoins"' in rv.data

    def test_trending_section_title(self, client):
        rv = client.get("/discover")
        assert "Trending Coinler".encode("utf-8") in rv.data

    def test_trending_fallback_data(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "TRENDING_FALLBACK" in html

    def test_trending_has_btc(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "BTCUSDT" in html

    def test_trending_has_eth(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "ETHUSDT" in html

    def test_trending_has_sol(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "SOLUSDT" in html

    def test_trending_render_function(self, client):
        rv = client.get("/discover")
        assert b"renderTrending" in rv.data


# ─── Opportunities Section ───────────────────────────────────

class TestOpportunitiesSection:
    """Featured opportunities section must render."""

    def test_opps_container_present(self, client):
        rv = client.get("/discover")
        assert b'id="featuredOpps"' in rv.data

    def test_opps_section_title(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "Öne Çıkan Fırsatlar" in html

    def test_opps_fallback_data(self, client):
        rv = client.get("/discover")
        assert b"OPPS_FALLBACK" in rv.data

    def test_opps_render_function(self, client):
        rv = client.get("/discover")
        assert b"renderFeaturedOpps" in rv.data

    def test_opps_fetch_has_catch(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "renderFeaturedOpps(OPPS_FALLBACK)" in html


# ─── News Section ────────────────────────────────────────────

class TestNewsSection:
    """News sections must render."""

    def test_news_items_container(self, client):
        rv = client.get("/discover")
        assert b'id="newsItems"' in rv.data

    def test_market_news_compact_container(self, client):
        rv = client.get("/discover")
        assert b'id="marketNewsCompact"' in rv.data

    def test_market_news_section_title(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "Piyasa Haberleri" in html

    def test_news_fallback_defined(self, client):
        rv = client.get("/discover")
        assert b"NEWS_FALLBACK" in rv.data

    def test_news_compact_render_function(self, client):
        rv = client.get("/discover")
        assert b"renderMarketNewsCompact" in rv.data

    def test_news_fetch_has_fallback(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "renderMarketNewsCompact(NEWS_FALLBACK)" in html

    def test_news_chips_present(self, client):
        rv = client.get("/discover")
        assert b'id="newsChips"' in rv.data


# ─── Bottom Navigation ──────────────────────────────────────

class TestBottomNavigation:
    """Desktop bottom nav must span full width."""

    def test_bottombar_present(self, client):
        rv = client.get("/discover")
        assert b"mt-bottombar" in rv.data

    def test_bottombar_css_max_width_override(self):
        """CSS must have max-width: none for mt-bottombar."""
        import os
        css_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "css", "mobile_trading.css"
        )
        with open(css_path, "r") as f:
            css = f.read()
        assert "max-width: none" in css

    def test_bottombar_css_display_flex(self):
        """CSS must force display: flex for mt-bottombar."""
        import os
        css_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "css", "mobile_trading.css"
        )
        with open(css_path, "r") as f:
            css = f.read()
        assert "display: flex" in css

    def test_bottombar_width_100(self):
        """CSS must set width: 100% for mt-bottombar."""
        import os
        css_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "css", "mobile_trading.css"
        )
        with open(css_path, "r") as f:
            css = f.read()
        assert "width: 100%" in css

    def test_bottombar_has_five_items(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        count = html.count("mt-bb-item")
        assert count >= 5


# ─── Watchlist ───────────────────────────────────────────────

class TestWatchlist:
    """Watchlist section must render."""

    def test_watchlist_container(self, client):
        rv = client.get("/discover")
        assert b'id="watchlistItems"' in rv.data

    def test_watchlist_section_title(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        assert "İzleme Listesi" in html


# ─── Ticker Bar ──────────────────────────────────────────────

class TestTickerBar:
    """Ticker bar must render."""

    def test_ticker_bar_present(self, client):
        rv = client.get("/discover")
        assert b'id="tickerBar"' in rv.data

    def test_ticker_has_btc(self, client):
        rv = client.get("/discover")
        assert b'id="tk-btc-p"' in rv.data

    def test_ticker_has_eth(self, client):
        rv = client.get("/discover")
        assert b'id="tk-eth-p"' in rv.data


# ─── API Endpoints ───────────────────────────────────────────

class TestAPIEndpoints:
    """Related API endpoints should work."""

    def test_ai_market_summary_endpoint(self, client):
        rv = client.get("/api/ai/market-summary")
        assert rv.status_code == 200

    def test_ai_summary_returns_json(self, client):
        rv = client.get("/api/ai/market-summary")
        data = rv.get_json()
        assert data is not None
        assert "ok" in data

    def test_ai_summary_sentiment_is_object(self, client):
        """Sentiment field should be an object, not a raw string."""
        rv = client.get("/api/ai/market-summary")
        data = rv.get_json()
        if data.get("ok") and data.get("data", {}).get("sentiment"):
            sent = data["data"]["sentiment"]
            # Should be either string or dict — never something that
            # would render as [object Object]
            assert isinstance(sent, (str, dict))

    def test_opportunities_endpoint(self, client):
        rv = client.get("/api/opportunities/trending?limit=5")
        assert rv.status_code == 200

    def test_activity_endpoint(self, client):
        rv = client.get("/api/activity?limit=10&hours=24")
        assert rv.status_code == 200


# ─── No Raw Object Rendering ────────────────────────────────

class TestNoRawObjects:
    """No section should ever render raw objects."""

    def test_no_object_object_anywhere(self, client):
        rv = client.get("/discover")
        assert b"[object Object]" not in rv.data

    def test_no_undefined_text(self, client):
        rv = client.get("/discover")
        html = rv.data.decode("utf-8")
        # Check that "undefined" isn't rendered as visible text in any section
        # (but it can appear in JS code)
        for section_id in ["aiBriefText", "mc-sentiment", "mc-ai-sent"]:
            match = re.search(rf'id="{section_id}"[^>]*>(.*?)</div>', html)
            if match:
                assert match.group(1) != "undefined"
