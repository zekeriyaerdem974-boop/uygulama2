#!/usr/bin/env python
"""ZKR Analiz unified entry point.

Usage:
    python run.py                          # development (default)
    ZKR_ANALIZ_ENV=production python run.py  # production mode

Starts the Flask dev server on port 34000 with background jobs.
"""
from __future__ import annotations

import logging
import os
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, start_background_jobs
from app.extensions import socketio
from app.config import get_config

logger = logging.getLogger("zkr_analiz")

app = create_app()


if __name__ == "__main__":
    start_background_jobs()

    cfg = get_config()
    host = getattr(cfg, "HOST", "0.0.0.0")
    port = getattr(cfg, "PORT", 34000)
    debug = getattr(cfg, "DEBUG", False)

    logger.info("Serving on http://%s:%s  debug=%s  env=%s",
                host, port, debug, getattr(cfg, "ENV", "?"))

    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
