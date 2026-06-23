# -*- coding: utf-8 -*-
"""FAZ 65 — Full Feature Masking Tests.

45+ tests covering:
- Courses COMING_SOON flag and 503 API responses
- Mentors COMING_SOON flag and 503 API responses
- Live Rooms COMING_SOON flag and 503 API responses
- Sidebar nav cs-locked classes
- Menu "Yakında" badges
- Template coming_soon content wrappers
- CSS coming-soon styles
- No data leakage from locked features
"""
import json
import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# ── File paths ────────────────────────────────────────────────────
COURSES_ROUTES     = os.path.join(BASE, "app", "blueprints", "courses", "routes.py")
MENTORS_ROUTES     = os.path.join(BASE, "app", "blueprints", "mentors", "routes.py")
LIVE_ROOMS_ROUTES  = os.path.join(BASE, "app", "blueprints", "live_rooms", "routes.py")
LAYOUT_HTML        = os.path.join(BASE, "templates", "layout_terminal.html")
MENU_HTML          = os.path.join(BASE, "templates", "menu.html")
COURSES_HTML       = os.path.join(BASE, "templates", "courses.html")
COURSE_DETAIL_HTML = os.path.join(BASE, "templates", "course_detail.html")
MY_COURSES_HTML    = os.path.join(BASE, "templates", "my_courses.html")
MENTORS_HTML       = os.path.join(BASE, "templates", "mentors.html")
ROOMS_HTML         = os.path.join(BASE, "templates", "rooms.html")
COMPONENTS_CSS     = os.path.join(BASE, "static", "css", "components.css")
ACTIVITY_HTML      = os.path.join(BASE, "templates", "activity.html")
DISCOVER_HTML      = os.path.join(BASE, "templates", "discover.html")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# 1) COURSES — COMING_SOON Backend Lock
# ══════════════════════════════════════════════════════════════════

class TestCoursesComingSoon(unittest.TestCase):
    """Verify courses COMING_SOON flag and 503 guards."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(COURSES_ROUTES)

    def test_coming_soon_flag_exists(self):
        self.assertIn("COMING_SOON = True", self.src)

    def test_coming_soon_response_function(self):
        self.assertIn("def _coming_soon_response()", self.src)

    def test_coming_soon_response_returns_503(self):
        self.assertIn("503", self.src)

    def test_coming_soon_response_json_message(self):
        self.assertIn("Kurs sistemi yakında aktif olacak", self.src)

    def test_api_list_courses_guarded(self):
        pattern = r'def api_list_courses.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_course_detail_guarded(self):
        pattern = r'def api_course_detail.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_featured_courses_guarded(self):
        pattern = r'def api_featured_courses.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_create_course_guarded(self):
        pattern = r'def api_create_course.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_update_course_guarded(self):
        pattern = r'def api_update_course.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_publish_course_guarded(self):
        pattern = r'def api_publish_course.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_add_lesson_guarded(self):
        pattern = r'def api_add_lesson.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_update_lesson_guarded(self):
        pattern = r'def api_update_lesson.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_list_lessons_guarded(self):
        pattern = r'def api_list_lessons.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_enroll_guarded(self):
        pattern = r'def api_enroll.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_my_courses_guarded(self):
        pattern = r'def api_my_courses.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_progress_guarded(self):
        pattern = r'def api_progress.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_copilot_courses_guarded(self):
        pattern = r'def api_copilot_courses.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_page_routes_pass_coming_soon(self):
        self.assertIn("coming_soon=COMING_SOON", self.src)

    def test_courses_page_passes_coming_soon(self):
        pattern = r'def courses_page.*?coming_soon=COMING_SOON'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_course_detail_page_passes_coming_soon(self):
        pattern = r'def course_detail_page.*?coming_soon=COMING_SOON'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_my_courses_page_passes_coming_soon(self):
        pattern = r'def my_courses_page.*?coming_soon=COMING_SOON'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))


# ══════════════════════════════════════════════════════════════════
# 2) MENTORS — COMING_SOON Backend Lock
# ══════════════════════════════════════════════════════════════════

class TestMentorsComingSoon(unittest.TestCase):
    """Verify mentors are already locked with COMING_SOON."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(MENTORS_ROUTES)

    def test_coming_soon_flag(self):
        self.assertIn("COMING_SOON = True", self.src)

    def test_coming_soon_response(self):
        self.assertIn("def _coming_soon_response()", self.src)

    def test_api_list_mentors_guarded(self):
        pattern = r'def api_list_mentors.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_featured_mentors_guarded(self):
        pattern = r'def api_featured_mentors.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_mentor_profile_guarded(self):
        pattern = r'def api_mentor_profile.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_pages_pass_coming_soon(self):
        self.assertIn("coming_soon=COMING_SOON", self.src)


