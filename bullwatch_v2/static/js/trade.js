/* =====================================================================
   ZKR Analiz Trade Terminal — FAZ 9 + FAZ 13 + FAZ 14 + FAZ 15 + FAZ 16
   (Indicators + Patterns + News + Multi-Market)
   ===================================================================== */

// ── Market Config (FAZ 16) ──────────────────────────────────────────────
const MARKET_CONFIG = {
  crypto: {
    label: 'Crypto',
    defaultSymbol: 'BTCUSDT',
    symbolsEndpoint: '/api/liquidation/symbols',
    klinesEndpoint: '/api/market/klines',
    tickerEndpoint: '/api/market/ticker',
    newsType: 'crypto',
    hasOrderflow: true,
    hasLiquidation: true,
    hasSignals: true,
    badgeClass: 'badge-crypto',
    symbolFilter: r => r.symbol && r.symbol.endsWith('USDT'),
    mapRow: r => r,
  },
  stocks: {
    label: 'US Stocks',
    defaultSymbol: 'AAPL',
    symbolsEndpoint: '/api/stocks/symbols',
    klinesEndpoint: '/api/stocks/klines',
    tickerEndpoint: '/api/stocks/ticker',
    newsType: 'stocks',
    hasOrderflow: false,
    hasLiquidation: false,
    hasSignals: true,
    badgeClass: 'badge-stocks',
    symbolFilter: () => true,
    mapRow: r => r,
  },
  bist: {
    label: 'BIST',
    defaultSymbol: 'THYAO.IS',
    symbolsEndpoint: '/api/bist/symbols',
    klinesEndpoint: '/api/bist/klines',
    tickerEndpoint: '/api/bist/ticker',
    newsType: 'bist',
    hasOrderflow: false,
    hasLiquidation: false,
    hasSignals: true,
    badgeClass: 'badge-bist',
    symbolFilter: () => true,
    mapRow: r => r,
  },
  forex: {
    label: 'Forex',
    defaultSymbol: 'EURUSD=X',
    symbolsEndpoint: '/api/forex/symbols',
    klinesEndpoint: '/api/forex/klines',
    tickerEndpoint: '/api/forex/ticker',
    newsType: 'forex',
    hasOrderflow: false,
    hasLiquidation: false,
    hasSignals: true,
    badgeClass: 'badge-forex',
    symbolFilter: () => true,
    mapRow: r => r,
  },
  commodities: {
    label: 'Commodities',
    defaultSymbol: 'GC=F',
    symbolsEndpoint: '/api/commodities/symbols',
    klinesEndpoint: '/api/commodities/klines',
    tickerEndpoint: '/api/commodities/ticker',
    newsType: 'commodities',
    hasOrderflow: false,
    hasLiquidation: false,
    hasSignals: true,
    badgeClass: 'badge-commodities',
    symbolFilter: () => true,
    mapRow: r => r,
  },
};

const LS_MARKET_KEY = 'bw_active_market';
let activeMarket = 'crypto';
try {
  const saved = localStorage.getItem(LS_MARKET_KEY);
  if (saved && MARKET_CONFIG[saved]) activeMarket = saved;
} catch {}

function getMarketConfig() { return MARKET_CONFIG[activeMarket]; }

// ── Config ──────────────────────────────────────────────────────────────
const TF = [
  { key: '1m',  label: '1m'  },
  { key: '5m',  label: '5m'  },
  { key: '15m', label: '15m' },
  { key: '1h',  label: '1h'  },
  { key: '4h',  label: '4h'  },
  { key: '1d',  label: '1D'  },
];

let currentSymbol = 'BTCUSDT';
let currentTf     = '15m';

// ── Indicator Config (FAZ 13) ───────────────────────────────────────────
const INDICATOR_DEFS = {
  ema20:     { label: 'EMA 20',          color: '#f5c842' },
  ema50:     { label: 'EMA 50',          color: '#f5882a' },
  ema200:    { label: 'EMA 200',         color: '#e84040' },
  sma50:     { label: 'SMA 50',          color: '#5b8cf5' },
  sma200:    { label: 'SMA 200',         color: '#a855f7' },
  vwap:      { label: 'VWAP',            color: '#26d9a8' },
  bollinger: { label: 'Bollinger Bands', color: '#8899b0' },
  volumeMA:  { label: 'Volume MA (20)',  color: '#f5a623' },
};

const LS_KEY = 'bw_active_indicators';

function loadIndicatorState() {
  try { const s = localStorage.getItem(LS_KEY); if (s) return JSON.parse(s); } catch {}
  return { ema20: true, ema50: false, ema200: false, sma50: false, sma200: false, vwap: false, bollinger: false, volumeMA: false };
}
function saveIndicatorState(st) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(st)); } catch {}
}

let activeIndicators = loadIndicatorState();

// ── Pattern Config (FAZ 14) ─────────────────────────────────────────────
const ANALYSIS_DEFS = {
  sr:        { label: 'Support / Resistance', color: '#5b8cf5' },
  swings:    { label: 'Swing High / Low',     color: '#f5a623' },
  breakouts: { label: 'Breakout Zones',       color: '#26d9a8' },
  trendlines:{ label: 'Trendlines',           color: '#a855f7' },
  triangles: { label: 'Triangle Detection',   color: '#f5882a' },
  flags:     { label: 'Flag / Pennant',       color: '#f0506e' },
  ranges:    { label: 'Range Detection',      color: '#8899b0' },
};

const LS_ANALYSIS_KEY = 'bw_active_analysis';

function loadAnalysisState() {
  try { const s = localStorage.getItem(LS_ANALYSIS_KEY); if (s) return JSON.parse(s); } catch {}
  return { sr: true, swings: false, breakouts: false, trendlines: false, triangles: false, flags: false, ranges: false };
}
function saveAnalysisState(st) {
  try { localStorage.setItem(LS_ANALYSIS_KEY, JSON.stringify(st)); } catch {}
}

let activeAnalysis = loadAnalysisState();

// ── Helpers ─────────────────────────────────────────────────────────────
function fmt(n, d = 2) {
  const x = Number(n);
  if (!Number.isFinite(x)) return '—';
  return x.toLocaleString(undefined, { maximumFractionDigits: d });
}

function pct(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return '—';
  return `${x >= 0 ? '+' : ''}${x.toFixed(2)}%`;
}

function $(id)   { return document.getElementById(id); }
function txt(id, v) { const e = $(id); if (e) e.textContent = v ?? '—'; }

function setStatus(text, cls = '') {
  const pill = $('statusPill');
  if (!pill) return;
  pill.textContent = text;
  pill.className = 'status-pill' + (cls ? ` ${cls}` : '');
}

async function fetchJson(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.text();
  let js;
  try { js = JSON.parse(body); }
  catch { throw new Error(`invalid_json: ${body.slice(0, 200)}`); }
  if (!r.ok || js.ok === false) throw new Error(js.error || `http_${r.status}`);
  return js;
}

// ── Tab Manager ─────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === `tab-${tab}`));
    });
  });
}

// ── Timeframe Manager ───────────────────────────────────────────────────
function renderTf() {
  const g = $('tfGroup');
  if (!g) return;
  g.innerHTML = '';
  for (const t of TF) {
    const b = document.createElement('button');
    b.textContent = t.label;
    b.className = 'tf-btn' + (t.key === currentTf ? ' active' : '');
    b.addEventListener('click', () => {
      currentTf = t.key;
      renderTf();
      // FAZ 26: re-subscribe WS stream to new interval
      if (typeof MarketStream !== 'undefined') MarketStream.subscribe(currentSymbol, activeMarket, currentTf);
      refreshFast().catch(e => setStatus(`Hata: ${e.message}`, 'err'));
    });
    g.appendChild(b);
  }
}

