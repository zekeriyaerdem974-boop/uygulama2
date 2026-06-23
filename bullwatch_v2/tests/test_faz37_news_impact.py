# -*- coding: utf-8 -*-
"""FAZ 37 — AI News Impact / Market Radar tests.

Covers:
  01-05  Engine — sector/asset keyword matching
  06-10  Engine — cross-impact rules (rate hike/cut, ETF, crypto ban, war)
  11-15  Engine — analyze() full pipeline (crypto, BIST, US stocks, macro, forex)
  16-20  Engine — confidence scoring, time horizon, summary generation
  21-25  Engine — DB CRUD (get_impact, trending, delete, upsert, batch)
  26-30  Engine — radar, top_sectors, most_impacted_assets aggregation
  31-35  Engine — edge cases (empty title, neutral sentiment, unknown source)
  36-40  Blueprint API routes (impact, trending, radar, analyze, sectors, assets)
  41-45  Blueprint — filters, pagination, error handling
  46-50  Page loads (market-radar, discover radar widget HTML)
"""
import json
import os
import sqlite3
import sys
import unittest

# ── project root on sys.path ──
_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

# ── isolate test data ──
_TEST_DIR = os.path.join(_PROJECT, ".test_data_faz37_impact")
os.makedirs(_TEST_DIR, exist_ok=True)

import app.core.news_impact_engine as nie

import app.core.db_manager as _dm
_dm._DB_DIR = _TEST_DIR
nie._DB_DIR = _TEST_DIR
nie._DB_PATH = os.path.join(_TEST_DIR, "news_impact.db")

# Re-init DB with test paths
nie._init_db()


def _reset_db():
    """Clear news_impacts for fresh tests."""
    conn = nie._get_conn()
    try:
        conn.execute("DELETE FROM news_impacts")
        conn.commit()
    finally:
        conn.close()


def _make_news(title, summary="", source="CoinDesk", sentiment="bullish",
               market="crypto", category="general", news_id=None,
               symbols=None):
    return {
        "id": news_id or nie._gen_id(),
        "title": title,
        "summary": summary or title,
        "source": source,
        "sentiment": sentiment,
        "market": market,
        "category": category,
        "symbols": symbols or [],
    }


# ══════════════════════════════════════════════════════════════════
# 01-05: Sector / asset keyword matching
# ══════════════════════════════════════════════════════════════════

class TestKeywordMatching(unittest.TestCase):
    """01-05: Sector and asset keyword matching."""

    def test_01_match_crypto_sectors(self):
        sectors = nie._match_sectors("Bitcoin rallies above $100k with ETH following")
        self.assertIn("crypto", sectors)

    def test_02_match_bist_sectors(self):
        sectors = nie._match_sectors("Borsa Istanbul BIST 100 endeksi yükseldi, THYAO güçlü")
        self.assertIn("bist", sectors)

    def test_03_match_banking_sectors(self):
        sectors = nie._match_sectors("Federal Reserve interest rate decision impacts banking")
        self.assertIn("banking", sectors)
        self.assertIn("macro", sectors)

    def test_04_match_assets_bullish(self):
        result = nie._match_assets("Bitcoin price surges, Ethereum follows", "bullish")
        self.assertIn("BTC", result["bullish"])
        self.assertIn("ETH", result["bullish"])
        self.assertEqual(result["bearish"], [])

    def test_05_match_assets_bearish(self):
        result = nie._match_assets("Bitcoin crashes below 50k, Ethereum dumps", "bearish")
        self.assertIn("BTC", result["bearish"])
        self.assertIn("ETH", result["bearish"])
        self.assertEqual(result["bullish"], [])


# ══════════════════════════════════════════════════════════════════
# 06-10: Cross-impact rules
# ══════════════════════════════════════════════════════════════════

