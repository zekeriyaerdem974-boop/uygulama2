"""WSGI entry point for production deployment.

Usage with gunicorn:
    gunicorn wsgi:app -b 127.0.0.1:48200 --workers 1 --threads 4

Environment:
    Set ZKR_ANALIZ_ENV=production for production settings.
    See .env.example for all available configuration options.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force production config when running via WSGI (unless overridden)
if "ZKR_ANALIZ_ENV" not in os.environ:
    os.environ["ZKR_ANALIZ_ENV"] = "production"

from app import create_app, start_background_jobs

app = create_app()
start_background_jobs()
