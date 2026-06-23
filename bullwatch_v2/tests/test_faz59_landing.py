# -*- coding: utf-8 -*-
"""FAZ 59 — Landing Page / Conversion Funnel Tests.

Validates:
  01. File — landing.html exists
  02. File — landing.css exists
  03. File — landing.js exists
  04. Route — /landing registered via onboarding_bp
  05. HTML — Turkish language (lang="tr")
  06. HTML — correct title
  07. HTML — meta description Turkish
  08. HTML — links landing.css
  09. HTML — links landing.js
  10. Hero — headline "Kripto ve Borsayı"
  11. Hero — sub "AI destekli analiz"
  12. Hero — CTA "Ücretsiz Başla"
  13. Hero — secondary CTA "Demo'yu Gör"
  14. Hero — social proof trust numbers
  15. Problem — section exists
  16. Problem — text "Farklı uygulamalar"
  17. Solution — text "Tek platformda"
  18. Features — AI Market Agent
  19. Features — Screener (Multi-Market)
  20. Features — Trading Simulator
  21. Features — Portfolio Tracking
  22. Features — Smart Alerts
  23. Features — Strateji Builder
  24. Proof — social proof bar exists
  25. Proof — kullanıcı sayısı
  26. Proof — başarı oranı
  27. Pricing — Free plan ₺0
  28. Pricing — Pro plan ₺149
  29. Pricing — Pro+ plan ₺299
  30. Pricing — Pro highlighted (featured)
  31. Pricing — "Hemen Başla" button
  32. CTA — final section exists
  33. CTA — "Bugün Başla" text
  34. CTA — "Kayıt Ol" button
  35. Nav — Logo
  36. Nav — Özellikler link
  37. Nav — Fiyatlar link
  38. Nav — Giriş link
  39. Nav — Kayıt Ol button
  40. Flow — /register links present
  41. Flow — /discover links present
  42. Flow — /login link present
  43. Footer — 2026 copyright
  44. CSS — ln-hero styles
  45. CSS — ln-features styles
  46. CSS — ln-pricing styles
  47. CSS — ln-proof styles
  48. CSS — ln-ps (problem/solution) styles
  49. CSS — ln-final-cta styles
  50. CSS — responsive breakpoints
  51. CSS — ln-fade-up animation
  52. CSS — ln-nav scrolled state
  53. JS — scroll handler for nav
  54. JS — IntersectionObserver for fade
  55. JS — counter animation
  56. JS — analytics tracking
  57. JS — smooth scroll
  58. JS — mobile menu toggle
  59. API — GET /landing returns 200
  60. API — response contains hero headline
  61. Design — dark background (#050608)
  62. Design — Inter font
  63. Design — accent color #3B82F6
  64. Design — green color #16C784
  65. No — English "Get Started" removed
  66. No — old $19/mo pricing removed
  67. No — "Enterprise" plan removed
  68. SEO — og:title meta tag
  69. SEO — og:description meta tag
  70. Conversion — multiple register CTAs
"""
import os
import sys
import unittest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)


def _get_flask_app():
    from legacy_monolith import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-faz59"
    return app


class TestFileExistence(unittest.TestCase):
    """Tests 01-03: Files exist."""

    def test_01_landing_html_exists(self):
        self.assertTrue(os.path.isfile(
            os.path.join(_PROJECT, "templates", "landing.html")))

    def test_02_landing_css_exists(self):
        self.assertTrue(os.path.isfile(
            os.path.join(_PROJECT, "static", "css", "landing.css")))

    def test_03_landing_js_exists(self):
        self.assertTrue(os.path.isfile(
            os.path.join(_PROJECT, "static", "js", "landing.js")))


class TestRoute(unittest.TestCase):
    """Test 04: Route registration."""

    def test_04_landing_route_in_onboarding(self):
        path = os.path.join(_PROJECT, "app", "blueprints", "onboarding", "routes.py")
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("/landing", src)
        self.assertIn("landing.html", src)