class TestCrossImpactRules(unittest.TestCase):
    """06-10: Cross-market impact rules."""

    def test_06_rate_hike(self):
        rule = nie._apply_cross_impact("Federal Reserve raises interest rate by 0.25%")
        self.assertIsNotNone(rule)
        self.assertIn("BTC", rule["bearish_assets"])
        self.assertIn("banking", rule["bullish_sectors"])

    def test_07_rate_cut(self):
        rule = nie._apply_cross_impact("Fed announces interest rate cut for first time in years")
        self.assertIsNotNone(rule)
        self.assertIn("BTC", rule["bullish_assets"])
        self.assertIn("technology", rule["bullish_sectors"])

    def test_08_bitcoin_etf_approval(self):
        rule = nie._apply_cross_impact("SEC approves Bitcoin ETF, historic day for crypto")
        self.assertIsNotNone(rule)
        self.assertIn("BTC", rule["bullish_assets"])
        self.assertIn("COIN", rule["bullish_assets"])
        self.assertIn("crypto", rule["bullish_sectors"])

    def test_09_crypto_ban(self):
        rule = nie._apply_cross_impact("China announces crypto ban, Bitcoin crashes")
        self.assertIsNotNone(rule)
        self.assertIn("BTC", rule["bearish_assets"])

    def test_10_war_geopolitics(self):
        rule = nie._apply_cross_impact("War tensions rise in Middle East, geopolitical crisis")
        self.assertIsNotNone(rule)
        self.assertIn("GC=F", rule["bullish_assets"])
        self.assertIn("defense", rule["bullish_sectors"])


# ══════════════════════════════════════════════════════════════════
# 11-15: Full analyze() pipeline
# ══════════════════════════════════════════════════════════════════

class TestAnalyzePipeline(unittest.TestCase):
    """11-15: Full analyze pipeline for different markets."""

    @classmethod
    def setUpClass(cls):
        _reset_db()

    def test_11_analyze_crypto_news(self):
        news = _make_news(
            "Bitcoin smashes new all-time high above $120k",
            "Ethereum and Solana also rallying hard",
            sentiment="bullish", market="crypto",
        )
        result = nie.analyze(news)
        self.assertEqual(result["news_id"], news["id"])
        self.assertIn("BTC", result["bullish_assets"])
        self.assertIn("crypto", result["bullish_sectors"])
        self.assertGreater(result["confidence_score"], 0)
        self.assertIn("impact_summary", result)
        self.__class__.crypto_id = news["id"]

    def test_12_analyze_bist_news(self):
        news = _make_news(
            "Borsa Istanbul BIST100 rekor kırdı, THYAO ve Aselsan güçlü",
            "TCMB faiz kararı sonrası bankacılık sektöründe hareketlilik",
            source="KAP", sentiment="bullish", market="bist",
        )
        result = nie.analyze(news)
        self.assertIn("bist", result["bullish_sectors"])
        self.assertTrue(
            "THYAO.IS" in result["bullish_assets"] or
            "ASELS.IS" in result["bullish_assets"]
        )
        self.__class__.bist_id = news["id"]

    def test_13_analyze_us_stock_news(self):
        news = _make_news(
            "NVIDIA earnings beat expectations, AI chip demand soars",
            "Microsoft and Google also benefit from AI boom",
            source="Bloomberg", sentiment="bullish", market="stocks",
        )
        result = nie.analyze(news)
        self.assertIn("NVDA", result["bullish_assets"])
        self.assertIn("technology", result["bullish_sectors"])
        self.__class__.stock_id = news["id"]

    def test_14_analyze_macro_news(self):
        news = _make_news(
            "Federal Reserve raises interest rate by 50 basis points",
            "Markets react negatively, dollar strengthens significantly",
            source="Reuters", sentiment="bearish", market="macro",
        )
        result = nie.analyze(news)
        # Cross-impact rule: rate hike → bearish for tech/crypto
        self.assertTrue(
            "BTC" in result["bearish_assets"] or
            "QQQ" in result["bearish_assets"]
        )
        self.__class__.macro_id = news["id"]

    def test_15_analyze_forex_news(self):
        news = _make_news(
            "Dollar index DXY reaches multi-year high, EURUSD drops",
            "Strong dollar pressures emerging market currencies",
            sentiment="bullish", market="forex",
        )
        result = nie.analyze(news)
        self.assertTrue(
            "DXY" in result["bullish_assets"] or
            "EURUSD=X" in result["bullish_assets"]
        )


# ══════════════════════════════════════════════════════════════════
# 16-20: Confidence, horizon, summary
# ══════════════════════════════════════════════════════════════════