// ── Watchlist Manager ───────────────────────────────────────────────────
const watchlistManager = (() => {
  let rows = [];

  function render() {
    const list = $('wlList');
    const count = $('wlCount');
    if (!list) return;
    list.innerHTML = '';

    const q = ($('symbolSearch')?.value || '').trim().toUpperCase();
    const filtered = rows
      .filter(r => !q || r.symbol.includes(q) || (r.base || '').toUpperCase().includes(q))
      .slice(0, 200);

    if (count) count.textContent = `${filtered.length} / ${rows.length}`;

    for (const r of filtered) {
      const el = document.createElement('div');
      el.className = 'wl-item' + (r.symbol === currentSymbol ? ' active' : '');

      const chg = Number(r.pct);
      const cls = Number.isFinite(chg) ? (chg >= 0 ? 'up' : 'down') : '';

      el.innerHTML = `
        <span class="wl-sym">${r.symbol}</span>
        <span class="wl-price">${fmt(r.lastPrice || 0, 6)}</span>
        <span class="wl-chg ${cls}">${pct(chg)}</span>
      `;

      el.addEventListener('click', () => {
        // FAZ 18: In multi-chart mode, load symbol into active chart
        if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) {
          MultiChartManager.onWatchlistSelect(r.symbol, activeMarket);
          currentSymbol = r.symbol;
          render();
          const mc = getMarketConfig();
          if (mc.hasSignals) signalManager.load();
          if (mc.hasOrderflow) orderflowManager.load();
          if (mc.hasLiquidation) liquidationManager.load();
          return;
        }
        currentSymbol = r.symbol;
        render();
        // FAZ 26: re-subscribe WS stream to new symbol
        if (typeof MarketStream !== 'undefined') MarketStream.subscribe(currentSymbol, activeMarket, currentTf);
        refreshFast().catch(e => setStatus(`Hata: ${e.message}`, 'err'));
        const mc = getMarketConfig();
        if (mc.hasSignals) signalManager.load();
        if (mc.hasOrderflow) orderflowManager.load();
        if (mc.hasLiquidation) liquidationManager.load();
      });

      list.appendChild(el);
    }
  }

  async function load() {
    setStatus('Watchlist…');
    const mc = getMarketConfig();

    // Update watchlist market badge
    const badge = $('wlMarketBadge');
    if (badge) {
      badge.textContent = mc.label;
      badge.className = 'market-badge ' + mc.badgeClass;
    }

    if (activeMarket === 'crypto') {
      // Crypto: liquidation/symbols now includes lastPrice from Binance 24h ticker
      const js = await fetchJson('/api/liquidation/symbols');
      const items = js.items || [];
      rows = items.filter(r => r.symbol && r.symbol.endsWith('USDT'));

    } else {
      // Non-crypto: use market-specific symbols endpoint (instant, no prices)
      try {
        const js = await fetchJson(mc.symbolsEndpoint);
        rows = (js.items || []).map(r => ({
          symbol: r.symbol,
          base: r.base || r.symbol,
          lastPrice: r.lastPrice || 0,
          pct: r.pct || 0,
          market: r.market || activeMarket,
        }));
      } catch (e) {
        rows = [];
        console.warn('Watchlist load failed:', e);
      }

      // Lazy-load prices for the first 30 visible symbols (non-blocking)
      if (rows.length > 0 && mc.tickerEndpoint) {
        const batch = rows.slice(0, 30);
        (async () => {
          for (const r of batch) {
            try {
              const t = await fetchJson(`${mc.tickerEndpoint}?symbol=${r.symbol}`);
              if (t && t.lastPrice) {
                r.lastPrice = t.lastPrice;
                r.pct = t.priceChangePercent || 0;
                render();
              }
            } catch { /* skip */ }
          }
        })();
      }
    }

    if (!rows.find(r => r.symbol === currentSymbol) && rows[0]) {
      currentSymbol = rows[0].symbol;
    }
    render();
    setStatus('✓ Bağlandı', 'ok');
  }

  return { load, render, getRows: () => rows };
})();

// ── Chart Manager ───────────────────────────────────────────────────────
const chartManager = (() => {
  let chart, seriesCandles, seriesVol;
  let lastData = null;
  let chartType = 'candlestick'; // candlestick | line | area | bar

  const CHART_OPTS = {
    layout: { background: { color: '#000000' }, textColor: '#e8edf5' },
    grid: { vertLines: { color: '#18243a' }, horzLines: { color: '#18243a' } },
    rightPriceScale: { borderColor: '#1e2d40' },
    timeScale: { borderColor: '#1e2d40' },
    crosshair: { mode: 1 },
  };

  function init() {
    const area = $('chartArea');
    if (!area) return;

    // Restore saved chart type
    try { const saved = localStorage.getItem('bw_chart_type'); if (saved && ['candlestick','line','area','bar'].includes(saved)) chartType = saved; } catch {}

    chart = LightweightCharts.createChart(area, {
      ...CHART_OPTS,
      width: area.clientWidth,
      height: area.clientHeight,
    });

    _createMainSeries(chartType);
    seriesVol = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      color: 'rgba(91,140,245,.30)',
    });
    seriesVol.priceScale().applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

    const resize = () => {
      if (!area.clientWidth) return;
      chart.applyOptions({ width: area.clientWidth, height: area.clientHeight });
    };
    window.addEventListener('resize', resize);
    new ResizeObserver(resize).observe(area);
  }

  function colorizeVolume(candles, volume) {
    const map = new Map(candles.map(c => [c.time, c]));
    return volume.map(v => {
      const c = map.get(v.time);
      return { ...v, color: c && Number(c.close) >= Number(c.open) ? 'rgba(38,217,168,.55)' : 'rgba(240,80,110,.55)' };
    });
  }

  function renderHeader(data) {
    const last = data.candles?.length ? data.candles[data.candles.length - 1] : null;
    txt('chartSymbol', `${data.symbol} • ${data.interval}`);
    txt('chartOhlc', last
      ? `O:${fmt(last.open)} H:${fmt(last.high)} L:${fmt(last.low)} C:${fmt(last.close)} (${data.candles.length} candles)`
      : '—');
  }

  async function load() {
    setStatus('Grafik…');
    const mc = getMarketConfig();
    const qs = new URLSearchParams({ symbol: currentSymbol, interval: currentTf, limit: '500' });
    const js = await fetchJson(`${mc.klinesEndpoint}?${qs}`);

    const candles = js.candles || [];
    const volume = colorizeVolume(candles, js.volume || []);

    lastData = { symbol: js.symbol, interval: js.interval, candles, volume };
    renderHeader(lastData);

    _setSeriesData(candles);
    seriesVol.setData(volume);
    chart.timeScale().fitContent();
    setStatus('✓ Bağlandı', 'ok');

    // Register with DrawingEngine (first call registers, subsequent update symbol)
    if (typeof DrawingEngine !== 'undefined') {
      const area = $('chartArea');
      if (area) {
        DrawingEngine.registerChart('main', chart, seriesCandles, area, currentSymbol);
      } else {
        DrawingEngine.updateSymbol('main', currentSymbol);
      }
      DrawingEngine.render();
    }
  }

  function _createMainSeries(type) {
    if (seriesCandles) { try { chart.removeSeries(seriesCandles); } catch {} }
    switch (type) {
      case 'line':
        seriesCandles = chart.addLineSeries({ color: '#26d9a8', lineWidth: 2, lastValueVisible: true, crosshairMarkerVisible: true });
        break;
      case 'area':
        seriesCandles = chart.addAreaSeries({ topColor: 'rgba(38,217,168,0.4)', bottomColor: 'rgba(38,217,168,0.02)', lineColor: '#26d9a8', lineWidth: 2 });
        break;
      case 'bar':
        seriesCandles = chart.addBarSeries({ upColor: '#26d9a8', downColor: '#f0506e' });
        break;
      default: // candlestick
        seriesCandles = chart.addCandlestickSeries({ upColor: '#26d9a8', downColor: '#f0506e', borderVisible: false, wickUpColor: '#26d9a8', wickDownColor: '#f0506e' });
        break;
    }
  }

  function _setSeriesData(candles) {
    if (chartType === 'line' || chartType === 'area') {
      seriesCandles.setData(candles.map(c => ({ time: c.time, value: Number(c.close) })));
    } else {
      seriesCandles.setData(candles);
    }
  }

  function setChartType(type) {
    if (!chart || !['candlestick', 'line', 'area', 'bar'].includes(type)) return;
    chartType = type;
    try { localStorage.setItem('bw_chart_type', type); } catch {}
    _createMainSeries(type);
    if (lastData && lastData.candles) {
      _setSeriesData(lastData.candles);
      chart.timeScale().fitContent();
      // Re-register drawing engine with new series
      if (typeof DrawingEngine !== 'undefined') {
        const area = $('chartArea');
        if (area) DrawingEngine.registerChart('main', chart, seriesCandles, area, currentSymbol);
      }
      // Re-apply indicator overlays
      if (typeof indicatorOverlayManager !== 'undefined') indicatorOverlayManager.updateAll();
    }
  }

  function getChartType() { return chartType; }

  return { init, load, getData: () => lastData, getChart: () => chart, getCandleSeries: () => seriesCandles, getVolSeries: () => seriesVol, setChartType, getChartType };
})();

