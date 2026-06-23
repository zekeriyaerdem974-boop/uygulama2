// static/js/index.js
import { jget, fmt, toLocalISO } from './utils.js';

const tickerEl = document.getElementById('ticker-marquee');
const btcStatsEl = document.getElementById('btc-stats');
const fngValueEl = document.getElementById('fng-value');
const fngClassEl = document.getElementById('fng-class');
const fngTimeEl  = document.getElementById('fng-time');
const checklistEl = document.getElementById('checklist');
const scanSummaryEl = document.getElementById('scan-summary');
const etfListEl = document.getElementById('etf-list');
const estimateEl = document.getElementById('estimate');
const oiCard = document.getElementById('oi-card');
const hashCard = document.getElementById('hash-card');
const stableCard = document.getElementById('stable-card');
const premiumCard = document.getElementById('premium-card');
const pumpsEl = document.getElementById('pumps');

/* ---------------- helpers ---------------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const API = {
  thresholds: '/api/thresholds',
  signals: (limit = 9) => `/api/signals?limit=${encodeURIComponent(limit)}`,
  binanceKlines: (symbol, interval='1d', limit=120) =>
    `https://api.binance.com/api/v3/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`,
};

const state = {
  thresholds: null,
  signals: [],
  limit: 9,             // pump kart sayısı
  etf: {
    raw: [],
    filter: 'ALL',      // ALL | BTC | ETH | SOL | XRP
    page: 1,
    pageSize: 8,
  },
  refreshTimer: null,   // 15s auto-refresh
  projections: {},      // { symbol: { fibTargets:[], atrTargets:[], ath: num } }
};

function fmtPct(x) {
  if (x === null || x === undefined || Number.isNaN(x)) return '--';
  return `${(+x).toFixed(2)}%`;
}
function fmtNum(x, dp = 6) {
  if (x === null || x === undefined || Number.isNaN(x)) return '--';
  return (+x).toFixed(dp);
}
function badge(text, color) {
  const colors = {
    green: 'bg-emerald-900/50 text-emerald-300 border-emerald-700',
    yellow: 'bg-yellow-900/40 text-yellow-200 border-yellow-700',
    red: 'bg-rose-900/40 text-rose-200 border-rose-700',
    gray: 'bg-neutral-800 text-neutral-300 border-neutral-700',
    blue: 'bg-sky-900/40 text-sky-200 border-sky-700',
  };
  return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-lg border ${colors[color] || colors.gray}">${text}</span>`;
}
const debounce = (fn, ms = 400) => {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
};

/* ----- skor rozeti yardımcıları ----- */
function scoreCls(score){
  const s = Number(score ?? 0);
  if (s >= 75) return {wrap:'bg-emerald-950 border-emerald-700 text-emerald-300', ring:'ring-emerald-800/50'};
  if (s >= 50) return {wrap:'bg-yellow-950 border-yellow-700 text-yellow-200', ring:'ring-yellow-800/50'};
  return {wrap:'bg-rose-950 border-rose-700 text-rose-200', ring:'ring-rose-800/50'};
}
function scoreBadgeHTML(score){
  const {wrap, ring} = scoreCls(score);
  const val = (score ?? '--');
  return `
    <div class="absolute -top-3 -right-3 z-10" data-slot="score">
      <div class="w-12 h-12 rounded-full border ${wrap} flex items-center justify-center
                  shadow-inner ring-8 ${ring} backdrop-blur-sm">
        <span class="text-sm font-semibold">${val}</span>
      </div>
    </div>
  `;
}

/* ---------------- Binance canlı ticker ---------------- */
(function startTicker() {
  const ws = new WebSocket('wss://stream.binance.com:9443/ws/!ticker@arr');
  let lastRender = 0;
  ws.onmessage = (evt) => {
    const now = Date.now();
    if (now - lastRender < 1000) return;
    lastRender = now;
    const data = JSON.parse(evt.data);
    const rows = data
      .filter(x => x.s && x.s.endsWith('USDT'))
      .sort((a,b)=> parseFloat(b.q) - parseFloat(a.q))
      .slice(0, 40)
      .map(x => {
        const chg = parseFloat(x.P);
        const cls = chg >= 0 ? 'badge-green' : 'badge-red';
        return `<span class="mx-2 badge ${cls}">${x.s} ${chg.toFixed(2)}%</span>`;
      }).join('');
    tickerEl.innerHTML = rows;
  };
  ws.onclose = () => setTimeout(startTicker, 1500);
  ws.onerror = () => ws.close();
})();