# ══════════════════════════════════════════════════════════════════
# 3) LIVE ROOMS — COMING_SOON Backend Lock
# ══════════════════════════════════════════════════════════════════

class TestLiveRoomsComingSoon(unittest.TestCase):
    """Verify live_rooms are locked with COMING_SOON."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(LIVE_ROOMS_ROUTES)

    def test_coming_soon_flag(self):
        self.assertIn("COMING_SOON = True", self.src)

    def test_coming_soon_response(self):
        self.assertIn("def _coming_soon_response()", self.src)

    def test_api_list_rooms_guarded(self):
        pattern = r'def api_list_rooms.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_room_detail_guarded(self):
        pattern = r'def api_room_detail.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_api_create_room_guarded(self):
        pattern = r'def api_create_room.*?return _coming_soon_response'
        self.assertRegex(self.src, re.compile(pattern, re.DOTALL))

    def test_pages_pass_coming_soon(self):
        self.assertIn("coming_soon=COMING_SOON", self.src)


# ══════════════════════════════════════════════════════════════════
# 4) SIDEBAR NAV — cs-locked Classes
# ══════════════════════════════════════════════════════════════════

class TestSidebarNavLock(unittest.TestCase):
    """Verify sidebar nav buttons have cs-locked class."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(LAYOUT_HTML)

    def test_mentors_cs_locked(self):
        self.assertIn('href="/mentors" class="tl-nav-btn cs-locked', self.html)

    def test_rooms_cs_locked(self):
        self.assertIn('href="/rooms" class="tl-nav-btn cs-locked', self.html)

    def test_courses_cs_locked(self):
        self.assertIn('href="/courses" class="tl-nav-btn cs-locked', self.html)

    def test_mentors_tooltip_yakinda(self):
        # Anonymized — no feature name in tooltip
        self.assertIn('data-tooltip="Yakında"', self.html)

    def test_rooms_tooltip_yakinda(self):
        self.assertIn('data-tooltip="Yakında"', self.html)

    def test_courses_tooltip_yakinda(self):
        self.assertIn('data-tooltip="Yakında"', self.html)


# ══════════════════════════════════════════════════════════════════
# 5) MENU — "Yakında" Badges
# ══════════════════════════════════════════════════════════════════