// ── Indicator Manager ───────────────────────────────────────────────────
const indicatorManager = (() => {
  let chartRsi, seriesRsi;
  let chartMacd, seriesMacd, seriesSignal, seriesHist;

  const OPTS = {
    layout: { background: { color: '#000000' }, textColor: '#e8edf5' },
    grid: { vertLines: { color: '#18243a' }, horzLines: { color: '#18243a' } },
    rightPriceScale: { borderColor: '#1e2d40' },
    timeScale: { borderColor: '#1e2d40', visible: false },
    crosshair: { mode: 1 },
  };

  function init() {
    const rsiEl = $('rsiPanel');
    const macdEl = $('macdPanel');
    if (!rsiEl || !macdEl) return;

    chartRsi = LightweightCharts.createChart(rsiEl, { ...OPTS, width: rsiEl.clientWidth, height: 120 });
    seriesRsi = chartRsi.addLineSeries({ color: '#7c5cff', lineWidth: 2 });
    chartRsi.priceScale('right').applyOptions({ scaleMargins: { top: 0.15, bottom: 0.15 } });

    chartMacd = LightweightCharts.createChart(macdEl, { ...OPTS, width: macdEl.clientWidth, height: 120 });
    seriesMacd  = chartMacd.addLineSeries({ color: '#26d9a8', lineWidth: 2 });
    seriesSignal = chartMacd.addLineSeries({ color: '#8899b0', lineWidth: 1 });
    seriesHist  = chartMacd.addHistogramSeries({ color: 'rgba(240,80,110,.5)' });

    const resize = () => {
      if (rsiEl.clientWidth) chartRsi.applyOptions({ width: rsiEl.clientWidth, height: rsiEl.clientHeight || 120 });
      if (macdEl.clientWidth) chartMacd.applyOptions({ width: macdEl.clientWidth, height: macdEl.clientHeight || 120 });
    };
    window.addEventListener('resize', resize);
    new ResizeObserver(resize).observe(rsiEl);
  }

  async function load() {
    const qs = new URLSearchParams({ symbol: currentSymbol, interval: currentTf, limit: '300' });
    const [rsiJs, macdJs] = await Promise.all([
      fetchJson(`/api/indicators/rsi?${qs}`),
      fetchJson(`/api/indicators/macd?${qs}`),
    ]);

    seriesRsi.setData(rsiJs.rsi || []);
    seriesMacd.setData(macdJs.macd || []);
    seriesSignal.setData(macdJs.signal || []);
    seriesHist.setData(macdJs.hist || []);
    chartRsi.timeScale().fitContent();
    chartMacd.timeScale().fitContent();
  }

  return { init, load };
})();


// ── Indicator Overlay Manager (FAZ 13) ──────────────────────────────────
const indicatorOverlayManager = (() => {
  const overlays = {};    // key -> { series, lastCount }
  let prevKey = '';       // symbol:interval
  let prevCandleCount = 0;

  /* ---- series lifecycle ---- */
  function _createSeries(key) {
    const chart = chartManager.getChart();
    if (!chart) return null;
    const def = INDICATOR_DEFS[key];
    if (!def) return null;
    if (key === 'bollinger') {
      return {
        upper:  chart.addLineSeries({ color: def.color, lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false }),
        middle: chart.addLineSeries({ color: def.color, lineWidth: 1, crosshairMarkerVisible: false, lastValueVisible: false }),
        lower:  chart.addLineSeries({ color: def.color, lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: false }),
      };
    }
    if (key === 'volumeMA') {
      return chart.addLineSeries({ color: def.color, lineWidth: 2, priceScaleId: '', crosshairMarkerVisible: false, lastValueVisible: false, priceFormat: { type: 'volume' } });
    }
    return chart.addLineSeries({ color: def.color, lineWidth: 1.5, crosshairMarkerVisible: false, lastValueVisible: true });
  }

  function _removeSeries(key) {
    const chart = chartManager.getChart();
    if (!chart || !overlays[key]) return;
    const e = overlays[key];
    if (key === 'bollinger') {
      try { chart.removeSeries(e.series.upper); } catch {}
      try { chart.removeSeries(e.series.middle); } catch {}
      try { chart.removeSeries(e.series.lower); } catch {}
    } else {
      try { chart.removeSeries(e.series); } catch {}
    }
    delete overlays[key];
  }

  /* ---- compute ---- */
  function _compute(key, candles, volumes) {
    switch (key) {
      case 'ema20':    return IndicatorEngine.ema(candles, 20);
      case 'ema50':    return IndicatorEngine.ema(candles, 50);
      case 'ema200':   return IndicatorEngine.ema(candles, 200);
      case 'sma50':    return IndicatorEngine.sma(candles, 50);
      case 'sma200':   return IndicatorEngine.sma(candles, 200);
      case 'vwap':     return IndicatorEngine.vwap(candles, volumes);
      case 'bollinger': return IndicatorEngine.bollinger(candles, 20, 2);
      case 'volumeMA': return IndicatorEngine.volumeMA(volumes, 20);
      default: return [];
    }
  }

  /* ---- apply data to series ---- */
  function _applyFull(key, result) {
    const o = overlays[key];
    if (key === 'bollinger') {
      o.series.upper.setData(result.upper || []);
      o.series.middle.setData(result.middle || []);
      o.series.lower.setData(result.lower || []);
    } else {
      o.series.setData(result);
    }
  }

  function _applyIncremental(key, result) {
    const o = overlays[key];
    if (key === 'bollinger') {
      const r = result;
      if (r.upper.length)  o.series.upper.update(r.upper[r.upper.length - 1]);
      if (r.middle.length) o.series.middle.update(r.middle[r.middle.length - 1]);
      if (r.lower.length)  o.series.lower.update(r.lower[r.lower.length - 1]);
    } else {
      if (result.length) o.series.update(result[result.length - 1]);
    }
  }

  /* ---- main update loop ---- */
  function updateAll() {
    const data = chartManager.getData();
    if (!data) return;
    const candles = data.candles || [];
    const volumes = (data.volume || []).map(v => ({ time: v.time, value: Number(v.value) }));
    const currentKey = (data.symbol || '') + ':' + (data.interval || '');
    const incremental = currentKey === prevKey && candles.length === prevCandleCount && candles.length > 0;
    prevKey = currentKey;
    prevCandleCount = candles.length;

    for (const key of Object.keys(INDICATOR_DEFS)) {
      if (!activeIndicators[key]) {
        if (overlays[key]) _removeSeries(key);
        continue;
      }
      if (!overlays[key]) {
        const s = _createSeries(key);
        if (!s) continue;
        overlays[key] = { series: s };
      }
      const result = _compute(key, candles, volumes);
      if (incremental) {
        _applyIncremental(key, result);
      } else {
        _applyFull(key, result);
      }
    }
  }

  /* ---- toggle ---- */
  function toggle(key) {
    activeIndicators[key] = !activeIndicators[key];
    saveIndicatorState(activeIndicators);
    if (!activeIndicators[key]) _removeSeries(key);
    else updateAll();
    _refreshChecks();
  }

  function _refreshChecks() {
    document.querySelectorAll('.ind-dropdown-item input[data-ind]').forEach(cb => {
      cb.checked = !!activeIndicators[cb.dataset.ind];
    });
  }

  /* ---- dropdown UI ---- */
  function init() {
    const topbar = document.querySelector('.topbar');
    const aiBtn  = document.getElementById('aiBtn');
    if (!topbar || !aiBtn) return;

    const wrap = document.createElement('div');
    wrap.className = 'ind-dropdown-wrapper';

    const btn = document.createElement('button');
    btn.className = 'ind-toggle-btn';
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 5-6"/></svg> Indicators <span class="ind-arrow">\u25BC</span>';

    const dd = document.createElement('div');
    dd.className = 'ind-dropdown';

    for (const [key, def] of Object.entries(INDICATOR_DEFS)) {
      const lbl = document.createElement('label');
      lbl.className = 'ind-dropdown-item';
      lbl.innerHTML = '<input type="checkbox" ' + (activeIndicators[key] ? 'checked' : '') + ' data-ind="' + key + '">'
        + '<span class="ind-color-dot" style="background:' + def.color + '"></span>'
        + '<span>' + def.label + '</span>';
      dd.appendChild(lbl);
    }

    wrap.appendChild(btn);
    wrap.appendChild(dd);
    topbar.insertBefore(wrap, aiBtn);

    btn.addEventListener('click', function(e) { e.stopPropagation(); dd.classList.toggle('open'); });
    dd.addEventListener('change', function(e) { var k = e.target.dataset.ind; if (k) toggle(k); });
    document.addEventListener('click', function(e) { if (!wrap.contains(e.target)) dd.classList.remove('open'); });
  }

  return { init, updateAll, toggle, isActive: function(k) { return !!activeIndicators[k]; } };
})();

