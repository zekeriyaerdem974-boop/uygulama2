"""Extension singletons for ZKR Analiz.

Provides shared service instances used by the legacy monolith and
new blueprint modules.  Instantiated once at import time; they do
NOT require a Flask app to construct.

Currently managed here:
  - job_manager  (core.job_manager.JobManager)
  - market_data  (core.market_data.MarketDataService)

Still initialized directly in legacy_monolith.py (will migrate later):
  - Flask-CORS   — CORS(app)
  - Flask-Sock   — Sock(app)   (flask-sock 0.7.x requires app at init)
"""
from __future__ import annotations

from core.job_manager import JobManager
from core.market_data import MarketDataService
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging

# ---- Singletons (app-independent) ----
job_manager = JobManager()
market_data = MarketDataService()
db = SQLAlchemy()
migrate = Migrate()

# Enable Socket.IO server-side logging and allow CORS from the frontend dev origin
socketio = SocketIO(cors_allowed_origins="*", logger=True, engineio_logger=True)


@socketio.on('connect')
def _socketio_on_connect(*args, **kwargs):
  logger = logging.getLogger('zkr_analiz.socketio')
  logger.info('Socket.IO client connected %s %s', args, kwargs)


@socketio.on('disconnect')
def _socketio_on_disconnect(*args, **kwargs):
  logger = logging.getLogger('zkr_analiz.socketio')
  logger.info('Socket.IO client disconnected %s %s', args, kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# MARKET RELAY WEBSOCKET NAMESPACE HANDLERS (Registered at import time)
# ─────────────────────────────────────────────────────────────────────────────

@socketio.on('connect', namespace='/ws/market-relay')
def _market_relay_connect(*args, **kwargs):
  """Client connected to market relay namespace"""
  logger = logging.getLogger('zkr_analiz.market_relay_ws')
  # In Socket.IO, args might be (sid, environ) or just ()
  sid = args[0] if len(args) > 0 else 'unknown'
  logger.info(f'[WS Market Relay] ✅ Client {sid} connected to /ws/market-relay')
  socketio.emit('relay_connected', {'status': 'connected'}, namespace='/ws/market-relay')


@socketio.on('disconnect', namespace='/ws/market-relay')
def _market_relay_disconnect(*args, **kwargs):
  """Client disconnected from market relay"""
  logger = logging.getLogger('zkr_analiz.market_relay_ws')
  logger.info(f'[WS Market Relay] ❌ Client disconnected')


@socketio.on('subscribe', namespace='/ws/market-relay')
def _market_relay_subscribe(data, *args, **kwargs):
  """Client subscribes to symbol"""
  logger = logging.getLogger('zkr_analiz.market_relay_ws')
  symbol = (data or {}).get('symbol', 'BTCUSDT').upper()
  logger.info(f'[WS Market Relay] 📊 Client subscribed to {symbol}')
  socketio.emit('subscribed', {'symbol': symbol}, namespace='/ws/market-relay')


@socketio.on('unsubscribe', namespace='/ws/market-relay')
def _market_relay_unsubscribe(data, *args, **kwargs):
  """Client unsubscribes"""
  logger = logging.getLogger('zkr_analiz.market_relay_ws')
  symbol = (data or {}).get('symbol', 'BTCUSDT').upper()
  logger.info(f'[WS Market Relay] 🔕 Client unsubscribed from {symbol}')


@socketio.on('ping', namespace='/ws/market-relay')
def _market_relay_ping(*args, **kwargs):
  """Keepalive ping"""
  socketio.emit('pong', {}, namespace='/ws/market-relay')


def init_extensions(app) -> None:
    """Register singletons on the Flask app.

    Called by create_app() after the legacy monolith is loaded.
    Ensures blueprints can find services via ``current_app.extensions``.
    Uses ``setdefault`` so that if the monolith already registered them,
    the same objects are kept (no duplication).
    """
    app.extensions.setdefault("job_manager", job_manager)
    app.extensions.setdefault("market_data", market_data)
    
    # Initialize SQLAlchemy with the app for Akademi feature (PostgreSQL)
    db.init_app(app)
    app.extensions.setdefault("db", db)
    migrate.init_app(app, db)
    app.extensions.setdefault("migrate", migrate)
    
    # Initialize SocketIO with the app (only once)
    socketio.init_app(app, async_mode="threading", cors_allowed_origins="*")
    app.extensions.setdefault("socketio", socketio)
