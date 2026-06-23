# -*- coding: utf-8 -*-
"""FAZ 61B — Localization UX Fix / Full Language Consistency Tests.

70+ tests covering:
- Expanded translation key completeness (295 keys × 9 languages)
- data-i18n attribute coverage in all major templates
- i18n.js feature completeness (fallback, toast, data-i18n variants)
- CSS ellipsis rules for translated labels
- Settings page checkmark CSS for active language
- JS toast messages wrapped in BW.i18n.t()
- Fallback chain correctness
- Template language consistency (no hardcoded text leaks)
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
I18N_JS = os.path.join(STATIC, "js", "i18n.js")
MOBILE_CSS = os.path.join(STATIC, "css", "mobile_trading.css")

LANGS = ["en", "tr", "es", "de", "fr", "pt", "ru", "ar", "zh"]


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════
# 1. EXPANDED KEY COMPLETENESS (10 tests)
# ══════════════════════════════════════════════════════════════
class TestExpandedKeyCompleteness(unittest.TestCase):
    """Verify all 9 locales have the full expanded key set."""

    def test_01_all_locales_have_minimum_295_keys(self):
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            self.assertGreaterEqual(len(data), 295, f"{lang}.json has {len(data)} keys, expected ≥295")

    def test_02_discover_keys_exist_in_all_locales(self):
        required = [
            "discover.live", "discover.volume", "discover.fear_greed",
            "discover.funding", "discover.btc_dom", "discover.ai_sentiment",
            "discover.ai_brief_label", "discover.ai_loading", "discover.watchlist",
            "discover.go_chart", "discover.trending_coins", "discover.featured_opps",
            "discover.view_all", "discover.market_news", "discover.news_title",
            "discover.chip_crypto", "discover.chip_stocks", "discover.chip_forex",
            "discover.chip_macro", "discover.go_source",
        ]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_03_activity_keys_exist_in_all_locales(self):
        required = [
            "activity.title", "activity.connecting", "activity.events",
            "activity.filter_all", "activity.filter_critical", "activity.filter_high",
            "activity.filter_volume", "activity.filter_momentum", "activity.filter_news",
            "activity.filter_strategy", "activity.filter_social", "activity.load_more",
            "activity.ai_summary", "activity.ai_loading", "activity.trending_symbols",
            "activity.type_distribution", "activity.severity_levels",
            "activity.sev_critical", "activity.sev_high", "activity.sev_medium", "activity.sev_low",
        ]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_04_settings_extended_keys_exist(self):
        required = [
            "settings.profile_desc", "settings.username", "settings.email",
            "settings.lang_desc", "settings.appearance_desc", "settings.notif_desc",
            "settings.notif_master_desc", "settings.markets_desc", "settings.ai_desc",
            "settings.ai_brief_notif", "settings.ai_brief_notif_desc",
            "settings.privacy_desc", "settings.search_indexing_desc",
            "settings.security_desc", "settings.subscription_desc",
            "settings.subscription_info", "settings.invite_desc", "settings.go_invite",
            "settings.data_desc", "settings.delete_confirm",
            "settings.theme_updated", "settings.region_saved", "settings.notif_saved",
            "settings.markets_saved", "settings.privacy_saved", "settings.pw_coming",
            "settings.logged_out_all", "settings.data_exported", "settings.export_failed",
            "settings.delete_requested", "settings.number_standard", "settings.number_european",
        ]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_05_tv_keys_exist_in_all_locales(self):
        required = ["tv.new_tab", "tv.mobile", "tv.search_panels", "tv.main_panel"]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_06_portfolio_keys_exist_in_all_locales(self):
        required = [
            "portfolio.total_pnl", "portfolio.asset_count", "portfolio.risk_score",
            "portfolio.allocation", "portfolio.risk_indicator", "portfolio.assets",
            "portfolio.market", "portfolio.symbol", "portfolio.amount",
            "portfolio.entry_price", "portfolio.ai_analysis",
        ]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_07_simulator_keys_exist_in_all_locales(self):
        required = [
            "simulator.title", "simulator.disclaimer", "simulator.demo",
            "simulator.balance", "simulator.equity", "simulator.available",
            "simulator.unrealized_pnl", "simulator.realized_pnl",
            "simulator.order_book", "simulator.place_order",
        ]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_08_pricing_keys_exist_in_all_locales(self):
        required = [
            "pricing.choose_plan", "pricing.plan_desc",
            "pricing.pro_desc", "pricing.pro_plus_desc",
        ]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_09_common_keys_exist_in_all_locales(self):
        required = ["common.all", "common.go_to", "common.view_all", "common.coming_soon"]
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for key in required:
                self.assertIn(key, data, f"{lang}.json missing key: {key}")

    def test_10_all_locales_have_same_keys(self):
        en_keys = set(_json(os.path.join(LOCALES, "en.json")).keys())
        for lang in LANGS:
            if lang == "en":
                continue
            keys = set(_json(os.path.join(LOCALES, f"{lang}.json")).keys())
            missing = en_keys - keys
            self.assertEqual(len(missing), 0, f"{lang}.json missing keys: {missing}")


# ══════════════════════════════════════════════════════════════
# 2. NO EMPTY TRANSLATION VALUES (5 tests)
# ══════════════════════════════════════════════════════════════
class TestNoEmptyValues(unittest.TestCase):
    """Verify no translation value is empty or whitespace-only."""

    def test_11_en_no_empty_values(self):
        data = _json(os.path.join(LOCALES, "en.json"))
        for k, v in data.items():
            self.assertTrue(v.strip(), f"en.json: key '{k}' has empty value")

    def test_12_tr_no_empty_values(self):
        data = _json(os.path.join(LOCALES, "tr.json"))
        for k, v in data.items():
            self.assertTrue(v.strip(), f"tr.json: key '{k}' has empty value")

    def test_13_all_locales_no_empty_values(self):
        for lang in LANGS:
            data = _json(os.path.join(LOCALES, f"{lang}.json"))
            for k, v in data.items():
                self.assertTrue(v.strip(), f"{lang}.json: key '{k}' has empty value")

    def test_14_en_and_tr_differ(self):
        """Important translated keys should differ between en and tr."""
        en = _json(os.path.join(LOCALES, "en.json"))
        tr = _json(os.path.join(LOCALES, "tr.json"))
        differ_keys = ["sidebar.discover", "settings.title", "activity.title",
                       "discover.volume", "settings.profile"]
        for k in differ_keys:
            if k in en and k in tr:
                self.assertNotEqual(en[k], tr[k], f"en and tr should differ for '{k}'")

    def test_15_ar_has_arabic_characters(self):
        """Arabic locale should contain Arabic script."""
        data = _json(os.path.join(LOCALES, "ar.json"))
        arabic_re = re.compile(r'[\u0600-\u06FF]')
        has_arabic = any(arabic_re.search(v) for v in data.values())
        self.assertTrue(has_arabic, "ar.json should contain Arabic characters")


# ══════════════════════════════════════════════════════════════
# 3. DATA-I18N COVERAGE IN TEMPLATES (20 tests)
# ══════════════════════════════════════════════════════════════
class TestDataI18nCoverage(unittest.TestCase):
    """Verify critical templates have proper data-i18n attributes."""

    def _count_data_i18n(self, html):
        return len(re.findall(r'data-i18n(?:-\w+)?=', html))

    # --- discover.html ---
    def test_16_discover_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "discover.html"))
        count = self._count_data_i18n(html)
        self.assertGreaterEqual(count, 15, f"discover.html: {count} data-i18n, expected ≥15")

    def test_17_discover_volume_label(self):
        html = _read(os.path.join(TEMPLATES, "discover.html"))
        self.assertIn('data-i18n="discover.volume"', html)

    def test_18_discover_watchlist_label(self):
        html = _read(os.path.join(TEMPLATES, "discover.html"))
        self.assertIn('data-i18n="discover.watchlist"', html)

    def test_19_discover_trending_label(self):
        html = _read(os.path.join(TEMPLATES, "discover.html"))
        self.assertIn('data-i18n="discover.trending_coins"', html)

    def test_20_discover_news_chips(self):
        html = _read(os.path.join(TEMPLATES, "discover.html"))
        self.assertIn('data-i18n="discover.chip_crypto"', html)
        self.assertIn('data-i18n="discover.chip_forex"', html)

    # --- settings.html ---
    def test_21_settings_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        count = self._count_data_i18n(html)
        self.assertGreaterEqual(count, 50, f"settings.html: {count} data-i18n, expected ≥50")

    def test_22_settings_nav_items_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertIn('data-i18n="settings.profile"', html)
        self.assertIn('data-i18n="settings.language"', html)
        self.assertIn('data-i18n="settings.appearance"', html)
        self.assertIn('data-i18n="settings.notifications"', html)
        self.assertIn('data-i18n="settings.privacy"', html)
        self.assertIn('data-i18n="settings.security"', html)

    def test_23_settings_toggle_labels_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertIn('data-i18n="settings.notif_enabled"', html)
        self.assertIn('data-i18n="settings.notif_email"', html)
        self.assertIn('data-i18n="settings.notif_push"', html)

    def test_24_settings_visibility_options_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertIn('data-i18n="settings.visibility_public"', html)
        self.assertIn('data-i18n="settings.visibility_friends"', html)
        self.assertIn('data-i18n="settings.visibility_private"', html)

    def test_25_settings_theme_names_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertIn('data-i18n="settings.theme_dark"', html)
        self.assertIn('data-i18n="settings.theme_dark_pro"', html)
        self.assertIn('data-i18n="settings.theme_system"', html)

    def test_26_settings_market_checkboxes_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertIn('data-i18n="settings.market_crypto"', html)
        self.assertIn('data-i18n="settings.market_stocks"', html)
        self.assertIn('data-i18n="settings.market_forex"', html)

    def test_27_settings_save_buttons_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        save_count = html.count('data-i18n="settings.save"')
        self.assertGreaterEqual(save_count, 3, f"Expected ≥3 save buttons with data-i18n, got {save_count}")

    def test_28_settings_password_placeholders_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "settings.html"))
        self.assertIn('data-i18n-placeholder="settings.current_password"', html)
        self.assertIn('data-i18n-placeholder="settings.new_password"', html)
        self.assertIn('data-i18n-placeholder="settings.confirm_password"', html)

    # --- activity.html ---
    def test_29_activity_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "activity.html"))
        count = self._count_data_i18n(html)
        self.assertGreaterEqual(count, 15, f"activity.html: {count} data-i18n, expected ≥15")

    def test_30_activity_filter_chips_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "activity.html"))
        self.assertIn('data-i18n="activity.filter_all"', html)
        self.assertIn('data-i18n="activity.filter_critical"', html)
        self.assertIn('data-i18n="activity.filter_social"', html)

    def test_31_activity_severity_labels_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "activity.html"))
        self.assertIn('data-i18n="activity.sev_critical"', html)
        self.assertIn('data-i18n="activity.sev_high"', html)
        self.assertIn('data-i18n="activity.sev_medium"', html)
        self.assertIn('data-i18n="activity.sev_low"', html)

    def test_32_activity_sidebar_titles_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "activity.html"))
        self.assertIn('data-i18n="activity.ai_summary"', html)
        self.assertIn('data-i18n="activity.trending_symbols"', html)
        self.assertIn('data-i18n="activity.type_distribution"', html)

    # --- tv.html ---
    def test_33_tv_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "tv.html"))
        count = self._count_data_i18n(html)
        self.assertGreaterEqual(count, 3, f"tv.html: {count} data-i18n, expected ≥3")

    def test_34_tv_buttons_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "tv.html"))
        self.assertIn('data-i18n="tv.new_tab"', html)
        self.assertIn('data-i18n="tv.mobile"', html)

    def test_35_tv_search_placeholder_has_i18n(self):
        html = _read(os.path.join(TEMPLATES, "tv.html"))
        self.assertIn('data-i18n-placeholder="tv.search_panels"', html)


# ══════════════════════════════════════════════════════════════
# 4. PORTFOLIO / SIMULATOR / PRICING TEMPLATES (8 tests)
# ══════════════════════════════════════════════════════════════
class TestOtherTemplates(unittest.TestCase):
    """Verify portfolio, simulator, pricing templates have data-i18n."""

    def test_36_portfolio_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "portfolio.html"))
        count = len(re.findall(r'data-i18n(?:-\w+)?=', html))
        self.assertGreaterEqual(count, 8, f"portfolio.html: {count} data-i18n, expected ≥8")

    def test_37_portfolio_card_labels_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "portfolio.html"))
        self.assertIn('data-i18n="portfolio.total_pnl"', html)
        self.assertIn('data-i18n="portfolio.asset_count"', html)
        self.assertIn('data-i18n="portfolio.risk_score"', html)

    def test_38_portfolio_table_headers_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "portfolio.html"))
        self.assertIn('data-i18n="portfolio.symbol"', html)
        self.assertIn('data-i18n="portfolio.market"', html)

    def test_39_simulator_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "simulator.html"))
        count = len(re.findall(r'data-i18n(?:-\w+)?=', html))
        self.assertGreaterEqual(count, 8, f"simulator.html: {count} data-i18n, expected ≥8")

    def test_40_simulator_account_labels_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "simulator.html"))
        self.assertIn('data-i18n="simulator.balance"', html)
        self.assertIn('data-i18n="simulator.equity"', html)
        self.assertIn('data-i18n="simulator.unrealized_pnl"', html)

    def test_41_simulator_panel_titles_have_i18n(self):
        html = _read(os.path.join(TEMPLATES, "simulator.html"))
        self.assertIn('data-i18n="simulator.order_book"', html)
        self.assertIn('data-i18n="simulator.place_order"', html)

    def test_42_pricing_has_data_i18n(self):
        html = _read(os.path.join(TEMPLATES, "pricing.html"))
        count = len(re.findall(r'data-i18n(?:-\w+)?=', html))
        self.assertGreaterEqual(count, 3, f"pricing.html: {count} data-i18n, expected ≥3")

    def test_43_pricing_hero_has_i18n(self):
        html = _read(os.path.join(TEMPLATES, "pricing.html"))
        self.assertIn('data-i18n="pricing.choose_plan"', html)
        self.assertIn('data-i18n="pricing.plan_desc"', html)


# ══════════════════════════════════════════════════════════════
# 5. I18N.JS FEATURES (12 tests)
# ══════════════════════════════════════════════════════════════
class TestI18nJsFeatures(unittest.TestCase):
    """Verify i18n.js has all FAZ 61B features."""

    def setUp(self):
        self.js = _read(I18N_JS)

    def test_44_no_double_iife_closing(self):
        """Must NOT have the double })(); bug."""
        matches = re.findall(r'\}\)\(\);', self.js)
        self.assertEqual(len(matches), 1, f"Expected exactly 1 IIFE closing, found {len(matches)}")

    def test_45_has_fallback_locale(self):
        self.assertIn('_fallbackLocale', self.js)

    def test_46_loads_en_fallback(self):
        self.assertIn("locale/en", self.js)

    def test_47_t_function_has_fallback_chain(self):
        """t() should check _fallbackLocale."""
        self.assertIn('_fallbackLocale[key]', self.js)

    def test_48_t_function_never_returns_undefined(self):
        """t() should return fallback or key, never undefined."""
        self.assertIn("return fallback || key", self.js)

    def test_49_has_show_toast(self):
        self.assertIn('_showToast', self.js)

    def test_50_toast_uses_green_bg(self):
        self.assertIn('#10b981', self.js)

    def test_51_setLanguage_shows_toast(self):
        self.assertIn("this._showToast", self.js)

    def test_52_refresh_handles_placeholder(self):
        self.assertIn('data-i18n-placeholder', self.js)

    def test_53_refresh_handles_title(self):
        self.assertIn('data-i18n-title', self.js)

    def test_54_refresh_handles_tooltip(self):
        self.assertIn('data-i18n-tooltip', self.js)

    def test_55_refresh_handles_tip(self):
        self.assertIn('data-i18n-tip', self.js)

    def test_56_refresh_handles_html(self):
        self.assertIn('data-i18n-html', self.js)

    def test_57_rtl_support_for_arabic(self):
        self.assertIn("lang === 'ar'", self.js)
        self.assertIn("'rtl'", self.js)

    def test_58_stores_lang_in_localstorage(self):
        self.assertIn('localStorage.setItem(_LS_KEY, lang)', self.js)

    def test_59_faz_header(self):
        self.assertIn('FAZ 52 + FAZ 61 + FAZ 61B', self.js)


# ══════════════════════════════════════════════════════════════
# 6. CSS ELLIPSIS RULES (5 tests)
# ══════════════════════════════════════════════════════════════
class TestCssEllipsis(unittest.TestCase):
    """Verify CSS has ellipsis/overflow rules for translated labels."""

    def setUp(self):
        self.css = _read(MOBILE_CSS)

    def test_60_has_text_overflow_ellipsis(self):
        self.assertIn('text-overflow: ellipsis', self.css)

    def test_61_mt_section_title_ellipsis(self):
        self.assertIn('.mt-section-title', self.css)

    def test_62_mt_stat_label_ellipsis(self):
        self.assertIn('.mt-stat-label', self.css)

    def test_63_settings_nav_item_ellipsis(self):
        self.assertIn('.settings-nav-item', self.css)

    def test_64_toggle_label_ellipsis(self):
        self.assertIn('.toggle-label', self.css)


# ══════════════════════════════════════════════════════════════
# 7. SETTINGS CHECKMARK & JS TOAST I18N (6 tests)
# ══════════════════════════════════════════════════════════════
class TestSettingsCheckmarkAndToasts(unittest.TestCase):
    """Verify settings page has checkmark CSS and i18n'd toast messages."""

    def setUp(self):
        self.html = _read(os.path.join(TEMPLATES, "settings.html"))

    def test_65_lang_option_checkmark_css(self):
        self.assertIn('.lang-option.selected::after', self.html)

    def test_66_checkmark_content(self):
        self.assertRegex(self.html, r"content:\s*['\"]✓['\"]")

    def test_67_theme_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.theme_updated'", self.html)

    def test_68_region_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.region_saved'", self.html)

    def test_69_notif_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.notif_saved'", self.html)

    def test_70_privacy_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.privacy_saved'", self.html)

    def test_71_markets_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.markets_saved'", self.html)

    def test_72_delete_warning_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.delete_warning'", self.html)

    def test_73_export_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.data_exported'", self.html)

    def test_74_password_toast_uses_i18n(self):
        self.assertIn("BW.i18n.t('settings.pw_coming'", self.html)


