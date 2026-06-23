# -*- coding: utf-8 -*-
"""Multi-Market Screener API routes.

FAZ 17 — Screener endpoints.

Endpoints:
  GET /api/screener          — Run screener scan with filters
  GET /api/screener/filters  — List available filters

Query parameters for /api/screener:
  market   = crypto|stocks|bist|forex|commodities  (default: crypto)
  filters  = comma-separated filter names (optional)
  sort     = column to sort by (default: change_24h)
  dir      = asc|desc (default: desc)
"""
from __future__ import annotations

import logging

from flask import jsonify, request

from app.blueprints.screener import screener_bp
from app.cache import cache_get_or_set
from app.core.screener_engine import ScreenerEngine, get_available_filters

_logger = logging.getLogger("zkr_analiz.screener.routes")

# ── Cache TTLs per market ────────────────────────────────────────────
_CACHE_TTLS = {
    "crypto": 60,
    "stocks": 120,
    "bist": 120,
    "forex": 120,
    "commodities": 120,
}

_VALID_MARKETS = {"crypto", "stocks", "bist", "forex", "commodities"}

_engine = ScreenerEngine()


@screener_bp.route("/api/screener", methods=["GET"])
def screener_scan():
    """Run a market screener scan with optional filters."""
    market = request.args.get("market", "crypto").strip().lower()
    filter_str = request.args.get("filters", "").strip()
    sort_by = request.args.get("sort", "change_24h").strip()
    sort_dir = request.args.get("dir", "desc").strip().lower()

    if market not in _VALID_MARKETS:
        return jsonify({
            "ok": False,
            "error": f"Invalid market: {market}. Must be one of: {', '.join(sorted(_VALID_MARKETS))}",
        }), 400

    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"

    # Parse filters
    filters = [f.strip() for f in filter_str.split(",") if f.strip()] if filter_str else []

    try:
        ttl = _CACHE_TTLS.get(market, 120)
        cache_key = f"screener:{market}:raw"

        # Cache the raw scan (no filters) per market
        all_rows = cache_get_or_set(
            cache_key, ttl,
            _engine.scan, market,
        )

        if all_rows is None:
            all_rows = []

        # Apply filters on cached data (fast, no re-computation)
        from app.core.screener_engine import _FILTERS
        rows = list(all_rows)
        for fname in filters:
            finfo = _FILTERS.get(fname)
            if finfo:
                rows = [r for r in rows if finfo["fn"](r)]

        # Sort
        reverse = sort_dir == "desc"
        rows.sort(
            key=lambda r: r.get(sort_by) if r.get(sort_by) is not None else -9999999,
            reverse=reverse,
        )

        return jsonify({
            "ok": True,
            "market": market,
            "count": len(rows),
            "total_scanned": len(all_rows),
            "filters_applied": filters,
            "data": rows,
        })
    except Exception as e:
        _logger.error("Screener scan error for %s: %s", market, e)
        return jsonify({"ok": False, "error": str(e)}), 502


@screener_bp.route("/api/screener/filters", methods=["GET"])
def screener_filters():
    """Return list of available screener filters."""
    try:
        filters = get_available_filters()
        return jsonify({
            "ok": True,
            "filters": filters,
            "count": len(filters),
        })
    except Exception as e:
        _logger.error("Screener filters error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 502
