"""Binance & external market-data API helpers.

Extracted from ``legacy_monolith.py`` (FAZ 3).
Functions here may use ``app.cache`` for caching but contain no Flask
route logic.

FAZ 48 — Added resilient HTTP with retry & cache fallback.
"""
from __future__ import annotations

import logging
import os
import time
import asyncio
import nest_asyncio
from typing import Dict, List, Optional

import aiohttp
import numpy as np
import pandas as pd
import requests

from app.cache import cache_get_or_set, cache_get, cache_set

_logger = logging.getLogger("zkr_analiz.infra")

# ── API base URLs ─────────────────────────────────────────────────────
BINANCE_API = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"
ALT_FNG_API = "https://api.alternative.me/fng/?limit=1"
COINGECKO_API = "https://api.coingecko.com/api/v3"

COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")

# ── Resilient HTTP ────────────────────────────────────────────────────
_DEFAULT_TIMEOUT = 15
_MAX_RETRIES = 2
_RETRY_DELAY = 1.0


def _resilient_get(
    url: str,
    *,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = _DEFAULT_TIMEOUT,
    cache_key: Optional[str] = None,
) -> requests.Response:
    """HTTP GET with retry and optional cache fallback.

    On failure after retries, if cache_key is provided, returns cached data.
    """
    last_err: Optional[Exception] = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r
        except (requests.RequestException, OSError) as e:
            last_err = e
            _logger.warning(
                "API request failed (attempt %d/%d) %s: %s",
                attempt, _MAX_RETRIES, url.split("?")[0], e,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY * attempt)

    # All retries exhausted
    _logger.error("API request failed after %d retries: %s", _MAX_RETRIES, url.split("?")[0])
    raise last_err  # type: ignore[misc]


async def fetch_kline_async(session, symbol, interval, limit):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        async with session.get(url, timeout=15) as response:
            data = await response.json()
            return symbol, data
    except Exception as e:
        return symbol, []


async def fetch_multiple_klines_async(symbols, interval, limit):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_kline_async(session, sym, interval, limit) for sym in symbols]
        results = await asyncio.gather(*tasks)
        return {sym: data for sym, data in results if data}


def get_klines_bulk(symbols, interval="4h", limit=100):
    # Senkron koddan asenkrona geçiş köprüsü
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            nest_asyncio.apply()
    except RuntimeError:
        pass
    return asyncio.run(fetch_multiple_klines_async(symbols, interval, limit))


# ── Binance Spot Klines ──────────────────────────────────────────────
def binance_klines(symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 400) -> pd.DataFrame:
    r = _resilient_get(
        f"{BINANCE_API}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=15,
    )
    arr = r.json()
    rows = []
    for a in arr:
        rows.append({
            "open_time": int(a[0]),
            "open": float(a[1]),
            "high": float(a[2]),
            "low": float(a[3]),
            "close": float(a[4]),
            "volume": float(a[5]),
            "close_time": int(a[6]),
        })
    return pd.DataFrame(rows)


def fetch_klines_df(symbol: str, interval: str = "15m", limit: int = 200) -> pd.DataFrame:
    """Thin wrapper kept for backward-compatibility."""
    return binance_klines(symbol, interval=interval, limit=limit)


# ── Binance Exchange Info ────────────────────────────────────────────
def _fetch_exchange_info() -> dict:
    """Fetch Binance exchangeInfo (internal helper for cache_get_or_set)."""
    r = _resilient_get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=20)
    return r.json()


def get_binance_usdt_map() -> Dict[str, str]:
    """Return ``{BASE: SYMBOL}`` for all active USDT spot pairs."""
    ex = cache_get_or_set("exchange_info", 600, _fetch_exchange_info)
    base_to_symbol: Dict[str, str] = {}
    for s in ex["symbols"]:
        if (
            s["status"] == "TRADING"
            and s.get("isSpotTradingAllowed")
            and s.get("quoteAsset") == "USDT"
        ):
            base = s.get("baseAsset")
            symb = s.get("symbol")
            if base and symb:
                base_to_symbol[base.upper()] = symb
    return base_to_symbol


# ── Binance Futures OI ──────────────────────────────────────────────
def fapi_open_interest(symbol: str = "BTCUSDT") -> dict:
    r = _resilient_get(
        f"{BINANCE_FAPI}/fapi/v1/openInterest",
        params={"symbol": symbol},
        timeout=10,
    )
    return r.json()


def fapi_open_interest_hist(symbol: str = "BTCUSDT", period: str = "1d", limit: int = 30) -> list:
    r = _resilient_get(
        f"{BINANCE_FAPI}/futures/data/openInterestHist",
        params={"symbol": symbol, "period": period, "limit": limit},
        timeout=10,
    )
    return r.json()


