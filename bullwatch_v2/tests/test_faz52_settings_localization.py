# -*- coding: utf-8 -*-
"""FAZ 52 — Settings / Preferences / Global Localization Tests.

Covers:
  1. File existence & structure
  2. Localization engine API
  3. Locale files (all 9 languages)
  4. Settings engine — DB CRUD
  5. Settings API routes — auth, responses, edge cases
  6. Language API routes
  7. Theme API
  8. Notification preferences API
  9. Data management (export / delete)
  10. i18n.js client structure
  11. RTL support
  12. Template structure
  13. Blueprint registration & context processor

80+ tests organized into 13 test classes.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest

# ── Paths ─────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# ── Helpers ───────────────────────────────────────────────────────
def _read(rel_path: str) -> str:
    with open(os.path.join(BASE, rel_path), encoding="utf-8") as f:
        return f.read()


def _get_app():
    from legacy_monolith import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-faz52"
    return app


def _client():
    return _get_app().test_client()


def _auth_client():
    app = _get_app()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "test_user_faz52"
        sess["username"] = "testuser52"
    return client


_FAKE_USER = {"id": "test_user_faz52", "username": "testuser52", "email": "t52@t.com"}


def _patch_auth():
    return patch("app.blueprints.auth.routes.get_current_user",
                 return_value=_FAKE_USER)


LOCALE_CODES = ["en", "tr", "es", "de", "fr", "pt", "ru", "ar", "zh"]


# ══════════════════════════════════════════════════════════════════
# CLASS 1: File Existence & Structure
# ══════════════════════════════════════════════════════════════════

class TestFaz52FileStructure(unittest.TestCase):
    """Verify all FAZ 52 files exist and are well-formed."""

    def test_localization_engine_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/core/localization_engine.py")))

    def test_settings_engine_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/core/settings_engine.py")))

    def test_settings_blueprint_init_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/blueprints/settings/__init__.py")))

    def test_settings_blueprint_routes_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/blueprints/settings/routes.py")))

    def test_settings_template_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "templates/settings.html")))

    def test_i18n_js_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/js/i18n.js")))

    def test_locale_files_exist(self):
        for code in LOCALE_CODES:
            path = os.path.join(BASE, f"app/locales/{code}.json")
            self.assertTrue(os.path.isfile(path), f"Missing: {code}.json")

    def test_localization_engine_has_public_api(self):
        src = _read("app/core/localization_engine.py")
        for fn in ["get_supported_languages", "get_locale", "translate",
                    "resolve_language", "is_rtl", "get_rtl_languages",
                    "get_language_info", "clear_locale_cache"]:
            self.assertIn(f"def {fn}(", src, f"Missing function: {fn}")

    def test_settings_engine_has_public_api(self):
        src = _read("app/core/settings_engine.py")
        for fn in ["get_user_settings", "update_user_settings",
                    "get_default_settings", "delete_user_settings"]:
            self.assertIn(f"def {fn}(", src, f"Missing function: {fn}")

    def test_blueprint_registered_in_monolith(self):
        src = _read("legacy_monolith.py")
        self.assertIn("from app.blueprints.settings import settings_bp", src)
        self.assertIn("app.register_blueprint(settings_bp)", src)


# ══════════════════════════════════════════════════════════════════
# CLASS 2: Localization Engine — Core API
# ══════════════════════════════════════════════════════════════════

class TestLocalizationEngine(unittest.TestCase):
    """Test localization engine functions."""

    def setUp(self):
        from app.core.localization_engine import clear_locale_cache
        clear_locale_cache()

    def test_supported_languages_count(self):
        from app.core.localization_engine import get_supported_languages
        langs = get_supported_languages()
        self.assertEqual(len(langs), 9)

    def test_supported_languages_have_required_keys(self):
        from app.core.localization_engine import get_supported_languages
        for lang in get_supported_languages():
            for key in ("code", "name", "native", "flag"):
                self.assertIn(key, lang)

    def test_supported_codes_set(self):
        from app.core.localization_engine import get_supported_codes
        codes = get_supported_codes()
        self.assertEqual(codes, set(LOCALE_CODES))

    def test_default_language_is_english(self):
        from app.core.localization_engine import DEFAULT_LANGUAGE
        self.assertEqual(DEFAULT_LANGUAGE, "en")

    def test_get_locale_returns_dict(self):
        from app.core.localization_engine import get_locale
        locale = get_locale("en")
        self.assertIsInstance(locale, dict)
        self.assertGreater(len(locale), 0)

    def test_get_locale_unknown_falls_back_to_english(self):
        from app.core.localization_engine import get_locale
        locale = get_locale("xx")
        self.assertIsInstance(locale, dict)
        # Should contain English keys
        self.assertIn("sidebar.discover", locale)

    def test_translate_existing_key(self):
        from app.core.localization_engine import translate
        app = _get_app()
        with app.test_request_context():
            result = translate("sidebar.discover", "en")
            self.assertEqual(result, "Discover")

    def test_translate_turkish_key(self):
        from app.core.localization_engine import translate
        app = _get_app()
        with app.test_request_context():
            result = translate("sidebar.discover", "tr")
            self.assertEqual(result, "Keşfet")

    def test_translate_missing_key_returns_key(self):
        from app.core.localization_engine import translate
        app = _get_app()
        with app.test_request_context():
            result = translate("nonexistent.key.xyz", "en")
            self.assertEqual(result, "nonexistent.key.xyz")

    def test_translate_missing_key_fallback_to_english(self):
        from app.core.localization_engine import translate
        app = _get_app()
        with app.test_request_context():
            result = translate("sidebar.discover", "ar")
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_is_rtl_arabic(self):
        from app.core.localization_engine import is_rtl
        self.assertTrue(is_rtl("ar"))

    def test_is_rtl_english_false(self):
        from app.core.localization_engine import is_rtl
        self.assertFalse(is_rtl("en"))

    def test_is_rtl_all_non_arabic_false(self):
        from app.core.localization_engine import is_rtl
        for code in ["en", "tr", "es", "de", "fr", "pt", "ru", "zh"]:
            self.assertFalse(is_rtl(code), f"{code} should not be RTL")

    def test_get_rtl_languages(self):
        from app.core.localization_engine import get_rtl_languages
        rtl = get_rtl_languages()
        self.assertIn("ar", rtl)
        self.assertNotIn("en", rtl)

    def test_get_language_info_valid(self):
        from app.core.localization_engine import get_language_info
        info = get_language_info("tr")
        self.assertIsNotNone(info)
        self.assertEqual(info["code"], "tr")
        self.assertEqual(info["native"], "Türkçe")

    def test_get_language_info_invalid(self):
        from app.core.localization_engine import get_language_info
        self.assertIsNone(get_language_info("xx"))

    def test_resolve_language_default_is_english(self):
        from app.core.localization_engine import resolve_language
        # Outside request context → should return DEFAULT
        result = resolve_language()
        self.assertEqual(result, "en")

    def test_resolve_language_session_override(self):
        from app.core.localization_engine import resolve_language
        app = _get_app()
        with app.test_request_context():
            from flask import session
            session["language"] = "fr"
            result = resolve_language()
            self.assertEqual(result, "fr")

    def test_resolve_language_invalid_session_ignored(self):
        from app.core.localization_engine import resolve_language
        app = _get_app()
        with app.test_request_context():
            from flask import session
            session["language"] = "xx"
            result = resolve_language()
            # Should not return invalid code
            self.assertIn(result, LOCALE_CODES)

    def test_clear_locale_cache(self):
        from app.core.localization_engine import get_locale, clear_locale_cache, _locale_cache
        get_locale("en")
        self.assertIn("en", _locale_cache)
        clear_locale_cache()
        self.assertEqual(len(_locale_cache), 0)


# ══════════════════════════════════════════════════════════════════
# CLASS 3: Locale Files — Content Validation
# ══════════════════════════════════════════════════════════════════

class TestLocaleFiles(unittest.TestCase):
    """Validate all 9 locale JSON files."""

    def _load_locale(self, code):
        path = os.path.join(BASE, f"app/locales/{code}.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_all_locales_valid_json(self):
        for code in LOCALE_CODES:
            data = self._load_locale(code)
            self.assertIsInstance(data, dict, f"{code}.json is not a dict")

    def test_english_has_required_keys(self):
        en = self._load_locale("en")
        required = ["sidebar.discover", "sidebar.portfolio", "sidebar.settings",
                     "settings.title", "settings.language", "settings.theme_label",
                     "common.save", "common.cancel"]
        for key in required:
            self.assertIn(key, en, f"Missing key in en.json: {key}")

    def test_all_locales_have_sidebar_keys(self):
        en = self._load_locale("en")
        sidebar_keys = [k for k in en if k.startswith("sidebar.")]
        for code in LOCALE_CODES:
            locale = self._load_locale(code)
            for key in sidebar_keys:
                self.assertIn(key, locale, f"Missing '{key}' in {code}.json")

    def test_all_locales_have_settings_keys(self):
        en = self._load_locale("en")
        settings_keys = [k for k in en if k.startswith("settings.")]
        for code in LOCALE_CODES:
            locale = self._load_locale(code)
            for key in settings_keys:
                self.assertIn(key, locale, f"Missing '{key}' in {code}.json")

    def test_locale_values_are_strings(self):
        for code in LOCALE_CODES:
            locale = self._load_locale(code)
            for key, val in locale.items():
                self.assertIsInstance(val, str, f"{code}.json[{key}] is not a string")

    def test_locale_keys_match_english(self):
        en = self._load_locale("en")
        en_keys = set(en.keys())
        for code in LOCALE_CODES:
            if code == "en":
                continue
            locale = self._load_locale(code)
            missing = en_keys - set(locale.keys())
            self.assertEqual(len(missing), 0,
                             f"{code}.json missing keys: {missing}")

    def test_arabic_locale_has_rtl_content(self):
        ar = self._load_locale("ar")
        # Arabic text should contain Arabic characters
        self.assertTrue(any("\u0600" <= c <= "\u06FF" for c in ar.get("settings.title", "")))

    def test_chinese_locale_has_cjk_content(self):
        zh = self._load_locale("zh")
        self.assertTrue(any("\u4E00" <= c <= "\u9FFF" for c in zh.get("settings.title", "")))


# ══════════════════════════════════════════════════════════════════
# CLASS 4: Settings Engine — Database CRUD
# ══════════════════════════════════════════════════════════════════

class TestSettingsEngine(unittest.TestCase):
    """Test settings engine with isolated DB."""

    def setUp(self):
        import app.core.settings_engine as se
        se._tables_ensured = False

    def test_get_default_settings_returns_dict(self):
        from app.core.settings_engine import get_default_settings
        defaults = get_default_settings()
        self.assertIsInstance(defaults, dict)
        self.assertEqual(defaults["language_code"], "en")
        self.assertEqual(defaults["theme"], "dark_pro")

    def test_default_settings_has_all_fields(self):
        from app.core.settings_engine import get_default_settings
        defaults = get_default_settings()
        expected = ["language_code", "theme", "timezone", "region",
                    "notifications_enabled", "market_preferences",
                    "profile_visibility", "two_factor_enabled"]
        for key in expected:
            self.assertIn(key, defaults)

    def test_default_notifications_enabled(self):
        from app.core.settings_engine import get_default_settings
        defaults = get_default_settings()
        self.assertTrue(defaults["notifications_enabled"])
        self.assertFalse(defaults["email_notifications"])

    def test_default_market_preferences_is_list(self):
        from app.core.settings_engine import get_default_settings
        defaults = get_default_settings()
        self.assertIsInstance(defaults["market_preferences"], list)
        self.assertIn("crypto", defaults["market_preferences"])

    @patch("app.core.settings_engine.get_connection")
    def test_get_user_settings_creates_defaults(self, mock_conn):
        """When no row exists, defaults should be inserted."""
        from app.core.settings_engine import get_user_settings, get_default_settings
        conn = MagicMock()
        mock_conn.return_value = conn
        conn.execute.return_value.fetchone.return_value = None
        result = get_user_settings("user123")
        self.assertEqual(result["language_code"], "en")
        self.assertEqual(result["user_id"], "user123")

    @patch("app.core.settings_engine.get_connection")
    def test_get_user_settings_existing_row(self, mock_conn):
        from app.core.settings_engine import get_user_settings
        mock_row = MagicMock()
        mock_row.__iter__ = MagicMock(return_value=iter([]))
        mock_row.keys = MagicMock(return_value=[
            "user_id", "language_code", "theme", "notifications_enabled",
            "market_preferences"
        ])
        mock_row.__getitem__ = lambda self, key: {
            "user_id": "u1", "language_code": "tr", "theme": "dark",
            "notifications_enabled": 1, "market_preferences": '["crypto"]'
        }[key]
        # Use a real dict-like row
        row_data = {
            "user_id": "u1", "language_code": "tr", "theme": "dark",
            "notifications_enabled": 1, "market_preferences": '["crypto"]'
        }

        class FakeRow:
            def __init__(self, d):
                self._d = d
            def keys(self):
                return self._d.keys()
            def __getitem__(self, k):
                return self._d[k]
            def __contains__(self, k):
                return k in self._d
            def __iter__(self):
                return iter(self._d)

        conn = MagicMock()
        mock_conn.return_value = conn
        conn.execute.return_value.fetchone.return_value = FakeRow(row_data)
        result = get_user_settings("u1")
        self.assertEqual(result["language_code"], "tr")

    def test_bool_fields_defined(self):
        from app.core.settings_engine import _BOOL_FIELDS
        self.assertIn("notifications_enabled", _BOOL_FIELDS)
        self.assertIn("two_factor_enabled", _BOOL_FIELDS)
        self.assertEqual(len(_BOOL_FIELDS), 12)

    def test_text_fields_defined(self):
        from app.core.settings_engine import _TEXT_FIELDS
        self.assertIn("language_code", _TEXT_FIELDS)
        self.assertIn("theme", _TEXT_FIELDS)
        self.assertEqual(len(_TEXT_FIELDS), 10)

    def test_json_fields_defined(self):
        from app.core.settings_engine import _JSON_FIELDS
        self.assertIn("market_preferences", _JSON_FIELDS)

    def test_all_fields_union(self):
        from app.core.settings_engine import _ALL_FIELDS, _BOOL_FIELDS, _TEXT_FIELDS, _JSON_FIELDS
        self.assertEqual(_ALL_FIELDS, _BOOL_FIELDS | _TEXT_FIELDS | _JSON_FIELDS)


# ══════════════════════════════════════════════════════════════════
# CLASS 5: Settings API Routes — CRUD
# ══════════════════════════════════════════════════════════════════

class TestSettingsAPI(unittest.TestCase):
    """Test settings API endpoints."""

    def test_settings_page_requires_auth(self):
        client = _client()
        resp = client.get("/settings")
        self.assertIn(resp.status_code, [302, 401, 403])

    def test_settings_page_with_auth(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.get("/settings")
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"settings", resp.data.lower())

    @patch("app.blueprints.settings.routes.get_user_settings")
    def test_api_get_settings_requires_auth(self, mock_gs):
        client = _client()
        resp = client.get("/api/settings/me")
        self.assertIn(resp.status_code, [302, 401, 403])

    @patch("app.blueprints.settings.routes.get_user_settings")
    def test_api_get_settings_with_auth(self, mock_gs):
        mock_gs.return_value = {"language_code": "en", "theme": "dark_pro"}
        with _patch_auth():
            client = _auth_client()
            resp = client.get("/api/settings/me")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertIn("settings", data)

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_api_update_settings(self, mock_update):
        mock_update.return_value = {"language_code": "tr", "theme": "dark"}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/update",
                              json={"theme": "dark"})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])

    def test_api_update_settings_empty_body(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/update",
                              data="",
                              content_type="application/json")
            self.assertEqual(resp.status_code, 400)

    def test_api_update_requires_auth(self):
        client = _client()
        resp = client.post("/api/settings/update", json={"theme": "dark"})
        self.assertIn(resp.status_code, [302, 401, 403])


# ══════════════════════════════════════════════════════════════════
# CLASS 6: Language API Routes
# ══════════════════════════════════════════════════════════════════

class TestLanguageAPI(unittest.TestCase):
    """Test language-specific API endpoints."""

    def test_get_languages_no_auth_required(self):
        client = _client()
        resp = client.get("/api/settings/languages")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["languages"]), 9)

    def test_get_languages_has_required_fields(self):
        client = _client()
        resp = client.get("/api/settings/languages")
        data = resp.get_json()
        for lang in data["languages"]:
            self.assertIn("code", lang)
            self.assertIn("name", lang)
            self.assertIn("native", lang)

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_language_valid(self, mock_update):
        mock_update.return_value = {"language_code": "tr"}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/language",
                              json={"language_code": "tr"})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["language_code"], "tr")

    def test_set_language_invalid_code(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/language",
                              json={"language_code": "xx"})
            self.assertEqual(resp.status_code, 400)

    def test_set_language_empty(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/language",
                              json={"language_code": ""})
            self.assertEqual(resp.status_code, 400)

    def test_set_language_requires_auth(self):
        client = _client()
        resp = client.post("/api/settings/language",
                          json={"language_code": "en"})
        self.assertIn(resp.status_code, [302, 401, 403])

    def test_get_locale_endpoint_english(self):
        client = _client()
        resp = client.get("/api/settings/locale/en")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertIn("translations", data)
        self.assertIn("sidebar.discover", data["translations"])

    def test_get_locale_endpoint_turkish(self):
        client = _client()
        resp = client.get("/api/settings/locale/tr")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["translations"]["sidebar.discover"], "Keşfet")

    def test_get_locale_endpoint_all_languages(self):
        client = _client()
        for code in LOCALE_CODES:
            resp = client.get(f"/api/settings/locale/{code}")
            self.assertEqual(resp.status_code, 200, f"Failed for {code}")
            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertGreater(len(data["translations"]), 0)

    def test_get_locale_unknown_code_fallback(self):
        client = _client()
        resp = client.get("/api/settings/locale/xx")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should fall back to English
        self.assertTrue(data["ok"])


# ══════════════════════════════════════════════════════════════════
# CLASS 7: Theme API
# ══════════════════════════════════════════════════════════════════

class TestThemeAPI(unittest.TestCase):
    """Test theme preference endpoints."""

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_theme_dark(self, mock_update):
        mock_update.return_value = {"theme": "dark"}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/theme", json={"theme": "dark"})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_theme_dark_pro(self, mock_update):
        mock_update.return_value = {"theme": "dark_pro"}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/theme", json={"theme": "dark_pro"})
            self.assertEqual(resp.status_code, 200)

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_theme_system(self, mock_update):
        mock_update.return_value = {"theme": "system"}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/theme", json={"theme": "system"})
            self.assertEqual(resp.status_code, 200)

    def test_set_theme_invalid(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/theme", json={"theme": "light"})
            self.assertEqual(resp.status_code, 400)

    def test_set_theme_empty(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/theme", json={"theme": ""})
            self.assertEqual(resp.status_code, 400)

    def test_set_theme_requires_auth(self):
        client = _client()
        resp = client.post("/api/settings/theme", json={"theme": "dark"})
        self.assertIn(resp.status_code, [302, 401, 403])


# ══════════════════════════════════════════════════════════════════
# CLASS 8: Notification Preferences API
# ══════════════════════════════════════════════════════════════════

class TestNotificationsAPI(unittest.TestCase):
    """Test notification preference endpoints."""

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_notifications(self, mock_update):
        mock_update.return_value = {"notifications_enabled": False}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/notifications",
                              json={"notifications_enabled": False})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_multiple_notifications(self, mock_update):
        mock_update.return_value = {}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/notifications",
                              json={
                                  "email_notifications": True,
                                  "push_notifications": True,
                                  "ai_brief_notifications": False,
                              })
            self.assertEqual(resp.status_code, 200)

    def test_set_notifications_empty_body(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/notifications", json={})
            self.assertEqual(resp.status_code, 400)

    def test_set_notifications_invalid_fields(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/notifications",
                              json={"invalid_field": True})
            self.assertEqual(resp.status_code, 400)

    def test_set_notifications_requires_auth(self):
        client = _client()
        resp = client.post("/api/settings/notifications",
                          json={"notifications_enabled": True})
        self.assertIn(resp.status_code, [302, 401, 403])


# ══════════════════════════════════════════════════════════════════
# CLASS 9: Data Management API
# ══════════════════════════════════════════════════════════════════

class TestDataManagementAPI(unittest.TestCase):
    """Test export and delete account endpoints."""

    @patch("app.blueprints.settings.routes.get_user_settings")
    def test_export_data(self, mock_gs):
        mock_gs.return_value = {"language_code": "en"}
        with _patch_auth():
            client = _auth_client()
            resp = client.get("/api/settings/export")
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])
            self.assertIn("export", data)
            self.assertIn("settings", data["export"])

    def test_export_requires_auth(self):
        client = _client()
        resp = client.get("/api/settings/export")
        self.assertIn(resp.status_code, [302, 401, 403])

    @patch("app.blueprints.settings.routes.delete_user_settings")
    def test_delete_account_with_confirm(self, mock_del):
        mock_del.return_value = True
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/delete-account",
                              json={"confirm": "DELETE"})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["ok"])

    def test_delete_account_without_confirm(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/delete-account",
                              json={"confirm": "wrong"})
            self.assertEqual(resp.status_code, 400)

    def test_delete_account_empty_body(self):
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/delete-account", json={})
            self.assertEqual(resp.status_code, 400)

    def test_delete_account_requires_auth(self):
        client = _client()
        resp = client.post("/api/settings/delete-account",
                          json={"confirm": "DELETE"})
        self.assertIn(resp.status_code, [302, 401, 403])


# ══════════════════════════════════════════════════════════════════
# CLASS 10: i18n.js Client Structure
# ══════════════════════════════════════════════════════════════════

class TestI18nJS(unittest.TestCase):
    """Test i18n.js file structure and content."""

    def test_i18n_defines_bw_namespace(self):
        src = _read("static/js/i18n.js")
        self.assertIn("BW.i18n", src)

    def test_i18n_has_load_function(self):
        src = _read("static/js/i18n.js")
        self.assertIn("load(lang)", src)

    def test_i18n_has_translate_function(self):
        src = _read("static/js/i18n.js")
        self.assertIn("t(key", src)

    def test_i18n_has_set_language_function(self):
        src = _read("static/js/i18n.js")
        self.assertIn("setLanguage(lang)", src)

    def test_i18n_handles_rtl(self):
        src = _read("static/js/i18n.js")
        self.assertIn("rtl", src)
        self.assertIn("dir", src)

    def test_i18n_fetches_locale_api(self):
        src = _read("static/js/i18n.js")
        self.assertIn("/api/settings/locale/", src)

    def test_i18n_posts_language_api(self):
        src = _read("static/js/i18n.js")
        self.assertIn("/api/settings/language", src)

    def test_i18n_has_lang_property(self):
        src = _read("static/js/i18n.js")
        self.assertIn("get lang()", src)

    def test_i18n_has_loaded_property(self):
        src = _read("static/js/i18n.js")
        self.assertIn("get loaded()", src)


# ══════════════════════════════════════════════════════════════════
# CLASS 11: RTL Support
# ══════════════════════════════════════════════════════════════════

class TestRTLSupport(unittest.TestCase):
    """Test RTL support across the system."""

    def test_arabic_is_only_rtl_language(self):
        from app.core.localization_engine import get_rtl_languages
        rtl = get_rtl_languages()
        self.assertEqual(rtl, {"ar"})

    @patch("app.blueprints.settings.routes.get_user_settings")
    def test_api_settings_returns_rtl_flag(self, mock_gs):
        mock_gs.return_value = {"language_code": "ar"}
        with _patch_auth():
            client = _auth_client()
            resp = client.get("/api/settings/me")
            data = resp.get_json()
            self.assertTrue(data["is_rtl"])

    @patch("app.blueprints.settings.routes.get_user_settings")
    def test_api_settings_returns_ltr_flag(self, mock_gs):
        mock_gs.return_value = {"language_code": "en"}
        with _patch_auth():
            client = _auth_client()
            resp = client.get("/api/settings/me")
            data = resp.get_json()
            self.assertFalse(data["is_rtl"])

    @patch("app.blueprints.settings.routes.update_user_settings")
    def test_set_arabic_returns_rtl(self, mock_update):
        mock_update.return_value = {"language_code": "ar"}
        with _patch_auth():
            client = _auth_client()
            resp = client.post("/api/settings/language",
                              json={"language_code": "ar"})
            data = resp.get_json()
            self.assertTrue(data["is_rtl"])

    def test_i18n_js_rtl_handling(self):
        src = _read("static/js/i18n.js")
        self.assertIn("ar", src)
        self.assertIn("rtl", src)

    def test_settings_template_rtl_css(self):
        src = _read("templates/settings.html")
        self.assertIn("rtl", src.lower())


# ══════════════════════════════════════════════════════════════════
# CLASS 12: Template Structure
# ══════════════════════════════════════════════════════════════════

class TestTemplateStructure(unittest.TestCase):
    """Test settings.html template structure."""

    def test_extends_layout(self):
        src = _read("templates/settings.html")
        self.assertIn("extends", src)
        self.assertIn("layout_terminal.html", src)

    def test_has_language_section(self):
        src = _read("templates/settings.html")
        self.assertIn("language", src.lower())

    def test_has_theme_section(self):
        src = _read("templates/settings.html")
        self.assertIn("theme", src.lower())

    def test_has_notification_section(self):
        src = _read("templates/settings.html")
        self.assertIn("notification", src.lower())

    def test_has_privacy_section(self):
        src = _read("templates/settings.html")
        self.assertIn("privacy", src.lower())

    def test_has_security_section(self):
        src = _read("templates/settings.html")
        self.assertIn("security", src.lower())

    def test_has_data_management_section(self):
        src = _read("templates/settings.html")
        self.assertIn("data", src.lower())
        self.assertIn("export", src.lower())

    def test_has_settings_navigation(self):
        src = _read("templates/settings.html")
        self.assertIn("settings-nav", src)

    def test_settings_has_js_functions(self):
        src = _read("templates/settings.html")
        for fn in ["loadSettings", "saveRegion", "saveNotifications"]:
            self.assertIn(fn, src)


# ══════════════════════════════════════════════════════════════════
# CLASS 13: Blueprint & Context Processor Integration
# ══════════════════════════════════════════════════════════════════

class TestIntegration(unittest.TestCase):
    """Test integration points."""

    def test_layout_has_i18n_script(self):
        src = _read("templates/layout_terminal.html")
        self.assertIn("i18n.js", src)

    def test_layout_has_language_selector(self):
        src = _read("templates/layout_terminal.html")
        self.assertIn("topbarLangBtn", src)
        self.assertIn("topbarLangDropdown", src)

    def test_layout_has_dynamic_lang_attribute(self):
        src = _read("templates/layout_terminal.html")
        self.assertIn("g.lang", src)

    def test_monolith_has_before_request_lang(self):
        src = _read("legacy_monolith.py")
        self.assertIn("set_language", src)
        self.assertIn("g.lang", src)

    def test_settings_blueprint_url_prefix(self):
        app = _get_app()
        rules = [r.rule for r in app.url_map.iter_rules()]
        self.assertIn("/settings", rules)
        self.assertIn("/api/settings/me", rules)
        self.assertIn("/api/settings/languages", rules)

    def test_all_settings_api_routes_registered(self):
        app = _get_app()
        rules = [r.rule for r in app.url_map.iter_rules()]
        expected = [
            "/settings", "/api/settings/me", "/api/settings/update",
            "/api/settings/languages", "/api/settings/language",
            "/api/settings/theme", "/api/settings/notifications",
            "/api/settings/export", "/api/settings/delete-account",
        ]
        for route in expected:
            self.assertIn(route, rules, f"Missing route: {route}")

    def test_locale_endpoint_route_registered(self):
        app = _get_app()
        rules = [r.rule for r in app.url_map.iter_rules()]
        self.assertTrue(any("/api/settings/locale/" in r for r in rules))


if __name__ == "__main__":
    unittest.main()
