"""
Jeopolitik modu bağlamı: son dönem haber başlıkları (RSS) + ülkeye bağlama çerçevesi.

Not: Bu mod yalnızca bağlam sağlar; analiz metnini LLM üretir.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_RSS = "https://feeds.reuters.com/reuters/worldNews"
_BBC_RSS = "https://feeds.bbci.co.uk/news/world/rss.xml"
_RSS_TIMEOUT = 10.0


def _zaman_satiri(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"Bugünün tarihi (bot sunucusu yerel saati): {now:%d %B %Y}."


def _rss_basliklari_ozet(url: str, limit: int = 8) -> str:
    headers = {
        "User-Agent": "MakroLensBot/1.0 (+https://t.me/)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    try:
        with httpx.Client(timeout=_RSS_TIMEOUT, headers=headers) as client:
            # Bazı kaynaklar kısa link / yönlendirme (302) döndürüyor; takip ederek gerçek RSS'e ulaşalım.
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            text = r.text
    except Exception as e:
        logger.warning("Jeopolitik RSS alınamadı (%s): %s", url, e)
        return "Jeopolitik haber akışı şu an alınamadı (ağ veya kaynak geçici)."

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
        return "Jeopolitik haber akışı ayrıştırılamadı."

    if not titles:
        return "Jeopolitik haber akışından başlık çıkarılamadı."

    satirlar = [f"- {t}" for t in titles]
    return (
        "Son dönemden örnek jeopolitik haber başlıkları (özet, yatırım tavsiyesi değil):\n"
        + "\n".join(satirlar)
    )


def _rss_basliklari_list(url: str, limit: int = 8) -> list[str]:
    """Tek bir RSS url’inden başlık listesi çıkar; olmazsa boş liste döner."""
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


def _env_geo_rss_listesini_oku() -> list[str]:
    """
    .env desteği:
    - GEO_RSS_URLS=url1,url2,url3 (önerilen)
    - GEO_RSS_URL=url1 (geri uyum)
    """
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
    Gemini/DeepSeek prompt’una eklenecek tek metin bloğu.
    (1) Zaman satırı
    (2) Ülke hedefi
    (3) RSS başlıkları
    """

    # Kullanıcı GEO_RSS_URLS/GEO_RSS_URL ile override edebilir; sonra fallback Reuters/BBC.
    rss_urls: list[str] = _env_geo_rss_listesini_oku()
    rss_urls.extend([_DEFAULT_RSS, _BBC_RSS])

    # Dedup (koruyarak)
    seen: set[str] = set()
    rss_urls = [u for u in rss_urls if not (u in seen or seen.add(u))]

    titles: list[str] = []
    for u in rss_urls:
        titles = _rss_basliklari_list(u, limit=8)
        if titles:
            break

    if titles:
        baslik_text = (
            "Son dönemden örnek jeopolitik haber başlıkları (özet, yatırım tavsiyesi değil):\n"
            + "\n".join([f"- {t}" for t in titles])
        )
    else:
        baslik_text = "Jeopolitik haber akışından başlık çıkarılamadı (ağ/kaynak geçici olabilir)."

    parcalar: list[str] = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satiri(),
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef, haber başlıklarından yola çıkarak jeopolitik kanalların (enerji/emtia, ticaret/lojistik, savunma, yaptırımlar) makro ve sektör etkisini dolaylama.",
        "### Jeopolitik haber başlıkları",
        baslik_text,
    ]

    return "\n".join(parcalar)

