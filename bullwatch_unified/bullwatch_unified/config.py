import os


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = _env_bool("FLASK_DEBUG", default=(ENV == "development"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    TEMPLATES_AUTO_RELOAD = True
    JSON_SORT_KEYS = False
