# -*- coding: utf-8 -*-
"""ZKR Analiz background jobs — FAZ 8.

Centralizes all background threads/loops that were previously in
legacy_monolith.py.  No thread starts at import time; everything
runs only when ``start_background_jobs()`` is called explicitly.

Moved here:
    - binance_ticker_ws_loop   (continuous Binance WS ticker stream)
    - refresh_loop             (60 s cache refresher for chat context)
    - refresh_top4h_loop       (15 min top-500 4h klines dataset)
    - fetch_4h_klines_for_symbols / build_top_coins_4h_dataset (helpers)
    - start_background_jobs    (idempotent orchestrator via JobManager)
"""
from __future__ import annotations

import logging

_logger = logging.getLogger("zkr_analiz.jobs")

import json
import os
import threading
import time
from typing import List

import websocket

from app.cache import cache_set, cache_get_or_set, utcnow
from app.extensions import socketio
from app.core.alert_engine import alert_check_loop
from app.core.opportunity_engine import opportunity_scan_loop
from app.core.yahoo_client import preload_yahoo_caches
from app.extensions import job_manager
from app.blueprints.signals.engine import evaluate_entry_signal
from app.core.thresholds import get_thresholds
from app.core.binance_client import (
    binance_klines,
    fng_latest,
    pump_candidates,
    get_binance_usdt_map,
    coingecko_top_by_marketcap,
    get_klines_bulk,
)
from app.core.etf_tracker import fetch_dynamic_etf_events
from app.core.thresholds import DEFAULT_THRESHOLDS, THRESHOLDS_KEY
from app.blueprints.chat.context import (
    build_chat_context,
    warm_chat_context_async,
    CHAT_REFRESH_SEC,
)

# --------------- Configuration (from env / Config) ---------------
TOP4H_REFRESH_SEC = int(os.getenv("TOP4H_REFRESH_SEC", "900"))   # 15 min
TOP4H_MAX_SYMBOLS = int(os.getenv("TOP4H_MAX_SYMBOLS", "500"))
TOP4H_KLINES = int(os.getenv("TOP4H_KLINES", "500"))
TOP4H_INTERVAL = "4h"

BINANCE_TICKER_STREAM = "wss://stream.binance.com:9443/ws/!ticker@arr"
TICKERS_KEY = "binance_top_tickers_v1"


# -------------------- Binance Realtime WebSocket --------------------

def on_ws_message(ws, message):
    try:
        data = json.loads(message)
        # Binance '!ticker@arr' stream'i tüm coinleri bir liste olarak gönderir
        for coin in data:
            symbol = coin.get('s')  # Sembol (Örn: BTCUSDT)
            
            # Sadece USDT çiftlerini filtreleyerek belleği (RAM) koruyalım
            if symbol and symbol.endswith("USDT"):
                current_price = float(coin.get('c', 0))      # Anlık Fiyat
                change_24h_pct = float(coin.get('P', 0))     # 24 Saatlik Yüzde Değişim
                volume_24h = float(coin.get('q', 0))         # 24 Saatlik Hacim (USDT bazlı)

                # app.py içindeki cache_set metodunu kullanarak anlık veriyi kaydediyoruz
                cache_set(f"rt_price_{symbol}", current_price)
                cache_set(f"rt_change_{symbol}", change_24h_pct)
                cache_set(f"rt_vol_{symbol}", volume_24h)
                socketio.emit(
                    'price_update',
                    {
                        'symbol': symbol,
                        'price': current_price,
                        'change24_pct': change_24h_pct,
                        'volume24': volume_24h,
                    },
                    broadcast=True,
                )
    except Exception as e:
        pass # Hata durumunda döngüyü kırma


def on_ws_error(ws, error):
    print(f"[WebSocket Error] Binance bağlantı hatası: {error}")


def on_ws_close(ws, close_status_code, close_msg):
    print("[WebSocket Closed] Bağlantı koptu, 5 saniye içinde yeniden bağlanılıyor...")
    time.sleep(5)
    start_binance_ws_thread()


def run_binance_ws():
    # !ticker@arr tüm piyasanın 24s özetini ve anlık fiyatını saniyede bir gönderir
    socket_url = "wss://stream.binance.com:9443/ws/!ticker@arr"
    ws = websocket.WebSocketApp(
        socket_url,
        on_message=on_ws_message,
        on_error=on_ws_error,
        on_close=on_ws_close
    )
    ws.run_forever()


def start_binance_ws_thread():
    ws_thread = threading.Thread(target=run_binance_ws, daemon=True)
    ws_thread.start()


