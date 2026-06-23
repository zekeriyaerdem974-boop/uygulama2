# -*- coding: utf-8 -*-
"""Yahoo Finance client — shared helper for stocks, BIST, forex, commodities.

FAZ 16 + FAZ 17 — Multi-market data abstraction layer.
FAZ 24B — Fixed: batch price fetching via yf.download() so symbols
arrive with REAL prices instead of zeros.

Key optimization: get_symbols_info() uses yf.download() for batch fetching
instead of per-symbol API calls, avoiding Yahoo rate limits.

Provides unified interface:
  get_symbols_info(symbol_list)  -> list of symbol dicts (with real prices)
  get_ticker(symbol)             -> ticker dict (with timeout protection)
  get_klines(symbol, interval, limit) -> list of OHLCV dicts
"""
from __future__ import annotations

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutTimeoutError
FuturesTimeout = FutTimeoutError  # alias for backward compat
from typing import List, Dict, Optional

import pandas as pd

_logger = logging.getLogger("zkr_analiz.yahoo")

# Silence yfinance verbose DEBUG logging — it forces single-threaded mode
# when DEBUG is enabled, making batch downloads 10x slower
logging.getLogger("yfinance").setLevel(logging.WARNING)
logging.getLogger("peewee").setLevel(logging.WARNING)

try:
    import yfinance as yf
except ImportError:
    yf = None
    _logger.warning("yfinance not installed — Yahoo data unavailable")

# ── Interval mapping: our intervals → yfinance intervals ──
_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "1h",       # yfinance doesn't have 4h, we resample
    "1d": "1d",
    "1w": "1wk",
    "1M": "1mo",
}

# Period mapping based on interval for yfinance
_PERIOD_MAP = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "1h": "730d",
    "4h": "730d",
    "1d": "2y",
    "1w": "5y",
    "1M": "max",
}

# ── Background batch price cache ──────────────────────────────────────
# Stores {symbol: {lastPrice, pct, volume, ts}} from background thread
_batch_cache: Dict[str, Dict] = {}
_batch_cache_lock = threading.Lock()
_batch_cache_ts: float = 0          # last successful batch time
_BATCH_CACHE_TTL = 300              # 5 min — stale-while-revalidate triggers refresh
_BATCH_STALE_TTL = 1800            # 30 min — max age before data is considered too old
_batch_thread: Optional[threading.Thread] = None

# Per-market download locks to prevent concurrent batch downloads
_market_download_locks: Dict[str, threading.Lock] = {}
_market_download_meta_lock = threading.Lock()

def _get_market_lock(market_type: str) -> threading.Lock:
    with _market_download_meta_lock:
        if market_type not in _market_download_locks:
            _market_download_locks[market_type] = threading.Lock()
        return _market_download_locks[market_type]

# ThreadPoolExecutor for timeout-protected individual calls
_executor = ThreadPoolExecutor(max_workers=4)


def _yf_available():
    """Check if yfinance is available."""
    return yf is not None


# ══════════════════════════════════════════════════════════════════════
# BATCH PRICE FETCHING — the core fix for FAZ 24B
# ══════════════════════════════════════════════════════════════════════

