/* ═══════════════════════════════════════════════════════════════
   Marketplace Detail — FAZ 29
   Strategy detail view with metrics, chart, signals
   ═══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  let strategyData = null;
  let lwChart = null;

  function init() {
    const slug = document.querySelector('meta[name="strategy-slug"]')?.content;
    if (!slug) return;
    loadStrategy(slug);
  }

  function loadStrategy(slug) {
    fetch("/api/marketplace/strategy/" + encodeURIComponent(slug))
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok || !d.strategy) {
          document.getElementById("md-content").innerHTML =
            '<div class="md-loading">Strateji bulunamadı</div>';
          return;
        }
        strategyData = d.strategy;
        renderDetail(d.strategy);
      })
      .catch(() => {
        document.getElementById("md-content").innerHTML =
          '<div class="md-loading">Yükleme hatası</div>';
      });
  }

  function renderDetail(s) {
    const container = document.getElementById("md-content");
    const m = s.metrics || {};
    const tags = s.tags || [];
    const signals = s.recent_signals || [];

    const winRate = m.win_rate != null ? m.win_rate.toFixed(1) + "%" : "—";
    const profitFactor = m.profit_factor != null ? m.profit_factor.toFixed(2) : "—";
    const netProfit = m.net_profit != null ? m.net_profit.toFixed(2) + "%" : "—";
    const drawdown = m.max_drawdown != null ? m.max_drawdown.toFixed(1) + "%" : "—";
    const avgTrade = m.avg_trade != null ? m.avg_trade.toFixed(2) + "%" : "—";
    const followers = m.followers_count || 0;
    const signalCount = m.live_signal_count || 0;
    const totalBt = m.total_backtests || 0;

    const winClass = (m.win_rate || 0) >= 50 ? "green" : "red";
    const profitClass = (m.net_profit || 0) >= 0 ? "green" : "red";
    const ddClass = (m.max_drawdown || 0) > 20 ? "red" : "amber";

    // Risk badge
    const riskMap = { low: "Düşük Risk", medium: "Orta Risk", high: "Yüksek Risk" };
    const riskBadge = '<span class="md-tag risk">' + (riskMap[s.risk_level] || "Orta Risk") + "</span>";

    // Follow button
    let followBtn = "";
    if (s.is_owner) {
      followBtn = '<button class="md-btn md-btn-copy" disabled>Kendi Stratejiniz</button>';
    } else if (s.is_following) {
      followBtn = '<button class="md-btn md-btn-follow following" onclick="MD.toggleFollow()" id="md-follow-btn">⭐ Takip Ediliyor</button>';
    } else {
      followBtn = '<button class="md-btn md-btn-follow" onclick="MD.toggleFollow()" id="md-follow-btn">⭐ Takip Et</button>';
    }

    // Code highlight
    const codeHTML = highlightCode(s.strategy_code || "");

    let html = `
      <div class="md-header">
        <a href="/marketplace" class="md-back">← Marketplace'e Dön</a>
        <div class="md-title">${esc(s.title)}</div>
        <div class="md-creator">@${esc(s.publisher_username || "anonim")} tarafından yayınlandı</div>
        <div class="md-desc">${esc(s.description || "")}</div>
        <div class="md-tags">
          <span class="md-tag market">${esc(s.market)}</span>
          <span class="md-tag">${esc(s.default_symbol)}</span>
          <span class="md-tag">${esc(s.default_interval)}</span>
          ${riskBadge}
          ${tags.map((t) => '<span class="md-tag">' + esc(t) + "</span>").join("")}
        </div>
      </div>

      <div class="md-actions">
        ${followBtn}
        <button class="md-btn md-btn-copy" onclick="MD.copyCode()">📋 Kodu Kopyala</button>
        <button class="md-btn md-btn-live" onclick="MD.activateLive()">⚡ Canlı Aktif Et</button>
      </div>

      <div class="md-metrics">
        <div class="md-metric"><div class="md-metric-value ${winClass}">${winRate}</div><div class="md-metric-label">Win Rate</div></div>
        <div class="md-metric"><div class="md-metric-value">${profitFactor}</div><div class="md-metric-label">Profit Factor</div></div>
        <div class="md-metric"><div class="md-metric-value ${profitClass}">${netProfit}</div><div class="md-metric-label">Net Kâr</div></div>
        <div class="md-metric"><div class="md-metric-value ${ddClass}">${drawdown}</div><div class="md-metric-label">Max Drawdown</div></div>
        <div class="md-metric"><div class="md-metric-value">${avgTrade}</div><div class="md-metric-label">Ort. İşlem</div></div>
        <div class="md-metric"><div class="md-metric-value amber">${followers}</div><div class="md-metric-label">Takipçi</div></div>
        <div class="md-metric"><div class="md-metric-value amber">${signalCount}</div><div class="md-metric-label">Canlı Sinyal</div></div>
        <div class="md-metric"><div class="md-metric-value">${totalBt}</div><div class="md-metric-label">Backtest</div></div>
      </div>

      <div class="md-chart-section">
        <div class="md-section-title">📊 Equity Curve</div>
        <div class="md-chart-container" id="md-chart"></div>
      </div>

      <div class="md-code-section">
        <div class="md-code-title">📝 Strateji Kodu</div>
        <div class="md-code-block">${codeHTML}</div>
      </div>

      <div class="md-signals-section">
        <div class="md-section-title">⚡ Son Canlı Sinyaller</div>
        <div id="md-signals-list">
          ${signals.length === 0
            ? '<div class="md-empty">Henüz canlı sinyal yok</div>'
            : signals.map(renderSignal).join("")}
        </div>
      </div>
    `;

    container.innerHTML = html;

    // Render equity curve chart
    setTimeout(() => renderEquityChart(s), 100);
  }

  function renderSignal(sig) {
    const price = Number(sig.price).toLocaleString("en-US", { maximumFractionDigits: 4 });
    const time = sig.created_at_iso ? new Date(sig.created_at_iso).toLocaleString("tr-TR") : "—";
    return `
      <div class="md-signal-item">
        <div class="md-signal-type ${sig.signal_type}">${sig.signal_type === "BULLISH" ? "↑ Bullish" : "↓ Bearish"}</div>
        <div class="md-signal-info">
          <div class="md-signal-symbol">${sig.symbol} <span style="color:#555;font-size:11px;">${sig.interval}</span></div>
          <div class="md-signal-time">${time}</div>
        </div>
        <div class="md-signal-price">$${price}</div>
      </div>`;
  }

  function renderEquityChart(strat) {
    const container = document.getElementById("md-chart");
    if (!container || typeof LightweightCharts === "undefined") return;

    // Run backtest to get equity curve
    fetch("/api/strategy/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: strat.strategy_code,
        symbol: strat.default_symbol,
        market: strat.market,
        interval: strat.default_interval,
        limit: 500,
      }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok || !d.equity_curve) {
          container.innerHTML = '<div class="md-empty">Grafik yüklenemedi</div>';
          return;
        }

        const equity = d.equity_curve;
        lwChart = LightweightCharts.createChart(container, {
          width: container.clientWidth,
          height: 340,
          layout: { background: { type: "solid", color: "#0a0a0f" }, textColor: "#999" },
          grid: { vertLines: { color: "#1a1a2e" }, horzLines: { color: "#1a1a2e" } },
          timeScale: { timeVisible: true, borderColor: "#1a1a2e" },
          rightPriceScale: { borderColor: "#1a1a2e" },
        });

        const areaSeries = lwChart.addAreaSeries({
          lineColor: "#f59e0b",
          topColor: "rgba(245,158,11,.3)",
          bottomColor: "rgba(245,158,11,.02)",
          lineWidth: 2,
        });

        // equity_curve is [{time, value}] or [{x,y}]
        const data = equity.map((p) => ({
          time: p.time || p.x,
          value: p.value != null ? p.value : p.y,
        }));
        areaSeries.setData(data);

        // Also update metrics from fresh backtest
        if (d.metrics) {
          updateMetricsFromBacktest(d.metrics, strat);
        }

        const ro = new ResizeObserver(() => {
          lwChart.applyOptions({ width: container.clientWidth });
        });
        ro.observe(container);
      })
      .catch(() => {
        container.innerHTML = '<div class="md-empty">Grafik yüklenemedi</div>';
      });
  }

  function updateMetricsFromBacktest(metrics, strat) {
    // Update marketplace metrics with fresh backtest data
    fetch("/api/marketplace/strategy/" + encodeURIComponent(strat.slug))
      .catch(() => {});
  }

  // ── Actions ────────────────────────────────────────────────
  function toggleFollow() {
    if (!strategyData) return;
    const btn = document.getElementById("md-follow-btn");
    const isFollowing = strategyData.is_following;
    const endpoint = isFollowing ? "/api/marketplace/unfollow" : "/api/marketplace/follow";

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pub_id: strategyData.id }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          strategyData.is_following = !isFollowing;
          if (btn) {
            if (strategyData.is_following) {
              btn.className = "md-btn md-btn-follow following";
              btn.textContent = "⭐ Takip Ediliyor";
            } else {
              btn.className = "md-btn md-btn-follow";
              btn.textContent = "⭐ Takip Et";
            }
          }
        }
      })
      .catch(() => {});
  }

  function copyCode() {
    if (!strategyData || !strategyData.strategy_code) return;
    navigator.clipboard.writeText(strategyData.strategy_code).then(() => {
      alert("Strateji kodu kopyalandı!");
    }).catch(() => {
      // Fallback
      const ta = document.createElement("textarea");
      ta.value = strategyData.strategy_code;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      alert("Strateji kodu kopyalandı!");
    });
  }

  function activateLive() {
    if (!strategyData) return;
    const symbol = prompt("Hangi sembolde çalıştırmak istiyorsunuz?", strategyData.default_symbol);
    if (!symbol) return;

    fetch("/api/strategy/live/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: strategyData.strategy_code,
        symbol: symbol.toUpperCase(),
        market: strategyData.market,
        interval: strategyData.default_interval,
        name: strategyData.title,
        strategy_id: strategyData.id,
      }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          alert("Strateji canlı olarak aktif edildi! Sinyaller sayfasından takip edebilirsiniz.");
        } else {
          alert("Hata: " + (d.error || "Bilinmeyen hata"));
        }
      })
      .catch(() => alert("Bağlantı hatası"));
  }

  // ── Helpers ────────────────────────────────────────────────
  function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function highlightCode(code) {
    return esc(code)
      .replace(/\b(strategy|entry|exit)\b/g, '<span class="kw">$1</span>')
      .replace(/\b(above|below|crosses_above|crosses_below)\b/g, '<span class="kw">$1</span>')
      .replace(/\b(RSI\d*|EMA\d*|SMA\d*|MACD|MACD_SIGNAL|BB_UPPER|BB_LOWER|ATR\d*|VOLUME|CLOSE|HIGH|LOW|OPEN)\b/g, '<span class="ind">$1</span>')
      .replace(/"([^"]*)"/g, '<span class="str">"$1"</span>');
  }

  // ── Boot ───────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", init);

  window.MD = { toggleFollow, copyCode, activateLive };
})();
