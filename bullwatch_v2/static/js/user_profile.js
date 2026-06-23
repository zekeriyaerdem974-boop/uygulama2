/* =====================================================================
   ZKR Analiz User Profile — FAZ 31
   ===================================================================== */
window.UP = (function () {
  'use strict';

  let profileData = null;
  let postsData = [];
  let analysisStats = null;

  function $(id) { return document.getElementById(id); }

  function timeAgo(iso) {
    const d = new Date(iso);
    const now = Date.now();
    const diff = Math.floor((now - d.getTime()) / 1000);
    if (diff < 60) return 'az önce';
    if (diff < 3600) return Math.floor(diff / 60) + 'dk';
    if (diff < 86400) return Math.floor(diff / 3600) + 'sa';
    if (diff < 604800) return Math.floor(diff / 86400) + 'g';
    return d.toLocaleDateString('tr-TR');
  }

  function avatarLetter(username) {
    return (username || '?')[0].toUpperCase();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async function api(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }

  async function load() {
    const username = document.querySelector('meta[name="profile-username"]')?.content;
    if (!username) return;

    const data = await api('/api/social/user/' + encodeURIComponent(username));
    if (!data.ok) {
      $('upProfile').innerHTML = '<div class="sf-empty">Kullanıcı bulunamadı</div>';
      return;
    }

    profileData = data.profile;
    postsData = data.posts || [];

    // Load analysis stats (FAZ 36)
    try {
      const astats = await api('/api/analysis/user-stats/' + encodeURIComponent(profileData.user_id));
      if (astats.ok) analysisStats = astats.stats;
    } catch(e) {}

    render();
  }

  function render() {
    const p = profileData;
    let html = `
      <div class="up-header">
        <div class="up-avatar">${avatarLetter(p.username)}</div>
        <div class="up-username">@${p.username}</div>
        <div class="up-stats">
          <div class="up-stat"><div class="up-stat-num">${p.post_count}</div><div class="up-stat-label">Paylaşım</div></div>
          <div class="up-stat"><div class="up-stat-num">${p.followers_count}</div><div class="up-stat-label">Takipçi</div></div>
          <div class="up-stat"><div class="up-stat-num">${p.following_count}</div><div class="up-stat-label">Takip</div></div>
          <div class="up-stat"><div class="up-stat-num">${p.total_likes}</div><div class="up-stat-label">Beğeni</div></div>
          ${analysisStats ? `<div class="up-stat"><div class="up-stat-num">${analysisStats.analysis_count}</div><div class="up-stat-label">Analiz</div></div>` : ''}
        </div>
        ${!p.is_own_profile ? `<button id="upFollowBtn" class="up-follow-btn ${p.is_following ? 'following' : ''}" onclick="UP.toggleFollow()">${p.is_following ? 'Takipten Çık' : 'Takip Et'}</button>` : ''}
      </div>
      <div class="up-tabs">
        <div class="up-tab active">Paylaşımlar</div>
      </div>
      <div id="upPosts" class="up-posts"></div>
    `;
    $('upProfile').innerHTML = html;
    renderPosts();
  }

  function renderPosts() {
    const container = $('upPosts');
    if (!container) return;

    if (postsData.length === 0) {
      container.innerHTML = '<div class="sf-empty">Henüz paylaşım yok</div>';
      return;
    }

    container.innerHTML = '';
    postsData.forEach(post => {
      const card = document.createElement('div');
      card.className = 'sf-card';

      let symbolBadge = '';
      if (post.symbol) {
        symbolBadge = `<span class="sf-symbol-badge">${post.symbol}${post.timeframe ? ' · ' + post.timeframe : ''}</span>`;
      }

      let chartHtml = '';
      if (post.chart_snapshot) {
        chartHtml = `<img class="sf-chart-img" src="${post.chart_snapshot}" alt="chart" loading="lazy" />`;
      }

      card.innerHTML = `
        <div class="sf-card-header">
          <div class="sf-avatar">${avatarLetter(post.username)}</div>
          <div class="sf-user-info">
            <span class="sf-username">${post.username}</span>
            <div class="sf-time">${timeAgo(post.created_at)} ${symbolBadge}</div>
          </div>
        </div>
        <div class="sf-content">${escapeHtml(post.content)}</div>
        ${chartHtml}
        <div class="sf-actions">
          <button class="sf-action ${post.is_liked ? 'liked' : ''}" onclick="UP.likePost('${post.id}', this)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
            <span class="like-count">${post.likes_count || 0}</span>
          </button>
          <span class="sf-action">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
            <span>${post.comments_count || 0}</span>
          </span>
        </div>
      `;
      container.appendChild(card);
    });
  }

  async function toggleFollow() {
    if (!profileData) return;
    const isFollowing = profileData.is_following;
    const url = isFollowing ? '/api/social/unfollow' : '/api/social/follow';
    const data = await api(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: profileData.user_id }),
    });
    if (data.ok) {
      profileData.is_following = !isFollowing;
      profileData.followers_count += isFollowing ? -1 : 1;
      render();
    }
  }

  async function likePost(postId, btn) {
    const data = await api('/api/social/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId }),
    });
    if (data.ok) {
      btn.classList.toggle('liked', data.liked);
      btn.querySelector('.like-count').textContent = data.likes_count;
    }
  }

  document.addEventListener('DOMContentLoaded', load);

  return { toggleFollow, likePost };
})();
