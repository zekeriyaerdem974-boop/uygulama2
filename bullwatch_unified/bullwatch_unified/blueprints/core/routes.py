from flask import render_template

from . import core_bp


@core_bp.get("/")
def dashboard():
    return render_template("core/dashboard.html", title="Dashboard")


@core_bp.get("/tv")
def trading_terminal():
    """STEP 3 + STEP 4: Trading Terminal with Live Metrics and Amphitheater"""
    return render_template("trading_terminal.html", title="Trading Terminal")
