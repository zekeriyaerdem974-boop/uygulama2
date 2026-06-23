# -*- coding: utf-8 -*-
"""Strategy Engine — FAZ 25.

User-defined strategy system with DSL parser, validation, execution,
and backtest integration.

Public API:
    parse_strategy(code: str) -> dict          — Parse DSL code
    validate_strategy(parsed: dict) -> dict    — Validate parsed strategy
    execute_strategy(parsed, df) -> pd.Series  — Generate signals from parsed strategy
    run_strategy_backtest(code, symbol, market, interval, limit) -> dict
    save_strategy(user_id, name, code) -> dict
    load_strategies(user_id) -> list
    delete_strategy(strategy_id) -> bool
    list_builtin_templates() -> list
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

_logger = logging.getLogger("zkr_analiz.strategy_engine")

# ══════════════════════════════════════════════════════════════════════
# STORAGE
# ══════════════════════════════════════════════════════════════════════

_STRATEGIES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "strategies"
_STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)


def _user_file(user_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", str(user_id))
    return _STRATEGIES_DIR / f"{safe}.json"


def save_strategy(user_id: str, name: str, code: str, strategy_id: str = "") -> dict:
    """Save a user strategy to disk. Returns the saved strategy dict."""
    fpath = _user_file(user_id)
    strategies = []
    if fpath.exists():
        try:
            strategies = json.loads(fpath.read_text("utf-8"))
        except Exception:
            strategies = []

    sid = strategy_id or hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]

    # Check for update
    existing = None
    for s in strategies:
        if s.get("id") == sid:
            existing = s
            break

    if existing:
        existing["name"] = name
        existing["code"] = code
        existing["updated_at"] = int(time.time())
    else:
        strategies.append({
            "id": sid,
            "name": name,
            "code": code,
            "user_id": user_id,
            "created_at": int(time.time()),
            "updated_at": int(time.time()),
        })

    fpath.write_text(json.dumps(strategies, ensure_ascii=False, indent=2), "utf-8")
    return {"ok": True, "id": sid, "name": name}


def load_strategies(user_id: str) -> list:
    """Load all strategies for a user."""
    fpath = _user_file(user_id)
    if not fpath.exists():
        return []
    try:
        return json.loads(fpath.read_text("utf-8"))
    except Exception:
        return []


def delete_strategy(user_id: str, strategy_id: str) -> bool:
    """Delete a strategy by ID."""
    fpath = _user_file(user_id)
    if not fpath.exists():
        return False
    try:
        strategies = json.loads(fpath.read_text("utf-8"))
        before = len(strategies)
        strategies = [s for s in strategies if s.get("id") != strategy_id]
        if len(strategies) == before:
            return False
        fpath.write_text(json.dumps(strategies, ensure_ascii=False, indent=2), "utf-8")
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
# INDICATOR FUNCTIONS — available in DSL
# ══════════════════════════════════════════════════════════════════════

def _ema(closes: pd.Series, period: int) -> pd.Series:
    return closes.ewm(span=period, adjust=False).mean()


def _sma(closes: pd.Series, period: int) -> pd.Series:
    return closes.rolling(period).mean()


def _rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)
    roll_up = up.ewm(alpha=1 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {"line": macd_line, "signal": signal_line, "histogram": histogram}


def _bbands(closes: pd.Series, period: int = 20, std_dev: float = 2.0) -> dict:
    mid = closes.rolling(period).mean()
    std = closes.rolling(period).std()
    return {"upper": mid + std_dev * std, "middle": mid, "lower": mid - std_dev * std}


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _vwap(df: pd.DataFrame, period: int = 20) -> pd.Series:
    tp = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float)
    return (tp * vol).rolling(period).sum() / vol.rolling(period).sum().replace(0, np.nan)


def _stoch(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> dict:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(d_period).mean()
    return {"k": k, "d": d}


# Available indicators for DSL
AVAILABLE_INDICATORS = {
    "EMA": {"fn": _ema, "args": ["period"], "source": "close", "desc": "Üssel Hareketli Ortalama"},
    "SMA": {"fn": _sma, "args": ["period"], "source": "close", "desc": "Basit Hareketli Ortalama"},
    "RSI": {"fn": _rsi, "args": ["period"], "source": "close", "desc": "Göreceli Güç Endeksi"},
    "MACD": {"fn": _macd, "args": ["fast", "slow", "signal"], "source": "close", "desc": "MACD İndikatörü"},
    "BBANDS": {"fn": _bbands, "args": ["period", "std_dev"], "source": "close", "desc": "Bollinger Bantları"},
    "ATR": {"fn": _atr, "args": ["period"], "source": "df", "desc": "Ortalama Gerçek Aralık"},
    "VWAP": {"fn": _vwap, "args": ["period"], "source": "df", "desc": "Hacim Ağırlıklı Ort. Fiyat"},
    "STOCH": {"fn": _stoch, "args": ["k_period", "d_period"], "source": "df", "desc": "Stokastik Osilatör"},
}


# ══════════════════════════════════════════════════════════════════════
# DSL PARSER
# ══════════════════════════════════════════════════════════════════════

# Pattern: EMA20, EMA(20), EMA(20,50), etc.
_INDICATOR_RE = re.compile(
    r"(EMA|SMA|RSI|MACD|BBANDS|ATR|VWAP|STOCH|CLOSE|OPEN|HIGH|LOW|VOLUME)"
    r"(?:\(([^)]*)\)|(\d+))?",
    re.IGNORECASE,
)

# Condition patterns
_CROSS_ABOVE_RE = re.compile(r"(.+?)\s+crosses?\s+above\s+(.+)", re.IGNORECASE)
_CROSS_BELOW_RE = re.compile(r"(.+?)\s+crosses?\s+below\s+(.+)", re.IGNORECASE)
_ABOVE_RE = re.compile(r"(.+?)\s+(?:is\s+)?above\s+(.+)", re.IGNORECASE)
_BELOW_RE = re.compile(r"(.+?)\s+(?:is\s+)?below\s+(.+)", re.IGNORECASE)
_GT_RE = re.compile(r"(.+?)\s*>\s*(.+)", re.IGNORECASE)
_LT_RE = re.compile(r"(.+?)\s*<\s*(.+)", re.IGNORECASE)

# Risk patterns
_STOP_LOSS_RE = re.compile(r"stop_?loss[:\s]+(\d+(?:\.\d+)?)\s*%?", re.IGNORECASE)
_TAKE_PROFIT_RE = re.compile(r"take_?profit[:\s]+(\d+(?:\.\d+)?)\s*%?", re.IGNORECASE)


def _parse_indicator_ref(text: str) -> dict:
    """Parse an indicator reference like 'EMA20', 'EMA(20)', 'RSI14', 'CLOSE', 'MACD.signal'."""
    text = text.strip()

    # Check for sub-field: MACD.signal, BBANDS.upper, STOCH.k
    sub_field = None
    if "." in text:
        parts = text.split(".", 1)
        text = parts[0]
        sub_field = parts[1].strip().lower()

    # Number literal?
    try:
        val = float(text)
        return {"type": "literal", "value": val}
    except ValueError:
        pass

    # Price references
    price_map = {"CLOSE": "close", "OPEN": "open", "HIGH": "high", "LOW": "low", "VOLUME": "volume"}
    up = text.upper()
    if up in price_map:
        return {"type": "price", "field": price_map[up]}

    # Indicator reference — supports EMA20, EMA(20), MACD(12,26,9) etc.
    m = _INDICATOR_RE.match(text)
    if m:
        ind_name = m.group(1).upper()
        result = {"type": "indicator", "name": ind_name}
        # group(2) is paren args: EMA(20) or MACD(12,26,9)
        # group(3) is suffix number: EMA20
        if m.group(2) is not None:
            args = [x.strip() for x in m.group(2).split(",") if x.strip()]
            if len(args) == 1:
                try:
                    result["period"] = int(args[0])
                except ValueError:
                    try:
                        result["period"] = float(args[0])
                    except ValueError:
                        pass
            elif len(args) > 1:
                # Multiple args — store as named args based on indicator
                ind_def = AVAILABLE_INDICATORS.get(ind_name, {})
                arg_names = ind_def.get("args", [])
                for i, arg_val in enumerate(args):
                    if i < len(arg_names):
                        try:
                            result[arg_names[i]] = int(arg_val)
                        except ValueError:
                            try:
                                result[arg_names[i]] = float(arg_val)
                            except ValueError:
                                result[arg_names[i]] = arg_val
        elif m.group(3) is not None:
            result["period"] = int(m.group(3))
        if sub_field:
            result["sub_field"] = sub_field
        return result

    return {"type": "unknown", "raw": text}


def _parse_condition(line: str) -> Optional[dict]:
    """Parse a single condition line into a condition dict."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # crosses above
    m = _CROSS_ABOVE_RE.match(line)
    if m:
        return {
            "op": "crosses_above",
            "left": _parse_indicator_ref(m.group(1)),
            "right": _parse_indicator_ref(m.group(2)),
        }

    # crosses below
    m = _CROSS_BELOW_RE.match(line)
    if m:
        return {
            "op": "crosses_below",
            "left": _parse_indicator_ref(m.group(1)),
            "right": _parse_indicator_ref(m.group(2)),
        }

    # above / is above
    m = _ABOVE_RE.match(line)
    if m:
        return {
            "op": "above",
            "left": _parse_indicator_ref(m.group(1)),
            "right": _parse_indicator_ref(m.group(2)),
        }

    # below / is below
    m = _BELOW_RE.match(line)
    if m:
        return {
            "op": "below",
            "left": _parse_indicator_ref(m.group(1)),
            "right": _parse_indicator_ref(m.group(2)),
        }

    # > operator
    m = _GT_RE.match(line)
    if m:
        return {
            "op": "above",
            "left": _parse_indicator_ref(m.group(1)),
            "right": _parse_indicator_ref(m.group(2)),
        }

    # < operator
    m = _LT_RE.match(line)
    if m:
        return {
            "op": "below",
            "left": _parse_indicator_ref(m.group(1)),
            "right": _parse_indicator_ref(m.group(2)),
        }

    return None


