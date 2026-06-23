# -*- coding: utf-8 -*-
"""
BullWatch Unified Engine
Kaynak: bullwatch_v2/app.py + TFT AI entegrasyonu
Port: 34000
"""
import os, json, time, math, requests, threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from dateutil import tz
from typing import List, Dict
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

# -------------------- App & Config --------------------
app = Flask(__name__,
            template_folder="/home/zkr-kripto2/Belgeler/Cypt/bullwatch_v2/templates",
            static_folder="/home/zkr-kripto2/Belgeler/Cypt/bullwatch_v2/static")
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

BINANCE_API  = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"
ALT_FNG_API  = "https://api.alternative.me/fng/?limit=1"
FR_API       = "https://www.federalregister.gov/api/v1/documents.json"
COINGECKO_API= "https://api.coingecko.com/api/v3"

OLLAMA_HOST        = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
COINGLASS_API_KEY  = os.getenv("COINGLASS_API_KEY")
TZ                 = tz.gettz("Europe/Istanbul")

CHAT_REFRESH_SEC   = int(os.getenv("CHAT_REFRESH_SEC", "60"))
TOP4H_REFRESH_SEC  = int(os.getenv("TOP4H_REFRESH_SEC", "900"))
TOP4H_MAX_SYMBOLS  = int(os.getenv("TOP4H_MAX_SYMBOLS", "100"))
TOP4H_KLINES       = int(os.getenv("TOP4H_KLINES", "100"))
TOP4H_INTERVAL     = "4h"

# TFT model dosyaları
_BASE = "/home/zkr-kripto2/Belgeler/Cypt/user_data/strategies"
TFT_MODELS = {
    "BTC": {
        "ckpt": f"{_BASE}/BTC_Yapay_Zeka_Model_2019_2025.ckpt",
        "pkl":  f"{_BASE}/BTC_Yapay_Zeka_Dataset_2019_2025.pkl",
    },
    "ETH": {
        "ckpt": f"{_BASE}/ETH_Yapay_Zeka_Model_2019_2025.ckpt",
        "pkl":  f"{_BASE}/ETH_Yapay_Zeka_Dataset_2019_2025.pkl",
    },
    "SOL": {
        "ckpt": f"{_BASE}/SOL_Yapay_Zeka_Model_2019_2025.ckpt",
        "pkl":  f"{_BASE}/SOL_Yapay_Zeka_Dataset_2019_2025.pkl",
    },
}

# -------------------- Thread-Safe Cache --------------------
_cache = {}
_CACHE_LOCK = threading.Lock()

def cache_get(key, ttl=60):
    with _CACHE_LOCK:
        it = _cache.get(key)
        if not it:
            return None
        ts, val = it
    if time.time() - ts > ttl:
        return None
    return val

def cache_set(key, val):
    with _CACHE_LOCK:
        _cache[key] = (time.time(), val)

def utcnow():
    return datetime.now(timezone.utc)

# -------------------- Runtime Thresholds --------------------
DEFAULT_THRESHOLDS = {
    "overextended_change24_max": 25.0,
    "min_ret7_pct":              5.0,
    "min_change24_pct":          2.0,
    "max_change24_pct":          15.0,
    "heat_atr_max":              1.5,
    "require_btc_regime":        True,
    "require_above200":          True,
}
THRESHOLDS_KEY = "runtime_thresholds_v1"

def get_thresholds():
    th = cache_get(THRESHOLDS_KEY, ttl=10**9)
    if th is None:
        th = DEFAULT_THRESHOLDS.copy()
        cache_set(THRESHOLDS_KEY, th)
    return th

def update_thresholds(partial: Dict):
    th = get_thresholds().copy()
    allowed = set(DEFAULT_THRESHOLDS.keys())
    for k, v in (partial or {}).items():
        if k in allowed:
            if k in ("require_btc_regime", "require_above200"):
                th[k] = bool(v)
            else:
                try:
                    th[k] = float(v)
                except Exception:
                    continue
    cache_set(THRESHOLDS_KEY, th)
    return th

# -------------------- Utilities --------------------
def simple_sma(series, window):
    if len(series) < window:
        return None
    return pd.Series(series).rolling(window=window).mean().iloc[-1]

def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

# -------------------- External APIs --------------------
def binance_klines(symbol="BTCUSDT", interval="1d", limit=400):
    r = requests.get(f"{BINANCE_API}/api/v3/klines",
                     params={"symbol": symbol, "interval": interval, "limit": limit},
                     timeout=15)
    r.raise_for_status()
    rows = []
    for a in r.json():
        rows.append({
            "open_time":  int(a[0]),
            "open":       float(a[1]),
            "high":       float(a[2]),
            "low":        float(a[3]),
            "close":      float(a[4]),
            "volume":     float(a[5]),
            "close_time": int(a[6]),
        })
    return pd.DataFrame(rows)

