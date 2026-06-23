/* =====================================================================
   ZKR Analiz — Çizimler (Drawing Tools) Bottom Sheet
   TradingView-mobile style · SVG line-art icons · 3-column grid
   ===================================================================== */
'use strict';

const ChartDrawer = (() => {

  /* ═══════════════════════════════════════════════════════════════════
     SVG Icon Library — clean line-art (stroke-based, 28×28 viewBox)
     ═══════════════════════════════════════════════════════════════════ */
  const I = {
    // ── Trend çizgileri ──
    trendline:      `<svg viewBox="0 0 28 28"><line x1="6" y1="22" x2="22" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="22" r="1.8" fill="currentColor"/><circle cx="22" cy="6" r="1.8" fill="currentColor"/></svg>`,
    ray:            `<svg viewBox="0 0 28 28"><line x1="6" y1="22" x2="24" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="6" cy="22" r="1.8" fill="currentColor"/><polyline points="20,6 24,6 24,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    info_line:      `<svg viewBox="0 0 28 28"><line x1="5" y1="22" x2="23" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="5" cy="22" r="1.8" fill="currentColor"/><circle cx="23" cy="6" r="1.8" fill="currentColor"/><rect x="10" y="11" width="8" height="5.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1"/></svg>`,
    extended:       `<svg viewBox="0 0 28 28"><line x1="2" y1="24" x2="26" y2="4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="9" cy="18" r="1.8" fill="currentColor"/><circle cx="19" cy="10" r="1.8" fill="currentColor"/></svg>`,
    trend_angle:    `<svg viewBox="0 0 28 28"><polyline points="6,20 22,20 22,8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="6" y1="20" x2="22" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M10,20 A4,4 0 0,0 9,17.5" fill="none" stroke="currentColor" stroke-width="1"/></svg>`,
    h_line:         `<svg viewBox="0 0 28 28"><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="14" r="1.8" fill="currentColor"/><circle cx="24" cy="14" r="1.8" fill="currentColor"/></svg>`,
    h_ray:          `<svg viewBox="0 0 28 28"><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="14" r="1.8" fill="currentColor"/><polyline points="21,11 24,14 21,17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    v_line:         `<svg viewBox="0 0 28 28"><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="14" cy="4" r="1.8" fill="currentColor"/><circle cx="14" cy="24" r="1.8" fill="currentColor"/></svg>`,
    cross:          `<svg viewBox="0 0 28 28"><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    par_channel:    `<svg viewBox="0 0 28 28"><line x1="4" y1="20" x2="24" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="12" x2="24" y2="4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="20" r="1.5" fill="currentColor"/><circle cx="24" cy="12" r="1.5" fill="currentColor"/></svg>`,
    regression:     `<svg viewBox="0 0 28 28"><line x1="4" y1="20" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="16" x2="24" y2="4" stroke="currentColor" stroke-width="1" opacity=".4"/><line x1="4" y1="24" x2="24" y2="12" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
    flat_tb:        `<svg viewBox="0 0 28 28"><line x1="4" y1="8" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="20" x2="24" y2="20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="14" cy="8" r="1.5" fill="currentColor"/><circle cx="14" cy="20" r="1.5" fill="currentColor"/></svg>`,
    disj_ch:        `<svg viewBox="0 0 28 28"><line x1="4" y1="20" x2="14" y2="10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="14" y1="18" x2="24" y2="8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="14" cy="10" r="1.5" fill="currentColor"/><circle cx="14" cy="18" r="1.5" fill="currentColor"/></svg>`,
    pitchfork:      `<svg viewBox="0 0 28 28"><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="14" x2="24" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="14" x2="24" y2="22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="14" r="2" fill="currentColor"/></svg>`,
    schiff:         `<svg viewBox="0 0 28 28"><line x1="4" y1="18" x2="24" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="18" x2="24" y2="6" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="18" x2="24" y2="22" stroke="currentColor" stroke-width="1.5"/><circle cx="4" cy="18" r="1.8" fill="currentColor"/><circle cx="14" cy="8" r="1.2" fill="currentColor"/></svg>`,
    mod_schiff:     `<svg viewBox="0 0 28 28"><line x1="6" y1="20" x2="24" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="6" y1="20" x2="24" y2="6" stroke="currentColor" stroke-width="1.5"/><line x1="6" y1="20" x2="24" y2="22" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="20" r="1.8" fill="currentColor"/><path d="M12,9 L14,7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    inside_pf:      `<svg viewBox="0 0 28 28"><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="14" x2="24" y2="8" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/><line x1="4" y1="14" x2="24" y2="20" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/><line x1="4" y1="14" x2="24" y2="5" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="14" x2="24" y2="23" stroke="currentColor" stroke-width="1.5"/><circle cx="4" cy="14" r="1.8" fill="currentColor"/></svg>`,

    // ── Gann ve fibonacci ──
    fib_ret:        `<svg viewBox="0 0 28 28"><line x1="4" y1="6" x2="24" y2="6" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="11" x2="24" y2="11" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/><line x1="4" y1="16.5" x2="24" y2="16.5" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/><line x1="4" y1="22" x2="24" y2="22" stroke="currentColor" stroke-width="1.5"/></svg>`,
    fib_ext:        `<svg viewBox="0 0 28 28"><polyline points="6,22 6,6 22,6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="6" y1="14" x2="22" y2="14" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/><line x1="6" y1="18" x2="22" y2="18" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/></svg>`,
    fib_ch:         `<svg viewBox="0 0 28 28"><line x1="4" y1="22" x2="24" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="14" x2="24" y2="6" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="18" x2="24" y2="10" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/></svg>`,
    fib_tz:         `<svg viewBox="0 0 28 28"><line x1="6" y1="4" x2="6" y2="24" stroke="currentColor" stroke-width="1.5"/><line x1="10" y1="4" x2="10" y2="24" stroke="currentColor" stroke-width="1"/><line x1="16" y1="4" x2="16" y2="24" stroke="currentColor" stroke-width="1"/><line x1="24" y1="4" x2="24" y2="24" stroke="currentColor" stroke-width="1"/></svg>`,
    fib_fan:        `<svg viewBox="0 0 28 28"><line x1="4" y1="22" x2="24" y2="4" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="22" x2="24" y2="12" stroke="currentColor" stroke-width="1"/><line x1="4" y1="22" x2="24" y2="18" stroke="currentColor" stroke-width="1"/><rect x="20" y="18" width="4" height="4" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/></svg>`,
    fib_tt:         `<svg viewBox="0 0 28 28"><line x1="4" y1="22" x2="24" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/><line x1="20" y1="4" x2="20" y2="24" stroke="currentColor" stroke-width="1" stroke-dasharray="3,2"/></svg>`,
    fib_circ:       `<svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="4" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="14" cy="14" r="8" fill="none" stroke="currentColor" stroke-width="1"/><circle cx="14" cy="14" r="12" fill="none" stroke="currentColor" stroke-width="1" opacity=".5"/></svg>`,
    fib_spiral:     `<svg viewBox="0 0 28 28"><path d="M14,14 Q14,10 18,10 Q22,10 22,14 Q22,20 14,20 Q6,20 6,14 Q6,6 14,6 Q24,6 24,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    fib_arcs:       `<svg viewBox="0 0 28 28"><path d="M4,22 Q4,6 22,6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M4,22 Q4,12 16,10" fill="none" stroke="currentColor" stroke-width="1"/><path d="M4,22 Q4,16 12,14" fill="none" stroke="currentColor" stroke-width="1"/></svg>`,
    fib_wedge:      `<svg viewBox="0 0 28 28"><line x1="4" y1="22" x2="24" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="4" y1="22" x2="24" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="22" r="2" fill="currentColor"/></svg>`,
    gann_fan:       `<svg viewBox="0 0 28 28"><line x1="4" y1="24" x2="24" y2="4" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="24" x2="24" y2="10" stroke="currentColor" stroke-width="1"/><line x1="4" y1="24" x2="24" y2="16" stroke="currentColor" stroke-width="1"/><line x1="4" y1="24" x2="24" y2="20" stroke="currentColor" stroke-width="1" opacity=".5"/></svg>`,
    gann_box:       `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1"/><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1"/><line x1="4" y1="4" x2="24" y2="24" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/></svg>`,
    gann_sq_fix:    `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="4" x2="24" y2="24" stroke="currentColor" stroke-width="1"/><line x1="24" y1="4" x2="4" y2="24" stroke="currentColor" stroke-width="1"/><rect x="9" y="9" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/></svg>`,
    gann_sq:        `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="4" x2="24" y2="24" stroke="currentColor" stroke-width="1"/><line x1="24" y1="4" x2="4" y2="24" stroke="currentColor" stroke-width="1"/><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1"/><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1"/></svg>`,
    gann_fan2:      `<svg viewBox="0 0 28 28"><line x1="4" y1="24" x2="24" y2="4" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="24" x2="14" y2="4" stroke="currentColor" stroke-width="1"/><line x1="4" y1="24" x2="8" y2="4" stroke="currentColor" stroke-width="1" opacity=".5"/></svg>`,

    // ── Desenler ──
    xabcd:          `<svg viewBox="0 0 28 28"><polyline points="4,18 8,8 14,16 18,6 24,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4" cy="18" r="1.3" fill="currentColor"/><circle cx="8" cy="8" r="1.3" fill="currentColor"/><circle cx="14" cy="16" r="1.3" fill="currentColor"/><circle cx="18" cy="6" r="1.3" fill="currentColor"/><circle cx="24" cy="14" r="1.3" fill="currentColor"/></svg>`,
    cypher:         `<svg viewBox="0 0 28 28"><polyline points="4,18 10,6 16,14 22,4 24,16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4" cy="18" r="1.3" fill="currentColor"/><circle cx="10" cy="6" r="1.3" fill="currentColor"/><circle cx="24" cy="16" r="1.3" fill="currentColor"/></svg>`,
    hns:            `<svg viewBox="0 0 28 28"><polyline points="4,20 8,14 10,20 14,6 18,20 20,14 24,20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    abcd:           `<svg viewBox="0 0 28 28"><polyline points="4,20 10,6 18,18 24,6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4" cy="20" r="1.3" fill="currentColor"/><circle cx="10" cy="6" r="1.3" fill="currentColor"/><circle cx="18" cy="18" r="1.3" fill="currentColor"/><circle cx="24" cy="6" r="1.3" fill="currentColor"/></svg>`,
    tri_pat:        `<svg viewBox="0 0 28 28"><polyline points="4,20 14,6 24,20 4,20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    three_d:        `<svg viewBox="0 0 28 28"><polyline points="4,16 8,8 12,14 16,6 20,12 24,4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    ew_imp:         `<svg viewBox="0 0 28 28"><polyline points="2,22 6,14 8,18 14,4 16,12 20,8 26,6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><text x="5" y="12" fill="currentColor" font-size="5" font-weight="700" font-family="sans-serif">1</text><text x="13" y="3" fill="currentColor" font-size="5" font-weight="700" font-family="sans-serif">5</text></svg>`,
    ew_abc:         `<svg viewBox="0 0 28 28"><polyline points="4,8 10,20 18,10 24,22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><text x="3" y="7" fill="currentColor" font-size="5" font-weight="700" font-family="sans-serif">A</text><text x="17" y="9" fill="currentColor" font-size="5" font-weight="700" font-family="sans-serif">B</text><text x="22" y="26" fill="currentColor" font-size="5" font-weight="700" font-family="sans-serif">C</text></svg>`,
    ew_tri:         `<svg viewBox="0 0 28 28"><polyline points="2,14 6,6 10,18 14,8 18,16 22,10 26,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    ew_dbl:         `<svg viewBox="0 0 28 28"><polyline points="2,10 7,20 12,8 17,18 22,10 26,16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    ew_trp:         `<svg viewBox="0 0 28 28"><polyline points="1,10 4,20 8,8 12,18 16,10 20,16 24,8 27,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    cyclic:         `<svg viewBox="0 0 28 28"><line x1="4" y1="4" x2="4" y2="24" stroke="currentColor" stroke-width="1.5"/><line x1="10" y1="4" x2="10" y2="24" stroke="currentColor" stroke-width="1.5"/><line x1="16" y1="4" x2="16" y2="24" stroke="currentColor" stroke-width="1.5"/><line x1="22" y1="4" x2="22" y2="24" stroke="currentColor" stroke-width="1.5"/></svg>`,
    time_cyc:       `<svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="14" cy="14" r="6" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/></svg>`,
    sine:           `<svg viewBox="0 0 28 28"><path d="M2,14 Q7,4 14,14 Q21,24 26,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,

    // ── Tahmin ve ölçüm ──
    long_pos:       `<svg viewBox="0 0 28 28"><rect x="6" y="4" width="16" height="20" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="6" y1="14" x2="22" y2="14" stroke="currentColor" stroke-width="1"/><rect x="7" y="5" width="14" height="9" rx="0.5" fill="currentColor" opacity=".15"/><path d="M14,18 L14,8 M11,11 L14,8 L17,11" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    short_pos:      `<svg viewBox="0 0 28 28"><rect x="6" y="4" width="16" height="20" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="6" y1="14" x2="22" y2="14" stroke="currentColor" stroke-width="1"/><rect x="7" y="14" width="14" height="9" rx="0.5" fill="currentColor" opacity=".15"/><path d="M14,10 L14,20 M11,17 L14,20 L17,17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    forecast:       `<svg viewBox="0 0 28 28"><polyline points="4,20 10,14 16,16 20,8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="20,8 26,4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="3,2"/><line x1="20" y1="4" x2="20" y2="24" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2" opacity=".4"/></svg>`,
    bars_pat:       `<svg viewBox="0 0 28 28"><rect x="4" y="12" width="3" height="10" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><rect x="9" y="8" width="3" height="14" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><rect x="14" y="10" width="3" height="12" rx="0.5" fill="none" stroke="currentColor" stroke-width="1"/><rect x="19" y="6" width="3" height="16" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" stroke-dasharray="2,1"/></svg>`,
    ghost:          `<svg viewBox="0 0 28 28"><polyline points="4,20 8,14 12,16 16,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="16,10 20,14 24,8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity=".35"/></svg>`,
    projection:     `<svg viewBox="0 0 28 28"><polyline points="4,20 10,10 16,16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="16,16 22,8 24,12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3,2"/><circle cx="16" cy="16" r="1.5" fill="currentColor"/></svg>`,
    anch_vwap:      `<svg viewBox="0 0 28 28"><path d="M4,18 Q10,10 14,14 Q18,18 24,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="18" r="2" fill="currentColor"/><line x1="4" y1="18" x2="4" y2="24" stroke="currentColor" stroke-width="1.5"/></svg>`,
    fixed_vol:      `<svg viewBox="0 0 28 28"><rect x="4" y="6" width="4" height="16" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><rect x="9" y="4" width="4" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><rect x="14" y="8" width="4" height="12" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><line x1="2" y1="4" x2="2" y2="24" stroke="currentColor" stroke-width="1.5"/><line x1="20" y1="4" x2="20" y2="24" stroke="currentColor" stroke-width="1.5"/></svg>`,
    anch_vol:       `<svg viewBox="0 0 28 28"><rect x="6" y="6" width="4" height="14" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><rect x="11" y="4" width="4" height="18" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><rect x="16" y="8" width="4" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><circle cx="6" cy="24" r="2" fill="currentColor"/></svg>`,
    p_range:        `<svg viewBox="0 0 28 28"><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1.5"/><line x1="10" y1="4" x2="18" y2="4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="10" y1="24" x2="18" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><polyline points="12,8 14,4 16,8" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><polyline points="12,20 14,24 16,20" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>`,
    d_range:        `<svg viewBox="0 0 28 28"><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="10" x2="4" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="24" y1="10" x2="24" y2="18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><polyline points="8,12 4,14 8,16" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><polyline points="20,12 24,14 20,16" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>`,
    dp_range:       `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="14" x2="24" y2="14" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1" stroke-dasharray="2,2"/></svg>`,

    // ── Geometrik şekiller ──
    brush:          `<svg viewBox="0 0 28 28"><path d="M6,22 Q8,16 12,14 Q16,12 18,8 Q20,4 22,4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
    highlight:      `<svg viewBox="0 0 28 28"><rect x="5" y="10" width="18" height="8" rx="2" fill="currentColor" opacity=".2"/><path d="M6,14 L22,14" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity=".5"/></svg>`,
    arr_mark:       `<svg viewBox="0 0 28 28"><line x1="6" y1="22" x2="22" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><polyline points="16,6 22,6 22,12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    arrow:          `<svg viewBox="0 0 28 28"><line x1="6" y1="22" x2="22" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><polyline points="16,6 22,6 22,12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6" cy="22" r="2" fill="currentColor"/></svg>`,
    arr_up:         `<svg viewBox="0 0 28 28"><path d="M14,22 L14,6 M8,12 L14,6 L20,12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    arr_down:       `<svg viewBox="0 0 28 28"><path d="M14,6 L14,22 M8,16 L14,22 L20,16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    rect:           `<svg viewBox="0 0 28 28"><rect x="4" y="6" width="20" height="16" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    rot_rect:       `<svg viewBox="0 0 28 28"><rect x="6" y="6" width="16" height="16" rx="1" fill="none" stroke="currentColor" stroke-width="1.5" transform="rotate(15 14 14)"/></svg>`,
    path:           `<svg viewBox="0 0 28 28"><polyline points="4,20 10,8 16,16 22,6 24,10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
    circle:         `<svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    ellipse:        `<svg viewBox="0 0 28 28"><ellipse cx="14" cy="14" rx="12" ry="8" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    polyline:       `<svg viewBox="0 0 28 28"><polyline points="4,18 10,8 14,16 20,6 24,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="4" cy="18" r="1.3" fill="currentColor"/><circle cx="10" cy="8" r="1.3" fill="currentColor"/><circle cx="14" cy="16" r="1.3" fill="currentColor"/><circle cx="20" cy="6" r="1.3" fill="currentColor"/><circle cx="24" cy="14" r="1.3" fill="currentColor"/></svg>`,
    triangle:       `<svg viewBox="0 0 28 28"><polygon points="14,4 4,24 24,24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    arc:            `<svg viewBox="0 0 28 28"><path d="M4,20 Q14,2 24,20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    curve:          `<svg viewBox="0 0 28 28"><path d="M4,20 Q14,4 24,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="20" r="1.5" fill="currentColor"/><circle cx="24" cy="14" r="1.5" fill="currentColor"/></svg>`,
    dbl_curve:      `<svg viewBox="0 0 28 28"><path d="M4,14 Q10,4 14,14 Q18,24 24,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="4" cy="14" r="1.5" fill="currentColor"/><circle cx="24" cy="14" r="1.5" fill="currentColor"/></svg>`,

    // ── Ek açıklama ──
    text:           `<svg viewBox="0 0 28 28"><text x="7" y="20" fill="currentColor" font-size="18" font-weight="700" font-family="serif">T</text></svg>`,
    anch_text:      `<svg viewBox="0 0 28 28"><text x="7" y="17" fill="currentColor" font-size="15" font-weight="700" font-family="serif">T</text><line x1="7" y1="21" x2="20" y2="21" stroke="currentColor" stroke-width="1.5"/><circle cx="7" cy="24" r="1.5" fill="currentColor"/></svg>`,
    note:           `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="8" y1="10" x2="20" y2="10" stroke="currentColor" stroke-width="1"/><line x1="8" y1="14" x2="18" y2="14" stroke="currentColor" stroke-width="1"/><line x1="8" y1="18" x2="14" y2="18" stroke="currentColor" stroke-width="1"/></svg>`,
    price_note:     `<svg viewBox="0 0 28 28"><rect x="4" y="6" width="17" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><text x="8" y="17" fill="currentColor" font-size="10" font-weight="700" font-family="sans-serif">$</text><line x1="21" y1="12" x2="26" y2="12" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2,1"/></svg>`,
    pin:            `<svg viewBox="0 0 28 28"><circle cx="14" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="14" y1="16" x2="14" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="14" cy="10" r="2" fill="currentColor"/></svg>`,
    table:          `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="4" y1="11" x2="24" y2="11" stroke="currentColor" stroke-width="1"/><line x1="4" y1="18" x2="24" y2="18" stroke="currentColor" stroke-width="1"/><line x1="14" y1="4" x2="14" y2="24" stroke="currentColor" stroke-width="1"/></svg>`,
    callout:        `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="14" rx="3" fill="none" stroke="currentColor" stroke-width="1.5"/><polyline points="10,18 8,24 14,18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    comment:        `<svg viewBox="0 0 28 28"><path d="M4,4 h20 a2,2 0 0,1 2,2 v10 a2,2 0 0,1 -2,2 h-12 l-4,4 v-4 h-4 a2,2 0 0,1 -2,-2 v-10 a2,2 0 0,1 2,-2z" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>`,
    p_label:        `<svg viewBox="0 0 28 28"><path d="M4,8 h14 l6,6 l-6,6 h-14 z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    signpost:       `<svg viewBox="0 0 28 28"><line x1="14" y1="2" x2="14" y2="26" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M8,6 h12 l3,4 l-3,4 h-12 z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M20,16 h-12 l-3,4 l3,4 h12 z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    flag:           `<svg viewBox="0 0 28 28"><line x1="6" y1="4" x2="6" y2="24" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M6,4 L22,8 L6,14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    image:          `<svg viewBox="0 0 28 28"><rect x="4" y="6" width="20" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="10" cy="12" r="2" fill="currentColor"/><polyline points="4,20 10,14 16,18 20,14 24,18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
    tweet:          `<svg viewBox="0 0 28 28"><path d="M24,6 C22,8 20,8.5 18,8 C16.5,6 14,5.5 12,7 C10,8.5 10,11 11,13 C8,13 5,11 3,8 C2,10 2.5,13 5,15 C4,15 3,14.5 2,14 C2,16.5 4,18.5 7,19 C6,19.5 5,19.5 4,19 C5,21 7,22.5 10,22.5 C8,24 5,25 2,24.5 C5,26 8,27 12,26 C20,24 24,18 24,10" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>`,
    idea:           `<svg viewBox="0 0 28 28"><circle cx="14" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="11" y1="18" x2="11" y2="22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="17" y1="18" x2="17" y2="22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="10" y1="22" x2="18" y2="22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="10" y1="25" x2="18" y2="25" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><path d="M11,8 L13,6 L15,8" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>`,

    // ── Görseller ──
    emoji:          `<svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="10" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="10" cy="12" r="1.5" fill="currentColor"/><circle cx="18" cy="12" r="1.5" fill="currentColor"/><path d="M9,17 Q14,22 19,17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
    sticker:        `<svg viewBox="0 0 28 28"><rect x="4" y="4" width="20" height="20" rx="5" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="10" cy="12" r="1.5" fill="currentColor"/><circle cx="18" cy="12" r="1.5" fill="currentColor"/><path d="M9,17 Q14,22 19,17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M18,24 Q24,18 24,12" fill="none" stroke="currentColor" stroke-width="1" opacity=".5"/></svg>`,
    icons:          `<svg viewBox="0 0 28 28"><path d="M14,4 L16.5,10 L24,11 L18.5,16 L20,24 L14,20 L8,24 L9.5,16 L4,11 L11.5,10 Z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  };

  /* ═══════════════════════════════════════════════════════════════════
     Tool Categories & Data
     ═══════════════════════════════════════════════════════════════════ */
  const CATEGORIES = [
    { id: 'trend',   label: 'Trend çizgileri' },
    { id: 'fib',     label: 'Gann ve fibonacci' },
    { id: 'pat',     label: 'Desenler' },
    { id: 'meas',    label: 'Tahmin ve ölçüm' },
    { id: 'shape',   label: 'Geometrik şekiller' },
    { id: 'annot',   label: 'Ek açıklama' },
    { id: 'visual',  label: 'Görseller' },
  ];

  const TOOLS = [
    // ── Trend çizgileri ──────────────────
    { id:'trendline',    name:'Trend Çizgisi',      cat:'trend', icon:I.trendline },
    { id:'ray',          name:'Işın',               cat:'trend', icon:I.ray },
    { id:'info_line',    name:'Bilgi Çizgisi',      cat:'trend', icon:I.info_line },
    { id:'extended',     name:'Çizgiyi Uzat',       cat:'trend', icon:I.extended },
    { id:'trend_angle',  name:'Trend Açısı',       cat:'trend', icon:I.trend_angle },
    { id:'h_line',       name:'Yatay Çizgi',        cat:'trend', icon:I.h_line },
    { id:'h_ray',        name:'Yatay Işın',        cat:'trend', icon:I.h_ray },
    { id:'v_line',       name:'Dikey Çizgi',        cat:'trend', icon:I.v_line },
    { id:'cross',        name:'Kesişen Çizgiler',  cat:'trend', icon:I.cross },
    { id:'par_channel',  name:'Paralel Kanal',      cat:'trend', icon:I.par_channel },
    { id:'regression',   name:'Regresyon Trendi',   cat:'trend', icon:I.regression },
    { id:'flat_tb',      name:'Düz Üst/Alt',      cat:'trend', icon:I.flat_tb },
    { id:'disj_ch',      name:'Ayrık Kanal',      cat:'trend', icon:I.disj_ch },
    { id:'pitchfork',    name:'Dirgen',             cat:'trend', icon:I.pitchfork },
    { id:'schiff',       name:'Schiff Dirgeni',     cat:'trend', icon:I.schiff },
    { id:'mod_schiff',   name:'Değiştirilmiş\nSchiff Dirgeni', cat:'trend', icon:I.mod_schiff },
    { id:'inside_pf',    name:'İç Dirgen',         cat:'trend', icon:I.inside_pf },

    // ── Gann ve fibonacci ────────────────
    { id:'fib_ret',      name:'Fib Düzeltmesi',    cat:'fib', icon:I.fib_ret },
    { id:'fib_ext',      name:'Trend Temelli\nFib Uzatma', cat:'fib', icon:I.fib_ext },
    { id:'fib_ch',       name:'Fib Kanalı',       cat:'fib', icon:I.fib_ch },
    { id:'fib_tz',       name:'Fib Zaman Dilimi',   cat:'fib', icon:I.fib_tz },
    { id:'fib_fan',      name:'Fib Hız Direnç\nFanı', cat:'fib', icon:I.fib_fan },
    { id:'fib_tt',       name:'Trend Temelli\nFib Zaman', cat:'fib', icon:I.fib_tt },
    { id:'fib_circ',     name:'Fib Çemberleri',    cat:'fib', icon:I.fib_circ },
    { id:'fib_spiral',   name:'Fib Spirali',        cat:'fib', icon:I.fib_spiral },
    { id:'fib_arcs',     name:'Fib Hız Direnç\nYayları', cat:'fib', icon:I.fib_arcs },
    { id:'fib_wedge',    name:'Fib Takozu',         cat:'fib', icon:I.fib_wedge },
    { id:'gann_fan',     name:'Gann Yelpazesi',     cat:'fib', icon:I.gann_fan },
    { id:'gann_box',     name:'Gann Kutusu',        cat:'fib', icon:I.gann_box },
    { id:'gann_sq_fix',  name:'Sabit Gann karesi',  cat:'fib', icon:I.gann_sq_fix },
    { id:'gann_sq',      name:'Gann Karesi',        cat:'fib', icon:I.gann_sq },
    { id:'gann_fan2',    name:'Gann Fanı',         cat:'fib', icon:I.gann_fan2 },

    // ── Desenler ─────────────────────────
    { id:'xabcd',        name:'XABCD\nFormasyonu',  cat:'pat', icon:I.xabcd },
    { id:'cypher',       name:'Cypher\nFormasyonu',  cat:'pat', icon:I.cypher },
    { id:'hns',          name:'Omuz Baş Omuz',     cat:'pat', icon:I.hns },
    { id:'abcd',         name:'ABCD Formasyonu',     cat:'pat', icon:I.abcd },
    { id:'tri_pat',      name:'Üçgen\nFormasyonu', cat:'pat', icon:I.tri_pat },
    { id:'three_d',      name:'Üç Sürücü\nFormasyonu', cat:'pat', icon:I.three_d },
    { id:'ew_imp',       name:'Elliott İtki\nDalgası (12345)', cat:'pat', icon:I.ew_imp },
    { id:'ew_abc',       name:'Elliott Düzeltme\nDalgası (ABC)', cat:'pat', icon:I.ew_abc },
    { id:'ew_tri',       name:'Elliott Üçgen\nDalgası (ABCDE)', cat:'pat', icon:I.ew_tri },
    { id:'ew_dbl',       name:'Elliott İkili Kombo\nDalgası (WXY)', cat:'pat', icon:I.ew_dbl },
    { id:'ew_trp',       name:'Elliott Üçlü Kombo\nDalgası (WXYXZ)', cat:'pat', icon:I.ew_trp },
    { id:'cyclic',       name:'Periyodik Çizgiler', cat:'pat', icon:I.cyclic },
    { id:'time_cyc',     name:'Zaman Döngüleri',   cat:'pat', icon:I.time_cyc },
    { id:'sine',         name:'Sinüs Çizgisi',     cat:'pat', icon:I.sine },

    // ── Tahmin ve ölçüm ──────────────────
    { id:'long_pos',     name:'Alış Pozisyonu',    cat:'meas', icon:I.long_pos },
    { id:'short_pos',    name:'Satış Pozisyonu',   cat:'meas', icon:I.short_pos },
    { id:'forecast',     name:'Tahmin',             cat:'meas', icon:I.forecast },
    { id:'bars_pat',     name:'Çubuk Formasyonu',  cat:'meas', icon:I.bars_pat },
    { id:'ghost',        name:'Hayalet Çizgiler',  cat:'meas', icon:I.ghost },
    { id:'projection',   name:'Projeksiyon',        cat:'meas', icon:I.projection },
    { id:'anch_vwap',    name:'Sabitlenmiş VWAP', cat:'meas', icon:I.anch_vwap },
    { id:'fixed_vol',    name:'Sabit Aralık\nHacim Profili', cat:'meas', icon:I.fixed_vol },
    { id:'anch_vol',     name:'Sabitlenmiş\nHacim Profili', cat:'meas', icon:I.anch_vol },
    { id:'p_range',      name:'Fiyat Aralığı',    cat:'meas', icon:I.p_range },
    { id:'d_range',      name:'Tarih Aralığı',    cat:'meas', icon:I.d_range },
    { id:'dp_range',     name:'Tarih ve\nFiyat Aralığı', cat:'meas', icon:I.dp_range },

    // ── Geometrik şekiller ───────────────
    { id:'brush',        name:'Fırça',             cat:'shape', icon:I.brush },
    { id:'highlight',    name:'Vurgulayıcı',      cat:'shape', icon:I.highlight },
    { id:'arr_mark',     name:'Ok İşaretleyicisi', cat:'shape', icon:I.arr_mark },
    { id:'arrow',        name:'Ok',                 cat:'shape', icon:I.arrow },
    { id:'arr_up',       name:'Yukarı Ok',         cat:'shape', icon:I.arr_up },
    { id:'arr_down',     name:'Aşağı Ok',         cat:'shape', icon:I.arr_down },
    { id:'rect',         name:'Dikdörtgen',        cat:'shape', icon:I.rect },
    { id:'rot_rect',     name:'Döndürülmüş\nDikdörtgen', cat:'shape', icon:I.rot_rect },
    { id:'path',         name:'Yol',                cat:'shape', icon:I.path },
    { id:'circle',       name:'Daire',              cat:'shape', icon:I.circle },
    { id:'ellipse',      name:'Elips',               cat:'shape', icon:I.ellipse },
    { id:'polyline',     name:'Çoklu Çizgi',       cat:'shape', icon:I.polyline },
    { id:'triangle',     name:'Üçgen',             cat:'shape', icon:I.triangle },
    { id:'arc',          name:'Yay',                 cat:'shape', icon:I.arc },
    { id:'curve',        name:'Eğri',               cat:'shape', icon:I.curve },
    { id:'dbl_curve',    name:'Çift Eğri',         cat:'shape', icon:I.dbl_curve },

    // ── Ek açıklama ──────────────────────
    { id:'text',         name:'Metin',               cat:'annot', icon:I.text },
    { id:'anch_text',    name:'Sabitlenmiş Metin',cat:'annot', icon:I.anch_text },
    { id:'note',         name:'Not',                 cat:'annot', icon:I.note },
    { id:'price_note',   name:'Fiyat Notu',         cat:'annot', icon:I.price_note },
    { id:'pin',          name:'İğne',               cat:'annot', icon:I.pin },
    { id:'table',        name:'Tablo',               cat:'annot', icon:I.table },
    { id:'callout',      name:'Balon',               cat:'annot', icon:I.callout },
    { id:'comment',      name:'Yorum yap',           cat:'annot', icon:I.comment },
    { id:'p_label',      name:'Fiyat Etiketi',      cat:'annot', icon:I.p_label },
    { id:'signpost',     name:'Yön levhası',       cat:'annot', icon:I.signpost },
    { id:'flag',         name:'Bayrak İşareti',    cat:'annot', icon:I.flag },
    { id:'image',        name:'Görüntü',           cat:'annot', icon:I.image },
    { id:'tweet',        name:'Tweet',               cat:'annot', icon:I.tweet },
    { id:'idea',         name:'Fikir',               cat:'annot', icon:I.idea },

    // ── Görseller ────────────────────────
    { id:'emoji',        name:'Emojiler',            cat:'visual', icon:I.emoji },
    { id:'sticker',      name:'Çıkartmalar',       cat:'visual', icon:I.sticker },
    { id:'icons',        name:'İkonlar',            cat:'visual', icon:I.icons },
  ];

  /* ═══════════════════════════════════════════════════════════════════
     State
     ═══════════════════════════════════════════════════════════════════ */
  let curCat     = 'trend';
  let searchQ    = '';
  let selTool    = null;
  let isOpen     = false;

  /* ═══════════════════════════════════════════════════════════════════
     Build DOM
     ═══════════════════════════════════════════════════════════════════ */
  function buildSheet() {
    if (document.getElementById('drawingSheet')) return;

    // Overlay
    let ov = document.getElementById('drawerOverlay');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'drawerOverlay';
      ov.className = 'drawer-overlay';
      ov.addEventListener('click', close);
      document.body.appendChild(ov);
    }

    const s = document.createElement('div');
    s.id = 'drawingSheet';
    s.className = 'bottom-sheet';
    s.innerHTML = `
      <div class="sheet-handle" id="sheetHandle"><div class="handle-bar"></div></div>
      <div class="sheet-header">
        <span class="sheet-title">Çizimler</span>
        <button class="sheet-close-btn" id="sheetClose" aria-label="Kapat">
          <svg viewBox="0 0 24 24" width="20" height="20"><line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="sheet-search-box">
        <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><line x1="15.5" y1="15.5" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <input class="search-input" id="drawSearch" placeholder="Ara" autocomplete="off" spellcheck="false" />
      </div>
      <div class="sheet-tabs" id="drawTabs"></div>
      <div class="sheet-body" id="drawBody">
        <div class="tool-grid" id="drawGrid"></div>
      </div>
    `;
    document.body.appendChild(s);

    document.getElementById('sheetClose').addEventListener('click', close);
    document.getElementById('drawSearch').addEventListener('input', e => {
      searchQ = e.target.value.trim().toLowerCase();
      renderTools();
    });

    renderTabs();
    renderTools();
    setupDrag(s);
  }

  /* ── Tabs ──────────────────────────────────────────────────────────── */
  function renderTabs() {
    const c = document.getElementById('drawTabs');
    if (!c) return;
    c.innerHTML = CATEGORIES.map(cat => `
      <button class="tab-pill${cat.id === curCat ? ' active' : ''}" data-cat="${cat.id}">${cat.label}</button>
    `).join('');
    c.querySelectorAll('.tab-pill').forEach(b => {
      b.addEventListener('click', () => {
        curCat = b.dataset.cat;
        c.querySelectorAll('.tab-pill').forEach(x => x.classList.toggle('active', x === b));
        renderTools();
        // Scroll selected tab into view
        b.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      });
    });
  }

  /* ── Tool Grid ─────────────────────────────────────────────────────── */
  function renderTools() {
    const g = document.getElementById('drawGrid');
    if (!g) return;

    let items = TOOLS;
    if (searchQ) {
      items = items.filter(t =>
        t.name.toLowerCase().replace(/\n/g,' ').includes(searchQ) ||
        t.id.toLowerCase().includes(searchQ)
      );
    } else {
      items = items.filter(t => t.cat === curCat);
    }

    if (!items.length) {
      g.innerHTML = `<div class="grid-empty" style="grid-column:1/-1;text-align:center;padding:40px 20px;color:#666">
        <div style="font-size:24px;margin-bottom:8px">🔍</div>
        <div>Araç bulunamadı</div>
      </div>`;
      return;
    }

g.innerHTML = items.map(t => {
        const isActive = typeof DrawingEngine !== 'undefined' && DrawingEngine.ACTIVE_TOOL_IDS.has(t.id);
        return `
        <button class="tool-card${t.id === selTool ? ' selected' : ''}${!isActive ? ' tool-disabled' : ''}" data-id="${t.id}" title="${t.name.replace(/\n/g,' ')}">
          <div class="tool-card-icon">${t.icon}</div>
          <div class="tool-card-label">${t.name.replace(/\n/g,'<br>')}</div>
          ${!isActive ? '<span class="tool-soon">Yak\u0131nda</span>' : ''}
        </button>
      `;
      }).join('');

    g.querySelectorAll('.tool-card').forEach(c => {
      c.addEventListener('click', () => selectTool(c.dataset.id));
    });
  }

  /* ── Select ────────────────────────────────────────────────────────── */
  function selectTool(id) {
    selTool = id;
    const t = TOOLS.find(x => x.id === id);
    if (t) {
      window.dispatchEvent(new CustomEvent('bw:tool-selected', { detail: t }));
      document.querySelectorAll('#drawGrid .tool-card').forEach(c =>
        c.classList.toggle('selected', c.dataset.id === id)
      );
    }
    if (window.innerWidth <= 1000) setTimeout(close, 200);
  }

  /* ── Drag ──────────────────────────────────────────────────────────── */
  function setupDrag(sheet) {
    const h = document.getElementById('sheetHandle');
    if (!h) return;
    let sy = 0, drag = false;
    const onS = e => { drag = true; sy = (e.touches?e.touches[0]:e).clientY; sheet.style.transition = 'none'; };
    const onM = e => { if (!drag) return; const d = (e.touches?e.touches[0]:e).clientY - sy; if (d > 0) sheet.style.transform = `translateY(${d}px)`; };
    const onE = e => { if (!drag) return; drag = false; sheet.style.transition = ''; const d = (e.changedTouches?e.changedTouches[0]:e).clientY - sy; d > 100 ? close() : sheet.style.transform = ''; };
    h.addEventListener('touchstart', onS, { passive: true });
    h.addEventListener('touchmove', onM, { passive: false });
    h.addEventListener('touchend', onE);
    h.addEventListener('mousedown', onS);
    document.addEventListener('mousemove', onM);
    document.addEventListener('mouseup', onE);
  }

  /* ── Open / Close ──────────────────────────────────────────────────── */
  function open() {
    buildSheet();
    isOpen = true;
    document.getElementById('drawerOverlay')?.classList.add('active');
    document.getElementById('drawingSheet')?.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    isOpen = false;
    document.getElementById('drawerOverlay')?.classList.remove('active');
    const s = document.getElementById('drawingSheet');
    if (s) { s.classList.remove('open'); s.style.transform = ''; }
    document.body.style.overflow = '';
  }

  function toggle() { isOpen ? close() : open(); }

  /* ── Init ──────────────────────────────────────────────────────────── */
  function init() {
    document.addEventListener('click', e => {
      const b = e.target.closest('[data-action="open-drawings"]');
      if (b) toggle();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && isOpen) close();
    });
  }

  return { init, open, close, toggle, getSelectedTool: () => selTool };
})();
