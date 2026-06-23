from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

socketio = SocketIO(cors_allowed_origins="*")
db = SQLAlchemy()
migrate = Migrate()


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, async_mode="threading")