def fng_latest():
    key = "fng_latest"
    c = cache_get(key, ttl=60)
    if c:
        return c
    r = requests.get(ALT_FNG_API, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("data"):
        it = data["data"][0]
        out = {
            "value":                  int(it["value"]),
            "value_classification":   it["value_classification"],
            "timestamp":              int(it["timestamp"]),
            "time_readable":          it.get("time_until_update"),
        }
        cache_set(key, out)
        return out
    return {"value": None, "value_classification": None, "timestamp": None, "time_readable": None}

def fapi_open_interest(symbol="BTCUSDT"):
    r = requests.get(f"{BINANCE_FAPI}/fapi/v1/openInterest", params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return r.json()

def fapi_open_interest_hist(symbol="BTCUSDT", period="1d", limit=30):
    r = requests.get(f"{BINANCE_FAPI}/futures/data/openInterestHist",
                     params={"symbol": symbol, "period": period, "limit": limit}, timeout=10)
    r.raise_for_status()
    return r.json()

def blockchain_hashrate(days=30):
    url = "https://api.blockchain.info/charts/hash-rate"
    r = requests.get(url, params={"format": "json", "timespan": f"{days}days"}, timeout=10)
    r.raise_for_status()
    return r.json()

def defillama_stablecoins():
    url = "https://stablecoins.llama.fi/stablecoins"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    coins = r.json().get("peggedAssets", []) or []
    rows = []
    for c in coins:
        if c.get("pegType") != "peggedUSD":
            continue
        sym  = c.get("symbol") or c.get("name") or "UNKNOWN"
        cur  = (c.get("circulating") or {}).get("peggedUSD")
        prev = (c.get("circulatingPrevDay") or {}).get("peggedUSD")
        if cur is None or prev is None:
            continue
        rows.append({"symbol": sym, "change24_usd": float(cur) - float(prev)})
    rows.sort(key=lambda x: -abs(x["change24_usd"]))
    top = rows[:10]
    return {"top": top, "approx_netflow_24h_usd": sum(x["change24_usd"] for x in top)}

def coinglass_coinbase_premium():
    if not COINGLASS_API_KEY:
        return {"error": "COINGLASS_API_KEY missing"}
    headers = {"coinglassSecret": COINGLASS_API_KEY}
    r = requests.get("https://open-api-v4.coinglass.com/api/coinbase-premium-index",
                     params={"symbol": "BTC"}, headers=headers, timeout=12)
    if r.status_code != 200:
        return {"error": f"http {r.status_code}"}
    return r.json()

# -------------------- Federal Register (ETF Events) --------------------
ASSET_KEYWORDS = {
    "BTC": ["bitcoin","spot bitcoin","btc","iShares","BlackRock","Fidelity","ARK 21Shares","Valkyrie","VanEck","WisdomTree","Franklin","Bitwise","Grayscale","Hashdex"],
    "ETH": ["ether","ethereum","spot ether","eth","iShares","BlackRock","Fidelity","VanEck","Bitwise","Grayscale","21Shares","Franklin","WisdomTree"],
    "SOL": ["solana","spot solana","sol","VanEck","21Shares","Fidelity","Hashdex","Grayscale","BlackRock"],
    "XRP": ["xrp","ripple","spot xrp","ripple labs","21Shares","Hashdex","Grayscale","BlackRock","Fidelity"],
}
EXCHANGE_KEYWORDS = ["Cboe BZX","NYSE Arca","Nasdaq","Cboe EDGX","Cboe BYX"]

def fr_search_documents(term, per_page=30, agency_slug="securities-and-exchange-commission"):
    params = {
        "per_page": per_page,
        "order": "newest",
        "conditions[term]": term,
        "conditions[agencies][]": agency_slug,
    }
    r = requests.get(FR_API, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def classify_fr_status(title: str):
    t = (title or "").lower()
    if "granting approval" in t or "order approving" in t or "approval order" in t: return "approved"
    if "instituting proceedings" in t: return "proceedings"
    if "designation of a longer period" in t or "extend" in t or "delay" in t: return "delay"
    if "notice of filing" in t or "notice" in t: return "filed"
    if "immediate effectiveness" in t: return "effective"
    return "unknown"

def detect_exchange(title):
    for ex in EXCHANGE_KEYWORDS:
        if ex.lower() in (title or "").lower():
            return ex
    return None

def rough_deadline(status: str, pub_date: str):
    if not pub_date:
        return None
    try:
        d = datetime.fromisoformat(pub_date) if "T" in pub_date else datetime.fromisoformat(pub_date + "T00:00:00")
        d = d.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    if status == "filed":       return (d + timedelta(days=45)).isoformat()
    if status == "proceedings": return (d + timedelta(days=60)).isoformat()
    if status == "delay":       return (d + timedelta(days=45)).isoformat()
    return None

def fetch_dynamic_etf_events():
    key = "dynamic_etf_events_v2"
    c = cache_get(key, ttl=300)
    if c:
        return c
    ev = []
    for asset, kws in ASSET_KEYWORDS.items():
        found_any = False
        for kw in kws:
            term = f"{kw} 19b-4"
            try:
                js = fr_search_documents(term, per_page=200)
                for d in js.get("results", []):
                    title = d.get("title", "")
                    pub   = d.get("publication_date") or d.get("effective_on") or d.get("signing_date") or d.get("created_at")
                    url   = d.get("html_url") or d.get("pdf_url")
                    doc   = d.get("document_number")
                    abstract = d.get("abstract") or ""
                    status   = classify_fr_status(title)
                    exch     = detect_exchange(title) or "—"
                    manager  = None
                    for m in ["iShares","BlackRock","Fidelity","ARK 21Shares","Valkyrie","VanEck","WisdomTree","Franklin","Bitwise","Grayscale","Hashdex","21Shares"]:
                        if m.lower() in (title + " " + abstract).lower():
                            manager = m; break
                    found_any = True
                    ev.append({
                        "asset": asset, "manager": manager or "—", "exchange": exch,
                        "status": status, "title": title, "date": pub or "TBD",
                        "url": url, "doc": doc,
                        "next_deadline_est": rough_deadline(status, pub),
                    })
            except Exception:
                continue
            time.sleep(0.15)
        if not found_any:
            ev.append({"asset": asset, "status": "none",
                       "title": f"{asset} için 19b-4 kaydı bulunamadı", "date": None, "url": None})
    uniq = {}
    for e in ev:
        k = (e.get("doc") or "") + "|" + (e.get("title") or "")
        if k not in uniq:
            uniq[k] = e
    out = list(uniq.values())
    out.sort(key=lambda x: (x.get("date") or ""), reverse=True)
    if out:
        cache_set(key, out)
    return out

# -------------------- Pump Candidates --------------------
def pump_candidates(limit_pairs=40):
    r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=20)
    r.raise_for_status()
    rows = []
    for x in r.json():
        s = x.get("symbol", "")
        if not s.endswith("USDT"):
            continue
        try:
            qv = float(x.get("quoteVolume", "0"))
            ch = float(x.get("priceChangePercent", "0"))
            lp = float(x.get("lastPrice", "0"))
        except Exception:
            continue
        rows.append({"symbol": s, "quoteVolume": qv, "change24": ch, "lastPrice": lp})
    rows.sort(key=lambda x: -x["quoteVolume"])
    top = rows[:limit_pairs]

    out = []
    rank_map = {top[i]["symbol"]: i + 1 for i in range(len(top))}
    for item in top:
        sym = item["symbol"]
        try:
            df    = binance_klines(sym, "1d", 220)
            closes = df["close"].tolist()
            if len(closes) < 200:
                continue
            sma200 = simple_sma(closes, 200)
            last   = closes[-1]
            above  = last > (sma200 or 1e18)
            ret7   = (closes[-1] / closes[-8] - 1.0) if len(closes) >= 8 else 0.0
            score  = ((ret7 * 100) * 0.4 + item["change24"] * 0.3
                      + (20 if above else 0) + max(0, 20 - (rank_map[sym] - 1)))
            out.append({
                "symbol":       sym,
                "last":         float(last),
                "price":        float(last),
                "sma200":       float(sma200) if sma200 is not None else None,
                "above200":     bool(above),
                "ret7_pct":     float(ret7 * 100.0),
                "change24_pct": float(item["change24"]),
                "volume_rank":  int(rank_map[sym]),
                "score":        round(float(score), 2),
            })
            time.sleep(0.03)
        except Exception:
            continue
    out.sort(key=lambda x: -x["score"])
    return out[:15]

# -------------------- Indicators --------------------
def simple_sma(series, window):
    if len(series) < window:
        return None
    return pd.Series(series).rolling(window=window).mean().iloc[-1]

def ema_last(series, window=20):
    if len(series) < window:
        return None
    return float(pd.Series(series).ewm(span=window, adjust=False).mean().iloc[-1])

def atr_last(df: pd.DataFrame, period=14):
    if df is None or df.empty or len(df) < period + 1:
        return None
    high, low, close = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])

