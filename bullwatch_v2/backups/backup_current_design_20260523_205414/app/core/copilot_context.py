# -*- coding: utf-8 -*-
"""Copilot Context Engine — FAZ 21.

Aggregates real-time market data from existing services into structured
context objects that the AI Copilot can reason over.

Context builders:
  build_symbol_context(symbol, market, timeframe)
  build_market_context(market)
  build_screener_context(market, filters)
  build_discover_context()

All functions return plain dicts — no mock data, all sourced from
live Binance / Yahoo / RSS feeds via existing app.core modules.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.cache import cache_get, cache_get_or_set, utcnow

_logger = logging.getLogger("zkr_analiz.copilot.context")

# ══════════════════════════════════════════════════════════════════════
# 1) SYMBOL CONTEXT
# ══════════════════════════════════════════════════════════════════════

def build_symbol_context(
    symbol: str,
    market: str = "crypto",
    timeframe: str = "1d",
) -> Dict:
    """Build a rich context object for a single symbol.

    Aggregates: price, indicators, signal engine, news, alerts,
    orderflow (crypto), support/resistance.

    Returns a plain dict safe for JSON serialization.
    """
    ctx: Dict = {
        "symbol": symbol,
        "market": market,
        "timeframe": timeframe,
        "generated_at": utcnow().isoformat(),
        "price": {},
        "indicators": {},
        "signal": {},
        "support_resistance": {},
        "news": [],
        "alerts": [],
        "orderflow": {},
    }

    # ── Price + Indicators ────────────────────────────────────────
    try:
        candles = _fetch_klines(symbol, market, timeframe, limit=250)
        if candles:
            last = candles[-1]
            ctx["price"] = {
                "current": float(last.get("close", 0)),
                "open": float(last.get("open", 0)),
                "high": float(last.get("high", 0)),
                "low": float(last.get("low", 0)),
                "volume": float(last.get("volume", 0)),
            }
            # Compute TA
            ctx["indicators"] = _compute_ta_summary(candles)
    except Exception as exc:
        _logger.debug("Symbol context — klines failed %s: %s", symbol, exc)

    # ── Signal Engine ─────────────────────────────────────────────
    try:
        sig = _fetch_signal(symbol, market)
        if sig:
            ctx["signal"] = {
                "decision": sig.get("decision"),
                "note": sig.get("note"),
                "ticks": sig.get("ticks", []),
                "risk": sig.get("risk", {}),
                "pullback_targets": sig.get("pullback_targets", []),
            }
            ctx["support_resistance"] = sig.get("support_resistance", {})
    except Exception as exc:
        _logger.debug("Symbol context — signal failed %s: %s", symbol, exc)

    # ── News ──────────────────────────────────────────────────────
    try:
        ctx["news"] = _fetch_news_for_symbol(symbol, market)
    except Exception as exc:
        _logger.debug("Symbol context — news failed %s: %s", symbol, exc)

    # ── Active Alerts ─────────────────────────────────────────────
    try:
        from app.core.alert_engine import get_alerts
        all_alerts = get_alerts()
        sym_upper = symbol.upper()
        ctx["alerts"] = [
            a for a in all_alerts
            if a.get("symbol", "").upper() == sym_upper and a.get("active")
        ]
    except Exception as exc:
        _logger.debug("Symbol context — alerts failed %s: %s", symbol, exc)

    # ── Orderflow (crypto only) ───────────────────────────────────
    if market == "crypto":
        try:
            ctx["orderflow"] = _fetch_orderflow(symbol)
        except Exception as exc:
            _logger.debug("Symbol context — orderflow failed %s: %s", symbol, exc)

    return ctx


# ══════════════════════════════════════════════════════════════════════
# 2) MARKET CONTEXT
# ══════════════════════════════════════════════════════════════════════

def build_market_context(market: str = "crypto") -> Dict:
    """Build a market-wide context: top movers, index regime, news summary."""
    ctx: Dict = {
        "market": market,
        "generated_at": utcnow().isoformat(),
        "top_movers": [],
        "market_sentiment": {},
        "news_summary": [],
    }

    # ── Top movers from screener ──────────────────────────────────
    try:
        from app.core.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        rows = cache_get_or_set(
            f"copilot:mkt:{market}", 120,
            engine.scan, market,
        )
        if rows:
            # Top 10 by absolute change
            sorted_rows = sorted(
                rows, key=lambda r: abs(r.get("change_24h") or 0), reverse=True,
            )[:10]
            ctx["top_movers"] = [
                {
                    "symbol": r["symbol"],
                    "price": r.get("price"),
                    "change_24h": r.get("change_24h"),
                    "rsi14": r.get("rsi14"),
                    "trend": r.get("trend"),
                    "volume": r.get("volume"),
                }
                for r in sorted_rows
            ]
    except Exception as exc:
        _logger.debug("Market context — screener failed %s: %s", market, exc)

    # ── Market sentiment (crypto: FNG) ────────────────────────────
    if market == "crypto":
        try:
            from app.core.binance_client import fng_latest
            fng = fng_latest()
            if fng:
                ctx["market_sentiment"] = {
                    "fear_greed_index": fng.get("value"),
                    "fear_greed_label": fng.get("value_classification"),
                }
        except Exception:
            pass

    # ── News ──────────────────────────────────────────────────────
    try:
        ctx["news_summary"] = _fetch_market_news(market)[:8]
    except Exception as exc:
        _logger.debug("Market context — news failed %s: %s", market, exc)

    return ctx


# ══════════════════════════════════════════════════════════════════════
# 3) SCREENER CONTEXT
# ══════════════════════════════════════════════════════════════════════

def build_screener_context(
    market: str = "crypto",
    filters: Optional[List[str]] = None,
) -> Dict:
    """Build context from screener results for AI interpretation."""
    ctx: Dict = {
        "market": market,
        "filters_applied": filters or [],
        "generated_at": utcnow().isoformat(),
        "total_scanned": 0,
        "match_count": 0,
        "results": [],
    }

    try:
        from app.core.screener_engine import ScreenerEngine, _FILTERS
        engine = ScreenerEngine()

        all_rows = cache_get_or_set(
            f"copilot:scr:{market}", 120,
            engine.scan, market,
        )
        if all_rows is None:
            all_rows = []

        ctx["total_scanned"] = len(all_rows)
        rows = list(all_rows)

        # Apply filters
        if filters:
            for fname in filters:
                finfo = _FILTERS.get(fname)
                if finfo:
                    rows = [r for r in rows if finfo["fn"](r)]

        ctx["match_count"] = len(rows)

        # Take top 20 for context (don't overwhelm AI)
        ctx["results"] = [
            {
                "symbol": r["symbol"],
                "price": r.get("price"),
                "change_24h": r.get("change_24h"),
                "rsi14": r.get("rsi14"),
                "trend": r.get("trend"),
                "ema20": r.get("ema20"),
                "ema50": r.get("ema50"),
                "volume": r.get("volume"),
                "atr_pct": r.get("atr_pct"),
            }
            for r in rows[:20]
        ]
    except Exception as exc:
        _logger.debug("Screener context failed %s: %s", market, exc)

    return ctx


# ══════════════════════════════════════════════════════════════════════
# 4) DISCOVER CONTEXT
# ══════════════════════════════════════════════════════════════════════

def build_discover_context() -> Dict:
    """Build context for the Discover page: market overview, top news, movers."""
    ctx: Dict = {
        "generated_at": utcnow().isoformat(),
        "markets": {},
        "top_news": [],
        "crypto_sentiment": {},
    }

    # ── Multi-market snapshot ─────────────────────────────────────
    for mkt in ("crypto", "stocks", "bist", "forex", "commodities"):
        try:
            from app.core.screener_engine import ScreenerEngine
            engine = ScreenerEngine()
            rows = cache_get_or_set(
                f"copilot:disc:{mkt}", 180,
                engine.scan, mkt,
            )
            if rows:
                top5 = sorted(
                    rows, key=lambda r: abs(r.get("change_24h") or 0), reverse=True,
                )[:5]
                ctx["markets"][mkt] = {
                    "count": len(rows),
                    "top_movers": [
                        {
                            "symbol": r["symbol"],
                            "price": r.get("price"),
                            "change_24h": r.get("change_24h"),
                            "trend": r.get("trend"),
                        }
                        for r in top5
                    ],
                }
        except Exception as exc:
            _logger.debug("Discover context — %s failed: %s", mkt, exc)

    # ── Crypto sentiment ──────────────────────────────────────────
    try:
        from app.core.binance_client import fng_latest
        fng = fng_latest()
        if fng:
            ctx["crypto_sentiment"] = {
                "fear_greed_index": fng.get("value"),
                "fear_greed_label": fng.get("value_classification"),
            }
    except Exception:
        pass

    # ── Top news (all markets) ────────────────────────────────────
    try:
        from app.core.news_service import NewsService
        news = cache_get_or_set(
            "copilot:disc:news", 300,
            NewsService.fetch_market_news,
        )
        ctx["top_news"] = [
            {
                "title": n.get("title"),
                "source": n.get("source"),
                "sentiment": n.get("sentiment"),
                "published_at": n.get("published_at"),
            }
            for n in (news or [])[:10]
        ]
    except Exception as exc:
        _logger.debug("Discover context — news failed: %s", exc)

    return ctx


# ══════════════════════════════════════════════════════════════════════
# 5) SIMULATOR CONTEXT (FAZ 22)
# ══════════════════════════════════════════════════════════════════════

def build_simulator_context() -> Dict:
    """Build context for the Paper Trading Simulator.

    Includes: account info, open positions with PnL, closed trade stats,
    portfolio summary. Enables AI to analyze performance and suggest improvements.
    """
    ctx: Dict = {
        "generated_at": utcnow().isoformat(),
        "simulator": {},
    }

    try:
        from app.core.paper_trading_engine import portfolio_summary, list_trades
        summary = portfolio_summary()
        ctx["simulator"] = {
            "account": summary.get("account", {}),
            "open_positions_count": summary.get("open_positions_count", 0),
            "open_positions": summary.get("open_positions", []),
            "total_open_pnl": summary.get("total_open_pnl", 0),
            "closed_trades_count": summary.get("closed_trades_count", 0),
            "closed_pnl": summary.get("closed_pnl", 0),
            "total_pnl": summary.get("total_pnl", 0),
            "total_pnl_pct": summary.get("total_pnl_pct", 0),
            "total_trade_count": summary.get("total_trade_count", 0),
        }

        # Add recent trades for context
        recent = list_trades(limit=10)
        ctx["simulator"]["recent_trades"] = [
            {
                "symbol": t.get("symbol"),
                "market": t.get("market"),
                "side": t.get("side"),
                "quantity": t.get("quantity"),
                "price": t.get("price"),
                "notional": t.get("notional"),
                "note": t.get("note"),
                "executed_at": t.get("executed_at"),
            }
            for t in recent
        ]
    except Exception as exc:
        _logger.debug("Simulator context failed: %s", exc)

    return ctx


# ══════════════════════════════════════════════════════════════════════
# 6) JOURNAL CONTEXT (FAZ 23)
# ══════════════════════════════════════════════════════════════════════

def build_journal_context() -> Dict:
    """Build context for the Trade Journal.

    Includes: journal stats, recent entries, emotion distribution,
    strategy performance. Enables AI to analyze trading psychology
    and suggest improvements.
    """
    ctx: Dict = {
        "generated_at": utcnow().isoformat(),
        "journal": {},
    }

    try:
        from app.core.journal_engine import list_entries, stats

        journal_stats = stats()
        ctx["journal"]["stats"] = journal_stats

        # Add recent entries for context
        recent = list_entries(limit=20)
        ctx["journal"]["recent_entries"] = [
            {
                "symbol": e.get("symbol"),
                "market": e.get("market"),
                "side": e.get("side"),
                "entry_price": e.get("entry_price"),
                "exit_price": e.get("exit_price"),
                "pnl": e.get("pnl"),
                "emotion": e.get("emotion"),
                "strategy": e.get("strategy"),
                "notes": e.get("notes"),
                "created_at": e.get("created_at"),
            }
            for e in recent
        ]
        ctx["journal"]["entry_count"] = len(recent)
    except Exception as exc:
        _logger.debug("Journal context failed: %s", exc)

    return ctx


# ══════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════

def _fetch_klines(
    symbol: str, market: str, interval: str, limit: int = 250,
) -> list:
    """Fetch OHLCV klines via the appropriate data service."""
    cache_key = f"copilot:klines:{symbol}:{interval}:{limit}"

    if market == "crypto":
        from app.core.binance_client import binance_klines
        df = cache_get_or_set(cache_key, 60, binance_klines, symbol, interval, limit)
        if df is not None and hasattr(df, "to_dict"):
            return df.to_dict("records")
        return df if isinstance(df, list) else []
    else:
        from app.core.yahoo_client import get_klines
        rows = cache_get_or_set(cache_key, 120, get_klines, symbol, interval, limit)
        return rows or []


def _compute_ta_summary(candles: list) -> Dict:
    """Compute a compact TA summary from candle data."""
    if not candles or len(candles) < 15:
        return {}

    import pandas as pd
    from app.core.ta import (
        simple_sma, ema_last, atr_last, compute_rsi, compute_macd,
    )

    closes = [float(c.get("close", 0)) for c in candles]
    result: Dict = {}

    # EMAs / SMAs
    result["ema20"] = round(ema_last(closes, 20), 6) if ema_last(closes, 20) else None
    if len(closes) >= 50:
        result["ema50"] = round(ema_last(closes, 50), 6) if ema_last(closes, 50) else None
        sma50 = simple_sma(closes, 50)
        result["sma50"] = round(float(sma50), 6) if sma50 is not None else None
    if len(closes) >= 200:
        result["ema200"] = round(ema_last(closes, 200), 6) if ema_last(closes, 200) else None
        sma200 = simple_sma(closes, 200)
        result["sma200"] = round(float(sma200), 6) if sma200 is not None else None

    # RSI
    rsi_series = compute_rsi(pd.Series(closes), 14)
    rsi_val = float(rsi_series.iloc[-1])
    if not pd.isna(rsi_val):
        result["rsi14"] = round(rsi_val, 1)

    # MACD
    macd_line, sig_line, hist = compute_macd(pd.Series(closes))
    if not pd.isna(macd_line.iloc[-1]):
        result["macd"] = round(float(macd_line.iloc[-1]), 6)
        result["macd_signal"] = round(float(sig_line.iloc[-1]), 6)
        result["macd_histogram"] = round(float(hist.iloc[-1]), 6)
        result["macd_bullish"] = float(hist.iloc[-1]) > 0

    # ATR
    df = pd.DataFrame(candles)
    for col in ("high", "low", "close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    atr = atr_last(df, 14)
    if atr:
        result["atr14"] = round(atr, 6)
        price = closes[-1]
        if price > 0:
            result["atr_pct"] = round((atr / price) * 100, 2)

    # Trend label
    ema20 = result.get("ema20")
    ema50 = result.get("ema50")
    if ema20 and ema50:
        if closes[-1] > ema20 > ema50:
            result["trend"] = "yükseliş"
        elif closes[-1] < ema20 < ema50:
            result["trend"] = "düşüş"
        else:
            result["trend"] = "yatay"

    return result


def _fetch_signal(symbol: str, market: str) -> Optional[Dict]:
    """Fetch signal evaluation for a symbol."""
    if market == "crypto":
        try:
            from app.blueprints.signals.engine import evaluate_entry_signal
            from app.core.binance_client import pump_candidates
            from app.core.thresholds import get_thresholds
            lst = cache_get_or_set(
                "pump_candidates_v1", 300, pump_candidates, limit_pairs=40,
            )
            row = None
            if lst:
                row = next((x for x in lst if x.get("symbol") == symbol), None)
            return evaluate_entry_signal(symbol, row, thresholds=get_thresholds())
        except Exception:
            pass
    else:
        try:
            from app.core.universal_signal import evaluate_market_signal
            return cache_get_or_set(
                f"copilot:sig:{market}:{symbol}", 120,
                evaluate_market_signal, symbol, market,
            )
        except Exception:
            pass
    return None


def _fetch_news_for_symbol(symbol: str, market: str) -> list:
    """Fetch relevant news items for a symbol, max 5."""
    from app.core.news_service import NewsService

    if market == "crypto":
        items = cache_get_or_set(
            f"copilot:news:coin:{symbol}", 300,
            NewsService.fetch_coin_news, symbol,
        )
    elif market == "bist":
        items = cache_get_or_set("copilot:news:bist", 300, NewsService.fetch_bist_news)
    elif market == "stocks":
        items = cache_get_or_set("copilot:news:stocks", 300, NewsService.fetch_stocks_news)
    elif market == "forex":
        items = cache_get_or_set("copilot:news:forex", 300, NewsService.fetch_forex_news)
    elif market == "commodities":
        items = cache_get_or_set("copilot:news:commodities", 300, NewsService.fetch_commodities_news)
    else:
        items = []

    return [
        {
            "title": n.get("title"),
            "source": n.get("source"),
            "sentiment": n.get("sentiment"),
            "published_at": n.get("published_at"),
        }
        for n in (items or [])[:5]
    ]


def _fetch_market_news(market: str) -> list:
    """Fetch general news for a market."""
    from app.core.news_service import NewsService

    fetchers = {
        "crypto": NewsService.fetch_crypto_news,
        "stocks": NewsService.fetch_stocks_news,
        "bist": NewsService.fetch_bist_news,
        "forex": NewsService.fetch_forex_news,
        "commodities": NewsService.fetch_commodities_news,
    }
    fetcher = fetchers.get(market, NewsService.fetch_market_news)
    items = cache_get_or_set(f"copilot:news:{market}", 300, fetcher)
    return [
        {
            "title": n.get("title"),
            "source": n.get("source"),
            "sentiment": n.get("sentiment"),
            "published_at": n.get("published_at"),
        }
        for n in (items or [])[:8]
    ]


def _fetch_orderflow(symbol: str) -> Dict:
    """Fetch orderflow data for a crypto symbol (OI, funding, L/S)."""
    result: Dict = {}
    try:
        from app.core.binance_client import (
            fapi_open_interest,
        )
        oi = fapi_open_interest(symbol)
        if oi:
            result["open_interest"] = oi
    except Exception:
        pass

    # Ticker data from cache
    try:
        tickers = cache_get("binance_top_tickers_v1", ttl=30)
        if tickers:
            for t in tickers:
                if t.get("s") == symbol or t.get("symbol") == symbol:
                    result["last_price"] = t.get("c") or t.get("lastPrice")
                    result["volume_24h"] = t.get("v") or t.get("volume")
                    result["change_24h"] = t.get("change") or t.get("priceChangePercent")
                    break
    except Exception:
        pass

    return result
