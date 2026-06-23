/* ═══════════════════════════════════════════════════════════════
   Strategy Builder — FAZ 25
   Interactive strategy editor with DSL, backtest & chart
   ═══════════════════════════════════════════════════════════════ */
window.SB = (function () {
  "use strict";

  // ── State ──────────────────────────────────────────────────
  let templates = [];
  let lwChart = null;
  let candleSeries = null;
  let equityChartJS = null;
  let indicatorSeries = {};  // label → LW line series
  let currentResult = null;

  // ── DOM refs ───────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  // ── Init ───────────────────────────────────────────────────
  function init() {
    loadTemplates();
    loadIndicatorChips();
    loadSaved();

    // Auto-parse on code change (debounced)
    let parseTimer = null;
    const codeEl = $("sb-code");
    if (codeEl) {
      codeEl.addEventListener("input", () => {
        clearTimeout(parseTimer);
        parseTimer = setTimeout(() => parseCode(true), 600);
      });
    }
  }

  // ── Templates ──────────────────────────────────────────────
  function loadTemplates() {
    fetch("/api/strategy/templates")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        templates = d.templates || [];
        renderTemplates();
      })
      .catch(() => {});
  }

  function renderTemplates() {
    const grid = $("sb-templates");
    if (!grid) return;
    grid.innerHTML = templates
      .map(
        (t) => `
      <div class="sb-template-card" data-id="${t.id}" onclick="SB.selectTemplate('${t.id}')">
        <div class="sb-template-name">${t.name}</div>
        <div class="sb-template-desc">${t.description}</div>
        <span class="sb-template-cat">${t.category}</span>
      </div>`
      )
      .join("");
  }

  function selectTemplate(id) {
    const t = templates.find((x) => x.id === id);
    if (!t) return;

    // Highlight selected
    document.querySelectorAll(".sb-template-card").forEach((el) => {
      el.classList.toggle("active", el.dataset.id === id);
    });

    // Set code
    const codeEl = $("sb-code");
    if (codeEl) {
      codeEl.value = t.code;
      parseCode(true);
    }
  }

  // ── Indicator Chips ────────────────────────────────────────
  function loadIndicatorChips() {
    fetch("/api/strategy/indicators")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        const chips = $("sb-indicator-chips");
        if (!chips) return;
        chips.innerHTML = (d.indicators || [])
          .map(
            (ind) =>
              `<span class="sb-indicator-chip" title="${ind.description} (${ind.args.join(", ")})" onclick="SB.insertIndicator('${ind.name}')">${ind.name}</span>`
          )
          .join("");
      })
      .catch(() => {});
  }

  function insertIndicator(name) {
    const codeEl = $("sb-code");
    if (!codeEl) return;

    const defaults = {
      EMA: "EMA20",
      SMA: "SMA20",
      RSI: "RSI14",
      MACD: "MACD.line",
      BBANDS: "BBANDS20.upper",
      ATR: "ATR14",
      VWAP: "VWAP20",
      STOCH: "STOCH.k",
    };

    const text = defaults[name] || name;
    const start = codeEl.selectionStart;
    const end = codeEl.selectionEnd;
    const val = codeEl.value;
    codeEl.value = val.substring(0, start) + text + val.substring(end);
    codeEl.selectionStart = codeEl.selectionEnd = start + text.length;
    codeEl.focus();
  }

  // ── Parse ──────────────────────────────────────────────────
  function parseCode(silent) {
    const code = ($("sb-code") || {}).value || "";
    if (!code.trim()) {
      if (!silent) showStatus("Strateji kodu yazın", "error");
      return;
    }

    fetch("/api/strategy/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) {
          showValidation(null, d);
          return;
        }
        showParsedPreview(d.parsed);
        showValidation(d.validation, d);
      })
      .catch((err) => {
        if (!silent) showStatus("Parse hatası: " + err.message, "error");
      });
  }

  function showParsedPreview(parsed) {
    const el = $("sb-parsed-preview");
    if (!el) return;

    let html = "";

    // Name
    if (parsed.name) {
      html += `<div class="pp-name">📊 ${esc(parsed.name)}</div>`;
    }

    // Entry conditions
    if (parsed.entry_conditions && parsed.entry_conditions.length) {
      html += `<div class="pp-label">🟢 Giriş Koşulları</div>`;
      parsed.entry_conditions.forEach((c) => {
        html += `<div class="pp-cond">${formatCondition(c)}</div>`;
      });
    }

    // Exit conditions
    if (parsed.exit_conditions && parsed.exit_conditions.length) {
      html += `<div class="pp-label">🔴 Çıkış Koşulları</div>`;
      parsed.exit_conditions.forEach((c) => {
        html += `<div class="pp-cond exit">${formatCondition(c)}</div>`;
      });
    } else {
      html += `<div class="pp-label">🔴 Çıkış Koşulları</div>`;
      html += `<div class="pp-cond exit" style="opacity:0.5">Giriş koşulunun tersi (otomatik)</div>`;
    }

    // Risk
    const risk = parsed.risk || {};
    if (risk.stop_loss || risk.take_profit) {
      html += `<div class="pp-label">⚡ Risk Yönetimi</div>`;
      html += `<div class="pp-risk">`;
      if (risk.stop_loss)
        html += `<span class="pp-risk-item sl">🛑 Risk Level: ${risk.stop_loss}%</span>`;
      if (risk.take_profit)
        html += `<span class="pp-risk-item tp">🎯 Target Level: ${risk.take_profit}%</span>`;
      html += `</div>`;
    }

    if (!html) {
      html = `<div style="text-align:center;opacity:0.3;padding-top:60px;">
        <div style="font-size:40px;margin-bottom:8px;">📊</div>
        <div>Strateji yazarak başlayın</div>
      </div>`;
    }

    el.innerHTML = html;
  }

  function formatCondition(cond) {
    const ops = {
      crosses_above: "↗ yukarı keser",
      crosses_below: "↘ aşağı keser",
      above: "▲ üstünde",
      below: "▼ altında",
    };
    const left = formatRef(cond.left);
    const right = formatRef(cond.right);
    const op = ops[cond.op] || cond.op;
    return `${left} ${op} ${right}`;
  }

  function formatRef(ref) {
    if (!ref) return "?";
    if (ref.type === "literal") return String(ref.value);
    if (ref.type === "price") return ref.field.toUpperCase();
    if (ref.type === "indicator") {
      let s = ref.name + (ref.period || "");
      if (ref.sub_field) s += "." + ref.sub_field;
      return s;
    }
    return ref.raw || "?";
  }

  function showValidation(validation) {
    const el = $("sb-validation");
    if (!el) return;

    if (!validation) {
      el.style.display = "none";
      return;
    }

    let html = "";
    if (validation.valid) {
      html = `<div class="sb-validation valid">✅ Strateji geçerli — çalıştırılmaya hazır</div>`;
    } else if (validation.errors && validation.errors.length) {
      html = `<div class="sb-validation invalid">❌ Hatalar:<ul>${validation.errors.map((e) => `<li>${esc(e)}</li>`).join("")}</ul></div>`;
    }

    if (validation.warnings && validation.warnings.length) {
      html += `<div class="sb-validation warning" style="margin-top:4px;">⚠️ Uyarılar:<ul>${validation.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>`;
    }

    el.innerHTML = html;
    el.style.display = html ? "block" : "none";
  }

  // ── Run Strategy ───────────────────────────────────────────
  function runStrategy() {
    const code = ($("sb-code") || {}).value || "";
    const symbol = ($("sb-symbol") || {}).value || "BTCUSDT";
    const market = ($("sb-market") || {}).value || "crypto";
    const interval = ($("sb-interval") || {}).value || "1d";
    const limit = parseInt(($("sb-limit") || {}).value || "500");

    if (!code.trim()) {
      showStatus("Strateji kodu yazın", "error");
      return;
    }

    const btn = $("sb-run-btn");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Çalışıyor...";
    }
    showStatus(`${symbol} için strateji çalıştırılıyor...`, "loading");

    fetch("/api/strategy/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, symbol, market, interval, limit }),
    })
      .then((r) => r.json())
      .then((d) => {
        resetBtn(btn);
        if (!d.ok) {
          showStatus("Hata: " + (d.error || "Bilinmeyen hata"), "error");
          if (d.validation) showValidation(d.validation);
          return;
        }

        currentResult = d;
        showStatus(
          `${d.candle_count} mum analiz edildi — ${d.trades.length} işlem, ${d.markers.length} sinyal`,
          "success"
        );

        renderChart(d);
        renderMetrics(d.metrics);
        renderEquityCurve(d.equity_curve);
        renderTrades(d.trades);

        if (d.validation) showValidation(d.validation);
      })
      .catch((err) => {
        resetBtn(btn);
        showStatus("Bağlantı hatası: " + err.message, "error");
      });
  }

  function resetBtn(btn) {
    if (!btn) return;
    btn.disabled = false;
    btn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> Stratejiyi Çalıştır`;
  }

  // ── Chart Rendering (LightweightCharts) ────────────────────
  function renderChart(data) {
    const section = $("sb-chart-section");
    const container = $("sb-chart");
    if (!section || !container) return;
    section.style.display = "block";

    // Update marker count
    const mc = $("sb-marker-count");
    if (mc) mc.textContent = (data.markers || []).length + " sinyal";

    // Destroy old chart
    if (lwChart) {
      lwChart.remove();
      lwChart = null;
      candleSeries = null;
      indicatorSeries = {};
    }

    container.innerHTML = "";

    // Create chart
    lwChart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: 350,
      layout: {
        background: { color: "#0f0f0f" },
        textColor: "#999",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.03)" },
        horzLines: { color: "rgba(255,255,255,0.03)" },
      },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      timeScale: {
        timeVisible: true,
        borderColor: "rgba(255,255,255,0.06)",
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.06)" },
    });

    // Responsive
    const ro = new ResizeObserver(() => {
      if (lwChart && container.clientWidth > 0) {
        lwChart.applyOptions({ width: container.clientWidth });
      }
    });
    ro.observe(container);

    // Candlestick series — need candle data from backtest
    // We need to fetch it or reconstruct from equity curve + trades
    // Since the API returns markers with time+price, we can use that
    // But for a proper chart, let's fetch candle data separately
    fetchCandleData(data);
  }

  function fetchCandleData(data) {
    // Fetch candle data for the chart
    const symbol = ($("sb-symbol") || {}).value || "BTCUSDT";
    const market = ($("sb-market") || {}).value || "crypto";
    const interval = ($("sb-interval") || {}).value || "1d";
    const limit = ($("sb-limit") || {}).value || "500";

    // Try the existing klines endpoint
    let url = "";
    if (market === "crypto") {
      url = `/api/market/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`;
    } else if (market === "bist") {
      url = `/api/bist/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`;
    } else if (market === "stocks") {
      url = `/api/stocks/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`;
    } else if (market === "forex") {
      url = `/api/forex/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`;
    } else if (market === "commodities") {
      url = `/api/commodities/klines?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`;
    }

    fetch(url)
      .then((r) => r.json())
      .then((kd) => {
        let klines = [];
        if (kd.candles && Array.isArray(kd.candles)) {
          klines = kd.candles;
        } else if (kd.ok && kd.data) {
          klines = kd.data;
        } else if (Array.isArray(kd)) {
          klines = kd;
        } else if (kd.klines) {
          klines = kd.klines;
        }

        if (klines.length > 0) {
          drawCandles(klines, data);
        } else {
          // Fallback: draw markers without candles
          drawMarkersOnly(data);
        }
      })
      .catch(() => {
        drawMarkersOnly(data);
      });
  }

  function drawCandles(klines, data) {
    if (!lwChart) return;

    // Add candlestick series
    candleSeries = lwChart.addCandlestickSeries({
      upColor: "#00C853",
      downColor: "#FF1744",
      borderDownColor: "#FF1744",
      borderUpColor: "#00C853",
      wickDownColor: "#FF1744",
      wickUpColor: "#00C853",
    });

    // Convert klines to LW format
    const candles = klines
      .map((k) => {
        const t = k.time || k.open_time || k.t;
        if (!t) return null;
        // Detect if time is in ms (> 1e12) or seconds
        let ts = typeof t === "number" ? t : new Date(t).getTime() / 1000;
        if (ts > 1e12) ts = Math.floor(ts / 1000);
        return {
          time: ts,
          open: parseFloat(k.open || k.o),
          high: parseFloat(k.high || k.h),
          low: parseFloat(k.low || k.l),
          close: parseFloat(k.close || k.c),
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.time - b.time);

    // Deduplicate by time
    const seen = new Set();
    const unique = candles.filter((c) => {
      if (seen.has(c.time)) return false;
      seen.add(c.time);
      return true;
    });

    if (unique.length > 0) {
      candleSeries.setData(unique);
    }

    // Build a time lookup
    const timeSet = new Set(unique.map((c) => c.time));

    // Add markers for buy/sell signals
    const markers = (data.markers || [])
      .map((m) => {
        let t = m.time > 1e12 ? Math.floor(m.time / 1000) : m.time;
        // Snap to nearest candle time if not exact
        if (!timeSet.has(t)) {
          const closest = unique.reduce((prev, curr) =>
            Math.abs(curr.time - t) < Math.abs(prev.time - t) ? curr : prev
          );
          if (closest && Math.abs(closest.time - t) < 86400 * 3) {
            t = closest.time;
          }
        }
        return {
          time: t,
          position: m.type === "buy" ? "belowBar" : "aboveBar",
          color: m.type === "buy" ? "#00C853" : "#FF1744",
          shape: m.type === "buy" ? "arrowUp" : "arrowDown",
          text: m.type === "buy" ? "Bullish" : "Bearish",
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.time - b.time);

    // Deduplicate markers by time
    const markerSeen = new Set();
    const uniqueMarkers = markers.filter((m) => {
      const key = m.time + "_" + m.text;
      if (markerSeen.has(key)) return false;
      markerSeen.add(key);
      return true;
    });

    if (uniqueMarkers.length > 0) {
      candleSeries.setMarkers(uniqueMarkers);
    }

    // Add indicator overlays
    const overlays = data.indicator_overlays || {};
    const colors = ["#2979FF", "#FFD600", "#FF6D00", "#AA00FF", "#00BFA5", "#FF4081"];
    let colorIdx = 0;

    Object.keys(overlays).forEach((label) => {
      const points = overlays[label];
      if (!points || !points.length) return;

      const lineData = points
        .map((p) => {
          let t = p.time > 1e12 ? Math.floor(p.time / 1000) : p.time;
          return { time: t, value: p.value };
        })
        .sort((a, b) => a.time - b.time);

      // Deduplicate
      const ldSeen = new Set();
      const ldUnique = lineData.filter((ld) => {
        if (ldSeen.has(ld.time)) return false;
        ldSeen.add(ld.time);
        return true;
      });

      if (ldUnique.length > 0) {
        const color = colors[colorIdx % colors.length];
        const series = lwChart.addLineSeries({
          color: color,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          title: label,
        });
        series.setData(ldUnique);
        indicatorSeries[label] = series;
        colorIdx++;
      }
    });

    // Fit content
    lwChart.timeScale().fitContent();
  }

  function drawMarkersOnly(data) {
    // If we can't get candle data, show a message
    const container = $("sb-chart");
    if (container) {
      container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#666;font-size:14px;">
        Grafik verisi yüklenemedi — sonuçlar metriklerde görüntüleniyor
      </div>`;
    }
  }

  // ── Metrics ────────────────────────────────────────────────
  function renderMetrics(m) {
    const section = $("sb-metrics-section");
    if (section) section.style.display = "block";

    const grid = $("sb-metrics-grid");
    if (!grid) return;

    const items = [
      { label: "Toplam İşlem", value: m.total_trades, cls: "" },
      { label: "Kazanma Oranı", value: m.win_rate + "%", cls: m.win_rate >= 50 ? "positive" : "negative" },
      { label: "Kâr Faktörü", value: m.profit_factor, cls: m.profit_factor >= 1 ? "positive" : "negative" },
      { label: "Net Kâr", value: "$" + num(m.net_profit), cls: m.net_profit >= 0 ? "positive" : "negative" },
      { label: "Net Kâr %", value: m.net_profit_pct + "%", cls: m.net_profit_pct >= 0 ? "positive" : "negative" },
      { label: "Ort. Kâr", value: "$" + num(m.avg_profit), cls: "positive" },
      { label: "Ort. Zarar", value: "$" + num(m.avg_loss), cls: "negative" },
      { label: "Maks. Düşüş", value: m.max_drawdown_pct + "%", cls: "negative" },
      { label: "En İyi İşlem", value: "$" + num(m.best_trade), cls: "positive" },
      { label: "En Kötü İşlem", value: "$" + num(m.worst_trade), cls: "negative" },
      { label: "Ort. Bar", value: m.avg_bars_held, cls: "" },
    ];

    grid.innerHTML = items
      .map(
        (it) => `
      <div class="sb-metric-card">
        <div class="sb-metric-label">${it.label}</div>
        <div class="sb-metric-value ${it.cls}">${it.value}</div>
      </div>`
      )
      .join("");
  }

  // ── Equity Curve ───────────────────────────────────────────
  function renderEquityCurve(curve) {
    const section = $("sb-equity-section");
    if (section) section.style.display = "block";

    const labels = curve.map((_, i) => i);
    const eqData = curve.map((p) => p.equity);

    if (equityChartJS) equityChartJS.destroy();

    const ctx = $("sb-equity-chart");
    if (!ctx) return;

    equityChartJS = new Chart(ctx.getContext("2d"), {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Equity ($)",
            data: eqData,
            borderColor: "#2979FF",
            backgroundColor: "rgba(41,121,255,0.08)",
            fill: true,
            tension: 0.3,
            pointRadius: 1,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: {
            grid: { color: "rgba(255,255,255,0.04)" },
            ticks: {
              color: "#666",
              callback: (v) => "$" + v.toLocaleString(),
            },
          },
        },
      },
    });
  }

  // ── Trade List ─────────────────────────────────────────────
  function renderTrades(trades) {
    const section = $("sb-trades-section");
    if (section) section.style.display = "block";

    const countEl = $("sb-trade-count");
    if (countEl) countEl.textContent = trades.length;

    const tbody = $("sb-trades-body");
    if (!tbody) return;

    if (!trades.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;opacity:.4;">İşlem bulunamadı</td></tr>';
      return;
    }

    tbody.innerHTML = trades
      .map((t) => {
        const cls = t.pnl >= 0 ? "positive" : "negative";
        const reason = t.exit_reason || "signal";
        const reasonLabels = {
          signal: "Sinyal",
          stop_loss: "Risk Seviyesi",
          take_profit: "Hedef Seviye",
          end: "Bitiş",
        };
        return `<tr>
        <td>$${num(t.analysis_price || t.entry_price)}</td>
        <td>$${num(t.close_price || t.exit_price)}</td>
        <td>${t.quantity.toFixed(4)}</td>
        <td>${t.bars_held}</td>
        <td><span class="exit-reason ${reason}">${reasonLabels[reason] || reason}</span></td>
        <td class="${cls}">$${num(t.pnl)}</td>
        <td class="${cls}">${t.pnl_pct}%</td>
      </tr>`;
      })
      .join("");
  }

  // ── Save / Load / Delete ───────────────────────────────────
  function saveStrategy() {
    const code = ($("sb-code") || {}).value || "";
    if (!code.trim()) {
      showStatus("Kaydetmek için strateji kodu yazın", "error");
      return;
    }

    // Parse to get name
    const nameMatch = code.match(/strategy\s+["'](.+?)["']/i);
    const name = nameMatch ? nameMatch[1] : "Custom Strategy";

    fetch("/api/strategy/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, code }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          showStatus(`"${name}" kaydedildi ✅`, "success");
          loadSaved();
        } else {
          showStatus("Kaydetme hatası: " + (d.error || ""), "error");
        }
      })
      .catch((err) => showStatus("Kaydetme hatası: " + err.message, "error"));
  }

  function loadSaved() {
    fetch("/api/strategy/list")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        const list = d.strategies || [];
        const section = $("sb-saved-section");
        const container = $("sb-saved-list");
        if (!container || !section) return;

        if (!list.length) {
          section.style.display = "none";
          return;
        }

        section.style.display = "block";
        container.innerHTML = list
          .map(
            (s) => `
          <div class="sb-saved-item" onclick="SB.loadStrategy('${esc(s.code.replace(/'/g, "\\'").replace(/\n/g, "\\n"))}')">
            <div>
              <div class="sb-saved-item-name">${esc(s.name)}</div>
              <div class="sb-saved-item-date">${new Date(s.created_at * 1000).toLocaleDateString("tr-TR")}</div>
            </div>
            <div class="sb-saved-item-actions">
              <button onclick="event.stopPropagation();SB.deleteSaved('${s.id}')" title="Sil">🗑</button>
            </div>
          </div>`
          )
          .join("");
      })
      .catch(() => {});
  }

  function loadStrategy(code) {
    const codeEl = $("sb-code");
    if (codeEl) {
      // Unescape
      codeEl.value = code.replace(/\\n/g, "\n").replace(/\\'/g, "'");
      parseCode(true);
    }
  }

  function deleteSaved(id) {
    if (!confirm("Bu stratejiyi silmek istediğinize emin misiniz?")) return;

    fetch("/api/strategy/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          showStatus("Strateji silindi", "success");
          loadSaved();
        }
      })
      .catch(() => {});
  }

  // ── Helpers ────────────────────────────────────────────────
  function showStatus(msg, type) {
    const el = $("sb-status");
    if (!el) return;
    el.textContent = msg;
    el.className = "sb-status " + type;
  }

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function num(v) {
    if (v === undefined || v === null) return "0";
    return Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 });
  }

  // ── Boot ───────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", init);

  // ── FAZ 28 — Activate Strategy for Live Signals ────────────
  function activateStrategy() {
    const code = ($("sb-code") || {}).value || "";
    const symbol = ($("sb-symbol") || {}).value || "BTCUSDT";
    const market = ($("sb-market") || {}).value || "crypto";
    const interval = ($("sb-interval") || {}).value || "1d";

    if (!code.trim()) {
      showStatus("Aktifleştirmek için strateji kodu yazın", "error");
      return;
    }

    // Extract name from code
    const nameMatch = code.match(/strategy\s+["'](.+?)["']/i);
    const name = nameMatch ? nameMatch[1] : "Custom Strategy";

    const btn = $("sb-activate-btn");
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Aktifleştiriliyor...';
    }

    fetch("/api/strategy/live/activate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code,
        symbol: symbol.toUpperCase(),
        market,
        interval,
        name,
        strategy_id: name.replace(/\s+/g, "_").toLowerCase(),
      }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Canlı Aktifleştir';
        }

        if (d.ok) {
          showStatus(
            `⚡ "${name}" canlı sinyal üretimi aktif — ${symbol} ${interval}`,
            "success"
          );
          showLiveStatus(d.activation);
        } else {
          showStatus("Aktifleştirme hatası: " + (d.error || ""), "error");
        }
      })
      .catch((err) => {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Canlı Aktifleştir';
        }
        showStatus("Bağlantı hatası: " + err.message, "error");
      });
  }

  function showLiveStatus(activation) {
    const el = $("sb-live-status");
    if (!el) return;

    el.style.display = "block";
    el.innerHTML = `
      <div class="sb-live-badge">
        <span class="sb-live-dot"></span>
        CANLI — ${esc(activation.strategy_name || "Strategy")}
        → ${activation.symbol} ${activation.interval}
      </div>
      <a href="/strategy-signals" class="sb-live-link">Sinyalleri Görüntüle →</a>
    `;
  }

  // ── FAZ 29 — Publish to Marketplace ────────────────────────
  function publishStrategy() {
    const code = ($("sb-code") || {}).value || "";
    if (!code.trim()) {
      showStatus("Önce bir strateji kodu yazın", "error");
      return;
    }

    // Extract strategy name from code
    const nameMatch = code.match(/strategy\s+"([^"]+)"/);
    const defaultName = nameMatch ? nameMatch[1] : "Strateji";
    const symbol = ($("sb-symbol") || {}).value || "BTCUSDT";
    const market = ($("sb-market") || {}).value || "crypto";
    const interval = ($("sb-interval") || {}).value || "1h";

    // Get metrics from last backtest if available
    let metricsData = {};
    if (currentResult && currentResult.metrics) {
      const m = currentResult.metrics;
      metricsData = {
        total_backtests: 1,
        win_rate: m.win_rate || 0,
        profit_factor: m.profit_factor || 0,
        net_profit: m.net_profit_pct || 0,
        max_drawdown: m.max_drawdown_pct || 0,
        avg_trade: m.avg_profit || 0,
      };
    }

    // Show publish modal
    const overlay = document.createElement("div");
    overlay.className = "sb-publish-overlay";
    overlay.innerHTML = `
      <div class="sb-publish-modal">
        <div class="sb-publish-title">📤 Strateji Yayınla</div>
        <div class="sb-publish-field">
          <label>Başlık</label>
          <input type="text" id="pub-title" value="${esc(defaultName)}" maxlength="100">
        </div>
        <div class="sb-publish-field">
          <label>Açıklama</label>
          <textarea id="pub-desc" placeholder="Strateji hakkında kısa bir açıklama..."></textarea>
        </div>
        <div class="sb-publish-field">
          <label>Etiketler (virgülle ayırın)</label>
          <input type="text" id="pub-tags" placeholder="trend, momentum, scalping">
        </div>
        <div class="sb-publish-field">
          <label>Görünürlük</label>
          <select id="pub-visibility">
            <option value="public">Herkese Açık</option>
            <option value="unlisted">Bağlantıyla Erişim</option>
            <option value="private">Gizli</option>
          </select>
        </div>
        <div class="sb-publish-field">
          <label>Risk Seviyesi</label>
          <select id="pub-risk">
            <option value="low">Düşük</option>
            <option value="medium" selected>Orta</option>
            <option value="high">Yüksek</option>
          </select>
        </div>
        <div class="sb-publish-actions">
          <button class="sb-publish-cancel" onclick="this.closest('.sb-publish-overlay').remove()">İptal</button>
          <button class="sb-publish-submit" id="pub-submit-btn">Yayınla</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.remove();
    });

    document.getElementById("pub-submit-btn").addEventListener("click", () => {
      const title = (document.getElementById("pub-title").value || "").trim();
      const desc = (document.getElementById("pub-desc").value || "").trim();
      const tagsStr = (document.getElementById("pub-tags").value || "").trim();
      const visibility = document.getElementById("pub-visibility").value;
      const riskLevel = document.getElementById("pub-risk").value;
      const tags = tagsStr ? tagsStr.split(",").map((t) => t.trim()).filter(Boolean) : [];

      if (!title) { alert("Başlık gerekli"); return; }

      const submitBtn = document.getElementById("pub-submit-btn");
      submitBtn.disabled = true;
      submitBtn.textContent = "Yayınlanıyor...";

      fetch("/api/marketplace/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description: desc,
          strategy_code: code,
          market,
          default_symbol: symbol,
          default_interval: interval,
          visibility,
          tags,
          risk_level: riskLevel,
          metrics: metricsData,
        }),
      })
        .then((r) => r.json())
        .then((d) => {
          if (d.ok) {
            overlay.remove();
            showStatus("✅ Strateji Marketplace'te yayınlandı! Slug: " + d.strategy.slug, "success");
          } else {
            alert("Hata: " + (d.error || "Bilinmeyen hata"));
            submitBtn.disabled = false;
            submitBtn.textContent = "Yayınla";
          }
        })
        .catch(() => {
          alert("Bağlantı hatası");
          submitBtn.disabled = false;
          submitBtn.textContent = "Yayınla";
        });
    });
  }

  // ── Public API ─────────────────────────────────────────────
  return {
    parseCode,
    runStrategy,
    saveStrategy,
    selectTemplate,
    insertIndicator,
    loadStrategy,
    deleteSaved,
    activateStrategy,
    publishStrategy,
  };
})();
