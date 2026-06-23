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
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from flask import jsonify, redirect, render_template, request, session, url_for

from app.blueprints.auth import auth_bp
from app.core.user_engine import (
    register_user,
    authenticate,
    get_user,
    save_user_data,
    load_user_data,
)
from app.extensions import db
from app.models import UserLegalConsent

_logger = logging.getLogger("zkr_analiz.auth.routes")


# ══════════════════════════════════════════════════════════════════════
# LEGAL COMPLIANCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def load_legal_terms() -> str:
    """Load Turkish legal terms from file (HMK Madde 193 compliance)."""
    legal_file = Path(__file__).parent.parent.parent.parent / "legal_terms.txt"
    try:
        with open(legal_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        _logger.error("Legal terms file not found: %s", legal_file)
        return "HATA: Sözleşme dosyası bulunamadı"


def compute_document_hash(document_text: str) -> str:
    """Compute SHA-256 hash of legal document (FIPS 180-2 standard).
    
    Per HMK Madde 193: SHA-256 logged records as conclusive proof.
    """
    return hashlib.sha256(document_text.encode("utf-8")).hexdigest()


def record_legal_consent(user_id: int, accept_terms: bool) -> None:
    """Record legal consent with SHA-256 proof (audit trail).
    
    Args:
        user_id: User ID from database
        accept_terms: Whether user accepted terms
    """
    if not accept_terms:
        return
    
    legal_text = load_legal_terms()
    doc_hash = compute_document_hash(legal_text)
    ip_address = request.remote_addr or "0.0.0.0"
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    # Create consent record
    consent = UserLegalConsent(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        document_version="v1.0",
        document_hash=doc_hash,
        timestamp_utc=datetime.utcnow()
    )
    
    db.session.add(consent)
    db.session.commit()
    
    _logger.info(
        "✅ Legal consent recorded: user_id=%s hash=%s ip=%s",
        user_id, doc_hash[:16], ip_address
    )



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
    """Register a new user with legal consent tracking (HMK Madde 193).

    Body: { email, username, password, accept_terms }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    username = data.get("username", "")
    password = data.get("password", "")
    accept_terms = data.get("accept_terms", False)

    try:
        user = register_user(email, username, password)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    # Record legal consent with SHA-256 proof
    record_legal_consent(user["id"], accept_terms)

    # Auto-login after registration
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session.permanent = True

    _logger.info(
        "✅ User registered: %s (terms_accepted=%s)",
        user["email"], accept_terms
    )
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
