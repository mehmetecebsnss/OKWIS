"""
Okwis AI — Günlük Haber Özeti Sistemi

Her akşam saat 20:00'de dünya genelinde yaşanan kritik haberleri
kısa bir özet ve yorum ile kullanıcılara bildirir.

Özellikler:
- Otomatik günlük gönderim (akşam 20:00)
- Dünya haberleri (ekonomi, jeopolitik, piyasalar)
- AI destekli özet ve trend yorumu
- Hem free hem pro kullanıcılara açık
- Kullanıcı açıp/kapatabilir
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, date, time
from pathlib import Path
from typing import Optional

from rss_utils import fetch_rss_titles

logger = logging.getLogger(__name__)

_METRICS_DIR = Path(__file__).resolve().parent / "metrics"
_GUNLUK_OZET_TERCIHLERI_PATH = _METRICS_DIR / "gunluk_ozet_tercihleri.json"
_GUNLUK_OZET_GECMIS_PATH = _METRICS_DIR / "gunluk_ozet_gecmis.jsonl"

# Günlük özet gönderim saati (24 saat formatı)
GUNLUK_OZET_SAAT = 20  # 20:00 (akşam 8)
GUNLUK_OZET_DAKIKA = 0

# RSS kaynakları - dünya haberleri için
_GUNLUK_OZET_RSS_KAYNAKLARI = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://rss.cnn.com/rss/edition_world.rss",
    "https://rss.cnn.com/rss/money_news_international.rss",
]

_RSS_TIMEOUT = 10.0
_MAX_HABER_SAYISI = 15  # En fazla kaç haber toplanacak


# ═══════════════════════════════════════════════════════════════════════════════
# TERCİH YÖNETİMİ
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_ozet_tercihleri_yukle() -> dict[str, dict]:
    """
    Kullanıcı günlük özet tercihlerini yükle.
    Format: {user_id: {"acik": bool, "saat": int, "dakika": int}}
    """
    if not _GUNLUK_OZET_TERCIHLERI_PATH.exists():
        return {}
    try:
        with open(_GUNLUK_OZET_TERCIHLERI_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Günlük özet tercihleri okunamadı: %s", e)
    return {}


def gunluk_ozet_tercihleri_kaydet(data: dict) -> None:
    """Günlük özet tercihlerini kaydet."""
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_GUNLUK_OZET_TERCIHLERI_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Günlük özet tercihleri kaydedilemedi: %s", e)


def kullanici_gunluk_ozet_acik_mi(user_id: int | str) -> bool:
    """Kullanıcının günlük özeti açık mı? Varsayılan: kapalı."""
    tercihler = gunluk_ozet_tercihleri_yukle()
    tercih = tercihler.get(str(user_id), {})
    return tercih.get("acik", False)


def kullanici_gunluk_ozet_ayarla(user_id: int | str, acik: bool, saat: int = GUNLUK_OZET_SAAT, dakika: int = GUNLUK_OZET_DAKIKA) -> None:
    """Kullanıcının günlük özet tercihini ayarla."""
    tercihler = gunluk_ozet_tercihleri_yukle()
    tercihler[str(user_id)] = {
        "acik": acik,
        "saat": saat,
        "dakika": dakika,
    }
    gunluk_ozet_tercihleri_kaydet(tercihler)


def kullanici_gunluk_ozet_saati_al(user_id: int | str) -> tuple[int, int]:
    """Kullanıcının günlük özet saatini al. Varsayılan: 20:00"""
    tercihler = gunluk_ozet_tercihleri_yukle()
    tercih = tercihler.get(str(user_id), {})
    saat = tercih.get("saat", GUNLUK_OZET_SAAT)
    dakika = tercih.get("dakika", GUNLUK_OZET_DAKIKA)
    return saat, dakika


def gunluk_ozet_aktif_kullanicilar() -> list[str]:
    """Günlük özeti açık olan tüm kullanıcıları döndür."""
    tercihler = gunluk_ozet_tercihleri_yukle()
    return [uid for uid, tercih in tercihler.items() if tercih.get("acik", False)]


# ═══════════════════════════════════════════════════════════════════════════════
# HABER TOPLAMA
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_haberler_topla() -> list[str]:
    """Tüm RSS kaynaklarından günlük haberleri topla."""
    tum_haberler = []
    
    for rss_url in _GUNLUK_OZET_RSS_KAYNAKLARI:
        haberler, _ = fetch_rss_titles(rss_url, limit=5)
        tum_haberler.extend(haberler)
        
        if len(tum_haberler) >= _MAX_HABER_SAYISI:
            break
    
    # Benzersiz haberleri al
    benzersiz = list(set(tum_haberler))
    
    return benzersiz[:_MAX_HABER_SAYISI]


# ═══════════════════════════════════════════════════════════════════════════════
# ÖZET OLUŞTURMA
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_ozet_prompt_olustur(haberler: list[str]) -> str:
    """Günlük özet için AI prompt'u oluştur."""
    
    # Haberleri metne çevir
    haber_metni = ""
    for i, haber in enumerate(haberler, 1):
        haber_metni += f"{i}. {haber}\n"
    
    prompt = f"""Sen bir finansal analist ve dünya olayları uzmanısın. Bugün dünya genelinde yaşanan kritik haberleri analiz et ve kısa bir özet + yorum hazırla.

BUGÜNÜN HABERLERİ:
{haber_metni}

GÖREV:
1. En önemli 5-7 haberi seç (ekonomi, jeopolitik, piyasalar odaklı)
2. Her birini 1 cümle ile özetle
3. Genel bir trend yorumu yap (piyasalara, ekonomiye etkisi)

FORMAT:
📰 BUGÜN DÜNYADA NELER OLDU?

🔹 [Haber 1 özeti - 1 cümle]
🔹 [Haber 2 özeti - 1 cümle]
🔹 [Haber 3 özeti - 1 cümle]
...

💡 YORUM VE TREND ANALİZİ:
[2-3 cümle ile genel değerlendirme: Bu haberler piyasalara nasıl etki edebilir? Hangi yöne doğru gidiyoruz? Yatırımcılar nelere dikkat etmeli?]

KURALLAR:
- Kısa ve öz yaz (toplam max 500 kelime)
- Sade Türkçe kullan
- Emoji kullan (🔹 📰 💡 📈 📉 ⚠️)
- Spekülasyon yapma, sadece haberlere dayalı yorum yap
- Yatırım tavsiyesi verme, sadece genel trend analizi yap
"""
    
    return prompt


