import React, { useEffect, useRef, useState, useCallback } from 'react';
import { init, dispose } from 'klinecharts';
import { io } from 'socket.io-client';

const API_BASE   = 'http://localhost:34000';
const SOCKET_URL = 'http://localhost:34000';

// ---- CSS ----
const styles = `
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  @keyframes shimmer {
    0%{background-position:-1000px 0} 100%{background-position:1000px 0}
  }
  @keyframes flashGreen {
    0%{background-color:rgba(0,192,135,0.35)} 100%{background-color:transparent}
  }
  @keyframes flashRed {
    0%{background-color:rgba(255,77,79,0.35)} 100%{background-color:transparent}
  }
  .flash-up   { animation: flashGreen 0.6s ease-out; border-radius:3px; }
  .flash-down { animation: flashRed   0.6s ease-out; border-radius:3px; }
  .skeleton-loader {
    background: linear-gradient(90deg,#181A20 0%,#2B3139 50%,#181A20 100%);
    background-size:1000px 100%;
    animation:shimmer 2s infinite;
    border-radius:4px;
  }
  .error-banner {
    background:#FF4D4F; border-left:4px solid #d32f2f;
    padding:12px 15px; border-radius:4px; color:#fff;
    font-size:13px; display:flex; align-items:center; gap:10px;
  }
  .chart-container, .chart-container>div, .chart-container canvas {
    min-height:560px !important; height:100% !important; width:100% !important;
  }
`;

// ---- helpers ----
function fmtPrice(v) {
  if (v === undefined || v === null) return '--';
  const n = Number(v);
  if (n >= 1000)  return n.toLocaleString('en-US', {maximumFractionDigits: 2});
  if (n >= 1)     return n.toFixed(4);
  return n.toFixed(6);
}

function decisionColor(d) {
  if (d === 'AL')              return '#00C087';
  if (d === 'PULLBACK BEKLE')  return '#FCD535';
  return '#848E9C';
}

// ---- FNG gauge (basit renkli bar) ----
function FngGauge({ value, label }) {
  const pct   = Math.min(100, Math.max(0, value || 0));
  const color = pct < 25 ? '#FF4D4F' : pct < 45 ? '#F77234' : pct < 55 ? '#FCD535' : pct < 75 ? '#73D13D' : '#00C087';
  return (
    <div>
      <div style={{display:'flex', justifyContent:'space-between', marginBottom:4}}>
        <span style={{fontSize:13, color:'#E0E0E0', fontWeight:'bold'}}>{pct} / 100</span>
        <span style={{fontSize:12, color}}>{label}</span>
      </div>
      <div style={{height:8, background:'#2B3139', borderRadius:4, overflow:'hidden'}}>
        <div style={{width:`${pct}%`, height:'100%', background:color, borderRadius:4, transition:'width 0.5s'}} />
      </div>
    </div>
  );
}