def vwap_last(df: pd.DataFrame, window=96):
    if df is None or df.empty:
        return None
    w   = min(window, len(df))
    tp  = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0
    vol = df["volume"].astype(float)
    num = (tp.iloc[-w:] * vol.iloc[-w:]).sum()
    den = vol.iloc[-w:].sum()
    return float(num / den) if den > 0 else None

def heuristic_bull_estimate(btc_df, fng, etf_events):
    if btc_df is None or btc_df.empty:
        return {"phase_label": "unknown", "score": 0, "explain": ["Veri yok"]}
    closes = btc_df["close"].tolist()
    sma200, sma50, sma20 = simple_sma(closes, 200), simple_sma(closes, 50), simple_sma(closes, 20)
    last = closes[-1]
    checks, score = [], 0
    for label, cond in [
        ("BTC 200D SMA üstünde",   last > (sma200 or last + 1)),
        ("50D > 200D",             (sma50 or 0) > (sma200 or 1e12)),
        ("20D > 50D",              (sma20 or 0) > (sma50 or 1e12)),
        (f"Son 90g BTC getirisi",  (len(closes) >= 90 and closes[-1] / closes[-90] - 1.0 > 0.20)),
        (f"FNG ≥ 55 (şu an: {fng.get('value')})", (fng.get("value") or 0) >= 55),
    ]:
        checks.append((label, bool(cond)))
        score += 1 if cond else 0
    soon_cut = utcnow() + timedelta(days=60)
    near = []
    for e in etf_events:
        dt = e.get("next_deadline_est") or e.get("date")
        if not dt:
            continue
        try:
            d = datetime.fromisoformat(dt if "T" in dt else dt + "T00:00:00")
            d = d.replace(tzinfo=timezone.utc)
            if d <= soon_cut and e.get("status") != "none":
                near.append(e)
        except Exception:
            pass
    checks.append((f"ETF kritik pencereler (≤60g): {len(near)}", len(near) > 0))
    score += 1 if len(near) > 0 else 0
    phase = (["Dip Toplama", "Dip Toplama", "İnançlı Yükseliş", "İnançlı Yükseliş",
              "Genişleme", "Genişleme", "FOMO/Zirve Yakını"][min(score, 6)])
    now = utcnow()
    explain = [f"{l}: {'✓' if ok else '×'}" for l, ok in checks]
    explain.append("Halving sonrası zirve penceresi ~ 2025-04 – 2025-10 (tarihsel bağlam)")
    return {
        "bull_start_estimate": (now + timedelta(days=max(0, 120 - score * 15))).isoformat(),
        "bull_end_estimate":   (now + timedelta(days=480 + (6 - score) * 15)).isoformat(),
        "phase_label": phase, "score": int(score),
        "checks": checks, "explain": explain,
    }

def compute_btc_indicators_from_df(df):
    closes = df["close"].tolist()
    last   = closes[-1]
    sma20  = simple_sma(closes, 20)
    sma50  = simple_sma(closes, 50)
    sma200 = simple_sma(closes, 200)
    ret30 = vol30 = None
    if len(closes) >= 30:
        ret30 = closes[-1] / closes[-30] - 1.0
        mean  = np.mean(closes[-30:])
        vol30 = float(np.std(closes[-30:]) / mean) if mean > 0 else None
    return {
        "price":      float(last),
        "sma20":      float(sma20)  if sma20  is not None else None,
        "sma50":      float(sma50)  if sma50  is not None else None,
        "sma200":     float(sma200) if sma200 is not None else None,
        "ret30":      float(ret30)  if ret30  is not None else None,
        "vol30":      float(vol30)  if vol30  is not None else None,
        "updated_at": utcnow().isoformat(),
    }

# ==================== TFT AI ENGINE ====================

_TFT_LOCK = threading.Lock()
_TFT_LOADED = {}   # sym -> {"model": ..., "training": ...}
_TFT_READY = False

def _fix_and_load_tft(sym: str):
    """Checkpoint typo'sunu patch ederek TFT modelini yükler."""
    import torch
    try:
        from pytorch_forecasting import TemporalFusionTransformer
    except ImportError:
        return None

    paths = TFT_MODELS.get(sym)
    if not paths:
        return None

    ckpt_path = paths["ckpt"]
    pkl_path  = paths["pkl"]

    if not os.path.exists(ckpt_path) or not os.path.exists(pkl_path):
        print(f"[TFT] {sym}: model dosyası bulunamadı — {ckpt_path}")
        return None

    try:
        ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        hp = ck.get("hyper_parameters", {})
        if "monotone_constaints" in hp:
            hp["monotone_constraints"] = hp.pop("monotone_constaints")
            ck["hyper_parameters"] = hp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ckpt", delete=False) as tmp:
            tmp_path = tmp.name
        torch.save(ck, tmp_path)

        model    = TemporalFusionTransformer.load_from_checkpoint(tmp_path)
        training = torch.load(pkl_path, weights_only=False)
        os.unlink(tmp_path)

        model.eval()
        print(f"[TFT] {sym} modeli yüklendi ✓ (encoder={training.max_encoder_length}, pred={training.max_prediction_length})")
        return {"model": model, "training": training}
    except Exception as e:
        print(f"[TFT] {sym} yükleme hatası: {e}")
        return None

def _load_all_tft_models():
    global _TFT_READY
    for sym in TFT_MODELS:
        with _TFT_LOCK:
            if sym not in _TFT_LOADED:
                result = _fix_and_load_tft(sym)
                if result:
                    _TFT_LOADED[sym] = result
    _TFT_READY = True
    print("[TFT] Tüm modeller yüklendi.")

