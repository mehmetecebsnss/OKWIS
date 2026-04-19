"""
Magazin / Viral Haberler modu bağlamı: entertainment + viral haber RSS + Tavily.
Ünlü-marka ilişkileri, viral olayların şirket değerlemelerine kısa vadeli etkisi.
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
    "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.reuters.com/reuters/entertainment",
    "https://feeds.bbci.co.uk/news/rss.xml",
]
_RSS_TIMEOUT = 10.0

# Magazin/viral moduna özgü filtre anahtar kelimeleri
_MAGAZIN_ANAHTAR = [
    "celebrity", "viral", "brand", "scandal", "boycott", "influencer",
    "social media", "trending", "star", "actor", "singer", "artist",
    "movie", "film", "music", "album", "award", "oscar", "grammy",
    "lawsuit", "controversy", "deal", "partnership", "endorsement",
    "ünlü", "viral", "marka", "skandal", "boykot", "sosyal medya",
    "film", "müzik", "ödül", "anlaşma", "reklam",
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
        logger.warning("Magazin RSS alınamadı (%s): %s", url, e)
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
        logger.warning("Magazin RSS XML ayrıştırılamadı: %s", url)
        return []

    return titles


def _filtrele_ve_sirala(titles: list[str]) -> tuple[list[str], list[str]]:
    """Başlıkları magazin-ilgili ve genel olarak ikiye ayır."""
    ilgili: list[str] = []
    genel: list[str] = []
    for t in titles:
        t_lower = t.lower()
        if any(k in t_lower for k in _MAGAZIN_ANAHTAR):
            ilgili.append(t)
        else:
            genel.append(t)
    return ilgili, genel


def _env_rss_listesini_oku() -> list[str]:
    out: list[str] = []
    raw = (os.getenv("MAGAZIN_RSS_URLS") or "").strip()
    if raw:
        for p in raw.split(","):
            u = p.strip()
            if u:
                out.append(u)
    tek = (os.getenv("MAGAZIN_RSS_URL") or "").strip()
    if tek:
        out.append(tek)
    seen: set[str] = set()
    return [u for u in out if not (u in seen or seen.add(u))]


def topla_magazin_baglami(ulke: str) -> str:
    """
    Magazin / Viral modu için prompt bağlamı.
    Tüm kaynaklardan başlık topla, magazin-ilgilileri öne al.
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

    # Filtrele: magazin haberleri öne, genel haberler arkaya
    ilgili, genel = _filtrele_ve_sirala(tum_basliklar)

    if ilgili:
        baslik_text = (
            f"Magazin/viral haberler ({len(ilgili)} başlık bulundu):\n"
            + "\n".join([f"- {t}" for t in ilgili[:7]])
        )
        if genel[:3]:
            baslik_text += "\n\nEk genel haberler:\n" + "\n".join([f"- {t}" for t in genel[:3]])
    elif tum_basliklar:
        baslik_text = (
            "Magazine özgü başlık bulunamadı — mevcut haberler:\n"
            + "\n".join([f"- {t}" for t in tum_basliklar[:8]])
        )
    else:
        baslik_text = "Magazin haber akışından başlık çıkarılamadı (ağ/kaynak geçici olabilir)."

    # Analiz rehberi
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki haberlerden şu soruları yanıtla:
1. VİRAL OLAY: Bağlamdaki en dikkat çekici ünlü/marka/viral olay hangisi? Hangi şirketi etkiliyor?
2. MARKA ETKİSİ: Bu olay ilgili şirketin hisse fiyatını, satışlarını veya marka değerini nasıl etkiler?
3. KISA VADE: Viral etki 1-2 hafta içinde piyasaya yansır mı? Hangi hisse/sektör?
4. UZUN VADE: Bu olay kalıcı bir marka değeri değişimi mi, yoksa geçici viral mi?
5. SOMUT FIRSAT: Bağlamdaki haberlerden {ulke} piyasasında somut bir al/izle/kaçın sinyali var mı?
NOT: Eğer bağlamda somut magazin/viral haber yoksa bunu açıkça belirt. Uydurma haber ekleme."""

    parcalar: list[str] = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satiri(),
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef: ünlü-marka ilişkileri, viral sosyal medya olayları ve eğlence haberlerinin şirket değerlemelerine, tüketici davranışına ve kısa vadeli spekülatif piyasa hareketlerine etkisini analiz etmek.",
        "### Güncel magazin ve viral haberler",
        baslik_text,
    ]

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("magazin", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    parcalar.append(analiz_rehberi)
    return "\n".join(parcalar)
