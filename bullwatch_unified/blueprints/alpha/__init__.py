from flask import Blueprint

alpha_bp = Blueprint("alpha", __name__, url_prefix="/alpha")

from . import routes  # noqa: E402,F401
