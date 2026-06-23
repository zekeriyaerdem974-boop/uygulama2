"""
ZKR Analiz Pro — FAZ 47 Pro UI Design System & Full Interface Refactor Tests
Covers: design tokens, design components, design layout CSS files,
        layout_terminal.html refactor (topbar, sidebar, global search),
        page template integrations (topbar_title blocks),
        backward compatibility with legacy classes,
        CSS custom properties, typography, animations.
"""

import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)


def _read(rel_path):
    with open(os.path.join(BASE, rel_path), "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════
# 1. Design Tokens CSS — File Existence & Token Definitions
# ═══════════════════════════════════════════════════════════════
class TestDesignTokensFile(unittest.TestCase):
    """Verify design_tokens.css exists and contains core tokens."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_tokens.css")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/design/design_tokens.css")))

    def test_has_root_selector(self):
        self.assertIn(":root", self.css)

    def test_bg_primary_token(self):
        self.assertIn("--bg-primary", self.css)

    def test_accent_token(self):
        self.assertIn("--accent", self.css)

    def test_accent_value_is_blue(self):
        match = re.search(r"--accent\s*:\s*([^;]+);", self.css)
        self.assertIsNotNone(match)
        self.assertIn("#5B8CFF", match.group(1).upper().replace(" ", "").replace("5b8cff", "5B8CFF"))

    def test_green_token(self):
        self.assertIn("--green", self.css)

    def test_red_token(self):
        self.assertIn("--red", self.css)

    def test_text_primary_token(self):
        self.assertIn("--text-primary", self.css)

    def test_text_secondary_token(self):
        self.assertIn("--text-secondary", self.css)

    def test_text_dim_token(self):
        self.assertIn("--text-dim", self.css)

    def test_spacing_scale(self):
        for i in [1, 2, 3, 4, 5, 6, 8]:
            self.assertIn(f"--space-{i}", self.css)

    def test_shadow_scale(self):
        self.assertIn("--shadow-sm", self.css)
        self.assertIn("--shadow-elevated", self.css)

    def test_radius_tokens(self):
        self.assertIn("--radius-sm", self.css)
        self.assertIn("--radius-md", self.css)
        self.assertIn("--radius-lg", self.css)

    def test_z_index_scale(self):
        self.assertIn("--z-sidebar", self.css)
        self.assertIn("--z-modal", self.css)
        self.assertIn("--z-tooltip", self.css)

    def test_transition_tokens(self):
        self.assertIn("--transition-fast", self.css)

    def test_border_token(self):
        self.assertIn("--border", self.css)


class TestDesignTokensTypography(unittest.TestCase):
    """Typography classes in design_tokens.css."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_tokens.css")

    def test_t_h1_class(self):
        self.assertIn(".t-h1", self.css)

    def test_t_h2_class(self):
        self.assertIn(".t-h2", self.css)

    def test_t_h3_class(self):
        self.assertIn(".t-h3", self.css)

    def test_t_body_class(self):
        self.assertIn(".t-body", self.css)

    def test_t_caption_class(self):
        self.assertIn(".t-caption", self.css)

    def test_t_mono_class(self):
        self.assertIn(".t-mono", self.css)

    def test_t_label_class(self):
        self.assertIn(".t-label", self.css)


class TestDesignTokensAnimations(unittest.TestCase):
    """Animation keyframes in design_tokens.css."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_tokens.css")

    def test_fadeIn_keyframe(self):
        self.assertIn("@keyframes fadeIn", self.css)

    def test_fadeUp_keyframe(self):
        self.assertIn("@keyframes fadeUp", self.css)

    def test_scaleIn_keyframe(self):
        self.assertIn("@keyframes scaleIn", self.css)

    def test_shimmer_keyframe(self):
        self.assertIn("@keyframes shimmer", self.css)

    def test_pulse_keyframe(self):
        self.assertIn("@keyframes pulse", self.css)


class TestDesignTokensBackwardCompat(unittest.TestCase):
    """Backward compatibility aliases for old ds-* classes."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_tokens.css")

    def test_ds_h1_alias(self):
        self.assertIn(".ds-h1", self.css)

    def test_ds_body_alias(self):
        self.assertIn(".ds-body", self.css)

    def test_ds_glass_alias(self):
        self.assertIn(".ds-glass", self.css)

    def test_ds_fade_up_alias(self):
        self.assertIn(".ds-fade", self.css)

    def test_ds_mono_alias(self):
        self.assertIn(".ds-mono", self.css)


