/* ═══════════════════════════════════════════════════════════════
   Marketplace — FAZ 29
   Strategy marketplace: browse, search, follow
   ═══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  let currentTab = "discover";
  let searchTimeout = null;

  // ── Init ───────────────────────────────────────────────────
  function init() {
    loadTab("discover");
  }

  // ── Tab Switching ──────────────────────────────────────────
  function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll(".mp-tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.tab === tab);
    });

    const filters = document.getElementById("mp-filters");
    if (filters) filters.style.display = (tab === "following" || tab === "published") ? "none" : "flex";

    loadTab(tab);
  }

  function loadTab(tab) {
    const content = document.getElementById("mp-content");
    content.innerHTML = '<div class="mp-loading"><div class="mp-loading-spinner"></div>Yükleniyor...</div>';

    if (tab === "following") {
      fetch("/api/marketplace/following")
        .then((r) => r.json())
        .then((d) => {
          if (!d.ok) { content.innerHTML = renderEmpty("Giriş yapmanız gerekiyor", "login"); return; }
          renderStrategies(d.strategies || [], content, "Takip Edilen Stratejiler", "following");
        })
        .catch(() => { content.innerHTML = renderEmpty("Yükleme hatası"); });
      return;
    }

    if (tab === "published") {
      fetch("/api/marketplace/my-published")
        .then((r) => r.json())
        .then((d) => {
          if (!d.ok) { content.innerHTML = renderEmpty("Giriş yapmanız gerekiyor", "login"); return; }
          renderStrategies(d.strategies || [], content, "Yayınladığım Stratejiler", "published");
        })
        .catch(() => { content.innerHTML = renderEmpty("Yükleme hatası"); });
      return;
    }

    const sortMap = { discover: "newest", top: "performance", popular: "popular", newest: "newest" };
    const sort = sortMap[tab] || "newest";
    const market = document.getElementById("mp-market-filter")?.value || "";
    const search = document.getElementById("mp-search-input")?.value || "";

    let url = `/api/marketplace/strategies?sort=${sort}&limit=50`;
    if (market) url += `&market=${market}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    fetch(url)
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) return;
        const strategies = d.strategies || [];
        const titleMap = {
          discover: "🔥 Keşfet",
          top: "🏆 En İyi Performans",
          popular: "👥 En Popüler",
          newest: "🆕 En Yeni",
        };

        if (tab === "discover") {
          renderDiscoverView(strategies, content);
        } else {
          renderStrategies(strategies, content, titleMap[tab] || "Stratejiler");
        }
      })
      .catch(() => { content.innerHTML = renderEmpty("Yükleme hatası"); });
  }

  // ── Discover View (Featured + Top + Newest) ────────────────
  function renderDiscoverView(all, container) {
    if (all.length === 0) {
      container.innerHTML = renderEmpty("Henüz yayınlanmış strateji yok", "publish");
      return;
    }

    // Split into sections
    const featured = all.slice(0, 3);
    const sorted = [...all].sort((a, b) => (b.win_rate || 0) - (a.win_rate || 0));
    const topPerf = sorted.slice(0, 6);
    const popular = [...all].sort((a, b) => (b.followers_count || 0) - (a.followers_count || 0)).slice(0, 6);

    let html = "";

    html += '<div class="mp-section-title">⭐ Öne Çıkan <span class="badge">' + featured.length + "</span></div>";
    html += '<div class="mp-grid">' + featured.map(renderCard).join("") + "</div>";

    if (topPerf.length > 0) {
      html += '<div class="mp-section-title">🏆 En İyi Performans <span class="badge">' + topPerf.length + "</span></div>";
      html += '<div class="mp-grid">' + topPerf.map(renderCard).join("") + "</div>";
    }

    if (popular.length > 0) {
      html += '<div class="mp-section-title">👥 En Popüler <span class="badge">' + popular.length + "</span></div>";
      html += '<div class="mp-grid">' + popular.map(renderCard).join("") + "</div>";
    }

    container.innerHTML = html;
  }

  // ── Render Strategy List ───────────────────────────────────
  function renderStrategies(strategies, container, title, type) {
    if (strategies.length === 0) {
      const msg = type === "following" ? "Henüz takip edilen strateji yok"
        : type === "published" ? "Henüz yayınlanmış stratejiniz yok"
        : "Sonuç bulunamadı";
      container.innerHTML = renderEmpty(msg, type === "published" ? "publish" : null);
      return;
    }

    container.innerHTML =
      '<div class="mp-section-title">' + title + ' <span class="badge">' + strategies.length + "</span></div>" +
      '<div class="mp-grid">' + strategies.map(renderCard).join("") + "</div>";
  }

  // ── Render Single Card ─────────────────────────────────────
  function renderCard(s) {
    const winRate = s.win_rate != null ? s.win_rate.toFixed(1) + "%" : "—";
    const drawdown = s.max_drawdown != null ? s.max_drawdown.toFixed(1) + "%" : "—";
    const followers = s.followers_count || 0;
    const signals = s.live_signal_count || 0;
    const tags = (s.tags || []).slice(0, 3);
    const desc = esc(s.description || "Açıklama yok").substring(0, 120);

    const winClass = (s.win_rate || 0) >= 50 ? "green" : "red";
    const ddClass = (s.max_drawdown || 0) > 20 ? "red" : "amber";

    let liveBadge = "";
    if (s.is_live_enabled || signals > 0) {
      liveBadge = '<div class="mp-live-badge"><span class="mp-live-dot"></span> Canlı</div>';
    }

    return `
    <div class="mp-card" onclick="MP.openDetail('${esc(s.slug)}')">
      ${liveBadge}
      <div class="mp-card-header">
        <div>
          <div class="mp-card-title">${esc(s.title)}</div>
          <div class="mp-card-creator">@${esc(s.publisher_username || "anonim")}</div>
        </div>
      </div>
      <div class="mp-card-desc">${desc}</div>
      <div class="mp-card-tags">
        <span class="mp-card-tag market">${esc(s.market || "crypto")}</span>
        <span class="mp-card-tag">${esc(s.default_symbol || "")}</span>
        <span class="mp-card-tag">${esc(s.default_interval || "")}</span>
        ${tags.map((t) => '<span class="mp-card-tag">' + esc(t) + "</span>").join("")}
      </div>
      <div class="mp-card-stats">
        <span class="mp-card-stat ${winClass}">📊 ${winRate}</span>
        <span class="mp-card-stat ${ddClass}">📉 ${drawdown}</span>
        <span class="mp-card-stat">👥 ${followers}</span>
        <span class="mp-card-stat amber">⚡ ${signals}</span>
      </div>
    </div>`;
  }

  // ── Empty State ────────────────────────────────────────────
  function renderEmpty(msg, action) {
    let link = "";
    if (action === "publish") {
      link = '<a class="mp-empty-link" href="/strategy-builder">Strategy Builder\'da bir strateji yayınlayın →</a>';
    } else if (action === "login") {
      link = '<a class="mp-empty-link" href="/login">Giriş yapın →</a>';
    }
    return `<div class="mp-empty"><div class="mp-empty-icon">🏪</div><div class="mp-empty-text">${msg}</div>${link}</div>`;
  }

  // ── Search ─────────────────────────────────────────────────
  function search(value) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadTab(currentTab), 300);
  }

  // ── Filters ────────────────────────────────────────────────
  function applyFilters() {
    loadTab(currentTab);
  }

  // ── Open Detail ────────────────────────────────────────────
  function openDetail(slug) {
    window.location.href = "/marketplace/" + slug;
  }

  // ── Helpers ────────────────────────────────────────────────
  function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Akademi Pills (FAZ 33) ─────────────────────────────────
  let currentPill = "strategies";

  function switchPill(pill) {
    currentPill = pill;
    document.querySelectorAll(".mp-pill").forEach((p) => {
      p.classList.toggle("active", p.dataset.pill === pill);
    });

    if (pill === "courses") {
      loadCourses();
    } else {
      loadTab(currentTab);
    }
  }

  function loadCourses() {
    const content = document.getElementById("mp-content");
    content.innerHTML = '<div class="mp-loading"><div class="mp-loading-spinner"></div>Kurslar yükleniyor...</div>';

    fetch("/api/marketplace/courses")
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) {
          content.innerHTML = renderEmpty("Kurs yükleme hatası");
          return;
        }
        renderCourses(d.courses || [], content);
      })
      .catch((e) => {
        console.error("Kurs yükleme hatası:", e);
        content.innerHTML = renderEmpty("Kurs yükleme hatası");
      });
  }

  function renderCourses(courses, container) {
    if (courses.length === 0) {
      container.innerHTML = renderEmpty("Henüz kurs yok", "coming");
      return;
    }

    let html = '<div class="mp-section-title">📚 Akademi & Masterclass <span class="badge">' + courses.length + "</span></div>";
    html += '<div class="mp-grid">';

    courses.forEach((course) => {
      const modules = course.modules_count || 0;
      const desc = esc(course.description || "").substring(0, 120);
      
      html += `
      <div class="mp-card" onclick="MP.openCourse('${esc(course.slug)}')">
        <div class="mp-card-header">
          <div>
            <div class="mp-card-title">${esc(course.title)}</div>
            <div class="mp-card-creator">👨‍🏫 ${esc(course.mentor_name || "ZKR Academy")}</div>
          </div>
        </div>
        <div class="mp-card-desc">${desc}</div>
        <div class="mp-card-tags">
          <span class="mp-card-tag" style="background:#4f46e522;color:#8b5cf6;">📖 ${course.level}</span>
          <span class="mp-card-tag" style="background:#0d4f3c22;color:#10b981;">🎯 ${modules} modül</span>
          <span class="mp-card-tag" style="background:#1f2937;color:#9ca3af;">${course.pricing === 'premium' ? '💎 Premium' : '🆓 Ücretsiz'}</span>
        </div>
      </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
  }

  function openCourse(slug) {
    // In-place course detail flip (async)
    const content = document.getElementById("mp-content");
    content.style.opacity = "0.8";
    content.innerHTML = '<div class="mp-loading"><div class="mp-loading-spinner"></div>Kurs detayı yükleniyor...</div>';

    fetch(`/api/marketplace/course/${slug}`)
      .then((r) => r.json())
      .then((d) => {
        if (!d.ok) {
          content.innerHTML = renderEmpty("Kurs bulunamadı");
          return;
        }
        renderCourseDetail(d.course, content);
      })
      .catch(() => {
        content.innerHTML = renderEmpty("Yükleme hatası");
      });
  }

  function renderCourseDetail(course, container) {
    const modules = course.modules || [];
    
    let html = `
    <div style="max-width:600px; margin:0 auto;">
      <button onclick="MP.backToCourses()" style="background:transparent;border:none;color:#f59e0b;font-size:14px;cursor:pointer;margin-bottom:16px;">← Akademi'ye Dön</button>
      
      <div style="background:#0d0d12;border:1px solid #1a1a2e;border-radius:12px;padding:20px;margin-bottom:20px;">
        <h2 style="color:#eee;margin:0 0 8px;font-size:20px;">${esc(course.title)}</h2>
        <p style="color:#666;margin:0 0 12px;font-size:13px;">👨‍🏫 ${esc(course.mentor_name || "ZKR Academy")}</p>
        <p style="color:#999;margin:0;font-size:13px;line-height:1.5;">${esc(course.description || "")}</p>
      </div>

      <div style="background:#0d0d12;border:1px solid #1a1a2e;border-radius:12px;padding:20px;">
        <h3 style="color:#eee;margin:0 0 16px;font-size:16px;">📖 Modüller (${modules.length})</h3>
    `;

    modules.forEach((mod, i) => {
      const mins = Math.floor(mod.duration_seconds / 60);
      html += `
      <div style="border-bottom:1px solid #1a1a2e;padding-bottom:12px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <p style="color:#eee;margin:0;font-size:13px;font-weight:600;">${i+1}. ${esc(mod.title)}</p>
            <p style="color:#666;margin:4px 0 0;font-size:12px;">${esc(mod.description || "")}</p>
          </div>
          <span style="color:#f59e0b;font-size:12px;white-space:nowrap;">${mins}min</span>
        </div>
      </div>`;
    });

    html += `
      </div>
    </div>
    `;

    container.innerHTML = html;
    container.style.opacity = "1";
  }

  function backToCourses() {
    currentPill = "courses";
    document.querySelectorAll(".mp-pill").forEach((p) => {
      p.classList.toggle("active", p.dataset.pill === "courses");
    });
    loadCourses();
  }

  // ── Boot ───────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", init);

  window.MP = { switchTab, search, applyFilters, openDetail, switchPill, openCourse, backToCourses };
})();
