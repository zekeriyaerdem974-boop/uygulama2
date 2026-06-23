# -*- coding: utf-8 -*-
"""Backtest Engine — FAZ 23.

Runs historical backtests using real candle data and strategy signals.

Public API:
  run_backtest(symbol, market, strategy_id, interval, limit, **params)
    → Dict with trades, metrics, equity_curve

Internal:
  _fetch_candles(symbol, market, interval, limit) → pd.DataFrame
  _simulate_trades(df, signals) → List[Dict]
  _compute_metrics(trades, initial_balance) → Dict
  _build_equity_curve(trades, initial_balance) → List[Dict]
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.strategies import get_strategy

_logger = logging.getLogger("zkr_analiz.backtest")

# Default initial balance for backtests
DEFAULT_INITIAL_BALANCE = 100_000.0
# Default trade size as fraction of balance
DEFAULT_POSITION_SIZE = 0.1  # 10% of balance per trade


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def run_backtest(
    symbol: str,
    market: str = "crypto",
    strategy_id: str = "ema_cross",
    interval: str = "1d",
    limit: int = 500,
    initial_balance: float = DEFAULT_INITIAL_BALANCE,
    position_size: float = DEFAULT_POSITION_SIZE,
    **strategy_params,
) -> Dict:
    """Run a full backtest and return results.

    Returns:
        {
            ok: True,
            symbol, market, strategy, interval,
            trades: [...],
            metrics: {...},
            equity_curve: [...]
        }
    """
    _logger.info(
        "Backtest: symbol=%s market=%s strategy=%s interval=%s limit=%d",
        symbol, market, strategy_id, interval, limit,
    )

    # 1. Get strategy
    strategy = get_strategy(strategy_id)

    # 2. Fetch candle data
    df = _fetch_candles(symbol, market, interval, limit)
    if df.empty or len(df) < 10:
        return {
            "ok": False,
            "error": f"Yetersiz veri: {symbol} için {len(df)} mum bulundu (min 10 gerekli)",
        }

    # 3. Generate signals
    signals = strategy.generate_signals(df, **strategy_params)

    # 4. Simulate trades
    trades = _simulate_trades(df, signals, initial_balance, position_size)

    # 5. Compute metrics
    metrics = _compute_metrics(trades, initial_balance)

    # 6. Build equity curve
    equity_curve = _build_equity_curve(trades, initial_balance, df)

    return {
        "ok": True,
        "symbol": symbol,
        "market": market,
        "strategy": strategy_id,
        "strategy_name": strategy.display_name,
        "interval": interval,
        "candle_count": len(df),
        "trades": trades,
        "metrics": metrics,
        "equity_curve": equity_curve,
    }


# ══════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════════════════════════════

def _fetch_candles(
    symbol: str, market: str, interval: str, limit: int,
) -> pd.DataFrame:
    """Fetch candle data using existing market data modules.

    Returns DataFrame with columns: open_time, open, high, low, close, volume
    """
    klines: List[Dict] = []

    try:
        if market == "crypto":
            # Try Binance first for crypto
            try:
                from app.core.binance_client import binance_klines
                df = binance_klines(symbol, interval=interval, limit=limit)
                if df is not None and not df.empty:
                    return df
            except Exception:
                pass
            # Fallback to Yahoo
            from app.core.yahoo_client import get_klines
            klines = get_klines(symbol, interval=interval, limit=limit)

        elif market == "bist":
            from app.core.bist_data import BISTData
            klines = BISTData.get_klines(symbol, interval=interval, limit=limit)

        elif market == "stocks":
            from app.core.stocks_data import StocksData
            klines = StocksData.get_klines(symbol, interval=interval, limit=limit)

        elif market == "forex":
            from app.core.forex_data import ForexData
            klines = ForexData.get_klines(symbol, interval=interval, limit=limit)

        elif market == "commodities":
            from app.core.commodities_data import CommoditiesData
            klines = CommoditiesData.get_klines(symbol, interval=interval, limit=limit)

        else:
            # Generic fallback via Yahoo
            from app.core.yahoo_client import get_klines
            klines = get_klines(symbol, interval=interval, limit=limit)

    except Exception as exc:
        _logger.warning("Candle fetch failed for %s/%s: %s", symbol, market, exc)
        return pd.DataFrame()

    if not klines:
        return pd.DataFrame()

    df = pd.DataFrame(klines)
    # Ensure numeric types
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ══════════════════════════════════════════════════════════════════════
# TRADE SIMULATION
# ══════════════════════════════════════════════════════════════════════

def _simulate_trades(
    df: pd.DataFrame,
    signals: pd.Series,
    initial_balance: float,
    position_size: float,
) -> List[Dict]:
    """Walk forward through signals and simulate trades.

    Rules:
    - Buy signal (+1): Open a long position if not already in one
    - Sell signal (-1): Close any open long position
    - Only one position at a time
    - Position size = position_size * current_balance
    """
    trades: List[Dict] = []
    balance = initial_balance
    position = None  # {entry_price, quantity, entry_idx, entry_time}

    for i in range(len(df)):
        sig = signals.iloc[i]
        row = df.iloc[i]
        price = float(row["close"])
        ts = int(row.get("open_time", i))

        if sig == 1 and position is None:
            # Open long position
            invest = balance * position_size
            qty = invest / price if price > 0 else 0
            if qty > 0:
                position = {
                    "entry_price": price,
                    "quantity": qty,
                    "entry_idx": i,
                    "entry_time": ts,
                    "invest": invest,
                }

        elif sig == -1 and position is not None:
            # Close position
            pnl = (price - position["entry_price"]) * position["quantity"]
            pnl_pct = ((price / position["entry_price"]) - 1) * 100 if position["entry_price"] > 0 else 0

            trade = {
                "entry_time": position["entry_time"],
                "exit_time": ts,
                "entry_price": round(position["entry_price"], 6),
                "exit_price": round(price, 6),
                "quantity": round(position["quantity"], 8),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "side": "long",
                "bars_held": i - position["entry_idx"],
            }
            trades.append(trade)
            balance += pnl
            position = None

    # Close any remaining open position at last price
    if position is not None and len(df) > 0:
        last_row = df.iloc[-1]
        price = float(last_row["close"])
        ts = int(last_row.get("open_time", len(df) - 1))
        pnl = (price - position["entry_price"]) * position["quantity"]
        pnl_pct = ((price / position["entry_price"]) - 1) * 100 if position["entry_price"] > 0 else 0

        trade = {
            "entry_time": position["entry_time"],
            "exit_time": ts,
            "entry_price": round(position["entry_price"], 6),
            "exit_price": round(price, 6),
            "quantity": round(position["quantity"], 8),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "side": "long",
            "bars_held": len(df) - 1 - position["entry_idx"],
            "still_open": True,
        }
        trades.append(trade)

    return trades


# ══════════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════════

def _compute_metrics(trades: List[Dict], initial_balance: float) -> Dict:
    """Compute performance metrics from trade list."""
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "avg_profit": 0,
            "avg_loss": 0,
            "max_drawdown": 0,
            "max_drawdown_pct": 0,
            "net_profit": 0,
            "net_profit_pct": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "avg_bars_held": 0,
        }

    pnls = [t["pnl"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_trades = len(trades)
    win_count = len(wins)
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
        float("inf") if gross_profit > 0 else 0
    )

    avg_profit = (gross_profit / len(wins)) if wins else 0
    avg_loss = (gross_loss / len(losses)) if losses else 0

    net_profit = sum(pnls)
    net_profit_pct = (net_profit / initial_balance) * 100 if initial_balance > 0 else 0

    # Max drawdown
    equity = initial_balance
    peak = equity
    max_dd = 0
    max_dd_pct = 0
    for pnl in pnls:
        equity += pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_pct = (dd / peak) * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = dd_pct

    bars_held = [t.get("bars_held", 0) for t in trades]
    avg_bars = sum(bars_held) / len(bars_held) if bars_held else 0

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999.99,
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "net_profit": round(net_profit, 2),
        "net_profit_pct": round(net_profit_pct, 2),
        "best_trade": round(max(pnls), 2) if pnls else 0,
        "worst_trade": round(min(pnls), 2) if pnls else 0,
        "avg_bars_held": round(avg_bars, 1),
    }


# ══════════════════════════════════════════════════════════════════════
# EQUITY CURVE
# ══════════════════════════════════════════════════════════════════════

def _build_equity_curve(
    trades: List[Dict], initial_balance: float, df: pd.DataFrame,
) -> List[Dict]:
    """Build an equity curve from trades.

    Returns list of {time, equity} points.
    """
    curve = [{"time": int(df.iloc[0].get("open_time", 0)), "equity": round(initial_balance, 2)}]
    equity = initial_balance

    for t in trades:
        equity += t["pnl"]
        curve.append({
            "time": t["exit_time"],
            "equity": round(equity, 2),
        })

    return curve