/* ---------------- BTC/FNG/OI/Stable/Hash/Premium ---------------- */
async function loadBTC(){ const r=await jget('/api/btc_indicators'); if(!r.ok) return; const d=r.data;
  btcStatsEl.innerHTML = `
    <div class="card"><div class="text-xs text-neutral-400">BTC/USDT</div><div class="text-2xl font-semibold">${fmt(d.price)}</div></div>
    <div class="card"><div class="text-xs text-neutral-400">SMA 20</div><div class="text-xl">${fmt(d.sma20)}</div></div>
    <div class="card"><div class="text-xs text-neutral-400">SMA 50</div><div class="text-xl">${fmt(d.sma50)}</div></div>
    <div class="card"><div class="text-xs text-neutral-400">SMA 200</div><div class="text-xl">${fmt(d.sma200)}</div></div>`;
}
document.getElementById('refresh-btc')?.addEventListener('click', loadBTC); loadBTC();

async function loadFNG(){ const r=await jget('/api/fng'); if(!r.ok) return; const d=r.data;
  fngValueEl.textContent=d.value ?? '--'; fngClassEl.textContent=d.value_classification ?? '--'; fngTimeEl.textContent=`Sonraki güncelleme: ${d.time_readable || '--'}`;
}
loadFNG();

async function loadOI(){ oiCard.innerHTML=`<div class="text-neutral-400">Yükleniyor...</div>`; const r=await jget('/api/oi'); if(!r.ok){ oiCard.textContent='Hata'; return; }
  const d=r.data; function block(sym){ const v=d[sym]?.now; if(!v) return ''; const oi=parseFloat(v.openInterest); const t=new Date(v.time).toLocaleString();
    return `<div class="card"><div class="flex items-center justify-between"><div class="font-medium">${sym}</div><div class="text-xs text-neutral-500">${t}</div></div><div class="text-xl font-semibold">${fmt(oi,0)}</div></div>`;}
  oiCard.innerHTML = block('BTCUSDT') + block('ETHUSDT');
}
document.getElementById('refresh-oi')?.addEventListener('click', loadOI); loadOI();

async function loadStable(){ const r=await jget('/api/stablecoin_flow'); if(!r.ok){ stableCard.textContent='Hata'; return; }
  const d=r.data; const total=d.approx_netflow_24h_usd || 0;
  const rows=(d.top||[]).slice(0,6).map(x=>`<li class="flex justify-between"><span>${x.symbol}</span><span>${(x.change24_usd>=0?'+':'')}${fmt(x.change24_usd,0)} $</span></li>`).join('');
  stableCard.innerHTML = `<div class="text-sm">Toplam (proxy, 24s): <span class="${total>=0?'text-emerald-400':'text-red-400'} font-semibold">${(total>=0?'+':'')}${fmt(total,0)} $</span></div><ul class="mt-2 space-y-1">${rows || '<li class="text-neutral-400 text-sm">Veri yok / 0</li>'}</ul>`;
}
loadStable();

async function loadHash(){ hashCard.innerHTML=`<div class="text-neutral-400">Yükleniyor...</div>`; const r=await jget('/api/hashrate'); if(!r.ok){ hashCard.textContent='Hata'; return; }
  const d=r.data; const vals=d.values||[]; const last=vals.length? vals[vals.length-1].y : null; const prev=vals.length>7? vals[vals.length-8].y : null; const chg7=(last&&prev)?((last/prev)-1)*100:null;
  hashCard.innerHTML = `<div class="text-sm">Son (TH/s): <span class="font-semibold">${last? last.toFixed(0):'--'}</span></div><div class="text-sm">7g değişim: <span class="${(chg7||0)>=0?'text-emerald-400':'text-red-400'} font-semibold">${chg7? chg7.toFixed(1)+'%':'--'}</span></div>`;
}
document.getElementById('refresh-hash')?.addEventListener('click', loadHash); loadHash();

