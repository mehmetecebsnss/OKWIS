"""
Makro Lens — Telegram Yatırım Asistanı
MVP — Mevsim ve Hava modları (OpenWeatherMap ile canlı hava).
"""

import asyncio
from collections import defaultdict
import html
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import CallbackQuery, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from hava_baglam import HavaModuHatasi, topla_hava_baglami
from jeopolitik_baglam import topla_jeopolitik_baglami
from mevsim_baglam import topla_mevsim_baglami

# ─── Ayarlar ──────────────────────────────────────────────────────────────────

load_dotenv()  # .env dosyasını yükle

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
# gemini: önce tüm Gemini anahtarları (sırayla); deepseek: önce DeepSeek, sonra yedek Gemini
AI_PROVIDER = (os.getenv("AI_PROVIDER") or "gemini").strip().lower()
DEEPSEEK_MODEL = (os.getenv("DEEPSEEK_MODEL") or "deepseek-chat").strip()
DEEPSEEK_BASE_URL = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()
AI_FALLBACK_GEMINI = (os.getenv("AI_FALLBACK_GEMINI") or "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Gemini kotası bitince DeepSeek dene (DEEPSEEK_API_KEY varsa varsayılan açık)
_raw_fb_ds = os.getenv("AI_FALLBACK_DEEPSEEK")
if _raw_fb_ds is None:
    AI_FALLBACK_DEEPSEEK = bool(DEEPSEEK_API_KEY)
else:
    AI_FALLBACK_DEEPSEEK = _raw_fb_ds.strip().lower() in ("1", "true", "yes", "on")

_deepseek_client = None


def _gemini_anahtarlari() -> list[str]:
    """Sırayla: GEMINI_API_KEYS (virgülle), GEMINI_API_KEY, _2, _3 — yinelenmez."""
    sira: list[str] = []
    gorduk: set[str] = set()
    ham = (os.getenv("GEMINI_API_KEYS") or "").strip()
    if ham:
        for parca in ham.split(","):
            k = parca.strip()
            if k and k not in gorduk:
                gorduk.add(k)
                sira.append(k)
    for ad in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"):
        k = (os.getenv(ad) or "").strip()
        if k and k not in gorduk:
            gorduk.add(k)
            sira.append(k)
    return sira


def _get_deepseek_client():
    global _deepseek_client
    if _deepseek_client is None:
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY eksik")
        try:
            from openai import OpenAI
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "openai paketi yüklü değil. Proje klasöründe: pip install openai"
            ) from e
        _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _deepseek_client


def _gemini_metin_uret_anahtarla(prompt: str, api_key: str) -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    response = model.generate_content(prompt)
    text = getattr(response, "text", None) or ""
    return str(text).strip()


def _gemini_kota_tarzi_mi(exc: BaseException) -> bool:
    """Bu anahtarla yeniden denemek (sıradaki anahtar veya DeepSeek) mantıklı mı?"""
    msg = str(exc).lower()
    if "429" in msg or "quota" in msg or "resource exhausted" in msg:
        return True
    if "rate" in msg and "limit" in msg:
        return True
    if "503" in msg or "overloaded" in msg:
        return True
    return False


def _gemini_tum_anahtarlarla_dene(prompt: str) -> str:
    keys = _gemini_anahtarlari()
    if not keys:
        raise RuntimeError(
            "GEMINI_API_KEY (veya GEMINI_API_KEY_2 / _3 / GEMINI_API_KEYS) tanımlı değil"
        )
    son_hata: BaseException | None = None
    for idx, key in enumerate(keys):
        try:
            out = _gemini_metin_uret_anahtarla(prompt, key)
            if not out:
                raise RuntimeError("Model boş yanıt döndü")
            return out
        except Exception as e:
            son_hata = e
            if idx < len(keys) - 1 and _gemini_kota_tarzi_mi(e):
                logger.warning(
                    "Gemini anahtar %s/%s başarısız (kota vb.), sıradaki deneniyor: %s",
                    idx + 1,
                    len(keys),
                    e,
                )
                continue
            raise
    if son_hata:
        raise son_hata
    raise RuntimeError("Gemini yanıt üretilemedi")


def _deepseek_metin_uret(prompt: str) -> str:
    client = _get_deepseek_client()
    r = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    choice = (r.choices or [None])[0]
    msg = choice.message if choice else None
    text = (getattr(msg, "content", None) or "") if msg else ""
    return str(text).strip()


def _deepseek_hatasi_gemini_yedegi_uygun(exc: BaseException) -> bool:
    """DeepSeek başarısız → Gemini yedeği uygun mu?"""
    msg = str(exc).lower()
    if "401" in msg and ("invalid" in msg or "incorrect" in msg or "unauthorized" in msg):
        return False
    anahtarlar = (
        "402",
        "403",
        "insufficient",
        "balance",
        "billing",
        "payment",
        "credit",
        "exceeded",
        "quota",
        "not enough",
        "rate limit",
        "timeout",
        "timed out",
    )
    return any(k in msg for k in anahtarlar)


def llm_metin_uret(prompt: str) -> str:
    """
    Mevsim / Hava analizleri için tek LLM giriş noktası.

    - AI_PROVIDER=gemini (varsayılan): tüm GEMINI anahtarları sırayla; kota benzeri hata → sıradaki anahtar.
      Tüm anahtarlar bittiyse veya AI_FALLBACK_DEEPSEEK + DEEPSEEK_API_KEY → DeepSeek.
    - AI_PROVIDER=deepseek: önce DeepSeek; openai yoksa veya hata + AI_FALLBACK_GEMINI → Gemini anahtarları.
    """
    keys = _gemini_anahtarlari()

    if AI_PROVIDER == "deepseek":
        try:
            out = _deepseek_metin_uret(prompt)
            if not out:
                raise RuntimeError("Model boş yanıt döndü")
            return out
        except ModuleNotFoundError as e:
            logger.warning("openai yüklü değil, Gemini anahtarlarına düşülüyor: %s", e)
            if keys:
                return _gemini_tum_anahtarlarla_dene(prompt)
            raise
        except Exception as e:
            if (
                AI_FALLBACK_GEMINI
                and keys
                and _deepseek_hatasi_gemini_yedegi_uygun(e)
            ):
                logger.warning("DeepSeek başarısız, Gemini anahtarları deneniyor: %s", e)
                return _gemini_tum_anahtarlarla_dene(prompt)
            raise

    if AI_PROVIDER not in ("gemini", ""):
        logger.warning("Bilinmeyen AI_PROVIDER=%s; gemini sırası kullanılıyor", AI_PROVIDER)

    try:
        return _gemini_tum_anahtarlarla_dene(prompt)
    except Exception as ge:
        if AI_FALLBACK_DEEPSEEK and DEEPSEEK_API_KEY:
            try:
                logger.warning("Gemini zinciri başarısız, DeepSeek deneniyor: %s", ge)
                out = _deepseek_metin_uret(prompt)
                if not out:
                    raise RuntimeError("Model boş yanıt döndü") from ge
                return out
            except ModuleNotFoundError as ie:
                logger.error("DeepSeek için openai gerekli: %s", ie)
                raise ge from ie
        raise

# ─── Konuşma adımları (state machine) ────────────────────────────────────────

MOD_SECIMI = 0       # Kullanıcı analiz modu seçiyor (Mevsim vb.)
ULKE_SECIMI = 1      # Kullanıcı ülke seçiyor
FORMAT_SECIMI = 2    # Çıktı: uzun anlatım / kısa özet

# Çıktı stilleri (mevsim analizi)
CIKTI_DETAY = "detay"
CIKTI_OZET = "ozet"

# Analiz türü (mesaj başlığı / bağlam)
ANALIZ_MEVSIM = "mevsim"
ANALIZ_HAVA = "hava"
ANALIZ_JEOPOLITIK = "jeopolitik"

# Telegram bot mesaj limiti (HTML dahil tüm metin)
TELEGRAM_MAX_UZUNLUK = 4096

# ─── Sabitler ─────────────────────────────────────────────────────────────────

ULKELER = ["Türkiye", "ABD", "Almanya", "İngiltere", "Japonya", "Çin", "Diğer"]
_METRICS_DIR = Path(__file__).resolve().parent / "metrics"
_ANALIZ_OLAYLARI_PATH = _METRICS_DIR / "analiz_olaylari.jsonl"
_KULLANIM_LIMIT_PATH = _METRICS_DIR / "kullanim_limitleri.json"
_PLAN_KAYIT_PATH = _METRICS_DIR / "plan_kullanicilari.json"
_ODEME_OLAYLARI_PATH = _METRICS_DIR / "odeme_olaylari.jsonl"
ANALIZ_GUNLUK_LIMIT = int((os.getenv("ANALIZ_GUNLUK_LIMIT") or "3").strip() or 3)
ADMIN_USER_IDS = {
    int(x.strip())
    for x in (os.getenv("ADMIN_USER_IDS") or "").split(",")
    if x.strip().isdigit()
}

