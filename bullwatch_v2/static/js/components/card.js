/**
 * ZKR Analiz Pro — Card Component
 * Handles expand/collapse/refresh actions on .pro-card elements
 */
const ProCard = (function() {
  'use strict';

  function init(scope) {
    const root = scope || document;

    // Collapse toggle
    root.querySelectorAll('[data-card-collapse]').forEach(function(btn) {
      if (btn._proCard) return;
      btn._proCard = true;
      btn.addEventListener('click', function() {
        const card = btn.closest('.pro-card');
        if (!card) return;
        card.classList.toggle('collapsed');
        const body = card.querySelector('.pro-card-body');
        if (body) {
          body.style.display = card.classList.contains('collapsed') ? 'none' : '';
        }
        // Rotate icon
        const icon = btn.querySelector('svg, .collapse-icon');
        if (icon) {
          icon.style.transform = card.classList.contains('collapsed') ? 'rotate(-90deg)' : '';
        }
      });
    });

    // Expand (fullscreen)
    root.querySelectorAll('[data-card-expand]').forEach(function(btn) {
      if (btn._proCard) return;
      btn._proCard = true;
      btn.addEventListener('click', function() {
        const card = btn.closest('.pro-card');
        if (!card) return;
        card.classList.toggle('card-expanded');
        if (card.classList.contains('card-expanded')) {
          card.style.position = 'fixed';
          card.style.top = '0';
          card.style.left = '0';
          card.style.right = '0';
          card.style.bottom = '0';
          card.style.zIndex = '9999';
          card.style.borderRadius = '0';
          card.style.margin = '0';
          document.body.style.overflow = 'hidden';
        } else {
          card.style.position = '';
          card.style.top = '';
          card.style.left = '';
          card.style.right = '';
          card.style.bottom = '';
          card.style.zIndex = '';
          card.style.borderRadius = '';
          card.style.margin = '';
          document.body.style.overflow = '';
        }
      });
    });

    // Refresh
    root.querySelectorAll('[data-card-refresh]').forEach(function(btn) {
      if (btn._proCard) return;
      btn._proCard = true;
      btn.addEventListener('click', function() {
        const card = btn.closest('.pro-card');
        if (!card) return;
        const event = new CustomEvent('card-refresh', { bubbles: true, detail: { card: card } });
        card.dispatchEvent(event);
        // Visual feedback
        const icon = btn.querySelector('svg');
        if (icon) {
          icon.style.animation = 'ds-spin 0.6s linear';
          setTimeout(function() { icon.style.animation = ''; }, 600);
        }
      });
    });
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { init(); });
  } else {
    init();
  }

  return { init: init };
})();

window.ProCard = ProCard;
