# -*- coding: utf-8 -*-
from flask import Blueprint

activity_bp = Blueprint("activity", __name__)

from app.blueprints.activity import routes  # noqa: E402, F401
