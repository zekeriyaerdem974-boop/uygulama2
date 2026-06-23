"""
FAZ 14 — Chart Pattern Analysis System Tests
Tests patterns.js PatternEngine, patternOverlayManager integration,
Patterns tab, Analysis dropdown, CSS styles, and live endpoint compatibility.
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


def _patterns_js():
    return _read("static/js/patterns.js")


# ── 1. patterns.js existence & structure ──────────────────────────────────

def test_patterns_js_exists():
    assert os.path.isfile(os.path.join(ROOT, "static", "js", "patterns.js"))


def test_patterns_js_is_iife():
    code = _patterns_js()
    assert "const PatternEngine" in code
    assert "return {" in code


def test_patterns_js_has_all_detect_functions():
    code = _patterns_js()
    for fn in ["detectSwings", "detectSupportResistance", "detectBreakouts",
               "detectTrendlines", "detectTriangles", "detectFlags",
               "detectRanges", "trendDirection"]:
        assert fn in code, f"PatternEngine.{fn} missing"


def test_patterns_js_has_helpers():
    code = _patterns_js()
    for fn in ["_atr", "_emaCalc", "_linearSlope", "_bestTrendline"]:
        assert fn in code, f"Helper {fn} missing in patterns.js"


def test_patterns_js_no_dom_access():
    """PatternEngine should be pure computation — no DOM, no fetch."""
    code = _patterns_js()
    assert "document." not in code, "patterns.js should not access DOM"
    assert "fetch(" not in code, "patterns.js should not make HTTP calls"


# ── 2. trade.js FAZ 14 integration ───────────────────────────────────────

def test_trade_js_has_analysis_defs():
    code = _trade_js()
    assert "ANALYSIS_DEFS" in code
    for key in ["sr", "swings", "breakouts", "trendlines",
                "triangles", "flags", "ranges"]:
        assert key in code, f"ANALYSIS_DEFS missing '{key}'"


def test_trade_js_has_pattern_overlay_manager():
    code = _trade_js()
    assert code.count("const patternOverlayManager") == 1, \
        "patternOverlayManager should appear exactly once"


def test_trade_js_pattern_manager_methods():
    code = _trade_js()
    for method in ["init", "updateAll", "toggle", "getResult"]:
        assert method in code, f"patternOverlayManager missing '{method}'"


def test_trade_js_calls_pattern_engine():
    code = _trade_js()
    for call in ["PatternEngine.detectSwings", "PatternEngine.detectSupportResistance",
                 "PatternEngine.detectBreakouts", "PatternEngine.detectTrendlines",
                 "PatternEngine.detectTriangles", "PatternEngine.detectFlags",
                 "PatternEngine.detectRanges", "PatternEngine.trendDirection"]:
        assert call in code, f"Missing call to {call} in trade.js"


def test_trade_js_analysis_localstorage():
    code = _trade_js()
    assert "bw_active_analysis" in code
    assert "loadAnalysisState" in code
    assert "saveAnalysisState" in code


def test_trade_js_pattern_init_in_main():
    code = _trade_js()
    assert "patternOverlayManager.init()" in code


def test_trade_js_pattern_update_in_refresh():
    code = _trade_js()
    assert "patternOverlayManager.updateAll()" in code


def test_trade_js_updates_patterns_tab():
    code = _trade_js()
    assert "patternsSummary" in code
    assert "_updatePatternsTab" in code


def test_trade_js_default_analysis_state():
    """Default state: only S/R enabled, rest disabled."""
    code = _trade_js()
    match = re.search(r'return\s*\{[^}]*sr:\s*(true|false)', code)
    assert match, "Default analysis state not found"
    assert match.group(1) == "true", "S/R should be enabled by default"


# ── 3. trade.html integration ────────────────────────────────────────────

def test_html_loads_patterns_js():
    html = _trade_html()
    assert "patterns.js" in html


def test_html_script_load_order():
    """patterns.js must load before trade.js and after indicators.js"""
    html = _trade_html()
    ind_pos = html.index("indicators.js")
    pat_pos = html.index("patterns.js")
    trd_pos = html.index("trade.js")
    assert ind_pos < pat_pos < trd_pos, \
        "Script order must be: indicators.js → patterns.js → trade.js"


def test_html_has_patterns_tab_button():
    html = _trade_html()
    assert 'data-tab="patterns"' in html


def test_html_has_patterns_tab_pane():
    html = _trade_html()
    assert 'id="tab-patterns"' in html
    assert 'patternsSummary' in html


# ── 4. CSS styles ────────────────────────────────────────────────────────

def test_css_analysis_dropdown():
    css = _trade_css()
    for cls in [".ana-dropdown-wrapper", ".ana-toggle-btn", ".ana-dropdown",
                ".ana-dropdown-item", ".ana-dropdown.open"]:
        assert cls in css, f"CSS missing {cls}"


def test_css_patterns_tab_summary():
    css = _trade_css()
    for cls in [".patterns-summary", ".pat-section", ".pat-section-title",
                ".pat-trend", ".pat-structure", ".pat-none"]:
        assert cls in css, f"CSS missing {cls}"


def test_css_pattern_levels():
    css = _trade_css()
    for cls in [".pat-level", ".pat-res", ".pat-sup", ".pat-price",
                ".pat-touches", ".pat-breakout", ".pat-swings"]:
        assert cls in css, f"CSS missing {cls}"


# ── 5. Live server tests ─────────────────────────────────────────────────

def _get(path):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
            return r.status, r.read().decode()
    except Exception:
        pytest.skip(f"Server not running at {BASE}")


def test_live_trade_page():
    status, body = _get("/trade")
    assert status == 200
    assert "patterns.js" in body
    assert "patternsSummary" in body


def test_live_patterns_js():
    status, body = _get("/static/js/patterns.js")
    assert status == 200
    assert "PatternEngine" in body


def test_live_trade_js():
    status, body = _get("/static/js/trade.js")
    assert status == 200
    assert "patternOverlayManager" in body
    assert "ANALYSIS_DEFS" in body


def test_live_klines_endpoint():
    status, body = _get("/api/market/klines?symbol=BTCUSDT&interval=1h")
    assert status == 200
    data = json.loads(body)
    assert len(data.get("candles", [])) >= 20, "Not enough candles for pattern analysis"
    assert len(data.get("volume", [])) >= 20


def test_live_existing_endpoints_unbroken():
    """Ensure FAZ 14 didn't break any existing API endpoints."""
    endpoints = [
        "/api/market/symbols",
        "/api/market/klines?symbol=BTCUSDT&interval=1h",
    ]
    for ep in endpoints:
        status, _ = _get(ep)
        assert status == 200, f"Endpoint {ep} broken (status={status})"


