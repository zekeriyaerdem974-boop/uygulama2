"""Pure technical-analysis helpers.

All functions are **stateless** — no cache, no HTTP, no Flask dependency.
Extracted from ``legacy_monolith.py`` (FAZ 3).

Canonical implementations of RSI & MACD that replace the duplicated
private helpers in both the monolith and ``blueprints/indicators.py``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── Simple Moving Average ──────────────────────────────────────────────
def simple_sma(series, window: int):
    """Return the last SMA value, or *None* if not enough data."""
    if len(series) < window:
        return None
    return pd.Series(series).rolling(window=window).mean().iloc[-1]


# ── Exponential Moving Average (last value) ────────────────────────────
def ema_last(series, window: int = 20):
    """Return the last EMA value, or *None* if not enough data."""
    if len(series) < window:
        return None
    s = pd.Series(series)
    return float(s.ewm(span=window, adjust=False).mean().iloc[-1])


# ── Average True Range (last value) ───────────────────────────────────
def atr_last(df: pd.DataFrame, period: int = 14):
    """ATR over a DataFrame with *high / low / close* columns."""
    if df is None or df.empty or len(df) < period + 1:
        return None
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


# ── VWAP (last value over *window* bars) ──────────────────────────────
def vwap_last(df: pd.DataFrame, window: int = 96):
    """Volume-weighted average price over the most recent *window* bars."""
    if df is None or df.empty:
        return None
    w = min(window, len(df))
    tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float)
    num = (tp.iloc[-w:] * vol.iloc[-w:]).sum()
    den = vol.iloc[-w:].sum()
    return float(num / den) if den > 0 else None


# ── RSI (full series) ────────────────────────────────────────────────
def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Wilder-smoothed RSI.  Returns a full ``pd.Series``."""
    delta = closes.diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)
    roll_up = up.ewm(alpha=1 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ── MACD (full series) ──────────────────────────────────────────────
def compute_macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns *(macd, signal_line, histogram)* as ``pd.Series`` tuple."""
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return macd, sig, hist


# ── Composite BTC indicator snapshot ─────────────────────────────────
def compute_btc_indicators_from_df(df: pd.DataFrame, *, now_iso: str | None = None) -> dict:
    """Build a dict of BTC indicators from a daily klines DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``close`` column (daily klines).
    now_iso : str, optional
        ISO-formatted timestamp for *updated_at*.  When *None* the caller
        is expected to fill it in.
    """
    closes = df["close"].tolist()
    last = closes[-1]
    sma20 = simple_sma(closes, 20)
    sma50 = simple_sma(closes, 50)
    sma200 = simple_sma(closes, 200)
    if len(closes) >= 30:
        ret30 = closes[-1] / closes[-30] - 1.0
        vol30 = float(np.std(closes[-30:]) / np.mean(closes[-30:])) if np.mean(closes[-30:]) > 0 else None
    else:
        ret30, vol30 = None, None
    return {
        "price": float(last),
        "sma20": float(sma20) if sma20 is not None else None,
        "sma50": float(sma50) if sma50 is not None else None,
        "sma200": float(sma200) if sma200 is not None else None,
        "ret30": float(ret30) if ret30 is not None else None,
        "vol30": float(vol30) if vol30 is not None else None,
        "updated_at": now_iso,
    }
