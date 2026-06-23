/* ═══════════════════════════════════════════════════════════════════
   chart_controls.js — FAZ 53 Chart Page Controls
   Symbol selector, timeframe selector, fullscreen, indicators
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  /* ── State ─────────────────────────────────────────────────────── */
  let currentSymbol = "BTCUSDT";
  let currentTimeframe = "1h";
  let isFullscreen = false;

  /* ── Popular symbols per market ─────────────────────────────────── */
  const SYMBOLS = {
    crypto: [
      { symbol: "BTCUSDT", label: "BTC/USDT" },
      { symbol: "ETHUSDT", label: "ETH/USDT" },
      { symbol: "SOLUSDT", label: "SOL/USDT" },
      { symbol: "BNBUSDT", label: "BNB/USDT" },
      { symbol: "XRPUSDT", label: "XRP/USDT" },
      { symbol: "DOGEUSDT", label: "DOGE/USDT" },
    ],
    bist: [
      { symbol: "XU100.IS", label: "BIST 100" },
      { symbol: "THYAO.IS", label: "THYAO" },
      { symbol: "GARAN.IS", label: "GARAN" },
      { symbol: "ASELS.IS", label: "ASELS" },
    ],
    stocks: [
      { symbol: "AAPL", label: "Apple" },
      { symbol: "MSFT", label: "Microsoft" },
      { symbol: "NVDA", label: "NVIDIA" },
      { symbol: "TSLA", label: "Tesla" },
    ],
    forex: [
      { symbol: "EURUSD=X", label: "EUR/USD" },
      { symbol: "USDTRY=X", label: "USD/TRY" },
      { symbol: "GBPUSD=X", label: "GBP/USD" },
    ],
    commodities: [
      { symbol: "GC=F", label: "Gold" },
      { symbol: "SI=F", label: "Silver" },
      { symbol: "CL=F", label: "Crude Oil" },
    ],
  };

  const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"];

  const INDICATORS = [
    { key: "rsi", label: "RSI" },
    { key: "macd", label: "MACD" },
    { key: "bb", label: "Bollinger Bands" },
    { key: "ema", label: "EMA 20/50" },
    { key: "volume", label: "Volume" },
  ];

  /* ── DOM ────────────────────────────────────────────────────────── */
  const controlsBar = document.getElementById("chartControlsBar");
  if (!controlsBar) return; // controls bar not present on page

  /* ── Build Controls UI ─────────────────────────────────────────── */
  function buildControls() {
    controlsBar.innerHTML = "";

    /* Symbol Selector */
    const symWrap = document.createElement("div");
    symWrap.className = "cc-group";
    const symSelect = document.createElement("select");
    symSelect.className = "cc-select";
    symSelect.id = "ccSymbolSelect";
    for (const [market, syms] of Object.entries(SYMBOLS)) {
      const optgroup = document.createElement("optgroup");
      optgroup.label = market.charAt(0).toUpperCase() + market.slice(1);
      syms.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.symbol;
        opt.textContent = s.label;
        if (s.symbol === currentSymbol) opt.selected = true;
        optgroup.appendChild(opt);
      });
      symSelect.appendChild(optgroup);
    }
    symSelect.addEventListener("change", () => {
      currentSymbol = symSelect.value;
      dispatchChange();
    });
    symWrap.appendChild(symSelect);
    controlsBar.appendChild(symWrap);

    /* Timeframe Selector */
    const tfWrap = document.createElement("div");
    tfWrap.className = "cc-group cc-tf-group";
    TIMEFRAMES.forEach((tf) => {
      const btn = document.createElement("button");
      btn.className = "cc-tf-btn" + (tf === currentTimeframe ? " active" : "");
      btn.textContent = tf;
      btn.addEventListener("click", () => {
        currentTimeframe = tf;
        tfWrap.querySelectorAll(".cc-tf-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        dispatchChange();
      });
      tfWrap.appendChild(btn);
    });
    controlsBar.appendChild(tfWrap);

    /* Indicator Toggle */
    const indWrap = document.createElement("div");
    indWrap.className = "cc-group cc-ind-group";
    const indBtn = document.createElement("button");
    indBtn.className = "cc-btn";
    indBtn.textContent = "📈 Indicators";
    const indMenu = document.createElement("div");
    indMenu.className = "cc-dropdown";
    indMenu.style.display = "none";
    INDICATORS.forEach((ind) => {
      const label = document.createElement("label");
      label.className = "cc-dropdown-item";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = ind.key;
      cb.addEventListener("change", () => {
        window.dispatchEvent(new CustomEvent("chart:indicator", { detail: { key: ind.key, enabled: cb.checked } }));
      });
      label.appendChild(cb);
      label.appendChild(document.createTextNode(" " + ind.label));
      indMenu.appendChild(label);
    });
    indBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      indMenu.style.display = indMenu.style.display === "none" ? "block" : "none";
    });
    document.addEventListener("click", () => { indMenu.style.display = "none"; });
    indWrap.appendChild(indBtn);
    indWrap.appendChild(indMenu);
    controlsBar.appendChild(indWrap);

    /* Fullscreen Toggle */
    const fsBtn = document.createElement("button");
    fsBtn.className = "cc-btn cc-fs-btn";
    fsBtn.textContent = "⛶";
    fsBtn.title = "Fullscreen";
    fsBtn.addEventListener("click", toggleFullscreen);
    controlsBar.appendChild(fsBtn);
  }

  function dispatchChange() {
    window.dispatchEvent(
      new CustomEvent("chart:change", {
        detail: { symbol: currentSymbol, timeframe: currentTimeframe },
      })
    );
  }

  function toggleFullscreen() {
    const shell = document.querySelector(".tv-shell") || document.documentElement;
    if (!document.fullscreenElement) {
      shell.requestFullscreen().catch(() => {});
      isFullscreen = true;
    } else {
      document.exitFullscreen();
      isFullscreen = false;
    }
  }

  /* ── Responsive ────────────────────────────────────────────────── */
  function handleResize() {
    if (!controlsBar) return;
    controlsBar.classList.toggle("cc-compact", window.innerWidth < 640);
  }

  window.addEventListener("resize", handleResize);
  handleResize();
  buildControls();
})();