def _parse_download_df(df, symbols: List[str]) -> Dict[str, Dict]:
    """Parse a yf.download() DataFrame into {symbol: {lastPrice, pct, ...}} dict."""
    results = {}
    if df is None or df.empty:
        return results

    if len(symbols) == 1:
        sym = symbols[0]
        if "Close" in df.columns and len(df) > 0:
            last_close = float(df["Close"].iloc[-1])
            prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else 0
            volume = float(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0
            pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0
            if last_close > 0:
                results[sym] = {
                    "lastPrice": round(last_close, 6),
                    "pct": round(pct, 4),
                    "prevClose": round(prev_close, 6),
                    "volume": round(volume, 2),
                }
    else:
        for sym in symbols:
            try:
                if sym not in df.columns.get_level_values(1):
                    continue
                close_series = df[("Close", sym)].dropna()
                if len(close_series) == 0:
                    continue
                last_close = float(close_series.iloc[-1])
                prev_close = float(close_series.iloc[-2]) if len(close_series) > 1 else 0
                try:
                    vol_series = df[("Volume", sym)].dropna()
                    volume = float(vol_series.iloc[-1]) if len(vol_series) > 0 else 0
                except Exception:
                    volume = 0
                pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0
                if last_close > 0:
                    results[sym] = {
                        "lastPrice": round(last_close, 6),
                        "pct": round(pct, 4),
                        "prevClose": round(prev_close, 6),
                        "volume": round(volume, 2),
                    }
            except Exception as exc:
                _logger.debug("Symbol %s parse error: %s", sym, exc)
    return results


def _batch_download_prices(symbols: List[str], chunk_size: int = 50,
                           timeout_per_chunk: float = 30.0) -> Dict[str, Dict]:
    """Download prices for many symbols using yf.download() batch API.

    FAZ 25: For <=500 symbols uses a SINGLE yf.download() call which is
    3-4x faster than chunking (7s vs 26s for 499 BIST symbols).
    Falls back to chunked download for >500 symbols.

    Returns: {symbol: {lastPrice, pct, prevClose, volume}} for symbols with data
    """
    if not _yf_available():
        return {}

    total = len(symbols)

    # ── Fast path: single download for <=500 symbols ──
    if total <= 500:
        _logger.info("Single-call download for %d symbols...", total)
        chunk_str = " ".join(symbols)

        def _do_download():
            return yf.download(chunk_str, period="2d", interval="1d",
                               progress=False, threads=True, timeout=60)

        try:
            with ThreadPoolExecutor(max_workers=1) as exe:
                future = exe.submit(_do_download)
                df = future.result(timeout=70)
            results = _parse_download_df(df, symbols)
            _logger.info("Single-call got %d/%d prices", len(results), total)
            return results
        except (FutTimeoutError, Exception) as exc:
            _logger.warning("Single-call failed (%s), falling back to chunks", exc)

    # ── Chunked fallback for >500 symbols or single-call failure ──
    results = {}
    for i in range(0, total, chunk_size):
        chunk = symbols[i:i + chunk_size]
        chunk_str = " ".join(chunk)
        chunk_num = i // chunk_size + 1
        total_chunks = (total + chunk_size - 1) // chunk_size

        try:
            _logger.info("Batch chunk %d/%d (%d symbols)...",
                         chunk_num, total_chunks, len(chunk))

            def _do_download_chunk(cs=chunk_str):
                return yf.download(cs, period="2d", interval="1d",
                                   progress=False, threads=True,
                                   timeout=timeout_per_chunk)

            with ThreadPoolExecutor(max_workers=1) as exe:
                future = exe.submit(_do_download_chunk)
                try:
                    df = future.result(timeout=timeout_per_chunk + 10)
                except (FutTimeoutError, Exception):
                    _logger.warning("Chunk %d/%d HARD TIMEOUT", chunk_num, total_chunks)
                    continue

            parsed = _parse_download_df(df, chunk)
            results.update(parsed)
            _logger.info("Chunk %d/%d: got %d prices so far",
                         chunk_num, total_chunks, len(results))
        except Exception as exc:
            _logger.warning("Batch chunk %d failed: %s", chunk_num, exc)
            continue

        if i + chunk_size < total:
            time.sleep(0.2)

    return results


def _update_batch_cache(symbols: List[str], market_type: str):
    """Update the global batch cache with fresh prices."""
    global _batch_cache_ts

    prices = _batch_download_prices(symbols)

    with _batch_cache_lock:
        for sym, data in prices.items():
            _batch_cache[sym] = {**data, "ts": time.time(), "market": market_type}
        _batch_cache_ts = time.time()

    ok = len(prices)
    total = len(symbols)
    _logger.info("Batch cache updated for %s: %d/%d symbols have prices (%.1f%%)",
                 market_type, ok, total, (ok / total * 100) if total else 0)
    return prices


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def _build_result_from_cache(symbols: List[str], market_type: str) -> List[Dict]:
    """Build symbol list from whatever is in batch cache right now."""
    result = []
    with _batch_cache_lock:
        for sym in symbols:
            cached = _batch_cache.get(sym, {})
            result.append({
                "symbol": sym,
                "base": sym.replace(".IS", "").replace("=X", "").replace("=F", ""),
                "lastPrice": cached.get("lastPrice", 0),
                "pct": cached.get("pct", 0),
                "volume": cached.get("volume", 0),
                "market": market_type,
            })
    return result


def _background_refresh(symbols: List[str], market_type: str):
    """Refresh batch cache in background thread (fire-and-forget)."""
    market_lock = _get_market_lock(market_type)
    if not market_lock.acquire(blocking=False):
        return  # another refresh already running
    try:
        _update_batch_cache(symbols, market_type)
    finally:
        market_lock.release()


def get_symbols_info(symbols: List[str], market_type: str = "unknown") -> List[Dict]:
    """Get symbol list WITH real prices via batch download.

    FAZ 25: Stale-while-revalidate pattern. Returns cached data INSTANTLY
    even if stale, and triggers background refresh. Only blocks on first
    ever call when no cache exists at all.

    Returns list of dicts with: symbol, base, lastPrice, pct, market
    """
    now = time.time()

    # Check how much cache we have
    with _batch_cache_lock:
        cached_count = sum(1 for s in symbols if s in _batch_cache)
        any_fresh = any(
            (now - _batch_cache.get(s, {}).get("ts", 0)) < _BATCH_CACHE_TTL
            for s in symbols if s in _batch_cache
        )

    # ── FAST PATH: have cache (fresh or stale) — return immediately ──
    if cached_count > 0:
        result = _build_result_from_cache(symbols, market_type)

        # If stale, trigger background refresh (non-blocking)
        if not any_fresh:
            _logger.info("Stale cache for %s, triggering background refresh", market_type)
            t = threading.Thread(target=_background_refresh,
                                 args=(symbols, market_type), daemon=True)
            t.start()

        return result

    # ── COLD START: no cache at all — must block and fetch ──
    market_lock = _get_market_lock(market_type)
    if not market_lock.acquire(timeout=90):
        _logger.warning("Timeout waiting for %s download lock", market_type)
    else:
        try:
            # Double-check after acquiring lock (check+release, then fetch)
            with _batch_cache_lock:
                already_cached = any(s in _batch_cache for s in symbols)

            if not already_cached:
                _logger.info("Cold start: fetching %d %s symbols...",
                             len(symbols), market_type)
                _update_batch_cache(symbols, market_type)
        finally:
            market_lock.release()

    return _build_result_from_cache(symbols, market_type)


def get_ticker(symbol: str) -> Dict:
    """Get real-time ticker data for a symbol with timeout protection.

    FAZ 24B: Added 15s timeout to prevent server from hanging.
    First checks batch cache, falls back to individual yf.Ticker() call.

    Returns dict with: symbol, lastPrice, priceChange, priceChangePercent,
                       highPrice, lowPrice, volume, quoteVolume
    """
    if not _yf_available():
        raise RuntimeError("yfinance not installed")

    # Check batch cache first (much faster than individual call)
    with _batch_cache_lock:
        cached = _batch_cache.get(symbol)

    if cached and cached.get("lastPrice", 0) > 0:
        age = time.time() - cached.get("ts", 0)
        last_price = cached.get("lastPrice", 0)
        pct = cached.get("pct", 0)
        prev_close = cached.get("prevClose", 0)
        volume = cached.get("volume", 0)
        price_change = last_price - prev_close if prev_close else 0
        result = {
            "symbol": symbol,
            "lastPrice": last_price,
            "priceChange": round(price_change, 6),
            "priceChangePercent": pct,
            "highPrice": last_price,
            "lowPrice": last_price,
            "volume": volume,
            "quoteVolume": round(last_price * volume, 2) if last_price and volume else 0,
            "weightedAvgPrice": last_price,
        }
        # Stale-while-revalidate: return cached data instantly, refresh in bg
        if age > _BATCH_CACHE_TTL:
            _logger.debug("Stale ticker %s (%.0fs old), bg refresh", symbol, age)
            threading.Thread(target=_bg_refresh_single, args=(symbol,), daemon=True).start()
        return result

    # Fallback: individual fetch with timeout
    def _fetch_single():
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info

        last_price = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
        prev_close = float(info.get("previousClose", 0) or info.get("previous_close", 0) or 0)
        day_high = float(info.get("dayHigh", 0) or info.get("day_high", 0) or 0)
        day_low = float(info.get("dayLow", 0) or info.get("day_low", 0) or 0)
        volume = float(info.get("lastVolume", 0) or info.get("last_volume", 0) or 0)

        price_change = last_price - prev_close if prev_close else 0
        pct_change = (price_change / prev_close * 100) if prev_close else 0

        return {
            "symbol": symbol,
            "lastPrice": last_price,
            "priceChange": round(price_change, 6),
            "priceChangePercent": round(pct_change, 4),
            "highPrice": day_high,
            "lowPrice": day_low,
            "volume": volume,
            "quoteVolume": round(last_price * volume, 2) if last_price and volume else 0,
            "weightedAvgPrice": round((day_high + day_low) / 2, 6) if day_high and day_low else last_price,
        }

    try:
        future = _executor.submit(_fetch_single)
        result = future.result(timeout=8)  # 8 second timeout
        _update_single_cache(symbol, result)
        return result
    except FuturesTimeout:
        _logger.warning("Ticker fetch TIMEOUT (8s) for %s", symbol)
        return {
            "symbol": symbol,
            "lastPrice": 0,
            "priceChange": 0,
            "priceChangePercent": 0,
            "highPrice": 0,
            "lowPrice": 0,
            "volume": 0,
            "quoteVolume": 0,
            "weightedAvgPrice": 0,
        }
    except Exception as exc:
        _logger.warning("Ticker fetch failed for %s: %s", symbol, exc)
        raise


def _update_single_cache(symbol: str, result: Dict):
    """Store individual ticker result in batch cache."""
    with _batch_cache_lock:
        _batch_cache[symbol] = {
            "lastPrice": result["lastPrice"],
            "pct": result["priceChangePercent"],
            "prevClose": result["lastPrice"] - result["priceChange"] if result["priceChange"] else 0,
            "volume": result["volume"],
            "ts": time.time(),
        }


def _bg_refresh_single(symbol: str):
    """Background refresh a single ticker."""
    try:
        def _fetch():
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            last_price = float(info.get("lastPrice", 0) or info.get("last_price", 0) or 0)
            prev_close = float(info.get("previousClose", 0) or info.get("previous_close", 0) or 0)
            volume = float(info.get("lastVolume", 0) or info.get("last_volume", 0) or 0)
            price_change = last_price - prev_close if prev_close else 0
            pct_change = (price_change / prev_close * 100) if prev_close else 0
            return {
                "lastPrice": last_price,
                "priceChangePercent": round(pct_change, 4),
                "priceChange": round(price_change, 6),
                "volume": volume,
            }
        future = _executor.submit(_fetch)
        result = future.result(timeout=10)
        if result["lastPrice"] > 0:
            _update_single_cache(symbol, result)
    except Exception:
        pass  # silent bg refresh


def get_klines(symbol: str, interval: str = "1d", limit: int = 500) -> List[Dict]:
    """Get OHLCV candlestick data with timeout protection.

    Returns list of dicts with: open_time, open, high, low, close, volume
    """
    if not _yf_available():
        raise RuntimeError("yfinance not installed")

    yf_interval = _INTERVAL_MAP.get(interval, "1d")
    period = _PERIOD_MAP.get(interval, "1y")

    def _fetch_klines():
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=yf_interval)

        if df is None or df.empty:
            _logger.warning("No kline data for %s/%s", symbol, interval)
            return []

        # Resample 4h from 1h data
        if interval == "4h" and yf_interval == "1h":
            df = df.resample("4h").agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }).dropna()

        rows = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp() * 1000)
            rows.append({
                "open_time": ts,
                "open": round(float(row.get("Open", 0)), 6),
                "high": round(float(row.get("High", 0)), 6),
                "low": round(float(row.get("Low", 0)), 6),
                "close": round(float(row.get("Close", 0)), 6),
                "volume": round(float(row.get("Volume", 0)), 2),
            })

        # Apply limit
        if len(rows) > limit:
            rows = rows[-limit:]

        return rows

    try:
        future = _executor.submit(_fetch_klines)
        return future.result(timeout=30)  # 30 second timeout for klines
    except FuturesTimeout:
        _logger.warning("Klines fetch TIMEOUT (30s) for %s/%s", symbol, interval)
        return []
    except Exception as exc:
        _logger.warning("Kline fetch failed for %s/%s: %s", symbol, interval, exc)
        raise