# ═══════════════════════════════════════════════════════════════
# 2. Design Components CSS — Component Library
# ═══════════════════════════════════════════════════════════════
class TestDesignComponentsFile(unittest.TestCase):
    """Verify design_components.css exists and has core components."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_components.css")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/design/design_components.css")))

    def test_pro_card(self):
        self.assertIn(".pro-card", self.css)

    def test_pro_card_header(self):
        self.assertIn(".pro-card-header", self.css)

    def test_pro_card_body(self):
        self.assertIn(".pro-card-body", self.css)

    def test_pro_stat_card(self):
        self.assertIn(".pro-stat-card", self.css)

    def test_pro_btn_primary(self):
        self.assertIn(".pro-btn-primary", self.css)

    def test_pro_btn_ghost(self):
        self.assertIn(".pro-btn-ghost", self.css)

    def test_pro_badge_accent(self):
        self.assertIn(".pro-badge-accent", self.css)

    def test_pro_badge_success(self):
        self.assertIn(".pro-badge-success", self.css)

    def test_pro_badge_danger(self):
        self.assertIn(".pro-badge-danger", self.css)

    def test_pro_chip(self):
        self.assertIn(".pro-chip", self.css)

    def test_pro_input(self):
        self.assertIn(".pro-input", self.css)

    def test_pro_tabs(self):
        self.assertIn(".pro-tabs", self.css)

    def test_pro_table(self):
        self.assertIn(".pro-table", self.css)

    def test_pro_modal(self):
        self.assertIn(".pro-modal", self.css)

    def test_pro_dropdown(self):
        self.assertIn(".pro-dropdown", self.css)

    def test_pro_toast(self):
        self.assertIn(".pro-toast", self.css)

    def test_pro_tooltip(self):
        self.assertIn(".pro-tooltip", self.css)

    def test_pro_progress(self):
        self.assertIn(".pro-progress", self.css)

    def test_pro_search(self):
        self.assertIn(".pro-search", self.css)

    def test_pro_avatar(self):
        self.assertIn(".pro-avatar", self.css)

    def test_pro_grid_classes(self):
        for n in [2, 3, 4]:
            self.assertIn(f".pro-grid-{n}", self.css)

    def test_hover_lift(self):
        self.assertIn(".pro-card.interactive:hover", self.css)

    def test_trend_indicator(self):
        self.assertIn(".trend-up", self.css)
        self.assertIn(".trend-down", self.css)

    def test_empty_state(self):
        self.assertIn(".empty-state", self.css)

    def test_page_header(self):
        self.assertIn(".page-header", self.css)


# ═══════════════════════════════════════════════════════════════
# 3. Design Layout CSS — App Shell Structure
# ═══════════════════════════════════════════════════════════════
class TestDesignLayoutFile(unittest.TestCase):
    """Verify design_layout.css exists and has layout components."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_layout.css")

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(BASE, "static/design/design_layout.css")))

    def test_app_shell(self):
        self.assertIn(".app-shell", self.css)

    def test_sidebar(self):
        self.assertIn(".sidebar", self.css)

    def test_tl_sidebar_compat(self):
        self.assertIn(".tl-sidebar", self.css)

    def test_topbar(self):
        self.assertIn(".topbar", self.css)

    def test_main_content(self):
        self.assertIn(".main-content", self.css)

    def test_sidebar_expanded_state(self):
        self.assertIn(".sidebar.expanded", self.css)
        self.assertIn(".tl-sidebar.expanded", self.css)

    def test_sidebar_toggle_button(self):
        self.assertIn(".sidebar-toggle", self.css)

    def test_nav_section_label(self):
        self.assertIn(".nav-section-label", self.css)

    def test_nav_btn(self):
        self.assertIn(".nav-btn", self.css)

    def test_tl_nav_btn_compat(self):
        self.assertIn(".tl-nav-btn", self.css)

    def test_nav_active_indicator(self):
        self.assertIn(".tl-nav-btn.active::after", self.css)

    def test_tooltip_on_hover(self):
        self.assertIn("data-tooltip", self.css)

    def test_topbar_glassmorphism(self):
        self.assertIn("backdrop-filter", self.css)

    def test_sidebar_brand_text(self):
        self.assertIn(".sidebar-brand-text", self.css)

    def test_sidebar_variables(self):
        self.assertIn("--sidebar-width", self.css)
        self.assertIn("--sidebar-expanded", self.css)

    def test_responsive_breakpoints(self):
        self.assertIn("1024px", self.css)

    def test_mobile_sidebar(self):
        self.assertIn(".mobile-open", self.css)

    def test_bottombar(self):
        self.assertIn(".pro-bottombar", self.css)

    def test_right_panel(self):
        self.assertIn(".right-panel", self.css)


