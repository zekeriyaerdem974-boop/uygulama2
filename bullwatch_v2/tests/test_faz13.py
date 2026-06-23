"""
FAZ 13 — Indicator System Tests
Tests the indicator engine, overlay manager integration, UI components,
and frontend asset delivery without using mock data.
"""

import pytest
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Static file existence ─────────────────────────────────────────────────

def test_indicators_js_exists():
    path = os.path.join(ROOT, "static", "js", "indicators.js")
    assert os.path.isfile(path), "indicators.js missing"


def test_indicators_js_has_engine():
    path = os.path.join(ROOT, "static", "js", "indicators.js")
    code = open(path).read()
    for fn in ["ema", "emaNext", "sma", "smaNext", "vwap", "vwapNext",
               "bollinger", "bollingerNext", "volumeMA"]:
        assert fn in code, f"IndicatorEngine.{fn} missing"


def test_indicators_js_is_iife():
    """IndicatorEngine should be an IIFE to avoid polluting global scope."""
    code = open(os.path.join(ROOT, "static", "js", "indicators.js")).read()
    assert "const IndicatorEngine" in code
    assert "return {" in code


# ── trade.js FAZ 13 integration ──────────────────────────────────────────

def _trade_js():
    return open(os.path.join(ROOT, "static", "js", "trade.js")).read()


def test_trade_js_has_indicator_defs():
    code = _trade_js()
    assert "INDICATOR_DEFS" in code
    for key in ["ema20", "ema50", "ema200", "sma50", "sma200",
                "vwap", "bollinger", "volumeMA"]:
        assert key in code, f"INDICATOR_DEFS missing {key}"


def test_trade_js_has_overlay_manager():
    code = _trade_js()
    assert "indicatorOverlayManager" in code
    for method in ["init", "updateAll", "toggle", "isActive"]:
        assert method in code, f"indicatorOverlayManager missing {method}"


def test_trade_js_has_localstorage_persistence():
    code = _trade_js()
    assert "localStorage" in code
    assert "bw_active_indicators" in code
    assert "loadIndicatorState" in code
    assert "saveIndicatorState" in code


def test_trade_js_has_dropdown_ui():
    code = _trade_js()
    assert "ind-dropdown" in code
    assert "ind-toggle-btn" in code
    assert "ind-color-dot" in code


def test_trade_js_calls_overlay_update_in_refresh():
    code = _trade_js()
    assert "indicatorOverlayManager.updateAll()" in code


def test_trade_js_inits_overlay_manager():
    code = _trade_js()
    assert "indicatorOverlayManager.init()" in code


def test_chart_manager_exposes_chart():
    code = _trade_js()
    assert "getChart" in code
    assert "getVolSeries" in code


def test_trade_js_uses_indicator_engine():
    code = _trade_js()
    for fn in ["IndicatorEngine.ema", "IndicatorEngine.sma",
               "IndicatorEngine.vwap", "IndicatorEngine.bollinger",
               "IndicatorEngine.volumeMA"]:
        assert fn in code, f"trade.js missing call to {fn}"


def test_trade_js_incremental_update():
    """Verify incremental update logic exists (performance optimization)."""
    code = _trade_js()
    assert "incremental" in code.lower()
    assert "_applyIncremental" in code
    assert "_applyFull" in code


# ── trade.css FAZ 13 styles ─────────────────────────────────────────────

def _trade_css():
    return open(os.path.join(ROOT, "static", "css", "trade.css")).read()


def test_trade_css_has_dropdown_styles():
    css = _trade_css()
    for cls in [".ind-dropdown-wrapper", ".ind-toggle-btn", ".ind-dropdown",
                ".ind-dropdown-item", ".ind-color-dot", ".ind-arrow"]:
        assert cls in css, f"CSS missing {cls}"


def test_trade_css_dropdown_animation():
    css = _trade_css()
    assert "indFadeIn" in css


