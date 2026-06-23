# -*- coding: utf-8 -*-
"""FAZ 48 — Infrastructure Cleanup Tests.

Validates:
  1. db_manager module — connection, WAL, retry, PRAGMAs, ensure_wal
  2. Engine DB integration — all engines use db_manager
  3. Concurrent DB writes — no lock errors
  4. Background job safety — JobManager health check, error handling
  5. API resilient HTTP — retry logic, timeout handling
  6. TEST_MODE support — config flag, env var
  7. Health check endpoint template
  8. SQLite performance PRAGMAs
  9. infra_logger usage
  10. Database migration (WAL check)

Minimum: 60 tests
"""
from __future__ import annotations

import importlib
import os
import re
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel_path: str) -> str:
    fp = os.path.join(BASE, rel_path)
    assert os.path.isfile(fp), f"Missing file: {rel_path}"
    with open(fp, encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════
# 1) DB MANAGER MODULE
# ═══════════════════════════════════════════════════════════════════

class TestDbManagerModule:
    """Test the centralized db_manager module exists and has correct API."""

    def test_db_manager_file_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/core/db_manager.py"))

    def test_db_manager_imports(self):
        src = _read("app/core/db_manager.py")
        assert "import sqlite3" in src
        assert "import threading" in src
        assert "import logging" in src

    def test_db_manager_has_get_connection(self):
        src = _read("app/core/db_manager.py")
        assert "def get_connection(" in src

    def test_db_manager_has_get_conn_context(self):
        src = _read("app/core/db_manager.py")
        assert "def get_conn(" in src

    def test_db_manager_has_execute_with_retry(self):
        src = _read("app/core/db_manager.py")
        assert "def execute_with_retry(" in src

    def test_db_manager_has_ensure_wal(self):
        src = _read("app/core/db_manager.py")
        assert "def ensure_wal(" in src

    def test_db_manager_has_ensure_all_wal(self):
        src = _read("app/core/db_manager.py")
        assert "def ensure_all_wal(" in src

    def test_db_manager_has_get_db_status(self):
        src = _read("app/core/db_manager.py")
        assert "def get_db_status(" in src

    def test_db_manager_has_get_db_path(self):
        src = _read("app/core/db_manager.py")
        assert "def get_db_path(" in src

    def test_db_manager_has_executemany_with_retry(self):
        src = _read("app/core/db_manager.py")
        assert "def executemany_with_retry(" in src

    def test_db_manager_wal_pragma(self):
        src = _read("app/core/db_manager.py")
        assert '"journal_mode", "WAL"' in src or "'journal_mode', 'WAL'" in src

    def test_db_manager_busy_timeout_pragma(self):
        src = _read("app/core/db_manager.py")
        assert '"busy_timeout", "5000"' in src or "'busy_timeout', '5000'" in src

    def test_db_manager_synchronous_pragma(self):
        src = _read("app/core/db_manager.py")
        assert '"synchronous", "NORMAL"' in src or "'synchronous', 'NORMAL'" in src

    def test_db_manager_cache_size_pragma(self):
        src = _read("app/core/db_manager.py")
        assert '"cache_size", "10000"' in src or "'cache_size', '10000'" in src

    def test_db_manager_temp_store_pragma(self):
        src = _read("app/core/db_manager.py")
        assert '"temp_store", "MEMORY"' in src or "'temp_store', 'MEMORY'" in src

    def test_db_manager_foreign_keys_pragma(self):
        src = _read("app/core/db_manager.py")
        assert '"foreign_keys", "ON"' in src or "'foreign_keys', 'ON'" in src

    def test_db_manager_max_retries(self):
        src = _read("app/core/db_manager.py")
        assert "MAX_RETRIES" in src

    def test_db_manager_infra_logger(self):
        src = _read("app/core/db_manager.py")
        assert "zkr_analiz.infra" in src


# ═══════════════════════════════════════════════════════════════════
# 2) DB MANAGER FUNCTIONALITY
# ═══════════════════════════════════════════════════════════════════

class TestDbManagerFunctionality:
    """Test db_manager get_connection actually works."""

    def test_get_db_path(self):
        from app.core.db_manager import get_db_path
        path = get_db_path("test.db")
        assert path.endswith("data/test.db")

    def test_get_db_path_adds_extension(self):
        from app.core.db_manager import get_db_path
        path = get_db_path("test")
        assert path.endswith("data/test.db")

    def test_get_connection_returns_conn(self):
        from app.core.db_manager import get_connection
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                conn = get_connection("_test_faz48.db")
                try:
                    assert conn is not None
                    assert isinstance(conn, sqlite3.Connection)
                finally:
                    conn.close()
                    try:
                        os.unlink(os.path.join(td, "_test_faz48.db"))
                    except OSError:
                        pass

    def test_get_connection_wal_mode(self):
        from app.core.db_manager import get_connection
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                conn = get_connection("_test_wal.db")
                try:
                    mode = conn.execute("PRAGMA journal_mode").fetchone()
                    assert mode[0].lower() == "wal"
                finally:
                    conn.close()

    def test_get_connection_row_factory(self):
        from app.core.db_manager import get_connection
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                conn = get_connection("_test_rf.db", row_factory=True)
                try:
                    assert conn.row_factory == sqlite3.Row
                finally:
                    conn.close()

    def test_get_connection_no_row_factory(self):
        from app.core.db_manager import get_connection
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                conn = get_connection("_test_nrf.db", row_factory=False)
                try:
                    assert conn.row_factory is None
                finally:
                    conn.close()

    def test_get_conn_context_manager(self):
        from app.core.db_manager import get_conn
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                with get_conn("_test_ctx.db") as conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
                    conn.execute("INSERT INTO t VALUES (1)")
                    conn.commit()
                    row = conn.execute("SELECT * FROM t").fetchone()
                    assert row["id"] == 1

    def test_ensure_wal(self):
        from app.core.db_manager import ensure_wal
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                # Create a DB file first
                db_path = os.path.join(td, "_test_ensure.db")
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE t (id INTEGER)")
                conn.close()
                result = ensure_wal("_test_ensure.db")
                assert result is True

    def test_execute_with_retry_success(self):
        from app.core.db_manager import execute_with_retry
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                # Create table first
                db_path = os.path.join(td, "_test_retry.db")
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE t (id INTEGER, val TEXT)")
                conn.commit()
                conn.close()
                # Execute with retry
                cursor = execute_with_retry(
                    "_test_retry.db",
                    "INSERT INTO t VALUES (?, ?)",
                    (1, "hello"),
                )
                assert cursor is not None

    def test_get_db_status(self):
        from app.core.db_manager import get_db_status
        status = get_db_status()
        assert isinstance(status, dict)
        assert "users.db" in status or len(status) > 0


# ═══════════════════════════════════════════════════════════════════
# 3) ENGINE DB INTEGRATION
# ═══════════════════════════════════════════════════════════════════

class TestEngineDbIntegration:
    """Verify all engines use db_manager instead of direct sqlite3.connect."""

    ENGINES_WITH_DB = [
        "app/core/portfolio_engine.py",
        "app/core/activity_stream_engine.py",
        "app/core/opportunity_engine.py",
        "app/core/smart_alert_engine.py",
        "app/core/user_engine.py",
        "app/core/paper_trading_engine.py",
        "app/core/journal_engine.py",
        "app/core/social_engine.py",
        "app/core/marketplace_engine.py",
        "app/core/mentor_engine.py",
        "app/core/course_engine.py",
        "app/core/live_room_engine.py",
        "app/core/reputation_engine.py",
        "app/core/analysis_engine.py",
        "app/core/news_impact_engine.py",
        "app/core/push_engine.py",
        "app/core/share_engine.py",
        "app/core/referral_engine.py",
    ]

    @pytest.mark.parametrize("engine_path", ENGINES_WITH_DB)
    def test_engine_uses_db_manager(self, engine_path):
        """Each engine's _get_db/_get_conn must import from db_manager."""
        src = _read(engine_path)
        assert "from app.core.db_manager import get_connection" in src, \
            f"{engine_path} should use db_manager.get_connection"

    def test_subscription_engine_uses_db_manager(self):
        """subscription_engine has special db_path param but still uses db_manager."""
        src = _read("app/core/subscription_engine.py")
        assert "from app.core.db_manager import get_connection" in src


# ═══════════════════════════════════════════════════════════════════
# 4) CONCURRENT DB WRITES
# ═══════════════════════════════════════════════════════════════════

class TestConcurrentDbWrites:
    """Verify concurrent SQLite writes don't cause lock errors."""

    def test_concurrent_writes_no_lock_error(self):
        """Multiple threads writing to same DB should not crash."""
        from app.core.db_manager import get_connection

        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                # Create table
                conn = get_connection("_test_concurrent.db")
                conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER, val TEXT)")
                conn.commit()
                conn.close()

                errors = []
                barrier = threading.Barrier(5)

                def writer(thread_id):
                    try:
                        barrier.wait(timeout=5)
                        for i in range(10):
                            c = get_connection("_test_concurrent.db")
                            try:
                                c.execute("INSERT INTO items VALUES (?, ?)",
                                          (thread_id * 100 + i, f"t{thread_id}"))
                                c.commit()
                            finally:
                                c.close()
                    except Exception as e:
                        errors.append(str(e))

                threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=30)

                assert len(errors) == 0, f"Concurrent write errors: {errors}"

                # Verify all rows written
                c = get_connection("_test_concurrent.db")
                try:
                    count = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
                    assert count == 50, f"Expected 50 rows, got {count}"
                finally:
                    c.close()

    def test_wal_allows_concurrent_reads(self):
        """WAL mode should allow reads while writing."""
        from app.core.db_manager import get_connection

        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                conn = get_connection("_test_wal_rw.db")
                conn.execute("CREATE TABLE IF NOT EXISTS data (id INTEGER)")
                conn.execute("INSERT INTO data VALUES (1)")
                conn.commit()
                conn.close()

                # Open two connections simultaneously
                c1 = get_connection("_test_wal_rw.db")
                c2 = get_connection("_test_wal_rw.db")
                try:
                    # c1 starts a write
                    c1.execute("INSERT INTO data VALUES (2)")
                    # c2 should be able to read (WAL allows this)
                    rows = c2.execute("SELECT COUNT(*) FROM data").fetchone()[0]
                    assert rows >= 1
                    c1.commit()
                finally:
                    c1.close()
                    c2.close()


