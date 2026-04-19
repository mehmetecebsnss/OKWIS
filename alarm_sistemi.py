"""
Okwis AI — Alarm Sistemi (Parça O)

Her 30 dakikada bir piyasayı etkileyen kritik gelişmeleri tarar.
Eşiği geçen olaylar Pro/Claude üyelere otomatik bildirim gönderir.
Kullanıcı /bildirim komutu ile açıp kapatabilir.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_METRICS_DIR = Path(__file__).resolve().parent / "metrics"
_BILDIRIM_TERCIHLERI_PATH = _METRICS_DIR / "bildirim_tercihleri.json"
_GONDERILEN_ALARMLAR_PATH = _METRICS_DIR / "gonderilen_alarmlar.jsonl"

# Tarama sıklığı (saniye)
ALARM_ARALIK_SANIYE = 1800  # 30 dakika

# Önem eşiği — bu skorun üzerindeki olaylar bildirim tetikler
ALARM_ESIK = 7  # 1-10 skalasında

# Aynı haberden ikinci bildirim gönderimini önlemek için
_DEDUPE_PENCERE_SAAT = 6

# Alarm RSS kaynakları — jeopolitik + ekonomik odaklı
_ALARM_RSS_LISTESI = [
    "https://feeds.reuters.com/reuters/worldNews",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.reuters.com/reuters/businessNews",
]
_RSS_TIMEOUT = 10.0


# ── Bildirim Tercihleri ───────────────────────────────────────────────────────

def bildirim_tercihleri_yukle() -> dict[str, bool]:
    """Kullanıcı bildirim tercihlerini yükle. {user_id: True/False}"""
    if not _BILDIRIM_TERCIHLERI_PATH.exists():
        return {}
    try:
        with open(_BILDIRIM_TERCIHLERI_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): bool(v) for k, v in data.items()}
    except Exception as e:
        logger.warning("Bildirim tercihleri okunamadı: %s", e)
    return {}


def bildirim_tercihleri_kaydet(data: dict[str, bool]) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_BILDIRIM_TERCIHLERI_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Bildirim tercihleri kaydedilemedi: %s", e)


def kullanici_bildirim_acik_mi(user_id: int | str) -> bool:
    """Kullanıcının bildirimi açık mı? Varsayılan: açık (Pro/Claude için)."""
    tercihler = bildirim_tercihleri_yukle()
    # Tercih hiç ayarlanmamışsa varsayılan açık
    return tercihler.get(str(user_id), True)


def kullanici_bildirim_ayarla(user_id: int | str, acik: bool) -> None:
    tercihler = bildirim_tercihleri_yukle()
    tercihler[str(user_id)] = acik
    bildirim_tercihleri_kaydet(tercihler)


# ── Deduplicate ───────────────────────────────────────────────────────────────

def _gonderilen_alarmlar_yukle() -> list[dict]:
    if not _GONDERILEN_ALARMLAR_PATH.exists():
        return []
    alarmlar = []
    try:
        with open(_GONDERILEN_ALARMLAR_PATH, encoding="utf-8") as f:
            for satir in f:
                s = satir.strip()
                if s:
                    try:
                        alarmlar.append(json.loads(s))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return alarmlar


def _alarm_daha_once_gonderildi_mi(anahtar: str) -> bool:
    """Son N saatte aynı anahtar gönderildi mi?"""
    alarmlar = _gonderilen_alarmlar_yukle()
    simdi = datetime.now(timezone.utc).timestamp()
    pencere = _DEDUPE_PENCERE_SAAT * 3600
    for a in alarmlar:
        if a.get("anahtar") == anahtar:
            try:
                ts = datetime.fromisoformat(a["ts"]).timestamp()
                if simdi - ts < pencere:
                    return True
            except Exception:
                continue
    return False


def _alarm_gonderildi_kaydet(anahtar: str) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        kayit = {"ts": datetime.now(timezone.utc).isoformat(), "anahtar": anahtar}
        with open(_GONDERILEN_ALARMLAR_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Alarm kaydedilemedi: %s", e)


# ── RSS Tarama ────────────────────────────────────────────────────────────────

def _rss_basliklar_topla(limit_per_kaynak: int = 10) -> list[str]:
    """Alarm RSS kaynaklarından başlıkları topla."""
    from xml.etree import ElementTree as ET
    tum: list[str] = []
    headers = {
        "User-Agent": "OkwisAlarmBot/1.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    for url in _ALARM_RSS_LISTESI:
        try:
            with httpx.Client(timeout=_RSS_TIMEOUT, headers=headers) as client:
                r = client.get(url, follow_redirects=True)
                r.raise_for_status()
                root = ET.fromstring(r.text)
                for item in root.findall(".//item"):
                    if len(tum) >= limit_per_kaynak * len(_ALARM_RSS_LISTESI):
                        break
                    el = item.find("title")
                    if el is not None and el.text and el.text.strip():
                        tum.append(el.text.strip()[:300])
        except Exception as e:
            logger.warning("Alarm RSS alınamadı (%s): %s", url, e)
    return tum


def _tavily_guncel_ara() -> list[dict]:
    """Tavily ile kritik güncel haber ara."""
    key = (os.getenv("TAVILY_API_KEY") or "").strip()
    if not key:
        return []
    now = datetime.now()
    aylar = ("January","February","March","April","May","June",
             "July","August","September","October","November","December")
    tarih_str = f"{now.day} {aylar[now.month-1]} {now.year}"
    sorgu = f"breaking news market crash war oil crisis geopolitical shock {tarih_str}"
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(
                "https://api.tavily.com/search",
                json={"api_key": key, "query": sorgu, "max_results": 5,
                      "search_depth": "basic", "days": 1},
            )
            r.raise_for_status()
            return r.json().get("results", [])
    except Exception as e:
        logger.warning("Alarm Tavily araması başarısız: %s", e)
    return []


# ── Önem Değerlendirmesi ──────────────────────────────────────────────────────

def _onem_skoru_hesapla(basliklar: list[str], tavily_sonuclar: list[dict]) -> tuple[int, str, str]:
    """
    Haber başlıklarını ve Tavily sonuçlarını değerlendir.
    Dönüş: (skor 1-10, olay_ozeti, aksiyon_onerileri)
    Skor ALARM_ESIK üzerindeyse bildirim gönderilir.
    """
    from web_arama import _api_key as tavily_key_kontrol

    # Tüm içeriği birleştir
    tum_icerik = "\n".join(basliklar[:15])
    for s in tavily_sonuclar[:3]:
        tum_icerik += f"\n{s.get('title', '')} — {s.get('content', '')[:200]}"

    if not tum_icerik.strip():
        return 0, "", ""

    prompt = f"""Aşağıdaki haber başlıklarını ve içeriklerini analiz et.