def test_trade_css_checkbox_custom():
    css = _trade_css()
    assert 'input[type="checkbox"]' in css
    assert "appearance: none" in css


# ── trade.html template ──────────────────────────────────────────────────

def _trade_html():
    return open(os.path.join(ROOT, "templates", "trade.html")).read()


def test_trade_html_loads_indicators_js():
    html = _trade_html()
    assert "indicators.js" in html


def test_trade_html_script_order():
    """indicators.js must load BEFORE trade.js."""
    html = _trade_html()
    pos_ind = html.index("indicators.js")
    pos_trade = html.index("trade.js")
    assert pos_ind < pos_trade, "indicators.js must load before trade.js"


# ── Indicator color scheme ───────────────────────────────────────────────

def test_indicator_colors():
    code = _trade_js()
    # EMA colors
    assert "#f5c842" in code, "EMA20 yellow missing"
    assert "#f5882a" in code, "EMA50 orange missing"
    assert "#e84040" in code, "EMA200 red missing"
    # SMA colors
    assert "#5b8cf5" in code, "SMA50 blue missing"
    assert "#a855f7" in code, "SMA200 purple missing"
    # VWAP
    assert "#26d9a8" in code, "VWAP teal missing"
    # Bollinger
    assert "#8899b0" in code, "Bollinger gray missing"
    # Volume MA
    assert "#f5a623" in code, "Volume MA amber missing"


# ── Default state ────────────────────────────────────────────────────────

def test_default_ema20_active():
    """EMA 20 should be active by default."""
    code = _trade_js()
    assert "ema20: true" in code


def test_default_others_inactive():
    """Other indicators should be inactive by default."""
    code = _trade_js()
    for key in ["ema50", "ema200", "sma50", "sma200", "vwap", "bollinger", "volumeMA"]:
        assert f"{key}: false" in code, f"{key} should default to false"


# ── Backend compat ────────────────────────────────────────────────────────

def test_no_new_backend_endpoints():
    """FAZ 13 should not add any new backend API endpoints."""
    from app import create_app
    app = create_app()
    rules = [r.rule for r in app.url_map.iter_rules()]
    # No /api/indicators/ema, /api/indicators/sma, etc.
    for path in rules:
        assert "/api/indicators/ema" not in path
        assert "/api/indicators/sma" not in path
        assert "/api/indicators/vwap" not in path
        assert "/api/indicators/bollinger" not in path


def test_klines_endpoint_unchanged():
    """The klines endpoint should still work unchanged."""
    from app import create_app
    app = create_app()
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/market/klines" in rules


# ── Live endpoint tests (server must be running) ────────────────────────

@pytest.fixture
def live_session():
    """Only run live tests if server is reachable."""
    import requests
    try:
        r = requests.get("http://127.0.0.1:34000/api/orderflow/health", timeout=3)
        if r.status_code == 200:
            return requests.Session()
    except Exception:
        pass
    pytest.skip("Server not running on port 34000")


def test_live_trade_page(live_session):
    r = live_session.get("http://127.0.0.1:34000/trade")
    assert r.status_code == 200
    assert "indicators.js" in r.text
    assert "trade.js" in r.text


def test_live_indicators_js_served(live_session):
    r = live_session.get("http://127.0.0.1:34000/static/js/indicators.js")
    assert r.status_code == 200
    assert "IndicatorEngine" in r.text


def test_live_klines_data_for_indicators(live_session):
    """Klines data must have all fields needed for indicator calculation."""
    r = live_session.get("http://127.0.0.1:34000/api/market/klines?symbol=BTCUSDT&interval=15m&limit=100")
    js = r.json()
    candles = js.get("candles", [])
    volumes = js.get("volume", [])
    assert len(candles) >= 50
    assert len(volumes) >= 50
    c = candles[0]
    assert all(k in c for k in ["time", "open", "high", "low", "close"])
    v = volumes[0]
    assert "time" in v and "value" in v
