"""
Doğal Afet modu bağlamı: USGS deprem API (ücretsiz) + Reuters/BBC RSS + Tavily.
Deprem, sel, kasırga sonrası yeniden yapılanma ekonomisi ve acil ihtiyaçlar.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx
from web_arama import topla_mod_aramalari

logger = logging.getLogger(__name__)

_USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
_DEFAULT_RSS_LIST = [
    "https://feeds.reuters.com/reuters/worldNews",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
]
_TIMEOUT = 10.0

# Afet moduna özgü filtre anahtar kelimeleri — bu kelimeleri içeren başlıklar öne alınır
_AFET_ANAHTAR = [
    "earthquake", "flood", "hurricane", "typhoon", "wildfire", "tsunami",
    "tornado", "cyclone", "volcano", "landslide", "drought", "storm",
    "disaster", "emergency", "evacuation", "relief", "rebuild",
    "deprem", "sel", "kasırga", "yangın", "afet", "tsunami", "kuraklık",
]


def _zaman_satiri(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"Bugünün tarihi (bot sunucusu yerel saati): {now:%d %B %Y}."


def _son_depremler(min_magnitude: float = 5.0, limit: int = 5) -> list[str]:
    """USGS API'den son 7 günün M5+ depremlerini çek."""
    now = datetime.now(timezone.utc)
    baslangic = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    bitis = now.strftime("%Y-%m-%d")

    params = {
        "format": "geojson",
        "starttime": baslangic,
        "endtime": bitis,
        "minmagnitude": str(min_magnitude),
        "orderby": "magnitude",
        "limit": str(limit),
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.get(_USGS_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("USGS deprem API alınamadı: %s", e)
        return []

    satirlar: list[str] = []
    try:
        for feature in data.get("features", [])[:limit]:
            props = feature.get("properties", {})
            mag = props.get("mag", "?")
            yer = props.get("place", "Bilinmeyen konum")
            zaman_ms = props.get("time", 0)
            if zaman_ms:
                zaman = datetime.fromtimestamp(zaman_ms / 1000, tz=timezone.utc).strftime("%d %b %Y")
            else:
                zaman = "?"
            satirlar.append(f"- M{mag} — {yer} ({zaman})")
    except Exception as e:
        logger.warning("USGS JSON ayrıştırılamadı: %s", e)
        return []

    return satirlar


def _rss_tum_basliklar(url: str, limit: int = 15) -> list[str]:
    """Tek bir RSS url'inden tüm başlıkları çek."""
    headers = {
        "User-Agent": "MakroLensBot/1.0 (+https://t.me/)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        with httpx.Client(timeout=_TIMEOUT, headers=headers) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            text = r.text
    except Exception as e:
        logger.warning("Doğal afet RSS alınamadı (%s): %s", url, e)
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
        return []

    return titles


def _filtrele_ve_sirala(titles: list[str]) -> tuple[list[str], list[str]]:
    """Başlıkları afet-ilgili ve genel olarak ikiye ayır."""
    ilgili: list[str] = []
    genel: list[str] = []
    for t in titles:
        t_lower = t.lower()
        if any(k in t_lower for k in _AFET_ANAHTAR):
            ilgili.append(t)
        else:
            genel.append(t)
    return ilgili, genel


def topla_dogal_afet_baglami(ulke: str) -> str:
    """
    Doğal Afet modu için prompt bağlamı.
    USGS son depremler + RSS afet/dünya haberleri (filtreli).
    """
    now = datetime.now()

    # USGS depremler
    depremler = _son_depremler(min_magnitude=5.0, limit=5)
    if depremler:
        deprem_text = "Son 7 günde M5.0+ depremler (USGS):\n" + "\n".join(depremler)
    else:
        deprem_text = "Son 7 günde M5.0+ deprem kaydı yok (USGS)."

    # Tüm RSS kaynaklarından başlık topla
    rss_urls = [os.getenv("AFET_RSS_URL", "")] if os.getenv("AFET_RSS_URL") else []
    rss_urls.extend(_DEFAULT_RSS_LIST)
    rss_urls = [u for u in rss_urls if u]

    tum_basliklar: list[str] = []
    for u in rss_urls:
        basliklar = _rss_tum_basliklar(u, limit=15)
        for b in basliklar:
            if b not in tum_basliklar:
                tum_basliklar.append(b)

    # Filtrele: afet haberleri öne, genel haberler arkaya
    ilgili, genel = _filtrele_ve_sirala(tum_basliklar)

    # En fazla 5 afet haberi + 3 genel haber
    secilen = ilgili[:5] + genel[:3]

    if ilgili:
        rss_text = (
            f"Afet/kriz haberleri ({len(ilgili)} başlık bulundu):\n"
            + "\n".join([f"- {t}" for t in ilgili[:5]])
        )
        if genel[:3]:
            rss_text += "\n\nEk dünya haberleri:\n" + "\n".join([f"- {t}" for t in genel[:3]])
    elif secilen:
        rss_text = (
            "Afete özgü başlık bulunamadı — genel dünya haberleri:\n"
            + "\n".join([f"- {t}" for t in secilen])
        )
    else:
        rss_text = "Haber akışı şu an alınamadı."

    # Analiz rehberi: modelin ne araması gerektiğini söyle
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki verilerden şu soruları yanıtla:
1. DEPREM/AFET: Bağlamdaki depremler veya afet haberleri {ulke} için doğrudan veya dolaylı ekonomik risk taşıyor mu?
2. YENİDEN YAPILANMA: Etkilenen bölgelerde inşaat, sigorta, enerji altyapısı talebinde artış bekleniyor mu?
3. ACİL İHTİYAÇ: Gıda, lojistik, tıbbi malzeme gibi acil sektörlerde talep patlaması var mı?
4. TEDARİK ZİNCİRİ: Afet bölgesi {ulke} ile tedarik zinciri veya ticaret bağlantısı var mı?
5. VARLIK ETKİSİ: Deprem/afet verileri hangi emtia veya sektör ETF'ini etkiliyor?
NOT: Eğer bağlamda somut afet verisi yoksa bunu açıkça belirt ve mevcut veriden ne çıkarılabildiğini söyle."""

    parcalar = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satiri(now),
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef: deprem, sel, kasırga, yangın gibi doğal afetlerin yeniden yapılanma ekonomisine, acil ihtiyaç sektörlerine (inşaat, enerji, gıda, lojistik, sigorta) ve kısa/orta vadeli yatırım temalarına etkisini analiz etmek.",
        "### Son deprem verileri (USGS)",
        deprem_text,
        "### Güncel haber başlıkları",
        rss_text,
    ]

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("dogal_afet", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    parcalar.append(analiz_rehberi)
    return "\n".join(parcalar)
