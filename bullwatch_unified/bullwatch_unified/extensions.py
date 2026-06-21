from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")


def register_extensions(app: Flask) -> None:
    socketio.init_app(app, async_mode="threading")