# ═══════════════════════════════════════════════════════════════
# 4. Layout Template — Topbar & Sidebar Integration
# ═══════════════════════════════════════════════════════════════
class TestLayoutTemplate(unittest.TestCase):
    """Verify layout_terminal.html has the new design system integrated."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read("templates/layout_terminal.html")

    def test_design_tokens_css_import(self):
        self.assertIn("design/design_tokens.css", self.html)

    def test_design_components_css_import(self):
        self.assertIn("design/design_components.css", self.html)

    def test_design_layout_css_import(self):
        self.assertIn("design/design_layout.css", self.html)

    def test_v47_cache_buster(self):
        self.assertIn("?v=47", self.html)

    def test_space_grotesk_font(self):
        self.assertIn("Space+Grotesk", self.html)

    def test_theme_color_dark(self):
        self.assertIn("#06080D", self.html)

    def test_topbar_element(self):
        self.assertIn('class="topbar"', self.html)

    def test_topbar_id(self):
        self.assertIn('id="proTopbar"', self.html)

    def test_global_search(self):
        self.assertIn('id="globalSearch"', self.html)

    def test_search_shortcut_badge(self):
        self.assertIn("⌘K", self.html)

    def test_market_status_indicator(self):
        self.assertIn("market-status", self.html)

    def test_topbar_notification_btn(self):
        self.assertIn('id="topbarNotifBtn"', self.html)

    def test_topbar_avatar_btn(self):
        self.assertIn('id="topbarUserBtn"', self.html)

    def test_topbar_title_block(self):
        self.assertIn("{% block topbar_title %}", self.html)

    def test_topbar_left_block(self):
        self.assertIn("{% block topbar_left %}", self.html)

    def test_topbar_right_block(self):
        self.assertIn("{% block topbar_right %}", self.html)

    def test_sidebar_toggle_button(self):
        self.assertIn('id="sidebarToggle"', self.html)

    def test_sidebar_brand_text(self):
        self.assertIn("sidebar-brand-text", self.html)

    def test_nav_section_labels(self):
        self.assertIn("nav-section-label", self.html)

    def test_sidebar_expand_js(self):
        self.assertIn("sidebarToggle", self.html)
        self.assertIn("sidebar.classList.toggle('expanded')", self.html)

    def test_cmd_k_shortcut_js(self):
        self.assertIn("e.key === 'k'", self.html)

    def test_button_ripple_js(self):
        self.assertIn("ripple", self.html)

    def test_main_content_wrapper(self):
        self.assertIn('class="main-content"', self.html)


# ═══════════════════════════════════════════════════════════════
# 5. Page Templates — topbar_title Integration
# ═══════════════════════════════════════════════════════════════
class TestPageTopbarTitles(unittest.TestCase):
    """Verify all page templates define topbar_title block."""

    PAGES = {
        "templates/discover.html": "Dashboard",
        "templates/trade.html": "Trade",
        "templates/portfolio.html": "Portfolio",
        "templates/opportunities.html": "Opportunities",
        "templates/activity.html": "Activity",
        "templates/feed.html": "Feed",
        "templates/mentors.html": "Mentors",
        "templates/courses.html": "Courses",
        "templates/rooms.html": "Live Rooms",
        "templates/marketplace.html": "Marketplace",
        "templates/alerts.html": "Alerts",
        "templates/screener.html": "Screener",
        "templates/invite.html": "Invite & Earn",
        "templates/simulator.html": "Simulator",
        "templates/backtest.html": "Backtest",
        "templates/chat.html": "AI Copilot",
        "templates/leaderboard.html": "Leaderboard",
        "templates/market_radar.html": "Market Radar",
    }

    def test_topbar_title_blocks(self):
        for path, expected_title in self.PAGES.items():
            full_path = os.path.join(BASE, path)
            self.assertTrue(os.path.isfile(full_path), f"{path} not found")
            content = _read(path)
            self.assertIn("{% block topbar_title %}", content,
                          f"{path} missing topbar_title block")
            self.assertIn(expected_title, content,
                          f"{path} missing expected title '{expected_title}'")


# ═══════════════════════════════════════════════════════════════
# 6. Design System Directory Structure
# ═══════════════════════════════════════════════════════════════
class TestDesignSystemStructure(unittest.TestCase):
    """Verify static/design/ directory structure."""

    def test_design_directory_exists(self):
        self.assertTrue(os.path.isdir(os.path.join(BASE, "static/design")))

    def test_three_design_files(self):
        design_dir = os.path.join(BASE, "static/design")
        files = os.listdir(design_dir)
        self.assertIn("design_tokens.css", files)
        self.assertIn("design_components.css", files)
        self.assertIn("design_layout.css", files)

    def test_tokens_file_size(self):
        path = os.path.join(BASE, "static/design/design_tokens.css")
        size = os.path.getsize(path)
        self.assertGreater(size, 3000, "design_tokens.css too small")

    def test_components_file_size(self):
        path = os.path.join(BASE, "static/design/design_components.css")
        size = os.path.getsize(path)
        self.assertGreater(size, 5000, "design_components.css too small")

    def test_layout_file_size(self):
        path = os.path.join(BASE, "static/design/design_layout.css")
        size = os.path.getsize(path)
        self.assertGreater(size, 3000, "design_layout.css too small")


# ═══════════════════════════════════════════════════════════════
# 7. CSS Custom Properties Consistency
# ═══════════════════════════════════════════════════════════════
class TestCSSPropertiesConsistency(unittest.TestCase):
    """Tokens defined in design_tokens are used in components/layout."""

    @classmethod
    def setUpClass(cls):
        cls.tokens = _read("static/design/design_tokens.css")
        cls.components = _read("static/design/design_components.css")
        cls.layout = _read("static/design/design_layout.css")

    def test_accent_used_in_components(self):
        self.assertIn("var(--accent)", self.components)

    def test_bg_primary_used_in_layout(self):
        self.assertIn("var(--bg-primary)", self.layout)

    def test_border_used_in_components(self):
        self.assertIn("var(--border)", self.components)

    def test_radius_used_in_components(self):
        self.assertIn("var(--radius-md)", self.components)

    def test_shadow_used_in_components(self):
        self.assertIn("var(--shadow", self.components)

    def test_transition_used_in_layout(self):
        self.assertIn("var(--transition-fast)", self.layout)

    def test_z_index_used_in_layout(self):
        self.assertIn("var(--z-sidebar)", self.layout)


# ═══════════════════════════════════════════════════════════════
# 8. Sidebar Section Labels
# ═══════════════════════════════════════════════════════════════
class TestSidebarSectionLabels(unittest.TestCase):
    """Sidebar has section labels for expanded mode."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read("templates/layout_terminal.html")

    def test_markets_label(self):
        self.assertIn("Markets", self.html)

    def test_trading_label(self):
        self.assertIn("Trading", self.html)

    def test_social_label(self):
        self.assertIn("Social", self.html)

    def test_ai_tools_label(self):
        self.assertIn("AI Tools", self.html)

    def test_learn_label(self):
        self.assertIn("Learn", self.html)

    def test_section_labels_use_class(self):
        count = self.html.count("nav-section-label")
        self.assertGreaterEqual(count, 5, "Expected at least 5 nav-section-label elements")