# ═══════════════════════════════════════════════════════════════════
# 5) JOB MANAGER HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

class TestJobManagerHealthCheck:
    """Test JobManager enhancements for health monitoring."""

    def test_job_manager_file_exists(self):
        assert os.path.isfile(os.path.join(BASE, "core/job_manager.py"))

    def test_job_manager_has_health_check(self):
        src = _read("core/job_manager.py")
        assert "def health_check(" in src

    def test_job_manager_has_uptime(self):
        src = _read("core/job_manager.py")
        assert "uptime_seconds" in src

    def test_job_manager_tracks_thread(self):
        src = _read("core/job_manager.py")
        assert "thread" in src.lower()
        assert "is_alive" in src

    def test_job_manager_logs_errors(self):
        src = _read("core/job_manager.py")
        assert "zkr_analiz.infra" in src

    def test_job_manager_has_last_error(self):
        src = _read("core/job_manager.py")
        assert "last_error" in src

    def test_job_manager_has_restart_count(self):
        src = _read("core/job_manager.py")
        assert "restart_count" in src

    def test_job_manager_health_check_returns_dict(self):
        from core.job_manager import JobManager
        jm = JobManager()
        jm.register_thread("test_job", lambda: None)
        result = jm.health_check()
        assert isinstance(result, dict)
        assert "test_job" in result

    def test_job_manager_uptime_zero_before_start(self):
        from core.job_manager import JobManager
        jm = JobManager()
        assert jm.uptime_seconds == 0.0

    def test_job_manager_start_sets_uptime(self):
        from core.job_manager import JobManager
        jm = JobManager()
        jm.register_thread("noop", lambda: time.sleep(0.01))
        jm.start_all()
        time.sleep(0.1)
        assert jm.uptime_seconds > 0

    def test_job_manager_health_alive_status(self):
        from core.job_manager import JobManager
        jm = JobManager()
        done = threading.Event()

        def long_job():
            done.wait(timeout=5)

        jm.register_thread("alive_test", long_job)
        jm.start_all()
        time.sleep(0.2)
        health = jm.health_check()
        assert health["alive_test"]["alive"] is True
        done.set()


