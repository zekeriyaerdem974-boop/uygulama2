/* ═══════════════════════════════════════════════════════════════════
   ZKR Analiz Pro — PWA Install Prompt (FAZ 43)
   Captures beforeinstallprompt, shows install banner/button
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  let _deferredPrompt = null;
  const DISMISS_KEY = 'bw_pwa_install_dismissed';
  const DISMISS_DAYS = 14;

  // Check if user recently dismissed
  function isDismissed() {
    try {
      const ts = localStorage.getItem(DISMISS_KEY);
      if (!ts) return false;
      return (Date.now() - parseInt(ts, 10)) < DISMISS_DAYS * 86400000;
    } catch (e) { return false; }
  }

  function setDismissed() {
    try { localStorage.setItem(DISMISS_KEY, Date.now().toString()); } catch (e) {}
  }

  // Create install banner
  function createBanner() {
    if (document.getElementById('pwaInstallBanner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwaInstallBanner';
    banner.className = 'pwa-install-banner';
    banner.innerHTML =
      '<div class="pwa-install-content">' +
        '<div class="pwa-install-icon">' +
          '<img src="/static/icon.svg" alt="ZKR Analiz" width="40" height="40">' +
        '</div>' +
        '<div class="pwa-install-text">' +
          '<strong>Install ZKR Analiz Pro</strong>' +
          '<span>Add to home screen for the full experience</span>' +
        '</div>' +
        '<div class="pwa-install-actions">' +
          '<button class="pwa-install-btn" id="pwaInstallAccept">Install</button>' +
          '<button class="pwa-install-dismiss" id="pwaInstallDismiss">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M6 18L18 6M6 6l12 12" stroke-linecap="round"/></svg>' +
          '</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(banner);

    // Animate in
    requestAnimationFrame(function () {
      banner.classList.add('visible');
    });

    document.getElementById('pwaInstallAccept').addEventListener('click', doInstall);
    document.getElementById('pwaInstallDismiss').addEventListener('click', dismissBanner);
  }

  function dismissBanner() {
    var b = document.getElementById('pwaInstallBanner');
    if (b) {
      b.classList.remove('visible');
      setTimeout(function () { b.remove(); }, 400);
    }
    setDismissed();
  }

  function doInstall() {
    if (!_deferredPrompt) return;
    _deferredPrompt.prompt();
    _deferredPrompt.userChoice.then(function (result) {
      if (result.outcome === 'accepted') {
        dismissBanner();
      }
      _deferredPrompt = null;
    });
  }

  // Also wire up any manual install button in the sidebar
  function wireManualButton() {
    var btn = document.getElementById('pwaInstallSidebarBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      if (_deferredPrompt) {
        doInstall();
      } else {
        if (typeof ProToast !== 'undefined') {
          ProToast.show('App already installed or not available', 'info');
        }
      }
    });
  }

  // Capture the install prompt
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    _deferredPrompt = e;

    // Show banner if not dismissed and not already installed
    if (!isDismissed() && !window.matchMedia('(display-mode: standalone)').matches) {
      // Delay slightly so page renders first
      setTimeout(createBanner, 2000);
    }

    // Show sidebar button
    var btn = document.getElementById('pwaInstallSidebarBtn');
    if (btn) btn.style.display = '';
  });

  // Hide if installed
  window.addEventListener('appinstalled', function () {
    dismissBanner();
    _deferredPrompt = null;
    var btn = document.getElementById('pwaInstallSidebarBtn');
    if (btn) btn.style.display = 'none';
  });

  // On load
  document.addEventListener('DOMContentLoaded', wireManualButton);

  // Expose for external use
  window.BWPwaInstall = {
    prompt: doInstall,
    isAvailable: function () { return !!_deferredPrompt; },
    dismiss: dismissBanner
  };
})();
