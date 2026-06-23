"""Ollama LLM client — tries ``/api/generate``, ``/api/chat``,
and ``/v1/chat/completions`` endpoints in order.

Extracted from ``legacy_monolith.py`` (FAZ 3).
"""
from __future__ import annotations

import os

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def ollama_generate(model: str, prompt: str, system: str | None = None,
                    stream: bool = False) -> dict:
    """Call Ollama with automatic endpoint fallback.

    Tries three endpoints in order:
    1. ``/api/generate``
    2. ``/api/chat``
    3. ``/v1/chat/completions`` (OpenAI-compat)

    Raises ``RuntimeError`` if all three fail.
    """
    base = OLLAMA_HOST.rstrip("/")
    payload = {"model": model, "prompt": prompt, "stream": stream}
    if system:
        payload["system"] = system

    # 1) /api/generate
    url = f"{base}/api/generate"
    try:
        r = requests.post(url, json=payload, timeout=120)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # Build messages for chat endpoints
    messages: list = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # 2) /api/chat
    url2 = f"{base}/api/chat"
    try:
        r2 = requests.post(url2, json={"model": model, "messages": messages, "stream": False}, timeout=120)
        if r2.status_code == 200:
            js = r2.json()
            text = js.get("message", {}).get("content") or js.get("response") or ""
            return {"response": text}
    except Exception:
        pass

    # 3) /v1/chat/completions (OpenAI compat)
    url3 = f"{base}/v1/chat/completions"
    try:
        r3 = requests.post(url3, json={"model": model, "messages": messages}, timeout=120)
        if r3.status_code == 200:
            js = r3.json()
            text = (js.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return {"response": text}
    except Exception:
        pass

    raise RuntimeError("Ollama API ulaşılamadı (generate/chat/completions).")
