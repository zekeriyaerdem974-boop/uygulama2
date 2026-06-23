/* =====================================================================
   ZKR Analiz Indicator Calculation Engine — FAZ 13
   Pure math functions. No DOM, no fetch.
   All calculations use klines data (close, high, low, volume, time).
   ===================================================================== */

const IndicatorEngine = (() => {
  'use strict';

  // ── EMA ────────────────────────────────────────────────────────────────
  /**
   * Exponential Moving Average.
   * @param {Array<{time:number, close:number}>} candles
   * @param {number} period
   * @returns {Array<{time:number, value:number}>}
   */
  function ema(candles, period) {
    if (!candles || candles.length < period) return [];
    const k = 2 / (period + 1);
    const result = [];

    // Seed: SMA of first `period` candles
    let sum = 0;
    for (let i = 0; i < period; i++) sum += Number(candles[i].close);
    let prev = sum / period;
    result.push({ time: candles[period - 1].time, value: prev });

    for (let i = period; i < candles.length; i++) {
      prev = Number(candles[i].close) * k + prev * (1 - k);
      result.push({ time: candles[i].time, value: prev });
    }
    return result;
  }

  /**
   * Incremental EMA: compute next value from previous EMA.
   * @param {number} prevEma
   * @param {number} newClose
   * @param {number} period
   * @returns {number}
   */
  function emaNext(prevEma, newClose, period) {
    const k = 2 / (period + 1);
    return newClose * k + prevEma * (1 - k);
  }

  // ── SMA ────────────────────────────────────────────────────────────────
  /**
   * Simple Moving Average.
   * @param {Array<{time:number, close:number}>} candles
   * @param {number} period
   * @returns {Array<{time:number, value:number}>}
   */
  function sma(candles, period) {
    if (!candles || candles.length < period) return [];
    const result = [];
    let sum = 0;

    for (let i = 0; i < period; i++) sum += Number(candles[i].close);
    result.push({ time: candles[period - 1].time, value: sum / period });

    for (let i = period; i < candles.length; i++) {
      sum += Number(candles[i].close) - Number(candles[i - period].close);
      result.push({ time: candles[i].time, value: sum / period });
    }
    return result;
  }

  /**
   * Incremental SMA: given old window and new close.
   * @param {Array<number>} window  - last `period` closes
   * @param {number} newClose
   * @returns {number}
   */
  function smaNext(window, newClose) {
    const period = window.length;
    const oldClose = window[0];
    const oldSum = window.reduce((a, b) => a + b, 0);
    return (oldSum - oldClose + newClose) / period;
  }

  // ── VWAP ───────────────────────────────────────────────────────────────
  /**
   * Volume Weighted Average Price.
   * Uses typical price = (high + low + close) / 3.
   * @param {Array<{time:number, high:number, low:number, close:number}>} candles
   * @param {Array<{time:number, value:number}>} volumes
   * @returns {Array<{time:number, value:number}>}
   */
  function vwap(candles, volumes) {
    if (!candles || !volumes || candles.length === 0) return [];
    const result = [];
    let cumPV = 0;
    let cumV = 0;

    for (let i = 0; i < candles.length; i++) {
      const c = candles[i];
      const v = volumes[i]?.value ?? 0;
      const tp = (Number(c.high) + Number(c.low) + Number(c.close)) / 3;
      cumPV += tp * v;
      cumV += v;
      if (cumV > 0) {
        result.push({ time: c.time, value: cumPV / cumV });
      }
    }
    return result;
  }

  /**
   * Incremental VWAP.
   * @param {number} cumPV  - previous cumulative price*volume
   * @param {number} cumV   - previous cumulative volume
   * @param {{high:number, low:number, close:number}} candle
   * @param {number} vol
   * @returns {{value:number, cumPV:number, cumV:number}}
   */
  function vwapNext(cumPV, cumV, candle, vol) {
    const tp = (Number(candle.high) + Number(candle.low) + Number(candle.close)) / 3;
    const newCumPV = cumPV + tp * vol;
    const newCumV = cumV + vol;
    return {
      value: newCumV > 0 ? newCumPV / newCumV : 0,
      cumPV: newCumPV,
      cumV: newCumV,
    };
  }

  // ── Bollinger Bands ────────────────────────────────────────────────────
  /**
   * Bollinger Bands (SMA ± k * std).
   * @param {Array<{time:number, close:number}>} candles
   * @param {number} period  - default 20
   * @param {number} mult    - default 2
   * @returns {{upper: Array, middle: Array, lower: Array}}
   */
  function bollinger(candles, period = 20, mult = 2) {
    if (!candles || candles.length < period) return { upper: [], middle: [], lower: [] };
    const upper = [], middle = [], lower = [];

    for (let i = period - 1; i < candles.length; i++) {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += Number(candles[j].close);
      const mean = sum / period;

      let sqSum = 0;
      for (let j = i - period + 1; j <= i; j++) {
        const diff = Number(candles[j].close) - mean;
        sqSum += diff * diff;
      }
      const std = Math.sqrt(sqSum / period);

      const t = candles[i].time;
      middle.push({ time: t, value: mean });
      upper.push({ time: t, value: mean + mult * std });
      lower.push({ time: t, value: mean - mult * std });
    }

    return { upper, middle, lower };
  }

  /**
   * Incremental Bollinger: given last `period` closes.
   * @param {Array<number>} window  - last `period` close values
   * @param {number} mult
   * @returns {{upper:number, middle:number, lower:number}}
   */
  function bollingerNext(window, mult = 2) {
    const period = window.length;
    const mean = window.reduce((a, b) => a + b, 0) / period;
    let sqSum = 0;
    for (const c of window) {
      const d = c - mean;
      sqSum += d * d;
    }
    const std = Math.sqrt(sqSum / period);
    return { upper: mean + mult * std, middle: mean, lower: mean - mult * std };
  }

  // ── Volume MA ──────────────────────────────────────────────────────────
  /**
   * Moving average of volume.
   * @param {Array<{time:number, value:number}>} volumes
   * @param {number} period
   * @returns {Array<{time:number, value:number}>}
   */
  function volumeMA(volumes, period = 20) {
    if (!volumes || volumes.length < period) return [];
    const result = [];
    let sum = 0;

    for (let i = 0; i < period; i++) sum += Number(volumes[i].value);
    result.push({ time: volumes[period - 1].time, value: sum / period });

    for (let i = period; i < volumes.length; i++) {
      sum += Number(volumes[i].value) - Number(volumes[i - period].value);
      result.push({ time: volumes[i].time, value: sum / period });
    }
    return result;
  }

  // ── Public API ─────────────────────────────────────────────────────────
  return {
    ema,
    emaNext,
    sma,
    smaNext,
    vwap,
    vwapNext,
    bollinger,
    bollingerNext,
    volumeMA,
  };
})();
