/* =====================================================================
   ZKR Analiz Courses — FAZ 33
   ===================================================================== */
window.CR = (function () {
  'use strict';

  let currentTab = 'all';
  let currentSort = 'newest';
  let currentLevel = '';
  let offset = 0;
  let loading = false;
  let hasMore = true;

  function $(id) { return document.getElementById(id); }

  async function api(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  // ── Tab / Sort / Level ──────────────────────────────────────
  function switchTab(tab) {
    currentTab = tab;
    offset = 0;
    hasMore = true;
    document.querySelectorAll('.cr-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });
    $('crList').innerHTML = '<div class="cr-loading">Yükleniyor…</div>';
    loadCourses();
  }

  function setSort(sort) {
    currentSort = sort;
    offset = 0;
    hasMore = true;
    document.querySelectorAll('.cr-filter').forEach(f => {
      f.classList.toggle('active', f.dataset.sort === sort);
    });
    $('crList').innerHTML = '<div class="cr-loading">Yükleniyor…</div>';
    loadCourses();
  }

  function setLevel(level) {
    currentLevel = level;
    offset = 0;
    hasMore = true;
    document.querySelectorAll('.cr-level').forEach(l => {
      l.classList.toggle('active', l.dataset.level === level);
    });
    $('crList').innerHTML = '<div class="cr-loading">Yükleniyor…</div>';
    loadCourses();
  }

  // ── Load Courses ────────────────────────────────────────────
  async function loadCourses(append) {
    if (loading) return;
    loading = true;

    try {
      let params = `sort=${currentSort}&limit=20&offset=${offset}`;

      // Market filter from tab
      if (['crypto', 'bist', 'stocks', 'forex'].includes(currentTab)) {
        params += `&market=${currentTab}`;
      }
      // Pricing filter from tab
      if (currentTab === 'free') params += '&pricing=free';
      if (currentTab === 'paid') params += '&pricing=paid';

      // Level filter
      if (currentLevel) params += `&level=${currentLevel}`;

      const data = await api(`/api/courses?${params}`);
      if (!data.ok) {
        $('crList').innerHTML = '<div class="cr-empty">Yüklenemedi</div>';
        return;
      }

      const courses = data.courses || [];

      if (!append) {
        $('crList').innerHTML = '';
      }

      if (courses.length === 0 && offset === 0) {
        $('crList').innerHTML = '<div class="cr-empty">Henüz kurs bulunamadı</div>';
        hasMore = false;
        return;
      }

      courses.forEach(c => $('crList').appendChild(renderCard(c)));
      offset += courses.length;
      hasMore = courses.length >= 20;
    } catch (e) {
      if (!append) $('crList').innerHTML = '<div class="cr-empty">Bağlantı hatası</div>';
    } finally {
      loading = false;
    }
  }

  // ── Render Course Card ──────────────────────────────────────
  function renderCard(c) {
    const card = document.createElement('a');
    card.className = 'cr-card';
    card.href = '/course/' + encodeURIComponent(c.slug);

    const levelLabels = {beginner:'Başlangıç', intermediate:'Orta', advanced:'İleri'};
    const levelClass = 'level-' + (c.level || 'beginner');
    const marketLabels = {crypto:'Kripto',bist:'BIST',stocks:'Hisse',forex:'Forex',commodities:'Emtia'};
    const pricingLabels = {free:'Ücretsiz', paid:'Ücretli', subscription:'Abonelik'};
    const pricingClass = c.pricing_model || 'free';

    const thumbIcon = c.market === 'crypto' ? '₿' : c.market === 'bist' ? '📊' : c.market === 'forex' ? '💱' : '📚';

    let badges = '';
    badges += `<span class="cr-badge ${levelClass}">${levelLabels[c.level] || 'Başlangıç'}</span>`;
    if (c.market) {
      badges += `<span class="cr-badge market">${marketLabels[c.market] || c.market}</span>`;
    }
    badges += `<span class="cr-badge ${pricingClass}">${pricingLabels[pricingClass] || 'Ücretsiz'}</span>`;
    if (pricingClass !== 'free' && c.price > 0) {
      badges += `<span class="cr-badge paid">₺${c.price}</span>`;
    }

    card.innerHTML = `
      <div class="cr-card-top">
        <div class="cr-thumb">${thumbIcon}</div>
        <div class="cr-card-info">
          <div class="cr-card-title">${escapeHtml(c.title)}</div>
          <div class="cr-card-mentor">🎓 ${escapeHtml(c.mentor_display_name || c.mentor_username)}</div>
        </div>
      </div>
      ${c.description ? `<div class="cr-card-desc">${escapeHtml(c.description)}</div>` : ''}
      <div class="cr-badges">${badges}</div>
      <div class="cr-stats">
        <div>👥 <span class="cr-stat-val">${c.students_count || 0}</span> öğrenci</div>
        <div>📖 <span class="cr-stat-val">${c.lesson_count || 0}</span> ders</div>
        <div>⏱ <span class="cr-stat-val">${c.total_duration || 0}</span> dk</div>
        ${c.rating ? `<div>⭐ ${Number(c.rating).toFixed(1)}</div>` : ''}
      </div>
    `;
    return card;
  }

  // ── Create Course Modal ─────────────────────────────────────
  function openCreateModal() {
    $('crCreateModal').classList.add('open');
  }

  function closeCreateModal() {
    $('crCreateModal').classList.remove('open');
  }

  async function submitCourse() {
    const title = $('crTitle').value.trim();
    if (!title) return alert('Kurs başlığı gerekli');

    const body = {
      title: title,
      description: $('crDesc').value.trim(),
      level: $('crLevel').value,
      market: $('crMarket').value,
      pricing_model: $('crPricing').value,
      price: parseFloat($('crPrice').value) || 0,
      thumbnail_url: $('crThumb').value.trim(),
    };

    const data = await api('/api/course', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (data.ok) {
      closeCreateModal();
      // Go to new course page
      window.location.href = '/course/' + data.course.slug;
    } else {
      alert(data.error || 'Hata oluştu');
    }
  }

  // ── Infinite Scroll ─────────────────────────────────────────
  window.addEventListener('scroll', () => {
    if (!hasMore || loading) return;
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
      loadCourses(true);
    }
  });

  // ── Init ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    loadCourses();
  });

  return { switchTab, setSort, setLevel, openCreateModal, closeCreateModal, submitCourse };
})();
