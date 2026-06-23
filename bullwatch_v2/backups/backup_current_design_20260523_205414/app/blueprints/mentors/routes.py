# -*- coding: utf-8 -*-
"""Mentor / Analyst Profiles API routes — FAZ 32.

Endpoints:
  GET  /api/mentors                — List mentors
  GET  /api/mentor/<username>      — Mentor profile data
  POST /api/mentor/profile         — Create/update own mentor profile
  POST /api/mentor/follow          — Follow a mentor
  POST /api/mentor/unfollow        — Unfollow a mentor
  GET  /api/mentor/featured        — Featured mentors
  GET  /api/mentor/my-profile      — Get own mentor profile

Pages:
  GET  /mentors                    — Mentors listing page
  GET  /mentor/<username>          — Mentor profile page

Copilot:
  POST /api/copilot/mentors        — Copilot mentor Q&A
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.mentors import mentors_bp
from app.core import mentor_engine as me

_logger = logging.getLogger("zkr_analiz.mentors.routes")

# ── FAZ 62: Feature Lock ─────────────────────────────────────────
COMING_SOON = True


def _coming_soon_response():
    return jsonify({"ok": False, "coming_soon": True, "message": "Mentör sistemi yakında geliyor"}), 503


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@mentors_bp.route("/mentors")
def mentors_page():
    return render_template("mentors.html", coming_soon=COMING_SOON)


@mentors_bp.route("/mentor/<username>")
def mentor_profile_page(username):
    return render_template("mentor_profile.html", profile_username=username, coming_soon=COMING_SOON)


# ══════════════════════════════════════════════════════════════════
# API — LIST & PROFILE
# ══════════════════════════════════════════════════════════════════

@mentors_bp.route("/api/mentors")
def api_list_mentors():
    if COMING_SOON:
        return _coming_soon_response()
    uid = session.get("user_id")
    market = request.args.get("market")
    sort = request.args.get("sort", "followers")
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    search = request.args.get("search")

    mentors = me.list_mentors(
        market=market, sort=sort, limit=limit, offset=offset,
        search=search, viewer_id=uid,
    )
    return jsonify({"ok": True, "mentors": mentors, "count": len(mentors)})


@mentors_bp.route("/api/mentor/featured")
def api_featured_mentors():
    if COMING_SOON:
        return _coming_soon_response()
    limit = min(int(request.args.get("limit", 6)), 20)
    mentors = me.featured_mentors(limit=limit)
    return jsonify({"ok": True, "mentors": mentors})


@mentors_bp.route("/api/mentor/<username>")
def api_mentor_profile(username):
    if COMING_SOON:
        return _coming_soon_response()
    uid = session.get("user_id")
    profile = me.get_profile(username, viewer_id=uid)
    if not profile:
        return jsonify({"ok": False, "error": "Mentor bulunamadı"}), 404

    stats = me.mentor_stats(profile["user_id"])

    # Get recent posts from social engine
    posts = []
    try:
        from app.core import social_engine as se
        posts = se.get_user_feed(profile["user_id"], limit=10, viewer_id=uid)
    except Exception:
        pass

    # Get published strategies from marketplace
    strategies = []
    try:
        from app.core import marketplace_engine as mpe
        strategies = mpe.get_my_published(profile["user_id"])
    except Exception:
        pass

    # Get courses from course engine (FAZ 33)
    courses = []
    try:
        from app.core import course_engine as ceng
        courses = ceng.get_mentor_courses(profile["user_id"], published_only=True)
    except Exception:
        pass

    # Get live rooms from live_room_engine (FAZ 34)
    live_rooms = []
    try:
        from app.core import live_room_engine as lreng
        live_rooms = lreng.get_mentor_rooms(profile["user_id"])
    except Exception:
        pass

    # Get reputation & ratings (FAZ 35)
    reputation = None
    mentor_avg_rating = None
    try:
        from app.core import reputation_engine as repeng
        reputation = repeng.get_reputation(profile["user_id"])
        if not reputation:
            reputation = repeng.calculate_user_score(profile["user_id"])
        mentor_avg_rating = repeng.get_mentor_avg_rating(profile["user_id"])
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "profile": profile,
        "stats": stats,
        "posts": posts,
        "strategies": strategies,
        "courses": courses,
        "live_rooms": live_rooms,
        "reputation": reputation,
        "mentor_avg_rating": mentor_avg_rating,
    })


@mentors_bp.route("/api/mentor/my-profile")
def api_my_profile():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    profile = me.get_profile_by_user_id(uid)
    if not profile:
        return jsonify({"ok": True, "profile": None})
    return jsonify({"ok": True, "profile": profile})


# ══════════════════════════════════════════════════════════════════
# API — CREATE / UPDATE PROFILE
# ══════════════════════════════════════════════════════════════════

@mentors_bp.route("/api/mentor/profile", methods=["POST"])
def api_create_or_update_profile():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    display_name = (data.get("display_name") or "").strip()
    if not display_name:
        return jsonify({"ok": False, "error": "Görünen ad gerekli"}), 400

    try:
        profile = me.create_or_update_profile(
            user_id=uid,
            display_name=display_name,
            headline=data.get("headline", ""),
            bio=data.get("bio", ""),
            experience_years=int(data.get("experience_years", 0)),
            markets=data.get("markets", ""),
            specialties=data.get("specialties", ""),
            languages=data.get("languages", "Türkçe"),
            pricing_model=data.get("pricing_model", "free"),
            monthly_price=float(data.get("monthly_price", 0.0)),
        )
        return jsonify({"ok": True, "profile": profile})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# API — FOLLOW / UNFOLLOW
# ══════════════════════════════════════════════════════════════════

@mentors_bp.route("/api/mentor/follow", methods=["POST"])
def api_follow_mentor():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    mentor_user_id = data.get("mentor_user_id")
    if not mentor_user_id:
        return jsonify({"ok": False, "error": "mentor_user_id gerekli"}), 400

    try:
        me.follow_mentor(uid, mentor_user_id)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@mentors_bp.route("/api/mentor/unfollow", methods=["POST"])
def api_unfollow_mentor():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    mentor_user_id = data.get("mentor_user_id")
    if not mentor_user_id:
        return jsonify({"ok": False, "error": "mentor_user_id gerekli"}), 400

    me.unfollow_mentor(uid, mentor_user_id)
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════
# COPILOT — MENTORS
# ══════════════════════════════════════════════════════════════════

@mentors_bp.route("/api/copilot/mentors", methods=["POST"])
def api_copilot_mentors():
    if COMING_SOON:
        return _coming_soon_response()
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Soru gerekli"}), 400

    featured = me.featured_mentors(limit=10)
    context_parts = ["ÖNE ÇIKAN MENTORLAR:"]
    for m in featured:
        context_parts.append(
            f"  - {m.get('display_name','?')} (@{m.get('username','?')}): "
            f"{m.get('headline','')}, markets={m.get('markets','')}, "
            f"specialties={m.get('specialties','')}, "
            f"followers={m.get('followers_count',0)}, "
            f"experience={m.get('experience_years',0)} yıl, "
            f"pricing={m.get('pricing_model','free')}"
        )
    context_text = "\n".join(context_parts)

    try:
        from app.core.copilot_service import _SYSTEM_BASE, _call_llm, DEFAULT_MODEL
        _MENTOR_PROMPT = (
            "\nBu yanıtı ZKR Analiz Mentor/Analizci sistemi için veriyorsun.\n"
            "Context'te öne çıkan mentorlar, uzmanlık alanları ve takipçi verileri var.\n"
            "En iyi mentorları, uzmanlık alanlarını ve takip önerilerini değerlendir.\n"
        )
        system = _SYSTEM_BASE + _MENTOR_PROMPT
        prompt = f"[CONTEXT]\n{context_text}\n\n[KULLANICI SORUSU]\n{question}\n\nassistant:"
        result = _call_llm(DEFAULT_MODEL, system, prompt, {"mentors": context_text})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        _logger.warning("Copilot mentors error: %s", e)
        return jsonify({
            "ok": True,
            "data": {
                "answer": f"Şu anda {len(featured)} öne çıkan mentor var.",
                "summary": "Mentor sistemi özeti",
                "key_points": [f"{len(featured)} aktif mentor"],
                "risk_points": [],
                "suggested_alerts": [],
            }
        })
