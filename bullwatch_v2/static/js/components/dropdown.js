/**
 * ZKR Analiz Pro — Dropdown Component
 * Auto-initializes elements with [data-dropdown-toggle].
 * Usage: ProDropdown.init() or auto via DOMContentLoaded
 */
const ProDropdown = (function() {
  'use strict';

  function init(scope) {
    const root = scope || document;
    root.querySelectorAll('[data-dropdown-toggle]').forEach(function(btn) {
      if (btn._proDropdown) return; // already initialized
      btn._proDropdown = true;
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        const targetId = btn.getAttribute('data-dropdown-toggle');
        const menu = document.getElementById(targetId);
        if (!menu) return;
        const wasOpen = menu.classList.contains('open');
        closeAll();
        if (!wasOpen) {
          menu.classList.add('open');
          positionMenu(btn, menu);
        }
      });
    });
  }

  function positionMenu(btn, menu) {
    const rect = btn.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    // Position below the button, right-aligned
    if (rect.bottom + menuRect.height > window.innerHeight) {
      menu.style.bottom = '100%';
      menu.style.top = 'auto';
    }
  }

  function closeAll() {
    document.querySelectorAll('.pro-dropdown.open').forEach(function(el) {
      el.classList.remove('open');
    });
  }

  // Close on outside click
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.pro-dropdown') && !e.target.closest('[data-dropdown-toggle]')) {
      closeAll();
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeAll();
  });

  // Auto-init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { init(); });
  } else {
    init();
  }

  return { init: init, closeAll: closeAll };
})();

window.ProDropdown = ProDropdown;