# ═══════════════════════════════════════════════════════════════
# 9. Legacy CSS Compatibility
# ═══════════════════════════════════════════════════════════════
class TestLegacyCSSCompat(unittest.TestCase):
    """Legacy CSS files still loaded for backward compat."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read("templates/layout_terminal.html")

    def test_legacy_design_system_css(self):
        self.assertIn("css/design_system.css", self.html)

    def test_legacy_layout_css(self):
        self.assertIn("css/layout.css", self.html)

    def test_legacy_components_css(self):
        self.assertIn("css/components.css", self.html)

    def test_legacy_terminal_css(self):
        self.assertIn("css/terminal.css", self.html)

    def test_new_css_before_legacy(self):
        new_pos = self.html.index("design/design_tokens.css")
        legacy_pos = self.html.index("css/design_system.css")
        self.assertLess(new_pos, legacy_pos, "New design CSS should load before legacy")


# ═══════════════════════════════════════════════════════════════
# 10. Component CSS Features
# ═══════════════════════════════════════════════════════════════
class TestComponentCSSFeatures(unittest.TestCase):
    """Specific component styling features."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read("static/design/design_components.css")

    def test_card_glass_effect(self):
        self.assertIn("backdrop-filter", self.css)

    def test_button_ripple(self):
        self.assertIn(".ripple", self.css)

    def test_stat_card_change_indicator(self):
        self.assertIn(".stat-change", self.css)

    def test_badge_neutral_variant(self):
        self.assertIn(".pro-badge-neutral", self.css)

    def test_chip_active_state(self):
        self.assertIn(".pro-chip.active", self.css)

    def test_table_sticky_header(self):
        self.assertIn("sticky", self.css)

    def test_modal_overlay(self):
        self.assertIn(".pro-modal-overlay", self.css)

    def test_toast_variants(self):
        self.assertIn(".pro-toast.success", self.css)
        self.assertIn(".pro-toast.error", self.css)

    def test_grid_auto_fill(self):
        self.assertIn("auto-fill", self.css)

    def test_responsive_grid(self):
        self.assertIn("@media", self.css)

    def test_price_flash_animation(self):
        self.assertIn(".price-flash-up", self.css)
        self.assertIn(".price-flash-down", self.css)

    def test_market_status_component(self):
        self.assertIn(".market-status", self.css)

    def test_allocation_bar(self):
        self.assertIn(".allocation-bar", self.css)

    def test_pro_kpi_row(self):
        self.assertIn(".pro-kpi-row", self.css)