# =====================================================================
#  2) refresh_loop — 60 s chat-context refresher
# =====================================================================
def refresh_loop() -> None:
    """Refresh klines, FNG, pump candidates, ETF events, and chat context every 60 s."""
    while True:
        try:
            # BTC 1d klines
            df = binance_klines("BTCUSDT", "1d", 400)
            cache_set("btc_1d_df", df)

            # Fear & Greed (self-caching)
            _ = fng_latest()

            # Pump candidates
            pumps = pump_candidates(limit_pairs=40)
            cache_set("pump_candidates_v1", pumps)

            # ETF events
            etf = fetch_dynamic_etf_events()
            cache_set("etf_events", etf)

            # Chat context
            ctx = build_chat_context()
            cache_set("chat_context", ctx)
        except Exception as e:
            _logger.error("refresh_loop error: %s", e, exc_info=True)
        time.sleep(CHAT_REFRESH_SEC)


# =====================================================================
#  3) Top-500 4h klines helpers
# =====================================================================
def fetch_4h_klines_for_symbols(
    symbols: List[str], limit_candles: int = 500
) -> dict:
    """Fetch 4h klines for a list of symbols from Binance."""
    res = {}
    raw_klines = get_klines_bulk(symbols, interval=TOP4H_INTERVAL, limit=limit_candles)
    for sb, arr in raw_klines.items():
        try:
            rows = []
            for a in arr:
                rows.append([
                    int(a[0]),
                    float(a[1]),
                    float(a[2]),
                    float(a[3]),
                    float(a[4]),
                    float(a[5]),
                    int(a[6]),
                ])
            res[sb] = rows
        except Exception:
            continue
    return res


def build_top_coins_4h_dataset(
    max_symbols: int = TOP4H_MAX_SYMBOLS, klines: int = TOP4H_KLINES
) -> dict:
    """Build top-500 market-cap coins 4h klines dataset."""
    cg_list = coingecko_top_by_marketcap(limit=max_symbols)
    usdt_map = get_binance_usdt_map()

    mapped = []
    for c in cg_list:
        base_sym = (c.get("symbol") or "").upper()
        name = c.get("name")
        rank = c.get("market_cap_rank")
        cg_id = c.get("id")
        mcap = c.get("market_cap")
        px = c.get("current_price")
        ch24 = c.get("price_change_percentage_24h") or 0

        binance_symbol = usdt_map.get(base_sym)
        if not binance_symbol:
            aliases = {"WBTC": "BTC", "WETH": "ETH"}
            alt = aliases.get(base_sym)
            if alt and alt in usdt_map:
                binance_symbol = usdt_map[alt]

        if binance_symbol:
            mapped.append({
                "cg_id": cg_id,
                "name": name,
                "ticker": base_sym,
                "rank": rank,
                "market_cap": mcap,
                "price": px,
                "change24_pct": ch24,
                "binance_symbol": binance_symbol,
            })

    symbols = [m["binance_symbol"] for m in mapped]
    kmap = fetch_4h_klines_for_symbols(symbols, limit_candles=klines)

    final = []
    for m in mapped:
        sb = m["binance_symbol"]
        if sb in kmap:
            final.append({**m, "klines_4h": kmap[sb]})

    payload = {
        "generated_at": utcnow().isoformat(),
        "interval": TOP4H_INTERVAL,
        "candles": klines,
        "total_requested": len(mapped),
        "total_with_klines": len(final),
        "rows": final,
    }
    return payload


# =====================================================================
#  4) refresh_top4h_loop — 15 min top-500 4h klines dataset
# =====================================================================
def refresh_top4h_loop() -> None:
    """Refresh top-500 market cap 4h klines dataset every 15 minutes."""
    while True:
        try:
            dataset = build_top_coins_4h_dataset(
                max_symbols=TOP4H_MAX_SYMBOLS,
                klines=TOP4H_KLINES,
            )
            cache_set("top_coins_4h_dataset", dataset)
        except Exception as e:
            _logger.error("refresh_top4h_loop error: %s", e, exc_info=True)
        time.sleep(TOP4H_REFRESH_SEC)


