# -*- coding: utf-8 -*-
"""News Impact / Market Radar API routes — FAZ 37.

Endpoints:
  GET  /api/news/impact/<news_id>   — Impact for one news article
  GET  /api/news/impact/trending    — Recent high-impact analyses
  GET  /api/news/radar              — Aggregated market radar view
  POST /api/news/impact/analyze     — Analyze a news article on demand

Pages:
  GET  /market-radar                — Market radar page
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request

from app.blueprints.news_impact import news_impact_bp
from app.core import news_impact_engine as nie

_logger = logging.getLogger("zkr_analiz.news_impact.routes")


# ── API: Get impact for a specific news article ──────────────────
@news_impact_bp.route("/api/news/impact/<news_id>")
def api_news_impact(news_id):
    impact = nie.get_impact(news_id)
    if not impact:
        return jsonify({"ok": False, "error": "Impact not found"}), 404
    return jsonify({"ok": True, "impact": impact})


# ── API: Trending impacts ────────────────────────────────────────
@news_impact_bp.route("/api/news/impact/trending")
def api_news_impact_trending():
    limit = min(int(request.args.get("limit", 10)), 50)
    market = request.args.get("market", "")
    min_conf = int(request.args.get("min_confidence", 0))

    impacts = nie.get_trending_impacts(
        limit=limit, market=market, min_confidence=min_conf
    )
    return jsonify({"ok": True, "impacts": impacts, "count": len(impacts)})


# ── API: Market radar (aggregated view) ──────────────────────────
@news_impact_bp.route("/api/news/radar")
def api_news_radar():
    market = request.args.get("market", "")
    hours = min(int(request.args.get("hours", 24)), 168)  # max 7 days
    limit = min(int(request.args.get("limit", 20)), 50)
    min_conf = int(request.args.get("min_confidence", 0))

    radar = nie.get_radar(
        market=market, limit=limit, hours=hours,
        min_confidence=min_conf,
    )
    return jsonify({"ok": True, "radar": radar})


# ── API: Analyze a news article on demand ────────────────────────
@news_impact_bp.route("/api/news/impact/analyze", methods=["POST"])
def api_news_impact_analyze():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "Title required"}), 400

    news = {
        "id": data.get("id", ""),
        "title": title,
        "summary": data.get("summary", ""),
        "source": data.get("source", ""),
        "sentiment": data.get("sentiment", "neutral"),
        "market": data.get("market", ""),
        "category": data.get("category", ""),
        "symbols": data.get("symbols", []),
    }

    impact = nie.analyze(news)
    return jsonify({"ok": True, "impact": impact})


# ── API: Top sectors ─────────────────────────────────────────────
@news_impact_bp.route("/api/news/impact/sectors")
def api_news_impact_sectors():
    hours = min(int(request.args.get("hours", 24)), 168)
    limit = min(int(request.args.get("limit", 5)), 20)
    data = nie.get_top_sectors(hours=hours, limit=limit)
    return jsonify({"ok": True, "sectors": data})


# ── API: Most impacted assets ────────────────────────────────────
@news_impact_bp.route("/api/news/impact/assets")
def api_news_impact_assets():
    hours = min(int(request.args.get("hours", 24)), 168)
    limit = min(int(request.args.get("limit", 10)), 30)
    data = nie.get_most_impacted_assets(hours=hours, limit=limit)
    return jsonify({"ok": True, "assets": data})


# ── PAGE: Market Radar ───────────────────────────────────────────
@news_impact_bp.route("/market-radar")
def page_market_radar():
    return render_template("market_radar.html")