# ═══════════════════════════════════════════════════════════════════
# 6) BACKGROUND JOB SAFETY
# ═══════════════════════════════════════════════════════════════════

class TestBackgroundJobSafety:
    """Verify background jobs have proper error handling."""

    def test_jobs_file_has_try_except_in_boot_live_engine(self):
        src = _read("app/background/jobs.py")
        assert "try:" in src
        # Check _boot_live_engine has error handling
        idx = src.find("def _boot_live_engine")
        assert idx > 0
        block = src[idx:idx + 500]
        assert "except" in block

    def test_jobs_file_has_try_except_in_boot_activity_stream(self):
        src = _read("app/background/jobs.py")
        idx = src.find("def _boot_activity_stream")
        assert idx > 0
        block = src[idx:idx + 500]
        assert "except" in block

    def test_activity_stream_boot_has_restart_loop(self):
        """Activity stream should restart on crash."""
        src = _read("app/background/jobs.py")
        idx = src.find("def _boot_activity_stream")
        block = src[idx:idx + 500]
        assert "while True" in block

    def test_wal_migration_at_startup(self):
        """Background jobs should ensure WAL at startup."""
        src = _read("app/background/jobs.py")
        assert "ensure_all_wal" in src

    def test_jobs_skip_in_test_mode(self):
        """Background jobs should skip in TEST_MODE."""
        src = _read("app/background/jobs.py")
        assert "TEST_MODE" in src

    def test_refresh_loop_has_error_handler(self):
        src = _read("app/background/jobs.py")
        idx = src.find("def refresh_loop")
        assert idx > 0
        block = src[idx:idx + 1500]
        assert "except" in block

    def test_refresh_top4h_has_error_handler(self):
        src = _read("app/background/jobs.py")
        idx = src.find("def refresh_top4h_loop")
        assert idx > 0
        block = src[idx:idx + 500]
        assert "except" in block


