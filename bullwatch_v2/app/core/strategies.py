# -*- coding: utf-8 -*-
"""Strategy Engine — FAZ 23.

Provides trading strategy definitions for backtesting.

Each strategy implements ``generate_signals(df)`` which takes a
DataFrame with OHLCV columns and returns a Series of signals:
  +1 = buy, -1 = sell, 0 = hold.

Built-in strategies:
  - EMA Cross (EMA20/EMA50)
  - RSI Reversal (RSI < 30 buy, RSI > 70 sell)
  - Breakout (range high breakout)
  - VWAP Trend (price vs VWAP)
"""
from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

_logger = logging.getLogger("zkr_analiz.strategies")


# ══════════════════════════════════════════════════════════════════════
# STRATEGY REGISTRY
# ══════════════════════════════════════════════════════════════════════

_STRATEGIES: Dict[str, "BaseStrategy"] = {}


def get_strategy(name: str) -> "BaseStrategy":
    """Return a strategy instance by name (case-insensitive)."""
    key = name.lower().strip()
    if key not in _STRATEGIES:
        raise ValueError(f"Unknown strategy: {name!r}. Available: {list(_STRATEGIES.keys())}")
    return _STRATEGIES[key]


def list_strategies() -> List[Dict]:
    """Return metadata for all registered strategies."""
    result = []
    for key, strat in _STRATEGIES.items():
        result.append({
            "id": key,
            "name": strat.display_name,
            "description": strat.description,
            "params": strat.default_params,
        })
    return result


# ══════════════════════════════════════════════════════════════════════
# BASE CLASS
# ══════════════════════════════════════════════════════════════════════

class BaseStrategy:
    """Abstract base for all strategies."""

    id: str = ""
    display_name: str = ""
    description: str = ""
    default_params: Dict = {}

    def generate_signals(self, df: pd.DataFrame, **params) -> pd.Series:
        """Return a Series of +1 (buy), -1 (sell), 0 (hold) for each row."""
        raise NotImplementedError


def _register(cls):
    """Decorator to register a strategy class."""
    instance = cls()
    _STRATEGIES[instance.id] = instance
    return cls


# ══════════════════════════════════════════════════════════════════════
# 1) EMA CROSS
# ══════════════════════════════════════════════════════════════════════

@_register
class EMACrossStrategy(BaseStrategy):
    id = "ema_cross"
    display_name = "EMA Cross"
    description = "EMA20 ve EMA50 kesişim stratejisi. EMA20 yukarı keserse AL, aşağı keserse SAT."
    default_params = {"fast": 20, "slow": 50}

    def generate_signals(self, df: pd.DataFrame, **params) -> pd.Series:
        fast = params.get("fast", self.default_params["fast"])
        slow = params.get("slow", self.default_params["slow"])

        closes = df["close"].astype(float)
        ema_fast = closes.ewm(span=fast, adjust=False).mean()
        ema_slow = closes.ewm(span=slow, adjust=False).mean()

        signals = pd.Series(0, index=df.index, dtype=int)

        # Buy when fast crosses above slow
        cross_up = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
        # Sell when fast crosses below slow
        cross_down = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

        signals[cross_up] = 1
        signals[cross_down] = -1

        return signals


# ══════════════════════════════════════════════════════════════════════
# 2) RSI REVERSAL
# ══════════════════════════════════════════════════════════════════════

@_register
class RSIReversalStrategy(BaseStrategy):
    id = "rsi_reversal"
    display_name = "RSI Reversal"
    description = "RSI 30 altına düşünce AL, 70 üstüne çıkınca SAT."
    default_params = {"period": 14, "oversold": 30, "overbought": 70}

    def generate_signals(self, df: pd.DataFrame, **params) -> pd.Series:
        period = params.get("period", self.default_params["period"])
        oversold = params.get("oversold", self.default_params["oversold"])
        overbought = params.get("overbought", self.default_params["overbought"])

        closes = df["close"].astype(float)
        delta = closes.diff()
        up = delta.clip(lower=0)
        down = (-delta).clip(lower=0)
        roll_up = up.ewm(alpha=1 / period, adjust=False).mean()
        roll_down = down.ewm(alpha=1 / period, adjust=False).mean()
        rs = roll_up / roll_down.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        signals = pd.Series(0, index=df.index, dtype=int)

        # Buy when RSI crosses up from below oversold
        buy_cond = (rsi > oversold) & (rsi.shift(1) <= oversold)
        sell_cond = (rsi < overbought) & (rsi.shift(1) >= overbought)

        signals[buy_cond] = 1
        signals[sell_cond] = -1

        return signals


# ══════════════════════════════════════════════════════════════════════
# 3) BREAKOUT
# ══════════════════════════════════════════════════════════════════════

@_register
class BreakoutStrategy(BaseStrategy):
    id = "breakout"
    display_name = "Breakout"
    description = "Son N bar'ın en yüksek seviyesini kıran mumda AL, en düşük seviyeyi kıranda SAT."
    default_params = {"lookback": 20}

    def generate_signals(self, df: pd.DataFrame, **params) -> pd.Series:
        lookback = params.get("lookback", self.default_params["lookback"])

        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)

        range_high = high.rolling(lookback).max().shift(1)
        range_low = low.rolling(lookback).min().shift(1)

        signals = pd.Series(0, index=df.index, dtype=int)

        signals[close > range_high] = 1
        signals[close < range_low] = -1

        return signals


# ══════════════════════════════════════════════════════════════════════
# 4) VWAP TREND
# ══════════════════════════════════════════════════════════════════════

@_register
class VWAPTrendStrategy(BaseStrategy):
    id = "vwap_trend"
    display_name = "VWAP Trend"
    description = "Fiyat VWAP üstüne çıkınca AL, altına düşünce SAT."
    default_params = {"window": 20}

    def generate_signals(self, df: pd.DataFrame, **params) -> pd.Series:
        window = params.get("window", self.default_params["window"])

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        volume = df["volume"].astype(float)

        tp = (high + low + close) / 3.0
        cum_tp_vol = (tp * volume).rolling(window).sum()
        cum_vol = volume.rolling(window).sum()
        vwap = cum_tp_vol / cum_vol.replace(0, np.nan)

        signals = pd.Series(0, index=df.index, dtype=int)

        # Buy when price crosses above VWAP
        cross_up = (close > vwap) & (close.shift(1) <= vwap.shift(1))
        cross_down = (close < vwap) & (close.shift(1) >= vwap.shift(1))

        signals[cross_up] = 1
        signals[cross_down] = -1

        return signals
