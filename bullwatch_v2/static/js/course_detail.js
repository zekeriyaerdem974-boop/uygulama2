/* =====================================================================
   ZKR Analiz Course Detail — FAZ 33
   ===================================================================== */
window.CD = (function () {
  'use strict';

  let courseData = null;

  function $(id) { return document.getElementById(id); }

  async function api(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text || '';
    return d.innerHTML;
  }

  // ── Load Course ─────────────────────────────────────────────
  async function loadCourse() {
    const slug = document.querySelector('meta[name="course-slug"]')?.content;
    if (!slug) {
      $('cdContent').innerHTML = '<div class="cd-loading">Kurs bulunamadı</div>';
      return;
    }

    const data = await api('/api/course/' + encodeURIComponent(slug));
    if (!data.ok) {
      $('cdContent').innerHTML = '<div class="cd-loading">Kurs bulunamadı</div>';
      return;
    }

    courseData = data;
    render(data.course, data.lessons, data.is_owner);
  }

  // ── Render ──────────────────────────────────────────────────
  function render(course, lessons, isOwner) {
    const c = course;
    const levelLabels = {beginner:'Başlangıç', intermediate:'Orta', advanced:'İleri'};
    const levelClass = 'level-' + (c.level || 'beginner');
    const marketLabels = {crypto:'Kripto',bist:'BIST',stocks:'Hisse',forex:'Forex',commodities:'Emtia'};
    const pricingLabels = {free:'Ücretsiz', paid:'Ücretli', subscription:'Abonelik'};
    const pc = c.pricing_model || 'free';
    const thumbIcon = c.market === 'crypto' ? '₿' : c.market === 'bist' ? '📊' : c.market === 'forex' ? '💱' : '📚';

    let badges = '';
    badges += `<span class="cd-badge ${levelClass}">${levelLabels[c.level] || 'Başlangıç'}</span>`;
    if (c.market) badges += `<span class="cd-badge market">${marketLabels[c.market] || c.market}</span>`;
    badges += `<span class="cd-badge ${pc}">${pricingLabels[pc] || 'Ücretsiz'}</span>`;
    if (pc !== 'free' && c.price > 0) badges += `<span class="cd-badge paid">₺${c.price}</span>`;

    let html = `
      <div class="cd-header">
        <div class="cd-top">
          <div class="cd-thumb">${thumbIcon}</div>
          <div class="cd-title-area">
            <div class="cd-title">${escapeHtml(c.title)}</div>
            <div class="cd-mentor">🎓 <a href="/mentor/${escapeHtml(c.mentor_username)}">${escapeHtml(c.mentor_display_name || c.mentor_username)}</a></div>
          </div>
        </div>
        <div class="cd-stats-row">
          <div class="cd-stat"><div class="cd-stat-val">${c.students_count || 0}</div><div class="cd-stat-label">Öğrenci</div></div>
          <div class="cd-stat"><div class="cd-stat-val">${c.lesson_count || 0}</div><div class="cd-stat-label">Ders</div></div>
          <div class="cd-stat"><div class="cd-stat-val">${c.total_duration || 0}</div><div class="cd-stat-label">Dakika</div></div>
          ${c.rating ? `<div class="cd-stat"><div class="cd-stat-val">${Number(c.rating).toFixed(1)}</div><div class="cd-stat-label">Puan</div></div>` : ''}
        </div>
        <div class="cd-badges">${badges}</div>
      </div>
    `;

    // Description
    if (c.description) {
      html += `<div class="cd-desc">${escapeHtml(c.description)}</div>`;
    }

    // Actions
    html += '<div class="cd-actions">';
    if (isOwner) {
      if (!c.is_published) {
        html += `<button class="cd-btn cd-btn-manage" onclick="CD.publishCourse()">📢 Yayınla</button>`;
      }
      html += `<button class="cd-btn cd-btn-manage" onclick="CD.openLessonModal()">+ Ders Ekle</button>`;
    } else if (c.is_enrolled) {
      html += `<button class="cd-btn cd-btn-enrolled" disabled>✓ Kayıtlı</button>`;
    } else if (c.is_published) {
      html += `<button class="cd-btn cd-btn-enroll" onclick="CD.enroll()">Kayıt Ol</button>`;
    }
    html += '</div>';

    // Lessons
    html += '<div class="cd-section"><div class="cd-section-title">📖 Dersler</div>';
    if (!lessons || lessons.length === 0) {
      html += '<div class="cd-empty">Henüz ders eklenmemiş</div>';
    } else {
      lessons.forEach((l, i) => {
        const typeLabels = {video:'🎬 Video', article:'📄 Makale', chart_case:'📊 Grafik', mixed:'📦 Karışık'};
        const hasContent = l.content || l.video_url;
        const previewBadge = l.is_preview ? '<span class="cd-lesson-preview">Önizleme</span>' : '';
        const lockedBadge = (!l.is_preview && !hasContent && !isOwner) ? '<span class="cd-lesson-locked">🔒 Kilitli</span>' : '';

        html += `
          <div class="cd-lesson">
            <div class="cd-lesson-header">
              <div class="cd-lesson-num">${i + 1}</div>
              <div class="cd-lesson-info">
                <div class="cd-lesson-title">${escapeHtml(l.title)}</div>
                <div class="cd-lesson-meta">
                  <span>${typeLabels[l.content_type] || '📄 Makale'}</span>
                  ${l.duration_minutes ? `<span>⏱ ${l.duration_minutes} dk</span>` : ''}
                  ${previewBadge}${lockedBadge}
                </div>
              </div>
            </div>
            ${l.video_url ? `<div class="cd-lesson-video"><a href="${escapeHtml(l.video_url)}" target="_blank" rel="noopener noreferrer">🎬 Videoyu İzle</a></div>` : ''}
            ${l.content ? `<div class="cd-lesson-content">${escapeHtml(l.content)}</div>` : ''}
          </div>
        `;
      });
    }
    html += '</div>';

    $('cdContent').innerHTML = html;
  }

  // ── Enroll ──────────────────────────────────────────────────
  async function enroll() {
    if (!courseData) return;
    const data = await api('/api/course/' + courseData.course.id + '/enroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (data.ok) {
      loadCourse(); // Reload to show enrolled state
    } else {
      alert(data.error || 'Hata oluştu');
    }
  }

  // ── Publish ─────────────────────────────────────────────────
  async function publishCourse() {
    if (!courseData) return;
    const data = await api('/api/course/' + courseData.course.id + '/publish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (data.ok) {
      loadCourse();
    } else {
      alert(data.error || 'Hata oluştu');
    }
  }

  // ── Lesson Modal ────────────────────────────────────────────
  function openLessonModal() {
    $('cdLessonTitle').value = '';
    $('cdLessonType').value = 'article';
    $('cdLessonVideo').value = '';
    $('cdLessonContent').value = '';
    $('cdLessonDuration').value = '0';
    $('cdLessonPreview').checked = false;
    $('cdLessonModal').classList.add('open');
  }

  function closeLessonModal() {
    $('cdLessonModal').classList.remove('open');
  }

  async function submitLesson() {
    if (!courseData) return;
    const title = $('cdLessonTitle').value.trim();
    if (!title) return alert('Ders başlığı gerekli');

    const body = {
      title: title,
      content_type: $('cdLessonType').value,
      video_url: $('cdLessonVideo').value.trim(),
      content: $('cdLessonContent').value.trim(),
      duration_minutes: parseInt($('cdLessonDuration').value) || 0,
      is_preview: $('cdLessonPreview').checked,
    };

    const data = await api('/api/course/' + courseData.course.id + '/lesson', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (data.ok) {
      closeLessonModal();
      loadCourse();
    } else {
      alert(data.error || 'Hata oluştu');
    }
  }

  // ── Init ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', loadCourse);

  return { enroll, publishCourse, openLessonModal, closeLessonModal, submitLesson };
})();