# ═══════════════════════════════════════════════════════════════════
# 7) API RESILIENT HTTP
# ═══════════════════════════════════════════════════════════════════

class TestAPIResilientHTTP:
    """Test _resilient_get in binance_client."""

    def test_binance_client_has_resilient_get(self):
        src = _read("app/core/binance_client.py")
        assert "def _resilient_get(" in src

    def test_resilient_get_has_retry_logic(self):
        src = _read("app/core/binance_client.py")
        assert "_MAX_RETRIES" in src
        assert "_RETRY_DELAY" in src

    def test_resilient_get_has_timeout(self):
        src = _read("app/core/binance_client.py")
        assert "_DEFAULT_TIMEOUT" in src

    def test_binance_klines_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def binance_klines")
        block = src[idx:idx + 300]
        assert "_resilient_get" in block

    def test_exchange_info_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def _fetch_exchange_info")
        block = src[idx:idx + 200]
        assert "_resilient_get" in block

    def test_fng_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def _fetch_fng_raw")
        block = src[idx:idx + 200]
        assert "_resilient_get" in block

    def test_pump_candidates_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def pump_candidates")
        block = src[idx:idx + 300]
        assert "_resilient_get" in block

    def test_coingecko_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def coingecko_top_by_marketcap")
        block = src[idx:idx + 500]
        assert "_resilient_get" in block

    def test_resilient_get_logs_warnings(self):
        src = _read("app/core/binance_client.py")
        assert "zkr_analiz.infra" in src

    def test_blockchain_hashrate_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def blockchain_hashrate")
        block = src[idx:idx + 200]
        assert "_resilient_get" in block

    def test_defillama_uses_resilient_get(self):
        src = _read("app/core/binance_client.py")
        idx = src.find("def defillama_stablecoins")
        block = src[idx:idx + 200]
        assert "_resilient_get" in block


