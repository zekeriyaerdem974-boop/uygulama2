# -*- coding: utf-8 -*-
"""Subscription / Access-Control Engine — FAZ 36.

Manages subscription plans (Free / Pro / Pro+), user subscriptions,
feature gating, and usage-limit enforcement.

No real payment processing — just plan logic and access control.
Payment providers (iyzico / Stripe) will integrate in a future phase.

Public API:
  get_all_plans()                          → list[dict]
  get_plan(code)                           → dict | None
  get_user_plan(user_id)                   → dict
  get_plan_limits(plan_code)               → dict | None
  set_user_plan(user_id, plan_code, source)→ dict
  can_use_feature(user_id, feature)        → dict
  can_create_alert(user_id)                → dict
  can_activate_strategy(user_id)           → dict
  can_save_strategy(user_id)               → dict
  can_access_premium_course(user_id)       → dict
  can_access_premium_room(user_id)         → dict
  can_access_premium_strategy(user_id)     → dict
  can_use_advanced_screener(user_id)       → dict
  can_use_advanced_backtest(user_id)       → dict
  can_use_advanced_copilot(user_id)        → dict
  enforce_limit(user_id, feature)          → dict
  get_usage(user_id)                       → dict
  increment_copilot_usage(user_id)         → dict
  get_subscription_info(user_id)           → dict
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.subscription_engine")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "subscriptions.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════
# PLAN DEFINITIONS (Static)
# ══════════════════════════════════════════════════════════════════════

PLANS = {
    "free": {
        "name": "Free",
        "code": "free",
        "is_active": True,
        "max_alerts": 5,
        "max_active_strategies": 1,
        "max_saved_strategies": 3,
        "max_live_signals": 1,
        "copilot_daily_limit": 10,
        "can_use_premium_courses": False,
        "can_use_premium_rooms": False,
        "can_use_premium_strategies": False,
        "can_use_advanced_screener": False,
        "can_use_advanced_backtest": False,
        "can_use_advanced_copilot": False,
    },
    "pro": {
        "name": "Pro",
        "code": "pro",
        "is_active": True,
        "max_alerts": 999,
        "max_active_strategies": 10,
        "max_saved_strategies": 20,
        "max_live_signals": 10,
        "copilot_daily_limit": 100,
        "can_use_premium_courses": True,
        "can_use_premium_rooms": True,
        "can_use_premium_strategies": True,
        "can_use_advanced_screener": True,
        "can_use_advanced_backtest": True,
        "can_use_advanced_copilot": True,
    },
    "pro_plus": {
        "name": "Pro+",
        "code": "pro_plus",
        "is_active": True,
        "max_alerts": 999,
        "max_active_strategies": 999,
        "max_saved_strategies": 999,
        "max_live_signals": 999,
        "copilot_daily_limit": 999,
        "can_use_premium_courses": True,
        "can_use_premium_rooms": True,
        "can_use_premium_strategies": True,
        "can_use_advanced_screener": True,
        "can_use_advanced_backtest": True,
        "can_use_advanced_copilot": True,
    },
}

# Feature → plan field mapping
_FEATURE_MAP = {
    "premium_courses": "can_use_premium_courses",
    "premium_rooms": "can_use_premium_rooms",
    "premium_strategies": "can_use_premium_strategies",
    "advanced_screener": "can_use_advanced_screener",
    "advanced_backtest": "can_use_advanced_backtest",
    "advanced_copilot": "can_use_advanced_copilot",
}

# Feature → required plan name (for UI messages)
_FEATURE_REQUIRED_PLAN = {
    "premium_courses": "Pro",
    "premium_rooms": "Pro",
    "premium_strategies": "Pro",
    "advanced_screener": "Pro",
    "advanced_backtest": "Pro",
    "advanced_copilot": "Pro",
}


# ══════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ══════════════════════════════════════════════════════════════════════

def _get_conn(db_path: str = None) -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    if db_path:
        import sqlite3 as _sql
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = _sql.connect(db_path, timeout=15)
        conn.row_factory = _sql.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    return get_connection("subscriptions.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            code        TEXT UNIQUE NOT NULL,
            is_active   INTEGER NOT NULL DEFAULT 1,
            max_alerts  INTEGER NOT NULL DEFAULT 5,
            max_active_strategies INTEGER NOT NULL DEFAULT 1,
            max_saved_strategies  INTEGER NOT NULL DEFAULT 3,
            max_live_signals      INTEGER NOT NULL DEFAULT 1,
            copilot_daily_limit   INTEGER NOT NULL DEFAULT 10,
            can_use_premium_courses    INTEGER NOT NULL DEFAULT 0,
            can_use_premium_rooms      INTEGER NOT NULL DEFAULT 0,
            can_use_premium_strategies INTEGER NOT NULL DEFAULT 0,
            can_use_advanced_screener  INTEGER NOT NULL DEFAULT 0,
            can_use_advanced_backtest  INTEGER NOT NULL DEFAULT 0,
            can_use_advanced_copilot   INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            plan_code   TEXT NOT NULL DEFAULT 'free',
            status      TEXT NOT NULL DEFAULT 'active',
            source      TEXT NOT NULL DEFAULT 'manual',
            start_date  TEXT NOT NULL,
            end_date    TEXT,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS copilot_usage (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            used_date   TEXT NOT NULL,
            count       INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, used_date)
        );

        CREATE INDEX IF NOT EXISTS idx_usub_user
            ON user_subscriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_usub_status
            ON user_subscriptions(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_copilot_usage
            ON copilot_usage(user_id, used_date);
    """)


