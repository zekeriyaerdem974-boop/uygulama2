# -*- coding: utf-8 -*-
"""FAZ 61 — Localization System Fix / Language Switching Tests.

70 tests covering:
- Backend localization engine
- Frontend i18n.js
- Translation file completeness
- data-i18n attribute coverage
- Settings page language switch
- RTL support
- API endpoints
- Template rendering
"""
import json
import os
import re
import sys
import unittest

# ── Path setup ──
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

TEMPLATES = os.path.join(BASE, "templates")
STATIC = os.path.join(BASE, "static")
LOCALES = os.path.join(BASE, "app", "locales")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════
# 1. LOCALE FILE EXISTENCE (9 tests)
# ══════════════════════════════════════════════════════════════
class TestLocaleFileExistence(unittest.TestCase):
    LANGS = ["en", "tr", "es", "de", "fr", "pt", "ru", "ar", "zh"]

    def test_01_all_locale_files_exist(self):
        for lang in self.LANGS:
            fp = os.path.join(LOCALES, f"{lang}.json")
            self.assertTrue(os.path.isfile(fp), f"Missing {lang}.json")

    def test_02_all_locale_files_valid_json(self):
        for lang in self.LANGS:
            fp = os.path.join(LOCALES, f"{lang}.json")
            data = _json(fp)
            self.assertIsInstance(data, dict)
            self.assertGreater(len(data), 100, f"{lang}.json has too few keys")

    def test_03_en_json_has_required_keys(self):
        data = _json(os.path.join(LOCALES, "en.json"))
        required = ["sidebar.discover", "settings.title", "common.save",
                     "bottombar.discover", "menu.title", "notif.title",
                     "nav.markets", "search.placeholder", "market.status_open"]
        for key in required:
            self.assertIn(key, data, f"en.json missing key: {key}")

    def test_04_tr_json_has_required_keys(self):
        data = _json(os.path.join(LOCALES, "tr.json"))
        required = ["sidebar.discover", "settings.title", "common.save",
                     "bottombar.discover", "menu.title", "notif.title",
                     "nav.markets", "search.placeholder", "market.status_open"]
        for key in required:
            self.assertIn(key, data, f"tr.json missing key: {key}")


# ══════════════════════════════════════════════════════════════
# 2. TRANSLATION KEY PARITY (5 tests)
# ══════════════════════════════════════════════════════════════
class TestTranslationKeyParity(unittest.TestCase):
    def setUp(self):
        self.en = _json(os.path.join(LOCALES, "en.json"))
        self.tr = _json(os.path.join(LOCALES, "tr.json"))

    def test_05_en_tr_same_key_count(self):
        self.assertEqual(len(self.en), len(self.tr))

    def test_06_en_keys_in_tr(self):
        missing = set(self.en.keys()) - set(self.tr.keys())
        self.assertEqual(missing, set(), f"Keys in en.json missing from tr.json: {missing}")

    def test_07_tr_keys_in_en(self):
        missing = set(self.tr.keys()) - set(self.en.keys())
        self.assertEqual(missing, set(), f"Keys in tr.json missing from en.json: {missing}")

    def test_08_all_langs_have_minimum_keys(self):
        """Each language must have the same keys as en.json"""
        en_keys = set(self.en.keys())
        for lang in ["es", "de", "fr", "pt", "ru", "ar", "zh"]:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            lang_keys = set(data.keys())
            missing = en_keys - lang_keys
            self.assertEqual(missing, set(), f"{lang}.json missing keys: {missing}")

    def test_09_no_empty_values(self):
        """No translation value should be empty string"""
        for lang in ["en", "tr", "es", "de", "fr", "pt", "ru", "ar", "zh"]:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for k, v in data.items():
                self.assertTrue(len(v.strip()) > 0, f"{lang}.json key '{k}' has empty value")


