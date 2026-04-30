"""
Özel Günler & Bayramlar modu bağlamı.
JSON takvim verisi + RSS haber başlıkları.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
from rss_utils import fetch_rss_titles, get_fallback_urls

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent / "data" / "ozel_gunler.json"
_DEFAULT_RSS_LIST = [
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
]
_RSS_TIMEOUT = 8.0


def _yukle_ozel_gunler() -> dict:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _yaklasan_gunler(ulke: str, pencere_gun: int = 30) -> list[dict]:
    """Bugünden itibaren pencere_gun içindeki özel günleri döndür."""
    tablo = _yukle_ozel_gunler()
    gunler = tablo.get(ulke) or tablo.get("Diğer", [])
    now = datetime.now()
    ay = now.month
    gun = now.day

    yaklasanlar: list[dict] = []
    for g in gunler:
        g_ay = g.get("ay", 0)
        g_gun = g.get("gun", 0)
        if g_ay == 0:
            # Değişken tarihli (Ramazan vb.) — her zaman dahil et
            yaklasanlar.append(g)
            continue
        # Basit yakınlık kontrolü: aynı ay veya bir sonraki ay
        if g_ay == ay or g_ay == (ay % 12) + 1:
            yaklasanlar.append(g)

    return yaklasanlar[:6]  # En fazla 6 gün


def _rss_basliklari_list(url: str, limit: int = 5) -> list[str]:
    """RSS başlıklarını çek (fallback ile)."""
    fallback_urls = get_fallback_urls("business") + get_fallback_urls("world_news")
    titles, used_url = fetch_rss_titles(url, limit, fallback_urls)
    return titles


def topla_ozel_gunler_baglami(ulke: str) -> str:
    """
    Özel Günler modu için prompt bağlamı.
    Yaklaşan bayram/tatil + RSS haber başlıkları + analiz rehberi.
    """
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]

    yaklasanlar = _yaklasan_gunler(ulke)

    if yaklasanlar:
        gun_satirlari = []
        for g in yaklasanlar:
            ay_str = ay_adlari[g["ay"] - 1] if g.get("ay", 0) > 0 else "Değişken tarih"
            gun_str = str(g.get("gun", "")) if g.get("gun", 0) > 0 else ""
            tarih_str = f"{gun_str} {ay_str}".strip() if gun_str else ay_str
            gun_satirlari.append(f"- {g['ad']} ({tarih_str}): {g['etki']}")
        gunler_text = "\n".join(gun_satirlari)
    else:
        gunler_text = "Bu dönemde tanımlı özel gün bulunamadı."

    # RSS başlıkları
    rss_urls = [os.getenv("OZEL_GUN_RSS_URL", "")] if os.getenv("OZEL_GUN_RSS_URL") else []
    rss_urls.extend(_DEFAULT_RSS_LIST)
    rss_urls = [u for u in rss_urls if u]

    titles: list[str] = []
    for u in rss_urls:
        titles = _rss_basliklari_list(u, limit=5)
        if titles:
            break

    rss_text = (
        "Güncel iş dünyası haberleri (bağlam için):\n" + "\n".join([f"- {t}" for t in titles])
        if titles else "Haber akışı şu an alınamadı."
    )

    # Analiz rehberi
    analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki özel gün verilerinden şu soruları yanıtla:
1. EN KRİTİK GÜN: Yaklaşan özel günler arasında en büyük tüketim etkisi yaratacak hangisi?
2. ÖNCE/SONRA: Bu özel günün 1-2 hafta öncesi ve sonrasında tüketim kalıbı nasıl değişiyor?
3. SEKTÖREL KAZANAN: Bu özel günden en çok kazanan sektörler hangileri? (perakende, gıda, seyahat, lojistik, hediye)
4. LOJİSTİK RİSKİ: Talep artışı lojistik kapasitesini zorluyor mu? Hangi tedarik zinciri riski var?
5. {ulke.upper()} ÖZGÜ: Bu özel günün {ulke} piyasasına özgü etkisi nedir? Hangi yerel şirketler kazanır?
NOT: Özel gün verisi JSON'dan geliyor — bu veriye dayan. Bağlamda olmayan günleri uydurma."""

    parcalar = [
        "### Verilen bağlam (bunu analizde dikkate al; uydurma veri ekleme)",
        f"Bugünün tarihi (bot sunucusu yerel saati): {now:%d} {ay_adi} {now.year}.",
        f"Hedef ülke (kullanıcı seçimi): {ulke}.",
        "Bu modda hedef: yaklaşan özel günler, bayramlar ve tatillerin tüketim, seyahat, perakende ve sektörel harcama örüntülerine etkisini analiz etmek.",
        "### Yaklaşan özel günler ve tahmini sektörel etkileri",
        gunler_text,
        "### Güncel haber bağlamı",
        rss_text,
    ]

    return "\n".join(parcalar)
