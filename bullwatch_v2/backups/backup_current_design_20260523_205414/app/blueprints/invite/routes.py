# -*- coding: utf-8 -*-
"""Invite & Referral API routes — FAZ 44.

Endpoints:
  GET  /invite                          — Invite dashboard (HTML)
  GET  /invite/<code>                   — Invite landing (redirect)
  GET  /api/invite/code                 — Get/generate invite code
  GET  /api/invite/stats                — Referral stats for user
  GET  /api/invite/rewards              — User rewards list
  GET  /api/invite/top-inviters         — Leaderboard: top inviters
  GET  /api/invite/recent               — Recent referral joins
  GET  /api/invite/growth-stats         — Platform growth stats
  POST /api/invite/register-referral    — Register a new referral
  GET  /api/leaderboard/referrals       — Referral leaderboard (alias)
  POST /api/share/generate              — Generate share URL + card
  GET  /api/share/<share_id>            — Get share info
  GET  /share/<share_id>                — Redirect to shared content
"""
from __future__ import annotations

import logging

from flask import jsonify, redirect, render_template, request, session

from app.blueprints.invite import invite_bp

_logger = logging.getLogger("zkr_analiz.invite.routes")


# ── HTML Pages ───────────────────────────────────────────────────

@invite_bp.route("/invite")
def invite_page():
    """Render the invite dashboard page."""
    return render_template("invite.html")


@invite_bp.route("/invite/<code>")
def invite_landing(code):
    """Invite link landing — stores code in session and redirects to register."""
    code = str(code).strip().upper()
    from app.core.referral_engine import validate_invite_code
    info = validate_invite_code(code)
    if info:
        session["invite_code"] = code
    return redirect("/register?ref=" + code)


# ── API: Invite Code ────────────────────────────────────────────

@invite_bp.route("/api/invite/code")
def api_get_code():
    """Get or generate user's invite code."""
    try:
        user_id = session.get("user_id", "")
        if not user_id:
            user_id = "demo_user"

        from app.core.referral_engine import get_invite_code
        code = get_invite_code(user_id)
        return jsonify({"ok": True, "code": code or "", "invite_url": f"/invite/{code}" if code else ""})
    except Exception as exc:
        _logger.error("Get invite code error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Stats ──────────────────────────────────────────────────

@invite_bp.route("/api/invite/stats")
def api_referral_stats():
    """Get referral stats for current user."""
    try:
        user_id = session.get("user_id", "demo_user")
        from app.core.referral_engine import get_referral_stats
        stats = get_referral_stats(user_id)
        return jsonify({"ok": True, "data": stats})
    except Exception as exc:
        _logger.error("Referral stats error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@invite_bp.route("/api/invite/rewards")
def api_rewards():
    """Get earned rewards for current user."""
    try:
        user_id = session.get("user_id", "demo_user")
        from app.core.referral_engine import calculate_referral_rewards
        rewards = calculate_referral_rewards(user_id)
        return jsonify({"ok": True, "data": rewards})
    except Exception as exc:
        _logger.error("Rewards error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Leaderboard ────────────────────────────────────────────

@invite_bp.route("/api/invite/top-inviters")
@invite_bp.route("/api/leaderboard/referrals")
def api_top_inviters():
    """Top inviters leaderboard."""
    try:
        limit = min(int(request.args.get("limit", 10)), 50)
        from app.core.referral_engine import get_top_inviters
        data = get_top_inviters(limit=limit)
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        _logger.error("Top inviters error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@invite_bp.route("/api/invite/recent")
def api_recent_referrals():
    """Recent referral registrations."""
    try:
        limit = min(int(request.args.get("limit", 10)), 50)
        from app.core.referral_engine import get_recent_referrals
        data = get_recent_referrals(limit=limit)
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        _logger.error("Recent referrals error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@invite_bp.route("/api/invite/growth-stats")
def api_growth_stats():
    """Platform growth stats."""
    try:
        from app.core.referral_engine import get_growth_stats
        data = get_growth_stats()
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        _logger.error("Growth stats error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Register Referral ──────────────────────────────────────

@invite_bp.route("/api/invite/register-referral", methods=["POST"])
def api_register_referral():
    """Register a new referral when user signs up with invite code."""
    try:
        body = request.get_json(force=True, silent=True) or {}
        invite_code = str(body.get("invite_code", "")).strip()
        new_user_id = str(body.get("new_user_id", "")).strip()
        ip_address = request.remote_addr or ""

        if not invite_code or not new_user_id:
            return jsonify({"ok": False, "error": "invite_code and new_user_id required"}), 400

        from app.core.referral_engine import register_referral
        result = register_referral(invite_code, new_user_id, ip_address)

        if result:
            return jsonify({"ok": True, "data": result})
        return jsonify({"ok": False, "error": "Invalid code, self-referral, or duplicate"}), 400
    except Exception as exc:
        _logger.error("Register referral error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── Share Routes ────────────────────────────────────────────────

@invite_bp.route("/api/share/generate", methods=["POST"])
def api_generate_share():
    """Generate a share URL and card for content."""
    try:
        body = request.get_json(force=True, silent=True) or {}
        content_type = str(body.get("content_type", "")).strip()
        content_id = str(body.get("content_id", "")).strip()
        user_id = session.get("user_id", "")
        title = str(body.get("title", "")).strip()
        description = str(body.get("description", "")).strip()

        if not content_type or not content_id:
            return jsonify({"ok": False, "error": "content_type and content_id required"}), 400

        from app.core.share_engine import generate_share_url, generate_share_card
        url = generate_share_url(content_type, content_id, user_id, title, description)
        card = generate_share_card(content_type, content_id, user_id)

        return jsonify({"ok": True, "data": {"url": url, "card": card}})
    except Exception as exc:
        _logger.error("Generate share error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@invite_bp.route("/api/share/<share_id>")
def api_share_info(share_id):
    """Get share info by ID."""
    try:
        from app.core.share_engine import get_share_by_id
        data = get_share_by_id(share_id)
        if not data:
            return jsonify({"ok": False, "error": "Share not found"}), 404
        return jsonify({"ok": True, "data": data})
    except Exception as exc:
        _logger.error("Share info error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@invite_bp.route("/share/<share_id>")
def share_redirect(share_id):
    """Redirect to shared content, tracking click."""
    from app.core.share_engine import get_share_by_id, track_share_click, CONTENT_TYPES
    track_share_click(share_id)
    data = get_share_by_id(share_id)
    if not data:
        return redirect("/discover")
    ct = CONTENT_TYPES.get(data["content_type"])
    if ct:
        return redirect(f"{ct['base_path']}/{data['content_id']}")
    return redirect("/discover")
