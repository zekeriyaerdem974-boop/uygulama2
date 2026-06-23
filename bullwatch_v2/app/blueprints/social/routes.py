# -*- coding: utf-8 -*-
"""Social Trading Feed API routes — FAZ 31.

Endpoints:
  POST /api/social/post           — Create a post
  GET  /api/social/feed           — Global feed (or following feed)
  GET  /api/social/post/<id>      — Single post with comments
  POST /api/social/comment        — Add comment
  POST /api/social/like           — Toggle like
  POST /api/social/follow         — Follow user
  POST /api/social/unfollow       — Unfollow user
  GET  /api/social/user/<username>— User profile data

Pages:
  GET  /feed                      — Feed page
  GET  /user/<username>           — User profile page
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.social import social_bp
from app.core import social_engine as se

_logger = logging.getLogger("zkr_analiz.social.routes")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@social_bp.route("/feed")
def feed_page():
    return render_template("feed.html")


@social_bp.route("/user/<username>")
def user_profile_page(username):
    return render_template("user_profile.html", profile_username=username)


# ══════════════════════════════════════════════════════════════════
# API — POSTS
# ══════════════════════════════════════════════════════════════════

@social_bp.route("/api/social/post", methods=["POST"])
def api_create_post():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "İçerik gerekli"}), 400

    try:
        post = se.create_post(
            user_id=uid,
            content=content,
            symbol=data.get("symbol"),
            market=data.get("market"),
            timeframe=data.get("timeframe"),
            chart_snapshot=data.get("chart_snapshot"),
        )
        return jsonify({"ok": True, "post": post})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@social_bp.route("/api/social/feed")
def api_feed():
    uid = session.get("user_id")
    feed_type = request.args.get("type", "global")
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    symbol = request.args.get("symbol")

    if feed_type == "following" and uid:
        posts = se.get_following_feed(uid, limit=limit, offset=offset)
    else:
        posts = se.get_feed(limit=limit, offset=offset, symbol=symbol, viewer_id=uid)

    return jsonify({"ok": True, "posts": posts, "count": len(posts)})


@social_bp.route("/api/social/post/<post_id>")
def api_get_post(post_id):
    uid = session.get("user_id")
    post = se.get_post(post_id, viewer_id=uid)
    if not post:
        return jsonify({"ok": False, "error": "Post bulunamadı"}), 404

    comments = se.get_comments(post_id)
    return jsonify({"ok": True, "post": post, "comments": comments})


@social_bp.route("/api/social/post/<post_id>", methods=["DELETE"])
def api_delete_post(post_id):
    uid, err = _require_login()
    if err:
        return err
    ok = se.delete_post(post_id, uid)
    if not ok:
        return jsonify({"ok": False, "error": "Silinemedi"}), 403
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# API — COMMENTS
# ══════════════════════════════════════════════════════════════════

@social_bp.route("/api/social/comment", methods=["POST"])
def api_add_comment():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    post_id = data.get("post_id")
    content = (data.get("content") or "").strip()

    if not post_id or not content:
        return jsonify({"ok": False, "error": "post_id ve content gerekli"}), 400

    try:
        comment = se.add_comment(post_id, uid, content)
        return jsonify({"ok": True, "comment": comment})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# API — LIKES
# ══════════════════════════════════════════════════════════════════

@social_bp.route("/api/social/like", methods=["POST"])
def api_toggle_like():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    post_id = data.get("post_id")
    if not post_id:
        return jsonify({"ok": False, "error": "post_id gerekli"}), 400

    result = se.toggle_like(post_id, uid)
    return jsonify({"ok": True, **result})


# ══════════════════════════════════════════════════════════════════
# API — FOLLOWS
# ══════════════════════════════════════════════════════════════════

@social_bp.route("/api/social/follow", methods=["POST"])
def api_follow_user():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    target_id = data.get("user_id")
    if not target_id:
        return jsonify({"ok": False, "error": "user_id gerekli"}), 400

    try:
        se.follow_user(uid, target_id)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@social_bp.route("/api/social/unfollow", methods=["POST"])
def api_unfollow_user():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    target_id = data.get("user_id")
    if not target_id:
        return jsonify({"ok": False, "error": "user_id gerekli"}), 400

    se.unfollow_user(uid, target_id)
    return jsonify({"ok": True})


@social_bp.route("/api/social/user/<username>")
def api_user_profile(username):
    uid = session.get("user_id")
    profile = se.get_user_profile(username, viewer_id=uid)
    if not profile:
        return jsonify({"ok": False, "error": "Kullanıcı bulunamadı"}), 404

    posts = se.get_user_feed(profile["user_id"], limit=20, viewer_id=uid)
    return jsonify({"ok": True, "profile": profile, "posts": posts})


# ══════════════════════════════════════════════════════════════════
# COPILOT — SOCIAL
# ══════════════════════════════════════════════════════════════════

@social_bp.route("/api/copilot/social", methods=["POST"])
def api_copilot_social():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Soru gerekli"}), 400

    trending = se.get_trending(limit=10)
    context_parts = ["TRENDING ANALİZLER (son 48 saat):"]
    for t in trending:
        context_parts.append(
            f"  - @{t.get('username','?')}: {t['content'][:80]} "
            f"({t.get('symbol','?')}) likes={t['likes_count']} comments={t['comments_count']}"
        )
    context_text = "\n".join(context_parts)

    try:
        from app.core.copilot_service import _SYSTEM_BASE, _call_llm, DEFAULT_MODEL
        _SOCIAL_PROMPT = (
            "\nBu yanıtı ZKR Analiz Social Trading Feed için veriyorsun.\n"
            "Context'te trending analizler, kullanıcı paylaşımları ve etkileşim verileri var.\n"
            "En çok konuşulan coinleri, başarılı analizcileri ve riskleri değerlendir.\n"
        )
        system = _SYSTEM_BASE + _SOCIAL_PROMPT
        prompt = f"[CONTEXT]\n{context_text}\n\n[KULLANICI SORUSU]\n{question}\n\nassistant:"
        result = _call_llm(DEFAULT_MODEL, system, prompt, {"social": context_text})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        _logger.warning("Copilot social error: %s", e)
        return jsonify({
            "ok": True,
            "data": {
                "answer": f"Feed'de şu anda {len(trending)} trending analiz var.",
                "summary": "Social feed özeti",
                "key_points": [f"{len(trending)} trending analiz"],
                "risk_points": [],
                "suggested_alerts": [],
            }
        })
