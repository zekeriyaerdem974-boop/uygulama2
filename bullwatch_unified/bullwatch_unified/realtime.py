import json
import logging
import threading
import time
from typing import Any

import websocket

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()
_thread_started = False
_BROADCAST_INTERVAL = 1.0  # seconds between price_update_batch emits


def cache_set(key: str, value: Any) -> None:
    with _cache_lock:
        _cache[key] = value


def cache_get(key: str, default: Any = None) -> Any:
    with _cache_lock:
        return _cache.get(key, default)


def _on_ws_message(ws: websocket.WebSocketApp, message: str) -> None:
    try:
        data = json.loads(message)
        for coin in data:
            symbol = coin.get("s")
            if symbol and symbol.endswith("USDT"):
                current_price = float(coin.get("c", 0))
                change_24h_pct = float(coin.get("P", 0))
                volume_24h = float(coin.get("q", 0))

                cache_set(f"rt_price_{symbol}", current_price)
                cache_set(f"rt_change_{symbol}", change_24h_pct)
                cache_set(f"rt_vol_{symbol}", volume_24h)
    except Exception as exc:
        logger.exception("Error processing Binance websocket message: %s", exc)


def _on_ws_error(ws: websocket.WebSocketApp, error: Exception) -> None:
    logger.error("[WebSocket Error] Binance bağlantı hatası: %s", error)


def _on_ws_close(ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
    logger.warning("[WebSocket Closed] Binance bağlantı koptu: %s %s", close_status_code, close_msg)


def _on_ws_open(ws: websocket.WebSocketApp) -> None:
    logger.info("[WebSocket Open] Binance realtime stream connected")


def run_binance_ws() -> None:
    socket_url = "wss://stream.binance.com:9443/ws/!ticker@arr"
    reconnect_delay = 5  # seconds
    max_reconnect_delay = 60  # max delay (exponential backoff cap)
    current_delay = reconnect_delay
    
    while True:
        try:
            logger.info("[WS Init] Başlatılıyor: %s", socket_url)
            ws = websocket.WebSocketApp(
                socket_url,
                on_open=_on_ws_open,
                on_message=_on_ws_message,
                on_error=_on_ws_error,
                on_close=_on_ws_close,
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as exc:
            logger.exception("[WS Exception] Binance websocket connection failed: %s", exc)

        logger.warning("[WS Reconnect] %d saniye bekledikten sonra yeniden bağlanılacak", current_delay)
        time.sleep(current_delay)
        
        # Exponential backoff: her başarısız denemede delay'i artır (max 60s)
        current_delay = min(current_delay * 1.5, max_reconnect_delay)
        current_delay = int(current_delay)


def _broadcast_loop() -> None:
    from .extensions import socketio

    while True:
        time.sleep(_BROADCAST_INTERVAL)
        batch: dict[str, float] = {}
        with _cache_lock:
            for key, value in _cache.items():
                if key.startswith("rt_price_"):
                    batch[key[len("rt_price_"):]] = value

        if batch:
            try:
                socketio.emit("price_update_batch", batch)
            except Exception as exc:
                logger.warning("Broadcast error: %s", exc)


def start_binance_ws_thread() -> None:
    global _thread_started
    if _thread_started:
        return

    _thread_started = True
    threading.Thread(target=run_binance_ws, daemon=True).start()
    threading.Thread(target=_broadcast_loop, daemon=True).start()
