"""
ZKR Analiz Pro — FAZ 43 PWA / App Shell Tests
Covers: manifest, service worker, offline page, PWA install,
        mobile components, bottom sheet, mobile nav, push engine,
        layout integration, responsive CSS, live HTTP endpoints.
"""

import json
import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import requests

BASE_URL = "http://127.0.0.1:34000"


def _read(rel_path):
    with open(os.path.join(BASE, rel_path), "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════
# 1. Manifest
# ═══════════════════════════════════════════════════════════════
class TestManifest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(_read("static/manifest.json"))

    def test_manifest_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/manifest.json")))

    def test_name_is_zkr_analiz_pro(self):
        self.assertEqual(self.data["name"], "ZKR Analiz Pro")

    def test_short_name(self):
        self.assertEqual(self.data["short_name"], "ZKR Analiz")

    def test_start_url(self):
        self.assertEqual(self.data["start_url"], "/discover")

    def test_display_standalone(self):
        self.assertEqual(self.data["display"], "standalone")

    def test_background_color(self):
        self.assertEqual(self.data["background_color"], "#06080D")

    def test_theme_color(self):
        self.assertEqual(self.data["theme_color"], "#06080D")

    def test_has_icons(self):
        self.assertGreaterEqual(len(self.data["icons"]), 2)

    def test_has_192_icon(self):
        sizes = [i["sizes"] for i in self.data["icons"]]
        self.assertIn("192x192", sizes)

    def test_has_512_icon(self):
        sizes = [i["sizes"] for i in self.data["icons"]]
        self.assertIn("512x512", sizes)

    def test_has_svg_icon(self):
        types = [i.get("type", "") for i in self.data["icons"]]
        self.assertIn("image/svg+xml", types)

    def test_has_shortcuts(self):
        self.assertIn("shortcuts", self.data)
        self.assertGreaterEqual(len(self.data["shortcuts"]), 2)

    def test_orientation(self):
        self.assertEqual(self.data["orientation"], "any")

    def test_scope(self):
        self.assertEqual(self.data["scope"], "/")


# ═══════════════════════════════════════════════════════════════
# 2. Icon Files
# ═══════════════════════════════════════════════════════════════
class TestIconFiles(unittest.TestCase):
    def test_icon_svg_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/icon.svg")))

    def test_icon_192_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/icons/icon-192.png")))

    def test_icon_512_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/icons/icon-512.png")))

    def test_icon_192_is_png(self):
        with open(os.path.join(BASE, "static/icons/icon-192.png"), "rb") as f:
            self.assertTrue(f.read(4).startswith(b"\x89PNG"))

    def test_icon_512_is_png(self):
        with open(os.path.join(BASE, "static/icons/icon-512.png"), "rb") as f:
            self.assertTrue(f.read(4).startswith(b"\x89PNG"))


# ═══════════════════════════════════════════════════════════════
# 3. Service Worker
# ═══════════════════════════════════════════════════════════════
class TestServiceWorker(unittest.TestCase):
    def setUp(self):
        self.sw = _read("static/service-worker.js")

    def test_sw_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/service-worker.js")))

    def test_has_cache_version(self):
        self.assertIn("CACHE_VERSION", self.sw)

    def test_has_shell_cache(self):
        self.assertIn("SHELL_CACHE", self.sw)

    def test_has_install_event(self):
        self.assertIn("addEventListener('install'", self.sw)

    def test_has_activate_event(self):
        self.assertIn("addEventListener('activate'", self.sw)

    def test_has_fetch_event(self):
        self.assertIn("addEventListener('fetch'", self.sw)

    def test_has_cache_first_strategy(self):
        self.assertIn("cacheFirst", self.sw)

    def test_has_network_first_strategy(self):
        self.assertIn("networkFirstPage", self.sw)

    def test_has_offline_fallback(self):
        self.assertIn("/offline", self.sw)

    def test_skips_api_calls(self):
        self.assertIn("/api/", self.sw)

    def test_skips_ws_calls(self):
        self.assertIn("/ws", self.sw)

    def test_has_push_handler(self):
        self.assertIn("addEventListener('push'", self.sw)

    def test_has_notification_click(self):
        self.assertIn("notificationclick", self.sw)

    def test_caches_mobile_components_css(self):
        self.assertIn("mobile_components.css", self.sw)

    def test_caches_pwa_install_js(self):
        self.assertIn("pwa_install.js", self.sw)


# ═══════════════════════════════════════════════════════════════
# 4. Offline Page
# ═══════════════════════════════════════════════════════════════
class TestOfflinePage(unittest.TestCase):
    def setUp(self):
        self.html = _read("templates/offline.html")

    def test_offline_template_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "templates/offline.html")))

    def test_extends_layout_terminal(self):
        self.assertIn('extends "layout_terminal.html"', self.html)

    def test_has_offline_message(self):
        self.assertIn("Offline", self.html)

    def test_has_retry_button(self):
        self.assertIn("Retry", self.html)

    def test_has_faz43_comment(self):
        self.assertIn("FAZ 43", self.html)


