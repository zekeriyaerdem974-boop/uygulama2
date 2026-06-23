"""Centralized configuration for ZKR Analiz.

Values are read from environment variables with sensible defaults.
This module is the single source of truth for all configuration.

FAZ 12 — Production hardening:
  - Dev / Test / Production config classes
  - All secrets env-based with safe fallbacks
  - Production SECRET_KEY enforcement
  - Centralized logging configuration
  - Rate limiting defaults
"""
from __future__ import annotations

import logging
import os
import secrets
import sys
import warnings


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Config:
    """Base configuration — all values come from env with safe defaults."""

    # --- Environment ---
    ENV = os.getenv("ZKR_ANALIZ_ENV", "development")

    # --- Security ---
    # In production, SECRET_KEY *must* be set via env.
    # In dev, a deterministic fallback is used (with a warning).
    _secret_from_env = os.getenv("SECRET_KEY")
    if _secret_from_env:
        SECRET_KEY = _secret_from_env
    else:
        SECRET_KEY = "dev-secret-change-me"
        if os.getenv("ZKR_ANALIZ_ENV", "development") == "production":
            warnings.warn(
                "SECRET_KEY is not set! Using random key. "
                "Set SECRET_KEY env var for production.",
                stacklevel=1,
            )
            SECRET_KEY = secrets.token_hex(32)

    DEBUG = _env_bool("ZKR_ANALIZ_DEBUG")

    # --- Server ---
    HOST = os.getenv("ZKR_ANALIZ_HOST", "0.0.0.0")
    PORT = _env_int("ZKR_ANALIZ_PORT", 34000)

    # --- Redis (optional cache backend) ---
    REDIS_URL = os.getenv("REDIS_URL")

    # --- Ollama LLM ---
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

    # --- Coinglass ---
    COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")

    # --- Refresh intervals ---
    CHAT_REFRESH_SEC = _env_int("CHAT_REFRESH_SEC", 60)
    TOP4H_REFRESH_SEC = _env_int("TOP4H_REFRESH_SEC", 900)
    TOP4H_MAX_SYMBOLS = _env_int("TOP4H_MAX_SYMBOLS", 500)
    TOP4H_KLINES = _env_int("TOP4H_KLINES", 500)

    # --- APK distribution ---
    ZKR_ANALIZ_ENABLE_APK = _env_bool("ZKR_ANALIZ_ENABLE_APK")

    # --- Rate limiting ---
    RATELIMIT_ENABLED = _env_bool("RATELIMIT_ENABLED", default=True)
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "120/minute")

    # --- CORS ---
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # --- Test mode ---
    TEST_MODE = _env_bool("TEST_MODE")

    # --- Flask niceties ---
    TEMPLATES_AUTO_RELOAD = True
    JSON_SORT_KEYS = False

    # --- Logging ---
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class DevelopmentConfig(Config):
    """Local development overrides."""

    ENV = "development"
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    LOG_LEVEL = "DEBUG"


class TestConfig(Config):
    """Overrides for pytest / CI."""

    ENV = "testing"
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-not-for-production"
    RATELIMIT_ENABLED = False
    LOG_LEVEL = "WARNING"
    TEST_MODE = True


class ProductionConfig(Config):
    """Production overrides."""

    ENV = "production"
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()


# Config selector
_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestConfig,
    "production": ProductionConfig,
}


def get_config(env: str | None = None) -> type:
    """Return the config class for the given environment name."""
    env = env or os.getenv("ZKR_ANALIZ_ENV", "development")
    return _CONFIG_MAP.get(env, Config)


def setup_logging(app=None) -> None:
    """Configure Python logging for the application.

    Called once at startup. Sets up:
      - Root logger with standard format
      - Console handler with appropriate level
      - Suppresses noisy third-party loggers
    """
    cfg = app.config if app else Config

    level_name = cfg.get("LOG_LEVEL", "INFO") if hasattr(cfg, "get") else getattr(cfg, "LOG_LEVEL", "INFO")
    log_format = cfg.get("LOG_FORMAT", Config.LOG_FORMAT) if hasattr(cfg, "get") else getattr(cfg, "LOG_FORMAT", Config.LOG_FORMAT)
    date_format = cfg.get("LOG_DATE_FORMAT", Config.LOG_DATE_FORMAT) if hasattr(cfg, "get") else getattr(cfg, "LOG_DATE_FORMAT", Config.LOG_DATE_FORMAT)

    level = getattr(logging, level_name, logging.INFO)

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for h in root.handlers[:]:
        root.removeHandler(h)

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    formatter = logging.Formatter(log_format, datefmt=date_format)
    console.setFormatter(formatter)
    root.addHandler(console)

    # App logger
    app_logger = logging.getLogger("zkr_analiz")
    app_logger.setLevel(level)

    # Suppress noisy loggers
    for noisy in ("urllib3", "websocket", "werkzeug"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    app_logger.info("Logging initialized — level=%s", level_name)
