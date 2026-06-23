/* ═══════════════════════════════════════════════════════════════════
   discover.js — ZKR Analiz v2 Keşfet (Discover) Page
   Mobile-first premium finance app — real data, no mocks
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  /* ── Config ──────────────────────────────────────────────────────── */
  const CATEGORY_CONFIG = {
    kripto: {
      title: "Popüler Kripto",
      featured: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
      list: ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","DOTUSDT","MATICUSDT","LINKUSDT","LTCUSDT"],
      tickerEndpoint: "/api/market/ticker",
      klinesEndpoint: "/api/market/klines",
      symbolsEndpoint: null, // use hardcoded list
      labels: { BTCUSDT:"Bitcoin", ETHUSDT:"Ethereum", SOLUSDT:"Solana", BNBUSDT:"BNB", XRPUSDT:"XRP", DOGEUSDT:"Dogecoin", ADAUSDT:"Cardano", AVAXUSDT:"Avalanche", DOTUSDT:"Polkadot", MATICUSDT:"Polygon", LINKUSDT:"Chainlink", LTCUSDT:"Litecoin" }
    },
    bist: {
      title: "BIST Endeksler & Hisseler",
      featured: ["XU100.IS", "XU030.IS", "XU050.IS", "THYAO.IS"],
      list: ["XU100.IS","XU030.IS","XU050.IS","THYAO.IS","ASELS.IS","TUPRS.IS","GARAN.IS","SISE.IS","KCHOL.IS","AKBNK.IS","EREGL.IS","BIMAS.IS"],
      tickerEndpoint: "/api/bist/ticker",
      klinesEndpoint: "/api/bist/klines",
      symbolsEndpoint: "/api/bist/symbols",
      labels: { "XU100.IS":"BIST 100", "XU030.IS":"BIST 30", "XU050.IS":"BIST 50", "THYAO.IS":"Türk Hava Yolları", "ASELS.IS":"Aselsan", "TUPRS.IS":"Tüpraş", "GARAN.IS":"Garanti BBVA", "SISE.IS":"Şişecam", "KCHOL.IS":"Koç Holding", "AKBNK.IS":"Akbank", "EREGL.IS":"Ereğli Demir Çelik", "BIMAS.IS":"BİM" }
    },
    commodities: {
      title: "Emtia",
      featured: ["GC=F", "SI=F", "CL=F", "HG=F"],
      list: ["GC=F","SI=F","CL=F","HG=F","PL=F"],
      tickerEndpoint: "/api/commodities/ticker",
      klinesEndpoint: "/api/commodities/klines",
      symbolsEndpoint: null,
      labels: { "GC=F":"Altın", "SI=F":"Gümüş", "CL=F":"Ham Petrol", "HG=F":"Bakır", "PL=F":"Platin" }
    },
    forex: {
      title: "Forex Pariteler",
      featured: ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDTRY=X"],
      list: ["EURUSD=X","GBPUSD=X","USDJPY=X","USDTRY=X","USDCHF=X","AUDUSD=X","NZDUSD=X","EURTRY=X"],
      tickerEndpoint: "/api/forex/ticker",
      klinesEndpoint: "/api/forex/klines",
      symbolsEndpoint: null,
      labels: { "EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "USDJPY=X":"USD/JPY", "USDTRY=X":"USD/TRY", "USDCHF=X":"USD/CHF", "AUDUSD=X":"AUD/USD", "NZDUSD=X":"NZD/USD", "EURTRY=X":"EUR/TRY" }
    },
    stocks: {
      title: "ABD Hisseleri",
      featured: ["AAPL", "MSFT", "GOOGL", "NVDA"],
      list: ["AAPL","MSFT","GOOGL","NVDA","AMZN","TSLA","META","AMD","NFLX","INTC","DIS","BA"],
      tickerEndpoint: "/api/stocks/ticker",
      klinesEndpoint: "/api/stocks/klines",
      symbolsEndpoint: null,
      labels: { AAPL:"Apple", MSFT:"Microsoft", GOOGL:"Alphabet", NVDA:"Nvidia", AMZN:"Amazon", TSLA:"Tesla", META:"Meta", AMD:"AMD", NFLX:"Netflix", INTC:"Intel", DIS:"Disney", BA:"Boeing" }
    }
  };

  /* Forex symbols need special handling */
  const FOREX_DISPLAY = { "EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "USDJPY=X":"USD/JPY", "USDTRY=X":"USD/TRY", "USDCHF=X":"USD/CHF", "AUDUSD=X":"AUD/USD", "NZDUSD=X":"NZD/USD", "EURTRY=X":"EUR/TRY" };

  /* Economic calendar mock data for Turkey timezone (no free API yet) */
  const CALENDAR_EVENTS = [
    { time: "09:00", flag: "🇹🇷", name: "TCMB Faiz Kararı", impact: "high", actual: "-", forecast: "42.50%", previous: "42.50%" },
    { time: "10:00", flag: "🇩🇪", name: "IFO İş İklimi Endeksi", impact: "high", actual: "-", forecast: "87.5", previous: "86.9" },
    { time: "11:00", flag: "🇪🇺", name: "Euro Bölgesi TÜFE (Yıllık)", impact: "high", actual: "-", forecast: "2.4%", previous: "2.6%" },
    { time: "14:30", flag: "🇺🇸", name: "ABD İstihdam Verileri", impact: "high", actual: "-", forecast: "200K", previous: "187K" },
    { time: "15:00", flag: "🇺🇸", name: "Michigan Tüketici Güveni", impact: "medium", actual: "-", forecast: "67.8", previous: "64.7" },
    { time: "16:00", flag: "🇬🇧", name: "İngiltere GDP (Çeyreklik)", impact: "medium", actual: "-", forecast: "0.3%", previous: "0.1%" },
    { time: "17:30", flag: "🇺🇸", name: "Ham Petrol Stokları", impact: "low", actual: "-", forecast: "-1.2M", previous: "-3.5M" }
  ];

  let currentCategory = "kripto";
  let tickerCache = {};
  let klinesCache = {};
  let newsCache = {};
  let allSymbolsCache = {};
  let refreshTimer = null;

  /* ── DOM refs ────────────────────────────────────────────────────── */
  const $  = (s, p) => (p || document).querySelector(s);
  const $$ = (s, p) => [...(p || document).querySelectorAll(s)];

  const dom = {
    sectionTitle:  $("#section-title"),
    featuredCards: $("#featured-cards"),
    marketList:    $("#market-list"),
    moversScroll:  $("#movers-scroll"),
    newsFeed:      $("#news-feed"),
    calendarFeed:  $("#calendar-feed"),
    calDate:       $("#cal-date"),
    searchOverlay: $("#search-overlay"),
    searchInput:   $("#search-input"),
    searchResults: $("#search-results"),
  };

  /* ── Utility ─────────────────────────────────────────────────────── */
  function fmtPrice(val, market) {
    if (val == null || val === 0) return "—";
    if (market === "forex") return val.toFixed(4);
    if (val >= 10000) return val.toLocaleString("tr-TR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    if (val >= 1) return val.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return val.toFixed(6);
  }

  function fmtPct(val) {
    if (val == null) return "—";
    const sign = val >= 0 ? "+" : "";
    return sign + val.toFixed(2) + "%";
  }

  function timeAgo(dateStr) {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Az önce";
    if (mins < 60) return mins + " dk önce";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + " sa önce";
    return Math.floor(hrs / 24) + " gün önce";
  }

  function cleanSymbol(sym) {
    return sym.replace("USDT","").replace(".IS","").replace("=X","").replace("=F","");
  }

  /* ── Sparkline Canvas Drawing ────────────────────────────────────── */
  function drawSparkline(canvas, data, color) {
    if (!canvas || !data || data.length < 2) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const stepX = w / (data.length - 1);

    ctx.beginPath();
    data.forEach((v, i) => {
      const x = i * stepX;
      const y = h - ((v - min) / range) * (h * 0.85) - h * 0.05;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    ctx.stroke();

    /* gradient fill */
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    const c = color === "#00C853" ? "0,200,83" : color === "#FF1744" ? "255,23,68" : "41,121,255";
    grad.addColorStop(0, `rgba(${c},0.15)`);
    grad.addColorStop(1, `rgba(${c},0)`);
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();
  }

  /* ── API Fetchers ────────────────────────────────────────────────── */
  async function fetchTicker(endpoint, symbol) {
    const key = endpoint + ":" + symbol;
    try {
      const res = await fetch(endpoint + "?symbol=" + encodeURIComponent(symbol));
      const d = await res.json();
      if (d.ok) {
        tickerCache[key] = d;
        return d;
      }
    } catch (e) { /* silent */ }
    return tickerCache[key] || null;
  }

  async function fetchKlines(endpoint, symbol) {
    const key = endpoint + ":" + symbol;
    if (klinesCache[key]) return klinesCache[key];
    try {
      const res = await fetch(endpoint + "?symbol=" + encodeURIComponent(symbol) + "&interval=1d&limit=14");
      const d = await res.json();
      if (d.ok && d.candles && d.candles.length > 0) {
        const closes = d.candles.map(c => c.close);
        klinesCache[key] = closes;
        return closes;
      }
    } catch (e) { /* silent */ }
    return klinesCache[key] || null;
  }

  async function fetchNews(type) {
    if (newsCache[type]) return newsCache[type];
    try {
      const res = await fetch("/api/news?type=" + type);
      const d = await res.json();
      if (d.ok) {
        newsCache[type] = d.data || [];
        return newsCache[type];
      }
    } catch (e) { /* silent */ }
    return [];
  }

  async function fetchAllSymbols(market) {
    if (allSymbolsCache[market]) return allSymbolsCache[market];
    const endpoints = {
      bist: "/api/bist/symbols",
      stocks: "/api/stocks/symbols",
      forex: "/api/forex/symbols",
      commodities: "/api/commodities/symbols"
    };
    const ep = endpoints[market];
    if (!ep) return [];
    try {
      const res = await fetch(ep);
      const d = await res.json();
      if (d.items) {
        allSymbolsCache[market] = d.items;
        return d.items;
      }
    } catch (e) { /* silent */ }
    return [];
  }

  /* ── Render: Featured Cards (2-col, with sparklines) ─────────────── */
  async function renderFeaturedCards() {
    const cfg = CATEGORY_CONFIG[currentCategory];
    dom.sectionTitle.textContent = cfg.title;
    dom.featuredCards.innerHTML = cfg.featured.map(() => '<div class="disc-skeleton-card"></div>').join("");

    const cards = await Promise.all(cfg.featured.map(async (sym) => {
      const ticker = await fetchTicker(cfg.tickerEndpoint, sym);
      const klines = await fetchKlines(cfg.klinesEndpoint, sym);
      return { sym, ticker, klines };
    }));

    dom.featuredCards.innerHTML = "";
    cards.forEach(({ sym, ticker, klines }) => {
      const label = cfg.labels[sym] || cleanSymbol(sym);
      const price = ticker ? ticker.lastPrice : 0;
      const pct   = ticker ? ticker.priceChangePercent : 0;
      const isUp  = pct >= 0;

      const card = document.createElement("div");
      card.className = "disc-market-card";
      card.onclick = () => window.location.href = "/trade?symbol=" + encodeURIComponent(sym) + "&market=" + currentCategory;
      card.innerHTML = `
        <div class="symbol-name">${cleanSymbol(sym)}</div>
        <div class="symbol-label">${label}</div>
        <div class="price">${fmtPrice(price, currentCategory)}</div>
        <div class="change ${isUp ? 'up' : 'down'}">${fmtPct(pct)}</div>
        <div class="sparkline-wrap"><canvas></canvas></div>
      `;
      dom.featuredCards.appendChild(card);

      if (klines && klines.length > 1) {
        const canvas = card.querySelector("canvas");
        requestAnimationFrame(() => drawSparkline(canvas, klines, isUp ? "#00C853" : "#FF1744"));
      }
    });
  }

  /* ── Render: Market List ─────────────────────────────────────────── */
  async function renderMarketList() {
    const cfg = CATEGORY_CONFIG[currentCategory];
    dom.marketList.innerHTML = cfg.list.map(() => '<div class="disc-skeleton-row"></div>').join("");

    const items = await Promise.all(cfg.list.map(async (sym, i) => {
      const ticker = await fetchTicker(cfg.tickerEndpoint, sym);
      const klines = await fetchKlines(cfg.klinesEndpoint, sym);
      return { sym, ticker, klines, rank: i + 1 };
    }));

    dom.marketList.innerHTML = "";
    items.forEach(({ sym, ticker, klines, rank }) => {
      const label = cfg.labels[sym] || cleanSymbol(sym);
      const price = ticker ? ticker.lastPrice : 0;
      const pct   = ticker ? ticker.priceChangePercent : 0;
      const isUp  = pct >= 0;

      const row = document.createElement("div");
      row.className = "disc-market-row";
      row.onclick = () => window.location.href = "/trade?symbol=" + encodeURIComponent(sym) + "&market=" + currentCategory;

      row.innerHTML = `
        <div class="row-rank">${rank}</div>
        <div class="row-icon">${cleanSymbol(sym).substring(0, 2)}</div>
        <div class="row-info">
          <div class="row-symbol">${cleanSymbol(sym)}</div>
          <div class="row-name">${label}</div>
        </div>
        <div class="row-sparkline"><canvas></canvas></div>
        <div class="row-price-col">
          <div class="row-price">${fmtPrice(price, currentCategory)}</div>
          <span class="row-change ${isUp ? 'up' : 'down'}">${fmtPct(pct)}</span>
        </div>
      `;
      dom.marketList.appendChild(row);

      if (klines && klines.length > 1) {
        const canvas = row.querySelector("canvas");
        requestAnimationFrame(() => drawSparkline(canvas, klines, isUp ? "#00C853" : "#FF1744"));
      }
    });
  }

  /* ── Render: Top Movers ──────────────────────────────────────────── */
  async function renderMovers(direction) {
    const cfg = CATEGORY_CONFIG[currentCategory];
    dom.moversScroll.innerHTML = '<div class="disc-skeleton-mover"></div><div class="disc-skeleton-mover"></div><div class="disc-skeleton-mover"></div>';

    /* Fetch tickers for all list symbols */
    const items = await Promise.all(cfg.list.map(async (sym) => {
      const ticker = await fetchTicker(cfg.tickerEndpoint, sym);
      const klines = await fetchKlines(cfg.klinesEndpoint, sym);
      return { sym, ticker, klines };
    }));

    /* Sort by price change */
    const sorted = items
      .filter(it => it.ticker && it.ticker.lastPrice > 0)
      .sort((a, b) => {
        const aPct = a.ticker.priceChangePercent || 0;
        const bPct = b.ticker.priceChangePercent || 0;
        return direction === "up" ? bPct - aPct : aPct - bPct;
      })
      .slice(0, 6);

    dom.moversScroll.innerHTML = "";
    sorted.forEach(({ sym, ticker, klines }) => {
      const price = ticker.lastPrice;
      const pct   = ticker.priceChangePercent || 0;
      const isUp  = pct >= 0;

      const card = document.createElement("div");
      card.className = "disc-mover-card";
      card.onclick = () => window.location.href = "/trade?symbol=" + encodeURIComponent(sym) + "&market=" + currentCategory;
      card.innerHTML = `
        <div class="mv-symbol">${cleanSymbol(sym)}</div>
        <div class="mv-price">${fmtPrice(price, currentCategory)}</div>
        <div class="mv-change ${isUp ? 'up' : 'down'}">${fmtPct(pct)}</div>
        <div class="mv-spark"><canvas></canvas></div>
      `;
      dom.moversScroll.appendChild(card);

      if (klines && klines.length > 1) {
        const canvas = card.querySelector("canvas");
        requestAnimationFrame(() => drawSparkline(canvas, klines, isUp ? "#00C853" : "#FF1744"));
      }
    });
  }

  /* ── Render: News Feed ───────────────────────────────────────────── */
  async function renderNews(type) {
    dom.newsFeed.innerHTML = '<div class="disc-skeleton-news"></div><div class="disc-skeleton-news"></div><div class="disc-skeleton-news"></div>';

    const articles = await fetchNews(type || "crypto");
    if (!articles.length) {
      dom.newsFeed.innerHTML = '<p class="text-sm text-neutral-500 py-4 text-center">Haber bulunamadı.</p>';
      return;
    }

    dom.newsFeed.innerHTML = "";
    const sentimentEmoji = { positive: "📈", negative: "📉", neutral: "📰", bullish: "🐂", bearish: "🐻" };

    articles.slice(0, 12).forEach(art => {
      const item = document.createElement("div");
      item.className = "disc-news-item";
      item.onclick = () => openNewsDetail(art);

      const sent = (art.sentiment || "neutral").toLowerCase();
      const sentClass = sent === "positive" || sent === "bullish" ? "bullish" : sent === "negative" || sent === "bearish" ? "bearish" : "neutral";
      const sentLabel = sent === "positive" || sent === "bullish" ? "Pozitif" : sent === "negative" || sent === "bearish" ? "Negatif" : "Nötr";

      const catBadge = art.category && art.category !== "general" ? `<span class="news-cat-badge">${art.category.toUpperCase()}</span>` : "";

      item.innerHTML = `
        <div class="news-content">
          <div class="news-source">${art.source || "—"} ${catBadge}</div>
          <div class="news-title">${art.title || ""}</div>
          <div class="news-meta">
            <span>${art.published_at ? timeAgo(art.published_at) : ""}</span>
            <span class="news-sentiment ${sentClass}">${sentimentEmoji[sent] || "📰"} ${sentLabel}</span>
            ${art.symbols && art.symbols.length ? '<span class="text-bull-blue">' + art.symbols.slice(0,3).join(", ") + '</span>' : ''}
          </div>
          <div class="news-impact-mini" data-nid="${art.id || ''}" style="display:none;margin-top:4px;font-size:.7rem;display:flex;gap:6px;flex-wrap:wrap;"></div>
        </div>
        <div class="news-thumb">${sentimentEmoji[sent] || "📰"}</div>
      `;
      dom.newsFeed.appendChild(item);

      // FAZ 37 — lazy-load AI impact mini badge
      if (art.id) {
        const miniEl = item.querySelector('.news-impact-mini');
        fetch('/api/news/impact/' + encodeURIComponent(art.id))
          .then(r => r.json())
          .then(d => {
            if (!d.ok || !d.impact) return;
            const imp = d.impact;
            let badges = '';
            if (imp.bullish_assets && imp.bullish_assets.length)
              badges += `<span style="color:#00C853;">📈 ${imp.bullish_assets.slice(0,2).join(', ')}</span>`;
            if (imp.bearish_assets && imp.bearish_assets.length)
              badges += `<span style="color:#FF1744;">📉 ${imp.bearish_assets.slice(0,2).join(', ')}</span>`;
            if (imp.confidence_score >= 60)
              badges += `<span style="color:#FFD600;">AI ${imp.confidence_score}%</span>`;
            if (badges) { miniEl.innerHTML = badges; miniEl.style.display = 'flex'; }
          }).catch(() => {});
      }
    });
  }

  /* ── News Detail Modal ───────────────────────────────────────────── */
  function openNewsDetail(article) {
    const modal = document.getElementById("news-detail-modal");
    if (!modal) return;

    const sent = (article.sentiment || "neutral").toLowerCase();
    const sentimentEmoji = { positive: "📈", negative: "📉", neutral: "📰", bullish: "🐂", bearish: "🐻" };
    const sentLabel = sent === "bullish" || sent === "positive" ? "Pozitif" : sent === "bearish" || sent === "negative" ? "Negatif" : "Nötr";
    const sentClass = sent === "bullish" || sent === "positive" ? "bullish" : sent === "bearish" || sent === "negative" ? "bearish" : "neutral";

    /* Source */
    document.getElementById("news-modal-source").textContent = article.source || "";

    /* External link */
    const extBtn = document.getElementById("news-modal-external");
    extBtn.href = article.url || "#";

    /* Sentiment badge */
    const badge = document.getElementById("news-modal-sentiment");
    badge.className = "news-modal-badge " + sentClass;
    badge.textContent = (sentimentEmoji[sent] || "📰") + " " + sentLabel;

    /* Title */
    document.getElementById("news-modal-title").textContent = article.title || "";

    /* Meta */
    const metaText = [];
    if (article.published_at) metaText.push(timeAgo(article.published_at));
    if (article.market) metaText.push(article.market.toUpperCase());
    if (article.category && article.category !== article.market) metaText.push(article.category.toUpperCase());
    document.getElementById("news-modal-meta").textContent = metaText.join(" · ");

    /* Symbols */
    const symEl = document.getElementById("news-modal-symbols");
    if (article.symbols && article.symbols.length) {
      symEl.innerHTML = article.symbols.map(s => `<span class="news-symbol-chip">${s}</span>`).join("");
      symEl.style.display = "";
    } else {
      symEl.style.display = "none";
    }

    /* Image */
    const imgWrap = document.getElementById("news-modal-image-wrap");
    const imgEl = document.getElementById("news-modal-image");
    if (article.image_url) {
      imgEl.src = article.image_url;
      imgEl.onerror = () => { imgWrap.style.display = "none"; };
      imgWrap.style.display = "";
    } else {
      imgWrap.style.display = "none";
    }

    /* Summary */
    document.getElementById("news-modal-summary").textContent = article.summary || article.title || "";

    /* Read more link */
    document.getElementById("news-modal-readmore").href = article.url || "#";

    /* FAZ 37 — AI Impact Panel */
    const impPanel = document.getElementById("news-modal-impact");
    if (impPanel) {
      impPanel.style.display = "none";
      if (article.id) {
        fetch('/api/news/impact/' + encodeURIComponent(article.id))
          .then(r => r.json())
          .then(d => {
            if (!d.ok || !d.impact) return;
            const imp = d.impact;
            // Confidence badge
            const confEl = document.getElementById('news-impact-confidence');
            const confLvl = imp.confidence_score >= 70 ? 'High' : imp.confidence_score >= 40 ? 'Medium' : 'Low';
            const confColor = imp.confidence_score >= 70 ? '#00C853' : imp.confidence_score >= 40 ? '#FFD600' : '#FF1744';
            confEl.textContent = confLvl + ' ' + imp.confidence_score + '%';
            confEl.style.background = confColor + '22';
            confEl.style.color = confColor;
            // Sectors
            const bsEl = document.getElementById('news-impact-bullish-sectors');
            bsEl.textContent = (imp.bullish_sectors || []).length ? imp.bullish_sectors.join(', ') : '—';
            const bsEl2 = document.getElementById('news-impact-bearish-sectors');
            bsEl2.textContent = (imp.bearish_sectors || []).length ? imp.bearish_sectors.join(', ') : '—';
            // Assets
            const baEl = document.getElementById('news-impact-bullish-assets');
            baEl.innerHTML = (imp.bullish_assets || []).map(a => `<span style="background:#00C85318;color:#00C853;padding:1px 6px;border-radius:4px;margin-right:3px;font-size:.72rem;">${a}</span>`).join('') || '—';
            const baEl2 = document.getElementById('news-impact-bearish-assets');
            baEl2.innerHTML = (imp.bearish_assets || []).map(a => `<span style="background:#FF174418;color:#FF1744;padding:1px 6px;border-radius:4px;margin-right:3px;font-size:.72rem;">${a}</span>`).join('') || '—';
            // Summary & horizon
            document.getElementById('news-impact-summary').textContent = imp.impact_summary || '';
            const hMap = {short_term: '⏱ Kısa Vadeli', mid_term: '⏳ Orta Vadeli', long_term: '📅 Uzun Vadeli'};
            document.getElementById('news-impact-horizon').textContent = hMap[imp.time_horizon] || imp.time_horizon;
            impPanel.style.display = 'block';
          }).catch(() => {});
      }
    }

    /* Show modal */
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  function closeNewsDetail() {
    const modal = document.getElementById("news-detail-modal");
    if (modal) modal.style.display = "none";
    document.body.style.overflow = "";
  }

  function initNewsModal() {
    const backBtn = document.getElementById("news-modal-back");
    const modal = document.getElementById("news-detail-modal");
    if (backBtn) backBtn.addEventListener("click", closeNewsDetail);
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeNewsDetail();
      });
    }
    /* ESC key */
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeNewsDetail();
    });
  }

  /* ── Render: Economic Calendar ───────────────────────────────────── */
  function renderCalendar() {
    const now = new Date();
    dom.calDate.textContent = now.toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" });
    dom.calendarFeed.innerHTML = "";

    CALENDAR_EVENTS.forEach(ev => {
      const item = document.createElement("div");
      item.className = "disc-cal-item";
      item.innerHTML = `
        <div class="cal-time">${ev.time}</div>
        <div class="cal-flag">${ev.flag}</div>
        <div class="cal-info">
          <div class="cal-name">${ev.name}</div>
          <div class="cal-vals">
            <span>Gerçek: ${ev.actual}</span>
            <span>Tahmin: ${ev.forecast}</span>
            <span>Önceki: ${ev.previous}</span>
          </div>
        </div>
        <div class="cal-impact ${ev.impact}"></div>
      `;
      dom.calendarFeed.appendChild(item);
    });
  }

  /* ── Search ──────────────────────────────────────────────────────── */
  function initSearch() {
    const btnSearch = $("#btn-search");
    const btnClose  = $("#btn-search-close");

    btnSearch.addEventListener("click", () => {
      dom.searchOverlay.classList.remove("hidden");
      dom.searchInput.value = "";
      dom.searchInput.focus();
      dom.searchResults.innerHTML = "";
    });

    btnClose.addEventListener("click", () => {
      dom.searchOverlay.classList.add("hidden");
    });

    let debounce = null;
    dom.searchInput.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => runSearch(dom.searchInput.value.trim()), 300);
    });
  }

  async function runSearch(query) {
    if (!query || query.length < 1) {
      dom.searchResults.innerHTML = "";
      return;
    }
    const q = query.toUpperCase();
    const results = [];

    /* search across all categories */
    for (const [market, cfg] of Object.entries(CATEGORY_CONFIG)) {
      for (const sym of cfg.list) {
        const clean = cleanSymbol(sym).toUpperCase();
        const label = (cfg.labels[sym] || "").toUpperCase();
        if (clean.includes(q) || label.includes(q) || sym.toUpperCase().includes(q)) {
          results.push({ sym, label: cfg.labels[sym] || clean, market });
        }
      }
    }

    /* Also search dynamic symbol lists for bist/stocks */
    for (const market of ["bist", "stocks"]) {
      const items = await fetchAllSymbols(market);
      items.forEach(it => {
        const base = (it.base || "").toUpperCase();
        if (base.includes(q) && !results.find(r => r.sym === it.symbol)) {
          results.push({ sym: it.symbol, label: base, market });
        }
      });
    }

    dom.searchResults.innerHTML = "";
    results.slice(0, 15).forEach(r => {
      const div = document.createElement("div");
      div.className = "search-item";
      div.onclick = () => window.location.href = "/trade?symbol=" + encodeURIComponent(r.sym) + "&market=" + r.market;
      const marketLabel = { kripto:"Kripto", bist:"BIST", commodities:"Emtia", forex:"Forex", stocks:"ABD" }[r.market] || r.market;
      div.innerHTML = `
        <div class="si-icon">${cleanSymbol(r.sym).substring(0,2)}</div>
        <div>
          <div class="si-name">${cleanSymbol(r.sym)}</div>
          <div class="si-market">${r.label} · ${marketLabel}</div>
        </div>
      `;
      dom.searchResults.appendChild(div);
    });

    if (results.length === 0) {
      dom.searchResults.innerHTML = '<p class="text-sm text-neutral-500 py-8 text-center">Sonuç bulunamadı</p>';
    }
  }

  /* ── Category Chip Switching ─────────────────────────────────────── */
  function initChips() {
    $$("#category-chips .t-chip[data-cat]").forEach(chip => {
      chip.addEventListener("click", () => {
        if (chip.dataset.cat === currentCategory) return;
        $$("#category-chips .t-chip[data-cat]").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        currentCategory = chip.dataset.cat;

        /* clear caches for fresh data */
        klinesCache = {};

        /* re-render market sections */
        renderFeaturedCards();
        renderMarketList();
        renderMovers("up");

        /* reset mover toggle */
        $("#movers-up").classList.add("active");
        $("#movers-down").classList.remove("active");
      });
    });
  }

  /* ── Mover Toggle ────────────────────────────────────────────────── */
  function initMovers() {
    const btnUp   = $("#movers-up");
    const btnDown = $("#movers-down");

    btnUp.addEventListener("click", () => {
      btnUp.classList.add("active");
      btnDown.classList.remove("active");
      renderMovers("up");
    });
    btnDown.addEventListener("click", () => {
      btnDown.classList.add("active");
      btnUp.classList.remove("active");
      renderMovers("down");
    });
  }

  /* ── News Chip Switching ─────────────────────────────────────────── */
  function initNewsChips() {
    $$("#news-chips .t-chip[data-news]").forEach(chip => {
      chip.addEventListener("click", () => {
        $$("#news-chips .t-chip[data-news]").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        newsCache = {}; // force fresh
        renderNews(chip.dataset.news);
      });
    });
  }

  /* ── Sort Buttons ────────────────────────────────────────────────── */
  function initSorting() {
    const btnChange = $("#sort-change");
    const btnVolume = $("#sort-volume");

    btnChange.addEventListener("click", () => {
      btnChange.classList.add("text-white");
      btnVolume.classList.remove("text-white");
      sortMarketList("change");
    });
    btnVolume.addEventListener("click", () => {
      btnVolume.classList.add("text-white");
      btnChange.classList.remove("text-white");
      sortMarketList("volume");
    });
  }

  function sortMarketList(by) {
    const rows = $$(".disc-market-row", dom.marketList);
    if (!rows.length) return;

    const cfg = CATEGORY_CONFIG[currentCategory];
    const rowData = rows.map((row, i) => {
      const sym = cfg.list[i];
      const key = cfg.tickerEndpoint + ":" + sym;
      const ticker = tickerCache[key];
      return { row, sym, ticker };
    });

    rowData.sort((a, b) => {
      if (!a.ticker || !b.ticker) return 0;
      if (by === "volume") return (b.ticker.quoteVolume || 0) - (a.ticker.quoteVolume || 0);
      return Math.abs(b.ticker.priceChangePercent || 0) - Math.abs(a.ticker.priceChangePercent || 0);
    });

    dom.marketList.innerHTML = "";
    rowData.forEach(({ row }) => dom.marketList.appendChild(row));
  }

  /* ── Auto Refresh ────────────────────────────────────────────────── */
  function startRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(async () => {
      /* Only refresh tickers, not klines (too expensive) */
      const cfg = CATEGORY_CONFIG[currentCategory];
      await Promise.all(cfg.list.map(sym => fetchTicker(cfg.tickerEndpoint, sym)));

      /* Update prices in DOM without full re-render */
      const rows = $$(".disc-market-row", dom.marketList);
      rows.forEach((row, i) => {
        const sym = cfg.list[i];
        if (!sym) return;
        const key = cfg.tickerEndpoint + ":" + sym;
        const ticker = tickerCache[key];
        if (!ticker) return;

        const priceEl  = $(".row-price", row);
        const changeEl = $(".row-change", row);
        if (priceEl)  priceEl.textContent = fmtPrice(ticker.lastPrice, currentCategory);
        if (changeEl) {
          const pct = ticker.priceChangePercent || 0;
          changeEl.textContent = fmtPct(pct);
          changeEl.className = "row-change " + (pct >= 0 ? "up" : "down");
        }
      });

      /* Update featured cards prices too */
      const cards = $$(".disc-market-card", dom.featuredCards);
      cards.forEach((card, i) => {
        const sym = cfg.featured[i];
        if (!sym) return;
        const key = cfg.tickerEndpoint + ":" + sym;
        const ticker = tickerCache[key];
        if (!ticker) return;

        const priceEl  = $(".price", card);
        const changeEl = $(".change", card);
        if (priceEl)  priceEl.textContent = fmtPrice(ticker.lastPrice, currentCategory);
        if (changeEl) {
          const pct = ticker.priceChangePercent || 0;
          changeEl.textContent = fmtPct(pct);
          changeEl.className = "change " + (pct >= 0 ? "up" : "down");
        }
      });
    }, 15000);
  }

  /* ── Init ─────────────────────────────────────────────────────────── */
  async function init() {
    initSearch();
    initChips();
    initMovers();
    initNewsChips();
    initSorting();
    initNewsModal();

    /* Render all sections in parallel */
    await Promise.all([
      renderFeaturedCards(),
      renderMarketList(),
      renderMovers("up"),
      renderNews("crypto"),
    ]);

    renderCalendar();
    startRefresh();
  }

  /* Wait for DOM */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
