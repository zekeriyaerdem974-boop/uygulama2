# -*- coding: utf-8 -*-
"""Legacy monolith — Flask app + routes not yet migrated to blueprints.

FAZ 11: Heavy cleanup. Dead code removed, helpers extracted to core modules:
  - heuristic_bull_estimate -> app.core.bull_estimate
  - security helpers -> app.core.security
  - safe_float inlined (only used here)
"""
import json
import logging
import os
import time
from datetime import datetime, timezone

_logger = logging.getLogger("zkr_analiz.monolith")

from flask import Flask, jsonify, request, send_file, abort, redirect, render_template
from flask_cors import CORS
from flask_sock import Sock
from pathlib import Path

from app.cache import cache_get, cache_get_or_set, utcnow
from app.extensions import job_manager, market_data, socketio
from app.core.etf_tracker import fetch_dynamic_etf_events
from app.core.security import apk_download_enabled

# Blueprints
from blueprints.market import bp as market_bp
from blueprints.indicators import bp as indicators_bp
from blueprints.orderflow import bp as orderflow_bp
from blueprints.liquidation import bp as liquidation_bp
from blueprints.alpha import bp as alpha_bp
from app.blueprints.dashboard import dashboard_bp
from app.blueprints.signals import signals_bp
from app.blueprints.chat import chat_bp
from app.blueprints.news import news_bp
from app.blueprints.markets import markets_bp
from app.blueprints.screener import screener_bp
from app.blueprints.alerts import alerts_bp
from app.blueprints.copilot import copilot_bp
from app.blueprints.simulator import simulator_bp
from app.blueprints.backtest import backtest_bp
from app.blueprints.journal import journal_bp
from app.blueprints.strategy import strategy_bp
from app.blueprints.auth import auth_bp
from app.blueprints.marketplace import marketplace_bp
from app.blueprints.social import social_bp
from app.blueprints.mentors import mentors_bp
from app.blueprints.courses import courses_bp
from app.blueprints.live_rooms import live_rooms_bp
from app.blueprints.reputation import reputation_bp
from app.blueprints.subscription import subscription_bp
from app.blueprints.payment import payment_bp
from app.blueprints.analysis import analysis_bp
from app.blueprints.news_impact import news_impact_bp
from app.blueprints.portfolio import portfolio_bp
from app.blueprints.opportunities import opportunities_bp
from app.blueprints.activity import activity_bp
from app.blueprints.invite import invite_bp
from app.blueprints.onboarding import onboarding_bp
from app.blueprints.analytics import analytics_bp
from app.blueprints.system import system_bp
from app.blueprints.ai_agent import ai_agent_bp
from app.blueprints.settings import settings_bp

# FAZ 8 — background jobs
from app.background.jobs import (
    build_top_coins_4h_dataset,
    TICKERS_KEY,
    TOP4H_REFRESH_SEC,
    TOP4H_MAX_SYMBOLS,
    TOP4H_KLINES,
)


# -------------------- App & Config --------------------
app = Flask(__name__)

# FAZ 27 — Session config
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# FAZ 27 — Inject current_user into all templates
from flask import session as flask_session, g
@app.context_processor
def inject_user():
    uid = flask_session.get('user_id')
    uname = flask_session.get('username')
    return {'current_user': {'id': uid, 'username': uname} if uid else None}

# FAZ 52 — Resolve language before each request
from app.core.localization_engine import resolve_language, translate as _translate
@app.before_request
def set_language():
    uid = flask_session.get('user_id')
    g.lang = resolve_language(user_id=uid)

@app.context_processor
def inject_i18n():
    """Make translate() available in all Jinja2 templates as t()."""
    lang = getattr(g, 'lang', 'tr')
    def t(key, fallback=None):
        result = _translate(key, lang)
        if result == key and fallback:
            return fallback
        return result
    return {'t': t, 'user_lang': lang}

