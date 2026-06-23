# -*- coding: utf-8 -*-
"""News Impact blueprint — FAZ 37 (AI Market Radar)."""
from flask import Blueprint

news_impact_bp = Blueprint(
    "news_impact",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.news_impact import routes  # noqa: E402, F401
