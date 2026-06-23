# -*- coding: utf-8 -*-
"""FAZ 4 — Dashboard Blueprint tests.

Verifies:
 1. app.core.thresholds module works standalone
 2. Dashboard blueprint registers all expected routes
 3. Monolith no longer contains moved routes
 4. Lazy imports in dashboard routes/api resolve correctly
"""
import pytest


# ── thresholds module ──────────────────────────────────────────────────
def test_thresholds_module_imports():
    from app.core.thresholds import (
        DEFAULT_THRESHOLDS, THRESHOLDS_KEY, get_thresholds, update_thresholds,
    )
    assert isinstance(DEFAULT_THRESHOLDS, dict)
    assert THRESHOLDS_KEY == "runtime_thresholds_v1"
    assert callable(get_thresholds)
    assert callable(update_thresholds)


def test_thresholds_default_keys():
    from app.core.thresholds import DEFAULT_THRESHOLDS
    expected = {
        "overextended_change24_max", "min_ret7_pct", "min_change24_pct",
        "max_change24_pct", "heat_atr_max", "require_btc_regime", "require_above200",
    }
    assert expected == set(DEFAULT_THRESHOLDS.keys())


# ── dashboard blueprint ───────────────────────────────────────────────
def test_dashboard_bp_exists():
    from app.blueprints.dashboard import dashboard_bp
    assert dashboard_bp.name == "dashboard"


def test_dashboard_routes_registered():
    """All 17 moved routes must appear in the Flask app's url_map."""
    from app import create_app
    flask_app = create_app()
    rules = [r.rule for r in flask_app.url_map.iter_rules()]
    dashboard_routes = [
        "/", "/chat", "/tv", "/trade", "/sim/mobile",
        "/api/mobile_snapshot", "/api/thresholds", "/api/fng",
        "/api/btc_indicators", "/api/coins_sma_summary",
        "/api/pump_candidates", "/api/bull_estimate",
        "/api/oi", "/api/hashrate", "/api/stablecoin_flow",
        "/api/coinbase_premium", "/api/trade_bundle",
    ]
    for route in dashboard_routes:
        assert route in rules, f"Missing dashboard route: {route}"


def test_monolith_no_dashboard_routes():
    """Monolith source should NOT contain @app.route decorators for moved routes."""
    import pathlib
    src = pathlib.Path("legacy_monolith.py").read_text()
    moved = [
        '"/api/mobile_snapshot"', '"/api/thresholds"', '"/api/fng"',
        '"/api/btc_indicators"', '"/api/coins_sma_summary"',
        '"/api/pump_candidates"', '"/api/bull_estimate"',
        '"/api/oi"', '"/api/hashrate"', '"/api/stablecoin_flow"',
        '"/api/coinbase_premium"', '"/api/trade_bundle"',
    ]
    for pattern in moved:
        assert f"@app.route({pattern}" not in src and f'@app.get({pattern}' not in src, \
            f"Monolith still contains route for {pattern}"


def test_monolith_imports_thresholds_from_core():
    """Thresholds should be used from app.core.thresholds by blueprints (not monolith directly after FAZ 11)."""
    import pathlib
    # After FAZ 11 cleanup, thresholds are imported by blueprints, not the monolith itself
    src = pathlib.Path("legacy_monolith.py").read_text()
    assert "def get_thresholds" not in src  # function def should be gone
    # Verify thresholds module exists and is importable
    from app.core.thresholds import get_thresholds
    assert callable(get_thresholds)


def test_monolith_registers_dashboard_bp():
    """Monolith should register the dashboard blueprint."""
    import pathlib
    src = pathlib.Path("legacy_monolith.py").read_text()
    assert "app.register_blueprint(dashboard_bp)" in src


def test_dashboard_api_file_routes():
    """api.py should contain all 12 dashboard API routes."""
    import pathlib
    src = pathlib.Path("app/blueprints/dashboard/api.py").read_text()
    expected_routes = [
        "/api/mobile_snapshot", "/api/thresholds", "/api/fng",
        "/api/btc_indicators", "/api/coins_sma_summary",
        "/api/pump_candidates", "/api/bull_estimate",
        "/api/oi", "/api/hashrate", "/api/stablecoin_flow",
        "/api/coinbase_premium", "/api/trade_bundle",
    ]
    for route in expected_routes:
        assert route in src, f"Missing route in api.py: {route}"


def test_dashboard_routes_file():
    """routes.py should contain all 5 HTML render routes."""
    import pathlib
    src = pathlib.Path("app/blueprints/dashboard/routes.py").read_text()
    for route in ['/"', '/chat"', '/tv"', '/trade"', '/sim/mobile"']:
        assert route in src, f"Missing route in routes.py: {route}"


def test_total_route_count():
    """Total route count should be preserved after FAZ 4."""
    from app import create_app
    flask_app = create_app()
    rules = [r.rule for r in flask_app.url_map.iter_rules()
             if r.rule != "/static/<path:filename>"]
    # Before FAZ 4: same number of routes, just moved to blueprint
    critical = [
        "/", "/chat", "/tv", "/trade", "/sim/mobile",
        "/api/mobile_snapshot", "/api/thresholds", "/api/fng",
        "/api/btc_indicators", "/api/coins_sma_summary",
        "/api/pump_candidates", "/api/bull_estimate",
        "/api/oi", "/api/hashrate", "/api/stablecoin_flow",
        "/api/coinbase_premium", "/api/trade_bundle",
        "/api/signal", "/api/signals", "/api/etf_events",
        "/api/top_coins_4h", "/api/chat",
        "/apk/ZKR Analiz.apk", "/ws/stream",
    ]
    for route in critical:
        assert route in rules, f"Missing route: {route}"
