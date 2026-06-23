/* =====================================================================
   ZKR Analiz Mentors — FAZ 32
   ===================================================================== */
window.MT = (function () {
  'use strict';

  let currentTab = 'featured';
  let currentSort = 'followers';
  let offset = 0;
  let loading = false;
  let hasMore = true;

  function $(id) { return document.getElementById(id); }

  async function api(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }

  function avatarLetter(name) {
    return (name || '?')[0].toUpperCase();
  }

  // ── Tab / Sort ──────────────────────────────────────────────
  function switchTab(tab) {
    currentTab = tab;
    offset = 0;
    hasMore = true;
    document.querySelectorAll('.mt-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tab);
    });
    $('mtList').innerHTML = '<div class="mt-loading">Yükleniyor…</div>';
    loadMentors();
  }

  function setSort(sort) {
    currentSort = sort;
    offset = 0;
    hasMore = true;
    document.querySelectorAll('.mt-filter').forEach(f => {
      f.classList.toggle('active', f.dataset.sort === sort);
    });
    $('mtList').innerHTML = '<div class="mt-loading">Yükleniyor…</div>';
    loadMentors();
  }

  // ── Load Mentors ────────────────────────────────────────────
  async function loadMentors(append) {
    if (loading) return;
    loading = true;

    try {
      let url;
      if (currentTab === 'featured') {
        url = '/api/mentor/featured?limit=20';
      } else {
        let params = `sort=${currentSort}&limit=20&offset=${offset}`;
        if (currentTab !== 'all') {
          params += `&market=${currentTab}`;
        }
        url = `/api/mentors?${params}`;
      }

      const data = await api(url);
      if (!data.ok) {
        $('mtList').innerHTML = '<div class="mt-empty">Yüklenemedi</div>';
        return;
      }

      const mentors = data.mentors || [];

      if (!append) {
        $('mtList').innerHTML = '';
      }

      if (mentors.length === 0 && offset === 0) {
        $('mtList').innerHTML = '<div class="mt-empty">Henüz mentor bulunamadı</div>';
        hasMore = false;
        return;
      }

      mentors.forEach(m => $('mtList').appendChild(renderCard(m)));
      offset += mentors.length;
      hasMore = mentors.length >= 20;
    } catch (e) {
      if (!append) $('mtList').innerHTML = '<div class="mt-empty">Bağlantı hatası</div>';
    } finally {
      loading = false;
    }
  }

  // ── Render Mentor Card ──────────────────────────────────────
  function renderCard(m) {
    const card = document.createElement('div');
    card.className = 'mt-card';
    card.id = 'mentor-' + m.id;

    let badges = '';
    (m.markets_list || []).forEach(mk => {
      const labels = {crypto:'Kripto',bist:'BIST',stocks:'Hisse',forex:'Forex',commodities:'Emtia'};
      badges += `<span class="mt-badge market">${labels[mk] || mk}</span>`;
    });
    if (m.is_verified) {
      badges += '<span class="mt-badge verified">✓ Doğrulanmış</span>';
    }
    const pricingLabels = {free:'Ücretsiz', paid:'Ücretli', subscription:'Abonelik'};
    const pricingClass = m.pricing_model || 'free';
    badges += `<span class="mt-badge ${pricingClass}">${pricingLabels[pricingClass] || 'Ücretsiz'}</span>`;

    let specialtyBadges = '';
    (m.specialties_list || []).slice(0, 3).forEach(s => {
      specialtyBadges += `<span class="mt-badge specialty">${escapeHtml(s)}</span>`;
    });

    const rating = m.rating ? `⭐ ${Number(m.rating).toFixed(1)}` : '';

    card.innerHTML = `
      <div class="mt-card-header">
        <div class="mt-avatar">${avatarLetter(m.display_name)}</div>
        <div style="flex:1;min-width:0;">
          <div class="mt-name">${escapeHtml(m.display_name)}</div>
          <div class="mt-headline">${escapeHtml(m.headline || '')}</div>
        </div>
      </div>
      <div class="mt-badges">${badges}${specialtyBadges}</div>
      <div class="mt-stats">
        <div>👥 <span class="mt-stat-val">${m.followers_count || 0}</span> takipçi</div>
        <div>📈 <span class="mt-stat-val">${m.experience_years || 0}</span> yıl</div>
        ${rating ? `<div>${rating}</div>` : ''}
      </div>
      <div class="mt-card-actions">
        <a href="/mentor/${m.username}" class="mt-btn mt-btn-primary" style="text-decoration:none">Profili Gör</a>
        <button class="mt-btn mt-btn-outline" id="follow-btn-${m.user_id}"
                onclick="MT.toggleFollow('${m.user_id}', this)">
          ${m.is_following ? 'Takibi Bırak' : 'Takip Et'}
        </button>
      </div>
    `;
    return card;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  // ── Follow / Unfollow ───────────────────────────────────────
  async function toggleFollow(mentorUserId, btn) {
    const isFollowing = btn.textContent.trim() === 'Takibi Bırak';
    const endpoint = isFollowing ? '/api/mentor/unfollow' : '/api/mentor/follow';

    const data = await api(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mentor_user_id: mentorUserId }),
    });

    if (data.ok) {
      btn.textContent = isFollowing ? 'Takip Et' : 'Takibi Bırak';
    }
  }

  // ── Create Modal ────────────────────────────────────────────
  function openCreateModal() {
    // Check if user already has a profile and pre-fill
    api('/api/mentor/my-profile').then(data => {
      if (data.ok && data.profile) {
        const p = data.profile;
        $('mtDisplayName').value = p.display_name || '';
        $('mtHeadline').value = p.headline || '';
        $('mtBio').value = p.bio || '';
        $('mtExpYears').value = p.experience_years || 0;
        $('mtSpecialties').value = p.specialties || '';
        $('mtLanguages').value = p.languages || 'Türkçe';
        $('mtPricing').value = p.pricing_model || 'free';
        $('mtPrice').value = p.monthly_price || 0;
        // Check market boxes
        const markets = (p.markets || '').split(',');
        document.querySelectorAll('input[name="mt-market"]').forEach(cb => {
          cb.checked = markets.includes(cb.value);
        });
      }
    });
    $('mtCreateModal').classList.add('open');
  }

  function closeCreateModal() {
    $('mtCreateModal').classList.remove('open');
  }

  async function submitProfile() {
    const displayName = $('mtDisplayName').value.trim();
    if (!displayName) return alert('Görünen ad gerekli');

    const markets = [];
    document.querySelectorAll('input[name="mt-market"]:checked').forEach(cb => {
      markets.push(cb.value);
    });

    const body = {
      display_name: displayName,
      headline: $('mtHeadline').value.trim(),
      bio: $('mtBio').value.trim(),
      experience_years: parseInt($('mtExpYears').value) || 0,
      markets: markets.join(','),
      specialties: $('mtSpecialties').value.trim(),
      languages: $('mtLanguages').value.trim() || 'Türkçe',
      pricing_model: $('mtPricing').value,
      monthly_price: parseFloat($('mtPrice').value) || 0,
    };

    const data = await api('/api/mentor/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (data.ok) {
      closeCreateModal();
      switchTab(currentTab);
    } else {
      alert(data.error || 'Hata oluştu');
    }
  }

  // ── Infinite Scroll ─────────────────────────────────────────
  window.addEventListener('scroll', () => {
    if (!hasMore || loading || currentTab === 'featured') return;
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
      loadMentors(true);
    }
  });

  // ── Init ────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    loadMentors();
  });

  return { switchTab, setSort, toggleFollow, openCreateModal, closeCreateModal, submitProfile };
})();