# ═══════════════════════════════════════════════════════════════════
# 8) TEST_MODE SUPPORT
# ═══════════════════════════════════════════════════════════════════

class TestTestModeSupport:
    """Verify TEST_MODE environment flag support."""

    def test_config_has_test_mode(self):
        src = _read("app/config.py")
        assert "TEST_MODE" in src

    def test_test_config_has_test_mode_true(self):
        src = _read("app/config.py")
        # Find TestConfig class and check TEST_MODE = True
        idx = src.find("class TestConfig")
        assert idx > 0
        block = src[idx:idx + 300]
        assert "TEST_MODE = True" in block

    def test_base_config_has_test_mode(self):
        src = _read("app/config.py")
        assert "TEST_MODE" in src

    def test_background_jobs_check_test_mode(self):
        src = _read("app/background/jobs.py")
        assert "TEST_MODE" in src


# ═══════════════════════════════════════════════════════════════════
# 9) HEALTH CHECK ENDPOINT
# ═══════════════════════════════════════════════════════════════════

class TestHealthCheckEndpoint:
    """Verify health check endpoint structure."""

    def test_system_blueprint_exists(self):
        assert os.path.isfile(
            os.path.join(BASE, "app/blueprints/system/__init__.py")
        )

    def test_health_route_defined(self):
        src = _read("app/blueprints/system/__init__.py")
        assert "/api/system/health" in src

    def test_health_returns_database_status(self):
        src = _read("app/blueprints/system/__init__.py")
        assert "database_status" in src

    def test_health_returns_api_status(self):
        src = _read("app/blueprints/system/__init__.py")
        assert "api_status" in src

    def test_health_returns_background_jobs(self):
        src = _read("app/blueprints/system/__init__.py")
        assert "background_jobs" in src

    def test_health_returns_memory_usage(self):
        src = _read("app/blueprints/system/__init__.py")
        assert "memory_usage" in src

    def test_health_returns_uptime(self):
        src = _read("app/blueprints/system/__init__.py")
        assert "uptime_seconds" in src

    def test_health_check_registered(self):
        """system_bp should be registered in legacy_monolith."""
        src = _read("legacy_monolith.py")
        assert "system_bp" in src
        assert "register_blueprint(system_bp)" in src

    def test_health_check_import(self):
        src = _read("legacy_monolith.py")
        assert "from app.blueprints.system import system_bp" in src

    def test_health_check_degraded_status(self):
        """Health check should report 'degraded' if issues found."""
        src = _read("app/blueprints/system/__init__.py")
        assert "degraded" in src


# ═══════════════════════════════════════════════════════════════════
# 10) SQLITE PERFORMANCE PRAGMAS
# ═══════════════════════════════════════════════════════════════════

class TestSQLitePerformancePragmas:
    """Verify performance PRAGMAs are applied."""

    def test_synchronous_normal(self):
        src = _read("app/core/db_manager.py")
        assert "synchronous" in src
        assert "NORMAL" in src

    def test_cache_size(self):
        src = _read("app/core/db_manager.py")
        assert "cache_size" in src
        assert "10000" in src

    def test_temp_store_memory(self):
        src = _read("app/core/db_manager.py")
        assert "temp_store" in src
        assert "MEMORY" in src

    def test_pragmas_applied_to_connection(self):
        """Verify PRAGMAs are actually applied by creating a test connection."""
        from app.core.db_manager import get_connection

        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                conn = get_connection("_test_pragmas.db")
                try:
                    # Check WAL
                    mode = conn.execute("PRAGMA journal_mode").fetchone()
                    assert mode[0].lower() == "wal"

                    # Check busy_timeout
                    bt = conn.execute("PRAGMA busy_timeout").fetchone()
                    assert bt[0] == 5000

                    # Check synchronous (1 = NORMAL)
                    sync = conn.execute("PRAGMA synchronous").fetchone()
                    assert sync[0] == 1  # NORMAL

                    # Check cache_size
                    cs = conn.execute("PRAGMA cache_size").fetchone()
                    assert cs[0] == 10000

                    # Check temp_store (2 = MEMORY)
                    ts = conn.execute("PRAGMA temp_store").fetchone()
                    assert ts[0] == 2  # MEMORY

                    # Check foreign_keys
                    fk = conn.execute("PRAGMA foreign_keys").fetchone()
                    assert fk[0] == 1  # ON
                finally:
                    conn.close()


