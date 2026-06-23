# -*- coding: utf-8 -*-
"""Marketplace API routes — FAZ 29.

Endpoints:
  GET  /api/marketplace/strategies    — List published strategies
  GET  /api/marketplace/strategy/<id> — Strategy detail with metrics
  POST /api/marketplace/publish       — Publish a strategy
  POST /api/marketplace/unpublish     — Unpublish a strategy
  POST /api/marketplace/follow        — Follow a strategy
  POST /api/marketplace/unfollow      — Unfollow a strategy
  GET  /api/marketplace/following     — Get followed strategies
  GET  /api/marketplace/my-published  — Get user's published strategies

Pages:
  GET  /marketplace                   — Marketplace page
  GET  /marketplace/<slug>            — Strategy detail page
"""
from __future__ import annotations

import json
import logging

from flask import jsonify, render_template, request, session

from app.blueprints.marketplace import marketplace_bp
from app.core.marketplace_engine import (
    publish_strategy,
    unpublish_strategy,
    get_published,
    get_published_by_slug,
    list_published,
    follow_strategy,
    unfollow_strategy,
    get_following,
    get_my_published,
    get_strategy_metrics,
    update_metrics,
    is_following,
    enrich_with_usernames,
    get_publisher_username,
)

_logger = logging.getLogger("zkr_analiz.marketplace.routes")


def _require_login():
    uid = session.get("user_id")
    if not uid:
        return None, (jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401)
    return uid, None


# ══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@marketplace_bp.route("/api/marketplace/strategies", methods=["GET"])
def api_list_strategies():
    """List published strategies with optional filters."""
    market = request.args.get("market")
    tag = request.args.get("tag")
    sort = request.args.get("sort", "newest")
    search = request.args.get("search")
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = int(request.args.get("offset", 0))

    strategies = list_published(
        market=market, tag=tag, sort=sort,
        limit=limit, offset=offset, search=search
    )
    strategies = enrich_with_usernames(strategies)
    return jsonify({"ok": True, "strategies": strategies, "count": len(strategies)})


@marketplace_bp.route("/api/marketplace/strategy/<pub_id>", methods=["GET"])
def api_strategy_detail(pub_id: str):
    """Get strategy detail with metrics and follow status."""
    strat = get_published(pub_id)
    if not strat:
        # Try by slug
        strat = get_published_by_slug(pub_id)
    if not strat:
        return jsonify({"ok": False, "error": "Strateji bulunamadı"}), 404

    strat["publisher_username"] = get_publisher_username(strat["user_id"])
    metrics = get_strategy_metrics(strat["id"])
    strat["metrics"] = metrics or {}

    # Check follow status
    uid = session.get("user_id")
    strat["is_following"] = is_following(strat["id"], uid) if uid else False
    strat["is_owner"] = (uid == strat["user_id"]) if uid else False

    # Get live signals for this strategy
    signals = _get_strategy_live_signals(strat.get("strategy_code", ""),
                                         strat.get("default_symbol", ""),
                                         strat["user_id"])
    strat["recent_signals"] = signals

    return jsonify({"ok": True, "strategy": strat})


@marketplace_bp.route("/api/marketplace/publish", methods=["POST"])
def api_publish():
    """Publish a strategy to the marketplace."""
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    try:
        strat = publish_strategy(
            user_id=uid,
            title=data.get("title", ""),
            description=data.get("description", ""),
            strategy_code=data.get("strategy_code", ""),
            market=data.get("market", "crypto"),
            default_symbol=data.get("default_symbol", "BTCUSDT"),
            default_interval=data.get("default_interval", "1h"),
            visibility=data.get("visibility", "public"),
            price_plan=data.get("price_plan", "free"),
            tags=data.get("tags", []),
            risk_level=data.get("risk_level", "medium"),
            metrics=data.get("metrics"),
        )
        return jsonify({"ok": True, "strategy": strat}), 201
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@marketplace_bp.route("/api/marketplace/unpublish", methods=["POST"])
def api_unpublish():
    """Unpublish a strategy (soft delete)."""
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    pub_id = data.get("pub_id", "")
    if not pub_id:
        return jsonify({"ok": False, "error": "pub_id gerekli"}), 400

    ok = unpublish_strategy(pub_id, uid)
    if not ok:
        return jsonify({"ok": False, "error": "Strateji bulunamadı veya yetkiniz yok"}), 404
    return jsonify({"ok": True})


