"""Dashboard Blueprint — HTML pages & dashboard API endpoints.

FAZ 4 — Extracted from ``legacy_monolith.py``.
Registers with **no** ``url_prefix`` so that all existing URLs
(``/``, ``/trade``, ``/api/fng``, etc.) remain unchanged.
"""
from __future__ import annotations

from flask import Blueprint

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    # No url_prefix — URLs stay exactly the same as before
)

# Import route modules so decorators execute and register on the blueprint
from app.blueprints.dashboard import routes, api  # noqa: E402, F401
