# -*- coding: utf-8 -*-
"""Live Trading Rooms API routes — FAZ 34.

Endpoints:
  GET  /api/rooms                  — List rooms
  GET  /api/room/<slug>            — Room detail
  POST /api/room                   — Create room
  POST /api/room/<id>/start        — Start room (go live)
  POST /api/room/<id>/stop         — Stop room
  POST /api/room/<id>/join         — Join room
  POST /api/room/<id>/leave        — Leave room
  GET  /api/room/<id>/messages     — List messages
  POST /api/room/<id>/message      — Post message

Pages:
  GET  /rooms                      — Rooms listing page
  GET  /room/<slug>                — Room detail page

Copilot:
  POST /api/copilot/rooms          — Copilot rooms Q&A
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.live_rooms import live_rooms_bp
from app.core import live_room_engine as lre

_logger = logging.getLogger("zkr_analiz.live_rooms.routes")

# ── FAZ 62: Feature Lock ─────────────────────────────────────────
COMING_SOON = True


def _coming_soon_response():
    return jsonify({"ok": False, "coming_soon": True, "message": "Canlı odalar yakında geliyor"}), 503


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


def _require_mentor(uid):
    try:
        from app.core.mentor_engine import is_mentor
        if not is_mentor(uid):
            return jsonify({"ok": False, "error": "Mentor profiliniz bulunmuyor"}), 403
    except Exception:
        return jsonify({"ok": False, "error": "Mentor sistemi erişilemiyor"}), 500
    return None


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@live_rooms_bp.route("/rooms")
def rooms_page():
    return render_template("rooms.html", coming_soon=COMING_SOON)


@live_rooms_bp.route("/room/<slug>")
def room_detail_page(slug):
    return render_template("room_detail.html", room_slug=slug, coming_soon=COMING_SOON)


# ══════════════════════════════════════════════════════════════════
# API — LIST & DETAIL
# ══════════════════════════════════════════════════════════════════

@live_rooms_bp.route("/api/rooms")
def api_list_rooms():
    if COMING_SOON:
        return _coming_soon_response()
    market = request.args.get("market")
    active_only = request.args.get("active") == "1"
    mentor = request.args.get("mentor_user_id")
    sort = request.args.get("sort", "active")
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = int(request.args.get("offset", 0))
    search = request.args.get("search")

    rooms = lre.list_rooms(
        market=market, active_only=active_only,
        mentor_user_id=mentor, sort=sort, limit=limit,
        offset=offset, search=search,
    )
    return jsonify({"ok": True, "rooms": rooms, "count": len(rooms)})


@live_rooms_bp.route("/api/room/<slug>")
def api_room_detail(slug):
    if COMING_SOON:
        return _coming_soon_response()
    uid = session.get("user_id")
    room = lre.get_room(slug, viewer_id=uid)
    if not room:
        return jsonify({"ok": False, "error": "Oda bulunamadı"}), 404

    participants = lre.get_participants(room["id"])
    messages = lre.list_messages(room["id"], limit=50)

    return jsonify({
        "ok": True,
        "room": room,
        "participants": participants,
        "messages": messages,
    })


# ══════════════════════════════════════════════════════════════════
# API — CREATE / START / STOP
# ══════════════════════════════════════════════════════════════════

@live_rooms_bp.route("/api/room", methods=["POST"])
def api_create_room():
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err
    merr = _require_mentor(uid)
    if merr:
        return merr

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Oda başlığı gerekli"}), 400

    try:
        room = lre.create_room(
            mentor_user_id=uid,
            title=title,
            description=data.get("description", ""),
            market=data.get("market", ""),
            visibility=data.get("visibility", "public"),
        )
        return jsonify({"ok": True, "room": room})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@live_rooms_bp.route("/api/room/<room_id>/start", methods=["POST"])
def api_start_room(room_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    try:
        room = lre.start_room(room_id, uid)
        # Broadcast system message to WebSocket clients
        lre.ws_broadcast(room_id, {
            "type": "system",
            "content": "Canlı yayın başladı!",
            "room_active": True,
        })
        return jsonify({"ok": True, "room": room})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@live_rooms_bp.route("/api/room/<room_id>/stop", methods=["POST"])
def api_stop_room(room_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    try:
        room = lre.stop_room(room_id, uid)
        lre.ws_broadcast(room_id, {
            "type": "system",
            "content": "Canlı yayın sona erdi.",
            "room_active": False,
        })
        return jsonify({"ok": True, "room": room})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# API — JOIN / LEAVE
# ══════════════════════════════════════════════════════════════════

@live_rooms_bp.route("/api/room/<room_id>/join", methods=["POST"])
def api_join_room(room_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    # FAZ 36 — premium room access check
    room = lre.get_room_by_id(room_id)
    if room and room.get("visibility") in ("subscribers_only",):
        from app.core.subscription_engine import can_access_premium_room
        check = can_access_premium_room(uid)
        if not check["allowed"]:
            return jsonify({"ok": False, "error": check["reason"], "upgrade_required": True, "required_plan": check.get("required_plan"), "locked": True}), 403

    try:
        participant = lre.join_room(room_id, uid)
        username = lre._get_username(uid)
        lre.ws_broadcast(room_id, {
            "type": "user_joined",
            "user_id": uid,
            "username": username,
        })
        return jsonify({"ok": True, "participant": participant})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@live_rooms_bp.route("/api/room/<room_id>/leave", methods=["POST"])
def api_leave_room(room_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    try:
        lre.leave_room(room_id, uid)
        username = lre._get_username(uid)
        lre.ws_broadcast(room_id, {
            "type": "user_left",
            "user_id": uid,
            "username": username,
        })
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# API — MESSAGES
# ══════════════════════════════════════════════════════════════════

@live_rooms_bp.route("/api/room/<room_id>/messages")
def api_list_messages(room_id):
    if COMING_SOON:
        return _coming_soon_response()
    limit = min(int(request.args.get("limit", 50)), 200)
    before = request.args.get("before")
    messages = lre.list_messages(room_id, limit=limit, before=before)
    return jsonify({"ok": True, "messages": messages, "count": len(messages)})


@live_rooms_bp.route("/api/room/<room_id>/message", methods=["POST"])
def api_post_message(room_id):
    if COMING_SOON:
        return _coming_soon_response()
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "Mesaj içeriği gerekli"}), 400

    message_type = data.get("message_type", "text")

    try:
        msg = lre.post_message(
            room_id=room_id,
            user_id=uid,
            content=content,
            message_type=message_type,
        )
        # Broadcast to WebSocket clients
        lre.ws_broadcast(room_id, {
            "type": "new_message",
            "message": msg,
        })
        return jsonify({"ok": True, "message": msg})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ══════════════════════════════════════════════════════════════════
# COPILOT — ROOMS
# ══════════════════════════════════════════════════════════════════

@live_rooms_bp.route("/api/copilot/rooms", methods=["POST"])
def api_copilot_rooms():
    if COMING_SOON:
        return _coming_soon_response()
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Soru gerekli"}), 400

    active_rooms = lre.list_rooms(active_only=True, limit=20)
    stats = lre.room_stats()

    context_parts = [
        f"CANLI ODA İSTATİSTİKLERİ: {stats['total_rooms']} oda, {stats['active_rooms']} aktif, "
        f"{stats['total_participants']} katılımcı, {stats['total_mentors']} mentor",
        "AKTİF ODALAR:",
    ]
    for r in active_rooms:
        context_parts.append(
            f"  - {r.get('title','?')} (mentor: {r.get('mentor_display_name','?')}): "
            f"market={r.get('market','')}, participants={r.get('participant_count',0)}"
        )
    context_text = "\n".join(context_parts)

    try:
        from app.core.copilot_service import _SYSTEM_BASE, _call_llm, DEFAULT_MODEL
        _ROOM_PROMPT = (
            "\nBu yanıtı ZKR Analiz Canlı Analiz Odaları sistemi için veriyorsun.\n"
            "Context'te aktif odalar, mentor bilgileri ve katılımcı sayıları var.\n"
            "Kullanıcıya en uygun odaları ve mentorları öner.\n"
        )
        system = _SYSTEM_BASE + _ROOM_PROMPT
        prompt = f"[CONTEXT]\n{context_text}\n\n[KULLANICI SORUSU]\n{question}\n\nassistant:"
        result = _call_llm(DEFAULT_MODEL, system, prompt, {"rooms": context_text})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        _logger.warning("Copilot rooms error: %s", e)
        return jsonify({
            "ok": True,
            "data": {
                "answer": f"Şu anda {stats['active_rooms']} aktif canlı oda var, toplam {stats['total_participants']} katılımcı.",
                "summary": "Canlı oda sistemi özeti",
                "key_points": [f"{stats['active_rooms']} aktif oda"],
                "risk_points": [],
                "suggested_alerts": [],
            }
        })
