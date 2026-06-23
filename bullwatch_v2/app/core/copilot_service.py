# -*- coding: utf-8 -*-
"""Copilot AI Service — FAZ 21.

Takes user questions + context from copilot_context.py,
constructs intelligent prompts, sends to Ollama, and returns
structured responses.

Features:
  - Turkish-only responses
  - Context-aware system prompts
  - Structured answer format with key_points, risk_points, suggested_alerts
  - Graceful Ollama fallback
  - Short-term response caching
  - Timeout management
  - "Yatırım tavsiyesi değildir" disclaimer
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Dict, List, Optional

from app.cache import cache_get, cache_set, utcnow
from app.core.ollama_client import ollama_generate

_logger = logging.getLogger("zkr_analiz.copilot.service")

# ── Configuration ─────────────────────────────────────────────────
DEFAULT_MODEL = "nemotron-3-nano:30b"
RESPONSE_CACHE_TTL = 120  # 2 minutes
MAX_CONTEXT_CHARS = 8000  # Truncate context to fit model window

# ── System Prompts ────────────────────────────────────────────────

_SYSTEM_BASE = """Sen ZKR Analiz AI Market Analyst'sın. Türkçe yanıt ver.
Görevin: Kullanıcıya piyasa verileri, teknik analiz, haberler ve piyasa duyarlılığı hakkında yardımcı olmak.

KURALLAR:
1. Her zaman Türkçe yanıt ver.
2. Yanıtlarını verilen CONTEXT JSON verisine dayandır — uydurma yapma.
3. Teknik terimleri (RSI, MACD, EMA, destek/direnç) doğal kullan.
4. Kısa ve öz yanıtlar ver, gereksiz tekrar yapma.
5. Her yanıtın sonunda "⚠️ Bu bir yatırım tavsiyesi değildir." ekle.
6. Eğer veri yoksa veya yetersizse, bunu açıkça belirt.
7. Kesinlikle alım/satım talimatı, giriş/çıkış fiyatı veya işlem sinyali verme.
   Sadece piyasa analizi ve eğitim amaçlı bilgi sun.