// ── Pattern Overlay Manager (FAZ 14) ────────────────────────────────────
const patternOverlayManager = (() => {
  const overlays = {};
  let lastResult = null;
  let prevKey = '';

  function _clearOverlays() {
    const chart = chartManager.getChart();
    if (!chart) return;
    for (const key of Object.keys(overlays)) {
      const arr = overlays[key];
      if (Array.isArray(arr)) {
        arr.forEach(s => { try { chart.removeSeries(s); } catch {} });
      }
      delete overlays[key];
    }
  }

  function _clearKey(key) {
    const chart = chartManager.getChart();
    if (!chart || !overlays[key]) return;
    const arr = overlays[key];
    if (Array.isArray(arr)) {
      arr.forEach(s => { try { chart.removeSeries(s); } catch {} });
    }
    delete overlays[key];
  }

  /* ---- Draw S/R levels ---- */
  function _drawSR(sr, candles) {
    const chart = chartManager.getChart();
    if (!chart) return;
    _clearKey('sr');
    const series = [];
    const first = candles[0].time;
    const last = candles[candles.length - 1].time;

    for (const s of (sr.supports || []).slice(0, 3)) {
      const ls = chart.addLineSeries({
        color: 'rgba(38,217,168,0.6)', lineWidth: 1, lineStyle: 2,
        crosshairMarkerVisible: false, lastValueVisible: true,
        title: 'S ' + s.price.toFixed(0),
      });
      ls.setData([{ time: first, value: s.price }, { time: last, value: s.price }]);
      series.push(ls);
    }
    for (const r of (sr.resistances || []).slice(0, 3)) {
      const ls = chart.addLineSeries({
        color: 'rgba(240,80,110,0.6)', lineWidth: 1, lineStyle: 2,
        crosshairMarkerVisible: false, lastValueVisible: true,
        title: 'R ' + r.price.toFixed(0),
      });
      ls.setData([{ time: first, value: r.price }, { time: last, value: r.price }]);
      series.push(ls);
    }
    overlays.sr = series;
  }

  /* ---- Draw Swing markers ---- */
  function _drawSwings(swings) {
    const cs = chartManager.getChart()?.series;
    // Use markers on the candlestick series
    const markers = [];
    for (const h of (swings.highs || [])) {
      markers.push({ time: h.time, position: 'aboveBar', color: '#f5a623', shape: 'arrowDown', text: 'SH' });
    }
    for (const l of (swings.lows || [])) {
      markers.push({ time: l.time, position: 'belowBar', color: '#5b8cf5', shape: 'arrowUp', text: 'SL' });
    }
    markers.sort((a, b) => a.time - b.time);
    overlays.swings = markers;
    // We'll apply markers via candlestick series
  }

  /* ---- Draw Breakout zones ---- */
  function _drawBreakouts(breakouts, candles) {
    const chart = chartManager.getChart();
    if (!chart) return;
    _clearKey('breakouts');
    const series = [];
    for (const b of breakouts) {
      const atr = Math.abs(Number(candles[candles.length - 1].high) - Number(candles[candles.length - 1].low)) * 0.5;
      const upper = b.price + atr;
      const lower = b.price - atr;
      // Draw as two lines creating a zone
      const color = b.type === 'bullish' ? 'rgba(38,217,168,0.25)' : 'rgba(240,80,110,0.25)';
      const ls = chart.addLineSeries({
        color: b.type === 'bullish' ? 'rgba(38,217,168,0.5)' : 'rgba(240,80,110,0.5)',
        lineWidth: 1, lineStyle: 1,
        crosshairMarkerVisible: false, lastValueVisible: false,
        title: b.type === 'bullish' ? 'BO\u2191' : 'BO\u2193',
      });
      ls.setData([{ time: b.time, value: b.price }, { time: b.endTime, value: b.price }]);
      series.push(ls);
    }
    overlays.breakouts = series;
  }

  /* ---- Draw Trendlines ---- */
  function _drawTrendlines(tlines) {
    const chart = chartManager.getChart();
    if (!chart) return;
    _clearKey('trendlines');
    const series = [];
    for (const tl of tlines) {
      const color = tl.type === 'support' ? 'rgba(38,217,168,0.7)' : 'rgba(168,85,247,0.7)';
      const ls = chart.addLineSeries({
        color, lineWidth: 2, lineStyle: 0,
        crosshairMarkerVisible: false, lastValueVisible: false,
        title: tl.type === 'support' ? 'STL' : 'RTL',
      });
      ls.setData(tl.points);
      series.push(ls);
    }
    overlays.trendlines = series;
  }

  /* ---- Draw Triangle ---- */
  function _drawTriangle(tri) {
    const chart = chartManager.getChart();
    if (!chart) return;
    _clearKey('triangles');
    if (!tri) return;
    const series = [];
    if (tri.upperLine) {
      const ls = chart.addLineSeries({
        color: 'rgba(245,136,42,0.7)', lineWidth: 1, lineStyle: 0,
        crosshairMarkerVisible: false, lastValueVisible: false, title: 'TRI-U',
      });
      ls.setData(tri.upperLine);
      series.push(ls);
    }
    if (tri.lowerLine) {
      const ls = chart.addLineSeries({
        color: 'rgba(245,136,42,0.7)', lineWidth: 1, lineStyle: 0,
        crosshairMarkerVisible: false, lastValueVisible: false, title: 'TRI-L',
      });
      ls.setData(tri.lowerLine);
      series.push(ls);
    }
    overlays.triangles = series;
  }

  /* ---- Draw Flag ---- */
  function _drawFlag(flag) {
    const chart = chartManager.getChart();
    if (!chart) return;
    _clearKey('flags');
    if (!flag) return;
    const series = [];
    // Flag range box (upper and lower)
    const color = flag.type === 'bull_flag' ? 'rgba(38,217,168,0.4)' : 'rgba(240,80,110,0.4)';
    const lsH = chart.addLineSeries({
      color, lineWidth: 1, lineStyle: 2,
      crosshairMarkerVisible: false, lastValueVisible: false, title: 'FLG-H',
    });
    lsH.setData([{ time: flag.flagStartTime, value: flag.flagHigh }, { time: flag.flagEndTime, value: flag.flagHigh }]);
    series.push(lsH);
    const lsL = chart.addLineSeries({
      color, lineWidth: 1, lineStyle: 2,
      crosshairMarkerVisible: false, lastValueVisible: false, title: 'FLG-L',
    });
    lsL.setData([{ time: flag.flagStartTime, value: flag.flagLow }, { time: flag.flagEndTime, value: flag.flagLow }]);
    series.push(lsL);
    overlays.flags = series;
  }

  /* ---- Draw Range ---- */
  function _drawRange(range) {
    const chart = chartManager.getChart();
    if (!chart) return;
    _clearKey('ranges');
    if (!range || !range.inRange) return;
    const series = [];
    const lsU = chart.addLineSeries({
      color: 'rgba(136,153,176,0.5)', lineWidth: 1, lineStyle: 2,
      crosshairMarkerVisible: false, lastValueVisible: true, title: 'RNG-H',
    });
    lsU.setData([{ time: range.startTime, value: range.upper }, { time: range.endTime, value: range.upper }]);
    series.push(lsU);
    const lsL = chart.addLineSeries({
      color: 'rgba(136,153,176,0.5)', lineWidth: 1, lineStyle: 2,
      crosshairMarkerVisible: false, lastValueVisible: true, title: 'RNG-L',
    });
    lsL.setData([{ time: range.startTime, value: range.lower }, { time: range.endTime, value: range.lower }]);
    series.push(lsL);
    overlays.ranges = series;
  }

  /* ---- Apply swing markers to candlestick series ---- */
  function _applyMarkers() {
    // Combine swing markers with existing markers
    const chart = chartManager.getChart();
    if (!chart) return;
    // Get candlestick series (first series added)
    try {
      const allMarkers = overlays.swings || [];
      // LightweightCharts: setMarkers on candlestick series
      // We access it through the chart's series list
      const cs = chart.series && chart.series[0];
      // Actually we need the candlestick series reference from chartManager
    } catch {}
  }

  /* ---- Main update ---- */
  function updateAll() {
    const data = chartManager.getData();
    if (!data) return;
    const candles = data.candles || [];
    const volumes = (data.volume || []).map(v => ({ time: v.time, value: Number(v.value) }));
    if (candles.length < 20) return;

    const currentKey = (data.symbol || '') + ':' + (data.interval || '') + ':' + candles.length;
    if (currentKey === prevKey) return; // skip if same data
    prevKey = currentKey;

    // Compute all patterns
    const swings = PatternEngine.detectSwings(candles, 5);
    const sr = PatternEngine.detectSupportResistance(swings, candles, 4);
    const breakouts = PatternEngine.detectBreakouts(sr, candles, volumes);
    const trendlines = PatternEngine.detectTrendlines(swings, candles);
    const triangle = PatternEngine.detectTriangles(swings, candles);
    const flag = PatternEngine.detectFlags(candles, swings);
    const range = PatternEngine.detectRanges(candles, 40);
    const trend = PatternEngine.trendDirection(candles);

    lastResult = { swings, sr, breakouts, trendlines, triangle, flag, range, trend };

    // Draw active overlays
    for (const key of Object.keys(ANALYSIS_DEFS)) {
      if (!activeAnalysis[key]) {
        _clearKey(key);
        continue;
      }
      switch (key) {
        case 'sr': _drawSR(sr, candles); break;
        case 'swings': _drawSwings(swings); break;
        case 'breakouts': _drawBreakouts(breakouts, candles); break;
        case 'trendlines': _drawTrendlines(trendlines); break;
        case 'triangles': _drawTriangle(triangle); break;
        case 'flags': _drawFlag(flag); break;
        case 'ranges': _drawRange(range); break;
      }
    }

    // Update patterns tab
    _updatePatternsTab();
  }

  /* ---- Patterns Tab Summary ---- */
  function _updatePatternsTab() {
    const el = document.getElementById('patternsSummary');
    if (!el || !lastResult) return;

    const r = lastResult;
    const lastPrice = chartManager.getData()?.candles?.length
      ? Number(chartManager.getData().candles[chartManager.getData().candles.length - 1].close) : 0;
    const fmtP = (n) => Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '\u2014';

    let html = '';

    // Trend
    const trendIcon = r.trend === 'uptrend' ? '\u2191' : r.trend === 'downtrend' ? '\u2193' : '\u2194';
    const trendColor = r.trend === 'uptrend' ? 'var(--good)' : r.trend === 'downtrend' ? 'var(--bad)' : 'var(--muted)';
    html += '<div class="pat-section">';
    html += '<div class="pat-section-title">Trend Direction</div>';
    html += '<div class="pat-trend" style="color:' + trendColor + '">' + trendIcon + ' ' + r.trend.charAt(0).toUpperCase() + r.trend.slice(1) + '</div>';
    html += '</div>';

    // Active structure
    const structures = [];
    if (r.triangle) structures.push(r.triangle.type.replace('_',' ').replace(/\b\w/g, c => c.toUpperCase()) + ' Triangle');
    if (r.flag) structures.push(r.flag.type === 'bull_flag' ? 'Bull Flag' : 'Bear Flag');
    if (r.range && r.range.inRange) structures.push('Ranging');

    html += '<div class="pat-section">';
    html += '<div class="pat-section-title">Active Structure</div>';
    html += structures.length
      ? structures.map(s => '<div class="pat-structure">' + s + '</div>').join('')
      : '<div class="pat-none">No pattern detected</div>';
    html += '</div>';

    // S/R Levels
    if (r.sr) {
      html += '<div class="pat-section">';
      html += '<div class="pat-section-title">Key Levels</div>';
      html += '<div class="pat-levels">';
      for (const res of (r.sr.resistances || []).slice(0, 3)) {
        html += '<div class="pat-level pat-res"><span>R</span><span>' + fmtP(res.price) + '</span><span class="pat-touches">' + res.touches + 'x</span></div>';
      }
      html += '<div class="pat-level pat-price"><span>\u25B6</span><span>' + fmtP(lastPrice) + '</span><span>now</span></div>';
      for (const sup of (r.sr.supports || []).slice(0, 3)) {
        html += '<div class="pat-level pat-sup"><span>S</span><span>' + fmtP(sup.price) + '</span><span class="pat-touches">' + sup.touches + 'x</span></div>';
      }
      html += '</div></div>';
    }

    // Breakout status
    html += '<div class="pat-section">';
    html += '<div class="pat-section-title">Breakout Status</div>';
    if (r.breakouts && r.breakouts.length > 0) {
      const latest = r.breakouts[r.breakouts.length - 1];
      const boColor = latest.type === 'bullish' ? 'var(--good)' : 'var(--bad)';
      html += '<div class="pat-breakout" style="color:' + boColor + '">' + (latest.type === 'bullish' ? '\u2191 Bullish' : '\u2193 Bearish') + ' breakout at ' + fmtP(latest.price) + '</div>';
    } else {
      html += '<div class="pat-none">No active breakout</div>';
    }
    html += '</div>';

    // Swing count
    html += '<div class="pat-section">';
    html += '<div class="pat-section-title">Swing Points</div>';
    html += '<div class="pat-swings">' + (r.swings.highs || []).length + ' highs, ' + (r.swings.lows || []).length + ' lows detected</div>';
    html += '</div>';

    el.innerHTML = html;
  }

  /* ---- Toggle ---- */
  function toggle(key) {
    activeAnalysis[key] = !activeAnalysis[key];
    saveAnalysisState(activeAnalysis);
    if (!activeAnalysis[key]) _clearKey(key);
    prevKey = ''; // force recompute
    updateAll();
    _refreshChecks();
    // FAZ 18: Update patterns on all multi-chart slots
    if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) {
      MultiChartManager.refreshPatterns();
    }
  }

  function _refreshChecks() {
    document.querySelectorAll('.ana-dropdown-item input[data-ana]').forEach(cb => {
      cb.checked = !!activeAnalysis[cb.dataset.ana];
    });
  }

  /* ---- Dropdown UI ---- */
  function init() {
    const topbar = document.querySelector('.topbar');
    const aiBtn = document.getElementById('aiBtn');
    if (!topbar || !aiBtn) return;

    const wrap = document.createElement('div');
    wrap.className = 'ana-dropdown-wrapper';

    const btn = document.createElement('button');
    btn.className = 'ana-toggle-btn';
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px"><path d="M2 12h4l3-9 4 18 3-9h6"/></svg> Analysis <span class="ana-arrow">\u25BC</span>';

    const dd = document.createElement('div');
    dd.className = 'ana-dropdown';

    for (const [key, def] of Object.entries(ANALYSIS_DEFS)) {
      const lbl = document.createElement('label');
      lbl.className = 'ana-dropdown-item';
      lbl.innerHTML = '<input type="checkbox" ' + (activeAnalysis[key] ? 'checked' : '') + ' data-ana="' + key + '">'
        + '<span class="ind-color-dot" style="background:' + def.color + '"></span>'
        + '<span>' + def.label + '</span>';
      dd.appendChild(lbl);
    }

    wrap.appendChild(btn);
    wrap.appendChild(dd);
    topbar.insertBefore(wrap, aiBtn);

    btn.addEventListener('click', function(e) { e.stopPropagation(); dd.classList.toggle('open'); });
    dd.addEventListener('change', function(e) { var k = e.target.dataset.ana; if (k) toggle(k); });
    document.addEventListener('click', function(e) { if (!wrap.contains(e.target)) dd.classList.remove('open'); });
  }

  return { init, updateAll, toggle, getResult: function() { return lastResult; } };
})();