# Uyarı politikası (plan / MIMARI): kısa metin her zaman bot şablonuyla; model uzun disclaimer üretmez.
ANALIZ_FOOTER = (
    "\n\n—\n"
    "Bilgilendirme amaçlıdır; yatırım tavsiyesi değildir. "
    "Yatırım kararı için kendi araştırmanı yap."
)


def _tg_html_escape(text: str) -> str:
    """Telegram HTML modu için model/ kullanıcı metnini güvenle kaçır."""
    return html.escape(text or "", quote=False)


def telegram_html_parcalara_bol(metin: str, ust_sinir: int = TELEGRAM_MAX_UZUNLUK) -> list[str]:
    """
    HTML’i satır sınırlarından bölerek parçalar; her parça ust_sinir’i aşmaz.
    Uzun tek satırda sert kesim yapılır (nadir).
    """
    metin = metin or ""
    if len(metin) <= ust_sinir:
        return [metin]

    parcalar: list[str] = []
    satirlar = metin.split("\n")
    buf: list[str] = []
    buf_uzunluk = 0

    def buf_flush() -> None:
        nonlocal buf, buf_uzunluk
        if buf:
            parcalar.append("\n".join(buf))
            buf = []
            buf_uzunluk = 0

    for satir in satirlar:
        satir_uzun = len(satir)
        ek = satir_uzun + (1 if buf else 0)

        if satir_uzun > ust_sinir:
            buf_flush()
            k = satir
            while len(k) > ust_sinir:
                parcalar.append(k[:ust_sinir])
                k = k[ust_sinir:]
            if k:
                buf = [k]
                buf_uzunluk = len(k)
            continue

        if buf_uzunluk + ek > ust_sinir:
            buf_flush()

        buf.append(satir)
        buf_uzunluk += ek

    buf_flush()
    return parcalar if parcalar else [metin[:ust_sinir]]


def _llm_hata_kullanici_metni(exc: BaseException) -> str:
    """Log’da tam istisna; kullanıcıya kısa Türkçe (Gemini / DeepSeek)."""
    msg = str(exc).lower()
    if isinstance(exc, ModuleNotFoundError) and "openai" in msg:
        return (
            "DeepSeek için `openai` paketi yüklü değil. "
            "Botu çalıştırdığın Python ile: pip install openai "
            "(veya pip install -r requirements.txt)"
        )
    if "no module named 'openai'" in msg:
        return (
            "DeepSeek için `openai` paketi gerekli. "
            "Terminalde: pip install openai"
        )
    if "402" in msg or "insufficient" in msg or "balance" in msg or "billing" in msg:
        return (
            "Yapay zekâ sağlayıcısında bakiye veya kota yetersiz görünüyor. "
            ".env içinde AI_PROVIDER=gemini ile devam edebilir veya DeepSeek hesabını kontrol edebilirsin."
        )
    if "429" in msg or "quota" in msg or "resource exhausted" in msg:
        return (
            "Yapay zekâ servisi şu an yoğun veya kotayı doldurmuş olabilir. "
            "Bir süre sonra tekrar dene."
        )
    if "timeout" in msg or "deadline" in msg:
        return "İstek zaman aşımına uğradı. Bağlantını kontrol edip tekrar dene."
    if "api key" in msg or "api_key" in msg or "invalid" in msg and "key" in msg:
        return "API anahtarı geçersiz veya eksik görünüyor. Yöneticiye bildir."
    if "blocked" in msg or "safety" in msg:
        return "Model bu isteği güvenlik filtresi nedeniyle tamamlayamadı. Farklı ülke veya mod dene."
    return "Analiz üretilirken beklenmeyen bir hata oluştu. Biraz sonra tekrar dene."


def _guven_etiketi(score: int) -> str:
    if score >= 80:
        return "🟢 Çok yüksek"
    if score >= 60:
        return "🟢 Yüksek"
    if score >= 40:
        return "🟡 Orta"
    if score >= 20:
        return "🟠 Düşük"
    return "🔴 Çok düşük"


def _guven_skoru_hesapla(analiz_turu: str, baglam_metni: str) -> dict[str, int | str]:
    """
    Parça K (v1): hızlı ve açıklanabilir güven skoru.
    V1 yaklaşımı: veri kalitesi + mod baz performans + sinyal netliği + benzer durum yakınsaması (heuristic).
    """
    metin = (baglam_metni or "").lower()

    mbp_tabani = {
        ANALIZ_MEVSIM: 88,
        ANALIZ_HAVA: 74,
        ANALIZ_JEOPOLITIK: 62,
    }
    mbp = mbp_tabani.get(analiz_turu, 60)

    negatif_isaretler = (
        "alınamadı",
        "oluşturulamadı",
        "boş",
        "hata",
        "ayrıştırılamadı",
        "geçici",
    )
    negatif_sayi = sum(1 for k in negatif_isaretler if k in metin)
    vkg = max(15, 90 - negatif_sayi * 18)

    # Sinyal netliği: daha çok somut satır = daha net.
    satir_skoru = min((baglam_metni or "").count("- "), 10)
    mbs = min(85, 45 + satir_skoru * 4)
    if "olası" in metin or "dolaylı" in metin:
        mbs = max(35, mbs - 4)

    # Benzer durum başarısı (v1): mod tabanı + veri kalitesi katkısı.
    gdb = min(90, max(35, mbp - 8 + int((vkg - 50) * 0.3)))

    toplam = int(round(gdb * 0.40 + mbs * 0.30 + vkg * 0.15 + mbp * 0.15))
    return {
        "toplam": toplam,
        "etiket": _guven_etiketi(toplam),
        "gdb": int(gdb),
        "mbs": int(mbs),
        "vkg": int(vkg),
        "mbp": int(mbp),
    }


def _analiz_olayi_kaydet(
    *,
    analiz_turu: str,
    ulke: str,
    cikti_stili: str,
    guven: dict[str, int | str],
    baglam_metni: str,
) -> None:
    """
    Parça K v1.5: güven skorunu ve temel özellikleri JSONL olarak kalıcı logla.
    Bu kayıtlar ileride `/performans` ve mod karnesi için veri kaynağı olacak.
    """
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        olay = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "mod": analiz_turu,
            "ulke": ulke,
            "cikti_stili": cikti_stili,
            "guven_toplam": guven.get("toplam"),
            "guven_etiket": guven.get("etiket"),
            "gdb": guven.get("gdb"),
            "mbs": guven.get("mbs"),
            "vkg": guven.get("vkg"),
            "mbp": guven.get("mbp"),
            "baglam_uzunluk": len(baglam_metni or ""),
            "baglam_madde_sayisi": (baglam_metni or "").count("- "),
        }
        with open(_ANALIZ_OLAYLARI_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(olay, ensure_ascii=False) + "\n")
        logger.info(
            "Güven olayı kaydedildi: mod=%s skor=%s etiket=%s dosya=%s",
            analiz_turu,
            guven.get("toplam"),
            guven.get("etiket"),
            _ANALIZ_OLAYLARI_PATH.name,
        )
    except Exception as e:
        logger.warning("Analiz olayı kaydedilemedi: %s", e)


