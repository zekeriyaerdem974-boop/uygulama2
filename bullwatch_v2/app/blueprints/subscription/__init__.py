# -*- coding: utf-8 -*-
"""Subscription blueprint — FAZ 36."""
from flask import Blueprint

subscription_bp = Blueprint("subscription", __name__)

from app.blueprints.subscription import routes  # noqa: E402,F401
