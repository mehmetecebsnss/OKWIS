"""
Mevsim modu için yapılandırılmış bağlam: zaman, mevsim fazı, ülke notları,
isteğe bağlı RSS özeti, başkent hava özeti (OpenWeather) ve Tavily web araması.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from web_arama import topla_mod_aramalari

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent / "data" / "ulke_mevsim.json"
_DEFAULT_RSS = "https://feeds.reuters.com/reuters/businessNews"
_BBC_BUSINESS_RSS = "https://feeds.bbci.co.uk/news/business/rss.xml"
_RSS_TIMEOUT = 8.0
_WEATHER_TIMEOUT = 6.0


def _yukle_ulke_tablosu() -> dict[str, Any]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _meteorolojik_mevsim(ay: int, hemisphere: str) -> str:
    """Kuzey yarımküre meteorolojik mevsim; güney için 6 ay kaydırılır."""
    h = (hemisphere or "north").lower()
    m = ay
    if h == "south":
        m = (ay + 5) % 12 + 1
    if m in (12, 1, 2):
        return "kış"
    if m in (3, 4, 5):
        return "ilkbahar"
    if m in (6, 7, 8):
        return "yaz"
    return "sonbahar"


def _zaman_satirlari(now: datetime | None = None) -> str:
    now = now or datetime.now()
    aylar = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    gun = now.day
    ay = aylar[now.month - 1]
    yil = now.year
    saat = now.strftime("%H:%M")
    return f"Bugünün tarihi (bot sunucusu yerel saati): {gun} {ay} {yil}, saat {saat}."


def _rss_basliklari_list(url: str, limit: int = 5) -> list[str]:
    headers = {
        "User-Agent": "MakroLensBot/1.0 (+https://t.me/)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        with httpx.Client(timeout=_RSS_TIMEOUT, headers=headers) as client:
            # Bazı feed URL'leri kısa link / yönlendirme döndürebilir.
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
            text = r.text
    except Exception as e:
        logger.warning("RSS alınamadı (%s): %s", url, e)
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
        logger.warning("RSS XML ayrıştırılamadı: %s", url)
        return []

    return titles


def _rss_basliklari_ozet(url_overrides: list[str] | None, limit: int = 5) -> str:
    """
    Çoklu fallback:
    1) .env MACRO_RSS_URL (varsa)
    2) Reuters business (default)
    3) BBC business
    """
    urls: list[str] = []
    if url_overrides:
        urls.extend([u.strip() for u in url_overrides if u and u.strip()])
    urls.extend([_DEFAULT_RSS, _BBC_BUSINESS_RSS])

    # sıra koruyarak tekilleştir
    seen: set[str] = set()
    urls = [u for u in urls if u and not (u in seen or seen.add(u))]

    for u in urls:
        titles = _rss_basliklari_list(u, limit=limit)
        if titles:
            satirlar = [f"- {t}" for t in titles]
            return "Son dönemden örnek haber başlıkları (özet, yatırım tavsiyesi değil):\n" + "\n".join(satirlar)

    return "Makro haber akışından başlık çıkarılamadı (ağ veya kaynak geçici)."


def _env_rss_listesini_oku() -> list[str]:
    """
    .env desteği:
    - MACRO_RSS_URLS=url1,url2,url3 (önerilen)
    - MACRO_RSS_URL=url1 (geri uyum)
    """
    out: list[str] = []
    raw_list = (os.getenv("MACRO_RSS_URLS") or "").strip()
    if raw_list:
        for p in raw_list.split(","):
            u = p.strip()
            if u:
                out.append(u)

    tek = (os.getenv("MACRO_RSS_URL") or "").strip()
    if tek:
        out.append(tek)

    # sıra koruyarak tekilleştir
    seen: set[str] = set()
    return [u for u in out if not (u in seen or seen.add(u))]


def _hava_ozet_baskent(capital_query: str | None) -> str | None:
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key or not capital_query:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": capital_query, "appid": key, "units": "metric", "lang": "tr"}
    try:
        with httpx.Client(timeout=_WEATHER_TIMEOUT) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Hava API hatası (%s): %s", capital_query, e)
        return None

    try:
        desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        city = data.get("name", capital_query)
        return f"Başkent ({city}) anlık hava özeti: {desc}, yaklaşık {temp:.0f}°C (OpenWeather)."
    except (KeyError, IndexError, TypeError):
        return None


def topla_mevsim_baglami(ulke: str) -> str:
    """
    Model prompt'una eklenecek tek metin bloğu.
    Dış kaynaklar: RSS (varsayılan veya MACRO_RSS_URL) + isteğe bağlı hava API.
    Statik: JSON ülke notları + türetilmiş mevsim fazı.
    """
    tablo = _yukle_ulke_tablosu()
    meta = tablo.get(ulke) or tablo.get("Diğer", {})
    hemisphere = meta.get("hemisphere", "north")
    notlar: list[str] = meta.get("takvim_notlari") or []
    capital_q = meta.get("capital_query")

    now = datetime.now()
    ay = now.month
    mevsim = _meteorolojik_mevsim(ay, hemisphere)
    ay_adlari = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    ay_adi = ay_adlari[ay - 1]

    parcalar: list[str] = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        _zaman_satirlari(now),
        f"Hedef ülke: {ulke}. Meteorolojik mevsim (yaklaşık): {mevsim} ({ay_adi} itibarıyla).",
        "Ülke / dönem notları (genel çerçeve, güncel haber değil):",
    ]
    for n in notlar[:5]:
        parcalar.append(f"- {n}")

    rss_urls = _env_rss_listesini_oku()
    parcalar.append("### Makro haber özeti (başlıklar)")
    parcalar.append(_rss_basliklari_ozet(rss_urls, limit=5))

    hava = _hava_ozet_baskent(capital_q)
    if hava:
        parcalar.append("### Hava (mevsim bağlamı için tek satır)")
        parcalar.append(hava)

    # Analiz rehberi
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki mevsim ve haber verilerinden şu soruları yanıtla:
1. MEVSİMSEL DÖNGÜ: {ay_adi} ayında {ulke} için hangi mevsimsel sektörel döngü aktif? (enerji, tarım, turizm, perakende)
2. HABER ÖRTÜŞMESI: Bağlamdaki haber başlıkları mevsimsel tezi destekliyor mu, çürütüyor mu?
3. SEKTÖREL KAZANAN: Bu mevsimde tarihsel olarak hangi sektörler güçlenir?
4. MEVSİM GEÇİŞİ: Bir sonraki mevsime geçiş yaklaşıyorsa hangi sektörel kayma bekleniyor?
5. {ulke.upper()} ÖZGÜ: Bu mevsimin {ulke} piyasasına özgü etkisi nedir?
NOT: Mevsimsel veriye ve haber başlıklarına dayan. Bağlamda olmayan verileri uydurma."""

    # Tavily web araması
    tavily_blok = topla_mod_aramalari("mevsim", ulke)
    if tavily_blok:
        parcalar.append(tavily_blok)

    parcalar.append(analiz_rehberi)

    return "\n".join(parcalar)