class TestHTMLStructure(unittest.TestCase):
    """Tests 05-14: HTML head & hero."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_05_turkish_language(self):
        self.assertIn('lang="tr"', self.html)

    def test_06_correct_title(self):
        self.assertIn("Kripto ve Borsayı Tek Ekranda", self.html)

    def test_07_meta_description_turkish(self):
        self.assertIn("AI destekli analiz", self.html)

    def test_08_links_landing_css(self):
        self.assertIn("landing.css", self.html)

    def test_09_links_landing_js(self):
        self.assertIn("landing.js", self.html)

    def test_10_hero_headline(self):
        self.assertIn("Kripto ve Borsayı", self.html)
        self.assertIn("Tek Ekranda Yönetin", self.html)

    def test_11_hero_sub(self):
        self.assertIn("AI destekli analiz", self.html)
        self.assertIn("profesyonel trading araçları", self.html)

    def test_12_hero_cta_ucretsiz(self):
        self.assertIn("Ücretsiz Başla", self.html)

    def test_13_hero_secondary_cta(self):
        self.assertIn("Demo'yu Gör", self.html)

    def test_14_hero_trust_numbers(self):
        self.assertIn("data-count", self.html)
        self.assertIn("Aktif Kullanıcı", self.html)


class TestProblemSolution(unittest.TestCase):
    """Tests 15-17: Problem/solution section."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_15_problem_section_exists(self):
        self.assertIn("ln-ps-problem", self.html)
        self.assertIn("ln-ps-solution", self.html)

    def test_16_problem_text(self):
        self.assertIn("Farklı uygulamalar", self.html)
        self.assertIn("karmaşık grafik", self.html)

    def test_17_solution_text(self):
        self.assertIn("Tek platformda", self.html)
        self.assertIn("AI", self.html)


class TestFeatures(unittest.TestCase):
    """Tests 18-23: Feature blocks."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_18_ai_market_agent(self):
        self.assertIn("AI Market Agent", self.html)

    def test_19_screener(self):
        self.assertIn("Screener", self.html)

    def test_20_trading_simulator(self):
        self.assertIn("Trading Simulator", self.html)

    def test_21_portfolio_tracking(self):
        self.assertIn("Portfolio Tracking", self.html)

    def test_22_smart_alerts(self):
        self.assertIn("Smart Alerts", self.html)

    def test_23_strateji_builder(self):
        self.assertIn("Strateji Builder", self.html)


class TestSocialProof(unittest.TestCase):
    """Tests 24-26: Social proof."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_24_proof_bar_exists(self):
        self.assertIn("ln-proof", self.html)

    def test_25_user_count(self):
        self.assertIn("12500", self.html)
        self.assertIn("Aktif Kullanıcı", self.html)

    def test_26_success_rate(self):
        self.assertIn("Başarı Oranı", self.html)


class TestPricing(unittest.TestCase):
    """Tests 27-31: Pricing section."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_27_free_plan(self):
        self.assertIn(">Free<", self.html)
        self.assertIn(">0<", self.html)

    def test_28_pro_plan_149(self):
        self.assertIn(">Pro<", self.html)
        self.assertIn("149", self.html)

    def test_29_pro_plus_plan_299(self):
        self.assertIn(">Pro+<", self.html)
        self.assertIn("299", self.html)

    def test_30_pro_highlighted(self):
        self.assertIn("featured", self.html)
        self.assertIn("EN POPÜLER", self.html)

    def test_31_hemen_basla_button(self):
        self.assertIn("Hemen Başla", self.html)


class TestCTA(unittest.TestCase):
    """Tests 32-34: Final CTA section."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_32_final_cta_section(self):
        self.assertIn("ln-final-cta", self.html)

    def test_33_bugun_basla(self):
        self.assertIn("Bugün Başla", self.html)

    def test_34_kayit_ol_button(self):
        self.assertIn("Kayıt Ol", self.html)


class TestNavigation(unittest.TestCase):
    """Tests 35-39: Top navigation."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_35_logo(self):
        self.assertIn("ln-logo", self.html)
        self.assertIn("ZKR Analiz Pro", self.html)

    def test_36_ozellikler_link(self):
        self.assertIn("Özellikler", self.html)
        self.assertIn("#features", self.html)

    def test_37_fiyatlar_link(self):
        self.assertIn("Fiyatlar", self.html)
        self.assertIn("#pricing", self.html)

    def test_38_giris_link(self):
        self.assertIn('href="/login"', self.html)
        self.assertIn("Giriş", self.html)

    def test_39_kayit_ol_nav(self):
        self.assertIn('href="/register"', self.html)


class TestConversionFlow(unittest.TestCase):
    """Tests 40-43: Conversion flow links."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_40_register_links(self):
        count = self.html.count('href="/register"')
        self.assertGreaterEqual(count, 4, "Need multiple register CTAs")

    def test_41_discover_links(self):
        self.assertIn('href="/discover"', self.html)

    def test_42_login_link(self):
        self.assertIn('href="/login"', self.html)

    def test_43_footer_2026(self):
        self.assertIn("2026", self.html)


