/**
 * ZKR Analiz Pro — Ticker Tape Widget
 * Scrolling ticker bar for market data.
 */
const ProTickerTape = (function() {
  'use strict';

  function render(containerSelector, tickers, options) {
    const container = typeof containerSelector === 'string'
      ? document.querySelector(containerSelector)
      : containerSelector;
    if (!container) return;

    const opts = Object.assign({
      speed: 30,    // seconds for full scroll
      onClick: null
    }, options);

    container.className = 'pro-ticker-tape';

    if (!tickers || tickers.length === 0) return;

    var inner = document.createElement('div');
    inner.className = 'pro-ticker-inner';
    inner.style.animation = 'ticker-scroll ' + opts.speed + 's linear infinite';

    // Duplicate items for seamless loop
    var items = tickers.concat(tickers);

    items.forEach(function(t) {
      var el = document.createElement('span');
      el.className = 'pro-ticker-item';

      var change = parseFloat(t.change_percent || t.change || 0);
      var sign = change >= 0 ? '+' : '';
      var cls = change >= 0 ? 'val-positive' : 'val-negative';

      el.innerHTML =
        '<span class="pro-ticker-symbol">' + escapeHtml(t.symbol || '') + '</span>' +
        '<span class="pro-ticker-price">' + escapeHtml(String(t.price || '')) + '</span>' +
        '<span class="' + cls + '">' + sign + change.toFixed(2) + '%</span>';

      if (typeof opts.onClick === 'function') {
        el.style.cursor = 'pointer';
        el.addEventListener('click', function() { opts.onClick(t); });
      }

      inner.appendChild(el);
    });

    container.innerHTML = '';
    container.appendChild(inner);

    // Pause on hover
    container.addEventListener('mouseenter', function() {
      inner.style.animationPlayState = 'paused';
    });
    container.addEventListener('mouseleave', function() {
      inner.style.animationPlayState = 'running';
    });
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  return { render: render };
})();

window.ProTickerTape = ProTickerTape;
