# -*- coding: utf-8 -*-
"""Opportunity Engine — FAZ 40.

AI-driven market opportunity detection across crypto, stocks, forex,
and commodities. Scans for technical and on-chain anomalies, momentum
shifts, volume spikes, volatility events, and sector rotation signals.

LEGAL_SAFE_MODE: No buy/sell/trade language. Uses "fırsat" (opportunity),
"dikkat çekici hareket" (noteworthy movement), "gözlem" (observation),
"izlenebilir" (watchable) terminology only.

Public API:
    scan_all_opportunities()          -> list[dict]
    scan_crypto_opportunities()       -> list[dict]
    scan_stock_opportunities()        -> list[dict]
    scan_forex_opportunities()        -> list[dict]
    scan_sector_rotation()            -> list[dict]
    detect_volume_spike(symbol, market) -> dict | None
    detect_momentum(symbol, market)     -> dict | None
    detect_volatility_spike(symbol, market) -> dict | None
    get_cached_opportunities()        -> list[dict]
    get_opportunity_by_symbol(symbol) -> list[dict]
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.cache import cache_get, cache_set

_logger = logging.getLogger("zkr_analiz.opportunity_engine")

# ── Database ──────────────────────────────────────────────────────
_DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
_DB_PATH = os.path.join(_DB_DIR, "opportunities.db")
_lock = threading.Lock()

CACHE_KEY = "opportunities_latest"
CACHE_TTL = 120  # 2 minutes

# ── Event Types ───────────────────────────────────────────────────
EVENT_TYPES = {
    "volume_spike": {"icon": "📊", "label": "Hacim Artışı", "color": "#3b82f6"},
    "momentum_shift": {"icon": "🚀", "label": "Momentum Değişimi", "color": "#10b981"},
    "volatility_spike": {"icon": "⚡", "label": "Volatilite Artışı", "color": "#f59e0b"},
    "rsi_extreme": {"icon": "📉", "label": "RSI Aşırı Bölge", "color": "#ef4444"},
    "ema_cross": {"icon": "✨", "label": "EMA Kesişimi", "color": "#8b5cf6"},
    "breakout": {"icon": "💎", "label": "Kırılım Hareketi", "color": "#06b6d4"},
    "sector_rotation": {"icon": "🔄", "label": "Sektör Rotasyonu", "color": "#ec4899"},
    "whale_activity": {"icon": "🐋", "label": "Büyük Hacim Hareketi", "color": "#6366f1"},
    "fng_extreme": {"icon": "😱", "label": "Korku/Açgözlülük Aşırı", "color": "#f97316"},
    "price_anomaly": {"icon": "🔍", "label": "Fiyat Anomalisi", "color": "#14b8a6"},
}

# ── Confidence Levels ─────────────────────────────────────────────
CONFIDENCE_HIGH = 80
CONFIDENCE_MEDIUM = 60
CONFIDENCE_LOW = 40

# ── LEGAL_SAFE_MODE Labels ─────────────────────────────────────────
_SAFE_LABELS = {
    "bullish": "yukarı yönlü hareket gözlemleniyor",
    "bearish": "aşağı yönlü hareket gözlemleniyor",
    "strong": "güçlü momentum dikkat çekiyor",
    "weak": "zayıflayan momentum gözlemleniyor",
    "overbought": "aşırı alım bölgesinde — dikkatli izlenebilir",
    "oversold": "aşırı satım bölgesinde — dikkatli izlenebilir",
    "breakout_up": "yukarı kırılım potansiyeli gözlemleniyor",
    "breakout_down": "aşağı kırılım potansiyeli gözlemleniyor",
    "high_volume": "normalin üzerinde hacim dikkat çekiyor",
    "volatile": "yüksek volatilite gözlemleniyor",
}


# ══════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("opportunities.db")


def _init_db():
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL DEFAULT 'crypto',
                event_type TEXT NOT NULL,
                confidence INTEGER NOT NULL DEFAULT 50,
                description TEXT NOT NULL,
                details TEXT,
                price REAL,
                change_pct REAL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_opp_symbol ON opportunities(symbol);
            CREATE INDEX IF NOT EXISTS idx_opp_market ON opportunities(market);
            CREATE INDEX IF NOT EXISTS idx_opp_event ON opportunities(event_type);
            CREATE INDEX IF NOT EXISTS idx_opp_created ON opportunities(created_at);
            CREATE INDEX IF NOT EXISTS idx_opp_active ON opportunities(active);

            CREATE TABLE IF NOT EXISTS user_opportunity_views (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                viewed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_uov_user ON user_opportunity_views(user_id);
            CREATE INDEX IF NOT EXISTS idx_uov_opp ON user_opportunity_views(opportunity_id);
        """)
        conn.commit()
    finally:
        conn.close()


