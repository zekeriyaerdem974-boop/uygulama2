/* ═══════════════════════════════════════════════════════════════════
   ZKR Analiz Pro — Mobile Navigation Enhancements (FAZ 43)
   Auto-hides bottom bar on scroll, sidebar overlay close,
   haptic-style feedback, active state management
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  var bottomBar = document.getElementById('proBottombar');
  var sidebar   = document.getElementById('proSidebar');
  var _lastScrollY = 0;
  var _ticking = false;

  /* ── Auto-hide bottom bar on scroll down ─────────────────────── */
  function onScroll() {
    if (_ticking) return;
    _ticking = true;
    requestAnimationFrame(function () {
      var y = window.scrollY;
      if (bottomBar) {
        if (y > _lastScrollY && y > 100) {
          bottomBar.classList.add('bb-hidden');
        } else {
          bottomBar.classList.remove('bb-hidden');
        }
      }
      _lastScrollY = y;
      _ticking = false;
    });
  }

  if (window.innerWidth <= 1024) {
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ── Close sidebar when clicking outside on mobile ───────────── */
  document.addEventListener('click', function (e) {
    if (!sidebar || window.innerWidth > 1024) return;
    if (sidebar.classList.contains('mobile-open') &&
        !sidebar.contains(e.target) &&
        !e.target.closest('#mobileMenuBtn')) {
      sidebar.classList.remove('mobile-open');
    }
  });

  /* ── Swipe-to-close sidebar ──────────────────────────────────── */
  (function () {
    var startX = 0;
    var tracking = false;

    if (!sidebar) return;

    sidebar.addEventListener('touchstart', function (e) {
      startX = e.touches[0].clientX;
      tracking = true;
    }, { passive: true });

    sidebar.addEventListener('touchend', function (e) {
      if (!tracking) return;
      tracking = false;
      var dx = e.changedTouches[0].clientX - startX;
      if (dx < -60 && sidebar.classList.contains('mobile-open')) {
        sidebar.classList.remove('mobile-open');
      }
    }, { passive: true });
  })();

  /* ── Orientation change handling ─────────────────────────────── */
  window.addEventListener('orientationchange', function () {
    // Close sidebar on orientation change
    if (sidebar) sidebar.classList.remove('mobile-open');
    // Re-evaluate bottom bar visibility
    if (bottomBar) bottomBar.classList.remove('bb-hidden');
  });

  /* ── Add CSS for auto-hide animation ─────────────────────────── */
  var style = document.createElement('style');
  style.textContent =
    '.pro-bottombar{transition:transform 0.3s ease}' +
    '.pro-bottombar.bb-hidden{transform:translateY(100%)}';
  document.head.appendChild(style);

})();