# ═══════════════════════════════════════════════════════════════
# 5. PWA Install Script
# ═══════════════════════════════════════════════════════════════
class TestPwaInstall(unittest.TestCase):
    def setUp(self):
        self.js = _read("static/js/pwa_install.js")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/js/pwa_install.js")))

    def test_has_beforeinstallprompt(self):
        self.assertIn("beforeinstallprompt", self.js)

    def test_has_dismiss_logic(self):
        self.assertIn("isDismissed", self.js)

    def test_has_localstorage_persist(self):
        self.assertIn("localStorage", self.js)

    def test_has_install_button(self):
        self.assertIn("pwaInstallAccept", self.js)

    def test_has_dismiss_button(self):
        self.assertIn("pwaInstallDismiss", self.js)

    def test_has_sidebar_button_wire(self):
        self.assertIn("pwaInstallSidebarBtn", self.js)

    def test_exposes_global_api(self):
        self.assertIn("BWPwaInstall", self.js)

    def test_has_appinstalled_handler(self):
        self.assertIn("appinstalled", self.js)


# ═══════════════════════════════════════════════════════════════
# 6. Mobile Components CSS
# ═══════════════════════════════════════════════════════════════
class TestMobileCSS(unittest.TestCase):
    def setUp(self):
        self.css = _read("static/css/mobile_components.css")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/css/mobile_components.css")))

    def test_has_pwa_install_banner(self):
        self.assertIn(".pwa-install-banner", self.css)

    def test_has_mobile_sheet(self):
        self.assertIn(".mobile-sheet", self.css)

    def test_has_bottom_sheet_overlay(self):
        self.assertIn(".mobile-sheet-overlay", self.css)

    def test_has_mobile_fab(self):
        self.assertIn(".mobile-fab", self.css)

    def test_has_768_breakpoint(self):
        self.assertIn("max-width: 768px", self.css)

    def test_has_1024_breakpoint(self):
        self.assertIn("max-width: 1024px", self.css)

    def test_has_touch_friendly_min_height(self):
        self.assertIn("min-height: 44px", self.css)

    def test_has_ios_zoom_prevention(self):
        self.assertIn("font-size: 16px", self.css)

    def test_has_safe_area_inset(self):
        self.assertIn("safe-area-inset", self.css)

    def test_has_chart_fullscreen(self):
        self.assertIn(".chart-fullscreen", self.css)

    def test_has_display_mode_standalone(self):
        self.assertIn("display-mode: standalone", self.css)

    def test_has_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", self.css)

    def test_has_faz43_comment(self):
        self.assertIn("FAZ 43", self.css)


# ═══════════════════════════════════════════════════════════════
# 7. Mobile Sheet JS Component
# ═══════════════════════════════════════════════════════════════
class TestMobileSheetJS(unittest.TestCase):
    def setUp(self):
        self.js = _read("static/js/components/mobile_sheet.js")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/js/components/mobile_sheet.js")))

    def test_has_constructor(self):
        self.assertIn("function MobileSheet", self.js)

    def test_has_open_method(self):
        self.assertIn(".open", self.js)

    def test_has_close_method(self):
        self.assertIn(".close", self.js)

    def test_has_set_content(self):
        self.assertIn("setContent", self.js)

    def test_has_touch_drag(self):
        self.assertIn("touchstart", self.js)
        self.assertIn("touchmove", self.js)
        self.assertIn("touchend", self.js)

    def test_exposes_global(self):
        self.assertIn("window.MobileSheet", self.js)

    def test_has_destroy(self):
        self.assertIn("destroy", self.js)


