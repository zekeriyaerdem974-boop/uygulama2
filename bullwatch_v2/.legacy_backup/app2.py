import os, json, time, math, requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from dateutil import tz
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BINANCE_API = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"
ALT_FNG_API = "https://api.alternative.me/fng/?limit=1"
FR_API = "https://www.federalregister.gov/api/v1/documents.json"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")
TZ = tz.gettz("Europe/Berlin")

_cache = {}
def cache_get(key, ttl=60):
    it = _cache.get(key)
    if not it: return None
    ts, val = it
    if time.time() - ts > ttl: return None
    return val
def cache_set(key, val): _cache[key] = (time.time(), val)
def utcnow(): return datetime.now(timezone.utc)

def binance_klines(symbol="BTCUSDT", interval="1d", limit=400):
    r = requests.get(f"{BINANCE_API}/api/v3/klines",
                     params={"symbol":symbol,"interval":interval,"limit":limit}, timeout=15)
    r.raise_for_status()
    arr = r.json()
    rows = []
    for a in arr:
        rows.append({"open_time": int(a[0]),"open": float(a[1]),"high": float(a[2]),
                     "low": float(a[3]),"close": float(a[4]),"volume": float(a[5]),
                     "close_time": int(a[6])})
    return pd.DataFrame(rows)

def simple_sma(series, window):
    if len(series) < window: return None
    return pd.Series(series).rolling(window=window).mean().iloc[-1]

def fng_latest():
    key = "fng_latest"
    c = cache_get(key, ttl=60)
    if c: return c
    r = requests.get(ALT_FNG_API, timeout=10); r.raise_for_status()
    data = r.json()
    if data.get("data"):
        it = data["data"][0]
        out = {"value": int(it["value"]),
               "value_classification": it["value_classification"],
               "timestamp": int(it["timestamp"]),
               "time_readable": it.get("time_until_update")}
        cache_set(key, out); return out
    return {"value": None, "value_classification": None, "timestamp": None, "time_readable": None}

