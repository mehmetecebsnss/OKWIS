"""
Jeopolitik modu bağlamı: son dönem haber başlıkları (RSS) + Tavily web araması.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx
from web_arama import topla_mod_aramalari

logger = logging.getLogger(__name__)

_DEFAULT_RSS = "https://feeds.reuters.com/reuters/worldNews"
_BBC_RSS = "https://feeds.bbci.co.uk/news/world/rss.xml"
_RSS_TIMEOUT = 10.0

# Jeopolitik moduna özgü filtre anahtar kelimeleri
_JEO_ANAHTAR = [
    # Çatışma/güvenlik
    "war", "conflict", "attack", "military", "troops", "missile", "bomb",
    "ceasefire", "peace", "nato", "defense", "sanction", "weapon",
    # Diplomasi/siyaset
    "summit", "treaty", "election", "president", "minister", "government",
    "diplomatic", "embassy", "alliance", "agreement",
    # Enerji/ticaret jeopolitiği
    "oil", "gas", "pipeline", "trade", "tariff", "embargo", "supply",
    "opec", "lng", "energy",
    # Bölgesel
    "ukraine", "russia", "china", "taiwan", "iran", "israel", "middle east",
    "north korea", "india", "pakistan",
    # Türkçe
    "savaş", "çatışma", "yaptırım", "anlaşma", "seçim", "hükümet",
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
        logger.warning("Jeopolitik RSS alınamadı (%s): %s", url, e)
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
        logger.warning("Jeopolitik RSS XML ayrıştırılamadı: %s", url)
        return []

    return titles


def _filtrele_ve_sirala(titles: list[str]) -> tuple[list[str], list[str]]:
    """Başlıkları jeopolitik-ilgili ve genel olarak ikiye ayır."""
    ilgili: list[str] = []
    genel: list[str] = []
    for t in titles:
        t_lower = t.lower()
        if any(k in t_lower for k in _JEO_ANAHTAR):
            ilgili.append(t)
        else:
            genel.append(t)
    return ilgili, genel


def _env_geo_rss_listesini_oku() -> list[str]:
    out: list[str] = []
    raw_list = (os.getenv("GEO_RSS_URLS") or "").strip()
    if raw_list:
        for p in raw_list.split(","):
            u = p.strip()
            if u:
                out.append(u)
    tek = (os.getenv("GEO_RSS_URL") or "").strip()
    if tek:
        out.append(tek)
    seen: set[str] = set()
    return [u for u in out if not (u in seen or seen.add(u))]


def topla_jeopolitik_baglami(ulke: str) -> str:
    """
    Jeopolitik modu için prompt bağlamı.
    Tüm kaynaklardan başlık topla, jeopolitik sinyal taşıyanları öne al.
    """
    rss_urls: list[str] = _env_geo_rss_listesini_oku()
    rss_urls.extend([_DEFAULT_RSS, _BBC_RSS])

    seen: set[str] = set()
    rss_urls = [u for u in rss_urls if not (u in seen or seen.add(u))]

    # Tüm kaynaklardan başlık topla
    tum_basliklar: list[str] = []
    for u in rss_urls:
        basliklar = _rss_tum_basliklar(u, limit=15)
        for b in basliklar:
            if b not in tum_basliklar:
                tum_basliklar.append(b)

    # Filtrele: jeopolitik haberler öne
    ilgili, genel = _filtrele_ve_sirala(tum_basliklar)

    if ilgili:
        baslik_text = (
            f"Jeopolitik sinyal taşıyan haberler ({len(ilgili)} başlık):\n"
            + "\n".join([f"- {t}" for t in ilgili[:8]])
        )
        if genel[:3]:
            baslik_text += "\n\nEk dünya haberleri:\n" + "\n".join([f"- {t}" for t in genel[:3]])
    elif tum_basliklar:
        baslik_text = (
            "Güncel dünya haberleri:\n"
            + "\n".join([f"- {t}" for t in tum_basliklar[:10]])
        )
    else:
        baslik_text = "Jeopolitik haber akışından başlık çıkarılamadı (ağ/kaynak geçici olabilir)."

    # Analiz rehberi
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki haberlerden şu soruları yanıtla:
1. JEOPOLİTİK RİSK: Bağlamdaki en kritik jeopolitik gelişme hangisi? Risk artıyor mu azalıyor mu?
2. ENERJİ/TİCARET KANALI: Bu gelişme enerji fiyatlarını, ticaret güzergahlarını veya tedarik zincirini nasıl etkiliyor?
3. SAVUNMA/GÜVENLİK: Çatışma veya gerilim haberleri savunma sektörünü nasıl etkiliyor?
4. {ulke.upper()} ETKİSİ: Bu jeopolitik gelişme {ulke}'yi doğrudan veya dolaylı nasıl etkiliyor?
5. VARLIK ETKİSİ: Jeopolitik riskten kazanan/kaybeden varlıklar neler? (altın, petrol, savunma hisseleri, döviz)
NOT: Her çıkarım bağlamdaki somut bir habere dayandırılmalı. Bağlamda olmayan jeopolitik gelişmeleri uydurma."""

    parcalar: list[str] = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satiri(),
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef: haber başlıklarından yola çıkarak jeopolitik kanalların (enerji/emtia, ticaret/lojistik, savunma, yaptırımlar) makro ve sektör etkisini analiz etmek.",
        "### Jeopolitik haber başlıkları",
        baslik_text,
    ]

    # Tavily web araması — RSS'in ötesinde canlı veri
    tavily_blok = topla_mod_aramalari("jeopolitik", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    return "\n".join(parcalar)
