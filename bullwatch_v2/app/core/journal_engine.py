# -*- coding: utf-8 -*-
"""Trade Journal Engine — FAZ 23.

SQLite-backed journal for recording and analyzing trades.

Public API:
  add_entry(data) → Dict
  update_entry(entry_id, data) → Dict
  delete_entry(entry_id) → bool
  list_entries(filters) → List[Dict]
  get_entry(entry_id) → Dict | None
  stats() → Dict
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.journal")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "journal.db")

VALID_EMOTIONS = ("confident", "neutral", "fear", "greed", "mistake")
VALID_SIDES = ("buy", "sell", "long", "short")

_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ══════════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    """Get a thread-safe SQLite connection."""
    from app.core.db_manager import get_connection
    return get_connection("journal.db")


def _ensure_table(conn: sqlite3.Connection):
    """Create journal table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS journal_entries (
            id           TEXT PRIMARY KEY,
            symbol       TEXT NOT NULL,
            market       TEXT DEFAULT 'crypto',
            side         TEXT DEFAULT 'buy',
            entry_price  REAL DEFAULT 0,
            exit_price   REAL DEFAULT 0,
            quantity     REAL DEFAULT 0,
            pnl          REAL DEFAULT 0,
            pnl_pct      REAL DEFAULT 0,
            notes        TEXT DEFAULT '',
            emotion      TEXT DEFAULT 'neutral',
            strategy     TEXT DEFAULT '',
            tags         TEXT DEFAULT '',
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            sim_position_id TEXT DEFAULT '',
            user_id      TEXT DEFAULT 'default'
        )
    """)
    # Migration: add user_id column to existing tables
    try:
        conn.execute("ALTER TABLE journal_entries ADD COLUMN user_id TEXT DEFAULT 'default'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict:
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def add_entry(data: Dict, user_id: str = "default") -> Dict:
    """Add a new journal entry.

    Required: symbol
    Optional: market, side, entry_price, exit_price, quantity, pnl, pnl_pct,
              notes, emotion, strategy, tags, sim_position_id, user_id
    """
    symbol = (data.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("symbol is required")

    emotion = (data.get("emotion") or "neutral").strip().lower()
    if emotion not in VALID_EMOTIONS:
        emotion = "neutral"

    now = datetime.now(timezone.utc).isoformat()
    entry_id = str(uuid.uuid4())[:8]

    entry = {
        "id": entry_id,
        "symbol": symbol,
        "market": (data.get("market") or "crypto").strip().lower(),
        "side": (data.get("side") or "buy").strip().lower(),
        "entry_price": float(data.get("entry_price", 0)),
        "exit_price": float(data.get("exit_price", 0)),
        "quantity": float(data.get("quantity", 0)),
        "pnl": float(data.get("pnl", 0)),
        "pnl_pct": float(data.get("pnl_pct", 0)),
        "notes": (data.get("notes") or "").strip(),
        "emotion": emotion,
        "strategy": (data.get("strategy") or "").strip(),
        "tags": (data.get("tags") or "").strip(),
        "created_at": now,
        "updated_at": now,
        "sim_position_id": (data.get("sim_position_id") or "").strip(),
        "user_id": user_id,
    }

    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            conn.execute("""
                INSERT INTO journal_entries
                (id, symbol, market, side, entry_price, exit_price, quantity,
                 pnl, pnl_pct, notes, emotion, strategy, tags,
                 created_at, updated_at, sim_position_id, user_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry["id"], entry["symbol"], entry["market"], entry["side"],
                entry["entry_price"], entry["exit_price"], entry["quantity"],
                entry["pnl"], entry["pnl_pct"], entry["notes"], entry["emotion"],
                entry["strategy"], entry["tags"],
                entry["created_at"], entry["updated_at"],
                entry["sim_position_id"], entry["user_id"],
            ))
            conn.commit()
        finally:
            conn.close()

    _logger.info("Journal entry added: %s %s %s", entry_id, symbol, entry["side"])
    return entry


