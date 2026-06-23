"""Onboarding Blueprint — FAZ 46.

Routes for the onboarding wizard and landing page.
"""
from __future__ import annotations

from flask import Blueprint

onboarding_bp = Blueprint("onboarding", __name__)

from app.blueprints.onboarding import routes  # noqa: E402, F401
