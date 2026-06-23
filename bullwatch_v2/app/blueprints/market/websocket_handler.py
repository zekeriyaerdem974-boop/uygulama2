# -*- coding: utf-8 -*-
"""
WebSocket handlers for Market Data Relay

Namespace: /ws/market-relay

HEARTBEAT PROTOCOL IMPLEMENTATION:
  1. Client connects → receives relay_connected event + [WS RELAY] 🟢 logged
  2. Client subscribes to BTCUSDT
  3. Relay publishes heartbeat every 1.5s via dummy_heartbeat event
  4. Chart updates candlestick with new price
"""

from __future__ import annotations

import logging

_logger = logging.getLogger("zkr_analiz.market_relay_ws")

# ═════════════════════════════════════════════════════════════════════════════
# MARKET RELAY WEBSOCKET HANDLERS (Simple emit-based approach)
# ═════════════════════════════════════════════════════════════════════════════

def register_market_relay_handlers(socketio_instance):
    """
    Register market relay WebSocket handlers using Flask-SocketIO emit patterns
    
    Namespace: /ws/market-relay
    """
    
    @socketio_instance.on('connect', namespace='/ws/market-relay')
    def on_connect(sid, environ):
        """Client connected to market relay"""
        _logger.info(f"[WS Market Relay] ✅ Client {sid} connected to /ws/market-relay")
        
        # Emit connection confirmation
        socketio_instance.emit('relay_connected', {
            'status': 'connected',
            'namespace': '/ws/market-relay'
        }, namespace='/ws/market-relay', to=sid)
    
    @socketio_instance.on('disconnect', namespace='/ws/market-relay')
    def on_disconnect(sid):
        """Client disconnected"""
        _logger.info(f"[WS Market Relay] ❌ Client {sid} disconnected")
    
    @socketio_instance.on('subscribe', namespace='/ws/market-relay')
    def on_subscribe(data, sid):
        """Client subscribes to symbol"""
        symbol = (data or {}).get('symbol', '').upper()
        _logger.info(f"[WS Market Relay] 📊 {sid} subscribed to {symbol}")
        socketio_instance.emit('subscribed', {'symbol': symbol}, namespace='/ws/market-relay', to=sid)
    
    @socketio_instance.on('unsubscribe', namespace='/ws/market-relay')
    def on_unsubscribe(data, sid):
        """Client unsubscribes"""
        symbol = (data or {}).get('symbol', '').upper()
        _logger.info(f"[WS Market Relay] 🔕 {sid} unsubscribed from {symbol}")
    
    @socketio_instance.on('ping', namespace='/ws/market-relay')
    def on_ping(sid):
        """Keepalive"""
        socketio_instance.emit('pong', {}, namespace='/ws/market-relay', to=sid)
    
    _logger.info("✅ [WS Market Relay] Handlers registered via emit patterns")
