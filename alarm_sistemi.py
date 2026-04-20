"""
Okwis AI — Alarm Sistemi (Geliştirilmiş)

Her 30 dakikada bir piyasayı etkileyen kritik gelişmeleri tarar.
Eşiği geçen olaylar Pro/Claude üyelere otomatik bildirim gönderir.

Yeni özellikler:
- Akıllı filtreleme: kullanıcının portföyüne göre alarm filtrele
- Spam önleme: günde max 3 alarm per kullanıcı
- Aciliyet seviyeleri: Kritik (8-10) / Önemli (6-7) / Bilgi (5)
- Portföy eşleşme skoru: portföydeki varlıkla ilgili alarmlar öncelikli
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, date
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_METRICS_DIR = Path(__file__).resolve().parent / "metrics"
_BILDIRIM_TERCIHLERI_PATH = _METRICS_DIR / "bildirim_tercihleri.json"
_GONDERILEN_ALARMLAR_PATH = _METRICS_DIR / "gonderilen_alarmlar.jsonl"
_GUNLUK_ALARM_PATH = _METRICS_DIR / "gunluk_alarm_sayaci.json"

# Tarama sıklığı (saniye)
ALARM_ARALIK_SANIYE = 1800  # 30 dakika

# Önem eşiği — bu skorun üzerindeki olaylar bildirim tetikler
ALARM_ESIK = 5  # 1-10 skalasında (5+ bildirim gönderilir)

# Günlük maksimum alarm sayısı per kullanıcı
GUNLUK_MAX_ALARM = 3

# Aynı haberden ikinci bildirim gönderimini önlemek için
_DEDUPE_PENCERE_SAAT = 6

# Aciliyet seviyeleri
ACILIYET_KRITIK = 8    # 8-10: Kritik
ACILIYET_ONEMLI = 6    # 6-7: Önemli
ACILIYET_BILGI = 5     # 5: Bilgi

# Alarm RSS kaynakları — jeopolitik + ekonomik odaklı
_ALARM_RSS_LISTESI = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
]
_RSS_TIMEOUT = 10.0


# ── Bildirim Tercihleri ───────────────────────────────────────────────────────

def bildirim_tercihleri_yukle() -> dict[str, dict]:
    """
    Kullanıcı bildirim tercihlerini yükle.
    Format: {user_id: {"acik": bool, "min_seviye": int, "portfoy_filtre": bool}}
    Geriye dönük uyumluluk: eski format {user_id: bool} de desteklenir.
    """
    if not _BILDIRIM_TERCIHLERI_PATH.exists():
        return {}
    try:
        with open(_BILDIRIM_TERCIHLERI_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Normalize: eski bool formatını yeni dict formatına çevir
        normalized = {}
        for k, v in data.items():
            if isinstance(v, bool):
                normalized[str(k)] = {"acik": v, "min_seviye": ACILIYET_BILGI, "portfoy_filtre": True}
            elif isinstance(v, dict):
                normalized[str(k)] = v
        return normalized
    except Exception as e:
        logger.warning("Bildirim tercihleri okunamadı: %s", e)
    return {}


def bildirim_tercihleri_kaydet(data: dict) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_BILDIRIM_TERCIHLERI_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Bildirim tercihleri kaydedilemedi: %s", e)


def kullanici_bildirim_acik_mi(user_id: int | str) -> bool:
    """Kullanıcının bildirimi açık mı? Varsayılan: açık (Pro/Claude için)."""
    tercihler = bildirim_tercihleri_yukle()
    tercih = tercihler.get(str(user_id))
    if tercih is None:
        return True  # Varsayılan açık
    if isinstance(tercih, dict):
        return tercih.get("acik", True)
    return bool(tercih)


def kullanici_bildirim_ayarla(user_id: int | str, acik: bool) -> None:
    tercihler = bildirim_tercihleri_yukle()
    uid = str(user_id)
    mevcut = tercihler.get(uid, {})
    if isinstance(mevcut, bool):
        mevcut = {"acik": mevcut, "min_seviye": ACILIYET_BILGI, "portfoy_filtre": True}
    mevcut["acik"] = acik
    tercihler[uid] = mevcut
    bildirim_tercihleri_kaydet(tercihler)


def kullanici_min_seviye_al(user_id: int | str) -> int:
    """Kullanıcının minimum alarm seviyesi (varsayılan: 5 = Bilgi)."""
    tercihler = bildirim_tercihleri_yukle()
    tercih = tercihler.get(str(user_id), {})
    if isinstance(tercih, dict):
        return int(tercih.get("min_seviye", ACILIYET_BILGI))
    return ACILIYET_BILGI


def kullanici_min_seviye_ayarla(user_id: int | str, seviye: int) -> None:
    """Minimum alarm seviyesini ayarla (5, 6 veya 8)."""
    tercihler = bildirim_tercihleri_yukle()
    uid = str(user_id)
    mevcut = tercihler.get(uid, {})
    if isinstance(mevcut, bool):
        mevcut = {"acik": mevcut, "min_seviye": ACILIYET_BILGI, "portfoy_filtre": True}
    mevcut["min_seviye"] = seviye
    tercihler[uid] = mevcut
    bildirim_tercihleri_kaydet(tercihler)


def kullanici_portfoy_filtre_al(user_id: int | str) -> bool:
    """Portföy filtresi açık mı? (varsayılan: True)"""
    tercihler = bildirim_tercihleri_yukle()
    tercih = tercihler.get(str(user_id), {})
    if isinstance(tercih, dict):
        return bool(tercih.get("portfoy_filtre", True))
    return True


def kullanici_portfoy_filtre_ayarla(user_id: int | str, acik: bool) -> None:
    """Portföy filtresini aç/kapat."""
    tercihler = bildirim_tercihleri_yukle()
    uid = str(user_id)
    mevcut = tercihler.get(uid, {})
    if isinstance(mevcut, bool):
        mevcut = {"acik": mevcut, "min_seviye": ACILIYET_BILGI, "portfoy_filtre": True}
    mevcut["portfoy_filtre"] = acik
    tercihler[uid] = mevcut
    bildirim_tercihleri_kaydet(tercihler)


# ── Günlük Alarm Sayacı ───────────────────────────────────────────────────────

def _gunluk_alarm_sayaci_yukle() -> dict[str, dict]:
    """Format: {user_id: {"tarih": "2026-04-20", "sayac": 2}}"""
    if not _GUNLUK_ALARM_PATH.exists():
        return {}
    try:
        with open(_GUNLUK_ALARM_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _gunluk_alarm_sayaci_kaydet(data: dict) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_GUNLUK_ALARM_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Günlük alarm sayacı kaydedilemedi: %s", e)


def kullanici_gunluk_alarm_sayisi(user_id: int | str) -> int:
    """Bugün bu kullanıcıya kaç alarm gönderildi?"""
    sayac_data = _gunluk_alarm_sayaci_yukle()
    uid = str(user_id)
    bugun = date.today().isoformat()
    kayit = sayac_data.get(uid, {})
    if kayit.get("tarih") != bugun:
        return 0
    return int(kayit.get("sayac", 0))


def _gunluk_alarm_artir(user_id: int | str) -> None:
    """Kullanıcının günlük alarm sayacını 1 artır."""
    sayac_data = _gunluk_alarm_sayaci_yukle()
    uid = str(user_id)
    bugun = date.today().isoformat()
    kayit = sayac_data.get(uid, {})
    if kayit.get("tarih") != bugun:
        kayit = {"tarih": bugun, "sayac": 0}
    kayit["sayac"] = kayit.get("sayac", 0) + 1
    sayac_data[uid] = kayit
    _gunluk_alarm_sayaci_kaydet(sayac_data)


def kullanici_gunluk_limit_doldu_mu(user_id: int | str) -> bool:
    """Kullanıcı günlük alarm limitine ulaştı mı?"""
    return kullanici_gunluk_alarm_sayisi(user_id) >= GUNLUK_MAX_ALARM


# ── Portföy Eşleşme ───────────────────────────────────────────────────────────

def _portfoy_varlik_listesi(user_id: int | str) -> list[str]:
    """Kullanıcının portföyündeki varlık sembollerini döndür."""
    try:
        from portfoy import kullanici_portfoy_al
        portfoy = kullanici_portfoy_al(user_id)
        varliklar = portfoy.get("varliklar", [])
        semboller = []
        for v in varliklar:
            semboller.append(v.get("sembol", "").lower())
            # Yaygın eş anlamlılar
            sembol = v.get("sembol", "").upper()
            if sembol == "BTC":
                semboller.extend(["bitcoin", "btc"])
            elif sembol == "ETH":
                semboller.extend(["ethereum", "eth"])
            elif sembol in ("ALTIN", "XAU"):
                semboller.extend(["gold", "altin", "altın", "xau"])
            elif sembol in ("PETROL", "OIL", "WTI"):
                semboller.extend(["oil", "petrol", "crude", "wti", "brent"])
        return list(set(semboller))
    except Exception:
        return []


def _alarm_portfoy_ilgili_mi(olay: str, aksiyon: str, user_id: int | str) -> bool:
    """
    Alarm kullanıcının portföyüyle ilgili mi?
    Portföy filtresi kapalıysa her zaman True döner.
    Portföy boşsa her zaman True döner (genel alarmlar göster).
    """
    if not kullanici_portfoy_filtre_al(user_id):
        return True

    varliklar = _portfoy_varlik_listesi(user_id)
    if not varliklar:
        return True  # Portföy yoksa tüm alarmları göster

    icerik = (olay + " " + aksiyon).lower()

    # Genel piyasa kelimeleri — her zaman ilgili
    genel_kelimeler = [
        "market", "piyasa", "borsa", "faiz", "enflasyon", "dolar",
        "fed", "merkez bankası", "recession", "kriz", "crash", "war",
        "savaş", "ekonomi", "gdp", "büyüme", "küresel", "global",
    ]
    for kelime in genel_kelimeler:
        if kelime in icerik:
            return True

    # Portföydeki varlıklar
    for varlik in varliklar:
        if varlik and varlik in icerik:
            return True

    return False


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
    """
    # Tüm içeriği birleştir
    tum_icerik = "\n".join(basliklar[:15])
    for s in tavily_sonuclar[:3]:
        tum_icerik += f"\n{s.get('title', '')} — {s.get('content', '')[:200]}"

    if not tum_icerik.strip():
        return 0, "", ""

    prompt = f"""Aşağıdaki haber başlıklarını ve içeriklerini analiz et.
Piyasaları etkileyen önemli bir gelişme var mı?

{tum_icerik}

Yanıtını SADECE şu formatta ver (başka hiçbir şey yazma):
SKOR: [1-10 arası tam sayı]
OLAY: [tek cümle — ne oldu, neden önemli]
AKSIYON: [AL/KAÇIN/İZLE — hangi varlık, neden, kısa]

Skor rehberi:
8-10 KRİTİK: Büyük güç savaşı, merkez bankası acil kararı, büyük borsa çöküşü, petrol %15+ şok, nükleer tehdit
6-7 ÖNEMLİ: Jeopolitik gerilim tırmanması, önemli ekonomik veri sürprizi, büyük şirket iflası, OPEC kararı
5 BİLGİ: Dikkat çekici piyasa hareketi, önemli siyasi gelişme, sektörel etki
1-4 NORMAL: Rutin haberler, beklenen gelişmeler

Her zaman Türkçe yaz."""

    try:
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


