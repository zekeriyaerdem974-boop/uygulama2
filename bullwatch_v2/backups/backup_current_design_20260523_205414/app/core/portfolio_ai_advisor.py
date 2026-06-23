# -*- coding: utf-8 -*-
"""Portfolio AI Advisor — FAZ 39.

AI destekli portföy içgörüleri. Mevcut piyasa bağlamını kullanarak
portföy analizi, risk uyarıları, çeşitlendirme önerileri üretir.

LEGAL_SAFE_MODE: Yatırım tavsiyesi üretilmez.
Yalnızca risk içgörüsü, dağılım yorumu, çeşitlendirme analizi,
piyasa maruziyeti gözlemleri sunar.

Public API:
  generate_portfolio_insight(user_id)
  ask_portfolio(user_id, question)
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Optional

from app.cache import cache_get, cache_set, utcnow

_logger = logging.getLogger("zkr_analiz.portfolio.ai_advisor")

CACHE_TTL = 180  # 3 minutes

_PORTFOLIO_SYSTEM = """Sen ZKR Analiz Portföy Analisti'sin. Türkçe yanıt ver.
Görevin: Kullanıcının portföyünü analiz ederek risk içgörüleri, dağılım yorumları,
çeşitlendirme analizi ve piyasa maruziyeti gözlemleri sunmak.

KESİN KURALLAR:
1. Her zaman Türkçe yanıt ver.
2. Kesinlikle al/sat/yatırım tavsiyesi verme.
3. "Almalısınız", "satmalısınız", "yatırım yapın" gibi ifadeler KULLANMA.
4. Sadece analitik gözlem, risk değerlendirmesi ve eğitim amaçlı bilgi sun.
5. Şu terimleri KULLAN: "gözlemlenmektedir", "dikkat çekmektedir", "değerlendirilebilir",
   "risk taşımaktadır", "dikkate alınabilir".
6. Her yanıtın sonunda "⚠️ Bu bir yatırım tavsiyesi değildir." ekle.
7. Veri yoksa bunu açıkça belirt.

