"""Canlı Mentoring Odaları - İzole WebSocket Amfitiyatrosu

STEP 4: Interactive Mentor Amphitheater
- Her mentor kendi canlı yayın odasını oluşturabilir
- Viewers odaya bağlanıp mesaj gönderebilir
- WebSocket olayları SADECE o oda'ya emit edilir
- Ana fiyat yayını (price_update_batch) hiçbir zaman bozulmaz
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify
from datetime import datetime
from ..extensions import db, socketio
from ..models import User, LiveRoom, RoomMessage, RoomStatus
import uuid
import logging

logger = logging.getLogger(__name__)

live_bp = Blueprint("live", __name__, url_prefix="/api/live")


@live_bp.route("/create-room", methods=["POST"])
def create_room():
    """POST /api/live/create-room
    
    Yeni canlı mentoring odası oluştur.
    
    Body:
    {
        "user_id": 1,
        "title": "Bitcoin Analiz - 15 Dakika"
    }
    
    Response:
    {
        "room_id": 1,
        "mentor_id": 1,
        "title": "Bitcoin Analiz - 15 Dakika",
        "stream_key": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "status": "SCHEDULED",
        "viewer_count": 0,
        "created_at": "2026-06-22T15:00:00Z"
    }
    """
    try:
        data = request.get_json()
        
        # Input validation
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400
        
        user_id = data.get("user_id")
        title = data.get("title", "").strip()
        
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        
        if not title:
            return jsonify({"error": "title required"}), 400
        
        # Kullanıcı kontrol et
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": f"User {user_id} not found"}), 404
        
        # Stream key üret (UUID4)
        stream_key = str(uuid.uuid4())
        
        # Yeni oda oluştur
        room = LiveRoom(
            mentor_id=user_id,
            title=title,
            stream_key=stream_key,
            status=RoomStatus.SCHEDULED,
            viewer_count=0
        )
        
        db.session.add(room)
        db.session.commit()
        
        logger.info(f"[LIVE] Room created: id={room.id} mentor_id={user_id} stream_key={stream_key}")
        
        return jsonify({
            "room_id": room.id,
            "mentor_id": room.mentor_id,
            "title": room.title,
            "stream_key": room.stream_key,
            "status": room.status.value,
            "viewer_count": room.viewer_count,
            "created_at": room.created_at.isoformat() + "Z"
        }), 201
    
    except Exception as e:
        logger.error(f"[LIVE] Error creating room: {e}")
        return jsonify({"error": str(e)}), 500


@live_bp.route("/rooms", methods=["GET"])
def get_rooms():
    """GET /api/live/rooms
    
    LIVE veya SCHEDULED statüsündeki odaları listele.
    
    Query Parameters:
    - status: LIVE, SCHEDULED, ENDED (optional)
    - limit: 1-200 (default 50)
    - offset: default 0
    
    Response:
    {
        "total": 5,
        "count": 2,
        "limit": 50,
        "offset": 0,
        "rooms": [
            {
                "room_id": 1,
                "mentor": {"id": 1, "username": "mentor1"},
                "title": "Bitcoin Analiz",
                "status": "LIVE",
                "viewer_count": 45,
                "created_at": "2026-06-22T15:00:00Z",
                "started_at": "2026-06-22T15:05:00Z"
            }
        ]
    }
    """
    try:
        status_param = request.args.get("status", "").upper()
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))
        
        query = LiveRoom.query
        
        # Statüs filtresi
        if status_param:
            try:
                status_enum = RoomStatus[status_param]
                query = query.filter_by(status=status_enum)
            except KeyError:
                return jsonify({"error": f"Invalid status: {status_param}"}), 400
        else:
            # Default: LIVE ve SCHEDULED
            query = query.filter(LiveRoom.status.in_([RoomStatus.LIVE, RoomStatus.SCHEDULED]))
        
        total = query.count()
        rooms_data = query.order_by(LiveRoom.created_at.desc()).limit(limit).offset(offset).all()
        
        rooms_list = []
        for room in rooms_data:
            rooms_list.append({
                "room_id": room.id,
                "mentor": {
                    "id": room.mentor_id,
                    "username": room.mentor.username if room.mentor else "Unknown"
                },
                "title": room.title,
                "status": room.status.value,
                "viewer_count": room.viewer_count,
                "created_at": room.created_at.isoformat() + "Z",
                "started_at": room.started_at.isoformat() + "Z" if room.started_at else None
            })
        
        return jsonify({
            "total": total,
            "count": len(rooms_list),
            "limit": limit,
            "offset": offset,
            "rooms": rooms_list
        }), 200
    
    except Exception as e:
        logger.error(f"[LIVE] Error fetching rooms: {e}")
        return jsonify({"error": str(e)}), 500


@live_bp.route("/room/<int:room_id>", methods=["GET"])
def get_room_details(room_id):
    """GET /api/live/room/<room_id>
    
    Oda detaylarını ve son 50 mesajı dök.
    
    Response:
    {
        "room_id": 1,
        "mentor": {"id": 1, "username": "mentor1"},
        "title": "Bitcoin Analiz",
        "stream_key": "a1b2c3d4-...",
        "status": "LIVE",
        "viewer_count": 45,
        "created_at": "2026-06-22T15:00:00Z",
        "started_at": "2026-06-22T15:05:00Z",
        "ended_at": null,
        "messages": [
            {
                "message_id": 1,
                "sender": {"id": 2, "username": "viewer1"},
                "content": "Harika analiz!",
                "created_at": "2026-06-22T15:30:00Z"
            }
        ]
    }
    """
    try:
        room = LiveRoom.query.filter_by(id=room_id).first()
        if not room:
            return jsonify({"error": f"Room {room_id} not found"}), 404
        
        # Son 50 mesajı al (en yeni sırada)
        messages = room.messages.order_by(RoomMessage.created_at.desc()).limit(50).all()
        messages.reverse()  # En eski ilk, en yeni son
        
        messages_list = []
        for msg in messages:
            messages_list.append({
                "message_id": msg.id,
                "sender": {
                    "id": msg.sender_id,
                    "username": msg.sender.username if msg.sender else "Unknown"
                },
                "content": msg.content,
                "created_at": msg.created_at.isoformat() + "Z"
            })
        
        return jsonify({
            "room_id": room.id,
            "mentor": {
                "id": room.mentor_id,
                "username": room.mentor.username if room.mentor else "Unknown"
            },
            "title": room.title,
            "stream_key": room.stream_key,
            "status": room.status.value,
            "viewer_count": room.viewer_count,
            "created_at": room.created_at.isoformat() + "Z",
            "started_at": room.started_at.isoformat() + "Z" if room.started_at else None,
            "ended_at": room.ended_at.isoformat() + "Z" if room.ended_at else None,
            "messages": messages_list
        }), 200
    
    except Exception as e:
        logger.error(f"[LIVE] Error fetching room details: {e}")
        return jsonify({"error": str(e)}), 500
