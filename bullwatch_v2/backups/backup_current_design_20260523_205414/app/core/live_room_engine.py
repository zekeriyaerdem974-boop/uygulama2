# -*- coding: utf-8 -*-
"""Live Trading Rooms Engine — FAZ 34.

SQLite-backed live room, chat & participant system.

Public API:
  create_room(...)                → dict
  update_room(...)                → dict
  start_room(room_id, uid)        → dict
  stop_room(room_id, uid)         → dict
  list_rooms(...)                 → list[dict]
  get_room(slug, viewer_id)       → dict | None
  get_room_by_id(room_id)         → dict | None
  join_room(room_id, uid)         → dict
  leave_room(room_id, uid)        → bool
  post_message(...)               → dict
  list_messages(room_id, ...)     → list[dict]
  get_mentor_rooms(mentor_uid)    → list[dict]
  room_stats()                    → dict
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

_logger = logging.getLogger("zkr_analiz.live_rooms")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "live_rooms.db")
_USERS_DB = os.path.join(_DB_DIR, "users.db")

_lock = threading.Lock()

VALID_MARKETS = {"crypto", "stocks", "bist", "forex", "commodities"}
VALID_VISIBILITY = {"public", "followers_only", "subscribers_only"}
VALID_MESSAGE_TYPES = {"text", "signal", "chart_share", "system"}
VALID_ROLES = {"mentor", "moderator", "member"}


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("live_rooms.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS live_rooms (
            id              TEXT PRIMARY KEY,
            mentor_user_id  TEXT NOT NULL,
            title           TEXT NOT NULL,
            slug            TEXT NOT NULL UNIQUE,
            description     TEXT,
            market          TEXT NOT NULL DEFAULT '',
            is_active       INTEGER NOT NULL DEFAULT 0,
            visibility      TEXT NOT NULL DEFAULT 'public',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS room_messages (
            id              TEXT PRIMARY KEY,
            room_id         TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            message_type    TEXT NOT NULL DEFAULT 'text',
            content         TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES live_rooms(id)
        );

        CREATE TABLE IF NOT EXISTS room_participants (
            id              TEXT PRIMARY KEY,
            room_id         TEXT NOT NULL,
            user_id         TEXT NOT NULL,
            role            TEXT NOT NULL DEFAULT 'member',
            joined_at       TEXT NOT NULL,
            UNIQUE(room_id, user_id),
            FOREIGN KEY (room_id) REFERENCES live_rooms(id)
        );

        CREATE INDEX IF NOT EXISTS idx_lr_mentor ON live_rooms(mentor_user_id);
        CREATE INDEX IF NOT EXISTS idx_lr_slug ON live_rooms(slug);
        CREATE INDEX IF NOT EXISTS idx_lr_active ON live_rooms(is_active);
        CREATE INDEX IF NOT EXISTS idx_lr_market ON live_rooms(market);
        CREATE INDEX IF NOT EXISTS idx_rm_room ON room_messages(room_id);
        CREATE INDEX IF NOT EXISTS idx_rm_created ON room_messages(room_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_rp_room ON room_participants(room_id);
        CREATE INDEX IF NOT EXISTS idx_rp_user ON room_participants(user_id);
    """)


def _init_db():
    conn = _get_conn()
    try:
        _ensure_tables(conn)
    finally:
        conn.close()


_init_db()


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())[:12]


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _get_username(user_id: str) -> str:
    if not os.path.exists(_USERS_DB):
        return "Anonim"
    try:
        conn = sqlite3.connect(_USERS_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return row["username"] if row else "Anonim"
    except Exception:
        return "Anonim"


def _make_slug(title: str, existing_id: str | None = None) -> str:
    """Generate a URL-friendly slug from title."""
    slug = title.lower().strip()
    tr_map = {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
              "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u"}
    for k, v in tr_map.items():
        slug = slug.replace(k, v)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    if not slug:
        slug = "oda"
    conn = _get_conn()
    try:
        base = slug
        counter = 1
        while True:
            row = conn.execute("SELECT id FROM live_rooms WHERE slug = ?", (slug,)).fetchone()
            if not row or (existing_id and row["id"] == existing_id):
                break
            slug = f"{base}-{counter}"
            counter += 1
        return slug
    finally:
        conn.close()


def _enrich_room(room: dict) -> dict:
    """Add computed fields: mentor name, participant count."""
    room["mentor_username"] = _get_username(room["mentor_user_id"])
    room["mentor_display_name"] = room["mentor_username"]
    try:
        from app.core.mentor_engine import get_profile_by_user_id
        mp = get_profile_by_user_id(room["mentor_user_id"])
        if mp:
            room["mentor_display_name"] = mp.get("display_name", room["mentor_username"])
    except Exception:
        pass
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM room_participants WHERE room_id = ?",
            (room["id"],)
        ).fetchone()
        room["participant_count"] = row["c"] if row else 0
    finally:
        conn.close()
    return room