def tft_predict(symbol: str, df_15m: pd.DataFrame) -> dict:
    """
    15m kline DataFrame'i alır, TFT ile sonraki 4 mum (1 saat) için close tahmin yapar.
    Dönüş: {ok, direction, confidence, predicted_closes, current_price, expected_return_pct}
    """
    base = symbol.replace("USDT", "").upper()
    with _TFT_LOCK:
        loaded = _TFT_LOADED.get(base)

    if loaded is None:
        return {"ok": False, "reason": "model_not_loaded"}

    try:
        import torch
        from pytorch_forecasting import TimeSeriesDataSet

        model    = loaded["model"]
        training = loaded["training"]

        enc_len  = training.max_encoder_length
        pred_len = training.max_prediction_length

        if len(df_15m) < enc_len:
            return {"ok": False, "reason": "insufficient_data"}

        df_infer = df_15m.copy()
        df_infer["group"]    = base
        df_infer["time_idx"] = np.arange(len(df_infer))

        encoder_data   = df_infer.iloc[-enc_len:].copy()
        last_time_idx  = int(encoder_data["time_idx"].iloc[-1])
        last_close     = float(encoder_data["close"].iloc[-1])
        last_open_time = int(encoder_data["open_time"].iloc[-1])

        # Gelecek dummy satırları (unknown özellikler için son değeri kopyala)
        future_rows = []
        for i in range(1, pred_len + 1):
            row = {
                "open_time": last_open_time + i * 15 * 60 * 1000,
                "open":      last_close,
                "high":      last_close,
                "low":       last_close,
                "close":     last_close,
                "volume":    0.0,
                "close_time": last_open_time + i * 15 * 60 * 1000 + 60000,
                "group":     base,
                "time_idx":  last_time_idx + i,
            }
            future_rows.append(row)
        future_df = pd.DataFrame(future_rows)

        combined = pd.concat([encoder_data, future_df], ignore_index=True)

        inf_dataset = TimeSeriesDataSet.from_dataset(
            training, combined, predict=True, stop_randomization=True
        )
        inf_loader = inf_dataset.to_dataloader(batch_size=1, num_workers=0)

        model.eval()
        with torch.no_grad():
            preds = model.predict(inf_loader).cpu().numpy().flatten()

        # Yönsellik: tahmin edilen fiyat mevcut fiyatın üstünde mi?
        avg_pred = float(np.mean(preds))
        exp_ret  = (avg_pred - last_close) / max(last_close, 1e-9)

        # Güven skoru: 4 tahminin tutarlılığına göre (trend ne kadar monoton?)
        diffs         = [preds[i + 1] - preds[i] for i in range(len(preds) - 1)]
        same_sign     = all(d > 0 for d in diffs) or all(d < 0 for d in diffs)
        magnitude     = abs(exp_ret)
        confidence    = min(0.95, 0.5 + magnitude * 5.0 + (0.15 if same_sign else 0.0))

        direction = "bullish" if exp_ret > 0.002 else "bearish" if exp_ret < -0.002 else "neutral"

        result = {
            "ok":                   True,
            "symbol":               symbol,
            "direction":            direction,
            "confidence":           round(confidence, 3),
            "current_price":        round(last_close, 6),
            "predicted_closes":     [round(float(p), 6) for p in preds],
            "expected_return_pct":  round(exp_ret * 100, 3),
            "model":                f"TFT-{base}-2019-2025",
            "updated_at":           utcnow().isoformat(),
        }
        cache_set(f"tft_{symbol}", result)
        return result

    except Exception as e:
        print(f"[TFT] {symbol} inference hatası: {e}")
        return {"ok": False, "reason": str(e)}

# -------------------- Signal Engine --------------------
def evaluate_entry_signal(symbol: str, pump_row: Dict = None, thresholds: Dict = None) -> Dict:
    th     = thresholds or get_thresholds()
    ticks  = []

    # 1) BTC rejimi
    try:
        btc_df = cache_get("btc_1d_df", ttl=300)
        if btc_df is None:
            btc_df = binance_klines("BTCUSDT", "1d", 400)
            cache_set("btc_1d_df", btc_df)
        closes_btc = btc_df["close"].tolist()
        btc_sma200 = simple_sma(closes_btc, 200)
        btc_sma50  = simple_sma(closes_btc, 50)
        btc_last   = closes_btc[-1]
        btc_regime = (btc_last > (btc_sma200 or 1e18)) and ((btc_sma50 or 0) > (btc_sma200 or 1e18))
    except Exception:
        btc_regime = False
    ticks.append({"label": "BTC rejimi (SMA200 üstü & 50>200)", "ok": (not th["require_btc_regime"]) or bool(btc_regime)})

    # 2) Coin 1D trend
    try:
        ddf    = binance_klines(symbol, "1d", 220)
        dcl    = ddf["close"].tolist()
        above200 = (dcl[-1] > simple_sma(dcl, 200)) if len(dcl) >= 200 else False
        ret7_pct = (dcl[-1] / dcl[-8] - 1.0) * 100 if len(dcl) >= 8 else 0.0
        change24 = float(pump_row["change24_pct"]) if pump_row and "change24_pct" in pump_row \
                   else ((dcl[-1] / dcl[-2]) - 1.0) * 100 if len(dcl) >= 2 else 0.0
    except Exception:
        above200, ret7_pct, change24 = False, 0.0, 0.0

    ticks.append({"label": "Coin 1D trend (SMA200 üstü)", "ok": (not th["require_above200"]) or bool(above200)})
    ticks.append({"label": f"Haftalık momentum (ret7 ≥ {th['min_ret7_pct']:.1f}%)", "ok": ret7_pct >= th["min_ret7_pct"]})
    ticks.append({"label": f"Günlük momentum (change24 ≥ {th['min_change24_pct']:.1f}%)", "ok": change24 >= th["min_change24_pct"]})

    overextended = change24 >= th["overextended_change24_max"]
    ideal_upto   = change24 <= th["max_change24_pct"]
    ticks.append({"label": f"Aşırı uzama değil (24h ≤ {th['overextended_change24_max']:.1f}%)", "ok": not overextended})
    ticks.append({"label": f"İdeal aralıkta (24h ≤ {th['max_change24_pct']:.1f}%)", "ok": ideal_upto})

    # 3) 15m teknik onay
    last15 = ema20_15 = atr14_15 = vwap96_15 = None
    cond_reclaim = False
    m15 = None
    try:
        m15           = binance_klines(symbol, "15m", 200)
        close_series  = m15["close"].astype(float).tolist()
        last15        = float(close_series[-1])
        ema20_15      = ema_last(close_series, 20)
        atr14_15      = atr_last(m15, 14)
        vwap96_15     = vwap_last(m15, 96)
        cond_reclaim  = (ema20_15 is not None and last15 > ema20_15) and (vwap96_15 is not None and last15 > vwap96_15)
        ticks.append({"label": "15m EMA20 üstü",  "ok": ema20_15 is not None and last15 > ema20_15})
        ticks.append({"label": "15m VWAP üstü",   "ok": vwap96_15 is not None and last15 > vwap96_15})
        if atr14_15 and ema20_15:
            heat = (last15 - ema20_15) / max(atr14_15, 1e-9)
            ticks.append({"label": f"Sıcaklık (EMA mesafesi ≤ {th['heat_atr_max']:.2f} ATR)", "ok": heat <= th["heat_atr_max"]})
        else:
            ticks.append({"label": "Sıcaklık (EMA/ATR)", "ok": False})
    except Exception:
        ticks.append({"label": "15m EMA20/VWAP teyidi", "ok": False})

    # 4) TFT AI onayı (BTC/ETH/SOL için)
    ai_result = None
    base = symbol.replace("USDT", "").upper()
    if base in TFT_MODELS and m15 is not None and len(m15) >= 48:
        cached_ai = cache_get(f"tft_{symbol}", ttl=300)
        if cached_ai:
            ai_result = cached_ai
        else:
            ai_result = tft_predict(symbol, m15)

        if ai_result and ai_result.get("ok"):
            ai_bullish = ai_result["direction"] == "bullish"
            ai_conf    = ai_result.get("confidence", 0)
            ticks.append({
                "label": f"TFT AI ({ai_result['direction']}, güven={ai_conf:.0%})",
                "ok":    ai_bullish and ai_conf > 0.55,
            })

    # 5) Karar mantığı
    decision = "ALMA"
    note     = ""
    sl = tp1 = tp2 = None
    pullbacks = []

    try:
        if ema20_15:   pullbacks.append({"label": "EMA20 (15m)",           "price": round(ema20_15, 6)})
        if vwap96_15:  pullbacks.append({"label": "VWAP (15m, ~son 24s)",   "price": round(vwap96_15, 6)})
        if m15 is not None and len(m15) >= 30:
            h    = float(m15["high"].iloc[-96:].max())
            l    = float(m15["low"].iloc[-96:].min())
            rng  = h - l
            for lv, name in [(0.236, "Fibo 23.6%"), (0.382, "Fibo 38.2%"), (0.5, "Fibo 50%")]:
                pullbacks.append({"label": name, "price": round(h - rng * lv, 6)})
    except Exception:
        pass

    if th["require_btc_regime"] and not btc_regime:
        decision = "ALMA";         note = "BTC rejimi uygun değil."
    elif th["require_above200"] and not above200:
        decision = "ALMA";         note = "Coin 1D trendi zayıf (SMA200 altı)."
    elif ret7_pct < th["min_ret7_pct"] or change24 < th["min_change24_pct"]:
        decision = "ALMA";         note = "Momentum yetersiz."
    elif overextended:
        decision = "PULLBACK BEKLE"; note = f"Günlük değişim yüksek (≈{change24:.1f}%). Çekilme bekleyin."
    elif not cond_reclaim:
        decision = "PULLBACK BEKLE"; note = "15m EMA20/VWAP üzeri kapanış teyidi yok."
    else:
        # TFT modeli varsa onay ekle
        if ai_result and ai_result.get("ok") and ai_result["direction"] == "bearish" and ai_result["confidence"] > 0.70:
            decision = "PULLBACK BEKLE"
            note = f"Teknik OK ama TFT modeli düşüşü gösteriyor ({ai_result['direction']}, {ai_result['confidence']:.0%})."
        else:
            decision = "AL"
            note = "Rejim + trend + 15m reclaim uyumlu" + (" + TFT onay" if ai_result and ai_result.get("ok") and ai_result["direction"] == "bullish" else "") + "."

    if last15 and atr14_15:
        sl  = round(last15 - 1.5 * atr14_15, 6)
        tp1 = round(last15 + 1.0 * atr14_15, 6)
        tp2 = round(last15 + 2.0 * atr14_15, 6)

    return {
        "symbol":   symbol,
        "now":      utcnow().isoformat(),
        "decision": decision,
        "note":     note,
        "ticks":    ticks,
        "ai":       ai_result,
        "context":  {
            "change24_pct":    round(change24, 2),
            "ret7_pct":        round(ret7_pct, 2),
            "above200_1d":     bool(above200),
            "btc_regime_ok":   bool(btc_regime),
            "last15":          last15,
            "ema20_15":        ema20_15,
            "vwap96_15":       vwap96_15,
            "atr14_15":        atr14_15,
        },
        "risk": {
            "suggested_sl": sl,
            "tp1":          tp1,
            "tp2":          tp2,
            "rationale":    "SL=1.5×ATR(14,15m); TP1=+1R, TP2=+2R",
        },
        "pullback_targets": pullbacks,
    }

