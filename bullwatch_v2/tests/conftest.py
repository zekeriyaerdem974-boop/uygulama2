# -*- coding: utf-8 -*-
"""Shared pytest fixtures and configuration for ZKR Analiz test suite."""
from __future__ import annotations

import os
import sys

# Ensure project root on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Set TESTING env var so background jobs are skipped
os.environ.setdefault("TESTING", "1")

import pytest


@pytest.fixture(scope="session")
def app():
    """Create Flask test app with TESTING=True."""
    from app import create_app
    _app = create_app()
    _app.config["TESTING"] = True
    return _app


@pytest.fixture(scope="session")
def client(app):
    """Flask test client."""
    return app.test_client()