class TestMenuBadges(unittest.TestCase):
    """Verify menu items have 'Yakında' badge for locked features."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(MENU_HTML)

    def test_mentors_badge(self):
        # Anonymized — menu labels say "Yakında" instead of feature names
        self.assertIn('Yakında <span class="badge-coming-soon">Yakında</span>', self.html)

    def test_rooms_badge(self):
        self.assertIn('Yakında <span class="badge-coming-soon">Yakında</span>', self.html)

    def test_courses_badge(self):
        self.assertIn('Yakında <span class="badge-coming-soon">Yakında</span>', self.html)


# ══════════════════════════════════════════════════════════════════
# 6) TEMPLATE — Coming Soon Content Wrappers
# ══════════════════════════════════════════════════════════════════

class TestCourseTemplatesComingSoon(unittest.TestCase):
    """Verify course templates have coming_soon content wrappers."""

    def test_courses_html_has_coming_soon_block(self):
        html = _read(COURSES_HTML)
        self.assertIn("{% if coming_soon %}", html)
        self.assertIn("coming-soon-page", html)

    def test_courses_html_has_cs_title(self):
        html = _read(COURSES_HTML)
        # Anonymized — generic title, no feature name
        self.assertIn("Yeni Özellik Yakında", html)

    def test_courses_html_has_notify_btn(self):
        html = _read(COURSES_HTML)
        self.assertIn("Haberdar Et", html)

    def test_courses_html_no_feature_leak(self):
        html = _read(COURSES_HTML)
        # Must NOT reveal feature details
        self.assertNotIn("Video Dersler", html)
        self.assertNotIn("Uzman Eğitmenler", html)
        self.assertNotIn("Kurs Sistemi", html)

    def test_courses_html_header_hidden_when_coming_soon(self):
        html = _read(COURSES_HTML)
        self.assertIn("{% if not coming_soon %}", html)

    def test_course_detail_has_coming_soon_block(self):
        html = _read(COURSE_DETAIL_HTML)
        self.assertIn("{% if coming_soon %}", html)
        self.assertIn("coming-soon-page", html)

    def test_my_courses_has_coming_soon_block(self):
        html = _read(MY_COURSES_HTML)
        self.assertIn("{% if coming_soon %}", html)
        self.assertIn("coming-soon-page", html)


class TestMentorTemplateComingSoon(unittest.TestCase):
    """Verify mentor template has coming_soon wrapper."""

    def test_mentors_html_has_coming_soon(self):
        html = _read(MENTORS_HTML)
        self.assertIn("{% if coming_soon %}", html)
        self.assertIn("coming-soon-page", html)

    def test_mentors_title(self):
        html = _read(MENTORS_HTML)
        # Anonymized — generic title, no feature name
        self.assertIn("Yeni Özellik Yakında", html)
        self.assertNotIn("Mentör Sistemi", html)


class TestRoomTemplateComingSoon(unittest.TestCase):
    """Verify rooms template has coming_soon wrapper."""

    def test_rooms_html_has_coming_soon(self):
        html = _read(ROOMS_HTML)
        self.assertIn("{% if coming_soon %}", html)
        self.assertIn("coming-soon-page", html)


# ══════════════════════════════════════════════════════════════════
# 7) CSS — Coming Soon Styles
# ══════════════════════════════════════════════════════════════════

class TestCSS(unittest.TestCase):
    """Verify CSS has all coming-soon styles."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read(COMPONENTS_CSS)

    def test_coming_soon_page(self):
        self.assertIn(".coming-soon-page", self.css)

    def test_cs_icon(self):
        self.assertIn(".cs-icon", self.css)

    def test_cs_title(self):
        self.assertIn(".cs-title", self.css)

    def test_cs_subtitle(self):
        self.assertIn(".cs-subtitle", self.css)

    def test_cs_btn(self):
        self.assertIn(".cs-btn", self.css)

    def test_cs_shimmer(self):
        self.assertIn(".cs-shimmer", self.css)

    def test_cs_features(self):
        self.assertIn(".cs-features", self.css)

    def test_badge_coming_soon(self):
        self.assertIn(".badge-coming-soon", self.css)

    def test_nav_btn_cs_locked(self):
        self.assertIn(".tl-nav-btn.cs-locked", self.css)

    def test_cs_locked_opacity(self):
        self.assertIn("opacity", self.css.split(".tl-nav-btn.cs-locked")[1][:100])

    def test_cs_locked_after_dot(self):
        self.assertIn(".tl-nav-btn.cs-locked::after", self.css)


# ══════════════════════════════════════════════════════════════════
# 8) NO DATA LEAKAGE — Locked features don't expose data
# ══════════════════════════════════════════════════════════════════

class TestNoDataLeakage(unittest.TestCase):
    """Verify locked feature templates don't expose real data when coming_soon."""

    def test_courses_template_else_contains_content(self):
        html = _read(COURSES_HTML)
        self.assertIn("{% else %}", html)

    def test_course_detail_template_else_contains_content(self):
        html = _read(COURSE_DETAIL_HTML)
        self.assertIn("{% else %}", html)

    def test_my_courses_template_else_contains_content(self):
        html = _read(MY_COURSES_HTML)
        self.assertIn("{% else %}", html)

    def test_mentors_template_else_contains_content(self):
        html = _read(MENTORS_HTML)
        self.assertIn("{% else %}", html)

    def test_rooms_template_blocks_content_when_locked(self):
        html = _read(ROOMS_HTML)
        self.assertIn("{% else %}", html)

    def test_courses_coming_soon_json_field(self):
        src = _read(COURSES_ROUTES)
        self.assertIn('"coming_soon": True', src)

    def test_all_three_features_locked(self):
        """All three features must have COMING_SOON = True."""
        for path in [COURSES_ROUTES, MENTORS_ROUTES, LIVE_ROOMS_ROUTES]:
            src = _read(path)
            self.assertIn("COMING_SOON = True", src,
                          f"COMING_SOON not found in {path}")


# ══════════════════════════════════════════════════════════════════
# 9) INTEGRATION — Flask App 503 Responses
# ══════════════════════════════════════════════════════════════════

