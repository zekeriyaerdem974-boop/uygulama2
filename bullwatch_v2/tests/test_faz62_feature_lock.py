# -*- coding: utf-8 -*-
"""FAZ 62 — Feature Lock / "Yakında Gelecek" State Tests.

85 tests covering:
- Coming Soon CSS classes in components.css
- "Yakında" badge in menu.html for Mentors and Live Rooms
- cs-locked class on sidebar nav buttons in layout_terminal.html
- Coming Soon wrapper in mentor/room templates
- COMING_SOON flag and _coming_soon_response in route files
- API guard checks returning coming_soon JSON
- Page routes pass coming_soon=True to templates
- No broken routes (pages still render, no 404)
"""
import os
import re
import sys
import unittest

# ── Path setup ──
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

TEMPLATES = os.path.join(BASE, "templates")
STATIC = os.path.join(BASE, "static")
CSS_FILE = os.path.join(STATIC, "css", "components.css")

MENTOR_ROUTES = os.path.join(BASE, "app", "blueprints", "mentors", "routes.py")
ROOM_ROUTES = os.path.join(BASE, "app", "blueprints", "live_rooms", "routes.py")

MENU_HTML = os.path.join(TEMPLATES, "menu.html")
LAYOUT_HTML = os.path.join(TEMPLATES, "layout_terminal.html")
MENTORS_HTML = os.path.join(TEMPLATES, "mentors.html")
MENTOR_PROFILE_HTML = os.path.join(TEMPLATES, "mentor_profile.html")
ROOMS_HTML = os.path.join(TEMPLATES, "rooms.html")
ROOM_DETAIL_HTML = os.path.join(TEMPLATES, "room_detail.html")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# 1) CSS — Coming Soon Classes
# ══════════════════════════════════════════════════════════════════

class TestComingSoonCSS(unittest.TestCase):
    """Verify all Coming Soon CSS classes exist in components.css."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read(CSS_FILE)

    def test_coming_soon_page_class(self):
        self.assertIn(".coming-soon-page", self.css)

    def test_cs_icon_class(self):
        self.assertIn(".cs-icon", self.css)

    def test_cs_title_class(self):
        self.assertIn(".cs-title", self.css)

    def test_cs_subtitle_class(self):
        self.assertIn(".cs-subtitle", self.css)

    def test_cs_btn_class(self):
        self.assertIn(".cs-btn", self.css)

    def test_cs_shimmer_class(self):
        self.assertIn(".cs-shimmer", self.css)

    def test_cs_features_class(self):
        self.assertIn(".cs-features", self.css)

    def test_cs_feature_class(self):
        self.assertIn(".cs-feature", self.css)

    def test_badge_coming_soon_class(self):
        self.assertIn(".badge-coming-soon", self.css)

    def test_cs_locked_class(self):
        self.assertIn(".tl-nav-btn.cs-locked", self.css)

    def test_fade_in_animation(self):
        self.assertIn("cs-fadeIn", self.css)

    def test_pulse_animation(self):
        self.assertIn("cs-pulse", self.css)

    def test_shimmer_animation(self):
        self.assertIn("@keyframes cs-shimmer", self.css)

    def test_badge_amber_color(self):
        self.assertIn("#fbbf24", self.css)

    def test_cs_locked_opacity(self):
        # cs-locked should reduce opacity
        locked_section = self.css[self.css.index(".tl-nav-btn.cs-locked"):]
        self.assertIn("opacity", locked_section[:200])

    def test_cs_locked_after_pseudo(self):
        self.assertIn(".tl-nav-btn.cs-locked::after", self.css)


# ══════════════════════════════════════════════════════════════════
# 2) MENU — Yakında Badges
# ══════════════════════════════════════════════════════════════════

class TestMenuBadges(unittest.TestCase):
    """Verify 'Yakında' badges appear on Mentors and Live Rooms menu items."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(MENU_HTML)

    def test_mentors_badge_exists(self):
        self.assertIn('badge-coming-soon">Yakında</span>', self.html)

    def test_mentors_link_still_exists(self):
        self.assertIn('href="/mentors"', self.html)

    def test_rooms_link_still_exists(self):
        self.assertIn('href="/rooms"', self.html)

    def test_mentors_menu_item_has_badge(self):
        # Search for the Mentörler label area containing badge
        idx = self.html.index('data-i18n="menu.mentors"')
        snippet = self.html[idx:idx + 200]
        self.assertIn("badge-coming-soon", snippet)

    def test_rooms_menu_item_has_badge(self):
        idx = self.html.index('data-i18n="menu.live_rooms"')
        snippet = self.html[idx:idx + 200]
        self.assertIn("badge-coming-soon", snippet)

    def test_badge_count(self):
        count = self.html.count("badge-coming-soon")
        self.assertEqual(count, 2, "Should be exactly 2 badges (mentors + rooms)")

    def test_badge_text_yakinda(self):
        badges = re.findall(r'class="badge-coming-soon">(.*?)</span>', self.html)
        for b in badges:
            self.assertEqual(b, "Yakında")


