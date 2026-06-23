(function () {
  "use strict";

  // ══════════════════════════════════════════════════════════════
  // CONFIG
  // ══════════════════════════════════════════════════════════════
  const COLORS = [
    "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    "#e879f9", "#fbbf24", "#34d399", "#fb7185",
  ];

  const MARKET_LABELS = {
    crypto: "Kripto",
    stocks: "Hisse (US)",
    bist: "BIST",
    forex: "Forex",
    commodities: "Emtia",
  };

  // ══════════════════════════════════════════════════════════════
  // DOM CACHE
  // ══════════════════════════════════════════════════════════════
  const $ = (s) => document.querySelector(s);
  const dom = {
    authGate: $("#pf-auth-gate"),
    main: $("#pf-main"),
    totalValue: $("#pf-total-value"),
    totalCost: $("#pf-total-cost"),
    totalPnl: $("#pf-total-pnl"),
    totalPnlPct: $("#pf-total-pnl-pct"),
    assetCount: $("#pf-asset-count"),
    marketInfo: $("#pf-market-info"),
    riskScore: $("#pf-risk-score"),
    riskLabel: $("#pf-risk-label"),
    tbody: $("#pf-asset-tbody"),
    addBtn: $("#pf-add-btn"),
    addSymbol: $("#pf-add-symbol"),
    addMarket: $("#pf-add-market"),
    addAmount: $("#pf-add-amount"),
    addPrice: $("#pf-add-price"),
    refreshBtn: $("#pf-refresh-btn"),
    aiBtn: $("#pf-ai-btn"),
    aiContent: $("#pf-ai-content"),
    aiAskRow: $("#pf-ai-ask-row"),
    aiQuestion: $("#pf-ai-question"),
    aiAskBtn: $("#pf-ai-ask-btn"),
    allocChart: $("#pf-alloc-chart"),
    riskGauge: $("#pf-risk-gauge"),
    allocLegend: $("#pf-alloc-legend"),
    gaugeLabel: $("#pf-gauge-label"),
    riskVol: $("#pf-risk-vol"),
    riskConc: $("#pf-risk-conc"),
    riskDd: $("#pf-risk-dd"),
    riskDiv: $("#pf-risk-div"),
  };

  // ══════════════════════════════════════════════════════════════
  // HELPERS
  // ══════════════════════════════════════════════════════════════
  function fmt(v, decimals) {
    if (v == null || isNaN(v)) return "—";
    const d = decimals != null ? decimals : (Math.abs(v) < 1 ? 4 : 2);
    return v.toLocaleString("en-US", {
      minimumFractionDigits: d,
      maximumFractionDigits: d,
    });
  }

  function fmtUSD(v) {
    if (v == null || isNaN(v)) return "$0.00";
    return "$" + fmt(v, 2);
  }

  function fmtPct(v) {
    if (v == null || isNaN(v)) return "0.00%";
    return (v >= 0 ? "+" : "") + fmt(v, 2) + "%";
  }

  async function jget(url) {
    const r = await fetch(url);
    return r.json();
  }

  async function jpost(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  async function jdelete(url, body) {
    const r = await fetch(url, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  // ══════════════════════════════════════════════════════════════
  // AUTH CHECK
  // ══════════════════════════════════════════════════════════════
  async function checkAuth() {
    try {
      const r = await jget("/api/auth/me");
      if (r.ok && r.user) {
        dom.authGate.style.display = "none";
        dom.main.style.display = "";
        return true;
      }
    } catch (e) {}
    // Not authenticated — keep main visible, hide auth gate
    dom.authGate.style.display = "none";
    dom.main.style.display = "";
    return false;
  }

  // ══════════════════════════════════════════════════════════════
  // LOAD PORTFOLIO
  // ══════════════════════════════════════════════════════════════
  let _summaryData = null;
  let _riskData = null;

  async function loadPortfolio() {
    try {
      const [summaryRes, riskRes] = await Promise.all([
        jget("/api/portfolio/summary"),
        jget("/api/portfolio/risk"),
      ]);

      if (summaryRes.ok) {
        _summaryData = summaryRes.data;
        renderSummaryCards(_summaryData);
        renderAssetTable(_summaryData.assets || []);
        renderAllocationChart(_summaryData.allocation || {});
      } else {
        // FAZ 64B — fallback: show demo portfolio data
        await loadDemoFallback();
      }

      if (riskRes.ok) {
        _riskData = riskRes.data;
        renderRiskScore(_riskData);
        renderRiskGauge(_riskData.risk_score || 0);
      }

      // Enable AI button if there are assets
      const hasAssets = (_summaryData && _summaryData.asset_count > 0);
      if (dom.aiBtn) dom.aiBtn.disabled = !hasAssets;
      if (hasAssets && dom.aiAskRow) {
        dom.aiAskRow.style.display = "";
      }
    } catch (e) {
      console.error("Portfolio load error:", e);
      // FAZ 64B — fallback on network error
      await loadDemoFallback();
    }
  }

  async function loadDemoFallback() {
    try {
      const r = await jget("/api/demo/portfolio");
      if (r.ok && r.assets && r.assets.length) {
        const assets = r.assets;
        let totalValue = 0, totalCost = 0;
        const enriched = assets.map(a => {
          const cost = a.amount * a.entry_price;
          const value = a.amount * (a.current_price || a.entry_price);
          const pnl = value - cost;
          const pnl_pct = cost > 0 ? (pnl / cost * 100) : 0;
          totalValue += value;
          totalCost += cost;
          return { ...a, cost, value, pnl, pnl_pct };
        });
        const totalPnl = totalValue - totalCost;
        const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost * 100) : 0;
        const alloc = {};
        enriched.forEach(a => { alloc[a.symbol] = totalValue > 0 ? (a.value / totalValue * 100) : 0; });

        _summaryData = {
          total_value: totalValue, total_cost: totalCost,
          total_pnl: totalPnl, total_pnl_pct: totalPnlPct,
          asset_count: enriched.length, assets: enriched, allocation: alloc,
          market_breakdown: {}, demo: true,
        };
        renderSummaryCards(_summaryData);
        renderAssetTable(enriched);
        renderAllocationChart(alloc);
      }
    } catch (e2) {
      console.error("Demo fallback error:", e2);
    }
  }

  // ══════════════════════════════════════════════════════════════
  // RENDER SUMMARY CARDS
  // ══════════════════════════════════════════════════════════════
  function renderSummaryCards(data) {
    dom.totalValue.textContent = fmtUSD(data.total_value);
    dom.totalCost.textContent = "Maliyet: " + fmtUSD(data.total_cost);

    dom.totalPnl.textContent = fmtUSD(data.total_pnl);
    dom.totalPnlPct.textContent = fmtPct(data.total_pnl_pct);

    const pnlCard = dom.totalPnl.closest(".pf-card");
    pnlCard.classList.remove("pf-positive", "pf-negative");
    pnlCard.classList.add(data.total_pnl >= 0 ? "pf-positive" : "pf-negative");

    dom.assetCount.textContent = data.asset_count || 0;

    // Market breakdown info
    const mb = data.market_breakdown || {};
    const mkts = Object.keys(mb).map((k) => MARKET_LABELS[k] || k);
    dom.marketInfo.textContent = mkts.length ? mkts.join(", ") : "—";
  }

  // ══════════════════════════════════════════════════════════════
  // RENDER RISK SCORE
  // ══════════════════════════════════════════════════════════════
  function renderRiskScore(data) {
    dom.riskScore.textContent = Math.round(data.risk_score || 0);
    dom.riskLabel.textContent = data.risk_label_tr || "—";

    const card = dom.riskScore.closest(".pf-card");
    card.classList.remove("pf-risk-low", "pf-risk-mid", "pf-risk-high", "pf-risk-extreme");
    const s = data.risk_score || 0;
    if (s < 30) card.classList.add("pf-risk-low");
    else if (s < 60) card.classList.add("pf-risk-mid");
    else if (s < 80) card.classList.add("pf-risk-high");
    else card.classList.add("pf-risk-extreme");

    dom.riskVol.textContent = data.volatility != null ? (data.volatility * 100).toFixed(1) + "%" : "—";
    dom.riskConc.textContent = data.concentration_risk != null ? data.concentration_risk.toFixed(0) + "/100" : "—";
    dom.riskDd.textContent = data.drawdown != null ? data.drawdown.toFixed(1) + "%" : "—";
    dom.riskDiv.textContent = data.diversification_score != null ? data.diversification_score.toFixed(0) + "/100" : "—";
  }

  // ══════════════════════════════════════════════════════════════
  // RENDER ASSET TABLE
  // ══════════════════════════════════════════════════════════════
  function renderAssetTable(assets) {
    if (!assets || !assets.length) {
      dom.tbody.innerHTML =
        '<tr class="pf-empty-row"><td colspan="9">Portföyünüzde henüz varlık bulunmuyor.</td></tr>';
      return;
    }

    dom.tbody.innerHTML = assets
      .map((a) => {
        const pnlClass = a.pnl >= 0 ? "pf-text-green" : "pf-text-red";
        return `<tr>
          <td class="pf-sym-cell"><strong>${esc(a.symbol)}</strong></td>
          <td>${MARKET_LABELS[a.market] || a.market}</td>
          <td class="text-right">${fmt(a.amount)}</td>
          <td class="text-right">${fmtUSD(a.entry_price)}</td>
          <td class="text-right">${fmtUSD(a.current_price)}</td>
          <td class="text-right">${fmtUSD(a.value)}</td>
          <td class="text-right ${pnlClass}">${fmtUSD(a.pnl)}</td>
          <td class="text-right ${pnlClass}">${fmtPct(a.pnl_pct)}</td>
          <td>
            <button class="pf-btn-icon pf-remove-btn" data-symbol="${esc(a.symbol)}" title="Kaldır">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
          </td>
        </tr>`;
      })
      .join("");

    // Remove buttons
    dom.tbody.querySelectorAll(".pf-remove-btn").forEach((btn) => {
      btn.addEventListener("click", () => removeAsset(btn.dataset.symbol));
    });
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // ══════════════════════════════════════════════════════════════
  // ALLOCATION PIE CHART (Pure Canvas)
  // ══════════════════════════════════════════════════════════════
  function renderAllocationChart(allocation) {
    const canvas = dom.allocChart;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2;
    const cy = H / 2;
    const R = Math.min(cx, cy) - 10;

    ctx.clearRect(0, 0, W, H);

    const entries = Object.entries(allocation).filter(([, v]) => v > 0);
    if (!entries.length) {
      ctx.fillStyle = "#374151";
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#6b7280";
      ctx.font = "14px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Veri yok", cx, cy + 5);
      dom.allocLegend.innerHTML = "";
      return;
    }

    let startAngle = -Math.PI / 2;
    entries.forEach(([sym, pct], i) => {
      const slice = (pct / 100) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, R, startAngle, startAngle + slice);
      ctx.closePath();
      ctx.fillStyle = COLORS[i % COLORS.length];
      ctx.fill();
      startAngle += slice;
    });

    // Inner circle for donut effect
    ctx.beginPath();
    ctx.arc(cx, cy, R * 0.55, 0, Math.PI * 2);
    ctx.fillStyle = "#0f1419";
    ctx.fill();

    // Center text
    ctx.fillStyle = "#e5e7eb";
    ctx.font = "bold 16px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(entries.length + " Varlık", cx, cy + 5);

    // Legend
    dom.allocLegend.innerHTML = entries
      .map(
        ([sym, pct], i) =>
          `<div class="pf-legend-item">
            <span class="pf-legend-dot" style="background:${COLORS[i % COLORS.length]}"></span>
            <span class="pf-legend-sym">${esc(sym)}</span>
            <span class="pf-legend-pct">${pct.toFixed(1)}%</span>
          </div>`
      )
      .join("");
  }

  // ══════════════════════════════════════════════════════════════
  // RISK GAUGE (Pure Canvas)
  // ══════════════════════════════════════════════════════════════
  function renderRiskGauge(score) {
    const canvas = dom.riskGauge;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;
    const cx = W / 2;
    const cy = H - 20;
    const R = Math.min(cx, cy) - 15;

    ctx.clearRect(0, 0, W, H);

    // Background arc
    const startA = Math.PI;
    const endA = 2 * Math.PI;

    // Color segments
    const segments = [
      { from: 0, to: 0.2, color: "#10b981" },
      { from: 0.2, to: 0.4, color: "#6ee7b7" },
      { from: 0.4, to: 0.6, color: "#fbbf24" },
      { from: 0.6, to: 0.8, color: "#f97316" },
      { from: 0.8, to: 1.0, color: "#ef4444" },
    ];

    segments.forEach((seg) => {
      const a1 = startA + seg.from * Math.PI;
      const a2 = startA + seg.to * Math.PI;
      ctx.beginPath();
      ctx.arc(cx, cy, R, a1, a2);
      ctx.lineWidth = 20;
      ctx.strokeStyle = seg.color;
      ctx.lineCap = "butt";
      ctx.stroke();
    });

    // Needle
    const normalised = Math.max(0, Math.min(100, score)) / 100;
    const needleAngle = startA + normalised * Math.PI;
    const needleLen = R - 25;

    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(
      cx + Math.cos(needleAngle) * needleLen,
      cy + Math.sin(needleAngle) * needleLen
    );
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#e5e7eb";
    ctx.lineCap = "round";
    ctx.stroke();

    // Center dot
    ctx.beginPath();
    ctx.arc(cx, cy, 6, 0, Math.PI * 2);
    ctx.fillStyle = "#e5e7eb";
    ctx.fill();

    // Score text
    dom.gaugeLabel.textContent = Math.round(score) + " / 100";
  }

  // ══════════════════════════════════════════════════════════════
  // ADD ASSET
  // ══════════════════════════════════════════════════════════════
  async function addAsset() {
    const symbol = dom.addSymbol.value.trim().toUpperCase();
    const market = dom.addMarket.value;
    const amount = parseFloat(dom.addAmount.value);
    const entry_price = parseFloat(dom.addPrice.value);

    if (!symbol) return alert("Sembol girin");
    if (!amount || amount <= 0) return alert("Geçerli miktar girin");
    if (!entry_price || entry_price <= 0) return alert("Geçerli giriş fiyatı girin");

    dom.addBtn.disabled = true;
    dom.addBtn.textContent = "Ekleniyor...";

    try {
      const r = await jpost("/api/portfolio/add", { symbol, market, amount, entry_price });
      if (r.ok) {
        dom.addSymbol.value = "";
        dom.addAmount.value = "";
        dom.addPrice.value = "";
        await loadPortfolio();
      } else {
        alert(r.error || "Hata oluştu");
      }
    } catch (e) {
      alert("Bağlantı hatası");
    } finally {
      dom.addBtn.disabled = false;
      dom.addBtn.innerHTML =
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15"/></svg> Ekle';
    }
  }

  // ══════════════════════════════════════════════════════════════
  // REMOVE ASSET
  // ══════════════════════════════════════════════════════════════
  async function removeAsset(symbol) {
    if (!confirm(symbol + " varlığını portföyden kaldırmak istiyor musunuz?")) return;
    try {
      const r = await jdelete("/api/portfolio/remove", { symbol });
      if (r.ok) {
        await loadPortfolio();
      } else {
        alert(r.error || "Kaldırma hatası");
      }
    } catch (e) {
      alert("Bağlantı hatası");
    }
  }

  // ══════════════════════════════════════════════════════════════
  // AI INSIGHT
  // ══════════════════════════════════════════════════════════════
  async function loadAIInsight() {
    dom.aiBtn.disabled = true;
    dom.aiBtn.textContent = "Analiz ediliyor...";
    dom.aiContent.innerHTML = '<div class="pf-ai-loading"><div class="pf-spinner"></div> AI analiz yapılıyor...</div>';

    try {
      const r = await jget("/api/portfolio/ai");
      if (r.ok && r.data) {
        renderAIInsight(r.data);
      } else {
        dom.aiContent.innerHTML = '<div class="pf-ai-error">AI analiz yüklenemedi.</div>';
      }
    } catch (e) {
      dom.aiContent.innerHTML = '<div class="pf-ai-error">AI bağlantı hatası.</div>';
    } finally {
      dom.aiBtn.disabled = false;
      dom.aiBtn.innerHTML =
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg> AI Analiz Başlat';
    }
  }

  async function askAI() {
    const q = dom.aiQuestion.value.trim();
    if (!q) return;

    dom.aiAskBtn.disabled = true;
    dom.aiAskBtn.textContent = "...";
    dom.aiContent.innerHTML = '<div class="pf-ai-loading"><div class="pf-spinner"></div> AI yanıt üretiliyor...</div>';

    try {
      const r = await jpost("/api/portfolio/ai/ask", { question: q });
      if (r.ok && r.data) {
        renderAIInsight(r.data);
        dom.aiQuestion.value = "";
      } else {
        dom.aiContent.innerHTML = '<div class="pf-ai-error">AI yanıt üretilemedi.</div>';
      }
    } catch (e) {
      dom.aiContent.innerHTML = '<div class="pf-ai-error">AI bağlantı hatası.</div>';
    } finally {
      dom.aiAskBtn.disabled = false;
      dom.aiAskBtn.textContent = "Sor";
    }
  }

  function renderAIInsight(data) {
    const sections = [];

    if (data.portfolio_insight) {
      sections.push(
        `<div class="pf-ai-section">
          <div class="pf-ai-section-title">📊 Portföy Özeti</div>
          <p>${esc(data.portfolio_insight)}</p>
        </div>`
      );
    }
    if (data.risk_warning) {
      sections.push(
        `<div class="pf-ai-section pf-ai-warning">
          <div class="pf-ai-section-title">⚠️ Risk Değerlendirmesi</div>
          <p>${esc(data.risk_warning)}</p>
        </div>`
      );
    }
    if (data.diversification_suggestion) {
      sections.push(
        `<div class="pf-ai-section">
          <div class="pf-ai-section-title">🎯 Dağılım Analizi</div>
          <p>${esc(data.diversification_suggestion)}</p>
        </div>`
      );
    }
    if (data.market_exposure) {
      sections.push(
        `<div class="pf-ai-section">
          <div class="pf-ai-section-title">🌍 Piyasa Maruziyeti</div>
          <p>${esc(data.market_exposure)}</p>
        </div>`
      );
    }

    if (data.answer && !sections.length) {
      sections.push(
        `<div class="pf-ai-section"><p>${esc(data.answer)}</p></div>`
      );
    }

    sections.push(
      `<div class="pf-ai-disclaimer">⚠️ Bu bir yatırım tavsiyesi değildir.</div>`
    );

    if (data.llm_used === false) {
      sections.push(
        `<div class="pf-ai-note">ℹ️ AI modeli kullanılamadı, kural tabanlı analiz sunuldu.</div>`
      );
    }

    dom.aiContent.innerHTML = sections.join("");
  }

  // ══════════════════════════════════════════════════════════════
  // EVENTS
  // ══════════════════════════════════════════════════════════════
  function bindEvents() {
    dom.addBtn.addEventListener("click", addAsset);
    dom.refreshBtn.addEventListener("click", loadPortfolio);
    dom.aiBtn.addEventListener("click", loadAIInsight);
    dom.aiAskBtn.addEventListener("click", askAI);

    dom.aiQuestion.addEventListener("keydown", (e) => {
      if (e.key === "Enter") askAI();
    });

    // Enter key on form fields
    [dom.addSymbol, dom.addAmount, dom.addPrice].forEach((el) => {
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter") addAsset();
      });
    });
  }

  // ══════════════════════════════════════════════════════════════
  // INIT
  // ══════════════════════════════════════════════════════════════
  async function init() {
    try {
      bindEvents();
    } catch (_) {}
    try {
      const authed = await checkAuth();
      if (authed) {
        await loadPortfolio();
      } else {
        // Not logged in — show main with demo data instead of blank page
        dom.authGate.style.display = "none";
        dom.main.style.display = "";
        await loadDemoFallback();
      }
    } catch (_) {
      // Guarantee visibility even if something throws
      dom.authGate.style.display = "none";
      dom.main.style.display = "";
      try { await loadDemoFallback(); } catch (_e) {}
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
