/**
 * ZKR Analiz Pro — Market Heatmap Widget
 * Creates a heatmap grid from market data.
 * Usage: ProHeatmap.render('#container', data)
 */
const ProHeatmap = (function() {
  'use strict';

  function render(containerSelector, data, options) {
    const container = typeof containerSelector === 'string'
      ? document.querySelector(containerSelector)
      : containerSelector;
    if (!container) return;

    const opts = Object.assign({
      valueKey: 'change_percent',
      labelKey: 'symbol',
      subLabelKey: 'price',
      onClick: null,
      columns: 6
    }, options);

    container.innerHTML = '';
    container.className = 'pro-heatmap';
    container.style.gridTemplateColumns = 'repeat(' + opts.columns + ', 1fr)';

    if (!data || data.length === 0) {
      container.innerHTML = '<div class="pro-empty"><p class="pro-empty-title">No data available</p></div>';
      return;
    }

    data.forEach(function(item) {
      var cell = document.createElement('div');
      cell.className = 'pro-heatmap-cell ' + getHeatClass(item[opts.valueKey]);

      var val = parseFloat(item[opts.valueKey]) || 0;
      var sign = val >= 0 ? '+' : '';

      cell.innerHTML =
        '<div class="hm-symbol">' + escapeHtml(item[opts.labelKey] || '') + '</div>' +
        '<div class="hm-value">' + sign + val.toFixed(2) + '%</div>';

      if (item[opts.subLabelKey]) {
        cell.innerHTML += '<div class="hm-price">' + escapeHtml(String(item[opts.subLabelKey])) + '</div>';
      }

      if (typeof opts.onClick === 'function') {
        cell.style.cursor = 'pointer';
        cell.addEventListener('click', function() { opts.onClick(item); });
      }

      container.appendChild(cell);
    });
  }

  function getHeatClass(val) {
    var v = parseFloat(val) || 0;
    if (v >= 5) return 'hm-strong-up';
    if (v >= 2) return 'hm-up';
    if (v >= 0.5) return 'hm-slight-up';
    if (v > -0.5) return 'hm-neutral';
    if (v > -2) return 'hm-slight-down';
    if (v > -5) return 'hm-down';
    return 'hm-strong-down';
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  return { render: render };
})();

window.ProHeatmap = ProHeatmap;