YAPILANDIRILMIŞ YANIT:
📊 PORTFÖY ÖZETİ: Genel portföy değerlendirmesi (2-3 cümle)
⚖️ RİSK DEĞERLENDİRMESİ: Risk seviyesi yorumu
🎯 DAĞILIM ANALİZİ: Varlık dağılımı ve çeşitlendirme gözlemleri
🌍 PİYASA MARUZİYETİ: Hangi piyasalara ağırlıklı maruziyet var
⚠️ DİKKAT NOKTALARI: Önemli risk faktörleri
"""


def generate_portfolio_insight(user_id: str) -> Dict:
    """Generate AI-powered portfolio insight using LLM.

    Returns structured insight dict with risk_warning,
    diversification_comment, market_exposure, etc.
    """
    cache_key = f"portfolio_ai:{user_id}"
    cached = cache_get(cache_key, ttl=CACHE_TTL)
    if cached:
        return cached

    # Gather all data
    context = _build_portfolio_context(user_id)
    if not context.get("has_assets"):
        return _empty_insight()

    # Try LLM
    result = _call_portfolio_llm(context, "Portföyümü kapsamlı analiz et.")

    cache_set(cache_key, result)
    return result


def ask_portfolio(user_id: str, question: str) -> Dict:
    """Answer a specific question about the portfolio using AI."""
    cache_key = f"portfolio_ai_q:{user_id}:{hash(question)}"
    cached = cache_get(cache_key, ttl=CACHE_TTL)
    if cached:
        return cached

    context = _build_portfolio_context(user_id)
    if not context.get("has_assets"):
        return _empty_insight()

    result = _call_portfolio_llm(context, question)
    cache_set(cache_key, result)
    return result


# ══════════════════════════════════════════════════════════════════════
# CONTEXT BUILDING
# ══════════════════════════════════════════════════════════════════════

def _build_portfolio_context(user_id: str) -> Dict:
    """Build comprehensive context for AI analysis."""
    try:
        from app.core.portfolio_engine import portfolio_summary
        from app.core.portfolio_risk_engine import calculate_risk_score

        summary = portfolio_summary(user_id)
        risk = calculate_risk_score(user_id)

        context = {
            "has_assets": summary.get("asset_count", 0) > 0,
            "portfolio_summary": summary,
            "risk_analysis": risk,
        }

        # Add market context if available
        try:
            from app.core import news_impact_engine
            trending = news_impact_engine.get_trending_impacts(limit=5)
            context["recent_news_impacts"] = trending
        except Exception:
            pass

        return context
    except Exception as exc:
        _logger.error("Failed to build portfolio context: %s", exc)
        return {"has_assets": False}


def _empty_insight() -> Dict:
    return {
        "ok": True,
        "portfolio_insight": "Portföyünüzde henüz varlık bulunmuyor. "
                             "Varlık ekleyerek portföy analizinden yararlanabilirsiniz.",
        "risk_warning": "",
        "diversification_suggestion": "",
        "market_exposure": "N/A",
        "llm_used": False,
        "disclaimer": "⚠️ Bu bir yatırım tavsiyesi değildir.",
    }


# ══════════════════════════════════════════════════════════════════════
# LLM CALL
# ══════════════════════════════════════════════════════════════════════

def _call_portfolio_llm(context: Dict, question: str) -> Dict:
    """Call Ollama for portfolio analysis."""
    from app.core.copilot_service import DEFAULT_MODEL

    ctx_str = json.dumps(context, ensure_ascii=False, default=str)
    if len(ctx_str) > 6000:
        ctx_str = ctx_str[:6000] + "...(kırpıldı)"

    prompt = (
        f"[PORTFÖY CONTEXT JSON]\n{ctx_str}\n\n"
        f"[KULLANICI SORUSU]\n{question}\n\nassistant:"
    )

    answer = ""
    llm_ok = True

    try:
        from app.core.ollama_client import ollama_generate
        resp = ollama_generate(DEFAULT_MODEL, prompt, system=_PORTFOLIO_SYSTEM, stream=False)
        answer = (resp.get("response") or "").strip()
    except Exception as exc:
        _logger.warning("Portfolio AI LLM call failed: %s", exc)
        answer = _generate_fallback(context)
        llm_ok = False

    if not answer:
        answer = _generate_fallback(context)
        llm_ok = False

    # Parse sections
    parsed = _parse_insight(answer)

    return {
        "ok": True,
        "answer": answer,
        "portfolio_insight": parsed.get("portfolio_insight", ""),
        "risk_warning": parsed.get("risk_warning", ""),
        "diversification_suggestion": parsed.get("diversification_suggestion", ""),
        "market_exposure": parsed.get("market_exposure", ""),
        "llm_used": llm_ok,
        "generated_at": utcnow().isoformat(),
        "disclaimer": "⚠️ Bu bir yatırım tavsiyesi değildir.",
    }


def _parse_insight(answer: str) -> Dict:
    """Parse structured AI answer into sections."""
    result = {
        "portfolio_insight": "",
        "risk_warning": "",
        "diversification_suggestion": "",
        "market_exposure": "",
    }
    if not answer:
        return result

    lines = answer.split("\n")
    current = "portfolio_insight"
    sections: Dict[str, list] = {k: [] for k in result}

    for line in lines:
        s = line.strip()
        if not s:
            continue
        lower = s.casefold()
        if "portföy özet" in lower or "📊" in s:
            current = "portfolio_insight"
            parts = s.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                sections[current].append(parts[1].strip())
            continue
        elif "risk değerlendirme" in lower or ("⚖️" in s and "risk" in lower):
            current = "risk_warning"
            parts = s.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                sections[current].append(parts[1].strip())
            continue
        elif "dağılım" in lower or "çeşitlendirme" in lower or "🎯" in s:
            current = "diversification_suggestion"
            parts = s.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                sections[current].append(parts[1].strip())
            continue
        elif "maruziyet" in lower or "🌍" in s:
            current = "market_exposure"
            parts = s.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                sections[current].append(parts[1].strip())
            continue
        elif "dikkat nokta" in lower or ("⚠️" in s and "yatırım tavsiyesi" not in lower):
            current = "risk_warning"
            parts = s.split(":", 1)
            if len(parts) > 1 and parts[1].strip():
                sections[current].append(parts[1].strip())
            continue

        clean = s.lstrip("-•*–►▸● ").strip()
        if clean and "yatırım tavsiyesi değildir" not in clean.lower():
            sections[current].append(clean)

    for key in result:
        result[key] = " ".join(sections[key][:5])

    if not result["portfolio_insight"]:
        result["portfolio_insight"] = answer[:500]

    return result


def _generate_fallback(context: Dict) -> str:
    """Generate a rule-based fallback when LLM is unavailable."""
    summary = context.get("portfolio_summary", {})
    risk = context.get("risk_analysis", {})

    total_value = summary.get("total_value", 0)
    total_pnl = summary.get("total_pnl", 0)
    asset_count = summary.get("asset_count", 0)
    risk_score = risk.get("risk_score", 0)
    risk_label_tr = risk.get("risk_label_tr", "Belirsiz")
    top_asset = risk.get("top_asset", "")
    top_alloc = risk.get("top_allocation", 0)
    mkt_breakdown = summary.get("market_breakdown", {})

    pnl_comment = "kârdadır" if total_pnl >= 0 else "zarardadır"
    pnl_pct = summary.get("total_pnl_pct", 0)

    parts = [
        f"📊 PORTFÖY ÖZETİ: Portföyünüz toplam ${total_value:,.0f} değerinde, "
        f"{asset_count} varlıktan oluşmaktadır. Portföyünüz şu an %{abs(pnl_pct):.1f} {pnl_comment}.",
        "",
        f"⚖️ RİSK DEĞERLENDİRMESİ: Risk skoru {risk_score:.0f}/100 ({risk_label_tr}). "
        f"Portföy volatilitesi {risk.get('volatility', 0):.2%} seviyesinde gözlemlenmektedir.",
        "",
    ]

    if top_alloc > 50:
        parts.append(
            f"🎯 DAĞILIM ANALİZİ: Portföyünüzde {top_asset} varlığı %{top_alloc:.0f} oranıyla "
            f"baskın konumdadır. Yüksek konsantrasyon riski dikkat çekmektedir."
        )
    else:
        parts.append(
            f"🎯 DAĞILIM ANALİZİ: Varlıklarınız daha dengeli bir dağılım göstermektedir. "
            f"En büyük ağırlık {top_asset} ile %{top_alloc:.0f} seviyesindedir."
        )

    # Market exposure
    if mkt_breakdown:
        dominant = max(mkt_breakdown, key=mkt_breakdown.get)
        parts.append("")
        parts.append(
            f"🌍 PİYASA MARUZİYETİ: Portföyünüz ağırlıklı olarak {dominant} "
            f"piyasasına maruz kalmaktadır (%{mkt_breakdown[dominant]:.0f})."
        )

    parts.append("")
    parts.append("⚠️ Bu bir yatırım tavsiyesi değildir.")

    return "\n".join(parts)