# ══════════════════════════════════════════════════════════════════
# ROOM CRUD
# ══════════════════════════════════════════════════════════════════

def create_room(
    mentor_user_id: str,
    title: str,
    description: str = "",
    market: str = "",
    visibility: str = "public",
) -> dict:
    if not title or not title.strip():
        raise ValueError("Oda başlığı gerekli")
    if market and market not in VALID_MARKETS:
        raise ValueError(f"Geçersiz market: {market}")
    if visibility not in VALID_VISIBILITY:
        visibility = "public"

    slug = _make_slug(title)
    now = _now_iso()
    room_id = _gen_id()

    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT INTO live_rooms
                    (id, mentor_user_id, title, slug, description, market,
                     is_active, visibility, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """, (room_id, mentor_user_id, title.strip(), slug,
                  description.strip(), market, visibility, now, now))
            # Auto-join mentor as mentor role
            conn.execute("""
                INSERT INTO room_participants (id, room_id, user_id, role, joined_at)
                VALUES (?, ?, ?, 'mentor', ?)
            """, (_gen_id(), room_id, mentor_user_id, now))
            conn.commit()

            row = conn.execute("SELECT * FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            result = _enrich_room(_row_to_dict(row))
            _logger.info("Room created: %s by %s", room_id, mentor_user_id)
            return result
        finally:
            conn.close()


def update_room(
    room_id: str,
    mentor_user_id: str,
    title: str | None = None,
    description: str | None = None,
    market: str | None = None,
    visibility: str | None = None,
) -> dict:
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM live_rooms WHERE id = ? AND mentor_user_id = ?",
                (room_id, mentor_user_id)
            ).fetchone()
            if not row:
                raise ValueError("Oda bulunamadı veya yetkiniz yok")

            updates = {}
            if title is not None:
                t = title.strip()
                if not t:
                    raise ValueError("Oda başlığı gerekli")
                updates["title"] = t
                updates["slug"] = _make_slug(t, existing_id=room_id)
            if description is not None:
                updates["description"] = description.strip()
            if market is not None:
                if market and market not in VALID_MARKETS:
                    raise ValueError(f"Geçersiz market: {market}")
                updates["market"] = market
            if visibility is not None:
                if visibility not in VALID_VISIBILITY:
                    visibility = "public"
                updates["visibility"] = visibility

            if updates:
                updates["updated_at"] = _now_iso()
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                vals = list(updates.values()) + [room_id]
                conn.execute(f"UPDATE live_rooms SET {set_clause} WHERE id = ?", vals)
                conn.commit()

            row = conn.execute("SELECT * FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            return _enrich_room(_row_to_dict(row))
        finally:
            conn.close()


def start_room(room_id: str, mentor_user_id: str) -> dict:
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM live_rooms WHERE id = ? AND mentor_user_id = ?",
                (room_id, mentor_user_id)
            ).fetchone()
            if not row:
                raise ValueError("Oda bulunamadı veya yetkiniz yok")

            now = _now_iso()
            conn.execute(
                "UPDATE live_rooms SET is_active = 1, updated_at = ? WHERE id = ?",
                (now, room_id)
            )
            # System message
            conn.execute("""
                INSERT INTO room_messages (id, room_id, user_id, message_type, content, created_at)
                VALUES (?, ?, ?, 'system', ?, ?)
            """, (_gen_id(), room_id, mentor_user_id, "Canlı yayın başladı!", now))
            conn.commit()

            row = conn.execute("SELECT * FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            return _enrich_room(_row_to_dict(row))
        finally:
            conn.close()


def stop_room(room_id: str, mentor_user_id: str) -> dict:
    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM live_rooms WHERE id = ? AND mentor_user_id = ?",
                (room_id, mentor_user_id)
            ).fetchone()
            if not row:
                raise ValueError("Oda bulunamadı veya yetkiniz yok")

            now = _now_iso()
            conn.execute(
                "UPDATE live_rooms SET is_active = 0, updated_at = ? WHERE id = ?",
                (now, room_id)
            )
            # System message
            conn.execute("""
                INSERT INTO room_messages (id, room_id, user_id, message_type, content, created_at)
                VALUES (?, ?, ?, 'system', ?, ?)
            """, (_gen_id(), room_id, mentor_user_id, "Canlı yayın sona erdi.", now))
            conn.commit()

            row = conn.execute("SELECT * FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            return _enrich_room(_row_to_dict(row))
        finally:
            conn.close()


def get_room(slug: str, viewer_id: str | None = None) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM live_rooms WHERE slug = ?", (slug,)).fetchone()
        if not row:
            return None
        room = _enrich_room(_row_to_dict(row))
        room["is_joined"] = False
        room["is_owner"] = False
        if viewer_id:
            room["is_owner"] = viewer_id == room["mentor_user_id"]
            prow = conn.execute(
                "SELECT 1 FROM room_participants WHERE room_id = ? AND user_id = ?",
                (room["id"], viewer_id)
            ).fetchone()
            room["is_joined"] = prow is not None
        return room
    finally:
        conn.close()


def get_room_by_id(room_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
        if not row:
            return None
        return _enrich_room(_row_to_dict(row))
    finally:
        conn.close()


def list_rooms(
    market: str | None = None,
    active_only: bool = False,
    mentor_user_id: str | None = None,
    sort: str = "newest",
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
) -> list:
    conn = _get_conn()
    try:
        conditions = []
        params = []

        if active_only:
            conditions.append("is_active = 1")
        if market:
            conditions.append("market = ?")
            params.append(market)
        if mentor_user_id:
            conditions.append("mentor_user_id = ?")
            params.append(mentor_user_id)
        if search:
            term = f"%{search}%"
            conditions.append("(title LIKE ? OR description LIKE ?)")
            params.extend([term, term])

        where = " AND ".join(conditions) if conditions else "1=1"

        sort_map = {
            "newest": "created_at DESC",
            "active": "is_active DESC, updated_at DESC",
            "popular": "updated_at DESC",
        }
        order = sort_map.get(sort, "created_at DESC")

        params.extend([limit, offset])
        rows = conn.execute(
            f"SELECT * FROM live_rooms WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
            params
        ).fetchall()

        return [_enrich_room(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# PARTICIPANTS
# ══════════════════════════════════════════════════════════════════

def join_room(room_id: str, user_id: str) -> dict:
    with _lock:
        conn = _get_conn()
        try:
            rrow = conn.execute("SELECT * FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            if not rrow:
                raise ValueError("Oda bulunamadı")

            existing = conn.execute(
                "SELECT * FROM room_participants WHERE room_id = ? AND user_id = ?",
                (room_id, user_id)
            ).fetchone()
            if existing:
                return _row_to_dict(existing)

            now = _now_iso()
            pid = _gen_id()
            role = "mentor" if rrow["mentor_user_id"] == user_id else "member"
            conn.execute("""
                INSERT INTO room_participants (id, room_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?, ?)
            """, (pid, room_id, user_id, role, now))
            conn.commit()

            row = conn.execute("SELECT * FROM room_participants WHERE id = ?", (pid,)).fetchone()
            _logger.info("User %s joined room %s", user_id, room_id)
            return _row_to_dict(row)
        finally:
            conn.close()


def leave_room(room_id: str, user_id: str) -> bool:
    with _lock:
        conn = _get_conn()
        try:
            # Don't let the mentor leave their own room
            rrow = conn.execute("SELECT mentor_user_id FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            if rrow and rrow["mentor_user_id"] == user_id:
                raise ValueError("Mentor kendi odasından ayrılamaz")

            conn.execute(
                "DELETE FROM room_participants WHERE room_id = ? AND user_id = ?",
                (room_id, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()


def get_participants(room_id: str) -> list:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM room_participants WHERE room_id = ? ORDER BY joined_at ASC",
            (room_id,)
        ).fetchall()
        result = []
        for r in rows:
            p = _row_to_dict(r)
            p["username"] = _get_username(p["user_id"])
            result.append(p)
        return result
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# MESSAGES
# ══════════════════════════════════════════════════════════════════

def post_message(
    room_id: str,
    user_id: str,
    content: str,
    message_type: str = "text",
) -> dict:
    if not content or not content.strip():
        raise ValueError("Mesaj içeriği gerekli")
    if message_type not in VALID_MESSAGE_TYPES:
        message_type = "text"

    with _lock:
        conn = _get_conn()
        try:
            # Verify room exists
            rrow = conn.execute("SELECT id FROM live_rooms WHERE id = ?", (room_id,)).fetchone()
            if not rrow:
                raise ValueError("Oda bulunamadı")

            now = _now_iso()
            msg_id = _gen_id()

            conn.execute("""
                INSERT INTO room_messages (id, room_id, user_id, message_type, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (msg_id, room_id, user_id, message_type, content.strip(), now))
            conn.commit()

            row = conn.execute("SELECT * FROM room_messages WHERE id = ?", (msg_id,)).fetchone()
            msg = _row_to_dict(row)
            msg["username"] = _get_username(user_id)
            # Check if user is mentor of this room
            prow = conn.execute(
                "SELECT role FROM room_participants WHERE room_id = ? AND user_id = ?",
                (room_id, user_id)
            ).fetchone()
            msg["role"] = prow["role"] if prow else "member"
            _logger.info("Message posted in room %s by %s", room_id, user_id)
            return msg
        finally:
            conn.close()


def list_messages(
    room_id: str,
    limit: int = 50,
    before: str | None = None,
) -> list:
    conn = _get_conn()
    try:
        if before:
            rows = conn.execute("""
                SELECT * FROM room_messages
                WHERE room_id = ? AND created_at < ?
                ORDER BY created_at DESC LIMIT ?
            """, (room_id, before, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM room_messages
                WHERE room_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (room_id, limit)).fetchall()

        result = []
        for r in reversed(rows):  # chronological order
            msg = _row_to_dict(r)
            msg["username"] = _get_username(msg["user_id"])
            prow = conn.execute(
                "SELECT role FROM room_participants WHERE room_id = ? AND user_id = ?",
                (room_id, msg["user_id"])
            ).fetchone()
            msg["role"] = prow["role"] if prow else "member"
            result.append(msg)
        return result
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# MENTOR / STATS
# ══════════════════════════════════════════════════════════════════

def get_mentor_rooms(mentor_user_id: str, active_only: bool = False) -> list:
    conn = _get_conn()
    try:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM live_rooms WHERE mentor_user_id = ? AND is_active = 1 ORDER BY updated_at DESC",
                (mentor_user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM live_rooms WHERE mentor_user_id = ? ORDER BY updated_at DESC",
                (mentor_user_id,)
            ).fetchall()
        return [_enrich_room(_row_to_dict(r)) for r in rows]
    finally:
        conn.close()


def room_stats() -> dict:
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) as c FROM live_rooms").fetchone()["c"]
        active = conn.execute("SELECT COUNT(*) as c FROM live_rooms WHERE is_active = 1").fetchone()["c"]
        participants = conn.execute(
            "SELECT COUNT(DISTINCT user_id) as c FROM room_participants"
        ).fetchone()["c"]
        mentors = conn.execute(
            "SELECT COUNT(DISTINCT mentor_user_id) as c FROM live_rooms"
        ).fetchone()["c"]
        return {
            "total_rooms": total,
            "active_rooms": active,
            "total_participants": participants,
            "total_mentors": mentors,
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
# WEBSOCKET — Connected clients registry
# ══════════════════════════════════════════════════════════════════

_ws_clients: Dict[str, Set] = {}  # room_id → set of (ws, user_id) pairs
_ws_lock = threading.Lock()


def ws_register(room_id: str, ws, user_id: str):
    """Register a WebSocket client for a room."""
    with _ws_lock:
        if room_id not in _ws_clients:
            _ws_clients[room_id] = set()
        _ws_clients[room_id].add((id(ws), ws, user_id))


def ws_unregister(room_id: str, ws):
    """Unregister a WebSocket client from a room."""
    with _ws_lock:
        if room_id in _ws_clients:
            _ws_clients[room_id] = {
                (wid, w, uid) for wid, w, uid in _ws_clients[room_id]
                if wid != id(ws)
            }
            if not _ws_clients[room_id]:
                del _ws_clients[room_id]


def ws_broadcast(room_id: str, message: dict, exclude_ws=None):
    """Broadcast a message to all WebSocket clients in a room."""
    with _ws_lock:
        clients = list(_ws_clients.get(room_id, set()))

    msg_json = json.dumps(message, ensure_ascii=False)
    for wid, ws, uid in clients:
        if exclude_ws and wid == id(exclude_ws):
            continue
        try:
            ws.send(msg_json)
        except Exception:
            # Client disconnected, will be cleaned up
            pass