YAPILANDIRILMIŞ YANIT:
Yanıtını şu bölümlere ayır (her bölümü bir satırla başlat):
📊 ÖZET: Genel değerlendirmen (2-3 cümle)
🔑 ÖNEMLİ NOKTALAR: Madde madde önemli gözlemler
⚠️ RİSKLER: Potansiyel riskler
🎯 İZLENECEK SEVİYELER: Varsa, izlenmesi gereken seviyeler (symbol, koşul, değer)
"""

_SYMBOL_PROMPT = """Bu yanıtı {symbol} ({market}) sembolü için {timeframe} zaman diliminde veriyorsun.
Context JSON'da bu sembolün güncel fiyatı, teknik indikatörleri (RSI, MACD, EMA),
sinyal motoru kararı, destek/direnç seviyeleri, ilgili haberler ve aktif alarmlar var.
Bu verilere dayanarak kullanıcının sorusunu yanıtla."""

_MARKET_PROMPT = """Bu yanıtı {market} piyasası genel durumu için veriyorsun.
Context JSON'da piyasanın en çok hareket eden sembollerinin verileri,
piyasa duyarlılığı ve güncel haberler var.
Bu verilere dayanarak kullanıcının sorusunu yanıtla."""

_SCREENER_PROMPT = """Bu yanıtı {market} piyasası screener (tarama) sonuçları için veriyorsun.
Context JSON'da tarama sonuçları, uygulanan filtreler ve eşleşen semboller var.
En güçlü adayları, filtre mantığını ve yatırımcı için önemli noktaları açıkla."""

_DISCOVER_PROMPT = """Bu yanıtı ZKR Analiz Keşfet sayfası için veriyorsun.
Context JSON'da çoklu piyasa verileri (kripto, hisse, BIST, forex, emtia),
güncel haberler ve piyasa duyarlılığı var.
Bugün piyasada öne çıkanları, önemli haberleri ve genel piyasa resmini özetle."""

_SIMULATOR_PROMPT = """Bu yanıtı ZKR Analiz Simülatör (Paper Trading) sistemi için veriyorsun.
Context JSON'da kullanıcının sanal portföyü, açık pozisyonları, PnL durumu,
son işlemleri ve hesap bilgileri var.
Kullanıcının portföy performansını analiz et, risk durumunu değerlendir,
pozisyon çeşitlendirmesi hakkında yorum yap ve iyileştirme önerileri sun."""

_PORTFOLIO_PROMPT = """Bu yanıtı ZKR Analiz Portföy (Portfolio Intelligence) sistemi için veriyorsun.
Context JSON'da kullanıcının portföy varlıkları, toplam değer, PnL durumu,
varlık dağılımı, risk skoru, volatilite, konsantrasyon riski ve çeşitlendirme bilgileri var.
Kullanıcının portföy riskini değerlendir, dağılım analizini yap,
piyasa maruziyetini yorumla ve çeşitlendirme gözlemleri sun.
Kesinlikle alım/satım tavsiyesi verme. Sadece analitik gözlemler sun."""

_JOURNAL_PROMPT = """Bu yanıtı ZKR Analiz Trade Journal (İşlem Günlüğü) sistemi için veriyorsun.
Context JSON'da kullanıcının işlem günlüğü kayıtları, istatistikleri,
duygu dağılımı, strateji performansı ve kazanma/kaybetme serileri var.
Kullanıcının işlem psikolojisini analiz et, duygu bazlı hataları tespit et,
strateji performanslarını karşılaştır ve iyileştirme önerileri sun.
Özellikle 'korku' veya 'açgözlülük' duygularıyla yapılan işlemlerde kalıp var mı analiz et."""

_OPPORTUNITIES_PROMPT = """Bu yanıtı ZKR Analiz AI Market Opportunities (Fırsat Motoru) sistemi için veriyorsun.
Context JSON'da fırsat motorunun tespit ettiği piyasa fırsatları, güvenilirlik skorları,
olay tipleri (hacim artışı, momentum değişimi, volatilite, RSI aşırı bölge, kırılım, 
büyük hacim hareketi, sektör rotasyonu) ve piyasa verileri var.
Tespit edilen fırsatları analiz et, en dikkat çekici olanları vurgula, 
piyasa korelasyonlarını ve genel piyasa resmini yorumla.
Kesinlikle alım/satım tavsiyesi verme — sadece gözlem ve analiz sun."""


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def ask_symbol(
    symbol: str,
    market: str,
    timeframe: str,
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about a specific symbol with full context.

    Returns structured response dict.
    """
    from app.core.copilot_context import build_symbol_context

    # Check cache
    cache_key = _cache_key("symbol", symbol, market, timeframe, question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    # Build context
    ctx = build_symbol_context(symbol, market, timeframe)

    # Build prompt
    system = _SYSTEM_BASE + _SYMBOL_PROMPT.format(
        symbol=symbol, market=market, timeframe=timeframe,
    )
    prompt = _build_prompt(ctx, question)

    # Call LLM
    result = _call_llm(model, system, prompt, ctx)

    # Cache
    cache_set(cache_key, result)
    return result


def ask_market(
    market: str,
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about a market with market-wide context."""
    from app.core.copilot_context import build_market_context

    cache_key = _cache_key("market", market, "", "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    ctx = build_market_context(market)
    system = _SYSTEM_BASE + _MARKET_PROMPT.format(market=market)
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


def ask_screener(
    market: str,
    filters: Optional[List[str]],
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about screener results."""
    from app.core.copilot_context import build_screener_context

    filter_str = ",".join(filters) if filters else ""
    cache_key = _cache_key("screener", market, filter_str, "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    ctx = build_screener_context(market, filters)
    system = _SYSTEM_BASE + _SCREENER_PROMPT.format(market=market)
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


def ask_discover(
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about overall market situation (discover page)."""
    from app.core.copilot_context import build_discover_context

    cache_key = _cache_key("discover", "", "", "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    ctx = build_discover_context()
    system = _SYSTEM_BASE + _DISCOVER_PROMPT
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


def ask_simulator(
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about the paper trading portfolio / simulator."""
    from app.core.copilot_context import build_simulator_context

    cache_key = _cache_key("simulator", "", "", "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    ctx = build_simulator_context()
    system = _SYSTEM_BASE + _SIMULATOR_PROMPT
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


def ask_portfolio_copilot(
    question: str,
    user_id: str = "default",
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about a user's portfolio — FAZ 39."""
    from app.core.portfolio_ai_advisor import _build_portfolio_context

    cache_key = _cache_key("portfolio", user_id, "", "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    ctx = _build_portfolio_context(user_id)
    system = _SYSTEM_BASE + _PORTFOLIO_PROMPT
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


def ask_journal(
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about the trade journal — FAZ 23."""
    from app.core.copilot_context import build_journal_context

    cache_key = _cache_key("journal", "", "", "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    ctx = build_journal_context()
    system = _SYSTEM_BASE + _JOURNAL_PROMPT
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


def ask_opportunities(
    question: str,
    model: str = DEFAULT_MODEL,
) -> Dict:
    """Ask a question about market opportunities — FAZ 40."""
    from app.core.opportunity_engine import get_cached_opportunities

    cache_key = _cache_key("opportunities", "", "", "", question)
    cached = cache_get(cache_key, ttl=RESPONSE_CACHE_TTL)
    if cached:
        return cached

    opps = get_cached_opportunities()
    ctx = {
        "opportunities": opps[:20] if opps else [],
        "total_count": len(opps) if opps else 0,
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
    system = _SYSTEM_BASE + _OPPORTUNITIES_PROMPT
    prompt = _build_prompt(ctx, question)

    result = _call_llm(model, system, prompt, ctx)
    cache_set(cache_key, result)
    return result


# ══════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════

def _build_prompt(context: Dict, question: str) -> str:
    """Combine context JSON and user question into a prompt string."""
    ctx_str = json.dumps(context, ensure_ascii=False, default=str)

    # Truncate if too long
    if len(ctx_str) > MAX_CONTEXT_CHARS:
        ctx_str = ctx_str[:MAX_CONTEXT_CHARS] + "...(kırpıldı)"

    return (
        f"[CONTEXT JSON]\n{ctx_str}\n\n"
        f"[KULLANICI SORUSU]\n{question}\n\n"
        f"assistant:"
    )


def _call_llm(model: str, system: str, prompt: str, context: Dict) -> Dict:
    """Call Ollama and parse the response into structured format."""
    answer = ""
    llm_ok = True

    try:
        resp = ollama_generate(model, prompt, system=system, stream=False)
        answer = (resp.get("response") or "").strip()
    except Exception as exc:
        _logger.warning("Copilot LLM call failed: %s", exc)
        answer = _generate_fallback_answer(context)
        llm_ok = False

    if not answer:
        answer = _generate_fallback_answer(context)
        llm_ok = False

    # Parse structured sections
    parsed = _parse_structured_answer(answer)

    # Extract suggested alerts from context (signal-based)
    suggested_alerts = _extract_suggested_alerts(context)

    return {
        "ok": True,
        "answer": answer,
        "summary": parsed.get("summary", ""),
        "key_points": parsed.get("key_points", []),
        "risk_points": parsed.get("risk_points", []),
        "suggested_alerts": suggested_alerts,
        "llm_used": llm_ok,
        "model": model,
        "generated_at": utcnow().isoformat(),
        "disclaimer": "⚠️ Bu bir yatırım tavsiyesi değildir.",
    }


def _parse_structured_answer(answer: str) -> Dict:
    """Parse the AI answer into summary, key_points, risk_points."""
    result: Dict = {"summary": "", "key_points": [], "risk_points": []}

    if not answer:
        return result

    lines = answer.split("\n")
    current_section = "summary"
    summary_lines = []
    key_points = []
    risk_points = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect section headers (handle Turkish İ/ı casefold)
        lower = stripped.casefold().replace("\u0130", "i").replace("i\u0307", "i")
        if "özet" in lower and ("📊" in stripped or "özet:" in lower):
            current_section = "summary"
            # Extract text after the header
            parts = stripped.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                summary_lines.append(parts[1].strip())
            continue
        elif "önemli nokta" in lower or "🔑" in stripped:
            current_section = "key_points"
            parts = stripped.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                key_points.append(parts[1].strip())
            continue
        elif ("⚠️" in stripped) or (lower.startswith("risk") and len(stripped.split()) <= 3):
            if "yatırım tavsiyesi" not in lower:
                current_section = "risk_points"
                parts = stripped.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    risk_points.append(parts[1].strip())
                continue
        elif "alarm" in lower and ("🎯" in stripped or "öner" in lower):
            current_section = "alerts"
            continue

        # Collect content per section
        # Remove bullet markers
        clean = stripped.lstrip("-•*–►▸● ").strip()
        if not clean:
            continue

        if current_section == "summary":
            summary_lines.append(clean)
        elif current_section == "key_points":
            key_points.append(clean)
        elif current_section == "risk_points":
            if "yatırım tavsiyesi" not in clean.lower():
                risk_points.append(clean)

    result["summary"] = " ".join(summary_lines[:3])
    result["key_points"] = key_points[:8]
    result["risk_points"] = risk_points[:5]

    # If no structured sections found, treat entire answer as summary
    if not result["summary"] and not result["key_points"]:
        result["summary"] = answer[:500]

    return result


def _extract_suggested_alerts(context: Dict) -> List[Dict]:
    """Extract suggested alerts from context data (signal + S/R levels)."""
    alerts = []
    symbol = context.get("symbol", "")
    market = context.get("market", "crypto")

    if not symbol:
        return alerts

    # From support/resistance
    sr = context.get("support_resistance", {})
    for r in (sr.get("resistance") or [])[:2]:
        alerts.append({
            "symbol": symbol,
            "market": market,
            "condition_type": "price_above",
            "condition_value": r.get("price"),
            "reason": f"{r.get('label', 'R')} direnci üstü breakout",
        })
    for s in (sr.get("support") or [])[:1]:
        alerts.append({
            "symbol": symbol,
            "market": market,
            "condition_type": "price_below",
            "condition_value": s.get("price"),
            "reason": f"{s.get('label', 'S')} desteği altına düşüş",
        })

    # RSI-based alerts
    indicators = context.get("indicators", {})
    rsi = indicators.get("rsi14")
    if rsi is not None:
        if rsi > 65:
            alerts.append({
                "symbol": symbol,
                "market": market,
                "condition_type": "rsi_above",
                "condition_value": 70,
                "reason": "RSI aşırı alım bölgesine yaklaşıyor",
            })
        elif rsi < 35:
            alerts.append({
                "symbol": symbol,
                "market": market,
                "condition_type": "rsi_below",
                "condition_value": 30,
                "reason": "RSI aşırı satım bölgesine yaklaşıyor",
            })

    return alerts


def _generate_fallback_answer(context: Dict) -> str:
    """Generate a data-driven fallback when Ollama is unavailable."""
    parts = []
    symbol = context.get("symbol", "")
    market = context.get("market", "")

    if symbol:
        parts.append(f"📊 **{symbol}** ({market}) analizi:")

        # Price info
        price_info = context.get("price", {})
        if price_info.get("current"):
            parts.append(f"Güncel fiyat: {price_info['current']}")

        # Indicators
        ind = context.get("indicators", {})
        if ind.get("rsi14"):
            rsi = ind["rsi14"]
            rsi_label = "aşırı alım" if rsi > 70 else "aşırı satım" if rsi < 30 else "normal"
            parts.append(f"RSI(14): {rsi} ({rsi_label})")
        if ind.get("trend"):
            parts.append(f"Trend: {ind['trend']}")
        if ind.get("macd_bullish") is not None:
            macd_label = "pozitif (boğa)" if ind["macd_bullish"] else "negatif (ayı)"
            parts.append(f"MACD histogram: {macd_label}")

        # Signal
        sig = context.get("signal", {})
        if sig.get("decision"):
            parts.append(f"Sinyal kararı: {sig['decision']}")
        if sig.get("note"):
            parts.append(f"Not: {sig['note']}")

        # S/R
        sr = context.get("support_resistance", {})
        supports = sr.get("support", [])
        resistances = sr.get("resistance", [])
        if supports:
            s_str = ", ".join(f"{s.get('label')}: {s.get('price')}" for s in supports[:2])
            parts.append(f"Destek: {s_str}")
        if resistances:
            r_str = ", ".join(f"{r.get('label')}: {r.get('price')}" for r in resistances[:2])
            parts.append(f"Direnç: {r_str}")
    else:
        # Market/discover context
        parts.append("📊 Piyasa Özeti:")
        movers = context.get("top_movers", [])
        if movers:
            for m in movers[:5]:
                chg = m.get("change_24h", 0)
                arrow = "🟢" if chg > 0 else "🔴" if chg < 0 else "⚪"
                parts.append(f"{arrow} {m['symbol']}: %{chg}")

        sentiment = context.get("market_sentiment", {}) or context.get("crypto_sentiment", {})
        if sentiment.get("fear_greed_label"):
            parts.append(f"Korku/Açgözlülük: {sentiment['fear_greed_index']} ({sentiment['fear_greed_label']})")

    if not parts:
        parts.append("Şu an yeterli veri bulunamadı. Lütfen daha sonra tekrar deneyin.")

    parts.append("\n⚠️ Bu bir yatırım tavsiyesi değildir.")
    return "\n".join(parts)


def _cache_key(*args) -> str:
    """Generate a short cache key from arguments."""
    raw = "|".join(str(a) for a in args)
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"copilot:resp:{h}"