# ═══════════════════════════════════════════════════════════════════════════════
# GEÇMİŞ KAYIT
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_ozet_kaydet(user_id: int | str, ozet: str) -> None:
    """Gönderilen günlük özeti kaydet."""
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        kayit = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id),
            "tarih": date.today().isoformat(),
            "ozet_uzunluk": len(ozet),
        }
        with open(_GUNLUK_OZET_GECMIS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Günlük özet kaydedilemedi: %s", e)


def bugun_ozet_gonderildi_mi(user_id: int | str) -> bool:
    """Bugün bu kullanıcıya özet gönderildi mi?"""
    if not _GUNLUK_OZET_GECMIS_PATH.exists():
        return False
    
    bugun = date.today().isoformat()
    
    try:
        with open(_GUNLUK_OZET_GECMIS_PATH, encoding="utf-8") as f:
            for satir in f:
                try:
                    kayit = json.loads(satir.strip())
                    if kayit.get("user_id") == str(user_id) and kayit.get("tarih") == bugun:
                        return True
                except:
                    continue
    except Exception as e:
        logger.warning("Günlük özet geçmişi okunamadı: %s", e)
    
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# ZAMANLAMA
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_ozet_zamani_geldi_mi(user_id: int | str) -> bool:
    """Kullanıcı için günlük özet zamanı geldi mi?"""
    
    # Kullanıcının özeti açık mı?
    if not kullanici_gunluk_ozet_acik_mi(user_id):
        return False
    
    # Bugün zaten gönderildi mi?
    if bugun_ozet_gonderildi_mi(user_id):
        return False
    
    # Saat kontrolü
    simdi = datetime.now()
    saat, dakika = kullanici_gunluk_ozet_saati_al(user_id)
    
    # Kullanıcının belirlediği saat geçti mi?
    hedef_zaman = time(hour=saat, minute=dakika)
    simdi_zaman = simdi.time()
    
    # Hedef saat geçtiyse ve henüz gönderilmediyse True
    if simdi_zaman >= hedef_zaman:
        return True
    
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# İSTATİSTİKLER
# ═══════════════════════════════════════════════════════════════════════════════

def gunluk_ozet_istatistikleri() -> dict:
    """Günlük özet istatistiklerini döndür."""
    tercihler = gunluk_ozet_tercihleri_yukle()
    
    toplam_kullanici = len(tercihler)
    aktif_kullanici = sum(1 for t in tercihler.values() if t.get("acik", False))
    
    # Bugün kaç özet gönderildi?
    bugun = date.today().isoformat()
    bugun_gonderilen = 0
    
    if _GUNLUK_OZET_GECMIS_PATH.exists():
        try:
            with open(_GUNLUK_OZET_GECMIS_PATH, encoding="utf-8") as f:
                for satir in f:
                    try:
                        kayit = json.loads(satir.strip())
                        if kayit.get("tarih") == bugun:
                            bugun_gonderilen += 1
                    except:
                        continue
        except:
            pass
    
    return {
        "toplam_kullanici": toplam_kullanici,
        "aktif_kullanici": aktif_kullanici,
        "bugun_gonderilen": bugun_gonderilen,
    }
