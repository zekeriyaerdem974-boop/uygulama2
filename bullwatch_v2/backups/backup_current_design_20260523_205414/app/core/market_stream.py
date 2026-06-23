# -*- coding: utf-8 -*-
"""Market Stream Engine — FAZ 26.

Server-side real-time market data manager.  Connects to upstream
WebSocket feeds (Binance, Yahoo, etc.), normalises data, and
broadcasts to all subscribed browser clients.

Architecture
────────────
  Binance WS (1 conn per symbol@kline_tf) ──┐
                                             ├─→ _SymbolRoom ──→ browser clients
  Yahoo / REST poll fallback ────────────────┘

Single-stream optimisation:
  100 browsers watching BTCUSDT  →  1 upstream WS  →  100 broadcasts.

Public API used by the /ws/market flask-sock endpoint:
    register_client(ws, symbol, market, interval)
    unregister_client(ws)
    get_stats() -> dict
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Dict, Optional, Set

import websocket as ws_client          # websocket-client (already installed)

from app.cache import cache_get

_logger = logging.getLogger("zkr_analiz.market_stream")

# ──────────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────────
BINANCE_WS_BASE = "wss://stream.binance.com:9443/ws"
TICKERS_KEY = "binance_top_tickers_v1"          # shared with background/jobs.py

# Timeframe → Binance kline interval code
_TF_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
    "30m": "30m", "1h": "1h", "2h": "2h", "4h": "4h",
    "1d": "1d", "1w": "1w", "1M": "1M",
}

# How often to push watchlist snapshot (seconds)
_WATCHLIST_PUSH_INTERVAL = 1.5


# ──────────────────────────────────────────────────────────────────────
# ROOM — one per unique (symbol, market, interval)
# ──────────────────────────────────────────────────────────────────────
class _SymbolRoom:
    """Manages a single upstream feed and fans-out to browser clients."""

    __slots__ = (
        "symbol", "market", "interval", "room_key",
        "_clients", "_lock",
        "_upstream_ws", "_upstream_thread", "_running",
        "_last_kline",
    )

    def __init__(self, symbol: str, market: str, interval: str):
        self.symbol = symbol.upper()
        self.market = market.lower()
        self.interval = interval
        self.room_key = f"{self.market}:{self.symbol}:{self.interval}"
        self._clients: Set = set()
        self._lock = threading.Lock()
        self._upstream_ws = None
        self._upstream_thread: Optional[threading.Thread] = None
        self._running = False
        self._last_kline: Optional[dict] = None

    # ── client management ────────────────────────────────────────────
    def add(self, client_ws) -> None:
        with self._lock:
            self._clients.add(client_ws)
        if not self._running and self.market == "crypto":
            self._start_upstream()

    def remove(self, client_ws) -> None:
        with self._lock:
            self._clients.discard(client_ws)
        if not self._clients:
            self._stop_upstream()

    @property
    def empty(self) -> bool:
        return len(self._clients) == 0

    @property
    def client_count(self) -> int:
        return len(self._clients)

    # ── broadcast to browsers ────────────────────────────────────────
    def broadcast(self, payload: dict) -> None:
        msg = json.dumps(payload, ensure_ascii=False)
        dead: list = []
        with self._lock:
            for c in self._clients:
                try:
                    c.send(msg)
                except Exception:
                    dead.append(c)
        for c in dead:
            with self._lock:
                self._clients.discard(c)

    # ── upstream Binance kline WS ────────────────────────────────────
    def _start_upstream(self) -> None:
        if self._running:
            return
        self._running = True
        self._upstream_thread = threading.Thread(
            target=self._upstream_loop,
            name=f"stream-{self.room_key}",
            daemon=True,
        )
        self._upstream_thread.start()
        _logger.info("Upstream started: %s", self.room_key)

    def _stop_upstream(self) -> None:
        self._running = False
        if self._upstream_ws:
            try:
                self._upstream_ws.close()
            except Exception:
                pass
        _logger.info("Upstream stopped: %s", self.room_key)

    def _upstream_loop(self) -> None:
        """Connect to Binance kline WS and relay to browsers."""
        bi = _TF_MAP.get(self.interval, self.interval)
        url = f"{BINANCE_WS_BASE}/{self.symbol.lower()}@kline_{bi}"

        def on_message(wsapp, message):
            try:
                data = json.loads(message)
                k = data.get("k")
                if not k:
                    return
                tick = {
                    "type": "kline",
                    "symbol": self.symbol,
                    "interval": self.interval,
                    "time": int(k["t"]) // 1000,       # seconds for LW charts
                    "open": float(k["o"]),
                    "high": float(k["h"]),
                    "low": float(k["l"]),
                    "close": float(k["c"]),
                    "volume": float(k["v"]),
                    "closed": k.get("x", False),        # candle closed?
                }
                self._last_kline = tick
                self.broadcast(tick)
            except Exception:
                pass

        def on_error(wsapp, err):
            _logger.debug("Upstream WS error %s: %s", self.room_key, err)

        def on_close(wsapp, *a):
            _logger.debug("Upstream WS closed %s", self.room_key)

        while self._running and not self.empty:
            try:
                self._upstream_ws = ws_client.WebSocketApp(
                    url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )
                self._upstream_ws.run_forever(
                    ping_interval=20, ping_timeout=10,
                )
            except Exception as e:
                _logger.warning("Upstream loop error %s: %s", self.room_key, e)
            if self._running and not self.empty:
                time.sleep(2)

        self._running = False


# ──────────────────────────────────────────────────────────────────────
# STREAM MANAGER — singleton
# ──────────────────────────────────────────────────────────────────────
class MarketStreamManager:
    """Global manager that maps rooms and clients."""

    def __init__(self):
        self._rooms: Dict[str, _SymbolRoom] = {}
        self._client_rooms: Dict[int, _SymbolRoom] = {}   # id(ws) → room
        self._watchlist_clients: Set = set()
        self._lock = threading.Lock()
        self._wl_thread: Optional[threading.Thread] = None
        self._wl_running = False

    # ── public API ───────────────────────────────────────────────────
    def register_client(
        self,
        client_ws,
        symbol: str,
        market: str = "crypto",
        interval: str = "15m",
    ) -> None:
        """Subscribe a browser WS to a symbol room."""
        key = f"{market.lower()}:{symbol.upper()}:{interval}"
        cid = id(client_ws)

        with self._lock:
            # Remove from previous room
            old = self._client_rooms.get(cid)
            if old and old.room_key != key:
                old.remove(client_ws)
                if old.empty:
                    self._rooms.pop(old.room_key, None)

            # Get or create room
            room = self._rooms.get(key)
            if room is None:
                room = _SymbolRoom(symbol, market, interval)
                self._rooms[key] = room

            room.add(client_ws)
            self._client_rooms[cid] = room

    def subscribe_watchlist(self, client_ws) -> None:
        """Subscribe browser WS to watchlist ticker updates."""
        with self._lock:
            self._watchlist_clients.add(client_ws)
        if not self._wl_running:
            self._start_watchlist_loop()

    def unregister_client(self, client_ws) -> None:
        """Remove a browser WS from all rooms and watchlist."""
        cid = id(client_ws)
        with self._lock:
            room = self._client_rooms.pop(cid, None)
            if room:
                room.remove(client_ws)
                if room.empty:
                    self._rooms.pop(room.room_key, None)
            self._watchlist_clients.discard(client_ws)

    def get_stats(self) -> dict:
        """Return runtime statistics."""
        with self._lock:
            rooms = {
                k: {"clients": r.client_count, "symbol": r.symbol, "market": r.market}
                for k, r in self._rooms.items()
            }
            return {
                "rooms": rooms,
                "total_rooms": len(self._rooms),
                "total_clients": sum(r.client_count for r in self._rooms.values()),
                "watchlist_clients": len(self._watchlist_clients),
            }

    # ── watchlist ticker loop ────────────────────────────────────────
    def _start_watchlist_loop(self) -> None:
        if self._wl_running:
            return
        self._wl_running = True
        self._wl_thread = threading.Thread(
            target=self._watchlist_loop,
            name="wl-broadcast",
            daemon=True,
        )
        self._wl_thread.start()

    def _watchlist_loop(self) -> None:
        """Push cached ticker snapshot to watchlist subscribers every N seconds."""
        _logger.info("Watchlist broadcast loop started")
        while self._wl_running:
            try:
                if not self._watchlist_clients:
                    time.sleep(_WATCHLIST_PUSH_INTERVAL)
                    continue

                tickers = cache_get(TICKERS_KEY, ttl=5) or []
                if not tickers:
                    time.sleep(_WATCHLIST_PUSH_INTERVAL)
                    continue

                payload = json.dumps({
                    "type": "watchlist",
                    "tickers": tickers,
                }, ensure_ascii=False)

                dead: list = []
                with self._lock:
                    for c in self._watchlist_clients:
                        try:
                            c.send(payload)
                        except Exception:
                            dead.append(c)
                for c in dead:
                    with self._lock:
                        self._watchlist_clients.discard(c)

            except Exception as e:
                _logger.debug("Watchlist loop error: %s", e)

            time.sleep(_WATCHLIST_PUSH_INTERVAL)


# ── Singleton instance ───────────────────────────────────────────────
stream_manager = MarketStreamManager()
