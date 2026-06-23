from flask import Blueprint

orderflow_bp = Blueprint("orderflow", __name__, url_prefix="/orderflow")

from . import routes  # noqa: E402,F401
