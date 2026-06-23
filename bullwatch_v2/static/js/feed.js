/* =====================================================================
   ZKR Analiz Social Feed — FAZ 31
   ===================================================================== */
window.SF = (function () {
  'use strict';

  let currentTab = 'global';
  let offset = 0;
  let loading = false;
  let hasMore = true;
  let pendingSnapshot = null;

  // ── Helpers ─────────────────────────────────────────────────────
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

  async function api(url, opts) {
    const r = await fetch(url, opts);
    return r.json();
  }

  // ── Tab Switching ───────────────────────────────────────────────
  function switchTab(tab) {
    currentTab = tab;
    offset = 0;
    hasMore = true;
    document.querySelectorAll('.sf-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.feed === tab);
    });
    $('sfFeed').innerHTML = '<div class="sf-loading">Yükleniyor…</div>';
    loadFeed();
  }

  // ── Load Feed ───────────────────────────────────────────────────
  async function loadFeed(append) {
    if (loading) return;
    loading = true;

    try {
      let url;
      if (currentTab === 'trending') {
        url = '/api/social/feed?type=global&limit=20&offset=0';
      } else {
        url = `/api/social/feed?type=${currentTab}&limit=20&offset=${offset}`;
      }
      const data = await api(url);

      if (!data.ok) {
        $('sfFeed').innerHTML = '<div class="sf-empty">Feed yüklenemedi</div>';
        return;
      }

      let posts = data.posts || [];

      // Sort trending by likes
      if (currentTab === 'trending') {
        posts.sort((a, b) => (b.likes_count || 0) - (a.likes_count || 0));
      }

      if (!append) {
        $('sfFeed').innerHTML = '';
      }

      if (posts.length === 0 && offset === 0) {
        $('sfFeed').innerHTML = '<div class="sf-empty">' +
          (currentTab === 'following' ? 'Takip ettiğiniz kişilerin paylaşımı yok' : 'Henüz paylaşım yok') +
          '</div>';
        hasMore = false;
        return;
      }

      posts.forEach(p => $('sfFeed').appendChild(renderCard(p)));
      offset += posts.length;
      hasMore = posts.length >= 20;
    } catch (e) {
      if (!append) $('sfFeed').innerHTML = '<div class="sf-empty">Bağlantı hatası</div>';
    } finally {
      loading = false;
    }
  }

  // ── Render Post Card ────────────────────────────────────────────
  function renderCard(post) {
    const card = document.createElement('div');
    card.className = 'sf-card';
    card.id = 'post-' + post.id;

    let symbolBadge = '';
    if (post.symbol) {
      symbolBadge = `<span class="sf-symbol-badge">${post.symbol}${post.timeframe ? ' · ' + post.timeframe : ''}</span>`;
    }

    let chartHtml = '';
    if (post.chart_snapshot) {
      chartHtml = `<img class="sf-chart-img" src="${post.chart_snapshot}" alt="chart snapshot" loading="lazy" />`;
    }

    let mentorBadge = '';
    if (post.is_mentor) {
      mentorBadge = '<span style="display:inline-flex;align-items:center;gap:3px;font-size:10px;padding:1px 6px;border-radius:8px;background:#f59e0b18;color:#fbbf24;border:1px solid #f59e0b33;margin-left:6px;vertical-align:middle;">🎓 Mentor</span>';
    }

    card.innerHTML = `
      <div class="sf-card-header">
        <a href="/user/${post.username}" class="sf-avatar">${avatarLetter(post.username)}</a>
        <div class="sf-user-info">
          <a href="${post.is_mentor ? '/mentor/' : '/user/'}${post.username}" class="sf-username">${post.username}${mentorBadge}</a>
          <div class="sf-time">${timeAgo(post.created_at)} ${symbolBadge}</div>
        </div>
      </div>
      <div class="sf-content">${escapeHtml(post.content)}</div>
      ${chartHtml}
      <div class="sf-actions">
        <button class="sf-action ${post.is_liked ? 'liked' : ''}" onclick="SF.toggleLike('${post.id}', this)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
          <span class="like-count">${post.likes_count || 0}</span>
        </button>
        <button class="sf-action" onclick="SF.toggleComments('${post.id}')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
          <span>${post.comments_count || 0}</span>
        </button>
      </div>
      <div id="comments-${post.id}" style="display:none"></div>
    `;
    return card;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ── Like ────────────────────────────────────────────────────────
  async function toggleLike(postId, btn) {
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

  // ── Comments ────────────────────────────────────────────────────
  async function toggleComments(postId) {
    const container = $('comments-' + postId);
    if (!container) return;

    if (container.style.display !== 'none') {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    container.innerHTML = '<div class="sf-loading" style="padding:10px">Yükleniyor…</div>';

    const data = await api('/api/social/post/' + postId);
    if (!data.ok) return;

    let html = '<div class="sf-comments">';
    (data.comments || []).forEach(c => {
      html += `
        <div class="sf-comment">
          <div class="sf-comment-avatar">${avatarLetter(c.username)}</div>
          <div class="sf-comment-body">
            <span class="sf-comment-user">${c.username}</span>
            <div class="sf-comment-text">${escapeHtml(c.content)}</div>
          </div>
        </div>`;
    });
    html += '</div>';
    html += `
      <div class="sf-comment-input-wrap">
        <input class="sf-comment-input" id="ci-${postId}" placeholder="Yorum yazın…" onkeydown="if(event.key==='Enter')SF.sendComment('${postId}')" />
        <button class="sf-comment-send" onclick="SF.sendComment('${postId}')">Gönder</button>
      </div>`;
    container.innerHTML = html;
  }

  async function sendComment(postId) {
    const input = $('ci-' + postId);
    if (!input || !input.value.trim()) return;

    const data = await api('/api/social/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postId, content: input.value.trim() }),
    });
    if (data.ok) {
      input.value = '';
      toggleComments(postId); // Close
      setTimeout(() => toggleComments(postId), 100); // Reopen to refresh
    }
  }

  // ── New Post Modal ──────────────────────────────────────────────
  function openNewPost(snapshot, symbol, timeframe) {
    $('sfNewPostModal').classList.add('open');
    $('sfPostContent').value = '';
    $('sfPostSymbol').value = symbol || '';
    $('sfPostTimeframe').value = timeframe || '1h';

    pendingSnapshot = snapshot || null;
    const preview = $('sfChartPreview');
    if (snapshot) {
      $('sfChartPreviewImg').src = snapshot;
      preview.style.display = 'block';
    } else {
      preview.style.display = 'none';
    }
  }

  function closeNewPost() {
    $('sfNewPostModal').classList.remove('open');
    pendingSnapshot = null;
  }

  async function submitPost() {
    const content = ($('sfPostContent').value || '').trim();
    if (!content) return alert('İçerik gerekli');

    const body = {
      content: content,
      symbol: $('sfPostSymbol').value.trim() || null,
      market: $('sfPostMarket').value.trim() || null,
      timeframe: $('sfPostTimeframe').value.trim() || null,
      chart_snapshot: pendingSnapshot,
    };

    const data = await api('/api/social/post', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (data.ok) {
      closeNewPost();
      switchTab('global'); // Refresh
    } else {
      alert(data.error || 'Paylaşılamadı');
    }
  }

  // ── Infinite Scroll ─────────────────────────────────────────────
  window.addEventListener('scroll', () => {
    if (!hasMore || loading) return;
    const scrollBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
    if (scrollBottom < 200) {
      loadFeed(true);
    }
  });

  // ── Init ────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    // Check if we have a shared chart snapshot from trade page
    try {
      const shared = sessionStorage.getItem('bw_share_chart');
      if (shared) {
        const d = JSON.parse(shared);
        sessionStorage.removeItem('bw_share_chart');
        openNewPost(d.snapshot, d.symbol, d.timeframe);
      }
    } catch (e) {}

    loadFeed();
  });

  return { switchTab, toggleLike, toggleComments, sendComment, openNewPost, closeNewPost, submitPost };
})();
