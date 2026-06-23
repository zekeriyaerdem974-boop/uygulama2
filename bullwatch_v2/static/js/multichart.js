/* =====================================================================
   ZKR Analiz Multi-Chart Manager — FAZ 18
   TradingView-style multi-chart layout system.
   Max 4 independent charts, each with own indicators & patterns.
   ===================================================================== */

const MultiChartManager = (() => {
  'use strict';

  /* ── Constants ─────────────────────────────────────────────────────── */
  const LS_LAYOUT = 'bw_mc_layout';
  const LS_SLOTS  = 'bw_mc_slots';
  const MAX_SLOTS = 4;

  const CHART_OPTS = {
    layout: { background: { color: '#000000' }, textColor: '#e8edf5' },
    grid:   { vertLines: { color: '#18243a' }, horzLines: { color: '#18243a' } },
    rightPriceScale: { borderColor: '#1e2d40' },
    timeScale:       { borderColor: '#1e2d40' },
    crosshair:       { mode: 1 },
  };

  const DEFAULTS = [
    { symbol: 'BTCUSDT',   market: 'crypto' },
    { symbol: 'ETHUSDT',   market: 'crypto' },
    { symbol: 'AAPL',      market: 'stocks' },
    { symbol: 'THYAO.IS',  market: 'bist'   },
  ];

  const SHORT_TF = [
    { key: '15m', label: '15m' },
    { key: '1h',  label: '1H'  },
    { key: '4h',  label: '4H'  },
    { key: '1d',  label: '1D'  },
  ];

  /* ── State ─────────────────────────────────────────────────────────── */
  let layout     = 1;
  let activeSlot = 0;
  const slots    = new Array(MAX_SLOTS).fill(null);
  let _refreshTimer = null;

  /* ══════════════════════════════════════════════════════════════════════
     PERSISTENCE
     ══════════════════════════════════════════════════════════════════════ */

  function _saveState() {
    try {
      localStorage.setItem(LS_LAYOUT, String(layout));
      const data = slots.map(s => s ? {
        symbol:     s.symbol,
        market:     s.market,
        timeframe:  s.timeframe,
        indicators: s.indicators,
      } : null);
      localStorage.setItem(LS_SLOTS, JSON.stringify(data));
    } catch (e) { /* localStorage unavailable */ }
  }

  function _loadState() {
    try {
      const l = Number(localStorage.getItem(LS_LAYOUT));
      if ([1, 2, 4].includes(l)) layout = l;
      const raw = localStorage.getItem(LS_SLOTS);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* ignore */ }
    return null;
  }

  /* ══════════════════════════════════════════════════════════════════════
     HELPERS
     ══════════════════════════════════════════════════════════════════════ */

  function _mc(market) { return MARKET_CONFIG[market] || MARKET_CONFIG.crypto; }

  function _colorizeVol(candles, volume) {
    const map = new Map(candles.map(c => [c.time, c]));
    return volume.map(v => {
      const c = map.get(v.time);
      return {
        ...v,
        color: c && Number(c.close) >= Number(c.open)
          ? 'rgba(38,217,168,.55)' : 'rgba(240,80,110,.55)',
      };
    });
  }

  /* ── Layout Icons (SVG) ────────────────────────────────────────────── */
  function _icon(n) {
    if (n === 1) return '<svg viewBox="0 0 16 16" width="14" height="14"><rect x="1" y="1" width="14" height="14" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
    if (n === 2) return '<svg viewBox="0 0 16 16" width="14" height="14"><rect x="1" y="1" width="6" height="14" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="1" width="6" height="14" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
    return '<svg viewBox="0 0 16 16" width="14" height="14"><rect x="1" y="1" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="1" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="1" y="9" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="9" width="6" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>';
  }

  /* ══════════════════════════════════════════════════════════════════════
     SLOT CREATION / DESTRUCTION
     ══════════════════════════════════════════════════════════════════════ */

  function _createSlot(idx, cfg) {
    const sym  = cfg?.symbol     || DEFAULTS[idx]?.symbol  || 'BTCUSDT';
    const mkt  = cfg?.market     || DEFAULTS[idx]?.market  || 'crypto';
    const tf   = cfg?.timeframe  || '15m';
    const inds = cfg?.indicators || { ema20: true };

    /* ---- DOM structure ---- */
    const container = document.createElement('div');
    container.className = 'mc-slot' + (idx === activeSlot ? ' mc-active' : '');
    container.dataset.slot = idx;

    // Toolbar
    const toolbar = document.createElement('div');
    toolbar.className = 'mc-toolbar';

    // Symbol display
    const marketDot = document.createElement('span');
    marketDot.className = 'mc-market-dot ' + mkt + '-dot';

    const symLabel = document.createElement('span');
    symLabel.className = 'mc-sym-label';
    symLabel.textContent = sym;

    const symWrap = document.createElement('div');
    symWrap.className = 'mc-sym-wrap';
    symWrap.appendChild(marketDot);
    symWrap.appendChild(symLabel);

    // Timeframe buttons
    const tfGroup = document.createElement('div');
    tfGroup.className = 'mc-tf-group';

    // Indicator button + dropdown
    const indWrap = document.createElement('div');
    indWrap.className = 'mc-ind-wrap';

    const indBtn = document.createElement('button');
    indBtn.className = 'mc-ind-btn';
    indBtn.innerHTML = '📊';
    indBtn.title = 'Indicators';

    const indDd = document.createElement('div');
    indDd.className = 'mc-ind-dropdown';

    for (const [key, def] of Object.entries(INDICATOR_DEFS)) {
      const lbl = document.createElement('label');
      lbl.className = 'mc-ind-item';
      lbl.innerHTML =
        '<input type="checkbox" data-ind="' + key + '"' + (inds[key] ? ' checked' : '') + '>'
        + '<span class="ind-color-dot" style="background:' + def.color + '"></span>'
        + '<span>' + def.label + '</span>';
      indDd.appendChild(lbl);
    }

    indWrap.appendChild(indBtn);
    indWrap.appendChild(indDd);

    toolbar.appendChild(symWrap);
    toolbar.appendChild(tfGroup);
    toolbar.appendChild(indWrap);

    // Chart area
    const chartArea = document.createElement('div');
    chartArea.className = 'mc-chart-area';

    container.appendChild(toolbar);
    container.appendChild(chartArea);

    /* ---- Events ---- */
    // Click to activate (except dropdown / tf buttons)
    container.addEventListener('mousedown', (e) => {
      if (e.target.closest('.mc-ind-dropdown') || e.target.closest('.mc-ind-btn')
          || e.target.closest('.mc-tf-btn')) return;
      _setActive(idx);
    });

    // Indicator toggle
    indBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      document.querySelectorAll('.mc-ind-dropdown.mc-ind-open').forEach(d => {
        if (d !== indDd) d.classList.remove('mc-ind-open');
      });
      indDd.classList.toggle('mc-ind-open');
    });

    indDd.addEventListener('change', (e) => {
      const k = e.target.dataset?.ind;
      if (!k || !slots[idx]) return;
      slots[idx].indicators[k] = e.target.checked;
      _updateOverlays(idx);
      _saveState();
    });

    const _closeHandler = (e) => {
      if (!indWrap.contains(e.target)) indDd.classList.remove('mc-ind-open');
    };
    document.addEventListener('click', _closeHandler);

    /* ---- LightweightCharts instance ---- */
    const chart = LightweightCharts.createChart(chartArea, {
      ...CHART_OPTS,
      width:  chartArea.clientWidth  || 400,
      height: chartArea.clientHeight || 300,
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26d9a8', downColor: '#f0506e', borderVisible: false,
      wickUpColor: '#26d9a8', wickDownColor: '#f0506e',
    });

    const volSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      color: 'rgba(91,140,245,.30)',
    });
    volSeries.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (chartArea.clientWidth && chartArea.clientHeight)
        chart.applyOptions({ width: chartArea.clientWidth, height: chartArea.clientHeight });
    });
    ro.observe(chartArea);

    // Render timeframe buttons
    _renderTf(tfGroup, idx, tf);

    /* ---- Slot object ---- */
    const slot = {
      id: idx,
      symbol: sym,
      market: mkt,
      timeframe: tf,
      indicators: { ...inds },
      chart,
      candleSeries,
      volSeries,
      overlays: {},           // indicator overlay series
      patternOverlays: {},    // pattern overlay series
      data: null,
      container,
      symLabel,
      marketDot,
      tfGroup,
      chartArea,
      ro,
      _closeHandler,
    };

    slots[idx] = slot;

    // Register slot with DrawingEngine
    if (typeof DrawingEngine !== 'undefined') {
      DrawingEngine.registerChart('mc-' + idx, chart, candleSeries, chartArea, sym);
    }

    return slot;
  }

  function _destroySlot(idx) {
    const s = slots[idx];
    if (!s) return;
    // Unregister from DrawingEngine
    if (typeof DrawingEngine !== 'undefined') {
      DrawingEngine.unregisterChart('mc-' + idx);
    }
    _clearOverlays(idx);
    _clearPatterns(idx);
    try { s.chart.remove(); } catch (e) { /* ok */ }
    try { s.ro.disconnect(); } catch (e) { /* ok */ }
    try { document.removeEventListener('click', s._closeHandler); } catch (e) { /* ok */ }
    try { s.container.remove(); } catch (e) { /* ok */ }
    slots[idx] = null;
  }

  /* ── Timeframe buttons per slot ────────────────────────────────────── */
  function _renderTf(container, idx, activeTf) {
    container.innerHTML = '';
    for (const t of SHORT_TF) {
      const b = document.createElement('button');
      b.className = 'mc-tf-btn' + (t.key === activeTf ? ' active' : '');
      b.textContent = t.label;
      b.addEventListener('click', (e) => {
        e.stopPropagation();
        setTimeframe(idx, t.key);
      });
      container.appendChild(b);
    }
  }

  /* ══════════════════════════════════════════════════════════════════════
     ACTIVE SLOT MANAGEMENT
     ══════════════════════════════════════════════════════════════════════ */

  function _setActive(idx) {
    const s = slots[idx];
    if (!s || idx === activeSlot) return;
    activeSlot = idx;

    // Visual highlight
    document.querySelectorAll('.mc-slot').forEach(el =>
      el.classList.toggle('mc-active', Number(el.dataset.slot) === idx));

    // Sync globals for right-panel compatibility
    currentSymbol = s.symbol;
    currentTf     = s.timeframe;

    // If market changed → update tabs + watchlist
    if (s.market !== activeMarket) {
      activeMarket = s.market;
      try { localStorage.setItem('bw_active_market', s.market); } catch (e) { /* ok */ }
      document.querySelectorAll('.market-tab').forEach(b =>
        b.classList.toggle('active', b.dataset.market === s.market));
      const badge = document.getElementById('wlMarketBadge');
      const mc = _mc(s.market);
      if (badge) { badge.textContent = mc.label; badge.className = 'market-badge ' + mc.badgeClass; }
      watchlistManager.load().catch(() => {});
    }

    // Update chart header (original, for reference)
    txt('chartSymbol', s.symbol + ' \u2022 ' + s.timeframe);

    // Refresh right panel for active chart
    signalManager.load().catch(() => {});
    if (_mc(s.market).hasOrderflow)   orderflowManager.load().catch(() => {});
    if (_mc(s.market).hasLiquidation) liquidationManager.load().catch(() => {});
  }

  /* ══════════════════════════════════════════════════════════════════════
     INDICATOR OVERLAYS (per slot)
     ══════════════════════════════════════════════════════════════════════ */

  function _clearOverlays(idx) {
    const s = slots[idx]; if (!s) return;
    for (const k of Object.keys(s.overlays)) _removeOverlay(s, k);
    s.overlays = {};
  }

  function _removeOverlay(s, k) {
    const o = s.overlays[k]; if (!o) return;
    if (k === 'bollinger') {
      try { s.chart.removeSeries(o.upper);  } catch (e) { /* ok */ }
      try { s.chart.removeSeries(o.middle); } catch (e) { /* ok */ }
      try { s.chart.removeSeries(o.lower);  } catch (e) { /* ok */ }
    } else {
      try { s.chart.removeSeries(o); } catch (e) { /* ok */ }
    }
    delete s.overlays[k];
  }

  function _updateOverlays(idx) {
    const s = slots[idx]; if (!s || !s.data) return;
    const candles = s.data.candles || [];
    const volumes = (s.data.volume || []).map(v => ({ time: v.time, value: Number(v.value) }));
    if (!candles.length) return;

    // Remove deactivated
    for (const k of Object.keys(s.overlays)) {
      if (!s.indicators[k]) _removeOverlay(s, k);
    }

    // Compute & draw active
    for (const [k, active] of Object.entries(s.indicators)) {
      if (!active) continue;
      const def = INDICATOR_DEFS[k]; if (!def) continue;

      let result;
      switch (k) {
        case 'ema20':     result = IndicatorEngine.ema(candles, 20); break;
        case 'ema50':     result = IndicatorEngine.ema(candles, 50); break;
        case 'ema200':    result = IndicatorEngine.ema(candles, 200); break;
        case 'sma50':     result = IndicatorEngine.sma(candles, 50); break;
        case 'sma200':    result = IndicatorEngine.sma(candles, 200); break;
        case 'vwap':      result = IndicatorEngine.vwap(candles, volumes); break;
        case 'bollinger': result = IndicatorEngine.bollinger(candles, 20, 2); break;
        case 'volumeMA':  result = IndicatorEngine.volumeMA(volumes, 20); break;
        default: continue;
      }

      // Create series if needed
      if (!s.overlays[k]) {
        if (k === 'bollinger') {
          s.overlays[k] = {
            upper:  s.chart.addLineSeries({ color: def.color, lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false }),
            middle: s.chart.addLineSeries({ color: def.color, lineWidth: 1, crosshairMarkerVisible: false, lastValueVisible: false }),
            lower:  s.chart.addLineSeries({ color: def.color, lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false }),
          };
        } else if (k === 'volumeMA') {
          s.overlays[k] = s.chart.addLineSeries({
            color: def.color, lineWidth: 2, priceScaleId: '',
            crosshairMarkerVisible: false, lastValueVisible: false,
            priceFormat: { type: 'volume' },
          });
        } else {
          s.overlays[k] = s.chart.addLineSeries({
            color: def.color, lineWidth: 1.5,
            crosshairMarkerVisible: false, lastValueVisible: true,
          });
        }
      }

      // Apply data
      if (k === 'bollinger') {
        s.overlays[k].upper.setData(result.upper   || []);
        s.overlays[k].middle.setData(result.middle  || []);
        s.overlays[k].lower.setData(result.lower    || []);
      } else {
        s.overlays[k].setData(result);
      }
    }
  }

  /* ══════════════════════════════════════════════════════════════════════
     PATTERN OVERLAYS (per slot)
     ══════════════════════════════════════════════════════════════════════ */

  function _clearPatterns(idx) {
    const s = slots[idx]; if (!s) return;
    for (const k of Object.keys(s.patternOverlays)) {
      const arr = s.patternOverlays[k];
      if (Array.isArray(arr)) {
        arr.forEach(sr => { try { s.chart.removeSeries(sr); } catch (e) { /* ok */ } });
      }
    }
    // Clear swing markers
    try { s.candleSeries.setMarkers([]); } catch (e) { /* ok */ }
    s.patternOverlays = {};
  }

  function _updatePatterns(idx) {
    const s = slots[idx]; if (!s || !s.data) return;
    const candles = s.data.candles || [];
    if (candles.length < 20) return;
    if (typeof activeAnalysis === 'undefined' || typeof PatternEngine === 'undefined') return;

    _clearPatterns(idx);

    // Compute patterns
    const swings     = PatternEngine.detectSwings(candles, 5);
    const sr         = PatternEngine.detectSupportResistance(swings, candles, 4);
    const breakouts  = PatternEngine.detectBreakouts(sr, candles,
      (s.data.volume || []).map(v => ({ time: v.time, value: Number(v.value) })));
    const trendlines = PatternEngine.detectTrendlines(swings, candles);

    // Draw active patterns (uses global activeAnalysis)
    if (activeAnalysis.sr)         _drawSlotSR(s, sr, candles);
    if (activeAnalysis.swings)     _drawSlotSwings(s, swings);
    if (activeAnalysis.breakouts)  _drawSlotBreakouts(s, breakouts, candles);
    if (activeAnalysis.trendlines) _drawSlotTrendlines(s, trendlines, candles);
  }

  function _drawSlotSR(s, sr, candles) {
    const series = [];
    const first = candles[0].time;
    const last  = candles[candles.length - 1].time;

    for (const sup of (sr.supports || []).slice(0, 3)) {
      const ls = s.chart.addLineSeries({
        color: 'rgba(38,217,168,0.6)', lineWidth: 1, lineStyle: 2,
        crosshairMarkerVisible: false, lastValueVisible: true,
        title: 'S ' + Number(sup.price).toFixed(2),
      });
      ls.setData([{ time: first, value: sup.price }, { time: last, value: sup.price }]);
      series.push(ls);
    }
    for (const res of (sr.resistances || []).slice(0, 3)) {
      const ls = s.chart.addLineSeries({
        color: 'rgba(240,80,110,0.6)', lineWidth: 1, lineStyle: 2,
        crosshairMarkerVisible: false, lastValueVisible: true,
        title: 'R ' + Number(res.price).toFixed(2),
      });
      ls.setData([{ time: first, value: res.price }, { time: last, value: res.price }]);
      series.push(ls);
    }
    s.patternOverlays.sr = series;
  }

  function _drawSlotSwings(s, swings) {
    const markers = [];
    for (const h of (swings.highs || []))
      markers.push({ time: h.time, position: 'aboveBar', color: '#f5a623', shape: 'arrowDown', text: 'SH' });
    for (const l of (swings.lows || []))
      markers.push({ time: l.time, position: 'belowBar', color: '#5b8cf5', shape: 'arrowUp', text: 'SL' });
    markers.sort((a, b) => a.time - b.time);
    if (markers.length) s.candleSeries.setMarkers(markers);
    s.patternOverlays.swings = [];
  }

  function _drawSlotBreakouts(s, breakouts, candles) {
    const series = [];
    const last = candles[candles.length - 1].time;
    for (const b of (breakouts || []).slice(0, 3)) {
      const ls = s.chart.addLineSeries({
        color: b.type === 'bullish' ? 'rgba(38,217,168,0.5)' : 'rgba(240,80,110,0.5)',
        lineWidth: 2, lineStyle: 1,
        crosshairMarkerVisible: false, lastValueVisible: false,
      });
      ls.setData([{ time: b.time, value: b.price }, { time: last, value: b.price }]);
      series.push(ls);
    }
    s.patternOverlays.breakouts = series;
  }

  function _drawSlotTrendlines(s, trendlines, candles) {
    const series = [];
    for (const tl of (trendlines || []).slice(0, 2)) {
      if (!tl.points || tl.points.length < 2) continue;
      const ls = s.chart.addLineSeries({
        color: tl.slope > 0 ? 'rgba(168,85,247,0.6)' : 'rgba(240,80,110,0.6)',
        lineWidth: 1, lineStyle: 1,
        crosshairMarkerVisible: false, lastValueVisible: false,
      });
      ls.setData(tl.points.map(p => ({ time: p.time, value: p.price })));
      series.push(ls);
    }
    s.patternOverlays.trendlines = series;
  }

  /* ══════════════════════════════════════════════════════════════════════
     DATA LOADING
     ══════════════════════════════════════════════════════════════════════ */

  async function _loadSlot(idx) {
    const s = slots[idx]; if (!s) return;
    const mc = _mc(s.market);
    const qs = new URLSearchParams({
      symbol:   s.symbol,
      interval: s.timeframe,
      limit:    '500',
    });

    try {
      const js = await fetchJson(mc.klinesEndpoint + '?' + qs);
      const candles = js.candles || [];
      const volume  = _colorizeVol(candles, js.volume || []);
      s.data = { symbol: js.symbol, interval: js.interval, candles, volume };

      // Render chart
      s.candleSeries.setData(candles);
      s.volSeries.setData(volume);
      s.chart.timeScale().fitContent();

      // Update toolbar
      s.symLabel.textContent = s.symbol;
      s.marketDot.className  = 'mc-market-dot ' + s.market + '-dot';

      // Compute overlays
      _updateOverlays(idx);
      _updatePatterns(idx);
    } catch (e) {
      console.warn('MC slot ' + idx + ' load error:', e);
    }
  }

  /* ══════════════════════════════════════════════════════════════════════
     LAYOUT MANAGEMENT
     ══════════════════════════════════════════════════════════════════════ */

  function _applyLayout() {
    const grid  = document.getElementById('mcGrid');
    const hdr   = document.querySelector('.chart-header');
    const area  = document.getElementById('chartArea');
    const strip = document.querySelector('.indicator-strip');

    if (layout === 1) {
      /* ---- Single chart: restore original elements ---- */
      if (grid)  grid.style.display  = 'none';
      if (hdr)   hdr.style.display   = '';
      if (area)  area.style.display  = '';
      if (strip) strip.style.display = '';

      // Destroy multi-chart slots
      for (let i = 0; i < MAX_SLOTS; i++) _destroySlot(i);
      if (grid) grid.innerHTML = '';

      // Restore original chart
      try {
        chartManager.load().then(() => {
          if (activeMarket === 'crypto') indicatorManager.load();
          indicatorOverlayManager.updateAll();
          patternOverlayManager.updateAll();
        });
      } catch (e) { /* ok */ }

      // Clear refresh timer
      if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null; }
      return;
    }

    /* ---- Multi-chart: hide original, show grid ---- */
    if (hdr)   hdr.style.display   = 'none';
    if (area)  area.style.display  = 'none';
    if (strip) strip.style.display = 'none';
    if (!grid) return;

    grid.style.display = 'grid';
    grid.className = 'mc-grid mc-layout-' + layout;
    grid.innerHTML = '';

    // Destroy old slots
    for (let i = 0; i < MAX_SLOTS; i++) _destroySlot(i);

    // Load saved slot configs
    const saved = _loadState();

    // Create slots
    for (let i = 0; i < layout; i++) {
      const cfg = saved?.[i] || null;
      const slot = _createSlot(i, cfg);
      grid.appendChild(slot.container);
    }

    // Set first as active
    activeSlot = 0;
    document.querySelectorAll('.mc-slot').forEach(el =>
      el.classList.toggle('mc-active', Number(el.dataset.slot) === 0));

    // Sync globals from slot 0
    const s0 = slots[0];
    if (s0) {
      currentSymbol = s0.symbol;
      currentTf     = s0.timeframe;
    }

    // Load data for all slots
    for (let i = 0; i < layout; i++) {
      _loadSlot(i).catch(() => {});
    }

    // Set up multi-chart refresh timer (every 15 seconds)
    if (_refreshTimer) clearInterval(_refreshTimer);
    _refreshTimer = setInterval(() => {
      for (let i = 0; i < layout; i++) {
        if (slots[i]) _loadSlot(i).catch(() => {});
      }
    }, 15000);
  }

  /* ── Layout Selector UI ────────────────────────────────────────────── */
  function _renderSelector() {
    const topbar = document.querySelector('.topbar');
    if (!topbar) return;

    const wrap = document.createElement('div');
    wrap.className = 'mc-layout-selector';
    wrap.id = 'mcLayoutSelector';

    const lbl = document.createElement('span');
    lbl.className = 'mc-layout-label';
    lbl.textContent = 'Layout';

    const btns = document.createElement('div');
    btns.className = 'mc-layout-btns';

    for (const n of [1, 2, 4]) {
      const b = document.createElement('button');
      b.className = 'mc-layout-btn' + (n === layout ? ' active' : '');
      b.dataset.layout = n;
      b.innerHTML = _icon(n);
      b.title = n + ' Chart' + (n > 1 ? 's' : '');
      b.addEventListener('click', () => setLayout(n));
      btns.appendChild(b);
    }

    wrap.appendChild(lbl);
    wrap.appendChild(btns);

    // Insert before indicator dropdown wrapper
    const indWrap = topbar.querySelector('.ind-dropdown-wrapper');
    if (indWrap) {
      topbar.insertBefore(wrap, indWrap);
    } else {
      const aiBtn = document.getElementById('aiBtn');
      if (aiBtn) topbar.insertBefore(wrap, aiBtn);
      else topbar.appendChild(wrap);
    }
  }

  function _highlightBtn() {
    document.querySelectorAll('.mc-layout-btn').forEach(b =>
      b.classList.toggle('active', Number(b.dataset.layout) === layout));
  }

  /* ══════════════════════════════════════════════════════════════════════
     PUBLIC API
     ══════════════════════════════════════════════════════════════════════ */

  function init() {
    _loadState();
    _renderSelector();
    if (layout > 1) {
      // Defer layout application to next frame (DOM must be ready)
      requestAnimationFrame(() => _applyLayout());
    }
  }

  function setLayout(n) {
    if (![1, 2, 4].includes(n)) return;
    if (n === layout) return;
    layout = n;
    _saveState();
    _highlightBtn();
    _applyLayout();
  }

  function setSymbol(idx, symbol, market) {
    const s = slots[idx]; if (!s) return;
    if (s.symbol === symbol && s.market === (market || s.market)) return;
    s.symbol = symbol;
    if (market) s.market = market;
    _saveState();
    _loadSlot(idx).catch(() => {});

    // If active slot, sync globals
    if (idx === activeSlot) {
      currentSymbol = symbol;
      if (market) {
        activeMarket = market;
        try { localStorage.setItem('bw_active_market', market); } catch (e) { /* ok */ }
      }
      signalManager.load().catch(() => {});
    }
  }

  function setTimeframe(idx, tf) {
    const s = slots[idx]; if (!s) return;
    if (s.timeframe === tf) return;
    s.timeframe = tf;
    _renderTf(s.tfGroup, idx, tf);
    _saveState();
    _loadSlot(idx).catch(() => {});
    if (idx === activeSlot) currentTf = tf;
  }

  function updateAllSlots() {
    for (let i = 0; i < layout; i++) {
      if (slots[i]) _loadSlot(i).catch(() => {});
    }
  }

  /** Called from watchlist click. Returns true if handled. */
  function onWatchlistSelect(symbol, market) {
    if (layout <= 1) return false;
    setSymbol(activeSlot, symbol, market || activeMarket);
    return true;
  }

  /** Refresh patterns on all visible slots (called when pattern toggles change). */
  function refreshPatterns() {
    for (let i = 0; i < layout; i++) {
      if (slots[i] && slots[i].data) _updatePatterns(i);
    }
  }

  function isMultiMode()     { return layout > 1; }
  function getLayout()       { return layout; }
  function getActiveSlotId() { return activeSlot; }

  return {
    init,
    setLayout,
    setSymbol,
    setTimeframe,
    updateAllSlots,
    onWatchlistSelect,
    refreshPatterns,
    isMultiMode,
    getLayout,
    getActiveSlotId,
    getSlot: idx => slots[idx] || null,
  };
})();
