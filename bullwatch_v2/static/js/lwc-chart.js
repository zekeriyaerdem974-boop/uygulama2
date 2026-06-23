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
    lastHeartbeatTime: 0,
    volumeVisible: false,  // FIX #3: Track volume visibility state
    typewriterTimeouts: [],  // FIX #2: Store typewriter timeouts for cleanup
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

    // Ensure container has dynamic height from flex parent
    function updateChartSize() {
      var h = container.clientHeight;
      if (h > 0 && state.chartInstance) {
        state.chartInstance.applyOptions({ height: h });
      }
    }

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
      crosshair: {
        mode: 0,  // FIX #1: Normal mode (not magnet) - cursor follows mouse freely
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
      priceScaleId: '',  // CRITICAL: Separate volume to own scale (not main price axis)
      visible: false,  // FIX #3: Start hidden - user toggles with [Vol] button
      scaleMargins: {
        top: 0.8,   // Mumlar %80'ini işgal etsin
        bottom: 0,  // Hacim sadece altta %20'de
      },
    });

    // FIX #4: RSI & MACD sub-panels (separate price scale)
    var rsiSeries = chart.addLineSeries({
      color: '#FFB800',  // Orange for RSI
      lineWidth: 1,
      priceScaleId: 'rsi',  // Separate scale for RSI (0-100)
      visible: false,  // Start hidden - toggle with [RSI] button
    });

    var macdSeries = chart.addLineSeries({
      color: '#00D4FF',  // Cyan for MACD
      lineWidth: 1,
      priceScaleId: 'macd',  // Separate scale for MACD
      visible: false,  // Start hidden - toggle with [MACD] button
    });

    var macdSignalSeries = chart.addLineSeries({
      color: '#FF6B9D',  // Pink for MACD signal line
      lineWidth: 1,
      lineStyle: 1,  // Dashed
      priceScaleId: 'macd',
      visible: false,
    });

    // Configure RSI price scale (0-100 range)
    chart.priceScale('rsi').applyOptions({
      scaleMargins: {
        top: 0.1,
        bottom: 0.8,  // RSI at bottom 20%
      },
    });

    // Configure MACD price scale (centered around 0)
    chart.priceScale('macd').applyOptions({
      scaleMargins: {
        top: 0.1,
        bottom: 0.8,
      },
    });

    state.chartInstance = {
      chart: chart,
      candleSeries: candleSeries,
      volumeSeries: volumeSeries,
      rsiSeries: rsiSeries,
      macdSeries: macdSeries,
      macdSignalSeries: macdSignalSeries,
      rsiVisible: false,  // FIX #4: Track indicator visibility
      macdVisible: false,
    };

    // ResizeObserver: Monitor container size changes and update chart
    try {
      var resizeObserver = new ResizeObserver(function(entries) {
        if (entries.length === 0 || entries[0].target !== container) return;
        var newRect = entries[0].contentRect;
        if (newRect.width > 0 && newRect.height > 0) {
          if (state.chartInstance && state.chartInstance.chart) {
            state.chartInstance.chart.applyOptions({
              width: Math.floor(newRect.width),
              height: Math.floor(newRect.height)
            });
            console.log('[LWC-RESIZE] 📏 Chart resized to', Math.floor(newRect.width), 'x', Math.floor(newRect.height));
          }
        }
      });
      resizeObserver.observe(container);
      console.log('[LWC-FAZE5] ✅ ResizeObserver attached to chart container');
    } catch (e) {
      console.warn('[LWC-FAZE5] ⚠️ ResizeObserver not supported, using window resize fallback');
    }

    // Bind window resize to update chart height dynamically (fallback)
    window.addEventListener('resize', function() {
      var h = container.clientHeight;
      if (h > 0 && state.chartInstance && state.chartInstance.chart) {
        state.chartInstance.chart.applyOptions({ height: h });
      }
    });

    setTimeout(function() {
      chart.timeScale().fitContent();
    }, 100);

    console.log('[LWC-FAZE5] ✅ Chart initialized with dynamic resize');
  }

  /**
   * FAZE 5: Load historical candles from REST endpoint
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

        console.log('[LWC-FAZE5] ✅ Got ' + data.count + ' candles');
        state.candleData = data.candles;

        var lwcCandles = data.candles.map(function(c) {
          return {
            time: Math.floor(c.time / 1000),
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume,
          };
        });

        paintChart(lwcCandles);
        if (typeof callback === 'function') callback(lwcCandles);
      })
      .catch(function(err) {
        console.error('[LWC-FAZE5] ❌ Historical fetch failed:', err);
      });
  }

  /**
   * Paint chart with candles + volumes
   * CRITICAL: Volume data MUST NOT contaminate candlestick price scale
   * candleData: ONLY open/high/low/close (no volume)
   * volumeData: ONLY time/value (separate histogram scale)
   */
  function paintChart(candles) {
    if (!state.chartInstance) return;

    var candleData = [];
    var volumeData = [];

    candles.forEach(function(c) {
      // Candlestick data: PURE price data, NO volume
      candleData.push({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        // ⚠️ MUST NOT add: volume, price scale will be contaminated
      });

      // Volume histogram: SEPARATE data, will use its own isolated scale
      volumeData.push({
        time: c.time,
        value: c.volume,  // Volume value ONLY here
        color: c.close >= c.open ? 'rgba(22,199,132,0.3)' : 'rgba(255,77,109,0.3)',
      });
    });

    console.log('[LWC-FAZE5] 🎨 Painting ' + candleData.length + ' candles');
    state.chartInstance.candleSeries.setData(candleData);
    if (volumeData.length > 0) {
      state.chartInstance.volumeSeries.setData(volumeData);
    }

    // FIX #4: Calculate and populate RSI series
    var rsiData = calculateRSIData(candles);
    if (rsiData.length > 0) {
      state.chartInstance.rsiSeries.setData(rsiData);
    }

    // FIX #4: Calculate and populate MACD series
    var macdData = calculateMACDData(candles);
    if (macdData.macd.length > 0) {
      state.chartInstance.macdSeries.setData(macdData.macd);
      state.chartInstance.macdSignalSeries.setData(macdData.signal);
    }

    state.chartInstance.chart.timeScale().fitContent();
  }

  /**
   * FIX #4: Calculate RSI data series
   */
  function calculateRSIData(candles) {
    var period = 14;
    var closes = candles.map(function(c) { return c.close; });
    var rsiValues = [];

    for (var i = 0; i < closes.length; i++) {
      if (i < period) {
        rsiValues.push(null);  // Not enough data
        continue;
      }

      var gains = 0, losses = 0;
      for (var j = i - period + 1; j <= i; j++) {
        var delta = closes[j] - closes[j - 1];
        if (delta > 0) gains += delta;
        else losses += Math.abs(delta);
      }

      var avgGain = gains / period;
      var avgLoss = losses / period;
      var rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      var rsi = 100 - (100 / (1 + rs));
      rsiValues.push(rsi);
    }

    // Map to LWC format
    return candles.map(function(c, idx) {
      if (rsiValues[idx] === null) return null;
      return {
        time: c.time,
        value: rsiValues[idx]
      };
    }).filter(function(v) { return v !== null; });
  }

  /**
   * FIX #4: Calculate MACD data series
   */
  function calculateMACDData(candles) {
    var closes = candles.map(function(c) { return c.close; });
    var ema12 = calculateEMA(closes, 12);
    var ema26 = calculateEMA(closes, 26);
    var macdLine = [];
    
    for (var i = 0; i < ema12.length; i++) {
      if (ema12[i] !== null && ema26[i] !== null) {
        macdLine.push(ema12[i] - ema26[i]);
      } else {
        macdLine.push(null);
      }
    }

    var signalLine = calculateEMA(macdLine.filter(function(v) { return v !== null; }), 9);

    // Map to LWC format
    var macdData = [];
    var signalData = [];
    var signalIdx = 0;

    for (var i = 0; i < candles.length; i++) {
      if (macdLine[i] !== null) {
        macdData.push({
          time: candles[i].time,
          value: macdLine[i]
        });
      }
      if (i >= 34 && signalIdx < signalLine.length && signalLine[signalIdx] !== null) {
        signalData.push({
          time: candles[i].time,
          value: signalLine[signalIdx]
        });
        signalIdx++;
      }
    }

    return {
      macd: macdData,
      signal: signalData
    };
  }

  /**
   * FIX #4: Calculate EMA (Exponential Moving Average)
   */
  function calculateEMA(data, period) {
    var ema = [];
    var k = 2 / (period + 1);
    var validData = data.filter(function(v) { return v !== null && !isNaN(v); });

    if (validData.length < period) return data.map(function() { return null; });

    // Calculate initial SMA
    var sma = 0;
    for (var i = 0; i < period; i++) {
      sma += validData[i];
    }
    sma /= period;
    ema.push(sma);

    // Calculate EMA for remaining values
    for (var i = period; i < validData.length; i++) {
      var emaValue = validData[i] * k + ema[ema.length - 1] * (1 - k);
      ema.push(emaValue);
    }

    return ema;
  }

  /**
   * FAZE 5: Update last candle with incoming tick
   */
  function onHeartbeat(data) {
    if (!state.chartInstance || !state.candleData || state.candleData.length === 0) return;
    if (!data || typeof data !== 'object') return;

    var tickSymbol = (data.symbol || '').toString().toUpperCase();
    var currentSymbol = (state.currentSymbol || '').toString().toUpperCase();
    if (!tickSymbol || !currentSymbol) return;

    // Accept plain symbol (BTCUSDT) and prefixed symbol (BINANCE:BTCUSDT)
    var normalizedTickSymbol = tickSymbol.indexOf(':') !== -1 ? tickSymbol.split(':').pop() : tickSymbol;
    if (normalizedTickSymbol !== currentSymbol) return;

    var price = parseFloat(data.price);
    if (!price || isNaN(price)) return;

    var lastCandle = state.chartInstance.candleSeries.data()[state.chartInstance.candleSeries.data().length - 1];
    if (!lastCandle) return;

    var updated = {
      time: lastCandle.time,
      open: lastCandle.open,
      high: Math.max(lastCandle.high, price),
      low: Math.min(lastCandle.low, price),
      close: price,
    };

    state.chartInstance.candleSeries.update(updated);

    if (Date.now() - state.lastHeartbeatTime > 5000) {
      console.log('[LWC-FAZE5] 💓 Updated: $' + price.toFixed(2));
      state.lastHeartbeatTime = Date.now();
    }
  }

  /**
   * STEP 3: Update metrics display from WebSocket data
   */
  function updateMetricsFromWebSocket(data) {
    if (!data || !data.metrics) return;
    
    var metrics = data.metrics;
    var safeUpdate = function(id, value) {
      var el = document.getElementById(id);
      if (el && el.innerText !== value) {
        el.innerText = value;
      }
    };
    
    safeUpdate('metric-volume', metrics.volume_24h);
    safeUpdate('metric-oi', metrics.open_interest);
    safeUpdate('metric-fng', metrics.fear_and_greed);
    safeUpdate('metric-funding', metrics.funding_rate);
    safeUpdate('metric-dom', metrics.btc_dominance);
    safeUpdate('metric-sentiment', metrics.sentiment);
  }

  /**
   * Connect to WebSocket
   */
  function connectWebSocket() {
    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var wsUrl = protocol + '//' + window.location.host + '/ws/market-relay';

    console.log('[LWC-FAZE5] 🔌 WebSocket:', wsUrl);
    state.ws = window.io(wsUrl);

    state.ws.on('connect', function() {
      state.isConnected = true;
      console.log('[LWC-FAZE5] ✅ Connected');
    });

    state.ws.on('dummy_heartbeat', onHeartbeat);
    
    // STEP 3: Listen for price_update_batch with enriched metrics
    state.ws.on('price_update_batch', function(data) {
      if (!data) return;
      
      // If data contains prices dict (legacy format)
      if (typeof data === 'object' && data.prices) {
        // Update price for current symbol
        var symbol = state.currentSymbol || 'BTCUSDT';
        var price = data.prices[symbol];
        if (price) {
          onHeartbeat({ symbol: symbol, price: price });
        }
        // Update metrics if present
        if (data.metrics) {
          updateMetricsFromWebSocket(data);
          console.log('[LWC-FAZE5] 📊 Metrics updated from WebSocket');
        }
      }
      // If data contains individual symbols (flat format)
      else if (typeof data === 'object') {
        var symbol = state.currentSymbol || 'BTCUSDT';
        var price = data[symbol];
        if (price) {
          onHeartbeat({ symbol: symbol, price: price });
        }
      }
    });

    state.ws.on('disconnect', function() {
      state.isConnected = false;
      console.warn('[LWC-FAZE5] ⚠️ Disconnected');
    });
  }

  /**
   * Timeframe change handler
   */
  function onTimeframeChange(newInterval) {
    console.log('[LWC-FAZE5] 📊 Timeframe:', newInterval);
    state.currentInterval = newInterval;
    loadHistoricalCandles(state.currentSymbol, newInterval, function(candles) {
      // FAZE 7: Generate AI brief after chart repaints
      setTimeout(function() {
        generateAIBrief(candles, newInterval, state.currentSymbol);
      }, 200);
    });
  }

  /**
   * FAZE 7: Generate AI Educational Market Brief
   */
  function generateAIBrief(candles, interval, symbol) {
    if (!candles || candles.length < 20) {
      console.warn('[LWC-FAZE7] Insufficient candles for AI brief');
      return;
    }

    // Prepare payload for AI analyst
    var payload = {
      candles: candles.map(function(c) {
        return {
          time: c.time * 1000,  // Convert back to ms
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
          volume: c.volume
        };
      }),
      timeframe: interval,
      symbol: symbol
    };

    console.log('[LWC-FAZE7] 🧠 Generating brief for ' + symbol + '/' + interval);

    // Call analytics API
    fetch('/api/v1/market/brief', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    .then(function(resp) {
      if (!resp.ok) throw new Error('API error: ' + resp.status);
      return resp.json();
    })
    .then(function(data) {
      if (!data.ok) {
        console.warn('[LWC-FAZE7] API returned error:', data.error);
        return;
      }

      // Update UI with brief
      var briefContent = document.getElementById('aiBriefContent');
      
      if (!briefContent) {
        console.warn('[LWC-FAZE7] Brief box not found in DOM');
        return;
      }

      // FIX #2: TYPEWRITER REMOVED - Direct innerHTML instead
      // Clear any previous timeouts to prevent race conditions
      state.typewriterTimeouts.forEach(function(t) {
        clearTimeout(t);
      });
      state.typewriterTimeouts = [];

      // Clean fade-out
      briefContent.style.opacity = '0';
      briefContent.style.transition = 'opacity 0.3s ease-in';

      // After fade-out, update content and fade back in
      setTimeout(function() {
        var text = data.brief;
        
        // Convert \n to <br/> and set directly (NO TYPEWRITER)
        var htmlText = text.replace(/\n/g, '<br/>');
        briefContent.innerHTML = htmlText;
        
        console.log('[LWC-FAZE7] ✅ Brief updated (direct HTML)');
        console.log('[LWC-FAZE7] Content:', text.substring(0, 100) + '...');
        
        // Fade back in
        briefContent.style.opacity = '1';
      }, 100);

      console.log('[LWC-FAZE7] ✅ Brief updated');
    })
    .catch(function(err) {
      console.error('[LWC-FAZE7] Error:', err);
      var briefContent = document.getElementById('aiBriefContent');
      if (briefContent) {
        briefContent.innerHTML = '❌ Analiz hatası. Lütfen sayfayı yenileyin.';
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
        buttons.forEach(function(b) {
          b.classList.remove('active');
        });
        this.classList.add('active');
        onTimeframeChange(interval);
      });
    });
    console.log('[LWC-FAZE5] ✅ Bound ' + buttons.length + ' buttons');
  }

  /**
   * Symbol dropdown change handler
   */
  function bindSymbolDropdown() {
    var dropdown = document.getElementById('ctrlSymbol');
    if (!dropdown) {
      console.warn('[LWC-Symbol] Dropdown not found');
      return;
    }

    dropdown.addEventListener('change', function(e) {
      e.preventDefault();
      var rawSymbol = this.value || 'BTCUSDT';
      
      // Extract symbol from "EXCHANGE:SYMBOL" format (e.g., "BINANCE:BTCUSDT" → "BTCUSDT")
      var newSymbol = rawSymbol;
      if (rawSymbol.includes(':')) {
        newSymbol = rawSymbol.split(':')[1];
      }
      newSymbol = newSymbol.toUpperCase();

      console.log('[LWC-Symbol] 📊 Dropdown changed: raw=' + rawSymbol + ', normalized=' + newSymbol);
      
      if (newSymbol && newSymbol !== state.currentSymbol) {
        state.currentSymbol = newSymbol;
        // Reload chart for new symbol (keep current timeframe)
        onSymbolChange(newSymbol, state.currentInterval);
      }
    });
    console.log('[LWC-Symbol] ✅ Symbol dropdown bound');
  }

  /**
   * Handle symbol change - reload chart with new symbol
   */
  function onSymbolChange(newSymbol, interval) {
    console.log('[LWC-Symbol] 🔄 Loading ' + newSymbol + ' / ' + interval);
    state.currentSymbol = newSymbol;
    
    loadHistoricalCandles(newSymbol, interval, function(candles) {
      // Generate new AI brief for new symbol
      setTimeout(function() {
        generateAIBrief(candles, interval, newSymbol);
      }, 300);
    });
  }

  /**
   * FIX #3: Volume toggle button handler
   */
  function bindVolumeButton() {
    var volBtn = document.querySelector('[data-ind="VOL"]');
    if (!volBtn) {
      console.warn('[LWC-UX-FIX3] VOL button not found');
      return;
    }

    volBtn.addEventListener('click', function(e) {
      e.preventDefault();
      
      if (!state.chartInstance || !state.chartInstance.volumeSeries) {
        console.warn('[LWC-UX-FIX3] Volume series not available');
        return;
      }

      // Toggle volume visibility
      state.volumeVisible = !state.volumeVisible;
      
      state.chartInstance.volumeSeries.applyOptions({
        visible: state.volumeVisible
      });

      // Visual feedback: toggle button highlight
      if (state.volumeVisible) {
        volBtn.classList.add('active');
        console.log('[LWC-UX-FIX3] ✅ Volume visible');
      } else {
        volBtn.classList.remove('active');
        console.log('[LWC-UX-FIX3] ✅ Volume hidden');
      }
    });
  }

  /**
   * FIX #4: RSI/MACD indicator toggle button handlers
   */
  function bindIndicatorButtons() {
    var rsiBtn = document.querySelector('[data-ind="RSI"]');
    var macdBtn = document.querySelector('[data-ind="MACD"]');
    var bbBtn = document.querySelector('[data-ind="BB"]');
    var emaBtn = document.querySelector('[data-ind="EMA"]');

    // RSI Toggle
    if (rsiBtn) {
      rsiBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (!state.chartInstance) return;

        state.chartInstance.rsiVisible = !state.chartInstance.rsiVisible;
        state.chartInstance.rsiSeries.applyOptions({
          visible: state.chartInstance.rsiVisible
        });

        if (state.chartInstance.rsiVisible) {
          rsiBtn.classList.add('active');
          console.log('[LWC-UX-FIX4] ✅ RSI visible');
        } else {
          rsiBtn.classList.remove('active');
          console.log('[LWC-UX-FIX4] ✅ RSI hidden');
        }
      });
    }

    // MACD Toggle
    if (macdBtn) {
      macdBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (!state.chartInstance) return;

        state.chartInstance.macdVisible = !state.chartInstance.macdVisible;
        state.chartInstance.macdSeries.applyOptions({
          visible: state.chartInstance.macdVisible
        });
        state.chartInstance.macdSignalSeries.applyOptions({
          visible: state.chartInstance.macdVisible
        });

        if (state.chartInstance.macdVisible) {
          macdBtn.classList.add('active');
          console.log('[LWC-UX-FIX4] ✅ MACD visible');
        } else {
          macdBtn.classList.remove('active');
          console.log('[LWC-UX-FIX4] ✅ MACD hidden');
        }
      });
    }

    // Placeholder handlers for BB and EMA
    if (bbBtn) {
      bbBtn.addEventListener('click', function(e) {
        e.preventDefault();
        console.log('[LWC-UX-FIX4] ⏳ Bollinger Bands coming soon');
      });
    }

    if (emaBtn) {
      emaBtn.addEventListener('click', function(e) {
        e.preventDefault();
        console.log('[LWC-UX-FIX4] ⏳ EMA coming soon');
      });
    }
  }

  /**
   * Bind AI Toggle Button
   * Toggle visibility of AI Brief Box with accordion logic
   */
  function bindAIToggle() {
    var btnAI = document.getElementById('btnToggleAI');
    var boxAI = document.getElementById('aiBriefBox');

    if (!btnAI || !boxAI) {
      console.warn('[LWC-AI-TOGGLE] ⚠️ AI toggle elements not found');
      return;
    }

    btnAI.addEventListener('click', function() {
      console.log('[LWC-AI-TOGGLE] Toggling AI Brief Box');

      // Vanilla JS toggle: if hidden, show; if shown, hide
      if (boxAI.style.display === 'none') {
        boxAI.style.display = '';
        btnAI.classList.add('active');
        console.log('[LWC-AI-TOGGLE] ✅ AI Brief Box shown');
      } else {
        boxAI.style.display = 'none';
        btnAI.classList.remove('active');
        console.log('[LWC-AI-TOGGLE] 🙈 AI Brief Box hidden');
      }

      // Trigger chart resize to adapt to new container height
      // (ResizeObserver will auto-fire, but we can force it manually if needed)
      if (state.chartInstance && state.chartInstance.chart) {
        setTimeout(function() {
          var h = document.getElementById('tvMainChart').clientHeight;
          if (h > 0) {
            state.chartInstance.chart.applyOptions({ height: h });
            console.log('[LWC-AI-TOGGLE] 📏 Chart resized to', h, 'px');
          }
        }, 100);
      }
    });

    console.log('[LWC-AI-TOGGLE] ✅ AI toggle button bound');
  }

  /**
   * Update Market Metrics - Mock Engine
   * Populates dashboard metrics with realistic market data
   */
  function updateMarketMetrics() {
    console.log('[LWC-METRICS] 🔍 Starting metrics update...');

    // Get metric display elements
    var volumeEl = document.getElementById('metric-volume');
    var oiEl = document.getElementById('metric-oi');
    var fngEl = document.getElementById('metric-fng');
    var fundingEl = document.getElementById('metric-funding');
    var domEl = document.getElementById('metric-dom');
    var sentimentEl = document.getElementById('metric-sentiment');

    console.log('[LWC-METRICS] Element check:');
    console.log('  metric-volume:', volumeEl ? '✓ FOUND' : '❌ MISSING');
    console.log('  metric-oi:', oiEl ? '✓ FOUND' : '❌ MISSING');
    console.log('  metric-fng:', fngEl ? '✓ FOUND' : '❌ MISSING');
    console.log('  metric-funding:', fundingEl ? '✓ FOUND' : '❌ MISSING');
    console.log('  metric-dom:', domEl ? '✓ FOUND' : '❌ MISSING');
    console.log('  metric-sentiment:', sentimentEl ? '✓ FOUND' : '❌ MISSING');

    if (!volumeEl || !oiEl || !fngEl || !fundingEl || !domEl || !sentimentEl) {
      console.error('[LWC-METRICS] ❌ CRITICAL: Some metric elements not found in DOM');
      return;
    }

    // Mock market data (realistic simulation)
    var mockData = {
      volume: '$42.8B',           // 24H BTC spot volume
      oi: '$18.2B',               // BTC futures open interest
      fng: 65,                    // Fear & Greed Index (0-100 scale, 65=Greed zone)
      fngStatus: 'Greed',         // Text label
      funding: '0.0100%',         // BTC perp funding rate
      dom: '53.4%',               // BTC dominance
      sentiment: 'Bullish',       // Market sentiment
    };

    // Update DOM with styled values
    volumeEl.textContent = mockData.volume;
    volumeEl.style.color = '#16C784';  // Green
    volumeEl.style.fontWeight = 'bold';
    volumeEl.style.fontSize = '13px';

    oiEl.textContent = mockData.oi;
    oiEl.style.color = '#60a5fa';  // Blue
    oiEl.style.fontWeight = 'bold';
    oiEl.style.fontSize = '13px';

    fngEl.innerHTML = mockData.fng + ' (' + mockData.fngStatus + ')';
    fngEl.style.color = '#16C784';  // Green (Greed)
    fngEl.style.fontWeight = 'bold';
    fngEl.style.fontSize = '13px';

    fundingEl.textContent = mockData.funding;
    fundingEl.style.color = '#16C784';  // Green
    fundingEl.style.fontWeight = 'bold';
    fundingEl.style.fontSize = '13px';

    domEl.textContent = mockData.dom;
    domEl.style.color = '#fbbf24';  // Amber
    domEl.style.fontWeight = 'bold';
    domEl.style.fontSize = '13px';

    sentimentEl.textContent = mockData.sentiment;
    sentimentEl.style.color = '#16C784';  // Green
    sentimentEl.style.fontWeight = 'bold';
    sentimentEl.style.fontSize = '13px';

    console.log('[LWC-METRICS] ✅ ALL metrics updated:', mockData);
  }

  /**
   * Main init
   */
  function init() {
    console.log('[LWC-FAZE5] 🚀 Initializing...');

    if (typeof window.LightweightCharts === 'undefined') {
      console.log('[LWC-FAZE5] ⏳ Waiting for LWC...');
      setTimeout(init, 500);
      return;
    }

    initChart();
    bindTimeframeButtons();
    bindSymbolDropdown();  // Bind symbol dropdown change handler
    bindVolumeButton();  // FIX #3: Bind volume toggle button
    bindIndicatorButtons();  // FIX #4: Bind RSI/MACD toggle buttons
    bindAIToggle();  // FIX #5: Bind AI toggle button (accordion logic)
    updateMarketMetrics();  // Update dashboard metrics with mock data
    loadHistoricalCandles(state.currentSymbol, state.currentInterval, function(candles) {
      // FAZE 7: Generate AI brief on page load
      setTimeout(function() {
        generateAIBrief(candles, state.currentInterval, state.currentSymbol);
      }, 300);
    });
    setTimeout(connectWebSocket, 500);
    console.log('[LWC-FAZE5] ✅ Ready');
  }

  window.lwcChartFaze5 = {
    init: init,
    onHeartbeat: onHeartbeat,
    onTimeframeChange: onTimeframeChange,
    state: state,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