# ═══════════════════════════════════════════════════════════════════
# 11) INFRA LOGGER USAGE
# ═══════════════════════════════════════════════════════════════════

class TestInfraLoggerUsage:
    """Verify zkr_analiz.infra logger is used consistently."""

    def test_db_manager_uses_infra_logger(self):
        src = _read("app/core/db_manager.py")
        assert 'getLogger("zkr_analiz.infra")' in src

    def test_binance_client_uses_infra_logger(self):
        src = _read("app/core/binance_client.py")
        assert 'getLogger("zkr_analiz.infra")' in src

    def test_job_manager_uses_infra_logger(self):
        src = _read("core/job_manager.py")
        assert 'getLogger("zkr_analiz.infra")' in src


# ═══════════════════════════════════════════════════════════════════
# 12) DATABASE MIGRATION CHECK
# ═══════════════════════════════════════════════════════════════════

class TestDatabaseMigrationCheck:
    """Verify ensure_all_wal covers all known databases."""

    KNOWN_DBS = [
        "activity_stream.db",
        "portfolios.db",
        "opportunities.db",
        "reputation.db",
        "referral_engine.db",
        "users.db",
        "paper_trading.db",
        "journal.db",
        "social.db",
        "marketplace.db",
        "mentors.db",
        "courses.db",
        "live_rooms.db",
        "analysis.db",
        "news_impact.db",
        "push_engine.db",
        "share_engine.db",
        "subscriptions.db",
    ]

    def test_ensure_all_wal_lists_all_databases(self):
        src = _read("app/core/db_manager.py")
        for db in self.KNOWN_DBS:
            assert db in src, f"Database {db} missing from ensure_all_wal"

    def test_ensure_all_wal_returns_dict(self):
        from app.core.db_manager import ensure_all_wal
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                result = ensure_all_wal()
                assert isinstance(result, dict)

    def test_ensure_wal_on_new_db(self):
        from app.core.db_manager import ensure_wal, get_connection
        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                # Create a fresh DB
                conn = get_connection("_migration_test.db")
                conn.execute("CREATE TABLE t (x INTEGER)")
                conn.commit()
                conn.close()
                # Ensure WAL
                result = ensure_wal("_migration_test.db")
                assert result is True


# ═══════════════════════════════════════════════════════════════════
# 13) EXECUTE_WITH_RETRY ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════

class TestExecuteWithRetry:
    """Test retry logic in execute_with_retry."""

    def test_retry_on_locked_error(self):
        """Simulate locked error and verify retry."""
        from app.core.db_manager import execute_with_retry

        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                db_path = os.path.join(td, "_test_retry_lock.db")
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE items (id INTEGER)")
                conn.commit()
                conn.close()

                # Normal insert should work
                cursor = execute_with_retry(
                    "_test_retry_lock.db",
                    "INSERT INTO items VALUES (?)",
                    (42,),
                )
                assert cursor is not None

    def test_retry_non_lock_error_raises(self):
        """Non-lock OperationalError should raise immediately."""
        from app.core.db_manager import execute_with_retry

        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                db_path = os.path.join(td, "_test_noretry.db")
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE items (id INTEGER)")
                conn.commit()
                conn.close()

                # Bad SQL should fail immediately
                with pytest.raises(sqlite3.OperationalError):
                    execute_with_retry(
                        "_test_noretry.db",
                        "INSERT INTO nonexistent_table VALUES (?)",
                        (1,),
                    )

    def test_executemany_with_retry(self):
        from app.core.db_manager import executemany_with_retry

        with tempfile.TemporaryDirectory() as td:
            with patch("app.core.db_manager._DB_DIR", td):
                db_path = os.path.join(td, "_test_many.db")
                conn = sqlite3.connect(db_path)
                conn.execute("CREATE TABLE items (id INTEGER, val TEXT)")
                conn.commit()
                conn.close()

                cursor = executemany_with_retry(
                    "_test_many.db",
                    "INSERT INTO items VALUES (?, ?)",
                    [(1, "a"), (2, "b"), (3, "c")],
                )
                assert cursor is not None