# ══════════════════════════════════════════════════════════════
# 3. TRANSLATION CONTENT QUALITY (6 tests)
# ══════════════════════════════════════════════════════════════
class TestTranslationContent(unittest.TestCase):
    def test_10_tr_translations_different_from_en(self):
        en = _json(os.path.join(LOCALES, "en.json"))
        tr = _json(os.path.join(LOCALES, "tr.json"))
        different = sum(1 for k in en if k in tr and en[k] != tr[k])
        self.assertGreater(different, 80, "Too many tr keys identical to en")

    def test_11_es_translations_different_from_en(self):
        en = _json(os.path.join(LOCALES, "en.json"))
        es = _json(os.path.join(LOCALES, "es.json"))
        different = sum(1 for k in en if k in es and en[k] != es[k])
        self.assertGreater(different, 80)

    def test_12_tr_sidebar_discover_is_turkish(self):
        tr = _json(os.path.join(LOCALES, "tr.json"))
        self.assertEqual(tr["sidebar.discover"], "Keşfet")

    def test_13_en_sidebar_discover_is_english(self):
        en = _json(os.path.join(LOCALES, "en.json"))
        self.assertEqual(en["sidebar.discover"], "Discover")

    def test_14_tr_menu_keys_valid(self):
        tr = _json(os.path.join(LOCALES, "tr.json"))
        self.assertEqual(tr["menu.section_market"], "Piyasa & Analiz")
        self.assertEqual(tr["menu.market_summary"], "Piyasa Özeti")
        self.assertEqual(tr["menu.settings"], "Ayarlar")

    def test_15_en_menu_keys_valid(self):
        en = _json(os.path.join(LOCALES, "en.json"))
        self.assertEqual(en["menu.section_market"], "Market & Analysis")
        self.assertEqual(en["menu.market_summary"], "Market Summary")
        self.assertEqual(en["menu.settings"], "Settings")


# ══════════════════════════════════════════════════════════════
# 4. NEW KEY CATEGORIES (6 tests)
# ══════════════════════════════════════════════════════════════
class TestNewKeyCategories(unittest.TestCase):
    def setUp(self):
        self.en = _json(os.path.join(LOCALES, "en.json"))

    def test_16_bottombar_keys_exist(self):
        for key in ["bottombar.discover", "bottombar.chart", "bottombar.activity",
                     "bottombar.community", "bottombar.menu"]:
            self.assertIn(key, self.en)

    def test_17_nav_keys_exist(self):
        for key in ["nav.markets", "nav.trading", "nav.ai_tools", "nav.tools",
                     "nav.social", "nav.learn", "nav.account"]:
            self.assertIn(key, self.en)

    def test_18_menu_section_keys_exist(self):
        for key in ["menu.section_market", "menu.section_trading", "menu.section_ai",
                     "menu.section_community", "menu.section_learn", "menu.section_account"]:
            self.assertIn(key, self.en)

    def test_19_menu_item_keys_exist(self):
        for key in ["menu.market_summary", "menu.activity", "menu.screener",
                     "menu.opportunities", "menu.alerts", "menu.trade",
                     "menu.portfolio", "menu.simulator"]:
            self.assertIn(key, self.en)

    def test_20_notif_keys_exist(self):
        for key in ["notif.title", "notif.all", "notif.alerts",
                     "notif.opportunities", "notif.signals", "notif.empty"]:
            self.assertIn(key, self.en)

    def test_21_market_and_search_keys_exist(self):
        self.assertIn("market.status_open", self.en)
        self.assertIn("market.status_closed", self.en)
        self.assertIn("search.placeholder", self.en)
        self.assertIn("common.user", self.en)


# ══════════════════════════════════════════════════════════════
# 5. BACKEND LOCALIZATION ENGINE (8 tests)
# ══════════════════════════════════════════════════════════════
class TestLocalizationEngine(unittest.TestCase):
    def setUp(self):
        from app.core.localization_engine import clear_locale_cache
        clear_locale_cache()

    def test_22_get_supported_languages(self):
        from app.core.localization_engine import get_supported_languages
        langs = get_supported_languages()
        self.assertEqual(len(langs), 9)
        codes = [l["code"] for l in langs]
        self.assertIn("en", codes)
        self.assertIn("tr", codes)
        self.assertIn("ar", codes)

    def test_23_get_locale_returns_dict(self):
        from app.core.localization_engine import get_locale
        locale = get_locale("en")
        self.assertIsInstance(locale, dict)
        self.assertIn("sidebar.discover", locale)

    def test_24_translate_returns_correct(self):
        from app.core.localization_engine import translate
        result = translate("sidebar.discover", "en")
        self.assertEqual(result, "Discover")

    def test_25_translate_turkish(self):
        from app.core.localization_engine import translate
        result = translate("sidebar.discover", "tr")
        self.assertEqual(result, "Keşfet")

    def test_26_translate_fallback_to_key(self):
        from app.core.localization_engine import translate
        result = translate("nonexistent.key", "en")
        self.assertEqual(result, "nonexistent.key")

    def test_27_translate_fallback_to_default(self):
        from app.core.localization_engine import translate
        # If language doesn't exist, should fall back to default (tr)
        result = translate("sidebar.discover", "xx")
        self.assertEqual(result, "Keşfet")

    def test_28_is_rtl_arabic(self):
        from app.core.localization_engine import is_rtl
        self.assertTrue(is_rtl("ar"))

    def test_29_is_rtl_english(self):
        from app.core.localization_engine import is_rtl
        self.assertFalse(is_rtl("en"))

    def test_30_default_language_is_tr(self):
        from app.core.localization_engine import DEFAULT_LANGUAGE
        self.assertEqual(DEFAULT_LANGUAGE, "tr")

    def test_31_get_supported_codes(self):
        from app.core.localization_engine import get_supported_codes
        codes = get_supported_codes()
        self.assertEqual(len(codes), 9)
        self.assertIn("zh", codes)


