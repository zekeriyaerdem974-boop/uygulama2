/* =====================================================================
   ZKR Analiz Pattern Engine — FAZ 14
   Pure analysis functions. No DOM, no fetch.
   All calculations use klines candle data (time, open, high, low, close, volume).
   ===================================================================== */

const PatternEngine = (() => {
  'use strict';

  // ── Swing High / Swing Low ─────────────────────────────────────────────
  /**
   * Detect pivot swing highs and lows.
   * @param {Array<{time,open,high,low,close}>} candles
   * @param {number} win — lookback/lookahead window (default 5)
   * @returns {{highs: Array<{time,price,index}>, lows: Array<{time,price,index}>}}
   */
  function detectSwings(candles, win = 5) {
    const highs = [], lows = [];
    if (!candles || candles.length < win * 2 + 1) return { highs, lows };

    for (let i = win; i < candles.length - win; i++) {
      let isHigh = true, isLow = true;
      const hi = Number(candles[i].high);
      const lo = Number(candles[i].low);
      for (let j = i - win; j <= i + win; j++) {
        if (j === i) continue;
        if (Number(candles[j].high) >= hi) isHigh = false;
        if (Number(candles[j].low) <= lo) isLow = false;
        if (!isHigh && !isLow) break;
      }
      if (isHigh) highs.push({ time: candles[i].time, price: hi, index: i });
      if (isLow)  lows.push({ time: candles[i].time, price: lo, index: i });
    }
    return { highs, lows };
  }

  // ── Support / Resistance ───────────────────────────────────────────────
  /**
   * Cluster swing points into S/R levels.
   * @param {{highs,lows}} swings — from detectSwings
   * @param {Array} candles — for context (last price, ATR)
   * @param {number} maxLevels
   * @returns {{supports: Array<{price,strength,touches}>, resistances: Array<{price,strength,touches}>}}
   */
  function detectSupportResistance(swings, candles, maxLevels = 5) {
    if (!candles || candles.length < 20) return { supports: [], resistances: [] };

    // Calculate clustering threshold based on ATR
    const atr = _atr(candles, 14);
    const threshold = atr * 0.6;
    const lastPrice = Number(candles[candles.length - 1].close);

    // Collect all swing prices with type
    const points = [];
    for (const h of (swings.highs || [])) points.push({ price: h.price, type: 'r', index: h.index });
    for (const l of (swings.lows || []))  points.push({ price: l.price, type: 's', index: l.index });

    // Cluster nearby prices
    points.sort((a, b) => a.price - b.price);
    const clusters = [];
    for (const p of points) {
      const found = clusters.find(c => Math.abs(c.price - p.price) < threshold);
      if (found) {
        found.prices.push(p.price);
        found.price = found.prices.reduce((a, b) => a + b, 0) / found.prices.length;
        found.touches++;
        if (p.index > found.lastIndex) found.lastIndex = p.index;
      } else {
        clusters.push({ price: p.price, prices: [p.price], touches: 1, lastIndex: p.index });
      }
    }

    // Score clusters: more touches + recency = stronger
    const totalCandles = candles.length;
    for (const c of clusters) {
      c.strength = c.touches + (c.lastIndex / totalCandles) * 0.5;
    }

    // Sort by strength descending
    clusters.sort((a, b) => b.strength - a.strength);

    // Split into supports & resistances relative to current price
    const supports = [], resistances = [];
    for (const c of clusters) {
      const level = { price: Math.round(c.price * 100) / 100, strength: c.strength, touches: c.touches };
      if (c.price < lastPrice) {
        if (supports.length < maxLevels) supports.push(level);
      } else {
        if (resistances.length < maxLevels) resistances.push(level);
      }
    }

    // Sort supports descending (nearest first), resistances ascending
    supports.sort((a, b) => b.price - a.price);
    resistances.sort((a, b) => a.price - b.price);

    return { supports, resistances };
  }

  // ── Breakout Zones ─────────────────────────────────────────────────────
  /**
   * Detect breakout from S/R levels.
   * @param {{supports,resistances}} sr
   * @param {Array} candles
   * @param {Array} volumes — [{time, value}]
   * @returns {Array<{time,price,type:'bullish'|'bearish',strength}>}
   */
  function detectBreakouts(sr, candles, volumes) {
    const breakouts = [];
    if (!candles || candles.length < 10) return breakouts;

    // Average volume for comparison
    const recentVols = (volumes || []).slice(-30);
    const avgVol = recentVols.length ? recentVols.reduce((s, v) => s + Number(v.value), 0) / recentVols.length : 0;

    const lookback = Math.min(20, candles.length);
    for (let i = candles.length - lookback; i < candles.length; i++) {
      const c = candles[i];
      const close = Number(c.close);
      const vol = volumes && volumes[i] ? Number(volumes[i].value) : 0;
      const volStrength = avgVol > 0 ? vol / avgVol : 1;

      // Check resistance breakouts (bullish)
      for (const r of (sr.resistances || [])) {
        const prev = i > 0 ? Number(candles[i - 1].close) : close;
        if (prev <= r.price && close > r.price && close > Number(c.open)) {
          breakouts.push({
            time: c.time, price: r.price, type: 'bullish',
            strength: Math.min(3, r.touches + (volStrength > 1.2 ? 1 : 0)),
            endTime: candles[Math.min(i + 3, candles.length - 1)].time,
          });
        }
      }
      // Check support breakdowns (bearish)
      for (const s of (sr.supports || [])) {
        const prev = i > 0 ? Number(candles[i - 1].close) : close;
        if (prev >= s.price && close < s.price && close < Number(c.open)) {
          breakouts.push({
            time: c.time, price: s.price, type: 'bearish',
            strength: Math.min(3, s.touches + (volStrength > 1.2 ? 1 : 0)),
            endTime: candles[Math.min(i + 3, candles.length - 1)].time,
          });
        }
      }
    }

    // Deduplicate: keep strongest per level
    const seen = new Map();
    for (const b of breakouts) {
      const key = `${b.type}_${b.price.toFixed(2)}`;
      if (!seen.has(key) || b.strength > seen.get(key).strength) seen.set(key, b);
    }
    return [...seen.values()].slice(-6);
  }

  // ── Trendlines ─────────────────────────────────────────────────────────
  /**
   * Find best-fit trendlines from swing points.
   * Returns at most 2 lines: one support trendline, one resistance trendline.
   * @param {{highs,lows}} swings
   * @param {Array} candles
   * @returns {Array<{type:'support'|'resistance', points: [{time,price}], slope, score}>}
   */
  function detectTrendlines(swings, candles) {
    const lines = [];
    if (!candles || candles.length < 30) return lines;

    // Support trendline: ascending lows
    const stl = _bestTrendline(swings.lows || [], candles, 'asc');
    if (stl) lines.push({ type: 'support', ...stl });

    // Resistance trendline: descending highs
    const rtl = _bestTrendline(swings.highs || [], candles, 'desc');
    if (rtl) lines.push({ type: 'resistance', ...rtl });

    return lines;
  }

  function _bestTrendline(points, candles, dir) {
    if (points.length < 2) return null;
    // Use recent points only
    const recent = points.slice(-8);
    let best = null;

    for (let i = 0; i < recent.length - 1; i++) {
      for (let j = i + 1; j < recent.length; j++) {
        const p1 = recent[i], p2 = recent[j];
        const dx = p2.index - p1.index;
        if (dx < 5) continue;
        const slope = (p2.price - p1.price) / dx;

        // Count touches (points near the line)
        let touches = 0;
        let violations = 0;
        const atr = _atr(candles, 14) * 0.3;
        for (const p of recent) {
          const expected = p1.price + slope * (p.index - p1.index);
          const diff = p.price - expected;
          if (Math.abs(diff) < atr) touches++;
          // For support line, price should be above; for resistance, below
          if (dir === 'asc' && diff < -atr * 2) violations++;
          if (dir === 'desc' && diff > atr * 2) violations++;
        }

        if (touches >= 2 && violations <= 1) {
          const score = touches - violations * 2;
          if (!best || score > best.score) {
            // Extend line to chart edges
            const startIdx = Math.max(0, p1.index - 5);
            const endIdx = Math.min(candles.length - 1, p2.index + 15);
            const startPrice = p1.price + slope * (startIdx - p1.index);
            const endPrice = p1.price + slope * (endIdx - p1.index);
            best = {
              points: [
                { time: candles[startIdx].time, value: startPrice },
                { time: candles[endIdx].time, value: endPrice },
              ],
              slope, score, touches,
            };
          }
        }
      }
    }
    return best;
  }

  // ── Triangle Detection ─────────────────────────────────────────────────
  /**
   * Detect triangle patterns from converging trendlines.
   * @param {{highs,lows}} swings
   * @param {Array} candles
   * @returns {{type:'ascending'|'descending'|'symmetrical'|null, upperLine,lowerLine,apex} | null}
   */
  function detectTriangles(swings, candles) {
    if (!candles || candles.length < 40) return null;
    const highs = (swings.highs || []).slice(-6);
    const lows = (swings.lows || []).slice(-6);
    if (highs.length < 2 || lows.length < 2) return null;

    // Compute slopes
    const hSlope = _linearSlope(highs);
    const lSlope = _linearSlope(lows);

    const atr = _atr(candles, 14);
    const flatThreshold = atr * 0.005; // near-zero slope = flat

    let type = null;
    if (Math.abs(hSlope) < flatThreshold && lSlope > flatThreshold) {
      type = 'ascending';
    } else if (hSlope < -flatThreshold && Math.abs(lSlope) < flatThreshold) {
      type = 'descending';
    } else if (hSlope < -flatThreshold && lSlope > flatThreshold) {
      type = 'symmetrical';
    }

    if (!type) return null;

    // Build triangle lines
    const upperLine = highs.length >= 2
      ? [{ time: highs[0].time, value: highs[0].price }, { time: highs[highs.length - 1].time, value: highs[highs.length - 1].price }]
      : null;
    const lowerLine = lows.length >= 2
      ? [{ time: lows[0].time, value: lows[0].price }, { time: lows[lows.length - 1].time, value: lows[lows.length - 1].price }]
      : null;

    return { type, upperLine, lowerLine };
  }

  function _linearSlope(points) {
    if (points.length < 2) return 0;
    const n = points.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
    for (let i = 0; i < n; i++) {
      sumX += points[i].index;
      sumY += points[i].price;
      sumXY += points[i].index * points[i].price;
      sumX2 += points[i].index * points[i].index;
    }
    const denom = n * sumX2 - sumX * sumX;
    return denom !== 0 ? (n * sumXY - sumX * sumY) / denom : 0;
  }

  // ── Flag / Pennant ─────────────────────────────────────────────────────
  /**
   * Detect flag/pennant after strong impulse move.
   * @param {Array} candles
   * @param {{highs,lows}} swings
   * @returns {{type:'bull_flag'|'bear_flag'|null, poleStart,poleEnd,flagStart,flagEnd} | null}
   */
  function detectFlags(candles, swings) {
    if (!candles || candles.length < 30) return null;

    const atr = _atr(candles, 14);
    // Look for strong move in last 40 candles, then consolidation
    const lookback = Math.min(40, candles.length - 10);
    const start = candles.length - lookback;

    // Find strongest impulse (pole)
    let bestPole = null;
    for (let i = start; i < candles.length - 10; i++) {
      for (let len = 5; len <= 15 && i + len < candles.length - 5; len++) {
        const move = Number(candles[i + len].close) - Number(candles[i].close);
        const moveAtr = Math.abs(move) / atr;
        if (moveAtr > 2.5 && (!bestPole || moveAtr > bestPole.moveAtr)) {
          bestPole = { start: i, end: i + len, move, moveAtr, dir: move > 0 ? 'bull' : 'bear' };
        }
      }
    }
    if (!bestPole) return null;

    // Check consolidation after pole
    const flagStart = bestPole.end;
    const flagEnd = Math.min(flagStart + 15, candles.length - 1);
    if (flagEnd - flagStart < 4) return null;

    const flagCandles = candles.slice(flagStart, flagEnd + 1);
    const flagHighs = flagCandles.map(c => Number(c.high));
    const flagLows = flagCandles.map(c => Number(c.low));
    const flagRange = Math.max(...flagHighs) - Math.min(...flagLows);

    // Flag should retrace less than 50% of pole and range should be narrow
    const poleRange = Math.abs(bestPole.move);
    if (flagRange > poleRange * 0.6) return null;

    return {
      type: bestPole.dir === 'bull' ? 'bull_flag' : 'bear_flag',
      poleStart: { time: candles[bestPole.start].time, price: Number(candles[bestPole.start].close) },
      poleEnd: { time: candles[bestPole.end].time, price: Number(candles[bestPole.end].close) },
      flagHigh: Math.max(...flagHighs),
      flagLow: Math.min(...flagLows),
      flagStartTime: candles[flagStart].time,
      flagEndTime: candles[flagEnd].time,
    };
  }

  // ── Range Detection ────────────────────────────────────────────────────
  /**
   * Detect sideways range in recent candles.
   * @param {Array} candles
   * @param {number} lookback
   * @returns {{inRange:boolean, upper,lower,startTime,endTime} | null}
   */
  function detectRanges(candles, lookback = 40) {
    if (!candles || candles.length < lookback) return null;

    const recent = candles.slice(-lookback);
    const highs = recent.map(c => Number(c.high));
    const lows = recent.map(c => Number(c.low));
    const closes = recent.map(c => Number(c.close));
    const upper = Math.max(...highs);
    const lower = Math.min(...lows);
    const range = upper - lower;
    const mid = (upper + lower) / 2;

    // Check if price stays within band (no strong trend)
    const atr = _atr(candles, 14);
    // Range width should be moderate (not too tight, not trending)
    if (range < atr * 2) return null; // too tight
    if (range > atr * 8) return null; // trending

    // Check mean reversion — most closes should be near middle
    let nearMid = 0;
    for (const c of closes) {
      if (Math.abs(c - mid) < range * 0.35) nearMid++;
    }
    const rangeRatio = nearMid / closes.length;
    if (rangeRatio < 0.4) return null; // not ranging

    // Check no clear trend (slope of closes should be near zero)
    const firstHalf = closes.slice(0, Math.floor(closes.length / 2));
    const secondHalf = closes.slice(Math.floor(closes.length / 2));
    const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
    if (Math.abs(avgSecond - avgFirst) > range * 0.25) return null; // trending

    return {
      inRange: true,
      upper: Math.round(upper * 100) / 100,
      lower: Math.round(lower * 100) / 100,
      startTime: recent[0].time,
      endTime: recent[recent.length - 1].time,
    };
  }

  // ── Trend Direction ────────────────────────────────────────────────────
  /**
   * Simple trend direction from EMA crossover.
   * @param {Array} candles
   * @returns {'uptrend'|'downtrend'|'sideways'}
   */
  function trendDirection(candles) {
    if (!candles || candles.length < 50) return 'sideways';
    const closes = candles.map(c => Number(c.close));
    const ema20 = _emaCalc(closes, 20);
    const ema50 = _emaCalc(closes, 50);
    if (ema20.length < 2 || ema50.length < 2) return 'sideways';

    const e20 = ema20[ema20.length - 1];
    const e50 = ema50[ema50.length - 1];
    const diff = (e20 - e50) / e50;
    if (diff > 0.003) return 'uptrend';
    if (diff < -0.003) return 'downtrend';
    return 'sideways';
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  function _atr(candles, period) {
    if (candles.length < period + 1) return 1;
    let sum = 0;
    for (let i = candles.length - period; i < candles.length; i++) {
      const h = Number(candles[i].high), l = Number(candles[i].low);
      const pc = Number(candles[i - 1].close);
      sum += Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
    }
    return sum / period;
  }

  function _emaCalc(arr, period) {
    if (arr.length < period) return [];
    const k = 2 / (period + 1);
    let prev = arr.slice(0, period).reduce((a, b) => a + b, 0) / period;
    const result = [prev];
    for (let i = period; i < arr.length; i++) {
      prev = arr[i] * k + prev * (1 - k);
      result.push(prev);
    }
    return result;
  }

  // ── Public API ─────────────────────────────────────────────────────────
  return {
    detectSwings,
    detectSupportResistance,
    detectBreakouts,
    detectTrendlines,
    detectTriangles,
    detectFlags,
    detectRanges,
    trendDirection,
  };
})();
