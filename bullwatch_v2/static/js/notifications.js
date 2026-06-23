/**
 * ZKR Analiz Pro — Notification Center
 * Manages real-time notifications, unread count, and panel population.
 */
const ProNotifications = (function() {
  'use strict';

  const MAX_NOTIFICATIONS = 50;
  let notifications = [];
  let unreadCount = 0;
  let currentFilter = 'all';
  let pollInterval = null;

  // DOM refs
  const els = {};

  function initElements() {
    els.panel = document.getElementById('notifPanel');
    els.list = document.getElementById('notifList');
    els.dot = document.getElementById('notifDot');
    els.btn = document.getElementById('notifBtn');
  }

  function init() {
    initElements();
    loadFromStorage();
    render();
    startPolling();

    // Filter buttons
    document.querySelectorAll('.pro-notif-filter').forEach(function(btn) {
      btn.addEventListener('click', function() {
        currentFilter = this.getAttribute('data-filter') || 'all';
        document.querySelectorAll('.pro-notif-filter').forEach(function(b) {
          b.classList.remove('active');
        });
        this.classList.add('active');
        render();
      });
    });
  }

  function add(notification) {
    const n = Object.assign({
      id: Date.now() + Math.random().toString(36).substr(2, 5),
      type: 'info',       // alerts, opportunities, signals, info
      title: '',
      message: '',
      time: new Date().toISOString(),
      read: false,
      action: null         // { url: '/...', label: 'View' }
    }, notification);

    notifications.unshift(n);
    if (notifications.length > MAX_NOTIFICATIONS) {
      notifications = notifications.slice(0, MAX_NOTIFICATIONS);
    }
    unreadCount = notifications.filter(function(x) { return !x.read; }).length;
    updateDot();
    saveToStorage();
    render();

    // Show toast for new items
    if (window.ProToast) {
      var toastType = n.type === 'alerts' ? 'warning' : n.type === 'opportunities' ? 'success' : 'info';
      ProToast[toastType](n.title || n.message, { duration: 3000 });
    }
  }

  function markRead(id) {
    notifications.forEach(function(n) {
      if (n.id === id) n.read = true;
    });
    unreadCount = notifications.filter(function(x) { return !x.read; }).length;
    updateDot();
    saveToStorage();
    render();
  }

  function markAllRead() {
    notifications.forEach(function(n) { n.read = true; });
    unreadCount = 0;
    updateDot();
    saveToStorage();
    render();
  }

  function clearAll() {
    notifications = [];
    unreadCount = 0;
    updateDot();
    saveToStorage();
    render();
  }

  function updateDot() {
    if (!els.dot) return;
    els.dot.style.display = unreadCount > 0 ? '' : 'none';
    if (unreadCount > 0) {
      els.dot.textContent = unreadCount > 9 ? '9+' : unreadCount;
    }
  }

  function render() {
    if (!els.list) return;

    var filtered = currentFilter === 'all'
      ? notifications
      : notifications.filter(function(n) { return n.type === currentFilter; });

    if (filtered.length === 0) {
      els.list.innerHTML = '<div class="pro-notif-empty">No notifications yet</div>';
      return;
    }

    var html = '';
    filtered.forEach(function(n) {
      var timeAgo = formatTimeAgo(n.time);
      var icon = getTypeIcon(n.type);
      var readClass = n.read ? ' read' : '';

      html += '<div class="pro-notif-item' + readClass + '" data-notif-id="' + n.id + '">';
      html += '  <div class="pro-notif-icon pro-notif-icon-' + n.type + '">' + icon + '</div>';
      html += '  <div class="pro-notif-body">';
      html += '    <div class="pro-notif-title">' + escapeHtml(n.title) + '</div>';
      if (n.message) {
        html += '    <div class="pro-notif-msg">' + escapeHtml(n.message) + '</div>';
      }
      html += '    <div class="pro-notif-time">' + timeAgo + '</div>';
      html += '  </div>';
      if (n.action && n.action.url) {
        html += '  <a href="' + escapeHtml(n.action.url) + '" class="pro-notif-action">' + escapeHtml(n.action.label || 'View') + '</a>';
      }
      html += '</div>';
    });

    els.list.innerHTML = html;

    // Click to mark read
    els.list.querySelectorAll('.pro-notif-item').forEach(function(item) {
      item.addEventListener('click', function() {
        var id = this.getAttribute('data-notif-id');
        markRead(id);
      });
    });
  }

  function getTypeIcon(type) {
    var paths = {
      alerts: 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z',
      opportunities: 'M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z',
      signals: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z',
      info: 'M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z'
    };
    var d = paths[type] || paths.info;
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="' + d + '" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  function formatTimeAgo(isoStr) {
    var diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function saveToStorage() {
    try {
      localStorage.setItem('pro_notifications', JSON.stringify(notifications.slice(0, 20)));
    } catch(e) {}
  }

  function loadFromStorage() {
    try {
      var stored = localStorage.getItem('pro_notifications');
      if (stored) {
        notifications = JSON.parse(stored);
        unreadCount = notifications.filter(function(x) { return !x.read; }).length;
      }
    } catch(e) {}
  }

  function startPolling() {
    // Poll server for new notifications every 30s
    pollInterval = setInterval(function() {
      fetch('/api/notifications/unread', { credentials: 'same-origin' })
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
          if (data && data.notifications) {
            data.notifications.forEach(function(n) {
              // Avoid duplicates
              var exists = notifications.some(function(x) { return x.id === n.id; });
              if (!exists) add(n);
            });
          }
        })
        .catch(function() {}); // Silently fail
    }, 30000);
  }

  function stopPolling() {
    if (pollInterval) clearInterval(pollInterval);
  }

  // Auto-init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  return {
    add: add,
    markRead: markRead,
    markAllRead: markAllRead,
    clearAll: clearAll,
    getUnreadCount: function() { return unreadCount; },
    getAll: function() { return notifications; },
    stopPolling: stopPolling
  };
})();

window.ProNotifications = ProNotifications;