# ── Aciliyet Seviyesi ─────────────────────────────────────────────────────────

def _aciliyet_bilgisi(skor: int) -> tuple[str, str, str]:
    """
    Skora göre aciliyet bilgisi döndür.
    Returns: (seviye_adi, ikon, renk_etiketi)
    """
    if skor >= ACILIYET_KRITIK:
        return "KRİTİK", "🔴", "kritik"
    elif skor >= ACILIYET_ONEMLI:
        return "ÖNEMLİ", "🟡", "onemli"
    else:
        return "BİLGİ", "🟢", "bilgi"


# ── Bildirim Mesajı ───────────────────────────────────────────────────────────

def _alarm_mesaji_olustur(skor: int, olay: str, aksiyon: str, portfoy_ilgili: bool = False) -> str:
    """Telegram HTML formatında alarm mesajı oluştur."""
    import html
    e = html.escape

    seviye_adi, seviye_ikon, _ = _aciliyet_bilgisi(skor)

    simdi = datetime.now()
    saat = simdi.strftime("%H:%M")
    aylar = ("Oca","Şub","Mar","Nis","May","Haz","Tem","Ağu","Eyl","Eki","Kas","Ara")
    tarih = f"{simdi.day} {aylar[simdi.month-1]}"

    portfoy_notu = "\n◈ <i>Portföyünle ilgili</i>" if portfoy_ilgili else ""

    return (
        f"{seviye_ikon} <b>OKWIS {seviye_adi}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<i>{e(tarih)} · {e(saat)}</i>{portfoy_notu}\n\n"
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

    Filtreler (sırayla):
    1. Skor >= ALARM_ESIK (5)
    2. Dedupe: aynı haber son 6 saatte gönderilmedi
    3. Kullanıcı bazlı:
       a. Pro/Claude plan
       b. Bildirim açık
       c. Günlük limit (max 3)
       d. Min seviye filtresi (kullanıcı ayarı)
       e. Portföy filtresi (portföy varsa ilgili alarmlar)
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
    anahtar = olay[:50].lower().strip()
    if _alarm_daha_once_gonderildi_mi(anahtar):
        logger.info("Alarm zaten gönderildi (dedupe), atlandı")
        return

    # ── Aciliyet seviyesi ─────────────────────────────────
    seviye_adi, seviye_ikon, _ = _aciliyet_bilgisi(skor)

    # ── Alıcıları belirle ve filtrele ─────────────────────
    plan_data = plan_kayitlari_yukle_fn()
    alicilar_gonderilecek: list[tuple[str, bool]] = []  # (user_id, portfoy_ilgili)

    for uid, kayit in plan_data.items():
        plan = (kayit.get("plan") or "free").lower()
        if plan not in ("pro", "claude"):
            continue

        # Bildirim açık mı?
        if not kullanici_bildirim_acik_mi(uid):
            continue

        # Günlük limit doldu mu?
        if kullanici_gunluk_limit_doldu_mu(uid):
            logger.debug("Alarm: user=%s günlük limit doldu (%d/%d)", uid, kullanici_gunluk_alarm_sayisi(uid), GUNLUK_MAX_ALARM)
            continue

        # Minimum seviye filtresi
        min_seviye = kullanici_min_seviye_al(uid)
        if skor < min_seviye:
            logger.debug("Alarm: user=%s min seviye filtresi (%d < %d)", uid, skor, min_seviye)
            continue

        # Portföy filtresi
        portfoy_ilgili = _alarm_portfoy_ilgili_mi(olay, aksiyon, uid)
        if not portfoy_ilgili:
            logger.debug("Alarm: user=%s portföy filtresi — ilgisiz alarm atlandı", uid)
            continue

        alicilar_gonderilecek.append((uid, portfoy_ilgili))

    if not alicilar_gonderilecek:
        logger.info("Alarm: filtreler sonrası alıcı yok (skor=%d, seviye=%s)", skor, seviye_adi)
        _alarm_gonderildi_kaydet(anahtar)
        return

    # ── Mesajı gönder ─────────────────────────────────────
    basarili = 0
    for uid, portfoy_ilgili in alicilar_gonderilecek:
        mesaj = _alarm_mesaji_olustur(skor, olay, aksiyon, portfoy_ilgili)
        try:
            await bot.send_message(
                chat_id=int(uid),
                text=mesaj,
                parse_mode="HTML",
            )
            _gunluk_alarm_artir(uid)
            basarili += 1
        except Exception as e:
            logger.warning("Alarm gönderilemedi (user=%s): %s", uid, e)

    logger.info(
        "Alarm gönderildi: skor=%d seviye=%s alıcı=%d/%d — %s",
        skor, seviye_adi, basarili, len(alicilar_gonderilecek), olay[:60]
    )
    _alarm_gonderildi_kaydet(anahtar)
