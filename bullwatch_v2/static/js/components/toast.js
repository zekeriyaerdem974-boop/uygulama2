/**
 * ZKR Analiz Pro — Toast Notification System
 * Usage: ProToast.success('Saved!'), ProToast.danger('Error'), ProToast.warning('Warning'), ProToast.info('Info')
 */
const ProToast = (function() {
  'use strict';

  const DEFAULTS = { duration: 4000, position: 'top-right' };
  let container = null;

  function getContainer() {
    if (container) return container;
    container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.className = 'pro-toast-container';
      container.id = 'toastContainer';
      document.body.appendChild(container);
    }
    return container;
  }

  function show(message, type, options) {
    const opts = Object.assign({}, DEFAULTS, options);
    const el = document.createElement('div');
    el.className = 'pro-toast pro-toast-' + type + ' toast-enter';

    const iconPath = {
      success: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
      danger:  'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
      warning: 'M12 9v3.75m0 3.75h.008M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
      info:    'M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z'
    };

    el.innerHTML =
      '<svg class="pro-toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">' +
        '<path d="' + (iconPath[type] || iconPath.info) + '" stroke-linecap="round" stroke-linejoin="round"/>' +
      '</svg>' +
      '<span class="pro-toast-msg">' + escapeHtml(message) + '</span>' +
      '<button class="pro-toast-dismiss" aria-label="Close">&times;</button>';

    el.querySelector('.pro-toast-dismiss').addEventListener('click', function() {
      dismiss(el);
    });

    getContainer().appendChild(el);

    // Auto dismiss
    const timer = setTimeout(function() { dismiss(el); }, opts.duration);
    el._timer = timer;

    return el;
  }

  function dismiss(el) {
    if (!el || !el.parentNode) return;
    clearTimeout(el._timer);
    el.classList.remove('toast-enter');
    el.classList.add('toast-exit');
    el.addEventListener('animationend', function() {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, { once: true });
    // Fallback removal
    setTimeout(function() {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 500);
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  return {
    success: function(msg, opts) { return show(msg, 'success', opts); },
    danger:  function(msg, opts) { return show(msg, 'danger', opts); },
    error:   function(msg, opts) { return show(msg, 'danger', opts); },
    warning: function(msg, opts) { return show(msg, 'warning', opts); },
    info:    function(msg, opts) { return show(msg, 'info', opts); },
    show: show,
    dismiss: dismiss
  };
})();

// Global alias
window.ProToast = ProToast;