// ── Signal Manager ──────────────────────────────────────────────────────
const signalManager = (() => {

  function badgeClass(decision) {
    if (!decision) return 'badge-neutral';
    const d = decision.toUpperCase();
    if (d === 'AL') return 'badge-good';
    if (d.includes('BEKLE')) return 'badge-warn';
    return 'badge-bad';
  }

  function showUnavailable() {
    const badge = $('sigBadge');
    if (badge) { badge.textContent = '—'; badge.className = 'badge badge-neutral'; }
    txt('sigDecision', 'N/A');
    txt('sigRisk', '—');
    txt('sigConfidence', '—');
    const ticksEl = $('sigTicks');
    if (ticksEl) ticksEl.innerHTML = '<div class="panel-unavailable"><div class="panel-unavailable-icon">📊</div><div class="panel-unavailable-text">Signal analysis is not available</div></div>';
    const targetsEl = $('sigTargets');
    if (targetsEl) targetsEl.innerHTML = '<div class="loading-text" style="grid-column:1/-1">—</div>';
    const srEl = $('sigSR');
    if (srEl) srEl.innerHTML = '';
  }

  async function load() {
    const mc = getMarketConfig();
    if (!mc.hasSignals) { showUnavailable(); return; }
    try {
      // Use market-aware endpoint for non-crypto markets
      let url;
      if (activeMarket === 'crypto') {
        url = `/api/signal?symbol=${currentSymbol}`;
      } else {
        url = `/api/market-signal?symbol=${encodeURIComponent(currentSymbol)}&market=${activeMarket}`;
      }
      const js = await fetchJson(url);
      const d = js.data || {};

      // Badge
      const badge = $('sigBadge');
      if (badge) {
        badge.textContent = d.decision || '—';
        badge.className = `badge ${badgeClass(d.decision)}`;
      }

      txt('sigDecision', d.decision || '—');

      // Risk
      const risk = d.risk || {};
      txt('sigRisk', risk.suggested_sl ? `SL: ${fmt(risk.suggested_sl)} | TP1: ${fmt(risk.tp1)} | TP2: ${fmt(risk.tp2)}` : '—');

      // Confidence (from context)
      const ctx = d.context || {};
      txt('sigConfidence', ctx.change24_pct !== undefined ? `24h: ${pct(ctx.change24_pct)} | 7d: ${pct(ctx.ret7_pct)}` : '—');

      // Ticks
      const ticksEl = $('sigTicks');
      if (ticksEl) {
        const ticks = d.ticks || [];
        if (ticks.length) {
          ticksEl.innerHTML = ticks.map(t =>
            `<div class="tick-item">
              <span class="tick-icon ${t.ok ? 'pass' : 'fail'}">${t.ok ? '✓' : '✗'}</span>
              <span>${t.label}</span>
            </div>`
          ).join('');
        } else {
          ticksEl.innerHTML = '<div class="loading-text">Veri yok</div>';
        }
      }

      // Pullback targets
      const targetsEl = $('sigTargets');
      if (targetsEl) {
        const targets = d.pullback_targets || [];
        if (targets.length) {
          targetsEl.innerHTML = targets.map(t =>
            `<div class="kv-key">${t.label || '—'}</div><div class="kv-val">${fmt(t.price || t, 6)}</div>`
          ).join('');
        } else {
          targetsEl.innerHTML = '<div class="loading-text" style="grid-column:1/-1">—</div>';
        }
      }

      // Support / Resistance (FAZ 17)
      const srEl = $('sigSR');
      if (srEl) {
        const sr = d.support_resistance || {};
        const sup = sr.support || [];
        const res = sr.resistance || [];
        if (sup.length || res.length) {
          let html = '';
          res.forEach(r => {
            html += `<div class="kv-key" style="color:#ef5350">▲ ${r.label}</div><div class="kv-val" style="color:#ef5350">${fmt(r.price, 6)}</div>`;
          });
          sup.forEach(s => {
            html += `<div class="kv-key" style="color:#26a69a">▼ ${s.label}</div><div class="kv-val" style="color:#26a69a">${fmt(s.price, 6)}</div>`;
          });
          srEl.innerHTML = html;
        } else {
          srEl.innerHTML = '<div class="loading-text" style="grid-column:1/-1">—</div>';
        }
      }

    } catch (e) {
      txt('sigDecision', `Hata: ${e.message}`);
    }
  }

  return { load };
})();

