# -*- coding: utf-8 -*-
"""FAZ 8 unit tests — Background job centralization.

Tests verify:
    - app/background/jobs.py exists and is importable
    - All 3 loop functions moved out of monolith
    - start_background_jobs lives in app.background.jobs
    - JobManager integration (register + start_all)
    - _BG_STARTED / _BG_LOCK removed from monolith
    - TICKERS_KEY accessible for ws_stream
    - No thread starts at import time
    - Monolith shrank (< 350 lines)
    - All critical routes still registered
    - No duplicate job definitions
"""
import importlib
import inspect
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_background_package_importable():
    """app.background package is importable."""
    import app.background
    assert hasattr(app.background, "start_background_jobs")


def test_jobs_module_importable():
    """app.background.jobs module is importable."""
    import app.background.jobs
    assert hasattr(app.background.jobs, "start_background_jobs")
    assert hasattr(app.background.jobs, "binance_ticker_ws_loop")
    assert hasattr(app.background.jobs, "refresh_loop")
    assert hasattr(app.background.jobs, "refresh_top4h_loop")


def test_helper_functions_in_jobs():
    """Helper functions moved to jobs module."""
    import app.background.jobs as jobs
    assert hasattr(jobs, "fetch_4h_klines_for_symbols")
    assert hasattr(jobs, "build_top_coins_4h_dataset")


def test_constants_in_jobs():
    """Constants moved to jobs module."""
    import app.background.jobs as jobs
    assert hasattr(jobs, "TICKERS_KEY")
    assert hasattr(jobs, "BINANCE_TICKER_STREAM")
    assert hasattr(jobs, "TOP4H_REFRESH_SEC")
    assert hasattr(jobs, "TOP4H_MAX_SYMBOLS")
    assert hasattr(jobs, "TOP4H_KLINES")
    assert hasattr(jobs, "TOP4H_INTERVAL")
    assert jobs.TOP4H_INTERVAL == "4h"


def test_monolith_no_bg_guard():
    """Monolith no longer has _BG_STARTED / _BG_LOCK."""
    src = open("legacy_monolith.py").read()
    assert "_BG_STARTED" not in src, "_BG_STARTED still in monolith"
    assert "_BG_LOCK" not in src, "_BG_LOCK still in monolith"


def test_monolith_no_loop_defs():
    """Loop functions removed from monolith."""
    src = open("legacy_monolith.py").read()
    assert "def binance_ticker_ws_loop" not in src
    assert "def refresh_loop" not in src
    assert "def refresh_top4h_loop" not in src
    assert "def fetch_4h_klines_for_symbols" not in src


def test_monolith_no_start_background_jobs_def():
    """start_background_jobs function removed from monolith."""
    src = open("legacy_monolith.py").read()
    assert "def start_background_jobs" not in src


def test_monolith_no_thread_start():
    """No direct threading.Thread().start() calls in monolith."""
    src = open("legacy_monolith.py").read()
    # Should not have any .start() thread invocations
    assert "Thread(target=" not in src, "Direct thread start still in monolith"


def test_monolith_imports_from_background():
    """Monolith imports needed constants from app.background.jobs."""
    src = open("legacy_monolith.py").read()
    assert "from app.background.jobs import" in src
    assert "TICKERS_KEY" in src
    assert "build_top_coins_4h_dataset" in src


def test_monolith_ws_stream_preserved():
    """ws_stream route still defined in monolith (needs sock)."""
    src = open("legacy_monolith.py").read()
    assert "def ws_stream" in src
    assert "ws/stream" in src


def test_monolith_shrank():
    """Monolith should be < 500 lines (grew from FAZ 8 baseline due to new routes)."""
    lines = len(open("legacy_monolith.py").readlines())
    assert lines < 500, f"Monolith still {lines} lines, expected < 500"


def test_app_init_delegates_to_background():
    """app/__init__.py delegates start_background_jobs to app.background."""
    src = open("app/__init__.py").read()
    assert "app.background.jobs" in src
    assert "legacy_monolith.start_background_jobs" not in src


def test_no_import_time_thread_start():
    """Importing app.background.jobs should NOT start any threads."""
    initial_count = threading.active_count()
    import app.background.jobs  # noqa: F401
    # re-import won't re-execute, but ensures no side effects
    importlib.reload(app.background.jobs)
    after_count = threading.active_count()
    assert after_count <= initial_count + 0, \
        f"Thread count increased from {initial_count} to {after_count} on import"


def test_job_manager_has_register():
    """JobManager has register_thread and start_all methods."""
    from core.job_manager import JobManager
    jm = JobManager()
    assert hasattr(jm, "register_thread")
    assert hasattr(jm, "start_all")
    assert hasattr(jm, "list_jobs")
    assert jm.started is False


def test_all_critical_routes_preserved():
    """All critical routes still present after FAZ 8."""
    import legacy_monolith
    rules = [r.rule for r in legacy_monolith.app.url_map.iter_rules()]
    for route in [
        "/", "/trade", "/chat", "/tv",
        "/api/fng", "/api/signal",
        "/api/market/symbols", "/api/market/klines",
        "/api/orderflow/health", "/api/orderflow/symbols",
        "/api/liquidation/symbols",
        "/api/alpha/status", "/api/alpha/symbols",
        "/api/etf_events", "/api/top_coins_4h",
        "/api/thresholds", "/api/mobile_snapshot",
    ]:
        assert route in rules, f"Route {route} missing"


def test_websocket_import_not_in_monolith():
    """websocket module import removed from monolith (moved to jobs)."""
    src = open("legacy_monolith.py").read()
    assert "import websocket" not in src, "websocket import still in monolith"


def test_jobs_uses_job_manager():
    """jobs.py registers via job_manager."""
    src = open("app/background/jobs.py").read()
    assert "job_manager.register_thread" in src
    assert "job_manager.start_all" in src
    assert 'zkr_analiz:ticker_ws' in src
    assert 'zkr_analiz:refresh' in src
    assert 'zkr_analiz:refresh_top4h' in src
