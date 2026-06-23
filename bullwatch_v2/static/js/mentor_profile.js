/* =====================================================================
   ZKR Analiz Mentor Profile Page — FAZ 32
   ===================================================================== */
window.MP = (function () {
  'use strict';

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

  function timeAgo(iso) {
    const d = new Date(iso);
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return 'az önce';
    if (diff < 3600) return Math.floor(diff / 60) + 'dk';
    if (diff < 86400) return Math.floor(diff / 3600) + 'sa';
    if (diff < 604800) return Math.floor(diff / 86400) + 'g';
    return d.toLocaleDateString('tr-TR');
  }

  // ── Load Profile ────────────────────────────────────────────
  async function loadProfile() {
    const username = document.querySelector('meta[name="mentor-username"]')?.content;
    if (!username) {
      $('mpContent').innerHTML = '<div class="mp-loading">Mentor bulunamadı</div>';
      return;
    }

    const data = await api('/api/mentor/' + encodeURIComponent(username));
    if (!data.ok) {
      $('mpContent').innerHTML = '<div class="mp-loading">Mentor bulunamadı</div>';
      return;
    }

    render(data.profile, data.stats, data.posts, data.strategies, data.courses, data.live_rooms, data.reputation, data.mentor_avg_rating);
  }

  // ── Render ──────────────────────────────────────────────────
  function render(profile, stats, posts, strategies, courses, liveRooms, reputation, mentorAvgRating) {
    const p = profile;
    const letter = (p.display_name || '?')[0].toUpperCase();
    const verifiedHtml = p.is_verified ? '<span class="mp-verified">✓</span>' : '';

    // Market badges
    let marketBadges = '';
    (p.markets_list || []).forEach(mk => {
      const labels = {crypto:'Kripto',bist:'BIST',stocks:'Hisse',forex:'Forex',commodities:'Emtia'};
      marketBadges += `<span class="mp-badge market">${labels[mk] || mk}</span>`;
    });

    // Pricing badge
    const pricingLabels = {free:'Ücretsiz', paid:'Ücretli', subscription:'Abonelik'};
    const pc = p.pricing_model || 'free';
    marketBadges += `<span class="mp-badge ${pc}">${pricingLabels[pc]}</span>`;
    if (pc !== 'free' && p.monthly_price > 0) {
      marketBadges += `<span class="mp-badge paid">₺${p.monthly_price}/ay</span>`;
    }

    // Specialty badges
    let specBadges = '';
    (p.specialties_list || []).forEach(s => {
      specBadges += `<span class="mp-badge specialty">${escapeHtml(s)}</span>`;
    });

    // Follow button
    const followClass = p.is_following ? 'following' : '';
    const followText = p.is_following ? 'Takip Ediliyor' : 'Takip Et';

    let html = `
      <div class="mp-header">
        <div class="mp-top">
          <div class="mp-avatar">${letter}</div>
          <div class="mp-name-area">
            <div class="mp-display-name">${escapeHtml(p.display_name)} ${verifiedHtml}</div>
            <div class="mp-username">@${escapeHtml(p.username)}</div>
            <div class="mp-headline">${escapeHtml(p.headline || '')}</div>
          </div>
        </div>
        <div class="mp-stats-row">
          <div class="mp-stat"><div class="mp-stat-val">${p.followers_count || 0}</div><div class="mp-stat-label">Takipçi</div></div>
          <div class="mp-stat"><div class="mp-stat-val">${stats.post_count || 0}</div><div class="mp-stat-label">Paylaşım</div></div>
          <div class="mp-stat"><div class="mp-stat-val">${stats.strategy_count || 0}</div><div class="mp-stat-label">Strateji</div></div>
          <div class="mp-stat"><div class="mp-stat-val">${stats.total_likes || 0}</div><div class="mp-stat-label">Beğeni</div></div>
        </div>
        <div class="mp-badges">${marketBadges}${specBadges}</div>
      </div>
    `;

    // Actions
    if (!p.is_own_profile) {
      html += `
        <div class="mp-actions">
          <button class="mp-btn mp-btn-follow ${followClass}" id="mpFollowBtn"
                  onclick="MP.toggleFollow('${p.user_id}')">${followText}</button>
        </div>
      `;
    }

    // Bio
    if (p.bio) {
      html += `<div class="mp-bio">${escapeHtml(p.bio)}</div>`;
    }

    // Info grid
    html += `
      <div class="mp-info-grid">
        <div class="mp-info-item"><div class="mp-info-val">${p.experience_years || 0} yıl</div><div class="mp-info-label">Deneyim</div></div>
        <div class="mp-info-item"><div class="mp-info-val">${(p.languages_list || ['Türkçe']).join(', ')}</div><div class="mp-info-label">Diller</div></div>
        <div class="mp-info-item"><div class="mp-info-val">${p.students_count || 0}</div><div class="mp-info-label">Öğrenci</div></div>
        <div class="mp-info-item"><div class="mp-info-val">${p.rating ? Number(p.rating).toFixed(1) : '—'}</div><div class="mp-info-label">Puan</div></div>
      </div>
    `;

    // Reputation & Trust Level section (FAZ 35)
    if (reputation) {
      const trustColors = {'Beginner Analyst':'#64748b','Trusted Analyst':'#3b82f6','Top Analyst':'#f59e0b','Elite Mentor':'#ef4444'};
      const tc = trustColors[reputation.trust_level] || '#64748b';
      const badgeDefs = {top_crypto:{icon:'₿',name:'Top Crypto'},bist_expert:{icon:'🏛',name:'BIST Expert'},strategy_master:{icon:'🎯',name:'Strategy Master'},top_mentor:{icon:'🏆',name:'Top Mentor'},community_leader:{icon:'👥',name:'Community Leader'}};
      let badgeHtml = '';
      (reputation.badges || []).forEach(b => {
        const bd = badgeDefs[b];
        if (bd) badgeHtml += `<span class="mp-badge" style="background:${tc}22;color:${tc};border:1px solid ${tc}44;">${bd.icon} ${bd.name}</span>`;
      });

      html += `
        <div class="mp-section">
          <div class="mp-section-title">⭐ Reputation</div>
          <div class="mp-info-grid">
            <div class="mp-info-item"><div class="mp-info-val" style="color:${tc};">${reputation.score}</div><div class="mp-info-label">Skor</div></div>
            <div class="mp-info-item"><div class="mp-info-val" style="color:${tc};font-size:.85rem;">${reputation.trust_level}</div><div class="mp-info-label">Seviye</div></div>
          </div>
          ${badgeHtml ? '<div class="mp-badges" style="margin-top:8px;">' + badgeHtml + '</div>' : ''}
        </div>
      `;
    }

    // Mentor Rating section (FAZ 35)
    if (mentorAvgRating) {
      const stars = '★'.repeat(Math.round(mentorAvgRating.avg_rating || 0)) + '☆'.repeat(5 - Math.round(mentorAvgRating.avg_rating || 0));
      html += `
        <div class="mp-section">
          <div class="mp-section-title">📊 Değerlendirmeler</div>
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span style="color:#f59e0b;font-size:1.2rem;">${stars}</span>
            <span style="color:#e5e7eb;font-weight:600;">${(mentorAvgRating.avg_rating || 0).toFixed(1)}</span>
            <span style="color:#9ca3af;font-size:.85rem;">(${mentorAvgRating.rating_count || 0} değerlendirme)</span>
          </div>
          ${!p.is_own_profile ? `
          <div id="mpRatingForm" style="margin-top:8px;">
            <div style="display:flex;gap:4px;margin-bottom:8px;" id="mpStars">
              ${[1,2,3,4,5].map(i => `<button onclick="MP.setRating(${i})" style="background:none;border:none;font-size:1.5rem;cursor:pointer;color:#374151;" data-star="${i}">☆</button>`).join('')}
            </div>
            <textarea id="mpReview" placeholder="Yorum yaz (opsiyonel)..." style="width:100%;background:#1a1a2e;color:#e5e7eb;border:1px solid #374151;border-radius:8px;padding:8px;font-size:.85rem;resize:none;" rows="2"></textarea>
            <button onclick="MP.submitRating('${p.user_id}')" style="margin-top:6px;padding:6px 16px;background:#f59e0b;color:#000;border:none;border-radius:8px;font-size:.85rem;font-weight:600;cursor:pointer;">Puanla</button>
          </div>
          ` : ''}
        </div>
      `;
    }

    // Live Rooms section (FAZ 34)
    if (liveRooms && liveRooms.length > 0) {
      html += '<div class="mp-section"><div class="mp-section-title">🔴 Canlı Odalar</div>';
      liveRooms.forEach(r => {
        const statusBadge = r.is_active ? '<span style="color:#4ade80;font-size:.75rem;">🔴 CANLI</span>' : '<span style="color:#64748b;font-size:.75rem;">Pasif</span>';
        html += `
          <a href="/room/${encodeURIComponent(r.slug)}" class="mp-strat-card" style="display:block;text-decoration:none;color:inherit;">
            <div class="mp-strat-name">${escapeHtml(r.title)} ${statusBadge}</div>
            <div class="mp-strat-meta">${r.market || 'Genel'} · ${r.participant_count || 0} katılımcı</div>
          </a>
        `;
      });
      html += '</div>';
    }

    // Courses section (FAZ 33)
    if (courses && courses.length > 0) {
      html += '<div class="mp-section"><div class="mp-section-title">📚 Kurslar</div>';
      courses.forEach(c => {
        const levelLabels = {beginner:'Başlangıç',intermediate:'Orta',advanced:'İleri'};
        html += `
          <a href="/course/${encodeURIComponent(c.slug)}" class="mp-strat-card" style="display:block;text-decoration:none;color:inherit;">
            <div class="mp-strat-name">${escapeHtml(c.title)}</div>
            <div class="mp-strat-meta">${levelLabels[c.level] || ''} · ${c.market || 'Genel'} · ${c.lesson_count || 0} ders</div>
            <div class="mp-strat-stats"><span class="val">${c.students_count || 0}</span> öğrenci</div>
          </a>
        `;
      });
      html += '</div>';
    }

    // Strategies section
    if (strategies && strategies.length > 0) {
      html += '<div class="mp-section"><div class="mp-section-title">📦 Yayınlanan Stratejiler</div>';
      strategies.forEach(s => {
        const wr = s.win_rate ? `<span class="val">${Number(s.win_rate).toFixed(1)}%</span> WR` : '';
        const pf = s.profit_factor ? `<span class="val">${Number(s.profit_factor).toFixed(2)}</span> PF` : '';
        html += `
          <div class="mp-strat-card">
            <div class="mp-strat-name">${escapeHtml(s.name || s.strategy_name || 'Strateji')}</div>
            <div class="mp-strat-meta">${s.market || ''} · ${s.timeframe || ''}</div>
            <div class="mp-strat-stats">${wr} ${pf}</div>
          </div>
        `;
      });
      html += '</div>';
    }

    // Recent posts section
    if (posts && posts.length > 0) {
      html += '<div class="mp-section"><div class="mp-section-title">📝 Son Paylaşımlar</div>';
      posts.forEach(post => {
        let badge = '';
        if (post.symbol) {
          badge = `<span class="mp-post-badge">${post.symbol}${post.timeframe ? ' · ' + post.timeframe : ''}</span>`;
        }
        html += `
          <div class="mp-post">
            <div class="mp-post-content">${escapeHtml(post.content)}</div>
            <div class="mp-post-meta">
              <span>${timeAgo(post.created_at)}</span>
              ${badge}
              <span>❤️ ${post.likes_count || 0}</span>
              <span>💬 ${post.comments_count || 0}</span>
            </div>
          </div>
        `;
      });
      html += '</div>';
    }

    $('mpContent').innerHTML = html;
  }

  // ── Follow Toggle ───────────────────────────────────────────
  async function toggleFollow(mentorUserId) {
    const btn = $('mpFollowBtn');
    if (!btn) return;

    const isFollowing = btn.classList.contains('following');
    const endpoint = isFollowing ? '/api/mentor/unfollow' : '/api/mentor/follow';

    const data = await api(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mentor_user_id: mentorUserId }),
    });

    if (data.ok) {
      btn.classList.toggle('following');
      btn.textContent = isFollowing ? 'Takip Et' : 'Takip Ediliyor';
    }
  }

  // ── Rating helpers (FAZ 35) ──────────────────────────────
  let _selectedRating = 0;

  function setRating(val) {
    _selectedRating = val;
    const stars = document.querySelectorAll('#mpStars button');
    stars.forEach(s => {
      s.textContent = parseInt(s.dataset.star) <= val ? '★' : '☆';
      s.style.color = parseInt(s.dataset.star) <= val ? '#f59e0b' : '#374151';
    });
  }

  async function submitRating(mentorUserId) {
    if (!_selectedRating) return;
    const review = document.getElementById('mpReview')?.value || '';
    const data = await api('/api/rate/mentor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mentor_user_id: mentorUserId, rating: _selectedRating, review }),
    });
    if (data.ok) {
      loadProfile(); // reload to show updated rating
    }
  }

  // ── Init ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', loadProfile);

  return { toggleFollow, setRating, submitRating };
})();
