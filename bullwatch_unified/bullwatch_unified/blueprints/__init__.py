from flask import Flask

from .alpha import alpha_bp
from .core import core_bp
from .liquidation import liquidation_bp
from .orderflow import orderflow_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(core_bp)
    app.register_blueprint(orderflow_bp)
    app.register_blueprint(liquidation_bp)
    app.register_blueprint(alpha_bp)
