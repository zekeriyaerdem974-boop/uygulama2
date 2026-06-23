from flask import Blueprint

core_bp = Blueprint("core", __name__)

from . import routes  # noqa: E402,F401