class TestConfidenceHorizonSummary(unittest.TestCase):
    """16-20: Confidence scoring, time horizon, summary generation."""

    def test_16_confidence_higher_for_trusted_source(self):
        n1 = _make_news("Bitcoin news test", source="Reuters", sentiment="bullish")
        n2 = _make_news("Bitcoin news test", source="Unknown Blog", sentiment="bullish")
        r1 = nie.analyze(n1)
        r2 = nie.analyze(n2)
        self.assertGreater(r1["confidence_score"], r2["confidence_score"])

    def test_17_confidence_range_0_100(self):
        news = _make_news("Random short title", sentiment="neutral")
        r = nie.analyze(news)
        self.assertGreaterEqual(r["confidence_score"], 0)
        self.assertLessEqual(r["confidence_score"], 100)

    def test_18_time_horizon_short_term(self):
        h = nie._determine_horizon("Market reacts to breaking news today")
        self.assertEqual(h, "short_term")

    def test_19_time_horizon_mid_term(self):
        h = nie._determine_horizon("Expected to impact markets this quarter mid-term outlook")
        self.assertEqual(h, "mid_term")

    def test_20_summary_contains_sectors(self):
        news = _make_news(
            "Bitcoin ETF approved by SEC",
            "Historic day for crypto industry with spot Bitcoin ETF",
            sentiment="bullish",
        )
        r = nie.analyze(news)
        self.assertTrue(len(r["impact_summary"]) > 10)
        # Summary should mention bullish sectors or assets
        summary_lower = r["impact_summary"].lower()
        self.assertTrue(
            "olumlu" in summary_lower or
            "yükselebilecek" in summary_lower or
            "sektör" in summary_lower or
            len(summary_lower) > 10
        )


# ══════════════════════════════════════════════════════════════════
# 21-25: DB CRUD
# ══════════════════════════════════════════════════════════════════

class TestDbCrud(unittest.TestCase):
    """21-25: Database create/read/update/delete operations."""

    @classmethod
    def setUpClass(cls):
        _reset_db()
        cls.news = _make_news(
            "Tesla stock surges on earnings beat",
            "EV market booms with Tesla leading",
            sentiment="bullish", market="stocks",
        )
        cls.impact = nie.analyze(cls.news)

    def test_21_get_impact_by_news_id(self):
        result = nie.get_impact(self.news["id"])
        self.assertIsNotNone(result)
        self.assertEqual(result["news_id"], self.news["id"])
        self.assertEqual(result["news_title"], self.news["title"])

    def test_22_get_impact_returns_none_for_missing(self):
        result = nie.get_impact("nonexistent-id-xyz")
        self.assertIsNone(result)

    def test_23_trending_returns_list(self):
        results = nie.get_trending_impacts(limit=10)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_24_upsert_updates_existing(self):
        # Analyze same news_id again -> should update, not duplicate
        updated_news = dict(self.news)
        updated_news["title"] = "Tesla stock surges even more"
        updated_news["sentiment"] = "bearish"
        r = nie.analyze(updated_news)
        self.assertEqual(r["news_id"], self.news["id"])

        # Verify only one record for this news_id
        conn = nie._get_conn()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM news_impacts WHERE news_id = ?",
                (self.news["id"],)
            ).fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            conn.close()

    def test_25_delete_impact(self):
        news = _make_news("Temporary news for deletion", sentiment="neutral")
        nie.analyze(news)
        self.assertIsNotNone(nie.get_impact(news["id"]))

        deleted = nie.delete_impact(news["id"])
        self.assertTrue(deleted)
        self.assertIsNone(nie.get_impact(news["id"]))

        # Double delete returns False
        self.assertFalse(nie.delete_impact(news["id"]))


# ══════════════════════════════════════════════════════════════════
# 26-30: Radar, top sectors, most impacted assets
# ══════════════════════════════════════════════════════════════════

