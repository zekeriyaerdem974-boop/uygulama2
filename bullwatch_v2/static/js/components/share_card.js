/**
 * share_card.js — FAZ 44 Share Card Component
 *
 * Usage:
 *   BW.ShareCard.open({ contentType, contentId, title, description })
 */
(function(root){
  'use strict';

  const ShareCard = {};

  /**
   * Open a share card overlay for the given content.
   * @param {Object} opts
   * @param {string} opts.contentType  — analysis|portfolio|activity|mentor|strategy|course
   * @param {string} opts.contentId    — ID of the content
   * @param {string} opts.title        — Share title
   * @param {string} opts.description  — Share description
   */
  ShareCard.open = async function(opts){
    const {contentType, contentId, title, description} = opts || {};
    if(!contentType || !contentId) return;

    /* Generate share URL via API */
    let shareData = null;
    try {
      const r = await fetch('/api/share/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content_type: contentType, content_id: contentId, title: title||'', description: description||''})
      });
      const d = await r.json();
      if(d.ok) shareData = d.data;
    } catch(e){ console.error('ShareCard generate error', e); }

    if(!shareData || !shareData.card) return;
    const card = shareData.card;
    const shareUrl = location.origin + (shareData.url || '');

    /* Build overlay */
    const overlay = document.createElement('div');
    overlay.className = 'bw-share-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:16px;';
    overlay.addEventListener('click', function(e){ if(e.target === overlay) overlay.remove(); });

    const modal = document.createElement('div');
    modal.style.cssText = 'background:#111;border-radius:16px;border:1px solid rgba(255,255,255,0.08);max-width:400px;width:100%;padding:24px;position:relative;';

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'position:absolute;top:12px;right:14px;background:none;border:none;color:#6b7280;font-size:18px;cursor:pointer;';
    closeBtn.onclick = function(){ overlay.remove(); };

    const headerEl = document.createElement('div');
    headerEl.style.cssText = 'text-align:center;margin-bottom:16px;';
    headerEl.innerHTML = '<div style="font-size:24px;margin-bottom:6px;">' + _esc(card.icon || '🔗') + '</div>'
      + '<div style="font-size:16px;font-weight:700;color:#e5e7eb;">' + _esc(card.title || 'Share') + '</div>'
      + '<div style="font-size:12px;color:#6b7280;margin-top:4px;">' + _esc(card.description || '') + '</div>';

    /* Link */
    const linkRow = document.createElement('div');
    linkRow.style.cssText = 'display:flex;gap:8px;background:rgba(0,0,0,0.3);border-radius:10px;padding:10px;margin-bottom:16px;';
    const linkInput = document.createElement('input');
    linkInput.type = 'text';
    linkInput.readOnly = true;
    linkInput.value = shareUrl;
    linkInput.style.cssText = 'flex:1;background:none;border:none;color:#e5e7eb;font-size:12px;font-family:monospace;outline:none;';
    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.style.cssText = 'background:#2979FF;color:#fff;border:none;border-radius:8px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;';
    copyBtn.onclick = function(){
      navigator.clipboard.writeText(shareUrl).then(function(){
        copyBtn.textContent = 'Copied!';
        setTimeout(function(){ copyBtn.textContent = 'Copy'; }, 2000);
      });
    };
    linkRow.appendChild(linkInput);
    linkRow.appendChild(copyBtn);

    /* Social buttons */
    const socials = document.createElement('div');
    socials.style.cssText = 'display:flex;gap:10px;justify-content:center;flex-wrap:wrap;';

    const shareText = encodeURIComponent((card.title || 'Check this out') + ' on ZKR Analiz Pro');
    const encodedUrl = encodeURIComponent(shareUrl);

    const platforms = card.platforms || {};
    const btnData = [
      {label: 'Twitter / X', color: '#1DA1F2', bg: 'rgba(29,155,240,0.12)', href: platforms.twitter || ('https://twitter.com/intent/tweet?text=' + shareText + '&url=' + encodedUrl)},
      {label: 'Telegram', color: '#0088CC', bg: 'rgba(0,136,204,0.12)', href: platforms.telegram || ('https://t.me/share/url?url=' + encodedUrl + '&text=' + shareText)},
      {label: 'WhatsApp', color: '#25D366', bg: 'rgba(37,211,102,0.12)', href: platforms.whatsapp || ('https://wa.me/?text=' + shareText + '%20' + encodedUrl)}
    ];

    btnData.forEach(function(b){
      const a = document.createElement('a');
      a.href = b.href;
      a.target = '_blank';
      a.rel = 'noopener';
      a.textContent = b.label;
      a.style.cssText = 'padding:10px 18px;border-radius:10px;font-weight:600;font-size:13px;text-decoration:none;color:' + b.color + ';background:' + b.bg + ';';
      socials.appendChild(a);
    });

    modal.appendChild(closeBtn);
    modal.appendChild(headerEl);
    modal.appendChild(linkRow);
    modal.appendChild(socials);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  };

  function _esc(s){
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  /* Export */
  root.BW = root.BW || {};
  root.BW.ShareCard = ShareCard;

})(typeof window !== 'undefined' ? window : this);
