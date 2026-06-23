# -*- coding: utf-8 -*-
"""User / Auth Engine — FAZ 27.

SQLite-backed user management with secure password hashing.

Public API:
  register_user(email, username, password)  → dict
  authenticate(email, password)             → dict | None
  get_user(user_id)                         → dict | None
  get_user_by_email(email)                  → dict | None
  update_user(user_id, fields)              → dict
  save_user_data(user_id, key, data)        → bool
  load_user_data(user_id, key)              → dict | None
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from werkzeug.security import generate_password_hash, check_password_hash

_logger = logging.getLogger("zkr_analiz.user_engine")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ══════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ══════════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    """Get a thread-safe SQLite connection."""
    from app.core.db_manager import get_connection
    return get_connection("users.db")


def _ensure_tables(conn: sqlite3.Connection):
    """Create user tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            username      TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            plan          TEXT NOT NULL DEFAULT 'free',
            is_active     INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_data (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT NOT NULL,
            data_key  TEXT NOT NULL,
            data_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, data_key)
        );

        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_user_data_uid ON user_data(user_id, data_key);
    """)


def _init_db():
    """Initialize database on first use."""
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        conn.commit()
    finally:
        conn.close()


# Auto-initialize on import
_init_db()


def _row_to_dict(row) -> dict:
    """Convert sqlite3.Row to dict, excluding password_hash."""
    if row is None:
        return None
    d = dict(row)
    d.pop("password_hash", None)
    return d


# ══════════════════════════════════════════════════════════════════════
# USER CRUD
# ══════════════════════════════════════════════════════════════════════

def register_user(email: str, username: str, password: str) -> dict:
    """Register a new user. Returns user dict (without password_hash).

    Raises ValueError on validation failure or duplicate email.
    """
    email = (email or "").strip().lower()
    username = (username or "").strip()
    password = (password or "")

    # Validation
    if not email or not _EMAIL_RE.match(email):
        raise ValueError("Geçerli bir e-posta adresi giriniz")
    if not username or len(username) < 2:
        raise ValueError("Kullanıcı adı en az 2 karakter olmalı")
    if len(password) < 6:
        raise ValueError("Şifre en az 6 karakter olmalı")

    user_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = generate_password_hash(password)

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        with _lock:
            # Check duplicate email
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                raise ValueError("Bu e-posta adresi zaten kayıtlı")

            conn.execute(
                """INSERT INTO users (id, email, username, password_hash, created_at, plan, is_active)
                   VALUES (?, ?, ?, ?, ?, 'free', 1)""",
                (user_id, email, username, pw_hash, now),
            )
            conn.commit()

        _logger.info("User registered: %s (%s)", username, email)
        return {
            "id": user_id,
            "email": email,
            "username": username,
            "created_at": now,
            "plan": "free",
            "is_active": True,
        }
    finally:
        conn.close()


def authenticate(email: str, password: str) -> Optional[dict]:
    """Authenticate user by email + password. Returns user dict or None."""
    email = (email or "").strip().lower()
    password = (password or "")

    if not email or not password:
        return None

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email,),
        ).fetchone()
        if row is None:
            return None

        if not check_password_hash(row["password_hash"], password):
            return None

        _logger.info("User authenticated: %s", email)
        return _row_to_dict(row)
    finally:
        conn.close()


def get_user(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    if not user_id:
        return None
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    email = (email or "").strip().lower()
    if not email:
        return None
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def update_user(user_id: str, fields: dict) -> dict:
    """Update user fields (username, plan, is_active)."""
    allowed = {"username", "plan", "is_active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        raise ValueError("No valid fields to update")

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        sets = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [user_id]
        with _lock:
            conn.execute(f"UPDATE users SET {sets} WHERE id = ?", vals)
            conn.commit()
        return get_user(user_id)
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# CLOUD DATA SYNC (key-value store per user)
# ══════════════════════════════════════════════════════════════════════

def save_user_data(user_id: str, key: str, data: dict) -> bool:
    """Save arbitrary JSON data for a user under a key.

    Keys: 'drawings', 'layout', 'watchlist_state', etc.
    """
    import json
    now = datetime.now(timezone.utc).isoformat()
    data_json = json.dumps(data, ensure_ascii=False)

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        with _lock:
            conn.execute(
                """INSERT INTO user_data (user_id, data_key, data_json, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, data_key)
                   DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at""",
                (user_id, key, data_json, now),
            )
            conn.commit()
        return True
    except Exception as e:
        _logger.warning("save_user_data error: %s", e)
        return False
    finally:
        conn.close()


def load_user_data(user_id: str, key: str) -> Optional[dict]:
    """Load JSON data for a user under a key."""
    import json
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT data_json FROM user_data WHERE user_id = ? AND data_key = ?",
            (user_id, key),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["data_json"])
    except Exception as e:
        _logger.warning("load_user_data error: %s", e)
        return None
    finally:
        conn.close()


def delete_user_data(user_id: str, key: str) -> bool:
    """Delete stored data for a user key."""
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        with _lock:
            cur = conn.execute(
                "DELETE FROM user_data WHERE user_id = ? AND data_key = ?",
                (user_id, key),
            )
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()
