"""
Web Arama Modülü — Tavily API entegrasyonu.

Her bağlam dosyası bu modülü çağırarak RSS'in ötesinde gerçek web araması yapabilir.
TAVILY_API_KEY tanımlı değilse tüm fonksiyonlar sessizce boş döner — sistemin geri kalanı etkilenmez.

Kullanım:
    from web_arama import tavily_ara
    sonuclar = tavily_ara("Türkiye jeopolitik risk Nisan 2026", max_sonuc=5)
    # [{"title": "...", "content": "...", "url": "...", "score": 0.9}, ...]
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

_TAVILY_API_URL = "https://api.tavily.com/search"
_TIMEOUT = 15.0


def _api_key() -> str:
    return (os.getenv("TAVILY_API_KEY") or "").strip()


def tavily_ara(
    sorgu: str,
    max_sonuc: int = 5,
    arama_derinligi: str = "basic",  # "basic" veya "advanced"
    guncel_mi: bool = True,          # True → son 3 gün, False → genel
) -> list[dict]:
    """
    Tavily API ile web araması yap.

    Dönüş: [{"title": str, "content": str, "url": str, "score": float}, ...]
    Hata veya anahtar yoksa: []
    """
    key = _api_key()
    if not key:
        return []

    payload: dict = {
        "api_key": key,
        "query": sorgu,
        "max_results": max_sonuc,
        "search_depth": arama_derinligi,
        "include_answer": False,
        "include_raw_content": False,
    }

    # Son 3 günlük içerik için tarih filtresi
    if guncel_mi:
        from datetime import timedelta
        ucgun_once = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
        payload["days"] = 3

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            r = client.post(_TAVILY_API_URL, json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning("Tavily API anahtarı geçersiz — TAVILY_API_KEY'i kontrol et")
        elif e.response.status_code == 429:
            logger.warning("Tavily rate limit — kota dolmuş olabilir")
        else:
            logger.warning("Tavily HTTP hatası %s: %s", e.response.status_code, e)
        return []
    except Exception as e:
        logger.warning("Tavily araması başarısız: %s", e)
        return []

    sonuclar: list[dict] = []
    for item in (data.get("results") or [])[:max_sonuc]:
        sonuclar.append({
            "title": (item.get("title") or "").strip()[:200],
            "content": (item.get("content") or "").strip()[:500],
            "url": (item.get("url") or "").strip(),
            "score": float(item.get("score") or 0.0),
        })

    logger.info("Tavily arama tamamlandı: sorgu=%r sonuc=%d", sorgu[:60], len(sonuclar))
    return sonuclar


def tavily_metin_ozeti(sonuclar: list[dict], baslik: str = "Web Araması") -> str:
    """
    Tavily sonuçlarını prompt'a eklenebilir metin bloğuna dönüştür.
    Boş sonuçta boş string döner.
    """
    if not sonuclar:
        return ""

    satirlar = [f"### {baslik} (Tavily — canlı web verisi)"]
    for i, s in enumerate(sonuclar, 1):
        satirlar.append(f"{i}. {s['title']}")
        if s["content"]:
            # İlk 200 karakter yeterli — model hallucination riskini azaltır
            satirlar.append(f"   {s['content'][:200]}")
        if s["url"]:
            satirlar.append(f"   Kaynak: {s['url']}")
    return "\n".join(satirlar)


# ── Mod-spesifik sorgu oluşturucular ──────────────────────────────────────────

def _bugun_str() -> str:
    now = datetime.now()
    aylar = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
             "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    return f"{now.day} {aylar[now.month-1]} {now.year}"


def jeopolitik_sorgulari(ulke: str) -> list[str]:
    """Jeopolitik mod için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"{ulke} geopolitical risk {bugun}",
        f"{ulke} sanctions war conflict news latest",
        f"global energy crisis oil supply {bugun}",
    ]


def sektor_sorgulari(ulke: str) -> list[str]:
    """Sektör trendleri modu için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"{ulke} stock market sector trends {bugun}",
        f"AI technology semiconductor earnings {bugun}",
        f"{ulke} economy GDP inflation latest news",
    ]


def trendler_sorgulari(ulke: str) -> list[str]:
    """Dünya trendleri modu için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"global trending news viral {bugun}",
        f"AI crypto technology social media trend {bugun}",
        f"{ulke} consumer behavior market trend {bugun}",
    ]


def magazin_sorgulari(ulke: str) -> list[str]:
    """Magazin/viral modu için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"celebrity brand viral controversy {bugun}",
        f"entertainment industry stock impact {bugun}",
        f"viral social media brand boycott {bugun}",
    ]


def dogal_afet_sorgulari(ulke: str) -> list[str]:
    """Doğal afet modu için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"earthquake flood hurricane disaster {bugun}",
        f"natural disaster economic impact reconstruction {bugun}",
        f"{ulke} disaster risk infrastructure {bugun}",
    ]


def mevsim_sorgulari(ulke: str) -> list[str]:
    """Mevsim modu için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"{ulke} seasonal economy market {bugun}",
        f"{ulke} energy demand commodity price seasonal {bugun}",
    ]


def varlik_sorgulari(ulke: str, varlik: str) -> list[str]:
    """Varlık odaklı Okwis/analiz için Tavily sorguları."""
    bugun = _bugun_str()
    return [
        f"{varlik} price prediction analysis {bugun}",
        f"{varlik} {ulke} market outlook {bugun}",
        f"{varlik} latest news fundamental {bugun}",
    ]


def topla_mod_aramalari(mod: str, ulke: str, varlik: str = "") -> str:
    """
    Verilen mod için uygun Tavily sorgularını çalıştır ve metin olarak döndür.
    Anahtar yoksa veya hata olursa boş string döner.
    """
    if not _api_key():
        return ""

    sorgu_fn = {
        "jeopolitik": jeopolitik_sorgulari,
        "sektor": sektor_sorgulari,
        "trendler": trendler_sorgulari,
        "magazin": magazin_sorgulari,
        "dogal_afet": dogal_afet_sorgulari,
        "mevsim": mevsim_sorgulari,
    }.get(mod)

    if sorgu_fn is None:
        return ""

    sorgular = sorgu_fn(ulke)

    # Varlık varsa ekstra sorgu
    if varlik and varlik.strip():
        sorgular = varlik_sorgulari(ulke, varlik) + sorgular[:1]

    # En fazla 2 sorgu çalıştır — istek sayısını koru
    tum_sonuclar: list[dict] = []
    gorulmus_url: set[str] = set()

    for sorgu in sorgular[:2]:
        sonuclar = tavily_ara(sorgu, max_sonuc=3, guncel_mi=True)
        for s in sonuclar:
            if s["url"] not in gorulmus_url:
                gorulmus_url.add(s["url"])
                tum_sonuclar.append(s)

    # Skora göre sırala
    tum_sonuclar.sort(key=lambda x: x["score"], reverse=True)

    return tavily_metin_ozeti(tum_sonuclar[:5], baslik=f"Güncel Web Araması — {mod.capitalize()}")
