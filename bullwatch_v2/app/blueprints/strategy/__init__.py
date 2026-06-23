# -*- coding: utf-8 -*-
"""Strategy Builder Blueprint — FAZ 25."""
from flask import Blueprint

strategy_bp = Blueprint(
    "strategy",
    __name__,
    url_prefix="/api/strategy",
)

from app.blueprints.strategy import routes  # noqa: E402, F401
