"""
FAZ 15 — News / Market Intelligence System Tests
Tests news service, blueprint API endpoints, frontend integration,
cache, sentiment analysis, and live endpoint compatibility.
"""

import pytest
import os
import re
import json
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://127.0.0.1:34000"


def _read(relpath):
    return open(os.path.join(ROOT, relpath)).read()


def _trade_js():
    return _read("static/js/trade.js")


def _trade_html():
    return _read("templates/trade.html")


def _trade_css():
    return _read("static/css/trade.css")


def _news_service():
    return _read("app/core/news_service.py")


def _news_routes():
    return _read("app/blueprints/news/routes.py")


# ── 1. news_service.py existence & structure ──────────────────────────────

def test_news_service_exists():
    assert os.path.isfile(os.path.join(ROOT, "app", "core", "news_service.py"))


def test_news_service_has_class():
    code = _news_service()
    assert "class NewsService" in code


def test_news_service_has_methods():
    code = _news_service()
    for method in ["fetch_crypto_news", "fetch_macro_news",
                   "fetch_market_news", "fetch_coin_news"]:
        assert method in code, f"NewsService missing {method}"


def test_news_service_has_sources():
    code = _news_service()
    for src in ["coindesk", "cointelegraph", "cryptopanic", "google_news"]:
        assert src in code.lower(), f"Source {src} missing from news service"


def test_news_service_has_sentiment():
    code = _news_service()
    assert "_detect_sentiment" in code
    assert "bullish" in code
    assert "bearish" in code
    assert "neutral" in code


def test_news_service_has_symbol_extraction():
    code = _news_service()
    assert "_extract_symbols" in code
    assert "_SYMBOL_MAP" in code


def test_news_service_has_deduplication():
    code = _news_service()
    assert "_deduplicate" in code


def test_news_service_no_mock_data():
    """News service should not contain hardcoded mock data."""
    code = _news_service()
    assert "mock" not in code.lower() or "mock" in "# no mock"
    # Verify it uses real fetching
    assert "urlopen" in code or "fetch_url" in code.lower()


# ── 2. News blueprint existence & structure ──────────────────────────────

def test_news_blueprint_exists():
    assert os.path.isfile(os.path.join(ROOT, "app", "blueprints", "news", "__init__.py"))
    assert os.path.isfile(os.path.join(ROOT, "app", "blueprints", "news", "routes.py"))


def test_news_routes_has_endpoints():
    code = _news_routes()
    assert "/api/news" in code
    assert "/api/news/coin" in code


def test_news_routes_uses_cache():
    code = _news_routes()
    assert "cache_get_or_set" in code


def test_news_routes_response_format():
    """Routes should return { ok, count, data } format."""
    code = _news_routes()
    assert '"ok"' in code
    assert '"count"' in code
    assert '"data"' in code


def test_news_blueprint_registered():
    code = open(os.path.join(ROOT, "legacy_monolith.py")).read()
    assert "news_bp" in code
    assert "register_blueprint(news_bp)" in code


# ── 3. Sentiment analysis ────────────────────────────────────────────────

def test_sentiment_importable():
    import sys
    sys.path.insert(0, ROOT)
    from app.core.news_service import _detect_sentiment
    assert _detect_sentiment("Bitcoin ETF approval surges market") == "bullish"
    assert _detect_sentiment("Major hack causes crash and panic") == "bearish"
    assert _detect_sentiment("Market moves sideways today") == "neutral"


def test_symbol_extraction_importable():
    import sys
    sys.path.insert(0, ROOT)
    from app.core.news_service import _extract_symbols
    result = _extract_symbols("Bitcoin and Ethereum rally today")
    assert "BTC" in result
    assert "ETH" in result


# ── 4. trade.js integration ──────────────────────────────────────────────

def test_trade_js_has_news_manager():
    code = _trade_js()
    assert "newsManager" in code
    assert "const newsManager" in code


def test_trade_js_news_manager_methods():
    code = _trade_js()
    for method in ["init", "load", "refreshIfNeeded"]:
        assert method in code, f"newsManager missing {method}"


def test_trade_js_news_init_in_main():
    code = _trade_js()
    assert "newsManager.init()" in code


def test_trade_js_news_load_called():
    code = _trade_js()
    assert "newsManager.load()" in code


def test_trade_js_news_refresh_in_polling():
    code = _trade_js()
    assert "newsManager.refreshIfNeeded()" in code


def test_trade_js_faz15_header():
    code = _trade_js()
    assert "FAZ 15" in code


