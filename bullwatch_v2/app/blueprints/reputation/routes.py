# -*- coding: utf-8 -*-
"""Reputation / Rating / Trust API routes — FAZ 35.

Endpoints:
  POST /api/rate/mentor             — Rate a mentor
  POST /api/rate/course             — Rate a course
  POST /api/rate/strategy           — Rate a strategy
  GET  /api/ratings/mentor/<uid>    — Get mentor ratings
  GET  /api/ratings/course/<cid>    — Get course ratings
  GET  /api/ratings/strategy/<sid>  — Get strategy ratings
  GET  /api/reputation/<user_id>    — Get user reputation
  POST /api/reputation/calculate    — Recalculate own reputation
  GET  /api/reputation/top-analysts — Top analysts
  GET  /api/reputation/top-mentors  — Top mentors
  GET  /api/reputation/top-strategies — Top strategy creators
  GET  /api/reputation/badges       — Badge definitions

Copilot:
  POST /api/copilot/reputation      — Copilot reputation Q&A
"""
from __future__ import annotations

import logging

from flask import jsonify, request, session

from app.blueprints.reputation import reputation_bp
from app.core import reputation_engine as re

_logger = logging.getLogger("zkr_analiz.reputation.routes")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


# ══════════════════════════════════════════════════════════════════
# RATING ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@reputation_bp.route("/api/rate/mentor", methods=["POST"])
def api_rate_mentor():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    mentor_user_id = data.get("mentor_user_id")
    rating = data.get("rating")
    review = data.get("review", "")

    if not mentor_user_id:
        return jsonify({"ok": False, "error": "mentor_user_id gerekli"}), 400

    try:
        result = re.rate_mentor(uid, mentor_user_id, int(rating), str(review))
        # Recalculate mentor reputation after rating
        re.calculate_user_score(mentor_user_id)
        return jsonify({"ok": True, "rating": result})
    except (ValueError, TypeError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@reputation_bp.route("/api/rate/course", methods=["POST"])
def api_rate_course():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id")
    rating = data.get("rating")
    review = data.get("review", "")

    if not course_id:
        return jsonify({"ok": False, "error": "course_id gerekli"}), 400

    try:
        result = re.rate_course(uid, course_id, int(rating), str(review))
        return jsonify({"ok": True, "rating": result})
    except (ValueError, TypeError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@reputation_bp.route("/api/rate/strategy", methods=["POST"])
def api_rate_strategy():
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    strategy_id = data.get("strategy_id")
    rating = data.get("rating")
    review = data.get("review", "")

    if not strategy_id:
        return jsonify({"ok": False, "error": "strategy_id gerekli"}), 400

    try:
        result = re.rate_strategy(uid, strategy_id, int(rating), str(review))
        return jsonify({"ok": True, "rating": result})
    except (ValueError, TypeError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# QUERY ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@reputation_bp.route("/api/ratings/mentor/<mentor_user_id>")
def api_get_mentor_ratings(mentor_user_id):
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    ratings = re.get_mentor_ratings(mentor_user_id, limit, offset)
    avg = re.get_mentor_avg_rating(mentor_user_id)
    return jsonify({"ok": True, "ratings": ratings, **avg})


@reputation_bp.route("/api/ratings/course/<course_id>")
def api_get_course_ratings(course_id):
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    ratings = re.get_course_ratings(course_id, limit, offset)
    avg = re.get_course_avg_rating(course_id)
    return jsonify({"ok": True, "ratings": ratings, **avg})


@reputation_bp.route("/api/ratings/strategy/<strategy_id>")
def api_get_strategy_ratings(strategy_id):
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    ratings = re.get_strategy_ratings(strategy_id, limit, offset)
    avg = re.get_strategy_avg_rating(strategy_id)
    return jsonify({"ok": True, "ratings": ratings, **avg})


@reputation_bp.route("/api/reputation/<user_id>")
def api_get_reputation(user_id):
    rep = re.get_reputation(user_id)
    if not rep:
        # Calculate it on-demand
        rep = re.calculate_user_score(user_id)
    return jsonify({"ok": True, "reputation": rep})


@reputation_bp.route("/api/reputation/calculate", methods=["POST"])
def api_calculate_reputation():
    uid, err = _require_login()
    if err:
        return err
    rep = re.calculate_user_score(uid)
    return jsonify({"ok": True, "reputation": rep})


@reputation_bp.route("/api/reputation/top-analysts")
def api_top_analysts():
    limit = min(int(request.args.get("limit", 10)), 50)
    analysts = re.list_top_analysts(limit)
    return jsonify({"ok": True, "analysts": analysts})


@reputation_bp.route("/api/reputation/top-mentors")
def api_top_mentors():
    limit = min(int(request.args.get("limit", 10)), 50)
    mentors = re.list_top_mentors(limit)
    return jsonify({"ok": True, "mentors": mentors})


@reputation_bp.route("/api/reputation/top-strategies")
def api_top_strategies():
    limit = min(int(request.args.get("limit", 10)), 50)
    strategies = re.list_top_strategies(limit)
    return jsonify({"ok": True, "strategies": strategies})


@reputation_bp.route("/api/reputation/badges")
def api_badges():
    return jsonify({"ok": True, "badges": re.BADGE_DEFS})


# ══════════════════════════════════════════════════════════════════
# COPILOT — REPUTATION
# ══════════════════════════════════════════════════════════════════

@reputation_bp.route("/api/copilot/reputation", methods=["POST"])
def api_copilot_reputation():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Soru gerekli"}), 400

    stats = re.reputation_stats()
    top_analysts = re.list_top_analysts(5)
    top_mentors = re.list_top_mentors(5)

    context_parts = [
        f"REPUTATION İSTATİSTİKLERİ: {stats['total_users_rated']} kullanıcı puanlandı, "
        f"{stats['mentor_ratings_count']} mentor puanı, "
        f"{stats['course_ratings_count']} kurs puanı, "
        f"{stats['strategy_ratings_count']} strateji puanı, "
        f"ortalama skor: {stats['avg_reputation_score']}",
        "EN İYİ ANALİZCİLER:",
    ]
    for a in top_analysts:
        context_parts.append(
            f"  - @{a.get('username','?')}: score={a.get('score',0)}, "
            f"trust={a.get('trust_level','?')}, badges={a.get('badges',[])}"
        )
    context_parts.append("EN İYİ MENTORLAR:")
    for m in top_mentors:
        context_parts.append(
            f"  - @{m.get('username','?')}: mentor_rating={m.get('mentor_rating',0)}, "
            f"score={m.get('score',0)}"
        )
    context_text = "\n".join(context_parts)

    try:
        from app.core.copilot_service import _SYSTEM_BASE, _call_llm, DEFAULT_MODEL
        _REP_PROMPT = (
            "\nBu yanıtı ZKR Analiz Reputation/Rating sistemi için veriyorsun.\n"
            "Context'te en iyi analizciler, mentorlar ve istatistikler var.\n"
            "En güvenilir analizcileri ve mentorları öner.\n"
        )
        system = _SYSTEM_BASE + _REP_PROMPT
        prompt = f"[CONTEXT]\n{context_text}\n\n[KULLANICI SORUSU]\n{question}\n\nassistant:"
        result = _call_llm(DEFAULT_MODEL, system, prompt, {"reputation": context_text})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        _logger.warning("Copilot reputation error: %s", e)
        return jsonify({
            "ok": True,
            "data": {
                "answer": f"Şu anda {stats['total_users_rated']} kullanıcı puanlandı, "
                          f"{stats['mentor_ratings_count']} mentor puanı verilmiş.",
                "summary": "Reputation sistemi özeti",
                "key_points": [
                    f"{stats['total_users_rated']} puanlı kullanıcı",
                    f"Ortalama skor: {stats['avg_reputation_score']}",
                ],
                "risk_points": [],
                "suggested_alerts": [],
            }
        })