def _seed_plans(conn: sqlite3.Connection):
    """Insert default plans if they don't exist."""
    now = datetime.now(timezone.utc).isoformat()
    for code, plan in PLANS.items():
        existing = conn.execute(
            "SELECT id FROM subscription_plans WHERE code = ?", (code,)
        ).fetchone()
        if not existing:
            conn.execute(
                """INSERT INTO subscription_plans
                   (id, name, code, is_active,
                    max_alerts, max_active_strategies, max_saved_strategies,
                    max_live_signals, copilot_daily_limit,
                    can_use_premium_courses, can_use_premium_rooms,
                    can_use_premium_strategies, can_use_advanced_screener,
                    can_use_advanced_backtest, can_use_advanced_copilot,
                    created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4())[:12], plan["name"], code,
                    1 if plan["is_active"] else 0,
                    plan["max_alerts"], plan["max_active_strategies"],
                    plan["max_saved_strategies"], plan["max_live_signals"],
                    plan["copilot_daily_limit"],
                    1 if plan["can_use_premium_courses"] else 0,
                    1 if plan["can_use_premium_rooms"] else 0,
                    1 if plan["can_use_premium_strategies"] else 0,
                    1 if plan["can_use_advanced_screener"] else 0,
                    1 if plan["can_use_advanced_backtest"] else 0,
                    1 if plan["can_use_advanced_copilot"] else 0,
                    now, now,
                ),
            )


def _init_db():
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        _seed_plans(conn)
        conn.commit()
    finally:
        conn.close()


_init_db()


# ══════════════════════════════════════════════════════════════════════
# PLAN QUERIES
# ══════════════════════════════════════════════════════════════════════

def get_all_plans() -> List[dict]:
    """Return all active plans."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY max_alerts ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_plan(code: str) -> Optional[dict]:
    """Return plan by code."""
    return PLANS.get(code)


def get_plan_limits(plan_code: str) -> Optional[dict]:
    """Return limit fields for a plan."""
    plan = PLANS.get(plan_code)
    if not plan:
        return None
    return {
        "max_alerts": plan["max_alerts"],
        "max_active_strategies": plan["max_active_strategies"],
        "max_saved_strategies": plan["max_saved_strategies"],
        "max_live_signals": plan["max_live_signals"],
        "copilot_daily_limit": plan["copilot_daily_limit"],
        "can_use_premium_courses": plan["can_use_premium_courses"],
        "can_use_premium_rooms": plan["can_use_premium_rooms"],
        "can_use_premium_strategies": plan["can_use_premium_strategies"],
        "can_use_advanced_screener": plan["can_use_advanced_screener"],
        "can_use_advanced_backtest": plan["can_use_advanced_backtest"],
        "can_use_advanced_copilot": plan["can_use_advanced_copilot"],
    }


# ══════════════════════════════════════════════════════════════════════
# USER SUBSCRIPTION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════

def get_user_plan(user_id: str) -> dict:
    """Get user's active subscription plan.
    Returns plan dict with subscription info.
    Falls back to 'free' if no active subscription found.
    """
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        row = conn.execute(
            """SELECT * FROM user_subscriptions
               WHERE user_id = ? AND status IN ('active', 'trial')
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()

        if row:
            plan_code = row["plan_code"]
            plan = PLANS.get(plan_code, PLANS["free"])
            return {
                "plan_code": plan_code,
                "plan_name": plan["name"],
                "status": row["status"],
                "source": row["source"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "limits": get_plan_limits(plan_code),
            }

        # No active subscription → free plan
        return {
            "plan_code": "free",
            "plan_name": "Free",
            "status": "active",
            "source": "default",
            "start_date": None,
            "end_date": None,
            "limits": get_plan_limits("free"),
        }
    finally:
        conn.close()


def set_user_plan(user_id: str, plan_code: str, source: str = "manual") -> dict:
    """Set/change user's subscription plan.

    Args:
        user_id: User ID
        plan_code: 'free', 'pro', or 'pro_plus'
        source: 'manual', 'admin', 'future_iyzico', 'future_stripe'

    Returns:
        dict with ok, subscription info
    """
    if plan_code not in PLANS:
        return {"ok": False, "error": f"Geçersiz plan: {plan_code}"}

    valid_sources = {"manual", "admin", "iyzico", "future_iyzico", "future_stripe"}
    if source not in valid_sources:
        source = "manual"

    now = datetime.now(timezone.utc).isoformat()
    sub_id = str(uuid.uuid4())[:12]

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        with _lock:
            # Expire existing active subscriptions for this user
            conn.execute(
                """UPDATE user_subscriptions
                   SET status = 'expired', updated_at = ?
                   WHERE user_id = ? AND status IN ('active', 'trial')""",
                (now, user_id),
            )

            # Create new subscription
            end_date = None
            if plan_code != "free":
                end_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()

            conn.execute(
                """INSERT INTO user_subscriptions
                   (id, user_id, plan_code, status, source,
                    start_date, end_date, created_at, updated_at)
                   VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (sub_id, user_id, plan_code, source, now, end_date, now, now),
            )
            conn.commit()

        # Also update users.db plan field
        _sync_user_plan(user_id, plan_code)

        _logger.info("Plan set: user=%s plan=%s source=%s", user_id, plan_code, source)
        return {
            "ok": True,
            "subscription": {
                "id": sub_id,
                "user_id": user_id,
                "plan_code": plan_code,
                "plan_name": PLANS[plan_code]["name"],
                "status": "active",
                "source": source,
                "start_date": now,
                "end_date": end_date,
            },
        }
    finally:
        conn.close()


def _sync_user_plan(user_id: str, plan_code: str):
    """Sync plan code to users.db."""
    try:
        conn = _get_conn(_USERS_DB)
        try:
            conn.execute(
                "UPDATE users SET plan = ? WHERE id = ?",
                (plan_code, user_id),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        _logger.warning("Could not sync plan to users.db: %s", exc)


def get_subscription_info(user_id: str) -> dict:
    """Get full subscription info including history."""
    conn = _get_conn()
    try:
        _ensure_tables(conn)
        rows = conn.execute(
            """SELECT * FROM user_subscriptions
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
        history = [dict(r) for r in rows]

        current = get_user_plan(user_id)
        return {
            "current": current,
            "history": history,
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# FEATURE GATING
# ══════════════════════════════════════════════════════════════════════

def can_use_feature(user_id: str, feature: str) -> dict:
    """Check if user can access a specific feature.

    Args:
        feature: one of 'premium_courses', 'premium_rooms',
                 'premium_strategies', 'advanced_screener',
                 'advanced_backtest', 'advanced_copilot'

    Returns:
        {"allowed": bool, "reason": str, "required_plan": str}
    """
    plan_info = get_user_plan(user_id)
    plan_code = plan_info["plan_code"]
    limits = plan_info["limits"]

    field = _FEATURE_MAP.get(feature)
    if not field:
        return {"allowed": True, "reason": "Bilinmeyen özellik"}

    allowed = limits.get(field, False)
    if allowed:
        return {"allowed": True, "reason": "Erişim izni var"}

    required = _FEATURE_REQUIRED_PLAN.get(feature, "Pro")
    return {
        "allowed": False,
        "reason": f"Bu özellik için {required} planı gerekiyor",
        "required_plan": required,
        "current_plan": plan_info["plan_name"],
    }


def can_create_alert(user_id: str) -> dict:
    """Check if user can create another alert."""
    plan_info = get_user_plan(user_id)
    max_alerts = plan_info["limits"]["max_alerts"]

    current_count = _count_user_alerts(user_id)
    allowed = current_count < max_alerts
    return {
        "allowed": allowed,
        "current": current_count,
        "max": max_alerts,
        "reason": "" if allowed else f"Alarm limitine ulaştınız ({max_alerts}). Planınızı yükseltin.",
        "required_plan": "Pro" if not allowed else None,
    }


def can_activate_strategy(user_id: str) -> dict:
    """Check if user can activate another live strategy."""
    plan_info = get_user_plan(user_id)
    max_active = plan_info["limits"]["max_active_strategies"]

    current_count = _count_active_strategies(user_id)
    allowed = current_count < max_active
    return {
        "allowed": allowed,
        "current": current_count,
        "max": max_active,
        "reason": "" if allowed else f"Aktif strateji limitine ulaştınız ({max_active}). Planınızı yükseltin.",
        "required_plan": "Pro" if not allowed else None,
    }


def can_save_strategy(user_id: str) -> dict:
    """Check if user can save another strategy."""
    plan_info = get_user_plan(user_id)
    max_saved = plan_info["limits"]["max_saved_strategies"]

    current_count = _count_saved_strategies(user_id)
    allowed = current_count < max_saved
    return {
        "allowed": allowed,
        "current": current_count,
        "max": max_saved,
        "reason": "" if allowed else f"Kayıtlı strateji limitine ulaştınız ({max_saved}). Planınızı yükseltin.",
        "required_plan": "Pro" if not allowed else None,
    }


def can_access_premium_course(user_id: str) -> dict:
    """Check if user can access premium courses."""
    return can_use_feature(user_id, "premium_courses")


def can_access_premium_room(user_id: str) -> dict:
    """Check if user can access premium rooms."""
    return can_use_feature(user_id, "premium_rooms")


def can_access_premium_strategy(user_id: str) -> dict:
    """Check if user can access premium marketplace strategies."""
    return can_use_feature(user_id, "premium_strategies")


def can_use_advanced_screener(user_id: str) -> dict:
    """Check if user can use advanced screener filters."""
    return can_use_feature(user_id, "advanced_screener")


def can_use_advanced_backtest(user_id: str) -> dict:
    """Check if user can use advanced backtest features."""
    return can_use_feature(user_id, "advanced_backtest")


def can_use_advanced_copilot(user_id: str) -> dict:
    """Check if user can use advanced copilot."""
    return can_use_feature(user_id, "advanced_copilot")


def enforce_limit(user_id: str, feature: str) -> dict:
    """Universal limit enforcer — combines feature + limit checks.

    Returns {"allowed": bool, "reason": str, ...}
    """
    if feature == "create_alert":
        return can_create_alert(user_id)
    elif feature == "activate_strategy":
        return can_activate_strategy(user_id)
    elif feature == "save_strategy":
        return can_save_strategy(user_id)
    elif feature == "copilot":
        return _check_copilot_limit(user_id)
    elif feature in _FEATURE_MAP:
        return can_use_feature(user_id, feature)
    else:
        return {"allowed": True, "reason": "Bilinmeyen özellik"}


# ══════════════════════════════════════════════════════════════════════
# COPILOT USAGE TRACKING
# ══════════════════════════════════════════════════════════════════════

def increment_copilot_usage(user_id: str) -> dict:
    """Increment copilot usage for today. Returns current count and limit."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan_info = get_user_plan(user_id)
    daily_limit = plan_info["limits"]["copilot_daily_limit"]

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        with _lock:
            row = conn.execute(
                "SELECT count FROM copilot_usage WHERE user_id = ? AND used_date = ?",
                (user_id, today),
            ).fetchone()

            if row:
                new_count = row["count"] + 1
                conn.execute(
                    "UPDATE copilot_usage SET count = ? WHERE user_id = ? AND used_date = ?",
                    (new_count, user_id, today),
                )
            else:
                new_count = 1
                conn.execute(
                    "INSERT INTO copilot_usage (user_id, used_date, count) VALUES (?, ?, 1)",
                    (user_id, today),
                )
            conn.commit()

        return {
            "count": new_count,
            "limit": daily_limit,
            "remaining": max(0, daily_limit - new_count),
        }
    finally:
        conn.close()


def _check_copilot_limit(user_id: str) -> dict:
    """Check if user has remaining copilot uses today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plan_info = get_user_plan(user_id)
    daily_limit = plan_info["limits"]["copilot_daily_limit"]

    conn = _get_conn()
    try:
        _ensure_tables(conn)
        row = conn.execute(
            "SELECT count FROM copilot_usage WHERE user_id = ? AND used_date = ?",
            (user_id, today),
        ).fetchone()
        current = row["count"] if row else 0
        allowed = current < daily_limit
        return {
            "allowed": allowed,
            "current": current,
            "max": daily_limit,
            "remaining": max(0, daily_limit - current),
            "reason": "" if allowed else f"Günlük copilot limitine ulaştınız ({daily_limit}). Planınızı yükseltin.",
            "required_plan": "Pro" if not allowed else None,
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# USAGE QUERY
# ══════════════════════════════════════════════════════════════════════

def get_usage(user_id: str) -> dict:
    """Get current usage stats for a user."""
    plan_info = get_user_plan(user_id)
    limits = plan_info["limits"]

    alert_count = _count_user_alerts(user_id)
    active_strat = _count_active_strategies(user_id)
    saved_strat = _count_saved_strategies(user_id)
    copilot_info = _check_copilot_limit(user_id)

    return {
        "plan_code": plan_info["plan_code"],
        "plan_name": plan_info["plan_name"],
        "alerts": {"used": alert_count, "max": limits["max_alerts"]},
        "active_strategies": {"used": active_strat, "max": limits["max_active_strategies"]},
        "saved_strategies": {"used": saved_strat, "max": limits["max_saved_strategies"]},
        "copilot": {
            "used_today": copilot_info["current"],
            "daily_limit": copilot_info["max"],
            "remaining": copilot_info["remaining"],
        },
    }


# ══════════════════════════════════════════════════════════════════════
# INTERNAL COUNTERS (read from other engines)
# ══════════════════════════════════════════════════════════════════════

def _count_user_alerts(user_id: str) -> int:
    """Count user's current alerts."""
    try:
        from app.core.alert_engine import get_alerts
        alerts = get_alerts(user_id=user_id)
        return len(alerts)
    except Exception:
        return 0


def _count_active_strategies(user_id: str) -> int:
    """Count user's active live strategies."""
    try:
        from app.core.strategy_live_engine import get_active_strategies
        active = get_active_strategies(user_id)
        return len(active)
    except Exception:
        return 0


def _count_saved_strategies(user_id: str) -> int:
    """Count user's saved strategies."""
    try:
        from app.core.strategy_engine import load_strategies
        strategies = load_strategies(user_id)
        return len(strategies)
    except Exception:
        return 0