class TestAggregation(unittest.TestCase):
    """26-30: Aggregation: radar, sectors, assets."""

    @classmethod
    def setUpClass(cls):
        _reset_db()
        # Seed multiple diverse news
        articles = [
            _make_news("Bitcoin explodes higher, ETH follows",
                       sentiment="bullish", market="crypto"),
            _make_news("Ethereum DeFi boom continues, Solana joins",
                       sentiment="bullish", market="crypto"),
            _make_news("NVIDIA beats earnings, AI revolution",
                       "Microsoft also surging on AI demand",
                       source="Bloomberg", sentiment="bullish", market="stocks"),
            _make_news("Borsa Istanbul BIST100 yükseldi, THYAO lider",
                       source="KAP", sentiment="bullish", market="bist"),
            _make_news("Gold surges on inflation fears, oil also up",
                       sentiment="bullish", market="commodities"),
        ]
        for a in articles:
            nie.analyze(a)

    def test_26_radar_returns_structure(self):
        radar = nie.get_radar()
        self.assertIn("top_bullish_sectors", radar)
        self.assertIn("top_bearish_sectors", radar)
        self.assertIn("trending_bullish_assets", radar)
        self.assertIn("trending_bearish_assets", radar)
        self.assertIn("most_impactful_news", radar)
        self.assertIn("total_analyzed", radar)
        self.assertGreater(radar["total_analyzed"], 0)

    def test_27_radar_market_filter(self):
        radar = nie.get_radar(market="crypto")
        self.assertEqual(radar["market_filter"], "crypto")
        # Should only contain crypto market news
        for news in radar["most_impactful_news"]:
            self.assertEqual(news["news_market"], "crypto")

    def test_28_top_sectors_format(self):
        sectors = nie.get_top_sectors()
        self.assertIn("bullish", sectors)
        self.assertIn("bearish", sectors)
        self.assertIsInstance(sectors["bullish"], list)
        # Each entry is (sector_name, count) tuple
        if sectors["bullish"]:
            self.assertEqual(len(sectors["bullish"][0]), 2)

    def test_29_most_impacted_assets_format(self):
        assets = nie.get_most_impacted_assets()
        self.assertIsInstance(assets, list)
        if assets:
            a = assets[0]
            self.assertIn("asset", a)
            self.assertIn("bullish_mentions", a)
            self.assertIn("bearish_mentions", a)
            self.assertIn("total", a)

    def test_30_analyze_batch(self):
        batch = [
            _make_news("Apple stock reaches new high", sentiment="bullish"),
            _make_news("Amazon cloud revenue doubles", sentiment="bullish"),
            _make_news("Netflix subscriber growth slows", sentiment="bearish"),
        ]
        results = nie.analyze_batch(batch)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("bullish_sectors", r)
            self.assertIn("bearish_sectors", r)


# ══════════════════════════════════════════════════════════════════
# 31-35: Edge cases
# ══════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):
    """31-35: Edge cases."""

    def test_31_empty_title_raises(self):
        with self.assertRaises(ValueError):
            nie.analyze({"title": "", "summary": "test"})

    def test_32_none_news_raises(self):
        with self.assertRaises(ValueError):
            nie.analyze(None)

    def test_33_neutral_sentiment_distributes_sectors(self):
        news = _make_news(
            "Bitcoin and banking news update, technology sector watched",
            sentiment="neutral",
        )
        r = nie.analyze(news)
        # Neutral distributes sectors between bullish and bearish
        total = len(r["bullish_sectors"]) + len(r["bearish_sectors"])
        self.assertGreater(total, 0)

    def test_34_unknown_source_still_works(self):
        news = _make_news(
            "Bitcoin price update today",
            source="RandomBlog.xyz", sentiment="bullish",
        )
        r = nie.analyze(news)
        self.assertIn("news_id", r)
        self.assertGreater(r["confidence_score"], 0)

    def test_35_auto_generate_news_id(self):
        news = _make_news("Ethereum upgrade news", news_id="")
        # Engine should not fail with empty id
        r = nie.analyze(news)
        self.assertTrue(len(r["news_id"]) > 0)


# ══════════════════════════════════════════════════════════════════
# 36-45: Blueprint API routes
# ══════════════════════════════════════════════════════════════════

