"""Signals Blueprint — Signal engine & signal API endpoints.

FAZ 5 — Extracted from ``legacy_monolith.py``.
Registers with **no** ``url_prefix`` so that ``/api/signal`` and
``/api/signals`` remain unchanged.
"""
from __future__ import annotations

from flask import Blueprint

signals_bp = Blueprint(
    "signals",
    __name__,
    # No url_prefix — URLs stay exactly the same as before
)

# Import route modules so decorators execute and register on the blueprint
from app.blueprints.signals import routes  # noqa: E402, F401
