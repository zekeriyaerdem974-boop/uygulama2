"""Rate limiting middleware for ZKR Analiz.

FAZ 12 — Production hardening.
Uses Flask-Limiter with in-memory storage (no Redis dependency).
Configurable via RATELIMIT_ENABLED and RATELIMIT_DEFAULT env vars.

Strategy:
  - Default: 120 req/min per IP for all endpoints
  - Heavy endpoints (/api/chat, /api/alpha/*): stricter limits
  - Health/status endpoints: exempt
  - Localhost/private IPs: more lenient in development
"""
from __future__ import annotations

import logging
from typing import Optional

from flask import Flask

_logger = logging.getLogger("zkr_analiz.ratelimit")

# Will be initialized by init_rate_limiter()
_limiter = None


def init_rate_limiter(app: Flask) -> Optional[object]:
    """Initialize Flask-Limiter on the app.

    Returns the limiter instance (or None if disabled).
    """
    global _limiter

    if not app.config.get("RATELIMIT_ENABLED", True):
        _logger.info("Rate limiting disabled by config")
        return None

    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address
    except ImportError:
        _logger.warning("flask-limiter not installed; rate limiting disabled")
        return None

    default_limit = app.config.get("RATELIMIT_DEFAULT", "120/minute")

    try:
        _limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=[default_limit],
            storage_uri="memory://",
            # Don't fail if storage is unavailable
            swallow_errors=True,
        )
    except (AssertionError, RuntimeError) as exc:
        # Flask raises AssertionError if app already handled requests
        # (e.g. when create_app() is called multiple times in tests)
        _logger.debug("Rate limiter skipped (app already running): %s", exc)
        return None

    # Exempt health endpoints
    for endpoint in ("orderflow.health",):
        try:
            _limiter.exempt(app.view_functions.get(endpoint, lambda: None))
        except Exception:
            pass

    _logger.info("Rate limiting initialized — default=%s", default_limit)
    return _limiter


def get_limiter():
    """Get the current limiter instance (may be None)."""
    return _limiter