# Register blueprints
app.register_blueprint(market_bp)
app.register_blueprint(indicators_bp)
app.register_blueprint(orderflow_bp)
app.register_blueprint(liquidation_bp)
app.register_blueprint(alpha_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(signals_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(news_bp)
app.register_blueprint(markets_bp)
app.register_blueprint(screener_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(copilot_bp)
app.register_blueprint(simulator_bp)
app.register_blueprint(backtest_bp)
app.register_blueprint(journal_bp)
app.register_blueprint(strategy_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(marketplace_bp)
app.register_blueprint(social_bp)
app.register_blueprint(mentors_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(live_rooms_bp)
app.register_blueprint(reputation_bp)
app.register_blueprint(subscription_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(news_impact_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(opportunities_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(invite_bp)
app.register_blueprint(onboarding_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(system_bp)
app.register_blueprint(ai_agent_bp)
app.register_blueprint(settings_bp)


@app.route('/api/klines', methods=['GET'])
def api_klines_for_chart():
    try:
        symbol = (request.args.get('symbol') or 'BTCUSDT').upper()
        interval = request.args.get('interval') or '1d'
        limit = int(request.args.get('limit') or 200)
        limit = max(1, min(limit, 1500))

        rows = market_data.get_klines(symbol, interval, limit)
        chart_data = []
        for row in rows:
            dt = datetime.fromtimestamp(row['open_time'] / 1000, tz=timezone.utc)
            time_value = dt.strftime('%Y-%m-%d') if interval == '1d' else int(row['open_time'] / 1000)
            chart_data.append({
                'time': time_value,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
            })

        return jsonify({'ok': True, 'data': chart_data})
    except Exception as e:
        _logger.exception('api_klines_for_chart failed: %s', e)
        return jsonify({'ok': False, 'error': str(e)}), 500


# --- Compatibility redirects (legacy mobile paths) ---
@app.route("/orderflow")
@app.route("/orderflow/")
def legacy_orderflow_root():
    return redirect("/trade", code=302)


@app.route("/likidasyon")
@app.route("/likidasyon/")
def legacy_likidasyon_root():
    return redirect("/trade", code=302)


@app.route("/alpha")
@app.route("/alpha/")
def legacy_alpha_root():
    return redirect("/trade", code=302)


@app.route("/orderflow/api/<path:subpath>")
def legacy_orderflow_api(subpath: str):
    return redirect(f"/api/orderflow/{subpath}", code=302)


@app.route("/likidasyon/api/<path:subpath>")
def legacy_liquidation_api(subpath: str):
    return redirect(f"/api/liquidation/{subpath}", code=302)


@app.route("/alpha/api/<path:subpath>")
def legacy_alpha_api(subpath: str):
    return redirect(f"/api/alpha/{subpath}", code=302)


CORS(app, origins=os.getenv("CORS_ORIGINS", "*"), supports_credentials=True)
sock = Sock(app)


# -------------------- WebSocket --------------------
@sock.route('/ws/stream')
def ws_stream(ws):
    """Mobile clients: stream cached ticker data."""
    _logger.info("WebSocket client connected")
    try:
        while True:
            payload = {
                "generated_at": utcnow().isoformat(),
                "tickers": cache_get(TICKERS_KEY, ttl=5) or [],
            }
            ws.send(json.dumps({"ok": True, "data": payload}, ensure_ascii=False))
            time.sleep(1)
    except Exception as e:
        _logger.debug("WebSocket client disconnected: %s", e)


# FAZ 26 — Real-time market data WebSocket
from app.core.market_stream import stream_manager

# FAZ 28 — Strategy Live Signals Engine
from app.core.strategy_live_engine import live_engine as strategy_live_engine


@sock.route('/ws/market')
def ws_market(ws):
    """Browser clients: real-time kline + watchlist stream.

    Client sends JSON commands:
        {"action": "subscribe",   "symbol": "BTCUSDT", "market": "crypto", "interval": "15m"}
        {"action": "subscribe",   "symbol": "AAPL",    "market": "stocks",  "interval": "1d"}
        {"action": "watchlist"}           — subscribe to watchlist ticker updates
        {"action": "ping"}                — keepalive
    """
    _logger.info("ws/market client connected")
    try:
        # Auto-subscribe to watchlist on connect
        stream_manager.subscribe_watchlist(ws)

        while True:
            raw = ws.receive(timeout=30)
            if raw is None:
                # send keepalive
                ws.send('{"type":"pong"}')
                continue

            try:
                cmd = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            action = cmd.get("action", "")

            if action == "subscribe":
                symbol = (cmd.get("symbol") or "BTCUSDT").upper()
                market = (cmd.get("market") or "crypto").lower()
                interval = cmd.get("interval") or "15m"
                stream_manager.register_client(ws, symbol, market, interval)
                ws.send(json.dumps({
                    "type": "subscribed",
                    "symbol": symbol,
                    "market": market,
                    "interval": interval,
                }))

            elif action == "watchlist":
                stream_manager.subscribe_watchlist(ws)
                ws.send('{"type":"watchlist_subscribed"}')

            elif action == "ping":
                ws.send('{"type":"pong"}')

            elif action == "stats":
                ws.send(json.dumps({
                    "type": "stats",
                    **stream_manager.get_stats(),
                }))

    except Exception as e:
        _logger.debug("ws/market client disconnected: %s", e)
    finally:
        stream_manager.unregister_client(ws)


# FAZ 28 — WebSocket for live strategy signals
@sock.route('/ws/signals')
def ws_signals(ws):
    """Browser clients: receive real-time strategy signals.

    Client sends JSON commands:
        {"action": "subscribe"}   — start receiving signals for logged-in user
        {"action": "ping"}        — keepalive
    """
    _logger.info("ws/signals client connected")
    user_id = None
    try:
        while True:
            raw = ws.receive(timeout=30)
            if raw is None:
                ws.send('{"type":"pong"}')
                continue

            try:
                cmd = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            action = cmd.get("action", "")

            if action == "subscribe":
                user_id = cmd.get("user_id", "")
                if user_id:
                    strategy_live_engine.register_listener(ws, user_id)
                    ws.send(json.dumps({
                        "type": "signals_subscribed",
                        "user_id": user_id,
                    }))

            elif action == "ping":
                ws.send('{"type":"pong"}')

    except Exception as e:
        _logger.debug("ws/signals client disconnected: %s", e)
    finally:
        strategy_live_engine.unregister_listener(ws)


# FAZ 34 — WebSocket for live room chat
from app.core import live_room_engine as _lre

@sock.route('/ws/room/<room_id>')
def ws_room(ws, room_id):
    """Browser clients: real-time room chat.

    Client sends JSON commands:
        {"action": "join"}     — register for room messages
        {"action": "ping"}     — keepalive
    """
    _logger.info("ws/room/%s client connected", room_id)
    user_id = None
    try:
        _lre.ws_register(room_id, ws, "anon")
        while True:
            raw = ws.receive(timeout=30)
            if raw is None:
                ws.send('{"type":"pong"}')
                continue
            try:
                cmd = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            action = cmd.get("action", "")
            if action == "join":
                ws.send(json.dumps({"type": "room_joined", "room_id": room_id}))
            elif action == "ping":
                ws.send('{"type":"pong"}')
    except Exception as e:
        _logger.debug("ws/room/%s client disconnected: %s", room_id, e)
    finally:
        _lre.ws_unregister(room_id, ws)


# FAZ 42 — WebSocket for live activity stream
from app.core import activity_stream_engine as _ase

@sock.route('/ws/activity')
def ws_activity(ws):
    """Browser clients: real-time activity stream events.

    Client sends JSON commands:
        {"action": "subscribe"}  — start receiving activity events
        {"action": "ping"}      — keepalive
    """
    _logger.info("ws/activity client connected")
    _ase.ws_register(ws)
    try:
        while True:
            raw = ws.receive(timeout=30)
            if raw is None:
                ws.send('{"type":"pong"}')
                continue
            try:
                cmd = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            action = cmd.get("action", "")
            if action == "subscribe":
                ws.send(json.dumps({"type": "activity_subscribed"}))
            elif action == "ping":
                ws.send('{"type":"pong"}')
    except Exception as e:
        _logger.debug("ws/activity client disconnected: %s", e)
    finally:
        _ase.ws_unregister(ws)


# FAZ 28 — Strategy Signals page route (clean URL)
@app.route("/strategy-signals")
def strategy_signals_page():
    return render_template("strategy_signals.html")


# FAZ 37 — Legal Disclaimer page
@app.route("/disclaimer")
def disclaimer_page():
    return render_template("disclaimer_page.html")


# FAZ 43 — Offline fallback page (PWA)
@app.route("/offline")
def offline_page():
    return render_template("offline.html")


# -------------------- Routes --------------------
def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


@app.route("/apk/ZKR Analiz.apk")
def apk_download():
    if not apk_download_enabled(request):
        abort(404)
    apk_path = Path(__file__).resolve().parent / "private_downloads" / "ZKR Analiz.apk"
    if not apk_path.exists():
        abort(404)
    return send_file(
        apk_path,
        as_attachment=True,
        download_name="ZKR Analiz.apk",
        mimetype="application/vnd.android.package-archive",
        max_age=0,
    )


@app.route("/api/etf_events")
def api_etf_events():
    try:
        return jsonify({"ok": True, "data": fetch_dynamic_etf_events()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/top_coins_4h")
def api_top_coins_4h():
    try:
        limit = int(request.args.get("limit", "100"))
        compact = request.args.get("compact", "false").lower() == "true"
        ds = cache_get_or_set(
            "top_coins_4h_dataset", TOP4H_REFRESH_SEC + 30,
            build_top_coins_4h_dataset,
            max_symbols=TOP4H_MAX_SYMBOLS,
            klines=TOP4H_KLINES,
        )

        rows = ds.get("rows", [])[:limit]
        if compact:
            comp = []
            for r in rows:
                comp.append([
                    r.get("rank"),
                    r.get("ticker"),
                    r.get("binance_symbol"),
                    _safe_float(r.get("market_cap")),
                    _safe_float(r.get("price")),
                    _safe_float(r.get("change24_pct")),
                    r.get("klines_4h"),
                ])
            return jsonify({"ok": True, "data": {
                "generated_at": ds.get("generated_at"),
                "interval": ds.get("interval"),
                "candles": ds.get("candles"),
                "count": len(comp),
                "rows": comp,
            }})
        else:
            return jsonify({"ok": True, "data": {
                "generated_at": ds.get("generated_at"),
                "interval": ds.get("interval"),
                "candles": ds.get("candles"),
                "count": len(rows),
                "rows": rows,
            }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
