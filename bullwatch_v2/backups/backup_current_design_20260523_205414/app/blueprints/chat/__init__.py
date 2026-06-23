"""Chat blueprint — /api/chat endpoint and context helpers.

Extracted from ``legacy_monolith.py`` (FAZ 6).
"""
from __future__ import annotations

from flask import Blueprint

chat_bp = Blueprint("chat", __name__)

# Register routes
from . import routes  # noqa: E402, F401
