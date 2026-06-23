/* ═══════════════════════════════════════════════════════════════════
   simulator.js — ZKR Analiz v2 Advanced Trading Simulator (FAZ 57)
   Real exchange experience: order types, order book, live PnL
   ═══════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  const API = "/api/simulator";

  // ── State ─────────────────────────────────────────────────────────
  let currentSide = "buy";      // buy | sell
  let currentType = "market";   // market | limit | stop_limit
  let livePrice = 0;
  let lastGoodPrice = 0;        // FAZ 63: cache last valid price as fallback
  let accountData = null;
  let activePresetPct = null;   // FAZ 63B: currently active percentage button

  // FAZ 63C: WebSocket live price state
  let _simWS = null;
  let _wsConnected = false;
  let _wsReconnectTimer = null;
  let _wsReconnectDelay = 1000;
  const _WS_MAX_RECONNECT = 30000;
  let _wsPriceSource = false;   // true when last livePrice came from WS

  // ── DOM refs ──────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const $balance     = $("sim-balance");
  const $equity      = $("sim-equity");
  const $available   = $("sim-available");
  const $unrealPnl   = $("sim-unrealized-pnl");
  const $realPnl     = $("sim-realized-pnl");
  const $symbol      = $("sim-symbol");
  const $market      = $("sim-market");
  const $quantity    = $("sim-quantity");
  const $livePrice   = $("sim-live-price");
  const $limitPrice  = $("sim-limit-price");
  const $stopPrice   = $("sim-stop-price");
  const $priceFields = $("sim-price-fields");
  const $stopWrap    = $("sim-stop-price-wrap");
  const $estCost     = $("sim-est-cost");
  const $executeBtn  = $("sim-execute-btn");
  const $tradeMsg    = $("sim-trade-msg");
  const $posOpen     = $("sim-positions-open");
  const $posClosed   = $("sim-positions-closed");
  const $ordersList  = $("sim-orders-list");
  const $tradesList  = $("sim-trades-list");
  const $refreshBtn  = $("sim-refresh-btn");
  const $resetBtn    = $("sim-reset-btn");
  const $resetModal  = $("sim-reset-modal");
  const $resetCancel = $("sim-reset-cancel");
  const $resetConfirm= $("sim-reset-confirm");
  const $obAsks      = $("sim-ob-asks");
  const $obBids      = $("sim-ob-bids");
  const $obSpread    = $("sim-ob-spread");
  const $midPrice    = $("sim-mid-price");
  const $tabPosCount = $("sim-tab-pos-count");
  const $tabOrdCount = $("sim-tab-ord-count");
  const $emptyPos    = $("sim-empty-positions");
  const $toast       = $("sim-toast-container");

  // ── Helpers ───────────────────────────────────────────────────────
  function fmt(n, dec) {
    if (n == null || isNaN(n)) return "$0.00";
    var v = Number(n);
    if (dec === undefined) dec = v >= 10000 ? 0 : 2;
    return "$" + v.toLocaleString("en-US", {
      minimumFractionDigits: dec,
      maximumFractionDigits: dec,
    });
  }

  function fmtPnl(n) {
    if (n == null || isNaN(n)) return "$0.00";
    var sign = n > 0 ? "+$" : n < 0 ? "-$" : "$";
    return sign + Math.abs(n).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function fmtPct(n) {
    if (n == null || isNaN(n)) return "0.00%";
    return (n > 0 ? "+" : "") + Number(n).toFixed(2) + "%";
  }

  function fmtQty(n) {
    if (n == null || isNaN(n)) return "0";
    var v = Number(n);
    if (v >= 1) return v.toLocaleString("en-US", { maximumFractionDigits: 4 });
    return v.toFixed(6);
  }

  function fmtPrice(n) {
    if (n == null || isNaN(n)) return "—";
    var v = Number(n);
    if (v >= 10000) return v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (v >= 1) return v.toFixed(2);
    if (v >= 0.01) return v.toFixed(4);
    return v.toFixed(6);
  }

  function timeAgo(iso) {
    if (!iso) return "";
    var diff = Date.now() - new Date(iso).getTime();
    var mins = Math.floor(diff / 60000);
    if (mins < 1) return "Az önce";
    if (mins < 60) return mins + " dk önce";
    var hours = Math.floor(mins / 60);
    if (hours < 24) return hours + " saat önce";
    return Math.floor(hours / 24) + " gün önce";
  }

  function pnlClass(n) {
    if (n > 0) return "positive";
    if (n < 0) return "negative";
    return "neutral";
  }

  async function api(path, opts) {
    try {
      var res = await fetch(API + path, opts || {});
      return await res.json();
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  // ── Toast Notifications ───────────────────────────────────────────
  function showToast(text, type) {
    type = type || "success";
    var toast = document.createElement("div");
    toast.className = "sim-toast sim-toast-" + type;
    toast.textContent = text;
    $toast.appendChild(toast);
    requestAnimationFrame(function() { toast.classList.add("show"); });
    setTimeout(function() {
      toast.classList.remove("show");
      setTimeout(function() { toast.remove(); }, 300);
    }, 4000);
  }

  function showMsg(text, type) {
    $tradeMsg.textContent = text;
    $tradeMsg.className = "sim-trade-msg " + (type || "success");
    setTimeout(function() { $tradeMsg.classList.add("hidden"); }, 5000);
  }

  // ══════════════════════════════════════════════════════════════════
  // ACCOUNT
  // ══════════════════════════════════════════════════════════════════
  async function loadAccount() {
    var data = await api("/account/extended");
    if (!data.ok) return;
    accountData = data;

    $balance.textContent = fmt(data.balance);
    $equity.textContent = fmt(data.equity);
    $available.textContent = fmt(data.available);

    $unrealPnl.textContent = fmtPnl(data.unrealized_pnl);
    $unrealPnl.className = "sim-acc-value " + pnlClass(data.unrealized_pnl);

    $realPnl.textContent = fmtPnl(data.realized_pnl);
    $realPnl.className = "sim-acc-value " + pnlClass(data.realized_pnl);

    // Render open positions from account data
    renderPositions(data.open_positions || [], "open");
    $tabPosCount.textContent = (data.open_positions || []).length;

    updateEstimate();
  }

  // ══════════════════════════════════════════════════════════════════
  // ORDER BOOK
  // ══════════════════════════════════════════════════════════════════
  async function loadOrderBook() {
    var symbol = ($symbol.value || "").trim().toUpperCase();
    var market = $market.value;
    if (!symbol) return;

    var data = await api("/orderbook?symbol=" + encodeURIComponent(symbol) +
      "&market=" + encodeURIComponent(market) + "&levels=10");
    if (!data.ok) return;

    // Render asks (reversed, lowest at bottom)
    var asks = (data.asks || []).slice(0, 10).reverse();
    var maxAskQty = Math.max.apply(null, asks.map(function(a) { return a.quantity; }).concat([1]));
    $obAsks.innerHTML = asks.map(function(a) {
      var pct = Math.min((a.quantity / maxAskQty) * 100, 100);
      return '<div class="sim-ob-row sim-ob-ask">' +
        '<div class="sim-ob-bar-bg" style="width:' + pct + '%"></div>' +
        '<span class="sim-ob-price">' + fmtPrice(a.price) + '</span>' +
        '<span class="sim-ob-qty">' + fmtQty(a.quantity) + '</span>' +
        '<span class="sim-ob-total">' + fmt(a.total, 0) + '</span>' +
        '</div>';
    }).join("");

    // Mid price
    $midPrice.textContent = fmtPrice(data.mid_price);

    // Spread
    $obSpread.textContent = "Spread: " + fmtPrice(data.spread) +
      " (" + (data.spread_pct || 0).toFixed(3) + "%)";

    // Render bids
    var bids = (data.bids || []).slice(0, 10);
    var maxBidQty = Math.max.apply(null, bids.map(function(b) { return b.quantity; }).concat([1]));
    $obBids.innerHTML = bids.map(function(b) {
      var pct = Math.min((b.quantity / maxBidQty) * 100, 100);
      return '<div class="sim-ob-row sim-ob-bid">' +
        '<div class="sim-ob-bar-bg" style="width:' + pct + '%"></div>' +
        '<span class="sim-ob-price">' + fmtPrice(b.price) + '</span>' +
        '<span class="sim-ob-qty">' + fmtQty(b.quantity) + '</span>' +
        '<span class="sim-ob-total">' + fmt(b.total, 0) + '</span>' +
        '</div>';
    }).join("");
  }

  // ══════════════════════════════════════════════════════════════════
  // POSITIONS
  // ══════════════════════════════════════════════════════════════════
  function renderPositions(positions, status) {
    var container = status === "open" ? $posOpen : $posClosed;
    if (!positions.length) {
      if (status === "open") {
        container.innerHTML = '<div class="sim-empty-state">' +
          '<div class="sim-empty-icon">📊</div>' +
          '<div class="sim-empty-title">Henüz işlem yapmadın</div>' +
          '<div class="sim-empty-desc">Simülasyon ile trading pratiği yap</div></div>';
      } else {
        container.innerHTML = '<div class="sim-empty-state">' +
          '<div class="sim-empty-icon">📁</div>' +
          '<div class="sim-empty-title">Kapanmış pozisyon yok</div></div>';
      }
      return;
    }

    container.innerHTML = positions.map(function(p) {
      var cls = pnlClass(p.pnl_abs);
      var closeBtn = status === "open"
        ? '<button class="sim-btn-close" data-close="' + p.id + '">Kapat</button>'
        : "";
      var sideLabel = p.side === "buy" ? "LONG" : "SHORT";
      var sideClass = p.side === "buy" ? "long" : "short";
      var notional = (p.entry_price || 0) * (p.quantity || 0);
      return '<div class="sim-position-card">' +
        '<div class="sim-pos-header">' +
          '<div class="sim-pos-symbol">' +
            '<span class="sim-pos-badge ' + sideClass + '">' + sideLabel + '</span>' +
            '<span class="sim-pos-symbol-name">' + p.symbol + '</span>' +
            '<span class="sim-pos-market">' + p.market + '</span>' +
          '</div>' +
          closeBtn +
        '</div>' +
        '<div class="sim-pos-grid">' +
          '<div class="sim-pos-stat">' +
            '<span class="sim-pos-stat-label">Miktar</span>' +
            '<span class="sim-pos-stat-value">' + fmtQty(p.quantity) + '</span>' +
          '</div>' +
          '<div class="sim-pos-stat">' +
            '<span class="sim-pos-stat-label">Giriş</span>' +
            '<span class="sim-pos-stat-value">' + fmtPrice(p.entry_price) + '</span>' +
          '</div>' +
          '<div class="sim-pos-stat">' +
            '<span class="sim-pos-stat-label">Güncel</span>' +
            '<span class="sim-pos-stat-value">' + fmtPrice(p.current_price) + '</span>' +
          '</div>' +
          '<div class="sim-pos-stat">' +
            '<span class="sim-pos-stat-label">Değer</span>' +
            '<span class="sim-pos-stat-value">' + fmt(notional) + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="sim-pos-footer">' +
          '<span class="sim-pos-time">' + timeAgo(p.opened_at || p.closed_at) + '</span>' +
          '<span class="sim-pos-pnl ' + cls + '">' + fmtPnl(p.pnl_abs) + ' (' + fmtPct(p.pnl_pct) + ')</span>' +
        '</div>' +
        '</div>';
    }).join("");

    // Bind close buttons
    if (status === "open") {
      container.querySelectorAll("[data-close]").forEach(function(btn) {
        btn.addEventListener("click", function() { closePosition(btn.dataset.close); });
      });
    }
  }

  async function loadClosedPositions() {
    var data = await api("/positions?status=closed");
    if (!data.ok) return;
    renderPositions(data.positions || [], "closed");
  }

  // ══════════════════════════════════════════════════════════════════
  // ORDERS
  // ══════════════════════════════════════════════════════════════════
  async function loadOrders() {
    var data = await api("/orders?status=pending");
    if (!data.ok) return;
    var orders = data.orders || [];
    $tabOrdCount.textContent = orders.length;

    if (!orders.length) {
      $ordersList.innerHTML = '<div class="sim-empty-state">' +
        '<div class="sim-empty-icon">📋</div>' +
        '<div class="sim-empty-title">Bekleyen emir yok</div>' +
        '<div class="sim-empty-desc">Limit veya Stop-Limit emri girin</div></div>';
      return;
    }

    $ordersList.innerHTML = orders.map(function(o) {
      var sideClass = o.side === "buy" ? "long" : "short";
      var sideLabel = o.side === "buy" ? "AL" : "SAT";
      var typeLabel = o.order_type === "limit" ? "Limit" : "Stop-Limit";
      var priceStr = o.order_type === "stop_limit"
        ? "Stop: " + fmtPrice(o.stop_price) + " → " + fmtPrice(o.price)
        : fmtPrice(o.price || o.limit_price);
      return '<div class="sim-order-card">' +
        '<div class="sim-order-header">' +
          '<div class="sim-order-info">' +
            '<span class="sim-pos-badge ' + sideClass + '">' + sideLabel + '</span>' +
            '<span class="sim-order-symbol">' + o.symbol + '</span>' +
            '<span class="sim-order-type-badge">' + typeLabel + '</span>' +
          '</div>' +
          '<button class="sim-btn-cancel" data-cancel="' + o.id + '">İptal</button>' +
        '</div>' +
        '<div class="sim-order-details">' +
          '<span>Fiyat: ' + priceStr + '</span>' +
          '<span>Miktar: ' + fmtQty(o.quantity) + '</span>' +
          '<span>' + timeAgo(o.created_at) + '</span>' +
        '</div>' +
        '</div>';
    }).join("");

    $ordersList.querySelectorAll("[data-cancel]").forEach(function(btn) {
      btn.addEventListener("click", function() { cancelOrder(btn.dataset.cancel); });
    });
  }

  async function cancelOrder(id) {
    var data = await api("/order/" + id + "/cancel", { method: "POST" });
    if (data.ok) {
      showToast("Emir iptal edildi", "info");
      refreshAll();
    } else {
      showToast(data.error || "İptal başarısız", "error");
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // TRADES HISTORY
  // ══════════════════════════════════════════════════════════════════
  async function loadTrades() {
    var data = await api("/trades?limit=50");
    if (!data.ok) return;
    var trades = data.trades || [];

    if (!trades.length) {
      $tradesList.innerHTML = '<div class="sim-empty-state">' +
        '<div class="sim-empty-icon">📜</div>' +
        '<div class="sim-empty-title">İşlem geçmişi boş</div></div>';
      return;
    }

    $tradesList.innerHTML = trades.map(function(t) {
      var icon = t.side === "buy" ? "↑" : "↓";
      var sideClass = t.side === "buy" ? "buy" : "sell";
      return '<div class="sim-trade-item">' +
        '<div class="sim-trade-left">' +
          '<div class="sim-trade-icon ' + sideClass + '">' + icon + '</div>' +
          '<div class="sim-trade-info">' +
            '<span class="sim-trade-symbol">' + t.symbol + '</span>' +
            '<span class="sim-trade-note">' + (t.note || "") + '</span>' +
          '</div>' +
        '</div>' +
        '<div class="sim-trade-right">' +
          '<div class="sim-trade-notional">' + fmt(t.notional) + '</div>' +
          '<div class="sim-trade-time">' + timeAgo(t.executed_at) + '</div>' +
        '</div>' +
        '</div>';
    }).join("");
  }

  // ══════════════════════════════════════════════════════════════════
  // TRADE EXECUTION
  // ══════════════════════════════════════════════════════════════════
  async function executeTrade() {
    var symbol = ($symbol.value || "").trim().toUpperCase();
    var market = $market.value;
    var quantity = parseFloat($quantity.value);

    if (!symbol) { showToast("Sembol girin", "error"); return; }
    if (!quantity || quantity <= 0) { showToast("Geçerli miktar girin", "error"); return; }

    $executeBtn.disabled = true;
    $executeBtn.textContent = "İşleniyor...";

    var body = {
      symbol: symbol,
      market: market,
      side: currentSide,
      order_type: currentType,
      quantity: quantity,
    };

    if (currentType === "limit" || currentType === "stop_limit") {
      var limitP = parseFloat($limitPrice.value);
      if (!limitP || limitP <= 0) {
        showToast("Geçerli fiyat girin", "error");
        $executeBtn.disabled = false;
        updateExecuteBtn();
        return;
      }
      body.price = limitP;
    }

    if (currentType === "stop_limit") {
      var stopP = parseFloat($stopPrice.value);
      if (!stopP || stopP <= 0) {
        showToast("Geçerli stop fiyat girin", "error");
        $executeBtn.disabled = false;
        updateExecuteBtn();
        return;
      }
      body.stop_price = stopP;
    }

    var data = await api("/order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    $executeBtn.disabled = false;
    updateExecuteBtn();

    if (data.ok) {
      showToast(data.message || "İşlem başarılı", "success");
      refreshAll();
    } else {
      showToast(data.error || "İşlem başarısız", "error");
    }
  }

  async function closePosition(id) {
    var data = await api("/close/" + id, { method: "POST" });
    if (data.ok) {
      var pnl = data.position ? data.position.pnl_abs : 0;
      var emoji = pnl >= 0 ? "🟢" : "🔴";
      showToast(emoji + " Pozisyon kapatıldı — PnL: " + fmtPnl(pnl), pnl >= 0 ? "success" : "error");
      refreshAll();
      // FAZ 23 — offer journal
      if (data.position) showJournalPrompt(data.position);
    } else {
      showToast(data.error || "Kapatma başarısız", "error");
    }
  }

  async function resetAccount() {
    var data = await api("/account/reset", { method: "POST" });
    if (data.ok) {
      showToast("Hesap sıfırlandı ✓", "success");
      $resetModal.classList.add("hidden");
      refreshAll();
    } else {
      showToast(data.error || "Sıfırlama başarısız", "error");
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // LIVE PRICE — FAZ 64: Robust WebSocket + REST with retry
  // ══════════════════════════════════════════════════════════════════

  var _wsFirstTickReceived = false; // FAZ 64: track if WS ever delivered a tick
  var _initialPriceLoaded = false;  // FAZ 64: track if we got any price on init

  // ── WebSocket live price (crypto only) ────────────────────────────
  function connectSimWS() {
    var market = ($market.value || "").toLowerCase();
    // Only use WS for crypto
    if (market !== "crypto") {
      disconnectSimWS();
      return;
    }

    var symbol = ($symbol.value || "").trim().toUpperCase();
    if (!symbol) return;

    // Close existing connection before opening new one
    if (_simWS) {
      try { _simWS.close(); } catch(e) {}
      _simWS = null;
    }

    var proto = location.protocol === "https:" ? "wss" : "ws";
    var url = proto + "://" + location.host + "/ws/market";

    try {
      _simWS = new WebSocket(url);
    } catch(e) {
      console.warn("[Simulator WS] create failed:", e);
      _wsConnected = false;
      _scheduleWSReconnect();
      return;
    }

    _simWS.onopen = function() {
      console.log("[Simulator WS] connected");
      _wsConnected = true;
      _wsReconnectDelay = 1000;
      _wsFirstTickReceived = false; // FAZ 64: reset tick flag on new connection
      // Subscribe to selected symbol with 1m interval for fastest price updates
      var sym = ($symbol.value || "").trim().toUpperCase();
      if (sym) {
        _simWS.send(JSON.stringify({
          action: "subscribe",
          symbol: sym,
          market: "crypto",
          interval: "1m"
        }));
      }
      // FAZ 64B: Keep REST at 5s until WS proves it delivers ticks.
      // Don't throttle REST on WS connect — only throttle after first kline tick.
      // This ensures continuous price updates regardless of WS state.

      // FAZ 64: If no WS tick within 5s, force a REST fetch for immediate display
      setTimeout(function() {
        if (!_wsFirstTickReceived && _wsConnected) {
          console.log("[Simulator WS] no tick in 5s, forcing REST fetch");
          fetchPrice(true); // force=true bypasses WS guard
        }
      }, 5000);
    };

    _simWS.onmessage = function(evt) {
      var msg;
      try { msg = JSON.parse(evt.data); } catch(e) { return; }

      if (msg.type === "kline") {
        _handleSimWSTick(msg);
      }
      // Ignore other message types (pong, subscribed, watchlist, etc.)
    };

    _simWS.onclose = function(evt) {
      console.log("[Simulator WS] closed, code:", evt.code);
      _wsConnected = false;
      _wsPriceSource = false;
      // Restore fast REST polling as fallback
      if (priceInterval) clearInterval(priceInterval);
      priceInterval = setInterval(fetchPrice, 5000);
      fetchPrice(); // immediate fetch
      _scheduleWSReconnect();
    };

    _simWS.onerror = function(err) {
      console.warn("[Simulator WS] error:", err);
    };
  }

  function _handleSimWSTick(tick) {
    // Only accept ticks matching current symbol
    var sym = ($symbol.value || "").trim().toUpperCase();
    if (!sym || tick.symbol !== sym) return;

    var price = tick.close;
    if (!price || price <= 0) return;

    _wsFirstTickReceived = true;

    var prev = livePrice;
    livePrice = price;
    lastGoodPrice = price;
    _wsPriceSource = true;

    // Update DOM
    $livePrice.textContent = fmtPrice(price);
    $livePrice.classList.add("loaded");

    // Flash green/red on change
    if (prev > 0 && price !== prev) {
      $livePrice.classList.remove("flash-up", "flash-down");
      $livePrice.classList.add(price > prev ? "flash-up" : "flash-down");
      setTimeout(function() {
        $livePrice.classList.remove("flash-up", "flash-down");
      }, 600);
    }

    updateEstimate();
  }

  function disconnectSimWS() {
    if (_wsReconnectTimer) { clearTimeout(_wsReconnectTimer); _wsReconnectTimer = null; }
    _wsConnected = false;
    _wsPriceSource = false;
    if (_simWS) {
      try { _simWS.close(); } catch(e) {}
      _simWS = null;
    }
  }

  function _scheduleWSReconnect() {
    if (_wsReconnectTimer) clearTimeout(_wsReconnectTimer);
    var market = ($market.value || "").toLowerCase();
    if (market !== "crypto") return; // don't reconnect for non-crypto

    _wsReconnectTimer = setTimeout(function() {
      _wsReconnectDelay = Math.min(_wsReconnectDelay * 2, _WS_MAX_RECONNECT);
      connectSimWS();
    }, _wsReconnectDelay);
  }

  function resubscribeSimWS() {
    // Re-subscribe to new symbol on existing WS connection
    if (!_wsConnected || !_simWS || _simWS.readyState !== WebSocket.OPEN) {
      connectSimWS();
      return;
    }
    var sym = ($symbol.value || "").trim().toUpperCase();
    var market = ($market.value || "").toLowerCase();
    if (market !== "crypto" || !sym) {
      disconnectSimWS();
      return;
    }
    _simWS.send(JSON.stringify({
      action: "subscribe",
      symbol: sym,
      market: "crypto",
      interval: "1m"
    }));
  }
  var priceInterval = null;
  var priceDebounce = null;

  function startPriceFetch() {
    if (priceInterval) clearInterval(priceInterval);
    fetchPrice();
    priceInterval = setInterval(fetchPrice, 5000); // FAZ 63: 5s for better responsiveness
  }

  async function fetchPrice(force) {
    var symbol = ($symbol.value || "").trim().toUpperCase();
    var market = $market.value;
    if (!symbol) {
      $livePrice.textContent = "—";
      $livePrice.classList.remove("loaded");
      livePrice = 0;
      return;
    }

    // FAZ 64: Show loading indicator on first load
    if (!_initialPriceLoaded && livePrice <= 0) {
      $livePrice.textContent = "Yükleniyor...";
    }

    // FAZ 64C: Always fetch REST price — no WS guard.
    // WS updates livePrice directly in _handleSimWSTick;
    // REST runs in parallel as the reliable baseline.

    try {
      var r = await fetch(API + "/price?symbol=" + encodeURIComponent(symbol) +
        "&market=" + encodeURIComponent(market));
      if (r.ok) {
        var d = await r.json();
        if (d.ok && d.price) {
          var prev = livePrice;
          livePrice = d.price;
          lastGoodPrice = d.price;
          _initialPriceLoaded = true;
          $livePrice.textContent = fmtPrice(d.price);
          $livePrice.classList.add("loaded");
          // Flash green/red on change
          if (prev > 0 && d.price !== prev) {
            $livePrice.classList.remove("flash-up", "flash-down");
            $livePrice.classList.add(d.price > prev ? "flash-up" : "flash-down");
            setTimeout(function() {
              $livePrice.classList.remove("flash-up", "flash-down");
            }, 600);
          }
          updateEstimate();
          return;
        }
      }
    } catch (e) {
      console.warn("[Simulator] fetchPrice error:", e.message);
    }

    // FAZ 63: Keep last good price as fallback instead of zeroing out
    if (lastGoodPrice > 0) {
      livePrice = lastGoodPrice;
      $livePrice.textContent = fmtPrice(lastGoodPrice);
      $livePrice.classList.add("loaded");
    } else {
      $livePrice.textContent = "—";
      $livePrice.classList.remove("loaded");
      livePrice = 0;
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // UI INTERACTIONS
  // ══════════════════════════════════════════════════════════════════

  // Side toggle
  document.querySelectorAll(".sim-side-btn").forEach(function(btn) {
    btn.addEventListener("click", function() {
      document.querySelectorAll(".sim-side-btn").forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      currentSide = btn.dataset.side;
      updateExecuteBtn();
    });
  });

  // Order type tabs
  document.querySelectorAll(".sim-otype-tab").forEach(function(tab) {
    tab.addEventListener("click", function() {
      document.querySelectorAll(".sim-otype-tab").forEach(function(t) { t.classList.remove("active"); });
      tab.classList.add("active");
      currentType = tab.dataset.type;

      if (currentType === "market") {
        $priceFields.classList.add("hidden");
      } else {
        $priceFields.classList.remove("hidden");
        if (currentType === "stop_limit") {
          $stopWrap.style.display = "";
        } else {
          $stopWrap.style.display = "none";
        }
        // Pre-fill limit price with current price
        if (livePrice > 0 && !$limitPrice.value) {
          $limitPrice.value = livePrice;
        }
      }
      updateExecuteBtn();
    });
  });

  function updateExecuteBtn() {
    var sideLabel = currentSide === "buy" ? "Long Aç" : "Short Aç";
    var typeLabel = currentType === "market" ? "Market"
      : currentType === "limit" ? "Limit" : "Stop-Limit";
    $executeBtn.textContent = sideLabel + " — " + typeLabel;
    $executeBtn.className = "sim-execute-btn " +
      (currentSide === "buy" ? "sim-execute-buy" : "sim-execute-sell");
  }

  // Amount presets — FAZ 63B: Full rewrite with active state, preview, smart precision
  function getEffectivePrice() {
    // For limit/stop-limit, prefer entered price; fallback to livePrice
    if (currentType !== "market") {
      var entered = parseFloat($limitPrice.value);
      if (entered > 0) return entered;
    }
    // FAZ 64B: fallback to lastGoodPrice when livePrice is temporarily 0
    return livePrice > 0 ? livePrice : lastGoodPrice;
  }

  function qtyDecimals(price) {
    if (price >= 10000) return 6;  // BTC-level: 0.000001
    if (price >= 100)   return 5;  // ETH-level
    if (price >= 1)     return 4;
    return 2; // low-priced tokens
  }

  function clearPresetActive() {
    document.querySelectorAll(".sim-preset-btn").forEach(function(b) {
      b.classList.remove("active");
    });
    activePresetPct = null;
  }

  function updatePresetPreview(usedBalance, qty, symbol) {
    var $preview = document.getElementById("sim-preset-preview");
    if (!$preview) return;
    if (!usedBalance || !qty) {
      $preview.textContent = "";
      $preview.classList.remove("visible");
      return;
    }
    var sym = (symbol || ($symbol.value || "")).toUpperCase();
    $preview.textContent = "Kullanılacak: " + fmt(usedBalance) +
      "  ·  Yaklaşık: " + fmtQty(qty) + " " + sym;
    $preview.classList.add("visible");
  }

  document.querySelectorAll(".sim-preset-btn").forEach(function(btn) {
    btn.addEventListener("click", async function() {
      var price = getEffectivePrice();

      // FAZ 64B: If no price yet, try an immediate REST fetch before showing error
      if (!price || price <= 0) {
        await fetchPrice(true);
        price = getEffectivePrice();
      }

      if (!price || price <= 0) {
        showToast("Fiyat verisi alınamadı", "error");
        return;
      }
      // FAZ 64C: If accountData not yet loaded, fetch it now instead of showing error
      if (!accountData || !accountData.available) {
        await loadAccount();
      }
      if (!accountData || !accountData.available) {
        showToast("Bakiye bilgisi yüklenemedi", "error");
        return;
      }

      var pct = parseInt(btn.dataset.pct) / 100;
      var available = accountData.available || 0;
      if (available <= 0) {
        showToast("Yetersiz bakiye", "error");
        return;
      }

      // Calculate quantity: (available * pct * 0.999) / price
      var usedBalance = available * pct;
      var maxQty = (usedBalance * 0.999) / price; // 0.1% fee buffer
      var dec = qtyDecimals(price);
      var qty = parseFloat(maxQty.toFixed(dec));

      if (!qty || qty <= 0 || isNaN(qty)) {
        showToast("Hesaplanan miktar çok küçük", "error");
        return;
      }

      $quantity.value = qty;
      activePresetPct = parseInt(btn.dataset.pct);

      // Highlight active button
      clearPresetActive();
      btn.classList.add("active");

      // Preview
      updatePresetPreview(usedBalance, qty);

      updateEstimate();
    });
  });

  // Clear preset highlight on manual quantity edit
  $quantity.addEventListener("input", function() {
    clearPresetActive();
    updatePresetPreview(0, 0);
    updateEstimate();
  });

  // Estimate cost
  function updateEstimate() {
    var qty = parseFloat($quantity.value) || 0;
    var price = getEffectivePrice();
    var cost = qty * price * 1.001; // include fee
    $estCost.textContent = cost > 0 ? fmt(cost) : "$0.00";
  }

  if ($limitPrice) $limitPrice.addEventListener("input", updateEstimate);

  // Execute button
  $executeBtn.addEventListener("click", executeTrade);

  // Tab switching
  document.querySelectorAll(".sim-tab-btn").forEach(function(btn) {
    btn.addEventListener("click", function() {
      document.querySelectorAll(".sim-tab-btn").forEach(function(b) { b.classList.remove("active"); });
      document.querySelectorAll(".sim-tab-pane").forEach(function(p) { p.classList.remove("active"); });
      btn.classList.add("active");
      var tab = btn.dataset.tab;
      var pane = document.getElementById("sim-pane-" + tab);
      if (pane) pane.classList.add("active");

      if (tab === "closed") loadClosedPositions();
      if (tab === "orders") loadOrders();
      if (tab === "history") loadTrades();
    });
  });

  // Refresh button
  $refreshBtn.addEventListener("click", function() {
    $refreshBtn.querySelector("svg").style.animation = "spin 0.6s linear";
    refreshAll();
    setTimeout(function() {
      $refreshBtn.querySelector("svg").style.animation = "";
    }, 600);
  });

  // Reset modal
  $resetBtn.addEventListener("click", function() { $resetModal.classList.remove("hidden"); });
  $resetCancel.addEventListener("click", function() { $resetModal.classList.add("hidden"); });
  $resetConfirm.addEventListener("click", resetAccount);
  var backdrop = document.querySelector(".sim-modal-backdrop");
  if (backdrop) backdrop.addEventListener("click", function() { $resetModal.classList.add("hidden"); });

  // Price fetch on input change
  $symbol.addEventListener("input", function() {
    if (priceDebounce) clearTimeout(priceDebounce);
    priceDebounce = setTimeout(function() {
      lastGoodPrice = 0; // FAZ 63: reset cache on symbol change
      livePrice = 0;
      _wsPriceSource = false; // FAZ 63C: reset WS price flag
      _wsFirstTickReceived = false; // FAZ 64: reset tick flag
      _initialPriceLoaded = false; // FAZ 64: reset initial load flag
      fetchPrice();
      loadOrderBook();
      startPriceFetch();
      resubscribeSimWS(); // FAZ 63C: re-subscribe WS to new symbol
    }, 500);
  });
  $market.addEventListener("change", function() {
    lastGoodPrice = 0; // FAZ 63: reset cache on market change
    livePrice = 0;
    _wsPriceSource = false; // FAZ 63C: reset WS price flag
    _wsFirstTickReceived = false; // FAZ 64: reset tick flag
    _initialPriceLoaded = false; // FAZ 64: reset initial load flag
    fetchPrice();
    loadOrderBook();
    startPriceFetch();
    // FAZ 63C: Connect WS for crypto, disconnect for others
    var market = ($market.value || "").toLowerCase();
    if (market === "crypto") {
      connectSimWS();
    } else {
      disconnectSimWS();
    }
  });

  // Quick symbol presets from URL
  var params = new URLSearchParams(window.location.search);
  if (params.get("symbol")) {
    $symbol.value = params.get("symbol");
    if (params.get("market")) $market.value = params.get("market");
  }

  // ══════════════════════════════════════════════════════════════════
  // FAZ 23: Journal prompt (preserved) — FAZ 64B: addEventListener pattern
  // ══════════════════════════════════════════════════════════════════
  function showJournalPrompt(pos) {
    var old = document.getElementById("sim-journal-prompt");
    if (old) old.remove();

    var pnl = pos.pnl_abs != null ? pos.pnl_abs : 0;
    var cls = pnl >= 0 ? "positive" : "negative";
    var sign = pnl >= 0 ? "+$" : "-$";
    var pnlStr = sign + Math.abs(pnl).toFixed(2);

    var div = document.createElement("div");
    div.id = "sim-journal-prompt";
    div.className = "sim-journal-prompt";
    div.innerHTML =
      '<div class="sim-journal-prompt-inner">' +
        '<span class="sim-journal-prompt-text">' +
          pos.symbol + ' kapatıldı: <strong class="' + cls + '">' + pnlStr + '</strong>' +
        '</span>' +
        '<button class="sim-btn-journal" id="sim-journal-add-btn">📓 Günlüğe Ekle</button>' +
        '<button class="sim-btn-journal-dismiss" id="sim-journal-dismiss-btn">✕</button>' +
      '</div>';

    $tradeMsg.parentElement.insertBefore(div, $tradeMsg.nextSibling);

    // FAZ 64B: Use addEventListener instead of inline onclick for reliable binding
    var addBtn = document.getElementById("sim-journal-add-btn");
    if (addBtn) {
      addBtn.addEventListener("click", function() {
        addToJournal(pos);
      });
    }
    var dismissBtn = document.getElementById("sim-journal-dismiss-btn");
    if (dismissBtn) {
      dismissBtn.addEventListener("click", function() {
        div.remove();
      });
    }

    setTimeout(function() { if (div.parentElement) div.remove(); }, 30000);
  }

  function addToJournal(pos) {
    var pnl = pos.pnl_abs != null ? pos.pnl_abs : 0;
    fetch("/api/journal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: pos.symbol || "",
        market: pos.market || "crypto",
        side: pos.side || "buy",
        entry_price: pos.entry_price || 0,
        exit_price: pos.current_price || pos.exit_price || 0,
        quantity: pos.quantity || 0,
        pnl: pnl,
        emotion: "neutral",
        notes: "Simülatörden aktarıldı",
        sim_position_id: String(pos.id || "")
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var prompt = document.getElementById("sim-journal-prompt");
      if (prompt) prompt.remove();
      showToast(d.ok ? "İşlem günlüğe eklendi ✅" : ("Günlüğe eklenemedi: " + (d.error || "")), d.ok ? "success" : "error");
    })
    .catch(function(err) { showToast("Günlük hatası: " + err.message, "error"); });
  }

  // ══════════════════════════════════════════════════════════════════
  // CHECK PENDING ORDERS
  // ══════════════════════════════════════════════════════════════════
  async function checkPendingOrders() {
    var data = await api("/check-orders", { method: "POST" });
    if (data.ok && data.filled_count > 0) {
      data.filled.forEach(function(o) {
        showToast("Emir gerçekleşti: " + o.symbol + " @ " + fmtPrice(o.filled_price), "success");
      });
      refreshAll();
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // REFRESH ALL
  // ══════════════════════════════════════════════════════════════════
  function refreshAll() {
    loadAccount();
    loadOrders();
    loadOrderBook();
  }

  // ══════════════════════════════════════════════════════════════════
  // INIT
  // ══════════════════════════════════════════════════════════════════

  // FAZ 64: Use server-side rendered price for instant display
  if (window.__SIM_INITIAL_PRICE__ && window.__SIM_INITIAL_PRICE__ > 0) {
    livePrice = window.__SIM_INITIAL_PRICE__;
    lastGoodPrice = livePrice;
    _initialPriceLoaded = true;
    $livePrice.textContent = fmtPrice(livePrice);
    $livePrice.classList.add("loaded");
  }

  refreshAll();
  startPriceFetch();
  updateExecuteBtn();

  // FAZ 64C: Ensure account + price are loaded — retry if init missed
  setTimeout(function() {
    if (!accountData) {
      console.log("[Simulator] accountData still null after 2s, retrying");
      loadAccount();
    }
    if (!_initialPriceLoaded && livePrice <= 0) {
      console.log("[Simulator] initial price not loaded after 2s, retrying");
      fetchPrice(true);
    }
  }, 2000);

  // FAZ 63C: Connect WebSocket for real-time crypto prices
  var initMarket = ($market.value || "").toLowerCase();
  if (initMarket === "crypto") {
    connectSimWS();
  }

  // FAZ 64C: Account refresh every 5s (was 15s), order book 20s, check orders 30s
  setInterval(loadAccount, 5000);
  setInterval(loadOrderBook, 20000);
  setInterval(checkPendingOrders, 30000);
})();
