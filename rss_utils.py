"""
RSS Utility Functions - Fallback mekanizması ile güvenli RSS okuma
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_RSS_TIMEOUT = 10.0
_MAX_RETRIES = 2


def fetch_rss_titles(
    url: str,
    limit: int = 15,
    fallback_urls: list[str] | None = None,
) -> tuple[list[str], str | None]:
    """
    RSS feed'den başlıkları çek, hata durumunda fallback URL'leri dene.
    
    Args:
        url: Ana RSS feed URL'i
        limit: Maksimum başlık sayısı
        fallback_urls: Hata durumunda denenecek alternatif URL'ler
    
    Returns:
        (başlık listesi, kullanılan URL veya None)
    """
    urls_to_try = [url]
    if fallback_urls:
        urls_to_try.extend(fallback_urls)
    
    for attempt_url in urls_to_try:
        titles = _fetch_single_rss(attempt_url, limit)
        if titles:
            if attempt_url != url:
                logger.info(
                    "RSS fallback başarılı: %s (ana: %s başarısız)",
                    attempt_url[:50],
                    url[:50],
                )
            return titles, attempt_url
    
    logger.error("Tüm RSS kaynakları başarısız: %s", url)
    return [], None


def _fetch_single_rss(url: str, limit: int) -> list[str]:
    """Tek bir RSS URL'inden başlıkları çek."""
    headers = {
        "User-Agent": "MakroLensBot/1.0 (+https://t.me/okwis_ai_bot)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    
    try:
        with httpx.Client(timeout=_RSS_TIMEOUT, headers=headers) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            text = r.text
    except httpx.TimeoutException:
        logger.warning("RSS timeout: %s", url[:50])
        return []
    except httpx.HTTPStatusError as e:
        logger.warning("RSS HTTP error %s: %s", e.response.status_code, url[:50])
        return []
    except Exception as e:
        logger.warning("RSS fetch error (%s): %s", url[:50], e)
        return []
    
    return _parse_rss_xml(text, url, limit)


def _parse_rss_xml(xml_text: str, url: str, limit: int) -> list[str]:
    """RSS XML'ini parse et ve başlıkları çıkar."""
    titles: list[str] = []
    
    try:
        root = ET.fromstring(xml_text)
        
        # RSS 2.0 format
        for item in root.findall(".//item"):
            if len(titles) >= limit:
                break
            title_el = item.find("title")
            if title_el is not None and title_el.text and title_el.text.strip():
                titles.append(title_el.text.strip()[:220])
        
        # Atom format fallback
        if not titles:
            # Atom namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                if len(titles) >= limit:
                    break
                title_el = entry.find("atom:title", ns)
                if title_el is not None and title_el.text and title_el.text.strip():
                    titles.append(title_el.text.strip()[:220])
    
    except ET.ParseError as e:
        logger.warning("RSS XML parse error (%s): %s", url[:50], e)
        return []
    
    return titles


# Yaygın RSS fallback URL'leri
FALLBACK_RSS_SOURCES = {
    "world_news": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/xml/rss-en-all",
    ],
    "business": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.ft.com/?format=rss",
    ],
    "technology": [
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.wired.com/feed/rss",
        "https://techcrunch.com/feed/",
    ],
    "entertainment": [
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://www.hollywoodreporter.com/feed/",
        "https://variety.com/feed/",
    ],
}


def get_fallback_urls(category: str) -> list[str]:
    """Kategori için fallback URL'leri al."""
    return FALLBACK_RSS_SOURCES.get(category, [])