Piyasaları DERINDEN etkileyen kritik bir gelişme var mı?

{tum_icerik}

Yanıtını SADECE şu formatta ver (başka hiçbir şey yazma):
SKOR: [1-10 arası tam sayı — 8+ büyük şok, 6-7 önemli, 5 altı normal]
OLAY: [tek cümle — ne oldu, neden kritik]
AKSIYON: [AL/KAÇIN/İZLE — hangi varlık, neden, kısa]

Kritik eşik örnekleri (8+):
- Büyük güç savaşı başladı / tırmandı
- Merkez bankası acil faiz kararı
- Büyük ekonomi iflasına yakın
- Petrol %15+ fiyat şoku
- Büyük borsa çöküşü
- Nükleer tehdit / büyük terör
- G7/G20 acil toplantısı

Her zaman Türkçe yaz."""

    try:
        # Alarm sistemi her zaman Gemini kullanır (user_id yok)
        from app import llm_metin_uret
        yanit = llm_metin_uret(prompt, user_id=None)
    except Exception as e:
        logger.warning("Alarm önem değerlendirmesi başarısız: %s", e)
        return 0, "", ""

    # Parse et
    skor = 0
    olay = ""
    aksiyon = ""
    for satir in yanit.strip().splitlines():
        satir = satir.strip()
        if satir.upper().startswith("SKOR:"):
            try:
                skor = int(satir.split(":", 1)[1].strip().split()[0])
            except Exception:
                pass
        elif satir.upper().startswith("OLAY:"):
            olay = satir.split(":", 1)[1].strip()
        elif satir.upper().startswith("AKSIYON:"):
            aksiyon = satir.split(":", 1)[1].strip()

    return skor, olay, aksiyon


# ── Bildirim Mesajı ───────────────────────────────────────────────────────────

def _alarm_mesaji_olustur(skor: int, olay: str, aksiyon: str) -> str:
    """Telegram HTML formatında alarm mesajı oluştur."""
    import html
    e = html.escape

    if skor >= 9:
        ikon = "🚨🚨"
        baslik = "ACİL İKAZ"
    elif skor >= 8:
        ikon = "🚨"
        baslik = "KRİTİK UYARI"
    else:
        ikon = "⚠️"
        baslik = "ÖNEMLİ GELİŞME"

    simdi = datetime.now()
    saat = simdi.strftime("%H:%M")
    aylar = ("Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara")
    tarih = f"{simdi.day} {aylar[simdi.month-1]}"

    return (
        f"{ikon} <b>OKWIS {baslik}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<i>{e(tarih)} · {e(saat)}</i>\n\n"
        f"<b>{e(olay)}</b>\n\n"
        f"◆ <b>Aksiyon:</b> {e(aksiyon)}\n\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<i>Skor: {skor}/10 · Okwis otomatik tarama</i>\n"
        f"/analiz ile detaylı analiz yap"
    )


# ── Ana Tarama Fonksiyonu ─────────────────────────────────────────────────────

async def alarm_tara_ve_bildir(bot, plan_kayitlari_yukle_fn, kullanici_pro_mu_fn) -> None:
    """
    Arka plan görevi: haberleri tara, kritikse bildirim gönder.
    bot: telegram.Bot instance
    plan_kayitlari_yukle_fn: _plan_kayitlarini_yukle fonksiyonu
    kullanici_pro_mu_fn: _kullanici_pro_mu fonksiyonu
    """
    logger.info("Alarm taraması başlıyor...")

    # ── Veri topla ────────────────────────────────────────
    basliklar = _rss_basliklar_topla()
    tavily_sonuclar = _tavily_guncel_ara()

    if not basliklar and not tavily_sonuclar:
        logger.info("Alarm taraması: veri yok, atlandı")
        return

    # ── Önem değerlendir ──────────────────────────────────
    skor, olay, aksiyon = _onem_skoru_hesapla(basliklar, tavily_sonuclar)
    logger.info("Alarm skoru: %d — %s", skor, olay[:60] if olay else "(boş)")

    if skor < ALARM_ESIK:
        logger.info("Alarm eşiği aşılmadı (%d < %d), bildirim yok", skor, ALARM_ESIK)
        return

    if not olay:
        logger.warning("Alarm: skor yüksek ama olay boş, atlandı")
        return

    # ── Dedupe — aynı haberi tekrar gönderme ──────────────
    # Olay özetinin ilk 50 karakteri anahtar olarak kullan
    anahtar = olay[:50].lower().strip()
    if _alarm_daha_once_gonderildi_mi(anahtar):
        logger.info("Alarm zaten gönderildi (dedupe), atlandı")
        return

    # ── Alıcıları belirle: Pro + Claude, bildirimi açık ──
    plan_data = plan_kayitlarini_yukle_fn()
    alicilar: list[str] = []
    for uid, kayit in plan_data.items():
        plan = (kayit.get("plan") or "free").lower()
        if plan not in ("pro", "claude"):
            continue
        if not kullanici_bildirim_acik_mi(uid):
            continue
        alicilar.append(uid)

    if not alicilar:
        logger.info("Alarm: alıcı yok (Pro/Claude üye veya bildirim açık)")
        _alarm_gonderildi_kaydet(anahtar)
        return

    # ── Mesajı gönder ─────────────────────────────────────
    mesaj = _alarm_mesaji_olustur(skor, olay, aksiyon)
    basarili = 0
    for uid in alicilar:
        try:
            await bot.send_message(
                chat_id=int(uid),
                text=mesaj,
                parse_mode="HTML",
            )
            basarili += 1
        except Exception as e:
            logger.warning("Alarm gönderilemedi (user=%s): %s", uid, e)

    logger.info("Alarm gönderildi: skor=%d alıcı=%d/%d — %s",
                skor, basarili, len(alicilar), olay[:60])
    _alarm_gonderildi_kaydet(anahtar)
