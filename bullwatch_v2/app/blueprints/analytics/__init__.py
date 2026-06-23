"""Analytics Blueprint — FAZ 46.

Simple event tracking for landing, signup, onboarding, invite metrics.
"""
from __future__ import annotations

from flask import Blueprint

analytics_bp = Blueprint("analytics", __name__)

from app.blueprints.analytics import routes  # noqa: E402, F401
