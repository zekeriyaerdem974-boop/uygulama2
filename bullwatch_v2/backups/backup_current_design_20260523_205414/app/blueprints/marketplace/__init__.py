# -*- coding: utf-8 -*-
"""Marketplace blueprint — FAZ 29."""
from flask import Blueprint

marketplace_bp = Blueprint(
    "marketplace",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.marketplace import routes  # noqa: E402, F401
