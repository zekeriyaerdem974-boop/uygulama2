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


def _get_market_metrics() -> dict:
    """Piyasa ölçümlerini topla ve human-readable format'ta döndür"""
    try:
        import requests
        
        metrics = {
            "volume_24h": "$0",
            "open_interest": "$0",
            "fear_and_greed": "0 (Unknown)",
            "funding_rate": "0.0000%",
            "btc_dominance": "0.0%",
            "sentiment": "Neutral"
        }
        
        # BTC 24h Volume (Binance)
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT", timeout=3)
            if r.ok:
                data = r.json()
                volume_usd = float(data.get("quoteAssetVolume", 0))
                if volume_usd >= 1e9:
                    metrics["volume_24h"] = f"${volume_usd/1e9:.1f}B"
                elif volume_usd >= 1e6:
                    metrics["volume_24h"] = f"${volume_usd/1e6:.1f}M"
        except:
            pass
        
        # Open Interest (mock için sabit, production'da CoinGlass)
        metrics["open_interest"] = "$18.2B"
        
        # Fear & Greed Index (cache'den al)
        fng_data = cache_get("fng_latest", {})
        if fng_data:
            fng_idx = fng_data.get("value", 50)
            fng_class = fng_data.get("value_classification", "Neutral")
            metrics["fear_and_greed"] = f"{int(fng_idx)} ({fng_class})"
        
        # Funding Rate (BTC perpetual)
        try:
            r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", timeout=3)
            if r.ok:
                data = r.json()
                if data:
                    rate = float(data[0].get("fundingRate", 0)) * 100
                    metrics["funding_rate"] = f"{rate:+.4f}%"
        except:
            pass
        
        # BTC Dominance (mock veya cache)
        dom = cache_get("btc_dominance", 54.2)
        metrics["btc_dominance"] = f"{dom:.1f}%"
        
        # Sentiment (F&G bazlı)
        try:
            fng_idx = int(fng_data.get("value", 50))
            if fng_idx >= 70:
                metrics["sentiment"] = "Extreme Greed"
            elif fng_idx >= 55:
                metrics["sentiment"] = "Greed"
            elif fng_idx >= 45:
                metrics["sentiment"] = "Neutral"
            elif fng_idx >= 25:
                metrics["sentiment"] = "Fear"
            else:
                metrics["sentiment"] = "Extreme Fear"
        except:
            pass
        
        return metrics
    except Exception as e:
        logger.warning("Market metrics collection error: %s", e)
        return {
            "volume_24h": "$0",
            "open_interest": "$0",
            "fear_and_greed": "0 (Unknown)",
            "funding_rate": "0.0000%",
            "btc_dominance": "0.0%",
            "sentiment": "Neutral"
        }


def _broadcast_loop() -> None:
    from .extensions import socketio

    logger.info("[BROADCAST LOOP] Starting price_update_batch broadcast thread")
    broadcast_count = 0
    
    while True:
        time.sleep(_BROADCAST_INTERVAL)
        batch: dict[str, float] = {}
        with _cache_lock:
            for key, value in _cache.items():
                if key.startswith("rt_price_"):
                    batch[key[len("rt_price_"):]] = value

        try:
            # Market metrics'i ekle (her zaman emit et, boş batch da sorun değil)
            metrics = _get_market_metrics()
            payload = {
                "prices": batch,
                "metrics": metrics,
                "timestamp": time.time()
            }
            # Broadcast to all connected clients
            socketio.emit("price_update_batch", payload, broadcast=True, skip_sid=None)
            broadcast_count += 1
            
            # Her 10. broadcast'te log et (spam'ı azalt)
            if broadcast_count % 10 == 0:
                logger.info("[BROADCAST] #%d Emitted metrics. Prices in cache: %d", broadcast_count, len(batch))
        except Exception as exc:
            logger.exception("[BROADCAST ERROR] Failed to emit price_update_batch: %s", exc)


def start_binance_ws_thread() -> None:
    global _thread_started
    if _thread_started:
        return

    _thread_started = True
    threading.Thread(target=run_binance_ws, daemon=True).start()
    threading.Thread(target=_broadcast_loop, daemon=True).start()
