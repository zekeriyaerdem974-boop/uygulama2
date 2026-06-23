# -*- coding: utf-8 -*-
"""Legal Compliance Filter — FAZ 37 (Legal Safe Mode).

Provides platform-wide terminology filtering to ensure the platform
does not appear to give financial advice or trading signals.

Public API:
  is_legal_safe_mode()          → bool
  filter_text(text)             → str  (filtered text)
  filter_signal_type(sig_type)  → str  (BULLISH/BEARISH/NEUTRAL)
  filter_api_response(data)     → dict (filtered response)
  get_disclaimer()              → str
"""
from __future__ import annotations

import re
from typing import Dict

from app.core.analysis_engine import feature_enabled, set_feature

# ══════════════════════════════════════════════════════════════════
# FEATURE FLAG
# ══════════════════════════════════════════════════════════════════

_FLAG_NAME = "legal_safe_mode"


def _ensure_flag():
    """Ensure legal_safe_mode flag exists (default True)."""
    try:
        from app.core.analysis_engine import _get_conn, _now_iso
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO platform_features (name, enabled, updated_at) "
                "VALUES (?, ?, ?)",
                (_FLAG_NAME, 1, _now_iso())
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


_ensure_flag()


def is_legal_safe_mode() -> bool:
    """Check if Legal Safe Mode is active."""
    return feature_enabled(_FLAG_NAME)


# ══════════════════════════════════════════════════════════════════
# TERMINOLOGY MAPPING
# ══════════════════════════════════════════════════════════════════

_TERM_MAP = {
    # Longer patterns FIRST to avoid partial replacements
    "BUY SIGNAL": "BULLISH OUTLOOK",
    "SELL SIGNAL": "BEARISH OUTLOOK",
    "Buy Signal": "Bullish Outlook",
    "Sell Signal": "Bearish Outlook",
    "buy signal": "bullish outlook",
    "sell signal": "bearish outlook",
    "TRADING SIGNAL": "AI MARKET INSIGHT",
    "Trading Signal": "AI Market Insight",
    "trading signal": "ai market insight",
    "SIGNAL ALERT": "MARKET INSIGHT",
    "Signal Alert": "Market Insight",
    "signal alert": "market insight",
    "BUY": "BULLISH",
    "SELL": "BEARISH",
    "Buy": "Bullish",
    "Sell": "Bearish",
    "buy": "bullish",
    "sell": "bearish",
}

# Signal type mapping
_SIGNAL_TYPE_MAP = {
    "BUY": "BULLISH",
    "SELL": "BEARISH",
    "buy": "bullish",
    "sell": "bearish",
}

# API field renaming
_FIELD_RENAME = {
    "entry_price": "analysis_price",
    "exit_price": "close_price",
    "take_profit": "target_level",
    "stop_loss": "risk_level",
    "tp1": "target_1",
    "tp2": "target_2",
    "suggested_sl": "suggested_risk_level",
}


# ══════════════════════════════════════════════════════════════════
# FILTER FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def filter_signal_type(signal_type: str) -> str:
    """Convert BUY/SELL signal types to BULLISH/BEARISH."""
    if not is_legal_safe_mode():
        return signal_type
    return _SIGNAL_TYPE_MAP.get(signal_type, signal_type)


def filter_text(text: str) -> str:
    """Filter trading terminology from display text."""
    if not is_legal_safe_mode() or not text:
        return text
    result = text
    for old, new in _TERM_MAP.items():
        result = result.replace(old, new)
    return result


def filter_api_response(data: dict) -> dict:
    """Filter API response fields for compliance."""
    if not is_legal_safe_mode() or not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        new_key = _FIELD_RENAME.get(key, key)

        # Filter signal_type values
        if key == "signal_type" and isinstance(value, str):
            value = _SIGNAL_TYPE_MAP.get(value, value)

        # Recursively filter nested dicts
        if isinstance(value, dict):
            value = filter_api_response(value)
        elif isinstance(value, list):
            value = [
                filter_api_response(v) if isinstance(v, dict) else v
                for v in value
            ]

        result[new_key] = value

    return result


def get_disclaimer() -> str:
    """Get the legal disclaimer text."""
    return (
        "This platform provides market analysis, educational insights "
        "and community discussions. Nothing on this platform constitutes "
        "financial advice or investment recommendations. Users should "
        "conduct their own research before making financial decisions."
    )


def get_disclaimer_tr() -> str:
    """Get the legal disclaimer text in Turkish."""
    return (
        "Bu platform piyasa analizi, eğitim içerikleri ve topluluk "
        "tartışmaları sunar. Platformdaki hiçbir içerik yatırım tavsiyesi "
        "veya finansal öneri niteliği taşımaz. Kullanıcılar finansal "
        "kararlarını vermeden önce kendi araştırmalarını yapmalıdır."
    )


# ══════════════════════════════════════════════════════════════════
# COPILOT COMPLIANCE RULE
# ══════════════════════════════════════════════════════════════════

COPILOT_COMPLIANCE_RULE = (
    "You must not provide financial advice, buy/sell instructions, "
    "entry/exit prices or trading signals. Only provide market analysis "
    "and educational insight."
)
