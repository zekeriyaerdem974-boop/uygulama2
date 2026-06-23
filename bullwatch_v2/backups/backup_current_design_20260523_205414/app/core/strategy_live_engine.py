# -*- coding: utf-8 -*-
"""Strategy Live Signals Engine — FAZ 28.

Evaluates user-defined strategies against real-time market data
from FAZ 26 WebSocket streams and emits BUY / SELL / EXIT signals.

Architecture
────────────
  MarketStreamManager (FAZ 26)
      ↓ (candle close tick)
  StrategyLiveEngine
      ├─ candle buffer per (symbol, interval)
      ├─ fetch initial history via binance_klines()
      ├─ on each closed candle: parse + execute strategy → signal
      ├─ dedup cache:  (strategy_id, symbol, candle_time) → prevents duplicates
      └─ emit signal → store + notify via alert-style notification

Single-stream optimisation:
  Multiple strategies on same (symbol, interval) share ONE upstream connection.

Public API:
    live_engine  — singleton StrategyLiveEngine
    activate_strategy(user_id, strategy_id, code, symbol, market, interval)
    deactivate_strategy(activation_id)
    get_active_strategies(user_id) -> list
    get_live_signals(user_id, limit) -> list
    get_all_active() -> list
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd

_logger = logging.getLogger("zkr_analiz.strategy_live")

# ══════════════════════════════════════════════════════════════════════
# STORAGE  — JSON file per active strategies + signals
# ══════════════════════════════════════════════════════════════════════
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "live_strategies"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_ACTIVE_FILE = _DATA_DIR / "active.json"
_SIGNALS_FILE = _DATA_DIR / "signals.json"

_lock = threading.Lock()
_MAX_SIGNALS = 500  # max stored signals


def _load_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return []


def _save_json(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


# ══════════════════════════════════════════════════════════════════════
# ACTIVE STRATEGIES CRUD
# ══════════════════════════════════════════════════════════════════════

def _load_active() -> list:
    return _load_json(_ACTIVE_FILE)


def _save_active(items: list) -> None:
    _save_json(_ACTIVE_FILE, items)


def activate_strategy(
    user_id: str,
    strategy_id: str,
    strategy_name: str,
    code: str,
    symbol: str,
    market: str = "crypto",
    interval: str = "15m",
) -> dict:
    """Activate a strategy for live signal generation."""
    symbol = symbol.upper()
    market = market.lower()

    with _lock:
        items = _load_active()

        # Check if already active for same user+strategy+symbol+interval
        for item in items:
            if (item["user_id"] == user_id
                    and item["strategy_id"] == strategy_id
                    and item["symbol"] == symbol
                    and item["interval"] == interval
                    and item.get("enabled", True)):
                return {"ok": False, "error": "Bu strateji zaten aktif"}

        activation = {
            "id": str(uuid.uuid4())[:12],
            "user_id": user_id,
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "code": code,
            "symbol": symbol,
            "market": market,
            "interval": interval,
            "enabled": True,
            "created_at": int(time.time()),
            "last_signal": None,
            "signal_count": 0,
        }
        items.append(activation)
        _save_active(items)

    # Register with live engine
    live_engine.register(activation)

    _logger.info("Strategy activated: %s %s %s %s by user %s",
                 activation["id"], strategy_name, symbol, interval, user_id)
    return {"ok": True, "activation": activation}


def deactivate_strategy(activation_id: str, user_id: str = None) -> dict:
    """Deactivate a live strategy."""
    with _lock:
        items = _load_active()
        found = None
        for item in items:
            if item["id"] == activation_id:
                if user_id and item["user_id"] != user_id:
                    return {"ok": False, "error": "Yetki hatası"}
                found = item
                break

        if not found:
            return {"ok": False, "error": "Aktivasyon bulunamadı"}

        found["enabled"] = False
        _save_active(items)

    # Unregister from live engine
    live_engine.unregister(activation_id)

    _logger.info("Strategy deactivated: %s", activation_id)
    return {"ok": True}


def toggle_strategy(activation_id: str, user_id: str = None) -> dict:
    """Toggle enabled state of a live strategy."""
    with _lock:
        items = _load_active()
        found = None
        for item in items:
            if item["id"] == activation_id:
                if user_id and item["user_id"] != user_id:
                    return {"ok": False, "error": "Yetki hatası"}
                found = item
                break

        if not found:
            return {"ok": False, "error": "Aktivasyon bulunamadı"}

        new_state = not found.get("enabled", True)
        found["enabled"] = new_state
        _save_active(items)

    if new_state:
        live_engine.register(found)
    else:
        live_engine.unregister(activation_id)

    return {"ok": True, "enabled": new_state}


def get_active_strategies(user_id: str = None) -> list:
    """Get active strategies, optionally filtered by user."""
    items = _load_active()
    if user_id:
        items = [i for i in items if i["user_id"] == user_id]
    return items


def get_all_active() -> list:
    """Get all active (enabled) strategies across all users."""
    return [i for i in _load_active() if i.get("enabled", True)]


def remove_strategy(activation_id: str, user_id: str = None) -> dict:
    """Permanently remove a live strategy activation."""
    with _lock:
        items = _load_active()
        new_items = []
        removed = False
        for item in items:
            if item["id"] == activation_id:
                if user_id and item["user_id"] != user_id:
                    new_items.append(item)
                    continue
                removed = True
                continue
            new_items.append(item)

        if not removed:
            return {"ok": False, "error": "Aktivasyon bulunamadı"}

        _save_active(new_items)

    live_engine.unregister(activation_id)
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════
# SIGNALS STORAGE
# ══════════════════════════════════════════════════════════════════════

def _load_signals() -> list:
    return _load_json(_SIGNALS_FILE)


def _save_signals(items: list) -> None:
    _save_json(_SIGNALS_FILE, items)


def store_signal(signal: dict) -> None:
    """Store a generated signal."""
    with _lock:
        signals = _load_signals()
        signals.insert(0, signal)
        if len(signals) > _MAX_SIGNALS:
            signals = signals[:_MAX_SIGNALS]
        _save_signals(signals)


def get_live_signals(user_id: str = None, limit: int = 50) -> list:
    """Get recent live signals, optionally filtered by user."""
    signals = _load_signals()
    if user_id:
        signals = [s for s in signals if s.get("user_id") == user_id]
    return signals[:limit]


def clear_signals(user_id: str = None) -> int:
    """Clear signals, optionally for a specific user."""
    with _lock:
        signals = _load_signals()
        if user_id:
            before = len(signals)
            signals = [s for s in signals if s.get("user_id") != user_id]
            _save_signals(signals)
            return before - len(signals)
        else:
            count = len(signals)
            _save_signals([])
            return count


# ══════════════════════════════════════════════════════════════════════
# LIVE ENGINE  — core real-time evaluation engine
# ══════════════════════════════════════════════════════════════════════

class StrategyLiveEngine:
    """Evaluates strategies against real-time market data.

    For each active strategy:
    1. Fetch initial candle history (200 bars) via binance_klines
    2. Subscribe to market stream for the same (symbol, interval)
    3. On each closed candle, append to buffer and evaluate
    4. Check last bar signal: +1 → BUY, -1 → SELL
    5. Dedup: skip if same signal already emitted for this candle
    6. Store + notify
    """

    def __init__(self):
        self._activations: Dict[str, dict] = {}        # id → activation dict
        self._candle_buffers: Dict[str, pd.DataFrame] = {}  # room_key → DataFrame
        self._signal_cache: Dict[str, str] = {}         # (act_id, candle_time) → signal_type
        self._room_subscriptions: Dict[str, Set[str]] = {}  # room_key → set of activation_ids
        self._ws_threads: Dict[str, threading.Thread] = {}  # room_key → WS thread
        self._running_rooms: Dict[str, bool] = {}        # room_key → running flag
        self._lock = threading.Lock()
        self._started = False
        # WebSocket client listeners (browser WS for pushing signals)
        self._signal_listeners: Dict[int, object] = {}  # id(ws) → ws
        self._listener_users: Dict[int, str] = {}        # id(ws) → user_id
        self._listener_lock = threading.Lock()

    def start(self) -> None:
        """Start the live engine — load and register all active strategies."""
        if self._started:
            return
        self._started = True
        _logger.info("Strategy Live Engine starting...")

        active = get_all_active()
        for act in active:
            self.register(act)

        _logger.info("Strategy Live Engine started with %d active strategies",
                     len(self._activations))

    def stop(self) -> None:
        """Stop all upstream connections."""
        self._started = False
        with self._lock:
            for key in list(self._running_rooms.keys()):
                self._running_rooms[key] = False
            self._activations.clear()
            self._room_subscriptions.clear()
        _logger.info("Strategy Live Engine stopped")

    def register(self, activation: dict) -> None:
        """Register an activation for live evaluation."""
        act_id = activation["id"]
        symbol = activation["symbol"]
        market = activation["market"]
        interval = activation["interval"]
        room_key = f"{market}:{symbol}:{interval}"

        with self._lock:
            self._activations[act_id] = activation

            if room_key not in self._room_subscriptions:
                self._room_subscriptions[room_key] = set()
            self._room_subscriptions[room_key].add(act_id)

        # Start upstream WS if not already running
        with self._lock:
            already_running = self._running_rooms.get(room_key, False)
        if not already_running:
            self._start_room(room_key, symbol, market, interval)

    def unregister(self, activation_id: str) -> None:
        """Unregister an activation."""
        with self._lock:
            act = self._activations.pop(activation_id, None)
            if not act:
                return

            room_key = f"{act['market']}:{act['symbol']}:{act['interval']}"
            subs = self._room_subscriptions.get(room_key, set())
            subs.discard(activation_id)

            # If no more strategies for this room, stop upstream
            if not subs:
                self._room_subscriptions.pop(room_key, None)
                self._running_rooms[room_key] = False

    def _start_room(self, room_key: str, symbol: str, market: str, interval: str) -> None:
        """Start upstream WS connection for a room."""
        if market != "crypto":
            _logger.info("Live signals only supported for crypto markets currently")
            return

        self._running_rooms[room_key] = True

        # Fetch initial candle history in background
        t = threading.Thread(
            target=self._room_loop,
            args=(room_key, symbol, market, interval),
            name=f"live-{room_key}",
            daemon=True,
        )
        self._ws_threads[room_key] = t
        t.start()

    def _room_loop(self, room_key: str, symbol: str, market: str, interval: str) -> None:
        """Main loop for a room: fetch history then listen to WS."""
        import websocket as ws_client

        _logger.info("Live room starting: %s", room_key)

        # 1. Fetch initial candle history
        try:
            from app.core.binance_client import binance_klines
            df = binance_klines(symbol, interval=interval, limit=200)
            with self._lock:
                self._candle_buffers[room_key] = df
            _logger.info("Fetched %d initial candles for %s", len(df), room_key)
        except Exception as e:
            _logger.error("Failed to fetch initial candles for %s: %s", room_key, e)
            self._running_rooms[room_key] = False
            return

        # 2. Connect to Binance kline WS
        from app.core.market_stream import _TF_MAP, BINANCE_WS_BASE

        bi = _TF_MAP.get(interval, interval)
        url = f"{BINANCE_WS_BASE}/{symbol.lower()}@kline_{bi}"

        def on_message(wsapp, message):
            try:
                data = json.loads(message)
                k = data.get("k")
                if not k:
                    return

                closed = k.get("x", False)
                candle_time = int(k["t"]) // 1000

                tick = {
                    "time": candle_time,
                    "open": float(k["o"]),
                    "high": float(k["h"]),
                    "low": float(k["l"]),
                    "close": float(k["c"]),
                    "volume": float(k["v"]),
                    "open_time": int(k["t"]),
                    "close_time": int(k["T"]),
                }

                if closed:
                    self._on_candle_close(room_key, tick, symbol, market, interval)

            except Exception as e:
                _logger.debug("Live WS message error %s: %s", room_key, e)

        def on_error(wsapp, err):
            _logger.debug("Live WS error %s: %s", room_key, err)

        def on_close(wsapp, *a):
            _logger.debug("Live WS closed %s", room_key)

        while self._running_rooms.get(room_key, False):
            subs = self._room_subscriptions.get(room_key, set())
            if not subs:
                break
            try:
                ws = ws_client.WebSocketApp(
                    url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )
                ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                _logger.warning("Live room loop error %s: %s", room_key, e)

            if self._running_rooms.get(room_key, False):
                time.sleep(2)

        self._running_rooms[room_key] = False
        _logger.info("Live room stopped: %s", room_key)

    def _on_candle_close(self, room_key: str, tick: dict,
                         symbol: str, market: str, interval: str) -> None:
        """Called when a candle closes. Evaluate all strategies for this room."""
        candle_time = tick["time"]

        # Append candle to buffer
        with self._lock:
            buf = self._candle_buffers.get(room_key)
            if buf is None or buf.empty:
                return

            # Check if candle already exists (by open_time)
            existing_times = set(buf["open_time"].values)
            if tick["open_time"] not in existing_times:
                new_row = pd.DataFrame([tick])
                self._candle_buffers[room_key] = pd.concat(
                    [buf, new_row], ignore_index=True
                ).tail(300)  # keep last 300 candles max

            df = self._candle_buffers[room_key].copy()
            activations = []
            for act_id in self._room_subscriptions.get(room_key, set()):
                act = self._activations.get(act_id)
                if act:
                    activations.append(act)

        # Evaluate each strategy
        for act in activations:
            try:
                self._evaluate_strategy(act, df, candle_time, symbol, market, interval)
            except Exception as e:
                _logger.warning("Strategy eval error %s: %s", act["id"], e)

    def _evaluate_strategy(self, activation: dict, df: pd.DataFrame,
                           candle_time: int, symbol: str, market: str,
                           interval: str) -> None:
        """Evaluate a single strategy on the current candle buffer."""
        act_id = activation["id"]
        code = activation["code"]

        # Dedup check
        cache_key = f"{act_id}:{candle_time}"
        if cache_key in self._signal_cache:
            return

        # Parse and execute
        from app.core.strategy_engine import parse_strategy, execute_strategy

        parsed = parse_strategy(code)
        signals = execute_strategy(parsed, df)

        # Check last bar signal
        if signals.empty:
            return

        last_signal = int(signals.iloc[-1])
        if last_signal == 0:
            # No signal — still cache to prevent re-evaluation
            self._signal_cache[cache_key] = "hold"
            return

        signal_type = "BULLISH" if last_signal == 1 else "BEARISH"

        # Cache this signal
        self._signal_cache[cache_key] = signal_type

        # Clean old cache entries (keep last 1000)
        if len(self._signal_cache) > 1000:
            keys = list(self._signal_cache.keys())
            for k in keys[:len(keys) - 500]:
                self._signal_cache.pop(k, None)

        # Get current price from last candle
        current_price = float(df["close"].iloc[-1])

        # Build signal object
        signal = {
            "id": str(uuid.uuid4())[:10],
            "activation_id": act_id,
            "user_id": activation["user_id"],
            "strategy_id": activation["strategy_id"],
            "strategy_name": activation.get("strategy_name", "Unknown"),
            "symbol": symbol,
            "market": market,
            "interval": interval,
            "signal_type": signal_type,
            "price": current_price,
            "candle_time": candle_time,
            "created_at": int(time.time()),
            "created_at_iso": datetime.now(timezone.utc).isoformat(),
        }

        # Store signal
        store_signal(signal)

        # Update activation stats
        self._update_activation_stats(act_id, signal_type, signal["created_at_iso"])

        # Push to WebSocket listeners
        self._broadcast_signal(signal)

        _logger.info("🔔 LIVE INSIGHT: %s %s %s @ %.4f [%s %s] strategy=%s",
                     signal_type, symbol, interval, current_price,
                     activation.get("strategy_name", "?"), act_id,
                     activation.get("strategy_id", "?"))

    def _update_activation_stats(self, activation_id: str, signal_type: str,
                                  timestamp: str) -> None:
        """Update signal count and last_signal on the activation record."""
        with _lock:
            items = _load_active()
            for item in items:
                if item["id"] == activation_id:
                    item["signal_count"] = item.get("signal_count", 0) + 1
                    item["last_signal"] = {
                        "type": signal_type,
                        "time": timestamp,
                    }
                    break
            _save_active(items)

    # ── WebSocket signal broadcasting ────────────────────────────
    def register_listener(self, ws, user_id: str) -> None:
        """Register a browser WebSocket to receive live signal notifications."""
        with self._listener_lock:
            self._signal_listeners[id(ws)] = ws
            self._listener_users[id(ws)] = user_id

    def unregister_listener(self, ws) -> None:
        """Unregister a browser WebSocket."""
        with self._listener_lock:
            wid = id(ws)
            self._signal_listeners.pop(wid, None)
            self._listener_users.pop(wid, None)

    def _broadcast_signal(self, signal: dict) -> None:
        """Push signal to relevant WebSocket listeners."""
        target_user = signal.get("user_id")
        msg = json.dumps({
            "type": "strategy_signal",
            "signal": signal,
        }, ensure_ascii=False)

        dead = []
        with self._listener_lock:
            for wid, ws in self._signal_listeners.items():
                # Only send to the strategy owner
                if self._listener_users.get(wid) == target_user:
                    try:
                        ws.send(msg)
                    except Exception:
                        dead.append(wid)

        for wid in dead:
            with self._listener_lock:
                self._signal_listeners.pop(wid, None)
                self._listener_users.pop(wid, None)

    # ── Stats ────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        """Return engine statistics."""
        with self._lock:
            return {
                "active_strategies": len(self._activations),
                "active_rooms": len([k for k, v in self._running_rooms.items() if v]),
                "buffer_sizes": {k: len(v) for k, v in self._candle_buffers.items()},
                "cache_size": len(self._signal_cache),
                "listeners": len(self._signal_listeners),
            }


# ── Singleton ────────────────────────────────────────────────────
live_engine = StrategyLiveEngine()
