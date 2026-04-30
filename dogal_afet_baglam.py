"""
Doğal Afet modu bağlamı: USGS deprem API (ücretsiz) + BBC RSS + Tavily.
Deprem, sel, kasırga sonrası yeniden yapılanma ekonomisi ve acil ihtiyaçlar.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx
from web_arama import topla_mod_aramalari
from rss_utils import fetch_rss_titles, get_fallback_urls

logger = logging.getLogger(__name__)

_USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
_DEFAULT_RSS_LIST = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
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
    """Tek bir RSS url'inden tüm başlıkları çek (fallback ile)."""
    fallback_urls = get_fallback_urls("world_news")
    titles, used_url = fetch_rss_titles(url, limit, fallback_urls)
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


def _ulke_afet_profili(ulke: str) -> str:
    """Ülkenin afet risk profili ve geçmiş trend bilgisi."""
    # Ülke bazlı afet risk profilleri
    ULKE_AFET_PROFIL = {
        "Türkiye": {
            "risk": "YÜKSEK",
            "ana_afetler": ["Deprem", "Sel", "Orman yangını"],
            "aktif_fay": "Kuzey Anadolu Fay Hattı, Doğu Anadolu Fay Hattı",
            "son_buyuk": "6 Şubat 2023 Kahramanmaraş depremleri (M7.8, M7.5)",
            "ekonomik_sektor": ["İnşaat", "Sigorta", "Çimento", "Çelik", "Altyapı"],
            "hazirlik": "Deprem yönetmeliği güncellendi, zorunlu deprem sigortası (DASK) var",
        },
        "Japonya": {
            "risk": "ÇOK YÜKSEK",
            "ana_afetler": ["Deprem", "Tsunami", "Tayfun", "Volkan"],
            "aktif_fay": "Pasifik Ateş Çemberi, Nankai Çukuru",
            "son_buyuk": "11 Mart 2011 Tōhoku depremi ve tsunamisi (M9.1)",
            "ekonomik_sektor": ["Depreme dayanıklı teknoloji", "Sigorta", "İnşaat", "Erken uyarı sistemleri"],
            "hazirlik": "Dünyanın en gelişmiş deprem erken uyarı sistemi, zorunlu bina standartları",
        },
        "ABD": {
            "risk": "YÜKSEK",
            "ana_afetler": ["Deprem (Kaliforniya)", "Kasırga (Güney)", "Tornado (Orta)", "Orman yangını (Batı)"],
            "aktif_fay": "San Andreas Fayı, Cascadia Subdüksiyon Zonu",
            "son_buyuk": "1994 Northridge depremi (M6.7), 2005 Kasırga Katrina",
            "ekonomik_sektor": ["Sigorta", "İnşaat", "Acil yardım", "Yeniden yapılanma"],
            "hazirlik": "FEMA (Federal Acil Durum Yönetimi), eyalet bazlı hazırlık planları",
        },
        "Çin": {
            "risk": "YÜKSEK",
            "ana_afetler": ["Deprem", "Sel", "Tayfun", "Heyelan"],
            "aktif_fay": "Longmenshan Fayı, Himalaya bölgesi",
            "son_buyuk": "12 Mayıs 2008 Sichuan depremi (M7.9)",
            "ekonomik_sektor": ["Altyapı", "İnşaat", "Çimento", "Çelik", "Sigorta"],
            "hazirlik": "Ulusal deprem izleme ağı, zorunlu bina standartları",
        },
        "Endonezya": {
            "risk": "ÇOK YÜKSEK",
            "ana_afetler": ["Deprem", "Tsunami", "Volkan", "Sel"],
            "aktif_fay": "Pasifik Ateş Çemberi, Sunda Megathrust",
            "son_buyuk": "2004 Hint Okyanusu depremi ve tsunamisi (M9.1)",
            "ekonomik_sektor": ["Yeniden yapılanma", "Acil yardım", "Sigorta", "Altyapı"],
            "hazirlik": "Tsunami erken uyarı sistemi, uluslararası yardım protokolleri",
        },
        "İtalya": {
            "risk": "ORTA-YÜKSEK",
            "ana_afetler": ["Deprem", "Volkan (Vezüv, Etna)", "Sel"],
            "aktif_fay": "Apenin Dağları fay sistemi",
            "son_buyuk": "2016 Orta İtalya depremleri (M6.2)",
            "ekonomik_sektor": ["Tarihi yapı restorasyonu", "Sigorta", "Turizm altyapısı"],
            "hazirlik": "AB afet yönetimi, ulusal sivil savunma sistemi",
        },
        "Meksika": {
            "risk": "YÜKSEK",
            "ana_afetler": ["Deprem", "Kasırga", "Volkan"],
            "aktif_fay": "Cocos Levhası subdüksiyonu, Trans-Meksika Volkanik Kuşağı",
            "son_buyuk": "19 Eylül 2017 Puebla depremi (M7.1)",
            "ekonomik_sektor": ["İnşaat", "Sigorta", "Acil yardım", "Altyapı"],
            "hazirlik": "Deprem erken uyarı sistemi (SASMEX), zorunlu bina kodları",
        },
        "Şili": {
            "risk": "ÇOK YÜKSEK",
            "ana_afetler": ["Deprem", "Tsunami", "Volkan"],
            "aktif_fay": "Nazca Levhası subdüksiyonu",
            "son_buyuk": "27 Şubat 2010 Maule depremi (M8.8)",
            "ekonomik_sektor": ["Madencilik altyapısı", "Sigorta", "İnşaat", "Liman yenileme"],
            "hazirlik": "Sıkı bina standartları, tsunami erken uyarı sistemi",
        },
    }
    
    profil = ULKE_AFET_PROFIL.get(ulke)
    if not profil:
        return f"{ulke} için detaylı afet profili mevcut değil, ancak genel risk analizi yapılabilir."
    
    return f"""
**{ulke} Afet Risk Profili:**
• Risk Seviyesi: {profil['risk']}
• Ana Afet Türleri: {', '.join(profil['ana_afetler'])}
• Aktif Fay/Bölge: {profil['aktif_fay']}
• Son Büyük Afet: {profil['son_buyuk']}
• Ekonomik Sektörler: {', '.join(profil['ekonomik_sektor'])}
• Hazırlık Durumu: {profil['hazirlik']}
"""


