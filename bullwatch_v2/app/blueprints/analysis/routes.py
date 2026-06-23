# -*- coding: utf-8 -*-
"""Analysis / Growth Engine API routes — FAZ 36 (Viral Sharing).

Endpoints:
  POST /api/analysis/create       — Create analysis post
  GET  /api/analysis/feed         — Analysis feed
  GET  /api/analysis/<id>         — Single analysis
  POST /api/analysis/like         — Toggle like
  POST /api/analysis/comment      — Add comment
  GET  /api/analysis/comments/<id>— Get comments
  DELETE /api/analysis/<id>       — Delete analysis
  POST /api/analysis/share        — Increment share counter
  GET  /api/analysis/trending     — Trending analyses
  GET  /api/analysis/leaderboard  — Analyst leaderboard data
  GET  /api/analysis/user/<uid>   — User analysis stats
  GET  /api/analysis/features     — Feature flag list
  POST /api/analysis/feature      — Toggle feature flag

Pages:
  GET  /analysis/<id>             — Public analysis page
  GET  /leaderboard               — Leaderboard page
"""
from __future__ import annotations

import base64
import logging
import os
import re
import uuid

from flask import jsonify, render_template, request, session

from app.blueprints.analysis import analysis_bp
from app.core import analysis_engine as ae

_logger = logging.getLogger("zkr_analiz.analysis.routes")

_MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "static", "media")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


def _save_chart_image(data_url: str) -> str | None:
    """Save base64 data URL to static/media and return relative path."""
    if not data_url:
        return None
    # Validate it's a data URL
    match = re.match(r'^data:image/(png|jpeg|webp);base64,(.+)$', data_url)
    if not match:
        return None

    ext = match.group(1)
    if ext == "jpeg":
        ext = "jpg"
    raw = match.group(2)

    try:
        img_bytes = base64.b64decode(raw)
    except Exception:
        return None

    # Limit to 5MB
    if len(img_bytes) > 5 * 1024 * 1024:
        return None

    os.makedirs(_MEDIA_DIR, exist_ok=True)
    filename = f"chart_{uuid.uuid4().hex[:12]}.{ext}"
    filepath = os.path.join(_MEDIA_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(img_bytes)

    return f"/static/media/{filename}"


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@analysis_bp.route("/analysis/<analysis_id>")
def analysis_detail_page(analysis_id):
    """Public analysis page."""
    return render_template("analysis_detail.html", analysis_id=analysis_id)


@analysis_bp.route("/leaderboard")
def leaderboard_page():
    return render_template("leaderboard.html")


# ══════════════════════════════════════════════════════════════════
# API — ANALYSIS CRUD
# ══════════════════════════════════════════════════════════════════

@analysis_bp.route("/api/analysis/create", methods=["POST"])
def api_create_analysis():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "İçerik gerekli"}), 400

    # Save chart image from data URL if provided
    chart_image = _save_chart_image(data.get("chart_image") or "")

    try:
        analysis = ae.create_analysis(
            user_id=uid,
            content=content,
            title=data.get("title", ""),
            symbol=data.get("symbol"),
            market=data.get("market"),
            timeframe=data.get("timeframe"),
            direction=data.get("direction"),
            chart_image=chart_image,
            is_public=data.get("is_public", True),
        )
        return jsonify({"ok": True, "analysis": analysis})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@analysis_bp.route("/api/analysis/feed")
def api_analysis_feed():
    uid = session.get("user_id")
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    symbol = request.args.get("symbol")

    posts = ae.get_analysis_feed(
        limit=limit, offset=offset, symbol=symbol, viewer_id=uid
    )
    return jsonify({"ok": True, "analyses": posts, "count": len(posts)})


@analysis_bp.route("/api/analysis/<analysis_id>")
def api_get_analysis(analysis_id):
    uid = session.get("user_id")
    analysis = ae.get_analysis(analysis_id, viewer_id=uid, increment_views=True)
    if not analysis:
        return jsonify({"ok": False, "error": "Bulunamadı"}), 404

    comments = ae.get_analysis_comments(analysis_id)
    return jsonify({"ok": True, "analysis": analysis, "comments": comments})


@analysis_bp.route("/api/analysis/<analysis_id>", methods=["DELETE"])
def api_delete_analysis(analysis_id):
    uid, err = _require_login()
    if err:
        return err
    deleted = ae.delete_analysis(analysis_id, uid)
    if not deleted:
        return jsonify({"ok": False, "error": "Silinemedi"}), 403
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# API — LIKES & COMMENTS
# ══════════════════════════════════════════════════════════════════

@analysis_bp.route("/api/analysis/like", methods=["POST"])
def api_toggle_like():
    uid, err = _require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    analysis_id = data.get("analysis_id")
    if not analysis_id:
        return jsonify({"ok": False, "error": "analysis_id gerekli"}), 400
    result = ae.toggle_analysis_like(analysis_id, uid)
    return jsonify(result)


@analysis_bp.route("/api/analysis/comment", methods=["POST"])
def api_add_comment():
    uid, err = _require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    analysis_id = data.get("analysis_id")
    content = (data.get("content") or "").strip()
    if not analysis_id or not content:
        return jsonify({"ok": False, "error": "analysis_id ve content gerekli"}), 400

    try:
        comment = ae.add_analysis_comment(analysis_id, uid, content)
        return jsonify({"ok": True, "comment": comment})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@analysis_bp.route("/api/analysis/comments/<analysis_id>")
def api_get_comments(analysis_id):
    comments = ae.get_analysis_comments(analysis_id)
    return jsonify({"ok": True, "comments": comments})


@analysis_bp.route("/api/analysis/share", methods=["POST"])
def api_share():
    data = request.get_json(silent=True) or {}
    analysis_id = data.get("analysis_id")
    if not analysis_id:
        return jsonify({"ok": False, "error": "analysis_id gerekli"}), 400
    result = ae.increment_shares(analysis_id)
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════
# API — TRENDING & LEADERBOARD
# ══════════════════════════════════════════════════════════════════

@analysis_bp.route("/api/analysis/trending")
def api_trending():
    limit = min(int(request.args.get("limit", 10)), 50)
    analyses = ae.get_trending_analyses(limit)
    return jsonify({"ok": True, "analyses": analyses})


@analysis_bp.route("/api/analysis/leaderboard")
def api_leaderboard():
    limit = min(int(request.args.get("limit", 20)), 50)
    data = ae.get_leaderboard(limit)
    return jsonify({"ok": True, "leaderboard": data})


@analysis_bp.route("/api/analysis/user-stats/<user_id>")
def api_user_stats(user_id):
    stats = ae.get_analyst_stats(user_id)
    return jsonify({"ok": True, "stats": stats})


# ══════════════════════════════════════════════════════════════════
# API — FEATURE FLAGS
# ══════════════════════════════════════════════════════════════════

@analysis_bp.route("/api/analysis/features")
def api_features():
    features = ae.list_features()
    return jsonify({"ok": True, "features": features})


@analysis_bp.route("/api/analysis/feature", methods=["POST"])
def api_set_feature():
    uid, err = _require_login()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    enabled = data.get("enabled")
    if not name or enabled is None:
        return jsonify({"ok": False, "error": "name ve enabled gerekli"}), 400
    result = ae.set_feature(name, bool(enabled))
    return jsonify(result)


@analysis_bp.route("/api/analysis/feature/<name>")
def api_check_feature(name):
    enabled = ae.feature_enabled(name)
    return jsonify({"ok": True, "feature": name, "enabled": enabled})