def parse_strategy(code: str) -> dict:
    """Parse DSL code into a structured strategy definition.

    Supports two DSL formats:

    Multi-line (recommended):
        strategy "Name"
        entry:
          EMA20 crosses above EMA50
        exit:
          EMA20 crosses below EMA50
        risk:
          stop_loss 2%
          take_profit 4%

    Compact / inline:
        strategy "Name"
        entry: EMA(20) crosses above EMA(50)
        exit: EMA(20) crosses below EMA(50)
        stop_loss: 3%
        take_profit: 6%

    Returns:
        {
            "name": str,
            "entry_conditions": [condition_dicts],
            "exit_conditions": [condition_dicts],
            "risk": {"stop_loss": float, "take_profit": float},
            "raw_code": str,
        }
    """
    result = {
        "name": "",
        "entry_conditions": [],
        "exit_conditions": [],
        "risk": {"stop_loss": None, "take_profit": None},
        "raw_code": code,
    }

    lines = code.strip().split("\n")
    current_section = None

    _SECTION_ENTRY = ("entry", "buy", "giriş", "giris", "al")
    _SECTION_EXIT = ("exit", "sell", "çıkış", "cikis", "sat")
    _SECTION_RISK = ("risk", "risk yönetimi", "risk yonetimi")

    for raw_line in lines:
        line = raw_line.strip()

        # Skip empty / comments
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # Strategy name
        name_match = re.match(r'strategy\s+["\'](.+?)["\']', line, re.IGNORECASE)
        if name_match:
            result["name"] = name_match.group(1)
            continue

        # ── Top-level stop_loss / take_profit (always match regardless of section) ──
        sl = _STOP_LOSS_RE.search(line)
        if sl:
            result["risk"]["stop_loss"] = float(sl.group(1))
            continue
        tp = _TAKE_PROFIT_RE.search(line)
        if tp:
            result["risk"]["take_profit"] = float(tp.group(1))
            continue

        # ── Section headers (possibly with inline content after colon) ──
        lower = line.lower()
        section_found = None
        remainder = ""

        # Check "entry: <condition>" or just "entry:"
        for kw in _SECTION_ENTRY:
            if lower.startswith(kw):
                after = line[len(kw):].strip()
                if after.startswith(":"):
                    section_found = "entry"
                    remainder = after[1:].strip()
                    break
                elif lower == kw:
                    section_found = "entry"
                    break

        if not section_found:
            for kw in _SECTION_EXIT:
                if lower.startswith(kw):
                    after = line[len(kw):].strip()
                    if after.startswith(":"):
                        section_found = "exit"
                        remainder = after[1:].strip()
                        break
                    elif lower == kw:
                        section_found = "exit"
                        break

        if not section_found:
            for kw in _SECTION_RISK:
                if lower.startswith(kw):
                    after = line[len(kw):].strip()
                    if after.startswith(":"):
                        section_found = "risk"
                        remainder = after[1:].strip()
                        break
                    elif lower == kw:
                        section_found = "risk"
                        break

        if section_found:
            current_section = section_found
            # If there's inline content after the colon, process it
            if remainder:
                if current_section == "risk":
                    sl2 = _STOP_LOSS_RE.search(remainder)
                    if sl2:
                        result["risk"]["stop_loss"] = float(sl2.group(1))
                    tp2 = _TAKE_PROFIT_RE.search(remainder)
                    if tp2:
                        result["risk"]["take_profit"] = float(tp2.group(1))
                elif current_section in ("entry", "exit"):
                    cond = _parse_condition(remainder)
                    if cond:
                        key = "entry_conditions" if current_section == "entry" else "exit_conditions"
                        result[key].append(cond)
            continue

        # ── Parse based on current section ──
        if current_section == "risk":
            sl3 = _STOP_LOSS_RE.search(line)
            if sl3:
                result["risk"]["stop_loss"] = float(sl3.group(1))
            tp3 = _TAKE_PROFIT_RE.search(line)
            if tp3:
                result["risk"]["take_profit"] = float(tp3.group(1))
            continue

        if current_section in ("entry", "exit"):
            cond = _parse_condition(line)
            if cond:
                key = "entry_conditions" if current_section == "entry" else "exit_conditions"
                result[key].append(cond)

    return result