# ══════════════════════════════════════════════════════════════
# 8. TRANSLATION VALUE QUALITY (6 tests)
# ══════════════════════════════════════════════════════════════
class TestTranslationQuality(unittest.TestCase):
    """Verify translations are not just copies of English."""

    def test_75_tr_discover_keys_are_turkish(self):
        data = _json(os.path.join(LOCALES, "tr.json"))
        self.assertIn("Keşfet", data.get("sidebar.discover", ""))

    def test_76_es_has_spanish_values(self):
        data = _json(os.path.join(LOCALES, "es.json"))
        spanish_re = re.compile(r'[áéíóúñ¿¡]', re.IGNORECASE)
        has_spanish = any(spanish_re.search(v) for v in data.values())
        self.assertTrue(has_spanish, "es.json should contain Spanish characters")

    def test_77_de_has_german_values(self):
        data = _json(os.path.join(LOCALES, "de.json"))
        german_re = re.compile(r'[äöüß]', re.IGNORECASE)
        has_german = any(german_re.search(v) for v in data.values())
        self.assertTrue(has_german, "de.json should contain German characters")

    def test_78_zh_has_chinese_characters(self):
        data = _json(os.path.join(LOCALES, "zh.json"))
        chinese_re = re.compile(r'[\u4e00-\u9fff]')
        has_chinese = any(chinese_re.search(v) for v in data.values())
        self.assertTrue(has_chinese, "zh.json should contain Chinese characters")

    def test_79_ru_has_cyrillic(self):
        data = _json(os.path.join(LOCALES, "ru.json"))
        cyrillic_re = re.compile(r'[\u0400-\u04FF]')
        has_cyrillic = any(cyrillic_re.search(v) for v in data.values())
        self.assertTrue(has_cyrillic, "ru.json should contain Cyrillic characters")

    def test_80_fr_has_french_accents(self):
        data = _json(os.path.join(LOCALES, "fr.json"))
        french_re = re.compile(r'[àâçéèêëîïôùûü]', re.IGNORECASE)
        has_french = any(french_re.search(v) for v in data.values())
        self.assertTrue(has_french, "fr.json should contain French accented characters")


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
