"""
Okwis AI — Kullanıcı Utility Fonksiyonları
Kullanıcı yönetimi, plan kontrolü, profil işlemleri
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Dosya yolları
_METRICS_DIR = Path(__file__).resolve().parent / "metrics"
_PLAN_KAYITLARI_PATH = _METRICS_DIR / "plan_kayitlari.json"
_KULLANICI_PROFIL_PATH = _METRICS_DIR / "kullanici_profilleri.json"
_GUNLUK_LIMIT_PATH = _METRICS_DIR / "gunluk_limit.json"


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN YÖNETİMİ
# ═══════════════════════════════════════════════════════════════════════════════

def plan_kayitlari_yukle() -> dict:
    """
    Plan kayıtlarını yükle
    
    Returns:
        {user_id: {"plan": "free|pro|claude", "baslangic": "ISO tarih", ...}}
    """
    if not _PLAN_KAYITLARI_PATH.exists():
        return {}
    try:
        with open(_PLAN_KAYITLARI_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Plan kayıtları okunamadı: %s", e)
        return {}


def plan_kayitlari_kaydet(data: dict) -> None:
    """Plan kayıtlarını kaydet"""
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_PLAN_KAYITLARI_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Plan kayıtları kaydedilemedi: %s", e)


def kullanici_plani_al(user_id: int | str) -> str:
    """
    Kullanıcının planını al
    
    Returns:
        "free" | "pro" | "claude"
    """
    kayitlar = plan_kayitlari_yukle()
    kayit = kayitlar.get(str(user_id), {})
    return kayit.get("plan", "free").lower()


def kullanici_pro_mu(user_id: int | str) -> bool:
    """Kullanıcı Pro veya Claude planında mı?"""
    plan = kullanici_plani_al(user_id)
    return plan in ("pro", "claude")


def kullanici_plan_ayarla(user_id: int | str, plan: str) -> None:
    """
    Kullanıcının planını ayarla
    
    Args:
        user_id: Kullanıcı ID
        plan: "free" | "pro" | "claude"
    """
    kayitlar = plan_kayitlari_yukle()
    uid = str(user_id)
    
    if uid not in kayitlar:
        kayitlar[uid] = {}
    
    kayitlar[uid]["plan"] = plan.lower()
    kayitlar[uid]["guncelleme"] = datetime.now(timezone.utc).isoformat()
    
    if "baslangic" not in kayitlar[uid]:
        kayitlar[uid]["baslangic"] = datetime.now(timezone.utc).isoformat()
    
    plan_kayitlari_kaydet(kayitlar)


# ═══════════════════════════════════════════════════════════════════════════════
# KULLANICI PROFİLİ
# ═══════════════════════════════════════════════════════════════════════════════

def kullanici_profili_yukle() -> dict:
    """
    Kullanıcı profillerini yükle
    
    Returns:
        {user_id: {"ulke": "...", "sehir": "...", "dil": "tr", ...}}
    """
    if not _KULLANICI_PROFIL_PATH.exists():
        return {}
    try:
        with open(_KULLANICI_PROFIL_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Kullanıcı profilleri okunamadı: %s", e)
        return {}


def kullanici_profili_kaydet(data: dict) -> None:
    """Kullanıcı profillerini kaydet"""
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_KULLANICI_PROFIL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Kullanıcı profilleri kaydedilemedi: %s", e)


def kullanici_profili_al(user_id: int | str) -> Optional[dict]:
    """
    Kullanıcının profilini al
    
    Returns:
        {"ulke": "...", "sehir": "...", "dil": "tr", ...} veya None
    """
    profiller = kullanici_profili_yukle()
    return profiller.get(str(user_id))


def kullanici_profili_guncelle(user_id: int | str, **kwargs) -> None:
    """
    Kullanıcı profilini güncelle
    
    Args:
        user_id: Kullanıcı ID
        **kwargs: Güncellenecek alanlar (ulke, sehir, dil, vb.)
    """
    profiller = kullanici_profili_yukle()
    uid = str(user_id)
    
    if uid not in profiller:
        profiller[uid] = {}
    
    profiller[uid].update(kwargs)
    profiller[uid]["guncelleme"] = datetime.now(timezone.utc).isoformat()
    
    kullanici_profili_kaydet(profiller)


def kullanici_ulke_al(user_id: int | str, varsayilan: str = "Türkiye") -> str:
    """Kullanıcının ülkesini al"""
    profil = kullanici_profili_al(user_id)
    if profil:
        return profil.get("ulke", varsayilan)
    return varsayilan


def kullanici_sehir_al(user_id: int | str, varsayilan: str = "Ankara") -> str:
    """Kullanıcının şehrini al"""
    profil = kullanici_profili_al(user_id)
    if profil:
        return profil.get("sehir", varsayilan)
    return varsayilan


# ═══════════════════════════════════════════════════════════════════════════════
# GÜNLÜK LİMİT
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_limit_yukle() -> dict:
    """
    Günlük limit verilerini yükle
    
    Returns:
        {user_id: {"tarih": "2026-04-30", "sayac": 3}}
    """
    if not _GUNLUK_LIMIT_PATH.exists():
        return {}
    try:
        with open(_GUNLUK_LIMIT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Günlük limit okunamadı: %s", e)
        return {}


def gunluk_limit_kaydet(data: dict) -> None:
    """Günlük limit verilerini kaydet"""
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_GUNLUK_LIMIT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Günlük limit kaydedilemedi: %s", e)


def kullanici_gunluk_sayac(user_id: int | str) -> int:
    """
    Kullanıcının bugünkü analiz sayısını al
    
    Returns:
        Bugün yapılan analiz sayısı
    """
    limit_data = gunluk_limit_yukle()
    uid = str(user_id)
    bugun = datetime.now().date().isoformat()
    
    kayit = limit_data.get(uid, {})
    if kayit.get("tarih") != bugun:
        return 0
    
    return int(kayit.get("sayac", 0))


def kullanici_gunluk_artir(user_id: int | str) -> int:
    """
    Kullanıcının günlük sayacını 1 artır
    
    Returns:
        Yeni sayaç değeri
    """
    limit_data = gunluk_limit_yukle()
    uid = str(user_id)
    bugun = datetime.now().date().isoformat()
    
    kayit = limit_data.get(uid, {})
    if kayit.get("tarih") != bugun:
        kayit = {"tarih": bugun, "sayac": 0}
    
    kayit["sayac"] = kayit.get("sayac", 0) + 1
    limit_data[uid] = kayit
    
    gunluk_limit_kaydet(limit_data)
    return kayit["sayac"]


def kullanici_limit_kontrolu(user_id: int | str, limit: int = 3) -> tuple[bool, int, int]:
    """
    Kullanıcının günlük limitini kontrol et
    
    Args:
        user_id: Kullanıcı ID
        limit: Günlük limit (varsayılan: 3)
    
    Returns:
        (limit_asildi_mi, mevcut_sayac, kalan)
    """
    sayac = kullanici_gunluk_sayac(user_id)
    limit_asildi = sayac >= limit
    kalan = max(0, limit - sayac)
    
    return limit_asildi, sayac, kalan


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN KONTROLÜ
# ═══════════════════════════════════════════════════════════════════════════════

def kullanici_admin_mi(user_id: int | str) -> bool:
    """Kullanıcı admin mi?"""
    import os
    admin_ids = os.getenv("ADMIN_USER_IDS", "").strip()
    if not admin_ids:
        return False
    
    admin_list = [aid.strip() for aid in admin_ids.split(",")]
    return str(user_id) in admin_list


# ═══════════════════════════════════════════════════════════════════════════════
# İSTATİSTİKLER
# ═══════════════════════════════════════════════════════════════════════════════

def kullanici_istatistikleri() -> dict:
    """
    Genel kullanıcı istatistikleri
    
    Returns:
        {
            "toplam_kullanici": int,
            "free": int,
            "pro": int,
            "claude": int,
            "aktif_bugun": int,
        }
    """
    plan_kayitlari = plan_kayitlari_yukle()
    limit_data = gunluk_limit_yukle()
    bugun = datetime.now().date().isoformat()
    
    toplam = len(plan_kayitlari)
    free = sum(1 for k in plan_kayitlari.values() if k.get("plan", "free").lower() == "free")
    pro = sum(1 for k in plan_kayitlari.values() if k.get("plan", "").lower() == "pro")
    claude = sum(1 for k in plan_kayitlari.values() if k.get("plan", "").lower() == "claude")
    
    aktif_bugun = sum(1 for k in limit_data.values() if k.get("tarih") == bugun)
    
    return {
        "toplam_kullanici": toplam,
        "free": free,
        "pro": pro,
        "claude": claude,
        "aktif_bugun": aktif_bugun,
    }
