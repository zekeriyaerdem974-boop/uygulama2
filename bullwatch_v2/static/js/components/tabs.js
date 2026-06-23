/**
 * ZKR Analiz Pro — Tabs Component
 * Auto-initializes .pro-tabs containers.
 * Each .pro-tab should have data-tab="tabId" and corresponding .pro-tab-pane#tabId
 */
const ProTabs = (function() {
  'use strict';

  function init(scope) {
    const root = scope || document;
    root.querySelectorAll('.pro-tabs').forEach(function(tabBar) {
      if (tabBar._proTabs) return;
      tabBar._proTabs = true;

      tabBar.addEventListener('click', function(e) {
        const tab = e.target.closest('.pro-tab');
        if (!tab) return;

        const tabId = tab.getAttribute('data-tab');
        const container = tabBar.closest('[data-tab-container]') || tabBar.parentElement;

        // Deactivate all tabs in this group
        tabBar.querySelectorAll('.pro-tab').forEach(function(t) {
          t.classList.remove('active');
        });
        tab.classList.add('active');

        // Show/hide panes
        if (tabId) {
          container.querySelectorAll('.pro-tab-pane').forEach(function(pane) {
            pane.classList.remove('active');
            pane.style.display = 'none';
          });
          var pane = container.querySelector('#' + CSS.escape(tabId)) ||
                     container.querySelector('[data-tab-pane="' + tabId + '"]');
          if (pane) {
            pane.classList.add('active');
            pane.style.display = '';
          }
        }

        // Fire custom event
        tabBar.dispatchEvent(new CustomEvent('tab-change', {
          detail: { tabId: tabId, tab: tab },
          bubbles: true
        }));
      });
    });
  }

  function activate(tabBarSelector, tabId) {
    var tabBar = document.querySelector(tabBarSelector);
    if (!tabBar) return;
    var tab = tabBar.querySelector('[data-tab="' + tabId + '"]');
    if (tab) tab.click();
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { init(); });
  } else {
    init();
  }

  return { init: init, activate: activate };
})();

window.ProTabs = ProTabs;