# ══════════════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════════════

def validate_strategy(parsed: dict) -> dict:
    """Validate a parsed strategy. Returns {valid: bool, errors: [str], warnings: [str]}."""
    errors = []
    warnings = []

    if not parsed.get("name"):
        errors.append("Strateji adı belirtilmeli: strategy \"İsim\"")

    if not parsed.get("entry_conditions"):
        errors.append("En az bir giriş (entry) koşulu gerekli")

    if not parsed.get("exit_conditions"):
        warnings.append("Çıkış (exit) koşulu belirtilmedi — giriş koşulunun tersi kullanılacak")

    # Check indicator references
    for section in ("entry_conditions", "exit_conditions"):
        for cond in parsed.get(section, []):
            for side in ("left", "right"):
                ref = cond.get(side, {})
                if ref.get("type") == "indicator":
                    name = ref.get("name", "").upper()
                    if name not in AVAILABLE_INDICATORS:
                        errors.append(f"Bilinmeyen indikatör: {name}")
                elif ref.get("type") == "unknown":
                    errors.append(f"Anlaşılamayan ifade: {ref.get('raw', '?')}")

    # Risk validation
    risk = parsed.get("risk", {})
    sl = risk.get("stop_loss")
    tp = risk.get("take_profit")
    if sl is not None and (sl <= 0 or sl > 50):
        errors.append(f"Stop loss değeri geçersiz: {sl}% (0-50 arası olmalı)")
    if tp is not None and (tp <= 0 or tp > 100):
        errors.append(f"Take profit değeri geçersiz: {tp}% (0-100 arası olmalı)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════════════
# EXECUTION ENGINE
# ══════════════════════════════════════════════════════════════════════

def _resolve_series(ref: dict, df: pd.DataFrame, cache: dict) -> pd.Series:
    """Resolve an indicator/price reference to a pd.Series."""
    if ref["type"] == "literal":
        return pd.Series(ref["value"], index=df.index)

    if ref["type"] == "price":
        return df[ref["field"]].astype(float)

    if ref["type"] == "indicator":
        name = ref["name"].upper()
        period = ref.get("period")
        sub_field = ref.get("sub_field")
        info = AVAILABLE_INDICATORS.get(name)
        if not info:
            raise ValueError(f"Unknown indicator: {name}")

        # Build cache key — include all args for uniqueness
        arg_parts = [name, str(period)]
        for akey in ("fast", "slow", "signal", "std_dev", "k_period", "d_period"):
            if akey in ref:
                arg_parts.append(f"{akey}={ref[akey]}")
        arg_parts.append(str(sub_field))
        cache_key = "_".join(arg_parts)
        if cache_key in cache:
            return cache[cache_key]

        # Calculate
        fn = info["fn"]
        if info["source"] == "close":
            closes = df["close"].astype(float)
            if name in ("EMA", "SMA"):
                p = period or 20
                result = fn(closes, p)
            elif name == "RSI":
                p = period or 14
                result = fn(closes, p)
            elif name == "MACD":
                fast = ref.get("fast", 12)
                slow = ref.get("slow", 26)
                sig = ref.get("signal", 9)
                result = fn(closes, fast, slow, sig)  # returns dict
            elif name == "BBANDS":
                p = period or 20
                sd = ref.get("std_dev", 2.0)
                result = fn(closes, p, sd)  # returns dict
            else:
                result = fn(closes)
        else:
            if name == "ATR":
                result = fn(df, period or 14)
            elif name == "VWAP":
                result = fn(df, period or 20)
            elif name == "STOCH":
                kp = ref.get("k_period", period or 14)
                dp = ref.get("d_period", 3)
                result = fn(df, kp, dp)  # returns dict
            else:
                result = fn(df)

        # Handle dict results (MACD, BBANDS, STOCH)
        if isinstance(result, dict):
            # Cache all sub-fields using base key pattern
            base_key = cache_key.rsplit("_", 1)[0]  # remove sub_field suffix
            for k, v in result.items():
                cache[f"{base_key}_{k}"] = v
            if sub_field and sub_field in result:
                cache[cache_key] = result[sub_field]
                return result[sub_field]
            # Default sub-field
            defaults = {"MACD": "line", "BBANDS": "middle", "STOCH": "k"}
            default_key = defaults.get(name, list(result.keys())[0])
            cache[cache_key] = result[default_key]
            return result[default_key]

        cache[cache_key] = result
        return result

    raise ValueError(f"Cannot resolve reference: {ref}")


def _evaluate_condition(cond: dict, df: pd.DataFrame, cache: dict) -> pd.Series:
    """Evaluate a single condition, returns boolean Series."""
    left = _resolve_series(cond["left"], df, cache)
    right = _resolve_series(cond["right"], df, cache)
    op = cond["op"]

    if op == "crosses_above":
        return (left > right) & (left.shift(1) <= right.shift(1))
    elif op == "crosses_below":
        return (left < right) & (left.shift(1) >= right.shift(1))
    elif op == "above":
        return left > right
    elif op == "below":
        return left < right
    else:
        return pd.Series(False, index=df.index)


def execute_strategy(parsed: dict, df: pd.DataFrame) -> pd.Series:
    """Execute a parsed strategy on a DataFrame.

    Returns a Series of +1 (buy), -1 (sell), 0 (hold).
    """
    signals = pd.Series(0, index=df.index, dtype=int)
    cache = {}

    # Entry conditions — all must be true (AND logic)
    if parsed.get("entry_conditions"):
        entry_mask = pd.Series(True, index=df.index)
        for cond in parsed["entry_conditions"]:
            entry_mask = entry_mask & _evaluate_condition(cond, df, cache)
        signals[entry_mask] = 1

    # Exit conditions
    if parsed.get("exit_conditions"):
        exit_mask = pd.Series(True, index=df.index)
        for cond in parsed["exit_conditions"]:
            exit_mask = exit_mask & _evaluate_condition(cond, df, cache)
        signals[exit_mask] = -1
    elif parsed.get("entry_conditions"):
        # Auto-generate exit: invert entry conditions
        exit_mask = pd.Series(True, index=df.index)
        for cond in parsed["entry_conditions"]:
            inv_cond = dict(cond)
            if cond["op"] == "crosses_above":
                inv_cond["op"] = "crosses_below"
            elif cond["op"] == "crosses_below":
                inv_cond["op"] = "crosses_above"
            elif cond["op"] == "above":
                inv_cond["op"] = "below"
            elif cond["op"] == "below":
                inv_cond["op"] = "above"
            exit_mask = exit_mask & _evaluate_condition(inv_cond, df, cache)
        signals[exit_mask] = -1

    # Where both entry and exit fire on same bar, entry wins
    both = (signals == 1) & (signals == -1)
    # (This shouldn't happen with mutually exclusive cross conditions, but safety)

    return signals


def _compute_indicator_data(parsed: dict, df: pd.DataFrame) -> dict:
    """Compute indicator overlay data for charting."""
    cache = {}
    overlays = {}

    # Collect all indicator references from conditions
    refs = []
    for section in ("entry_conditions", "exit_conditions"):
        for cond in parsed.get(section, []):
            for side in ("left", "right"):
                ref = cond.get(side, {})
                if ref.get("type") == "indicator":
                    refs.append(ref)

    for ref in refs:
        name = ref["name"].upper()
        period = ref.get("period")
        sub_field = ref.get("sub_field")
        label = f"{name}{period or ''}"
        if sub_field:
            label += f".{sub_field}"

        try:
            series = _resolve_series(ref, df, cache)
            # Convert to list of {time, value} for chart
            times = df.get("open_time")
            if times is not None:
                data = []
                for i in range(len(series)):
                    v = series.iloc[i]
                    if pd.notna(v):
                        data.append({"time": int(times.iloc[i]), "value": round(float(v), 6)})
                overlays[label] = data
        except Exception:
            pass

    return overlays


# ══════════════════════════════════════════════════════════════════════
# FULL BACKTEST INTEGRATION
# ══════════════════════════════════════════════════════════════════════

def run_strategy_backtest(
    code: str,
    symbol: str,
    market: str = "crypto",
    interval: str = "1d",
    limit: int = 500,
) -> dict:
    """Parse DSL code and run a full backtest using existing backtest engine.

    Returns same format as backtest_engine.run_backtest plus extra fields.
    """
    # 1. Parse
    parsed = parse_strategy(code)

    # 2. Validate
    validation = validate_strategy(parsed)
    if not validation["valid"]:
        return {
            "ok": False,
            "error": "Strateji geçersiz: " + "; ".join(validation["errors"]),
            "validation": validation,
        }

    # 3. Fetch candles (reuse backtest engine's fetcher)
    from app.core.backtest_engine import (
        _fetch_candles,
        _simulate_trades,
        _compute_metrics,
        _build_equity_curve,
        DEFAULT_INITIAL_BALANCE,
        DEFAULT_POSITION_SIZE,
    )

    _logger.info(
        "Strategy backtest: symbol=%s market=%s interval=%s limit=%d strategy=%s",
        symbol, market, interval, limit, parsed.get("name", "unnamed"),
    )

    df = _fetch_candles(symbol, market, interval, limit)
    if df.empty or len(df) < 10:
        return {
            "ok": False,
            "error": f"Yetersiz veri: {symbol} için {len(df)} mum bulundu (min 10 gerekli)",
        }

    # 4. Execute strategy
    signals = execute_strategy(parsed, df)

    # 5. Apply risk management (stop loss / take profit) into simulation
    sl_pct = parsed["risk"].get("stop_loss")
    tp_pct = parsed["risk"].get("take_profit")

    if sl_pct or tp_pct:
        trades = _simulate_trades_with_risk(
            df, signals, DEFAULT_INITIAL_BALANCE, DEFAULT_POSITION_SIZE,
            sl_pct, tp_pct,
        )
    else:
        trades = _simulate_trades(df, signals, DEFAULT_INITIAL_BALANCE, DEFAULT_POSITION_SIZE)

    # 6. Metrics
    metrics = _compute_metrics(trades, DEFAULT_INITIAL_BALANCE)

    # 7. Equity curve
    equity_curve = _build_equity_curve(trades, DEFAULT_INITIAL_BALANCE, df)

    # 8. Indicator overlay data
    indicator_overlays = _compute_indicator_data(parsed, df)

    # 9. Signal markers for chart
    markers = []
    times = df.get("open_time")
    closes = df["close"].astype(float)
    if times is not None:
        for i in range(len(signals)):
            sig = signals.iloc[i]
            if sig == 1:
                markers.append({
                    "time": int(times.iloc[i]),
                    "type": "buy",
                    "price": round(float(closes.iloc[i]), 6),
                })
            elif sig == -1:
                markers.append({
                    "time": int(times.iloc[i]),
                    "type": "sell",
                    "price": round(float(closes.iloc[i]), 6),
                })

    return {
        "ok": True,
        "symbol": symbol,
        "market": market,
        "strategy_name": parsed.get("name", "Custom Strategy"),
        "interval": interval,
        "candle_count": len(df),
        "trades": trades,
        "metrics": metrics,
        "equity_curve": equity_curve,
        "markers": markers,
        "indicator_overlays": indicator_overlays,
        "validation": validation,
        "parsed": {
            "name": parsed.get("name", ""),
            "entry_count": len(parsed.get("entry_conditions", [])),
            "exit_count": len(parsed.get("exit_conditions", [])),
            "risk": parsed.get("risk", {}),
        },
    }


def _simulate_trades_with_risk(
    df: pd.DataFrame,
    signals: pd.Series,
    initial_balance: float,
    position_size: float,
    sl_pct: Optional[float],
    tp_pct: Optional[float],
) -> list:
    """Walk-forward simulation with stop loss and take profit."""
    trades = []
    balance = initial_balance
    position = None

    for i in range(len(df)):
        sig = signals.iloc[i]
        row = df.iloc[i]
        price = float(row["close"])
        high = float(row.get("high", price))
        low = float(row.get("low", price))
        ts = int(row.get("open_time", i))

        # Check SL/TP if in position
        if position is not None:
            entry_p = position["entry_price"]
            hit_sl = sl_pct and low <= entry_p * (1 - sl_pct / 100)
            hit_tp = tp_pct and high >= entry_p * (1 + tp_pct / 100)

            if hit_sl:
                exit_price = entry_p * (1 - sl_pct / 100)
                pnl = (exit_price - entry_p) * position["quantity"]
                pnl_pct = ((exit_price / entry_p) - 1) * 100
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": ts,
                    "entry_price": round(entry_p, 6),
                    "exit_price": round(exit_price, 6),
                    "quantity": round(position["quantity"], 8),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "side": "long",
                    "bars_held": i - position["entry_idx"],
                    "exit_reason": "stop_loss",
                })
                balance += pnl
                position = None
                continue

            if hit_tp:
                exit_price = entry_p * (1 + tp_pct / 100)
                pnl = (exit_price - entry_p) * position["quantity"]
                pnl_pct = ((exit_price / entry_p) - 1) * 100
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": ts,
                    "entry_price": round(entry_p, 6),
                    "exit_price": round(exit_price, 6),
                    "quantity": round(position["quantity"], 8),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "side": "long",
                    "bars_held": i - position["entry_idx"],
                    "exit_reason": "take_profit",
                })
                balance += pnl
                position = None
                continue

        # Normal signal processing
        if sig == 1 and position is None:
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
            pnl = (price - position["entry_price"]) * position["quantity"]
            pnl_pct = ((price / position["entry_price"]) - 1) * 100 if position["entry_price"] > 0 else 0
            trades.append({
                "entry_time": position["entry_time"],
                "exit_time": ts,
                "entry_price": round(position["entry_price"], 6),
                "exit_price": round(price, 6),
                "quantity": round(position["quantity"], 8),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "side": "long",
                "bars_held": i - position["entry_idx"],
                "exit_reason": "signal",
            })
            balance += pnl
            position = None

    # Close remaining open position
    if position is not None and len(df) > 0:
        last_row = df.iloc[-1]
        price = float(last_row["close"])
        ts = int(last_row.get("open_time", len(df) - 1))
        pnl = (price - position["entry_price"]) * position["quantity"]
        pnl_pct = ((price / position["entry_price"]) - 1) * 100 if position["entry_price"] > 0 else 0
        trades.append({
            "entry_time": position["entry_time"],
            "exit_time": ts,
            "entry_price": round(position["entry_price"], 6),
            "exit_price": round(price, 6),
            "quantity": round(position["quantity"], 8),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "side": "long",
            "bars_held": len(df) - 1 - position["entry_idx"],
            "exit_reason": "end",
            "still_open": True,
        })

    return trades


