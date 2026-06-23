# -*- coding: utf-8 -*-
"""Screener blueprint registration.

FAZ 17 — Multi-Market Screener API.
"""
from flask import Blueprint

screener_bp = Blueprint("screener", __name__)

from app.blueprints.screener import routes  # noqa: E402, F401