async function loadPremium(){ premiumCard.innerHTML=`<div class="text-neutral-400">Yükleniyor...</div>`; const r=await jget('/api/coinbase_premium');
  if(!r.ok){ premiumCard.innerHTML = `<div class="text-neutral-400 text-sm">Premium verisi pasif (API key yok).</div>`; return; }
  const data=r.data?.data || r.data || {}; const val=data?.value ?? data?.data?.[0]?.value ?? null; const ts=data?.time ?? data?.data?.[0]?.time ?? null;
  premiumCard.innerHTML = `<div class="text-sm">Premium: <span class="${(val||0)>=0?'text-emerald-400':'text-red-400'} font-semibold">${val!==null? Number(val).toFixed(4):'--'}</span></div><div class="text-xs text-neutral-500">${ts? new Date(ts).toLocaleString():''}</div>`;
}
document.getElementById('refresh-premium')?.addEventListener('click', loadPremium); loadPremium();

/* ---------------- 3) ETF: filtre + pagination ---------------- */
function ensureEtfControls() {
  let bar = $('#etf-controls');
  if (bar) return;
  const host = etfListEl?.parentElement;
  if (!host) return;
  bar = document.createElement('div');
  bar.id = 'etf-controls';
  bar.className = 'mb-3 flex flex-wrap items-center justify-between gap-2';
  bar.innerHTML = `
    <div class="flex flex-wrap gap-2" id="etf-filters"></div>
    <div class="flex items-center gap-2 text-xs">
      <button id="etf-prev" class="px-2 py-1 rounded-md border border-neutral-700 hover:bg-neutral-800">Önceki</button>
      <span id="etf-pageinfo" class="text-neutral-400"></span>
      <button id="etf-next" class="px-2 py-1 rounded-md border border-neutral-700 hover:bg-neutral-800">Sonraki</button>
    </div>
  `;
  host.insertBefore(bar, etfListEl);

  const filters = ['ALL','BTC','ETH','SOL','XRP'];
  const filtWrap = $('#etf-filters');
  filters.forEach(tag => {
    const b = document.createElement('button');
    b.className = 'text-xs px-3 py-1 rounded-lg border border-neutral-700 hover:bg-neutral-800';
    b.dataset.tag = tag;
    b.textContent = tag;
    b.addEventListener('click', () => {
      state.etf.filter = tag;
      state.etf.page = 1;
      renderETF();
    });
    filtWrap.appendChild(b);
  });

  $('#etf-prev').addEventListener('click', () => {
    state.etf.page = Math.max(1, state.etf.page - 1);
    renderETF();
  });
  $('#etf-next').addEventListener('click', () => {
    const total = filteredETF().length;
    const maxPage = Math.max(1, Math.ceil(total / state.etf.pageSize));
    state.etf.page = Math.min(maxPage, state.etf.page + 1);
    renderETF();
  });
}
function filteredETF() {
  const f = state.etf.filter;
  if (f === 'ALL') return state.etf.raw;
  return state.etf.raw.filter(e => (e.asset || '').toUpperCase() === f);
}
function pagedETF() {
  const arr = filteredETF();
  const { page, pageSize } = state.etf;
  const start = (page - 1) * pageSize;
  return { slice: arr.slice(start, start + pageSize), total: arr.length };
}
async function loadETF(){
  ensureEtfControls();
  const r=await jget('/api/etf_events');
  if(!r.ok){ etfListEl.innerHTML = `<div class="text-neutral-400 text-sm">Hata.</div>`; return; }
  state.etf.raw = r.data || [];
  renderETF();
}
function renderETF(){
  const { slice, total } = pagedETF();
  if(!total){
    etfListEl.innerHTML = `<div class="text-neutral-400 text-sm">Kayıt yok.</div>`;
    $('#etf-pageinfo').textContent = '';
    return;
  }
  $('#etf-pageinfo').textContent = `Sayfa ${state.etf.page} / ${Math.max(1, Math.ceil(total / state.etf.pageSize))}`;
  etfListEl.innerHTML = slice.map(e=>{
    const dt=e.next_deadline_est || e.date;
    let diffTxt=""; if(dt){ const d=new Date(dt); const now=new Date(); const days=Math.ceil((d-now)/(1000*60*60*24)); diffTxt = isFinite(days)? `${days>=0?days+'g kaldı':(-days)+'g geçti'}` : ""; }
    const soonCls=(diffTxt && diffTxt.includes('kaldı') && parseInt(diffTxt) <= 60)? 'badge-green':'';
    const title=e.title || (e.status==='none' ? `${e.asset}: resmi kayıt bulunamadı` : '');
    return `<div class="p-3 rounded-xl border border-neutral-800">
      <div class="flex items-center justify-between">
        <div class="font-medium">${e.asset||'—'}${e.manager? ' • '+e.manager:''}</div>
        <span class="badge ${soonCls}">${(e.status||'').toUpperCase()}</span>
      </div>
      <div class="text-sm text-neutral-300">${e.exchange || ''}</div>
      <div class="text-xs text-neutral-500">${title}</div>
      <div class="text-xs text-neutral-500">Tarih: ${dt? toLocalISO(dt):'--'} ${diffTxt? ' • '+diffTxt:''}</div>
      ${e.url? `<a class="text-xs text-blue-300 underline" href="${e.url}" target="_blank" rel="noreferrer">Belge</a>`:''}
    </div>`;
  }).join('');
}
document.getElementById('refresh-etf')?.addEventListener('click', loadETF); loadETF();

