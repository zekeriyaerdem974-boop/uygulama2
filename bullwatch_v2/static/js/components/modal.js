/**
 * ZKR Analiz Pro — Modal Component
 * Usage: ProModal.open({title, body, footer, size, onClose})
 */
const ProModal = (function() {
  'use strict';

  let activeModal = null;

  function open(options) {
    const opts = Object.assign({ title: '', body: '', footer: '', size: 'md', closable: true }, options);

    close(); // close any existing

    const overlay = document.createElement('div');
    overlay.className = 'pro-modal-overlay modal-enter';

    const modal = document.createElement('div');
    modal.className = 'pro-modal pro-modal-' + opts.size;

    let html = '<div class="pro-modal-header">';
    html += '<h3 class="pro-modal-title">' + opts.title + '</h3>';
    if (opts.closable) {
      html += '<button class="pro-modal-close" aria-label="Close">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18"><path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
      '</button>';
    }
    html += '</div>';
    html += '<div class="pro-modal-body">' + opts.body + '</div>';
    if (opts.footer) {
      html += '<div class="pro-modal-footer">' + opts.footer + '</div>';
    }
    modal.innerHTML = html;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Bind close
    if (opts.closable) {
      modal.querySelector('.pro-modal-close').addEventListener('click', close);
      overlay.addEventListener('click', function(e) {
        if (e.target === overlay) close();
      });
      document.addEventListener('keydown', handleEsc);
    }

    activeModal = { overlay: overlay, onClose: opts.onClose };
    return { overlay: overlay, modal: modal, close: close };
  }

  function close() {
    if (!activeModal) return;
    const overlay = activeModal.overlay;
    const onClose = activeModal.onClose;
    overlay.classList.remove('modal-enter');
    overlay.classList.add('modal-exit');
    document.body.style.overflow = '';
    document.removeEventListener('keydown', handleEsc);
    overlay.addEventListener('animationend', function() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, { once: true });
    setTimeout(function() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, 400);
    activeModal = null;
    if (typeof onClose === 'function') onClose();
  }

  function handleEsc(e) {
    if (e.key === 'Escape') close();
  }

  function confirm(options) {
    const opts = Object.assign({
      title: 'Confirm',
      message: 'Are you sure?',
      confirmText: 'Confirm',
      cancelText: 'Cancel',
      confirmClass: 'pro-btn-primary',
      onConfirm: null,
      onCancel: null
    }, options);

    return open({
      title: opts.title,
      body: '<p style="color:var(--text-secondary);line-height:1.6">' + opts.message + '</p>',
      footer:
        '<button class="pro-btn-ghost pro-modal-cancel">' + opts.cancelText + '</button>' +
        '<button class="' + opts.confirmClass + ' pro-modal-confirm">' + opts.confirmText + '</button>',
      onClose: opts.onCancel,
      size: 'sm'
    });
  }

  // Attach confirm button handlers after DOM is ready
  document.addEventListener('click', function(e) {
    if (e.target.matches('.pro-modal-confirm')) {
      close();
    }
    if (e.target.matches('.pro-modal-cancel')) {
      close();
    }
  });

  return { open: open, close: close, confirm: confirm };
})();

window.ProModal = ProModal;