# ══════════════════════════════════════════════════════════════════════
# BUILT-IN TEMPLATES
# ══════════════════════════════════════════════════════════════════════

BUILTIN_TEMPLATES = [
    {
        "id": "ema_cross",
        "name": "EMA Cross",
        "description": "EMA20 ve EMA50 kesişim stratejisi",
        "category": "Trend",
        "code": '''strategy "EMA Cross"

entry:
  EMA20 crosses above EMA50

exit:
  EMA20 crosses below EMA50

risk:
  stop_loss 2%
  take_profit 4%''',
    },
    {
        "id": "rsi_reversal",
        "name": "RSI Reversal",
        "description": "RSI aşırı alım/satım dönüş stratejisi",
        "category": "Osilatör",
        "code": '''strategy "RSI Reversal"

entry:
  RSI14 crosses above 30

exit:
  RSI14 crosses below 70

risk:
  stop_loss 3%
  take_profit 5%''',
    },
    {
        "id": "breakout",
        "name": "Breakout",
        "description": "Fiyat SMA kırılım stratejisi",
        "category": "Trend",
        "code": '''strategy "Breakout"

entry:
  CLOSE crosses above SMA20

exit:
  CLOSE crosses below SMA20

risk:
  stop_loss 2%
  take_profit 6%''',
    },
    {
        "id": "vwap_trend",
        "name": "VWAP Trend",
        "description": "VWAP trend takip stratejisi",
        "category": "Hacim",
        "code": '''strategy "VWAP Trend"

entry:
  CLOSE crosses above VWAP20

exit:
  CLOSE crosses below VWAP20

risk:
  stop_loss 2%
  take_profit 4%''',
    },
    {
        "id": "golden_cross",
        "name": "Golden Cross",
        "description": "SMA50/SMA200 altın kesişim",
        "category": "Trend",
        "code": '''strategy "Golden Cross"

entry:
  SMA50 crosses above SMA200

exit:
  SMA50 crosses below SMA200

risk:
  stop_loss 5%
  take_profit 10%''',
    },
    {
        "id": "macd_cross",
        "name": "MACD Crossover",
        "description": "MACD sinyal çizgisi kesişimi",
        "category": "Momentum",
        "code": '''strategy "MACD Crossover"

entry:
  MACD.line crosses above MACD.signal

exit:
  MACD.line crosses below MACD.signal

risk:
  stop_loss 3%
  take_profit 5%''',
    },
    {
        "id": "bb_bounce",
        "name": "Bollinger Bounce",
        "description": "Bollinger alt bandından sıçrama",
        "category": "Volatilite",
        "code": '''strategy "Bollinger Bounce"

entry:
  CLOSE crosses above BBANDS20.lower

exit:
  CLOSE crosses above BBANDS20.upper

risk:
  stop_loss 2%
  take_profit 4%''',
    },
]


def list_builtin_templates() -> list:
    """Return builtin strategy templates."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "code": t["code"],
        }
        for t in BUILTIN_TEMPLATES
    ]


def list_available_indicators() -> list:
    """Return available indicators for the UI."""
    return [
        {"name": k, "description": v["desc"], "args": v["args"]}
        for k, v in AVAILABLE_INDICATORS.items()
    ]
