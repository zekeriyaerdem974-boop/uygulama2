# -*- coding: utf-8 -*-
from flask import Blueprint

portfolio_bp = Blueprint("portfolio", __name__)

from app.blueprints.portfolio import routes  # noqa: E402, F401
