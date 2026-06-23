# -*- coding: utf-8 -*-
"""Settings & Localization API routes — FAZ 52."""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.auth.routes import login_required, get_current_user
from app.blueprints.settings import settings_bp
from app.core.localization_engine import (
    get_locale,
    get_supported_languages,
    is_rtl,
    resolve_language,
    translate,
)
from app.core.settings_engine import (
    delete_user_settings,
    get_default_settings,
    get_user_settings,
    update_user_settings,
)

_logger = logging.getLogger("zkr_analiz.settings.routes")


# ══════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════

@settings_bp.route("/settings")
def page_settings():
    """Settings page — works for both authenticated and anonymous users."""
    uid = session.get("user_id")
    if uid:
        user = get_current_user()
        lang = resolve_language(uid) if user else "en"
    else:
        user = None
        lang = "en"
    return render_template(
        "settings.html",
        user_lang=lang,
        is_rtl=is_rtl(lang),
        languages=get_supported_languages(),
    )


# ══════════════════════════════════════════════════════════════════
# SETTINGS CRUD API
# ══════════════════════════════════════════════════════════════════

@settings_bp.route("/api/settings/me", methods=["GET"])
@login_required
def api_settings_me(user):
    """Get current user settings."""
    settings = get_user_settings(user["id"])
    lang = settings.get("language_code", "en")
    return jsonify({
        "ok": True,
        "settings": settings,
        "is_rtl": is_rtl(lang),
    })


@settings_bp.route("/api/settings/update", methods=["POST"])
@login_required
def api_settings_update(user):
    """Update user settings (accepts partial updates)."""
    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"ok": False, "error": "No data provided"}), 400

    updated = update_user_settings(user["id"], body)

    # Update session language if changed
    if "language_code" in body:
        session["language"] = updated.get("language_code", "en")

    return jsonify({"ok": True, "settings": updated})


# ══════════════════════════════════════════════════════════════════
# LANGUAGE API
# ══════════════════════════════════════════════════════════════════

@settings_bp.route("/api/settings/languages", methods=["GET"])
def api_languages():
    """Get list of supported languages (no auth required)."""
    return jsonify({
        "ok": True,
        "languages": get_supported_languages(),
    })


@settings_bp.route("/api/settings/language", methods=["POST"])
@login_required
def api_set_language(user):
    """Set user language preference."""
    body = request.get_json(silent=True) or {}
    lang_code = (body.get("language_code") or "").strip().lower()

    from app.core.localization_engine import get_supported_codes
    if lang_code not in get_supported_codes():
        return jsonify({"ok": False, "error": "Unsupported language"}), 400

    updated = update_user_settings(user["id"], {"language_code": lang_code})
    session["language"] = lang_code

    return jsonify({
        "ok": True,
        "language_code": lang_code,
        "is_rtl": is_rtl(lang_code),
    })


@settings_bp.route("/api/settings/locale/<lang_code>", methods=["GET"])
def api_get_locale(lang_code):
    """Get translation strings for a language (no auth required)."""
    locale = get_locale(lang_code)
    return jsonify({"ok": True, "lang": lang_code, "translations": locale})


# ══════════════════════════════════════════════════════════════════
# THEME API
# ══════════════════════════════════════════════════════════════════

@settings_bp.route("/api/settings/theme", methods=["POST"])
@login_required
def api_set_theme(user):
    """Set user theme preference."""
    body = request.get_json(silent=True) or {}
    theme = (body.get("theme") or "").strip()

    valid_themes = {"dark", "dark_pro", "system"}
    if theme not in valid_themes:
        return jsonify({"ok": False, "error": "Invalid theme"}), 400

    updated = update_user_settings(user["id"], {"theme": theme})
    return jsonify({"ok": True, "theme": updated.get("theme")})


# ══════════════════════════════════════════════════════════════════
# NOTIFICATIONS API
# ══════════════════════════════════════════════════════════════════

@settings_bp.route("/api/settings/notifications", methods=["POST"])
@login_required
def api_set_notifications(user):
    """Update notification preferences."""
    body = request.get_json(silent=True) or {}

    notif_fields = {
        "notifications_enabled", "email_notifications", "push_notifications",
        "ai_brief_notifications", "opportunity_alerts", "portfolio_risk_alerts",
        "mentor_activity_notifications", "course_update_notifications",
        "live_room_notifications", "referral_reward_notifications",
    }
    filtered = {k: v for k, v in body.items() if k in notif_fields}
    if not filtered:
        return jsonify({"ok": False, "error": "No notification fields provided"}), 400

    updated = update_user_settings(user["id"], filtered)
    return jsonify({"ok": True, "settings": updated})


# ══════════════════════════════════════════════════════════════════
# DATA MANAGEMENT API
# ══════════════════════════════════════════════════════════════════

@settings_bp.route("/api/settings/export", methods=["GET"])
@login_required
def api_export_data(user):
    """Export user data (returns JSON of all settings)."""
    settings = get_user_settings(user["id"])
    return jsonify({
        "ok": True,
        "export": {
            "user_id": user["id"],
            "username": user.get("username"),
            "email": user.get("email"),
            "settings": settings,
        },
    })


@settings_bp.route("/api/settings/delete-account", methods=["POST"])
@login_required
def api_delete_account(user):
    """Delete user account settings (marks for deletion)."""
    body = request.get_json(silent=True) or {}
    confirm = body.get("confirm")

    if confirm != "DELETE":
        return jsonify({"ok": False, "error": "Confirmation required"}), 400

    deleted = delete_user_settings(user["id"])
    return jsonify({"ok": deleted, "message": "Account data deleted" if deleted else "Error"})
