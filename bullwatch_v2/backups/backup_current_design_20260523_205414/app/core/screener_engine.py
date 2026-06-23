# -*- coding: utf-8 -*-
"""Multi-Market Screener Engine.

FAZ 17 — TradingView/Finviz-style screener across all markets.

Scans symbols for each market, computes technical metrics (EMA, SMA, RSI,
ATR, trend, support/resistance), and applies user-selected filters.

Usage:
    engine = ScreenerEngine()
    results = engine.scan("crypto", filters=["ema20_above_ema50", "rsi_above_60"])
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

import pandas as pd

from app.core.ta import (
    compute_rsi,
    ema_last,
    simple_sma,
    atr_last,
)

_logger = logging.getLogger("zkr_analiz.screener")

# ── Market scan limits (avoid heavy computation) ──────────────────────
_SCAN_LIMITS = {
    "crypto": 150,
    "stocks": 100,
    "bist": 80,
    "forex": 20,
    "commodities": 20,
}

# ── Filter registry ─────────────────────────────────────────────────
# Each filter is (name, description, callable(row_dict) -> bool)
_FILTERS = {}


def _register(name: str, desc: str):
    """Decorator to register a screener filter function."""
    def decorator(fn):
        _FILTERS[name] = {"desc": desc, "fn": fn}
        return fn
    return decorator


# ── Trend Filters ────────────────────────────────────────────────────
@_register("price_above_ema20", "Price > EMA 20")
def _f_price_above_ema20(r):
    return r["price"] > 0 and r["ema20"] and r["price"] > r["ema20"]


@_register("ema20_above_ema50", "EMA 20 > EMA 50")
def _f_ema20_above_ema50(r):
    return r["ema20"] and r["ema50"] and r["ema20"] > r["ema50"]


@_register("ema50_above_ema200", "EMA 50 > EMA 200")
def _f_ema50_above_ema200(r):
    return r["ema50"] and r["ema200"] and r["ema50"] > r["ema200"]


# ── Momentum Filters ────────────────────────────────────────────────
@_register("rsi_above_60", "RSI > 60 (Bullish)")
def _f_rsi_above_60(r):
    return r["rsi14"] is not None and r["rsi14"] > 60


@_register("rsi_below_30", "RSI < 30 (Oversold)")
def _f_rsi_below_30(r):
    return r["rsi14"] is not None and r["rsi14"] < 30


@_register("rsi_above_50", "RSI > 50")
def _f_rsi_above_50(r):
    return r["rsi14"] is not None and r["rsi14"] > 50


# ── Volume Filters ───────────────────────────────────────────────────
@_register("volume_spike", "Volume Spike (> 2x avg)")
def _f_volume_spike(r):
    return r.get("vol_ratio") is not None and r["vol_ratio"] > 2.0


# ── Breakout Filters ────────────────────────────────────────────────
@_register("price_near_resistance", "Price Near Resistance (< 2%)")
def _f_near_resistance(r):
    rd = r.get("resistance_distance")
    return rd is not None and 0 < rd < 2.0


@_register("price_breakout", "Price Breakout (above resistance)")
def _f_breakout(r):
    rd = r.get("resistance_distance")
    return rd is not None and rd <= 0


# ── Support Filters ─────────────────────────────────────────────────
@_register("price_near_support", "Price Near Support (< 2%)")
def _f_near_support(r):
    sd = r.get("support_distance")
    return sd is not None and 0 < sd < 2.0


# ── MA Cross Filters ────────────────────────────────────────────────
@_register("ema20_cross_ema50", "EMA 20 just crossed above EMA 50")
def _f_ema20_cross_ema50(r):
    return r.get("ema20_cross_ema50") is True


@_register("ema50_cross_ema200", "EMA 50 just crossed above EMA 200")
def _f_ema50_cross_ema200(r):
    return r.get("ema50_cross_ema200") is True


# ── Volatility Filters ──────────────────────────────────────────────
@_register("atr_high", "High Volatility (ATR > 3%)")
def _f_atr_high(r):
    return r.get("atr_pct") is not None and r["atr_pct"] > 3.0


@_register("atr_low", "Low Volatility (ATR < 1%)")
def _f_atr_low(r):
    return r.get("atr_pct") is not None and r["atr_pct"] < 1.0


# ── Composite Filters ───────────────────────────────────────────────
@_register("strong_uptrend", "Strong Uptrend (EMA stack + RSI>50)")
def _f_strong_uptrend(r):
    return (
        r["ema20"] and r["ema50"] and r["ema200"]
        and r["price"] > r["ema20"] > r["ema50"] > r["ema200"]
        and r["rsi14"] is not None and r["rsi14"] > 50
    )


@_register("strong_downtrend", "Strong Downtrend (reverse EMA stack)")
def _f_strong_downtrend(r):
    return (
        r["ema20"] and r["ema50"] and r["ema200"]
        and r["price"] < r["ema20"] < r["ema50"] < r["ema200"]
        and r["rsi14"] is not None and r["rsi14"] < 50
    )


def get_available_filters() -> List[Dict]:
    """Return list of available filter definitions for the frontend."""
    result = []
    for name, info in _FILTERS.items():
        # Categorize filters
        if "ema" in name and "cross" not in name or "price_above" in name:
            cat = "trend"
        elif "rsi" in name:
            cat = "momentum"
        elif "volume" in name:
            cat = "volume"
        elif "breakout" in name or "resistance" in name:
            cat = "breakout"
        elif "support" in name:
            cat = "support"
        elif "cross" in name:
            cat = "cross"
        elif "atr" in name:
            cat = "volatility"
        elif "uptrend" in name or "downtrend" in name:
            cat = "trend"
        else:
            cat = "other"
        result.append({"name": name, "desc": info["desc"], "category": cat})
    return result


# ══════════════════════════════════════════════════════════════════════
# Screener Engine
# ══════════════════════════════════════════════════════════════════════

class ScreenerEngine:
    """Compute technical metrics for a batch of symbols and apply filters."""

    def scan(
        self,
        market: str,
        filters: Optional[List[str]] = None,
        sort_by: str = "change_24h",
        sort_dir: str = "desc",
    ) -> List[Dict]:
        """Scan a market and return filtered/sorted results.

        Parameters
        ----------
        market : str
            One of crypto, stocks, bist, forex, commodities
        filters : list[str], optional
            List of filter names to apply (AND logic)
        sort_by : str
            Column to sort by (default: change_24h)
        sort_dir : str
            'asc' or 'desc'

        Returns
        -------
        list[dict]
            List of symbol dicts with all computed metrics
        """
        market = (market or "").strip().lower()
        scanner = {
            "crypto": self.scan_crypto,
            "stocks": self.scan_stocks,
            "bist": self.scan_bist,
            "forex": self.scan_forex,
            "commodities": self.scan_commodities,
        }.get(market)
        if not scanner:
            return []
        rows = scanner()

        # Apply filters (AND logic)
        if filters:
            for fname in filters:
                finfo = _FILTERS.get(fname)
                if finfo:
                    rows = [r for r in rows if finfo["fn"](r)]

        # Sort
        reverse = sort_dir == "desc"
        rows.sort(
            key=lambda r: r.get(sort_by) if r.get(sort_by) is not None else -9999999,
            reverse=reverse,
        )

        return rows

    # ── Public API required by FAZ 17 ───────────────────────────────

    def scan_crypto(self) -> List[Dict]:
        """Public crypto scan entry-point."""
        return self._scan_crypto()

    def scan_stocks(self) -> List[Dict]:
        """Public US stocks scan entry-point."""
        return self._scan_stocks()

    def scan_bist(self) -> List[Dict]:
        """Public BIST scan entry-point."""
        return self._scan_bist()

    def scan_forex(self) -> List[Dict]:
        """Public forex scan entry-point."""
        return self._scan_forex()

    def scan_commodities(self) -> List[Dict]:
        """Public commodities scan entry-point."""
        return self._scan_commodities()

    def scan_market(self, symbols: List[str], klines_data: Dict[str, List[Dict]], market: str) -> List[Dict]:
        """Shared market scanner over prepared symbols+klines payload.

        Parameters
        ----------
        symbols : list[str]
            Symbols to process.
        klines_data : dict[str, list[dict]]
            Pre-fetched OHLCV rows keyed by symbol.
        market : str
            Market label to include in output rows.
        """
        rows: List[Dict] = []
        for sym in symbols:
            klines = klines_data.get(sym) or []
            if not klines:
                continue
            try:
                price = float(klines[-1].get("close", 0))
                if price <= 0:
                    continue
                prev = float(klines[-2].get("close", 0)) if len(klines) >= 2 else 0
                change_24h = ((price - prev) / prev * 100) if prev else 0.0
                volume = float(klines[-1].get("volume", 0))

                metrics = self._compute_indicators(klines, price)
                metrics.update({
                    "symbol": sym,
                    "price": round(price, 6),
                    "change_24h": round(change_24h, 2),
                    "volume": round(volume, 0),
                    "market": market,
                })
                rows.append(metrics)
            except Exception as exc:
                _logger.debug("scan_market failed %s: %s", sym, exc)
        return rows

    # ── Market scanners ──────────────────────────────────────────────

    def _scan_crypto(self) -> List[Dict]:
        """Scan top crypto symbols via Binance Futures."""
        try:
            from flask import current_app
            svc = current_app.extensions.get("market_data")
            if not svc:
                _logger.warning("MarketDataService not available")
                return []

            # Get symbols sorted by volume
            tickers = svc.get_ticker_24h(ttl_s=30)
            usdt_tickers = [
                t for t in tickers
                if t.get("symbol", "").endswith("USDT")
            ]
            # Sort by quote volume descending
            usdt_tickers.sort(
                key=lambda t: float(t.get("quoteVolume", 0)),
                reverse=True,
            )
            limit = _SCAN_LIMITS["crypto"]
            top_symbols = [t["symbol"] for t in usdt_tickers[:limit]]

            results = []
            # Phase-1: build fast rows for all symbols from 24h ticker data.
            ticker_map = {t.get("symbol"): t for t in usdt_tickers}
            for sym in top_symbols:
                try:
                    t = ticker_map.get(sym) or {}
                    price = float(t.get("lastPrice", 0) or 0)
                    if price <= 0:
                        continue
                    row = {
                        "symbol": sym,
                        "price": round(price, 6),
                        "change_24h": round(float(t.get("priceChangePercent", 0) or 0), 2),
                        "volume": round(float(t.get("quoteVolume", 0) or 0), 0),
                        "market": "crypto",
                        "ema20": None,
                        "ema50": None,
                        "ema200": None,
                        "sma50": None,
                        "sma200": None,
                        "rsi14": None,
                        "atr": None,
                        "atr_pct": None,
                        "trend": "sideways",
                        "support_distance": None,
                        "resistance_distance": None,
                        "vol_ratio": None,
                        "ema20_cross_ema50": False,
                        "ema50_cross_ema200": False,
                    }
                    if row:
                        results.append(row)
                except Exception as exc:
                    _logger.debug("Crypto scan failed %s: %s", sym, exc)

            # Phase-2: enrich most-liquid subset with indicators (faster total scan).
            enrich_n = min(40, len(results))
            for i in range(enrich_n):
                sym = results[i]["symbol"]
                try:
                    klines = svc.get_klines(sym, "1d", 250, ttl_s=120)
                    metrics = self._compute_indicators(klines, results[i]["price"])
                    results[i].update(metrics)
                except Exception as exc:
                    _logger.debug("Crypto enrich failed %s: %s", sym, exc)

            return results
        except Exception as exc:
            _logger.warning("Crypto scan error: %s", exc)
            return []

    def _compute_crypto_metrics(self, svc, symbol: str, tickers: list) -> Optional[Dict]:
        """Compute metrics for one crypto symbol."""
        # Get ticker info
        ticker = next((t for t in tickers if t["symbol"] == symbol), None)
        if not ticker:
            return None

        price = float(ticker.get("lastPrice", 0))
        if price <= 0:
            return None

        change_24h = float(ticker.get("priceChangePercent", 0))
        volume = float(ticker.get("quoteVolume", 0))

        # Get 1d klines for indicator computation
        try:
            klines = svc.get_klines(symbol, "1d", 250, ttl_s=120)
        except Exception:
            klines = []

        metrics = self._compute_indicators(klines, price)
        metrics.update({
            "symbol": symbol,
            "price": price,
            "change_24h": round(change_24h, 2),
            "volume": round(volume, 0),
            "market": "crypto",
        })
        return metrics

    def _scan_stocks(self) -> List[Dict]:
        """Scan US stock symbols."""
        return self._scan_yahoo_market("stocks")

    def _scan_bist(self) -> List[Dict]:
        """Scan BIST symbols."""
        return self._scan_yahoo_market("bist")

    def _scan_forex(self) -> List[Dict]:
        """Scan Forex symbols."""
        return self._scan_yahoo_market("forex")

    def _scan_commodities(self) -> List[Dict]:
        """Scan Commodity symbols."""
        return self._scan_yahoo_market("commodities")

    def _scan_yahoo_market(self, market: str) -> List[Dict]:
        """Generic Yahoo-Finance-based market scanner.

        FAZ 56: Uses batch price fetch for ALL symbols so no row has price=0.
        Top 25 symbols additionally get full indicator enrichment via klines.
        """
        try:
            from app.core.yahoo_client import get_klines, get_symbols_info
            from app.cache import cache_get_or_set

            # Get symbol list
            if market == "stocks":
                from app.core.stocks_data import DEFAULT_SYMBOLS
                symbols = list(DEFAULT_SYMBOLS)
            elif market == "bist":
                from app.core.bist_data import DEFAULT_SYMBOLS
                symbols = list(DEFAULT_SYMBOLS)
            elif market == "forex":
                from app.core.forex_data import DEFAULT_SYMBOLS
                symbols = list(DEFAULT_SYMBOLS)
            elif market == "commodities":
                from app.core.commodities_data import DEFAULT_SYMBOLS
                symbols = list(DEFAULT_SYMBOLS)
            else:
                return []

            limit = _SCAN_LIMITS.get(market, 50)
            symbols = symbols[:limit]

            # ── Phase 1: Batch-fetch prices for ALL symbols ──
            price_map: Dict[str, Dict] = {}
            try:
                batch_info = cache_get_or_set(
                    f"scr:batch:{market}", 120,
                    get_symbols_info, symbols, market,
                ) or []
                for info in batch_info:
                    sym = info.get("symbol", "")
                    if sym:
                        price_map[sym] = info
            except Exception as exc:
                _logger.warning("Batch price fetch failed for %s: %s", market, exc)

            # ── Phase 2: Enrich top subset with full indicators ──
            enrich_n = min(25, len(symbols))
            enrich_symbols = symbols[:enrich_n]
            klines_data: Dict[str, List[Dict]] = {}

            for sym in enrich_symbols:
                try:
                    klines_data[sym] = cache_get_or_set(
                        f"scr:klines:{sym}:1d", 300,
                        get_klines, sym, "1d", 250,
                    ) or []
                except Exception as exc:
                    _logger.debug("Yahoo kline failed %s: %s", sym, exc)

            enriched = self.scan_market(enrich_symbols, klines_data, market)
            enriched_syms = {r["symbol"] for r in enriched}

            results = list(enriched)

            # ── Phase 3: Add price-populated rows for remaining symbols ──
            for sym in symbols:
                if sym in enriched_syms:
                    continue
                info = price_map.get(sym, {})
                price = float(info.get("lastPrice", 0) or 0)
                pct_chg = float(info.get("pct", 0) or 0)
                results.append({
                    "symbol": sym,
                    "name": info.get("name", ""),
                    "price": round(price, 6),
                    "change_24h": round(pct_chg, 2),
                    "volume": 0,
                    "market": market,
                    "ema20": None,
                    "ema50": None,
                    "ema200": None,
                    "sma50": None,
                    "sma200": None,
                    "rsi14": None,
                    "atr": None,
                    "atr_pct": None,
                    "trend": "sideways",
                    "support_distance": None,
                    "resistance_distance": None,
                    "vol_ratio": None,
                    "ema20_cross_ema50": False,
                    "ema50_cross_ema200": False,
                })

            return results
        except Exception as exc:
            _logger.warning("%s scan error: %s", market, exc)
            return []

    # ── Shared indicator computation ─────────────────────────────────

    def _compute_indicators(self, klines: list, current_price: float) -> Dict:
        """Compute all technical indicators from klines data."""
        result = {
            "ema20": None,
            "ema50": None,
            "ema200": None,
            "sma50": None,
            "sma200": None,
            "rsi14": None,
            "atr": None,
            "atr_pct": None,
            "trend": "sideways",
            "support_distance": None,
            "resistance_distance": None,
            "vol_ratio": None,
            "ema20_cross_ema50": False,
            "ema50_cross_ema200": False,
        }

        if not klines or len(klines) < 20:
            return result

        closes = [float(k["close"]) for k in klines]
        highs = [float(k["high"]) for k in klines]
        lows = [float(k["low"]) for k in klines]
        volumes = [float(k["volume"]) for k in klines]

        # ── EMA ──
        ema20 = ema_last(closes, 20)
        ema50 = ema_last(closes, 50) if len(closes) >= 50 else None
        ema200 = ema_last(closes, 200) if len(closes) >= 200 else None

        result["ema20"] = round(ema20, 6) if ema20 else None
        result["ema50"] = round(ema50, 6) if ema50 else None
        result["ema200"] = round(ema200, 6) if ema200 else None

        # ── SMA ──
        sma50 = simple_sma(closes, 50) if len(closes) >= 50 else None
        sma200 = simple_sma(closes, 200) if len(closes) >= 200 else None
        result["sma50"] = round(float(sma50), 6) if sma50 is not None else None
        result["sma200"] = round(float(sma200), 6) if sma200 is not None else None

        # ── RSI ──
        if len(closes) >= 15:
            rsi_series = compute_rsi(pd.Series(closes), 14)
            rsi_val = float(rsi_series.iloc[-1])
            result["rsi14"] = round(rsi_val, 1) if not math.isnan(rsi_val) else None

        # ── ATR ──
        if len(klines) >= 15:
            df_atr = pd.DataFrame(klines)
            for col in ("high", "low", "close"):
                df_atr[col] = pd.to_numeric(df_atr[col], errors="coerce")
            atr = atr_last(df_atr, 14)
            if atr and current_price > 0:
                result["atr"] = round(atr, 6)
                result["atr_pct"] = round((atr / current_price) * 100, 2)

        # ── Trend ──
        if ema20 and ema50:
            if current_price > ema20 > ema50:
                result["trend"] = "up"
            elif current_price < ema20 < ema50:
                result["trend"] = "down"
            else:
                result["trend"] = "sideways"

        # ── Volume Ratio ──
        if len(volumes) >= 21:
            avg_vol = sum(volumes[-21:-1]) / 20  # avg of last 20 (excluding current)
            if avg_vol > 0:
                result["vol_ratio"] = round(volumes[-1] / avg_vol, 2)

        # ── Support / Resistance (pivot-based) ──
        if len(klines) >= 20:
            recent_highs = sorted(highs[-20:], reverse=True)
            recent_lows = sorted(lows[-20:])
            resistance = recent_highs[0]
            support = recent_lows[0]
            if current_price > 0:
                result["resistance_distance"] = round(
                    ((resistance - current_price) / current_price) * 100, 2
                )
                result["support_distance"] = round(
                    ((current_price - support) / current_price) * 100, 2
                )

        # ── MA Crossovers ──
        if len(closes) >= 52 and ema20 and ema50:
            # Check if EMA20 just crossed above EMA50 (within last 3 bars)
            prev_closes = closes[:-3]
            if len(prev_closes) >= 50:
                prev_ema20 = ema_last(prev_closes, 20)
                prev_ema50 = ema_last(prev_closes, 50)
                if prev_ema20 and prev_ema50:
                    if prev_ema20 <= prev_ema50 and ema20 > ema50:
                        result["ema20_cross_ema50"] = True

        if len(closes) >= 203 and ema50 and ema200:
            prev_closes = closes[:-3]
            if len(prev_closes) >= 200:
                prev_ema50 = ema_last(prev_closes, 50)
                prev_ema200 = ema_last(prev_closes, 200)
                if prev_ema50 and prev_ema200:
                    if prev_ema50 <= prev_ema200 and ema50 > ema200:
                        result["ema50_cross_ema200"] = True

        return result