# ══════════════════════════════════════════════════════════════
# 6. I18N.JS FILE (8 tests)
# ══════════════════════════════════════════════════════════════
class TestI18nJS(unittest.TestCase):
    def setUp(self):
        self.js = _read(os.path.join(STATIC, "js", "i18n.js"))

    def test_32_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(STATIC, "js", "i18n.js")))

    def test_33_has_bw_i18n_namespace(self):
        self.assertIn("BW.i18n", self.js)

    def test_34_has_load_function(self):
        self.assertIn("async load(lang)", self.js)

    def test_35_has_t_function(self):
        self.assertIn("t:", self.js)
        self.assertIn("t(key", self.js)

    def test_36_has_setLanguage_function(self):
        self.assertIn("async setLanguage(lang)", self.js)

    def test_37_has_refresh_function(self):
        self.assertIn("refresh:", self.js)
        self.assertIn("data-i18n", self.js)

    def test_38_handles_data_i18n_placeholder(self):
        self.assertIn("data-i18n-placeholder", self.js)

    def test_39_handles_data_i18n_tooltip(self):
        self.assertIn("data-i18n-tooltip", self.js)

    def test_40_uses_localstorage(self):
        self.assertIn("localStorage", self.js)
        self.assertIn("bw_lang", self.js)

    def test_41_has_rtl_support(self):
        self.assertIn("rtl", self.js)
        self.assertIn("ar", self.js)

    def test_42_auto_init_on_domcontentloaded(self):
        self.assertIn("DOMContentLoaded", self.js)

    def test_43_calls_api_settings_locale(self):
        self.assertIn("/api/settings/locale/", self.js)

    def test_44_calls_api_settings_language(self):
        self.assertIn("/api/settings/language", self.js)


# ══════════════════════════════════════════════════════════════
# 7. LAYOUT TEMPLATE data-i18n (8 tests)
# ══════════════════════════════════════════════════════════════
class TestLayoutDataI18n(unittest.TestCase):
    def setUp(self):
        self.html = _read(os.path.join(TEMPLATES, "layout_terminal.html"))

    def test_45_bottombar_has_data_i18n(self):
        self.assertIn('data-i18n="bottombar.discover"', self.html)
        self.assertIn('data-i18n="bottombar.chart"', self.html)
        self.assertIn('data-i18n="bottombar.activity"', self.html)
        self.assertIn('data-i18n="bottombar.community"', self.html)
        self.assertIn('data-i18n="bottombar.menu"', self.html)

    def test_46_sidebar_sections_have_data_i18n(self):
        self.assertIn('data-i18n="nav.markets"', self.html)
        self.assertIn('data-i18n="nav.trading"', self.html)
        self.assertIn('data-i18n="nav.ai_tools"', self.html)
        self.assertIn('data-i18n="nav.tools"', self.html)
        self.assertIn('data-i18n="nav.social"', self.html)

    def test_47_sidebar_tooltips_have_data_i18n_tooltip(self):
        self.assertIn('data-i18n-tooltip="sidebar.discover"', self.html)
        self.assertIn('data-i18n-tooltip="sidebar.portfolio"', self.html)
        self.assertIn('data-i18n-tooltip="sidebar.settings"', self.html)

    def test_48_notif_panel_has_data_i18n(self):
        self.assertIn('data-i18n="notif.title"', self.html)
        self.assertIn('data-i18n="notif.all"', self.html)
        self.assertIn('data-i18n="notif.empty"', self.html)

    def test_49_market_status_has_data_i18n(self):
        self.assertIn('data-i18n="market.status_open"', self.html)

    def test_50_search_placeholder_has_data_i18n(self):
        self.assertIn('data-i18n-placeholder="search.placeholder"', self.html)

    def test_51_html_lang_uses_g_lang(self):
        self.assertIn("g.lang", self.html)

    def test_52_html_dir_rtl_support(self):
        self.assertIn("rtl", self.html)
        self.assertIn("ltr", self.html)


