# -*- coding: utf-8 -*-
from flask import Blueprint

opportunities_bp = Blueprint("opportunities", __name__)

from app.blueprints.opportunities import routes  # noqa: E402, F401