def update_entry(entry_id: str, data: Dict) -> Dict:
    """Update an existing journal entry."""
    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            row = conn.execute(
                "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            if not row:
                raise ValueError(f"Journal entry not found: {entry_id}")

            existing = _row_to_dict(row)
            now = datetime.now(timezone.utc).isoformat()

            # Merge updates
            updates = {
                "notes": data.get("notes", existing["notes"]),
                "emotion": data.get("emotion", existing["emotion"]),
                "strategy": data.get("strategy", existing["strategy"]),
                "tags": data.get("tags", existing["tags"]),
                "exit_price": float(data.get("exit_price", existing["exit_price"])),
                "pnl": float(data.get("pnl", existing["pnl"])),
                "pnl_pct": float(data.get("pnl_pct", existing["pnl_pct"])),
                "updated_at": now,
            }

            # Validate emotion
            if updates["emotion"] not in VALID_EMOTIONS:
                updates["emotion"] = existing["emotion"]

            conn.execute("""
                UPDATE journal_entries
                SET notes=?, emotion=?, strategy=?, tags=?,
                    exit_price=?, pnl=?, pnl_pct=?, updated_at=?
                WHERE id=?
            """, (
                updates["notes"], updates["emotion"], updates["strategy"],
                updates["tags"], updates["exit_price"], updates["pnl"],
                updates["pnl_pct"], updates["updated_at"], entry_id,
            ))
            conn.commit()

            # Return updated entry
            row = conn.execute(
                "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def delete_entry(entry_id: str) -> bool:
    """Delete a journal entry."""
    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            cursor = conn.execute(
                "DELETE FROM journal_entries WHERE id = ?", (entry_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                _logger.info("Journal entry deleted: %s", entry_id)
            return deleted
        finally:
            conn.close()


def list_entries(
    symbol: Optional[str] = None,
    market: Optional[str] = None,
    emotion: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[str] = None,
) -> List[Dict]:
    """List journal entries with optional filters."""
    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            query = "SELECT * FROM journal_entries WHERE 1=1"
            params: list = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            if market:
                query += " AND market = ?"
                params.append(market.lower())
            if emotion:
                query += " AND emotion = ?"
                params.append(emotion.lower())
            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()


def get_entry(entry_id: str) -> Optional[Dict]:
    """Get a single journal entry by ID."""
    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            row = conn.execute(
                "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()


def stats(user_id: Optional[str] = None) -> Dict:
    """Compute journal statistics."""
    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            if user_id:
                rows = conn.execute(
                    "SELECT * FROM journal_entries WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM journal_entries ORDER BY created_at DESC"
                ).fetchall()

            if not rows:
                return {
                    "total_entries": 0,
                    "win_rate": 0,
                    "average_pnl": 0,
                    "best_trade": 0,
                    "worst_trade": 0,
                    "total_pnl": 0,
                    "by_emotion": {},
                    "by_strategy": {},
                    "streak": 0,
                }

            entries = [_row_to_dict(r) for r in rows]
            pnls = [e["pnl"] for e in entries]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]

            total = len(entries)
            win_rate = (len(wins) / total * 100) if total > 0 else 0

            # By emotion
            by_emotion: Dict = {}
            for e in entries:
                emo = e["emotion"]
                if emo not in by_emotion:
                    by_emotion[emo] = {"count": 0, "total_pnl": 0, "win_count": 0}
                by_emotion[emo]["count"] += 1
                by_emotion[emo]["total_pnl"] += e["pnl"]
                if e["pnl"] > 0:
                    by_emotion[emo]["win_count"] += 1
            for emo in by_emotion:
                c = by_emotion[emo]["count"]
                by_emotion[emo]["win_rate"] = round(
                    (by_emotion[emo]["win_count"] / c * 100) if c > 0 else 0, 1
                )
                by_emotion[emo]["total_pnl"] = round(by_emotion[emo]["total_pnl"], 2)

            # By strategy
            by_strategy: Dict = {}
            for e in entries:
                strat = e["strategy"] or "unknown"
                if strat not in by_strategy:
                    by_strategy[strat] = {"count": 0, "total_pnl": 0, "win_count": 0}
                by_strategy[strat]["count"] += 1
                by_strategy[strat]["total_pnl"] += e["pnl"]
                if e["pnl"] > 0:
                    by_strategy[strat]["win_count"] += 1
            for strat in by_strategy:
                c = by_strategy[strat]["count"]
                by_strategy[strat]["win_rate"] = round(
                    (by_strategy[strat]["win_count"] / c * 100) if c > 0 else 0, 1
                )
                by_strategy[strat]["total_pnl"] = round(by_strategy[strat]["total_pnl"], 2)

            # Current streak
            streak = 0
            if pnls:
                direction = 1 if pnls[0] > 0 else -1
                for p in pnls:
                    if (p > 0 and direction > 0) or (p <= 0 and direction < 0):
                        streak += direction
                    else:
                        break

            return {
                "total_entries": total,
                "win_rate": round(win_rate, 1),
                "average_pnl": round(sum(pnls) / total, 2) if total > 0 else 0,
                "best_trade": round(max(pnls), 2) if pnls else 0,
                "worst_trade": round(min(pnls), 2) if pnls else 0,
                "total_pnl": round(sum(pnls), 2),
                "by_emotion": by_emotion,
                "by_strategy": by_strategy,
                "streak": streak,
            }
        finally:
            conn.close()


def clear_all() -> int:
    """Delete all journal entries (used in tests). Returns count deleted."""
    with _lock:
        conn = _get_conn()
        try:
            _ensure_table(conn)
            cursor = conn.execute("DELETE FROM journal_entries")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