# ═══════════════════════════════════════════════════════════════
# 11. Live HTTP Endpoint Tests (require server on port 34000)
# ═══════════════════════════════════════════════════════════════
LIVE_TEST = os.environ.get("ZKR_ANALIZ_LIVE_TEST", "0") == "1"


@unittest.skipUnless(LIVE_TEST, "Set ZKR_ANALIZ_LIVE_TEST=1 to run live tests")
class TestLiveDesignAssets(unittest.TestCase):
    """Verify design CSS files are served correctly via HTTP."""

    def test_design_tokens_css_served(self):
        import requests
        r = requests.get(f"{BASE_URL}/static/design/design_tokens.css", timeout=5)
        self.assertEqual(r.status_code, 200)
        self.assertIn("--bg-primary", r.text)

    def test_design_components_css_served(self):
        import requests
        r = requests.get(f"{BASE_URL}/static/design/design_components.css", timeout=5)
        self.assertEqual(r.status_code, 200)
        self.assertIn(".pro-card", r.text)

    def test_design_layout_css_served(self):
        import requests
        r = requests.get(f"{BASE_URL}/static/design/design_layout.css", timeout=5)
        self.assertEqual(r.status_code, 200)
        self.assertIn(".topbar", r.text)


if __name__ == "__main__":
    unittest.main()