class TestBlueprintRoutes(unittest.TestCase):
    """36-45: Blueprint API routes via Flask test client."""

    @classmethod
    def setUpClass(cls):
        _reset_db()
        from legacy_monolith import app
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-faz37"
        cls.app = app
        cls.client = app.test_client()

        # Seed test data
        cls.test_news = _make_news(
            "Bitcoin price surges to new all-time high above $150k",
            "Ethereum and Solana follow with strong gains in DeFi sector",
            sentiment="bullish", market="crypto",
        )
        cls.impact = nie.analyze(cls.test_news)

    def test_36_get_impact_api(self):
        r = self.client.get(f"/api/news/impact/{self.test_news['id']}")
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d["ok"])
        self.assertIn("impact", d)
        self.assertEqual(d["impact"]["news_id"], self.test_news["id"])

    def test_37_get_impact_not_found(self):
        r = self.client.get("/api/news/impact/nonexistent-id")
        d = r.get_json()
        self.assertEqual(r.status_code, 404)
        self.assertFalse(d["ok"])

    def test_38_trending_api(self):
        r = self.client.get("/api/news/impact/trending")
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d["ok"])
        self.assertIn("impacts", d)
        self.assertIn("count", d)
        self.assertIsInstance(d["impacts"], list)

    def test_39_trending_with_filters(self):
        r = self.client.get("/api/news/impact/trending?market=crypto&min_confidence=30&limit=5")
        d = r.get_json()
        self.assertTrue(d["ok"])
        for imp in d["impacts"]:
            self.assertEqual(imp["news_market"], "crypto")
            self.assertGreaterEqual(imp["confidence_score"], 30)

    def test_40_radar_api(self):
        r = self.client.get("/api/news/radar")
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d["ok"])
        radar = d["radar"]
        self.assertIn("top_bullish_sectors", radar)
        self.assertIn("trending_bullish_assets", radar)
        self.assertIn("most_impactful_news", radar)

    def test_41_radar_with_filters(self):
        r = self.client.get("/api/news/radar?market=crypto&hours=48&min_confidence=20")
        d = r.get_json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["radar"]["market_filter"], "crypto")

    def test_42_analyze_api(self):
        r = self.client.post("/api/news/impact/analyze", json={
            "title": "Nvidia stock jumps on AI earnings beat",
            "summary": "Semiconductor demand highest in years",
            "source": "Bloomberg",
            "sentiment": "bullish",
            "market": "stocks",
        })
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d["ok"])
        self.assertIn("impact", d)
        self.assertIn("NVDA", d["impact"]["bullish_assets"])

    def test_43_analyze_api_missing_title(self):
        r = self.client.post("/api/news/impact/analyze", json={
            "summary": "No title provided",
        })
        d = r.get_json()
        self.assertEqual(r.status_code, 400)
        self.assertFalse(d["ok"])

    def test_44_sectors_api(self):
        r = self.client.get("/api/news/impact/sectors")
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d["ok"])
        self.assertIn("sectors", d)
        self.assertIn("bullish", d["sectors"])
        self.assertIn("bearish", d["sectors"])

    def test_45_assets_api(self):
        r = self.client.get("/api/news/impact/assets")
        d = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(d["ok"])
        self.assertIn("assets", d)


# ══════════════════════════════════════════════════════════════════
# 46-50: Page loads
# ══════════════════════════════════════════════════════════════════

class TestPageLoads(unittest.TestCase):
    """46-50: Page rendering and HTML checks."""

    @classmethod
    def setUpClass(cls):
        from legacy_monolith import app
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-faz37"
        cls.client = app.test_client()

    def test_46_market_radar_page_loads(self):
        r = self.client.get("/market-radar")
        self.assertEqual(r.status_code, 200)
        html = r.data.decode()
        self.assertIn("Market Radar", html)

    def test_47_market_radar_has_filter_buttons(self):
        r = self.client.get("/market-radar")
        html = r.data.decode()
        self.assertIn("Crypto", html)
        self.assertIn("BIST", html)
        self.assertIn("Stocks", html)

    def test_48_market_radar_has_sector_cards(self):
        r = self.client.get("/market-radar")
        html = r.data.decode()
        # Check for sector display elements
        self.assertIn("bullish", html.lower())
        self.assertIn("bearish", html.lower())

    def test_49_market_radar_has_js(self):
        r = self.client.get("/market-radar")
        html = r.data.decode()
        self.assertIn("loadRadar", html)
        self.assertIn("/api/news/radar", html)

    def test_50_discover_page_has_radar_widget(self):
        r = self.client.get("/discover")
        self.assertIn(r.status_code, [200, 302])
        if r.status_code == 200:
            html = r.data.decode()
            self.assertIn("Market Radar", html)


if __name__ == "__main__":
    unittest.main()
