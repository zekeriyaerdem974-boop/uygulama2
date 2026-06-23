from __future__ import annotations

from flask import Flask

from .config import Config
from .extensions import register_extensions, db
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

    # Models'i import et (veritabanı tanımlaması için)
    with app.app_context():
        from . import models  # noqa

    # Socket.IO event handlers'ı import et (register ediliyor)
    with app.app_context():
        from . import socket_events  # noqa

    app.before_request(start_binance_ws_thread)

    return app
