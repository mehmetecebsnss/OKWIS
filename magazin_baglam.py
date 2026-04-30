"""
Magazin / Viral Haberler modu bağlamı: entertainment + viral haber RSS + Tavily.
Ünlü-marka ilişkileri, viral olayların şirket değerlemelerine kısa vadeli etkisi.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
from web_arama import topla_mod_aramalari
from rss_utils import fetch_rss_titles, get_fallback_urls

logger = logging.getLogger(__name__)

_DEFAULT_RSS_LIST = [
    "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
]
_RSS_TIMEOUT = 10.0
_ULKE_RSS_PATH = Path(__file__).resolve().parent / "data" / "ulke_rss_kaynaklari.json"

# Magazin/viral moduna özgü filtre anahtar kelimeleri
_MAGAZIN_ANAHTAR = [
    "celebrity", "viral", "brand", "scandal", "boycott", "influencer",
    "social media", "trending", "star", "actor", "singer", "artist",
    "movie", "film", "music", "album", "award", "oscar", "grammy",
    "lawsuit", "controversy", "deal", "partnership", "endorsement",
    "ünlü", "viral", "marka", "skandal", "boykot", "sosyal medya",
    "film", "müzik", "ödül", "anlaşma", "reklam",
]


def _ulke_rss_yukle() -> dict:
    """Ülkeye özel RSS kaynaklarını yükle."""
    try:
        with open(_ULKE_RSS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Ülke RSS kaynakları yüklenemedi: %s", e)
        return {}


def _ulke_rss_al(ulke: str, kategori: str = "magazin") -> list[str]:
    """
    Ülkeye özel RSS feed'lerini al.
    
    Args:
        ulke: Ülke adı (örn: "Türkiye", "ABD", "Japonya")
        kategori: RSS kategorisi ("magazin", "genel", "teknoloji")
    
    Returns:
        RSS URL listesi
    """
    rss_data = _ulke_rss_yukle()
    
    # Ülkeye özel RSS'ler
    if ulke in rss_data:
        feeds = rss_data[ulke].get(kategori, [])
        if feeds:
            logger.info("Ülkeye özel RSS kullanılıyor: %s (%s) - %d feed", ulke, kategori, len(feeds))
            return feeds
    
    # Default RSS'ler
    default_feeds = rss_data.get("DEFAULT", {}).get(kategori, [])
    if default_feeds:
        logger.info("Default RSS kullanılıyor: %s - %d feed", kategori, len(default_feeds))
        return default_feeds
    
    # Hiçbiri yoksa hardcoded default
    logger.warning("RSS bulunamadı, hardcoded default kullanılıyor")
    return _DEFAULT_RSS_LIST


def _zaman_satiri(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"Bugünün tarihi (bot sunucusu yerel saati): {now:%d %B %Y}."


def _rss_tum_basliklar(url: str, limit: int = 15) -> list[str]:
    """Tek bir RSS url'inden tüm başlıkları çek (fallback ile)."""
    fallback_urls = get_fallback_urls("entertainment")
    titles, used_url = fetch_rss_titles(url, limit, fallback_urls)
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
    Ülkeye özel RSS kaynaklarından başlık topla, magazin-ilgilileri öne al.
    
    Args:
        ulke: Ülke adı (örn: "Türkiye", "ABD", "Japonya")
    """
    # Ülkeye özel RSS feed'leri al
    rss_urls = _ulke_rss_al(ulke, "magazin")
    
    # Env'den ek RSS'ler varsa ekle
    env_rss = _env_rss_listesini_oku()
    if env_rss:
        rss_urls.extend(env_rss)
    
    # Tekrar eden URL'leri temizle
    seen: set[str] = set()
    rss_urls = [u for u in rss_urls if not (u in seen or seen.add(u))]
    
    logger.info("Magazin bağlamı: %s için %d RSS feed kullanılıyor", ulke, len(rss_urls))

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
            f"Magazin/viral haberler ({len(ilgili)} başlık bulundu - {ulke} kaynakları):\n"
            + "\n".join([f"- {t}" for t in ilgili[:7]])
        )
        if genel[:3]:
            baslik_text += "\n\nEk genel haberler:\n" + "\n".join([f"- {t}" for t in genel[:3]])
    elif tum_basliklar:
        baslik_text = (
            f"Magazine özgü başlık bulunamadı — {ulke} mevcut haberleri:\n"
            + "\n".join([f"- {t}" for t in tum_basliklar[:8]])
        )
    else:
        baslik_text = f"Magazin haber akışından başlık çıkarılamadı ({ulke} kaynakları geçici olabilir)."

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
        f"Haber kaynakları: {ulke}'ye özel magazin ve eğlence RSS feed'leri.",
        "Bu modda hedef: ünlü-marka ilişkileri, viral sosyal medya olayları ve eğlence haberlerinin şirket değerlemelerine, tüketici davranışına ve kısa vadeli spekülatif piyasa hareketlerine etkisini analiz etmek.",
        "### Güncel magazin ve viral haberler",
        baslik_text,
    ]

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("magazin", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    return "\n".join(parcalar)
