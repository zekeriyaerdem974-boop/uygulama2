# -*- coding: utf-8 -*-
"""BIST (Borsa Istanbul) data service.

FAZ 17 — Real market data via Yahoo Finance.
BIST symbols use .IS suffix on Yahoo Finance.
FAZ 24A — Validated symbol universe (~500 symbols, delisted removed).
"""
from __future__ import annotations

import logging
from typing import List, Dict

from app.core.yahoo_client import get_symbols_info, get_ticker, get_klines

_logger = logging.getLogger("zkr_analiz.bist")

# ══════════════════════════════════════════════════════════════════════
# BIST TÜM — BIST-30, BIST-50, BIST-100, Yıldız Pazar, Ana Pazar
# ══════════════════════════════════════════════════════════════════════
DEFAULT_SYMBOLS = [
    # ── BIST-30 ──────────────────────────────────────────────────────
    "THYAO.IS", "ASELS.IS", "TUPRS.IS", "SISE.IS", "GARAN.IS",
    "KCHOL.IS", "SAHOL.IS", "EREGL.IS", "BIMAS.IS", "AKBNK.IS",
    "PGSUS.IS", "TAVHL.IS", "FROTO.IS", "TOASO.IS", "SASA.IS",
    "YKBNK.IS", "HALKB.IS", "PETKM.IS", "TCELL.IS", "ARCLK.IS", "KRDMD.IS", "EKGYO.IS", "EKOS.IS", "ENKAI.IS",
    "TTKOM.IS", "DOHOL.IS", "GUBRF.IS", "ISCTR.IS", "VAKBN.IS",
    # ── BIST-50 Ek ───────────────────────────────────────────────────
    "AEFES.IS", "AKSEN.IS", "ALARK.IS", "AGHOL.IS", "ANHYT.IS",
    "AYDEM.IS", "BASGZ.IS", "BRISA.IS", "CCOLA.IS", "CIMSA.IS",
    "DOAS.IS", "EGEEN.IS", "ENJSA.IS", "GESAN.IS", "HEKTS.IS",
    "ISGYO.IS", "KONTR.IS", "LOGO.IS", "MGROS.IS", "ODAS.IS",
    "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "QUAGR.IS", "SELEC.IS",
    "SOKM.IS", "TMSN.IS", "TRGYO.IS", "ULKER.IS", "VESTL.IS",
    # ── BIST-100 Ek ──────────────────────────────────────────────────
    "AGYO.IS", "AKFGY.IS", "AKSA.IS", "ALFAS.IS", "ALKIM.IS",
    "ANSGR.IS", "ASTOR.IS", "BERA.IS", "BTCIM.IS", "BUCIM.IS",
    "CEMAS.IS", "CEMTS.IS", "CUSAN.IS", "CVKMD.IS", "DEVA.IS",
    "DYOBY.IS", "ECILC.IS", "ESEN.IS", "EUPWR.IS", "EUREN.IS",
    "GEDZA.IS", "GLYHO.IS", "GOKNR.IS", "GOZDE.IS", "GSDHO.IS",
    "GWIND.IS", "HKTM.IS", "INDES.IS", "ISDMR.IS",
    "ISFIN.IS", "IZENR.IS", "KARSN.IS", "KAYSE.IS", "KLSER.IS",
    "KMPUR.IS", "KONKA.IS", "KONYA.IS", "KORDS.IS", "KTLEV.IS",
    "MAVI.IS", "MIATK.IS", "NETAS.IS", "NUGYO.IS", "OBAMS.IS",
    "PAPIL.IS", "PARSN.IS", "POLHO.IS", "REEDR.IS",
    "SMRTG.IS", "SNGYO.IS", "SUNTK.IS", "SUWEN.IS", "TATGD.IS",
    "TKFEN.IS", "TKNSA.IS", "TMPOL.IS", "TTRAK.IS", "TUKAS.IS",
    "TURSG.IS", "VAKKO.IS", "VERUS.IS", "VESBE.IS", "YEOTK.IS",
    "YYLGD.IS", "ZOREN.IS",
    # ── Yıldız Pazar — Bankacılık / Finans ───────────────────────────
    "TSKB.IS", "SKBNK.IS", "ALBRK.IS", "ICBCT.IS", "KLNMA.IS", "ATAGY.IS", "FENER.IS",
    "BJKAS.IS", "GSRAY.IS", "TSPOR.IS", "BRYAT.IS", "MPARK.IS",
    # ── Yıldız Pazar — Sanayi / Üretim ──────────────────────────────
    "ACSEL.IS", "ADEL.IS", "AKENR.IS", "AKSGY.IS", "AKSUE.IS",
    "ALCAR.IS", "ALCTL.IS", "ALGYO.IS", "ALTNY.IS", "ANELE.IS",
    "ARENA.IS", "ARSAN.IS", "ARZUM.IS", "ATATP.IS",
    "ATEKS.IS", "AVGYO.IS", "AVHOL.IS", "AVOD.IS", "AVTUR.IS",
    "AYCES.IS", "BAGFS.IS", "BAKAB.IS", "BALAT.IS", "BANVT.IS",
    "BARMA.IS", "BASCM.IS", "BAYRK.IS", "BEYAZ.IS", "BFREN.IS",
    "BIENY.IS", "BIGCH.IS", "BINHO.IS", "BIOEN.IS",
    "BIZIM.IS", "BLCYT.IS", "BMSCH.IS", "BMSTL.IS", "BNTAS.IS",
    "BOBET.IS", "BOSSA.IS", "BRKSN.IS", "BRLSM.IS", "BRMEN.IS",
    "BSOKE.IS", "BURCE.IS", "BURVA.IS", "CASA.IS", "CANTE.IS",
    # ── Yıldız Pazar — Devam ────────────────────────────────────────
    "CELHA.IS", "CEOEM.IS", "CGCAM.IS", "CMENT.IS", "CONSE.IS",
    "COSMO.IS", "CRDFA.IS", "CRFSA.IS", "DAGI.IS",
    "DAPGM.IS", "DARDL.IS", "DENGE.IS", "DERHL.IS", "DERIM.IS",
    "DESPC.IS", "DGATE.IS", "DGNMO.IS", "DITAS.IS", "DMRGD.IS",
    "DMSAS.IS", "DNISI.IS", "DOCO.IS", "DOGUB.IS",
    "DURDO.IS", "DZGYO.IS", "EBEBK.IS", "EDIP.IS", "EGGUB.IS", "EGPRO.IS", "EGSER.IS",
    "EKSUN.IS", "ELITE.IS", "EMKEL.IS", "EMNIS.IS", "ENSRI.IS",
    "ENTRA.IS", "EPLAS.IS", "ERBOS.IS", "ERCB.IS", "ERSU.IS",
    "ESCAR.IS", "ESCOM.IS", "ETILR.IS", "ETYAT.IS", "EUYO.IS",
    # ── Ana Pazar — Teknoloji / Yazılım ──────────────────────────────
    "FONET.IS", "FORMT.IS", "FORTE.IS", "FRIGO.IS", "FZLGY.IS",
    "GARAN.IS", "GARFA.IS", "GEDIK.IS", "GENIL.IS", "GENTS.IS",
    "GLBMD.IS", "GLCVY.IS", "GLRMK.IS", "GLRYH.IS", "GMTAS.IS", "GOODY.IS", "GRSEL.IS", "GSDDE.IS", "GSRAY.IS", "GZNMI.IS", "HATEK.IS", "HATSN.IS",
    "HEDEF.IS", "HDFGS.IS", "HLGYO.IS", "HTTBT.IS",
    "HUBVC.IS", "HUNER.IS", "HURGZ.IS", "ICUGS.IS", "IDGYO.IS",
    # ── Ana Pazar — Gıda / Tarım ────────────────────────────────────
    "IHEVA.IS", "IHGZT.IS", "IHLAS.IS", "IHLGM.IS", "IHYAY.IS",
    "IMASM.IS", "INGRM.IS", "INTEM.IS", "INVEO.IS", "ISATR.IS",
    "ISBIR.IS", "ISBTR.IS", "ISDMR.IS", "ISFIN.IS", "ISKPL.IS", "ISMEN.IS", "IEYHO.IS", "IZFAS.IS",
    "JANTS.IS", "KAPLM.IS", "KAREL.IS", "KARSN.IS", "KARTN.IS",
    "KATMR.IS", "KAYSE.IS", "KBORU.IS", "KCAER.IS", "KCHOL.IS",
    "KENT.IS", "KERVN.IS", "KFEIN.IS", "KGYO.IS",
    "KIMMR.IS", "KLGYO.IS", "KLMSN.IS", "KLRHO.IS", "KLSYN.IS",
    # ── Ana Pazar — Enerji / Madencilik ──────────────────────────────
    "KNFRT.IS", "KONKA.IS", "KOTON.IS", "KRGYO.IS",
    "KRONT.IS", "KRPLS.IS", "KRSTL.IS", "KRTEK.IS", "KRVGD.IS",
    "KTSKR.IS", "KUTPO.IS", "KUYAS.IS", "KZBGY.IS", "KZGYO.IS",
    "LIDER.IS", "LIDFA.IS", "LILAK.IS", "LINK.IS", "LKMNH.IS",
    "LUKSK.IS", "MAALT.IS", "MACKO.IS", "MAGEN.IS", "MAKIM.IS",
    "MANAS.IS", "MARKA.IS", "MARTI.IS", "MAVI.IS", "MEDTR.IS",
    "MEGAP.IS", "MEGMT.IS", "MEKAG.IS", "MERCN.IS", "MERIT.IS",
    "MERKO.IS", "METRO.IS", "MHRGY.IS", "MIATK.IS", "MMCAS.IS", "MNDRS.IS", "MNDTR.IS", "MOBTL.IS",
    "MOGAN.IS", "MSGYO.IS", "MTRKS.IS", "MTRYO.IS", "MZHLD.IS",
    # ── Ana Pazar — İnşaat / Gayrimenkul ─────────────────────────────
    "NATEN.IS", "NETAS.IS", "NIBAS.IS", "NTGAZ.IS", "NTHOL.IS",
    "NUGYO.IS", "NUHCM.IS", "OBAMS.IS", "OBASE.IS", "ODINE.IS",
    "OFSYM.IS", "ONCSM.IS", "ORGE.IS", "ORMA.IS", "OSMEN.IS",
    "OSTIM.IS", "OTKAR.IS", "OTTO.IS", "OYAKC.IS", "OYLUM.IS",
    "OYYAT.IS", "OZGYO.IS", "OZKGY.IS", "OZRDN.IS", "OZSUB.IS", "PAGYO.IS", "PAMEL.IS", "PAPIL.IS", "PARSN.IS",
    "PASEU.IS", "PCILT.IS", "PEKGY.IS", "PENGD.IS", "PENTA.IS",
    "PETKM.IS", "PETUN.IS", "PGSUS.IS", "PINSU.IS", "PKART.IS",
    "PKENT.IS", "PLTUR.IS", "PNLSN.IS", "PNSUT.IS", "POLHO.IS",
    "POLTK.IS", "PRDGS.IS", "PRKAB.IS", "PRKME.IS", "PRZMA.IS",
    # ── Ana Pazar — Holding / Yatırım ───────────────────────────────
    "QUAGR.IS", "RALYH.IS", "RAYSG.IS", "REEDR.IS", "RGYAS.IS",
    "RODRG.IS", "ROYAL.IS", "RTALB.IS", "RUBNS.IS", "RYGYO.IS",
    "RYSAS.IS", "SAFKR.IS", "SAHOL.IS", "SAMAT.IS", "SANEL.IS",
    "SANFM.IS", "SANKO.IS", "SARKY.IS", "SASA.IS", "SAYAS.IS",
    "SDTTR.IS", "SEGYO.IS", "SEKFK.IS", "SEKUR.IS", "SELEC.IS", "SELVA.IS", "SILVR.IS", "SISE.IS", "SKTAS.IS",
    "SMART.IS", "SMRTG.IS", "SNGYO.IS", "SNKRN.IS", "SNPAM.IS",
    "SODSN.IS", "SOKM.IS", "SONME.IS", "SRVGY.IS", "SUMAS.IS",
    "SUNTK.IS", "SURGY.IS", "SUWEN.IS", "TABGD.IS", "TARKM.IS",
    "TATEN.IS", "TATGD.IS", "TAVHL.IS", "TDGYO.IS", "TEKTU.IS",
    # ── Ana Pazar — Son ─────────────────────────────────────────────
    "TERA.IS", "TEZOL.IS", "TGSAS.IS", "THYAO.IS", "TKFEN.IS",
    "TKNSA.IS", "TLMAN.IS", "TMPOL.IS", "TMSN.IS", "TOASO.IS", "TRCAS.IS", "TRGYO.IS", "TRILC.IS", "TSGYO.IS",
    "TSPOR.IS", "TTKOM.IS", "TTRAK.IS", "TUCLK.IS", "TUKAS.IS",
    "TUPRS.IS", "TUREX.IS", "TURSG.IS", "UFUK.IS", "ULAS.IS",
    "ULKER.IS", "ULUFA.IS", "ULUSE.IS", "ULUUN.IS", "UMPAS.IS",
    "UNLU.IS", "USAK.IS", "VAKBN.IS", "VAKFN.IS",
    "VAKKO.IS", "VANGD.IS", "VBTYZ.IS", "VERTU.IS", "VERUS.IS",
    "VESBE.IS", "VESTL.IS", "VKFYO.IS", "VKGYO.IS", "VRGYO.IS",
    "YAPRK.IS", "YATAS.IS", "YEOTK.IS", "YESIL.IS", "YGYO.IS",
    "YKBNK.IS", "YKSLN.IS", "YONGA.IS", "YUNSA.IS", "YYAPI.IS",
    "YYLGD.IS", "ZEDUR.IS", "ZOREN.IS", "ZRGYO.IS",
]

class BistDataService:
    """BIST (Borsa Istanbul) data service using Yahoo Finance."""

    MARKET_TYPE = "bist"

    @staticmethod
    def get_symbols() -> List[Dict]:
        """Return list of BIST symbols with prices."""
        return get_symbols_info(DEFAULT_SYMBOLS, market_type="bist")

    @staticmethod
    def get_ticker_single(symbol: str) -> Dict:
        """Return ticker data for a single BIST stock."""
        return get_ticker(symbol)

    @staticmethod
    def get_klines(symbol: str, interval: str = "1d", limit: int = 500) -> List[Dict]:
        """Return OHLCV kline data for a BIST stock."""
        return get_klines(symbol, interval, limit)