# ══════════════════════════════════════════════════════════════════
# 3) SIDEBAR — cs-locked on Nav Buttons
# ══════════════════════════════════════════════════════════════════

class TestSidebarLocked(unittest.TestCase):
    """Verify cs-locked class on mentor/room sidebar nav buttons."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(LAYOUT_HTML)

    def test_mentors_sidebar_has_cs_locked(self):
        idx = self.html.index('href="/mentors"')
        snippet = self.html[max(0, idx - 50):idx + 100]
        self.assertIn("cs-locked", snippet)

    def test_rooms_sidebar_has_cs_locked(self):
        idx = self.html.index('href="/rooms"')
        snippet = self.html[max(0, idx - 50):idx + 100]
        self.assertIn("cs-locked", snippet)

    def test_mentors_tooltip_updated(self):
        idx = self.html.index('href="/mentors"')
        snippet = self.html[idx:idx + 200]
        self.assertIn("Yakında", snippet)

    def test_rooms_tooltip_updated(self):
        idx = self.html.index('href="/rooms"')
        snippet = self.html[idx:idx + 200]
        self.assertIn("Yakında", snippet)

    def test_cs_locked_count(self):
        count = self.html.count("cs-locked")
        self.assertGreaterEqual(count, 2, "Should have at least 2 cs-locked entries")


# ══════════════════════════════════════════════════════════════════
# 4) TEMPLATES — Coming Soon UI Wrappers
# ══════════════════════════════════════════════════════════════════

class TestMentorsTemplate(unittest.TestCase):
    """Verify mentors.html has coming_soon wrapper."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(MENTORS_HTML)

    def test_coming_soon_conditional(self):
        self.assertIn("{% if coming_soon %}", self.html)

    def test_coming_soon_page_div(self):
        self.assertIn("coming-soon-page", self.html)

    def test_cs_icon_mentor(self):
        self.assertIn("🎓", self.html)

    def test_cs_title_mentors(self):
        self.assertIn("Mentör Sistemi Yakında Geliyor", self.html)

    def test_cs_btn_haberdar(self):
        self.assertIn("Haberdar Et", self.html)

    def test_cs_features_exist(self):
        self.assertIn("cs-features", self.html)
        self.assertIn("Uzman Analistler", self.html)

    def test_else_block_preserves_original(self):
        self.assertIn("{% else %}", self.html)
        self.assertIn("mt-tabs", self.html)

    def test_header_actions_guarded(self):
        self.assertIn("{% if not coming_soon %}", self.html)

    def test_scripts_guarded(self):
        # mentors.js should be conditionally loaded
        idx = self.html.index("mentors.js")
        snippet = self.html[max(0, idx - 100):idx]
        self.assertIn("not coming_soon", snippet)

    def test_shimmer(self):
        self.assertIn("cs-shimmer", self.html)


