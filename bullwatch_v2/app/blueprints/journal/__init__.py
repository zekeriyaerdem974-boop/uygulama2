# -*- coding: utf-8 -*-
"""Journal Blueprint — FAZ 23."""
from flask import Blueprint

journal_bp = Blueprint(
    "journal",
    __name__,
    url_prefix="/api/journal",
)

from app.blueprints.journal import routes  # noqa: E402, F401