def _kullanim_limitleri_yukle() -> dict[str, dict[str, int]]:
    if not _KULLANIM_LIMIT_PATH.exists():
        return {}
    try:
        with open(_KULLANIM_LIMIT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            out: dict[str, dict[str, int]] = {}
            for uid, val in data.items():
                if isinstance(val, dict):
                    out[str(uid)] = {
                        str(k): int(v) for k, v in val.items() if isinstance(v, (int, float))
                    }
            return out
    except Exception as e:
        logger.warning("Kullanım limit dosyası okunamadı: %s", e)
    return {}


def _kullanim_limitleri_kaydet(data: dict[str, dict[str, int]]) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_KULLANIM_LIMIT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Kullanım limit dosyası yazılamadı: %s", e)


def _gunluk_kullanim_oku(user_id: int | str, gun: str | None = None) -> int:
    gun = gun or date.today().isoformat()
    data = _kullanim_limitleri_yukle()
    return int(data.get(str(user_id), {}).get(gun, 0))


def _gunluk_kullanim_arttir(user_id: int | str, gun: str | None = None) -> int:
    gun = gun or date.today().isoformat()
    data = _kullanim_limitleri_yukle()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {}
    yeni = int(data[uid].get(gun, 0)) + 1
    data[uid][gun] = yeni
    _kullanim_limitleri_kaydet(data)
    return yeni


def _gunluk_limit_asildi_mi(user_id: int | str, limit: int = ANALIZ_GUNLUK_LIMIT) -> tuple[bool, int]:
    kullanilan = _gunluk_kullanim_oku(user_id)
    return (kullanilan >= limit, kullanilan)


def _plan_kayitlarini_yukle() -> dict[str, dict[str, str]]:
    if not _PLAN_KAYIT_PATH.exists():
        return {}
    try:
        with open(_PLAN_KAYIT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            out: dict[str, dict[str, str]] = {}
            for uid, val in data.items():
                if not isinstance(val, dict):
                    continue
                plan = str(val.get("plan") or "free")
                pro_until = str(val.get("pro_until") or "")
                out[str(uid)] = {"plan": plan, "pro_until": pro_until}
            return out
    except Exception as e:
        logger.warning("Plan kayıt dosyası okunamadı: %s", e)
    return {}


def _plan_kayitlarini_kaydet(data: dict[str, dict[str, str]]) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_PLAN_KAYIT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        logger.warning("Plan kayıt dosyası yazılamadı: %s", e)


def _odeme_olayi_kaydet(
    *,
    action: str,
    hedef_user_id: int | str,
    admin_user_id: int | str | None = None,
    detail: str = "",
) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        olay = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "hedef_user_id": str(hedef_user_id),
            "admin_user_id": str(admin_user_id) if admin_user_id is not None else "",
            "detail": detail,
        }
        with open(_ODEME_OLAYLARI_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(olay, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Ödeme olayı kaydedilemedi: %s", e)


def _tarih_parse_iso(v: str) -> date | None:
    try:
        return date.fromisoformat(v)
    except Exception:
        return None


def _kullanici_plan_bilgisi(user_id: int | str) -> dict[str, str]:
    uid = str(user_id)
    data = _plan_kayitlarini_yukle()
    kayit = data.get(uid, {"plan": "free", "pro_until": ""})
    plan = str(kayit.get("plan") or "free").lower()
    pro_until = str(kayit.get("pro_until") or "")

    # Süresi dolmuş pro kayıtlarını otomatik free yap.
    if plan == "pro" and pro_until:
        bitis = _tarih_parse_iso(pro_until)
        if bitis is not None and bitis < date.today():
            data[uid] = {"plan": "free", "pro_until": ""}
            _plan_kayitlarini_kaydet(data)
            _odeme_olayi_kaydet(
                action="auto_expire",
                hedef_user_id=uid,
                detail=f"pro_until={pro_until}",
            )
            return {"plan": "free", "pro_until": ""}
    return {"plan": plan, "pro_until": pro_until}


def _kullanici_pro_mu(user_id: int | str) -> bool:
    info = _kullanici_plan_bilgisi(user_id)
    return info.get("plan") == "pro"


def _kalan_pro_gun(pro_until: str) -> int:
    bitis = _tarih_parse_iso(pro_until)
    if bitis is None:
        return 0
    return max((bitis - date.today()).days, 0)


def _admin_mi(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in ADMIN_USER_IDS


def _odeme_kayit_son_n(n: int = 10) -> list[dict[str, str]]:
    if not _ODEME_OLAYLARI_PATH.exists():
        return []
    satirlar: list[dict[str, str]] = []
    try:
        with open(_ODEME_OLAYLARI_PATH, encoding="utf-8") as f:
            for satir in f:
                s = satir.strip()
                if not s:
                    continue
                try:
                    o = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if not isinstance(o, dict):
                    continue
                satirlar.append(
                    {
                        "ts_utc": str(o.get("ts_utc") or ""),
                        "action": str(o.get("action") or ""),
                        "hedef_user_id": str(o.get("hedef_user_id") or ""),
                        "admin_user_id": str(o.get("admin_user_id") or ""),
                        "detail": str(o.get("detail") or ""),
                    }
                )
    except Exception as e:
        logger.warning("Ödeme logu okunamadı: %s", e)
        return []
    return satirlar[-max(n, 1):]


def _performans_ozeti_hesapla() -> str:
    """
    JSONL analiz olaylarından canlı özet üretir.
    Dönüş: Telegram HTML uyumlu kısa metin.
    """
    if not _ANALIZ_OLAYLARI_PATH.exists():
        return (
            "<b>📈 Canlı performans</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "Henüz kayıt yok. Önce birkaç analiz çalıştırıp tekrar dene."
        )

    olaylar: list[dict[str, object]] = []
    try:
        with open(_ANALIZ_OLAYLARI_PATH, encoding="utf-8") as f:
            for satir in f:
                s = satir.strip()
                if not s:
                    continue
                try:
                    olay = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if isinstance(olay, dict):
                    olaylar.append(olay)
    except Exception as e:
        logger.warning("Performans dosyası okunamadı: %s", e)
        return (
            "<b>📈 Canlı performans</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "Performans verisi okunamadı. Biraz sonra tekrar dene."
        )

    if not olaylar:
        return (
            "<b>📈 Canlı performans</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "Kayıt dosyası boş görünüyor. Önce birkaç analiz çalıştır."
        )

    simdi = datetime.now(timezone.utc)
    son_7 = simdi.timestamp() - 7 * 24 * 3600
    son_30 = simdi.timestamp() - 30 * 24 * 3600

    def ts_to_epoch(v: object) -> float | None:
        if not isinstance(v, str):
            return None
        try:
            return datetime.fromisoformat(v).timestamp()
        except Exception:
            return None

    toplam = len(olaylar)
    son7 = 0
    son30 = 0

    mod_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "n": 0.0,
            "sum": 0.0,
            "low": 0.0,
            "n7": 0.0,
            "sum7": 0.0,
            "low7": 0.0,
            "n30": 0.0,
            "sum30": 0.0,
        }
    )

    for o in olaylar:
        ts = ts_to_epoch(o.get("ts_utc"))
        if ts is not None:
            if ts >= son_7:
                son7 += 1
            if ts >= son_30:
                son30 += 1

        mod = str(o.get("mod") or "bilinmeyen")
        score_raw = o.get("guven_toplam")
        try:
            score = float(score_raw)
        except Exception:
            continue

        mod_stats[mod]["n"] += 1
        mod_stats[mod]["sum"] += score
        if score < 40:
            mod_stats[mod]["low"] += 1
        if ts is not None:
            if ts >= son_7:
                mod_stats[mod]["n7"] += 1
                mod_stats[mod]["sum7"] += score
                if score < 40:
                    mod_stats[mod]["low7"] += 1
            if ts >= son_30:
                mod_stats[mod]["n30"] += 1
                mod_stats[mod]["sum30"] += score

    satirlar = [
        "<b>📈 Canlı performans</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "",
        f"Toplam kayıt: <b>{toplam}</b>",
        f"Son 7 gün: <b>{son7}</b> · Son 30 gün: <b>{son30}</b>",
        "",
        "<b>Mod bazlı karşılaştırma</b>",
    ]

    etiket = {
        ANALIZ_MEVSIM: "Mevsim",
        ANALIZ_HAVA: "Hava",
        ANALIZ_JEOPOLITIK: "Jeopolitik",
    }
    sira = [ANALIZ_MEVSIM, ANALIZ_HAVA, ANALIZ_JEOPOLITIK]

    def trend_oku(avg7: float | None, avg30: float | None) -> str:
        if avg7 is None or avg30 is None:
            return "→ yatay"
        fark = avg7 - avg30
        if fark >= 3:
            return "↗ yükseliş"
        if fark <= -3:
            return "↘ düşüş"
        return "→ yatay"

    siralama: list[tuple[str, float]] = []
    en_dusuk_guven_modu: tuple[str, float, int] | None = None
    alarm_satirlari: list[str] = []

    for mod in sira:
        st = mod_stats.get(mod)
        if not st or st["n"] <= 0:
            continue
        avg = st["sum"] / st["n"]
        low_pct = (st["low"] / st["n"]) * 100
        avg7 = (st["sum7"] / st["n7"]) if st["n7"] > 0 else None
        avg30 = (st["sum30"] / st["n30"]) if st["n30"] > 0 else None
        trend = trend_oku(avg7, avg30)
        a7_text = f"{avg7:.1f}" if avg7 is not None else "—"
        a30_text = f"{avg30:.1f}" if avg30 is not None else "—"
        satirlar.append(
            f"- {etiket.get(mod, mod)}: ort <b>{avg:.1f}</b> | 7g <b>{a7_text}</b> / 30g <b>{a30_text}</b> ({trend}), düşük güven <b>%{low_pct:.0f}</b> (n={int(st['n'])})"
        )
        siralama.append((mod, avg))

        n_int = int(st["n"])
        if en_dusuk_guven_modu is None or low_pct > en_dusuk_guven_modu[1]:
            en_dusuk_guven_modu = (mod, low_pct, n_int)

        if st["n7"] > 0:
            low7_pct = (st["low7"] / st["n7"]) * 100
            if low7_pct >= 35:
                alarm_satirlari.append(
                    f"- {etiket.get(mod, mod)}: son 7 günde düşük güven oranı <b>%{low7_pct:.0f}</b> (alarm eşiği: %35)"
                )

    if len(satirlar) == 7:
        satirlar.append("- Mod kaydı henüz oluşmadı.")
    else:
        siralama.sort(key=lambda x: x[1], reverse=True)
        satirlar.append("")
        satirlar.append("<b>Liderlik (ortalama güven)</b>")
        for i, (mod, avg) in enumerate(siralama, start=1):
            satirlar.append(f"{i}) {etiket.get(mod, mod)} — <b>{avg:.1f}</b>")

        if en_dusuk_guven_modu is not None:
            mod, low_pct, n_int = en_dusuk_guven_modu
            satirlar.append("")
            satirlar.append(
                f"🧪 En çok düşük güven üreten mod: <b>{etiket.get(mod, mod)}</b> (oran <b>%{low_pct:.0f}</b>, n={n_int})"
            )

        satirlar.append("")
        satirlar.append("<b>🚨 Son 7 gün alarmı</b>")
        if alarm_satirlari:
            satirlar.extend(alarm_satirlari)
        else:
            satirlar.append("- Kritik alarm yok (tüm modlar eşik altında).")

    satirlar.extend(
        [
            "",
            "<i>Not: Bu panel modelin gerçekleşen getirisini değil, üretilen güven skorlarının canlı dağılımını ve kısa/orta trendini gösterir.</i>",
        ]
    )
    return "\n".join(satirlar)


async def gonder_parcali_html(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    tam_metin: str,
) -> None:
    """İlk parça mevcut mesajı düzenler; devamı aynı sohbete gönderilir."""
    parcalar = telegram_html_parcalara_bol(tam_metin.strip(), TELEGRAM_MAX_UZUNLUK)
    chat_id = query.message.chat_id
    toplam = len(parcalar)

    for i, parca in enumerate(parcalar):
        if toplam > 1 and i > 0:
            bant = f"<i>{_tg_html_escape(f'Devam {i + 1}/{toplam}')}</i>\n"
            parca = bant + parca
            if len(parca) > TELEGRAM_MAX_UZUNLUK:
                parca = parca[: TELEGRAM_MAX_UZUNLUK]

        try:
            if i == 0:
                await query.edit_message_text(parca, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=parca,
                    parse_mode=ParseMode.HTML,
                )
        except BadRequest as e:
            logger.warning("HTML gönderilemedi (parça %s/%s), düz metin: %s", i + 1, toplam, e)
            düz = re.sub(r"<[^>]+>", "", parca)
            if i == 0:
                await query.edit_message_text(düz[:TELEGRAM_MAX_UZUNLUK])
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=düz[:TELEGRAM_MAX_UZUNLUK],
                )
        except TelegramError as e:
            logger.exception("Telegram gönderim hatası: %s", e)
            if i == 0:
                await query.edit_message_text(
                    _tg_html_escape(
                        "Mesaj gönderilirken bir sorun oluştu. /analiz ile tekrar dene."
                    )
                )
            break


def _ozet_satirlari_html(govde: str) -> str:
    """Kısa özeti premium kart görünümünde sun."""
    etiketler = "ÖZET|SEKTÖR|ŞİRKETLER|VARLIK|GİRİŞİM|RİSK|GÜVEN|TERS_SENARYO"
    desen = re.compile(rf"^({etiketler})\s*:\s*(.*)$", re.IGNORECASE)
    alanlar: dict[str, str] = {}
    for ham in (govde or "").strip().splitlines():
        s = ham.strip()
        if not s:
            continue
        m = desen.match(s)
        if m:
            etiket = m.group(1).strip()
            icerik = m.group(2).strip()
            alanlar[etiket.upper()] = icerik
        else:
            # Beklenmeyen satırları özete ekle (bozulmasın).
            alanlar.setdefault("ÖZET", s)

    if not alanlar:
        return _tg_html_escape(govde)

    # Premium mini kart düzeni
    c: list[str] = []
    if "ÖZET" in alanlar:
        c.append(f"<b>🧭 Piyasa Özeti</b>\n{_tg_html_escape(alanlar['ÖZET'])}")
    if "SEKTÖR" in alanlar:
        c.append(f"<b>🏭 Öne Çıkan Tema</b>\n{_tg_html_escape(alanlar['SEKTÖR'])}")
    if "ŞİRKETLER" in alanlar:
        c.append(f"<b>🏷️ Şirket Örnekleri</b>\n{_tg_html_escape(alanlar['ŞİRKETLER'])}")
    if "VARLIK" in alanlar:
        c.append(f"<b>🧺 Varlık Kanalı</b>\n{_tg_html_escape(alanlar['VARLIK'])}")
    if "GİRİŞİM" in alanlar:
        c.append(f"<b>🚀 Girişim Fırsatı</b>\n{_tg_html_escape(alanlar['GİRİŞİM'])}")

    alt: list[str] = []
    if "RİSK" in alanlar:
        alt.append(f"<b>⚠️ Risk</b>: {_tg_html_escape(alanlar['RİSK'])}")
    if "TERS_SENARYO" in alanlar:
        alt.append(f"<b>🧯 Ters Senaryo</b>: {_tg_html_escape(alanlar['TERS_SENARYO'])}")
    if "GÜVEN" in alanlar:
        alt.append(f"<b>🎯 Güven</b>: {_tg_html_escape(alanlar['GÜVEN'])}")
    if alt:
        c.append("\n".join(alt))

    return "\n\n".join(c)


def _detay_govdeyi_sadelestir_html(govde: str) -> str:
    """
    Uzun anlatım metnini Telegram'da daha okunur kart bloklarına dönüştür.
    Amaç: metin yığını görünümünü azaltmak (satır/sentence bloklama + etiket vurgusu).
    """
    txt = (govde or "").strip()
    if not txt:
        return ""

    # Fazla boşlukları sadeleştir; satır kırılımlarını koru.
    satirlar = [re.sub(r"\s+", " ", s).strip() for s in txt.splitlines() if s.strip()]

    # Tek satır geldiyse cümle bazlı bloklara böl.
    if len(satirlar) <= 1:
        satirlar = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])", txt)
            if s.strip()
        ]

    icerik_satirlari: list[str] = []
    guven_satiri = ""
    ters_satiri = ""
    risk_satiri = ""
    for s in satirlar:
        u = s.upper()
        if u.startswith("GÜVEN:"):
            if ":" in s:
                guven_satiri = s.split(":", 1)[1].strip()
            else:
                guven_satiri = s
            continue
        if u.startswith("TERS_SENARYO:"):
            ters_satiri = s.split(":", 1)[1].strip() if ":" in s else s
            continue
        if u.startswith("RİSK:"):
            risk_satiri = s.split(":", 1)[1].strip() if ":" in s else s
            continue

        icerik_satirlari.append(s)

    # İçeriği 3 bölüme ayır: Durum / Etki / Fırsat
    n = len(icerik_satirlari)
    if n <= 3:
        durum = icerik_satirlari[:1]
        etki = icerik_satirlari[1:2]
        firsat = icerik_satirlari[2:]
    elif n <= 6:
        durum = icerik_satirlari[:2]
        etki = icerik_satirlari[2:4]
        firsat = icerik_satirlari[4:]
    else:
        durum = icerik_satirlari[:2]
        etki = icerik_satirlari[2:5]
        firsat = icerik_satirlari[5:]

    def blok_baslikli(baslik: str, satirs: list[str]) -> str:
        if not satirs:
            return ""
        govde2 = "\n\n".join([f"• {_tg_html_escape(x)}" for x in satirs])
        return f"<b>{baslik}</b>\n{govde2}"

    bloklar: list[str] = []
    for b in (
        blok_baslikli("🧭 Durum", durum),
        blok_baslikli("🏗️ Etki Zinciri", etki),
        blok_baslikli("🚀 Fırsat Alanı", firsat),
    ):
        if b:
            bloklar.append(b)

    alt: list[str] = []
    if risk_satiri:
        alt.append(f"<b>⚠️ Risk</b>: {_tg_html_escape(risk_satiri)}")
    if ters_satiri:
        alt.append(f"<b>🧯 Ters Senaryo</b>: {_tg_html_escape(ters_satiri)}")
    if guven_satiri:
        alt.append(f"<b>🎯 Güven</b>: {_tg_html_escape(guven_satiri)}")
    if alt:
        bloklar.append("\n".join(alt))

    return "\n\n".join(bloklar)