# ══════════════════════════════════════════════════════════════
# 8. MENU TEMPLATE data-i18n (6 tests)
# ══════════════════════════════════════════════════════════════
class TestMenuDataI18n(unittest.TestCase):
    def setUp(self):
        self.html = _read(os.path.join(TEMPLATES, "menu.html"))

    def test_53_menu_section_titles_i18n(self):
        self.assertIn('data-i18n="menu.section_market"', self.html)
        self.assertIn('data-i18n="menu.section_trading"', self.html)
        self.assertIn('data-i18n="menu.section_ai"', self.html)
        self.assertIn('data-i18n="menu.section_community"', self.html)

    def test_54_menu_item_labels_i18n(self):
        self.assertIn('data-i18n="menu.market_summary"', self.html)
        self.assertIn('data-i18n="menu.activity"', self.html)
        self.assertIn('data-i18n="menu.screener"', self.html)
        self.assertIn('data-i18n="menu.trade"', self.html)

    def test_55_menu_item_descs_i18n(self):
        self.assertIn('data-i18n="menu.market_summary_desc"', self.html)
        self.assertIn('data-i18n="menu.activity_desc"', self.html)
        self.assertIn('data-i18n="menu.trade_desc"', self.html)

    def test_56_menu_view_account_i18n(self):
        self.assertIn('data-i18n="menu.view_account"', self.html)

    def test_57_menu_settings_i18n(self):
        self.assertIn('data-i18n="menu.settings"', self.html)
        self.assertIn('data-i18n="menu.settings_desc"', self.html)

    def test_58_menu_invite_i18n(self):
        self.assertIn('data-i18n="menu.invite"', self.html)
        self.assertIn('data-i18n="menu.invite_desc"', self.html)


# ══════════════════════════════════════════════════════════════
# 9. SETTINGS PAGE (5 tests)
# ══════════════════════════════════════════════════════════════
class TestSettingsPage(unittest.TestCase):
    def setUp(self):
        self.html = _read(os.path.join(TEMPLATES, "settings.html"))

    def test_59_settings_has_language_selector(self):
        self.assertIn("lang-option", self.html)
        self.assertIn("data-lang", self.html)

    def test_60_settings_calls_setLanguage(self):
        self.assertIn("BW.i18n.setLanguage", self.html)

    def test_61_settings_no_full_reload(self):
        """Settings should not force a full page reload after language change"""
        # After FAZ 61 fix, we removed setTimeout + location.reload
        self.assertNotIn("location.reload", self.html)

    def test_62_settings_uses_user_lang(self):
        self.assertIn("user_lang", self.html)

    def test_63_settings_renders_all_languages(self):
        self.assertIn("{% for lang in languages %}", self.html)


# ══════════════════════════════════════════════════════════════
# 10. RTL SUPPORT (5 tests)
# ══════════════════════════════════════════════════════════════
class TestRTLSupport(unittest.TestCase):
    def test_64_rtl_css_exists(self):
        css = _read(os.path.join(STATIC, "design", "design_layout.css"))
        self.assertIn('[dir="rtl"]', css)

    def test_65_rtl_sidebar(self):
        css = _read(os.path.join(STATIC, "design", "design_layout.css"))
        self.assertIn('[dir="rtl"] .tl-sidebar', css)

    def test_66_rtl_menu_item(self):
        css = _read(os.path.join(STATIC, "design", "design_layout.css"))
        self.assertIn('[dir="rtl"] .menu-item', css)

    def test_67_i18n_js_sets_dir_rtl(self):
        js = _read(os.path.join(STATIC, "js", "i18n.js"))
        self.assertIn("dir", js)
        self.assertIn("rtl", js)

    def test_68_layout_html_dir_attribute(self):
        html = _read(os.path.join(TEMPLATES, "layout_terminal.html"))
        self.assertIn('dir=', html)


