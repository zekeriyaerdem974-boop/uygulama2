/**
 * Lightweight Charts Integration — FAZE 5
 * Historical Backfill + Live Tick Sync
 * 
 * Architecture:
 * 1. Chart Initialize: Create LWC instance
 * 2. Historical Load: Fetch last 200 candles via /api/v1/chart/historical
 * 3. Canvas Paint: candleSeries.setData(candles) - instant 200-candle display
 * 4. WebSocket Connect: Listen to /ws/market-relay for 'dummy_heartbeat'
 * 5. Live Update: Update last candle with incoming tick (close, high, low)
 * 6. Timeframe Sync: Re-fetch and re-paint when user clicks 15m/1h/4h/1d buttons
 */

(function() {
  'use strict';

  // Global state
  window.lwcChart = {
    currentSymbol: 'BTCUSDT',
    currentInterval: '1h',  // 15m, 1h, 4h, 1d, 1w
    chartInstance: null,
    candleData: [],  // Last fetched candles
    ws: null,
    isConnected: false,
    lastHeartbeatTime: 0
  };

  var state = window.lwcChart;

  /**
   * Initialize Lightweight Charts
   */
  function initChart() {
    var container = document.getElementById('tvMainChart');
    if (!container) {
      console.warn('[LWC-FAZE5] tvMainChart container not found');
      return;
    }

    container.innerHTML = '';
    var canvasDiv = document.createElement('div');
    canvasDiv.id = 'lwc-canvas-container';
    canvasDiv.style.cssText = 'width:100%;height:100%;background:#000;position:relative;';
    container.appendChild(canvasDiv);

    if (typeof window.LightweightCharts === 'undefined') {
      console.error('[LWC-FAZE5] LightweightCharts not loaded');
      setTimeout(initChart, 1000);
      return;
    }

    var LWC = window.LightweightCharts;

    var chart = LWC.createChart(canvasDiv, {
      layout: {
        background: { color: '#000000' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.03)' },
        horzLines: { color: 'rgba(255,255,255,0.03)' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: false,
      },
      watermark: {
        visible: false,
      },
    });

    var candleSeries = chart.addCandlestickSeries({
      upColor: '#16C784',
      downColor: '#FF4D6D',
      borderUpColor: '#16C784',
      borderDownColor: '#FF4D6D',
      wickUpColor: '#16C784',
      wickDownColor: '#FF4D6D',
    });

    var volumeSeries = chart.addHistogramSeries({
      color: 'rgba(100,150,200,0.3)',
      priceFormat: { type: 'volume' },
    });

    state.chartInstance = {
      chart: chart,
      candleSeries: candleSeries,
      volumeSeries: volumeSeries,
    };

    setTimeout(function() {
      chart.timeScale().fitContent();
    }, 100);

    console.log('[LWC-FAZE5] ✅ Chart initialized');
  }

  /**
   * FAZE 5: Load historical candles from REST endpoint
   * Fetches last 200 candles for given symbol/interval
   */
  function loadHistoricalCandles(symbol, interval, callback) {
    console.log('[LWC-FAZE5] 📥 Fetching historical candles:', symbol, interval);

    var url = '/api/v1/chart/historical?symbol=' + encodeURIComponent(symbol) 
            + '&interval=' + encodeURIComponent(interval) 
            + '&limit=200';

    fetch(url)
      .then(function(response) {
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
      })
      .then(function(data) {
        if (!data.ok || !data.candles) {
          throw new Error(data.error || 'No candles in response');
        }

        console.log('[LWC-FAZE5] ✅ Got ' + data.count + ' candles for ' + symbol + '/' + interval);

        // Store candles locally
        state.candleData = data.candles;

        // Transform to LWC format (time must be in seconds for LWC)
        var lwcCandles = data.candles.map(function(c) {
          return {
            time: Math.floor(c.time / 1000),  // Convert ms to seconds
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume,
          };
        });

        // Paint canvas immediately
        paintChart(lwcCandles);

        // Callback for timeframe sync
        if (typeof callback === 'function') callback(lwcCandles);
      })
      .catch(function(err) {
        console.error('[LWC-FAZE5] ❌ Historical fetch failed:', err);
        // Show error on chart
        if (state.chartInstance) {
          state.chartInstance.chart.applyOptions({
            watermark: {
              visible: true,
              text: '⚠ Load failed: ' + err.message,
              fontSize: 14,
              color: '#FF4D6D',
            }
          });
        }
      });
  }

  /**
   * Paint chart with candles + volumes
   */
  function paintChart(candles) {
    if (!state.chartInstance) return;

    var candleData = [];
    var volumeData = [];

    candles.forEach(function(c) {
      candleData.push({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      });

      volumeData.push({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(22,199,132,0.3)' : 'rgba(255,77,109,0.3)',
      });
    });

    console.log('[LWC-FAZE5] 🎨 Painting ' + candleData.length + ' candles');

    state.chartInstance.candleSeries.setData(candleData);
    if (volumeData.length > 0) {
      state.chartInstance.volumeSeries.setData(volumeData);
    }

    state.chartInstance.chart.timeScale().fitContent();
  }

  /**
   * FAZE 5: Update last candle with incoming tick
   * Called by WebSocket 'dummy_heartbeat' listener
   */
  function onHeartbeat(data) {
    if (!state.chartInstance || !state.candleData || state.candleData.length === 0) return;

    var price = parseFloat(data.price);
    var volume = parseFloat(data.volume || 0);
    if (!price || isNaN(price)) return;

    var now = Math.floor(Date.now() / 1000);
    var lastCandle = state.chartInstance.candleSeries.data()[state.chartInstance.candleSeries.data().length - 1];

    if (!lastCandle) return;

    // If tick is for current candle's timeframe
    if (lastCandle.time === now || Math.abs(lastCandle.time - now) < 60) {
      // Update last candle's OHLC
      var updated = {
        time: lastCandle.time,
        open: lastCandle.open,
        high: Math.max(lastCandle.high, price),
        low: Math.min(lastCandle.low, price),
        close: price,
      };

      // Update candle
      state.chartInstance.candleSeries.update(updated);

      // Log
      if (Date.now() - state.lastHeartbeatTime > 5000) {  // Log every 5s to avoid spam
        console.log('[LWC-FAZE5] 💓 Updated last candle: $' + price.toFixed(2));
        state.lastHeartbeatTime = Date.now();
      }
    }
  }

  /**
   * Connect to WebSocket and listen for ticks
   */
  function connectWebSocket() {
    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var wsUrl = protocol + '//' + window.location.host + '/ws/market-relay';

    console.log('[LWC-FAZE5] 🔌 Connecting to WebSocket:', wsUrl);

    state.ws = window.io(wsUrl);

    state.ws.on('connect', function() {
      state.isConnected = true;
      console.log('[LWC-FAZE5] ✅ WebSocket connected');
    });

    state.ws.on('dummy_heartbeat', function(data) {
      onHeartbeat(data);
    });

    state.ws.on('disconnect', function() {
      state.isConnected = false;
      console.warn('[LWC-FAZE5] ⚠️ WebSocket disconnected');
    });

    state.ws.on('error', function(err) {
      console.error('[LWC-FAZE5] WebSocket error:', err);
    });
  }

  /**
   * Timeframe button handler
   * Fetches new historical data and re-paints chart
   */
  function onTimeframeChange(newInterval) {
    console.log('[LWC-FAZE5] 📊 Timeframe changed to:', newInterval);
    state.currentInterval = newInterval;

    // Show loading state
    if (state.chartInstance) {
      state.chartInstance.chart.applyOptions({
        watermark: {
          visible: true,
          text: 'Loading ' + newInterval + '...',
          fontSize: 12,
          color: '#888',
        }
      });
    }

    // Fetch and paint new candles
    loadHistoricalCandles(state.currentSymbol, newInterval, function() {
      // Hide loading state
      if (state.chartInstance) {
        state.chartInstance.chart.applyOptions({
          watermark: { visible: false }
        });
      }
    });
  }

  /**
   * Bind timeframe buttons
   */
  function bindTimeframeButtons() {
    var buttons = document.querySelectorAll('[data-timeframe]');
    buttons.forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var interval = this.getAttribute('data-timeframe');
        
        // Update active button styling
        buttons.forEach(function(b) {
          b.classList.remove('active');
        });
        btn.classList.add('active');

        onTimeframeChange(interval);
      });
    });
    
    console.log('[LWC-FAZE5] ✅ Bound ' + buttons.length + ' timeframe buttons');
  }

  /**
   * Main initialization
   */
  function init() {
    console.log('[LWC-FAZE5] 🚀 Initializing Lightweight Charts (FAZE 5)');

    // Wait for LWC library
    if (typeof window.LightweightCharts === 'undefined') {
      console.log('[LWC-FAZE5] ⏳ Waiting for LightweightCharts library...');
      setTimeout(init, 500);
      return;
    }

    // Step 1: Initialize chart
    initChart();

    // Step 2: Bind timeframe buttons
    bindTimeframeButtons();

    // Step 3: Load historical candles
    loadHistoricalCandles(state.currentSymbol, state.currentInterval);

    // Step 4: Connect WebSocket
    setTimeout(function() {
      connectWebSocket();
    }, 500);

    console.log('[LWC-FAZE5] ✅ Initialization complete');
  }

  // Export functions to window for testing
  window.lwcChartFaze5 = {
    init: init,
    onHeartbeat: onHeartbeat,
    onTimeframeChange: onTimeframeChange,
    loadHistoricalCandles: loadHistoricalCandles,
    state: state,
  };

  // Auto-initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