def sarmla_analiz_mesaji_html(
    ulke: str,
    cikti_stili: str,
    analiz_govdesi: str,
    analiz_turu: str = ANALIZ_MEVSIM,
) -> str:
    """
    Telegram HTML (parse_mode) ile kart hissi: başlıklar kalın, gövde kaçırılmış.
    Gerçek mobil UI yok; Telegram’ın desteklediği biçimlendirme kullanılır.
    """
    govde = (analiz_govdesi or "").strip()
    e_ulke = _tg_html_escape(ulke)
    if analiz_turu == ANALIZ_HAVA:
        mod_etiket = "Hava"
        uzun_baslik = "Hava · Uzun anlatım"
    elif analiz_turu == ANALIZ_JEOPOLITIK:
        mod_etiket = "Jeopolitik"
        uzun_baslik = "Jeopolitik · Uzun anlatım"
    else:
        mod_etiket = "Mevsim"
        uzun_baslik = "Mevsim · Uzun anlatım"

    alt_cizgi = "<b>━━━━━━━━━━━━━━━━━━━━</b>"

    footer = (
        f"\n{alt_cizgi}\n"
        f"<i>{_tg_html_escape('Bilgilendirme amaçlıdır; yatırım tavsiyesi değildir. Yatırım kararı için kendi araştırmanı yap.')}</i>\n\n"
        f"<b>{_tg_html_escape('Yeni analiz:')}</b> /analiz"
    )

    if cikti_stili == CIKTI_OZET:
        govde_html = _ozet_satirlari_html(govde)
        return (
            f"<b>⚡ Makro Lens</b> · <i>{_tg_html_escape('Kısa özet')}</i>\n"
            f"{alt_cizgi}\n"
            f"📍 <b>{e_ulke}</b> · <i>{_tg_html_escape(mod_etiket)}</i>\n"
            f"{alt_cizgi}\n\n"
            f"{govde_html}\n"
            f"{footer}"
        )

    govde_html = _detay_govdeyi_sadelestir_html(govde)
    return (
        f"<b>📊 Makro Lens</b> · <i>{_tg_html_escape(uzun_baslik)}</i>\n"
        f"{alt_cizgi}\n"
        f"🌍 <b>{e_ulke}</b>\n"
        f"🧩 <i>{_tg_html_escape('Sade görünüm')}</i>\n"
        f"{alt_cizgi}\n\n"
        f"{govde_html}"
        f"{footer}"
    )

