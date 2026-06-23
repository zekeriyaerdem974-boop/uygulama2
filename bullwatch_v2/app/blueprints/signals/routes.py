"""Signal API routes (cleaned).
This file provides /api/signal and /api/signals using cached pre-serialized JSON
for minimal latency. Other market endpoints are preserved.
"""
from __future__ import annotations

import time
import json

from flask import jsonify, request, Response

from app.blueprints.signals import signals_bp
from app.blueprints.signals.engine import evaluate_entry_signal
from app.cache import cache_get_or_set, cache_get
from app.core.binance_client import pump_candidates
from app.core.thresholds import get_thresholds
from app.core.universal_signal import evaluate_market_signal, scan_market_signals
from app.core.compliance_filter import filter_api_response


@signals_bp.route('/api/signal')
def api_signal():
    try:
        symbol = request.args.get('symbol')
        if symbol:
            symbol = symbol.upper()
            latest_json = cache_get('latest_signals_json')
            if latest_json:
                try:
                    parsed = json.loads(latest_json)
                    for r in parsed.get('rows', []):
                        if r.get('symbol') == symbol:
                            return jsonify(r)
                except Exception:
                    pass
            latest = cache_get('latest_signals')
            if not latest:
                return jsonify({'ok': False, 'error': 'Sinyaller hesaplanıyor, lütfen bekleyin'}), 503
            for r in latest.get('rows', []):
                if r.get('symbol') == symbol:
                    return jsonify(r)
            return jsonify({'ok': False, 'error': 'Symbol not found in latest_signals'}), 404

        # No symbol -> return top row
        latest_json = cache_get('latest_signals_json')
        if latest_json:
            try:
                parsed = json.loads(latest_json)
                rows = parsed.get('rows', [])
                if rows:
                    return jsonify(rows[0])
            except Exception:
                pass
        latest = cache_get('latest_signals')
        if not latest:
            return jsonify({'ok': False, 'error': 'Sinyaller hesaplanıyor, lütfen bekleyin'}), 503
        rows = latest.get('rows', [])
        if not rows:
            return jsonify({'ok': False, 'error': 'Sinyaller henüz hazır değil'}), 503
        return jsonify({'ok': True, 'data': rows[0]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@signals_bp.route('/api/signals')
def api_signals():
    try:
        latest_json = cache_get('latest_signals_json')
        if latest_json:
            return Response(latest_json, mimetype='application/json')
        latest = cache_get('latest_signals')
        if not latest:
            return jsonify({'ok': False, 'error': 'Sinyaller hesaplanıyor, lütfen bekleyin'}), 503
        return jsonify({'ok': True, 'data': latest})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@signals_bp.route('/api/market-signal')
def api_market_signal():
    symbol = request.args.get('symbol', '').strip()
    market = request.args.get('market', '').strip().lower()
    if not symbol:
        return jsonify({'ok': False, 'error': 'symbol parameter required.'}), 400
    valid_markets = {'stocks', 'bist', 'forex', 'commodities'}
    if market not in valid_markets:
        return jsonify({'ok': False, 'error': f"market must be one of: {', '.join(sorted(valid_markets))}"}), 400
    try:
        cache_key = f'msig:{market}:{symbol}'
        res = cache_get_or_set(cache_key, 120, evaluate_market_signal, symbol, market)
        return jsonify({'ok': True, 'data': res})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@signals_bp.route('/api/market-signals')
def api_market_signals():
    market = request.args.get('market', '').strip().lower()
    limit = min(int(request.args.get('limit', '20')), 50)
    valid_markets = {'stocks', 'bist', 'forex', 'commodities'}
    if market not in valid_markets:
        return jsonify({'ok': False, 'error': f"market must be one of: {', '.join(sorted(valid_markets))}"}), 400
    try:
        from app.core.stocks_data import DEFAULT_SYMBOLS as STOCKS_SYMS
        from app.core.bist_data import DEFAULT_SYMBOLS as BIST_SYMS
        from app.core.forex_data import DEFAULT_SYMBOLS as FOREX_SYMS
        from app.core.commodities_data import DEFAULT_SYMBOLS as COMM_SYMS
        sym_map = {
            'stocks': STOCKS_SYMS,
            'bist': BIST_SYMS,
            'forex': FOREX_SYMS,
            'commodities': COMM_SYMS,
        }
        symbols = sym_map.get(market, [])[:limit]
        cache_key = f'msigs:{market}:{limit}'
        results = cache_get_or_set(cache_key, 300, scan_market_signals, market, symbols, limit)
        return jsonify({'ok': True, 'data': {'market': market, 'count': len(results), 'rows': results}})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