def fapi_open_interest(symbol="BTCUSDT"):
    r = requests.get(f"{BINANCE_FAPI}/fapi/v1/openInterest",
                     params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return r.json()

def fapi_open_interest_hist(symbol="BTCUSDT", period="1d", limit=30):
    r = requests.get(f"{BINANCE_FAPI}/futures/data/openInterestHist",
                     params={"symbol":symbol,"period":period,"limit":limit}, timeout=10)
    r.raise_for_status()
    return r.json()

def blockchain_hashrate(days=30):
    url = "https://api.blockchain.info/charts/hash-rate"
    r = requests.get(url, params={"format":"json","timespan":f"{days}days"}, timeout=10)
    r.raise_for_status()
    return r.json()

def defillama_stablecoins():
    url = "https://stablecoins.llama.fi/stablecoins"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    js = r.json()
    coins = js.get("peggedAssets", []) or []

    rows = []
    for c in coins:
        # Sadece USD-pegged (istenirse bunu kaldırabilirsin)
        if c.get("pegType") != "peggedUSD":
            continue

        sym = c.get("symbol") or c.get("name") or "UNKNOWN"

        cur = (c.get("circulating") or {}).get("peggedUSD")
        prev = (c.get("circulatingPrevDay") or {}).get("peggedUSD")

        # Bazı kayıtlarda eksik olabilir
        if cur is None or prev is None:
            continue

        change_usd = float(cur) - float(prev)
        rows.append({"symbol": sym, "change24_usd": change_usd})

    # En büyük mutlak 24s net akışa göre ilk 10
    rows.sort(key=lambda x: -abs(x["change24_usd"]))
    top = rows[:10]

    total_change = sum(x["change24_usd"] for x in top) if top else 0.0

    return {
        "top": top,
        "approx_netflow_24h_usd": total_change
    }

def coinglass_coinbase_premium():
    if not COINGLASS_API_KEY:
        return {"error":"COINGLASS_API_KEY missing"}
    headers = {"coinglassSecret": COINGLASS_API_KEY}
    r = requests.get("https://open-api-v4.coinglass.com/api/coinbase-premium-index",
                     params={"symbol":"BTC"}, headers=headers, timeout=12)
    if r.status_code != 200:
        return {"error": f"http {r.status_code}"}
    return r.json()

ASSET_KEYWORDS = {
    "BTC": ["bitcoin","spot bitcoin","btc","iShares","BlackRock","Fidelity","ARK 21Shares","Valkyrie","VanEck","WisdomTree","Franklin","Bitwise","Grayscale","Hashdex"],
    "ETH": ["ether","ethereum","spot ether","eth","iShares","BlackRock","Fidelity","VanEck","Bitwise","Grayscale","21Shares","Franklin","WisdomTree"],
    "SOL": ["solana","spot solana","sol","VanEck","21Shares","Fidelity","Hashdex","Grayscale","BlackRock"],
    "XRP": ["xrp","ripple","spot xrp","ripple labs","21Shares","Hashdex","Grayscale","BlackRock","Fidelity"]
}
EXCHANGE_KEYWORDS = ["Cboe BZX","NYSE Arca","Nasdaq","Cboe EDGX","Cboe BYX"]

def fr_search_documents(term, per_page=30, agency_slug="securities-and-exchange-commission"):
    params = {
        "per_page": per_page,
        "order": "newest",
        "conditions[term]": term,
        "conditions[agencies][]": agency_slug,   # <-- SLUG KULLAN
    }
    r = requests.get(FR_API, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def classify_fr_status(title: str):
    t = (title or "").lower()
    if "granting approval" in t or "order approving" in t or "approval order" in t: return "approved"
    if "instituting proceedings" in t: return "proceedings"
    if "designation of a longer period" in t or "longer period" in t or "extend" in t or "delay" in t: return "delay"
    if "notice of filing" in t or "notice" in t: return "filed"
    if "immediate effectiveness" in t: return "effective"
    return "unknown"

def detect_exchange(title):
    for ex in EXCHANGE_KEYWORDS:
        if ex.lower() in (title or "").lower():
            return ex
    return None

def rough_deadline(status:str, pub_date:str):
    if not pub_date: return None
    try:
        d = datetime.fromisoformat(pub_date) if "T" in pub_date else datetime.fromisoformat(pub_date+"T00:00:00")
        d = d.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    if status == "filed": return (d + timedelta(days=45)).isoformat()
    if status == "proceedings": return (d + timedelta(days=60)).isoformat()
    if status == "delay": return (d + timedelta(days=45)).isoformat()
    return None

def fetch_dynamic_etf_events():
    key = "dynamic_etf_events_v2"
    c = cache_get(key, ttl=300)
    if c: return c
    ev = []
    for asset, kws in ASSET_KEYWORDS.items():
        found_any = False
        for kw in kws:
            term = f"{kw} 19b-4"
            try:
                js = fr_search_documents(term, per_page=200)  # biraz yükselt
                for d in js.get("results", []):
                    title = d.get("title","")
                    pub = (d.get("publication_date") or d.get("effective_on") 
                           or d.get("signing_date") or d.get("created_at"))
                    url = d.get("html_url") or d.get("pdf_url")
                    doc = d.get("document_number")
                    abstract = d.get("abstract") or ""
                    status = classify_fr_status(title)
                    exch = detect_exchange(title) or "—"
                    manager = None
                    for m in ["iShares","BlackRock","Fidelity","ARK 21Shares","Valkyrie","VanEck","WisdomTree","Franklin","Bitwise","Grayscale","Hashdex","21Shares"]:
                        if m.lower() in (title+" "+abstract).lower():
                            manager = m; break
                    # has_kw filtresini KALDIR
                    found_any = True
                    ev.append({
                        "asset": asset, "manager": manager or "—", "exchange": exch,
                        "status": status, "title": title, "date": pub or "TBD",
                        "url": url, "doc": doc, "next_deadline_est": rough_deadline(status, pub)
                    })
            except Exception:
                continue
            time.sleep(0.15)
        if not found_any:
            ev.append({"asset": asset, "status": "none", "title": f"{asset} için 19b-4 kaydı bulunamadı", "date": None, "url": None})
    uniq = {}
    for e in ev:
        k = (e.get("doc") or "") + "|" + (e.get("title") or "")
        if k not in uniq: uniq[k] = e
    out = list(uniq.values())
    out.sort(key=lambda x: (x.get("date") or ""), reverse=True)
    # BOŞSA cache’leme
    if out:
        cache_set(key, out)
    return out

def pump_candidates(limit_pairs=40):
    r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=20)
    r.raise_for_status()
    arr = r.json()
    rows = []
    for x in arr:
        s = x.get("symbol","")
        if not s.endswith("USDT"): continue
        try:
            qv = float(x.get("quoteVolume","0"))
            ch = float(x.get("priceChangePercent","0"))
        except Exception:
            continue
        rows.append({"symbol":s, "quoteVolume": qv, "change24": ch})
    rows.sort(key=lambda x: -x["quoteVolume"])
    top = rows[:limit_pairs]
    out = []
    rank_map = {top[i]["symbol"]: i+1 for i in range(len(top))}
    for item in top:
        sym = item["symbol"]
        try:
            df = binance_klines(sym, "1d", 220)
            closes = df["close"].tolist()
            if len(closes) < 200: continue
            sma200 = simple_sma(closes, 200)
            last = closes[-1]
            above = False
            if last > (sma200 or 1e18):
                above = True


            ret7 = (closes[-1]/closes[-8]-1.0) if len(closes)>=8 else 0.0
            score = ( (ret7*100)*0.4 + item["change24"]*0.3 + (20 if above else 0) + max(0, 20 - (rank_map[sym]-1)) )
            out.append({
                "symbol": sym,
                "last": last,
                "sma200": sma200,
                "above200": above,
                "ret7_pct": ret7*100.0,
                "change24_pct": item["change24"],
                "volume_rank": rank_map[sym],
                "score": round(score,2)
            })
            time.sleep(0.03)
        except Exception:
            continue
    out.sort(key=lambda x: -x["score"])
    return out[:15]

def heuristic_bull_estimate(btc_df, fng, etf_events):
    if btc_df is None or btc_df.empty:
        return {"bull_start_estimate": None, "bull_end_estimate": None,
                "phase_label": "unknown", "score": 0, "explain": ["Veri yok"]}
    closes = btc_df["close"].tolist()
    sma200 = simple_sma(closes, 200)
    sma50 = simple_sma(closes, 50)
    sma20 = simple_sma(closes, 20)
    last = closes[-1]
    checks, score = [], 0
    cond1 = last > (sma200 or last+1); checks.append(("BTC 200D SMA üstünde", bool(cond1))); score += 1 if cond1 else 0
    cond2 = (sma50 or 0) > (sma200 or 1e12); checks.append(("50D > 200D", bool(cond2))); score += 1 if cond2 else 0
    cond3 = (sma20 or 0) > (sma50 or 1e12); checks.append(("20D > 50D", bool(cond3))); score += 1 if cond3 else 0
    ret90 = (closes[-1] / closes[-90] - 1.0) if len(closes) >= 90 else 0.0
    cond4 = ret90 > 0.20; checks.append((f"Son 90g BTC getirisi {ret90:.1%}", bool(cond4))); score += 1 if cond4 else 0
    fng_val = fng.get("value"); cond5 = (fng_val or 0) >= 55; checks.append((f"FNG ≥ 55 (şu an: {fng_val})", bool(cond5))); score += 1 if cond5 else 0
    soon_cut = utcnow() + timedelta(days=60)
    near = []
    for e in etf_events:
        dt = e.get("next_deadline_est") or e.get("date")
        if not dt: continue
        try:
            d = datetime.fromisoformat(dt) if "T" in dt else datetime.fromisoformat(dt+"T00:00:00")
            d = d.replace(tzinfo=timezone.utc)
            if d <= soon_cut and e.get("status") != "none": near.append(e)
        except Exception: pass
    cond6 = len(near) > 0; checks.append((f"ETF kritik pencereler (≤60g): {len(near)}", bool(cond6))); score += 1 if cond6 else 0
    if score <= 1: phase = "Dip Toplama"
    elif score <= 3: phase = "İnançlı Yükseliş"
    elif score in (4,5): phase = "Genişleme"
    else: phase = "FOMO/Zirve Yakını"
    now = utcnow()
    start_in_days = max(0, 120 - score*15)
    bull_start_est = now + timedelta(days=start_in_days)
    bull_end_est = now + timedelta(days=480 + (6-score)*15)
    explain = [f"{l}: {'✓' if ok else '×'}" for (l,ok) in checks]
    explain.append("Halving sonrası zirve penceresi ~ 2025-04 – 2025-10 (tarihsel bağlam)")
    return {"bull_start_estimate": bull_start_est.isoformat(),
            "bull_end_estimate": bull_end_est.isoformat(),
            "phase_label": phase, "score": int(score),
            "checks": checks, "explain": explain}

@app.route("/")
def home(): return render_template("index.html")
@app.route("/chat")
def chat_page(): return render_template("chat.html")

@app.route("/api/fng")
def api_fng():
    try: return jsonify({"ok":True,"data":fng_latest()})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/btc_indicators")
def api_btc_indicators():
    try:
        df = cache_get("btc_1d_df", ttl=300)
        if df is None:
            df = binance_klines("BTCUSDT","1d",400); cache_set("btc_1d_df", df)
        closes = df["close"].tolist(); last = closes[-1]
        sma20, sma50, sma200 = simple_sma(closes,20), simple_sma(closes,50), simple_sma(closes,200)
        if len(closes)>=30:
            ret30 = closes[-1]/closes[-30]-1.0
            vol30 = float(np.std(closes[-30:])/np.mean(closes[-30:])) if np.mean(closes[-30:])>0 else None
        else: ret30, vol30 = None, None
        return jsonify({"ok":True,"data":{
            "price": last,"sma20":sma20,"sma50":sma50,"sma200":sma200,
            "ret30":ret30,"vol30":vol30,"updated_at":utcnow().isoformat()
        }})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/coins_sma_summary")
def api_coins_sma_summary():
    try:
        limit = int(request.args.get("limit", 60))
        ex = cache_get("exchange_info", ttl=600)
        if ex is None:
            r = requests.get(f"{BINANCE_API}/api/v3/exchangeInfo", timeout=15); r.raise_for_status()
            ex = r.json(); cache_set("exchange_info", ex)
        symbols = []
        for s in ex["symbols"]:
            if s["status"]=="TRADING" and s["quoteAsset"]=="USDT" and s.get("isSpotTradingAllowed"):
                symbols.append(s["symbol"])
        symbols = symbols[:limit]
        count_above, scan = 0, []
        for sb in symbols:
            try:
                df = binance_klines(sb,"1d",220)
                if df.empty or len(df)<200: continue
                closes = df["close"].tolist()
                sma200 = simple_sma(closes,200); last = closes[-1]
                above = last > (sma200 or 1e18)
                scan.append({"symbol":sb,"last":last,"sma200":sma200,"above":above})
                if above: count_above += 1
                time.sleep(0.03)
            except Exception: continue
        pct = (count_above/len(scan))*100 if scan else 0.0
        return jsonify({"ok":True,"data":{"scanned":len(scan),"above200":count_above,"percent_above200":pct,"rows":scan}})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/etf_events")
def api_etf_events():
    try: return jsonify({"ok":True,"data":fetch_dynamic_etf_events()})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/pump_candidates")
def api_pump_candidates():
    try:
        res = cache_get("pump_candidates_v1", ttl=300)
        if not res:
            res = pump_candidates(limit_pairs=40)
            cache_set("pump_candidates_v1", res)
        return jsonify({"ok":True,"data":res})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/bull_estimate")
def api_bull_estimate():
    try:
        fng = fng_latest()
        df = cache_get("btc_1d_df", ttl=300)
        if df is None:
            df = binance_klines("BTCUSDT","1d",400); cache_set("btc_1d_df", df)
        est = heuristic_bull_estimate(df, fng, fetch_dynamic_etf_events())
        return jsonify({"ok":True,"data":est})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/oi")
def api_oi():
    try:
        spot = {}
        for sym in ["BTCUSDT","ETHUSDT"]:
            cur = fapi_open_interest(sym)
            hist = fapi_open_interest_hist(sym, period="1d", limit=30)
            spot[sym] = {"now": cur, "hist": hist}
        return jsonify({"ok":True,"data":spot})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/hashrate")
def api_hashrate():
    try: return jsonify({"ok":True,"data":blockchain_hashrate(30)})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/stablecoin_flow")
def api_stablecoin_flow():
    try: return jsonify({"ok":True,"data":defillama_stablecoins()})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

@app.route("/api/coinbase_premium")
def api_coinbase_premium():
    try:
        res = coinglass_coinbase_premium()
        if "error" in res: return jsonify({"ok":False,"error":res["error"]}),400
        return jsonify({"ok":True,"data":res})
    except Exception as e: return jsonify({"ok":False,"error":str(e)}),500

def ollama_generate(model, prompt, system=None, stream=False):
    base = OLLAMA_HOST.rstrip("/")
    payload = {"model": model, "prompt": prompt, "stream": stream}
    if system: payload["system"] = system
    url = f"{base}/api/generate"
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code == 200:
        return r.json()
    url2 = f"{base}/api/chat"
    messages = []
    if system: messages.append({"role":"system","content":system})
    messages.append({"role":"user","content":prompt})
    r2 = requests.post(url2, json={"model": model, "messages": messages, "stream": False}, timeout=120)
    if r2.status_code == 200:
        js = r2.json()
        text = js.get("message",{}).get("content") or js.get("response") or ""
        return {"response": text}
    url3 = f"{base}/v1/chat/completions"
    r3 = requests.post(url3, json={"model": model, "messages": messages}, timeout=120)
    if r3.status_code == 200:
        js = r3.json()
        text = (js.get("choices") or [{}])[0].get("message",{}).get("content","")
        return {"response": text}
    raise RuntimeError("Ollama API ulaşılamadı (generate/chat/completions).")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        body = request.get_json(force=True)
        model = body.get("model","llama3.1:8b-instruct-q6_K")
        messages = body.get("messages", [])
        btc = api_btc_indicators().json["data"]
        fng = api_fng().json["data"]
        pumps = api_pump_candidates().json["data"][:5]
        etf = api_etf_events().json["data"]
        etf_summary = {}
        for a in ["BTC","ETH","SOL","XRP"]:
            etf_summary[a] = [e for e in etf if e.get("asset")==a and e.get("status")!="none"][:2]
        context = {"now": utcnow().isoformat(), "btc": btc, "fng": fng, "pump_candidates": pumps, "etf_summary": etf_summary}
        sys_prompt = ("You are a local crypto assistant. Use the JSON CONTEXT as latest truth. Answer in Turkish.")
        prompt = f"[CONTEXT JSON]\\n{json.dumps(context, ensure_ascii=False)}\\n\\n"
        for m in messages:
            role = m.get('role','user'); content = m.get('content','')
            prompt += f"{role}: {content}\\n"
        prompt += "assistant:"
        resp = ollama_generate(model, prompt, system=sys_prompt, stream=False)
        out = resp.get("response","").strip()
        return jsonify({"ok":True,"data":{"response": out}})
    except Exception as e:
        return jsonify({"ok":False,"error":str(e)}),500

if __name__ == "__main__":
    app.run(debug=True, port=34000, host="0.0.0.0")
