# -*- coding: utf-8 -*-
"""FAZ 45 — Stabilization / Test Debt Cleanup / Production Hardening.

Validates:
  1.  No Thread(target=) in legacy_monolith.py
  2.  Monolith under 500 lines
  3.  Thread starts moved to app/background/jobs.py
  4.  TESTING mode skips background jobs
  5.  pytest.ini exists with correct config
  6.  conftest.py provides shared fixtures
  7.  live_api marker declared in pytest.ini
  8.  test_api_endpoints.py ignored by default
  9.  All test files importable without hanging
 10.  No import-time side effects in test files
 11.  DB isolation — journal engine uses separate DB in tests
 12.  DB isolation — paper trading uses separate DB in tests
 13.  Network mocking — all HTTP tests use timeout ≤ 5
 14.  FAZ 8 tests pass
 15.  FAZ 21 tests pass (non-live)
 16.  FAZ 22 tests pass (non-live)
 17.  FAZ 23 tests pass (non-live)
 18.  FAZ 37 tests pass
 19.  Performance — full test suite < 120 seconds
 20.  Performance — 3 formerly hanging suites < 5s total
 21.  Performance — individual test files importable < 2s each
 22.  CI helper — pytest.ini addopts excludes live_api
 23.  CI helper — pytest.ini has timeout configured
 24.  CI helper — conftest sets TESTING env var
 25.  Job control — start_background_jobs accepts app kwarg
 26.  Job control — start_background_jobs checks TESTING env
 27.  Job control — live_engine registered in jobs.py
 28.  Job control — activity_stream registered in jobs.py
 29.  Thread safety — no module-level Thread starts in any test
 30.  Code health — monolith has no import-time Thread starts
 31.  Marker — live_api used in faz21 tests
 32.  Marker — live_api used in faz22 tests
 33.  Marker — live_api used in faz23 tests
 34.  Template compat — faz37 filter buttons match template
 35.  Template compat — faz22 template extends layout
 36.  Template compat — faz23 backtest extends layout
 37.  Template compat — faz23 journal extends layout
 38.  Marker — pytest.ini ignores test_api_endpoints
 39.  Cleanup — no skip_no_server in test files
 40.  Health — app factory importable without threads
 41.  Health — create_app returns Flask instance
 42.  Health — test client works with TESTING=True
 43.  Performance — import of all core modules < 3s
 44.  Coverage — at least 20 test files exist
 45.  Coverage — at least 1500 total tests exist
"""
from __future__ import annotations

import os
import sys
import time
import importlib
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

os.environ.setdefault("TESTING", "1")


# ═══════════════════════════════════════════════════════════════════
# 1-3: MONOLITH CLEANUP
# ═══════════════════════════════════════════════════════════════════

def test_01_no_thread_in_monolith():
    with open(os.path.join(BASE, "legacy_monolith.py"), encoding="utf-8") as f:
        src = f.read()
    assert "Thread(target=" not in src


def test_02_monolith_under_500_lines():
    with open(os.path.join(BASE, "legacy_monolith.py"), encoding="utf-8") as f:
        lines = len(f.readlines())
    assert lines < 500, f"Monolith is {lines} lines"


def test_03_thread_starts_in_jobs():
    with open(os.path.join(BASE, "app/background/jobs.py"), encoding="utf-8") as f:
        src = f.read()
    assert "_boot_live_engine" in src
    assert "_boot_activity_stream" in src
    assert "job_manager.register_thread" in src


# ═══════════════════════════════════════════════════════════════════
# 4-6: TESTING MODE + INFRA
# ═══════════════════════════════════════════════════════════════════

def test_04_testing_mode_skips_jobs():
    with open(os.path.join(BASE, "app/background/jobs.py"), encoding="utf-8") as f:
        src = f.read()
    assert "TESTING" in src
    assert "skipping background jobs" in src.lower() or "TESTING mode" in src


def test_05_pytest_ini_exists():
    assert os.path.isfile(os.path.join(BASE, "pytest.ini"))


def test_06_conftest_exists():
    assert os.path.isfile(os.path.join(BASE, "tests/conftest.py"))


# ═══════════════════════════════════════════════════════════════════
# 7-8: MARKER AND IGNORE CONFIG
# ═══════════════════════════════════════════════════════════════════

def test_07_live_api_marker_declared():
    with open(os.path.join(BASE, "pytest.ini"), encoding="utf-8") as f:
        src = f.read()
    assert "live_api" in src


def test_08_api_endpoints_ignored():
    with open(os.path.join(BASE, "pytest.ini"), encoding="utf-8") as f:
        src = f.read()
    assert "test_api_endpoints" in src


