from flask import Blueprint

liquidation_bp = Blueprint("liquidation", __name__, url_prefix="/liquidation")

from . import routes  # noqa: E402,F401