# -------------------- Top-4h Dataset --------------------
def get_binance_usdt_map():
    ex = cache_get("exchange_info", ttl=600)
    if ex is None:
        r = requests.get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=20)
        r.raise_for_status()
        ex = r.json()
        cache_set("exchange_info", ex)
    base_to_symbol = {}
    for s in ex["symbols"]:
        if s["status"] == "TRADING" and s.get("isSpotTradingAllowed") and s.get("quoteAsset") == "USDT":
            base = s.get("baseAsset")
            symb = s.get("symbol")
            if base and symb:
                base_to_symbol[base.upper()] = symb
    return base_to_symbol

def coingecko_top_by_marketcap(limit=TOP4H_MAX_SYMBOLS) -> List[Dict]:
    out, pages = [], (limit + 249) // 250
    for page in range(1, pages + 1):
        r = requests.get(f"{COINGECKO_API}/coins/markets",
                         params={"vs_currency": "usd", "order": "market_cap_desc",
                                 "per_page": 250, "page": page,
                                 "price_change_percentage": "24h", "locale": "en"},
                         timeout=25)
        r.raise_for_status()
        out.extend(r.json() or [])
        time.sleep(0.15)
    return out[:limit]

def fetch_4h_klines_for_symbols(symbols: List[str], limit_candles=TOP4H_KLINES):
    res = {}
    for i, sb in enumerate(symbols):
        try:
            df   = binance_klines(sb, interval=TOP4H_INTERVAL, limit=limit_candles)
            rows = [[int(r["open_time"]), float(r["open"]), float(r["high"]),
                     float(r["low"]), float(r["close"]), float(r["volume"]),
                     int(r["close_time"])] for _, r in df.iterrows()]
            res[sb] = rows
        except Exception:
            continue
        if (i + 1) % 10 == 0:
            time.sleep(0.1)
    return res

def build_top_coins_4h_dataset(max_symbols=TOP4H_MAX_SYMBOLS, klines=TOP4H_KLINES):
    cg_list  = coingecko_top_by_marketcap(limit=max_symbols)
    usdt_map = get_binance_usdt_map()
    mapped = []
    for c in cg_list:
        base_sym       = (c.get("symbol") or "").upper()
        binance_symbol = usdt_map.get(base_sym)
        if not binance_symbol:
            alt = {"WBTC": "BTC", "WETH": "ETH"}.get(base_sym)
            if alt:
                binance_symbol = usdt_map.get(alt)
        if binance_symbol:
            mapped.append({"cg_id": c.get("id"), "name": c.get("name"),
                           "ticker": base_sym, "rank": c.get("market_cap_rank"),
                           "market_cap": c.get("market_cap"),
                           "price": c.get("current_price"),
                           "change24_pct": c.get("price_change_percentage_24h") or 0,
                           "binance_symbol": binance_symbol})
    kmap  = fetch_4h_klines_for_symbols([m["binance_symbol"] for m in mapped], limit_candles=klines)
    final = [{**m, "klines_4h": kmap[m["binance_symbol"]]} for m in mapped if m["binance_symbol"] in kmap]
    return {"generated_at": utcnow().isoformat(), "interval": TOP4H_INTERVAL,
            "candles": klines, "total_requested": len(mapped),
            "total_with_klines": len(final), "rows": final}