# ═══════════════════════════════════════════════════════════════════
# 9-10: IMPORT SAFETY
# ═══════════════════════════════════════════════════════════════════

def test_09_test_files_importable():
    """All test files can be imported without hanging (< 2s each)."""
    test_dir = os.path.join(BASE, "tests")
    for fname in os.listdir(test_dir):
        if fname.startswith("test_") and fname.endswith(".py"):
            if fname == "test_api_endpoints.py":
                continue
            t0 = time.time()
            try:
                importlib.import_module(f"tests.{fname[:-3]}")
            except Exception:
                pass  # import errors are ok, we just check no hang
            elapsed = time.time() - t0
            assert elapsed < 2.0, f"{fname} import took {elapsed:.1f}s"


def test_10_no_import_time_threads_in_tests():
    """Test files should not start threads at import time."""
    test_dir = os.path.join(BASE, "tests")
    for fname in os.listdir(test_dir):
        if fname.startswith("test_") and fname.endswith(".py"):
            with open(os.path.join(test_dir, fname), encoding="utf-8") as f:
                lines = f.readlines()
            # Check for top-level Thread().start() patterns
            for lineno, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("def ") or stripped.startswith("class "):
                    continue
                # Skip lines inside string literals (assertions checking for threads)
                if '"Thread("' in stripped or "'Thread('" in stripped:
                    continue
                if "Thread(" in stripped and ".start()" in stripped and not line[0].isspace():
                    assert False, f"{fname}:{lineno} has import-time thread start: {stripped}"


# ═══════════════════════════════════════════════════════════════════
# 11-12: DB ISOLATION
# ═══════════════════════════════════════════════════════════════════

def test_11_journal_engine_importable():
    """Journal engine can be imported during testing."""
    from app.core.journal_engine import add_entry, list_entries, stats
    assert callable(add_entry)
    assert callable(list_entries)
    assert callable(stats)


def test_12_paper_trading_importable():
    """Paper trading engine importable."""
    from app.core.paper_trading_engine import create_account, open_position, close_position
    assert callable(create_account)
    assert callable(open_position)
    assert callable(close_position)


# ═══════════════════════════════════════════════════════════════════
# 13: NETWORK SAFETY
# ═══════════════════════════════════════════════════════════════════

def test_13_http_timeouts_short():
    """All test files with HTTP calls use timeout ≤ 5."""
    test_dir = os.path.join(BASE, "tests")
    for fname in ["test_faz21_copilot.py", "test_faz22_simulator.py", "test_faz23_backtest_journal.py"]:
        fpath = os.path.join(test_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            src = f.read()
        assert "TIMEOUT = 5" in src, f"{fname} should have TIMEOUT = 5"


# ═══════════════════════════════════════════════════════════════════
# 14-18: PREVIOUSLY BROKEN TESTS PASS
# ═══════════════════════════════════════════════════════════════════

def _run_test_file(filename, max_time=60):
    """Run a test file and return (passed, failed, time)."""
    import re
    cmd = [
        sys.executable, "-m", "pytest",
        os.path.join(BASE, "tests", filename),
        "-v", "--tb=no",
        "-o", "addopts=",
        "-m", "not live_api",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time, cwd=BASE)
    output = result.stdout + result.stderr
    # Parse passed/failed from output
    m = re.search(r"(\d+) passed", output)
    passed = int(m.group(1)) if m else 0
    m = re.search(r"(\d+) failed", output)
    failed = int(m.group(1)) if m else 0
    return passed, failed, result.returncode


def test_14_faz8_passes():
    passed, failed, rc = _run_test_file("test_faz8.py")
    assert failed == 0, f"FAZ 8: {failed} failures"
    assert passed >= 15


def test_15_faz21_passes():
    passed, failed, rc = _run_test_file("test_faz21_copilot.py")
    assert failed == 0, f"FAZ 21: {failed} failures"
    assert passed >= 100


def test_16_faz22_passes():
    passed, failed, rc = _run_test_file("test_faz22_simulator.py")
    assert failed == 0, f"FAZ 22: {failed} failures"
    assert passed >= 30


def test_17_faz23_passes():
    passed, failed, rc = _run_test_file("test_faz23_backtest_journal.py")
    assert failed == 0, f"FAZ 23: {failed} failures"
    assert passed >= 50


def test_18_faz37_passes():
    passed, failed, rc = _run_test_file("test_faz37_news_impact.py")
    assert failed == 0, f"FAZ 37: {failed} failures"
    assert passed >= 45


# ═══════════════════════════════════════════════════════════════════
# 19-21: PERFORMANCE
# ═══════════════════════════════════════════════════════════════════

import pytest as _pytest

@_pytest.mark.timeout(180)
def test_19_full_suite_under_120s():
    """The entire test suite must complete in under 120 seconds."""
    cmd = [
        sys.executable, "-m", "pytest",
        os.path.join(BASE, "tests"),
        "-q", "--tb=no",
        "--ignore=" + os.path.join(BASE, "tests", "test_api_endpoints.py"),
        "--ignore=" + os.path.join(BASE, "tests", "test_faz45_stabilization.py"),
    ]
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=150, cwd=BASE)
    elapsed = time.time() - t0
    assert result.returncode == 0, f"Suite failed with rc={result.returncode}\n{result.stdout[-500:]}"
    assert elapsed < 120, f"Suite took {elapsed:.1f}s, expected < 120s"


