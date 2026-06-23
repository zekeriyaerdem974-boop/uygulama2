/* ═══════════════════════════════════════════════════════════════════
   ZKR Analiz Pro — Mobile Bottom Sheet Component (FAZ 43)
   Touch-draggable bottom sheet for mobile detail views
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  function MobileSheet(options) {
    options = options || {};
    this.id = options.id || 'mobileSheet_' + Date.now();
    this.title = options.title || '';
    this.onClose = options.onClose || null;

    this._overlay = null;
    this._sheet = null;
    this._startY = 0;
    this._currentY = 0;
    this._dragging = false;

    this._build();
  }

  MobileSheet.prototype._build = function () {
    // Overlay
    this._overlay = document.createElement('div');
    this._overlay.className = 'mobile-sheet-overlay';
    this._overlay.addEventListener('click', this.close.bind(this));

    // Sheet
    this._sheet = document.createElement('div');
    this._sheet.className = 'mobile-sheet';
    this._sheet.id = this.id;
    this._sheet.innerHTML =
      '<div class="mobile-sheet-handle"></div>' +
      '<div class="mobile-sheet-header">' +
        '<span class="mobile-sheet-title">' + this._escapeHtml(this.title) + '</span>' +
        '<button class="mobile-sheet-close" aria-label="Close">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M6 18L18 6M6 6l12 12" stroke-linecap="round"/></svg>' +
        '</button>' +
      '</div>' +
      '<div class="mobile-sheet-body"></div>';

    this._sheet.querySelector('.mobile-sheet-close').addEventListener('click', this.close.bind(this));

    // Touch drag on handle
    var handle = this._sheet.querySelector('.mobile-sheet-handle');
    handle.addEventListener('touchstart', this._onTouchStart.bind(this), { passive: true });
    handle.addEventListener('touchmove', this._onTouchMove.bind(this), { passive: false });
    handle.addEventListener('touchend', this._onTouchEnd.bind(this), { passive: true });

    document.body.appendChild(this._overlay);
    document.body.appendChild(this._sheet);
  };

  MobileSheet.prototype._escapeHtml = function (str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  };

  MobileSheet.prototype.open = function () {
    var self = this;
    requestAnimationFrame(function () {
      self._overlay.classList.add('open');
      self._sheet.classList.add('open');
      self._sheet.style.transform = '';
      document.body.style.overflow = 'hidden';
    });
  };

  MobileSheet.prototype.close = function () {
    var self = this;
    this._overlay.classList.remove('open');
    this._sheet.classList.remove('open');
    this._sheet.style.transform = '';
    document.body.style.overflow = '';
    if (this.onClose) {
      setTimeout(function () { self.onClose(); }, 350);
    }
  };

  MobileSheet.prototype.setContent = function (html) {
    this._sheet.querySelector('.mobile-sheet-body').innerHTML = html;
  };

  MobileSheet.prototype.setTitle = function (title) {
    this._sheet.querySelector('.mobile-sheet-title').textContent = title;
  };

  MobileSheet.prototype.getBody = function () {
    return this._sheet.querySelector('.mobile-sheet-body');
  };

  MobileSheet.prototype.destroy = function () {
    this.close();
    var self = this;
    setTimeout(function () {
      if (self._overlay && self._overlay.parentNode) self._overlay.remove();
      if (self._sheet && self._sheet.parentNode) self._sheet.remove();
    }, 400);
  };

  // Touch drag
  MobileSheet.prototype._onTouchStart = function (e) {
    this._dragging = true;
    this._startY = e.touches[0].clientY;
    this._sheet.style.transition = 'none';
  };

  MobileSheet.prototype._onTouchMove = function (e) {
    if (!this._dragging) return;
    this._currentY = e.touches[0].clientY - this._startY;
    if (this._currentY < 0) this._currentY = 0; // don't drag up past origin
    this._sheet.style.transform = 'translateY(' + this._currentY + 'px)';
    if (this._currentY > 10) e.preventDefault();
  };

  MobileSheet.prototype._onTouchEnd = function () {
    this._dragging = false;
    this._sheet.style.transition = '';
    // If dragged more than 100px down, close
    if (this._currentY > 100) {
      this.close();
    } else {
      this._sheet.style.transform = '';
    }
    this._currentY = 0;
  };

  // Factory
  window.MobileSheet = MobileSheet;
})();
