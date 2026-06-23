# -*- coding: utf-8 -*-
"""Live Rooms blueprint — FAZ 34."""
from flask import Blueprint

live_rooms_bp = Blueprint(
    "live_rooms",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.live_rooms import routes  # noqa: E402, F401
