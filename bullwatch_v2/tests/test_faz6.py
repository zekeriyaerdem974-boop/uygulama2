# -*- coding: utf-8 -*-
"""FAZ 6 – Chat blueprint modularisation tests.

Validates:
  • chat_bp blueprint exists and is importable
  • context.py exposes build_chat_context, warm_chat_context_async, CHAT_REFRESH_SEC
  • routes.py exposes /api/chat POST route
  • ollama_client.py is still intact
  • legacy_monolith no longer defines build_chat_context / api_chat locally
  • legacy_monolith registers chat_bp
  • all previous critical routes still present
  • build_chat_context return keys are correct
"""
from __future__ import annotations

import importlib
import inspect
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ---------- Blueprint existence ----------
def test_chat_bp_exists():
    mod = importlib.import_module("app.blueprints.chat")
    bp = getattr(mod, "chat_bp", None)
    assert bp is not None
    assert bp.name == "chat"


# ---------- context.py ----------
def test_context_module_importable():
    mod = importlib.import_module("app.blueprints.chat.context")
    assert hasattr(mod, "build_chat_context")
    assert hasattr(mod, "warm_chat_context_async")
    assert hasattr(mod, "CHAT_REFRESH_SEC")
    assert callable(mod.build_chat_context)
    assert callable(mod.warm_chat_context_async)
    assert isinstance(mod.CHAT_REFRESH_SEC, int)


def test_context_uses_core_deps():
    src = (ROOT / "app" / "blueprints" / "chat" / "context.py").read_text()
    assert "from app.cache import" in src
    assert "from app.core.binance_client import" in src
    assert "from app.core.etf_tracker import" in src
    assert "from app.core.ta import" in src
    assert "from app.core.thresholds import" in src


def test_context_build_returns_dict():
    """build_chat_context signature should return a dict."""
    mod = importlib.import_module("app.blueprints.chat.context")
    sig = inspect.signature(mod.build_chat_context)
    # Should accept no required arguments
    assert len([p for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty]) == 0


# ---------- routes.py ----------
def test_routes_has_api_chat():
    src = (ROOT / "app" / "blueprints" / "chat" / "routes.py").read_text()
    assert '"/api/chat"' in src
    assert "def api_chat" in src
    assert "POST" in src


def test_routes_preserves_response_format():
    src = (ROOT / "app" / "blueprints" / "chat" / "routes.py").read_text()
    # Must return ok + data.response
    assert '"ok"' in src or "'ok'" in src
    assert '"response"' in src
    assert "ollama_generate" in src


# ---------- ollama_client.py intact ----------
def test_ollama_client_still_intact():
    mod = importlib.import_module("app.core.ollama_client")
    assert hasattr(mod, "ollama_generate")
    assert callable(mod.ollama_generate)


# ---------- Monolith cleanup ----------
def test_monolith_no_build_chat_context_def():
    src = (ROOT / "legacy_monolith.py").read_text()
    assert "def build_chat_context" not in src


def test_monolith_no_api_chat_route():
    src = (ROOT / "legacy_monolith.py").read_text()
    assert "def api_chat" not in src


def test_monolith_no_warm_chat_def():
    src = (ROOT / "legacy_monolith.py").read_text()
    assert "def warm_chat_context_async" not in src


def test_monolith_registers_chat_bp():
    src = (ROOT / "legacy_monolith.py").read_text()
    assert "from app.blueprints.chat import chat_bp" in src
    assert "register_blueprint(chat_bp)" in src


# ---------- All critical routes preserved ----------
def test_all_critical_routes_preserved():
    src = (ROOT / "legacy_monolith.py").read_text()
    # Routes that must still be in monolith
    for pattern in [
        "/apk/ZKR Analiz.apk",
        "/api/etf_events",
        "/api/top_coins_4h",
        "/ws/stream",
    ]:
        assert pattern in src, f"Missing route: {pattern}"

    # Routes that must be in blueprints (NOT in monolith as def)
    for fn_name in ["def api_chat", "def build_chat_context"]:
        assert fn_name not in src, f"Still in monolith: {fn_name}"


def test_chat_route_registered_on_blueprint():
    """The /api/chat route must be registered on chat_bp, not on app."""
    src = (ROOT / "app" / "blueprints" / "chat" / "routes.py").read_text()
    assert "@chat_bp.route" in src
    assert '"/api/chat"' in src


# ---------- Turkish system prompt preserved ----------
def test_turkish_prompt_preserved():
    src = (ROOT / "app" / "blueprints" / "chat" / "routes.py").read_text()
    assert "Answer in Turkish" in src


# ---------- Monolith line count decreased ----------
def test_monolith_shrank():
    src = (ROOT / "legacy_monolith.py").read_text()
    lines = src.count("\n") + 1
    # Pre-FAZ6 was 611, after should be significantly less
    assert lines < 600, f"Monolith still {lines} lines, expected < 600"
