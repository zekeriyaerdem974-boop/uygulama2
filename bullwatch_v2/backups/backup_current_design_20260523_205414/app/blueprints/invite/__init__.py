# -*- coding: utf-8 -*-
from flask import Blueprint

invite_bp = Blueprint("invite", __name__)

from app.blueprints.invite import routes  # noqa: E402, F401
