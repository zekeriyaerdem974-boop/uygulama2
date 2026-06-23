# -*- coding: utf-8 -*-
"""Multi-market blueprint registration.

FAZ 16 — Stocks, BIST, Forex, Commodities API routes.
"""
from flask import Blueprint

markets_bp = Blueprint("markets", __name__)

from app.blueprints.markets import routes  # noqa: E402, F401