// ---- AI Widget ----
function AiWidget({ symbol, apiBase }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    fetch(`${apiBase}/api/ai/signal/${symbol}`)
      .then(r => r.json())
      .then(res => {
        setData(res.success ? res.data : null);
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [symbol, apiBase]);

  if (loading) return <div style={{color:'#848E9C', fontSize:13}}>TFT modeli hesaplıyor...</div>;
  if (!data)   return <div style={{color:'#848E9C', fontSize:13}}>{symbol} için AI verisi yok (BTC/ETH/SOL destekleniyor)</div>;

  const dirColor = data.direction === 'bullish' ? '#00C087' : data.direction === 'bearish' ? '#FF4D4F' : '#FCD535';
  const preds    = data.predicted_closes || [];

  return (
    <div style={{fontSize:12, lineHeight:1.6}}>
      <div style={{display:'flex', gap:10, alignItems:'center', marginBottom:6}}>
        <span style={{fontSize:18, fontWeight:'bold', color:dirColor}}>
          {data.prediction}
        </span>
        <span style={{color:dirColor, fontSize:13}}>
          {data.direction} — {(data.confidence * 100).toFixed(0)}% güven
        </span>
      </div>
      <div style={{color:'#848E9C'}}>
        Beklenen getiri:{' '}
        <span style={{color: data.expected_return_pct >= 0 ? '#00C087' : '#FF4D4F', fontWeight:'bold'}}>
          {data.expected_return_pct >= 0 ? '+' : ''}{data.expected_return_pct?.toFixed(2)}%
        </span>
        {' '}(sonraki 4 × 15dk)
      </div>
      {preds.length > 0 && (
        <div style={{color:'#848E9C', marginTop:3}}>
          Tahmin:{' '}
          {preds.map((p, i) => (
            <span key={i} style={{marginRight:6, color:'#E0E0E0'}}>${fmtPrice(p)}</span>
          ))}
        </div>
      )}
      <div style={{color:'#555', fontSize:11, marginTop:4}}>
        Model: {data.model} · {data.updated_at ? new Date(data.updated_at).toLocaleTimeString('tr') : ''}
      </div>
    </div>
  );
}

// ---- Makro Widget ----
function MacroWidget({ symbol, apiBase }) {
  const [btc, setBtc]   = useState(null);
  const [bull, setBull] = useState(null);

  useEffect(() => {
    fetch(`${apiBase}/api/btc_indicators`)
      .then(r => r.json())
      .then(d => d.ok && setBtc(d.data))
      .catch(() => {});
    fetch(`${apiBase}/api/bull_estimate`)
      .then(r => r.json())
      .then(d => d.ok && setBull(d.data))
      .catch(() => {});
  }, [apiBase]);

  if (!btc) return <div style={{color:'#848E9C', fontSize:13}}>Makro veri yükleniyor...</div>;

  const trend = btc.price > btc.sma200 ? '📈 SMA200 Üstü' : '📉 SMA200 Altı';
  const trendColor = btc.price > btc.sma200 ? '#00C087' : '#FF4D4F';

  return (
    <div style={{fontSize:12, lineHeight:1.7}}>
      <div style={{color: trendColor, fontWeight:'bold', marginBottom:3}}>{trend}</div>
      <div style={{color:'#848E9C'}}>
        BTC:{' '}<span style={{color:'#E0E0E0'}}>${fmtPrice(btc.price)}</span>
        {' '}· SMA200: <span style={{color:'#E0E0E0'}}>${fmtPrice(btc.sma200)}</span>
      </div>
      <div style={{color:'#848E9C'}}>
        30g Getiri:{' '}
        <span style={{color: btc.ret30 >= 0 ? '#00C087' : '#FF4D4F'}}>
          {btc.ret30 != null ? `${(btc.ret30 * 100).toFixed(1)}%` : '--'}
        </span>
      </div>
      {bull && (
        <div style={{color:'#848E9C', marginTop:3}}>
          Piyasa Fazı:{' '}
          <span style={{color:'#FCD535', fontWeight:'bold'}}>{bull.phase_label}</span>
          {' '}({bull.score}/6)
        </div>
      )}
    </div>
  );
}

// ============================================================
export default function TradingTerminal() {
  const chartContainerRef = useRef(null);
  const chartInstance     = useRef(null);

  const [showVolume, setShowVolume]   = useState(true);
  const [showSMA,    setShowSMA]      = useState(false);
  const [timeframe,  setTimeframe]    = useState('1d');

  const [signals,          setSignals]          = useState([]);
  const [isLoadingSignals, setIsLoadingSignals] = useState(true);
  const [signalError,      setSignalError]      = useState(null);
  const [selectedSymbol,   setSelectedSymbol]   = useState('BTCUSDT');
  const [searchTerm,       setSearchTerm]       = useState('');

  const [isConnected, setIsConnected]   = useState(false);
  const [flashClasses, setFlashClasses] = useState({});
  const previousPrices = useRef({});

  const [fng, setFng] = useState(null);

  // ---- 1) Sinyalleri çek ----
  const fetchSignals = useCallback(async () => {
    setIsLoadingSignals(true);
    setSignalError(null);
    try {
      const res = await fetch(`${API_BASE}/api/signals?limit=20`);
      if (!res.ok) throw new Error(`API hatası: ${res.status}`);
      const data = await res.json();

      const rows = Array.isArray(data?.data?.rows)
        ? data.data.rows
        : Array.isArray(data?.rows)
          ? data.rows
          : [];

      if (!rows.length) throw new Error('Sinyal verisi boş');
      setSignals(rows);
    } catch (err) {
      setSignalError(err.message);
      setSignals([]);
    } finally {
      setIsLoadingSignals(false);
    }
  }, []);

  useEffect(() => {
    fetchSignals();
    // Sinyalleri her 60s yenile (backend'in refresh döngüsüyle senkron)
    const id = setInterval(fetchSignals, 60000);
    return () => clearInterval(id);
  }, [fetchSignals]);

  // ---- 2) FNG yükle ----
  useEffect(() => {
    fetch(`${API_BASE}/api/fng`)
      .then(r => r.json())
      .then(d => d.ok && setFng(d.data))
      .catch(() => {});
    const id = setInterval(() => {
      fetch(`${API_BASE}/api/fng`)
        .then(r => r.json())
        .then(d => d.ok && setFng(d.data))
        .catch(() => {});
    }, 60000);
    return () => clearInterval(id);
  }, []);

  // ---- 3) KLineChart ----
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = init(chartContainerRef.current, {
      styles: {
        grid: {
          horizontal: {color:'#2B3139', visible:true},
          vertical:   {color:'#2B3139', visible:true},
        },
        candle: {
          type: 'candle_solid',
          bar: {
            upColor:'#00C087',    downColor:'#FF4D4F',    noChangeColor:'#848E9C',
            upBorderColor:'#00C087', downBorderColor:'#FF4D4F', noChangeBorderColor:'#848E9C',
            upWickColor:'#00C087',   downWickColor:'#FF4D4F',   noChangeWickColor:'#848E9C',
          },
        },
        xAxis: { axisLine:{color:'#2B3139'}, tickLine:{color:'#2B3139'}, tickText:{color:'#848E9C'} },
        yAxis: { axisLine:{color:'#2B3139'}, tickLine:{color:'#2B3139'}, tickText:{color:'#848E9C'} },
      },
    });
    if (!chart) return;
    chartInstance.current = chart;

    // Canvas yükseklik fix
    setTimeout(() => {
      if (!chartContainerRef.current) return;
      const h = chartContainerRef.current.parentElement?.offsetHeight || 500;
      chartContainerRef.current.querySelectorAll('canvas').forEach(c => {
        if (c.height > 10000000) { c.height = h; c.width = chartContainerRef.current.offsetWidth; }
      });
    }, 100);

    const tfConfig = { '15m':{type:'minute',span:15}, '1h':{type:'hour',span:1}, '4h':{type:'hour',span:4}, '1d':{type:'day',span:1} };

    chart.setSymbol({ ticker: selectedSymbol, pricePrecision: 2, volumePrecision: 0 });
    chart.setPeriod(tfConfig[timeframe] || tfConfig['1d']);
    chart.setDataLoader({
      getBars: async (params) => {
        try {
          const r = await fetch(
            `https://api.binance.com/api/v3/klines?symbol=${selectedSymbol}&interval=${timeframe}&limit=500`
          );
          if (!r.ok) throw new Error('Binance klines error');
          const d = await r.json();
          params.callback(d.map(a => ({
            timestamp: parseInt(a[0]),
            open:  parseFloat(a[1]),
            high:  parseFloat(a[2]),
            low:   parseFloat(a[3]),
            close: parseFloat(a[4]),
            volume:parseFloat(a[7]),
          })), false);
        } catch { params.callback([], false); }
      },
    });

    setTimeout(() => {
      try {
        if (showVolume) chart.createIndicator('VOL', false);
        if (showSMA)    chart.createIndicator('MA', true, {id:'candle_pane', params:{periodOne:20}});
      } catch {}
    }, 300);

    const onResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      if (chartContainerRef.current) dispose(chartContainerRef.current);
    };
  }, [selectedSymbol, timeframe]);

  // ---- 4) Volume toggle ----
  useEffect(() => {
    if (!chartInstance.current) return;
    try {
      if (showVolume) chartInstance.current.createIndicator('VOL', false);
      else            chartInstance.current.removeIndicator('VOL');
    } catch {}
  }, [showVolume]);

  // ---- 5) SMA toggle ----
  useEffect(() => {
    if (!chartInstance.current) return;
    try {
      if (showSMA) chartInstance.current.createIndicator('MA', true, {id:'candle_pane', params:{periodOne:20}});
      else         chartInstance.current.removeIndicator('MA');
    } catch {}
  }, [showSMA]);

  // ---- 6) Socket.IO — fiyat flaşları ----
  useEffect(() => {
    const socket = io(SOCKET_URL, {
      transports: ['websocket'],
      reconnectionAttempts: 5,
      reconnectionDelay: 2000,
      timeout: 8000,
    });

    socket.on('connect',       () => setIsConnected(true));
    socket.on('disconnect',    () => setIsConnected(false));
    socket.on('connect_error', () => setIsConnected(false));

    socket.on('price_update_batch', (batch) => {
      const flashes = {};
      setSignals(prev => prev.map(sig => {
        const newPrice = batch[sig.symbol];
        if (newPrice === undefined) return sig;
        const prevPrice = previousPrices.current[sig.symbol];
        if (prevPrice !== undefined && newPrice !== prevPrice) {
          flashes[sig.symbol] = newPrice > prevPrice ? 'flash-up' : 'flash-down';
        }
        previousPrices.current[sig.symbol] = newPrice;
        return { ...sig, price: newPrice };
      }));
      if (Object.keys(flashes).length) {
        setFlashClasses(prev => ({ ...prev, ...flashes }));
        Object.keys(flashes).forEach(sym => {
          setTimeout(() => setFlashClasses(prev => { const n={...prev}; delete n[sym]; return n; }), 600);
        });
      }
    });

    return () => socket.disconnect();
  }, []);

  // ---- Render ----
  const filteredSignals = signals.filter(s =>
    s.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      <style>{styles}</style>
      <div style={{display:'flex', height:'100%', width:'100%', fontFamily:'monospace'}}>

        {/* ===== Sol Panel ===== */}
        <div style={{width:300, borderRight:'1px solid #2B3139', display:'flex', flexDirection:'column', background:'#0B0E11'}}>

          {/* Header */}
          <div style={{padding:'12px 15px', borderBottom:'1px solid #2B3139', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <span style={{fontWeight:'bold', fontSize:14, color:'#E0E0E0'}}>Sinyal Motoru</span>
            <div style={{display:'flex', alignItems:'center', gap:6, fontSize:11}}>
              <span style={{
                display:'inline-block', width:8, height:8, borderRadius:'50%',
                background: isConnected ? '#00C087' : '#FF4D4F',
                animation: isConnected ? 'pulse 2s infinite' : 'none',
              }} />
              <span style={{color: isConnected ? '#00C087' : '#FF4D4F'}}>
                {isConnected ? 'Canlı' : 'Bağlanıyor...'}
              </span>
            </div>
          </div>

          {/* Arama */}
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="🔍 Sembol ara..."
            style={{
              margin:10, padding:'7px 12px',
              border:'1px solid #2B3139', borderRadius:4,
              background:'#181A20', color:'#848E9C', fontSize:13, outline:'none',
            }}
          />

          {/* Liste */}
          <div style={{flex:1, overflowY:'auto'}}>
            {signalError && (
              <div style={{padding:12, margin:10}}>
                <div className="error-banner">
                  <span>⚠️</span>
                  <div>
                    <strong>Sinyaller Yüklenemedi</strong>
                    <div style={{fontSize:12, marginTop:4}}>{signalError}</div>
                    <div style={{marginTop:6, fontSize:12}}>
                      <a href="#" onClick={e => { e.preventDefault(); fetchSignals(); }}
                         style={{color:'#fff', textDecoration:'underline'}}>Tekrar dene</a>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!signalError && isLoadingSignals && (
              <div style={{padding:10}}>
                {[...Array(8)].map((_, i) => (
                  <div key={i} style={{padding:'10px 15px', marginBottom:6, display:'flex', justifyContent:'space-between'}}>
                    <div>
                      <div className="skeleton-loader" style={{height:14, width:80, marginBottom:5}} />
                      <div className="skeleton-loader" style={{height:11, width:50}} />
                    </div>
                    <div style={{textAlign:'right'}}>
                      <div className="skeleton-loader" style={{height:12, width:60, marginBottom:5, marginLeft:'auto'}} />
                      <div className="skeleton-loader" style={{height:11, width:40, marginLeft:'auto'}} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!signalError && !isLoadingSignals && (
              filteredSignals.length === 0
                ? <div style={{padding:20, textAlign:'center', color:'#848E9C', fontSize:13}}>
                    {signals.length === 0 ? 'Sinyal bekleniyor...' : 'Sonuç yok'}
                  </div>
                : filteredSignals.map((sig, i) => (
                    <div
                      key={i}
                      onClick={() => setSelectedSymbol(sig.symbol)}
                      style={{
                        padding:'10px 15px', cursor:'pointer',
                        borderBottom:'1px solid #181A20',
                        background: selectedSymbol === sig.symbol ? '#1E2329' : 'transparent',
                        display:'flex', justifyContent:'space-between', alignItems:'center',
                        transition:'background 0.15s',
                      }}
                    >
                      <div>
                        <div style={{fontWeight:'bold', color:'#E0E0E0', fontSize:13}}>{sig.symbol}</div>
                        <div style={{fontSize:11, color: decisionColor(sig.decision), marginTop:2}}>
                          {sig.decision}
                        </div>
                        <div style={{fontSize:10, color:'#555', marginTop:1}}>Skor: {sig.score?.toFixed(1)}</div>
                      </div>
                      <div style={{textAlign:'right'}}>
                        <div
                          className={flashClasses[sig.symbol] || ''}
                          style={{fontSize:13, color:'#E0E0E0', fontWeight:'bold', padding:'1px 4px'}}
                        >
                          ${fmtPrice(sig.price)}
                        </div>
                        <div style={{
                          fontSize:11, marginTop:2,
                          color: sig.change24_pct >= 0 ? '#00C087' : '#FF4D4F',
                        }}>
                          {sig.change24_pct >= 0 ? '+' : ''}{sig.change24_pct?.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  ))
            )}
          </div>
        </div>

        {/* ===== Sağ Panel ===== */}
        <div style={{flex:1, display:'flex', flexDirection:'column', background:'#0B0E11'}}>

          {/* Grafik header */}
          <div style={{
            display:'flex', alignItems:'center', justifyContent:'space-between',
            padding:'12px 15px', borderBottom:'1px solid #2B3139',
          }}>
            <div style={{display:'flex', alignItems:'center', gap:15}}>
              <span style={{fontSize:17, fontWeight:'bold', color:'#E0E0E0'}}>
                {selectedSymbol}
                <span style={{fontSize:11, color:'#848E9C', fontWeight:'normal', marginLeft:6}}>
                  {timeframe.toUpperCase()}
                </span>
              </span>
              <div style={{display:'flex', gap:5, borderLeft:'1px solid #2B3139', paddingLeft:15}}>
                {['15m','1h','4h','1d'].map(tf => (
                  <button key={tf} onClick={() => setTimeframe(tf)} style={{
                    padding:'3px 9px', cursor:'pointer', fontSize:11, borderRadius:3,
                    border: `1px solid ${timeframe===tf ? '#00C087' : '#2B3139'}`,
                    background: timeframe===tf ? 'rgba(0,192,135,0.1)' : 'transparent',
                    color: timeframe===tf ? '#00C087' : '#848E9C',
                    fontWeight: timeframe===tf ? 'bold' : 'normal',
                  }}>{tf.toUpperCase()}</button>
                ))}
              </div>
            </div>
            <div style={{display:'flex', gap:16, fontSize:12}}>
              <label style={{display:'flex', alignItems:'center', gap:4, cursor:'pointer', color:'#848E9C'}}>
                <input type="checkbox" checked={showVolume} onChange={e => setShowVolume(e.target.checked)} />
                Hacim
              </label>
              <label style={{display:'flex', alignItems:'center', gap:4, cursor:'pointer', color:'#848E9C'}}>
                <input type="checkbox" checked={showSMA} onChange={e => setShowSMA(e.target.checked)} />
                SMA 20
              </label>
            </div>
          </div>

          {/* Grafik */}
          <div ref={chartContainerRef} className="chart-container"
               style={{flex:1, width:'100%', minHeight:560, position:'relative'}} />

          {/* ===== Widget Bar ===== */}
          <div style={{
            borderTop:'1px solid #2B3139', background:'#0B0E11',
            display:'grid', gridTemplateColumns:'1fr 1fr 1fr',
            minHeight:140,
          }}>

            {/* AI Asistan */}
            <div style={{borderRight:'1px solid #2B3139', padding:'12px 15px'}}>
              <div style={{fontSize:11, fontWeight:'bold', color:'#FCD535', marginBottom:8, letterSpacing:1}}>
                🤖 TFT AI ASISTAN
              </div>
              <AiWidget symbol={selectedSymbol} apiBase={API_BASE} />
            </div>

            {/* Makro Analiz */}
            <div style={{borderRight:'1px solid #2B3139', padding:'12px 15px'}}>
              <div style={{fontSize:11, fontWeight:'bold', color:'#FCD535', marginBottom:8, letterSpacing:1}}>
                📊 MAKRO ANALİZ
              </div>
              <MacroWidget symbol={selectedSymbol} apiBase={API_BASE} />
            </div>

            {/* Fear & Greed */}
            <div style={{padding:'12px 15px'}}>
              <div style={{fontSize:11, fontWeight:'bold', color:'#FCD535', marginBottom:8, letterSpacing:1}}>
                😨 FEAR & GREED
              </div>
              {fng ? (
                <FngGauge value={fng.value} label={fng.value_classification} />
              ) : (
                <div style={{color:'#848E9C', fontSize:13}}>Yükleniyor...</div>
              )}
            </div>

          </div>
        </div>

      </div>
    </>
  );
}
