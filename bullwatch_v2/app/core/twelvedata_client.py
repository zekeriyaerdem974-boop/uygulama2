# -*- coding: utf-8 -*-
"""Twelve Data websocket client for TradFi price streaming."""
from __future__ import annotations

import json
import logging
import os
import time
import websocket

from app.cache import cache_set
from app.core.symbol_dictionary import SYMBOL_MAP, is_supported_by_twelvedata, get_twelvedata_symbol

_logger = logging.getLogger("zkr_analiz.twelvedata")

TWELVEDATA_PRICE_WS = "wss://ws.twelvedata.com/v1/quotes/price"

# Build supported symbols list from SYMBOL_MAP (only those with twelvedata support)
def _get_supported_symbols() -> list[str]:
    """Get list of symbols supported by TwelveData from SYMBOL_MAP."""
    supported = []
    for ui_symbol, config in SYMBOL_MAP.items():
        td_symbol = config.get('twelvedata')
        if td_symbol is not None:  # Not None = supported
            supported.append(td_symbol)
    return supported

TWELVEDATA_SYMBOLS = _get_supported_symbols()  # Dynamic list from SYMBOL_MAP


def _get_api_key() -> str:
    return os.getenv("TWELVEDATA_API_KEY", "").strip()


def _build_subscribe_payload(api_key: str) -> str:
    return json.dumps({
        "action": "subscribe",
        "symbols": ",".join(TWELVEDATA_SYMBOLS),
        "apikey": api_key,
    })


def on_td_message(ws, message, price_buffer, price_buffer_lock):
    try:
        data = json.loads(message)
    except Exception as exc:
        _logger.exception("Twelve Data message JSON parse failed: %s", exc)
        return

    if not isinstance(data, dict):
        return

    event = data.get("event") or data.get("type")
    if event != "price":
        return

    symbol = data.get("symbol") or data.get("instrument") or data.get("ticker")
    if not symbol:
        return

    raw_price = data.get("price") or data.get("close") or data.get("last")
    try:
        current_price = float(raw_price)
    except (TypeError, ValueError):
        return

    with price_buffer_lock:
        cache_set(f"rt_price_{symbol}", current_price)
        price_buffer[symbol] = current_price

    _logger.debug("Twelve Data price event %s=%s added to price_buffer", symbol, current_price)


def on_td_open(ws, api_key: str):
    try:
        payload = _build_subscribe_payload(api_key)
        ws.send(payload)
        _logger.info("Twelve Data WS connection opened and subscribe message sent: %s", payload)
    except Exception as exc:
        _logger.exception("Twelve Data subscribe failed: %s", exc)


def on_td_error(ws, error):
    _logger.error("Twelve Data WS error: %s", error)


def on_td_close(ws, close_status_code, close_msg):
    _logger.warning("Twelve Data WS closed: %s %s", close_status_code, close_msg)
    time.sleep(5)


def run_twelvedata_ws(price_buffer, price_buffer_lock) -> None:
    api_key = _get_api_key()
    if not api_key:
        _logger.warning("Twelve Data API Key bulunamadı, TradFi akışı başlatılmadı")
        return

    socket_url = f"{TWELVEDATA_PRICE_WS}?apikey={api_key}"
    ws = websocket.WebSocketApp(
        socket_url,
        on_message=lambda ws, msg: on_td_message(ws, msg, price_buffer, price_buffer_lock),
        on_error=on_td_error,
        on_close=on_td_close,
        on_open=lambda ws: on_td_open(ws, api_key),
    )
    ws.run_forever()
