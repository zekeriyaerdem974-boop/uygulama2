# -*- coding: utf-8 -*-
"""FAZ 54 — Force Apply New Trading Terminal Layout To /tv Route.

Validates:
  1. trading_terminal.html template exists and structure
  2. Route /tv renders trading_terminal.html (not tv.html)
  3. Route /chart renders trading_terminal.html (not tv.html)
  4. Required element IDs: tickerBar, chartControlsBar, terminalMainGrid,
     tvMainChart, metricsBar, rightPanelTabs
  5. Old layout sections removed (no tv-shell, tv-grid, VIEWS, iframes)
  6. Ticker bar with instruments
  7. Chart controls (symbol selector, timeframes, indicators)
  8. Right panel tabs (Watchlist, Activity, Signals, News)
  9. Metrics bar with 6 cards
  10. TradingView widget integration
  11. Inline JS functionality
  12. News modal
  13. Old tv.html backup exists
  14. Extends layout_terminal.html (not base.html)

Minimum: 40 tests

Run:
    python -m pytest tests/test_faz54_trading_terminal_apply.py -v
"""
from __future__ import annotations

import os
import re

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel_path: str) -> str:
    fp = os.path.join(BASE, rel_path)
    assert os.path.isfile(fp), f"Missing file: {rel_path}"
    with open(fp, encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════════
# 1) TEMPLATE FILE EXISTS
# ═══════════════════════════════════════════════════════════════════

class TestTemplateFileExists:
    """trading_terminal.html must exist and extend layout_terminal.html."""

    def test_trading_terminal_html_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/trading_terminal.html"))

    def test_extends_layout_terminal(self):
        src = _read("templates/trading_terminal.html")
        assert 'extends "layout_terminal.html"' in src

    def test_not_extends_base(self):
        src = _read("templates/trading_terminal.html")
        assert 'extends "base.html"' not in src

    def test_old_tv_backup_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/tv.html.bak.faz54"))


# ═══════════════════════════════════════════════════════════════════
# 2) ROUTE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

class TestRouteConfiguration:
    """Both /tv and /chart must render trading_terminal.html."""

    def test_tv_route_renders_trading_terminal(self):
        src = _read("app/blueprints/dashboard/routes.py")
        # Find the tv_page function and check it renders trading_terminal.html
        match = re.search(r'def tv_page\(\):\s*\n\s*return render_template\(["\']([^"\']+)', src)
        assert match, "tv_page function not found"
        assert match.group(1) == "trading_terminal.html", f"Expected trading_terminal.html, got {match.group(1)}"

    def test_chart_route_renders_trading_terminal(self):
        src = _read("app/blueprints/dashboard/routes.py")
        match = re.search(r'def chart_page\(\):\s*\n\s*return render_template\(["\']([^"\']+)', src)
        assert match, "chart_page function not found"
        assert match.group(1) == "trading_terminal.html", f"Expected trading_terminal.html, got {match.group(1)}"

    def test_tv_route_decorator(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert '@dashboard_bp.route("/tv")' in src

    def test_chart_route_decorator(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert '@dashboard_bp.route("/chart")' in src

    def test_routes_not_rendering_old_tv(self):
        src = _read("app/blueprints/dashboard/routes.py")
        # tv.html should not appear in render_template calls for tv_page or chart_page
        lines = src.split('\n')
        for i, line in enumerate(lines):
            if 'def tv_page' in line or 'def chart_page' in line:
                if i + 1 < len(lines):
                    assert 'render_template("tv.html")' not in lines[i + 1]


# ═══════════════════════════════════════════════════════════════════
# 3) REQUIRED ELEMENT IDS
# ═══════════════════════════════════════════════════════════════════

class TestRequiredElementIDs:
    """FAZ 54 spec requires specific element IDs in the terminal."""

    def test_id_tickerBar(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="tickerBar"' in src

    def test_id_chartControlsBar(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="chartControlsBar"' in src

    def test_id_terminalMainGrid(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="terminalMainGrid"' in src

    def test_id_tvMainChart(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="tvMainChart"' in src

    def test_id_metricsBar(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="metricsBar"' in src

    def test_id_rightPanelTabs(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="rightPanelTabs"' in src


# ═══════════════════════════════════════════════════════════════════
# 4) OLD LAYOUT REMOVED
# ═══════════════════════════════════════════════════════════════════

class TestOldLayoutRemoved:
    """Old tv.html elements must not appear in trading_terminal.html."""

    def test_no_tv_shell(self):
        src = _read("templates/trading_terminal.html")
        assert "tv-shell" not in src

    def test_no_tv_grid(self):
        src = _read("templates/trading_terminal.html")
        assert "tv-grid" not in src

    def test_no_tv_left(self):
        src = _read("templates/trading_terminal.html")
        assert "tv-left" not in src

    def test_no_tv_main(self):
        src = _read("templates/trading_terminal.html")
        assert "tv-main" not in src.split("tv-main-chart")[0]  # tv-main-chart is valid, tv-main alone is old

    def test_no_VIEWS_array(self):
        src = _read("templates/trading_terminal.html")
        assert "var VIEWS" not in src and "const VIEWS" not in src

    def test_no_iframe_src(self):
        src = _read("templates/trading_terminal.html")
        assert "<iframe" not in src.lower()

    def test_no_tv_tab(self):
        src = _read("templates/trading_terminal.html")
        assert "tv-tab" not in src


# ═══════════════════════════════════════════════════════════════════
# 5) TICKER BAR
# ═══════════════════════════════════════════════════════════════════

class TestTickerBar:
    """Ticker bar with multiple instruments."""

    def test_ticker_bar_class(self):
        src = _read("templates/trading_terminal.html")
        assert 'class="ticker-bar"' in src

    def test_ticker_has_btc(self):
        src = _read("templates/trading_terminal.html")
        assert "tk-btc-p" in src

    def test_ticker_has_eth(self):
        src = _read("templates/trading_terminal.html")
        assert "tk-eth-p" in src

    def test_ticker_has_sol(self):
        src = _read("templates/trading_terminal.html")
        assert "tk-sol-p" in src

    def test_ticker_has_gold(self):
        src = _read("templates/trading_terminal.html")
        assert "tk-gold-p" in src

    def test_ticker_items_exist(self):
        src = _read("templates/trading_terminal.html")
        assert src.count('class="ticker-item"') >= 6


# ═══════════════════════════════════════════════════════════════════
# 6) CHART CONTROLS
# ═══════════════════════════════════════════════════════════════════

class TestChartControls:
    """Chart controls bar with symbol selector, timeframes, indicators."""

    def test_symbol_selector_exists(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="ctrlSymbol"' in src

    def test_timeframes_group(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="ctrlTimeframes"' in src

    def test_indicators_group(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="ctrlIndicators"' in src

    def test_has_btcusdt_option(self):
        src = _read("templates/trading_terminal.html")
        assert "BINANCE:BTCUSDT" in src

    def test_has_timeframe_buttons(self):
        src = _read("templates/trading_terminal.html")
        assert 'data-tf="1"' in src
        assert 'data-tf="D"' in src

    def test_has_indicator_buttons(self):
        src = _read("templates/trading_terminal.html")
        assert 'data-ind="RSI"' in src
        assert 'data-ind="MACD"' in src

    def test_fullscreen_button(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="ctrlFullscreen"' in src

    def test_panel_toggle_button(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="ctrlPanelToggle"' in src


# ═══════════════════════════════════════════════════════════════════
# 7) RIGHT PANEL TABS
# ═══════════════════════════════════════════════════════════════════

class TestRightPanel:
    """Right panel with 4 tabs: Watchlist, Activity, Signals, News."""

    def test_right_panel_div(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="rightPanel"' in src

    def test_tab_watchlist(self):
        src = _read("templates/trading_terminal.html")
        assert 'data-rp="watchlist"' in src

    def test_tab_activity(self):
        src = _read("templates/trading_terminal.html")
        assert 'data-rp="activity"' in src

    def test_tab_signals(self):
        src = _read("templates/trading_terminal.html")
        assert 'data-rp="signals"' in src

    def test_tab_news(self):
        src = _read("templates/trading_terminal.html")
        assert 'data-rp="news"' in src

    def test_four_tab_buttons(self):
        src = _read("templates/trading_terminal.html")
        assert src.count('class="rp-tab') >= 4


# ═══════════════════════════════════════════════════════════════════
# 8) METRICS BAR
# ═══════════════════════════════════════════════════════════════════

class TestMetricsBar:
    """Metrics bar with 6 metric cards."""

    def test_metrics_bar_html(self):
        src = _read("templates/trading_terminal.html")
        assert 'class="metrics-bar"' in src

    def test_metric_card_html(self):
        src = _read("templates/trading_terminal.html")
        assert 'class="metric-card"' in src

    def test_mc_volume_id(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="mc-volume"' in src

    def test_mc_oi_id(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="mc-oi"' in src

    def test_mc_fng_id(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="mc-fng"' in src

    def test_mc_funding_id(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="mc-funding"' in src

    def test_mc_dom_id(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="mc-dom"' in src

    def test_mc_sentiment_id(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="mc-sentiment"' in src

    def test_loadMetrics_function(self):
        src = _read("templates/trading_terminal.html")
        assert 'loadMetrics' in src


# ═══════════════════════════════════════════════════════════════════
# 9) TRADINGVIEW INTEGRATION
# ═══════════════════════════════════════════════════════════════════

class TestTradingViewIntegration:
    """TradingView Advanced Chart widget must be integrated."""

    def test_tradingview_script_url(self):
        src = _read("templates/trading_terminal.html")
        assert "s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" in src

    def test_loadChart_function(self):
        src = _read("templates/trading_terminal.html")
        assert "function loadChart()" in src

    def test_chart_symbol_variable(self):
        src = _read("templates/trading_terminal.html")
        assert "currentSymbol" in src

    def test_chart_interval_variable(self):
        src = _read("templates/trading_terminal.html")
        assert "currentInterval" in src


# ═══════════════════════════════════════════════════════════════════
# 10) INLINE JS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

class TestInlineJavaScript:
    """Key inline JS functions must exist."""

    def test_connectMarketWS_function(self):
        src = _read("templates/trading_terminal.html")
        assert "function connectMarketWS()" in src

    def test_onWatchlistTickers_function(self):
        src = _read("templates/trading_terminal.html")
        assert "function onWatchlistTickers(" in src

    def test_renderActivity_function(self):
        src = _read("templates/trading_terminal.html")
        assert "function renderActivity(" in src

    def test_loadNews_function(self):
        src = _read("templates/trading_terminal.html")
        assert "function loadNews(" in src

    def test_openNewsDetail_function(self):
        src = _read("templates/trading_terminal.html")
        assert "function openNewsDetail(" in src

    def test_market_ws_connection(self):
        src = _read("templates/trading_terminal.html")
        assert "connectMarketWS()" in src

    def test_activity_ws_connection(self):
        src = _read("templates/trading_terminal.html")
        assert "connectActivityWS()" in src


# ═══════════════════════════════════════════════════════════════════
# 11) NEWS MODAL
# ═══════════════════════════════════════════════════════════════════

class TestNewsModal:
    """News detail modal must exist."""

    def test_news_modal_exists(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="news-detail-modal"' in src

    def test_news_modal_title(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="news-modal-title"' in src

    def test_news_modal_impact(self):
        src = _read("templates/trading_terminal.html")
        assert 'id="news-modal-impact"' in src


# ═══════════════════════════════════════════════════════════════════
# 12) CSS LAYOUT STRUCTURE
# ═══════════════════════════════════════════════════════════════════

class TestCSSLayout:
    """Dark professional trading terminal styling."""

    def test_terminal_wrap_class(self):
        src = _read("templates/trading_terminal.html")
        assert "terminal-wrap" in src

    def test_dark_background(self):
        src = _read("templates/trading_terminal.html")
        assert "#06080D" in src or "--bg-primary" in src

    def test_chart_area_class(self):
        src = _read("templates/trading_terminal.html")
        assert "chart-area" in src

    def test_responsive_media_query(self):
        src = _read("templates/trading_terminal.html")
        assert "@media" in src
        assert "768px" in src