# -------------------- Symbol helpers --------------------
def _get_usdt_symbol_map():
    m = cache_get("base_to_usdt_symbol", ttl=600)
    if m is not None:
        return m
    ex = cache_get("exchange_info", ttl=600)
    if ex is None:
        r  = requests.get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=20)
        r.raise_for_status()
        ex = r.json()
        cache_set("exchange_info", ex)
    base_to_symbol = {s["baseAsset"].upper(): s["symbol"]
                      for s in ex.get("symbols", [])
                      if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT"
                         and s.get("isSpotTradingAllowed")}
    cache_set("base_to_usdt_symbol", base_to_symbol)
    return base_to_symbol

def normalize_to_binance_usdt_symbol(user_text: str):
    if not user_text:
        return None
    import re
    t        = user_text.strip().lower()
    aliases  = {"ripple": "XRP", "bitcoin": "BTC", "ether": "ETH",
                "ethereum": "ETH", "solana": "SOL", "bnb": "BNB",
                "cardano": "ADA", "doge": "DOGE"}
    usdt_map = _get_usdt_symbol_map()
    m = re.search(r"\b([A-Z]{2,10})USDT\b", user_text.upper())
    if m and m.group(1) + "USDT" in usdt_map.values():
        return m.group(1) + "USDT"
    for k, v in aliases.items():
        if k in t:
            return usdt_map.get(v.upper())
    for base in usdt_map:
        if re.search(rf"\b{base}\b", user_text.upper()):
            return usdt_map.get(base)
    return None

def binance_ticker_24h(symbol: str):
    try:
        r  = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", params={"symbol": symbol}, timeout=10)
        r.raise_for_status()
        js = r.json()
        return {"symbol": js.get("symbol"), "last": safe_float(js.get("lastPrice")),
                "change24_pct": safe_float(js.get("priceChangePercent")),
                "volume": safe_float(js.get("volume")),
                "updated_at": utcnow().isoformat()}
    except Exception:
        return None

# -------------------- Chat Context --------------------
def build_chat_context():
    df = cache_get("btc_1d_df", ttl=300)
    if df is None:
        df = binance_klines("BTCUSDT", "1d", 400)
        cache_set("btc_1d_df", df)
    fng   = fng_latest()
    pumps = cache_get("pump_candidates_v1", ttl=300)
    if pumps is None:
        pumps = pump_candidates(limit_pairs=40)
        cache_set("pump_candidates_v1", pumps)
    etf = fetch_dynamic_etf_events()
    btc = compute_btc_indicators_from_df(df)
    etf_summary = {a: [e for e in etf if e.get("asset") == a and e.get("status") != "none"][:2]
                   for a in ["BTC", "ETH", "SOL", "XRP"]}
    ds = cache_get("top_coins_4h_dataset", ttl=TOP4H_REFRESH_SEC + 30)
    if ds is None:
        ds = build_top_coins_4h_dataset(max_symbols=TOP4H_MAX_SYMBOLS, klines=TOP4H_KLINES)
        cache_set("top_coins_4h_dataset", ds)
    top_rows = (ds.get("rows", []) or [])[:40]
    top4h_compact = [{"rank": r.get("rank"), "ticker": r.get("ticker"),
                      "symbol": r.get("binance_symbol"),
                      "price": safe_float(r.get("price")),
                      "change24_pct": safe_float(r.get("change24_pct")),
                      "klines_4h": (r.get("klines_4h") or [])[-100:]} for r in top_rows]
    return {
        "now":            utcnow().isoformat(),
        "btc":            btc,
        "fng":            fng,
        "pump_candidates": pumps,
        "etf_summary":    etf_summary,
        "top4h":          {"generated_at": ds.get("generated_at"), "interval": ds.get("interval"),
                           "candles": min(100, ds.get("candles", 0)),
                           "count": len(top4h_compact), "rows": top4h_compact},
        "bull":           heuristic_bull_estimate(df, fng, etf),
        "thresholds":     get_thresholds(),
        "realtime_query": None,
    }

# -------------------- Background Loops --------------------
def refresh_loop():
    """Her 60 saniyede veri yeniler; TFT modellerini de tetikler."""
    while True:
        try:
            df = binance_klines("BTCUSDT", "1d", 400)
            cache_set("btc_1d_df", df)
            _ = fng_latest()
            pumps = pump_candidates(limit_pairs=40)
            cache_set("pump_candidates_v1", pumps)
            etf = fetch_dynamic_etf_events()
            cache_set("etf_events", etf)
            ctx = build_chat_context()
            cache_set("chat_context", ctx)

            # TFT modelleri hazırsa; BTC/ETH/SOL için arka planda tahmin yenile
            if _TFT_READY:
                for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
                    try:
                        m15 = binance_klines(sym, "15m", 200)
                        if len(m15) >= 48:
                            result = tft_predict(sym, m15)
                            if result.get("ok"):
                                print(f"[TFT] {sym}: {result['direction']} "
                                      f"exp={result['expected_return_pct']:+.2f}% "
                                      f"conf={result['confidence']:.0%}")
                    except Exception as e:
                        print(f"[TFT refresh] {sym}: {e}")

            print(f"[refresh_loop] OK — {utcnow().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[refresh_loop] hata: {e}")
        time.sleep(CHAT_REFRESH_SEC)

def refresh_top4h_loop():
    while True:
        try:
            dataset = build_top_coins_4h_dataset(max_symbols=TOP4H_MAX_SYMBOLS, klines=TOP4H_KLINES)
            cache_set("top_coins_4h_dataset", dataset)
            print(f"[top4h_loop] OK — {len(dataset.get('rows', []))} coins")
        except Exception as e:
            print(f"[top4h_loop] hata: {e}")
        time.sleep(TOP4H_REFRESH_SEC)