def _symbol_stub(sym: str, market_type: str) -> Dict:
    """Return a placeholder symbol dict when data is unavailable."""
    return {
        "symbol": sym,
        "base": sym.replace(".IS", "").replace("=X", "").replace("=F", ""),
        "lastPrice": 0,
        "pct": 0,
        "market": market_type,
    }


def _symbols_fallback(symbols: List[str], market_type: str) -> List[Dict]:
    """Return all symbols as stubs when batch download fails entirely."""
    return [_symbol_stub(sym, market_type) for sym in symbols]


# ══════════════════════════════════════════════════════════════════════
# BACKGROUND PRELOAD — warm caches on server startup
# ══════════════════════════════════════════════════════════════════════

def preload_yahoo_caches():
    """Pre-warm batch caches for all Yahoo-backed markets.

    FAZ 25: Called from background jobs on server startup.
    Downloads BIST, Stocks, Forex, Commodities prices so the first
    user request is served from cache instantly.
    """
    from app.core.bist_data import DEFAULT_SYMBOLS as BIST_SYMBOLS
    from app.core.stocks_data import DEFAULT_SYMBOLS as STOCK_SYMBOLS
    from app.core.forex_data import DEFAULT_SYMBOLS as FOREX_SYMBOLS
    from app.core.commodities_data import DEFAULT_SYMBOLS as COMMODITY_SYMBOLS

    markets = [
        ("bist", BIST_SYMBOLS),
        ("stocks", STOCK_SYMBOLS),
        ("forex", FOREX_SYMBOLS),
        ("commodities", COMMODITY_SYMBOLS),
    ]

    for market_type, symbols in markets:
        try:
            _logger.info("Preloading %d %s symbols...", len(symbols), market_type)
            t0 = time.time()
            _update_batch_cache(symbols, market_type)
            elapsed = time.time() - t0
            _logger.info("Preload %s complete in %.1fs", market_type, elapsed)
        except Exception as exc:
            _logger.warning("Preload %s failed: %s", market_type, exc)

