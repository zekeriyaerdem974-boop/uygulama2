# -*- coding: utf-8 -*-
"""Growth & Referral Engine — FAZ 44.

Invite code generation, referral tracking, reward calculation,
fraud detection. SQLite-backed, thread-safe.

Public API:
  generate_invite_code(user_id)          → str (6-char code)
  register_referral(invite_code, new_uid) → dict | None
  get_referral_stats(user_id)            → dict
  calculate_referral_rewards(user_id)    → list[dict]
  get_invite_code(user_id)               → str | None
  get_top_inviters(limit)                → list[dict]
  get_recent_referrals(limit)            → list[dict]
  validate_invite_code(code)             → dict | None
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.referral_engine")

# ── Database ──────────────────────────────────────────────────────
_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
_DB_PATH = os.path.join(_DB_DIR, "referral_engine.db")
_lock = threading.Lock()

# ── Constants ─────────────────────────────────────────────────────
CODE_LENGTH = 6
CODE_PREFIX = "BW"
MAX_CODES_PER_USER = 3

# Reward tiers: (min_referrals, reward_type, reward_value, description)
REWARD_TIERS = [
    (1, "pro_trial", 3, "3 days Pro trial"),
    (3, "copilot_credits", 10, "10 Copilot credits"),
    (5, "copilot_credits", 25, "25 Copilot credits"),
    (10, "badge", 1, "Elite Inviter badge"),
    (25, "portfolio_credits", 50, "50 Portfolio AI credits"),
    (50, "badge", 1, "Growth Champion badge"),
]

# ── Compliance ────────────────────────────────────────────────────
BANNED_WORDS = {"BUY", "SELL", "ENTRY", "EXIT", "TAKE PROFIT", "STOP LOSS", "TRADE NOW"}


def _sanitize_text(text: str) -> str:
    if not text:
        return ""
    result = text
    for word in BANNED_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub("***", result)
    return result.strip()


# ── Database Setup ───────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    conn = get_connection("referral_engine.db", row_factory=False)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            code       TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_user_id  TEXT NOT NULL,
            referred_user_id  TEXT NOT NULL UNIQUE,
            invite_code       TEXT NOT NULL,
            created_at        TEXT DEFAULT (datetime('now')),
            ip_hash           TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL,
            reward_type  TEXT NOT NULL,
            reward_value INTEGER DEFAULT 0,
            description  TEXT DEFAULT '',
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_invite_user ON invite_codes(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_referral_referrer ON referrals(referrer_user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reward_user ON referral_rewards(user_id)")
    conn.commit()
    return conn


# ── Invite Code Generation ───────────────────────────────────────

def _generate_code(user_id: str) -> str:
    """Generate a deterministic-ish unique invite code."""
    seed = f"{user_id}_{time.time()}_{os.urandom(4).hex()}"
    h = hashlib.sha256(seed.encode()).hexdigest().upper()
    # Take CODE_LENGTH chars, prefix with BW
    raw = h[:CODE_LENGTH]
    return f"{CODE_PREFIX}{raw}"


def generate_invite_code(user_id: str) -> str:
    """Generate a new invite code for user. Returns code string."""
    if not user_id:
        return ""
    user_id = str(user_id).strip()
    with _lock:
        try:
            conn = _get_db()
            # Check existing codes
            existing = conn.execute(
                "SELECT COUNT(*) FROM invite_codes WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            if existing >= MAX_CODES_PER_USER:
                # Return the first existing code
                row = conn.execute(
                    "SELECT code FROM invite_codes WHERE user_id = ? ORDER BY id ASC LIMIT 1",
                    (user_id,),
                ).fetchone()
                conn.close()
                return row[0] if row else ""

            # Generate unique code
            for _ in range(10):
                code = _generate_code(user_id)
                try:
                    conn.execute(
                        "INSERT INTO invite_codes (user_id, code) VALUES (?, ?)",
                        (user_id, code),
                    )
                    conn.commit()
                    conn.close()
                    return code
                except sqlite3.IntegrityError:
                    continue
            conn.close()
            return ""
        except Exception as e:
            _logger.error("generate_invite_code error: %s", e)
            return ""


def get_invite_code(user_id: str) -> Optional[str]:
    """Get existing invite code for user, or generate one."""
    if not user_id:
        return None
    user_id = str(user_id).strip()
    with _lock:
        try:
            conn = _get_db()
            row = conn.execute(
                "SELECT code FROM invite_codes WHERE user_id = ? ORDER BY id ASC LIMIT 1",
                (user_id,),
            ).fetchone()
            conn.close()
            if row:
                return row[0]
        except Exception:
            pass
    # No code exists, generate one
    code = generate_invite_code(user_id)
    return code if code else None


def validate_invite_code(code: str) -> Optional[Dict]:
    """Check if invite code is valid. Returns info dict or None."""
    if not code:
        return None
    code = str(code).strip().upper()
    with _lock:
        try:
            conn = _get_db()
            row = conn.execute(
                "SELECT id, user_id, code, created_at FROM invite_codes WHERE code = ?",
                (code,),
            ).fetchone()
            conn.close()
            if not row:
                return None
            return {
                "id": row[0],
                "user_id": row[1],
                "code": row[2],
                "created_at": row[3],
            }
        except Exception:
            return None


# ── Referral Registration ────────────────────────────────────────

def register_referral(
    invite_code: str,
    new_user_id: str,
    ip_address: str = "",
) -> Optional[Dict]:
    """Register a referral. Returns referral dict or None on failure."""
    if not invite_code or not new_user_id:
        return None

    invite_code = str(invite_code).strip().upper()
    new_user_id = str(new_user_id).strip()

    # Hash IP for privacy
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16] if ip_address else ""

    with _lock:
        try:
            conn = _get_db()

            # Validate code
            code_row = conn.execute(
                "SELECT user_id FROM invite_codes WHERE code = ?", (invite_code,)
            ).fetchone()
            if not code_row:
                conn.close()
                return None

            referrer_id = code_row[0]

            # Fraud detection: self-referral
            if referrer_id == new_user_id:
                _logger.warning("Self-referral attempt: %s", new_user_id)
                conn.close()
                return None

            # Fraud detection: duplicate referred user
            dup = conn.execute(
                "SELECT id FROM referrals WHERE referred_user_id = ?", (new_user_id,)
            ).fetchone()
            if dup:
                conn.close()
                return None

            # Fraud detection: IP duplicate (same IP registering multiple times)
            if ip_hash:
                ip_count = conn.execute(
                    "SELECT COUNT(*) FROM referrals WHERE ip_hash = ? AND referrer_user_id = ?",
                    (ip_hash, referrer_id),
                ).fetchone()[0]
                if ip_count >= 5:
                    _logger.warning("IP fraud suspected: %s referrals from same IP for user %s", ip_count, referrer_id)
                    conn.close()
                    return None

            conn.execute(
                "INSERT INTO referrals (referrer_user_id, referred_user_id, invite_code, ip_hash) VALUES (?, ?, ?, ?)",
                (referrer_id, new_user_id, invite_code, ip_hash),
            )
            conn.commit()

            # Check if new rewards should be granted
            _check_and_grant_rewards(conn, referrer_id)

            conn.commit()
            conn.close()

            # Push activity event
            _push_referral_activity(referrer_id, new_user_id)

            return {
                "referrer_id": referrer_id,
                "referred_id": new_user_id,
                "invite_code": invite_code,
            }
        except Exception as e:
            _logger.error("register_referral error: %s", e)
            return None


# ── Rewards ──────────────────────────────────────────────────────

def _check_and_grant_rewards(conn: sqlite3.Connection, user_id: str):
    """Check if user hit any reward tier and grant if not already given."""
    total = conn.execute(
        "SELECT COUNT(*) FROM referrals WHERE referrer_user_id = ?", (user_id,)
    ).fetchone()[0]

    existing_rewards = set()
    for row in conn.execute(
        "SELECT reward_type, description FROM referral_rewards WHERE user_id = ?",
        (user_id,),
    ).fetchall():
        existing_rewards.add(f"{row[0]}_{row[1]}")

    for min_refs, rtype, rvalue, desc in REWARD_TIERS:
        key = f"{rtype}_{desc}"
        if total >= min_refs and key not in existing_rewards:
            conn.execute(
                "INSERT INTO referral_rewards (user_id, reward_type, reward_value, description) VALUES (?, ?, ?, ?)",
                (user_id, rtype, rvalue, desc),
            )


def calculate_referral_rewards(user_id: str) -> List[Dict]:
    """Get all rewards earned by user."""
    if not user_id:
        return []
    with _lock:
        try:
            conn = _get_db()
            rows = conn.execute(
                "SELECT id, reward_type, reward_value, description, created_at FROM referral_rewards WHERE user_id = ? ORDER BY id",
                (str(user_id),),
            ).fetchall()
            conn.close()
            return [
                {"id": r[0], "reward_type": r[1], "reward_value": r[2], "description": r[3], "created_at": r[4]}
                for r in rows
            ]
        except Exception:
            return []


# ── Stats ────────────────────────────────────────────────────────

def get_referral_stats(user_id: str) -> Dict:
    """Get referral statistics for a user."""
    if not user_id:
        return {"referrals": 0, "successful_invites": 0, "rewards": 0, "invite_code": ""}
    user_id = str(user_id).strip()
    with _lock:
        try:
            conn = _get_db()
            total = conn.execute(
                "SELECT COUNT(*) FROM referrals WHERE referrer_user_id = ?", (user_id,)
            ).fetchone()[0]

            rewards_count = conn.execute(
                "SELECT COUNT(*) FROM referral_rewards WHERE user_id = ?", (user_id,)
            ).fetchone()[0]

            code_row = conn.execute(
                "SELECT code FROM invite_codes WHERE user_id = ? ORDER BY id ASC LIMIT 1",
                (user_id,),
            ).fetchone()

            conn.close()
            return {
                "referrals": total,
                "successful_invites": total,
                "rewards": rewards_count,
                "invite_code": code_row[0] if code_row else "",
            }
        except Exception:
            return {"referrals": 0, "successful_invites": 0, "rewards": 0, "invite_code": ""}


def get_top_inviters(limit: int = 10) -> List[Dict]:
    """Get top inviters for leaderboard."""
    limit = min(int(limit), 50)
    with _lock:
        try:
            conn = _get_db()
            rows = conn.execute(
                """SELECT referrer_user_id, COUNT(*) as cnt,
                          (SELECT COUNT(*) FROM referral_rewards WHERE user_id = referrer_user_id) as reward_cnt
                   FROM referrals
                   GROUP BY referrer_user_id
                   ORDER BY cnt DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            conn.close()
            result = []
            for i, r in enumerate(rows):
                result.append({
                    "rank": i + 1,
                    "user_id": r[0],
                    "username": f"User_{r[0][:8]}" if r[0] else "Anonymous",
                    "referrals": r[1],
                    "rewards": r[2],
                })
            return result
        except Exception:
            return []


