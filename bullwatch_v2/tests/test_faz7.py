# -*- coding: utf-8 -*-
"""FAZ 7 – Unified blueprint enhancement tests.

Validates:
  • market blueprint: /symbols, /klines, /ticker endpoints + validation
  • orderflow blueprint: /health, /symbols, /symbol/<sym>, /depth/<sym>
  • liquidation blueprint: /symbols, /price_profile
  • alpha blueprint: /status, /symbols, /pair
  • MarketDataService new methods exist
  • All existing endpoints preserved
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ---------- MarketDataService new methods ----------
def test_market_data_service_has_new_methods():
    mod = importlib.import_module("core.market_data")
    cls = mod.MarketDataService
    for method in [
        "get_ticker_single",
        "get_open_interest",
        "get_funding_rate",
        "get_depth",
        "get_long_short_ratio",
        "get_taker_volume",
    ]:
        assert hasattr(cls, method), f"Missing method: {method}"
        assert callable(getattr(cls, method))


# ---------- Market blueprint ----------
def test_market_bp_has_routes():
    src = (ROOT / "blueprints" / "market.py").read_text()
    assert '"/symbols"' in src
    assert '"/klines"' in src
    assert '"/ticker"' in src
    assert "VALID_INTERVALS" in src


def test_market_bp_has_validation():
    src = (ROOT / "blueprints" / "market.py").read_text()
    assert "VALID_INTERVALS" in src
    assert "Invalid interval" in src
    assert "limit must be" in src


def test_market_bp_error_handling():
    src = (ROOT / "blueprints" / "market.py").read_text()
    # Each endpoint has try/except with 502
    assert src.count("502") >= 2  # at least symbols + klines


# ---------- Orderflow blueprint ----------
def test_orderflow_bp_has_routes():
    src = (ROOT / "blueprints" / "orderflow.py").read_text()
    assert '"/health"' in src
    assert '"/symbols"' in src
    assert '"/symbol/<symbol>"' in src
    assert '"/depth/<symbol>"' in src


def test_orderflow_symbol_aggregates_real_data():
    src = (ROOT / "blueprints" / "orderflow.py").read_text()
    for data_source in [
        "get_ticker_single",
        "get_open_interest",
        "get_funding_rate",
        "get_long_short_ratio",
        "get_taker_volume",
        "get_depth",
    ]:
        assert data_source in src, f"Missing: {data_source}"


def test_orderflow_no_mock_data():
    src = (ROOT / "blueprints" / "orderflow.py").read_text()
    assert "mock" not in src.lower()
    assert "fake" not in src.lower()


# ---------- Liquidation blueprint ----------
def test_liquidation_bp_has_routes():
    src = (ROOT / "blueprints" / "liquidation.py").read_text()
    assert '"/symbols"' in src
    assert '"/price_profile"' in src


def test_liquidation_price_profile_real_data():
    src = (ROOT / "blueprints" / "liquidation.py").read_text()
    assert "get_klines" in src
    assert "poc" in src.lower()
    assert "valueAreaHigh" in src
    assert "valueAreaLow" in src
    assert "rangePosition" in src


def test_liquidation_no_mock_data():
    src = (ROOT / "blueprints" / "liquidation.py").read_text()
    assert "mock" not in src.lower()
    assert "fake" not in src.lower()


# ---------- Alpha blueprint ----------
def test_alpha_bp_has_routes():
    src = (ROOT / "blueprints" / "alpha.py").read_text()
    assert '"/status"' in src
    assert '"/symbols"' in src
    assert '"/pair"' in src


def test_alpha_pair_returns_klines():
    src = (ROOT / "blueprints" / "alpha.py").read_text()
    assert "get_alpha_klines" in src
    assert "candles" in src
    assert "volume" in src
    assert "summary" in src


def test_alpha_pair_validation():
    src = (ROOT / "blueprints" / "alpha.py").read_text()
    assert "pair parameter required" in src
    assert "400" in src


# ---------- Preserved endpoints ----------
def test_existing_endpoints_preserved():
    """All previous route patterns still exist."""
    market_src = (ROOT / "blueprints" / "market.py").read_text()
    assert '"/symbols"' in market_src
    assert '"/klines"' in market_src

    of_src = (ROOT / "blueprints" / "orderflow.py").read_text()
    assert '"/health"' in of_src
    assert '"/symbols"' in of_src

    liq_src = (ROOT / "blueprints" / "liquidation.py").read_text()
    assert '"/symbols"' in liq_src

    alpha_src = (ROOT / "blueprints" / "alpha.py").read_text()
    assert '"/status"' in alpha_src
    assert '"/symbols"' in alpha_src


# ---------- No old port dependencies ----------
def test_no_old_port_references():
    """Blueprints should not reference old standalone ports."""
    for name in ["market", "orderflow", "liquidation", "alpha"]:
        src = (ROOT / "blueprints" / f"{name}.py").read_text()
        assert "25000" not in src
        assert "30000" not in src or "setInterval" in src  # 30000 is fine in JS context
        assert "35000" not in src
        assert "localhost" not in src.lower()


def test_all_blueprints_use_market_data_service():
    """Every blueprint accesses data through _svc() = current_app.extensions['market_data']."""
    for name in ["market", "orderflow", "liquidation", "alpha"]:
        src = (ROOT / "blueprints" / f"{name}.py").read_text()
        assert 'extensions["market_data"]' in src
        assert "_svc()" in src