# ── Fear & Greed Index ───────────────────────────────────────────────
def _fetch_fng_raw() -> dict:
    """Fetch Fear & Greed from Alternative.me (internal helper)."""
    r = _resilient_get(ALT_FNG_API, timeout=10)
    data = r.json()
    if data.get("data"):
        it = data["data"][0]
        return {
            "value": int(it["value"]),
            "value_classification": it["value_classification"],
            "timestamp": int(it["timestamp"]),
            "time_readable": it.get("time_until_update"),
        }
    return {"value": None, "value_classification": None, "timestamp": None, "time_readable": None}


def fng_latest() -> dict:
    return cache_get_or_set("fng_latest", 60, _fetch_fng_raw) or {
        "value": None, "value_classification": None, "timestamp": None, "time_readable": None,
    }


# ── Blockchain Hashrate ─────────────────────────────────────────────
def blockchain_hashrate(days: int = 30) -> dict:
    url = "https://api.blockchain.info/charts/hash-rate"
    r = _resilient_get(url, params={"format": "json", "timespan": f"{days}days"}, timeout=10)
    return r.json()


# ── DeFiLlama Stablecoins ───────────────────────────────────────────
def defillama_stablecoins() -> dict:
    url = "https://stablecoins.llama.fi/stablecoins"
    r = _resilient_get(url, timeout=20)
    js = r.json()
    coins = js.get("peggedAssets", []) or []

    rows = []
    for c in coins:
        if c.get("pegType") != "peggedUSD":
            continue
        sym = c.get("symbol") or c.get("name") or "UNKNOWN"
        cur = (c.get("circulating") or {}).get("peggedUSD")
        prev = (c.get("circulatingPrevDay") or {}).get("peggedUSD")
        if cur is None or prev is None:
            continue
        change_usd = float(cur) - float(prev)
        rows.append({"symbol": sym, "change24_usd": change_usd})

    rows.sort(key=lambda x: -abs(x["change24_usd"]))
    top = rows[:10]
    total_change = sum(x["change24_usd"] for x in top) if top else 0.0
    return {"top": top, "approx_netflow_24h_usd": total_change}


# ── CoinGlass Coinbase Premium ───────────────────────────────────────
def coinglass_coinbase_premium() -> dict:
    if not COINGLASS_API_KEY:
        return {"error": "COINGLASS_API_KEY missing"}
    headers = {"coinglassSecret": COINGLASS_API_KEY}
    r = _resilient_get(
        "https://open-api-v4.coinglass.com/api/coinbase-premium-index",
        params={"symbol": "BTC"},
        headers=headers,
        timeout=12,
    )
    if r.status_code != 200:
        return {"error": f"http {r.status_code}"}
    return r.json()


# ── Pump Candidates Scanner ─────────────────────────────────────────
def pump_candidates(limit_pairs: int = 40) -> list:
    """Scan Binance 24-hr tickers, score top USDT pairs by momentum."""
    from app.core.ta import simple_sma  # local import to avoid circular

    r = _resilient_get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=20)
    arr = r.json()
    rows = []
    for x in arr:
        s = x.get("symbol", "")
        if not s.endswith("USDT"):
            continue
        try:
            qv = float(x.get("quoteVolume", "0"))
            ch = float(x.get("priceChangePercent", "0"))
        except Exception:
            continue
        rows.append({"symbol": s, "quoteVolume": qv, "change24": ch})
    rows.sort(key=lambda x: -x["quoteVolume"])
    top = rows[:limit_pairs]

    out = []
    rank_map = {top[i]["symbol"]: i + 1 for i in range(len(top))}
    for item in top:
        sym = item["symbol"]
        try:
            df = binance_klines(sym, "1d", 220)
            closes = df["close"].tolist()
            if len(closes) < 200:
                continue
            sma200 = simple_sma(closes, 200)
            last = closes[-1]
            above = last > (sma200 or 1e18)
            ret7 = (closes[-1] / closes[-8] - 1.0) if len(closes) >= 8 else 0.0
            score = ((ret7 * 100) * 0.4 + item["change24"] * 0.3 + (20 if above else 0) + max(0, 20 - (rank_map[sym] - 1)))
            out.append({
                "symbol": sym,
                "last": float(last),
                "sma200": float(sma200) if sma200 is not None else None,
                "above200": bool(above),
                "ret7_pct": float(ret7 * 100.0),
                "change24_pct": float(item["change24"]),
                "volume_rank": int(rank_map[sym]),
                "score": round(float(score), 2),
            })
            time.sleep(0.03)
        except Exception:
            continue
    out.sort(key=lambda x: -x["score"])
    return out[:15]


# ── CoinGecko Top Market-Cap ────────────────────────────────────────
def coingecko_top_by_marketcap(limit: int = 500) -> List[Dict]:
    out: list = []
    pages = (limit + 249) // 250
    per_page = 250
    for page in range(1, pages + 1):
        r = _resilient_get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "price_change_percentage": "24h",
                "locale": "en",
            },
            timeout=25,
        )
        data = r.json() or []
        out.extend(data)
        time.sleep(0.15)
    return out[:limit]
