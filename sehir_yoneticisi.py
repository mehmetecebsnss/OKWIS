"""
Okwis AI - Şehir Yöneticisi
Kullanıcı şehir bilgisini yönet ve default şehirler sağla.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default şehirler (ülke başkentleri)
DEFAULT_SEHIRLER = {
    "Türkiye": "Ankara",
    "ABD": "Washington",
    "Japonya": "Tokyo",
    "Çin": "Beijing",
    "Almanya": "Berlin",
    "Fransa": "Paris",
    "İngiltere": "London",
    "İtalya": "Rome",
    "İspanya": "Madrid",
    "Rusya": "Moscow",
    "Hindistan": "New Delhi",
    "Brezilya": "Brasilia",
    "Meksika": "Mexico City",
    "Kanada": "Ottawa",
    "Avustralya": "Canberra",
    "Güney Kore": "Seoul",
    "Suudi Arabistan": "Riyadh",
    "Birleşik Arap Emirlikleri": "Abu Dhabi",
    "Güney Afrika": "Pretoria",
    "Arjantin": "Buenos Aires",
}

# Ülke → OpenWeatherMap şehir adı (API için)
ULKE_SEHIR_API_MAP = {
    "Türkiye": "Ankara,TR",
    "ABD": "Washington,US",
    "Japonya": "Tokyo,JP",
    "Çin": "Beijing,CN",
    "Almanya": "Berlin,DE",
    "Fransa": "Paris,FR",
    "İngiltere": "London,GB",
    "İtalya": "Rome,IT",
    "İspanya": "Madrid,ES",
    "Rusya": "Moscow,RU",
    "Hindistan": "New Delhi,IN",
    "Brezilya": "Brasilia,BR",
    "Meksika": "Mexico City,MX",
    "Kanada": "Ottawa,CA",
    "Avustralya": "Canberra,AU",
    "Güney Kore": "Seoul,KR",
    "Suudi Arabistan": "Riyadh,SA",
    "Birleşik Arap Emirlikleri": "Abu Dhabi,AE",
    "Güney Afrika": "Pretoria,ZA",
    "Arjantin": "Buenos Aires,AR",
}


def default_sehir_al(ulke: str) -> str:
    """
    Ülke için default şehir al (başkent).
    
    Args:
        ulke: Ülke adı (örn: "Türkiye", "ABD")
    
    Returns:
        Şehir adı (örn: "Ankara", "Washington")
    """
    return DEFAULT_SEHIRLER.get(ulke, "Unknown")


def sehir_api_format(ulke: str, sehir: Optional[str] = None) -> str:
    """
    OpenWeatherMap API için şehir formatı.
    
    Args:
        ulke: Ülke adı
        sehir: Şehir adı (opsiyonel, yoksa default kullanılır)
    
    Returns:
        API formatı (örn: "Ankara,TR", "Washington,US")
    """
    if sehir:
        # Kullanıcı şehri varsa, ülke kodunu ekle
        ulke_kod = ULKE_SEHIR_API_MAP.get(ulke, "").split(",")[-1]
        if ulke_kod:
            return f"{sehir},{ulke_kod}"
        return sehir
    
    # Default şehir kullan
    return ULKE_SEHIR_API_MAP.get(ulke, "Unknown")


def sehir_normalize(sehir: str) -> str:
    """
    Şehir adını normalize et (Türkçe karakterler, büyük/küçük harf).
    
    Args:
        sehir: Şehir adı
    
    Returns:
        Normalize edilmiş şehir adı
    """
    # Türkçe karakterleri koru, sadece ilk harfi büyük yap
    return sehir.strip().title()


# ─── Kullanıcı Şehir Tercihi (Profil Entegrasyonu) ───────────────────────────

_SEHIR_TERCIH_PATH = Path(__file__).resolve().parent / "metrics" / "kullanici_sehir.json"


def _sehir_tercih_yukle() -> dict:
    """Kullanıcı şehir tercihlerini yükle."""
    try:
        if _SEHIR_TERCIH_PATH.exists():
            with open(_SEHIR_TERCIH_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Şehir tercihleri yüklenemedi: %s", e)
    return {}


def _sehir_tercih_kaydet(data: dict):
    """Kullanıcı şehir tercihlerini kaydet."""
    try:
        _SEHIR_TERCIH_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SEHIR_TERCIH_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Şehir tercihleri kaydedilemedi: %s", e)


def kullanici_sehir_al(user_id: int | str, ulke: str) -> str:
    """
    Kullanıcının şehir tercihini al.
    
    Args:
        user_id: Kullanıcı ID
        ulke: Ülke adı
    
    Returns:
        Şehir adı (kullanıcı tercihi veya default)
    """
    tercihler = _sehir_tercih_yukle()
    user_key = str(user_id)
    
    if user_key in tercihler:
        user_tercih = tercihler[user_key]
        # Ülkeye özel şehir var mı?
        if ulke in user_tercih:
            return user_tercih[ulke]
        # Genel şehir tercihi var mı?
        if "default" in user_tercih:
            return user_tercih["default"]
    
    # Default şehir kullan
    return default_sehir_al(ulke)


def kullanici_sehir_kaydet(user_id: int | str, ulke: str, sehir: str):
    """
    Kullanıcının şehir tercihini kaydet.
    
    Args:
        user_id: Kullanıcı ID
        ulke: Ülke adı
        sehir: Şehir adı
    """
    tercihler = _sehir_tercih_yukle()
    user_key = str(user_id)
    
    if user_key not in tercihler:
        tercihler[user_key] = {}
    
    tercihler[user_key][ulke] = sehir_normalize(sehir)
    _sehir_tercih_kaydet(tercihler)
    
    logger.info("Kullanıcı şehir tercihi kaydedildi: user=%s, ulke=%s, sehir=%s", user_id, ulke, sehir)


def kullanici_sehir_sil(user_id: int | str):
    """
    Kullanıcının tüm şehir tercihlerini sil.
    
    Args:
        user_id: Kullanıcı ID
    """
    tercihler = _sehir_tercih_yukle()
    user_key = str(user_id)
    
    if user_key in tercihler:
        del tercihler[user_key]
        _sehir_tercih_kaydet(tercihler)
        logger.info("Kullanıcı şehir tercihleri silindi: user=%s", user_id)


# ─── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 80)
    print("ŞEHİR YÖNETİCİSİ TEST")
    print("=" * 80)
    
    # Default şehirler
    print("\n1. DEFAULT ŞEHİRLER:")
    for ulke in ["Türkiye", "ABD", "Japonya", "Çin", "Almanya"]:
        sehir = default_sehir_al(ulke)
        api_format = sehir_api_format(ulke)
        print(f"   {ulke} → {sehir} (API: {api_format})")
    
    # Kullanıcı tercihi
    print("\n2. KULLANICI TERCİHİ:")
    test_user_id = 12345
    
    # Tercih kaydet
    kullanici_sehir_kaydet(test_user_id, "Türkiye", "İstanbul")
    kullanici_sehir_kaydet(test_user_id, "ABD", "New York")
    
    # Tercih al
    sehir_tr = kullanici_sehir_al(test_user_id, "Türkiye")
    sehir_us = kullanici_sehir_al(test_user_id, "ABD")
    sehir_jp = kullanici_sehir_al(test_user_id, "Japonya")  # Default kullanılacak
    
    print(f"   User {test_user_id} - Türkiye: {sehir_tr}")
    print(f"   User {test_user_id} - ABD: {sehir_us}")
    print(f"   User {test_user_id} - Japonya: {sehir_jp} (default)")
    
    # Tercih sil
    kullanici_sehir_sil(test_user_id)
    sehir_tr_after = kullanici_sehir_al(test_user_id, "Türkiye")
    print(f"   User {test_user_id} - Türkiye (silindikten sonra): {sehir_tr_after} (default)")
    
    print("\n" + "=" * 80)
