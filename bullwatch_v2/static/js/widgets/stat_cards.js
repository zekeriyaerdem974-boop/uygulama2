/**
 * ZKR Analiz Pro — Stat Card Widget
 * Creates animated stat/KPI cards.
 */
const ProStatCard = (function() {
  'use strict';

  function render(containerSelector, stats) {
    const container = typeof containerSelector === 'string'
      ? document.querySelector(containerSelector)
      : containerSelector;
    if (!container) return;

    container.innerHTML = '';

    stats.forEach(function(stat, idx) {
      var card = document.createElement('div');
      card.className = 'pro-stat-card stagger-item';
      card.style.animationDelay = (idx * 60) + 'ms';

      var change = parseFloat(stat.change || 0);
      var changeSign = change >= 0 ? '+' : '';
      var changeClass = change >= 0 ? 'val-positive' : 'val-negative';
      var changeIcon = change >= 0
        ? '<svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12"><path fill-rule="evenodd" d="M12.577 4.878a.75.75 0 01.919-.53l4.78 1.281a.75.75 0 01.531.919l-1.281 4.78a.75.75 0 01-1.449-.387l.81-3.022a19.407 19.407 0 00-5.594 5.203.75.75 0 01-1.139.093L7 10.06l-4.72 4.72a.75.75 0 01-1.06-1.06l5.25-5.25a.75.75 0 011.06 0l3.074 3.073a20.923 20.923 0 015.545-4.93l-3.043.815a.75.75 0 01-.53-.919z" clip-rule="evenodd"/></svg>'
        : '<svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12"><path fill-rule="evenodd" d="M1.22 5.222a.75.75 0 011.06 0L7 9.942l3.768-3.769a.75.75 0 011.113.058 20.908 20.908 0 013.813 7.254l1.574-2.727a.75.75 0 011.3.75l-2.475 4.286a.75.75 0 01-1.025.275l-4.287-2.475a.75.75 0 01.75-1.3l2.71 1.565a19.422 19.422 0 00-3.013-5.554L7.53 12.22a.75.75 0 01-1.06 0l-5.25-5.25a.75.75 0 010-1.06z" clip-rule="evenodd"/></svg>';

      card.innerHTML =
        '<div class="pro-stat-label">' + escapeHtml(stat.label || '') + '</div>' +
        '<div class="pro-stat-value">' + escapeHtml(String(stat.value || '0')) + '</div>' +
        (stat.change !== undefined
          ? '<div class="pro-stat-change ' + changeClass + '">' + changeIcon + ' ' + changeSign + change.toFixed(2) + '%</div>'
          : '') +
        (stat.icon ? '<div class="pro-stat-icon">' + stat.icon + '</div>' : '');

      container.appendChild(card);
    });
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  return { render: render };
})();

window.ProStatCard = ProStatCard;
