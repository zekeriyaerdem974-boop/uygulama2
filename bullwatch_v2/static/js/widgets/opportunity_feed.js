/**
 * ZKR Analiz Pro — Opportunity Feed Widget
 * Live-updating opportunity list with animation.
 */
const ProOpportunityFeed = (function() {
  'use strict';

  function render(containerSelector, opportunities, options) {
    const container = typeof containerSelector === 'string'
      ? document.querySelector(containerSelector)
      : containerSelector;
    if (!container) return;

    const opts = Object.assign({
      maxItems: 10,
      onClick: null,
      showConfidence: true
    }, options);

    container.className = 'pro-opp-feed';

    if (!opportunities || opportunities.length === 0) {
      container.innerHTML = '<div class="pro-empty"><p class="pro-empty-title">No opportunities found</p></div>';
      return;
    }

    const items = opportunities.slice(0, opts.maxItems);
    container.innerHTML = '';

    items.forEach(function(opp, idx) {
      var el = document.createElement('div');
      el.className = 'pro-opp-feed-item stagger-item';
      el.style.animationDelay = (idx * 50) + 'ms';

      var typeClass = getTypeClass(opp.type || opp.signal_type || '');
      var conf = parseFloat(opp.confidence || opp.score || 0);

      var html = '<div class="pro-opp-feed-icon ' + typeClass + '">' + getTypeIcon(opp.type || opp.signal_type || '') + '</div>';
      html += '<div class="pro-opp-feed-body">';
      html += '  <div class="pro-opp-feed-title">' + escapeHtml(opp.symbol || opp.title || '') + '</div>';
      html += '  <div class="pro-opp-feed-desc">' + escapeHtml(opp.description || opp.reason || '') + '</div>';
      html += '</div>';

      if (opts.showConfidence && conf > 0) {
        var confClass = conf >= 80 ? 'top' : conf >= 60 ? 'high' : conf >= 40 ? 'med' : 'low';
        html += '<span class="pro-badge-' + (conf >= 60 ? 'success' : conf >= 40 ? 'warning' : 'neutral') + '">' + Math.round(conf) + '%</span>';
      }

      el.innerHTML = html;

      if (typeof opts.onClick === 'function') {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function() { opts.onClick(opp); });
      }

      container.appendChild(el);
    });
  }

  function getTypeClass(type) {
    var t = (type || '').toLowerCase();
    if (t.includes('buy') || t.includes('long') || t.includes('bullish')) return 'type-bullish';
    if (t.includes('sell') || t.includes('short') || t.includes('bearish')) return 'type-bearish';
    return 'type-neutral';
  }

  function getTypeIcon(type) {
    var t = (type || '').toLowerCase();
    if (t.includes('buy') || t.includes('long') || t.includes('bullish')) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M7 17l9.2-9.2M17 17V8H8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    }
    if (t.includes('sell') || t.includes('short') || t.includes('bearish')) {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M17 7l-9.2 9.2M7 7v9h9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><path d="M8 12h8" stroke-linecap="round"/></svg>';
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  return { render: render };
})();

window.ProOpportunityFeed = ProOpportunityFeed;
