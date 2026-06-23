/**
 * ZKR Analiz AI Copilot — Frontend Module (FAZ 21)
 *
 * Shared copilot UI logic for trade, discover, and screener pages.
 * Handles: input, fetch, loading state, answer render, key/risk points,
 * suggested alerts.
 */

/* global document, window, fetch */

const BullCopilot = (function () {
  "use strict";

  // ── Constants ─────────────────────────────────────────────────
  const API = {
    ask:      "/api/copilot/ask",
    symbol:   "/api/copilot/symbol",
    discover: "/api/copilot/discover",
    screener: "/api/copilot/screener",
  };

  const TIMEOUT_MS = 90000; // 90 seconds

  // ── State ─────────────────────────────────────────────────────
  let _loading = false;

  // ══════════════════════════════════════════════════════════════
  // 1) API CALLS
  // ══════════════════════════════════════════════════════════════

  async function askSymbol(symbol, market, timeframe, question) {
    return _post(API.symbol, { symbol, market, timeframe, question });
  }

  async function askDiscover(question) {
    return _post(API.discover, { question });
  }

  async function askScreener(market, filters, question) {
    return _post(API.screener, { market, filters, question });
  }

  async function askGeneral(question, opts) {
    const body = { question, ...(opts || {}) };
    return _post(API.ask, body);
  }

  async function _post(url, body) {
    if (_loading) return null;
    _loading = true;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timer);
      const json = await res.json();
      _loading = false;
      return json;
    } catch (err) {
      clearTimeout(timer);
      _loading = false;
      if (err.name === "AbortError") {
        return { ok: false, error: "İstek zaman aşımına uğradı. Tekrar deneyin." };
      }
      return { ok: false, error: err.message || "Bağlantı hatası" };
    }
  }

  // ══════════════════════════════════════════════════════════════
  // 2) RENDER HELPERS
  // ══════════════════════════════════════════════════════════════

  function renderLoading(container) {
    if (!container) return;
    container.innerHTML = `
      <div class="copilot-loading">
        <div class="copilot-skeleton-line w-full"></div>
        <div class="copilot-skeleton-line w-3/4"></div>
        <div class="copilot-skeleton-line w-5/6"></div>
        <div class="copilot-skeleton-line w-2/3"></div>
        <p class="copilot-loading-text">AI analiz ediyor…</p>
      </div>`;
  }

  function renderAnswer(container, data) {
    if (!container || !data) return;

    const answer = data.answer || "";
    const summary = data.summary || "";
    const keyPoints = data.key_points || [];
    const riskPoints = data.risk_points || [];
    const suggestedAlerts = data.suggested_alerts || [];
    const disclaimer = data.disclaimer || "⚠️ Bu bir yatırım tavsiyesi değildir.";

    let html = '<div class="copilot-answer">';

    // Summary
    if (summary) {
      html += `<div class="copilot-summary">${_escapeHtml(_formatMarkdown(summary))}</div>`;
    }

    // Full answer (if different from summary)
    if (answer && answer !== summary) {
      html += `<div class="copilot-detail">${_formatAnswer(answer)}</div>`;
    }

    // Key Points
    if (keyPoints.length > 0) {
      html += '<div class="copilot-section">';
      html += '<h4 class="copilot-section-title">🔑 Önemli Noktalar</h4>';
      html += '<ul class="copilot-list copilot-key-list">';
      keyPoints.forEach(p => {
        html += `<li>${_escapeHtml(p)}</li>`;
      });
      html += "</ul></div>";
    }

    // Risk Points
    if (riskPoints.length > 0) {
      html += '<div class="copilot-section">';
      html += '<h4 class="copilot-section-title">⚠️ Riskler</h4>';
      html += '<ul class="copilot-list copilot-risk-list">';
      riskPoints.forEach(p => {
        html += `<li>${_escapeHtml(p)}</li>`;
      });
      html += "</ul></div>";
    }

    // Suggested Alerts
    if (suggestedAlerts.length > 0) {
      html += '<div class="copilot-section">';
      html += '<h4 class="copilot-section-title">🎯 Önerilen Alarmlar</h4>';
      html += '<div class="copilot-alerts">';
      suggestedAlerts.forEach(a => {
        const cond = _conditionLabel(a.condition_type);
        html += `
          <div class="copilot-alert-card" data-symbol="${_escapeAttr(a.symbol)}"
               data-market="${_escapeAttr(a.market)}"
               data-condition="${_escapeAttr(a.condition_type)}"
               data-value="${a.condition_value}">
            <div class="copilot-alert-info">
              <span class="copilot-alert-symbol">${_escapeHtml(a.symbol)}</span>
              <span class="copilot-alert-cond">${cond} ${a.condition_value}</span>
            </div>
            <div class="copilot-alert-reason">${_escapeHtml(a.reason || "")}</div>
            <button class="copilot-alert-btn" onclick="BullCopilot.createAlertFromSuggestion(this)">
              Alarm Kur
            </button>
          </div>`;
      });
      html += "</div></div>";
    }

    // Disclaimer
    html += `<div class="copilot-disclaimer">${_escapeHtml(disclaimer)}</div>`;
    html += "</div>";

    container.innerHTML = html;
  }

  function renderError(container, msg) {
    if (!container) return;
    container.innerHTML = `
      <div class="copilot-error">
        <p>❌ ${_escapeHtml(msg || "Bir hata oluştu")}</p>
        <p class="copilot-error-hint">Lütfen tekrar deneyin.</p>
      </div>`;
  }

  // ══════════════════════════════════════════════════════════════
  // 3) TRADE PAGE — COPILOT TAB
  // ══════════════════════════════════════════════════════════════

  function initTradeTab() {
    const container = document.getElementById("copilotOutput");
    const input = document.getElementById("copilotInput");
    const sendBtn = document.getElementById("copilotSend");
    const quickBtns = document.querySelectorAll(".copilot-quick-btn");

    if (!container) return;

    function _getTradeContext() {
      const symEl = document.getElementById("chartSymbol");
      const symbol = symEl ? symEl.textContent.trim() : "BTCUSDT";
      // Detect market from active market tab
      const activeTab = document.querySelector(".market-tab.active");
      const market = activeTab ? activeTab.dataset.market : "crypto";
      // Detect timeframe from active tf button
      const activeTf = document.querySelector(".tf-btn.active");
      const timeframe = activeTf ? activeTf.dataset.tf : "15m";
      return { symbol, market, timeframe };
    }

    async function _ask(question) {
      renderLoading(container);
      const ctx = _getTradeContext();
      const resp = await askSymbol(ctx.symbol, ctx.market, ctx.timeframe, question);
      if (resp && resp.ok && resp.data) {
        renderAnswer(container, resp.data);
      } else {
        renderError(container, (resp && resp.error) || "Yanıt alınamadı");
      }
    }

    // Send button
    if (sendBtn) {
      sendBtn.addEventListener("click", () => {
        const q = input ? input.value.trim() : "";
        if (q) { _ask(q); if (input) input.value = ""; }
      });
    }

    // Enter key
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          const q = input.value.trim();
          if (q) { _ask(q); input.value = ""; }
        }
      });
    }

    // Quick prompt buttons
    quickBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const q = btn.dataset.prompt || btn.textContent;
        _ask(q);
      });
    });
  }

  // ══════════════════════════════════════════════════════════════
  // 4) DISCOVER PAGE — AI SUMMARY
  // ══════════════════════════════════════════════════════════════

  function initDiscoverCard() {
    const btn = document.getElementById("discoverAiBtn");
    const container = document.getElementById("discoverAiOutput");
    const quickBtns = document.querySelectorAll(".t-chat-suggest-btn");

    if (!btn || !container) return;

    async function _ask(question) {
      container.style.display = "block";
      renderLoading(container);
      const resp = await askDiscover(question);
      if (resp && resp.ok && resp.data) {
        renderAnswer(container, resp.data);
      } else {
        renderError(container, (resp && resp.error) || "Yanıt alınamadı");
      }
    }

    btn.addEventListener("click", () => {
      _ask("Bugün piyasada ne öne çıkıyor? En önemli gelişmeleri özetle.");
    });

    quickBtns.forEach(qb => {
      qb.addEventListener("click", () => {
        _ask(qb.dataset.prompt || qb.textContent);
      });
    });
  }

  // ══════════════════════════════════════════════════════════════
  // 5) SCREENER PAGE — AI INTERPRET
  // ══════════════════════════════════════════════════════════════

  function initScreenerAI() {
    const container = document.getElementById("screenerAiOutput");
    const quickBtns = document.querySelectorAll(".screener-ai-btn");

    if (!container) return;

    function _getScreenerContext() {
      const activeTab = document.querySelector(".scr-mtab.active");
      const market = activeTab ? activeTab.dataset.market : "crypto";
      // Collect active filters
      const filterCheckboxes = document.querySelectorAll('.scr-fgroup-body input[type="checkbox"]:checked');
      const filters = Array.from(filterCheckboxes).map(cb => cb.value || cb.name);
      return { market, filters };
    }

    async function _ask(question) {
      container.style.display = "block";
      renderLoading(container);
      const ctx = _getScreenerContext();
      const resp = await askScreener(ctx.market, ctx.filters, question);
      if (resp && resp.ok && resp.data) {
        renderAnswer(container, resp.data);
      } else {
        renderError(container, (resp && resp.error) || "Yanıt alınamadı");
      }
    }

    quickBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        _ask(btn.dataset.prompt || btn.textContent);
      });
    });
  }

  // ══════════════════════════════════════════════════════════════
  // 6) ALERT CREATION FROM SUGGESTION
  // ══════════════════════════════════════════════════════════════

  function createAlertFromSuggestion(btnEl) {
    const card = btnEl.closest(".copilot-alert-card");
    if (!card) return;

    const payload = {
      symbol: card.dataset.symbol,
      market: card.dataset.market,
      condition_type: card.dataset.condition,
      condition_value: parseFloat(card.dataset.value),
    };

    fetch("/api/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(r => r.json())
      .then(json => {
        if (json.ok) {
          btnEl.textContent = "✓ Kuruldu";
          btnEl.disabled = true;
          btnEl.classList.add("copilot-alert-btn-done");
        } else {
          btnEl.textContent = "Hata";
          setTimeout(() => { btnEl.textContent = "Alarm Kur"; }, 2000);
        }
      })
      .catch(() => {
        btnEl.textContent = "Hata";
        setTimeout(() => { btnEl.textContent = "Alarm Kur"; }, 2000);
      });
  }

  // ══════════════════════════════════════════════════════════════
  // INTERNAL HELPERS
  // ══════════════════════════════════════════════════════════════

  function _escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  function _escapeAttr(str) {
    return (str || "").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function _conditionLabel(type) {
    const labels = {
      price_above: "Fiyat ≥",
      price_below: "Fiyat ≤",
      rsi_above: "RSI ≥",
      rsi_below: "RSI ≤",
      ema_cross: "EMA Kesişim ≥",
      breakout: "Breakout ≥",
      volume_spike: "Hacim Spike ≥",
    };
    return labels[type] || type;
  }

  function _formatAnswer(text) {
    // Simple markdown-like formatting
    return _escapeHtml(text)
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  function _formatMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, "$1")
      .replace(/\n/g, " ");
  }

  function isLoading() {
    return _loading;
  }

  // ══════════════════════════════════════════════════════════════
  // PUBLIC API
  // ══════════════════════════════════════════════════════════════

  return {
    askSymbol,
    askDiscover,
    askScreener,
    askGeneral,
    renderLoading,
    renderAnswer,
    renderError,
    initTradeTab,
    initDiscoverCard,
    initScreenerAI,
    createAlertFromSuggestion,
    isLoading,
  };
})();

// Auto-init based on page
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("copilotOutput")) BullCopilot.initTradeTab();
  if (document.getElementById("discoverAiOutput")) BullCopilot.initDiscoverCard();
  if (document.getElementById("screenerAiOutput")) BullCopilot.initScreenerAI();
});
