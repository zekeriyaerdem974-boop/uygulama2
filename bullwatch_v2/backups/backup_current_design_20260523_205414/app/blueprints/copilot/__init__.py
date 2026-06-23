# -*- coding: utf-8 -*-
"""Copilot blueprint — FAZ 21."""
from flask import Blueprint

copilot_bp = Blueprint("copilot", __name__)

from . import routes  # noqa: E402, F401
