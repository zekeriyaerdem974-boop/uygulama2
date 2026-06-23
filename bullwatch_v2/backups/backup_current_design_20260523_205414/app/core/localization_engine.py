# -*- coding: utf-8 -*-
"""Localization Engine — FAZ 52.

Manages supported languages, loads locale files, resolves current
language from user preferences / browser / fallback.

Public API:
  get_supported_languages()            → list[dict]
  get_locale(lang_code)                → dict
  translate(key, lang_code)            → str
  resolve_language(user_id=None)       → str
  get_rtl_languages()                  → set[str]
  is_rtl(lang_code)                    → bool
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional, Set

from flask import request, session

_logger = logging.getLogger("zkr_analiz.localization")

# ── Configuration ─────────────────────────────────────────────────
_LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "locales",
)

DEFAULT_LANGUAGE = "tr"

SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "flag": "🇬🇧"},
    {"code": "tr", "name": "Turkish", "native": "Türkçe", "flag": "🇹🇷"},
    {"code": "es", "name": "Spanish", "native": "Español", "flag": "🇪🇸"},
    {"code": "de", "name": "German", "native": "Deutsch", "flag": "🇩🇪"},
    {"code": "fr", "name": "French", "native": "Français", "flag": "🇫🇷"},
    {"code": "pt", "name": "Portuguese", "native": "Português", "flag": "🇵🇹"},
    {"code": "ru", "name": "Russian", "native": "Русский", "flag": "🇷🇺"},
    {"code": "ar", "name": "Arabic", "native": "العربية", "flag": "🇸🇦"},
    {"code": "zh", "name": "Chinese", "native": "中文", "flag": "🇨🇳"},
]

_SUPPORTED_CODES: Set[str] = {lang["code"] for lang in SUPPORTED_LANGUAGES}
_RTL_LANGUAGES: Set[str] = {"ar"}

# ── In-memory locale cache ────────────────────────────────────────
_locale_cache: Dict[str, Dict[str, str]] = {}


def _load_locale_file(lang_code: str) -> Dict[str, str]:
    """Load a locale JSON file from disk. Returns empty dict on failure."""
    if lang_code in _locale_cache:
        return _locale_cache[lang_code]

    filepath = os.path.join(_LOCALES_DIR, f"{lang_code}.json")
    if not os.path.isfile(filepath):
        _logger.debug("Locale file not found: %s", filepath)
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        _locale_cache[lang_code] = data
        return data
    except Exception as e:
        _logger.warning("Failed to load locale %s: %s", lang_code, e)
        return {}


def clear_locale_cache() -> None:
    """Clear the in-memory locale cache (useful for testing)."""
    _locale_cache.clear()


# ══════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════

def get_supported_languages() -> List[Dict]:
    """Return list of supported languages."""
    return list(SUPPORTED_LANGUAGES)


def get_supported_codes() -> Set[str]:
    """Return set of valid language codes."""
    return set(_SUPPORTED_CODES)


def get_locale(lang_code: str) -> Dict[str, str]:
    """Get all translations for a language code.

    Falls back to English for unknown codes.
    """
    if lang_code not in _SUPPORTED_CODES:
        lang_code = DEFAULT_LANGUAGE
    return _load_locale_file(lang_code)


def translate(key: str, lang_code: str = None) -> str:
    """Translate a key to the given language.

    Falls back to English translation, then to the key itself.
    """
    if lang_code is None:
        lang_code = resolve_language()

    locale = get_locale(lang_code)
    if key in locale:
        return locale[key]

    # Fallback to English
    if lang_code != DEFAULT_LANGUAGE:
        en_locale = get_locale(DEFAULT_LANGUAGE)
        if key in en_locale:
            return en_locale[key]

    return key


def resolve_language(user_id: str = None) -> str:
    """Determine the active language in priority order:

    1. User preference (from settings)
    2. Session override
    3. Browser Accept-Language header
    4. Fallback to English
    """
    # 1. User preference from DB
    if user_id:
        try:
            from app.core.settings_engine import get_user_settings
            settings = get_user_settings(user_id)
            if settings and settings.get("language_code") in _SUPPORTED_CODES:
                return settings["language_code"]
        except Exception:
            pass

    # 2. Session override
    try:
        lang = session.get("language")
        if lang in _SUPPORTED_CODES:
            return lang
    except RuntimeError:
        pass  # Outside request context

    # 3. Browser Accept-Language
    try:
        accept = request.accept_languages
        for lang, _ in accept:
            code = lang[:2].lower()
            if code in _SUPPORTED_CODES:
                return code
    except RuntimeError:
        pass  # Outside request context

    # 4. Default
    return DEFAULT_LANGUAGE


def get_rtl_languages() -> Set[str]:
    """Return set of RTL language codes."""
    return set(_RTL_LANGUAGES)


def is_rtl(lang_code: str) -> bool:
    """Check if a language requires RTL layout."""
    return lang_code in _RTL_LANGUAGES


def get_language_info(lang_code: str) -> Optional[Dict]:
    """Get info dict for a specific language code."""
    for lang in SUPPORTED_LANGUAGES:
        if lang["code"] == lang_code:
            return dict(lang)
    return None