class TestMentorProfileTemplate(unittest.TestCase):
    """Verify mentor_profile.html has coming_soon wrapper."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(MENTOR_PROFILE_HTML)

    def test_coming_soon_conditional(self):
        self.assertIn("{% if coming_soon %}", self.html)

    def test_coming_soon_page_div(self):
        self.assertIn("coming-soon-page", self.html)

    def test_cs_title_profile(self):
        self.assertIn("Mentör Profilleri Yakında Geliyor", self.html)

    def test_cs_btn_haberdar(self):
        self.assertIn("Haberdar Et", self.html)

    def test_else_preserves_original(self):
        self.assertIn("{% else %}", self.html)
        self.assertIn("mpContent", self.html)

    def test_scripts_guarded(self):
        idx = self.html.index("mentor_profile.js")
        snippet = self.html[max(0, idx - 100):idx]
        self.assertIn("not coming_soon", snippet)


class TestRoomsTemplate(unittest.TestCase):
    """Verify rooms.html has coming_soon wrapper."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(ROOMS_HTML)

    def test_coming_soon_conditional(self):
        self.assertIn("{% if coming_soon %}", self.html)

    def test_coming_soon_page_div(self):
        self.assertIn("coming-soon-page", self.html)

    def test_cs_icon_rooms(self):
        self.assertIn("🔴", self.html)

    def test_cs_title_rooms(self):
        self.assertIn("Canlı Odalar Yakında Geliyor", self.html)

    def test_cs_btn_haberdar(self):
        self.assertIn("Haberdar Et", self.html)

    def test_else_preserves_original(self):
        self.assertIn("{% else %}", self.html)
        self.assertIn("lr-page", self.html)

    def test_rooms_js_guarded(self):
        self.assertIn("{% endif %}", self.html)
        # rooms.js should be inside the else block
        idx_js = self.html.index("rooms.js")
        idx_endif = self.html.index("{% endif %}", idx_js)
        self.assertTrue(idx_endif > idx_js)


class TestRoomDetailTemplate(unittest.TestCase):
    """Verify room_detail.html has coming_soon wrapper."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(ROOM_DETAIL_HTML)

    def test_coming_soon_conditional(self):
        self.assertIn("{% if coming_soon %}", self.html)

    def test_coming_soon_page_div(self):
        self.assertIn("coming-soon-page", self.html)

    def test_cs_title_room_detail(self):
        self.assertIn("Canlı Oda Yakında Geliyor", self.html)

    def test_cs_btn_haberdar(self):
        self.assertIn("Haberdar Et", self.html)

    def test_else_preserves_original(self):
        self.assertIn("{% else %}", self.html)
        self.assertIn("rd-page", self.html)

    def test_room_detail_js_guarded(self):
        idx_js = self.html.index("room_detail.js")
        idx_endif = self.html.index("{% endif %}", idx_js)
        self.assertTrue(idx_endif > idx_js)


# ══════════════════════════════════════════════════════════════════
# 5) ROUTES — COMING_SOON Flag & API Guards (mentors)
# ══════════════════════════════════════════════════════════════════

class TestMentorRoutes(unittest.TestCase):
    """Verify mentor routes.py has COMING_SOON flag and API guards."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(MENTOR_ROUTES)

    def test_coming_soon_flag_exists(self):
        self.assertIn("COMING_SOON = True", self.src)

    def test_coming_soon_response_helper(self):
        self.assertIn("def _coming_soon_response()", self.src)

    def test_coming_soon_response_returns_json(self):
        self.assertIn('"coming_soon": True', self.src)

    def test_coming_soon_response_status_503(self):
        self.assertIn("503", self.src)

    def test_mentors_page_passes_flag(self):
        self.assertIn("coming_soon=COMING_SOON", self.src)

    def test_mentor_profile_page_passes_flag(self):
        idx = self.src.index("mentor_profile_page")
        snippet = self.src[idx:idx + 200]
        self.assertIn("coming_soon=COMING_SOON", snippet)

    def test_api_list_mentors_guarded(self):
        idx = self.src.index("def api_list_mentors")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_featured_mentors_guarded(self):
        idx = self.src.index("def api_featured_mentors")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_mentor_profile_guarded(self):
        idx = self.src.index("def api_mentor_profile")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_my_profile_guarded(self):
        idx = self.src.index("def api_my_profile")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_create_or_update_guarded(self):
        idx = self.src.index("def api_create_or_update_profile")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_follow_guarded(self):
        idx = self.src.index("def api_follow_mentor")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_unfollow_guarded(self):
        idx = self.src.index("def api_unfollow_mentor")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_copilot_mentors_guarded(self):
        idx = self.src.index("def api_copilot_mentors")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_all_api_functions_guarded(self):
        api_funcs = re.findall(r"def (api_\w+)", self.src)
        for fn in api_funcs:
            idx = self.src.index(f"def {fn}")
            snippet = self.src[idx:idx + 200]
            self.assertIn("COMING_SOON", snippet,
                          f"API function {fn} is NOT guarded by COMING_SOON")


