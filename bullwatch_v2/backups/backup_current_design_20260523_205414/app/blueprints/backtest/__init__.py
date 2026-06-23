# -*- coding: utf-8 -*-
"""Backtest Blueprint — FAZ 23."""
from flask import Blueprint

backtest_bp = Blueprint(
    "backtest",
    __name__,
    url_prefix="/api/backtest",
)

from app.blueprints.backtest import routes  # noqa: E402, F401
