/* rooms.js — FAZ 34 — Live Rooms listing IIFE */
window.LR = (function () {
  "use strict";

  let currentTab = "all";
  let currentSort = "active";
  let offset = 0;
  const PAGE = 20;

  document.addEventListener("DOMContentLoaded", () => loadRooms());

  function $(id) { return document.getElementById(id); }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  async function api(url, opts) {
    try {
      const r = await fetch(url, opts);
      return await r.json();
    } catch { return { ok: false }; }
  }

  function switchTab(el, tab) {
    document.querySelectorAll(".lr-tab").forEach(t => t.classList.remove("active"));
    el.classList.add("active");
    currentTab = tab;
    offset = 0;
    loadRooms();
  }

  function setSort(el, sort) {
    document.querySelectorAll(".lr-filter").forEach(f => f.classList.remove("active"));
    el.classList.add("active");
    currentSort = sort;
    offset = 0;
    loadRooms();
  }

  async function loadRooms() {
    const params = new URLSearchParams();
    params.set("sort", currentSort);
    params.set("limit", PAGE);
    params.set("offset", offset);

    if (currentTab === "active") {
      params.set("active", "1");
    } else if (currentTab !== "all") {
      params.set("market", currentTab);
    }

    const data = await api("/api/rooms?" + params);
    const grid = $("lrGrid");
    if (!data.ok) { grid.innerHTML = '<div class="lr-empty">Yüklenemedi</div>'; return; }

    if (!data.rooms || data.rooms.length === 0) {
      grid.innerHTML = '<div class="lr-empty">Henüz canlı oda yok. İlk odayı sen oluştur!</div>';
      return;
    }

    grid.innerHTML = data.rooms.map(renderCard).join("");
  }

  function renderCard(r) {
    const letter = (r.mentor_display_name || "?")[0].toUpperCase();
    const marketLabels = { crypto: "Kripto", bist: "BIST", stocks: "Hisse", forex: "Forex", commodities: "Emtia" };
    const visLabels = { public: "Herkese Açık", followers_only: "Takipçi", subscribers_only: "Abone" };
    const activeBadge = r.is_active
      ? '<span class="lr-badge active">🔴 CANLI</span>'
      : '<span class="lr-badge inactive">Pasif</span>';
    const marketBadge = r.market ? `<span class="lr-badge market">${marketLabels[r.market] || r.market}</span>` : "";
    const visBadge = r.visibility !== "public" ? `<span class="lr-badge vis">${visLabels[r.visibility] || r.visibility}</span>` : "";

    return `
      <a href="/room/${encodeURIComponent(r.slug)}" class="lr-card">
        <div class="lr-card-top">
          <div class="lr-card-avatar">${letter}</div>
          <div class="lr-card-info">
            <div class="lr-card-title">${escapeHtml(r.title)}</div>
            <div class="lr-card-mentor">${escapeHtml(r.mentor_display_name)}</div>
          </div>
        </div>
        <div class="lr-card-badges">${activeBadge}${marketBadge}${visBadge}</div>
        ${r.description ? `<div class="lr-card-desc">${escapeHtml(r.description)}</div>` : ""}
        <div class="lr-card-stats">
          <span><span class="val">${r.participant_count || 0}</span> katılımcı</span>
        </div>
      </a>
    `;
  }

  function openCreateModal() { $("lrCreateModal").classList.add("open"); }
  function closeCreateModal() { $("lrCreateModal").classList.remove("open"); }

  async function submitRoom() {
    const title = $("lrTitle").value.trim();
    if (!title) return alert("Başlık gerekli");

    const body = {
      title,
      description: $("lrDesc").value.trim(),
      market: $("lrMarket").value,
      visibility: $("lrVisibility").value,
    };

    const data = await api("/api/room", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (data.ok) {
      closeCreateModal();
      window.location.href = "/room/" + encodeURIComponent(data.room.slug);
    } else {
      alert(data.error || "Hata oluştu");
    }
  }

  return { switchTab, setSort, openCreateModal, closeCreateModal, submitRoom };
})();