def ticker_loop():
    """Her 5 saniyede izlenen sembollerin anlık fiyatlarını çekip Socket.IO ile yayınlar."""
    TRACKED = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
               "WLDUSDT", "ZECUSDT", "NEARUSDT", "USDCUSDT", "XLMUSDT",
               "PORTALUSDT", "ALLOUSDT", "ONDOUSDT", "TONUSDT", "DOGEUSDT"]
    while True:
        try:
            # Pump candidates'dan güncel sembol listesini al
            pumps = cache_get("pump_candidates_v1", ttl=300)
            if pumps:
                symbols = [p["symbol"] for p in pumps[:20]]
            else:
                symbols = TRACKED

            # Binance spot fiyatlarını toplu çek
            r = requests.get(
                f"{BINANCE_API}/api/v3/ticker/price",
                timeout=8
            )
            if r.ok:
                all_prices = {item["symbol"]: float(item["price"]) for item in r.json()}
                batch = {sym: all_prices[sym] for sym in symbols if sym in all_prices}
                if batch:
                    socketio.emit("price_update_batch", batch)
        except Exception as e:
            pass
        time.sleep(5)

# -------------------- Ollama --------------------
def ollama_generate(model, prompt, system=None, stream=False):
    base = OLLAMA_HOST.rstrip("/")
    for url, payload in [
        (f"{base}/api/generate",   {"model": model, "prompt": prompt, "stream": stream,
                                    **({} if not system else {"system": system})}),
        (f"{base}/api/chat",       {"model": model, "stream": False,
                                    "messages": ([{"role":"system","content":system}] if system else [])
                                                + [{"role":"user","content":prompt}]}),
        (f"{base}/v1/chat/completions", {"model": model,
                                         "messages": ([{"role":"system","content":system}] if system else [])
                                                     + [{"role":"user","content":prompt}]}),
    ]:
        try:
            r = requests.post(url, json=payload, timeout=120)
            if r.status_code == 200:
                js = r.json()
                text = (js.get("response") or
                        (js.get("message") or {}).get("content") or
                        ((js.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
                if text:
                    return {"response": text}
        except Exception:
            continue
    raise RuntimeError("Ollama API ulaşılamadı.")

# ==================== Flask Routes ====================

@app.route("/")
def home():
    return render_template("index.html", show_apk=False)

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/api/coinbase_premium")
def api_coinbase_premium():
    try:
        res = coinglass_coinbase_premium()
        if "error" in res:
            return jsonify({"ok": False, "error": res["error"]}), 400
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/coins_sma_summary")
def api_coins_sma_summary():
    try:
        limit = int(request.args.get("limit", 60))
        ex = cache_get("exchange_info", ttl=600)
        if ex is None:
            r = requests.get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=15)
            r.raise_for_status()
            ex = r.json()
            cache_set("exchange_info", ex)
        symbols = [s["symbol"] for s in ex["symbols"]
                   if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
                   and s.get("isSpotTradingAllowed")][:limit]
        count_above, scan = 0, []
        for sb in symbols:
            try:
                df = binance_klines(sb, "1d", 220)
                if df.empty or len(df) < 200:
                    continue
                closes = df["close"].tolist()
                sma200 = simple_sma(closes, 200)
                last = closes[-1]
                above = last > (sma200 or 1e18)
                scan.append({"symbol": sb, "last": float(last),
                             "sma200": float(sma200) if sma200 is not None else None,
                             "above": bool(above)})
                if above:
                    count_above += 1
                time.sleep(0.03)
            except Exception:
                continue
        pct = (count_above / len(scan)) * 100 if scan else 0.0
        return jsonify({"ok": True, "data": {
            "scanned": len(scan), "above200": count_above,
            "percent_above200": pct, "rows": scan
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/health")
def health():
    tft_status = {sym: sym in _TFT_LOADED for sym in TFT_MODELS}
    return jsonify({"ok": True, "tft_models": tft_status, "tft_ready": _TFT_READY})

@app.route("/api/thresholds", methods=["GET","POST"])
def api_thresholds():
    try:
        if request.method == "GET":
            return jsonify({"ok": True, "data": get_thresholds()})
        new_th = update_thresholds(request.get_json(force=True, silent=True) or {})
        return jsonify({"ok": True, "data": new_th})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/fng")
def api_fng():
    try:
        return jsonify({"ok": True, "data": fng_latest()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/btc_indicators")
def api_btc_indicators():
    try:
        df = cache_get("btc_1d_df", ttl=300)
        if df is None:
            df = binance_klines("BTCUSDT", "1d", 400)
            cache_set("btc_1d_df", df)
        return jsonify({"ok": True, "data": compute_btc_indicators_from_df(df)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/etf_events")
def api_etf_events():
    try:
        return jsonify({"ok": True, "data": fetch_dynamic_etf_events()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/pump_candidates")
def api_pump_candidates():
    try:
        res = cache_get("pump_candidates_v1", ttl=300) or pump_candidates(limit_pairs=40)
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/signal")
def api_signal():
    try:
        symbol = request.args.get("symbol")
        pump_map = {}
        if symbol:
            symbol = symbol.upper()
        else:
            lst = cache_get("pump_candidates_v1", ttl=300) or pump_candidates(limit_pairs=40)
            if not lst:
                return jsonify({"ok": False, "error": "Aday bulunamadı."}), 400
            symbol   = lst[0]["symbol"]
            pump_map = {x["symbol"]: x for x in lst}
        res = evaluate_entry_signal(symbol, pump_map.get(symbol), thresholds=get_thresholds())
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/signals")
def api_signals():
    """
    Ana sinyal endpoint'i.
    React frontend'in beklediği format:
      { success, count, data: { rows: [{symbol, decision, score, price, change24_pct, ...}] } }
    """
    try:
        lst = cache_get("pump_candidates_v1", ttl=300)
        if not lst:
            lst = pump_candidates(limit_pairs=40)
            cache_set("pump_candidates_v1", lst)

        limit = int(request.args.get("limit", 20))
        rows  = lst[:limit]
        th    = get_thresholds()
        out   = []
        for r in rows:
            sym = r["symbol"]
            sig = evaluate_entry_signal(sym, r, thresholds=th)
            out.append({
                "symbol":           sym,
                "score":            r.get("score"),
                "price":            r.get("price") or r.get("last"),
                "change24_pct":     r.get("change24_pct"),
                "ret7_pct":         r.get("ret7_pct"),
                "above200":         r.get("above200"),
                "volume_rank":      r.get("volume_rank"),
                "decision":         sig["decision"],
                "note":             sig["note"],
                "ticks":            sig["ticks"],
                "risk":             sig["risk"],
                "pullback_targets": sig["pullback_targets"],
                "context":          sig["context"],
                "ai":               sig.get("ai"),
            })
            time.sleep(0.01)

        return jsonify({
            "success": True,
            "count":   len(out),
            "data":    {"thresholds": th, "count": len(out), "rows": out},
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "data": {"rows": []}}), 500

@app.route("/api/ai/signal/<symbol>")
def api_ai_signal(symbol: str):
    """
    TFT AI inference endpoint — React frontend'in AI commentary widget'ı için.
    """
    try:
        symbol = symbol.upper()
        if not symbol.endswith("USDT"):
            symbol = symbol + "USDT"

        cached = cache_get(f"tft_{symbol}", ttl=300)
        if cached and cached.get("ok"):
            return jsonify({"success": True, "data": {
                "symbol":       symbol,
                "prediction":   "BUY" if cached["direction"] == "bullish" else
                                "SELL" if cached["direction"] == "bearish" else "HOLD",
                "confidence":   cached["confidence"],
                "direction":    cached["direction"],
                "expected_return_pct": cached.get("expected_return_pct"),
                "predicted_closes":    cached.get("predicted_closes"),
                "message":      f"TFT modeli {cached['direction']} yönünü işaret ediyor "
                                f"({cached['expected_return_pct']:+.2f}% beklenen getiri, "
                                f"{cached['confidence']:.0%} güven).",
                "model":        cached.get("model"),
                "updated_at":   cached.get("updated_at"),
            }})

        base = symbol.replace("USDT", "").upper()
        if base not in TFT_MODELS:
            return jsonify({"success": False,
                            "error": f"{base} için TFT modeli yok (BTC/ETH/SOL destekleniyor)",
                            "data":  {"symbol": symbol, "prediction": "HOLD", "confidence": 0.0}}), 400

        if not _TFT_READY or base not in _TFT_LOADED:
            return jsonify({"success": False, "error": "TFT modeller henüz yükleniyor...",
                            "data": {"symbol": symbol, "prediction": "HOLD", "confidence": 0.0}}), 503

        m15 = binance_klines(symbol, "15m", 200)
        res = tft_predict(symbol, m15)

        if not res.get("ok"):
            return jsonify({"success": False, "error": res.get("reason", "inference failed"),
                            "data": {"symbol": symbol, "prediction": "HOLD", "confidence": 0.0}}), 500

        return jsonify({"success": True, "data": {
            "symbol":       symbol,
            "prediction":   "BUY" if res["direction"] == "bullish" else
                            "SELL" if res["direction"] == "bearish" else "HOLD",
            "confidence":   res["confidence"],
            "direction":    res["direction"],
            "expected_return_pct": res.get("expected_return_pct"),
            "predicted_closes":    res.get("predicted_closes"),
            "message":      f"TFT ({res['model']}): {res['direction']}, "
                            f"{res['expected_return_pct']:+.2f}% beklenen getiri "
                            f"({res['confidence']:.0%} güven).",
            "model":        res.get("model"),
            "updated_at":   res.get("updated_at"),
        }})

    except Exception as e:
        return jsonify({"success": False, "error": str(e),
                        "data": {"symbol": symbol, "prediction": "HOLD", "confidence": 0.0}}), 500

@app.route("/api/bull_estimate")
def api_bull_estimate():
    try:
        fng = fng_latest()
        df  = cache_get("btc_1d_df", ttl=300)
        if df is None:
            df = binance_klines("BTCUSDT", "1d", 400)
            cache_set("btc_1d_df", df)
        return jsonify({"ok": True, "data": heuristic_bull_estimate(df, fng, fetch_dynamic_etf_events())})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/oi")
def api_oi():
    try:
        spot = {}
        for sym in ["BTCUSDT", "ETHUSDT"]:
            spot[sym] = {"now": fapi_open_interest(sym),
                         "hist": fapi_open_interest_hist(sym, period="1d", limit=30)}
        return jsonify({"ok": True, "data": spot})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/hashrate")
def api_hashrate():
    try:
        return jsonify({"ok": True, "data": blockchain_hashrate(30)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/stablecoin_flow")
def api_stablecoin_flow():
    try:
        return jsonify({"ok": True, "data": defillama_stablecoins()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/top_coins_4h")
def api_top_coins_4h():
    try:
        limit   = int(request.args.get("limit", "100"))
        compact = request.args.get("compact", "false").lower() == "true"
        ds      = cache_get("top_coins_4h_dataset", ttl=TOP4H_REFRESH_SEC + 30)
        if ds is None:
            ds = build_top_coins_4h_dataset(max_symbols=TOP4H_MAX_SYMBOLS, klines=TOP4H_KLINES)
            cache_set("top_coins_4h_dataset", ds)
        rows = ds.get("rows", [])[:limit]
        if compact:
            rows = [[r.get("rank"), r.get("ticker"), r.get("binance_symbol"),
                     safe_float(r.get("market_cap")), safe_float(r.get("price")),
                     safe_float(r.get("change24_pct")), r.get("klines_4h")] for r in rows]
        return jsonify({"ok": True, "data": {**{k: ds.get(k) for k in ("generated_at","interval","candles")},
                                             "count": len(rows), "rows": rows}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        body     = request.get_json(force=True)
        model    = body.get("model", "gpt-oss")
        messages = body.get("messages", [])
        last_user_text = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")

        context = cache_get("chat_context", ttl=CHAT_REFRESH_SEC + 30)
        if context is None:
            context = build_chat_context()
            cache_set("chat_context", context)

        rt  = {}
        sym = normalize_to_binance_usdt_symbol(last_user_text)
        if sym:
            tick = binance_ticker_24h(sym)
            if tick:
                rt = {"requested_symbol": sym, "ticker_24h": tick}
        context = {**context, "realtime_query": rt or None}

        sys_prompt = """You are a STRICTLY-CONTEXT-BOUND local crypto assistant.
Cevaplarını SADECE verilen [CONTEXT JSON] içindeki veriye dayandır.
Bağlamda olmayan bilgi için "Veri bulunamadı" de. Cevap dili: Türkçe."""

        prompt = f"[CONTEXT JSON]\n{json.dumps(context, ensure_ascii=False)}\n\n"
        for m in messages:
            prompt += f"{m.get('role','user')}: {m.get('content','')}\n"
        prompt += "assistant:"

        resp = ollama_generate(model, prompt, system=sys_prompt)
        return jsonify({"ok": True, "data": {"response": (resp.get("response") or "").strip()}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ==================== Main ====================
if __name__ == "__main__":
    cache_set(THRESHOLDS_KEY, DEFAULT_THRESHOLDS.copy())

    # Tüm ağır işlemler arka planda — Flask anında başlasın
    def _startup_jobs():
        try:
            cache_set("chat_context", build_chat_context())
            print("[startup] İlk context build OK")
        except Exception as e:
            print(f"[startup] İlk context build hatası: {e}")

    threading.Thread(target=_startup_jobs,      daemon=True).start()
    threading.Thread(target=_load_all_tft_models, daemon=True).start()
    threading.Thread(target=refresh_loop,         daemon=True).start()
    threading.Thread(target=refresh_top4h_loop,   daemon=True).start()
    threading.Thread(target=ticker_loop,           daemon=True).start()

    print("[BullWatch Engine] Port 34000'de başlıyor...")
    socketio.run(app, debug=False, port=34000, host="0.0.0.0", allow_unsafe_werkzeug=True)
