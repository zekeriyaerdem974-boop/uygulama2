/**
 * ZKR Analiz i18n — FAZ 52 + FAZ 61 + FAZ 61B
 * Client-side internationalization support.
 *
 * Usage:
 *   await BW.i18n.load('tr');
 *   BW.i18n.t('sidebar.discover');  // → "Keşfet"
 *   BW.i18n.refresh();              // Re-render all data-i18n elements
 */
(function () {
  'use strict';

  window.BW = window.BW || {};

  var _LS_KEY = 'bw_lang';
  var _fallbackLocale = {};

  var i18n = {
    _locale: {},
    _lang: 'tr',
    _loaded: false,

    /**
     * Load translations for a language code.
     * Also loads en.json as fallback if lang is not en.
     */
    async load(lang) {
      if (!lang) lang = localStorage.getItem(_LS_KEY) || 'tr';
      try {
        // Load fallback (en) if switching away from en
        if (lang !== 'en' && Object.keys(_fallbackLocale).length === 0) {
          try {
            var fbResp = await fetch('/api/settings/locale/en');
            if (fbResp.ok) {
              var fbData = await fbResp.json();
              if (fbData.ok && fbData.translations) _fallbackLocale = fbData.translations;
            }
          } catch(e) {}
        }
        var resp = await fetch('/api/settings/locale/' + encodeURIComponent(lang));
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();
        if (data.ok && data.translations) {
          this._locale = data.translations;
          this._lang = lang;
          this._loaded = true;
          localStorage.setItem(_LS_KEY, lang);
          document.documentElement.lang = lang;
          if (lang === 'ar') {
            document.documentElement.dir = 'rtl';
            document.body.classList.add('rtl');
          } else {
            document.documentElement.dir = 'ltr';
            document.body.classList.remove('rtl');
          }
          this.refresh();
          return this._locale;
        }
      } catch (e) {
        console.warn('[i18n] Failed to load locale:', lang, e);
      }
      return {};
    },

    /**
     * Translate a key. Fallback chain: current locale → en locale → fallback arg → key.
     * Never returns undefined or null.
     */
    t: function(key, fallback) {
      if (!key) return fallback || '';
      var val = this._locale ? this._locale[key] : null;
      if (val) return val;
      // Fallback to en
      if (_fallbackLocale[key]) return _fallbackLocale[key];
      return fallback || key;
    },

    /** Current language code */
    get lang() { return this._lang; },

    /** Whether translations are loaded */
    get loaded() { return this._loaded; },

    /** All current translations */
    get locale() { return this._locale; },

    /**
     * Refresh all elements with data-i18n attributes.
     * Handles: textContent, placeholder, title, tooltip, aria-label, data-tip, innerHTML.
     */
    refresh: function() {
      var self = this;

      document.querySelectorAll('[data-i18n]').forEach(function(el) {
        var key = el.getAttribute('data-i18n');
        if (!key) return;
        var val = self.t(key);
        if (val && val !== key) el.textContent = val;
      });

      document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-placeholder');
        var val = self.t(key);
        if (val && val !== key) el.placeholder = val;
      });

      document.querySelectorAll('[data-i18n-title]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-title');
        var val = self.t(key);
        if (val && val !== key) el.title = val;
      });

      document.querySelectorAll('[data-i18n-tooltip]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-tooltip');
        var val = self.t(key);
        if (val && val !== key) el.setAttribute('data-tooltip', val);
      });

      document.querySelectorAll('[data-i18n-tip]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-tip');
        var val = self.t(key);
        if (val && val !== key) el.setAttribute('data-tip', val);
      });

      document.querySelectorAll('[data-i18n-html]').forEach(function(el) {
        var key = el.getAttribute('data-i18n-html');
        var val = self.t(key);
        if (val && val !== key) el.innerHTML = val;
      });
    },

    /**
     * Change language: update settings + reload translations.
     * Shows toast feedback to user.
     */
    async setLanguage(lang) {
      try {
        localStorage.setItem(_LS_KEY, lang);
        fetch('/api/settings/language', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language_code: lang }),
        }).catch(function() {});
        fetch('/api/settings/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language: lang }),
        }).catch(function() {});
        await this.load(lang);
        // Show language-change toast feedback
        this._showToast(this.t('settings.saved', 'Language updated'));
        return true;
      } catch (e) {
        console.warn('[i18n] setLanguage failed:', e);
        return false;
      }
    },

    /**
     * Show a brief toast notification.
     */
    _showToast: function(msg) {
      var existing = document.getElementById('bw-i18n-toast');
      if (existing) existing.remove();
      var toast = document.createElement('div');
      toast.id = 'bw-i18n-toast';
      toast.textContent = msg;
      toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(10px);padding:10px 24px;background:#10b981;color:#fff;border-radius:8px;font-size:13px;font-weight:600;z-index:99999;opacity:0;transition:all .3s;pointer-events:none;white-space:nowrap;';
      document.body.appendChild(toast);
      requestAnimationFrame(function() {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(-50%) translateY(0)';
      });
      setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-50%) translateY(10px)';
        setTimeout(function() { toast.remove(); }, 300);
      }, 2200);
    },
  };

  BW.i18n = i18n;

  // Auto-init on page load
  document.addEventListener('DOMContentLoaded', function() {
    var lang = localStorage.getItem(_LS_KEY)
      || document.documentElement.lang
      || 'tr';
    BW.i18n.load(lang);
  });
})();