/* ---------------- Boğa Tahmini ---------------- */
async function scanCoins(){ checklistEl.innerHTML=`<li class="text-neutral-400">Taranıyor...</li>`;
  const r_btc=await jget('/api/btc_indicators'); const r_scan=await jget('/api/coins_sma_summary?limit=60'); const r_fng=await jget('/api/fng'); const r_etf=await jget('/api/etf_events');
  const btc=r_btc.ok ? r_btc.data : {}; const fng=r_fng.ok ? r_fng.data : {}; const scan=r_scan.ok ? r_scan.data : {scanned:0, above200:0, percent_above200:0}; const etf=r_etf.ok ? r_etf.data : [];
  const checks=[
    {label:'BTC 200D SMA üstünde', ok: btc.price > btc.sma200},
    {label:'50D > 200D', ok: (btc.sma50 ?? 0) > (btc.sma200 ?? 1e12)},
    {label:'20D > 50D', ok: (btc.sma20 ?? 0) > (btc.sma50 ?? 1e12)},
    {label:"Top 60 USDT'nin %≥50'si 200D üstünde", ok: (scan.percent_above200 ?? 0) >= 50},
    {label: `FNG ≥ 55 (şu an: ${fng.value ?? '--'})`, ok: (fng.value ?? 0) >= 55},
    {label:'60 gün içinde kritik ETF penceresi', ok: etf.some(e=>{ const dt=e.next_deadline_est || e.date; if(!dt) return false; const diff=(new Date(dt)-new Date())/(1000*60*60*24); return diff <= 60 && e.status!=='none'; })}
  ];
  checklistEl.innerHTML = checks.map(c=>`<li class="flex items-center gap-2"><span>${c.ok?'✅':'❌'}</span><span>${c.label}</span></li>`).join('');
  scanSummaryEl.innerHTML = `Taranan: ${scan.scanned} • 200D üstünde: ${scan.above200} (${scan.percent_above200?.toFixed(1)}%)`;
}
document.getElementById('scan-coins')?.addEventListener('click', scanCoins);

