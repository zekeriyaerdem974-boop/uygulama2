"""WebSocket Event Handlers - İzole Canlı Oda Namespace'leri

STEP 4: Interactive Mentor Amphitheater - WebSocket Layer
- join_live_room: Viewer odaya bağlanır, viewer_count +1
- leave_live_room: Viewer odadan ayrılır, viewer_count -1
- send_room_message: Mesaj SADECE o oda'ya emit edilir
- ASLA ana price_update_batch broadcast'ini bozmaz

Her oda kendi izole Socket.IO room'una sahiptir:
  - room_{room_id} → messages ve events SADECE burada emit edilir
  - Hiçbir cross-room contamination
  - Main broadcast (price_update_batch) hiçbir zaman etkilenmez
"""
from __future__ import annotations

from flask import request
from flask_socketio import join_room, leave_room, emit
from datetime import datetime
from .extensions import socketio, db
from .models import LiveRoom, RoomMessage, User
import logging

logger = logging.getLogger(__name__)


@socketio.on("join_live_room")
def on_join_live_room(data, *args, **kwargs):
    """Viewer canlı odaya bağlan
    
    Client data:
    {
        "room_id": 1,
        "user_id": 2
    }
    
    Actions:
    1. Socket'i room_{room_id} Socket.IO room'una ekle
    2. viewer_count +1 yap ve veritabanında güncelle
    3. O oda'ya viewer_count_updated emit et
    """
    try:
        if not data:
            emit("error", {"message": "No data provided"})
            return
        
        room_id = data.get("room_id")
        user_id = data.get("user_id")
        
        if not room_id or not user_id:
            emit("error", {"message": "room_id and user_id required"})
            return
        
        # Oda var mı kontrol et
        room = LiveRoom.query.filter_by(id=room_id).first()
        if not room:
            emit("error", {"message": f"Room {room_id} not found"})
            return
        
        # Kullanıcı var mı kontrol et
        user = User.query.filter_by(id=user_id).first()
        if not user:
            emit("error", {"message": f"User {user_id} not found"})
            return
        
        # Socket.IO room'a ekle (izole namespace)
        socket_room = f"room_{room_id}"
        join_room(socket_room)
        
        # Viewer count'u +1 yap
        room.viewer_count += 1
        db.session.commit()
        
        logger.info(f"[LIVE] User {user.username} joined room {room_id}, new viewer_count={room.viewer_count}")
        
        # Bu oda'ya viewer_count_updated emit et (SADECE bu oda'daki clients)
        emit(
            "viewer_count_updated",
            {
                "room_id": room_id,
                "viewer_count": room.viewer_count,
                "username": user.username,
                "message": f"{user.username} odaya bağlandı"
            },
            to=socket_room
        )
    
    except Exception as e:
        logger.error(f"[LIVE] Error in on_join_live_room: {e}")
        emit("error", {"message": str(e)})


@socketio.on("leave_live_room")
def on_leave_live_room(data, *args, **kwargs):
    """Viewer canlı odadan ayrıl
    
    Client data:
    {
        "room_id": 1,
        "user_id": 2
    }
    
    Actions:
    1. Socket'i room_{room_id} room'undan çıkar
    2. viewer_count -1 yap ve veritabanında güncelle
    3. O oda'ya viewer_count_updated emit et
    """
    try:
        if not data:
            emit("error", {"message": "No data provided"})
            return
        
        room_id = data.get("room_id")
        user_id = data.get("user_id")
        
        if not room_id or not user_id:
            emit("error", {"message": "room_id and user_id required"})
            return
        
        # Oda var mı kontrol et
        room = LiveRoom.query.filter_by(id=room_id).first()
        if not room:
            emit("error", {"message": f"Room {room_id} not found"})
            return
        
        # Kullanıcı var mı kontrol et
        user = User.query.filter_by(id=user_id).first()
        username = user.username if user else f"User{user_id}"
        
        # Socket.IO room'undan çıkar
        socket_room = f"room_{room_id}"
        leave_room(socket_room)
        
        # Viewer count'u -1 yap (minimum 0)
        if room.viewer_count > 0:
            room.viewer_count -= 1
        db.session.commit()
        
        logger.info(f"[LIVE] User {username} left room {room_id}, new viewer_count={room.viewer_count}")
        
        # Bu oda'ya viewer_count_updated emit et (SADECE bu oda'daki clients)
        emit(
            "viewer_count_updated",
            {
                "room_id": room_id,
                "viewer_count": room.viewer_count,
                "username": username,
                "message": f"{username} odadan ayrıldı"
            },
            to=socket_room
        )
    
    except Exception as e:
        logger.error(f"[LIVE] Error in on_leave_live_room: {e}")
        emit("error", {"message": str(e)})


@socketio.on("send_room_message")
def on_send_room_message(data, *args, **kwargs):
    """Canlı oda'ya mesaj gönder
    
    Client data:
    {
        "room_id": 1,
        "user_id": 2,
        "content": "Merhaba herkese!"
    }
    
    Actions:
    1. RoomMessage tablosuna mesajı kaydet
    2. SADECE o oda'ya (room_{room_id}) new_room_message emit et
    3. Ana broadcast'e hiçbir şey emit etme
    
    ⚠️ KRİTİK: Ana price_update_batch kesinlikle bozulmasın!
    """
    try:
        if not data:
            emit("error", {"message": "No data provided"})
            return
        
        room_id = data.get("room_id")
        user_id = data.get("user_id")
        content = data.get("content", "").strip()
        
        if not room_id or not user_id:
            emit("error", {"message": "room_id and user_id required"})
            return
        
        if not content:
            emit("error", {"message": "Message content required"})
            return
        
        # Oda var mı kontrol et
        room = LiveRoom.query.filter_by(id=room_id).first()
        if not room:
            emit("error", {"message": f"Room {room_id} not found"})
            return
        
        # Kullanıcı var mı kontrol et
        user = User.query.filter_by(id=user_id).first()
        if not user:
            emit("error", {"message": f"User {user_id} not found"})
            return
        
        # Mesajı veritabanına kaydet
        message = RoomMessage(
            room_id=room_id,
            sender_id=user_id,
            content=content,
            created_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()
        
        logger.info(f"[LIVE] Message in room {room_id} from user {user.username}: {content[:50]}...")
        
        # SADECE bu oda'ya mesajı emit et
        # to=f"room_{room_id}" — diğer odalara bir şey gitmez
        # Ana broadcast'a müdahale yok
        socket_room = f"room_{room_id}"
        emit(
            "new_room_message",
            {
                "message_id": message.id,
                "room_id": room_id,
                "sender": {
                    "id": user.id,
                    "username": user.username
                },
                "content": content,
                "created_at": message.created_at.isoformat() + "Z"
            },
            to=socket_room
        )
        
        # Gönderene confirmation
        emit("message_sent", {"message_id": message.id, "status": "ok"})
    
    except Exception as e:
        logger.error(f"[LIVE] Error in on_send_room_message: {e}")
        emit("error", {"message": str(e)})


@socketio.on("connect", namespace="/live")
def on_connect_live(*args, **kwargs):
    """Canlı namespace'ine bağlan"""
    logger.info(f"[LIVE] WebSocket client connected to /live namespace")
    emit("connect_response", {"status": "connected to /live"})


@socketio.on("disconnect", namespace="/live")
def on_disconnect_live(*args, **kwargs):
    """Canlı namespace'inden ayrıl"""
    logger.info(f"[LIVE] WebSocket client disconnected from /live namespace")
