# -*- coding: utf-8 -*-
"""Courses blueprint — FAZ 33."""
from flask import Blueprint

courses_bp = Blueprint(
    "courses",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.courses import routes  # noqa: E402, F401
