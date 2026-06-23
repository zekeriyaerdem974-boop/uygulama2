# -*- coding: utf-8 -*-
"""Mentors blueprint — FAZ 32."""
from flask import Blueprint

mentors_bp = Blueprint(
    "mentors",
    __name__,
    template_folder="../../../templates",
)

from app.blueprints.mentors import routes  # noqa: E402, F401
