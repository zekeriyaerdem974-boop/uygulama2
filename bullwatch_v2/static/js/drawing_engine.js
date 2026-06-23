/* =====================================================================
   ZKR Analiz v2 — Drawing Engine  (FAZ 24D — EXPANDED)
   Full-featured chart drawing tools with canvas overlay
   40+ active tools · properties panel · drag/move · anchor editing
   Supports: multi-chart, touch, persist (localStorage)
   ===================================================================== */
'use strict';

const DrawingEngine = (() => {

  /* ═══════════════════════════════════════════════════════════════════
     Constants
     ═══════════════════════════════════════════════════════════════════ */
  const STORE_KEY  = 'bw_drawings_v2';
  const HIT_T      = 8;
  const ANCHOR_R   = 5;
  const DEF_COLOR  = '#5b8cf5';
  const SEL_COLOR  = '#ffd700';
  const FIB = [
    { r: 0,     c: '#787B86', l: '0%' },
    { r: 0.236, c: '#F44336', l: '23.6%' },
    { r: 0.382, c: '#FF9800', l: '38.2%' },
    { r: 0.5,   c: '#4CAF50', l: '50%' },
    { r: 0.618, c: '#2196F3', l: '61.8%' },
    { r: 0.786, c: '#9C27B0', l: '78.6%' },
    { r: 1,     c: '#787B86', l: '100%' },
  ];
  const FIB_EXT = [
    { r: 0,     c: '#787B86', l: '0%' },
    { r: 0.236, c: '#F44336', l: '23.6%' },
    { r: 0.382, c: '#FF9800', l: '38.2%' },
    { r: 0.5,   c: '#4CAF50', l: '50%' },
    { r: 0.618, c: '#2196F3', l: '61.8%' },
    { r: 0.786, c: '#9C27B0', l: '78.6%' },
    { r: 1,     c: '#787B86', l: '100%' },
    { r: 1.272, c: '#E91E63', l: '127.2%' },
    { r: 1.618, c: '#00BCD4', l: '161.8%' },
    { r: 2.618, c: '#FF5722', l: '261.8%' },
  ];
  const DASH_STYLES = { solid: [], dashed: [6, 4], dotted: [2, 3] };

  /* ═══════════════════════════════════════════════════════════════════
     Active tools — these have full render + hit-test support
     ═══════════════════════════════════════════════════════════════════ */
  const ACTIVE_TOOL_IDS = new Set([
    /* original 11 */
    'trendline','h_line','v_line','ray',
    'rect','triangle','circle','ellipse',
    'fib_ret','text','p_label',
    /* FAZ 24D — Trend */
    'extended','trend_angle','par_channel','flat_tb','disj_ch',
    'h_ray','cross','info_line',
    /* FAZ 24D — Fib */
    'fib_ch','fib_tz','fib_ext',
    /* FAZ 24D — Measurement */
    'p_range','d_range','dp_range',
    /* FAZ 24D — Freeform / Shape */
    'brush','path','highlight',
    'arrow','arr_up','arr_down','arr_mark',
    'arc','curve',
    /* FAZ 24D — Annotation */
    'callout','note','pin','flag','signpost','comment',
  ]);

  const TOOL_DEFS = {
    trendline:   { pts: 2, name: 'Trend Çizgisi' },
    ray:         { pts: 2, name: 'Işın' },
    h_line:      { pts: 1, name: 'Yatay Çizgi' },
    v_line:      { pts: 1, name: 'Dikey Çizgi' },
    h_ray:       { pts: 2, name: 'Yatay Işın' },
    cross:       { pts: 1, name: 'Kesişen Çizgiler' },
    info_line:   { pts: 2, name: 'Bilgi Çizgisi' },
    extended:    { pts: 2, name: 'Uzatılmış Çizgi' },
    trend_angle: { pts: 2, name: 'Trend Açısı' },
    par_channel: { pts: 3, name: 'Paralel Kanal' },
    flat_tb:     { pts: 2, name: 'Düz Üst/Alt' },
    disj_ch:     { pts: 4, name: 'Ayrık Kanal' },
    rect:        { pts: 2, name: 'Dikdörtgen' },
    triangle:    { pts: 3, name: 'Üçgen' },
    circle:      { pts: 2, name: 'Daire' },
    ellipse:     { pts: 2, name: 'Elips' },
    arc:         { pts: 2, name: 'Yay' },
    curve:       { pts: 2, name: 'Eğri' },
    fib_ret:     { pts: 2, name: 'Fib Düzeltmesi' },
    fib_ext:     { pts: 2, name: 'Fib Uzatma' },
    fib_ch:      { pts: 3, name: 'Fib Kanalı' },
    fib_tz:      { pts: 2, name: 'Fib Zaman Dilimi' },
    p_range:     { pts: 2, name: 'Fiyat Aralığı' },
    d_range:     { pts: 2, name: 'Tarih Aralığı' },
    dp_range:    { pts: 2, name: 'Tarih ve Fiyat Aralığı' },
    brush:       { pts: -1, name: 'Fırça' },
    path:        { pts: -1, name: 'Yol' },
    highlight:   { pts: 2, name: 'Vurgulayıcı' },
    arrow:       { pts: 2, name: 'Ok' },
    arr_up:      { pts: 1, name: 'Yukarı Ok' },
    arr_down:    { pts: 1, name: 'Aşağı Ok' },
    arr_mark:    { pts: 2, name: 'Ok İşaretleyicisi' },
    text:        { pts: 1, name: 'Metin' },
    p_label:     { pts: 1, name: 'Fiyat Etiketi' },
    callout:     { pts: 2, name: 'Balon' },
    note:        { pts: 1, name: 'Not' },
    pin:         { pts: 1, name: 'İğne' },
    flag:        { pts: 1, name: 'Bayrak' },
    signpost:    { pts: 1, name: 'Yön Levhası' },
    comment:     { pts: 1, name: 'Yorum' },
  };

  /* ═══════════════════════════════════════════════════════════════════
     State
     ═══════════════════════════════════════════════════════════════════ */
  let activeTool   = null;
  let pending      = [];
  let preview      = null;
  let drawings     = {};
  let selectedId   = null;
  let chartRefs    = {};
  let chartSymbols = {};
  let activeChart  = 'main';
  let idCtr        = 0;
  let textInp      = null;
  let rafId        = null;
  let dirty        = {};
  let delBtn       = null;
  let propPanel    = null;
  let brushStream  = false;
  let brushPoints  = [];
  let dragState    = null;

  /* ═══════════════════════════════════════════════════════════════════
     Utilities
     ═══════════════════════════════════════════════════════════════════ */
  const uid = () => 'd' + (++idCtr) + '_' + Date.now();

  function dist(x1, y1, x2, y2) { return Math.hypot(x2 - x1, y2 - y1); }

  function distSeg(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1, l2 = dx * dx + dy * dy;
    if (!l2) return dist(px, py, x1, y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / l2;
    t = Math.max(0, Math.min(1, t));
    return dist(px, py, x1 + t * dx, y1 + t * dy);
  }

  function distRay(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1, l2 = dx * dx + dy * dy;
    if (!l2) return dist(px, py, x1, y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / l2;
    t = Math.max(0, t);
    return dist(px, py, x1 + t * dx, y1 + t * dy);
  }

  function distLine(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1, l2 = dx * dx + dy * dy;
    if (!l2) return dist(px, py, x1, y1);
    const t = ((px - x1) * dx + (py - y1) * dy) / l2;
    return dist(px, py, x1 + t * dx, y1 + t * dy);
  }

  function fmtPrice(p) {
    if (p == null) return '\u2014';
    if (Math.abs(p) >= 100) return p.toFixed(2);
    if (Math.abs(p) >= 1)   return p.toFixed(4);
    return p.toFixed(6);
  }

  function angleDeg(x1, y1, x2, y2) {
    return Math.atan2(-(y2 - y1), x2 - x1) * 180 / Math.PI;
  }

  /* ═══════════════════════════════════════════════════════════════════
     Coordinate conversion
     ═══════════════════════════════════════════════════════════════════ */
  function toPixel(cid, time, price) {
    const r = chartRefs[cid];
    if (!r) return null;
    try {
      const x = r.chart.timeScale().timeToCoordinate(time);
      const y = r.series.priceToCoordinate(price);
      if (x == null || y == null) return null;
      return { x, y };
    } catch { return null; }
  }

  function toData(cid, px, py) {
    const r = chartRefs[cid];
    if (!r) return null;
    try {
      const price = r.series.coordinateToPrice(py);
      if (price == null) return null;
      let time = null;
      const ts = r.chart.timeScale();
      const logical = ts.coordinateToLogical(px);
      if (logical != null) {
        try {
          const d = r.series.dataByIndex(Math.round(logical));
          if (d && d.time != null) time = d.time;
        } catch {}
      }
      if (time == null) {
        const range = ts.getVisibleRange();
        if (range) {
          const x1 = ts.timeToCoordinate(range.from);
          const x2 = ts.timeToCoordinate(range.to);
          if (x1 != null && x2 != null && x2 !== x1) {
            const t = (px - x1) / (x2 - x1);
            time = Math.round(range.from + t * (range.to - range.from));
          }
        }
      }
      if (time == null) return null;
      return { time, price };
    } catch { return null; }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Canvas management
     ═══════════════════════════════════════════════════════════════════ */
  function setupCanvas(cid) {
    const r = chartRefs[cid];
    if (!r || r.canvas) return;
    const el = r.container;
    const cs = getComputedStyle(el);
    if (cs.position === 'static') el.style.position = 'relative';
    const c = document.createElement('canvas');
    c.className = 'drawing-canvas';
    c.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;z-index:10;pointer-events:none;touch-action:none;';
    el.appendChild(c);
    r.canvas = c;
    r.ctx = c.getContext('2d');
    resizeCanvas(cid);
    const ro = new ResizeObserver(() => resizeCanvas(cid));
    ro.observe(el);
    r._ro = ro;
    c.addEventListener('pointerdown', e => onPointerDown(cid, e), { passive: false });
    c.addEventListener('pointermove', e => onPointerMove(cid, e), { passive: false });
    c.addEventListener('pointerup',   e => onPointerUp(cid, e),   { passive: false });
    c.addEventListener('contextmenu', e => { if (activeTool) e.preventDefault(); });
    el.addEventListener('pointerdown', e => onSelectionClick(cid, e));
    try { r.chart.timeScale().subscribeVisibleTimeRangeChange(() => markDirty(cid)); } catch {}
  }

  function resizeCanvas(cid) {
    const r = chartRefs[cid];
    if (!r || !r.canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const w = r.container.clientWidth, h = r.container.clientHeight;
    r.canvas.width = w * dpr;
    r.canvas.height = h * dpr;
    r.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    markDirty(cid);
  }

  /* ═══════════════════════════════════════════════════════════════════
     Render loop
     ═══════════════════════════════════════════════════════════════════ */
  function markDirty(cid) {
    dirty[cid] = true;
    if (!rafId) rafId = requestAnimationFrame(renderLoop);
  }
  function markDirtyAll() { for (const c of Object.keys(chartRefs)) markDirty(c); }

  function renderLoop() {
    rafId = null;
    for (const cid of Object.keys(dirty)) {
      if (dirty[cid]) { dirty[cid] = false; render(cid); }
    }
  }

  function render(cid) {
    const r = chartRefs[cid];
    if (!r || !r.ctx) return;
    const ctx = r.ctx;
    const W = r.canvas.width / (window.devicePixelRatio || 1);
    const H = r.canvas.height / (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, W, H);
    const sym = chartSymbols[cid] || '';
    const list = (drawings[cid] || []).filter(d => d.symbol === sym && !d.hidden);
    for (const d of list) {
      const sel = d.id === selectedId;
      const pts = d.points.map(p => toPixel(cid, p.time, p.price));
      const color = sel ? SEL_COLOR : (d.color || DEF_COLOR);
      const lw = sel ? 2.5 : (d.lineWidth || 1.5);
      const dash = DASH_STYLES[d.lineStyle] || [];
      drawShape(ctx, d.type, pts, { color, lw, W, H, data: d, dash, fillOpacity: d.fillOpacity });
      if (sel) {
        ctx.fillStyle = SEL_COLOR;
        for (const p of pts) {
          if (!p) continue;
          ctx.beginPath(); ctx.arc(p.x, p.y, ANCHOR_R, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = '#000'; ctx.lineWidth = 1; ctx.stroke();
        }
      }
    }
    /* preview */
    if (activeTool && pending.length > 0 && cid === activeChart) {
      if (activeTool === 'brush' || activeTool === 'path') {
        const pts = (brushPoints.length ? brushPoints : pending).map(p => toPixel(cid, p.time, p.price));
        drawShape(ctx, activeTool, pts, { color: DEF_COLOR, lw: 1.5, W, H, data: { type: activeTool }, prev: true, dash: [] });
      } else {
        const pts = pending.map(p => toPixel(cid, p.time, p.price));
        if (preview) pts.push(preview);
        drawShape(ctx, activeTool, pts, { color: DEF_COLOR, lw: 1.5, W, H, data: { type: activeTool }, prev: true, dash: [] });
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Shape renderers
     ═══════════════════════════════════════════════════════════════════ */
  function drawShape(ctx, type, pts, o) {
    const vp = pts.filter(Boolean);
    if (!vp.length && type !== 'brush' && type !== 'path') return;
    ctx.save();
    ctx.strokeStyle = o.color;
    ctx.fillStyle = o.color;
    ctx.lineWidth = o.lw;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.setLineDash(o.dash || []);
    switch (type) {
      case 'trendline':   rTrend(ctx, vp, o);       break;
      case 'ray':         rRay(ctx, vp, o);         break;
      case 'h_line':      rHLine(ctx, vp, o);       break;
      case 'v_line':      rVLine(ctx, vp, o);       break;
      case 'h_ray':       rHRay(ctx, vp, o);        break;
      case 'cross':       rCross(ctx, vp, o);       break;
      case 'info_line':   rInfoLine(ctx, vp, o);    break;
      case 'extended':    rExtended(ctx, vp, o);    break;
      case 'trend_angle': rTrendAngle(ctx, vp, o);  break;
      case 'par_channel': rParChannel(ctx, vp, o);  break;
      case 'flat_tb':     rFlatTB(ctx, vp, o);      break;
      case 'disj_ch':     rDisjCh(ctx, vp, o);      break;
      case 'rect':        rRect(ctx, vp, o);        break;
      case 'triangle':    rTri(ctx, vp, o);         break;
      case 'circle':      rCirc(ctx, vp, o);        break;
      case 'ellipse':     rEllip(ctx, vp, o);       break;
      case 'arc':         rArc(ctx, vp, o);         break;
      case 'curve':       rCurve(ctx, vp, o);       break;
      case 'fib_ret':     rFib(ctx, vp, o);         break;
      case 'fib_ext':     rFibExt(ctx, vp, o);      break;
      case 'fib_ch':      rFibCh(ctx, vp, o);       break;
      case 'fib_tz':      rFibTZ(ctx, vp, o);       break;
      case 'p_range':     rPRange(ctx, vp, o);      break;
      case 'd_range':     rDRange(ctx, vp, o);      break;
      case 'dp_range':    rDPRange(ctx, vp, o);     break;
      case 'brush':       rBrush(ctx, vp, o);       break;
      case 'path':        rPath(ctx, vp, o);        break;
      case 'highlight':   rHighlight(ctx, vp, o);   break;
      case 'arrow':       rArrow(ctx, vp, o);       break;
      case 'arr_up':      rArrUp(ctx, vp, o);       break;
      case 'arr_down':    rArrDown(ctx, vp, o);     break;
      case 'arr_mark':    rArrMark(ctx, vp, o);     break;
      case 'text':        rText(ctx, vp, o);        break;
      case 'p_label':     rPLabel(ctx, vp, o);      break;
      case 'callout':     rCallout(ctx, vp, o);     break;
      case 'note':        rNote(ctx, vp, o);        break;
      case 'pin':         rPin(ctx, vp, o);         break;
      case 'flag':        rFlag(ctx, vp, o);        break;
      case 'signpost':    rSignpost(ctx, vp, o);    break;
      case 'comment':     rComment(ctx, vp, o);     break;
    }
    ctx.restore();
  }

  /* ── helpers ── */
  function xhair(ctx, p, o) {
    ctx.save(); ctx.strokeStyle = o.color; ctx.lineWidth = 0.5; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(p.x, 0); ctx.lineTo(p.x, o.H); ctx.moveTo(0, p.y); ctx.lineTo(o.W, p.y); ctx.stroke();
    ctx.restore();
  }
  function drawArrowhead(ctx, x1, y1, x2, y2, sz) {
    const a = Math.atan2(y2 - y1, x2 - x1);
    ctx.beginPath(); ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - sz * Math.cos(a - Math.PI / 6), y2 - sz * Math.sin(a - Math.PI / 6));
    ctx.lineTo(x2 - sz * Math.cos(a + Math.PI / 6), y2 - sz * Math.sin(a + Math.PI / 6));
    ctx.closePath(); ctx.fill();
  }
  function fillAlpha(ctx, alpha) { ctx.save(); ctx.globalAlpha = alpha || 0.08; ctx.fill(); ctx.restore(); }

  /* ════════════════ TREND ════════════════ */
  function rTrend(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rRay(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const dx = p[1].x - p[0].x, dy = p[1].y - p[0].y;
    const len = Math.hypot(dx, dy); if (!len) return;
    const sc = Math.max(o.W, o.H) * 2 / len;
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[0].x + dx * sc, p[0].y + dy * sc); ctx.stroke();
    ctx.beginPath(); ctx.arc(p[0].x, p[0].y, 3, 0, Math.PI * 2); ctx.fill();
  }

  function rHLine(ctx, p, o) {
    if (!p.length) return;
    const y = p[0].y;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(o.W, y); ctx.stroke();
    if (o.data && o.data.points && o.data.points[0]) {
      const txt = fmtPrice(o.data.points[0].price);
      ctx.font = 'bold 11px monospace';
      const tw = ctx.measureText(txt).width;
      ctx.globalAlpha = 0.9; ctx.fillRect(o.W - tw - 12, y - 9, tw + 8, 18);
      ctx.globalAlpha = 1; ctx.fillStyle = '#000'; ctx.fillText(txt, o.W - tw - 8, y + 4);
    }
  }

  function rVLine(ctx, p, o) {
    if (!p.length) return;
    ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(p[0].x, 0); ctx.lineTo(p[0].x, o.H); ctx.stroke();
  }

  function rHRay(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const dir = p[1].x >= p[0].x ? 1 : -1;
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(dir > 0 ? o.W : 0, p[0].y); ctx.stroke();
    ctx.beginPath(); ctx.arc(p[0].x, p[0].y, 3, 0, Math.PI * 2); ctx.fill();
  }

  function rCross(ctx, p, o) {
    if (!p.length) return;
    ctx.setLineDash([4, 3]); ctx.beginPath();
    ctx.moveTo(p[0].x, 0); ctx.lineTo(p[0].x, o.H);
    ctx.moveTo(0, p[0].y); ctx.lineTo(o.W, p[0].y); ctx.stroke();
  }

  function rInfoLine(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    const mx = (p[0].x + p[1].x) / 2, my = (p[0].y + p[1].y) / 2;
    if (o.data && o.data.points && o.data.points.length >= 2) {
      const dp = Math.abs(o.data.points[1].price - o.data.points[0].price);
      const pct = o.data.points[0].price ? (dp / Math.abs(o.data.points[0].price) * 100).toFixed(2) : '0';
      const txt = fmtPrice(dp) + ' (' + pct + '%)';
      ctx.font = '10px monospace';
      const tw = ctx.measureText(txt).width;
      ctx.fillStyle = 'rgba(10,14,23,0.85)'; ctx.fillRect(mx - tw / 2 - 4, my - 18, tw + 8, 16);
      ctx.fillStyle = o.color; ctx.fillText(txt, mx - tw / 2, my - 6);
    }
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rExtended(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const dx = p[1].x - p[0].x, dy = p[1].y - p[0].y;
    const len = Math.hypot(dx, dy); if (!len) return;
    const sc = Math.max(o.W, o.H) * 3 / len;
    ctx.beginPath(); ctx.moveTo(p[0].x - dx * sc, p[0].y - dy * sc); ctx.lineTo(p[0].x + dx * sc, p[0].y + dy * sc); ctx.stroke();
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rTrendAngle(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[0].y); ctx.stroke();
    ctx.setLineDash([]); ctx.beginPath(); ctx.moveTo(p[1].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    const angle = angleDeg(p[0].x, p[0].y, p[1].x, p[1].y);
    const rad = 20;
    ctx.beginPath(); ctx.arc(p[0].x, p[0].y, rad, 0, -angle * Math.PI / 180, angle > 0); ctx.stroke();
    ctx.font = 'bold 11px monospace'; ctx.fillText(angle.toFixed(1) + '\u00B0', p[0].x + rad + 4, p[0].y - 4);
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rParChannel(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    if (p.length >= 3) {
      const oy = p[2].y - p[0].y;
      ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y + oy); ctx.lineTo(p[1].x, p[1].y + oy); ctx.stroke();
      ctx.setLineDash([4, 4]); ctx.globalAlpha = 0.4;
      ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y + oy / 2); ctx.lineTo(p[1].x, p[1].y + oy / 2); ctx.stroke();
      ctx.globalAlpha = 1; ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y);
      ctx.lineTo(p[1].x, p[1].y + oy); ctx.lineTo(p[0].x, p[0].y + oy);
      ctx.closePath(); fillAlpha(ctx, o.fillOpacity || 0.06);
    }
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rFlatTB(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(0, p[0].y); ctx.lineTo(o.W, p[0].y); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, p[1].y); ctx.lineTo(o.W, p[1].y); ctx.stroke();
    ctx.beginPath(); ctx.rect(0, Math.min(p[0].y, p[1].y), o.W, Math.abs(p[1].y - p[0].y));
    fillAlpha(ctx, o.fillOpacity || 0.06);
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rDisjCh(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    if (p.length >= 4) {
      ctx.beginPath(); ctx.moveTo(p[2].x, p[2].y); ctx.lineTo(p[3].x, p[3].y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y);
      ctx.lineTo(p[3].x, p[3].y); ctx.lineTo(p[2].x, p[2].y); ctx.closePath();
      fillAlpha(ctx, o.fillOpacity || 0.06);
    } else if (p.length >= 3) {
      ctx.beginPath(); ctx.moveTo(p[2].x, p[2].y);
      if (preview) ctx.lineTo(preview.x, preview.y);
      ctx.stroke();
    }
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  /* ════════════════ SHAPES ════════════════ */
  function rRect(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const x = Math.min(p[0].x, p[1].x), y = Math.min(p[0].y, p[1].y);
    const w = Math.abs(p[1].x - p[0].x), h = Math.abs(p[1].y - p[0].y);
    ctx.beginPath(); ctx.rect(x, y, w, h); fillAlpha(ctx, o.fillOpacity || 0.08); ctx.stroke();
  }

  function rTri(ctx, p, o) {
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y);
    for (let i = 1; i < p.length; i++) ctx.lineTo(p[i].x, p[i].y);
    if (p.length >= 3) { ctx.closePath(); fillAlpha(ctx, o.fillOpacity || 0.08); }
    ctx.stroke();
  }

  function rCirc(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const rad = dist(p[0].x, p[0].y, p[1].x, p[1].y);
    ctx.beginPath(); ctx.arc(p[0].x, p[0].y, rad, 0, Math.PI * 2);
    fillAlpha(ctx, o.fillOpacity || 0.06); ctx.stroke();
  }

  function rEllip(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const rx = Math.abs(p[1].x - p[0].x) || 1, ry = Math.abs(p[1].y - p[0].y) || 1;
    ctx.beginPath(); ctx.ellipse(p[0].x, p[0].y, rx, ry, 0, 0, Math.PI * 2);
    fillAlpha(ctx, o.fillOpacity || 0.06); ctx.stroke();
  }

  function rArc(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const mx = (p[0].x + p[1].x) / 2, cpy = p[0].y - Math.abs(p[1].y - p[0].y);
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.quadraticCurveTo(mx, cpy, p[1].x, p[1].y); ctx.stroke();
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rCurve(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const cpX = (p[0].x + p[1].x) / 2, cpY = Math.min(p[0].y, p[1].y) - 40;
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.quadraticCurveTo(cpX, cpY, p[1].x, p[1].y); ctx.stroke();
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  /* ════════════════ FIBONACCI ════════════════ */
  function rFib(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const y1 = p[0].y, y2 = p[1].y, dy = y2 - y1;
    ctx.font = 'bold 11px monospace';
    for (const f of FIB) {
      const y = y1 + dy * f.r;
      ctx.strokeStyle = f.c; ctx.lineWidth = (f.r === 0 || f.r === 1) ? 1.5 : 1;
      ctx.globalAlpha = (f.r === 0 || f.r === 1) ? 1 : 0.7;
      ctx.setLineDash(f.r === 0.5 ? [4, 3] : []);
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(o.W, y); ctx.stroke();
      let pTxt = '';
      if (o.data && o.data.points && o.data.points.length >= 2) {
        const p1 = o.data.points[0].price, p2 = o.data.points[1].price;
        pTxt = ' (' + fmtPrice(p1 + (p2 - p1) * f.r) + ')';
      }
      ctx.fillStyle = f.c; ctx.fillText(f.l + pTxt, 8, y - 4);
    }
    const yA = y1 + dy * 0.382, yB = y1 + dy * 0.618;
    ctx.fillStyle = '#4CAF50'; ctx.globalAlpha = 0.04;
    ctx.fillRect(0, Math.min(yA, yB), o.W, Math.abs(yB - yA)); ctx.globalAlpha = 1;
  }

  function rFibExt(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const y1 = p[0].y, y2 = p[1].y, dy = y2 - y1;
    ctx.font = 'bold 11px monospace';
    for (const f of FIB_EXT) {
      const y = y1 + dy * f.r;
      if (y < -50 || y > o.H + 50) continue;
      ctx.strokeStyle = f.c; ctx.lineWidth = (f.r === 0 || f.r === 1) ? 1.5 : 1;
      ctx.globalAlpha = f.r > 1 ? 0.5 : 0.7;
      ctx.setLineDash(f.r > 1 ? [5, 3] : (f.r === 0.5 ? [4, 3] : []));
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(o.W, y); ctx.stroke();
      let pTxt = '';
      if (o.data && o.data.points && o.data.points.length >= 2) {
        const p1v = o.data.points[0].price, p2v = o.data.points[1].price;
        pTxt = ' (' + fmtPrice(p1v + (p2v - p1v) * f.r) + ')';
      }
      ctx.fillStyle = f.c; ctx.fillText(f.l + pTxt, 8, y - 4);
    }
    ctx.globalAlpha = 1;
  }

  function rFibCh(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    if (p.length >= 3) {
      const offsetY = p[2].y - p[0].y;
      ctx.font = 'bold 10px monospace';
      for (const f of FIB) {
        const oy = offsetY * f.r;
        ctx.strokeStyle = f.c; ctx.lineWidth = 1; ctx.globalAlpha = 0.6;
        ctx.setLineDash(f.r === 0.5 ? [4, 3] : []);
        ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y + oy); ctx.lineTo(p[1].x, p[1].y + oy); ctx.stroke();
        ctx.fillStyle = f.c; ctx.fillText(f.l, p[1].x + 4, p[1].y + oy + 4);
      }
      ctx.globalAlpha = 1;
    }
    for (const pt of p) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2); ctx.fill(); }
  }

  function rFibTZ(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const dx = Math.abs(p[1].x - p[0].x);
    const startX = Math.min(p[0].x, p[1].x);
    const fibs = [1, 1, 2, 3, 5, 8, 13, 21];
    let accum = 0;
    ctx.font = 'bold 10px monospace';
    for (let i = 0; i < fibs.length; i++) {
      accum += fibs[i];
      const x = startX + dx * accum / fibs[fibs.length - 1];
      if (x > o.W + 50) break;
      ctx.strokeStyle = FIB[i % FIB.length].c; ctx.globalAlpha = 0.6; ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, o.H); ctx.stroke();
      ctx.fillStyle = FIB[i % FIB.length].c; ctx.fillText('' + fibs[i], x + 2, 14);
    }
    ctx.globalAlpha = 1; ctx.setLineDash([]); ctx.strokeStyle = o.color; ctx.lineWidth = o.lw;
    ctx.beginPath(); ctx.moveTo(p[0].x, 0); ctx.lineTo(p[0].x, o.H); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(p[1].x, 0); ctx.lineTo(p[1].x, o.H); ctx.stroke();
  }

  /* ════════════════ MEASUREMENT ════════════════ */
  function rPRange(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const x = (p[0].x + p[1].x) / 2, y1 = p[0].y, y2 = p[1].y;
    ctx.beginPath(); ctx.moveTo(x, y1); ctx.lineTo(x, y2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 10, y1); ctx.lineTo(x + 10, y1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 10, y2); ctx.lineTo(x + 10, y2); ctx.stroke();
    drawArrowhead(ctx, x, y2, x, y1, 6);
    drawArrowhead(ctx, x, y1, x, y2, 6);
    if (o.data && o.data.points && o.data.points.length >= 2) {
      const dp = o.data.points[1].price - o.data.points[0].price;
      const pct = o.data.points[0].price ? (dp / Math.abs(o.data.points[0].price) * 100).toFixed(2) : '0';
      const txt = fmtPrice(Math.abs(dp)) + ' (' + (dp >= 0 ? '+' : '') + pct + '%)';
      ctx.font = 'bold 11px monospace'; const tw = ctx.measureText(txt).width;
      const my = (y1 + y2) / 2;
      ctx.fillStyle = 'rgba(10,14,23,0.85)'; ctx.fillRect(x + 8, my - 10, tw + 10, 20);
      ctx.fillStyle = dp >= 0 ? '#26d9a8' : '#f0506e'; ctx.fillText(txt, x + 13, my + 4);
    }
  }

  function rDRange(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const y = (p[0].y + p[1].y) / 2, x1 = p[0].x, x2 = p[1].x;
    ctx.beginPath(); ctx.moveTo(x1, y); ctx.lineTo(x2, y); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1, y - 10); ctx.lineTo(x1, y + 10); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x2, y - 10); ctx.lineTo(x2, y + 10); ctx.stroke();
    drawArrowhead(ctx, x2, y, x1, y, 6); drawArrowhead(ctx, x1, y, x2, y, 6);
    if (o.data && o.data.points && o.data.points.length >= 2) {
      const bars = Math.abs(o.data.points[1].time - o.data.points[0].time);
      const txt = bars + ' bars';
      ctx.font = 'bold 11px monospace'; const tw = ctx.measureText(txt).width;
      const mx = (x1 + x2) / 2;
      ctx.fillStyle = 'rgba(10,14,23,0.85)'; ctx.fillRect(mx - tw / 2 - 4, y - 24, tw + 8, 18);
      ctx.fillStyle = o.color; ctx.fillText(txt, mx - tw / 2, y - 10);
    }
  }

  function rDPRange(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const x1 = Math.min(p[0].x, p[1].x), y1 = Math.min(p[0].y, p[1].y);
    const w = Math.abs(p[1].x - p[0].x), h = Math.abs(p[1].y - p[0].y);
    ctx.setLineDash([4, 3]); ctx.beginPath(); ctx.rect(x1, y1, w, h);
    fillAlpha(ctx, o.fillOpacity || 0.06); ctx.stroke(); ctx.setLineDash([]);
    const mx = x1 + w / 2, my = y1 + h / 2;
    ctx.globalAlpha = 0.3;
    ctx.beginPath(); ctx.moveTo(mx, y1); ctx.lineTo(mx, y1 + h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1, my); ctx.lineTo(x1 + w, my); ctx.stroke();
    ctx.globalAlpha = 1;
    if (o.data && o.data.points && o.data.points.length >= 2) {
      const dp = o.data.points[1].price - o.data.points[0].price;
      const pct = o.data.points[0].price ? (dp / Math.abs(o.data.points[0].price) * 100).toFixed(2) : '0';
      const bars = Math.abs(o.data.points[1].time - o.data.points[0].time);
      const txt = fmtPrice(Math.abs(dp)) + ' | ' + bars + 'bars | ' + (dp >= 0 ? '+' : '') + pct + '%';
      ctx.font = 'bold 10px monospace'; const tw = ctx.measureText(txt).width;
      ctx.fillStyle = 'rgba(10,14,23,0.85)'; ctx.fillRect(mx - tw / 2 - 4, y1 - 18, tw + 8, 16);
      ctx.fillStyle = dp >= 0 ? '#26d9a8' : '#f0506e'; ctx.fillText(txt, mx - tw / 2, y1 - 6);
    }
  }

  /* ════════════════ FREEFORM ════════════════ */
  function rBrush(ctx, p, o) {
    if (p.length < 2) return;
    ctx.lineWidth = o.lw * 1.5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y);
    for (let i = 1; i < p.length; i++) { if (p[i]) ctx.lineTo(p[i].x, p[i].y); }
    ctx.stroke();
  }

  function rPath(ctx, p, o) {
    if (p.length < 2) return;
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y);
    for (let i = 1; i < p.length; i++) { if (p[i]) ctx.lineTo(p[i].x, p[i].y); }
    ctx.stroke();
    for (const pt of p) { if (pt) { ctx.beginPath(); ctx.arc(pt.x, pt.y, 2.5, 0, Math.PI * 2); ctx.fill(); } }
  }

  function rHighlight(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    const x1 = Math.min(p[0].x, p[1].x), y1 = Math.min(p[0].y, p[1].y);
    const w = Math.abs(p[1].x - p[0].x), h = Math.abs(p[1].y - p[0].y) || 20;
    ctx.fillStyle = o.color; ctx.globalAlpha = o.fillOpacity || 0.2;
    ctx.fillRect(x1, y1, w, h); ctx.globalAlpha = 1;
  }

  /* ════════════════ ARROWS ════════════════ */
  function rArrow(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    drawArrowhead(ctx, p[0].x, p[0].y, p[1].x, p[1].y, 12);
    ctx.beginPath(); ctx.arc(p[0].x, p[0].y, 3, 0, Math.PI * 2); ctx.fill();
  }

  function rArrMark(ctx, p, o) {
    if (p.length < 2) { if (p[0]) xhair(ctx, p[0], o); return; }
    ctx.beginPath(); ctx.moveTo(p[0].x, p[0].y); ctx.lineTo(p[1].x, p[1].y); ctx.stroke();
    drawArrowhead(ctx, p[0].x, p[0].y, p[1].x, p[1].y, 10);
  }

  function rArrUp(ctx, p, o) {
    if (!p.length) return;
    const x = p[0].x, y = p[0].y, sz = 16;
    ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x, y + sz); ctx.lineTo(x, y - sz); ctx.stroke();
    drawArrowhead(ctx, x, y + sz, x, y - sz, 10);
  }

  function rArrDown(ctx, p, o) {
    if (!p.length) return;
    const x = p[0].x, y = p[0].y, sz = 16;
    ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(x, y - sz); ctx.lineTo(x, y + sz); ctx.stroke();
    drawArrowhead(ctx, x, y - sz, x, y + sz, 10);
  }

  /* ════════════════ ANNOTATIONS ════════════════ */
  function rText(ctx, p, o) {
    if (!p.length) return;
    const txt = (o.data && o.data.text) || 'Metin';
    ctx.font = 'bold 13px -apple-system,BlinkMacSystemFont,sans-serif';
    const tw = ctx.measureText(txt).width;
    const bx = p[0].x - 2, by = p[0].y - 16;
    ctx.fillStyle = 'rgba(10,14,23,0.85)'; ctx.fillRect(bx - 4, by, tw + 12, 22);
    ctx.strokeStyle = o.color; ctx.lineWidth = 1; ctx.strokeRect(bx - 4, by, tw + 12, 22);
    ctx.fillStyle = o.color; ctx.fillText(txt, bx, p[0].y);
  }

  function rPLabel(ctx, p, o) {
    if (!p.length) return;
    const price = (o.data && o.data.points && o.data.points[0]) ? fmtPrice(o.data.points[0].price) : '\u2014';
    ctx.font = 'bold 12px monospace'; const tw = ctx.measureText(price).width;
    const tW = tw + 16, tH = 22, x = p[0].x, y = p[0].y;
    ctx.fillStyle = o.color;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 8, y - tH / 2);
    ctx.lineTo(x + 8 + tW, y - tH / 2); ctx.lineTo(x + 8 + tW, y + tH / 2);
    ctx.lineTo(x + 8, y + tH / 2); ctx.closePath();
    ctx.globalAlpha = 0.9; ctx.fill(); ctx.globalAlpha = 1;
    ctx.fillStyle = '#000'; ctx.fillText(price, x + 14, y + 4);
  }

  function rCallout(ctx, p, o) {
    if (p.length < 1) return;
    const txt = (o.data && o.data.text) || 'Balon';
    ctx.font = '12px -apple-system,BlinkMacSystemFont,sans-serif';
    const tw = ctx.measureText(txt).width;
    const bW = tw + 20, bH = 30, bx = p[0].x, by = p[0].y - bH - 20;
    const r = 6;
    ctx.fillStyle = 'rgba(10,14,23,0.9)';
    ctx.beginPath();
    ctx.moveTo(bx + r, by); ctx.lineTo(bx + bW - r, by);
    ctx.arcTo(bx + bW, by, bx + bW, by + r, r);
    ctx.lineTo(bx + bW, by + bH - r);
    ctx.arcTo(bx + bW, by + bH, bx + bW - r, by + bH, r);
    ctx.lineTo(bx + 20, by + bH);
    ctx.lineTo(p.length >= 2 ? p[1].x : bx + 10, p.length >= 2 ? p[1].y : p[0].y);
    ctx.lineTo(bx + 10, by + bH); ctx.lineTo(bx + r, by + bH);
    ctx.arcTo(bx, by + bH, bx, by + bH - r, r); ctx.lineTo(bx, by + r);
    ctx.arcTo(bx, by, bx + r, by, r); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = o.color; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.fillStyle = o.color; ctx.fillText(txt, bx + 10, by + bH / 2 + 4);
  }

  function rNote(ctx, p, o) {
    if (!p.length) return;
    const txt = (o.data && o.data.text) || 'Not';
    ctx.font = '12px -apple-system,BlinkMacSystemFont,sans-serif';
    const lines = txt.split('\n'), lh = 16;
    const maxW = Math.max(...lines.map(l => ctx.measureText(l).width));
    const bW = maxW + 16, bH = lines.length * lh + 12;
    const x = p[0].x, y = p[0].y;
    ctx.fillStyle = 'rgba(10,14,23,0.9)';
    ctx.beginPath(); ctx.roundRect(x, y, bW, bH, 4); ctx.fill();
    ctx.strokeStyle = o.color; ctx.lineWidth = 1; ctx.stroke();
    ctx.fillStyle = '#d0d0d8';
    for (let i = 0; i < lines.length; i++) ctx.fillText(lines[i], x + 8, y + 16 + i * lh);
  }

  function rPin(ctx, p, o) {
    if (!p.length) return;
    const x = p[0].x, y = p[0].y;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - 24); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y - 30, 8, 0, Math.PI * 2);
    ctx.fillStyle = o.color; ctx.globalAlpha = 0.9; ctx.fill(); ctx.globalAlpha = 1; ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y - 30, 3, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.fill();
  }

  function rFlag(ctx, p, o) {
    if (!p.length) return;
    const x = p[0].x, y = p[0].y;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - 36); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y - 36); ctx.lineTo(x + 20, y - 30); ctx.lineTo(x, y - 24); ctx.closePath();
    ctx.fillStyle = o.color; ctx.globalAlpha = 0.8; ctx.fill(); ctx.globalAlpha = 1; ctx.stroke();
  }

  function rSignpost(ctx, p, o) {
    if (!p.length) return;
    const x = p[0].x, y = p[0].y;
    ctx.beginPath(); ctx.moveTo(x, y + 20); ctx.lineTo(x, y - 24); ctx.lineWidth = 2; ctx.stroke();
    const sw = 40, sh = 16;
    ctx.fillStyle = o.color; ctx.globalAlpha = 0.85;
    ctx.beginPath(); ctx.moveTo(x - sw / 2, y - 20); ctx.lineTo(x + sw / 2, y - 20);
    ctx.lineTo(x + sw / 2 + 6, y - 12); ctx.lineTo(x + sw / 2, y - 4); ctx.lineTo(x - sw / 2, y - 4);
    ctx.closePath(); ctx.fill(); ctx.globalAlpha = 1; ctx.stroke();
    const stxt = (o.data && o.data.text) || '\u2192';
    ctx.font = 'bold 9px sans-serif'; ctx.fillStyle = '#000'; ctx.fillText(stxt, x - sw / 2 + 4, y - 9);
  }

  function rComment(ctx, p, o) {
    if (!p.length) return;
    const txt = (o.data && o.data.text) || '\uD83D\uDCAC';
    ctx.font = '12px -apple-system,BlinkMacSystemFont,sans-serif';
    const tw = ctx.measureText(txt).width;
    const bW = tw + 16, bH = 28, x = p[0].x, y = p[0].y;
    ctx.fillStyle = 'rgba(10,14,23,0.9)';
    ctx.beginPath(); ctx.roundRect(x, y - bH - 8, bW, bH, 6); ctx.fill();
    ctx.strokeStyle = o.color; ctx.lineWidth = 1; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 6, y - 8); ctx.lineTo(x + 4, y); ctx.lineTo(x + 14, y - 8);
    ctx.fillStyle = 'rgba(10,14,23,0.9)'; ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#d0d0d8'; ctx.fillText(txt, x + 8, y - bH + 10);
  }

  /* ═══════════════════════════════════════════════════════════════════
     Hit testing
     ═══════════════════════════════════════════════════════════════════ */
  function hitTest(cid, px, py) {
    const sym = chartSymbols[cid] || '';
    const list = (drawings[cid] || []).filter(d => d.symbol === sym && !d.hidden);
    const r = chartRefs[cid];
    if (!r) return null;
    const W = r.canvas.width / (window.devicePixelRatio || 1);
    const H = r.canvas.height / (window.devicePixelRatio || 1);
    for (let i = list.length - 1; i >= 0; i--) {
      const d = list[i];
      const pts = d.points.map(p => toPixel(cid, p.time, p.price)).filter(Boolean);
      if (!pts.length) continue;
      if (htShape(d.type, px, py, pts, W, H, d)) return d.id;
    }
    return null;
  }

  function hitTestAnchor(cid, px, py) {
    const sym = chartSymbols[cid] || '';
    const list = (drawings[cid] || []).filter(d => d.symbol === sym && !d.hidden);
    for (let i = list.length - 1; i >= 0; i--) {
      const d = list[i];
      const pts = d.points.map(p => toPixel(cid, p.time, p.price));
      for (let j = 0; j < pts.length; j++) {
        if (pts[j] && dist(px, py, pts[j].x, pts[j].y) < ANCHOR_R + 4) {
          return { drawingId: d.id, anchorIdx: j };
        }
      }
    }
    return null;
  }

  function htShape(type, px, py, pts, W, H) {
    const T = HIT_T;
    switch (type) {
      case 'trendline': case 'info_line':
        return pts.length >= 2 && distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T;
      case 'ray': case 'h_ray':
        return pts.length >= 2 && distRay(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T;
      case 'extended':
        return pts.length >= 2 && distLine(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T;
      case 'trend_angle':
        if (pts.length < 2) return false;
        return distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T
            || distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[0].y) < T
            || distSeg(px, py, pts[1].x, pts[0].y, pts[1].x, pts[1].y) < T;
      case 'h_line':
        return pts.length >= 1 && Math.abs(py - pts[0].y) < T;
      case 'v_line': case 'cross':
        return pts.length >= 1 && (Math.abs(px - pts[0].x) < T || Math.abs(py - pts[0].y) < T);
      case 'par_channel': {
        if (pts.length < 2) return false;
        if (distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T) return true;
        if (pts.length >= 3) {
          const oy = pts[2].y - pts[0].y;
          if (distSeg(px, py, pts[0].x, pts[0].y + oy, pts[1].x, pts[1].y + oy) < T) return true;
        }
        return false;
      }
      case 'flat_tb':
        return pts.length >= 2 && (Math.abs(py - pts[0].y) < T || Math.abs(py - pts[1].y) < T);
      case 'disj_ch': {
        if (pts.length < 2) return false;
        if (distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T) return true;
        if (pts.length >= 4 && distSeg(px, py, pts[2].x, pts[2].y, pts[3].x, pts[3].y) < T) return true;
        return false;
      }
      case 'rect': case 'dp_range': case 'highlight': {
        if (pts.length < 2) return false;
        const x1 = Math.min(pts[0].x, pts[1].x), x2 = Math.max(pts[0].x, pts[1].x);
        const y1 = Math.min(pts[0].y, pts[1].y), y2 = Math.max(pts[0].y, pts[1].y);
        return ((Math.abs(py - y1) < T || Math.abs(py - y2) < T) && px >= x1 - T && px <= x2 + T)
            || ((Math.abs(px - x1) < T || Math.abs(px - x2) < T) && py >= y1 - T && py <= y2 + T);
      }
      case 'triangle': {
        if (pts.length < 3) return false;
        for (let i = 0; i < 3; i++) {
          const j = (i + 1) % 3;
          if (distSeg(px, py, pts[i].x, pts[i].y, pts[j].x, pts[j].y) < T) return true;
        }
        return false;
      }
      case 'circle': {
        if (pts.length < 2) return false;
        const r = dist(pts[0].x, pts[0].y, pts[1].x, pts[1].y);
        return Math.abs(dist(px, py, pts[0].x, pts[0].y) - r) < T;
      }
      case 'ellipse': {
        if (pts.length < 2) return false;
        const rx = Math.abs(pts[1].x - pts[0].x) || 1, ry = Math.abs(pts[1].y - pts[0].y) || 1;
        const norm = Math.sqrt(Math.pow((px - pts[0].x) / rx, 2) + Math.pow((py - pts[0].y) / ry, 2));
        return Math.abs(norm - 1) * Math.min(rx, ry) < T;
      }
      case 'fib_ret': case 'fib_ext': {
        if (pts.length < 2) return false;
        const y1 = pts[0].y, dy = pts[1].y - y1;
        const levels = type === 'fib_ext' ? FIB_EXT : FIB;
        for (const f of levels) { if (Math.abs(py - (y1 + dy * f.r)) < T) return true; }
        return false;
      }
      case 'fib_ch': {
        if (pts.length < 2) return false;
        if (distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T) return true;
        if (pts.length >= 3) {
          const oy = pts[2].y - pts[0].y;
          for (const f of FIB) {
            const o2 = oy * f.r;
            if (distSeg(px, py, pts[0].x, pts[0].y + o2, pts[1].x, pts[1].y + o2) < T) return true;
          }
        }
        return false;
      }
      case 'fib_tz':
        return pts.length >= 2 && (Math.abs(px - pts[0].x) < T || Math.abs(px - pts[1].x) < T);
      case 'p_range': case 'd_range': {
        if (pts.length < 2) return false;
        if (type === 'p_range') {
          const mx = (pts[0].x + pts[1].x) / 2;
          return Math.abs(px - mx) < T * 2 && py >= Math.min(pts[0].y, pts[1].y) - T && py <= Math.max(pts[0].y, pts[1].y) + T;
        } else {
          const my = (pts[0].y + pts[1].y) / 2;
          return Math.abs(py - my) < T * 2 && px >= Math.min(pts[0].x, pts[1].x) - T && px <= Math.max(pts[0].x, pts[1].x) + T;
        }
      }
      case 'arrow': case 'arr_mark':
        return pts.length >= 2 && distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T;
      case 'arc': case 'curve':
        return pts.length >= 2 && distSeg(px, py, pts[0].x, pts[0].y, pts[1].x, pts[1].y) < T * 2;
      case 'brush': case 'path': {
        for (let i = 1; i < pts.length; i++) {
          if (distSeg(px, py, pts[i - 1].x, pts[i - 1].y, pts[i].x, pts[i].y) < T) return true;
        }
        return false;
      }
      case 'text': case 'p_label': case 'callout': case 'note': case 'pin':
      case 'flag': case 'signpost': case 'comment': case 'arr_up': case 'arr_down':
        return pts.length >= 1 && dist(px, py, pts[0].x, pts[0].y) < T * 4;
      default: return false;
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Event handling
     ═══════════════════════════════════════════════════════════════════ */
  function canvasCoords(cid, e) {
    const r = chartRefs[cid]; if (!r || !r.canvas) return null;
    const rc = r.canvas.getBoundingClientRect();
    return { x: e.clientX - rc.left, y: e.clientY - rc.top };
  }

  function onSelectionClick(cid, e) {
    if (activeTool) return;
    const r = chartRefs[cid]; if (!r || !r.canvas) return;
    const rc = r.canvas.getBoundingClientRect();
    const px = e.clientX - rc.left, py = e.clientY - rc.top;

    if (selectedId) {
      const anchor = hitTestAnchor(cid, px, py);
      if (anchor && anchor.drawingId === selectedId) {
        const d = findDrawing(anchor.drawingId);
        if (d) {
          e.preventDefault(); e.stopPropagation();
          dragState = { mode: 'anchor', drawingId: anchor.drawingId, cid, anchorIdx: anchor.anchorIdx,
            startMouse: { x: px, y: py }, origPoints: d.points.map(p => ({ ...p })) };
          r.canvas.style.pointerEvents = 'auto'; r.canvas.style.cursor = 'grabbing';
          try { r.chart.applyOptions({ handleScroll: false, handleScale: false }); } catch {}
          return;
        }
      }
    }

    const hit = hitTest(cid, px, py);
    if (hit) {
      selectDrawing(hit); markDirty(cid);
      if (e.detail >= 2) showPropertiesPanel(cid, hit);
      const d = findDrawing(hit);
      if (d) {
        e.preventDefault(); e.stopPropagation();
        dragState = { mode: 'move', drawingId: hit, cid, anchorIdx: -1,
          startMouse: { x: px, y: py }, origPoints: d.points.map(p => ({ ...p })) };
        r.canvas.style.pointerEvents = 'auto'; r.canvas.style.cursor = 'grabbing';
        try { r.chart.applyOptions({ handleScroll: false, handleScale: false }); } catch {}
      }
    } else if (selectedId) {
      selectDrawing(null); markDirty(cid);
    }
  }

  function onPointerDown(cid, e) {
    if (dragState) return;
    if (!activeTool) return;
    e.preventDefault(); e.stopPropagation();
    activeChart = cid;
    const co = canvasCoords(cid, e); if (!co) return;

    if (activeTool === 'brush' || activeTool === 'path') {
      const dp = toData(cid, co.x, co.y); if (!dp) return;
      brushStream = true; brushPoints = [dp]; pending = [dp]; markDirty(cid); return;
    }

    const dp = toData(cid, co.x, co.y); if (!dp) return;
    const def = TOOL_DEFS[activeTool]; if (!def) return;
    pending.push(dp);
    if (pending.length >= def.pts) finalizeDrawing(cid);
    else markDirty(cid);
  }

  function onPointerMove(cid, e) {
    if (dragState && dragState.cid === cid) {
      const co = canvasCoords(cid, e); if (!co) return;
      const d = findDrawing(dragState.drawingId); if (!d) return;
      const dp = toData(cid, co.x, co.y); if (!dp) return;
      const startDp = toData(cid, dragState.startMouse.x, dragState.startMouse.y); if (!startDp) return;
      if (dragState.mode === 'anchor') {
        d.points[dragState.anchorIdx] = dp;
      } else {
        const dtTime = dp.time - startDp.time, dtPrice = dp.price - startDp.price;
        for (let i = 0; i < d.points.length; i++) {
          d.points[i] = { time: dragState.origPoints[i].time + dtTime, price: dragState.origPoints[i].price + dtPrice };
        }
      }
      save(); markDirty(cid); return;
    }
    if (brushStream && (activeTool === 'brush' || activeTool === 'path') && cid === activeChart) {
      const co = canvasCoords(cid, e); if (!co) return;
      const dp = toData(cid, co.x, co.y); if (dp) { brushPoints.push(dp); markDirty(cid); }
      return;
    }
    if (!activeTool || !pending.length || cid !== activeChart) return;
    const co = canvasCoords(cid, e); if (!co) return;
    preview = { x: co.x, y: co.y }; markDirty(cid);
  }

  function onPointerUp(cid, e) {
    if (dragState) {
      const r = chartRefs[dragState.cid];
      if (r) {
        r.canvas.style.pointerEvents = 'none'; r.canvas.style.cursor = 'default';
        try { r.chart.applyOptions({ handleScroll: true, handleScale: true }); } catch {}
      }
      dragState = null; save(); updateList(); return;
    }
    if (brushStream && (activeTool === 'brush' || activeTool === 'path')) {
      brushStream = false;
      if (brushPoints.length >= 2) {
        const sym = chartSymbols[cid] || (typeof currentSymbol !== 'undefined' ? currentSymbol : '');
        addDrawing(cid, { id: uid(), type: activeTool, symbol: sym, points: [...brushPoints], color: DEF_COLOR, created: Date.now() });
      }
      brushPoints = []; pending = []; preview = null; markDirtyAll();
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Finalize / Text input
     ═══════════════════════════════════════════════════════════════════ */
  function finalizeDrawing(cid) {
    if (!activeTool || !pending.length) return;
    const sym = chartSymbols[cid] || (typeof currentSymbol !== 'undefined' ? currentSymbol : '');
    const textTools = new Set(['text', 'callout', 'note', 'comment', 'signpost']);
    if (textTools.has(activeTool)) {
      const toolType = activeTool;
      showTextInput(cid, pending[0], txt => {
        if (txt && txt.trim()) {
          addDrawing(cid, { id: uid(), type: toolType, symbol: sym, points: [...pending], color: DEF_COLOR, text: txt.trim(), created: Date.now() });
        }
        resetPending();
      });
      return;
    }
    addDrawing(cid, { id: uid(), type: activeTool, symbol: sym, points: [...pending], color: DEF_COLOR, created: Date.now() });
    resetPending();
  }

  function resetPending() { pending = []; preview = null; markDirtyAll(); }

  function showTextInput(cid, dataPoint, cb) {
    const r = chartRefs[cid]; if (!r) { cb(null); return; }
    const pt = toPixel(cid, dataPoint.time, dataPoint.price); if (!pt) { cb(null); return; }
    if (textInp) textInp.remove();
    const box = document.createElement('div');
    box.className = 'drawing-text-input';
    box.style.cssText = 'position:absolute;left:' + pt.x + 'px;top:' + pt.y + 'px;z-index:20;';
    box.innerHTML = '<input type="text" class="dt-inp" placeholder="Metin girin\u2026" autofocus>' +
      '<button class="dt-ok">\u2713</button><button class="dt-no">\u2715</button>';
    r.container.appendChild(box); textInp = box;
    const inp = box.querySelector('.dt-inp'); inp.focus();
    const done = v => { box.remove(); textInp = null; cb(v); };
    box.querySelector('.dt-ok').onclick = () => done(inp.value);
    box.querySelector('.dt-no').onclick = () => done(null);
    inp.onkeydown = e => { if (e.key === 'Enter') done(inp.value); if (e.key === 'Escape') done(null); };
  }

  /* ═══════════════════════════════════════════════════════════════════
     Drawing CRUD
     ═══════════════════════════════════════════════════════════════════ */
  function findDrawing(did) {
    for (const cid of Object.keys(drawings)) {
      const d = (drawings[cid] || []).find(d => d.id === did);
      if (d) return d;
    }
    return null;
  }

  function addDrawing(cid, d) {
    if (!drawings[cid]) drawings[cid] = [];
    drawings[cid].push(d); selectedId = d.id;
    save(); markDirty(cid); updateList(); showDelBtn(cid);
  }

  function removeDrawing(did) {
    for (const cid of Object.keys(drawings)) {
      const idx = (drawings[cid] || []).findIndex(d => d.id === did);
      if (idx !== -1) {
        drawings[cid].splice(idx, 1);
        if (selectedId === did) { selectedId = null; hideDelBtn(); hidePropertiesPanel(); }
        save(); markDirty(cid); updateList(); return true;
      }
    }
    return false;
  }

  function selectDrawing(id) {
    selectedId = id;
    if (id) {
      for (const cid of Object.keys(drawings)) {
        if ((drawings[cid] || []).find(d => d.id === id)) { showDelBtn(cid); markDirty(cid); break; }
      }
    } else { hideDelBtn(); hidePropertiesPanel(); }
    markDirtyAll(); updateList();
  }

  function toggleVis(did) {
    for (const cid of Object.keys(drawings)) {
      const d = (drawings[cid] || []).find(d => d.id === did);
      if (d) { d.hidden = !d.hidden; save(); markDirty(cid); updateList(); return; }
    }
  }

  function renameDrawing(did, newName) {
    const d = findDrawing(did);
    if (d) { d.text = newName; save(); updateList(); markDirtyAll(); }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Delete / Action bar
     ═══════════════════════════════════════════════════════════════════ */
  function showDelBtn(cid) {
    if (!delBtn) {
      delBtn = document.createElement('div');
      delBtn.className = 'drawing-action-bar';
      delBtn.innerHTML = '<button class="dab-btn dab-props" title="\u00D6zellikler">\u2699</button>' +
        '<button class="dab-btn dab-delete" title="Sil">\uD83D\uDDD1</button>';
      delBtn.querySelector('.dab-delete').onclick = () => { if (selectedId) removeDrawing(selectedId); };
      delBtn.querySelector('.dab-props').onclick = () => {
        if (selectedId) {
          for (const c of Object.keys(drawings)) {
            if ((drawings[c] || []).find(d => d.id === selectedId)) { showPropertiesPanel(c, selectedId); break; }
          }
        }
      };
      document.body.appendChild(delBtn);
    }
    delBtn.classList.add('visible');
    posDelBtn(cid);
  }

  function hideDelBtn() { if (delBtn) delBtn.classList.remove('visible'); }

  function posDelBtn(cid) {
    if (!delBtn || !selectedId) return;
    const r = chartRefs[cid]; if (!r) return;
    const rc = r.container.getBoundingClientRect();
    delBtn.style.left = (rc.right - 90) + 'px';
    delBtn.style.top = (rc.top + 8) + 'px';
  }

  /* ═══════════════════════════════════════════════════════════════════
     Properties Panel
     ═══════════════════════════════════════════════════════════════════ */
  function showPropertiesPanel(cid, did) {
    hidePropertiesPanel();
    const d = findDrawing(did); if (!d) return;
    const def = TOOL_DEFS[d.type];
    const colors = ['#5b8cf5','#26d9a8','#f0506e','#f5c842','#ff9800','#9c27b0','#e91e63','#ffffff','#888888'];
    const widths = [1, 1.5, 2, 3, 4];
    const styles = [{ id:'solid', label:'\u2500\u2500\u2500' },{ id:'dashed', label:'- - -' },{ id:'dotted', label:'\u00B7\u00B7\u00B7' }];

    const panel = document.createElement('div');
    panel.id = 'drawingPropsPanel';
    panel.className = 'drawing-props-panel';
    panel.innerHTML = '<div class="dp-header"><span>\u2699 ' + (def ? def.name : d.type) + '</span>' +
      '<button class="dp-close" title="Kapat">\u2715</button></div>' +
      '<div class="dp-body">' +
      '<div class="dp-section"><div class="dp-label">Renk</div><div class="dp-colors">' +
      colors.map(c => '<button class="dp-color-btn' + (c === (d.color || DEF_COLOR) ? ' active' : '') +
        '" data-color="' + c + '" style="background:' + c + '"></button>').join('') +
      '</div></div>' +
      '<div class="dp-section"><div class="dp-label">\u00C7izgi Kal\u0131nl\u0131\u011F\u0131</div><div class="dp-widths">' +
      widths.map(w => '<button class="dp-width-btn' + (w === (d.lineWidth || 1.5) ? ' active' : '') +
        '" data-w="' + w + '"><span style="display:block;height:' + w + 'px;background:currentColor;border-radius:' + (w/2) + 'px"></span></button>').join('') +
      '</div></div>' +
      '<div class="dp-section"><div class="dp-label">\u00C7izgi Tipi</div><div class="dp-styles">' +
      styles.map(s => '<button class="dp-style-btn' + (s.id === (d.lineStyle || 'solid') ? ' active' : '') +
        '" data-style="' + s.id + '">' + s.label + '</button>').join('') +
      '</div></div>' +
      '<div class="dp-section"><div class="dp-label">Dolgu Opakl\u0131\u011F\u0131</div>' +
      '<input type="range" class="dp-opacity" min="0" max="50" value="' + Math.round((d.fillOpacity || 0.08) * 100) + '" /></div>' +
      (d.text !== undefined ? '<div class="dp-section"><div class="dp-label">Metin</div>' +
        '<input type="text" class="dp-text-input" value="' + (d.text || '') + '" /></div>' : '') +
      '<div class="dp-section dp-danger"><button class="dp-delete-btn">\uD83D\uDDD1 \u00C7izimi Sil</button></div></div>';

    document.body.appendChild(panel);
    requestAnimationFrame(() => panel.classList.add('open'));
    propPanel = panel;

    panel.querySelector('.dp-close').onclick = () => hidePropertiesPanel();
    panel.querySelectorAll('.dp-color-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        d.color = btn.dataset.color; save(); markDirtyAll();
        panel.querySelectorAll('.dp-color-btn').forEach(b => b.classList.toggle('active', b === btn));
      });
    });
    panel.querySelectorAll('.dp-width-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        d.lineWidth = parseFloat(btn.dataset.w); save(); markDirtyAll();
        panel.querySelectorAll('.dp-width-btn').forEach(b => b.classList.toggle('active', b === btn));
      });
    });
    panel.querySelectorAll('.dp-style-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        d.lineStyle = btn.dataset.style; save(); markDirtyAll();
        panel.querySelectorAll('.dp-style-btn').forEach(b => b.classList.toggle('active', b === btn));
      });
    });
    const opSlider = panel.querySelector('.dp-opacity');
    if (opSlider) opSlider.addEventListener('input', () => { d.fillOpacity = parseInt(opSlider.value) / 100; save(); markDirtyAll(); });
    const textInput = panel.querySelector('.dp-text-input');
    if (textInput) textInput.addEventListener('input', () => { d.text = textInput.value; save(); markDirtyAll(); });
    panel.querySelector('.dp-delete-btn').onclick = () => { removeDrawing(did); hidePropertiesPanel(); };
  }

  function hidePropertiesPanel() {
    if (propPanel) { propPanel.classList.remove('open'); setTimeout(() => { if (propPanel) { propPanel.remove(); propPanel = null; } }, 300); }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Tool activation
     ═══════════════════════════════════════════════════════════════════ */
  function setActiveTool(id) {
    if (id && !ACTIVE_TOOL_IDS.has(id)) { toast((TOOL_DEFS[id] || {}).name || id, false); return false; }
    if (id === activeTool) { clearTool(); return false; }
    activeTool = id; pending = []; preview = null; brushStream = false; brushPoints = [];
    selectedId = null; hideDelBtn();
    for (const cid of Object.keys(chartRefs)) {
      const r = chartRefs[cid];
      if (r && r.canvas) { r.canvas.style.pointerEvents = id ? 'auto' : 'none'; r.canvas.style.cursor = id ? 'crosshair' : 'default'; }
      if (r && r.chart) { try { r.chart.applyOptions({ handleScroll: !id, handleScale: !id }); } catch {} }
    }
    updateIndicator(); return true;
  }

  function clearTool() {
    activeTool = null; pending = []; preview = null; brushStream = false; brushPoints = [];
    for (const cid of Object.keys(chartRefs)) {
      const r = chartRefs[cid];
      if (r && r.canvas) { r.canvas.style.pointerEvents = 'none'; r.canvas.style.cursor = 'default'; }
      if (r && r.chart) { try { r.chart.applyOptions({ handleScroll: true, handleScale: true }); } catch {} }
      markDirty(cid);
    }
    updateIndicator();
  }

  function toast(name, ok) {
    let t = document.getElementById('drawingToast');
    if (!t) { t = document.createElement('div'); t.id = 'drawingToast'; t.className = 'drawing-toast'; document.body.appendChild(t); }
    t.textContent = ok ? '\u270F\uFE0F ' + name + ' arac\u0131 se\u00E7ildi' : name + ' \u2014 yak\u0131nda';
    t.classList.add('visible');
    setTimeout(() => t.classList.remove('visible'), 2000);
  }

  function updateIndicator() {
    let el = document.getElementById('drawingToolIndicator');
    if (activeTool) {
      const def = TOOL_DEFS[activeTool];
      if (!el) {
        el = document.createElement('div'); el.id = 'drawingToolIndicator'; el.className = 'drawing-tool-indicator';
        el.innerHTML = '<span class="dti-label"></span><button class="dti-cancel" title="\u0130ptal (ESC)">\u2715</button>';
        el.querySelector('.dti-cancel').onclick = () => {
          clearTool(); document.querySelectorAll('#drawGrid .tool-card').forEach(c => c.classList.remove('selected'));
        };
        document.body.appendChild(el);
      }
      el.querySelector('.dti-label').textContent = '\u270F\uFE0F ' + (def ? def.name : activeTool);
      el.classList.add('visible');
    } else { if (el) el.classList.remove('visible'); }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Drawing List Panel (Object Tree)
     ═══════════════════════════════════════════════════════════════════ */
  function buildListPanel() {
    if (document.getElementById('drawingListPanel')) return;
    const el = document.createElement('div');
    el.id = 'drawingListPanel'; el.className = 'drawing-list-panel';
    el.innerHTML = '<div class="dl-header"><span class="dl-title">\uD83D\uDCD0 \u00C7izim Listesi</span>' +
      '<div class="dl-hdr-acts"><button class="dl-clear" title="T\u00FCm\u00FCn\u00FC Sil">\uD83D\uDDD1</button>' +
      '<button class="dl-close" title="Kapat">\u2715</button></div></div><div class="dl-items"></div>';
    document.body.appendChild(el);
    el.querySelector('.dl-close').onclick = () => el.classList.remove('open');
    el.querySelector('.dl-clear').onclick = () => {
      if (!confirm('T\u00FCm \u00E7izimleri silmek istedi\u011Finize emin misiniz?')) return;
      for (const cid of Object.keys(drawings)) { drawings[cid] = []; markDirty(cid); }
      selectedId = null; hideDelBtn(); save(); updateList();
    };
    updateList();
  }

  function updateList() {
    const panel = document.getElementById('drawingListPanel'); if (!panel) return;
    const items = panel.querySelector('.dl-items'); if (!items) return;
    const all = [];
    for (const cid of Object.keys(drawings)) {
      for (const d of (drawings[cid] || [])) all.push({ ...d, _cid: cid });
    }
    if (!all.length) { items.innerHTML = '<div class="dl-empty">\u00C7izim yok</div>'; return; }
    items.innerHTML = all.map(d => {
      const def = TOOL_DEFS[d.type]; const nm = def ? def.name : d.type;
      return '<div class="dl-item' + (d.id === selectedId ? ' selected' : '') + (d.hidden ? ' hidden' : '') +
        '" data-id="' + d.id + '" data-cid="' + d._cid + '">' +
        '<span class="dl-color-dot" style="background:' + (d.color || DEF_COLOR) + '"></span>' +
        '<span class="dl-name">' + nm + (d.text ? ': ' + d.text : '') + '</span>' +
        '<div class="dl-acts">' +
        '<button class="dl-rename" data-id="' + d.id + '" title="Yeniden Adland\u0131r">\u270E</button>' +
        '<button class="dl-vis" data-id="' + d.id + '" title="' + (d.hidden ? 'G\u00F6ster' : 'Gizle') + '">' + (d.hidden ? '\u25FB' : '\u25FC') + '</button>' +
        '<button class="dl-del" data-id="' + d.id + '" title="Sil">\u2715</button>' +
        '</div></div>';
    }).join('');
    items.querySelectorAll('.dl-item').forEach(el => {
      el.addEventListener('click', e => {
        if (e.target.closest('.dl-vis') || e.target.closest('.dl-del') || e.target.closest('.dl-rename')) return;
        selectDrawing(el.dataset.id);
      });
    });
    items.querySelectorAll('.dl-vis').forEach(b => b.addEventListener('click', () => toggleVis(b.dataset.id)));
    items.querySelectorAll('.dl-del').forEach(b => b.addEventListener('click', () => removeDrawing(b.dataset.id)));
    items.querySelectorAll('.dl-rename').forEach(b => b.addEventListener('click', () => {
      const newName = prompt('Yeni ad:', ''); if (newName !== null) renameDrawing(b.dataset.id, newName);
    }));
  }

  function toggleList() {
    const p = document.getElementById('drawingListPanel'); if (!p) return;
    p.classList.toggle('open'); if (p.classList.contains('open')) updateList();
  }

  /* ═══════════════════════════════════════════════════════════════════
     Persistence
     ═══════════════════════════════════════════════════════════════════ */
  function save() {
    try {
      const out = {};
      for (const cid of Object.keys(drawings)) {
        out[cid] = (drawings[cid] || []).map(d => ({
          id: d.id, type: d.type, symbol: d.symbol, points: d.points, color: d.color,
          text: d.text || undefined, hidden: d.hidden || undefined,
          lineWidth: d.lineWidth || undefined, lineStyle: d.lineStyle || undefined,
          fillOpacity: d.fillOpacity || undefined, created: d.created,
        }));
      }
      localStorage.setItem(STORE_KEY, JSON.stringify(out));
      // Cloud sync: push drawings to server if logged in
      _cloudSaveDebounced(out);
    } catch {}
  }

  let _cloudSaveTimer = null;
  function _cloudSaveDebounced(data) {
    clearTimeout(_cloudSaveTimer);
    _cloudSaveTimer = setTimeout(() => {
      fetch('/api/auth/me').then(r => r.json()).then(me => {
        if (me.logged_in) {
          fetch('/api/auth/data/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'drawings', data: data }),
          }).catch(() => {});
        }
      }).catch(() => {});
    }, 2000);
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORE_KEY); if (!raw) return;
      const data = JSON.parse(raw);
      _applyDrawingData(data);
    } catch {}
    // Also try to load from cloud
    _cloudLoad();
  }

  function _applyDrawingData(data) {
    for (const cid of Object.keys(data)) {
      drawings[cid] = data[cid] || [];
      for (const d of drawings[cid]) {
        const m = d.id.match(/^d(\d+)_/);
        if (m) idCtr = Math.max(idCtr, parseInt(m[1]));
      }
    }
  }

  function _cloudLoad() {
    fetch('/api/auth/me').then(r => r.json()).then(me => {
      if (me.logged_in) {
        fetch('/api/auth/data/load', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: 'drawings' }),
        }).then(r => r.json()).then(resp => {
          if (resp.ok && resp.data) {
            _applyDrawingData(resp.data);
            // Also update localStorage
            localStorage.setItem(STORE_KEY, JSON.stringify(resp.data));
            markDirtyAll();
          }
        }).catch(() => {});
      }
    }).catch(() => {});
  }

  /* ═══════════════════════════════════════════════════════════════════
     Chart registration
     ═══════════════════════════════════════════════════════════════════ */
  function registerChart(chartId, chart, series, container, symbol) {
    const existing = chartRefs[chartId];
    if (existing && existing.container === container) {
      existing.chart = chart; existing.series = series;
      chartSymbols[chartId] = symbol || ''; markDirty(chartId); return;
    }
    unregisterChart(chartId);
    chartRefs[chartId] = { chart, series, container, canvas: null, ctx: null };
    chartSymbols[chartId] = symbol || '';
    setupCanvas(chartId); markDirty(chartId);
  }

  function unregisterChart(chartId) {
    const r = chartRefs[chartId]; if (!r) return;
    if (r._ro) r._ro.disconnect();
    if (r.canvas) r.canvas.remove();
    delete chartRefs[chartId]; delete dirty[chartId];
  }

  function updateSymbol(chartId, symbol) { chartSymbols[chartId] = symbol; markDirty(chartId); }

  /* ═══════════════════════════════════════════════════════════════════
     Init & keyboard
     ═══════════════════════════════════════════════════════════════════ */
  function init() {
    load(); buildListPanel();
    window.addEventListener('bw:tool-selected', e => {
      const t = e.detail;
      if (t && t.id) { const ok = setActiveTool(t.id); if (ok) toast(TOOL_DEFS[t.id] ? TOOL_DEFS[t.id].name : t.id, true); }
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        if (activeTool) { clearTool(); document.querySelectorAll('#drawGrid .tool-card').forEach(c => c.classList.remove('selected')); }
        else if (selectedId) selectDrawing(null);
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        removeDrawing(selectedId);
      }
    });
  }

  /* ═══════════════════════════════════════════════════════════════════
     Public API
     ═══════════════════════════════════════════════════════════════════ */
  return {
    init, registerChart, unregisterChart, updateSymbol,
    setActiveTool, clearTool,
    deleteSelected: () => selectedId && removeDrawing(selectedId),
    getDrawings: cid => drawings[cid] || [],
    getAllDrawings: () => drawings,
    render: () => markDirtyAll(),
    toggleDrawingList: toggleList,
    isToolActive: () => !!activeTool,
    getActiveTool: () => activeTool,
    ACTIVE_TOOL_IDS,
  };
})();