// ── Orderflow Manager ───────────────────────────────────────────────────
const orderflowManager = (() => {

  function showUnavailable() {
    txt('ofPrice', '—');
    txt('ofChange', '—');
    txt('ofVolume', '—');
    txt('ofOi', '—');
    txt('ofFr', '—');
    txt('ofMark', '—');
    txt('ofLs', '—');
    txt('ofLong', '—');
    txt('ofShort', '—');
    txt('ofTakerRatio', '—');
    txt('ofBuyVol', '—');
    txt('ofSellVol', '—');
    txt('ofBidTotal', '—');
    txt('ofAskTotal', '—');
    const imbEl = $('ofImbalance');
    if (imbEl) imbEl.textContent = '—';
    // Show unavailable message in first card
    const ov = $('ofOverview');
    if (ov) {
      ov.parentElement.innerHTML = '<div class="r-card-title">Market Overview</div><div class="panel-unavailable"><div class="panel-unavailable-icon">📈</div><div class="panel-unavailable-text">Orderflow data is only available for Crypto market</div></div>';
    }
  }

  async function load() {
    const mc = getMarketConfig();
    if (!mc.hasOrderflow) { showUnavailable(); return; }
    try {
      const js = await fetchJson(`/api/orderflow/symbol/${currentSymbol}`);

      // Market Overview
      const t = js.ticker || {};
      txt('ofPrice',  fmt(t.lastPrice, 6));
      txt('ofChange', pct(t.priceChangePercent));
      txt('ofVolume', fmt(t.quoteVolume, 0));

      // OI & Funding
      const oi = js.openInterest || {};
      const fr = js.fundingRate || {};
      txt('ofOi',   fmt(oi.openInterest, 2));
      txt('ofFr',   fr.fundingRate !== undefined ? `${(fr.fundingRate * 100).toFixed(4)}%` : '—');
      txt('ofMark', fmt(fr.markPrice, 2));

      // Long/Short
      const ls = js.longShortRatio || {};
      txt('ofLs',    fmt(ls.longShortRatio, 4));
      txt('ofLong',  ls.longAccount !== undefined ? `${(ls.longAccount * 100).toFixed(1)}%` : '—');
      txt('ofShort', ls.shortAccount !== undefined ? `${(ls.shortAccount * 100).toFixed(1)}%` : '—');

      // Taker
      const tv = js.takerVolume || {};
      txt('ofTakerRatio', fmt(tv.buySellRatio, 4));
      txt('ofBuyVol',     fmt(tv.buyVol, 2));
      txt('ofSellVol',    fmt(tv.sellVol, 2));

      // Book Imbalance
      const bi = js.bookImbalance || {};
      txt('ofBidTotal',   fmt(bi.bidTotal, 4));
      txt('ofAskTotal',   fmt(bi.askTotal, 4));
      const imb = bi.imbalance;
      const imbEl = $('ofImbalance');
      if (imbEl) {
        imbEl.textContent = imb !== undefined ? `${(imb * 100).toFixed(2)}%` : '—';
        imbEl.style.color = imb > 0 ? 'var(--good)' : imb < 0 ? 'var(--bad)' : '';
      }

    } catch (e) {
      txt('ofPrice', `Hata: ${e.message}`);
    }
  }

  return { load };
})();

