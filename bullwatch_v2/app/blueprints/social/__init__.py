# -*- coding: utf-8 -*-
"""Social blueprint — FAZ 31."""
from flask import Blueprint

social_bp = Blueprint(
    "social",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.social import routes  # noqa: E402, F401