# ─── Gemini Prompt ────────────────────────────────────────────────────────────

def mevsim_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY) -> str:
    """Yapılandırılmış bağlam + mevsim görevi ile LLM analizi (Gemini veya DeepSeek)."""

    from datetime import datetime
    aylar = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan",
        5: "Mayıs", 6: "Haziran", 7: "Temmuz", 8: "Ağustos",
        9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }
    bugun = datetime.now()
    ay_adi = aylar[bugun.month]
    yil = bugun.year

    dil_notu = (
        "Tüm yanıtı Türkçe yaz. Türkiye dışı ülkelerde somut varlık önerirken "
        "gerekirse uluslararası sembolleri parantez içinde İngilizce ekleyebilirsin."
        if ulke != "Türkiye"
        else "Tüm yanıtı Türkçe yaz; BIST ve yerel şirket isimlerinde tutarlı ol."
    )
    guven = _guven_skoru_hesapla(ANALIZ_MEVSIM, baglam_metni)

    if cikti_stili == CIKTI_OZET:
        prompt = f"""
{baglam_metni}

---

### Görev (kısa özet kartı)
Sen deneyimli bir makro yatırım analistsin. Yukarıdaki bağlamı kullanarak {ulke} için {ay_adi} {yil} mevsim tablosunu **tek bakışta** özetle.

Ön-hesaplanan güven skoru (v1): {guven['toplam']}/100 ({guven['etiket']}).

Çıktıyı **yalnızca** aşağıdaki sekiz satır olarak ver; her satır tam olarak `ETİKET: içerik` biçiminde olsun (ETİKET büyük harf ve Türkçe). İçerikler tek cümle veya virgüllü kısa liste olabilir.

ÖZET: (bu mevsimde ülkede genel tablo ne, bir cümle)
SEKTÖR: (1–2 öne çıkan sektör/tema)
ŞİRKETLER: ({ulke} için bilgilendirme amaçlı tam üç şirket adı, virgülle; emin değilsen “isim vermek için veri yetersiz” yaz)
VARLIK: (hisse/kripto dışı kısa kanal notu veya yoksa “—”)
GİRİŞİM: (mevsime uygun bir girişim/yenilik teması, bir cümle)
RİSK: (tek cümle risk)
GÜVEN: ({guven['toplam']}/100 — {guven['etiket']}; kısa kullanıcı dili, teknik kısaltma kullanma)
TERS_SENARYO: (bu tezi bozabilecek tek bir koşul, bir cümle)

### Kurallar (özet)
- Başka paragraf, giriş cümlesi veya numaralı liste ekleme; sadece bu sekiz satır
- Düz metin; *, _, #, madde işareti kullanma
- {dil_notu}
- Uydurma veri kullanma; emin değilsen kısaca belirt
- "Yatırım tavsiyesi değildir" veya benzeri ek uyarı/risk kapanış cümlesi yazma; bot footer ekleyecek
"""
    else:
        prompt = f"""
{baglam_metni}

---

### Görev (uzun anlatım)
Sen deneyimli bir makro yatırım analistsin. Yukarıdaki bağlamı dikkate alarak {ulke} için {ay_adi} {yil} dönemine odaklı mevsim analizi üret.

Ön-hesaplanan güven skoru (v1): {guven['toplam']}/100 ({guven['etiket']}).

Şu adımları izle:
1. Bu ay ülke için hangi mevsim fazı anlamlı? (bağlamdaki meteorolojik mevsimle tutarlı ol)
2. Bu fazda tipik ekonomik/tüketim hareketleri neler? (enerji, tarım, turizm, perakende vb.)
3. En az iki adımlı neden-sonuç zinciri kur: makro/mevsim etkisi → öne çıkan sektör veya tema
4. **Yükselen / öne çıkan sektör temaları:** Bu mevsimle bağlantılı 1–2 ana sektör veya tema adını net söyle (ör. enerji, turizm teknolojileri, perakende lojistiği).
5. **Üç şirket örneği ({ulke}):** Az önce vurguladığın sektör temasıyla uyumlu, o ülkenin kamuya açık piyasasında gerçekten işlem gören veya yaygın bilinen **tam üç** şirket adı ver; yalnızca bilgilendirme amaçlı örnek olduğunu ima et. Bu üçlüyü tek cümlede virgülle sıralayabilirsin. Emin olmadığın isimleri uydurma: eminsen yaz, değilsen sektörü anlatıp “somut isim vermek için veri yetersiz” de.
6. **Varlık çeşitliliği:** Sadece hisse veya kripto ile sınırlanma; uygunsa kısaca emtia, tahvil/ETF veya döviz gibi başka kanallardan bahset (zorunlu değil, zorlama).
7. **Girişim fırsatları:** Aynı mevsim ve ülke bağlamında **girişim / yenilik / yan proje** açısından 1–2 cümle ekle: hangi problem alanlarında fırsat oluşur, hangi B2B veya tüketici ihtiyaçları artar, erken aşama hangi tema gündemde olabilir (somut “şunu kur” talimatı değil, tema düzeyinde).
8. Ayrı bir cümlede **GÜVEN** satırı ver: “GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ...” (kullanıcı dili; teknik kısaltma yok).
9. Ayrı bir cümlede **TERS_SENARYO** ver: “Bu tezi bozabilecek ana koşul ...”.

### Kurallar
- Toplam **en fazla 10 kısa cümle**; arkadaşça, akıcı düz metin; her cümle mümkünse 20-22 kelimeyi aşmasın
- Teknik finans jargonundan kaçın
- Sonda tek cümle risk notu zorunlu
- Bilmediğin spesifik veriyi uydurma; emin değilsen kısaca belirt
- {dil_notu}
- "Yatırım tavsiyesi değildir" veya benzeri kapanış cümlesi üretme; bunu mesaj sonunda yalnız bot ekler
"""

    try:
        text = llm_metin_uret(prompt)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM mevsim analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


