"""
Sektör Trendleri modu bağlamı: BBC business / Technology RSS + Tavily.
Yükselen/düşen sektörlerin öncü sinyalleri, uzun vadeli büyüme temaları.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx
from web_arama import topla_mod_aramalari

logger = logging.getLogger(__name__)

_DEFAULT_RSS_LIST = [
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
]
_RSS_TIMEOUT = 10.0

# Sektör moduna özgü filtre anahtar kelimeleri — sektörel sinyal taşıyan başlıklar öne alınır
_SEKTOR_ANAHTAR = [
    # Teknoloji
    "ai", "artificial intelligence", "chip", "semiconductor", "cloud", "software",
    "tech", "startup", "ipo", "acquisition", "merger",
    # Enerji
    "oil", "gas", "energy", "solar", "wind", "battery", "ev", "electric vehicle",
    "opec", "renewable",
    # Finans
    "bank", "interest rate", "fed", "inflation", "earnings", "profit", "revenue",
    "stock", "market", "fund", "investment",
    # Sağlık
    "pharma", "drug", "fda", "clinical", "biotech", "health",
    # Tüketim
    "retail", "consumer", "sales", "ecommerce", "amazon", "walmart",
    # Sanayi
    "manufacturing", "supply chain", "logistics", "shipping", "trade",
    # Türkçe
    "sektör", "şirket", "yatırım", "büyüme", "kâr", "gelir", "ihracat",
]


def _zaman_satiri(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"Bugünün tarihi (bot sunucusu yerel saati): {now:%d %B %Y}."


def _rss_tum_basliklar(url: str, limit: int = 15) -> list[str]:
    """Tek bir RSS url'inden tüm başlıkları çek."""
    headers = {
        "User-Agent": "MakroLensBot/1.0 (+https://t.me/)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        with httpx.Client(timeout=_RSS_TIMEOUT, headers=headers) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            text = r.text
    except Exception as e:
        logger.warning("Sektör RSS alınamadı (%s): %s", url, e)
        return []

    titles: list[str] = []
    try:
        root = ET.fromstring(text)
        for item in root.findall(".//item"):
            if len(titles) >= limit:
                break
            el = item.find("title")
            if el is not None and el.text and el.text.strip():
                titles.append(el.text.strip()[:220])
    except ET.ParseError:
        logger.warning("Sektör RSS XML ayrıştırılamadı: %s", url)
        return []

    return titles


def _filtrele_ve_sirala(titles: list[str]) -> tuple[list[str], list[str]]:
    """Başlıkları sektör-ilgili ve genel olarak ikiye ayır."""
    ilgili: list[str] = []
    genel: list[str] = []
    for t in titles:
        t_lower = t.lower()
        if any(k in t_lower for k in _SEKTOR_ANAHTAR):
            ilgili.append(t)
        else:
            genel.append(t)
    return ilgili, genel


def _env_rss_listesini_oku() -> list[str]:
    out: list[str] = []
    raw = (os.getenv("SEKTOR_RSS_URLS") or "").strip()
    if raw:
        for p in raw.split(","):
            u = p.strip()
            if u:
                out.append(u)
    tek = (os.getenv("SEKTOR_RSS_URL") or "").strip()
    if tek:
        out.append(tek)
    seen: set[str] = set()
    return [u for u in out if not (u in seen or seen.add(u))]


def topla_sektor_baglami(ulke: str) -> str:
    """
    Sektör Trendleri modu için prompt bağlamı.
    Tüm kaynaklardan başlık topla, sektörel sinyal taşıyanları öne al.
    """
    rss_urls = _env_rss_listesini_oku()
    rss_urls.extend(_DEFAULT_RSS_LIST)

    seen: set[str] = set()
    rss_urls = [u for u in rss_urls if not (u in seen or seen.add(u))]

    # Tüm kaynaklardan başlık topla
    tum_basliklar: list[str] = []
    for u in rss_urls:
        basliklar = _rss_tum_basliklar(u, limit=15)
        for b in basliklar:
            if b not in tum_basliklar:
                tum_basliklar.append(b)

    # Filtrele: sektörel haberler öne
    ilgili, genel = _filtrele_ve_sirala(tum_basliklar)

    if ilgili:
        baslik_text = (
            f"Sektörel sinyal taşıyan haberler ({len(ilgili)} başlık):\n"
            + "\n".join([f"- {t}" for t in ilgili[:8]])
        )
        if genel[:3]:
            baslik_text += "\n\nEk haberler:\n" + "\n".join([f"- {t}" for t in genel[:3]])
    elif tum_basliklar:
        baslik_text = (
            "Güncel iş dünyası ve sektör haberleri:\n"
            + "\n".join([f"- {t}" for t in tum_basliklar[:10]])
        )
    else:
        baslik_text = "Sektör haber akışından başlık çıkarılamadı (ağ/kaynak geçici olabilir)."

    # Analiz rehberi
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki haberlerden şu soruları yanıtla:
1. SEKTÖREL MOMENTUM: Bağlamdaki haberler hangi sektörün ivme kazandığını gösteriyor? Hangi sektör gerileme sinyali veriyor?
2. ŞİRKET SİNYALİ: Hangi şirket haberi tek bir şirketi değil, tüm sektörü temsil ediyor?
3. KISA VADE: Bu sektörel momentum 1-2 hafta içinde {ulke} piyasasına nasıl yansır?
4. UZUN VADE: Bu haberler 3-5 yıllık yapısal bir büyüme temasını mı işaret ediyor?
5. SOMUT FIRSAT: {ulke} piyasasından sektörel kazanan 3 şirket/varlık — bağlamdaki hangi habere dayanıyor?
NOT: Her çıkarım bağlamdaki somut bir habere dayandırılmalı. Bağlamda olmayan sektörel gelişmeleri uydurma."""

    parcalar: list[str] = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satiri(),
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef: güncel iş dünyası ve teknoloji haberlerinden yola çıkarak yükselen/düşen sektörlerin öncü sinyallerini tespit etmek; 3-5 yıllık büyüme temalarını ve kısa vadeli sektörel momentumu analiz etmek.",
        "### Güncel sektör ve iş dünyası haberleri",
        baslik_text,
    ]

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("sektor", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    return "\n".join(parcalar)
