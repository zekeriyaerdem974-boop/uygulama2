/* ═══════════════════════════════════════════════════════════════════
   alerts.js — ZKR Analiz v2 Alert System Frontend (FAZ 20)
   ═══════════════════════════════════════════════════════════════════ */
;(function(){
  'use strict';

  const API = '/api/alerts';
  const POLL_INTERVAL = 5000;

  const CONDITION_LABELS = {
    price_above:  { icon: '📈', label: 'Fiyat Üstünde' },
    price_below:  { icon: '📉', label: 'Fiyat Altında' },
    rsi_above:    { icon: '⚡', label: 'RSI Üstünde' },
    rsi_below:    { icon: '💤', label: 'RSI Altında' },
    ema_cross:    { icon: '✂️', label: 'EMA Kesişim' },
    breakout:     { icon: '🚀', label: 'Kırılım' },
    volume_spike: { icon: '🔊', label: 'Hacim Patlaması' }
  };

  let pollTimer = null;
  let seenTriggeredIds = new Set();

  const $ = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  /* ── Init ────────────────────────────────────────────────────── */
  function init(){
    bindEvents();
    loadAlerts();
    loadTriggered();
    startPolling();
  }

  /* ── Events ──────────────────────────────────────────────────── */
  function bindEvents(){
    const btnNew    = $('#btnCreateAlert');
    const btnCancel = $('#btnCancelAlert');
    const btnSave   = $('#btnSaveAlert');

    if(btnNew)    btnNew.addEventListener('click', toggleForm);
    if(btnCancel) btnCancel.addEventListener('click', toggleForm);
    if(btnSave)   btnSave.addEventListener('click', handleCreate);

    $$('.alerts-tab').forEach(tab => {
      tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
  }

  /* ── Form Toggle ─────────────────────────────────────────────── */
  function toggleForm(){
    const wrap = $('#alertFormWrap');
    if(wrap) wrap.classList.toggle('hidden');
  }

  /* ── Tab Switching ───────────────────────────────────────────── */
  function switchTab(tabId){
    $$('.alerts-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
    const activeId = tabId === 'triggered' ? 'triggeredAlertsWrap' : 'activeAlertsWrap';
    $$('.alerts-table-wrap').forEach(w => w.classList.toggle('hidden', w.id !== activeId));
    if(tabId === 'triggered') loadTriggered();
  }

  /* ── Create Alert ────────────────────────────────────────────── */
  async function handleCreate(e){
    if(e) e.preventDefault();
    const symbol    = $('#alertSymbol').value.trim().toUpperCase();
    const market    = $('#alertMarket').value;
    const condType  = $('#alertCondition').value;
    const condValue = parseFloat($('#alertValue').value);

    if(!symbol || isNaN(condValue)){
      showToast('⚠️', 'Hata', 'Sembol ve değer alanları zorunludur.');
      return;
    }

    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          symbol, market,
          condition_type: condType,
          condition_value: condValue
        })
      });
      const data = await res.json();
      if(res.ok){
        showToast('✅', 'Alarm Oluşturuldu', symbol + ' — ' + (CONDITION_LABELS[condType]?.label || condType));
        toggleForm();
        // reset inputs
        const sym = $('#alertSymbol'); if(sym) sym.value = '';
        const val = $('#alertValue');  if(val) val.value = '';
        loadAlerts();
      } else {
        showToast('❌', 'Hata', data.error || 'Alarm oluşturulamadı');
      }
    } catch(err){
      showToast('❌', 'Bağlantı Hatası', err.message);
    }
  }

  /* ── Load Active Alerts ──────────────────────────────────────── */
  async function loadAlerts(){
    try {
      const res = await fetch(API);
      const data = await res.json();
      renderActiveTable(data.alerts || []);
      const countEl = $('#alertCount');
      if(countEl) countEl.textContent = (data.alerts || []).length + ' alarm';
    } catch(e) {
      console.warn('loadAlerts error:', e);
    }
  }

  function renderActiveTable(alerts){
    const tbody = $('#alertsBody');
    if(!tbody) return;

    if(alerts.length === 0){
      tbody.innerHTML = '<tr class="alert-empty-row"><td colspan="7">Henüz alarm oluşturulmadı</td></tr>';
      return;
    }

    tbody.innerHTML = alerts.map(a => {
      const cond = CONDITION_LABELS[a.condition_type] || { icon: '🔔', label: a.condition_type };
      const statusCls = a.status === 'active' ? 'active' : (a.status === 'triggered' ? 'triggered' : 'inactive');
      const created = new Date(a.created_at).toLocaleString('tr-TR');
      return '<tr data-id="' + a.id + '">'
        + '<td><strong>' + a.symbol + '</strong></td>'
        + '<td>' + a.market + '</td>'
        + '<td><span class="alert-condition"><span class="cond-icon">' + cond.icon + '</span> ' + cond.label + '</span></td>'
        + '<td>' + a.condition_value + '</td>'
        + '<td><span class="alert-status ' + statusCls + '">' + a.status + '</span></td>'
        + '<td>' + created + '</td>'
        + '<td><button class="alert-btn-delete" onclick="AlertsApp.deleteAlert(\'' + a.id + '\')">Sil</button></td>'
        + '</tr>';
    }).join('');
  }

  /* ── Delete Alert ────────────────────────────────────────────── */
  async function deleteAlert(id){
    try {
      const res = await fetch(API + '/' + id, { method: 'DELETE' });
      if(res.ok){
        showToast('🗑️', 'Alarm Silindi', 'Alarm başarıyla kaldırıldı.');
        loadAlerts();
      }
    } catch(e){
      showToast('❌', 'Hata', e.message);
    }
  }

  /* ── Load Triggered ──────────────────────────────────────────── */
  async function loadTriggered(){
    try {
      const res = await fetch(API + '/triggered');
      const data = await res.json();
      const alerts = data.triggered || [];
      renderTriggeredTable(alerts);

      alerts.forEach(a => {
        const key = a.id + '_' + a.triggered_at;
        if(!seenTriggeredIds.has(key)){
          seenTriggeredIds.add(key);
          const cond = CONDITION_LABELS[a.condition_type] || { icon:'🔔', label: a.condition_type };
          showToast('🔔', a.symbol + ' Alarm Tetiklendi!',
            cond.label + ': ' + a.condition_value + ' → Fiyat: ' + a.trigger_price, 8000);
        }
      });
    } catch(e) {
      console.warn('loadTriggered error:', e);
    }
  }

  function renderTriggeredTable(alerts){
    const tbody = $('#triggeredBody');
    if(!tbody) return;

    if(alerts.length === 0){
      tbody.innerHTML = '<tr class="alert-empty-row"><td colspan="5">Tetiklenen alarm yok</td></tr>';
      return;
    }

    tbody.innerHTML = alerts.map(a => {
      const cond = CONDITION_LABELS[a.condition_type] || { icon:'🔔', label: a.condition_type };
      const time = new Date(a.triggered_at).toLocaleString('tr-TR');
      const price = a.trigger_price != null ? a.trigger_price : '—';
      return '<tr>'
        + '<td><strong>' + a.symbol + '</strong></td>'
        + '<td><span class="alert-condition"><span class="cond-icon">' + cond.icon + '</span> ' + cond.label + '</span></td>'
        + '<td>' + a.condition_value + '</td>'
        + '<td>' + price + '</td>'
        + '<td>' + time + '</td>'
        + '</tr>';
    }).join('');
  }

  /* ── Polling ─────────────────────────────────────────────────── */
  function startPolling(){
    if(pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
      loadTriggered();
      loadAlerts();
    }, POLL_INTERVAL);
  }

  /* ── Toast Notification ──────────────────────────────────────── */
  function showToast(icon, title, msg, duration){
    duration = duration || 5000;
    let container = $('.alert-toast-container');
    if(!container){
      container = document.createElement('div');
      container.className = 'alert-toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'alert-toast';
    toast.innerHTML = '<span class="toast-icon">' + icon + '</span>'
      + '<div class="toast-content">'
      + '<div class="toast-title">' + title + '</div>'
      + '<div class="toast-msg">' + msg + '</div>'
      + '<div class="toast-time">' + new Date().toLocaleTimeString('tr-TR') + '</div>'
      + '</div>'
      + '<button class="toast-close" onclick="this.closest(\'.alert-toast\').remove()">×</button>';

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('removing');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /* ── Public API ──────────────────────────────────────────────── */
  window.AlertsApp = {
    init,
    deleteAlert,
    showToast,
    loadAlerts,
    loadTriggered
  };

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