# ══════════════════════════════════════════════════════════════
# 11. BACKEND INTEGRATION (5 tests)
# ══════════════════════════════════════════════════════════════
class TestBackendIntegration(unittest.TestCase):
    def test_69_before_request_sets_g_lang(self):
        monolith = _read(os.path.join(BASE, "legacy_monolith.py"))
        self.assertIn("g.lang", monolith)
        self.assertIn("resolve_language", monolith)

    def test_70_context_processor_inject_t(self):
        monolith = _read(os.path.join(BASE, "legacy_monolith.py"))
        self.assertIn("inject_i18n", monolith)
        self.assertIn("'t':", monolith)
        self.assertIn("'user_lang':", monolith)

    def test_71_settings_routes_exist(self):
        routes = _read(os.path.join(BASE, "app", "blueprints", "settings", "routes.py"))
        self.assertIn("/api/settings/language", routes)
        self.assertIn("/api/settings/locale/", routes)
        self.assertIn("/api/settings/languages", routes)

    def test_72_settings_language_updates_session(self):
        routes = _read(os.path.join(BASE, "app", "blueprints", "settings", "routes.py"))
        self.assertIn('session["language"]', routes)

    def test_73_localization_engine_caching(self):
        from app.core.localization_engine import clear_locale_cache, get_locale, _locale_cache
        clear_locale_cache()
        self.assertEqual(len(_locale_cache), 0)
        get_locale("en")
        self.assertIn("en", _locale_cache)


# ══════════════════════════════════════════════════════════════
# 12. I18N.JS LOAD & PERSIST (4 tests)
# ══════════════════════════════════════════════════════════════
class TestI18nPersistence(unittest.TestCase):
    def setUp(self):
        self.js = _read(os.path.join(STATIC, "js", "i18n.js"))

    def test_74_localstorage_set_on_load(self):
        self.assertIn("localStorage.setItem", self.js)

    def test_75_localstorage_get_on_init(self):
        self.assertIn("localStorage.getItem", self.js)

    def test_76_sets_document_lang(self):
        self.assertIn("document.documentElement.lang", self.js)

    def test_77_calls_refresh_after_load(self):
        self.assertIn("this.refresh()", self.js)


# ══════════════════════════════════════════════════════════════
# 13. ARABIC SPECIFIC (3 tests)
# ══════════════════════════════════════════════════════════════
class TestArabicLocale(unittest.TestCase):
    def test_78_arabic_json_has_all_keys(self):
        en = _json(os.path.join(LOCALES, "en.json"))
        ar = _json(os.path.join(LOCALES, "ar.json"))
        missing = set(en.keys()) - set(ar.keys())
        self.assertEqual(missing, set(), f"ar.json missing: {missing}")

    def test_79_arabic_values_are_arabic_script(self):
        ar = _json(os.path.join(LOCALES, "ar.json"))
        arabic_pattern = re.compile(r'[\u0600-\u06FF]')
        arabic_count = sum(1 for v in ar.values() if arabic_pattern.search(v))
        self.assertGreater(arabic_count, 80, "Too few Arabic translations")

    def test_80_engine_knows_arabic_rtl(self):
        from app.core.localization_engine import get_rtl_languages
        self.assertIn("ar", get_rtl_languages())


# ══════════════════════════════════════════════════════════════
# 14. FULL APP COVERAGE (5 tests)
# ══════════════════════════════════════════════════════════════
class TestFullAppCoverage(unittest.TestCase):
    def test_81_layout_loads_i18n_js(self):
        html = _read(os.path.join(TEMPLATES, "layout_terminal.html"))
        self.assertIn("i18n.js", html)

    def test_82_data_i18n_count_in_layout(self):
        html = _read(os.path.join(TEMPLATES, "layout_terminal.html"))
        count = html.count("data-i18n")
        self.assertGreaterEqual(count, 20, f"Only {count} data-i18n attrs in layout")

    def test_83_data_i18n_count_in_menu(self):
        html = _read(os.path.join(TEMPLATES, "menu.html"))
        count = html.count("data-i18n")
        self.assertGreaterEqual(count, 25, f"Only {count} data-i18n attrs in menu")

    def test_84_no_location_reload_in_settings(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertNotIn("location.reload", html)

    def test_85_i18n_js_default_lang_tr(self):
        js = _read(os.path.join(STATIC, "js", "i18n.js"))
        self.assertIn("'tr'", js)


if __name__ == "__main__":
    unittest.main()