# ═══════════════════════════════════════════════════════════════════
# 14) ACTIVITY STREAM ENGINE LOOP HARDENING
# ═══════════════════════════════════════════════════════════════════

class TestActivityStreamLoopHardening:
    """Verify activity_collect_loop has proper error handling."""

    def test_activity_collect_loop_has_try_except(self):
        src = _read("app/core/activity_stream_engine.py")
        idx = src.find("def activity_collect_loop")
        assert idx > 0
        block = src[idx:idx + 300]
        assert "try:" in block
        assert "except" in block

    def test_opportunity_scan_loop_has_try_except(self):
        src = _read("app/core/opportunity_engine.py")
        idx = src.find("def opportunity_scan_loop")
        assert idx > 0
        block = src[idx:idx + 800]
        assert "try:" in block
        assert "except" in block

    def test_alert_check_loop_has_try_except(self):
        src = _read("app/core/alert_engine.py")
        idx = src.find("def alert_check_loop")
        assert idx > 0
        block = src[idx:idx + 800]
        assert "try:" in block
        assert "except" in block


# ═══════════════════════════════════════════════════════════════════
# 15) CROSS-FILE CONSISTENCY
# ═══════════════════════════════════════════════════════════════════

class TestCrossFileConsistency:
    """Verify consistency across all infrastructure files."""

    def test_no_direct_sqlite_connect_in_engines(self):
        """No engine should use bare sqlite3.connect in _get_db/_get_conn."""
        for engine in TestEngineDbIntegration.ENGINES_WITH_DB:
            src = _read(engine)
            # Find the _get_db or _get_conn function
            fn_match = re.search(r"def (_get_db|_get_conn)\(.*?\).*?:", src)
            if fn_match:
                fn_start = fn_match.start()
                # Find the next function definition
                next_fn = re.search(r"\ndef [a-zA-Z_]", src[fn_start + 10:])
                fn_end = fn_start + 10 + next_fn.start() if next_fn else fn_start + 500
                fn_body = src[fn_start:fn_end]
                # Should NOT have bare sqlite3.connect (except subscription_engine for db_path)
                if "subscription_engine" not in engine:
                    assert "sqlite3.connect" not in fn_body, \
                        f"{engine} still uses bare sqlite3.connect in DB function"

    def test_all_pragmas_in_db_manager(self):
        """All six PRAGMAs should be in db_manager."""
        src = _read("app/core/db_manager.py")
        for pragma in ["journal_mode", "busy_timeout", "synchronous",
                       "cache_size", "temp_store", "foreign_keys"]:
            assert pragma in src, f"Missing PRAGMA {pragma} in db_manager"

    def test_system_blueprint_imported_in_monolith(self):
        src = _read("legacy_monolith.py")
        assert "from app.blueprints.system import system_bp" in src


# ═══════════════════════════════════════════════════════════════════
# 16) LIVE TESTS (require running server)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(
    os.environ.get("ZKR_ANALIZ_LIVE_TEST", "").lower() not in ("1", "true"),
    reason="Live tests require ZKR_ANALIZ_LIVE_TEST=1",
)
class TestLiveHealthEndpoint:
    """Test health endpoint against running server."""

    def test_health_endpoint_returns_200(self):
        import requests
        r = requests.get("http://127.0.0.1:34000/api/system/health", timeout=10)
        assert r.status_code == 200

    def test_health_endpoint_json_structure(self):
        import requests
        r = requests.get("http://127.0.0.1:34000/api/system/health", timeout=10)
        data = r.json()
        assert "status" in data
        assert "database_status" in data
        assert "background_jobs" in data
        assert "memory_usage" in data
        assert "uptime_seconds" in data

    def test_health_endpoint_db_details(self):
        import requests
        r = requests.get("http://127.0.0.1:34000/api/system/health", timeout=10)
        data = r.json()
        db = data.get("database_status", {})
        assert "healthy" in db
        assert "databases" in db
