# -*- coding: utf-8 -*-
"""FAZ 5 — Signal Engine Blueprint tests.

Verifies:
 1. signals blueprint registers expected routes
 2. engine module is importable and callable
 3. monolith no longer contains signal routes or evaluate_entry_signal
 4. all previous routes still exist
"""
import pathlib


# ── signals blueprint ──────────────────────────────────────────────────
def test_signals_bp_exists():
    from app.blueprints.signals import signals_bp
    assert signals_bp.name == "signals"


def test_engine_importable():
    from app.blueprints.signals.engine import evaluate_entry_signal
    assert callable(evaluate_entry_signal)


def test_engine_uses_core_deps():
    """engine.py should import from app.core, not re-implement."""
    src = pathlib.Path("app/blueprints/signals/engine.py").read_text()
    assert "from app.core.ta import" in src
    assert "from app.core.binance_client import" in src
    assert "from app.core.thresholds import" in src
    assert "from app.cache import" in src


def test_routes_file_has_signal_apis():
    src = pathlib.Path("app/blueprints/signals/routes.py").read_text()
    assert "/api/signal" in src
    assert "/api/signals" in src


def test_signal_routes_registered():
    """Both /api/signal and /api/signals must be in the Flask app."""
    from app import create_app
    flask_app = create_app()
    rules = [r.rule for r in flask_app.url_map.iter_rules()]
    assert "/api/signal" in rules
    assert "/api/signals" in rules


def test_monolith_no_signal_routes():
    """Monolith should NOT have @app.route for signal endpoints."""
    src = pathlib.Path("legacy_monolith.py").read_text()
    assert '@app.route("/api/signal")' not in src
    assert '@app.route("/api/signals")' not in src


def test_monolith_no_evaluate_entry_signal():
    """evaluate_entry_signal function def should be gone from monolith."""
    src = pathlib.Path("legacy_monolith.py").read_text()
    assert "def evaluate_entry_signal" not in src


def test_monolith_registers_signals_bp():
    src = pathlib.Path("legacy_monolith.py").read_text()
    assert "app.register_blueprint(signals_bp)" in src


def test_all_critical_routes_preserved():
    """All routes from FAZ 4 plus signal routes must still exist."""
    from app import create_app
    flask_app = create_app()
    rules = [r.rule for r in flask_app.url_map.iter_rules()
             if r.rule != "/static/<path:filename>"]
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


def test_engine_decision_keys():
    """Engine return dict must have the expected top-level keys."""
    from app.blueprints.signals.engine import evaluate_entry_signal
    # Inspect the function source for the expected return keys
    import inspect
    src = inspect.getsource(evaluate_entry_signal)
    for key in ("symbol", "now", "decision", "note", "ticks", "context", "risk", "pullback_targets"):
        assert f'"{key}"' in src, f"Missing key '{key}' in engine return"
