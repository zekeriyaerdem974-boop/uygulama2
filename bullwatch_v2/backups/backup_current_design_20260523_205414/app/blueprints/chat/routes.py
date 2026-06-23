"""Chat API route — POST /api/chat.

Extracted from ``legacy_monolith.py`` (FAZ 6).
"""
from __future__ import annotations

import json

from flask import jsonify, request

from app.cache import cache_get, cache_set, utcnow
from app.core.ollama_client import ollama_generate

from . import chat_bp
from .context import CHAT_REFRESH_SEC, warm_chat_context_async


@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():
    # Rate limit: /api/chat is heavy (Ollama call) — handled by global limiter
    try:
        body = request.get_json(force=True)
        model = body.get("model", "llama3.1:8b-instruct-q6_K")
        messages = body.get("messages", [])

        # Hazır chat_context'i kullan
        context = cache_get("chat_context", ttl=CHAT_REFRESH_SEC + 30)
        if context is None:
            # İlk kullanımda senkron bloklamayalım; arkaplanda hazırlansın.
            placeholder = {"generated_at": utcnow().isoformat(), "status": "warming_up"}
            cache_set("chat_context", placeholder)
            warm_chat_context_async()
            context = placeholder

        sys_prompt = "You are a local crypto assistant. Use the JSON CONTEXT as latest truth. Answer in Turkish."
        prompt = f"[CONTEXT JSON]\n{json.dumps(context, ensure_ascii=False)}\n\n"
        for m in messages:
            role = m.get('role', 'user'); content = m.get('content', '')
            prompt += f"{role}: {content}\n"
        prompt += "assistant:"

        resp = ollama_generate(model, prompt, system=sys_prompt, stream=False)
        out = (resp.get("response") or "").strip()
        return jsonify({"ok": True, "data": {"response": out}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
