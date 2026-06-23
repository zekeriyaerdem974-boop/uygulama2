"""ZKR Analiz Unified App Package.

Provides ``create_app()`` factory and ``start_background_jobs()``
entry points.

FAZ 12 — Production hardening:
  * Environment-aware config (dev/test/prod)
  * Centralized logging setup
  * Error handler registration
  * Rate limiting integration
"""
from __future__ import annotations

import logging

logger = logging.getLogger("zkr_analiz.app")


def create_app(config_object=None):
    """Application factory.

    1. Imports ``legacy_monolith`` (triggers route registration).
    2. Applies centralized ``Config`` from ``app.config``.
    3. Sets up logging, error handlers, and extensions.

    Args:
        config_object: Optional config class/object to override defaults.

    Returns:
        The configured Flask application instance.
    """
    from app.config import get_config, setup_logging
    from app.extensions import init_extensions

    # Determine config
    if config_object is None:
        config_object = get_config()

    # Importing the monolith triggers Flask app creation,
    # route registration, CORS, Sock, and blueprint mounting.
    import legacy_monolith

    flask_app = legacy_monolith.app

    # Apply centralized configuration
    flask_app.config.from_object(config_object)

    # Initialize logging
    setup_logging(flask_app)

    # Ensure extension singletons are discoverable by blueprints
    init_extensions(flask_app)

    # Rate limiting & error handlers (skip if app already served requests — test safety)
    try:
        from app.ratelimit import init_rate_limiter
        init_rate_limiter(flask_app)
        _register_error_handlers(flask_app)
    except (AssertionError, RuntimeError):
        # Flask raises if app already handled requests (multiple create_app in tests)
        pass

    logger.info(
        "App created — env=%s debug=%s port=%s",
        flask_app.config.get("ENV", "?"),
        flask_app.config.get("DEBUG", False),
        flask_app.config.get("PORT", 34000),
    )

    return flask_app


def _register_error_handlers(app):
    """Register JSON error handlers for common HTTP errors."""
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"ok": False, "error": "Bad request", "detail": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"ok": False, "error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"ok": False, "error": "Method not allowed"}), 405

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"ok": False, "error": "Rate limit exceeded. Try again later."}), 429

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Internal server error: %s", e)
        return jsonify({"ok": False, "error": "Internal server error"}), 500


def start_background_jobs():
    """Start all background refresh loops (idempotent).

    Delegates to ``app.background.jobs`` which uses
    JobManager for thread lifecycle.  No thread starts at import time.
    """
    from app.background.jobs import start_background_jobs as _start

    _start()
    logger.info("Background jobs started")
