/**
 * ZKR Analiz Pro — Tooltip Component
 * Auto-initializes elements with [data-tooltip].
 */
const ProTooltip = (function() {
  'use strict';

  let active = null;

  function init(scope) {
    const root = scope || document;
    root.querySelectorAll('[data-tooltip]').forEach(function(el) {
      if (el._proTooltip) return;
      el._proTooltip = true;
      el.addEventListener('mouseenter', show);
      el.addEventListener('mouseleave', hide);
      el.addEventListener('focus', show);
      el.addEventListener('blur', hide);
    });
  }

  function show(e) {
    const el = e.currentTarget;
    const text = el.getAttribute('data-tooltip');
    if (!text) return;

    hide(); // remove any existing

    const tip = document.createElement('div');
    tip.className = 'pro-tooltip';
    tip.textContent = text;
    document.body.appendChild(tip);

    const rect = el.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();

    // Position above by default, centered
    let top = rect.top - tipRect.height - 8;
    let left = rect.left + (rect.width / 2) - (tipRect.width / 2);

    // If overflowing top, show below
    if (top < 4) {
      top = rect.bottom + 8;
    }
    // Keep within viewport horizontally
    if (left < 4) left = 4;
    if (left + tipRect.width > window.innerWidth - 4) {
      left = window.innerWidth - tipRect.width - 4;
    }

    tip.style.top = top + 'px';
    tip.style.left = left + 'px';
    active = tip;
  }

  function hide() {
    if (active && active.parentNode) {
      active.parentNode.removeChild(active);
    }
    active = null;
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { init(); });
  } else {
    init();
  }

  return { init: init, show: show, hide: hide };
})();

window.ProTooltip = ProTooltip;
