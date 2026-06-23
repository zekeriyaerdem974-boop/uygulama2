"""Dashboard HTML render routes.

FAZ 4 — Moved from ``legacy_monolith.py``.
All template paths and URL patterns are preserved exactly.
"""
from __future__ import annotations

from flask import render_template, request, make_response, session, redirect

from app.blueprints.dashboard import dashboard_bp


@dashboard_bp.route("/")
def home():
    # FAZ 27 — Session Guard: redirect to landing if not logged in
    if not session.get('user_id'):
        return redirect('/landing')
    
    # Lazy import to avoid circular dependency at module-load time
    from app.core.security import apk_download_enabled as _apk_download_enabled
    return render_template("index.html", show_apk=_apk_download_enabled(request))


@dashboard_bp.route("/landing")
def landing():
    # Public landing/auth page
    return render_template("landing.html")


@dashboard_bp.route("/tv")
def tv_page():
    # Trading terminal — requires session + no-cache headers
    if not session.get('user_id'):
        return redirect('/landing')
    resp = make_response(render_template("trading_terminal.html"))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@dashboard_bp.route("/chat")
def chat_page():
    return render_template("chat.html")


@dashboard_bp.route("/trade")
def trade_page():
    return render_template("trade.html")


@dashboard_bp.route("/screener")
def screener_page():
    return render_template("screener.html")


@dashboard_bp.route("/sim/mobile")
def mobile_sim_page():
    return render_template("mobile_sim.html")


@dashboard_bp.route("/discover")
def discover_page():
    return render_template("discover.html")



@dashboard_bp.route("/alerts")
def alerts_page():
    return render_template("alerts.html")


@dashboard_bp.route("/simulator")
def simulator_page():
    # FAZ 64: Pre-fetch initial price server-side for instant display
    initial_price = None
    try:
        from app.core.paper_trading_engine import fetch_current_price
        initial_price = fetch_current_price("BTCUSDT", "crypto")
        if initial_price and initial_price > 0:
            initial_price = round(initial_price, 2)
        else:
            initial_price = None
    except Exception:
        initial_price = None
    return render_template("simulator.html", initial_price=initial_price)


@dashboard_bp.route("/backtest")
def backtest_page():
    return render_template("backtest.html")


@dashboard_bp.route("/journal")
def journal_page():
    return render_template("journal.html")


@dashboard_bp.route("/strategy-builder")
def strategy_builder_page():
    return render_template("strategy_builder.html")


@dashboard_bp.route("/chart")
def chart_page():
    return render_template("trading_terminal.html")


@dashboard_bp.route("/copilot")
def copilot_page():
    return render_template("copilot.html")


@dashboard_bp.route("/menu")
def menu_page():
    return render_template("menu.html")
