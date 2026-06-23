# -*- coding: utf-8 -*-
"""Analysis blueprint — FAZ 36 (Viral Sharing)."""
from flask import Blueprint

analysis_bp = Blueprint(
    "analysis",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.analysis import routes  # noqa: E402, F401

from app.blueprints.analysis import routes  # noqa: E402,F401