class TestCSS(unittest.TestCase):
    """Tests 44-52: CSS content."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "static", "css", "landing.css")
        with open(path, "r", encoding="utf-8") as f:
            cls.css = f.read()

    def test_44_hero_styles(self):
        self.assertIn(".ln-hero", self.css)

    def test_45_features_styles(self):
        self.assertIn(".ln-features", self.css)
        self.assertIn(".ln-feature", self.css)

    def test_46_pricing_styles(self):
        self.assertIn(".ln-pricing", self.css)
        self.assertIn(".ln-price-card", self.css)

    def test_47_proof_styles(self):
        self.assertIn(".ln-proof", self.css)

    def test_48_problem_solution_styles(self):
        self.assertIn(".ln-ps", self.css)
        self.assertIn(".ln-ps-problem", self.css)
        self.assertIn(".ln-ps-solution", self.css)

    def test_49_final_cta_styles(self):
        self.assertIn(".ln-final-cta", self.css)

    def test_50_responsive(self):
        self.assertIn("@media", self.css)
        self.assertIn("768px", self.css)

    def test_51_fade_up_animation(self):
        self.assertIn(".ln-fade-up", self.css)
        self.assertIn(".visible", self.css)

    def test_52_nav_scrolled(self):
        self.assertIn(".scrolled", self.css)


class TestJS(unittest.TestCase):
    """Tests 53-58: JavaScript interactions."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "static", "js", "landing.js")
        with open(path, "r", encoding="utf-8") as f:
            cls.js = f.read()

    def test_53_scroll_handler(self):
        self.assertIn("scroll", self.js)
        self.assertIn("scrolled", self.js)

    def test_54_intersection_observer(self):
        self.assertIn("IntersectionObserver", self.js)
        self.assertIn("ln-fade-up", self.js)

    def test_55_counter_animation(self):
        self.assertIn("data-count", self.js)
        self.assertIn("animateCounter", self.js)

    def test_56_analytics_tracking(self):
        self.assertIn("landing_visit", self.js)
        self.assertIn("landing_register_click", self.js)

    def test_57_smooth_scroll(self):
        self.assertIn("smooth", self.js)
        self.assertIn('href^="#"', self.js)

    def test_58_mobile_menu(self):
        self.assertIn("ln-menu-toggle", self.js)


class TestAPIIntegration(unittest.TestCase):
    """Tests 59-60: Live endpoint test."""

    @classmethod
    def setUpClass(cls):
        cls.app = _get_flask_app()

    def test_59_landing_returns_200(self):
        with self.app.test_client() as c:
            r = c.get("/landing")
            self.assertEqual(r.status_code, 200)

    def test_60_response_contains_hero(self):
        with self.app.test_client() as c:
            r = c.get("/landing")
            html = r.data.decode("utf-8")
            self.assertIn("Tek Ekranda Yönetin", html)


class TestDesign(unittest.TestCase):
    """Tests 61-64: Design tokens."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "static", "css", "landing.css")
        with open(path, "r", encoding="utf-8") as f:
            cls.css = f.read()

    def test_61_dark_background(self):
        self.assertIn("#050608", self.css)

    def test_62_inter_font(self):
        self.assertIn("Inter", self.css)

    def test_63_accent_blue(self):
        self.assertIn("#3B82F6", self.css)

    def test_64_green_color(self):
        self.assertIn("#16C784", self.css)


class TestCleanup(unittest.TestCase):
    """Tests 65-67: Old content removed."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_65_no_get_started(self):
        self.assertNotIn("Get Started", self.html)

    def test_66_no_dollar_pricing(self):
        self.assertNotIn("$19", self.html)
        self.assertNotIn("$0", self.html)

    def test_67_no_enterprise(self):
        self.assertNotIn("Enterprise", self.html)


class TestSEO(unittest.TestCase):
    """Tests 68-70: SEO & conversion."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(_PROJECT, "templates", "landing.html")
        with open(path, "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_68_og_title(self):
        self.assertIn('og:title', self.html)

    def test_69_og_description(self):
        self.assertIn('og:description', self.html)

    def test_70_multiple_register_ctas(self):
        count = self.html.count('href="/register"')
        self.assertGreaterEqual(count, 5, "Need 5+ register CTAs for conversion")


if __name__ == "__main__":
    unittest.main()
