# -*- coding: utf-8 -*-
"""Subscription API routes — FAZ 36.

Endpoints:
  GET  /api/plans                    — List all plans
  GET  /api/subscription/me          — Current user's subscription
  POST /api/subscription/check-feature — Check feature access
  POST /api/subscription/set-plan    — Admin/manual plan change
  GET  /api/subscription/usage       — Current usage stats

Pages:
  GET  /pricing                      — Pricing page
  GET  /account/plan                 — Account plan page
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.subscription import subscription_bp
from app.core import subscription_engine

_logger = logging.getLogger("zkr_analiz.subscription.routes")


# ── helpers ───────────────────────────────────────────────────────
def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


# ══════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════

@subscription_bp.route("/pricing")
def pricing_page():
    return render_template("pricing.html")


@subscription_bp.route("/account/plan")
def account_plan_page():
    return render_template("account_plan.html")


# ══════════════════════════════════════════════════════════════════════
# API — PLANS
# ══════════════════════════════════════════════════════════════════════

@subscription_bp.route("/api/plans", methods=["GET"])
def api_plans():
    """List all available plans with their limits."""
    plans = subscription_engine.get_all_plans()
    return jsonify({"ok": True, "plans": plans})


# ══════════════════════════════════════════════════════════════════════
# API — SUBSCRIPTION info
# ══════════════════════════════════════════════════════════════════════

@subscription_bp.route("/api/subscription/me", methods=["GET"])
def api_my_subscription():
    """Get current user's subscription info."""
    uid, err = _require_login()
    if err:
        return err

    info = subscription_engine.get_subscription_info(uid)
    return jsonify({"ok": True, **info})


@subscription_bp.route("/api/subscription/usage", methods=["GET"])
def api_usage():
    """Get current user's usage stats."""
    uid, err = _require_login()
    if err:
        return err

    usage = subscription_engine.get_usage(uid)
    return jsonify({"ok": True, **usage})


# ══════════════════════════════════════════════════════════════════════
# API — FEATURE GATE CHECK
# ══════════════════════════════════════════════════════════════════════

@subscription_bp.route("/api/subscription/check-feature", methods=["POST"])
def api_check_feature():
    """Check if current user can access a feature.

    Body JSON:
      feature: str  — feature name (e.g., 'premium_courses', 'create_alert')
    """
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    feature = (data.get("feature") or "").strip()
    if not feature:
        return jsonify({"ok": False, "error": "feature parametresi gerekli"}), 400

    result = subscription_engine.enforce_limit(uid, feature)
    return jsonify({"ok": True, **result})


# ══════════════════════════════════════════════════════════════════════
# API — SET PLAN (admin/manual only)
# ══════════════════════════════════════════════════════════════════════

@subscription_bp.route("/api/subscription/set-plan", methods=["POST"])
def api_set_plan():
    """Set user plan (admin/manual activation only).

    Body JSON:
      user_id:   str — target user ID
      plan_code: str — 'free', 'pro', or 'pro_plus'
      source:    str — 'manual' or 'admin' (default 'manual')

    Note: This endpoint requires login. In production, add admin check.
    Currently accepts 'manual' and 'admin' sources for testing.
    """
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    target_user = (data.get("user_id") or "").strip()
    plan_code = (data.get("plan_code") or "").strip()
    source = (data.get("source") or "manual").strip()

    if not target_user:
        return jsonify({"ok": False, "error": "user_id gerekli"}), 400
    if not plan_code:
        return jsonify({"ok": False, "error": "plan_code gerekli"}), 400
    if plan_code not in subscription_engine.PLANS:
        return jsonify({"ok": False, "error": f"Geçersiz plan: {plan_code}"}), 400

    # Only allow manual/admin sources (no payment sources yet)
    if source not in ("manual", "admin"):
        source = "manual"

    result = subscription_engine.set_user_plan(target_user, plan_code, source)
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════
# COPILOT INTEGRATION
# ══════════════════════════════════════════════════════════════════════

@subscription_bp.route("/api/copilot/subscription", methods=["POST"])
def copilot_subscription():
    """Copilot endpoint: answer user plan questions."""
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()

    plan_info = subscription_engine.get_user_plan(uid)
    usage = subscription_engine.get_usage(uid)

    return jsonify({
        "ok": True,
        "plan": plan_info,
        "usage": usage,
        "message": f"Mevcut planınız: {plan_info['plan_name']}. "
                   f"Alarm: {usage['alerts']['used']}/{usage['alerts']['max']}, "
                   f"Aktif strateji: {usage['active_strategies']['used']}/{usage['active_strategies']['max']}, "
                   f"Copilot: {usage['copilot']['used_today']}/{usage['copilot']['daily_limit']}",
    })
