from __future__ import annotations

from flask import Flask

from .config import Config
from .extensions import register_extensions
from .blueprints import register_blueprints
from .realtime import start_binance_ws_thread


def create_app(config_object: object | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    if config_object is None:
        app.config.from_object(Config)
    else:
        app.config.from_object(config_object)

    register_extensions(app)
    register_blueprints(app)

    app.before_request(start_binance_ws_thread)

    return app
