/* =====================================================================
   ZKR Analiz Market Stream — FAZ 26
   Real-time WebSocket client for kline + watchlist data.

   Architecture:
     Browser  ──WS──→  /ws/market  ──→  Binance upstream kline WS
                                    └─→  cached watchlist ticker push

   Integration:
     • chartManager.updateTick(tick)       — real-time candle update
     • watchlistManager.updateTickers(arr) — live price DOM update
     • Falls back to REST polling when WS disconnects
   ===================================================================== */

const MarketStream = (() => {
  // ── State ─────────────────────────────────────────────────────────
  let _ws = null;
  let _connected = false;
  let _intentionalClose = false;
  let _reconnectTimer = null;
  let _reconnectDelay = 1000;          // starts at 1s, exponential backoff
  const _MAX_RECONNECT = 30000;        // cap at 30s
  let _keepaliveTimer = null;

  let _subscribedSymbol = null;
  let _subscribedMarket = null;
  let _subscribedInterval = null;

  // Fallback polling state
  let _fallbackChartTimer = null;
  let _fallbackWatchlistTimer = null;
  let _usingFallback = false;

  // ── Public: connect ───────────────────────────────────────────────
  function connect() {
    if (_ws && (_ws.readyState === WebSocket.CONNECTING ||
                _ws.readyState === WebSocket.OPEN)) return;

    _intentionalClose = false;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/market`;

    try {
      _ws = new WebSocket(url);
    } catch (e) {
      console.warn('[MarketStream] WS create failed:', e);
      _scheduleReconnect();
      return;
    }

    _ws.onopen = _onOpen;
    _ws.onmessage = _onMessage;
    _ws.onclose = _onClose;
    _ws.onerror = _onError;
  }

  // ── Public: subscribe to kline stream ─────────────────────────────
  function subscribe(symbol, market, interval) {
    _subscribedSymbol = symbol;
    _subscribedMarket = market || 'crypto';
    _subscribedInterval = interval || '15m';

    if (_connected) {
      _sendSubscribe();
    }
    // If not connected yet, _onOpen will call _sendSubscribe
  }

  // ── Public: disconnect ────────────────────────────────────────────
  function disconnect() {
    _intentionalClose = true;
    _stopKeepalive();
    _clearReconnect();
    if (_ws) {
      try { _ws.close(); } catch {}
      _ws = null;
    }
    _connected = false;
  }

  // ── Public: status ────────────────────────────────────────────────
  function isConnected() { return _connected; }

  // ── WS callbacks ──────────────────────────────────────────────────
  function _onOpen() {
    console.log('[MarketStream] connected');
    _connected = true;
    _reconnectDelay = 1000;
    _startKeepalive();
    _stopFallback();
    _updateStatusBadge(true);

    // Re-subscribe to current symbol if any
    if (_subscribedSymbol) {
      _sendSubscribe();
    }
  }

  function _onMessage(evt) {
    let msg;
    try { msg = JSON.parse(evt.data); } catch { return; }

    switch (msg.type) {
      case 'kline':
        _handleKline(msg);
        break;
      case 'watchlist':
        _handleWatchlist(msg);
        break;
      case 'subscribed':
        console.log(`[MarketStream] subscribed: ${msg.symbol} ${msg.interval}`);
        break;
      case 'pong':
        break;   // keepalive ack
      case 'stats':
        console.log('[MarketStream] stats:', msg);
        break;
      default:
        break;
    }
  }

  function _onClose(evt) {
    console.log('[MarketStream] closed, code:', evt.code);
    _connected = false;
    _stopKeepalive();
    _updateStatusBadge(false);

    if (!_intentionalClose) {
      _startFallback();
      _scheduleReconnect();
    }
  }

  function _onError(err) {
    console.warn('[MarketStream] error:', err);
  }

  // ── Send helpers ──────────────────────────────────────────────────
  function _sendSubscribe() {
    _send({
      action: 'subscribe',
      symbol: _subscribedSymbol,
      market: _subscribedMarket,
      interval: _subscribedInterval,
    });
  }

  function _send(obj) {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      try { _ws.send(JSON.stringify(obj)); } catch {}
    }
  }

  // ── Keepalive ─────────────────────────────────────────────────────
  function _startKeepalive() {
    _stopKeepalive();
    _keepaliveTimer = setInterval(() => _send({ action: 'ping' }), 20000);
  }

  function _stopKeepalive() {
    if (_keepaliveTimer) { clearInterval(_keepaliveTimer); _keepaliveTimer = null; }
  }

  // ── Reconnect ─────────────────────────────────────────────────────
  function _scheduleReconnect() {
    _clearReconnect();
    console.log(`[MarketStream] reconnecting in ${_reconnectDelay}ms…`);
    _reconnectTimer = setTimeout(() => {
      _reconnectDelay = Math.min(_reconnectDelay * 2, _MAX_RECONNECT);
      connect();
    }, _reconnectDelay);
  }

  function _clearReconnect() {
    if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
  }

  // ── Kline handler → chart update ──────────────────────────────────
  function _handleKline(tick) {
    // Only update if this tick matches the currently-viewed symbol & interval
    if (!_subscribedSymbol) return;
    if (tick.symbol !== _subscribedSymbol) return;
    if (tick.interval !== _subscribedInterval) return;

    // Guard: skip if in multi-chart mode
    if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) return;

    _updateChart(tick);
  }

  function _updateChart(tick) {
    // chartManager is defined in trade.js
    if (typeof chartManager === 'undefined') return;

    const seriesCandles = chartManager.getCandleSeries();
    const seriesVol = chartManager.getVolSeries();
    if (!seriesCandles || !seriesVol) return;

    const chartType = chartManager.getChartType();
    const candleTick = { time: tick.time, open: tick.open, high: tick.high, low: tick.low, close: tick.close };
    const volColor = tick.close >= tick.open ? 'rgba(38,217,168,.55)' : 'rgba(240,80,110,.55)';

    // LightweightCharts .update() will:
    //   - if time === last bar time → update in-place (intra-candle tick)
    //   - if time > last bar time  → append new bar (candle closed)
    if (chartType === 'line' || chartType === 'area') {
      seriesCandles.update({ time: tick.time, value: tick.close });
    } else {
      seriesCandles.update(candleTick);
    }

    seriesVol.update({ time: tick.time, value: tick.volume, color: volColor });

    // Update chart header
    const lastData = chartManager.getData();
    if (lastData) {
      _mergeLastCandle(lastData, tick);
      // Update OHLC header text
      const hdr = document.getElementById('chartOhlc');
      if (hdr) {
        const _f = (n) => {
          const x = Number(n);
          return Number.isFinite(x) ? x.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—';
        };
        hdr.textContent = `O:${_f(tick.open)} H:${_f(tick.high)} L:${_f(tick.low)} C:${_f(tick.close)}`;
      }
    }
  }

  /**
   * Keep chartManager.lastData in sync so that when the user changes
   * timeframe / symbol the full-refresh has accurate recent data.
   */
  function _mergeLastCandle(lastData, tick) {
    if (!lastData.candles || !lastData.candles.length) return;
    const last = lastData.candles[lastData.candles.length - 1];

    if (last.time === tick.time) {
      // Update existing candle
      last.open = tick.open;
      last.high = tick.high;
      last.low = tick.low;
      last.close = tick.close;
    } else if (tick.time > last.time) {
      // New candle — push it
      lastData.candles.push({
        time: tick.time,
        open: tick.open,
        high: tick.high,
        low: tick.low,
        close: tick.close,
      });
      if (lastData.volume) {
        lastData.volume.push({
          time: tick.time,
          value: tick.volume,
        });
      }
    }
  }

  // ── Watchlist handler → DOM update ────────────────────────────────
  function _handleWatchlist(msg) {
    const tickers = msg.tickers;
    if (!tickers || !Array.isArray(tickers)) return;

    // Only update DOM when viewing crypto market (tickers come from Binance)
    if (typeof activeMarket !== 'undefined' && activeMarket !== 'crypto') return;

    // Build a lookup map: symbol → ticker data
    const tickerMap = {};
    for (const t of tickers) {
      const sym = t.s || t.symbol;
      if (!sym) continue;
      tickerMap[sym] = {
        lastPrice: parseFloat(t.last || t.c || t.lastPrice || 0),
        pct: parseFloat(t.change24_pct || t.P || t.priceChangePercent || 0),
        volume: parseFloat(t.quoteVolume || t.v || t.volume || 0),
      };
    }

    // Update existing DOM elements in-place (no full re-render)
    const items = document.querySelectorAll('#wlList .wl-item');
    for (const el of items) {
      const symEl = el.querySelector('.wl-sym');
      if (!symEl) continue;
      const sym = symEl.textContent.trim();
      const data = tickerMap[sym];
      if (!data) continue;

      const priceEl = el.querySelector('.wl-price');
      const chgEl = el.querySelector('.wl-chg');

      if (priceEl) {
        const oldPrice = parseFloat(priceEl.textContent.replace(/,/g, '')) || 0;
        priceEl.textContent = _fmtPrice(data.lastPrice);
        // Flash effect on price change
        if (data.lastPrice !== oldPrice && oldPrice !== 0) {
          priceEl.classList.remove('flash-up', 'flash-down');
          void priceEl.offsetWidth;  // force reflow
          priceEl.classList.add(data.lastPrice > oldPrice ? 'flash-up' : 'flash-down');
        }
      }

      if (chgEl) {
        const pctVal = data.pct;
        chgEl.textContent = `${pctVal >= 0 ? '+' : ''}${pctVal.toFixed(2)}%`;
        chgEl.classList.remove('up', 'down');
        chgEl.classList.add(pctVal >= 0 ? 'up' : 'down');
      }
    }

    // Also update the current symbol's header price if it matches
    if (typeof currentSymbol !== 'undefined' && tickerMap[currentSymbol]) {
      const t = tickerMap[currentSymbol];
      const hdrPrice = document.getElementById('headerPrice');
      if (hdrPrice) hdrPrice.textContent = _fmtPrice(t.lastPrice);
    }
  }

  function _fmtPrice(n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return '—';
    // Smart decimals: more for small prices
    const d = x >= 100 ? 2 : x >= 1 ? 4 : 6;
    return x.toLocaleString(undefined, { maximumFractionDigits: d });
  }

  // ── Fallback: REST polling when WS is down ────────────────────────
  function _startFallback() {
    if (_usingFallback) return;
    _usingFallback = true;
    console.log('[MarketStream] WS down → falling back to REST polling');

    // Chart polling every 5s (crypto) / 15s (others)
    const chartInterval = (typeof activeMarket !== 'undefined' && activeMarket === 'crypto') ? 5000 : 15000;
    _fallbackChartTimer = setInterval(() => {
      if (typeof refreshFast === 'function') {
        refreshFast().catch(() => {});
      }
    }, chartInterval);

    // Watchlist polling every 30s
    _fallbackWatchlistTimer = setInterval(() => {
      if (typeof watchlistManager !== 'undefined') {
        watchlistManager.load().catch(() => {});
      }
    }, 30000);
  }

  function _stopFallback() {
    if (!_usingFallback) return;
    _usingFallback = false;
    console.log('[MarketStream] WS restored → stopping REST fallback');
    if (_fallbackChartTimer) { clearInterval(_fallbackChartTimer); _fallbackChartTimer = null; }
    if (_fallbackWatchlistTimer) { clearInterval(_fallbackWatchlistTimer); _fallbackWatchlistTimer = null; }
  }

  // ── Status badge ──────────────────────────────────────────────────
  function _updateStatusBadge(connected) {
    let badge = document.getElementById('wsStatusBadge');
    if (!badge) {
      // Create badge next to status pill if it doesn't exist
      const pill = document.getElementById('statusPill');
      if (pill && pill.parentNode) {
        badge = document.createElement('span');
        badge.id = 'wsStatusBadge';
        badge.style.cssText = 'margin-left:8px;font-size:11px;padding:2px 8px;border-radius:8px;font-weight:600;';
        pill.parentNode.insertBefore(badge, pill.nextSibling);
      }
    }
    if (badge) {
      if (connected) {
        badge.textContent = '⚡ LIVE';
        badge.style.background = 'rgba(38,217,168,.18)';
        badge.style.color = '#26d9a8';
      } else {
        badge.textContent = '⏳ REST';
        badge.style.background = 'rgba(240,80,110,.18)';
        badge.style.color = '#f0506e';
      }
    }
  }

  // ── Return public API ─────────────────────────────────────────────
  return {
    connect,
    subscribe,
    disconnect,
    isConnected,
  };
})();
