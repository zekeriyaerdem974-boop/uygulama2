/* ═══════════════════════════════════════════════════════════════════
   trade_alerts.js — Toast notifications on /trade page (FAZ 20)
   Polls /api/alerts/triggered every 5s and shows toasts for new ones.
   ═══════════════════════════════════════════════════════════════════ */
;(function(){
  'use strict';

  const POLL_MS = 5000;
  const seen = new Set();
  const COND = {
    price_above:'Fiyat Üstünde', price_below:'Fiyat Altında',
    rsi_above:'RSI Üstünde', rsi_below:'RSI Altında',
    ema_cross:'EMA Kesişim', breakout:'Kırılım', volume_spike:'Hacim Patlaması'
  };

  function showToast(icon, title, msg, dur){
    dur = dur || 6000;
    var c = document.querySelector('.alert-toast-container');
    if(!c){
      c = document.createElement('div');
      c.className = 'alert-toast-container';
      document.body.appendChild(c);
    }
    var t = document.createElement('div');
    t.className = 'alert-toast';
    t.innerHTML = '<span class="toast-icon">'+icon+'</span>'
      +'<div class="toast-content">'
      +'<div class="toast-title">'+title+'</div>'
      +'<div class="toast-msg">'+msg+'</div>'
      +'</div>'
      +'<button class="toast-close" onclick="this.closest(\'.alert-toast\').remove()">×</button>';
    c.appendChild(t);
    setTimeout(function(){ t.classList.add('removing'); setTimeout(function(){ t.remove(); }, 300); }, dur);
  }

  function poll(){
    fetch('/api/alerts/triggered').then(function(r){ return r.json(); }).then(function(d){
      (d.triggered||[]).forEach(function(a){
        var key = a.id+'_'+a.triggered_at;
        if(!seen.has(key)){
          seen.add(key);
          showToast('🔔', a.symbol+' Alarm!', (COND[a.condition_type]||a.condition_type)+': '+a.condition_value+' → '+a.trigger_price, 8000);
        }
      });
    }).catch(function(){});
  }

  setInterval(poll, POLL_MS);
  setTimeout(poll, 1000);
})();