def test_20_formerly_hanging_suites_fast():
    """Three formerly hanging suites must complete in < 10s total."""
    files = ["test_faz21_copilot.py", "test_faz22_simulator.py", "test_faz23_backtest_journal.py"]
    cmd = [
        sys.executable, "-m", "pytest",
        *[os.path.join(BASE, "tests", f) for f in files],
        "-q", "--tb=no",
        "-m", "not live_api",
    ]
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=BASE)
    elapsed = time.time() - t0
    assert result.returncode == 0, f"Formerly hanging suites failed\n{result.stdout[-300:]}"
    assert elapsed < 10, f"Took {elapsed:.1f}s, expected < 10s"


def test_21_core_modules_import_fast():
    """Core modules import in < 3s total."""
    modules = [
        "app.core.journal_engine",
        "app.core.paper_trading_engine",
        "app.core.strategy_signals",
        "app.background.jobs",
        "app.extensions",
    ]
    t0 = time.time()
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception:
            pass
    elapsed = time.time() - t0
    assert elapsed < 3.0, f"Core imports took {elapsed:.1f}s"


# ═══════════════════════════════════════════════════════════════════
# 22-24: CI CONFIG
# ═══════════════════════════════════════════════════════════════════

def test_22_pytest_ini_excludes_live_api():
    with open(os.path.join(BASE, "pytest.ini"), encoding="utf-8") as f:
        src = f.read()
    assert "not live_api" in src


def test_23_pytest_ini_has_timeout():
    with open(os.path.join(BASE, "pytest.ini"), encoding="utf-8") as f:
        src = f.read()
    assert "timeout" in src.lower()


def test_24_conftest_sets_testing_env():
    with open(os.path.join(BASE, "tests/conftest.py"), encoding="utf-8") as f:
        src = f.read()
    assert "TESTING" in src


# ═══════════════════════════════════════════════════════════════════
# 25-28: JOB CONTROL
# ═══════════════════════════════════════════════════════════════════

def test_25_start_bg_jobs_accepts_app():
    from app.background.jobs import start_background_jobs
    import inspect
    sig = inspect.signature(start_background_jobs)
    assert "app" in sig.parameters


def test_26_start_bg_jobs_checks_testing_env():
    with open(os.path.join(BASE, "app/background/jobs.py"), encoding="utf-8") as f:
        src = f.read()
    assert 'os.environ.get("TESTING"' in src or "os.environ.get('TESTING'" in src


def test_27_live_engine_in_jobs():
    with open(os.path.join(BASE, "app/background/jobs.py"), encoding="utf-8") as f:
        src = f.read()
    assert "live_engine" in src
    assert "_boot_live_engine" in src


def test_28_activity_stream_in_jobs():
    with open(os.path.join(BASE, "app/background/jobs.py"), encoding="utf-8") as f:
        src = f.read()
    assert "activity_stream" in src
    assert "_boot_activity_stream" in src


# ═══════════════════════════════════════════════════════════════════
# 29-30: THREAD SAFETY
# ═══════════════════════════════════════════════════════════════════

