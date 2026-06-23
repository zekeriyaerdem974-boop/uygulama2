/* =====================================================================
   ZKR Analiz Screener JS — FAZ 56
   Multi-market screener with search, filters, sorting, fallback data.
   ===================================================================== */

(function () {
  'use strict';

  // ── State ─────────────────────────────────────────────────────────
  var activeMarket = 'crypto';
  var activeFilters = [];
  var sortCol = 'change_24h';
  var sortDir = 'desc';
  var rows = [];
  var filteredRows = [];
  var allFilters = [];
  var refreshTimer = null;
  var searchQuery = '';
  var REFRESH_INTERVAL = 60000;

  // ── Symbol display names ──────────────────────────────────────────
  var SYMBOL_NAMES = {
    // Crypto
    BTCUSDT:'Bitcoin', ETHUSDT:'Ethereum', BNBUSDT:'BNB', SOLUSDT:'Solana',
    XRPUSDT:'XRP', DOGEUSDT:'Dogecoin', ADAUSDT:'Cardano', AVAXUSDT:'Avalanche',
    DOTUSDT:'Polkadot', MATICUSDT:'Polygon', LINKUSDT:'Chainlink', UNIUSDT:'Uniswap',
    LTCUSDT:'Litecoin', ATOMUSDT:'Cosmos', NEARUSDT:'NEAR', FILUSDT:'Filecoin',
    APTUSDT:'Aptos', ARBUSDT:'Arbitrum', OPUSDT:'Optimism', SUIUSDT:'Sui',
    TONUSDT:'Toncoin', TRXUSDT:'TRON', SHIBUSDT:'Shiba Inu', PEPEUSDT:'Pepe',
    // US Stocks
    AAPL:'Apple', MSFT:'Microsoft', GOOGL:'Alphabet', AMZN:'Amazon', NVDA:'NVIDIA',
    META:'Meta', TSLA:'Tesla', JPM:'JPMorgan', V:'Visa', JNJ:'Johnson & Johnson',
    WMT:'Walmart', PG:'Procter & Gamble', MA:'Mastercard', HD:'Home Depot',
    DIS:'Disney', BAC:'Bank of America', CRM:'Salesforce', AMD:'AMD', INTC:'Intel',
    NFLX:'Netflix', PYPL:'PayPal', COST:'Costco', PEP:'PepsiCo', KO:'Coca-Cola',
    ABBV:'AbbVie', MRK:'Merck', PFE:'Pfizer', UNH:'UnitedHealth', XOM:'Exxon',
    CVX:'Chevron', LLY:'Eli Lilly', AVGO:'Broadcom', ORCL:'Oracle', CSCO:'Cisco',
    ACN:'Accenture', MCD:'McDonald\'s', NKE:'Nike', BA:'Boeing', CAT:'Caterpillar',
    GS:'Goldman Sachs', MS:'Morgan Stanley', COIN:'Coinbase', PLTR:'Palantir',
    HOOD:'Robinhood', MSTR:'MicroStrategy', SQ:'Block Inc',
    // BIST
    'THYAO.IS':'Türk Hava Yolları', 'GARAN.IS':'Garanti BBVA', 'AKBNK.IS':'Akbank',
    'YKBNK.IS':'Yapı Kredi', 'ISCTR.IS':'İş Bankası', 'KCHOL.IS':'Koç Holding',
    'SAHOL.IS':'Sabancı Holding', 'EREGL.IS':'Ereğli Demir Çelik', 'BIMAS.IS':'BİM',
    'ASELS.IS':'ASELSAN', 'SISE.IS':'Şişecam', 'TUPRS.IS':'Tüpraş',
    'TCELL.IS':'Turkcell', 'PGSUS.IS':'Pegasus', 'TAVHL.IS':'TAV Havalimanları',
    'ARCLK.IS':'Arçelik', 'TOASO.IS':'Tofaş Oto', 'FROTO.IS':'Ford Otosan',
    'KOZAL.IS':'Koza Altın', 'KOZAA.IS':'Koza Anadolu', 'SASA.IS':'SASA Polyester',
    'KRDMD.IS':'Kardemir', 'PETKM.IS':'Petkim', 'HALKB.IS':'Halkbank',
    'VAKBN.IS':'Vakıfbank', 'ENKAI.IS':'Enka İnşaat', 'MGROS.IS':'Migros',
    // Forex
    'EURUSD=X':'EUR/USD', 'GBPUSD=X':'GBP/USD', 'USDJPY=X':'USD/JPY',
    'USDCHF=X':'USD/CHF', 'AUDUSD=X':'AUD/USD', 'USDCAD=X':'USD/CAD',
    'NZDUSD=X':'NZD/USD', 'USDTRY=X':'USD/TRY', 'EURTRY=X':'EUR/TRY',
    'GBPTRY=X':'GBP/TRY', 'EURGBP=X':'EUR/GBP', 'EURJPY=X':'EUR/JPY',
    'GBPJPY=X':'GBP/JPY', 'AUDCAD=X':'AUD/CAD', 'AUDNZD=X':'AUD/NZD',
    // Commodities
    'GC=F':'Altın', 'SI=F':'Gümüş', 'PL=F':'Platin', 'PA=F':'Paladyum',
    'HG=F':'Bakır', 'CL=F':'Ham Petrol (WTI)', 'BZ=F':'Brent Petrol',
    'NG=F':'Doğal Gaz', 'RB=F':'Benzin', 'HO=F':'Isıtma Yağı',
    'ZW=F':'Buğday', 'ZC=F':'Mısır', 'ZS=F':'Soya', 'KC=F':'Kahve',
    'CC=F':'Kakao', 'CT=F':'Pamuk', 'SB=F':'Şeker'
  };

  // ── Fallback demo data (if API fails) ─────────────────────────────
  var FALLBACK_DATA = {
    crypto: [
      {symbol:'BTCUSDT',price:84250,change_24h:2.35,volume:28500000000,rsi14:58.2,trend:'up',market:'crypto'},
      {symbol:'ETHUSDT',price:1920,change_24h:1.85,volume:12400000000,rsi14:52.1,trend:'up',market:'crypto'},
      {symbol:'BNBUSDT',price:595,change_24h:-0.45,volume:1800000000,rsi14:48.5,trend:'sideways',market:'crypto'},
      {symbol:'SOLUSDT',price:132,change_24h:4.12,volume:3200000000,rsi14:62.8,trend:'up',market:'crypto'},
      {symbol:'XRPUSDT',price:2.38,change_24h:-1.22,volume:2100000000,rsi14:44.3,trend:'down',market:'crypto'},
      {symbol:'DOGEUSDT',price:0.168,change_24h:3.55,volume:1500000000,rsi14:55.0,trend:'up',market:'crypto'},
      {symbol:'ADAUSDT',price:0.72,change_24h:0.88,volume:680000000,rsi14:50.2,trend:'sideways',market:'crypto'},
      {symbol:'AVAXUSDT',price:22.5,change_24h:2.10,volume:520000000,rsi14:53.4,trend:'up',market:'crypto'}
    ],
    stocks: [
      {symbol:'AAPL',price:172.50,change_24h:1.25,volume:52000000,rsi14:55.8,trend:'up',market:'stocks'},
      {symbol:'MSFT',price:415.20,change_24h:0.85,volume:21000000,rsi14:58.2,trend:'up',market:'stocks'},
      {symbol:'NVDA',price:878.50,change_24h:3.45,volume:41000000,rsi14:65.1,trend:'up',market:'stocks'},
      {symbol:'GOOGL',price:153.80,change_24h:0.42,volume:18000000,rsi14:52.0,trend:'sideways',market:'stocks'},
      {symbol:'AMZN',price:178.90,change_24h:1.10,volume:34000000,rsi14:54.3,trend:'up',market:'stocks'},
      {symbol:'META',price:502.30,change_24h:-0.55,volume:15000000,rsi14:48.7,trend:'sideways',market:'stocks'},
      {symbol:'TSLA',price:175.40,change_24h:-2.10,volume:62000000,rsi14:38.5,trend:'down',market:'stocks'},
      {symbol:'AMD',price:162.80,change_24h:2.30,volume:48000000,rsi14:56.9,trend:'up',market:'stocks'}
    ],
    bist: [
      {symbol:'THYAO.IS',price:312.50,change_24h:1.85,volume:2800000000,rsi14:54.2,trend:'up',market:'bist'},
      {symbol:'GARAN.IS',price:134.10,change_24h:0.98,volume:1500000000,rsi14:48.5,trend:'sideways',market:'bist'},
      {symbol:'ASELS.IS',price:68.20,change_24h:2.45,volume:980000000,rsi14:58.8,trend:'up',market:'bist'},
      {symbol:'AKBNK.IS',price:62.50,change_24h:-0.32,volume:720000000,rsi14:45.2,trend:'sideways',market:'bist'},
      {symbol:'EREGL.IS',price:51.80,change_24h:1.22,volume:650000000,rsi14:52.1,trend:'up',market:'bist'},
      {symbol:'BIMAS.IS',price:448.00,change_24h:0.55,volume:320000000,rsi14:50.8,trend:'sideways',market:'bist'},
      {symbol:'SISE.IS',price:42.48,change_24h:2.16,volume:450000000,rsi14:46.1,trend:'sideways',market:'bist'},
      {symbol:'KCHOL.IS',price:195.20,change_24h:1.05,volume:280000000,rsi14:51.5,trend:'up',market:'bist'}
    ],
    forex: [
      {symbol:'EURUSD=X',price:1.0885,change_24h:0.12,volume:0,rsi14:52.3,trend:'sideways',market:'forex'},
      {symbol:'GBPUSD=X',price:1.2650,change_24h:-0.08,volume:0,rsi14:48.8,trend:'sideways',market:'forex'},
      {symbol:'USDJPY=X',price:148.52,change_24h:0.35,volume:0,rsi14:58.1,trend:'up',market:'forex'},
      {symbol:'USDTRY=X',price:38.42,change_24h:0.05,volume:0,rsi14:62.5,trend:'up',market:'forex'},
      {symbol:'USDCHF=X',price:0.8780,change_24h:-0.18,volume:0,rsi14:44.2,trend:'down',market:'forex'},
      {symbol:'AUDUSD=X',price:0.6520,change_24h:0.22,volume:0,rsi14:50.5,trend:'sideways',market:'forex'}
    ],
    commodities: [
      {symbol:'GC=F',price:2985.50,change_24h:0.85,volume:185000,rsi14:62.1,trend:'up',market:'commodities'},
      {symbol:'SI=F',price:33.42,change_24h:1.55,volume:72000,rsi14:55.8,trend:'up',market:'commodities'},
      {symbol:'CL=F',price:68.20,change_24h:-1.22,volume:320000,rsi14:42.5,trend:'down',market:'commodities'},
      {symbol:'NG=F',price:4.15,change_24h:2.80,volume:145000,rsi14:58.3,trend:'up',market:'commodities'},
      {symbol:'BZ=F',price:72.10,change_24h:-0.95,volume:110000,rsi14:44.8,trend:'sideways',market:'commodities'},
      {symbol:'ZW=F',price:548.25,change_24h:0.35,volume:52000,rsi14:49.2,trend:'sideways',market:'commodities'}
    ]
  };

  // ── DOM helpers ───────────────────────────────────────────────────
  var $ = function(id) { return document.getElementById(id); };
  var $$ = function(sel) { return document.querySelectorAll(sel); };

  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function fmt(n, decimals) {
    if (n == null || n === '' || n === 0) return '—';
    var v = Number(n);
    if (!Number.isFinite(v)) return '—';
    if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + 'B';
    if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
    if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'K';
    return v.toFixed(decimals || 2);
  }

  function fmtPrice(n) {
    if (n == null || n === '' || n === 0) return '—';
    var v = Number(n);
    if (!Number.isFinite(v)) return '—';
    if (v >= 10000) return v.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    if (v >= 1) return v.toFixed(2);
    if (v >= 0.01) return v.toFixed(4);
    return v.toFixed(6);
  }

  function pct(n) {
    if (n == null || n === '') return '—';
    var v = Number(n);
    if (!Number.isFinite(v)) return '—';
    return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
  }

  function cleanSymbol(sym) {
    if (!sym) return '';
    return sym.replace(/\.IS$/, '').replace(/=X$/, '').replace(/=F$/, '').replace(/USDT$/, '');
  }

  function getDisplayName(sym) {
    return SYMBOL_NAMES[sym] || '';
  }

  function safeVal(v) {
    if (v === null || v === undefined || v === '' || v === 'null' || v === 'undefined' || v === 'NaN') return null;
    var n = Number(v);
    return Number.isFinite(n) ? n : null;
  }

  async function fetchJson(url) {
    var r = await fetch(url);
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }

  // ── Status ────────────────────────────────────────────────────────
  function setStatus(msg, cls) {
    var el = $('scrStatus');
    if (!el) return;
    el.className = 'scr-status ' + (cls || '');
    el.innerHTML = (cls === 'loading' ? '<span class="scr-spinner"></span>' : '') + esc(msg);
  }

  function showEmpty(show) {
    var el = $('scrEmpty');
    if (el) el.style.display = show ? 'flex' : 'none';
  }

  // ── Load filters ──────────────────────────────────────────────────
  async function loadFilters() {
    try {
      var js = await fetchJson('/api/screener/filters');
      allFilters = js.filters || [];
      renderFilters();
    } catch (e) {
      console.warn('Failed to load filters:', e);
    }
  }

  function renderFilters() {
    var groups = {};
    for (var i = 0; i < allFilters.length; i++) {
      var f = allFilters[i];
      var cat = f.category || 'other';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(f);
    }

    var cats = Object.keys(groups);
    for (var c = 0; c < cats.length; c++) {
      var cat = cats[c];
      var container = $('fg-' + cat);
      if (!container) continue;
      container.innerHTML = '';
      var items = groups[cat];
      for (var j = 0; j < items.length; j++) {
        var f = items[j];
        var label = document.createElement('label');
        label.className = 'scr-fcheck';
        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = f.name;
        cb.checked = activeFilters.indexOf(f.name) !== -1;
        cb.addEventListener('change', (function(fname) {
          return function(e) {
            if (e.target.checked) {
              if (activeFilters.indexOf(fname) === -1) activeFilters.push(fname);
            } else {
              activeFilters = activeFilters.filter(function(x){ return x !== fname; });
            }
          };
        })(f.name));
        label.appendChild(cb);
        label.appendChild(document.createTextNode(f.desc));
        container.appendChild(label);
      }
    }
  }

  // ── Filter group toggle ───────────────────────────────────────────
  function initFilterToggles() {
    $$('.scr-fgroup-title').forEach(function(el) {
      el.addEventListener('click', function() {
        var cat = el.dataset.toggle;
        var body = $('fg-' + cat);
        if (!body) return;
        var open = body.classList.toggle('open');
        el.classList.toggle('open', open);
        el.textContent = (open ? '▾ ' : '▸ ') + el.textContent.replace(/^[▸▾]\s*/, '');
      });
    });
  }

  // ── Load screener data ────────────────────────────────────────────
  async function loadScreener() {
    setStatus('Taranıyor…', 'loading');
    showEmpty(false);

    var params = new URLSearchParams({ market: activeMarket });
    if (activeFilters.length) {
      params.set('filters', activeFilters.join(','));
    }
    params.set('sort', sortCol);
    params.set('dir', sortDir);

    try {
      var js = await fetchJson('/api/screener?' + params.toString());
      if (!js.ok) {
        setStatus('Hata: ' + (js.error || 'Bilinmeyen'), 'err');
        useFallback();
        return;
      }
      rows = (js.data || []).filter(function(r) {
        return r && r.symbol;
      });
      $('scrCount').textContent = js.count || 0;
      $('scrTotal').textContent = js.total_scanned || 0;

      if (rows.length === 0) {
        useFallback();
        return;
      }

      applySearch();
      setStatus('✓ ' + rows.length + ' sonuç bulundu (' + (js.total_scanned || 0) + ' taranan)', 'ok');
    } catch (e) {
      setStatus('Veri yüklenemedi — örnek veriler gösteriliyor', 'err');
      useFallback();
    }
  }

  function useFallback() {
    rows = FALLBACK_DATA[activeMarket] || [];
    if (rows.length > 0) {
      setStatus('Canlı veri yok — örnek sonuçlar gösteriliyor', 'err');
    }
    applySearch();
  }

  // ── Search ────────────────────────────────────────────────────────
  function applySearch() {
    if (!searchQuery) {
      filteredRows = rows.slice();
    } else {
      var q = searchQuery.toLowerCase();
      filteredRows = rows.filter(function(r) {
        var sym = (r.symbol || '').toLowerCase();
        var clean = cleanSymbol(r.symbol).toLowerCase();
        var name = (getDisplayName(r.symbol) || r.name || '').toLowerCase();
        return sym.indexOf(q) !== -1 || clean.indexOf(q) !== -1 || name.indexOf(q) !== -1;
      });
    }
    sortRows();
    renderList();
    showEmpty(filteredRows.length === 0);
  }

  function sortRows() {
    var rev = sortDir === 'desc';
    filteredRows.sort(function(a, b) {
      var va = a[sortCol], vb = b[sortCol];
      if (va == null) va = rev ? -Infinity : Infinity;
      if (vb == null) vb = rev ? -Infinity : Infinity;
      if (typeof va === 'string') return rev ? vb.localeCompare(va) : va.localeCompare(vb);
      return rev ? vb - va : va - vb;
    });
  }

  // ── Render list-style results ─────────────────────────────────────
  function renderList() {
    var list = $('scrList');
    if (!list) return;
    list.innerHTML = '';

    // Column header
    var header = document.createElement('div');
    header.className = 'scr-row scr-row-header';
    header.innerHTML =
      '<div class="scr-col-sym scr-sortable" data-col="symbol">Sembol</div>' +
      '<div class="scr-col-price scr-sortable" data-col="price">Fiyat</div>' +
      '<div class="scr-col-chg scr-sortable" data-col="change_24h">Değişim</div>' +
      '<div class="scr-col-vol scr-sortable" data-col="volume">Hacim</div>' +
      '<div class="scr-col-rsi scr-sortable" data-col="rsi14">RSI</div>' +
      '<div class="scr-col-trend scr-sortable" data-col="trend">Trend</div>';
    list.appendChild(header);

    // Update sort indicators on header
    header.querySelectorAll('.scr-sortable').forEach(function(el) {
      if (el.dataset.col === sortCol) {
        el.classList.add(sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
      }
      el.addEventListener('click', function() {
        var col = el.dataset.col;
        if (sortCol === col) {
          sortDir = sortDir === 'desc' ? 'asc' : 'desc';
        } else {
          sortCol = col;
          sortDir = col === 'symbol' ? 'asc' : 'desc';
        }
        sortRows();
        renderList();
      });
    });

    for (var i = 0; i < filteredRows.length; i++) {
      var r = filteredRows[i];
      var row = document.createElement('div');
      row.className = 'scr-row';

      var sym = r.symbol || '';
      var displaySym = cleanSymbol(sym);
      var name = getDisplayName(sym) || r.name || '';
      var price = safeVal(r.price);
      var chg = safeVal(r.change_24h);
      var vol = safeVal(r.volume);
      var rsi = safeVal(r.rsi14);
      var trend = r.trend || 'sideways';

      var chgCls = chg !== null && chg >= 0 ? 'scr-up' : 'scr-down';
      var trendCls = trend === 'up' ? 'scr-trend-up' : trend === 'down' ? 'scr-trend-down' : 'scr-trend-side';
      var trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '—';

      var rsiHtml = '—';
      if (rsi !== null) {
        var rsiFill = rsi > 70 ? '#16C784' : rsi < 30 ? '#FF4D6D' : '#3B82F6';
        rsiHtml = '<span class="scr-rsi">' + rsi.toFixed(1) +
          '<span class="scr-rsi-bar"><span class="scr-rsi-fill" style="width:' +
          Math.min(rsi, 100) + '%;background:' + rsiFill + '"></span></span></span>';
      }

      var volHtml = vol !== null && vol > 0 ? fmt(vol, 0) : '—';

      row.innerHTML =
        '<div class="scr-col-sym">' +
          '<div class="scr-sym-main">' + esc(displaySym) + '</div>' +
          (name ? '<div class="scr-sym-name">' + esc(name) + '</div>' : '') +
        '</div>' +
        '<div class="scr-col-price">' + (price !== null ? fmtPrice(price) : '—') + '</div>' +
        '<div class="scr-col-chg ' + chgCls + '">' + (chg !== null ? pct(chg) : '—') + '</div>' +
        '<div class="scr-col-vol">' + volHtml + '</div>' +
        '<div class="scr-col-rsi">' + rsiHtml + '</div>' +
        '<div class="scr-col-trend"><span class="scr-trend-badge ' + trendCls + '">' + trendIcon + '</span></div>';

      // Click → navigate to trade terminal
      (function(symbol, market) {
        row.addEventListener('click', function() {
          var tradeSym = symbol;
          localStorage.setItem('bw_active_market', market || 'crypto');
          localStorage.setItem('bw_current_symbol', tradeSym);
          window.location.href = '/tv';
        });
      })(sym, r.market);

      list.appendChild(row);
    }
  }

  // ── Market tabs ───────────────────────────────────────────────────
  function initMarketTabs() {
    $$('.scr-mtab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        $$('.scr-mtab').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeMarket = btn.dataset.market;
        rows = [];
        filteredRows = [];
        $('scrList').innerHTML = '';
        showEmpty(false);
        loadScreener();
      });
    });
  }

  // ── Search input ──────────────────────────────────────────────────
  function initSearch() {
    var input = $('scrSearch');
    if (!input) return;
    var debounce = null;
    input.addEventListener('input', function() {
      clearTimeout(debounce);
      debounce = setTimeout(function() {
        searchQuery = input.value.trim();
        applySearch();
      }, 200);
    });
  }

  // ── Buttons ───────────────────────────────────────────────────────
  function initButtons() {
    var applyBtn = $('btnApply');
    var clearBtn = $('btnClear');

    if (applyBtn) {
      applyBtn.addEventListener('click', function() { loadScreener(); });
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', function() {
        activeFilters = [];
        $$('.scr-fcheck input').forEach(function(cb) { cb.checked = false; });
        loadScreener();
      });
    }
  }

  // ── Auto-refresh ──────────────────────────────────────────────────
  function startRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(function() { loadScreener(); }, REFRESH_INTERVAL);
  }

  // ── Init ──────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', async function() {
    initMarketTabs();
    initFilterToggles();
    initSearch();
    initButtons();
    await loadFilters();
    await loadScreener();
    startRefresh();
  });
})();