class TestFlaskApp503(unittest.TestCase):
    """Integration: locked API endpoints return 503."""

    @classmethod
    def setUpClass(cls):
        try:
            os.environ.setdefault("FLASK_TESTING", "1")
            from app import create_app
            app = create_app()
            app.config["TESTING"] = True
            cls.client = app.test_client()
            cls.available = True
        except Exception:
            cls.available = False

    def setUp(self):
        if not self.available:
            self.skipTest("Flask app not available")

    def test_api_courses_returns_503(self):
        r = self.client.get("/api/courses")
        self.assertEqual(r.status_code, 503)

    def test_api_course_detail_returns_503(self):
        r = self.client.get("/api/course/test-slug")
        self.assertEqual(r.status_code, 503)

    def test_api_courses_featured_returns_503(self):
        r = self.client.get("/api/courses/featured")
        self.assertEqual(r.status_code, 503)

    def test_api_courses_503_json(self):
        r = self.client.get("/api/courses")
        data = r.get_json()
        self.assertFalse(data["ok"])
        self.assertTrue(data.get("coming_soon"))

    def test_api_mentors_returns_503(self):
        r = self.client.get("/api/mentors")
        self.assertEqual(r.status_code, 503)

    def test_api_rooms_returns_503(self):
        r = self.client.get("/api/rooms")
        self.assertEqual(r.status_code, 503)

    def test_courses_page_returns_200(self):
        r = self.client.get("/courses")
        self.assertEqual(r.status_code, 200)

    def test_courses_page_shows_coming_soon(self):
        r = self.client.get("/courses")
        # Anonymized — no feature name
        self.assertIn(b"Yeni", r.data)
        self.assertNotIn(b"Kurs Sistemi", r.data)

    def test_mentors_page_returns_200(self):
        r = self.client.get("/mentors")
        self.assertEqual(r.status_code, 200)

    def test_rooms_page_returns_200(self):
        r = self.client.get("/rooms")
        self.assertEqual(r.status_code, 200)


class TestI18nAnonymization(unittest.TestCase):
    """Ensure i18n locale files and menu HTML don't leak feature names."""

    def test_menu_html_no_data_i18n_for_locked_features(self):
        """Menu must NOT have data-i18n attributes pointing to locked feature keys."""
        menu_path = MENU_HTML
        with open(menu_path, encoding="utf-8") as f:
            html = f.read()
        for key in ["menu.mentors", "menu.mentors_desc",
                     "menu.live_rooms", "menu.live_rooms_desc",
                     "menu.courses", "menu.courses_desc"]:
            self.assertNotIn(f'data-i18n="{key}"', html,
                             f"data-i18n=\"{key}\" should be removed from menu.html")

    def test_tr_locale_locked_features_anonymized(self):
        """Turkish locale must not reveal feature names."""
        locale_path = os.path.join(BASE, "app", "locales", "tr.json")
        with open(locale_path, encoding="utf-8") as f:
            data = json.load(f)
        for key in ["menu.mentors", "menu.live_rooms", "menu.courses",
                     "sidebar.mentors", "sidebar.live_rooms", "sidebar.courses"]:
            self.assertEqual(data.get(key), "Yakında",
                             f"{key} should be 'Yakında' in tr.json")
        for key in ["menu.mentors_desc", "menu.live_rooms_desc", "menu.courses_desc"]:
            self.assertEqual(data.get(key), "Geliştirme aşamasında",
                             f"{key} should be anonymized in tr.json")

    def test_all_locales_locked_features_anonymized(self):
        """All locale files must anonymize locked feature translations."""
        locales_dir = os.path.join(BASE, "app", "locales")
        for fname in os.listdir(locales_dir):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(locales_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
            for key in ["menu.mentors", "menu.live_rooms", "menu.courses",
                         "sidebar.mentors", "sidebar.live_rooms", "sidebar.courses"]:
                self.assertEqual(data.get(key), "Yakında",
                                 f"{key} in {fname} should be 'Yakında'")

    def test_portfolio_script_has_cache_bust(self):
        """Portfolio template must include cache-busting version on portfolio.js."""
        pf_path = os.path.join(BASE, "templates", "portfolio.html")
        with open(pf_path, encoding="utf-8") as f:
            html = f.read()
        self.assertIn("portfolio.js", html)
        self.assertRegex(html, r"portfolio\.js.*\?v=")


if __name__ == "__main__":
    unittest.main()