def hava_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY) -> str:
    """Güncel hava + tahmin bağlamıyla makro/yatırım temalı hava analizi (LLM)."""

    from datetime import datetime
    aylar = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    bugun = datetime.now()
    ay_adi = aylar[bugun.month - 1]
    yil = bugun.year

    dil_notu = (
        "Tüm yanıtı Türkçe yaz. Türkiye dışı ülkelerde somut varlık önerirken "
        "gerekirse uluslararası sembolleri parantez içinde İngilizce ekleyebilirsin."
        if ulke != "Türkiye"
        else "Tüm yanıtı Türkçe yaz; BIST ve yerel şirket isimlerinde tutarlı ol."
    )
    guven = _guven_skoru_hesapla(ANALIZ_HAVA, baglam_metni)

    if cikti_stili == CIKTI_OZET:
        prompt = f"""
{baglam_metni}

---

### Görev (kısa özet — hava)
Sen deneyimli bir makro yatırım analistsin. Yukarıdaki **gerçek hava verisini** kullanarak {ulke} ({ay_adi} {yil}) için ekonomi ve piyasalar açısından **tek bakışta** özet üret.

Ön-hesaplanan güven skoru (v1): {guven['toplam']}/100 ({guven['etiket']}).

Çıktıyı **yalnızca** sekiz satır olarak ver; her satır `ETİKET: içerik` (ETİKET büyük harf, Türkçe).

ÖZET: (anlık + günlük 5 güne kadar trend ne anlatıyor, bir cümle; gerekirse ilk 24 saat vurgusu; ufku “önümüzdeki birkaç gün / kısa vade” ile sınırla)
SEKTÖR: (bu hava ile öne çıkan 1–2 sektör/tema: enerji, tarım, sigorta, perakende, lojistik, turizm vb.)
ŞİRKETLER: (en fazla üç isim, yalnızca **temsilî örnek**; “örneğin” veya “temsilen” geçsin; hava→sektör köprüsü kısa; emin değilsen veya uygun değilse “isim vermek için veri yetersiz”)
VARLIK: (hisse dışı kısa kanal: emtia/ETF vb. veya “—”)
GİRİŞİM: (hava/iklim/lojistik ile ilgili bir girişim teması, bir cümle; kısa vadeli talep/operasyon çerçevesinde)
RİSK: (tek cümle risk; hava tahmininin belirsizliği dahil)
GÜVEN: ({guven['toplam']}/100 — {guven['etiket']}; kısa kullanıcı dili, teknik kısaltma kullanma)
TERS_SENARYO: (bu tezi bozabilecek tek bir koşul, bir cümle)

### Kurallar (özet)
- Sadece bu sekiz satır; numaralı liste yok; *, _, # yok
- Tahmin verisi en fazla ~5 gün: “uzun vadeli”, “aylar boyunca”, “stratejik dönem” gibi bu tahmini uzatan ifadeler kullanma
- Şirket adları yatırım tavsiyesi değildir; al/sat ima etme
- {dil_notu}
- Veride olmayan sıcaklık veya olayı uydurma
- "Yatırım tavsiyesi değildir" veya benzeri kapanış cümlesi üretme; bunu mesaj sonunda yalnız bot ekler
"""
    else:
        prompt = f"""
{baglam_metni}

---

### Görev (uzun anlatım — hava)
Sen deneyimli bir makro yatırım analistsin. Yukarıdaki **anlık hava, günlük min–max özet (yaklaşık 5 güne kadar) ve ilk 24 saatlik 3 saat dilimleri** verisini temel alarak {ulke} için {ay_adi} {yil} çerçevesinde analiz üret.

Ön-hesaplanan güven skoru (v1): {guven['toplam']}/100 ({guven['etiket']}).

**Ufuk:** Bu veri en fazla ~**5 günlük** tahmindir; analizi **önümüzdeki birkaç gün / kısa vade** ile çerçevele. Bu tahmini haftalar veya aylar boyunca sürecekmiş gibi anlatma; “uzun vadeli dağıtım”, “stratejik dönem boyunca” gibi ifadelerden kaçın.

Şunları kapsa:
1. Anlık koşullar; **günlük özetten** birkaç günün yönü (ısınma/soğuma, kuruluk/yağışlılık eğilimi) ve istersen ilk 24 saatteki kısa vadeli değişim (veriye sadık kal).
2. Bu koşulların tüketim, enerji talebi, tarım, ulaştırma, perakende, turizm üzerinden **en az iki adımlı** neden-sonuç; zayıf veya spekülatif bağları **kısa tut** ve mümkünse “olası”, “dolaylı” dil kullan.
3. **Sektör temaları:** 1–2 ana tema (ör. doğalgaz/elektrik, gıda zinciri, e-ticaret kargo, seyahat iptalleri).
4. **Şirket örnekleri ({ulke}, en fazla üç):** yalnızca **temsilî örnek**; “örneğin”, “temsilen” benzeri ifade kullan; hava→sektör→isim zincirini **tek cümlede** ve **yatırım tavsiyesi ima etmeden** kur. Emin değilsen isim verme, kısaca belirt.
5. **Varlık çeşitliliği:** uygunsa kısaca emtia/ETF/tahvil veya döviz kanalı (zorunlu değil).
6. **Girişim açısı:** hava olayına bağlı **kısa vadeli** talep veya operasyonel fırsat teması (talimat değil, tema).
7. Son cümle: tek cümle **risk** (hava modeli belirsizliği, politik/regülasyon müdahalesi vb.).
8. Ayrı bir cümlede **GÜVEN** satırı ver: “GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ...” (kullanıcı dili; teknik kısaltma yok).
9. Ayrı bir cümlede **TERS_SENARYO** ver: “Bu tezi bozabilecek ana koşul ...”.

### Kurallar
- En fazla **10 kısa cümle**; düz metin; her cümle mümkünse 20-22 kelimeyi aşmasın
- Teknik jargondan kaçın; “al/sat”, “mutlaka”, “kesin hareket” dili kullanma
- {dil_notu}
- "Yatırım tavsiyesi değildir" veya benzeri kapanış cümlesi üretme; bunu mesaj sonunda yalnız bot ekler
"""

    try:
        text = llm_metin_uret(prompt)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM hava analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


def jeopolitik_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY) -> str:
    """Jeopolitik haber başlıkları bağlamıyla makro/yatırım temalı jeopolitik analizi (LLM)."""

    from datetime import datetime

    bugun = datetime.now()
    aylar = (
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık",
    )
    ay_adi = aylar[bugun.month - 1]
    yil = bugun.year

    dil_notu = (
        "Tüm yanıtı Türkçe yaz. Türkiye dışı ülkelerde somut varlık önerirken "
        "gerekirse uluslararası sembolleri parantez içinde İngilizce ekleyebilirsin."
        if ulke != "Türkiye"
        else "Tüm yanıtı Türkçe yaz; BIST ve yerel şirket isimlerinde tutarlı ol."
    )
    guven = _guven_skoru_hesapla(ANALIZ_JEOPOLITIK, baglam_metni)

    if cikti_stili == CIKTI_OZET:
        prompt = f"""
{baglam_metni}

---

### Görev (kısa özet — jeopolitik)
Sen deneyimli bir makro yatırım analistsin. Yukarıdaki jeopolitik haber başlıkları ve hedef ülke bilgisine dayanarak {ulke} ({ay_adi} {yil}) için ekonomi ve piyasalar açısından tek bakışta özet üret.

Ön-hesaplanan güven skoru (v1): {guven['toplam']}/100 ({guven['etiket']}).

Çıktıyı yalnızca aşağıdaki sekiz satır olarak ver; her satır tam olarak `ETİKET: içerik` biçiminde olsun (ETİKET büyük harf ve Türkçe).

ÖZET: (son jeopolitik gelişmelerin makro/piyasa özeti; belirsizlik içeren kısa dil kullan, bir cümle)
SEKTÖR: (1–2 sektör/tema)
ŞİRKETLER: (en fazla üç şirket adı, yalnızca temsilî örnek; emin değilsen “isim vermek için veri yetersiz”)
VARLIK: (emtia/ETF/döviz vb. kısa kanal veya “—”)
GİRİŞİM: (jeopolitik risk ile ilgili girişim/operasyon teması, bir cümle)
RİSK: (tek cümle risk; haberlerin hızlı değişebilirliği dahil)
GÜVEN: ({guven['toplam']}/100 — {guven['etiket']}; kısa kullanıcı dili, teknik kısaltma kullanma)
TERS_SENARYO: (bu tezi bozabilecek tek bir koşul, bir cümle)

### Kurallar (özet)
- Sadece bu sekiz satır; numaralı liste yok; *, _, # yok
- Tahmin dili: “olası”, “dolaylı”, “kısa vadede etkileyebilir” gibi ifadeleri tercih et; kesinlik kurma
- Şirket adı uydurma yapma; emin değilsen isim verme
- Teknik jargondan kaçın; “al/sat”, “mutlaka”, “kesin hareket” dili kullanma
- {dil_notu}
- "Yatırım tavsiyesi değildir" veya benzeri kapanış cümlesi üretme; bunu mesaj sonunda yalnız bot ekler
"""
    else:
        prompt = f"""
{baglam_metni}

---

### Görev (uzun anlatım — jeopolitik)
Sen deneyimli bir makro yatırım analistsin. Yukarıdaki jeopolitik haber başlıkları ve hedef ülke bağlamını dikkate alarak {ulke} ({ay_adi} {yil}) için makro ve sektör etkisi odaklı jeopolitik analizi üret.

Ön-hesaplanan güven skoru (v1): {guven['toplam']}/100 ({guven['etiket']}).

Şunları kapsa:
1. Haberlerde öne çıkan jeopolitik risk kanalını (enerji/emtia, ticaret/lojistik, savunma, yaptırımlar vb.) 1–2 cümleyle özetle.
2. En az iki adımlı neden-sonuç zinciri kur: jeopolitik risk → makro değişken (fiyat, tedarik, güvenlik algısı, para/kur riski gibi) → öne çıkan sektör/tema.
3. 1–2 ana sektör/tema adını net söyle.
4. Ülke için (kamuya açık) bilinen **en fazla üç** şirket örneğini tek cümlede virgülle ver; sadece temsilî örnek olduğunu ima et; emin değilsen isim verme, kısa belirt.
5. Varlık çeşitliliği: mümkünse emtia/ETF/döviz gibi kısa bir kanal ekle (zorunlu değil).
6. Girişim açısı: jeopolitik kaynaklı talep veya operasyonel ihtiyaçla ilgili kısa bir tema (talimat değil).
7. Son cümle: tek cümle risk (haberlerin hızlı değişebilirliği + belirsizlik).
8. Ayrı bir cümlede **GÜVEN** satırı ver: “GÜVEN: {guven['toplam']}/100 ({guven['etiket']}) ...” (kullanıcı dili; teknik kısaltma yok).
9. Ayrı bir cümlede **TERS_SENARYO** ver: “Bu tezi bozabilecek ana koşul ...”.

### Kurallar
- En fazla 10 kısa cümle; düz metin; her cümle mümkünse 20-22 kelimeyi aşmasın
- Kesin ifade kurma; “olası/dolaylı” dil kullan
- Teknik finans jargonu minimum; “al/sat”, “mutlaka”, “kesin hareket” yok
- {dil_notu}
- "Yatırım tavsiyesi değildir" veya benzeri kapanış cümlesi üretme; bunu mesaj sonunda yalnız bot ekler
"""

    try:
        text = llm_metin_uret(prompt)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM jeopolitik analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Telegram Handler'ları ────────────────────────────────────────────────────