# Init DB on module load
try:
    _init_db()
except Exception as e:
    _logger.warning("Opportunity DB init deferred: %s", e)


def _save_opportunity(opp: dict) -> None:
    """Persist an opportunity to the database."""
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO opportunities
                   (id, symbol, market, event_type, confidence, description,
                    details, price, change_pct, created_at, expires_at, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    opp["id"], opp["symbol"], opp["market"],
                    opp["event_type"], opp["confidence"], opp["description"],
                    opp.get("details", ""), opp.get("price"),
                    opp.get("change_pct"), opp["created_at"],
                    opp.get("expires_at"), 1,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _deactivate_old() -> None:
    """Mark opportunities older than 4 hours as inactive."""
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                """UPDATE opportunities SET active = 0
                   WHERE active = 1
                   AND datetime(created_at) < datetime('now', '-4 hours')""",
            )
            conn.commit()
        finally:
            conn.close()


def get_db_opportunities(
    market: str = None,
    event_type: str = None,
    limit: int = 50,
) -> List[dict]:
    """Fetch active opportunities from the database."""
    conn = _get_db()
    try:
        query = "SELECT * FROM opportunities WHERE active = 1"
        params: list = []
        if market:
            query += " AND market = ?"
            params.append(market)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY confidence DESC, created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_viewed(user_id: str, opportunity_id: str) -> None:
    """Mark an opportunity as viewed by a user."""
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO user_opportunity_views
                   (id, user_id, opportunity_id, viewed_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    str(uuid.uuid4())[:8], user_id, opportunity_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════════
# DETECTION HELPERS
# ══════════════════════════════════════════════════════════════════════

def _calc_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate RSI from close prices."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _calc_ema(values: List[float], period: int) -> List[float]:
    """Calculate EMA."""
    if not values or len(values) < period:
        return []
    k = 2.0 / (period + 1)
    ema = [sum(values[:period]) / period]
    for val in values[period:]:
        ema.append(val * k + ema[-1] * (1 - k))
    return ema


def _calc_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
    """Calculate ATR (Average True Range)."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def _make_opportunity(
    symbol: str,
    market: str,
    event_type: str,
    confidence: int,
    description: str,
    details: str = "",
    price: float = None,
    change_pct: float = None,
) -> dict:
    """Create an opportunity dict."""
    opp = {
        "id": str(uuid.uuid4())[:12],
        "symbol": symbol,
        "market": market,
        "event_type": event_type,
        "confidence": max(0, min(100, confidence)),
        "description": description,
        "details": details,
        "price": price,
        "change_pct": change_pct,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "icon": EVENT_TYPES.get(event_type, {}).get("icon", "🔍"),
        "label": EVENT_TYPES.get(event_type, {}).get("label", event_type),
        "color": EVENT_TYPES.get(event_type, {}).get("color", "#64748b"),
    }
    return opp


# ══════════════════════════════════════════════════════════════════════
# INDIVIDUAL DETECTORS
# ══════════════════════════════════════════════════════════════════════

def detect_volume_spike(symbol: str, market: str = "crypto",
                        klines: List[dict] = None) -> Optional[dict]:
    """Detect abnormal volume spike for a symbol.

    Returns an opportunity dict if volume > 2x average, else None.
    """
    if not klines or len(klines) < 5:
        return None

    volumes = [float(k.get("volume", 0)) for k in klines]
    if not volumes or volumes[-1] == 0:
        return None

    avg_vol = sum(volumes[:-1]) / max(len(volumes) - 1, 1)
    if avg_vol <= 0:
        return None

    ratio = volumes[-1] / avg_vol
    if ratio < 2.0:
        return None

    confidence = min(95, int(50 + ratio * 10))
    last_close = float(klines[-1].get("close", 0))

    return _make_opportunity(
        symbol=symbol,
        market=market,
        event_type="volume_spike",
        confidence=confidence,
        description=f"{symbol}: Hacim normalin {ratio:.1f}x üzerinde — {_SAFE_LABELS['high_volume']}",
        details=f"Son hacim: {volumes[-1]:,.0f}, Ortalama: {avg_vol:,.0f}, Oran: {ratio:.1f}x",
        price=last_close,
    )


def detect_momentum(symbol: str, market: str = "crypto",
                     klines: List[dict] = None) -> Optional[dict]:
    """Detect momentum shift via EMA crossover.

    Returns an opportunity dict if EMA9 crosses EMA21, else None.
    """
    if not klines or len(klines) < 25:
        return None

    closes = [float(k.get("close", 0)) for k in klines]
    if not closes:
        return None

    ema9 = _calc_ema(closes, 9)
    ema21 = _calc_ema(closes, 21)

    if len(ema9) < 2 or len(ema21) < 2:
        return None

    # Check for crossover in the last 2 bars
    curr_diff = ema9[-1] - ema21[-1]
    prev_diff = ema9[-2] - ema21[-2]

    if curr_diff > 0 and prev_diff <= 0:
        # Bullish cross
        direction = "yukarı"
        label = _SAFE_LABELS["bullish"]
        confidence = min(85, int(55 + abs(curr_diff / closes[-1]) * 5000))
    elif curr_diff < 0 and prev_diff >= 0:
        # Bearish cross
        direction = "aşağı"
        label = _SAFE_LABELS["bearish"]
        confidence = min(85, int(55 + abs(curr_diff / closes[-1]) * 5000))
    else:
        return None

    return _make_opportunity(
        symbol=symbol,
        market=market,
        event_type="momentum_shift",
        confidence=confidence,
        description=f"{symbol}: EMA(9/21) {direction} kesişimi — {label}",
        details=f"EMA9: {ema9[-1]:.4f}, EMA21: {ema21[-1]:.4f}",
        price=closes[-1],
    )


def detect_volatility_spike(symbol: str, market: str = "crypto",
                             klines: List[dict] = None) -> Optional[dict]:
    """Detect abnormal volatility via ATR expansion.

    Returns an opportunity dict if current ATR > 1.5x average ATR, else None.
    """
    if not klines or len(klines) < 20:
        return None

    highs = [float(k.get("high", 0)) for k in klines]
    lows = [float(k.get("low", 0)) for k in klines]
    closes = [float(k.get("close", 0)) for k in klines]

    atr_14 = _calc_atr(highs, lows, closes, 14)
    if not atr_14 or atr_14 == 0:
        return None

    # Compare current candle range to ATR
    curr_range = highs[-1] - lows[-1]
    ratio = curr_range / atr_14

    if ratio < 1.5:
        return None

    confidence = min(90, int(50 + ratio * 15))

    return _make_opportunity(
        symbol=symbol,
        market=market,
        event_type="volatility_spike",
        confidence=confidence,
        description=f"{symbol}: ATR'nin {ratio:.1f}x üzerinde hareket — {_SAFE_LABELS['volatile']}",
        details=f"ATR(14): {atr_14:.4f}, Anlık mum aralığı: {curr_range:.4f}",
        price=closes[-1],
    )


def detect_rsi_extreme(symbol: str, market: str = "crypto",
                        klines: List[dict] = None) -> Optional[dict]:
    """Detect RSI entering extreme zones (<30 or >70).

    Returns an opportunity dict if RSI in extreme zone, else None.
    """
    if not klines or len(klines) < 16:
        return None

    closes = [float(k.get("close", 0)) for k in klines]
    rsi = _calc_rsi(closes, 14)
    if rsi is None:
        return None

    if rsi >= 75:
        label = _SAFE_LABELS["overbought"]
        confidence = min(90, int(55 + (rsi - 75) * 2))
    elif rsi <= 25:
        label = _SAFE_LABELS["oversold"]
        confidence = min(90, int(55 + (25 - rsi) * 2))
    else:
        return None

    return _make_opportunity(
        symbol=symbol,
        market=market,
        event_type="rsi_extreme",
        confidence=confidence,
        description=f"{symbol}: RSI({rsi:.0f}) — {label}",
        details=f"RSI(14): {rsi:.1f}",
        price=closes[-1],
    )


def detect_breakout(symbol: str, market: str = "crypto",
                     klines: List[dict] = None) -> Optional[dict]:
    """Detect price breakout above/below recent range.

    Uses 20-bar high/low as range definition.
    """
    if not klines or len(klines) < 22:
        return None

    closes = [float(k.get("close", 0)) for k in klines]
    highs = [float(k.get("high", 0)) for k in klines]
    lows = [float(k.get("low", 0)) for k in klines]

    # 20-bar range (exclude last 2 bars)
    range_high = max(highs[-22:-2])
    range_low = min(lows[-22:-2])

    curr_close = closes[-1]

    if curr_close > range_high:
        label = _SAFE_LABELS["breakout_up"]
        pct_above = ((curr_close - range_high) / range_high) * 100
        confidence = min(90, int(60 + pct_above * 5))
        direction = "yukarı"
    elif curr_close < range_low:
        label = _SAFE_LABELS["breakout_down"]
        pct_below = ((range_low - curr_close) / range_low) * 100
        confidence = min(90, int(60 + pct_below * 5))
        direction = "aşağı"
    else:
        return None

    return _make_opportunity(
        symbol=symbol,
        market=market,
        event_type="breakout",
        confidence=confidence,
        description=f"{symbol}: 20 barlık aralığın {direction} kırılımı — {label}",
        details=f"Aralık: {range_low:.4f}-{range_high:.4f}, Kapanış: {curr_close:.4f}",
        price=curr_close,
    )


def detect_whale_activity(symbol: str, market: str = "crypto",
                           klines: List[dict] = None) -> Optional[dict]:
    """Detect abnormally large single-candle volume (whale-like).

    Triggers if a single candle has > 5x the median volume.
    """
    if not klines or len(klines) < 10:
        return None

    volumes = [float(k.get("volume", 0)) for k in klines]
    sorted_vols = sorted(volumes[:-1])
    median_vol = sorted_vols[len(sorted_vols) // 2] if sorted_vols else 0
    if median_vol <= 0:
        return None

    ratio = volumes[-1] / median_vol
    if ratio < 5.0:
        return None

    closes = [float(k.get("close", 0)) for k in klines]
    confidence = min(95, int(60 + ratio * 3))

    return _make_opportunity(
        symbol=symbol,
        market=market,
        event_type="whale_activity",
        confidence=confidence,
        description=f"{symbol}: Medyan hacmin {ratio:.1f}x üzerinde tek mum — büyük hacim hareketi dikkat çekiyor",
        details=f"Mum hacmi: {volumes[-1]:,.0f}, Medyan: {median_vol:,.0f}",
        price=closes[-1] if closes else None,
    )


# ══════════════════════════════════════════════════════════════════════
# MARKET SCANNERS
# ══════════════════════════════════════════════════════════════════════

def _get_crypto_klines(symbol: str, interval: str = "4h", limit: int = 50) -> List[dict]:
    """Fetch klines from Binance for a crypto symbol."""
    try:
        from app.core.binance_client import binance_klines
        df = binance_klines(symbol, interval=interval, limit=limit)
        return [
            {
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["volume"]),
            }
            for _, r in df.iterrows()
        ]
    except Exception as e:
        _logger.debug("Crypto klines failed for %s: %s", symbol, e)
        return []


def scan_crypto_opportunities() -> List[dict]:
    """Scan top crypto symbols for opportunities."""
    opportunities = []

    # Get top tickers from cache
    tickers = cache_get("binance_top_tickers_v1", ttl=60) or []
    symbols = [t["symbol"] for t in tickers[:20]] if tickers else [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT",
    ]

    for symbol in symbols[:15]:
        try:
            klines = _get_crypto_klines(symbol, "4h", 50)
            if not klines:
                continue

            # Run all detectors
            for detector in [
                detect_volume_spike,
                detect_momentum,
                detect_volatility_spike,
                detect_rsi_extreme,
                detect_breakout,
                detect_whale_activity,
            ]:
                opp = detector(symbol, "crypto", klines)
                if opp:
                    opportunities.append(opp)

            # Small delay to avoid rate limits
            time.sleep(0.05)
        except Exception as e:
            _logger.debug("Crypto scan error for %s: %s", symbol, e)

    # Check Fear & Greed Index
    try:
        from app.core.binance_client import fng_latest
        fng = fng_latest()
        fng_val = fng.get("value")
        if fng_val is not None:
            if fng_val <= 20:
                opportunities.append(_make_opportunity(
                    symbol="MARKET",
                    market="crypto",
                    event_type="fng_extreme",
                    confidence=75,
                    description=f"Fear & Greed Index: {fng_val} (Aşırı Korku) — piyasa duyarlılığı dikkat çekici seviyede",
                    details=f"Sınıflandırma: {fng.get('value_classification', 'Extreme Fear')}",
                ))
            elif fng_val >= 80:
                opportunities.append(_make_opportunity(
                    symbol="MARKET",
                    market="crypto",
                    event_type="fng_extreme",
                    confidence=75,
                    description=f"Fear & Greed Index: {fng_val} (Aşırı Açgözlülük) — piyasa duyarlılığı dikkat çekici seviyede",
                    details=f"Sınıflandırma: {fng.get('value_classification', 'Extreme Greed')}",
                ))
    except Exception:
        pass

    return opportunities


def scan_stock_opportunities() -> List[dict]:
    """Scan major stock indices and popular stocks for opportunities."""
    opportunities = []

    symbols = [
        ("AAPL", "stocks"), ("MSFT", "stocks"), ("GOOGL", "stocks"),
        ("AMZN", "stocks"), ("NVDA", "stocks"), ("TSLA", "stocks"),
        ("META", "stocks"), ("JPM", "stocks"),
    ]

    try:
        from app.core.yahoo_client import get_symbols_info
        infos = get_symbols_info([s[0] for s in symbols], "stocks")
        if infos:
            for info in infos:
                sym = info.get("symbol", "")
                pct = info.get("pct", 0) or info.get("priceChangePercent", 0)
                price = info.get("lastPrice", 0)

                # Large daily moves are noteworthy
                if abs(pct) >= 3.0:
                    direction = "yukarı" if pct > 0 else "aşağı"
                    label = _SAFE_LABELS["strong"] if pct > 0 else _SAFE_LABELS["weak"]
                    opportunities.append(_make_opportunity(
                        symbol=sym,
                        market="stocks",
                        event_type="price_anomaly",
                        confidence=min(85, int(55 + abs(pct) * 5)),
                        description=f"{sym}: Günlük %{pct:+.1f} {direction} hareket — {label}",
                        details=f"Fiyat: ${price:,.2f}",
                        price=price,
                        change_pct=pct,
                    ))
    except Exception as e:
        _logger.debug("Stock scan error: %s", e)

    return opportunities


def scan_forex_opportunities() -> List[dict]:
    """Scan forex pairs for opportunities."""
    opportunities = []

    pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDTRY=X", "EURTRY=X"]

    try:
        from app.core.yahoo_client import get_symbols_info
        infos = get_symbols_info(pairs, "forex")
        if infos:
            for info in infos:
                sym = info.get("symbol", "")
                pct = info.get("pct", 0) or info.get("priceChangePercent", 0)
                price = info.get("lastPrice", 0)

                if abs(pct) >= 0.5:
                    direction = "yukarı" if pct > 0 else "aşağı"
                    opportunities.append(_make_opportunity(
                        symbol=sym.replace("=X", ""),
                        market="forex",
                        event_type="price_anomaly",
                        confidence=min(80, int(50 + abs(pct) * 20)),
                        description=f"{sym.replace('=X', '')}: Günlük %{pct:+.2f} — dikkat çekici hareket",
                        details=f"Fiyat: {price:,.4f}",
                        price=price,
                        change_pct=pct,
                    ))
    except Exception as e:
        _logger.debug("Forex scan error: %s", e)

    return opportunities


def scan_sector_rotation() -> List[dict]:
    """Detect sector rotation via BIST sector indices or crypto categories."""
    opportunities = []

    # Check crypto top movers from cache
    tickers = cache_get("binance_top_tickers_v1", ttl=60) or []
    if tickers:
        # Find extreme movers
        big_gainers = [t for t in tickers if t.get("change24_pct", 0) > 10]
        big_losers = [t for t in tickers if t.get("change24_pct", 0) < -10]

        if len(big_gainers) >= 3:
            symbols_str = ", ".join(t["symbol"] for t in big_gainers[:5])
            opportunities.append(_make_opportunity(
                symbol="CRYPTO_SECTOR",
                market="crypto",
                event_type="sector_rotation",
                confidence=70,
                description=f"Kripto piyasasında toplu yukarı hareket gözlemleniyor: {symbols_str}",
                details=f"{len(big_gainers)} sembol %10+ hareket gösteriyor",
            ))

        if len(big_losers) >= 3:
            symbols_str = ", ".join(t["symbol"] for t in big_losers[:5])
            opportunities.append(_make_opportunity(
                symbol="CRYPTO_SECTOR",
                market="crypto",
                event_type="sector_rotation",
                confidence=70,
                description=f"Kripto piyasasında toplu aşağı hareket gözlemleniyor: {symbols_str}",
                details=f"{len(big_losers)} sembol %-10 hareket gösteriyor",
            ))

    return opportunities


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def scan_all_opportunities() -> List[dict]:
    """Run all scanners and return combined opportunity list.

    Also saves results to DB and cache.
    """
    all_opps: List[dict] = []

    # Deactivate old entries
    try:
        _deactivate_old()
    except Exception:
        pass

    # Run scanners
    for scanner in [
        scan_crypto_opportunities,
        scan_stock_opportunities,
        scan_forex_opportunities,
        scan_sector_rotation,
    ]:
        try:
            opps = scanner()
            all_opps.extend(opps)
        except Exception as e:
            _logger.warning("Scanner %s error: %s", scanner.__name__, e)

    # Sort by confidence (desc)
    all_opps.sort(key=lambda o: -o.get("confidence", 0))

    # Save to DB
    for opp in all_opps:
        try:
            _save_opportunity(opp)
        except Exception:
            pass

    # Cache the result
    cache_set(CACHE_KEY, all_opps)

    _logger.info("Opportunity scan complete: %d opportunities found", len(all_opps))
    return all_opps


def get_cached_opportunities() -> List[dict]:
    """Return the latest cached opportunities without re-scanning."""
    cached = cache_get(CACHE_KEY, ttl=CACHE_TTL)
    if cached:
        return cached
    # Fallback to DB
    return get_db_opportunities(limit=50)


def get_opportunity_by_symbol(symbol: str) -> List[dict]:
    """Get all active opportunities for a specific symbol."""
    conn = _get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM opportunities
               WHERE active = 1 AND (symbol = ? OR symbol = ?)
               ORDER BY confidence DESC, created_at DESC LIMIT 20""",
            (symbol.upper(), symbol),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trending_opportunities(limit: int = 10) -> List[dict]:
    """Return top trending opportunities by confidence."""
    cached = get_cached_opportunities()
    if cached:
        return cached[:limit]
    return get_db_opportunities(limit=limit)


# ══════════════════════════════════════════════════════════════════════
# BACKGROUND SCAN LOOP
# ══════════════════════════════════════════════════════════════════════

SCAN_INTERVAL = int(os.getenv("OPPORTUNITY_SCAN_SEC", "120"))  # 2 min default


def opportunity_scan_loop() -> None:
    """Background loop: scan for opportunities periodically."""
    _logger.info("Opportunity scan loop started (interval=%ds)", SCAN_INTERVAL)
    # Wait for initial data to warm up
    time.sleep(30)
    while True:
        try:
            scan_all_opportunities()
        except Exception as e:
            _logger.warning("Opportunity scan loop error: %s", e)
        time.sleep(SCAN_INTERVAL)
