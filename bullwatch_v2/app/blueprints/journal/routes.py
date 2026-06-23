# -*- coding: utf-8 -*-
"""Journal API routes — FAZ 23.

Endpoints:
  GET    /api/journal          — List journal entries
  POST   /api/journal          — Add a journal entry
  PUT    /api/journal/<id>     — Update a journal entry
  DELETE /api/journal/<id>     — Delete a journal entry
  GET    /api/journal/stats    — Get journal statistics
"""
from flask import jsonify, request, session

from app.blueprints.journal import journal_bp


@journal_bp.route("", methods=["GET"])
@journal_bp.route("/", methods=["GET"])
def api_list_journal():
    """List journal entries with optional filters."""
    try:
        from app.core.journal_engine import list_entries

        symbol = request.args.get("symbol")
        market = request.args.get("market")
        emotion = request.args.get("emotion")
        strategy = request.args.get("strategy")
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        user_id = session.get("user_id") or request.args.get("user_id")

        entries = list_entries(
            symbol=symbol, market=market, emotion=emotion,
            strategy=strategy, limit=limit, offset=offset,
            user_id=user_id,
        )
        return jsonify({"ok": True, "entries": entries, "count": len(entries)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@journal_bp.route("", methods=["POST"])
@journal_bp.route("/", methods=["POST"])
def api_add_journal():
    """Add a new journal entry."""
    try:
        from app.core.journal_engine import add_entry

        body = request.get_json(force=True, silent=True) or {}
        if not body.get("symbol"):
            return jsonify({"ok": False, "error": "symbol is required"}), 400

        user_id = session.get("user_id", "default")
        entry = add_entry(body, user_id=user_id)
        return jsonify({"ok": True, "entry": entry}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@journal_bp.route("/<entry_id>", methods=["PUT"])
def api_update_journal(entry_id):
    """Update a journal entry."""
    try:
        from app.core.journal_engine import update_entry

        body = request.get_json(force=True, silent=True) or {}
        entry = update_entry(entry_id, body)
        return jsonify({"ok": True, "entry": entry})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@journal_bp.route("/<entry_id>", methods=["DELETE"])
def api_delete_journal(entry_id):
    """Delete a journal entry."""
    try:
        from app.core.journal_engine import delete_entry

        deleted = delete_entry(entry_id)
        if not deleted:
            return jsonify({"ok": False, "error": "Entry not found"}), 404
        return jsonify({"ok": True, "message": "Entry deleted"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@journal_bp.route("/stats", methods=["GET"])
def api_journal_stats():
    """Get journal statistics."""
    try:
        from app.core.journal_engine import stats

        user_id = session.get("user_id")
        data = stats(user_id=user_id)
        return jsonify({"ok": True, "stats": data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
