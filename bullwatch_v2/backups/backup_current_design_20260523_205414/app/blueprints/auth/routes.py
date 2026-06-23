# -*- coding: utf-8 -*-
"""Auth API routes — FAZ 27.

Endpoints:
  POST /api/auth/register     — Register a new user
  POST /api/auth/login        — Login (returns session cookie)
  POST /api/auth/logout       — Logout (clears session)
  GET  /api/auth/me           — Get current logged-in user info
  POST /api/auth/data/save    — Save cloud sync data
  POST /api/auth/data/load    — Load cloud sync data

Pages:
  GET  /login                 — Login page
  GET  /register              — Register page
"""
from __future__ import annotations

import functools
import logging

from flask import jsonify, redirect, render_template, request, session, url_for

from app.blueprints.auth import auth_bp
from app.core.user_engine import (
    register_user,
    authenticate,
    get_user,
    save_user_data,
    load_user_data,
)

_logger = logging.getLogger("zkr_analiz.auth.routes")


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def get_current_user() -> dict | None:
    """Get current user from session. Returns user dict or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user(user_id)


def login_required(f):
    """Decorator: require authenticated session for API endpoints."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401
        return f(*args, user=user, **kwargs)
    return wrapper


def get_session_user_id() -> str | None:
    """Get user_id from session (for use in other blueprints)."""
    return session.get("user_id")


# ══════════════════════════════════════════════════════════════════════
# AUTH API
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    """Register a new user.

    Body: { email, username, password }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    username = data.get("username", "")
    password = data.get("password", "")

    try:
        user = register_user(email, username, password)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    # Auto-login after registration
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session.permanent = True

    return jsonify({"ok": True, "user": user}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    """Login with email + password.

    Body: { email, password }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    password = data.get("password", "")

    user = authenticate(email, password)
    if not user:
        return jsonify({"ok": False, "error": "E-posta veya şifre hatalı"}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session.permanent = True

    _logger.info("User logged in: %s", user["email"])
    return jsonify({"ok": True, "user": user})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    """Logout — clear session."""
    username = session.get("username", "?")
    session.clear()
    _logger.info("User logged out: %s", username)
    return jsonify({"ok": True, "message": "Çıkış yapıldı"})


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_me():
    """Get current logged-in user info."""
    user = get_current_user()
    if not user:
        return jsonify({"ok": False, "logged_in": False}), 200
    return jsonify({"ok": True, "logged_in": True, "user": user})


# ══════════════════════════════════════════════════════════════════════
# CLOUD DATA SYNC API
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/api/auth/data/save", methods=["POST"])
@login_required
def api_data_save(user):
    """Save user cloud data.

    Body: { key: "drawings|layout|watchlist|...", data: {...} }
    """
    body = request.get_json(silent=True) or {}
    key = (body.get("key") or "").strip()
    data = body.get("data")

    if not key:
        return jsonify({"ok": False, "error": "key gerekli"}), 400
    if data is None:
        return jsonify({"ok": False, "error": "data gerekli"}), 400

    ok = save_user_data(user["id"], key, data)
    return jsonify({"ok": ok})


@auth_bp.route("/api/auth/data/load", methods=["POST", "GET"])
@login_required
def api_data_load(user):
    """Load user cloud data.

    Body/Query: { key: "drawings|layout|watchlist|..." }
    """
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        key = (body.get("key") or "").strip()
    else:
        key = request.args.get("key", "").strip()

    if not key:
        return jsonify({"ok": False, "error": "key gerekli"}), 400

    data = load_user_data(user["id"], key)
    return jsonify({"ok": True, "key": key, "data": data})


# ══════════════════════════════════════════════════════════════════════
# AUTH PAGES
# ══════════════════════════════════════════════════════════════════════

@auth_bp.route("/login", methods=["GET"])
def page_login():
    """Login page."""
    if get_current_user():
        return redirect("/trade")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET"])
def page_register():
    """Register page."""
    if get_current_user():
        return redirect("/trade")
    return render_template("register.html")
