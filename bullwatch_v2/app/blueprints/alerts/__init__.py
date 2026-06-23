# -*- coding: utf-8 -*-
"""Alerts Blueprint — FAZ 20.

Registers with **no** ``url_prefix`` so that ``/api/alerts`` stays clean.
"""
from __future__ import annotations

from flask import Blueprint

alerts_bp = Blueprint("alerts", __name__)

from app.blueprints.alerts import routes  # noqa: E402, F401