def get_recent_referrals(limit: int = 10) -> List[Dict]:
    """Get most recent referral registrations."""
    limit = min(int(limit), 50)
    with _lock:
        try:
            conn = _get_db()
            rows = conn.execute(
                "SELECT id, referrer_user_id, referred_user_id, invite_code, created_at FROM referrals ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            return [
                {
                    "id": r[0],
                    "referrer": f"User_{r[1][:8]}" if r[1] else "",
                    "referred": f"User_{r[2][:8]}" if r[2] else "",
                    "code": r[3],
                    "created_at": r[4],
                }
                for r in rows
            ]
        except Exception:
            return []


def get_growth_stats() -> Dict:
    """Get overall platform growth stats."""
    with _lock:
        try:
            conn = _get_db()
            total_referrals = conn.execute("SELECT COUNT(*) FROM referrals").fetchone()[0]
            total_codes = conn.execute("SELECT COUNT(*) FROM invite_codes").fetchone()[0]
            total_rewards = conn.execute("SELECT COUNT(*) FROM referral_rewards").fetchone()[0]
            conn.close()
            return {
                "total_referrals": total_referrals,
                "total_codes": total_codes,
                "total_rewards": total_rewards,
            }
        except Exception:
            return {"total_referrals": 0, "total_codes": 0, "total_rewards": 0}


# ── Activity Stream Integration ──────────────────────────────────

def _push_referral_activity(referrer_id: str, referred_id: str):
    """Push referral event to activity stream."""
    try:
        from app.core.activity_stream_engine import push_event

        push_event({
            "event_type": "social_trending",
            "title": _sanitize_text("New community member joined via referral"),
            "symbol": "",
            "market": "platform",
            "severity": "low",
            "confidence": 80,
            "source": "referral_engine",
            "metadata": {"referrer": referrer_id, "type": "referral_join"},
        })
    except Exception:
        pass