# =====================================================================
#  New: refresh_signals_loop — 5 min evaluate top pump candidates
# =====================================================================
def refresh_signals_loop() -> None:
    """Evaluate entry signals for top pump candidates and cache results every 5 minutes."""
    INTERVAL = 300  # 5 minutes
    while True:
        try:
            # Get pump candidates (freshen cache via cache_get_or_set)
            lst = cache_get_or_set("pump_candidates_v1", 300, pump_candidates, limit_pairs=40)
            if not lst:
                time.sleep(INTERVAL)
                continue

            top_rows = lst[:20]
            th = get_thresholds()
            out = []
            for r in top_rows:
                try:
                    sym = r["symbol"]
                    sig = evaluate_entry_signal(sym, r, thresholds=th)

                    # Build a compact summary for frontend (avoid heavy arrays)
                    levels = []
                    for t in (sig.get("pullback_targets") or [])[:3]:
                        try:
                            levels.append({"label": t.get("label"), "price": float(t.get("price"))})
                        except Exception:
                            continue

                    summary = {
                        "symbol": sym,
                        "decision": sig.get("decision"),
                        "score": round(float(r.get("score") or 0.0), 2),
                        "change24_pct": float(r.get("change24_pct") or 0.0),
                        "levels": levels,
                    }
                    out.append(summary)
                except Exception:
                    continue

            data = {"generated_at": utcnow().isoformat(), "rows": out}
            cache_set("latest_signals", data)
            try:
                cache_set("latest_signals_json", json.dumps(data, separators=(',',':')))
            except Exception:
                pass
        except Exception as e:
            _logger.error("refresh_signals_loop error: %s", e, exc_info=True)
        time.sleep(INTERVAL)


# =====================================================================
#  5) start_background_jobs — idempotent orchestrator
# =====================================================================
def start_background_jobs(app=None) -> None:
    """Register and start all background jobs via JobManager (idempotent).

    This is the single entry point for starting background work.
    Safe to call multiple times — JobManager.start_all() is idempotent.
    No thread starts at import time.
    Skips job startup when TESTING env var is set or app.config["TESTING"] is True.
    """
    # Skip background jobs during testing
    testing = os.environ.get("TESTING", "").lower() in ("1", "true")
    test_mode = os.environ.get("TEST_MODE", "").lower() in ("1", "true")
    if app and app.config.get("TESTING"):
        testing = True
    if app and app.config.get("TEST_MODE"):
        test_mode = True
    if testing or test_mode:
        _logger.info("TESTING/TEST_MODE — skipping background jobs")
        return

    # Ensure WAL mode on all databases at startup
    try:
        from app.core.db_manager import ensure_all_wal
        wal_results = ensure_all_wal()
        _logger.info("WAL migration: %s", wal_results)
    except Exception as e:
        _logger.warning("WAL migration skipped: %s", e)

    # Seed initial cache values
    try:
        cache_set(THRESHOLDS_KEY, DEFAULT_THRESHOLDS.copy())
    except Exception:
        pass

    try:
        cache_set(
            "chat_context",
            {"generated_at": utcnow().isoformat(), "status": "warming_up"},
        )
        warm_chat_context_async()
    except Exception:
        pass

    # Register jobs (once) then start via JobManager
    try:
        job_manager.register_thread("zkr_analiz:ticker_ws", run_binance_ws)
        job_manager.register_thread("zkr_analiz:refresh", refresh_loop)
        job_manager.register_thread("zkr_analiz:refresh_top4h", refresh_top4h_loop)
        job_manager.register_thread("zkr_analiz:refresh_signals", refresh_signals_loop)
        job_manager.register_thread("zkr_analiz:alert_check", alert_check_loop)
        job_manager.register_thread("zkr_analiz:opportunity_scan", opportunity_scan_loop)
        job_manager.register_thread("zkr_analiz:yahoo_preload", preload_yahoo_caches)
        job_manager.register_thread("zkr_analiz:live_engine", _boot_live_engine)
        job_manager.register_thread("zkr_analiz:activity_stream", _boot_activity_stream)
    except Exception:
        # ignore duplicate registration or unexpected errors
        pass

    job_manager.start_all()


# =====================================================================
#  6) Delayed-start helpers (moved from legacy_monolith.py)
# =====================================================================
def _boot_live_engine() -> None:
    """Start the strategy live engine after a short delay."""
    import time
    time.sleep(3)
    try:
        from app.core.strategy_live_engine import live_engine as strategy_live_engine
        strategy_live_engine.start()
        _logger.info("Strategy Live Engine started successfully")
    except Exception as e:
        _logger.error("Strategy Live Engine start failed: %s", e, exc_info=True)


def _boot_activity_stream() -> None:
    """Start the activity stream collection loop after a delay."""
    import time
    time.sleep(8)
    while True:
        try:
            from app.core import activity_stream_engine as _ase
            _ase.activity_collect_loop()
        except Exception as e:
            _logger.error("Activity Stream loop crashed, restarting in 30s: %s", e, exc_info=True)
            time.sleep(30)
