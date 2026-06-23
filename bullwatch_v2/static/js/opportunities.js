/* ═══════════════════════════════════════════════════════════
   Opportunities JS — FAZ 40
   AI Smart Alerts & Market Opportunity Engine
   ═══════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  // ── State ────────────────────────────────────────────────
  var _opportunities = [];
  var _alerts = [];
  var _marketFilter = "all";
  var _eventFilter = "all";
  var _refreshTimer = null;
  var REFRESH_INTERVAL = 30000; // 30s

  // ── Init ─────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    loadOpportunities();
    loadStats();
    bindFilters();
    bindControls();
    startAutoRefresh();
  });

  // ── Data Loading ─────────────────────────────────────────
  function loadOpportunities() {
    var params = [];
    if (_marketFilter !== "all") params.push("market=" + _marketFilter);
    if (_eventFilter !== "all") params.push("event_type=" + _eventFilter);
    var qs = params.length ? "?" + params.join("&") : "";

    fetch("/api/opportunities" + qs)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          _opportunities = d.data || [];
          renderOpportunities();
          updateStats();
        }
      })
      .catch(function (e) {
        console.warn("Opportunities load error:", e);
        renderEmpty();
      });
  }

  function loadStats() {
    // Alerts count
    fetch("/api/opportunities/alerts")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          _alerts = d.data || [];
          var el = document.getElementById("stat-alerts");
          if (el) el.textContent = _alerts.filter(function (a) { return a.active; }).length;
        }
      })
      .catch(function () {});

    // Notifications count
    fetch("/api/opportunities/notifications?unread=1&limit=1")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          var el = document.getElementById("stat-notifs");
          if (el) el.textContent = d.unread_count || 0;
        }
      })
      .catch(function () {});
  }

  function updateStats() {
    var totalEl = document.getElementById("stat-total");
    var highEl = document.getElementById("stat-high-conf");
    if (totalEl) totalEl.textContent = _opportunities.length;
    if (highEl) {
      highEl.textContent = _opportunities.filter(function (o) {
        return o.confidence >= 80;
      }).length;
    }
  }

  // ── Rendering ────────────────────────────────────────────
  function renderOpportunities() {
    var grid = document.getElementById("opp-grid");
    if (!grid) return;

    if (!_opportunities.length) {
      renderEmpty();
      return;
    }

    var html = "";
    _opportunities.forEach(function (opp) {
      html += renderCard(opp);
    });
    grid.innerHTML = html;

    // Update scan time
    var scanEl = document.getElementById("opp-last-scan");
    if (scanEl) {
      scanEl.textContent = "Son güncelleme: " + new Date().toLocaleTimeString("tr-TR");
    }
  }

  function renderCard(opp) {
    var confColor = opp.confidence >= 80 ? "var(--success)"
      : opp.confidence >= 60 ? "var(--warning)"
      : "var(--text-dim)";

    var bgColor = (opp.color || "#64748b") + "15";
    var time = opp.created_at ? timeAgo(opp.created_at) : "";

    var priceStr = "";
    if (opp.price) {
      priceStr = opp.price >= 1 ? "$" + numberFormat(opp.price)
        : "$" + opp.price.toFixed(6);
    }

    var changeBadge = "";
    if (opp.change_pct) {
      var cColor = opp.change_pct >= 0 ? "var(--success)" : "var(--danger)";
      changeBadge = '<span style="color:' + cColor + ';font-size:11px;font-weight:600;">'
        + (opp.change_pct >= 0 ? "+" : "") + opp.change_pct.toFixed(1) + "%</span>";
    }

    return '<div class="opp-card" data-symbol="' + esc(opp.symbol) + '" data-market="' + esc(opp.market) + '">'
      + '<div class="opp-card-header">'
      + '<div class="opp-card-icon" style="background:' + bgColor + ';">' + (opp.icon || "🔍") + "</div>"
      + '<div>'
      + '<div class="opp-card-symbol">' + esc(opp.symbol) + " " + changeBadge + "</div>"
      + '<div class="opp-card-market">' + esc(opp.market) + (priceStr ? " • " + priceStr : "") + "</div>"
      + "</div>"
      + '<span class="opp-card-label" style="background:' + bgColor + ";color:" + (opp.color || "#64748b") + ';">'
      + esc(opp.label || opp.event_type) + "</span>"
      + "</div>"
      + '<div class="opp-card-desc">' + esc(opp.description) + "</div>"
      + (opp.details ? '<div class="opp-card-details">' + esc(opp.details) + "</div>" : "")
      + '<div class="opp-card-footer">'
      + '<div class="opp-confidence">'
      + '<div class="opp-confidence-bar"><div class="opp-confidence-fill" style="width:' + opp.confidence + "%;background:" + confColor + ';"></div></div>'
      + '<span class="opp-confidence-text" style="color:' + confColor + ';">%' + opp.confidence + "</span>"
      + "</div>"
      + '<span class="opp-card-time">' + esc(time) + "</span>"
      + "</div>"
      + "</div>";
  }

  function renderEmpty() {
    var grid = document.getElementById("opp-grid");
    if (!grid) return;
    grid.innerHTML = '<div class="opp-empty">'
      + '<div class="opp-empty-icon">🔍</div>'
      + '<div class="opp-empty-text">Henüz fırsat tespit edilmedi</div>'
      + '<div class="opp-empty-sub">Fırsatlar her 2 dakikada otomatik taranır</div>'
      + "</div>";
  }

  // ── Filters ──────────────────────────────────────────────
  function bindFilters() {
    // Market filters
    var chips = document.querySelectorAll("#opp-market-filters .pro-chip");
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        chips.forEach(function (c) { c.classList.remove("active"); });
        chip.classList.add("active");
        _marketFilter = chip.getAttribute("data-market");
        loadOpportunities();
      });
    });

    // Event type filters
    var eChips = document.querySelectorAll("#opp-event-filters .pro-chip");
    eChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        eChips.forEach(function (c) { c.classList.remove("active"); });
        chip.classList.add("active");
        _eventFilter = chip.getAttribute("data-event");
        loadOpportunities();
      });
    });
  }

  // ── Controls ─────────────────────────────────────────────
  function bindControls() {
    // Scan button
    var scanBtn = document.getElementById("btn-scan-now");
    if (scanBtn) {
      scanBtn.addEventListener("click", function () {
        scanBtn.disabled = true;
        scanBtn.textContent = "Taranıyor...";
        fetch("/api/opportunities/scan", { method: "POST" })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.ok) {
              _opportunities = d.data || [];
              renderOpportunities();
              updateStats();
              loadStats();
            }
          })
          .catch(function (e) { console.warn("Scan error:", e); })
          .finally(function () {
            scanBtn.disabled = false;
            scanBtn.innerHTML = '<svg style="width:14px;height:14px;margin-right:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>Tara';
          });
      });
    }

    // Alerts panel toggle
    var alertsBtn = document.getElementById("btn-manage-alerts");
    var alertsPanel = document.getElementById("alerts-panel");
    if (alertsBtn && alertsPanel) {
      alertsBtn.addEventListener("click", function () {
        var visible = alertsPanel.style.display !== "none";
        alertsPanel.style.display = visible ? "none" : "block";
        if (!visible) loadAlerts();
      });
    }

    // Create alert form
    var createBtn = document.getElementById("btn-create-alert");
    var alertForm = document.getElementById("alert-form");
    if (createBtn && alertForm) {
      createBtn.addEventListener("click", function () {
        alertForm.style.display = alertForm.style.display === "none" ? "block" : "none";
      });
    }

    var cancelBtn = document.getElementById("btn-cancel-alert");
    if (cancelBtn && alertForm) {
      cancelBtn.addEventListener("click", function () {
        alertForm.style.display = "none";
      });
    }

    var saveBtn = document.getElementById("btn-save-alert");
    if (saveBtn) {
      saveBtn.addEventListener("click", saveAlert);
    }

    // Notifications button (stat card click)
    var notifStat = document.getElementById("stat-notifs");
    if (notifStat) {
      notifStat.parentElement.parentElement.style.cursor = "pointer";
      notifStat.parentElement.parentElement.addEventListener("click", function () {
        var panel = document.getElementById("notifs-panel");
        if (panel) {
          var visible = panel.style.display !== "none";
          panel.style.display = visible ? "none" : "block";
          if (!visible) loadNotifications();
        }
      });
    }

    // Mark all read
    var markAllBtn = document.getElementById("btn-mark-all-read");
    if (markAllBtn) {
      markAllBtn.addEventListener("click", function () {
        fetch("/api/opportunities/notifications/read", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.ok) {
              loadNotifications();
              loadStats();
            }
          })
          .catch(function () {});
      });
    }
  }

  // ── Alerts CRUD ──────────────────────────────────────────
  function loadAlerts() {
    fetch("/api/opportunities/alerts")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          _alerts = d.data || [];
          renderAlerts();
        }
      })
      .catch(function () {});
  }

  function renderAlerts() {
    var list = document.getElementById("alerts-list");
    if (!list) return;

    if (!_alerts.length) {
      list.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-dim);font-size:13px;">'
        + "Henüz smart alert oluşturulmadı.</div>";
      return;
    }

    var html = "";
    _alerts.forEach(function (a) {
      var triggerInfo = a.trigger_count > 0
        ? a.trigger_count + " kez tetiklendi"
        : "Henüz tetiklenmedi";
      html += '<div class="alert-card">'
        + '<div style="font-size:20px;">🔔</div>'
        + '<div class="alert-card-info">'
        + '<div class="alert-card-name">' + esc(a.name) + "</div>"
        + '<div class="alert-card-type">' + esc(a.alert_type) + (a.symbol ? " • " + esc(a.symbol) : "") + "</div>"
        + '<div class="alert-card-stats">' + esc(triggerInfo) + "</div>"
        + "</div>"
        + '<div class="alert-card-actions">'
        + '<div class="alert-toggle' + (a.active ? " active" : "") + '" data-id="' + esc(a.id) + '" data-active="' + (a.active ? "1" : "0") + '"></div>'
        + '<button class="alert-delete-btn" data-id="' + esc(a.id) + '" title="Sil">✕</button>'
        + "</div>"
        + "</div>";
    });
    list.innerHTML = html;

    // Bind toggle
    list.querySelectorAll(".alert-toggle").forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        var id = toggle.getAttribute("data-id");
        var isActive = toggle.getAttribute("data-active") === "1";
        fetch("/api/opportunities/alert/" + id, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: !isActive }),
        })
          .then(function (r) { return r.json(); })
          .then(function (d) { if (d.ok) loadAlerts(); })
          .catch(function () {});
      });
    });

    // Bind delete
    list.querySelectorAll(".alert-delete-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        if (!confirm("Bu alarmı silmek istediğinizden emin misiniz?")) return;
        fetch("/api/opportunities/alert/" + id, { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function (d) { if (d.ok) loadAlerts(); })
          .catch(function () {});
      });
    });
  }

  function saveAlert() {
    var data = {
      alert_type: document.getElementById("alert-type").value,
      name: document.getElementById("alert-name").value,
      symbol: document.getElementById("alert-symbol").value,
      market: document.getElementById("alert-market").value,
      min_confidence: parseInt(document.getElementById("alert-confidence").value) || 50,
      cooldown_minutes: parseInt(document.getElementById("alert-cooldown").value) || 60,
    };

    if (!data.name) {
      alert("Alarm adı gerekli");
      return;
    }

    fetch("/api/opportunities/alert/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) {
          document.getElementById("alert-form").style.display = "none";
          document.getElementById("alert-name").value = "";
          document.getElementById("alert-symbol").value = "";
          loadAlerts();
          loadStats();
        } else {
          alert(d.error || "Alarm oluşturulamadı");
        }
      })
      .catch(function (e) {
        alert("Hata: " + e.message);
      });
  }

  // ── Notifications ────────────────────────────────────────
  function loadNotifications() {
    fetch("/api/opportunities/notifications?limit=30")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.ok) renderNotifications(d.data || []);
      })
      .catch(function () {});
  }

  function renderNotifications(notifs) {
    var list = document.getElementById("notifs-list");
    if (!list) return;

    if (!notifs.length) {
      list.innerHTML = '<div style="text-align:center;padding:24px;color:var(--text-dim);font-size:13px;">'
        + "Henüz bildirim yok.</div>";
      return;
    }

    var html = "";
    notifs.forEach(function (n) {
      var cls = n.read ? "notif-item" : "notif-item unread";
      html += '<div class="' + cls + '">'
        + '<div class="notif-item-msg">' + esc(n.message) + "</div>"
        + '<div class="notif-item-time">' + timeAgo(n.triggered_at) + "</div>"
        + "</div>";
    });
    list.innerHTML = html;
  }

  // ── Auto-refresh ─────────────────────────────────────────
  function startAutoRefresh() {
    _refreshTimer = setInterval(function () {
      loadOpportunities();
      loadStats();
    }, REFRESH_INTERVAL);
  }

  // ── Helpers ──────────────────────────────────────────────
  function esc(s) {
    if (!s) return "";
    var d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
  }

  function numberFormat(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(2) + "K";
    return n.toFixed(2);
  }

  function timeAgo(isoStr) {
    if (!isoStr) return "";
    var d = new Date(isoStr);
    var now = new Date();
    var diff = Math.floor((now - d) / 1000);
    if (diff < 60) return diff + "s önce";
    if (diff < 3600) return Math.floor(diff / 60) + "dk önce";
    if (diff < 86400) return Math.floor(diff / 3600) + "sa önce";
    return Math.floor(diff / 86400) + "g önce";
  }

})();