// ── Liquidation Manager ─────────────────────────────────────────────────
const liquidationManager = (() => {

  function showUnavailable() {
    txt('liqClose', '—');
    txt('liqPoc', '—');
    txt('liqVaH', '—');
    txt('liqVaL', '—');
    txt('liqRange', '—');
    txt('liqChg24', '—');
    txt('liqQvol', '—');
    const vpEl = $('vpBars');
    if (vpEl) vpEl.innerHTML = '<div class="panel-unavailable"><div class="panel-unavailable-icon">🔥</div><div class="panel-unavailable-text">Liquidation data is only available for Crypto market</div></div>';
  }

  async function load() {
    const mc = getMarketConfig();
    if (!mc.hasLiquidation) { showUnavailable(); return; }
    try {
      const qs = new URLSearchParams({ symbol: currentSymbol, interval: currentTf, limit: '200', bins: '20' });
      const js = await fetchJson(`/api/liquidation/price_profile?${qs}`);

      const s = js.summary || {};
      txt('liqClose',  fmt(s.lastClose, 6));
      txt('liqPoc',    fmt(s.poc, 6));
      txt('liqVaH',    fmt(s.valueAreaHigh, 6));
      txt('liqVaL',    fmt(s.valueAreaLow, 6));
      txt('liqRange',  s.rangePosition !== undefined ? `${(s.rangePosition * 100).toFixed(1)}%` : '—');
      txt('liqChg24',  pct(s.priceChange24hPct));
      txt('liqQvol',   fmt(s.quoteVolume24h, 0));

      // Volume Profile Bars
      const vpEl = $('vpBars');
      if (vpEl) {
        const profile = js.profile || [];
        if (!profile.length) {
          vpEl.innerHTML = '<div class="loading-text">Veri yok</div>';
          return;
        }
        const maxVol = Math.max(...profile.map(p => p.volume));
        vpEl.innerHTML = profile.map(p => {
          const pctWidth = maxVol > 0 ? (p.volume / maxVol * 100).toFixed(1) : 0;
          const isPoc = s.poc && Math.abs(p.priceMid - s.poc) < (p.priceHigh - p.priceLow);
          const isVa  = p.priceMid >= (s.valueAreaLow || 0) && p.priceMid <= (s.valueAreaHigh || Infinity);
          const cls = isPoc ? 'poc' : isVa ? 'va' : '';
          return `<div class="vp-row">
            <span class="vp-price">${fmt(p.priceMid, 2)}</span>
            <div><div class="vp-fill ${cls}" style="width:${pctWidth}%"></div></div>
            <span class="vp-vol">${fmt(p.volume, 0)}</span>
          </div>`;
        }).join('');
      }

    } catch (e) {
      txt('liqClose', `Hata: ${e.message}`);
    }
  }

  return { load };
})();

// ── AI Manager ──────────────────────────────────────────────────────────
const aiManager = (() => {

  async function analyze() {
    const out = $('aiOutput');
    if (!out) return;
    out.textContent = 'AI analiz hazırlanıyor…';

    const mkt = chartManager.getData();
    const last = mkt?.candles?.length ? mkt.candles[mkt.candles.length - 1] : {};

    const prompt = [
      `Sembol: ${currentSymbol}`,
      `Timeframe: ${currentTf}`,
      `Son fiyat: ${last.close || '?'}`,
      `Son mum: O=${last.open} H=${last.high} L=${last.low} C=${last.close}`,
      '',
      `Mevcut piyasa yapısını analiz et: RSI, MACD, volume, orderflow ve likidite profilini kullanarak.`,
      `Kısa bir teknik analiz yap: trend, destek/direnç, risk, olası senaryo.`,
      `Türkçe yanıt ver. Finansal tavsiye verme; sadece analiz.`,
    ].join('\n');

    try {
      const js = await fetchJson('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'llama3.1:8b-instruct-q6_K',
          messages: [{ role: 'user', content: prompt }],
        }),
      });
      out.textContent = js.data?.response || '—';
    } catch (e) {
      out.textContent = `Hata: ${e?.message || e}`;
    }
  }

  function clear() {
    const out = $('aiOutput');
    if (out) out.textContent = 'AI analizini başlatmak için butona tıklayın.';
  }

  return { analyze, clear };
})();

// ── News Manager (FAZ 15) ──────────────────────────────────────────────────────────
const newsManager = (() => {
  let currentType = 'crypto';
  let lastSymbol = '';

  function _sentimentBadge(s) {
    if (s === 'bullish') return '<span class="news-sent news-sent-bull">↑ Bullish</span>';
    if (s === 'bearish') return '<span class="news-sent news-sent-bear">↓ Bearish</span>';
    return '<span class="news-sent news-sent-neutral">─ Neutral</span>';
  }

  function _timeAgo(iso) {
    if (!iso) return '';
    try {
      const diff = Date.now() - new Date(iso).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return 'just now';
      if (mins < 60) return mins + 'm ago';
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return hrs + 'h ago';
      const days = Math.floor(hrs / 24);
      return days + 'd ago';
    } catch { return ''; }
  }

  function _renderList(items) {
    const el = $('newsList');
    const badge = $('newsBadge');
    if (!el) return;
    if (!items || items.length === 0) {
      el.innerHTML = '<div class="news-empty">Haber bulunamadı.</div>';
      if (badge) badge.textContent = '0';
      return;
    }
    if (badge) badge.textContent = items.length;
    el.innerHTML = items.map(n => `
      <a class="news-card" href="${n.url || '#'}" target="_blank" rel="noopener">
        <div class="news-card-header">
          <span class="news-source">${n.source || ''}</span>
          <span class="news-time">${_timeAgo(n.published_at)}</span>
        </div>
        <div class="news-title">${n.title || ''}</div>
        <div class="news-summary">${(n.summary || '').slice(0, 200)}</div>
        <div class="news-footer">
          ${_sentimentBadge(n.sentiment)}
          ${(n.symbols || []).map(s => '<span class="news-sym">' + s + '</span>').join('')}
        </div>
      </a>
    `).join('');
  }

  async function load(type) {
    if (type) currentType = type;

    // FAZ 16: Auto-adjust news type based on active market
    const mc = getMarketConfig();
    if (currentType === 'crypto' && activeMarket !== 'crypto') {
      currentType = mc.newsType;
    }

    const el = $('newsList');
    if (el) el.innerHTML = '<div class="loading-text">Yükleniyor…</div>';

    try {
      let url;
      if (currentType === 'coin') {
        url = '/api/news/coin?symbol=' + encodeURIComponent(currentSymbol);
      } else {
        url = '/api/news?type=' + currentType;
      }
      const js = await fetchJson(url);
      _renderList(js.data || []);
      lastSymbol = currentSymbol;
    } catch (e) {
      if (el) el.innerHTML = '<div class="news-empty">Haber yüklenemedi.</div>';
    }
  }

  function init() {
    // Wire type buttons
    document.querySelectorAll('.news-type-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.news-type-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        load(btn.dataset.ntype);
      });
    });
  }

  function refreshIfNeeded() {
    // Auto-refresh when symbol changes and type is 'coin'
    if (currentType === 'coin' && currentSymbol !== lastSymbol) {
      load();
    }
  }

  // FAZ 16: Reset news type for new market
  function setMarketDefault() {
    const mc = getMarketConfig();
    currentType = mc.newsType;
    // Reset button states
    document.querySelectorAll('.news-type-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.ntype === currentType || (b.dataset.ntype === 'crypto' && activeMarket === 'crypto'));
    });
  }

  return { init, load, refreshIfNeeded, setMarketDefault };
})();

