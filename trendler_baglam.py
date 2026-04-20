"""
Dünya Trendleri modu bağlamı: BBC / NYT RSS + Tavily.
Viral olaylar, sosyal medya trendleri ve dünya gündeminin piyasa yansıması.
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
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]
_RSS_TIMEOUT = 10.0

# Trendler moduna özgü filtre anahtar kelimeleri — trend/viral sinyal taşıyan başlıklar öne alınır
_TREND_ANAHTAR = [
    # Teknoloji trendleri
    "ai", "artificial intelligence", "chatgpt", "openai", "robot", "automation",
    "crypto", "bitcoin", "blockchain", "metaverse", "vr", "ar",
    # Sosyal trendler
    "viral", "trending", "social media", "tiktok", "instagram", "youtube",
    "protest", "movement", "generation", "youth", "culture",
    # Ekonomik trendler
    "inflation", "recession", "growth", "unemployment", "housing",
    "remote work", "gig economy", "startup",
    # Çevre/iklim trendleri
    "climate", "green", "sustainable", "carbon", "electric",
    # Sağlık trendleri
    "pandemic", "vaccine", "mental health", "wellness",
    # Türkçe
    "trend", "viral", "sosyal medya", "yapay zeka", "kripto",
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
        logger.warning("Trendler RSS alınamadı (%s): %s", url, e)
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
        logger.warning("Trendler RSS XML ayrıştırılamadı: %s", url)
        return []

    return titles


def _filtrele_ve_sirala(titles: list[str]) -> tuple[list[str], list[str]]:
    """Başlıkları trend-ilgili ve genel olarak ikiye ayır."""
    ilgili: list[str] = []
    genel: list[str] = []
    for t in titles:
        t_lower = t.lower()
        if any(k in t_lower for k in _TREND_ANAHTAR):
            ilgili.append(t)
        else:
            genel.append(t)
    return ilgili, genel


def _env_rss_listesini_oku() -> list[str]:
    out: list[str] = []
    raw = (os.getenv("TREND_RSS_URLS") or "").strip()
    if raw:
        for p in raw.split(","):
            u = p.strip()
            if u:
                out.append(u)
    tek = (os.getenv("TREND_RSS_URL") or "").strip()
    if tek:
        out.append(tek)
    seen: set[str] = set()
    return [u for u in out if not (u in seen or seen.add(u))]


def topla_trendler_baglami(ulke: str) -> str:
    """
    Dünya Trendleri modu için prompt bağlamı.
    Tüm kaynaklardan başlık topla, trend sinyali taşıyanları öne al.
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

    # Filtrele: trend haberleri öne
    ilgili, genel = _filtrele_ve_sirala(tum_basliklar)

    if ilgili:
        baslik_text = (
            f"Trend/viral sinyal taşıyan haberler ({len(ilgili)} başlık):\n"
            + "\n".join([f"- {t}" for t in ilgili[:7]])
        )
        if genel[:4]:
            baslik_text += "\n\nDünya gündemi:\n" + "\n".join([f"- {t}" for t in genel[:4]])
    elif tum_basliklar:
        baslik_text = (
            "Şu an dünya gündemindeki öne çıkan başlıklar:\n"
            + "\n".join([f"- {t}" for t in tum_basliklar[:10]])
        )
    else:
        baslik_text = "Dünya trend akışından başlık çıkarılamadı (ağ/kaynak geçici olabilir)."

    # Analiz rehberi
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki haberlerden şu soruları yanıtla:
1. TREND TESPİTİ: Bağlamdaki haberler hangi küresel trendi işaret ediyor? Bu trend yapısal mı viral mı?
2. TÜKETİCİ DAVRANIŞI: Bu trend tüketici tercihlerini, teknoloji benimsemesini veya yaşam tarzını nasıl değiştiriyor?
3. PIYASA YANSIMASI: Bu trend {ulke} piyasasında hangi sektörü veya şirketi etkiliyor?
4. ZAMANLAMA: Trend kısa vadeli (1-2 hafta) mi yoksa uzun vadeli (3-12 ay) mi?
5. SOMUT FIRSAT: Bağlamdaki trend haberlerinden {ulke} için somut bir yatırım sinyali çıkıyor mu?
NOT: Her çıkarım bağlamdaki somut bir habere dayandırılmalı. Bağlamda olmayan trendleri uydurma."""

    parcalar: list[str] = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satiri(),
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef: güncel dünya gündemi ve viral olayların (sosyal medya trendleri, viral haberler, kültürel olaylar) kısa vadeli piyasa ve tüketici davranışına yansımasını analiz etmek.",
        "### Güncel dünya gündemi ve trend haberleri",
        baslik_text,
    ]

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("trendler", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    return "\n".join(parcalar)
