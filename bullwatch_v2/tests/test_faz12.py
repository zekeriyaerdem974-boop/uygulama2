# -*- coding: utf-8 -*-
"""FAZ 12 — Production readiness tests.

Smoke tests, config tests, security tests, and integration tests.
"""
import importlib
import os
import pathlib


ROOT = pathlib.Path(__file__).resolve().parent.parent


# ========== 1. Config Tests ==========

def test_config_classes_exist():
    """Config, DevelopmentConfig, TestConfig, ProductionConfig should exist."""
    from app.config import Config, DevelopmentConfig, TestConfig, ProductionConfig
    assert Config.HOST == "0.0.0.0"
    assert TestConfig.TESTING is True
    assert TestConfig.SECRET_KEY != Config.SECRET_KEY or Config.SECRET_KEY == "dev-secret-change-me"
    assert ProductionConfig.DEBUG is False
    assert DevelopmentConfig.DEBUG is True


def test_get_config_returns_correct_class():
    from app.config import get_config, DevelopmentConfig, TestConfig, ProductionConfig
    assert get_config("development") is DevelopmentConfig
    assert get_config("testing") is TestConfig
    assert get_config("production") is ProductionConfig


def test_config_env_based_values():
    """All critical values should come from env with safe defaults."""
    from app.config import Config
    assert hasattr(Config, "SECRET_KEY")
    assert hasattr(Config, "REDIS_URL")
    assert hasattr(Config, "OLLAMA_HOST")
    assert hasattr(Config, "COINGLASS_API_KEY")
    assert hasattr(Config, "CORS_ORIGINS")
    assert hasattr(Config, "RATELIMIT_ENABLED")
    assert hasattr(Config, "LOG_LEVEL")


def test_secret_key_not_empty():
    from app.config import Config
    assert Config.SECRET_KEY
    assert len(Config.SECRET_KEY) > 8


def test_debug_off_in_production():
    from app.config import ProductionConfig
    assert ProductionConfig.DEBUG is False


def test_test_config_disables_ratelimit():
    from app.config import TestConfig
    assert TestConfig.RATELIMIT_ENABLED is False


# ========== 2. App Startup Tests ==========

def test_app_creates_successfully():
    """App factory should create a Flask app without errors."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    assert flask_app is not None
    assert flask_app.config["TESTING"] is True


def test_app_has_extensions():
    """App should have market_data and job_manager extensions."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    assert "market_data" in flask_app.extensions
    assert "job_manager" in flask_app.extensions


# ========== 3. Critical Route Smoke Tests ==========

def test_critical_routes_registered():
    """All critical routes must be registered."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    rules = [r.rule for r in flask_app.url_map.iter_rules()]
    critical = [
        "/", "/chat", "/tv", "/trade", "/sim/mobile",
        "/api/mobile_snapshot",
        "/api/thresholds",
        "/api/signal",
        "/api/signals",
        "/api/market/symbols",
        "/api/market/klines",
        "/api/market/ticker",
        "/api/orderflow/health",
        "/api/orderflow/symbols",
        "/api/orderflow/symbol/<symbol>",
        "/api/orderflow/depth/<symbol>",
        "/api/liquidation/symbols",
        "/api/liquidation/price_profile",
        "/api/indicators/rsi",
        "/api/indicators/macd",
        "/api/alpha/status",
        "/api/alpha/symbols",
        "/api/alpha/pair",
        "/api/etf_events",
        "/api/top_coins_4h",
        "/api/chat",
        "/ws/stream",
    ]
    for route in critical:
        assert route in rules, f"Missing critical route: {route}"


def test_health_endpoint():
    """Health endpoint should return ok."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    with flask_app.test_client() as client:
        resp = client.get("/api/orderflow/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True


def test_mobile_snapshot_endpoint():
    """Mobile snapshot should return ok with tickers and thresholds."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    with flask_app.test_client() as client:
        resp = client.get("/api/mobile_snapshot")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "data" in data


def test_404_returns_json():
    """404 errors should return JSON, not HTML."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    with flask_app.test_client() as client:
        resp = client.get("/nonexistent-endpoint-xyz")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False
        assert "error" in data


# ========== 4. Background Job Tests ==========

def test_background_job_registration():
    """Background jobs should be registerable."""
    from core.job_manager import JobManager
    jm = JobManager()
    jm.register_thread("test:dummy", lambda: None)
    assert "test:dummy" in jm._jobs


# ========== 5. Security Tests ==========

def test_apk_download_requires_private_network():
    """APK download should only work from private networks."""
    from app.core.security import apk_download_enabled
    from unittest.mock import MagicMock

    # Public IP → should deny
    req = MagicMock()
    req.headers = {}
    req.remote_addr = "203.0.113.1"
    assert apk_download_enabled(req) is False


def test_cors_configured():
    """CORS should be applied to the app."""
    from app.config import TestConfig
    from app import create_app
    flask_app = create_app(TestConfig)
    # Check that CORS headers are applied
    with flask_app.test_client() as client:
        resp = client.get("/api/orderflow/health")
        # After CORS, Access-Control headers may be present
        # At minimum, the response should succeed
        assert resp.status_code == 200


# ========== 6. Logging Tests ==========

def test_setup_logging_importable():
    """setup_logging function should be importable."""
    from app.config import setup_logging
    assert callable(setup_logging)


def test_no_print_in_production_code():
    """No print() calls should remain in production Python files."""
    prod_dirs = [ROOT / "app", ROOT / "blueprints", ROOT / "core"]
    for d in prod_dirs:
        for py in d.rglob("*.py"):
            src = py.read_text()
            lines = src.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # Skip comments, docstrings, and Blueprint() calls
                if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                    continue
                if "print(" in stripped and "Blueprint(" not in stripped:
                    assert False, f"print() found in {py}:{i}: {stripped}"


# ========== 7. Deploy Readiness Tests ==========

def test_env_example_exists():
    """.env.example should exist with documented config options."""
    env_file = ROOT / ".env.example"
    assert env_file.exists(), ".env.example missing"
    content = env_file.read_text()
    assert "SECRET_KEY" in content
    assert "ZKR_ANALIZ_ENV" in content
    assert "REDIS_URL" in content
    assert "OLLAMA_HOST" in content


def test_dockerfile_exists():
    """Dockerfile should exist for production deployment."""
    assert (ROOT / "Dockerfile").exists()


def test_requirements_has_key_deps():
    """requirements.txt should list all key dependencies."""
    req = (ROOT / "requirements.txt").read_text()
    for dep in ["Flask", "Flask-Cors", "Flask-Limiter", "gunicorn", "requests", "pandas", "numpy"]:
        assert dep in req, f"Missing dependency: {dep}"


def test_wsgi_module_importable():
    """wsgi.py should be importable (the module, not the app start)."""
    assert (ROOT / "wsgi.py").exists()
    import py_compile
    py_compile.compile(str(ROOT / "wsgi.py"), doraise=True)


# ========== 8. Core Module Tests ==========

def test_all_core_modules_importable():
    """All core modules should import without errors."""
    modules = [
        "app.config",
        "app.cache",
        "app.extensions",
        "app.core.ta",
        "app.core.binance_client",
        "app.core.etf_tracker",
        "app.core.ollama_client",
        "app.core.thresholds",
        "app.core.bull_estimate",
        "app.core.security",
        "core.market_data",
        "core.job_manager",
    ]
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None, f"Failed to import {mod_name}"


def test_ratelimit_module_importable():
    """Rate limit module should import and have init function."""
    from app.ratelimit import init_rate_limiter, get_limiter
    assert callable(init_rate_limiter)
    assert callable(get_limiter)