def topla_dogal_afet_baglami(ulke: str) -> str:
    """
    Doğal Afet modu için prompt bağlamı.
    USGS son depremler + RSS afet/dünya haberleri (filtreli).
    Deprem yoksa alternatif risk analizi sağla.
    """
    now = datetime.now()

    # USGS depremler
    depremler = _son_depremler(min_magnitude=5.0, limit=5)
    if depremler:
        deprem_text = "Son 7 günde M5.0+ depremler (USGS):\n" + "\n".join(depremler)
        deprem_yok = False
    else:
        deprem_text = "Son 7 günde M5.0+ deprem kaydı yok (USGS)."
        deprem_yok = True

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
    if deprem_yok:
        # Deprem yoksa alternatif analiz rehberi
        ulke_profil = _ulke_afet_profili(ulke)
        analiz_rehberi = f"""### Analiz Rehberi (Deprem Yok - Alternatif Analiz)
Son 7 günde M5.0+ deprem kaydı olmadığı için, aşağıdaki alternatif analizi yap:

{ulke_profil}

**Analiz Soruları:**
1. RİSK DEĞERLENDİRMESİ: {ulke}'nin afet risk profili nedir? Hangi afet türleri için yüksek risk var?
2. HAZIRLıK EKONOMİSİ: Afet hazırlığı sektörleri (depreme dayanıklı bina, erken uyarı sistemleri, sigorta) için yatırım fırsatları var mı?
3. GEÇMİŞ TREND: Son büyük afetten bu yana hangi sektörler büyüdü? (İnşaat, sigorta, altyapı)
4. ÖNLEYICI YATIRIM: {ulke} hükümeti veya özel sektör afet önleme/hazırlık için hangi alanlara yatırım yapıyor?
5. SEKTÖR ÖNERİLERİ: Afet riski yüksek ülkelerde hangi sektörler uzun vadede değer kazanır?
   - İnşaat malzemeleri (çimento, çelik, depreme dayanıklı teknoloji)
   - Sigorta şirketleri (deprem, afet sigortası)
   - Altyapı teknolojileri (erken uyarı, izleme sistemleri)
   - Acil yardım ve lojistik
6. VARLIK ÖNERİSİ: {ulke} piyasasında veya global piyasada hangi hisse/ETF/emtia bu temadan faydalanabilir?

NOT: Somut deprem verisi olmadığı için, risk profili ve hazırlık ekonomisi üzerine odaklan. Uydurma deprem verisi ekleme."""
    else:
        # Normal deprem analizi rehberi
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
        analiz_rehberi,  # Analiz rehberini ekle
    ]

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("dogal_afet", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    return "\n".join(parcalar)
