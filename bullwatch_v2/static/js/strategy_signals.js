/* ═══════════════════════════════════════════════════════════════
   Strategy Live Signals — FAZ 28
   Real-time strategy signal monitoring & management
   ═══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let signalWS = null;
  let lwChart = null;
  let candleSeries = null;
  let refreshTimer = null;

  // ── Init ───────────────────────────────────────────────────
  function init() {
    loadActiveStrategies();
    loadSignals();
    loadStats();
    connectWebSocket();

    // Auto-refresh every 15 seconds
    refreshTimer = setInterval(() => {
      loadActiveStrategies();
      loadSignals();
      loadStats();
    }, 15000);
  }

  // ── Load Active Strategies ─────────────────────────────────
  function loadActiveStrategies() {
    fetch("/api/strategy/live/active")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        renderActiveStrategies(d.strategies || []);
      })
      .catch(() => {});
  }

  function renderActiveStrategies(strategies) {
    const grid = $("ss-active-grid");
    const badge = $("ss-active-badge");
    const count = $("ss-active-count");

    if (badge) badge.textContent = strategies.length;
    if (count) count.textContent = strategies.length;

    if (!grid) return;

    if (strategies.length === 0) {
      grid.innerHTML = `
        <div class="ss-empty">
          <div class="ss-empty-icon">⚡</div>
          <div class="ss-empty-text">Henüz aktif strateji yok</div>
          <a href="/strategy-builder" class="ss-empty-link">Strategy Builder'da bir strateji aktifleştirin →</a>
        </div>`;
      return;
    }

    grid.innerHTML = strategies
      .map((s) => {
        const enabled = s.enabled !== false;
        const lastSignal = s.last_signal
          ? `<span class="ss-signal-type ${s.last_signal.type}">${s.last_signal.type}</span>`
          : '<span style="color:#555">—</span>';
        const date = new Date(s.created_at * 1000).toLocaleDateString("tr-TR");

        return `
        <div class="ss-strategy-card ${enabled ? "" : "disabled"}">
          <div class="ss-strategy-header">
            <div class="ss-strategy-name">
              ${enabled ? '<span class="ss-live-dot green" style="margin-right:6px;"></span>' : ""}
              ${esc(s.strategy_name || "Strategy")}
            </div>
            ${lastSignal}
          </div>
          <div class="ss-strategy-meta">
            <span class="ss-strategy-tag">${s.symbol}</span>
            <span class="ss-strategy-tag interval">${s.interval}</span>
            <span class="ss-strategy-tag" style="background:rgba(255,255,255,0.05);color:#888;">${s.market}</span>
          </div>
          <div class="ss-strategy-stats">
            <span>📊 ${s.signal_count || 0} sinyal</span>
            <span>📅 ${date}</span>
          </div>
          <div class="ss-strategy-actions">
            <button class="ss-btn-sm toggle ${enabled ? "active" : ""}"
              onclick="SS.toggleStrategy('${s.id}')">
              ${enabled ? "✅ Aktif" : "⏸️ Durduruldu"}
            </button>
            <button class="ss-btn-sm danger" onclick="SS.removeStrategy('${s.id}')">
              🗑 Kaldır
            </button>
          </div>
        </div>`;
      })
      .join("");
  }

  // ── Load Signals ───────────────────────────────────────────
  function loadSignals() {
    fetch("/api/strategy/live/signals?limit=50")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        const signals = d.signals || [];
        renderSignals(signals);
        const badge = $("ss-signal-badge");
        const count = $("ss-signal-count");
        if (badge) badge.textContent = d.count || 0;
        if (count) count.textContent = d.count || 0;

        // Initialize chart with first signal's symbol/interval if chart not yet created
        if (!lwChart && signals.length > 0) {
          const first = signals[0];
          initChart(first.symbol, first.interval, signals);
        }
      })
      .catch(() => {});
  }

  function renderSignals(signals) {
    const list = $("ss-signals-list");
    if (!list) return;

    if (signals.length === 0) {
      list.innerHTML = `
        <div class="ss-empty">
          <div class="ss-empty-icon">📡</div>
          <div class="ss-empty-text">Henüz sinyal üretilmedi</div>
          <div style="font-size:12px;color:#444;">Stratejiler aktif olduğunda burada sinyaller görünecek</div>
        </div>`;
      return;
    }

    list.innerHTML = signals
      .map((s) => {
        const timeStr = formatTime(s.created_at);
        const price = Number(s.price).toLocaleString("en-US", {
          maximumFractionDigits: 4,
        });

        return `
        <div class="ss-signal-item">
          <div class="ss-signal-type ${s.signal_type}">${s.signal_type === "BULLISH" ? "↑ Bullish" : "↓ Bearish"}</div>
          <div class="ss-signal-info">
            <div class="ss-signal-symbol">${s.symbol} <span style="color:#555;font-size:11px;">${s.interval}</span></div>
            <div class="ss-signal-strategy">${esc(s.strategy_name || "Strategy")}</div>
          </div>
          <div class="ss-signal-price">$${price}</div>
          <div class="ss-signal-time">${timeStr}</div>
        </div>`;
      })
      .join("");
  }

  // ── Load Stats ─────────────────────────────────────────────
  function loadStats() {
    fetch("/api/strategy/live/stats")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        const stats = d.stats || {};
        const rooms = $("ss-room-count");
        const status = $("ss-engine-status");
        if (rooms) rooms.textContent = stats.active_rooms || 0;
        if (status) status.textContent = "Motor Çalışıyor";
      })
      .catch(() => {
        const status = $("ss-engine-status");
        if (status) status.textContent = "Bağlantı Hatası";
      });
  }

  // ── WebSocket Connection ───────────────────────────────────
  function connectWebSocket() {
    // Get user_id from page meta or cookie
    const userId = getUserId();
    if (!userId) return;

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws/signals`;

    try {
      signalWS = new WebSocket(url);

      signalWS.onopen = () => {
        signalWS.send(JSON.stringify({ action: "subscribe", user_id: userId }));
      };

      signalWS.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "strategy_signal") {
            onNewSignal(data.signal);
          }
        } catch (e) {}
      };

      signalWS.onclose = () => {
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };

      signalWS.onerror = () => {};

      // Keepalive
      setInterval(() => {
        if (signalWS && signalWS.readyState === WebSocket.OPEN) {
          signalWS.send(JSON.stringify({ action: "ping" }));
        }
      }, 25000);
    } catch (e) {}
  }

  function onNewSignal(signal) {
    // Show toast notification
    showToast(signal);

    // Reload signals list
    loadSignals();
    loadActiveStrategies();

    // Add marker to chart if chart is active
    if (candleSeries && signal.candle_time && signal.price) {
      addSignalMarker(signal);
    }
  }

  function showToast(signal) {
    const toast = document.createElement("div");
    toast.className = `ss-toast ${signal.signal_type === "BULLISH" ? "buy" : "sell"}`;
    const icon = signal.signal_type === "BULLISH" ? "↑" : "↓";
    const price = Number(signal.price).toLocaleString("en-US", {
      maximumFractionDigits: 4,
    });
    toast.innerHTML = `
      <span style="font-size:20px;">${icon}</span>
      <div>
        <div style="font-weight:600;font-size:14px;">${signal.signal_type} ${signal.symbol}</div>
        <div style="font-size:12px;color:#888;">$${price} — ${signal.strategy_name || "Strategy"}</div>
      </div>
    `;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = "ss-slideIn 0.3s ease-out reverse";
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }

  // ── Signal Chart ────────────────────────────────────────────
  let signalMarkers = [];

  function initChart(symbol, interval, signals) {
    const section = $("ss-chart-section");
    const container = $("ss-chart");
    if (!section || !container) return;

    // Fetch candle data
    fetch(`/api/trade_bundle?symbol=${symbol}&interval=${interval}&limit=200`)
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok || !d.data) return;
        const candles = d.data.candles;
        if (!candles || !candles.length) return;

        section.style.display = "block";
        container.innerHTML = "";

        lwChart = LightweightCharts.createChart(container, {
          width: container.clientWidth,
          height: 400,
          layout: { background: { type: "solid", color: "#0a0a0f" }, textColor: "#999" },
          grid: { vertLines: { color: "#1a1a2e" }, horzLines: { color: "#1a1a2e" } },
          crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
          timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#1a1a2e" },
          rightPriceScale: { borderColor: "#1a1a2e" },
        });

        candleSeries = lwChart.addCandlestickSeries({
          upColor: "#00c853", downColor: "#ff1744",
          borderUpColor: "#00c853", borderDownColor: "#ff1744",
          wickUpColor: "#00c853", wickDownColor: "#ff1744",
        });

        candleSeries.setData(candles);

        // Add signal markers from existing signals
        signalMarkers = [];
        if (signals && signals.length) {
          signals.forEach((s) => {
            if (s.candle_time && s.price) {
              signalMarkers.push({
                time: s.candle_time,
                position: s.signal_type === "BULLISH" ? "belowBar" : "aboveBar",
                color: s.signal_type === "BULLISH" ? "#00c853" : "#ff1744",
                shape: s.signal_type === "BULLISH" ? "arrowUp" : "arrowDown",
                text: s.signal_type === "BULLISH" ? "Bullish" : "Bearish",
              });
            }
          });
          signalMarkers.sort((a, b) => a.time - b.time);
          candleSeries.setMarkers(signalMarkers);
        }

        // Responsive resize
        const ro = new ResizeObserver(() => {
          lwChart.applyOptions({ width: container.clientWidth });
        });
        ro.observe(container);
      })
      .catch(() => {});
  }

  function addSignalMarker(signal) {
    signalMarkers.push({
      time: signal.candle_time,
      position: signal.signal_type === "BULLISH" ? "belowBar" : "aboveBar",
      color: signal.signal_type === "BULLISH" ? "#00c853" : "#ff1744",
      shape: signal.signal_type === "BULLISH" ? "arrowUp" : "arrowDown",
      text: signal.signal_type === "BULLISH" ? "Bullish" : "Bearish",
    });
    signalMarkers.sort((a, b) => a.time - b.time);
    candleSeries.setMarkers(signalMarkers);
  }

  // ── Actions ────────────────────────────────────────────────
  function toggleStrategy(activationId) {
    fetch("/api/strategy/live/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activation_id: activationId }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) loadActiveStrategies();
      })
      .catch(() => {});
  }

  function removeStrategy(activationId) {
    if (!confirm("Bu stratejiyi kaldırmak istediğinize emin misiniz?")) return;

    fetch("/api/strategy/live/remove", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activation_id: activationId }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          loadActiveStrategies();
          loadStats();
        }
      })
      .catch(() => {});
  }

  // ── Helpers ────────────────────────────────────────────────
  function getUserId() {
    // Try to get from a meta tag or make an API call
    const meta = document.querySelector('meta[name="user-id"]');
    if (meta) return meta.content;

    // Fallback: fetch from auth API
    try {
      const xhr = new XMLHttpRequest();
      xhr.open("GET", "/api/auth/me", false); // synchronous
      xhr.send();
      if (xhr.status === 200) {
        const data = JSON.parse(xhr.responseText);
        if (data.ok && data.user) return data.user.id;
      }
    } catch (e) {}

    return null;
  }

  function formatTime(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);

    if (diffMin < 1) return "Az önce";
    if (diffMin < 60) return `${diffMin}dk önce`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}sa önce`;
    return d.toLocaleDateString("tr-TR") + " " + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Boot ───────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", init);

  // ── Public API ─────────────────────────────────────────────
  window.SS = {
    toggleStrategy,
    removeStrategy,
  };
})();
