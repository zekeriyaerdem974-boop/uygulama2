# -*- coding: utf-8 -*-
"""Simulator Blueprint — FAZ 22."""
from flask import Blueprint

simulator_bp = Blueprint(
    "simulator",
    __name__,
    url_prefix="/api/simulator",
)

from app.blueprints.simulator import routes  # noqa: E402, F401
