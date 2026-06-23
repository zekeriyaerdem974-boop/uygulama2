/* =====================================================================
   ZKR Analiz My Courses — FAZ 33
   ===================================================================== */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  async function api(url) {
    const r = await fetch(url);
    return r.json();
  }

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text || '';
    return d.innerHTML;
  }

  async function load() {
    const data = await api('/api/courses/my');
    if (!data.ok) {
      $('mcList').innerHTML = '<div class="mc-empty">Yüklenemedi</div>';
      return;
    }

    const courses = data.courses || [];

    // Stats
    const active = courses.filter(c => c.enrollment_status === 'active').length;
    const completed = courses.filter(c => c.enrollment_status === 'completed').length;
    $('mcStats').innerHTML = `
      <div class="mc-stats">
        <div class="mc-stat-box"><div class="mc-stat-val">${courses.length}</div><div class="mc-stat-label">Toplam</div></div>
        <div class="mc-stat-box"><div class="mc-stat-val">${active}</div><div class="mc-stat-label">Devam Eden</div></div>
        <div class="mc-stat-box"><div class="mc-stat-val">${completed}</div><div class="mc-stat-label">Tamamlanan</div></div>
      </div>
    `;

    if (courses.length === 0) {
      $('mcList').innerHTML = `
        <div class="mc-empty">
          <div class="mc-empty-icon">📚</div>
          <div>Henüz bir kursa kayıt olmadınız</div>
          <div style="margin-top:8px"><a href="/courses">Kursları Keşfet →</a></div>
        </div>
      `;
      return;
    }

    $('mcList').innerHTML = '';
    courses.forEach(c => {
      const card = document.createElement('a');
      card.className = 'mc-card';
      card.href = '/course/' + encodeURIComponent(c.slug);

      const levelLabels = {beginner:'Başlangıç', intermediate:'Orta', advanced:'İleri'};
      const levelClass = 'level-' + (c.level || 'beginner');
      const status = c.enrollment_status || 'active';
      const statusLabel = status === 'completed' ? '✓ Tamamlandı' : 'Devam Ediyor';
      const statusClass = status === 'completed' ? 'mc-status-completed' : 'mc-status-active';
      const pct = Math.round(c.progress_pct || 0);
      const thumbIcon = c.market === 'crypto' ? '₿' : c.market === 'bist' ? '📊' : c.market === 'forex' ? '💱' : '📚';

      card.innerHTML = `
        <div class="mc-card-top">
          <div class="mc-thumb">${thumbIcon}</div>
          <div class="mc-card-info">
            <div class="mc-card-title">${escapeHtml(c.title)}</div>
            <div class="mc-card-mentor">🎓 ${escapeHtml(c.mentor_display_name || c.mentor_username)}</div>
          </div>
        </div>
        <div class="mc-progress-bar"><div class="mc-progress-fill" style="width:${pct}%"></div></div>
        <div class="mc-progress-row">
          <span class="mc-progress-pct">%${pct}</span>
          <span class="mc-progress-status ${statusClass}">${statusLabel}</span>
        </div>
        <div class="mc-badges">
          <span class="mc-badge ${levelClass}">${levelLabels[c.level] || 'Başlangıç'}</span>
          <span class="mc-badge" style="color:#888">${c.lesson_count || 0} ders</span>
        </div>
      `;
      $('mcList').appendChild(card);
    });
  }

  document.addEventListener('DOMContentLoaded', load);
})();