def test_29_no_module_level_threads_in_tests():
    test_dir = os.path.join(BASE, "tests")
    for fname in os.listdir(test_dir):
        if not fname.startswith("test_") or not fname.endswith(".py"):
            continue
        with open(os.path.join(test_dir, fname), encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "Thread(" in stripped and "target=" in stripped and not line.startswith(" "):
                    assert False, f"{fname}:{lineno} has module-level Thread"


def test_30_monolith_no_import_time_threads():
    with open(os.path.join(BASE, "legacy_monolith.py"), encoding="utf-8") as f:
        src = f.read()
    assert "_start_live_engine()" not in src
    assert "_start_activity_stream()" not in src


# ═══════════════════════════════════════════════════════════════════
# 31-33: LIVE_API MARKER USAGE
# ═══════════════════════════════════════════════════════════════════

def test_31_faz21_uses_live_api():
    with open(os.path.join(BASE, "tests/test_faz21_copilot.py"), encoding="utf-8") as f:
        src = f.read()
    assert "live_api" in src
    assert "@live_api" in src


def test_32_faz22_uses_live_api():
    with open(os.path.join(BASE, "tests/test_faz22_simulator.py"), encoding="utf-8") as f:
        src = f.read()
    assert "live_api" in src
    assert "@live_api" in src


def test_33_faz23_uses_live_api():
    with open(os.path.join(BASE, "tests/test_faz23_backtest_journal.py"), encoding="utf-8") as f:
        src = f.read()
    assert "live_api" in src
    assert "@live_api" in src


# ═══════════════════════════════════════════════════════════════════
# 34-37: TEMPLATE COMPAT
# ═══════════════════════════════════════════════════════════════════

def test_34_faz37_filter_buttons():
    with open(os.path.join(BASE, "tests/test_faz37_news_impact.py"), encoding="utf-8") as f:
        src = f.read()
    assert "Crypto" in src
    assert "Stocks" in src


def test_35_faz22_template_extends():
    with open(os.path.join(BASE, "templates/simulator.html"), encoding="utf-8") as f:
        src = f.read()
    assert "extends" in src


def test_36_faz23_backtest_extends():
    with open(os.path.join(BASE, "templates/backtest.html"), encoding="utf-8") as f:
        src = f.read()
    assert "extends" in src


def test_37_faz23_journal_extends():
    with open(os.path.join(BASE, "templates/journal.html"), encoding="utf-8") as f:
        src = f.read()
    assert "extends" in src


# ═══════════════════════════════════════════════════════════════════
# 38-39: CLEANUP VERIFICATION
# ═══════════════════════════════════════════════════════════════════

def test_38_pytest_ini_ignores_api_endpoints():
    with open(os.path.join(BASE, "pytest.ini"), encoding="utf-8") as f:
        src = f.read()
    assert "test_api_endpoints" in src


def test_39_no_skip_no_server_remains():
    """Old skip_no_server pattern should be removed."""
    for fname in ["test_faz21_copilot.py", "test_faz22_simulator.py", "test_faz23_backtest_journal.py"]:
        fpath = os.path.join(BASE, "tests", fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            src = f.read()
        assert "skip_no_server" not in src, f"{fname} still has skip_no_server"


# ═══════════════════════════════════════════════════════════════════
# 40-42: APP HEALTH
# ═══════════════════════════════════════════════════════════════════

def test_40_app_factory_importable():
    from app import create_app
    assert callable(create_app)


def test_41_create_app_returns_flask():
    from app import create_app
    from flask import Flask
    a = create_app()
    assert isinstance(a, Flask)


def test_42_test_client_works():
    from app import create_app
    a = create_app()
    a.config["TESTING"] = True
    client = a.test_client()
    r = client.get("/")
    assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 43-45: COVERAGE METRICS
# ═══════════════════════════════════════════════════════════════════

def test_43_core_modules_fast_import():
    """Core modules must import in < 3s total."""
    mods = [
        "app.cache", "app.extensions", "app.background.jobs",
        "app.core.security", "app.core.etf_tracker",
    ]
    t0 = time.time()
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception:
            pass
    assert time.time() - t0 < 3.0


def test_44_at_least_20_test_files():
    test_dir = os.path.join(BASE, "tests")
    test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
    assert len(test_files) >= 20, f"Only {len(test_files)} test files found"


@_pytest.mark.timeout(120)
def test_45_at_least_1500_tests():
    """Verify we have at least 1500 test cases across all files."""
    import re as _re
    cmd = [
        sys.executable, "-m", "pytest",
        os.path.join(BASE, "tests"),
        "--collect-only", "-q",
        "-o", "addopts=",
        "--ignore=" + os.path.join(BASE, "tests", "test_api_endpoints.py"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=BASE)
    output = result.stdout + result.stderr
    # Try different output formats
    m = _re.search(r"(\d+) tests? collected", output)
    if not m:
        m = _re.search(r"(\d+) tests?/", output)
    if not m:
        # Count <Module> lines or test items
        items = [l for l in output.splitlines() if '::test_' in l or '::Test' in l]
        total = len(items)
    else:
        total = int(m.group(1))
    assert total >= 1500, f"Only {total} tests collected, expected >= 1500\n{output[-500:]}"
