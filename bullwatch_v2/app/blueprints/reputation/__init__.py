# -*- coding: utf-8 -*-
from flask import Blueprint

reputation_bp = Blueprint("reputation", __name__, template_folder="../../../templates")

from app.blueprints.reputation import routes  # noqa: E402, F401