async function loadEstimate(){ estimateEl.innerHTML=`<div class="text-neutral-400">Hesaplanıyor...</div>`; const r=await jget('/api/bull_estimate'); if(!r.ok){ estimateEl.textContent='Hata'; return; }
  const d=r.data; const checks=(d.checks||[]).map(x=>`<li class="flex items-center gap-2"><span>${x[1]?'✅':'❌'}</span><span>${x[0]}</span></li>`).join('');
  estimateEl.innerHTML = `<div class="text-sm">Skor: <span class="font-semibold">${d.score}/6</span> • Faz: <span class="font-semibold">${d.phase_label}</span></div><div class="mt-2 text-sm">Tahmini Başlangıç: <span class="font-semibold">${toLocalISO(d.bull_start_estimate)}</span></div><div class="text-sm">Tahmini Bitiş: <span class="font-semibold">${toLocalISO(d.bull_end_estimate)}</span></div><ul class="mt-3 space-y-1">${checks}</ul>`;
}
document.getElementById('refresh-est')?.addEventListener('click', loadEstimate); loadEstimate(); scanCoins();

/* ---------------- 1 & 2 & 4) Pump kartları: fiyat + auto-refresh + projeksiyon ---------------- */
// eşik paneli
function ensureThresholdsButton() {
  const container = document.getElementById('refresh-pumps')?.parentElement;
  if (!container || $('#btn-thresholds')) return;
  const btn = document.createElement('button');
  btn.id = 'btn-thresholds';
  btn.className = 'text-xs px-3 py-1 rounded-lg border border-neutral-700 hover:bg-neutral-800';
  btn.textContent = 'Eşikler';
  container.prepend(btn);
  btn.addEventListener('click', toggleThresholdsPanel);
}
function renderThresholdsPanel() {
  let panel = $('#thresholds-panel');
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'thresholds-panel';
    panel.className = 'mt-3 hidden';
    const pumpsWrapper = $('#pumps')?.parentElement;
    pumpsWrapper?.insertBefore(panel, $('#pumps'));
  }
  const th = state.thresholds || {};
  panel.innerHTML = `
    <div class="rounded-xl border border-neutral-800 bg-neutral-950 p-4">
      <div class="flex items-center justify-between mb-3">
        <div class="text-sm font-medium">Eşik Parametreleri</div>
        <button id="btn-close-th" class="text-xs px-2 py-0.5 rounded-md border border-neutral-700 hover:bg-neutral-800">Kapat</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        ${renderNumberInput('overextended_change24_max', 'Aşırı Uzama Eşiği (24h %)', th.overextended_change24_max, 10, 200, 0.1)}
        ${renderNumberInput('max_change24_pct', 'İdeal Üst Sınır (24h %)', th.max_change24_pct, 5, 200, 0.1)}
        ${renderNumberInput('min_change24_pct', 'Günlük Min Momentum (24h %)', th.min_change24_pct, -50, 100, 0.1)}
        ${renderNumberInput('min_ret7_pct', 'Haftalık Min Momentum (7g %)', th.min_ret7_pct, -100, 200, 0.1)}
        ${renderNumberInput('heat_atr_max', 'Sıcaklık: EMA Mesafesi ≤ (ATR)', th.heat_atr_max, 0.2, 5, 0.1)}
        ${renderToggle('require_btc_regime', 'BTC Rejimi Zorunlu', !!th.require_btc_regime)}
        ${renderToggle('require_above200', 'Coin 1D SMA200 Üstü Zorunlu', !!th.require_above200)}
      </div>
      <p class="mt-3 text-xs text-neutral-400">Değerler değişince otomatik kaydedilir ve kartlar yenilenir.</p>
    </div>
  `;
  $('#btn-close-th')?.addEventListener('click', toggleThresholdsPanel);
  bindThresholdInputs();
}
function toggleThresholdsPanel() {
  const panel = $('#thresholds-panel');
  if (!panel) return;
  panel.classList.toggle('hidden');
}
function renderNumberInput(key, label, value, min, max, step) {
  return `
  <label class="block">
    <div class="text-xs text-neutral-300 mb-1">${label}</div>
    <input data-th-key="${key}" type="number" value="${value ?? ''}" min="${min}" max="${max}" step="${step}"
      class="w-full bg-neutral-900 border border-neutral-700 rounded-md px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-neutral-500">
  </label>`;
}
function renderToggle(key, label, checked) {
  return `
  <label class="flex items-center gap-2">
    <input data-th-key="${key}" type="checkbox" ${checked ? 'checked' : ''} class="h-4 w-4 rounded border-neutral-700">
    <span class="text-sm">${label}</span>
  </label>`;
}
const postThresholdsDebounced = debounce(async (payload) => {
  try {
    const res = await fetch('/api/thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('eşik kaydetme hatası');
    const js = await res.json();
    state.thresholds = js.data;
    await loadSignals(); // eşik değişince yenile
  } catch (e) {
    console.error(e);
    alert('Eşikleri kaydederken hata oluştu.');
  }
}, 500);
function bindThresholdInputs() {
  $$('#thresholds-panel [data-th-key]').forEach(el => {
    el.addEventListener('input', () => {
      const key = el.getAttribute('data-th-key');
      let val = el.type === 'checkbox' ? el.checked : (el.value === '' ? null : parseFloat(el.value));
      postThresholdsDebounced({ [key]: val });
    });
  });
}
async function loadThresholds() {
  const res = await jget('/api/thresholds');
  if (res.ok) {
    state.thresholds = res.data;
    ensureThresholdsButton();
    renderThresholdsPanel();
  }
}

/* ---- Projeksiyon hesapları (client-side) ---- */
async function computeProjections(symbol, lastPrice, atr15m) {
  const d1 = await fetch(API.binanceKlines(symbol, '1d', 120)).then(r=>r.json()).catch(()=>[]);
  const highs = d1.map(k=>+k[2]);
  const lows  = d1.map(k=>+k[3]);
  const lookback = Math.min(60, d1.length || 0);
  const h = lookback ? Math.max(...highs.slice(-lookback)) : null;
  const l = lookback ? Math.min(...lows.slice(-lookback)) : null;
  const athLookback = Math.min(365, d1.length || 0);
  const ath = athLookback ? Math.max(...highs.slice(-athLookback)) : null;

  let fibTargets = [];
  if (h && l && h > l) {
    const range = h - l;
    const base  = h;
    const levels = [1.272, 1.414, 1.618];
    fibTargets = levels.map(mult => ({
      label: `Fibo ${mult}×`,
      price: +(base + range*(mult-1)).toFixed(6)
    }));
  }
  let atrTargets = [];
  if (lastPrice && atr15m) {
    atrTargets = [
      { label: 'ATR +1.5R', price: +(lastPrice + 1.5*atr15m).toFixed(6) },
      { label: 'ATR +2.5R', price: +(lastPrice + 2.5*atr15m).toFixed(6) },
    ];
  }
  state.projections[symbol] = { fibTargets, atrTargets, ath: ath || null };
  return state.projections[symbol];
}
function renderProjection(p) {
  const fib = (p.fibTargets||[]).map(t=>`<div class="flex justify-between text-xs"><span class="text-neutral-400">${t.label}</span><span>${fmtNum(t.price)}</span></div>`).join('');
  const atr = (p.atrTargets||[]).map(t=>`<div class="flex justify-between text-xs"><span class="text-neutral-400">${t.label}</span><span>${fmtNum(t.price)}</span></div>`).join('');
  const ath = p.ath ? `<div class="flex justify-between text-xs"><span class="text-neutral-400">Son 365g ATH</span><span>${fmtNum(p.ath)}</span></div>` : '';
  return `
    <div class="text-xs font-medium mb-1">Projeksiyon (hedefler)</div>
    ${fib || atr || ath ? '' : '<div class="text-xs text-neutral-500">—</div>'}
    ${fib}
    ${atr}
    ${ath}
    <div class="mt-2 text-[11px] text-neutral-500">Not: Fibo 1D swing uzatmaları ve ATR tabanlı R hedefleri bilgilendirme amaçlıdır.</div>
  `;
}

/* ---- Signals (smooth update) ---- */
function decisionBadge(decision) {
  if (decision === 'AL') return badge('AL', 'green');
  if (decision === 'PULLBACK BEKLE') return badge('PULLBACK', 'yellow');
  return badge('ALMA', 'red');
}
function tickRow(t) {
  return `
    <div class="flex items-start gap-2">
      <div class="${t.ok ? 'text-emerald-400' : 'text-rose-400'}">${t.ok ? '✅' : '❌'}</div>
      <div class="text-xs text-neutral-200">${t.label}</div>
    </div>
  `;
}

function upsertPumpCard(row) {
  const { symbol, score, change24_pct, ret7_pct, volume_rank, decision, note, ticks, risk, pullback_targets, context } = row;
  const id = `card-${symbol}`;
  let card = document.getElementById(id);

  const priceNow = context?.last15 ?? null;
  const chg = change24_pct ?? null;
  const chgBadge = chg === null ? badge('--','gray') : badge(`${chg>=0?'+':''}${chg.toFixed(2)}%`, chg>=0?'green':'red');
  const priceLine = `
    <div class="flex items-center justify-between text-sm">
      <div class="text-neutral-400">Fiyat (yaklaşık)</div>
      <div class="flex items-center gap-2">
        <span class="font-semibold">${fmtNum(priceNow)}</span>
        ${chgBadge}
      </div>
    </div>`;

  const stats = `
    <div class="grid grid-cols-2 gap-2 text-xs">
      <div class="flex justify-between opacity-60"><span class="text-neutral-400">Skor</span><span>${score ?? '--'}</span></div>
      <div class="flex justify-between"><span class="text-neutral-400">Vol. Rank</span><span>#${volume_rank ?? '--'}</span></div>
      <div class="flex justify-between"><span class="text-neutral-400">24h</span><span>${fmtPct(change24_pct)}</span></div>
      <div class="flex justify-between"><span class="text-neutral-400">7g</span><span>${fmtPct(ret7_pct)}</span></div>
    </div>
  `;
  const riskBox = `
    <div class="grid grid-cols-3 gap-2 text-xs">
      <div class="flex flex-col rounded-md border border-neutral-800 p-2">
        <div class="text-neutral-400">SL</div><div>${fmtNum(risk?.suggested_sl)}</div>
      </div>
      <div class="flex flex-col rounded-md border border-neutral-800 p-2">
        <div class="text-neutral-400">TP1 (+1R)</div><div>${fmtNum(risk?.tp1)}</div>
      </div>
      <div class="flex flex-col rounded-md border border-neutral-800 p-2">
        <div class="text-neutral-400">TP2 (+2R)</div><div>${fmtNum(risk?.tp2)}</div>
      </div>
    </div>
  `;
  const pulls = (pullback_targets || []).slice(0, 4).map(p => `
    <div class="flex justify-between text-xs"><span class="text-neutral-400">${p.label}</span><span>${fmtNum(p.price)}</span></div>
  `).join('');
  const ticksHtml = (ticks || []).map(tickRow).join('');

  if (!card) {
    card = document.createElement('div');
    card.id = id;
    card.dataset.symbol = symbol;
    card.className = 'relative rounded-xl border border-neutral-800 bg-neutral-900 p-4 transition-colors';
    card.innerHTML = `
      ${scoreBadgeHTML(score)}
      <div class="flex items-center gap-x-3">
        <div class="font-semibold">${symbol}</div>
        <div class="flex items-center gap-2" data-slot="decision">${decisionBadge(decision)}</div>
      </div>
      <div class="mt-4 pt-3 border-t border-neutral-800" data-slot="price">${priceLine}</div>
      <div class="mt-2" data-slot="stats">${stats}</div>
      <div class="mt-3 text-xs ${decision === 'ALMA' ? 'text-rose-300' : 'text-neutral-300'}" data-slot="note">${note || ''}</div>
      <div class="mt-3 flex flex-col gap-2" data-slot="ticks">${ticksHtml}</div>
      <div class="mt-3" data-slot="risk">${riskBox}</div>
      <div class="mt-3 rounded-md border border-neutral-800 p-2" data-slot="pulls">
        <div class="text-xs font-medium mb-1">Potansiyel Gerileme Hedefleri</div>
        ${pulls || '<div class="text-xs text-neutral-500">--</div>'}
      </div>
      <div class="mt-3 rounded-md border border-neutral-800 p-2" data-slot="projection">
        <div class="text-xs font-medium mb-1">Projeksiyon (hedefler)</div>
        <div class="text-xs text-neutral-500">Hesaplanıyor...</div>
      </div>
      <div class="mt-3 text-[11px] text-neutral-500">
        <div>15m: EMA20/VWAP teyidi ve ATR tabanlı SL/TP kullanılır.</div>
      </div>
    `;
    pumpsEl.appendChild(card);
  } else {
    card.querySelector('[data-slot="decision"]').innerHTML = decisionBadge(decision);

    const priceSlot = card.querySelector('[data-slot="price"]');
    priceSlot.className = 'mt-4 pt-3 border-t border-neutral-800';
    priceSlot.innerHTML = priceLine;

    card.querySelector('[data-slot="stats"]').innerHTML = stats;

    const noteEl = card.querySelector('[data-slot="note"]');
    noteEl.textContent = note || '';
    noteEl.className = `mt-3 text-xs ${decision === 'ALMA' ? 'text-rose-300' : 'text-neutral-300'}`;

    card.querySelector('[data-slot="ticks"]').innerHTML = ticksHtml;
    card.querySelector('[data-slot="risk"]').innerHTML = riskBox;
    card.querySelector('[data-slot="pulls"]').innerHTML = `
      <div class="text-xs font-medium mb-1">Potansiyel Gerileme Hedefleri</div>
      ${pulls || '<div class="text-xs text-neutral-500">--</div>'}
    `;

    // skor rozeti
    let scoreSlot = card.querySelector('[data-slot="score"]');
    if (!scoreSlot) {
      card.insertAdjacentHTML('afterbegin', scoreBadgeHTML(score));
    } else {
      scoreSlot.outerHTML = scoreBadgeHTML(score);
    }
  }

  // Projeksiyon (cache + async compute)
  const projSlot = card.querySelector('[data-slot="projection"]');
  const cached = state.projections[symbol];
  if (cached) {
    projSlot.innerHTML = renderProjection(cached);
  } else {
    projSlot.innerHTML = `<div class="text-xs font-medium mb-1">Projeksiyon (hedefler)</div><div class="text-xs text-neutral-500">Hesaplanıyor...</div>`;
    computeProjections(symbol, priceNow, context?.atr14_15).then(p => {
      const liveCard = document.getElementById(id);
      if (liveCard) {
        liveCard.querySelector('[data-slot="projection"]').innerHTML = renderProjection(p);
      }
    }).catch(()=>{ projSlot.innerHTML = `<div class="text-xs font-medium mb-1">Projeksiyon (hedefler)</div><div class="text-xs text-neutral-500">—</div>`; });
  }
}

async function loadSignals() {
  if (!pumpsEl) return;
  const res = await jget(API.signals(state.limit));
  if (!res.ok) {
    console.error(res.error || 'signals error');
    return;
  }
  const data = res.data || {};
  state.thresholds = data.thresholds || state.thresholds;
  const rows = data.rows || [];

  const incomingSymbols = new Set(rows.map(r=>r.symbol));
  rows.forEach(upsertPumpCard);

  // listeden düşenleri nazikçe kaldır
  $$('#pumps [id^="card-"]').forEach(el => {
    const sym = el.dataset.symbol;
    if (!incomingSymbols.has(sym)) {
      el.classList.add('opacity-0');
      setTimeout(()=> el.remove(), 250);
    }
  });
}

document.getElementById('refresh-pumps')?.addEventListener('click', loadSignals);

function startAutoRefresh() {
  if (state.refreshTimer) clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(loadSignals, 15000); // 15 sn
}

/* ---------------- init ---------------- */
async function initPumps() {
  ensureThresholdsButton();
  await loadThresholds();
  await loadSignals();
  startAutoRefresh();
}

document.addEventListener('DOMContentLoaded', () => {
  initPumps().catch(console.error);
});

/* keep existing first-run wiring */
document.getElementById('refresh-est')?.addEventListener('click', loadEstimate);
document.getElementById('refresh-oi')?.addEventListener('click', loadOI);
document.getElementById('refresh-btc')?.addEventListener('click', loadBTC);
document.getElementById('refresh-hash')?.addEventListener('click', loadHash);
document.getElementById('refresh-premium')?.addEventListener('click', loadPremium);
