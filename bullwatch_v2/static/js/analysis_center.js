/* =====================================================================
   ZKR Analiz — Analiz Merkezi (Analysis Center) Bottom Sheet  — FAZ 24C
   Fully functional: connects to real systems, disables non-ready items
   ===================================================================== */
'use strict';

const AnalysisCenter = (() => {

  /* ── SVG Icons for analysis cards ─────────────────────────────── */
  const IC = {
    layout:      `<svg viewBox="0 0 28 28"><rect x="3" y="3" width="10" height="22" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="15" y="3" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="15" y="15" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    manage:      `<svg viewBox="0 0 28 28"><rect x="4" y="6" width="20" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="11" x2="24" y2="11" stroke="currentColor" stroke-width="1"/><circle cx="9" cy="8.5" r="1" fill="currentColor"/><circle cx="13" cy="8.5" r="1" fill="currentColor"/><circle cx="17" cy="8.5" r="1" fill="currentColor"/></svg>`,
    new_file:    `<svg viewBox="0 0 28 28"><path d="M8,4 h8 l6,6 v14 a2,2 0 0,1 -2,2 h-12 a2,2 0 0,1 -2,-2 v-18 a2,2 0 0,1 2,-2z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><polyline points="16,4 16,10 22,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><line x1="14" y1="15" x2="14" y2="21" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="11" y1="18" x2="17" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    save:        `<svg viewBox="0 0 28 28"><path d="M6,4 h14 l4,4 v16 a2,2 0 0,1 -2,2 h-16 a2,2 0 0,1 -2,-2 v-18 a2,2 0 0,1 2,-2z" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="9" y="4" width="10" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><rect x="8" y="16" width="12" height="8" rx="1" fill="none" stroke="currentColor" stroke-width="1"/></svg>`,
    open:        `<svg viewBox="0 0 28 28"><path d="M4,8 a2,2 0 0,1 2,-2 h5 l3,3 h8 a2,2 0 0,1 2,2 v0 h-16 l-3,10 h16 l3,-10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    indicators:  `<svg viewBox="0 0 28 28"><path d="M4,20 Q8,8 14,14 Q20,20 24,8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="20" r="1.5" fill="currentColor"/><circle cx="24" cy="8" r="1.5" fill="currentColor"/></svg>`,
    compare:     `<svg viewBox="0 0 28 28"><polyline points="4,20 10,10 16,16 24,6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="4,22 8,16 14,20 20,12 24,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity=".5"/></svg>`,
    alarm:       `<svg viewBox="0 0 28 28"><path d="M14,4 C9,4 6,8 6,13 L4,20 h20 l-2,-7 C22,8 19,4 14,4z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><line x1="14" y1="2" x2="14" y2="4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M11,20 Q11,24 14,24 Q17,24 17,20" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    replay:      `<svg viewBox="0 0 28 28"><rect x="4" y="8" width="3" height="12" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><rect x="9" y="6" width="3" height="14" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><rect x="14" y="10" width="3" height="10" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><rect x="19" y="4" width="3" height="16" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><path d="M19,22 L24,22 L21.5,26z" fill="currentColor"/></svg>`,
    template:    `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="10" x2="24" y2="10" stroke="currentColor" stroke-width="1"/><line x1="14" y1="10" x2="14" y2="24" stroke="currentColor" stroke-width="1"/><path d="M7,16 Q10,12 13,16" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>`,
    chart_type:  `<svg viewBox="0 0 28 28"><rect x="5" y="10" width="4" height="8" rx="0.5" fill="none" stroke="currentColor" stroke-width="1.3"/><line x1="7" y1="8" x2="7" y2="10" stroke="currentColor" stroke-width="1.3"/><line x1="7" y1="18" x2="7" y2="20" stroke="currentColor" stroke-width="1.3"/><rect x="12" y="6" width="4" height="12" rx="0.5" fill="none" stroke="currentColor" stroke-width="1.3"/><line x1="14" y1="4" x2="14" y2="6" stroke="currentColor" stroke-width="1.3"/><line x1="14" y1="18" x2="14" y2="22" stroke="currentColor" stroke-width="1.3"/><rect x="19" y="8" width="4" height="10" rx="0.5" fill="none" stroke="currentColor" stroke-width="1.3"/><line x1="21" y1="6" x2="21" y2="8" stroke="currentColor" stroke-width="1.3"/><line x1="21" y1="18" x2="21" y2="24" stroke="currentColor" stroke-width="1.3"/></svg>`,
    obj_tree:    `<svg viewBox="0 0 28 28"><circle cx="14" cy="6" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="7" cy="22" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="21" cy="22" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="12" y1="9" x2="8" y2="19" stroke="currentColor" stroke-width="1.5"/><line x1="16" y1="9" x2="20" y2="19" stroke="currentColor" stroke-width="1.5"/></svg>`,
    details:     `<svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/><text x="12.5" y="11" fill="currentColor" font-size="8" font-weight="700" font-family="sans-serif">i</text><line x1="14" y1="13" x2="14" y2="20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    financials:  `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="11" x2="24" y2="11" stroke="currentColor" stroke-width="1"/><line x1="8" y1="15" x2="12" y2="15" stroke="currentColor" stroke-width="1"/><line x1="8" y1="19" x2="16" y2="19" stroke="currentColor" stroke-width="1"/><line x1="16" y1="15" x2="20" y2="15" stroke="currentColor" stroke-width="1"/><text x="8" y="9" fill="currentColor" font-size="6" font-weight="600" font-family="sans-serif">$</text></svg>`,
    forecast:    `<svg viewBox="0 0 28 28"><polyline points="4,20 10,14 16,16 20,8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="20,8 26,4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="3,2"/></svg>`,
    technicals:  `<svg viewBox="0 0 28 28"><path d="M4,14 L8,8 L12,12 L16,6 L20,10 L24,4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="4" y1="22" x2="24" y2="22" stroke="currentColor" stroke-width="1"/><rect x="6" y="16" width="4" height="6" rx="0.5" fill="currentColor" opacity=".3"/><rect x="12" y="18" width="4" height="4" rx="0.5" fill="currentColor" opacity=".3"/><rect x="18" y="14" width="4" height="8" rx="0.5" fill="currentColor" opacity=".3"/></svg>`,
    publish:     `<svg viewBox="0 0 28 28"><path d="M14,4 L14,18 M8,10 L14,4 L20,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M4,18 v4 a2,2 0 0,0 2,2 h16 a2,2 0 0,0 2,-2 v-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    share:       `<svg viewBox="0 0 28 28"><circle cx="20" cy="7" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="14" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="20" cy="21" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="10.5" y1="12.5" x2="17.5" y2="8.5" stroke="currentColor" stroke-width="1.5"/><line x1="10.5" y1="15.5" x2="17.5" y2="19.5" stroke="currentColor" stroke-width="1.5"/></svg>`,
    pine:        `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><text x="7" y="16" fill="currentColor" font-size="9" font-weight="700" font-family="monospace">&lt;/&gt;</text></svg>`,
    multi:       `<svg viewBox="0 0 28 28"><rect x="3" y="3" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="15" y="3" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3" y="15" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="15" y="15" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    signals:     `<svg viewBox="0 0 28 28"><path d="M8,20 L8,12 L14,8 L20,12 L20,20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><line x1="14" y1="8" x2="14" y2="4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="14" cy="16" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="14" cy="16" r="1" fill="currentColor"/><path d="M5,22 Q5,14 14,6 Q23,14 23,22" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
    copilot:     `<svg viewBox="0 0 28 28"><circle cx="14" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8,16 Q8,24 14,24 Q20,24 20,16" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="11" cy="9" r="1.2" fill="currentColor"/><circle cx="17" cy="9" r="1.2" fill="currentColor"/><path d="M11,13 Q14,16 17,13" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>`,
    simulator:   `<svg viewBox="0 0 28 28"><rect x="4" y="6" width="20" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><polyline points="8,18 12,12 16,16 20,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M17,16 L21,10 L21,14" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    orderflow:   `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="8" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="16" y="8" width="8" height="16" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="14" x2="12" y2="14" stroke="currentColor" stroke-width="1"/><line x1="16" y1="16" x2="24" y2="16" stroke="currentColor" stroke-width="1"/></svg>`,
    liquidation: `<svg viewBox="0 0 28 28"><rect x="6" y="18" width="4" height="6" rx="0.5" fill="currentColor" opacity=".4"/><rect x="12" y="10" width="4" height="14" rx="0.5" fill="currentColor" opacity=".4"/><rect x="18" y="14" width="4" height="10" rx="0.5" fill="currentColor" opacity=".4"/><polyline points="4,16 10,8 16,12 24,4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="20,4 24,4 24,8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    news:        `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="8" y1="9" x2="20" y2="9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="8" y1="13" x2="18" y2="13" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><line x1="8" y1="17" x2="16" y2="17" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><line x1="8" y1="21" x2="14" y2="21" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>`,
    backtest:    `<svg viewBox="0 0 28 28"><path d="M6,14 A8,8 0 1,1 14,22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><polyline points="6,18 6,14 10,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="14" y1="10" x2="14" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="14" y1="14" x2="18" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  };

  /* ── Item status: working | disabled ──────────────────────────── */
  const DISABLED_ITEMS = new Set([
    'layout', 'manage', 'new', 'save', 'open',
    'replay', 'templates', 'backtest',
    'financials', 'forecast',
    'publish', 'share', 'pine', 'help', 'broker'
  ]);

  let isOpen = false;

  /* ═══════════════════════════════════════════════════════════════════
     Build DOM
     ═══════════════════════════════════════════════════════════════════ */
  function buildSheet() {
    if (document.getElementById('analysisSheet')) return;

    let ov = document.getElementById('drawerOverlay');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'drawerOverlay';
      ov.className = 'drawer-overlay';
      document.body.appendChild(ov);
    }

    const s = document.createElement('div');
    s.id = 'analysisSheet';
    s.className = 'analysis-sheet';
    s.innerHTML = buildHTML();
    document.body.appendChild(s);

    document.getElementById('acClose').addEventListener('click', close);

    s.querySelectorAll('.ac-card[data-action]').forEach(card => {
      card.addEventListener('click', () => handleCardAction(card.dataset.action));
    });

    setupDrag(s);
  }

  function buildHTML() {
    return `
      <div class="sheet-handle" id="acHandle"><div class="handle-bar"></div></div>
      <div class="sheet-header">
        <span class="sheet-title">Analiz merkezi</span>
        <button class="sheet-close-btn" id="acClose" aria-label="Kapat">
          <svg viewBox="0 0 24 24" width="20" height="20"><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="analysis-body">

        <!-- Top cards (disabled) -->
        <div class="ac-grid-2">
          ${card(IC.layout, 'Yerleşim kurulumu', 'layout')}
          ${card(IC.manage, 'Yönet', 'manage')}
        </div>
        <div class="ac-grid-3">
          ${card(IC.new_file, 'Yeni', 'new')}
          ${card(IC.save, 'Kaydet', 'save')}
          ${card(IC.open, 'Aç', 'open')}
        </div>

        <!-- ARAÇLAR -->
        <div class="ac-section-title">ARAÇLAR</div>
        <div class="ac-grid-2">
          ${card(IC.indicators, 'Göstergeler', 'indicators')}
          ${card(IC.compare, 'Karşılaştır', 'compare')}
        </div>
        <div class="ac-grid-2">
          ${card(IC.alarm, 'Alarmlar', 'alarms')}
          ${card(IC.chart_type, 'Grafik türü', 'chart_type')}
        </div>
        <div class="ac-grid-2">
          ${card(IC.obj_tree, 'Nesne Ağacı', 'obj_tree')}
          ${card(IC.replay, 'Çubuk Tekrarı', 'replay')}
        </div>

        <!-- ANALİZ -->
        <div class="ac-section-title">ANALİZ</div>
        <div class="ac-grid-2">
          ${card(IC.signals, 'Sinyaller', 'signals')}
          ${card(IC.orderflow, 'Orderflow', 'orderflow')}
        </div>
        <div class="ac-grid-2">
          ${card(IC.liquidation, 'Likidasyon', 'liquidation')}
          ${card(IC.copilot, 'AI Copilot', 'copilot')}
        </div>
        <div class="ac-grid-3">
          ${card(IC.simulator, 'Simülatör', 'simulator')}
          ${card(IC.backtest, 'Backtest', 'backtest')}
          ${card(IC.multi, 'Multi-Chart', 'multichart')}
        </div>

        <!-- BİLGİ -->
        <div class="ac-section-title">BİLGİ</div>
        <div class="ac-grid-2">
          ${card(IC.details, 'Sembol ayrıntıları', 'details')}
          ${card(IC.technicals, 'Teknikler', 'technicals')}
        </div>
        <div class="ac-grid-2">
          ${card(IC.financials, 'Finansallar', 'financials')}
          ${card(IC.forecast, 'Tahmin', 'forecast')}
        </div>

        <!-- DAHA FAZLASI -->
        <div class="ac-section-title">DAHA FAZLASI</div>
        <div class="ac-grid-2">
          ${card(IC.news, 'Haberler', 'news')}
          ${card(IC.template, 'Gösterge şabl.', 'templates')}
        </div>
        <div class="ac-grid-3">
          ${card(IC.publish, 'Fikir yayınla', 'publish')}
          ${card(IC.share, 'Paylaş', 'share')}
          ${card(IC.pine, 'Pine Editörü', 'pine')}
        </div>

      </div>
    `;
  }

  function card(icon, label, action) {
    const disabled = DISABLED_ITEMS.has(action);
    const cls = disabled ? 'ac-card ac-card-disabled' : 'ac-card';
    const badge = disabled ? '<span class="ac-soon-badge">Yakında</span>' : '';
    return `<div class="${cls}" data-action="${action}">
      <div class="ac-card-icon">${icon}</div>
      <div class="ac-card-label">${label}</div>
      ${badge}
    </div>`;
  }

  /* ═══════════════════════════════════════════════════════════════════
     Card Actions — connect to real systems
     ═══════════════════════════════════════════════════════════════════ */
  function handleCardAction(action) {
    if (DISABLED_ITEMS.has(action)) {
      _toast('\u{1F512}', 'Bu özellik yakında eklenecek');
      return;
    }

    close();

    switch (action) {
      /* ── WORKING: Tab switches ── */
      case 'signals':     _activateTab('signals');     break;
      case 'orderflow':   _activateTab('orderflow');   break;
      case 'liquidation': _activateTab('liquidation'); break;
      case 'copilot':     _activateTab('copilot');     break;
      case 'news':        _activateTab('news');        break;
      case 'simulator':   _activateTab('simulator');   break;

      /* ── WORKING: Direct features ── */
      case 'multichart':
        if (typeof MultiChartManager !== 'undefined') MultiChartManager.open?.();
        break;
      case 'alarms':
        window.location.href = '/alerts';
        break;

      /* ── FUNCTIONAL: Real connections ── */
      case 'indicators':  _openIndicatorDropdown(); break;
      case 'chart_type':  _openChartTypeSheet();    break;
      case 'obj_tree':    _openObjectTree();        break;
      case 'compare':     _openCompareSheet();      break;
      case 'details':     _openDetailsSheet();      break;
      case 'technicals':  _openTechnicalsSheet();   break;
    }

    window.dispatchEvent(new CustomEvent('bw:analysis-action', { detail: { action } }));
  }

  /* ── Tab Activation Helper ─────────────────────────────────────── */
  function _activateTab(tabName) {
    const tabBtn = document.querySelector('[data-tab="' + tabName + '"]');
    if (tabBtn) {
      tabBtn.click();
      const rp = document.querySelector('.panel-right');
      const grid = document.querySelector('.main-grid');
      if (rp && !rp.classList.contains('panel-open')) {
        rp.classList.add('panel-open');
        if (grid) grid.classList.add('rp-visible');
        setTimeout(function(){ window.dispatchEvent(new Event('resize')); }, 350);
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Indicators — toggle the existing dropdown
     ═══════════════════════════════════════════════════════════════════ */
  function _openIndicatorDropdown() {
    var dd = document.querySelector('.ind-dropdown');
    if (dd) {
      dd.classList.add('open');
      var autoClose = function(e) {
        if (!dd.contains(e.target)) {
          dd.classList.remove('open');
          document.removeEventListener('click', autoClose);
        }
      };
      setTimeout(function(){ document.addEventListener('click', autoClose); }, 50);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Chart Type — bottom sheet with real switching
     ═══════════════════════════════════════════════════════════════════ */
  function _openChartTypeSheet() {
    _removePanel('acChartTypePanel');
    var current = (typeof chartManager !== 'undefined' && chartManager.getChartType) ? chartManager.getChartType() : 'candlestick';
    var types = [
      { id: 'candlestick', label: 'Mum Grafik',  icon: '\u{1F56F}\uFE0F' },
      { id: 'line',        label: 'Çizgi',        icon: '\u{1F4C8}' },
      { id: 'area',        label: 'Alan',          icon: '\u{1F4CA}' },
      { id: 'bar',         label: 'Bar (OHLC)',    icon: '\u{1F4C9}' },
    ];

    var panel = document.createElement('div');
    panel.id = 'acChartTypePanel';
    panel.className = 'ac-mini-panel';
    panel.innerHTML =
      '<div class="ac-mp-header"><span>Grafik Türü</span><button class="ac-mp-close" aria-label="Kapat">\u2715</button></div>' +
      '<div class="ac-mp-body">' +
      types.map(function(t) {
        return '<div class="ac-mp-item' + (t.id === current ? ' active' : '') + '" data-type="' + t.id + '">' +
          '<span class="ac-mp-icon">' + t.icon + '</span>' +
          '<span class="ac-mp-label">' + t.label + '</span>' +
          (t.id === current ? '<span class="ac-mp-check">\u2713</span>' : '') +
          '</div>';
      }).join('') +
      '</div>';
    document.body.appendChild(panel);
    requestAnimationFrame(function(){ panel.classList.add('open'); });

    panel.querySelector('.ac-mp-close').onclick = function(){ _dismissPanel(panel); };
    panel.querySelectorAll('.ac-mp-item').forEach(function(item) {
      item.addEventListener('click', function() {
        var type = item.dataset.type;
        if (typeof chartManager !== 'undefined' && chartManager.setChartType) {
          chartManager.setChartType(type);
          var found = types.find(function(t){ return t.id === type; });
          _toast('\u2713', 'Grafik türü: ' + (found ? found.label : type));
        }
        _dismissPanel(panel);
      });
    });
  }

  /* ═══════════════════════════════════════════════════════════════════
     Object Tree — open drawing list from DrawingEngine
     ═══════════════════════════════════════════════════════════════════ */
  function _openObjectTree() {
    if (typeof DrawingEngine !== 'undefined' && DrawingEngine.toggleDrawingList) {
      DrawingEngine.toggleDrawingList();
    } else {
      _toast('\u{1F4D0}', 'Çizim motoru henüz başlatılmadı');
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Compare — MVP overlay second symbol on chart
     ═══════════════════════════════════════════════════════════════════ */
  var compareSeries = null;
  var compareSymbol = '';

  function _openCompareSheet() {
    _removePanel('acComparePanel');
    var panel = document.createElement('div');
    panel.id = 'acComparePanel';
    panel.className = 'ac-mini-panel';

    var statusHtml = compareSymbol
      ? '\u2713 Aktif: <strong>' + compareSymbol + '</strong> <button id="acCompareRemove" class="ac-mp-btn-sm">Kaldır</button>'
      : 'Karşılaştırma yok';

    panel.innerHTML =
      '<div class="ac-mp-header"><span>Karşılaştır</span><button class="ac-mp-close" aria-label="Kapat">\u2715</button></div>' +
      '<div class="ac-mp-body">' +
      '<div style="padding:4px 0 8px;font-size:11px;color:rgba(255,255,255,0.4)">İkinci bir sembol ekleyerek fiyat karşılaştırması yapın</div>' +
      '<div style="display:flex;gap:6px;margin-bottom:8px">' +
      '<input id="acCompareInput" class="ac-mp-input" placeholder="Sembol girin (ör: ETHUSDT)" autocomplete="off" spellcheck="false" style="flex:1"/>' +
      '<button id="acCompareAdd" class="ac-mp-btn-primary">Ekle</button>' +
      '</div>' +
      '<div id="acCompareStatus" style="font-size:11px;color:rgba(255,255,255,0.3)">' + statusHtml + '</div>' +
      '<div class="ac-mp-quick" style="margin-top:8px">' +
      '<span style="font-size:10px;color:rgba(255,255,255,0.3);margin-right:4px">Hızlı:</span>' +
      '<button class="ac-mp-chip" data-sym="ETHUSDT">ETH</button>' +
      '<button class="ac-mp-chip" data-sym="BNBUSDT">BNB</button>' +
      '<button class="ac-mp-chip" data-sym="SOLUSDT">SOL</button>' +
      '<button class="ac-mp-chip" data-sym="XRPUSDT">XRP</button>' +
      '</div></div>';

    document.body.appendChild(panel);
    requestAnimationFrame(function(){ panel.classList.add('open'); });

    panel.querySelector('.ac-mp-close').onclick = function(){ _dismissPanel(panel); };
    panel.querySelector('#acCompareAdd').onclick = function() {
      var inp = panel.querySelector('#acCompareInput');
      var sym = inp ? inp.value.trim().toUpperCase() : '';
      if (sym) { _addCompareSymbol(sym); _dismissPanel(panel); }
    };
    var removeBtn = panel.querySelector('#acCompareRemove');
    if (removeBtn) {
      removeBtn.addEventListener('click', function() {
        _removeCompareSymbol();
        _toast('\u2713', 'Karşılaştırma kaldırıldı');
        _dismissPanel(panel);
      });
    }
    panel.querySelectorAll('.ac-mp-chip').forEach(function(chip) {
      chip.addEventListener('click', function() {
        _addCompareSymbol(chip.dataset.sym);
        _dismissPanel(panel);
      });
    });
  }

  function _addCompareSymbol(symbol) {
    _removeCompareSymbol();
    var chart = (typeof chartManager !== 'undefined') ? chartManager.getChart() : null;
    if (!chart) return;
    try {
      var data = chartManager.getData();
      var tf = (data && data.interval) ? data.interval : '15m';
      var mc = (typeof getMarketConfig === 'function') ? getMarketConfig() : { klinesEndpoint: '/api/market/klines' };
      var qs = new URLSearchParams({ symbol: symbol, interval: tf, limit: '500' });
      fetch(mc.klinesEndpoint + '?' + qs)
        .then(function(r){ return r.json(); })
        .then(function(js) {
          var candles = js.candles || [];
          if (!candles.length) { _toast('\u26A0\uFE0F', 'Veri bulunamadı: ' + symbol); return; }
          compareSeries = chart.addLineSeries({
            color: '#f5a623', lineWidth: 2,
            priceScaleId: 'compare',
            lastValueVisible: true,
            crosshairMarkerVisible: true,
            title: symbol,
          });
          chart.priceScale('compare').applyOptions({
            scaleMargins: { top: 0.1, bottom: 0.1 },
            borderVisible: false,
            alignLabels: true,
          });
          compareSeries.setData(candles.map(function(c){ return { time: c.time, value: Number(c.close) }; }));
          compareSymbol = symbol;
          _toast('\u2713', symbol + ' eklendi');
        })
        .catch(function(e) {
          _toast('\u274C', 'Hata: ' + (e.message || e));
        });
    } catch (e) {
      _toast('\u274C', 'Hata: ' + (e.message || e));
    }
  }

  function _removeCompareSymbol() {
    if (compareSeries) {
      try {
        var chart = (typeof chartManager !== 'undefined') ? chartManager.getChart() : null;
        if (chart) chart.removeSeries(compareSeries);
      } catch(ex) {}
      compareSeries = null;
      compareSymbol = '';
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     Symbol Details — real data panel
     ═══════════════════════════════════════════════════════════════════ */
  function _openDetailsSheet() {
    _removePanel('acDetailsPanel');
    var data = (typeof chartManager !== 'undefined') ? chartManager.getData() : null;
    var candles = (data && data.candles) ? data.candles : [];
    var last = candles.length ? candles[candles.length - 1] : null;

    var change = '\u2014', changePct = '\u2014', high = '\u2014', low = '\u2014';
    if (last) {
      var o = Number(last.open), c = Number(last.close), h = Number(last.high), l = Number(last.low);
      change = (c - o).toFixed(4);
      changePct = o ? ((c - o) / o * 100).toFixed(2) + '%' : '\u2014';
      high = h.toLocaleString(undefined, { maximumFractionDigits: 6 });
      low = l.toLocaleString(undefined, { maximumFractionDigits: 6 });
    }

    var sessionHigh = '\u2014', sessionLow = '\u2014';
    if (candles.length) {
      var highs = candles.map(function(c){ return Number(c.high); });
      var lows  = candles.map(function(c){ return Number(c.low); });
      sessionHigh = Math.max.apply(null, highs).toLocaleString(undefined, { maximumFractionDigits: 6 });
      sessionLow  = Math.min.apply(null, lows).toLocaleString(undefined, { maximumFractionDigits: 6 });
    }

    var symbol = (data && data.symbol) ? data.symbol : '\u2014';
    var interval = (data && data.interval) ? data.interval : '\u2014';
    var closePrice = last ? Number(last.close).toLocaleString(undefined, { maximumFractionDigits: 6 }) : '\u2014';
    var changeColor = Number(change) >= 0 ? '#26d9a8' : '#f0506e';

    var activeInds = [];
    if (typeof INDICATOR_DEFS !== 'undefined' && typeof activeIndicators !== 'undefined') {
      for (var key in INDICATOR_DEFS) {
        if (activeIndicators[key]) activeInds.push(INDICATOR_DEFS[key].label);
      }
    }
    var drawingCount = 0;
    if (typeof DrawingEngine !== 'undefined' && DrawingEngine.getDrawings) {
      drawingCount = (DrawingEngine.getDrawings('main') || []).length;
    }

    var panel = document.createElement('div');
    panel.id = 'acDetailsPanel';
    panel.className = 'ac-mini-panel ac-mini-panel-wide';
    panel.innerHTML =
      '<div class="ac-mp-header"><span>\u{1F4CA} ' + symbol + ' Detayları</span><button class="ac-mp-close" aria-label="Kapat">\u2715</button></div>' +
      '<div class="ac-mp-body"><div class="ac-detail-grid">' +
      _kv('Sembol', symbol, 'font-weight:600;color:#2979FF') +
      _kv('Periyot', interval) +
      _kv('Son Fiyat', closePrice, 'font-weight:700;font-size:14px') +
      _kv('Değişim', change + ' (' + changePct + ')', 'color:' + changeColor) +
      _kv('Son Mum High', high) +
      _kv('Son Mum Low', low) +
      _kv('Seans High', sessionHigh, 'color:#26d9a8') +
      _kv('Seans Low', sessionLow, 'color:#f0506e') +
      _kv('Mum Sayısı', '' + candles.length) +
      _kv('Aktif Gösterge', activeInds.length ? activeInds.join(', ') : 'Yok') +
      _kv('Çizim Sayısı', '' + drawingCount) +
      '</div></div>';

    document.body.appendChild(panel);
    requestAnimationFrame(function(){ panel.classList.add('open'); });
    panel.querySelector('.ac-mp-close').onclick = function(){ _dismissPanel(panel); };
  }

  function _kv(label, value, style) {
    return '<div class="ac-detail-key">' + label + '</div><div class="ac-detail-val"' + (style ? ' style="' + style + '"' : '') + '>' + value + '</div>';
  }

  /* ═══════════════════════════════════════════════════════════════════
     Technicals — RSI/MACD/signal summary panel
     ═══════════════════════════════════════════════════════════════════ */
  function _openTechnicalsSheet() {
    _removePanel('acTechPanel');
    var data = (typeof chartManager !== 'undefined') ? chartManager.getData() : null;
    var candles = (data && data.candles) ? data.candles : [];
    var volumes = ((data && data.volume) || []).map(function(v){ return { time: v.time, value: Number(v.value) }; });

    var rsiVal = '\u2014', rsiColor = '#8899b0';
    var macdLine = '\u2014', signalLine = '\u2014', macdHist = '\u2014', histColor = '#8899b0';
    var ema20Val = '\u2014', ema50Val = '\u2014', sma200Val = '\u2014', vwapVal = '\u2014';
    var trendLabel = '\u2014', trendColor = '#8899b0';

    if (candles.length > 30 && typeof IndicatorEngine !== 'undefined') {
      var ema20arr = IndicatorEngine.ema(candles, 20);
      var ema50arr = IndicatorEngine.ema(candles, 50);
      if (ema20arr.length) ema20Val = Number(ema20arr[ema20arr.length - 1].value).toLocaleString(undefined, { maximumFractionDigits: 4 });
      if (ema50arr.length) ema50Val = Number(ema50arr[ema50arr.length - 1].value).toLocaleString(undefined, { maximumFractionDigits: 4 });
      var sma200arr = IndicatorEngine.sma(candles, 200);
      if (sma200arr.length) sma200Val = Number(sma200arr[sma200arr.length - 1].value).toLocaleString(undefined, { maximumFractionDigits: 4 });
      var vwapArr = IndicatorEngine.vwap(candles, volumes);
      if (vwapArr.length) vwapVal = Number(vwapArr[vwapArr.length - 1].value).toLocaleString(undefined, { maximumFractionDigits: 4 });
    }

    if (typeof patternOverlayManager !== 'undefined' && patternOverlayManager.getResult) {
      var pResult = patternOverlayManager.getResult();
      if (pResult) {
        trendLabel = pResult.trend || '\u2014';
        trendColor = trendLabel === 'uptrend' ? '#26d9a8' : trendLabel === 'downtrend' ? '#f0506e' : '#8899b0';
      }
    }

    // RSI 14
    if (candles.length > 15) {
      var closes = candles.map(function(c){ return Number(c.close); });
      var gains = 0, losses = 0;
      for (var i = closes.length - 14; i < closes.length; i++) {
        var diff = closes[i] - closes[i - 1];
        if (diff > 0) gains += diff; else losses -= diff;
      }
      var avgGain = gains / 14, avgLoss = losses / 14;
      var rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      var rsi = 100 - 100 / (1 + rs);
      rsiVal = rsi.toFixed(1);
      rsiColor = rsi > 70 ? '#f0506e' : rsi < 30 ? '#26d9a8' : '#f5c842';
    }

    // MACD (12,26,9)
    if (candles.length > 30) {
      var cls = candles.map(function(c){ return Number(c.close); });
      var _ema = function(arr, p) {
        var k = 2 / (p + 1), r = [arr[0]];
        for (var j = 1; j < arr.length; j++) r.push(arr[j] * k + r[j - 1] * (1 - k));
        return r;
      };
      var e12 = _ema(cls, 12), e26 = _ema(cls, 26);
      var macd = e12.map(function(v, idx){ return v - e26[idx]; });
      var sig = _ema(macd, 9);
      var lastM = macd[macd.length - 1], lastS = sig[sig.length - 1];
      var hist = lastM - lastS;
      macdLine = lastM.toFixed(4);
      signalLine = lastS.toFixed(4);
      macdHist = hist.toFixed(4);
      histColor = hist >= 0 ? '#26d9a8' : '#f0506e';
    }

    // Summary
    var summaryText = 'Nötr', summaryColor = '#8899b0';
    if (rsiVal !== '\u2014' && macdHist !== '\u2014') {
      var rsiNum = parseFloat(rsiVal), histNum = parseFloat(macdHist);
      if (rsiNum < 30 && histNum > 0)      { summaryText = 'Güçlü Al';  summaryColor = '#26d9a8'; }
      else if (rsiNum > 70 && histNum < 0) { summaryText = 'Güçlü Sat'; summaryColor = '#f0506e'; }
      else if (rsiNum < 45 && histNum > 0) { summaryText = 'Al';        summaryColor = '#26d9a8'; }
      else if (rsiNum > 55 && histNum < 0) { summaryText = 'Sat';       summaryColor = '#f0506e'; }
      else                                  { summaryText = 'Nötr';     summaryColor = '#f5c842'; }
    }

    var panel = document.createElement('div');
    panel.id = 'acTechPanel';
    panel.className = 'ac-mini-panel ac-mini-panel-wide';
    panel.innerHTML =
      '<div class="ac-mp-header"><span>\u{1F4D0} Teknik Özet</span><button class="ac-mp-close" aria-label="Kapat">\u2715</button></div>' +
      '<div class="ac-mp-body">' +
      '<div class="ac-tech-summary" style="text-align:center;padding:8px 0 12px">' +
      '<div style="font-size:10px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:1px">Teknik Sinyal</div>' +
      '<div style="font-size:22px;font-weight:700;color:' + summaryColor + ';margin:4px 0">' + summaryText + '</div>' +
      '</div>' +
      '<div class="ac-detail-grid">' +
      _kv('RSI (14)', rsiVal, 'color:' + rsiColor + ';font-weight:600') +
      _kv('MACD Çizgisi', macdLine) +
      _kv('Sinyal Çizgisi', signalLine) +
      _kv('MACD Histogram', macdHist, 'color:' + histColor + ';font-weight:600') +
      _kv('Trend', (trendLabel === 'uptrend' ? '\u2191 Yükseliş' : trendLabel === 'downtrend' ? '\u2193 Düşüş' : '\u2194 Yatay'), 'color:' + trendColor) +
      _kv('EMA 20', ema20Val) +
      _kv('EMA 50', ema50Val) +
      _kv('SMA 200', sma200Val) +
      _kv('VWAP', vwapVal) +
      '</div></div>';

    document.body.appendChild(panel);
    requestAnimationFrame(function(){ panel.classList.add('open'); });
    panel.querySelector('.ac-mp-close').onclick = function(){ _dismissPanel(panel); };
  }

  /* ═══════════════════════════════════════════════════════════════════
     Panel helpers
     ═══════════════════════════════════════════════════════════════════ */
  function _removePanel(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }

  function _dismissPanel(panel) {
    panel.classList.remove('open');
    setTimeout(function(){ panel.remove(); }, 300);
  }

  function _toast(icon, msg) {
    var container = document.querySelector('.alert-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'alert-toast-container';
      document.body.appendChild(container);
    }
    var t = document.createElement('div');
    t.className = 'alert-toast';
    t.innerHTML = '<span class="toast-icon">' + icon + '</span><div class="toast-content"><div class="toast-msg">' + msg + '</div></div><button class="toast-close" onclick="this.closest(\'.alert-toast\').remove()">\u00D7</button>';
    container.appendChild(t);
    setTimeout(function(){ t.classList.add('removing'); setTimeout(function(){ t.remove(); }, 300); }, 3000);
  }

  /* ── Drag ──────────────────────────────────────────────────────── */
  function setupDrag(sheet) {
    var h = document.getElementById('acHandle');
    if (!h) return;
    var sy = 0, drag = false;
    var onS = function(e) { drag = true; sy = (e.touches ? e.touches[0] : e).clientY; sheet.style.transition = 'none'; };
    var onM = function(e) { if (!drag) return; var d = (e.touches ? e.touches[0] : e).clientY - sy; if (d > 0) sheet.style.transform = 'translateY(' + d + 'px)'; };
    var onE = function(e) { if (!drag) return; drag = false; sheet.style.transition = ''; var d = (e.changedTouches ? e.changedTouches[0] : e).clientY - sy; if (d > 100) close(); else sheet.style.transform = ''; };
    h.addEventListener('touchstart', onS, { passive: true });
    h.addEventListener('touchmove', onM, { passive: false });
    h.addEventListener('touchend', onE);
    h.addEventListener('mousedown', onS);
    document.addEventListener('mousemove', onM);
    document.addEventListener('mouseup', onE);
  }

  /* ── Open / Close ──────────────────────────────────────────────── */
  function open() {
    buildSheet();
    isOpen = true;
    if (typeof ChartDrawer !== 'undefined') ChartDrawer.close?.();
    document.getElementById('drawerOverlay')?.classList.add('active');
    document.getElementById('analysisSheet')?.classList.add('open');
    document.body.style.overflow = 'hidden';
    var ov = document.getElementById('drawerOverlay');
    if (ov) ov.onclick = close;
  }

  function close() {
    isOpen = false;
    document.getElementById('drawerOverlay')?.classList.remove('active');
    var s = document.getElementById('analysisSheet');
    if (s) { s.classList.remove('open'); s.style.transform = ''; }
    document.body.style.overflow = '';
  }

  function toggle() { isOpen ? close() : open(); }

  /* ── Init ──────────────────────────────────────────────────────── */
  function init() {
    document.addEventListener('click', function(e) {
      var b = e.target.closest('[data-action="open-analysis"]');
      if (b) toggle();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen) close();
    });
  }

  return { init, open, close, toggle };
})();
