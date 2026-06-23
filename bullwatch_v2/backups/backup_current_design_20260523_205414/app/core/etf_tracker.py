"""Federal Register ETF event tracker.

Monitors SEC 19b-4 filings for crypto ETF approvals.
Extracted from ``legacy_monolith.py`` (FAZ 3).
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import requests

from app.cache import cache_get, cache_set

# ── API ──────────────────────────────────────────────────────────────
FR_API = "https://www.federalregister.gov/api/v1/documents.json"

# ── Keyword dictionaries ─────────────────────────────────────────────
ASSET_KEYWORDS = {
    "BTC": ["bitcoin", "spot bitcoin", "btc", "iShares", "BlackRock", "Fidelity",
            "ARK 21Shares", "Valkyrie", "VanEck", "WisdomTree", "Franklin",
            "Bitwise", "Grayscale", "Hashdex"],
    "ETH": ["ether", "ethereum", "spot ether", "eth", "iShares", "BlackRock",
            "Fidelity", "VanEck", "Bitwise", "Grayscale", "21Shares",
            "Franklin", "WisdomTree"],
    "SOL": ["solana", "spot solana", "sol", "VanEck", "21Shares", "Fidelity",
            "Hashdex", "Grayscale", "BlackRock"],
    "XRP": ["xrp", "ripple", "spot xrp", "ripple labs", "21Shares", "Hashdex",
            "Grayscale", "BlackRock", "Fidelity"],
}

EXCHANGE_KEYWORDS = ["Cboe BZX", "NYSE Arca", "Nasdaq", "Cboe EDGX", "Cboe BYX"]


# ── Helpers ──────────────────────────────────────────────────────────
def fr_search_documents(term: str, per_page: int = 30,
                        agency_slug: str = "securities-and-exchange-commission") -> dict:
    params = {
        "per_page": per_page,
        "order": "newest",
        "conditions[term]": term,
        "conditions[agencies][]": agency_slug,
    }
    r = requests.get(FR_API, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def classify_fr_status(title: str) -> str:
    t = (title or "").lower()
    if "granting approval" in t or "order approving" in t or "approval order" in t:
        return "approved"
    if "instituting proceedings" in t:
        return "proceedings"
    if "designation of a longer period" in t or "longer period" in t or "extend" in t or "delay" in t:
        return "delay"
    if "notice of filing" in t or "notice" in t:
        return "filed"
    if "immediate effectiveness" in t:
        return "effective"
    return "unknown"


def detect_exchange(title: str) -> str | None:
    for ex in EXCHANGE_KEYWORDS:
        if ex.lower() in (title or "").lower():
            return ex
    return None


def rough_deadline(status: str, pub_date: str) -> str | None:
    if not pub_date:
        return None
    try:
        d = datetime.fromisoformat(pub_date) if "T" in pub_date else datetime.fromisoformat(pub_date + "T00:00:00")
        d = d.replace(tzinfo=timezone.utc)
    except Exception:
        return None
    if status == "filed":
        return (d + timedelta(days=45)).isoformat()
    if status == "proceedings":
        return (d + timedelta(days=60)).isoformat()
    if status == "delay":
        return (d + timedelta(days=45)).isoformat()
    return None


# ── Main fetcher ────────────────────────────────────────────────────
def fetch_dynamic_etf_events() -> list:
    """Scrape Federal Register for crypto ETF 19b-4 filings, cached 5 min."""
    key = "dynamic_etf_events_v2"
    c = cache_get(key, ttl=300)
    if c is not None:
        return c
    ev: list = []
    for asset, kws in ASSET_KEYWORDS.items():
        found_any = False
        for kw in kws:
            term = f"{kw} 19b-4"
            try:
                js = fr_search_documents(term, per_page=200)
                for d in js.get("results", []):
                    title = d.get("title", "")
                    pub = (d.get("publication_date") or d.get("effective_on")
                           or d.get("signing_date") or d.get("created_at"))
                    url = d.get("html_url") or d.get("pdf_url")
                    doc = d.get("document_number")
                    abstract = d.get("abstract") or ""
                    status = classify_fr_status(title)
                    exch = detect_exchange(title) or "—"
                    manager = None
                    for m in ["iShares", "BlackRock", "Fidelity", "ARK 21Shares",
                              "Valkyrie", "VanEck", "WisdomTree", "Franklin",
                              "Bitwise", "Grayscale", "Hashdex", "21Shares"]:
                        if m.lower() in (title + " " + abstract).lower():
                            manager = m
                            break
                    found_any = True
                    ev.append({
                        "asset": asset, "manager": manager or "—", "exchange": exch,
                        "status": status, "title": title, "date": pub or "TBD",
                        "url": url, "doc": doc, "next_deadline_est": rough_deadline(status, pub),
                    })
            except Exception:
                continue
            time.sleep(0.15)
        if not found_any:
            ev.append({
                "asset": asset, "status": "none",
                "title": f"{asset} için 19b-4 kaydı bulunamadı",
                "date": None, "url": None,
            })
    uniq: dict = {}
    for e in ev:
        k = (e.get("doc") or "") + "|" + (e.get("title") or "")
        if k not in uniq:
            uniq[k] = e
    out = list(uniq.values())
    out.sort(key=lambda x: (x.get("date") or ""), reverse=True)
    if out:
        cache_set(key, out)
    return out