def _karsilama_mesaji_html() -> str:
    return (
        "👋 Merhaba! Ben <b>Makro Lens</b>.\n\n"
        "Mevsimler, hava olayları, jeopolitik gelişmeler gibi "
        "büyük resim faktörlerin piyasalara etkisini analiz ediyorum.\n\n"
        "Başlamak için <b>/analiz</b> yaz.\n"
        "Analiz sırasında çıkmak için <b>/cancel</b> veya <b>/start</b> kullanabilirsin."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu — kullanıcıyı karşıla, oturum verisini temizle"""
    context.user_data.clear()
    await update.message.reply_text(_karsilama_mesaji_html(), parse_mode=ParseMode.HTML)


async def start_ve_konusmayi_bitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konuşma içindeyken /start — karşılama + akışı kapat"""
    await start(update, context)
    return ConversationHandler.END


async def iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Konuşma içindeyken /cancel"""
    context.user_data.clear()
    await update.message.reply_text(
        "<b>Analiz iptal edildi.</b>\n\n"
        "İstediğinde <b>/analiz</b> ile yeniden başlayabilirsin.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/yardim komutu"""
    mesaj = (
        "<b>📖 Nasıl kullanılır?</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>/analiz</b> — Yeni bir analiz başlat\n"
        "<b>/hesabim</b> — Plan, kalan Pro gün ve kullanım durumu\n"
        "<b>/performans</b> — Canlı güven skoru özeti\n"
        "<b>/start</b> — Karşılama; analiz akışındaysan akışı kapatır\n"
        "<b>/cancel</b> — Analiz akışını iptal eder\n\n"
        f"Ücretsiz kullanım limiti: günde <b>{ANALIZ_GUNLUK_LIMIT}</b> analiz.\n"
        "Ülke seçtikten sonra <b>uzun anlatım</b> veya <b>kısa özet</b> çıktısı seçebilirsin.\n"
        "<b>Hava</b> modu için <code>OPENWEATHER_API_KEY</code> (.env) gerekir.\n\n"
        "<i>Bilgilendirme amaçlıdır; yatırım tavsiyesi değildir.</i>\n"
        "<i>Yatırım kararı için kendi araştırmanı yap.</i>"
    )
    await update.message.reply_text(mesaj, parse_mode=ParseMode.HTML)


async def performans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/performans — canlı güven skoru özet paneli"""
    metin = _performans_ozeti_hesapla()
    await update.message.reply_text(metin, parse_mode=ParseMode.HTML)


async def hesabim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/hesabim — plan ve kullanım özeti"""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        await update.message.reply_text("Kullanıcı bilgisi alınamadı.")
        return

    plan = _kullanici_plan_bilgisi(user_id)
    pro_mu = plan.get("plan") == "pro"
    pro_until = plan.get("pro_until") or ""
    kalan = _kalan_pro_gun(pro_until) if pro_mu else 0
    gunluk = _gunluk_kullanim_oku(user_id)

    plan_satiri = "Pro ✅" if pro_mu else "Ücretsiz"
    pro_satiri = (
        f"Pro bitiş: <b>{_tg_html_escape(pro_until)}</b> · kalan <b>{kalan}</b> gün"
        if pro_mu and pro_until
        else "Pro aktif değil."
    )

    mesaj = (
        "<b>👤 Hesabım</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"Kullanıcı ID: <code>{user_id}</code>\n"
        f"Plan: <b>{plan_satiri}</b>\n"
        f"{pro_satiri}\n"
        f"Günlük kullanım: <b>{gunluk}/{ANALIZ_GUNLUK_LIMIT}</b>\n"
        f"Limit durumu: <b>{'Bypass (Pro)' if pro_mu else 'Standart (Free)'}</b>"
    )
    await update.message.reply_text(mesaj, parse_mode=ParseMode.HTML)


async def pro_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pro_ver <user_id> <gun> — admin manuel pro atama"""
    admin_id = update.effective_user.id if update.effective_user else None
    if not _admin_mi(admin_id):
        await update.message.reply_text("Bu komut yalnız admin için.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /pro_ver <user_id> <gun>")
        return
    try:
        hedef_user_id = int(context.args[0])
        gun = int(context.args[1])
        if gun <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Geçersiz parametre. Örnek: /pro_ver 123456789 30")
        return

    bitis = date.today() + timedelta(days=gun)
    data = _plan_kayitlarini_yukle()
    data[str(hedef_user_id)] = {"plan": "pro", "pro_until": bitis.isoformat()}
    _plan_kayitlarini_kaydet(data)
    _odeme_olayi_kaydet(
        action="pro_grant",
        hedef_user_id=hedef_user_id,
        admin_user_id=admin_id,
        detail=f"gun={gun}; pro_until={bitis.isoformat()}",
    )
    await update.message.reply_text(
        f"✅ Pro atandı.\nuser_id={hedef_user_id}\npro_until={bitis.isoformat()}"
    )


async def pro_iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pro_iptal <user_id> — admin manuel pro iptal"""
    admin_id = update.effective_user.id if update.effective_user else None
    if not _admin_mi(admin_id):
        await update.message.reply_text("Bu komut yalnız admin için.")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /pro_iptal <user_id>")
        return
    try:
        hedef_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Geçersiz user_id.")
        return

    data = _plan_kayitlarini_yukle()
    data[str(hedef_user_id)] = {"plan": "free", "pro_until": ""}
    _plan_kayitlarini_kaydet(data)
    _odeme_olayi_kaydet(
        action="pro_revoke",
        hedef_user_id=hedef_user_id,
        admin_user_id=admin_id,
        detail="manual revoke",
    )
    await update.message.reply_text(f"✅ Pro iptal edildi. user_id={hedef_user_id}")


async def odeme_kayit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/odeme_kayit [n] — admin için son ödeme/plan olayları"""
    admin_id = update.effective_user.id if update.effective_user else None
    if not _admin_mi(admin_id):
        await update.message.reply_text("Bu komut yalnız admin için.")
        return

    n = 10
    if context.args:
        try:
            n = max(1, min(int(context.args[0]), 30))
        except ValueError:
            n = 10

    kayitlar = _odeme_kayit_son_n(n)
    if not kayitlar:
        await update.message.reply_text("Henüz ödeme/plan kaydı yok.")
        return

    satirlar = [
        "<b>🧾 Son ödeme/plan kayıtları</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "",
    ]
    for k in reversed(kayitlar):
        satirlar.append(
            f"- {k['ts_utc']} · <b>{_tg_html_escape(k['action'])}</b> · hedef={_tg_html_escape(k['hedef_user_id'])} · admin={_tg_html_escape(k['admin_user_id'])}"
        )
        if k["detail"]:
            satirlar.append(f"  <i>{_tg_html_escape(k['detail'])}</i>")

    await update.message.reply_text("\n".join(satirlar), parse_mode=ParseMode.HTML)


async def analiz_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/analiz komutu — mod seçim ekranını göster"""
    context.user_data.clear()
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is not None and not _kullanici_pro_mu(user_id):
        asildi, kullanilan = _gunluk_limit_asildi_mi(user_id)
        if asildi:
            await update.message.reply_text(
                (
                    f"⛔ Günlük ücretsiz limit doldu ({kullanilan}/{ANALIZ_GUNLUK_LIMIT}).\n\n"
                    "Yarın tekrar deneyebilirsin. Manuel Pro yükseltme için admin ile iletişime geç."
                )
            )
            return ConversationHandler.END

    klavye = [
        [InlineKeyboardButton("🍂 Mevsimler", callback_data="mod_mevsim")],
        [InlineKeyboardButton("🌦 Hava durumu", callback_data="mod_hava")],
        [InlineKeyboardButton("⚔️ Jeopolitik", callback_data="mod_jeopolitik")],
        [InlineKeyboardButton("📅 Özel Günler — Yakında", callback_data="yakinda")],
    ]
    reply_markup = InlineKeyboardMarkup(klavye)

    await update.message.reply_text(
        "Hangi modu kullanmak istersin?",
        reply_markup=reply_markup
    )
    return MOD_SECIMI


async def mod_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı mod seçti — ülke ekranını göster"""
    query = update.callback_query
    await query.answer()

    if query.data == "yakinda":
        await query.edit_message_text("🔜 Bu mod yakında geliyor! /analiz ile Mevsim modunu deneyebilirsin.")
        return ConversationHandler.END

    # Modu kaydet
    context.user_data["mod"] = query.data

    # Ülke seçim butonları oluştur
    klavye = []
    for i in range(0, len(ULKELER), 2):
        satir = []
        satir.append(InlineKeyboardButton(ULKELER[i], callback_data=f"ulke_{ULKELER[i]}"))
        if i + 1 < len(ULKELER):
            satir.append(InlineKeyboardButton(ULKELER[i+1], callback_data=f"ulke_{ULKELER[i+1]}"))
        klavye.append(satir)

    reply_markup = InlineKeyboardMarkup(klavye)
    await query.edit_message_text("Hangi ülke için analiz yapalım?", reply_markup=reply_markup)
    return ULKE_SECIMI


async def ulke_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı ülke seçti — çıktı formatı (uzun / kısa) sor"""
    query = update.callback_query
    await query.answer()

    ulke = query.data.replace("ulke_", "")
    context.user_data["ulke"] = ulke

    klavye = [
        [
            InlineKeyboardButton("📖 Uzun anlatım", callback_data="cikti_detay"),
            InlineKeyboardButton("⚡ Kısa özet", callback_data="cikti_ozet"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(klavye)

    await query.edit_message_text(
        f"✅ {ulke} seçildi.\n\n"
        "Nasıl göstereyim?\n"
        "• Uzun anlatım — detaylı metin\n"
        "• Kısa özet — kritik satırlar, tek mobakışta",
        reply_markup=reply_markup,
    )
    return FORMAT_SECIMI


async def cikti_format_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Çıktı stili seçildi — analizi üret ve gönder"""
    query = update.callback_query
    await query.answer()

    ulke = context.user_data.get("ulke")
    mod = context.user_data.get("mod", "mod_mevsim")

    if not ulke:
        await query.edit_message_text(
            "Oturum sıfırlandı. Yeniden başlamak için /analiz",
        )
        return ConversationHandler.END

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is not None and not _kullanici_pro_mu(user_id):
        asildi, kullanilan = _gunluk_limit_asildi_mi(user_id)
        if asildi:
            await query.edit_message_text(
                (
                    f"⛔ Günlük ücretsiz limit doldu ({kullanilan}/{ANALIZ_GUNLUK_LIMIT}).\n\n"
                    "Yarın tekrar deneyebilirsin. Manuel Pro yükseltme için admin ile iletişime geç."
                )
            )
            return ConversationHandler.END

    stil = CIKTI_OZET if query.data == "cikti_ozet" else CIKTI_DETAY
    stil_etiket = "kısa özet" if stil == CIKTI_OZET else "uzun anlatım"
    if mod == "mod_hava":
        mod_kisa = "hava"
    elif mod == "mod_jeopolitik":
        mod_kisa = "jeopolitik"
    else:
        mod_kisa = "mevsim"

    await query.edit_message_text(f"🔍 {ulke} · {mod_kisa} · {stil_etiket} hazırlanıyor…")

    try:
        analiz_turu = ANALIZ_MEVSIM
        baglam = ""
        if mod == "mod_mevsim":
            try:
                baglam = await asyncio.to_thread(topla_mevsim_baglami, ulke)
            except Exception:
                logger.exception("Mevsim bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Bağlam yüklenemedi</b>\n\n"
                    "Veri dosyası veya ağ kaynaklı bir sorun olabilir. "
                    "Lütfen bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            analiz = await asyncio.to_thread(mevsim_analizi_yap, ulke, baglam, stil)
        elif mod == "mod_hava":
            analiz_turu = ANALIZ_HAVA
            try:
                baglam = await asyncio.to_thread(topla_hava_baglami, ulke)
            except HavaModuHatasi as e:
                await query.edit_message_text(
                    f"<b>Hava modu</b>\n\n{_tg_html_escape(str(e))}",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            except Exception:
                logger.exception("Hava bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Hava verisi alınamadı</b>\n\n"
                    "Bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            analiz = await asyncio.to_thread(hava_analizi_yap, ulke, baglam, stil)
        elif mod == "mod_jeopolitik":
            analiz_turu = ANALIZ_JEOPOLITIK
            try:
                baglam = await asyncio.to_thread(topla_jeopolitik_baglami, ulke)
            except Exception:
                logger.exception("Jeopolitik bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Jeopolitik bağlamı yüklenemedi</b>\n\n"
                    "RSS kaynağı veya ağ sorunu olabilir. "
                    "Lütfen bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            analiz = await asyncio.to_thread(jeopolitik_analizi_yap, ulke, baglam, stil)
        else:
            analiz = "Bu mod henüz aktif değil."

        guven_olayi = _guven_skoru_hesapla(analiz_turu, baglam)
        _analiz_olayi_kaydet(
            analiz_turu=analiz_turu,
            ulke=ulke,
            cikti_stili=stil,
            guven=guven_olayi,
            baglam_metni=baglam,
        )

        mesaj = sarmla_analiz_mesaji_html(ulke, stil, analiz, analiz_turu=analiz_turu)
        await gonder_parcali_html(query, context, mesaj)
        if user_id is not None:
            yeni = _gunluk_kullanim_arttir(user_id)
            logger.info(
                "Günlük kullanım arttı: user=%s %s/%s",
                user_id,
                yeni,
                ANALIZ_GUNLUK_LIMIT,
            )
    except Exception:
        logger.exception("Analiz sonucu gönderilemedi (ülke=%s)", ulke)
        try:
            await query.edit_message_text(
                "<b>Mesaj gönderilemedi</b>\n\n"
                "Beklenmeyen bir hata oluştu. <b>/analiz</b> ile tekrar dene.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.exception("Hata mesajı da gönderilemedi")

    return ConversationHandler.END


async def diger_mesajlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Beklenmeyen mesajları yönet"""
    await update.message.reply_text(
        "Analiz başlatmak için /analiz yaz. 👇"
    )


# ─── Botu Başlat ──────────────────────────────────────────────────────────────

def main():
    """Botu çalıştır"""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Konuşma akışını tanımla
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("analiz", analiz_baslat)],
        states={
            MOD_SECIMI: [CallbackQueryHandler(mod_secildi)],
            ULKE_SECIMI: [CallbackQueryHandler(ulke_secildi)],
            FORMAT_SECIMI: [CallbackQueryHandler(cikti_format_secildi)],
        },
        fallbacks=[
            CommandHandler("start", start_ve_konusmayi_bitir),
            CommandHandler("cancel", iptal),
        ],
    )

    # Konuşma önce: aktif akışta /start ve /cancel fallbacks ile biter.
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("hesabim", hesabim))
    app.add_handler(CommandHandler("performans", performans))
    app.add_handler(CommandHandler("pro_ver", pro_ver))
    app.add_handler(CommandHandler("pro_iptal", pro_iptal))
    app.add_handler(CommandHandler("odeme_kayit", odeme_kayit))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, diger_mesajlar))

    logger.info(
        "Bot başlatıldı… AI_PROVIDER=%s AI_FALLBACK_GEMINI=%s AI_FALLBACK_DEEPSEEK=%s gemini_anahtar_sayısı=%s",
        AI_PROVIDER,
        AI_FALLBACK_GEMINI,
        AI_FALLBACK_DEEPSEEK,
        len(_gemini_anahtarlari()),
    )
    app.run_polling()


if __name__ == "__main__":
    main()