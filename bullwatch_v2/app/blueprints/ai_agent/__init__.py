# -*- coding: utf-8 -*-
"""AI Agent blueprint — FAZ 49."""
from flask import Blueprint

ai_agent_bp = Blueprint("ai_agent", __name__)

from . import routes  # noqa: E402, F401
