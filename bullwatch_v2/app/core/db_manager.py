# -*- coding: utf-8 -*-
"""Centralized Database Connection Manager — FAZ 48.

Thread-safe SQLite connection management with:
  - WAL mode for concurrent read/write
  - busy_timeout for lock contention
  - Performance PRAGMAs (synchronous=NORMAL, cache_size, temp_store)
  - Retry logic on transient write failures
  - Per-thread connection isolation
  - Structured logging via infra_logger

All engine modules should use ``get_connection(db_name)`` instead of
their own ``_get_db()`` / ``_get_conn()`` helpers.

Public API:
  get_connection(db_name, row_factory=True)  → sqlite3.Connection
  execute_with_retry(db_name, sql, params)   → cursor
  ensure_wal(db_path)                        → bool
  close_all()                                → None
  get_db_path(db_name)                       → str
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Optional, Sequence, Tuple

_logger = logging.getLogger("zkr_analiz.infra")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)

# Retry settings
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.1  # seconds, doubles each retry

# SQLite PRAGMAs applied to every connection
_PRAGMAS = [
    ("journal_mode", "WAL"),
    ("busy_timeout", "5000"),
    ("synchronous", "NORMAL"),
    ("cache_size", "10000"),
    ("temp_store", "MEMORY"),
    ("foreign_keys", "ON"),
]

# ── Thread-local storage ─────────────────────────────────────────
_local = threading.local()
_global_lock = threading.Lock()


def get_db_path(db_name: str) -> str:
    """Return the absolute path for a database file name.

    Args:
        db_name: Base filename (e.g. "portfolios.db") or just stem ("portfolios").
    """
    if not db_name.endswith(".db"):
        db_name = f"{db_name}.db"
    return os.path.join(_DB_DIR, db_name)


def get_connection(
    db_name: str,
    *,
    row_factory: bool = True,
) -> sqlite3.Connection:
    """Get a configured SQLite connection.

    Each call returns a NEW connection with WAL mode, busy_timeout,
    and performance PRAGMAs applied. The caller is responsible for
    closing the connection (use try/finally or context manager).

    Args:
        db_name: Database file name (e.g. "portfolios.db").
        row_factory: If True, set ``sqlite3.Row`` as row_factory.

    Returns:
        Configured sqlite3.Connection.
    """
    os.makedirs(_DB_DIR, exist_ok=True)
    db_path = get_db_path(db_name)

    conn = sqlite3.connect(db_path, timeout=15)

    if row_factory:
        conn.row_factory = sqlite3.Row

    # Apply performance and safety PRAGMAs
    for pragma_name, pragma_value in _PRAGMAS:
        try:
            conn.execute(f"PRAGMA {pragma_name}={pragma_value}")
        except sqlite3.Error:
            pass  # Non-critical — some PRAGMAs may not be supported

    return conn


@contextmanager
def get_conn(db_name: str, *, row_factory: bool = True):
    """Context manager that yields a connection and auto-closes it.

    Usage::

        with get_conn("portfolios.db") as conn:
            conn.execute("SELECT ...")
    """
    conn = get_connection(db_name, row_factory=row_factory)
    try:
        yield conn
    finally:
        conn.close()


def execute_with_retry(
    db_name: str,
    sql: str,
    params: Sequence[Any] = (),
    *,
    commit: bool = True,
    row_factory: bool = True,
) -> sqlite3.Cursor:
    """Execute a SQL statement with automatic retry on lock/busy errors.

    Opens a fresh connection, executes the statement, optionally commits,
    and closes. Retries up to MAX_RETRIES times with exponential backoff
    on ``OperationalError`` (database locked / busy).

    Args:
        db_name: Database file name.
        sql: SQL statement to execute.
        params: Parameters for the SQL statement.
        commit: Whether to commit after execution.
        row_factory: Whether to use sqlite3.Row.

    Returns:
        The sqlite3.Cursor from the successful execution.

    Raises:
        sqlite3.OperationalError: If all retries are exhausted.
    """
    last_error: Optional[Exception] = None
    delay = RETRY_BASE_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        conn = None
        try:
            conn = get_connection(db_name, row_factory=row_factory)
            cursor = conn.execute(sql, params)
            if commit:
                conn.commit()
            return cursor
        except sqlite3.OperationalError as e:
            last_error = e
            err_msg = str(e).lower()
            if "locked" in err_msg or "busy" in err_msg:
                _logger.warning(
                    "DB %s locked (attempt %d/%d): %s",
                    db_name, attempt, MAX_RETRIES, e,
                )
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                time.sleep(delay)
                delay *= 2
                continue
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    _logger.error("DB %s: all %d retries exhausted: %s", db_name, MAX_RETRIES, last_error)
    raise last_error  # type: ignore[misc]


def executemany_with_retry(
    db_name: str,
    sql: str,
    params_seq: Sequence[Sequence[Any]],
    *,
    commit: bool = True,
    row_factory: bool = True,
) -> sqlite3.Cursor:
    """Execute a SQL statement with many param sets, with retry logic."""
    last_error: Optional[Exception] = None
    delay = RETRY_BASE_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        conn = None
        try:
            conn = get_connection(db_name, row_factory=row_factory)
            cursor = conn.executemany(sql, params_seq)
            if commit:
                conn.commit()
            return cursor
        except sqlite3.OperationalError as e:
            last_error = e
            err_msg = str(e).lower()
            if "locked" in err_msg or "busy" in err_msg:
                _logger.warning(
                    "DB %s locked on executemany (attempt %d/%d): %s",
                    db_name, attempt, MAX_RETRIES, e,
                )
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                time.sleep(delay)
                delay *= 2
                continue
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    _logger.error("DB %s: executemany retries exhausted: %s", db_name, MAX_RETRIES, last_error)
    raise last_error  # type: ignore[misc]


def ensure_wal(db_name: str) -> bool:
    """Ensure a database is in WAL journal mode.

    Can be called at startup to migrate existing databases.

    Returns:
        True if WAL is now active, False on error.
    """
    try:
        conn = get_connection(db_name, row_factory=False)
        try:
            result = conn.execute("PRAGMA journal_mode").fetchone()
            mode = result[0] if result else "unknown"
            if mode.lower() != "wal":
                conn.execute("PRAGMA journal_mode=WAL")
                _logger.info("DB %s: migrated to WAL mode", db_name)
            return True
        finally:
            conn.close()
    except Exception as e:
        _logger.error("DB %s: WAL migration failed: %s", db_name, e)
        return False


def ensure_all_wal() -> dict:
    """Ensure WAL mode on all known database files.

    Returns:
        Dict mapping db_name → bool (success).
    """
    known_dbs = [
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
    results = {}
    for db in known_dbs:
        db_path = get_db_path(db)
        if os.path.exists(db_path):
            results[db] = ensure_wal(db)
        else:
            results[db] = True  # Does not exist yet, will be WAL on creation
    return results


def get_db_status() -> dict:
    """Get status information for all databases (used by health check).

    Returns:
        Dict with per-database info: exists, size_bytes, wal_mode, table_count.
    """
    status = {}
    known_dbs = [
        "activity_stream.db", "portfolios.db", "opportunities.db",
        "reputation.db", "referral_engine.db", "users.db",
        "paper_trading.db", "journal.db", "social.db",
        "marketplace.db", "mentors.db", "courses.db",
        "live_rooms.db", "analysis.db", "news_impact.db",
        "push_engine.db", "share_engine.db", "subscriptions.db",
    ]
    for db_name in known_dbs:
        db_path = get_db_path(db_name)
        info: dict = {"exists": os.path.exists(db_path)}
        if info["exists"]:
            try:
                info["size_bytes"] = os.path.getsize(db_path)
                conn = sqlite3.connect(db_path, timeout=5)
                try:
                    mode = conn.execute("PRAGMA journal_mode").fetchone()
                    info["wal_mode"] = (mode[0].lower() == "wal") if mode else False
                    tables = conn.execute(
                        "SELECT count(*) FROM sqlite_master WHERE type='table'"
                    ).fetchone()
                    info["table_count"] = tables[0] if tables else 0
                finally:
                    conn.close()
            except Exception as e:
                info["error"] = str(e)
        status[db_name] = info
    return status