# ═══════════════════════════════════════════════════════════════
# 8. Mobile Nav JS
# ═══════════════════════════════════════════════════════════════
class TestMobileNavJS(unittest.TestCase):
    def setUp(self):
        self.js = _read("static/js/mobile_nav.js")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/js/mobile_nav.js")))

    def test_auto_hide_scroll(self):
        self.assertIn("bb-hidden", self.js)

    def test_swipe_close_sidebar(self):
        self.assertIn("touchstart", self.js)

    def test_orientation_change(self):
        self.assertIn("orientationchange", self.js)

    def test_references_bottombar(self):
        self.assertIn("proBottombar", self.js)


# ═══════════════════════════════════════════════════════════════
# 9. Push Engine
# ═══════════════════════════════════════════════════════════════
class TestPushEngine(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "app/core/push_engine.py")))

    def test_imports_succeed(self):
        from app.core import push_engine
        self.assertTrue(hasattr(push_engine, "register_device"))
        self.assertTrue(hasattr(push_engine, "unregister_device"))
        self.assertTrue(hasattr(push_engine, "send_push"))
        self.assertTrue(hasattr(push_engine, "get_preferences"))
        self.assertTrue(hasattr(push_engine, "update_preferences"))
        self.assertTrue(hasattr(push_engine, "get_stats"))
        self.assertTrue(hasattr(push_engine, "get_push_log"))
        self.assertTrue(hasattr(push_engine, "get_user_devices"))

    def test_register_device(self):
        from app.core import push_engine
        result = push_engine.register_device("test_user", "test_token_faz43", "web")
        self.assertTrue(result)

    def test_get_user_devices(self):
        from app.core import push_engine
        push_engine.register_device("test_user_faz43", "token_get_test", "web")
        devices = push_engine.get_user_devices("test_user_faz43")
        self.assertIsInstance(devices, list)

    def test_get_preferences_defaults(self):
        from app.core import push_engine
        prefs = push_engine.get_preferences("nonexistent_user_faz43")
        self.assertIsInstance(prefs, dict)
        self.assertIn("alerts_enabled", prefs)
        self.assertTrue(prefs["alerts_enabled"])

    def test_update_preferences(self):
        from app.core import push_engine
        result = push_engine.update_preferences("test_pref_user", {"alerts_enabled": 0})
        self.assertTrue(result)

    def test_send_push_stub(self):
        from app.core import push_engine
        result = push_engine.send_push("test_user", "Test Title", "Test body")
        self.assertTrue(result)

    def test_get_push_log(self):
        from app.core import push_engine
        push_engine.send_push("log_test_user", "Log Test", "Body")
        log = push_engine.get_push_log("log_test_user", limit=5)
        self.assertIsInstance(log, list)

    def test_get_stats(self):
        from app.core import push_engine
        stats = push_engine.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("active_devices", stats)
        self.assertIn("total_sent", stats)


# ═══════════════════════════════════════════════════════════════
# 10. Layout Integration
# ═══════════════════════════════════════════════════════════════
class TestLayoutIntegration(unittest.TestCase):
    def setUp(self):
        self.layout = _read("templates/layout_terminal.html")

    def test_has_manifest_link(self):
        self.assertIn('rel="manifest"', self.layout)

    def test_has_theme_color_meta(self):
        self.assertIn('name="theme-color"', self.layout)

    def test_has_viewport_meta(self):
        self.assertIn('name="viewport"', self.layout)

    def test_has_apple_mobile_meta(self):
        self.assertIn('apple-mobile-web-app-capable', self.layout)

    def test_has_apple_touch_icon(self):
        self.assertIn('apple-touch-icon', self.layout)

    def test_has_mobile_components_css(self):
        self.assertIn('mobile_components.css', self.layout)

    def test_has_pwa_install_js(self):
        self.assertIn('pwa_install.js', self.layout)

    def test_has_mobile_nav_js(self):
        self.assertIn('mobile_nav.js', self.layout)

    def test_has_mobile_sheet_js(self):
        self.assertIn('mobile_sheet.js', self.layout)

    def test_has_sw_registration(self):
        self.assertIn("serviceWorker", self.layout)

    def test_has_pwa_install_sidebar_btn(self):
        self.assertIn("pwaInstallSidebarBtn", self.layout)

    def test_has_mobile_menu_btn(self):
        self.assertIn("mobileMenuBtn", self.layout)

    def test_has_bottom_bar(self):
        self.assertIn("pro-bottombar", self.layout)

    def test_bottom_bar_has_5_items(self):
        count = self.layout.count("pro-bb-item")
        self.assertGreaterEqual(count, 5)

    def test_faz43_comment(self):
        self.assertIn("FAZ 43", self.layout)