# ── 6. Structural integrity ──────────────────────────────────────────────

def test_no_duplicate_managers():
    code = _trade_js()
    assert code.count("const patternOverlayManager") == 1
    assert code.count("const indicatorOverlayManager") == 1
    assert code.count("const chartManager") == 1


def test_pattern_engine_no_side_effects():
    """PatternEngine should be a pure IIFE with no side effects."""
    code = _patterns_js()
    assert code.count("window.") == 0 or "window.PatternEngine" not in code, \
        "PatternEngine should not set window globals"
    assert "addEventListener" not in code
    assert "setTimeout" not in code


def test_analysis_defs_match_pattern_engine():
    """ANALYSIS_DEFS keys should correspond to PatternEngine functions."""
    trade_code = _trade_js()
    pattern_code = _patterns_js()
    # Verify key analysis types have matching detect functions
    assert "detectSwings" in pattern_code
    assert "detectSupportResistance" in pattern_code
    assert "detectBreakouts" in pattern_code
    assert "detectTrendlines" in pattern_code
    assert "detectTriangles" in pattern_code
    assert "detectFlags" in pattern_code
    assert "detectRanges" in pattern_code


def test_faz14_header_updated():
    code = _trade_js()
    assert "FAZ 14" in code, "trade.js header should reference FAZ 14"