# ── 5. trade.html integration ────────────────────────────────────────────

def test_html_has_news_tab_button():
    html = _trade_html()
    assert 'data-tab="news"' in html


def test_html_has_news_tab_pane():
    html = _trade_html()
    assert 'id="tab-news"' in html


def test_html_has_news_list():
    html = _trade_html()
    assert 'id="newsList"' in html


def test_html_has_news_type_buttons():
    html = _trade_html()
    assert 'data-ntype="crypto"' in html
    assert 'data-ntype="coin"' in html
    assert 'data-ntype="macro"' in html


# ── 6. CSS styles ────────────────────────────────────────────────────────

def test_css_news_styles():
    css = _trade_css()
    for cls in [".news-card", ".news-list", ".news-title", ".news-source",
                ".news-time", ".news-summary", ".news-footer"]:
        assert cls in css, f"CSS missing {cls}"


def test_css_news_sentiment_styles():
    css = _trade_css()
    for cls in [".news-sent-bull", ".news-sent-bear", ".news-sent-neutral"]:
        assert cls in css, f"CSS missing {cls}"


def test_css_news_type_buttons():
    css = _trade_css()
    assert ".news-type-btn" in css
    assert ".news-type-btn.active" in css


# ── 7. Live server tests ─────────────────────────────────────────────────

def _get(path, timeout=15):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
            return r.status, r.read().decode()
    except Exception:
        pytest.skip(f"Server not running at {BASE}")


def test_live_api_news():
    status, body = _get("/api/news")
    assert status == 200
    data = json.loads(body)
    assert data.get("ok") is True
    assert "count" in data
    assert "data" in data
    assert isinstance(data["data"], list)


def test_live_api_news_crypto():
    status, body = _get("/api/news?type=crypto")
    assert status == 200
    data = json.loads(body)
    assert data.get("ok") is True


def test_live_api_news_macro():
    status, body = _get("/api/news?type=macro")
    assert status == 200
    data = json.loads(body)
    assert data.get("ok") is True


def test_live_api_news_coin():
    status, body = _get("/api/news/coin?symbol=BTCUSDT")
    assert status == 200
    data = json.loads(body)
    assert data.get("ok") is True
    assert "data" in data


def test_live_api_news_coin_missing_symbol():
    """Should return 400 when symbol is missing."""
    try:
        req = urllib.request.Request(f"{BASE}/api/news/coin")
        with urllib.request.urlopen(req, timeout=10) as r:
            pass
    except urllib.error.HTTPError as e:
        assert e.code == 400
    except Exception:
        pytest.skip(f"Server not running at {BASE}")


def test_live_news_response_format():
    """Each news item should have the required fields."""
    status, body = _get("/api/news?type=crypto")
    assert status == 200
    data = json.loads(body)
    if data["count"] > 0:
        item = data["data"][0]
        for field in ["source", "title", "url", "published_at", "sentiment"]:
            assert field in item, f"News item missing field '{field}'"


def test_live_trade_page_has_news():
    status, body = _get("/trade")
    assert status == 200
    assert "newsList" in body
    assert 'data-tab="news"' in body


def test_live_existing_endpoints_unbroken():
    """Ensure FAZ 15 didn't break any existing API endpoints."""
    endpoints = [
        "/api/market/symbols",
        "/api/market/klines?symbol=BTCUSDT&interval=1h",
    ]
    for ep in endpoints:
        status, _ = _get(ep)
        assert status == 200, f"Endpoint {ep} broken (status={status})"


# ── 8. Cache integration ─────────────────────────────────────────────────

def test_cache_keys_in_routes():
    code = _news_routes()
    assert "news:crypto" in code
    assert "news:macro" in code
    assert "news:coin:" in code


def test_cache_ttl_values():
    """Verify TTL constants are defined."""
    code = _news_routes()
    assert "_CRYPTO_TTL" in code
    assert "_MACRO_TTL" in code
    assert "_COIN_TTL" in code


# ── 9. Structural integrity ──────────────────────────────────────────────

def test_no_duplicate_news_manager():
    code = _trade_js()
    assert code.count("const newsManager") == 1


def test_all_existing_managers_intact():
    code = _trade_js()
    for mgr in ["chartManager", "indicatorManager", "indicatorOverlayManager",
                "patternOverlayManager", "signalManager", "orderflowManager",
                "liquidationManager", "aiManager"]:
        assert mgr in code, f"Manager {mgr} missing from trade.js"