// ── Refresh orchestration ───────────────────────────────────────────────
async function refreshFast() {
  // FAZ 18: In multi-chart mode, delegate to MultiChartManager
  if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) {
    MultiChartManager.updateAllSlots();
    return;
  }
  await chartManager.load();
  // Only load RSI/MACD indicators for crypto (they use crypto endpoints)
  if (activeMarket === 'crypto') {
    await indicatorManager.load();
  }
  indicatorOverlayManager.updateAll();
  patternOverlayManager.updateAll();
}

// ── Market Tab Manager (FAZ 16) ─────────────────────────────────────────
const marketTabManager = (() => {

  function init() {
    document.querySelectorAll('.market-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        const market = btn.dataset.market;
        if (market === activeMarket) return;
        switchMarket(market);
      });
    });
    // Set initial active state
    _highlightTab(activeMarket);
  }

  function _highlightTab(market) {
    document.querySelectorAll('.market-tab').forEach(b =>
      b.classList.toggle('active', b.dataset.market === market)
    );
  }

  async function switchMarket(market) {
    if (!MARKET_CONFIG[market]) return;

    // FAZ 18: In multi-chart mode, only switch watchlist (don't change charts)
    if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) {
      activeMarket = market;
      try { localStorage.setItem(LS_MARKET_KEY, market); } catch {}
      _highlightTab(market);
      setStatus(MARKET_CONFIG[market].label + ' yükleniyor…');
      try { await watchlistManager.load(); } catch (e) { console.warn('WL fail:', e); }
      setStatus('✓ Bağlandı', 'ok');
      return;
    }

    activeMarket = market;
    try { localStorage.setItem(LS_MARKET_KEY, market); } catch {}

    _highlightTab(market);

    const mc = getMarketConfig();
    currentSymbol = mc.defaultSymbol;
    // FAZ 26: re-subscribe WS stream to new market/symbol
    if (typeof MarketStream !== 'undefined') MarketStream.subscribe(currentSymbol, activeMarket, currentTf);

    // Update status
    setStatus(`${mc.label} yükleniyor…`);

    // Load watchlist for new market
    try { await watchlistManager.load(); } catch (e) { console.warn('WL fail:', e); }

    // Load chart for new market
    try { await refreshFast(); } catch (e) { console.warn('Chart fail:', e); }

    // Load right-panel data
    signalManager.load().catch(() => {});
    orderflowManager.load().catch(() => {});
    liquidationManager.load().catch(() => {});

    // Update news for market
    newsManager.setMarketDefault();
    newsManager.load().catch(() => {});

    setStatus('✓ Bağlandı', 'ok');
  }

  return { init, switchMarket };
})();

// ── Wire UI ─────────────────────────────────────────────────────────────
function wireUi() {
  // Search filter
  $('symbolSearch')?.addEventListener('input', () => watchlistManager.render());

  // AI buttons (topbar + inner)
  $('aiBtn')?.addEventListener('click', () => {
    // Switch to AI tab
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'ai'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.toggle('active', p.id === 'tab-ai'));
    aiManager.analyze();
  });
  $('aiAnalyzeBtn')?.addEventListener('click', () => aiManager.analyze());
  $('aiClear')?.addEventListener('click', () => aiManager.clear());
}

// ── Main entry ──────────────────────────────────────────────────────────
async function main() {
  try {
    setStatus('Başlatılıyor…');

    // FAZ 16: Set initial market state
    const mc = getMarketConfig();
    currentSymbol = mc.defaultSymbol;

    renderTf();
    initTabs();
    wireUi();
    marketTabManager.init();
    chartManager.init();
    indicatorManager.init();
    indicatorOverlayManager.init();
    patternOverlayManager.init();
    newsManager.init();

    // FAZ 18: Initialize multi-chart manager
    if (typeof MultiChartManager !== 'undefined') MultiChartManager.init();

    // Initial data load
    await watchlistManager.load();
    // FAZ 18: Skip single-chart refresh if multi-mode is active
    if (typeof MultiChartManager === 'undefined' || !MultiChartManager.isMultiMode()) {
      await refreshFast();
    }

    // Load right panel data
    signalManager.load().catch(() => {});
    orderflowManager.load().catch(() => {});
    liquidationManager.load().catch(() => {});
    newsManager.load().catch(() => {});
    // FAZ 26: Connect real-time WebSocket stream
    if (typeof MarketStream !== 'undefined') {
      MarketStream.connect();
      MarketStream.subscribe(currentSymbol, activeMarket, currentTf);
    }

    // Polling — fast (chart + indicators) every 5s (crypto) / 15s (others)
    // FAZ 18: Multi-chart has its own refresh timer
    setInterval(() => {
      if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) return;
      // FAZ 26: Skip chart polling when WS live stream is active (crypto only)
      if (typeof MarketStream !== 'undefined' && MarketStream.isConnected() && activeMarket === 'crypto') return;
      refreshFast().catch(() => {});
    }, activeMarket === 'crypto' ? 5000 : 15000);

    // Polling — watchlist every 30s (crypto) / 60s (others)
    // FAZ 26: Skip watchlist polling when WS stream handles it
    setInterval(() => { if (typeof MarketStream !== 'undefined' && MarketStream.isConnected() && activeMarket === 'crypto') return; watchlistManager.load().catch(() => {}); }, activeMarket === 'crypto' ? 30000 : 60000);

    // Polling — right panel every 60s
    // FAZ 18: In multi-chart mode, skip auto right-panel refresh
    setInterval(() => {
      if (typeof MultiChartManager !== 'undefined' && MultiChartManager.isMultiMode()) return;
      signalManager.load().catch(() => {});
      orderflowManager.load().catch(() => {});
      liquidationManager.load().catch(() => {});
      newsManager.refreshIfNeeded();
    }, 60000);

    setStatus('✓ Bağlandı', 'ok');
  } catch (e) {
    setStatus(`Hata: ${e?.message || e}`, 'err');
  }
}

// ── FAZ 31: Share Chart Snapshot ─────────────────────────────────
function shareChart() {
  try {
    const chart = chartManager.getChart();
    if (!chart) return alert('Grafik yüklenmedi');

    const canvas = chart.takeScreenshot();
    const snapshot = canvas.toDataURL('image/png');

    sessionStorage.setItem('bw_share_chart', JSON.stringify({
      snapshot: snapshot,
      symbol: currentSymbol,
      timeframe: currentTf,
      market: activeMarket,
    }));

    window.location.href = '/feed';
  } catch (e) {
    alert('Grafik yakalanamadı: ' + (e.message || e));
  }
}

main();