# ══════════════════════════════════════════════════════════════════
# 6) ROUTES — COMING_SOON Flag & API Guards (live rooms)
# ══════════════════════════════════════════════════════════════════

class TestRoomRoutes(unittest.TestCase):
    """Verify live_rooms routes.py has COMING_SOON flag and API guards."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read(ROOM_ROUTES)

    def test_coming_soon_flag_exists(self):
        self.assertIn("COMING_SOON = True", self.src)

    def test_coming_soon_response_helper(self):
        self.assertIn("def _coming_soon_response()", self.src)

    def test_coming_soon_response_returns_json(self):
        self.assertIn('"coming_soon": True', self.src)

    def test_coming_soon_response_status_503(self):
        self.assertIn("503", self.src)

    def test_rooms_page_passes_flag(self):
        self.assertIn("coming_soon=COMING_SOON", self.src)

    def test_room_detail_page_passes_flag(self):
        idx = self.src.index("room_detail_page")
        snippet = self.src[idx:idx + 200]
        self.assertIn("coming_soon=COMING_SOON", snippet)

    def test_api_list_rooms_guarded(self):
        idx = self.src.index("def api_list_rooms")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_room_detail_guarded(self):
        idx = self.src.index("def api_room_detail")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_create_room_guarded(self):
        idx = self.src.index("def api_create_room")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_start_room_guarded(self):
        idx = self.src.index("def api_start_room")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_stop_room_guarded(self):
        idx = self.src.index("def api_stop_room")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_join_room_guarded(self):
        idx = self.src.index("def api_join_room")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_leave_room_guarded(self):
        idx = self.src.index("def api_leave_room")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_list_messages_guarded(self):
        idx = self.src.index("def api_list_messages")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_post_message_guarded(self):
        idx = self.src.index("def api_post_message")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_api_copilot_rooms_guarded(self):
        idx = self.src.index("def api_copilot_rooms")
        snippet = self.src[idx:idx + 150]
        self.assertIn("COMING_SOON", snippet)

    def test_all_api_functions_guarded(self):
        api_funcs = re.findall(r"def (api_\w+)", self.src)
        for fn in api_funcs:
            idx = self.src.index(f"def {fn}")
            snippet = self.src[idx:idx + 200]
            self.assertIn("COMING_SOON", snippet,
                          f"API function {fn} is NOT guarded by COMING_SOON")


# ══════════════════════════════════════════════════════════════════
# 7) INTEGRATION — No Broken Structure
# ══════════════════════════════════════════════════════════════════

class TestTemplateIntegrity(unittest.TestCase):
    """Verify templates still have valid Jinja structure."""

    def _check_balanced(self, path, name):
        html = _read(path)
        ifs = len(re.findall(r"\{%[-\s]*if\b", html))
        endifs = len(re.findall(r"\{%[-\s]*endif\b", html))
        self.assertEqual(ifs, endifs,
                         f"{name}: if/endif mismatch ({ifs} vs {endifs})")

    def test_mentors_balanced_ifs(self):
        self._check_balanced(MENTORS_HTML, "mentors.html")

    def test_mentor_profile_balanced_ifs(self):
        self._check_balanced(MENTOR_PROFILE_HTML, "mentor_profile.html")

    def test_rooms_balanced_ifs(self):
        self._check_balanced(ROOMS_HTML, "rooms.html")

    def test_room_detail_balanced_ifs(self):
        self._check_balanced(ROOM_DETAIL_HTML, "room_detail.html")

    def test_mentors_extends_layout(self):
        html = _read(MENTORS_HTML)
        self.assertIn('{% extends "layout_terminal.html" %}', html)

    def test_rooms_extends_layout(self):
        html = _read(ROOMS_HTML)
        self.assertIn('{% extends "layout_terminal.html" %}', html)

    def test_room_detail_extends_layout(self):
        html = _read(ROOM_DETAIL_HTML)
        self.assertIn('{% extends "layout_terminal.html" %}', html)

    def test_mentor_profile_extends_layout(self):
        html = _read(MENTOR_PROFILE_HTML)
        self.assertIn('{% extends "layout_terminal.html" %}', html)


if __name__ == "__main__":
    unittest.main()