# ═══════════════════════════════════════════════════════════════
# 11. Base Template Integration
# ═══════════════════════════════════════════════════════════════
class TestBaseTemplateIntegration(unittest.TestCase):
    def setUp(self):
        self.base = _read("templates/base.html")

    def test_has_manifest_link(self):
        self.assertIn('rel="manifest"', self.base)

    def test_has_apple_touch_icon(self):
        self.assertIn('apple-touch-icon', self.base)

    def test_has_theme_color(self):
        self.assertIn('#06080D', self.base)

    def test_has_sw_registration(self):
        self.assertIn("serviceWorker", self.base)


# ═══════════════════════════════════════════════════════════════
# 12. Monolith Routes
# ═══════════════════════════════════════════════════════════════
class TestMonolithRoutes(unittest.TestCase):
    def setUp(self):
        self.mono = _read("legacy_monolith.py")

    def test_has_offline_route(self):
        self.assertIn('/offline', self.mono)

    def test_has_offline_function(self):
        self.assertIn('def offline_page', self.mono)

    def test_offline_renders_template(self):
        self.assertIn('render_template("offline.html")', self.mono)

    def test_faz43_comment(self):
        self.assertIn("FAZ 43", self.mono)


# ═══════════════════════════════════════════════════════════════
# 13. Live HTTP Tests
# ═══════════════════════════════════════════════════════════════
class TestLiveHTTP(unittest.TestCase):
    def test_manifest_json_200(self):
        r = requests.get(f"{BASE_URL}/static/manifest.json", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_manifest_json_valid(self):
        r = requests.get(f"{BASE_URL}/static/manifest.json", timeout=5)
        data = r.json()
        self.assertEqual(data["name"], "ZKR Analiz Pro")

    def test_service_worker_200(self):
        r = requests.get(f"{BASE_URL}/static/service-worker.js", timeout=5)
        self.assertEqual(r.status_code, 200)
        self.assertIn("CACHE_VERSION", r.text)

    def test_offline_page_200(self):
        r = requests.get(f"{BASE_URL}/offline", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_offline_page_content(self):
        r = requests.get(f"{BASE_URL}/offline", timeout=5)
        self.assertIn("Offline", r.text)

    def test_icon_svg_200(self):
        r = requests.get(f"{BASE_URL}/static/icon.svg", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_icon_192_200(self):
        r = requests.get(f"{BASE_URL}/static/icons/icon-192.png", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_icon_512_200(self):
        r = requests.get(f"{BASE_URL}/static/icons/icon-512.png", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_mobile_components_css_200(self):
        r = requests.get(f"{BASE_URL}/static/css/mobile_components.css", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_pwa_install_js_200(self):
        r = requests.get(f"{BASE_URL}/static/js/pwa_install.js", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_mobile_nav_js_200(self):
        r = requests.get(f"{BASE_URL}/static/js/mobile_nav.js", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_mobile_sheet_js_200(self):
        r = requests.get(f"{BASE_URL}/static/js/components/mobile_sheet.js", timeout=5)
        self.assertEqual(r.status_code, 200)

    def test_discover_has_manifest_link(self):
        r = requests.get(f"{BASE_URL}/discover", timeout=5)
        self.assertIn('manifest.json', r.text)

    def test_discover_has_mobile_css(self):
        r = requests.get(f"{BASE_URL}/discover", timeout=5)
        self.assertIn('mobile_components.css', r.text)

    def test_discover_has_pwa_install(self):
        r = requests.get(f"{BASE_URL}/discover", timeout=5)
        self.assertIn('pwa_install.js', r.text)

    def test_discover_has_mobile_nav(self):
        r = requests.get(f"{BASE_URL}/discover", timeout=5)
        self.assertIn('mobile_nav.js', r.text)

    def test_trade_page_has_sw_registration(self):
        r = requests.get(f"{BASE_URL}/trade", timeout=5)
        self.assertIn('serviceWorker', r.text)

    def test_discover_has_bottom_bar(self):
        r = requests.get(f"{BASE_URL}/discover", timeout=5)
        self.assertIn('pro-bottombar', r.text)

    def test_discover_has_pwa_sidebar_btn(self):
        r = requests.get(f"{BASE_URL}/discover", timeout=5)
        self.assertIn('pwaInstallSidebarBtn', r.text)


if __name__ == "__main__":
    unittest.main()