@marketplace_bp.route("/api/marketplace/follow", methods=["POST"])
def api_follow():
    """Follow a published strategy."""
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    pub_id = data.get("pub_id", "")
    if not pub_id:
        return jsonify({"ok": False, "error": "pub_id gerekli"}), 400

    # FAZ 36 — premium strategy access check
    strategy = get_published(pub_id)
    if strategy and strategy.get("price_plan") not in ("free", None, ""):
        from app.core.subscription_engine import can_access_premium_strategy
        check = can_access_premium_strategy(uid)
        if not check["allowed"]:
            return jsonify({"ok": False, "error": check["reason"], "upgrade_required": True, "required_plan": check.get("required_plan"), "locked": True}), 403

    try:
        follow_strategy(pub_id, uid)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@marketplace_bp.route("/api/marketplace/unfollow", methods=["POST"])
def api_unfollow():
    """Unfollow a published strategy."""
    uid, err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    pub_id = data.get("pub_id", "")
    if not pub_id:
        return jsonify({"ok": False, "error": "pub_id gerekli"}), 400

    unfollow_strategy(pub_id, uid)
    return jsonify({"ok": True})


@marketplace_bp.route("/api/marketplace/following", methods=["GET"])
def api_following():
    """Get strategies the current user follows."""
    uid, err = _require_login()
    if err:
        return err

    strategies = get_following(uid)
    strategies = enrich_with_usernames(strategies)
    return jsonify({"ok": True, "strategies": strategies})


@marketplace_bp.route("/api/marketplace/my-published", methods=["GET"])
def api_my_published():
    """Get current user's published strategies."""
    uid, err = _require_login()
    if err:
        return err

    strategies = get_my_published(uid)
    return jsonify({"ok": True, "strategies": strategies})


# ══════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════

@marketplace_bp.route("/marketplace")
def marketplace_page():
    return render_template("marketplace.html")


@marketplace_bp.route("/marketplace/<slug>")
def marketplace_detail_page(slug: str):
    return render_template("marketplace_detail.html", slug=slug)


# ══════════════════════════════════════════════════════════════════
# COPILOT INTEGRATION
# ══════════════════════════════════════════════════════════════════

@marketplace_bp.route("/api/copilot/marketplace", methods=["POST"])
def api_copilot_marketplace():
    """Answer marketplace-related copilot questions."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "question gerekli"}), 400

    # Build context from marketplace data
    top_strategies = list_published(sort="performance", limit=10)
    top_strategies = enrich_with_usernames(top_strategies)
    popular = list_published(sort="popular", limit=10)
    popular = enrich_with_usernames(popular)

    context_parts = ["=== MARKETPLACE VERİLERİ ===\n"]
    context_parts.append("EN İYİ PERFORMANSLI STRATEJİLER:")
    for s in top_strategies[:5]:
        context_parts.append(
            f"  - {s['title']} ({s['market']}/{s['default_symbol']}) "
            f"win_rate={s.get('win_rate', 0):.1f}% "
            f"takipçi={s.get('followers_count', 0)} "
            f"yazan={s.get('publisher_username', '?')}"
        )

    context_parts.append("\nEN POPÜLER STRATEJİLER:")
    for s in popular[:5]:
        context_parts.append(
            f"  - {s['title']} ({s['market']}/{s['default_symbol']}) "
            f"takipçi={s.get('followers_count', 0)} "
            f"sinyal={s.get('live_signal_count', 0)}"
        )

    context_text = "\n".join(context_parts)

    try:
        from app.core.copilot_service import _SYSTEM_BASE, _call_llm, DEFAULT_MODEL
        _MARKETPLACE_PROMPT = (
            "\nBu yanıtı ZKR Analiz Marketplace (Strateji Pazarı) için veriyorsun.\n"
            "Context'te yayınlanmış stratejiler, performans metrikleri ve takipçi sayıları var.\n"
            "Kullanıcıya en uygun stratejiyi öner, performansları karşılaştır.\n"
        )
        system = _SYSTEM_BASE + _MARKETPLACE_PROMPT
        prompt = f"[CONTEXT]\n{context_text}\n\n[KULLANICI SORUSU]\n{question}\n\nassistant:"
        result = _call_llm(DEFAULT_MODEL, system, prompt, {"marketplace": context_text})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        _logger.warning("Copilot marketplace error: %s", e)
        return jsonify({
            "ok": True,
            "data": {
                "answer": f"Marketplace'te şu anda {len(top_strategies)} strateji mevcut. "
                          f"En popüler strateji: {top_strategies[0]['title'] if top_strategies else 'henüz yok'}.",
                "summary": "Marketplace özeti",
                "key_points": [f"{len(top_strategies)} yayınlanmış strateji"],
                "risk_points": [],
                "suggested_alerts": [],
            }
        })


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _get_strategy_live_signals(code: str, symbol: str, user_id: str) -> list:
    """Get recent live signals for a strategy from the live engine."""
    try:
        from app.core.strategy_live_engine import live_engine
        all_signals = live_engine.get_live_signals(user_id, limit=20)
        # Filter by symbol match
        return [s for s in all_signals if s.get("symbol") == symbol][:10]
    except Exception:
        return []
