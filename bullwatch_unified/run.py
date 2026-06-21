import os

from bullwatch_unified import create_app
from bullwatch_unified.extensions import socketio

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "34000"))
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=app.config.get("DEBUG", False),
        allow_unsafe_werkzeug=True,
    )
