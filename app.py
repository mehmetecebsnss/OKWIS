"""
Okwis AI — Telegram Yatırım Asistanı
8 analiz modu (Mevsim, Hava, Jeopolitik, Sektör, Trendler, Magazin, Özel Günler, Doğal Afet)
+ Okwis — Tanrının Gözü (tüm modların birleşimi, ultra sade çıktı).
"""

import asyncio
from collections import defaultdict
import html
import io
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

from dogal_afet_baglam import topla_dogal_afet_baglami
from hava_baglam import HavaModuHatasi, topla_hava_baglami
from jeopolitik_baglam import topla_jeopolitik_baglami
from magazin_baglam import topla_magazin_baglami
from mevsim_baglam import topla_mevsim_baglami
from ozel_gunler_baglam import topla_ozel_gunler_baglami
from sektor_baglam import topla_sektor_baglami
from trendler_baglam import topla_trendler_baglami
from alarm_sistemi import (
    alarm_tara_ve_bildir,
    kullanici_bildirim_acik_mi,
    kullanici_bildirim_ayarla,
    ALARM_ARALIK_SANIYE,
)
from gorsel_olusturucu import gorsel_olusturucu_al

# ─── Kaynak Etiketleri (mod → kullanılan kaynaklar) ──────────────────────────
_MOD_KAYNAKLARI: dict[str, list[str]] = {
    "mevsim":     ["BBC Business RSS", "OpenWeatherMap API (başkent)", "data/ulke_mevsim.json"],
    "hava":       ["OpenWeatherMap API (anlık + 5 günlük tahmin)", "data/ulke_mevsim.json"],
    "jeopolitik": ["BBC World News RSS", "data/ulke_mevsim.json"],
    "sektor":     ["BBC Business RSS", "BBC Technology RSS"],
    "trendler":   ["BBC News RSS", "BBC World RSS", "BBC Technology RSS"],
    "magazin":    ["BBC Entertainment RSS", "BBC Technology RSS"],
    "ozel_gun":   ["data/ozel_gunler.json", "BBC Business RSS"],
    "dogal_afet": ["USGS Earthquake API (M5+, son 7 gün)", "BBC World News RSS"],
    "okwis":      ["8 mod paralel (Mevsim, Hava, Jeopolitik, Sektör, Trendler, Magazin, Özel Günler, Doğal Afet)"],
}

_PROB_ZINCIRI_PATH = Path(__file__).resolve().parent / "data" / "prob_zinciri.json"


def _prob_zinciri_yukle() -> list[dict]:
    """Sosyal olasılık zincirlerini yükle."""
    try:
        if _PROB_ZINCIRI_PATH.exists():
            with open(_PROB_ZINCIRI_PATH, encoding="utf-8-sig") as f:  # UTF-8 BOM desteği
                data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("prob_zinciri.json yüklenemedi: %s", e)
    return []


def _ilgili_prob_zincirleri(mod: str, ulke: str = "", varlik: str = "") -> str:
    """
    Verilen mod + ülke + varlık için en ilgili sosyal ihtimal zincirlerini döndür.
    Akıllı skorlama: mod eşleşmesi + ülke/varlık içerik eşleşmesi.
    """
    zincirler = _prob_zinciri_yukle()

    def _skor(z: dict) -> int:
        puan = 0
        if mod in z.get("ilgili_modlar", []):
            puan += 3
        baslik = z.get("baslik", "").lower()
        tetikleyici = z.get("tetikleyici", "").lower()
        if ulke:
            ulke_lower = ulke.lower()
            if ulke_lower in baslik or ulke_lower in tetikleyici:
                puan += 2
        if varlik:
            varlik_lower = varlik.lower()
            if varlik_lower in baslik or varlik_lower in tetikleyici:
                puan += 2
            # Yaygın eş anlamlılar
            if varlik_lower in ("btc", "bitcoin") and ("bitcoin" in baslik or "kripto" in baslik):
                puan += 1
            if varlik_lower in ("altin", "altın", "gold", "xau") and ("altin" in baslik or "gold" in baslik):
                puan += 1
            if varlik_lower in ("petrol", "oil", "wti", "brent") and ("petrol" in baslik or "enerji" in baslik):
                puan += 1
        return puan

    ilgili = [(z, _skor(z)) for z in zincirler if _skor(z) >= 3]
    ilgili.sort(key=lambda x: x[1], reverse=True)
    en_iyi = [z for z, _ in ilgili[:2]]  # 3 yerine 2 — daha az ama daha ilgili

    if not en_iyi:
        return ""
    satirlar = ["### Sosyal İhtimal Zincirleri"]
    for z in en_iyi:
        satirlar.append(f"\n[{z['baslik']}] Tetikleyici: {z['tetikleyici']}")
        for adim in z.get("zincir", [])[:3]:  # 4 yerine 3 adım
            satirlar.append(f"  {adim['adim']}. {adim['olay']} -> {adim['etki']} (%{int(adim['olasilik']*100)})")
        satirlar.append(f"  Sonuc: {z['net_etki']}")
    return "\n".join(satirlar)


def _kaynak_listesi_html(mod_adi: str) -> str:
    """Analiz sonuna eklenecek kaynak listesi (Telegram HTML)."""
    kaynaklar = _MOD_KAYNAKLARI.get(mod_adi, [])
    if not kaynaklar:
        return ""
    satirlar = ["<b>━━━━━━━━━━━━━━━━━━━━</b>", "<b>◆ Kullanılan Kaynaklar</b>"]
    for k in kaynaklar:
        satirlar.append(f"▸ {_tg_html_escape(k)}")
    satirlar.append("<i>Analiz bu kaynaklardan derlenen veriler + AI çıkarımına dayanır. Yatırım tavsiyesi değildir.</i>")
    return "\n".join(satirlar)


def _guven_karti_html(
    mod_adi: str,
    baglam_metni: str,
    guven: dict,
    user_id: int | str | None = None,
) -> str:
    """
    Analiz sonuna eklenen Güven Kartı.
    Bağlam metnini parse ederek gerçek sayıları gösterir.
    """
    # ── Bağlam zenginliğini ölç ──────────────────────────────────────────────
    metin = baglam_metni or ""

    # Haber başlığı sayısı ("- " ile başlayan satırlar)
    baslik_sayisi = metin.count("\n- ")

    # Tavily var mı?
    tavily_var = "Güncel Web Araması" in metin or "Tavily" in metin
    tavily_sonuc_sayisi = 0
    if tavily_var:
        # "1." "2." "3." şeklinde numaralı satırları say
        import re as _re
        tavily_sonuc_sayisi = len(_re.findall(r"^\d+\.", metin, _re.MULTILINE))

    # USGS var mı?
    usgs_var = "USGS" in metin or "M5." in metin or "M6." in metin or "M7." in metin
    deprem_sayisi = metin.count("- M")

    # Hava verisi var mı?
    hava_var = "OpenWeather" in metin or "Anlık" in metin or "°C" in metin

    # ── Bağlam zenginliği etiketi ─────────────────────────────────────────────
    kaynak_skoru = 0
    kaynak_skoru += min(baslik_sayisi, 10)          # max 10 puan
    kaynak_skoru += 3 if tavily_var else 0           # Tavily var
    kaynak_skoru += 2 if usgs_var else 0             # USGS var
    kaynak_skoru += 1 if hava_var else 0             # Hava var

    if kaynak_skoru >= 12:
        zenginlik = "🟢 Yüksek"
    elif kaynak_skoru >= 6:
        zenginlik = "🟡 Orta"
    else:
        zenginlik = "🟠 Düşük"

    # ── AI Motoru ─────────────────────────────────────────────────────────────
    motor = "Gemini 2.5 Flash"
    if user_id is not None:
        plan_bilgi = _kullanici_plan_bilgisi(user_id)
        if plan_bilgi.get("plan") == "claude":
            motor = "Claude 3.5 Sonnet"
        elif AI_PROVIDER == "deepseek":
            motor = f"DeepSeek ({DEEPSEEK_MODEL})"

    # ── Güven açıklaması ──────────────────────────────────────────────────────
    g_toplam = guven.get("toplam", 0)
    g_etiket = guven.get("etiket", "")
    vkg = guven.get("vkg", 0)
    mbs = guven.get("mbs", 0)

    # Neden bu skor? — dinamik açıklama
    aciklama_parcalari = []
    if vkg >= 80:
        aciklama_parcalari.append("veri kalitesi yüksek")
    elif vkg < 50:
        aciklama_parcalari.append("bazı veri kaynakları boş geldi")

    if mbs >= 70:
        aciklama_parcalari.append("sinyaller net")
    elif mbs < 45:
        aciklama_parcalari.append("sinyaller belirsiz")

    if tavily_var:
        aciklama_parcalari.append(f"web araması destekledi ({tavily_sonuc_sayisi} sonuç)")

    if not aciklama_parcalari:
        aciklama_parcalari.append("standart bağlam")

    aciklama = ", ".join(aciklama_parcalari)

    # ── Statik kaynaklar ──────────────────────────────────────────────────────
    kaynaklar = _MOD_KAYNAKLARI.get(mod_adi, [])
    kaynak_satirlari = "\n".join(f"  ▸ {_tg_html_escape(k)}" for k in kaynaklar)
    if tavily_var:
        kaynak_satirlari += f"\n  ▸ Tavily Web Araması ({tavily_sonuc_sayisi} sonuç)"

    # ── Kart ─────────────────────────────────────────────────────────────────
    veri_ozeti_parcalari = [f"{baslik_sayisi} haber başlığı"]
    if tavily_var:
        veri_ozeti_parcalari.append(f"{tavily_sonuc_sayisi} web sonucu")
    if usgs_var:
        veri_ozeti_parcalari.append(f"{deprem_sayisi} deprem kaydı")
    if hava_var:
        veri_ozeti_parcalari.append("hava verisi")
    veri_ozeti = ", ".join(veri_ozeti_parcalari)

    return (
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "<b>◆ Analiz Kalite Kartı</b>\n"
        f"Veri: {_tg_html_escape(veri_ozeti)}\n"
        f"Bağlam: {_tg_html_escape(zenginlik)}\n"
        f"Motor: {_tg_html_escape(motor)}\n"
        f"Güven: <b>{g_toplam}/100</b> {_tg_html_escape(g_etiket)} — {_tg_html_escape(aciklama)}\n"
        f"Kaynaklar:\n{kaynak_satirlari}\n"
        "<i>Yatırım tavsiyesi değildir. Kendi araştırmanı yap.</i>"
    )

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
CLAUDE_API_KEY = (os.getenv("CLAUDE_API_KEY") or "").strip()
CLAUDE_MODEL = (os.getenv("CLAUDE_MODEL") or "claude-3-5-sonnet-20241022").strip()
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
    """Sırayla: GEMINI_API_KEYS (virgülle), GEMINI_API_KEY, _2, _3, ..., _10 — yinelenmez."""
    sira: list[str] = []
    gorduk: set[str] = set()
    
    # Önce GEMINI_API_KEYS (virgülle ayrılmış)
    ham = (os.getenv("GEMINI_API_KEYS") or "").strip()
    if ham:
        for parca in ham.split(","):
            k = parca.strip()
            if k and k not in gorduk:
                gorduk.add(k)
                sira.append(k)
    
    # Sonra GEMINI_API_KEY, _2, _3, ..., _10
    for i in range(1, 11):  # 1'den 10'a kadar
        if i == 1:
            ad = "GEMINI_API_KEY"
        else:
            ad = f"GEMINI_API_KEY_{i}"
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


def _claude_metin_uret(prompt: str) -> str:
    """Claude API (Anthropic) ile metin üret."""
    if not CLAUDE_API_KEY:
        raise RuntimeError("CLAUDE_API_KEY tanımlı değil")
    try:
        import anthropic
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "anthropic paketi yüklü değil. pip install anthropic"
        ) from e
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = ""
    for block in (message.content or []):
        if hasattr(block, "text"):
            text += block.text
    return text.strip()


def _claude_hatasi_gemini_yedegi_uygun(exc: BaseException) -> bool:
    """Claude başarısız → Gemini yedeğine düşülsün mü?"""
    msg = str(exc).lower()
    # Geçersiz anahtar — yedek işe yaramaz
    if "401" in msg or "authentication" in msg or "invalid x-api-key" in msg:
        return False
    # Kota, rate limit, overload → yedek dene
    return any(k in msg for k in ("429", "529", "overloaded", "rate", "quota", "timeout"))


def llm_metin_uret(prompt: str, user_id: int | str | None = None) -> str:
    """
    Tek LLM giriş noktası — kullanıcı planına göre motor seçer.

    Plan → Motor:
      claude  → Claude API (Anthropic) | anahtar yoksa Gemini'ye düşer
      pro     → Gemini (limit bypass, kota biterse DeepSeek)
      free    → Gemini (varsayılan)
      (AI_PROVIDER=deepseek olduğunda: tüm planlar DeepSeek önce, Gemini yedek)
    """
    # Claude planı: önce Claude dene
    if user_id is not None:
        plan_bilgi = _kullanici_plan_bilgisi(user_id)
        if plan_bilgi.get("plan") == "claude":
            if CLAUDE_API_KEY:
                try:
                    out = _claude_metin_uret(prompt)
                    if not out:
                        raise RuntimeError("Claude boş yanıt döndü")
                    logger.info("Claude API kullanıldı (user=%s)", user_id)
                    return out
                except Exception as e:
                    if _claude_hatasi_gemini_yedegi_uygun(e):
                        logger.warning("Claude başarısız, Gemini'ye düşülüyor (user=%s): %s", user_id, e)
                        # Gemini zincirine devam et
                    else:
                        raise
            else:
                logger.warning("Kullanıcı claude planında ama CLAUDE_API_KEY eksik, Gemini kullanılıyor (user=%s)", user_id)

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
VARLIK_SORGUSU = 2   # Kullanıcı varlık adı yazıyor (metin girişi, opsiyonel)
FORMAT_SECIMI = 3    # Çıktı: uzun anlatım / kısa özet
OKWIS_DETAY_SECIMI = 4  # Okwis kısa analizden sonra detay isteği

# Çıktı stilleri (mevsim analizi)
CIKTI_DETAY = "detay"
CIKTI_OZET = "ozet"

# Analiz türü (mesaj başlığı / bağlam)
ANALIZ_MEVSIM = "mevsim"
ANALIZ_HAVA = "hava"
ANALIZ_JEOPOLITIK = "jeopolitik"
ANALIZ_SEKTOR = "sektor"
ANALIZ_TRENDLER = "trendler"
ANALIZ_MAGAZIN = "magazin"
ANALIZ_OZEL_GUN = "ozel_gun"
ANALIZ_DOGAL_AFET = "dogal_afet"

# Telegram bot mesaj limiti (HTML dahil tüm metin)
TELEGRAM_MAX_UZUNLUK = 4096

# Dil kuralı — tüm analiz fonksiyonlarında kullanılır
# Bağlam verisi İngilizce olsa bile kullanıcıya her zaman Türkçe çıktı verilir.
ANALIZ_DIL_NOTU = (
    "Her zaman Türkçe yaz. "
    "Yabancı şirket/sembol/yer adları parantez içinde orijinal haliyle kalabilir."
)

# Ortak analiz kuralları — tüm modlarda geçerli (kısa, ~50 token)
_ORTAK_KURALLAR = (
    "Net yön ver: al/tut/sat/kaçın. Somut fiyat/tarih/seviye ver. "
    "Kaçamak dil kesinlikle yasak ('etkilenebilir', 'değerlendirilebilir', 'olabilir', 'düşünülebilir' yasak). "
    "Kesin yargı ver, ihtimal değil. Ters senaryo somut olsun. "
    "Markdown yasak. Em dash (—) yasak, tire (-) kullan. Türkçe yaz."
)

# Mod-spesifik analist kimlikleri (~40-50 token her biri)
_MOD_KIMLIK = {
    "mevsim":     "Mevsimsel döngü uzmanısın. Enerji/tarım/turizm/perakende mevsimselliğini analiz et. Sadece mevsimsel veriden çıkarım yap.",
    "hava":       "Hava-ekonomi analistisin. Hava verisini lojistik/enerji/tarım/turizm etkisine çevir. Sadece hava verisinden çıkarım yap.",
    "jeopolitik": "Jeopolitik risk analistisin. Haber başlıklarından enerji/ticaret/savunma risk kanallarını tespit et. Sadece haberlerden çıkarım yap.",
    "sektor":     "Sektör momentum analistisin. Haber başlıklarından yükselen/düşen sektörleri tespit et. Sadece sektör haberlerinden çıkarım yap.",
    "trendler":   "Dünya trendleri analistisin. Viral/sosyal olayların piyasa yansımasını analiz et. Sadece trend haberlerinden çıkarım yap.",
    "magazin":    "Marka-piyasa analistisin. Ünlü/viral olayların şirket değerine etkisini analiz et. Her çıkarım somut bir habere dayansın.",
    "ozel_gun":   "Takvim-tüketim analistisin. Özel günlerin perakende/lojistik/seyahat etkisini analiz et. Sadece özel gün verilerinden çıkarım yap.",
    "dogal_afet": "Afet ekonomisi analistisin. Deprem/afet verilerinden yeniden yapılanma ekonomisini analiz et. Afet yoksa açıkça belirt.",
    "okwis":      "Kıdemli makro yatırım analistisin, hedge fon geçmişin var. 8 modun verisini sentezleyip paranın nereye gideceğini kesin olarak söyle. Belirsiz dil yasak — her cümle bir karar içermeli. Kullanıcı ne olabileceğini değil, ne yapması gerektiğini öğrenmek istiyor.",
}

# Geriye dönük uyumluluk — eski kod _ANALIST_KIMLIK kullanıyorsa çalışsın
_ANALIST_KIMLIK = (
    "Kıdemli makro yatırım analistisin. Hedge fon deneyimin var. "
    "Bağlamdaki verileri yorumlayıp net, cesur, aksiyon odaklı çıkarımlar yap. " + _ORTAK_KURALLAR
)

# ─── Varlık Tipi Tespit ve Direktif İşlevleri ─────────────────────────────────

def _varlik_tipi_tespit(varlik: str) -> str:
    """Varlık adından türünü tespit et."""
    varlik_lower = varlik.lower() if varlik else ""
    
    # Emtia: petrol, altın, gümüş, bakır, doğalgaz, kömür, soya, buğday, kahve, kakao, demir, vs.
    emtialar = [
        "petrol", "crude", "gas", "gaz", "doğalgaz", "lng",
        "altın", "gold", "gümüş", "silver", "bakır", "copper",
        "demir", "iron", "kömür", "coal", "çinko", "zinc",
        "soya", "soybeans", "buğday", "wheat", "mısır", "corn",
        "kahve", "coffee", "kakao", "cocoa", "şeker", "sugar",
        "nikel", "nickel", "kurşun", "lead", "tın", "tin"
    ]
    
    # Kripto: bitcoin, ethereum, altcoin, vb.
    kriptolar = [
        "bitcoin", "btc", "ethereum", "eth", "altcoin", "crypto",
        "kripto", "doge", "cardano", "ada", "solana", "avax"
    ]
    
    # Hisse: şirket adları (Apple, Microsoft, Tesla, vs.) — genelde büyük harf veya ABD sembolü
    # Burada basit heuristic: 2-5 karakterli sembol (AAPL, MSFT) veya bilinen isim
    hisseler = [
        "apple", "aapl", "microsoft", "msft", "tesla", "tsla",
        "amazon", "amzn", "google", "googl", "meta", "metaaa",
        "nvidia", "nvda", "amd", "intel", "ibm", "coca", "ko",
        "mcdonald", "mcd", "accenture", "act", "sap", "ibm"
    ]
    
    # Para/Döviz
    dovizler = ["dolar", "dollar", "euro", "sterlin", "pound", "yen", "para", "currency"]
    
    for emtia in emtialar:
        if emtia in varlik_lower:
            return "emtia"
    
    for kripto in kriptolar:
        if kripto in varlik_lower:
            return "kripto"
    
    for hisse in hisseler:
        if hisse in varlik_lower:
            return "hisse"
    
    for doviz in dovizler:
        if doviz in varlik_lower:
            return "doviz"
    
    # Default: bilinmiyor (genelleme)
    return "diğer"


def _varlik_detay_directive(varlik: str, varlik_tipi: str, ay_adi: str, ulke: str) -> str:
    """
    Varlık odağı direktifi — sıkıştırılmış (~80 token).
    Modeli doğru çerçeveye kilitler, genel bilgi tekrarı yapmaz.
    """
    varlik_lower = varlik.lower() if varlik else ""

    kis_aylari = {"Aralık", "Ocak", "Şubat"}
    yaz_aylari = {"Haziran", "Temmuz", "Ağustos"}
    mevsim = "yaz" if ay_adi in yaz_aylari else ("kış" if ay_adi in kis_aylari else "geçiş")

    if varlik_tipi == "emtia":
        if "petrol" in varlik_lower or "crude" in varlik_lower or "gaz" in varlik_lower:
            if mevsim == "kış":
                odak = f"Kış enerji talebi piki ({ay_adi}): ısınma talebi + OPEC/dolar/stok üçgeni. {ulke} net ithalatçı - Brent belirleyici. Somut fiyat seviyeleri ver."
            elif mevsim == "yaz":
                odak = f"Yaz ulaşım/turizm talebi piki ({ay_adi}): klima+karayolu tüketimi + OPEC/stok/dolar. Kasırga riski Körfez üretimine. Somut fiyat seviyeleri ver."
            else:
                odak = f"Geçiş mevsimi ({ay_adi}): enerji talep belirsizliği + stok ayarlamaları + OPEC kararları. Volatilite yüksek. Somut fiyat seviyeleri ver."
        elif "altın" in varlik_lower or "gold" in varlik_lower or "xau" in varlik_lower:
            odak = f"Altın ({ay_adi}): reel faiz (nominal-enflasyon) + dolar kuru + jeopolitik risk iştahı üçgeni. {ulke} merkez bankası sinyali kritik. Somut fiyat seviyeleri ver."
        elif "gümüş" in varlik_lower or "silver" in varlik_lower:
            odak = f"Gümüş ({ay_adi}): sanayi talebi (elektronik/güneş) + altın korelasyonu + dolar. Somut fiyat seviyeleri ver."
        else:
            odak = f"{varlik} emtiası ({ay_adi}): mevsimsel arz/talep döngüsü + dolar kuru + üretici güveni. {ulke} penceresinden net yön ver."
    elif varlik_tipi == "kripto":
        odak = f"{varlik} kripto ({ay_adi}): risk iştahı (risk-on/off) + merkez bankası faiz beklentisi + regülasyon haberleri. {ulke} ve global perspektiften net yön ver."
    elif varlik_tipi == "hisse":
        odak = f"{varlik} hissesi ({ay_adi}): sektörel mevsimsellik + reel faiz (kazanç iskonto) + para kuru etkisi. Somut giriş/hedef/stop seviyeleri ver."
    elif varlik_tipi == "doviz":
        odak = f"{varlik} dövizi ({ay_adi}): faiz farkı (carry) + cari denge + jeopolitik güvenli liman. {ulke} merkez bankası beklentisi belirleyici. Somut kur seviyeleri ver."
    else:
        odak = f"{varlik} ({ay_adi}): varlık sınıfını belirle (emtia/kripto/hisse/döviz), mevsimsel ve makro etkiyi analiz et. Somut fiyat/seviye ver."

    return f"VARLIK ODAGI - {varlik.upper()}: {odak}"


# ─── Sabitler ─────────────────────────────────────────────────────────────────

ULKELER = ["Türkiye", "ABD", "Almanya", "İngiltere", "Japonya", "Çin", "Diğer"]
_METRICS_DIR = Path(__file__).resolve().parent / "metrics"
_ANALIZ_OLAYLARI_PATH = _METRICS_DIR / "analiz_olaylari.jsonl"
_KULLANIM_LIMIT_PATH = _METRICS_DIR / "kullanim_limitleri.json"
_PLAN_KAYIT_PATH = _METRICS_DIR / "plan_kullanicilari.json"
_ODEME_OLAYLARI_PATH = _METRICS_DIR / "odeme_olaylari.jsonl"
_PROFIL_PATH = _METRICS_DIR / "kullanici_profilleri.json"
_TAHMIN_KAYIT_PATH = _METRICS_DIR / "tahmin_kayitlari.jsonl"
ANALIZ_GUNLUK_LIMIT = int((os.getenv("ANALIZ_GUNLUK_LIMIT") or "3").strip() or 3)
ADMIN_USER_IDS = {
    int(x.strip())
    for x in (os.getenv("ADMIN_USER_IDS") or "").split(",")
    if x.strip().isdigit()
}

# Uyarı politikası (plan / MIMARI): kısa metin her zaman bot şablonuyla; model uzun disclaimer üretmez.
ANALIZ_FOOTER_HTML = "<b>Yeni analiz:</b> /analiz"


def _tg_html_escape(text: str) -> str:
    """Telegram HTML modu için model/ kullanıcı metnini güvenle kaçır."""
    return html.escape(text or "", quote=False)


def _analiz_html_temizle(text: str) -> str:
    """AI çıktısındaki izin verilen Telegram HTML taglarını koru, diğer her şeyi escape et.

    İzin verilen taglar: <b>, </b>, <i>, </i>, <code>, </code>
    Diğer tüm < > karakterleri escape edilir.
    """
    if not text:
        return ""
    # Önce izin verilen tagları geçici placeholder'larla koru
    korunan = text
    korunan = korunan.replace("<b>",    "\x00B_OPEN\x00")
    korunan = korunan.replace("</b>",   "\x00B_CLOSE\x00")
    korunan = korunan.replace("<i>",    "\x00I_OPEN\x00")
    korunan = korunan.replace("</i>",   "\x00I_CLOSE\x00")
    korunan = korunan.replace("<code>", "\x00C_OPEN\x00")
    korunan = korunan.replace("</code>","\x00C_CLOSE\x00")
    # Kalan tüm < > karakterlerini escape et
    korunan = html.escape(korunan, quote=False)
    # Placeholder'ları geri çevir
    korunan = korunan.replace("\x00B_OPEN\x00",  "<b>")
    korunan = korunan.replace("\x00B_CLOSE\x00", "</b>")
    korunan = korunan.replace("\x00I_OPEN\x00",  "<i>")
    korunan = korunan.replace("\x00I_CLOSE\x00", "</i>")
    korunan = korunan.replace("\x00C_OPEN\x00",  "<code>")
    korunan = korunan.replace("\x00C_CLOSE\x00", "</code>")
    return korunan


def _markdown_temizle(text: str) -> str:
    """
    Model çıktısındaki Markdown artıklarını temizle.
    **bold** → düz metin, *italic* → düz metin, — → -, ``` → kaldır.
    """
    if not text:
        return text
    # **bold** ve __bold__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # *italic* ve _italic_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # ``` kod blokları
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Em dash ve özel tireler → normal tire
    text = text.replace('—', '-').replace('–', '-')
    # Markdown başlıkları ### ## #
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Madde işaretleri * - + satır başında (zaten • kullanıyoruz)
    text = re.sub(r'^\s*[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    return text.strip()


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
        ANALIZ_SEKTOR: 70,
        ANALIZ_TRENDLER: 58,
        ANALIZ_MAGAZIN: 45,
        ANALIZ_OZEL_GUN: 82,
        ANALIZ_DOGAL_AFET: 65,
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


# ─── Kullanıcı Profil Sistemi ─────────────────────────────────────────────────

def _profil_yukle() -> dict[str, dict]:
    """Tüm kullanıcı profillerini yükle."""
    if not _PROFIL_PATH.exists():
        return {}
    try:
        with open(_PROFIL_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Profil dosyası okunamadı: %s", e)
    return {}


def _profil_kaydet(data: dict[str, dict]) -> None:
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_PROFIL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Profil dosyası yazılamadı: %s", e)


def _kullanici_profili_al(user_id: int | str) -> dict | None:
    """Kullanıcının profilini döndür; yoksa None."""
    data = _profil_yukle()
    return data.get(str(user_id))


def _kullanici_profili_kaydet(user_id: int | str, profil_metni: str) -> None:
    """Kullanıcı profilini kaydet/güncelle."""
    data = _profil_yukle()
    data[str(user_id)] = {
        "profil": profil_metni.strip(),
        "guncelleme": datetime.now(timezone.utc).isoformat(),
    }
    _profil_kaydet(data)


def _kullanici_profili_sil(user_id: int | str) -> bool:
    """Kullanıcı profilini sil. Başarılıysa True döner."""
    data = _profil_yukle()
    if str(user_id) in data:
        del data[str(user_id)]
        _profil_kaydet(data)
        return True
    return False


def _profil_okwis_blogu(profil: dict | None) -> str:
    """
    Profil varsa Okwis prompt'una eklenecek kişiselleştirme bloğunu üret.
    Yoksa boş string döner.
    """
    if not profil:
        return ""
    metin = (profil.get("profil") or "").strip()
    if not metin:
        return ""
    return (
        "### Kullanıcı Profili (KİŞİSELLEŞTİRME — bu bilgilere göre analizi özelleştir)\n"
        f"{metin}\n\n"
        "ÖNEMLI: Yukarıdaki profil bilgilerini kullanarak analizi tamamen bu kişiye özelleştir.\n"
        "- Elindeki varlıkları sahiplen: 'senin bitcoin'in', 'portföyündeki X' gibi konuş.\n"
        "- Soyut tavsiye değil, somut aksiyon ver: 'X fiyatına gelince sat', 'Y seviyesinde al' gibi.\n"
        "- Kişinin ilgi alanlarına ve risk profiline göre önceliklendirme yap.\n"
        "- Uzaktan konuşan analist değil, portföyünü bilen yakın bir danışman gibi konuş.\n"
        "- Profilde belirtilen her varlık için ayrı bir değerlendirme yap."
    )


def _kullanici_profili_html(profil: dict) -> str:
    """Profili Telegram HTML formatında göster."""
    metin = (profil.get("profil") or "").strip()
    guncelleme = (profil.get("guncelleme") or "")[:10]
    return (
        f"<b>◆ Profilin</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"{_tg_html_escape(metin)}\n\n"
        f"<i>Son güncelleme: {_tg_html_escape(guncelleme)}</i>"
    )


# ─── Profil Konuşma State'leri ────────────────────────────────────────────────
PROFIL_METIN_BEKLENIYOR = 10  # /profil komutundan sonra metin bekleniyor


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

    # Süresi dolmuş pro/claude kayıtlarını otomatik free yap.
    if plan in ("pro", "claude") and pro_until:
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
    """Pro veya Claude planında mı? (limit bypass için)"""
    info = _kullanici_plan_bilgisi(user_id)
    return info.get("plan") in ("pro", "claude")


def _kullanici_claude_mi(user_id: int | str) -> bool:
    """Claude planında mı?"""
    info = _kullanici_plan_bilgisi(user_id)
    return info.get("plan") == "claude"


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



# --- Tahmin Kayit Sistemi (Parca L) ---

def _yon_tespit(analiz_metni: str) -> str:
    metin = (analiz_metni or "").lower()
    bullish = ["yukseli", "yukseleceğ", "artis", "al/izle", "bullish", "toparlanma",
               "pozitif", "firsat", "kazanan", "pozisyon: al", "yon: yukseli",
               "yukseliyor", "guclen"]
    bearish = ["dusus", "duseceğ", "kacin", "bearish", "dusuyor", "gerileme",
               "negatif", "baski", "azalt", "pozisyon: sat", "yon: dusus"]
    neutral = ["yatay", "izle", "bekle", "notr", "neutral", "belirsiz", "pozisyon: tut"]
    b = sum(1 for w in bullish if w in metin)
    br = sum(1 for w in bearish if w in metin)
    n = sum(1 for w in neutral if w in metin)
    if b == 0 and br == 0 and n == 0:
        return "neutral"
    if b > br and b > n:
        return "bullish"
    if br > b and br > n:
        return "bearish"
    return "neutral"


def _sure_tespit(analiz_metni: str) -> str:
    metin = (analiz_metni or "").lower()
    if "1-2 hafta" in metin or "kisa vade" in metin or "kisa vade" in metin:
        return "1-2 hafta"
    if "1-3 ay" in metin or "orta vade" in metin:
        return "1-3 ay"
    if "3-12 ay" in metin or "uzun vade" in metin:
        return "3-12 ay"
    return "belirsiz"


def _tahmin_kaydet(*, mod: str, ulke: str, varlik: str, analiz_metni: str, user_id=None) -> dict:
    yon = _yon_tespit(analiz_metni)
    sure = _sure_tespit(analiz_metni)
    bugun = date.today()
    gun = {"1-2 hafta": 14, "1-3 ay": 45, "3-12 ay": 180}.get(sure, 14)
    hedef = bugun + timedelta(days=gun)
    tahmin = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "tarih": bugun.isoformat(),
        "mod": mod,
        "ulke": ulke,
        "varlik": varlik or "genel",
        "yon": yon,
        "sure": sure,
        "hedef_tarih": hedef.isoformat(),
        "dogrulandi": None,
        "gercek_yon": None,
        "user_id": str(user_id) if user_id else None,
    }
    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(_TAHMIN_KAYIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(tahmin, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Tahmin kaydedilemedi: %s", e)
    return tahmin


def _tahmin_gecmis_yukle(son_n: int = 20) -> list:
    if not _TAHMIN_KAYIT_PATH.exists():
        return []
    kayitlar = []
    try:
        with open(_TAHMIN_KAYIT_PATH, encoding="utf-8") as f:
            for satir in f:
                s = satir.strip()
                if not s:
                    continue
                try:
                    o = json.loads(s)
                    if isinstance(o, dict):
                        kayitlar.append(o)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning("Tahmin gecmisi okunamadi: %s", e)
    return kayitlar[-son_n:]


def _tahmin_istatistik() -> dict:
    kayitlar = _tahmin_gecmis_yukle(son_n=500)
    toplam = len(kayitlar)
    if not toplam:
        return {"toplam": 0, "dogrulanan": 0, "dogru": 0, "yanlis": 0, "oran": None}
    dogrulanan = [k for k in kayitlar if k.get("dogrulandi") is not None]
    dogru = [k for k in dogrulanan if k.get("dogrulandi") is True]
    yanlis = [k for k in dogrulanan if k.get("dogrulandi") is False]
    oran = (len(dogru) / len(dogrulanan) * 100) if dogrulanan else None
    return {"toplam": toplam, "dogrulanan": len(dogrulanan),
            "dogru": len(dogru), "yanlis": len(yanlis), "oran": oran}


def _gecmis_tahminler_html(son_n: int = 10) -> str:
    tahminler = _tahmin_gecmis_yukle(son_n)
    if not tahminler:
        return (
            "<b>\u25c6 Tahmin Ge\u00e7mi\u015fi</b>\n"
            "<b>\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501</b>\n\n"
            "Hen\u00fcz tahmin kay\u0131d\u0131 yok. Analiz yap\u0131nca otomatik kaydedilir."
        )
    yon_emoji = {"bullish": "\U0001f7e2", "bearish": "\U0001f534", "neutral": "\U0001f7e1"}
    ok_emoji = {True: "\u2713", False: "\u2717", None: "\u23f3"}
    istat = _tahmin_istatistik()
    s = [
        "<b>\u25c6 Tahmin Ge\u00e7mi\u015fi</b>",
        "<b>\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501</b>",
    ]
    s.append(f"Toplam: <b>{istat['toplam']}</b> tahmin   Do\u011frulanan: <b>{istat['dogrulanan']}</b>")
    if istat["oran"] is not None:
        dogru = istat['dogru']
        dogrulanan = istat['dogrulanan']
        oran = istat['oran']
        s.append(f"Do\u011fruluk: <b>{dogru}/{dogrulanan}</b> ({oran:.0f}%)")
    s.append("")
    for t in reversed(tahminler):
        tarih = (t.get("tarih") or "")[:10]
        mod = t.get("mod", "?")
        ulke = t.get("ulke", "?")
        varlik = t.get("varlik", "genel")
        yon = t.get("yon", "neutral")
        sure = t.get("sure", "?")
        hedef = (t.get("hedef_tarih") or "")[:10]
        dogru = t.get("dogrulandi")
        e_yon = yon_emoji.get(yon, "\u26aa")
        e_ok = ok_emoji.get(dogru, "\u23f3")
        varlik_str = f" \u00b7 {_tg_html_escape(varlik)}" if varlik != "genel" else ""
        s.append(
            f"{e_ok} <b>{_tg_html_escape(tarih)}</b> "
            f"{_tg_html_escape(mod)}/{_tg_html_escape(ulke)}{varlik_str}\n"
            f"   {e_yon} <b>{_tg_html_escape(yon)}</b> \u00b7 {_tg_html_escape(sure)} \u00b7 hedef: {_tg_html_escape(hedef)}"
        )
    s.extend([
        "",
        "<i>\u23f3 bekliyor \u00b7 \u2713 do\u011frulandi \u00b7 \u2717 yanl\u0131\u015f</i>",
        "<i>Do\u011frulama \u015fu an manuel \u2014 ileride fiyat API\u2019si ile otomatik olacak.</i>",
    ])
    return "\n".join(s)


def _performans_ozeti_hesapla() -> str:
    """
    JSONL analiz olaylarından canlı özet üretir.
    Dönüş: Telegram HTML uyumlu kısa metin.
    """
    if not _ANALIZ_OLAYLARI_PATH.exists():
        return (
            "<b>◆ Canlı Performans</b>\n"
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
            "<b>◆ Canlı Performans</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "Performans verisi okunamadı. Biraz sonra tekrar dene."
        )

    if not olaylar:
        return (
            "<b>◆ Canlı Performans</b>\n"
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
        "<b>◆ Canlı Performans</b>",
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
    reply_markup: InlineKeyboardMarkup | None = None,
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
                await query.edit_message_text(
                    parca, 
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup if i == toplam - 1 else None
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=parca,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup if i == toplam - 1 else None
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
    # Önce markdown artıklarını temizle
    govde = _markdown_temizle(govde or "")
    etiketler = "ÖZET|KISA_VADE|ORTA_VADE|SEKTÖR|ŞİRKETLER|VARLIK|GİRİŞİM|RİSK|GÜVEN|TERS_SENARYO|PİYASA_YÖNÜ|YÜKSELEN|DÜŞEN|MARKA_ETKİSİ"
    desen = re.compile(rf"^({etiketler})\s*:\s*(.*)$", re.IGNORECASE)
    alanlar: dict[str, str] = {}
    for ham in (govde or "").strip().splitlines():
        s = ham.strip()
        if not s:
            continue
        m = desen.match(s)
        if m:
            etiket = m.group(1).strip().upper()
            icerik = m.group(2).strip()
            alanlar[etiket] = icerik
        else:
            alanlar.setdefault("ÖZET", s)

    if not alanlar:
        return _tg_html_escape(govde)

    c: list[str] = []
    if "ÖZET" in alanlar:
        c.append(f"<b>◆ Özet</b>\n{_tg_html_escape(alanlar['ÖZET'])}")
    if "KISA_VADE" in alanlar:
        c.append(f"<b>▸ Kısa Vade  1-2 hafta</b>\n{_tg_html_escape(alanlar['KISA_VADE'])}")
    if "ORTA_VADE" in alanlar:
        c.append(f"<b>▸ Orta Vade  1-3 ay</b>\n{_tg_html_escape(alanlar['ORTA_VADE'])}")
    if "YÜKSELEN" in alanlar:
        c.append(f"<b>▲ Yükselen</b>\n{_tg_html_escape(alanlar['YÜKSELEN'])}")
    if "DÜŞEN" in alanlar:
        c.append(f"<b>▼ Düşen</b>\n{_tg_html_escape(alanlar['DÜŞEN'])}")
    if "SEKTÖR" in alanlar:
        c.append(f"<b>◈ Sektör</b>\n{_tg_html_escape(alanlar['SEKTÖR'])}")
    if "ŞİRKETLER" in alanlar:
        c.append(f"<b>◈ Şirketler</b>\n{_tg_html_escape(alanlar['ŞİRKETLER'])}")
    if "MARKA_ETKİSİ" in alanlar:
        c.append(f"<b>◈ Marka Etkisi</b>\n{_tg_html_escape(alanlar['MARKA_ETKİSİ'])}")
    if "VARLIK" in alanlar:
        c.append(f"<b>◈ Varlık</b>\n{_tg_html_escape(alanlar['VARLIK'])}")
    if "GİRİŞİM" in alanlar:
        c.append(f"<b>◈ Girişim</b>\n{_tg_html_escape(alanlar['GİRİŞİM'])}")
    if "PİYASA_YÖNÜ" in alanlar:
        c.append(f"<b>◈ Piyasa Yönü</b>\n{_tg_html_escape(alanlar['PİYASA_YÖNÜ'])}")

    alt: list[str] = []
    if "RİSK" in alanlar:
        alt.append(f"<b>▹ Risk</b>: {_tg_html_escape(alanlar['RİSK'])}")
    if "TERS_SENARYO" in alanlar:
        alt.append(f"<b>▹ Ters Senaryo</b>: {_tg_html_escape(alanlar['TERS_SENARYO'])}")
    if "GÜVEN" in alanlar:
        alt.append(f"<b>◆ Güven</b>: {_tg_html_escape(alanlar['GÜVEN'])}")
    if alt:
        c.append("\n".join(alt))

    return "\n\n".join(c)


def _detay_govdeyi_sadelestir_html(govde: str) -> str:
    """
    Uzun anlatım metnini Telegram'da premium kart bloklarına dönüştür.
    Markdown artıklarını temizler, yapılandırılmış bloklar oluşturur.
    """
    txt = _markdown_temizle((govde or "").strip())
    if not txt:
        return ""

    satirlar = [re.sub(r"\s+", " ", s).strip() for s in txt.splitlines() if s.strip()]

    if len(satirlar) <= 1:
        satirlar = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9])", txt)
            if s.strip()
        ]

    # Numaralı satırları (1. 2. 3.) tanı ve etiketle
    NUMARALI = re.compile(r'^(\d+)\.\s+(.*)')
    ETIKET_MAP = {
        "1": ("▸", "Durum"),
        "2": ("▸", "Etki Zinciri"),
        "3": ("▸", "Kısa Vade"),
        "4": ("▸", "Orta Vade"),
        "5": ("▸", "Uzun Vade"),
        "6": ("◆", "Fırsatlar"),
        "7": ("◈", "Girişim"),
        "8": ("◆", "Güven"),
        "9": ("▹", "Ters Senaryo"),
    }

    icerik_satirlari: list[str] = []
    guven_satiri = ""
    ters_satiri = ""
    risk_satiri = ""

    for s in satirlar:
        u = s.upper()
        if u.startswith("GÜVEN:"):
            guven_satiri = s.split(":", 1)[1].strip() if ":" in s else s
            continue
        if u.startswith("TERS_SENARYO:"):
            ters_satiri = s.split(":", 1)[1].strip() if ":" in s else s
            continue
        if u.startswith("RİSK:"):
            risk_satiri = s.split(":", 1)[1].strip() if ":" in s else s
            continue
        icerik_satirlari.append(s)

    bloklar: list[str] = []

    # Numaralı yapı varsa her satırı kendi başlığıyla göster
    numarali_var = any(NUMARALI.match(s) for s in icerik_satirlari)

    if numarali_var:
        for s in icerik_satirlari:
            m = NUMARALI.match(s)
            if m:
                num = m.group(1)
                icerik = m.group(2).strip()
                emoji, baslik = ETIKET_MAP.get(num, ("▸", f"Adım {num}"))
                bloklar.append(f"<b>{emoji} {baslik}</b>\n{_tg_html_escape(icerik)}")
            else:
                bloklar.append(_tg_html_escape(s))
    else:
        # Serbest metin: 3 bölüme böl
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

        def blok_baslikli(emoji: str, baslik: str, satirs: list[str]) -> str:
            if not satirs:
                return ""
            govde2 = "\n".join([f"› {_tg_html_escape(x)}" for x in satirs])
            return f"<b>{emoji} {baslik}</b>\n{govde2}"

        for b in (
            blok_baslikli("▸", "Durum", durum),
            blok_baslikli("▸", "Etki Zinciri", etki),
            blok_baslikli("◆", "Fırsat Alanı", firsat),
        ):
            if b:
                bloklar.append(b)

    alt: list[str] = []
    if risk_satiri:
        alt.append(f"<b>▹ Risk</b>  {_tg_html_escape(risk_satiri)}")
    if ters_satiri:
        alt.append(f"<b>▹ Ters Senaryo</b>  {_tg_html_escape(ters_satiri)}")
    if guven_satiri:
        alt.append(f"<b>◆ Güven</b>  {_tg_html_escape(guven_satiri)}")
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
    elif analiz_turu == ANALIZ_SEKTOR:
        mod_etiket = "Sektör Trendleri"
        uzun_baslik = "Sektör · Uzun anlatım"
    elif analiz_turu == ANALIZ_TRENDLER:
        mod_etiket = "Dünya Trendleri"
        uzun_baslik = "Trendler · Uzun anlatım"
    elif analiz_turu == ANALIZ_MAGAZIN:
        mod_etiket = "Magazin/Viral"
        uzun_baslik = "Magazin · Uzun anlatım"
    elif analiz_turu == ANALIZ_OZEL_GUN:
        mod_etiket = "Özel Günler"
        uzun_baslik = "Özel Günler · Uzun anlatım"
    elif analiz_turu == ANALIZ_DOGAL_AFET:
        mod_etiket = "Doğal Afet"
        uzun_baslik = "Doğal Afet · Uzun anlatım"
    else:
        mod_etiket = "Mevsim"
        uzun_baslik = "Mevsim · Uzun anlatım"

    alt_cizgi = "<b>━━━━━━━━━━━━━━━━━━━━</b>"

    footer = f"\n\n{ANALIZ_FOOTER_HTML}"

    if cikti_stili == CIKTI_OZET:
        govde_html = _ozet_satirlari_html(govde)
        return (
            f"<b>◆ Okwis AI</b> · <i>{_tg_html_escape('◆ Kısa Özet')}</i>\n"
            f"{alt_cizgi}\n"
            f"▸ <b>{e_ulke}</b> · <i>{_tg_html_escape(mod_etiket)}</i>\n"
            f"{alt_cizgi}\n\n"
            f"{govde_html}\n"
            f"{footer}"
        )

    govde_html = _detay_govdeyi_sadelestir_html(govde)
    return (
        f"<b>◆ Okwis AI</b> · <i>{_tg_html_escape(uzun_baslik)}</i>\n"
        f"{alt_cizgi}\n"
        f"▸ <b>{e_ulke}</b>\n"
        f"🧩 <i>{_tg_html_escape('Detaylı Analiz')}</i>\n"
        f"{alt_cizgi}\n\n"
        f"{govde_html}"
        f"{footer}"
    )

# ─── Gemini Prompt ────────────────────────────────────────────────────────────

def mevsim_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
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
    dil_notu = ANALIZ_DIL_NOTU

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_detay = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)
        varlik_notu = f"\n\n{varlik_detay}"

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_MEVSIM, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    guven = _guven_skoru_hesapla(ANALIZ_MEVSIM, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    mod_kimlik = _MOD_KIMLIK["mevsim"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: {ulke} / {ay_adi} {yil} mevsimsel döngüsünü analiz et.\n"
        "Odak: hangi sektörler bu mevsimde güçlenir/zayıflar? Enerji/tarım/turizm/perakende döngüleri nerede? "
        "Mevsim geçişi yaklaşıyorsa hangi sektörel kayma bekleniyor? Haberler mevsimsel tezi destekliyor mu?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — MEVSİM KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (bu mevsimde ne oluyor — mevsimsel dinamikten tek cümle)\n"
            "KISA_VADE: (1-2 hafta — mevsimsel momentum: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — mevsim geçişi yaklaşırken hangi sektör öne çıkar)\n"
            "SEKTÖR: (bu mevsimde güçlenen 1-2 sektör)\n"
            f"ŞİRKETLER: ({ulke} piyasasından mevsimsel kazanan 3 isim)\n"
            "VARLIK: (mevsimsel emtia/ETF/döviz kanalı veya —)\n"
            "RİSK: (mevsimsel tezi bozacak tek koşul)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X olursa mevsimsel tez çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Mevsimsel veriden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — MEVSİM DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. MEVSİMSEL DURUM: Bu ay hangi mevsimsel döngü aktif? Hangi sektörler bu döngüde?\n"
            "2. ETKİ ZİNCİRİ: Mevsimden sektöre, sektörden varlığa — en az 2 adım.\n"
            "3. KISA VADE (1-2 hafta): Mevsimsel momentum ne yönde? al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Mevsim geçişi yaklaşırken hangi sektör/varlık öne çıkar?\n"
            "5. UZUN VADE (3-12 ay): Bu mevsimsel döngünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından mevsimsel kazanan 3 şirket/varlık — neden bu dönemde?\n"
            "7. GİRİŞİM AÇISI: Bu mevsimde büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X olursa mevsimsel tez çöker.\n\n"
            f"Kurallar: Mevsimsel veriden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM mevsim analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


def _hava_petrol_lojistik_directive(ay_adi: str, ulke: str) -> str:
    """Hava → lojistik → petrol talebi zinciri — sıkıştırılmış direktif."""
    return (
        f"HAVA-PETROL ZİNCİRİ ({ay_adi}): Hava koşulları karayolu lojistik verimliliğini etkiler "
        f"(kar/yağmur → yakıt tüketimi +2-4%, sıcaklık aşırılığı → motor tüketimi artar). "
        f"{ulke} petrolün %80+ ithal ediyor — Brent/WTI ana belirleyici, yerel talep marjinal. "
        "OPEC kararları + dolar kuru + stok seviyeleri fiyatı tayin eder, hava sadece kısa vadeli talep pulse'ı yaratır. "
        f"Soru: {ay_adi} hava tahmininin lojistik üzerindeki etkisi Brent fiyatını amplify mi ediyor, sönümlüyor mu?"
    )


def hava_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    """Güncel hava + tahmin bağlamıyla makro/yatırım temalı hava analizi (LLM)."""

    from datetime import datetime
    aylar = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    bugun = datetime.now()
    ay_adi = aylar[bugun.month - 1]
    yil = bugun.year
    dil_notu = ANALIZ_DIL_NOTU

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_detay = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)
        varlik_notu = f"\n\n{varlik_detay}\n\n**HAVA BAĞLANTISI:** Yukarıdaki hava verisi bu varlığın fiyatını nasıl etkileyeceğini göz önünde tut."
        if "petrol" in varlik.lower() or "crude" in varlik.lower() or "gaz" in varlik.lower():
            petrol_hava_ek = _hava_petrol_lojistik_directive(ay_adi, ulke)
            varlik_notu += f"\n\n{petrol_hava_ek}"

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_HAVA, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    guven = _guven_skoru_hesapla(ANALIZ_HAVA, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    mod_kimlik = _MOD_KIMLIK["hava"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: {ulke} başkentinin anlık hava ve 5 günlük tahmininden ekonomik çıkarım yap.\n"
        "Odak: mevcut koşullar hangi sektörleri etkiliyor? 5 günlük tahmin lojistik/enerji/tarım/turizm için ne anlama geliyor? "
        "Aşırı hava olayı var mı? Hava verisi haberlerle örtüşüyor mu?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — HAVA KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (mevcut hava koşullarının ekonomik özeti — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — hava tahmininden sektörel etki: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — mevsimsel hava geçişinin sektörel yansıması)\n"
            "SEKTÖR: (hava koşullarından en çok etkilenen 1-2 sektör)\n"
            f"ŞİRKETLER: ({ulke} piyasasından hava-hassas 3 isim)\n"
            "VARLIK: (hava bağlantılı emtia/ETF veya —)\n"
            "RİSK: (hava tezini bozacak tek koşul)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer hava X yönde değişirse tez çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Hava verisinden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — HAVA DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. HAVA DURUMU: Anlık koşullar ve 5 günlük tahmin — ne görüyorum?\n"
            "2. ETKİ ZİNCİRİ: Hava → sektör → varlık fiyatı — en az 2 adım.\n"
            "3. KISA VADE (1-2 hafta): Hava tahmininden sektörel etki. al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Mevsimsel hava geçişi yaklaşırken hangi sektör/varlık öne çıkar?\n"
            "5. UZUN VADE (3-12 ay): Bu hava döngüsünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından hava-hassas 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu hava koşullarında büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer hava X yönde değişirse tez çöker.\n\n"
            f"Kurallar: Hava verisinden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM hava analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


def jeopolitik_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    """Jeopolitik haber başlıkları bağlamıyla makro/yatırım temalı jeopolitik analizi (LLM)."""

    from datetime import datetime
    bugun = datetime.now()
    aylar = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = aylar[bugun.month - 1]
    yil = bugun.year
    dil_notu = ANALIZ_DIL_NOTU

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_detay = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)
        varlik_notu = f"\n\n{varlik_detay}\n\n**JEOPOLİTİK BAĞLANTISI:** Yukarıdaki jeopolitik gelişmeleri bu varlığın fiyat dinamikleriyle ilişkilendirtip analiz et."

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_JEOPOLITIK, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    guven = _guven_skoru_hesapla(ANALIZ_JEOPOLITIK, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    mod_kimlik = _MOD_KIMLIK["jeopolitik"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: Bağlamdaki güncel haber başlıklarından {ulke} için jeopolitik risk haritası çıkar.\n"
        "Odak: hangi gerilimler/çatışmalar/yaptırımlar var? Enerji/ticaret/savunma/döviz kanallarına etkisi? "
        "Risk artıyor mu azalıyor mu? Hangi varlıklar kazanır/kaybeder?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — JEOPOLİTİK KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (bağlamdaki en kritik jeopolitik gelişme ve piyasa etkisi — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — jeopolitik riskten etkilenen varlık: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — jeopolitik gerilim sürer/azalırsa hangi sektör öne çıkar)\n"
            "SEKTÖR: (jeopolitik gelişmeden en çok etkilenen 1-2 sektör)\n"
            f"ŞİRKETLER: ({ulke} piyasasından jeopolitik-hassas 3 isim)\n"
            "VARLIK: (jeopolitik riskten kazanan emtia/ETF/döviz veya —)\n"
            "RİSK: (jeopolitik tezi tersine çevirecek tek gelişme)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X diplomatik/askeri gelişme olursa tez çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — JEOPOLİTİK DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. JEOPOLİTİK TABLO: Bağlamdaki haberlerde ne görüyorum? En kritik gelişme hangisi?\n"
            "2. ETKİ ZİNCİRİ: Jeopolitik gelişme → enerji/ticaret/savunma kanalı → piyasa etkisi.\n"
            "3. KISA VADE (1-2 hafta): Jeopolitik riskten etkilenen varlık. al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Gerilim sürer/azalırsa hangi sektör/varlık öne çıkar?\n"
            "5. UZUN VADE (3-12 ay): Bu jeopolitik döngünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından jeopolitik-hassas 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu jeopolitik ortamda büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X diplomatik/askeri gelişme olursa tez çöker.\n\n"
            f"Kurallar: Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM jeopolitik analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Sektör Trendleri Analizi ─────────────────────────────────────────────────

def sektor_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]
    yil = now.year
    dil_notu = "Her zaman Türkçe yaz. Yabancı şirket/sembol adları parantez içinde orijinal haliyle kalabilir."
    guven = _guven_skoru_hesapla(ANALIZ_SEKTOR, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_notu = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_SEKTOR, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    mod_kimlik = _MOD_KIMLIK["sektor"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: Bağlamdaki iş dünyası ve teknoloji haberlerinden {ulke} için sektörel momentum haritası çıkar.\n"
        "Odak: hangi sektörler öne çıkıyor/gerileme sinyali veriyor? Hangi şirket haberi sektörel trendi temsil ediyor? "
        f"Bu sektörel hareket {ulke} piyasasına nasıl yansıyor?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — SEKTÖR KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (bağlamdaki haberlerden en güçlü sektörel sinyal — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — sektörel momentum: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — hangi sektör büyümeye devam eder, hangisi yavaşlar)\n"
            "SEKTÖR: (bağlamdaki haberlerden öne çıkan 1-2 sektör)\n"
            f"ŞİRKETLER: ({ulke} piyasasından sektörel kazanan 3 isim)\n"
            "VARLIK: (sektörel ETF/emtia/döviz kanalı veya —)\n"
            "RİSK: (sektörel tezi bozacak tek gelişme)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X sektörel gelişme olursa tez çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — SEKTÖR DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. SEKTÖREL TABLO: Bağlamdaki haberlerde hangi sektörler öne çıkıyor? Hangileri gerileme sinyali veriyor?\n"
            "2. ETKİ ZİNCİRİ: Haber → sektörel momentum → varlık fiyatı — en az 2 adım.\n"
            "3. KISA VADE (1-2 hafta): Sektörel momentum ne yönde? al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Hangi sektör büyümeye devam eder? Neden?\n"
            "5. UZUN VADE (3-12 ay): Bu sektörel döngünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından sektörel kazanan 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu sektörel ortamda büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X sektörel gelişme olursa tez çöker.\n\n"
            f"Kurallar: Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM sektör analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Dünya Trendleri Analizi ──────────────────────────────────────────────────

def trendler_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]
    yil = now.year
    dil_notu = "Her zaman Türkçe yaz. Yabancı şirket/sembol adları parantez içinde orijinal haliyle kalabilir."
    guven = _guven_skoru_hesapla(ANALIZ_TRENDLER, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_notu = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_TRENDLER, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    mod_kimlik = _MOD_KIMLIK["trendler"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: Bağlamdaki güncel dünya gündemi haberlerinden {ulke} için piyasa yansıması çıkar.\n"
        "Odak: hangi küresel trendler/viral olaylar öne çıkıyor? Tüketici davranışını nasıl değiştiriyor? "
        f"{ulke} piyasasında somut fırsat/risk yaratıyor mu? Trend kısa vadeli viral mı, uzun vadeli yapısal mı?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — DÜNYA TRENDLERİ KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (bağlamdaki en güçlü küresel trend ve piyasa yansıması — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — trend momentumu: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — trend yapısal mı viral mı? Hangi sektör kazanır?)\n"
            "SEKTÖR: (trendin en çok etkilediği 1-2 sektör)\n"
            f"ŞİRKETLER: ({ulke} piyasasından trend-kazanan 3 isim)\n"
            "VARLIK: (trend bağlantılı ETF/emtia/döviz veya —)\n"
            "RİSK: (trend tezini bozacak tek gelişme)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X olursa trend tezi çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — DÜNYA TRENDLERİ DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. TREND TABLOSU: Bağlamdaki haberlerde hangi küresel trendler öne çıkıyor?\n"
            "2. ETKİ ZİNCİRİ: Trend → tüketici/teknoloji davranışı → sektör → varlık fiyatı.\n"
            "3. KISA VADE (1-2 hafta): Trend momentumu ne yönde? al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Trend yapısal mı viral mı? Hangi sektör kazanır?\n"
            "5. UZUN VADE (3-12 ay): Bu trendin uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından trend-kazanan 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu trend ortamında büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X olursa trend tezi çöker.\n\n"
            f"Kurallar: Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM trendler analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Magazin / Viral Analizi ──────────────────────────────────────────────────

def magazin_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]
    yil = now.year
    dil_notu = "Her zaman Türkçe yaz. Yabancı şirket/sembol adları parantez içinde orijinal haliyle kalabilir."
    guven = _guven_skoru_hesapla(ANALIZ_MAGAZIN, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_notu = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_MAGAZIN, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    mod_kimlik = _MOD_KIMLIK["magazin"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: Bağlamdaki magazin, eğlence ve viral haberlerden {ulke} için somut piyasa çıkarımı yap.\n"
        "Odak: hangi ünlü/marka/viral olay öne çıkıyor? Hangi şirket/sektörü etkiliyor? "
        "Viral etki kısa vadeli spekülasyon mu, uzun vadeli marka değeri değişimi mi?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — MAGAZİN/VİRAL KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (bağlamdaki en güçlü magazin/viral haber ve piyasa etkisi — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — viral etki: al/izle/kaçın — hangi hisse/marka?)\n"
            "ORTA_VADE: (1-3 ay — viral etki kalıcı mı geçici mi? Marka değeri değişimi?)\n"
            "MARKA_ETKİSİ: (bağlamdaki haberden etkilenen 1-2 marka/şirket)\n"
            f"ŞİRKETLER: ({ulke} piyasasından magazin-hassas 3 isim)\n"
            "VARLIK: (viral etki bağlantılı ETF/hisse/döviz veya —)\n"
            "RİSK: (viral tezi bozacak tek gelişme)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X olursa viral tez çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Bağlamdaki haberlerden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — MAGAZİN/VİRAL DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. MAGAZİN TABLOSU: Bağlamdaki haberlerde hangi ünlü/marka/viral olay öne çıkıyor?\n"
            "2. ETKİ ZİNCİRİ: Viral haber → marka algısı → tüketici davranışı → hisse/sektör fiyatı.\n"
            "3. KISA VADE (1-2 hafta): Viral etki hangi hisse/markayı etkiliyor? al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Viral etki kalıcı mı geçici mi? Marka değeri değişimi?\n"
            "5. UZUN VADE (3-12 ay): Bu magazin döngüsünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından magazin-hassas 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu viral ortamda büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X olursa viral tez çöker.\n\n"
            f"Kurallar: Her çıkarım bağlamdaki somut bir habere dayandırılmalı. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM magazin analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Özel Günler Analizi ──────────────────────────────────────────────────────

def ozel_gun_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]
    yil = now.year
    dil_notu = "Her zaman Türkçe yaz. Yabancı şirket/sembol adları parantez içinde orijinal haliyle kalabilir."
    guven = _guven_skoru_hesapla(ANALIZ_OZEL_GUN, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_notu = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_OZEL_GUN, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    mod_kimlik = _MOD_KIMLIK["ozel_gun"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: Bağlamdaki yaklaşan bayram/tatil/özel günlerden {ulke} için tüketim ve sektörel çıkarım yap.\n"
        "Odak: hangi sektörlerde talep artışı? Özel gün öncesi/sonrası tüketim kalıbı? "
        f"{ulke} piyasasında hangi şirketlere somut gelir artışı? Lojistik kapasitesi zorlanıyor mu?\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — ÖZEL GÜNLER KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (yaklaşan en kritik özel gün ve tüketim etkisi — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — özel gün öncesi tüketim dalgası: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — özel gün sonrası tüketim yavaşlaması ve sektörel etki)\n"
            "SEKTÖR: (özel günden en çok kazanan 1-2 sektör)\n"
            f"ŞİRKETLER: ({ulke} piyasasından özel gün-kazanan 3 isim)\n"
            "VARLIK: (özel gün bağlantılı ETF/emtia/döviz veya —)\n"
            "RİSK: (özel gün tezini bozacak tek koşul)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X olursa özel gün tüketim tezi çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Bağlamdaki özel günlerden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — ÖZEL GÜNLER DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. ÖZEL GÜN TABLOSU: Bağlamdaki yaklaşan özel günler neler? Hangisi en büyük tüketim etkisi yaratıyor?\n"
            "2. ETKİ ZİNCİRİ: Özel gün → tüketim dalgası → sektör → şirket geliri — en az 2 adım.\n"
            "3. KISA VADE (1-2 hafta): Özel gün öncesi tüketim dalgası. al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Özel gün sonrası tüketim yavaşlaması ve sektörel etki.\n"
            "5. UZUN VADE (3-12 ay): Bu özel gün döngüsünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından özel gün-kazanan 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu özel gün ortamında büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X olursa özel gün tüketim tezi çöker.\n\n"
            f"Kurallar: Bağlamdaki özel günlerden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM özel gün analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Doğal Afet Analizi ───────────────────────────────────────────────────────

def dogal_afet_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "", user_id: int | str | None = None) -> str:
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]
    yil = now.year
    dil_notu = "Her zaman Türkçe yaz. Yabancı şirket/sembol adları parantez içinde orijinal haliyle kalabilir."
    guven = _guven_skoru_hesapla(ANALIZ_DOGAL_AFET, baglam_metni)
    g_toplam = guven["toplam"]
    g_etiket = guven["etiket"]

    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_tipi = _varlik_tipi_tespit(varlik)
        varlik_notu = _varlik_detay_directive(varlik, varlik_tipi, ay_adi, ulke)

    prob_notu = _ilgili_prob_zincirleri(ANALIZ_DOGAL_AFET, ulke, varlik)
    if prob_notu:
        varlik_notu += f"\n\n{prob_notu}"

    mod_kimlik = _MOD_KIMLIK["dogal_afet"]
    mod_direktifi = (
        f"{mod_kimlik}\n"
        f"Görev: Bağlamdaki USGS deprem verileri ve afet haberlerinden {ulke} için somut ekonomik çıkarım yap.\n"
        "Odak: hangi bölgeler etkileniyor? Hangi sektörler doğrudan etkileniyor (inşaat/sigorta/enerji/lojistik/gıda)? "
        f"Yeniden yapılanma ekonomisi ne zaman başlar? Afet bölgesi {ulke} ile ticaret/tedarik bağlantısı var mı? "
        "Afet yoksa açıkça belirt.\n"
        f"{_ORTAK_KURALLAR}"
    )

    if cikti_stili == CIKTI_OZET:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — DOĞAL AFET KISA ÖZET\n\n"
            "Tam olarak 9 satır yaz, ETİKET: içerik formatında:\n\n"
            "ÖZET: (bağlamdaki en kritik afet/deprem ve ekonomik etkisi — tek cümle)\n"
            "KISA_VADE: (1-2 hafta — afet sonrası acil ihtiyaç sektörü: al/izle/kaçın)\n"
            "ORTA_VADE: (1-3 ay — yeniden yapılanma ekonomisi hangi sektörü büyütür)\n"
            "SEKTÖR: (afetten en çok kazanan 1-2 sektör: inşaat/sigorta/enerji/lojistik)\n"
            f"ŞİRKETLER: ({ulke} piyasasından afet-kazanan 3 isim)\n"
            "VARLIK: (afet bağlantılı emtia/ETF/döviz veya —)\n"
            "RİSK: (afet tezini bozacak tek koşul)\n"
            f"GÜVEN: ({g_toplam}/100 — {g_etiket})\n"
            "TERS_SENARYO: (eğer X olursa afet ekonomi tezi çöker)\n\n"
            f"Kurallar: Sadece 9 satır. Bağlamdaki afet verilerinden çıkarım yap. {dil_notu}"
        )
    else:
        prompt = (
            f"{baglam_metni}{varlik_notu}\n\n"
            "---\n"
            f"{mod_direktifi}\n\n"
            f"Görev: {ulke} / {ay_adi} {yil} — DOĞAL AFET DETAYLI ANALİZ\n\n"
            "Şu yapıda yaz (10-12 cümle, düz metin):\n\n"
            "1. AFET TABLOSU: Bağlamdaki depremler/afetler neler? Hangi bölge, hangi büyüklük, hangi ekonomik önem?\n"
            "2. ETKİ ZİNCİRİ: Afet → altyapı hasarı → tedarik zinciri → sektör → varlık fiyatı.\n"
            "3. KISA VADE (1-2 hafta): Afet sonrası acil ihtiyaç sektörü. al/izle/kaçın.\n"
            "4. ORTA VADE (1-3 ay): Yeniden yapılanma ekonomisi hangi sektörü büyütür?\n"
            "5. UZUN VADE (3-12 ay): Bu afet döngüsünün uzun vadeli kazananı kim?\n"
            f"6. SOMUT FIRSATLAR: {ulke} piyasasından afet-kazanan 3 şirket/varlık — neden şimdi?\n"
            "7. GİRİŞİM AÇISI: Bu afet ortamında büyüyen hangi ihtiyaç/problem alanı var?\n"
            f"8. GÜVEN: {g_toplam}/100 ({g_etiket})\n"
            "9. TERS_SENARYO: Eğer X olursa afet ekonomi tezi çöker.\n\n"
            f"Kurallar: Bağlamdaki afet verilerinden çıkarım yap. {dil_notu}"
        )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text
    except Exception as e:
        logger.exception("LLM doğal afet analizi: %s", e)
        return _llm_hata_kullanici_metni(e)


# ─── Okwis — Tanrının Gözü (Tüm Modların Birleşimi) ─────────────────────────

async def _topla_tum_baglamlari(
    ulke: str,
    ilerleme_cb=None,  # async callable(tamamlanan: int, toplam: int, mod_adi: str, basarili: bool)
) -> dict[str, str]:
    """
    Tüm modların bağlamlarını topla.
    ilerleme_cb verilirse her mod tamamlandığında çağrılır — canlı bildirim için.
    """
    MODLAR = [
        ("mevsim",     "◈ Mevsim",        topla_mevsim_baglami),
        ("jeopolitik", "◈ Jeopolitik",     topla_jeopolitik_baglami),
        ("sektor",     "◈ Sektör",         topla_sektor_baglami),
        ("trendler",   "◈ Dünya Trendleri",topla_trendler_baglami),
        ("magazin",    "◈ Magazin",        topla_magazin_baglami),
        ("ozel_gun",   "◈ Özel Günler",    topla_ozel_gunler_baglami),
        ("dogal_afet", "◈ Doğal Afet",     topla_dogal_afet_baglami),
        ("hava",       "◈ Hava",           topla_hava_baglami),
    ]
    toplam = len(MODLAR)
    baglamlar: dict[str, str] = {}

    for i, (anahtar, adi, fn) in enumerate(MODLAR, start=1):
        try:
            deger = await asyncio.to_thread(fn, ulke)
            baglamlar[anahtar] = deger
            basarili = True
        except Exception as e:
            logger.warning("Okwis bağlam hatası (%s): %s", anahtar, e)
            baglamlar[anahtar] = ""
            basarili = False

        if ilerleme_cb:
            try:
                await ilerleme_cb(i, toplam, adi, basarili)
            except Exception:
                pass  # bildirim hatası analizi durdurmasın

    return baglamlar


def okwis_analizi_yap(ulke: str, baglamlar: dict[str, str], varlik: str = "", profil: dict | None = None, stil: str = "kisa", user_id: int | str | None = None) -> str:
    """Okwis — Tanrının Gözü.
    stil: 'kisa' → net, aksiyon odaklı özet | 'detay' → tam derinlikli analiz
    """
    now = datetime.now()
    ay_adlari = ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")
    ay_adi = ay_adlari[now.month - 1]
    yil = now.year

    etiketler = {
        "mevsim": "MEVSİM", "hava": "HAVA", "jeopolitik": "JEOPOLİTİK",
        "sektor": "SEKTÖR", "trendler": "TRENDLER", "magazin": "MAGAZİN",
        "ozel_gun": "ÖZEL GÜNLER", "dogal_afet": "DOĞAL AFET",
    }
    # Dinamik ağırlıklandırma: yüksek sinyal modlara daha fazla bağlam
    _MOD_ONEM = {
        "jeopolitik": 1.5, "mevsim": 1.3, "sektor": 1.2, "dogal_afet": 1.1,
        "hava": 1.0, "trendler": 0.8, "ozel_gun": 0.7, "magazin": 0.6,
    }
    baz_limit = 220 if stil == "kisa" else 480
    parcalar = []
    for key, etiket in etiketler.items():
        v = baglamlar.get(key, "").strip()
        if v:
            mod_limit = int(baz_limit * _MOD_ONEM.get(key, 1.0))
            parcalar.append(f"[{etiket}]\n{v[:mod_limit]}")
    birlestik_baglam = "\n\n".join(parcalar)

    # Varlık araması varsa Tavily ile zenginleştir
    try:
        from web_arama import varlik_sorgulari, tavily_ara, tavily_metin_ozeti, _api_key
        if varlik and varlik.strip() and _api_key():
            varlik_sonuclar = []
            gorulmus: set[str] = set()
            for sorgu in varlik_sorgulari(ulke, varlik)[:2]:
                for s in tavily_ara(sorgu, max_sonuc=3, guncel_mi=True):
                    if s["url"] not in gorulmus:
                        gorulmus.add(s["url"])
                        varlik_sonuclar.append(s)
            varlik_sonuclar.sort(key=lambda x: x["score"], reverse=True)
            tavily_blok = tavily_metin_ozeti(varlik_sonuclar[:4], baslik=f"Güncel Web Araması — {varlik}")
            if tavily_blok:
                birlestik_baglam += f"\n\n{tavily_blok}"
    except Exception as _e:
        import logging as _lg
        _lg.getLogger(__name__).warning("Okwis Tavily araması başarısız: %s", _e)

    # Varlık varsa gerçek zamanlı fiyat verisini bağlama ekle
    if varlik and varlik.strip():
        try:
            from fiyat_servisi import sembol_tespit, kripto_fiyat_al, hisse_fiyat_al
            tespit = sembol_tespit(varlik)
            if tespit:
                tip, sembol = tespit
                if tip == "kripto":
                    fiyat_bilgi = kripto_fiyat_al(sembol)
                else:
                    fiyat_bilgi = hisse_fiyat_al(sembol)
                if fiyat_bilgi:
                    fiyat = fiyat_bilgi.get("fiyat_usd") or fiyat_bilgi.get("fiyat")
                    yuksek = fiyat_bilgi.get("yuksek_24s") or fiyat_bilgi.get("yuksek_gun")
                    dusuk = fiyat_bilgi.get("dusuk_24s") or fiyat_bilgi.get("dusuk_gun")
                    degisim = fiyat_bilgi.get("degisim_24s") or fiyat_bilgi.get("degisim_yuzde")
                    para = fiyat_bilgi.get("para_birimi", "USD")
                    fiyat_blok = (
                        f"[GERÇEK ZAMANLI FİYAT VERİSİ — {varlik.upper()}]\n"
                        f"Anlık Fiyat: {fiyat:.4f} {para}\n"
                        f"Gün İçi Yüksek: {yuksek:.4f} {para}\n"
                        f"Gün İçi Düşük: {dusuk:.4f} {para}\n"
                        f"24s Değişim: {degisim:+.2f}%\n"
                        f"Kaynak: {'CoinGecko' if tip == 'kripto' else 'Yahoo Finance'}\n"
                        "NOT: Bu fiyat verileri gerçek zamanlıdır. Analizde bu fiyatları kullan, uydurma."
                    )
                    birlestik_baglam = fiyat_blok + "\n\n" + birlestik_baglam
        except Exception as _fe:
            import logging as _lg2
            _lg2.getLogger(__name__).warning("Okwis fiyat verisi eklenemedi: %s", _fe)

    profil_blogu = _profil_okwis_blogu(profil)

    # Portföy bloğunu da ekle (profil bloğundan öncelikli — daha yapılandırılmış)
    if user_id is not None:
        try:
            from portfoy import portfoy_analiz_blogu
            portfoy_blogu = portfoy_analiz_blogu(user_id)
            if portfoy_blogu:
                # Portföy varsa profil bloğunu portföy bloğuyla birleştir
                profil_blogu = portfoy_blogu + ("\n\n" + profil_blogu if profil_blogu else "")
        except Exception as _pe:
            import logging as _lg2
            _lg2.getLogger(__name__).warning("Portföy bloğu alınamadı: %s", _pe)

    profil_var = bool(profil_blogu)
    prob_notu = _ilgili_prob_zincirleri("sektor", ulke, varlik)

    # ── KISA ANALİZ ──────────────────────────────────────────────────────────
    if stil == "kisa":
        FORMAT_KURALI = (
            "FORMAT: Her bölümün başlığını <b>BAŞLIK</b> şeklinde yaz, altına 1-2 satır açıklama ekle. "
            "Bölümler arasında boş satır bırak. Toplam 10-14 satır. "
            "Telegram HTML kullan: kalın yazmak için <b>metin</b> formatını kullan, başka tag yasak."
        )
        if profil_var:
            varlik_ek = f'\nKullanıcı özellikle "{varlik}" üzerine odaklanmak istiyor.' if varlik and varlik.strip() else ""
            prompt = (
                f"{profil_blogu}\n\n---\n"
                + f"{birlestik_baglam}\n\n"
                + f"{_MOD_KIMLIK['okwis']}\n{_ORTAK_KURALLAR}\n\n"
                + f"Görev: {ulke} / {ay_adi} {yil} — OKWİS KİŞİSEL KISA ANALİZ{varlik_ek}\n\n"
                + "Portföydeki/profildeki varlıkları merkeze al. Kullanıcının elindeki parayı şu an nereye koyacağını söyle.\n\n"
                + "<b>POZİSYON</b>\n"
                + "Her varlık için tek satırda: varlık adı - AL/TUT/SAT - neden (hangi mod sinyali)\n\n"
                + "<b>FİYAT HEDEFİ</b>\n"
                + "Her varlık için: giriş seviyesi / hedef / stop-loss (somut rakam)\n\n"
                + "<b>ZAMANLAMA</b>\n"
                + "Kısa vade (1-2 hafta) ve orta vade (1-3 ay) için ayrı aksiyon\n\n"
                + "<b>YAPMA</b>\n"
                + "Şu an kesinlikle yapılmaması gereken tek şey - somut, neden\n\n"
                + f"{FORMAT_KURALI}\n"
                + "Kural: 'Senin X'in', 'elindeki Y' dili kullan. Soyut değil, somut fiyat/tarih ver. Türkçe yaz."
            )
        elif varlik and varlik.strip():
            prompt = (
                f"{birlestik_baglam}\n\n"
                + (f"{prob_notu}\n\n" if prob_notu else "")
                + f"{_MOD_KIMLIK['okwis']}\n{_ORTAK_KURALLAR}\n\n"
                + f"Görev: {ulke} / {ay_adi} {yil} — OKWİS VARLIK KISA ANALİZ: {varlik}\n\n"
                + f"8 modun verisini {varlik} için filtrele. Kullanıcıya şu an ne yapması gerektiğini söyle.\n\n"
                + "<b>POZİSYON</b>\n"
                + f"{varlik} için: AL / TUT / SAT - hangi modun verisi, neden şimdi\n\n"
                + "<b>FİYAT HEDEFİ</b>\n"
                + "Giriş seviyesi / hedef fiyat / stop-loss (somut rakam)\n\n"
                + "<b>ZAMANLAMA</b>\n"
                + "Kısa vade (1-2 hafta) / orta vade (1-3 ay) - hangi sinyal tetikleyici\n\n"
                + "<b>YAPMA</b>\n"
                + "Şu an kesinlikle yapılmaması gereken - somut, neden bu tezi bozar\n\n"
                + f"{FORMAT_KURALI}\n"
                + "Kural: Somut fiyat/seviye ver. Türkçe yaz."
            )
        else:
            prompt = (
                f"{birlestik_baglam}\n\n"
                + (f"{prob_notu}\n\n" if prob_notu else "")
                + f"{_MOD_KIMLIK['okwis']}\n{_ORTAK_KURALLAR}\n\n"
                + f"Görev: {ulke} / {ay_adi} {yil} — OKWİS GENEL KISA ANALİZ\n\n"
                + "8 modun verisini sentezle. Kullanıcının parasını şu an nereye koyacağını söyle.\n\n"
                + "<b>EN GÜÇLÜ FIRSAT</b>\n"
                + f"{ulke} piyasasında şu an en net sinyal veren 2-3 varlık/sektör - hangi modun verisi, neden şimdi\n\n"
                + "<b>POZİSYON ÖNERİLERİ</b>\n"
                + "Her varlık için: AL/TUT/SAT - giriş seviyesi / hedef / stop-loss\n\n"
                + "<b>ZAMANLAMA</b>\n"
                + "Kısa vade (1-2 hafta) / orta vade (1-3 ay) - hangi sinyal tetikleyici\n\n"
                + "<b>UZAK DUR</b>\n"
                + "Şu an kesinlikle girilmemesi gereken sektör/varlık - somut isim, neden\n\n"
                + f"{FORMAT_KURALI}\n"
                + "Kural: Gerçek isim ver. Somut fiyat/seviye ver. Türkçe yaz."
            )

    # ── DETAYLI ANALİZ ───────────────────────────────────────────────────────
    else:
        FORMAT_KURALI_DETAY = (
            "FORMAT: Her bölümün başlığını <b>BAŞLIK</b> şeklinde yaz, altına 2-3 satır açıklama ekle. "
            "Bölümler arasında boş satır bırak. Toplam 20-28 satır. "
            "Telegram HTML kullan: kalın yazmak için <b>metin</b> formatını kullan, başka tag yasak."
        )
        if profil_var:
            varlik_ek = f'\nKullanıcı özellikle "{varlik}" üzerine odaklanmak istiyor.' if varlik and varlik.strip() else ""
            prompt = (
                f"{profil_blogu}\n\n---\n"
                + f"{birlestik_baglam}\n\n"
                + (f"{prob_notu}\n\n" if prob_notu else "")
                + f"{_MOD_KIMLIK['okwis']}\n{_ORTAK_KURALLAR}\n\n"
                + f"Görev: {ulke} / {ay_adi} {yil} — OKWİS KİŞİSEL DETAYLI ANALİZ{varlik_ek}\n\n"
                + "Profildeki varlıkları ve 8 modun verisini kullanarak tam derinlikli analiz yap. "
                + "Kullanıcının elindeki parayı şu an nereye, ne kadar, ne zaman koyacağını söyle.\n\n"
                + "<b>PORTFÖY DURUMU</b>\n"
                + "Profildeki her varlık için: mevcut pozisyon sağlıklı mı, devam et mi çık mı - somut karar\n\n"
                + "<b>POZİSYON STRATEJİSİ</b>\n"
                + "Her varlık için: AL/TUT/AZALT/SAT - ne kadar süre tut, hangi seviyede ekle, hangi seviyede çık\n\n"
                + "<b>FİYAT HARİTASI</b>\n"
                + "Her varlık için 3 seviye: agresif giriş / konservatif giriş / stop-loss (somut rakam)\n\n"
                + "<b>ZAMANLAMA</b>\n"
                + "Kısa vade (1-2 hafta) / orta vade (1-3 ay) / uzun vade (3-12 ay) - her dönem için ayrı aksiyon\n\n"
                + "<b>YENİ FIRSAT</b>\n"
                + "Mevcut piyasa koşullarında profiline uygun yeni pozisyon var mı - somut varlık, neden şimdi, giriş seviyesi\n\n"
                + "<b>RİSK YÖNETİMİ</b>\n"
                + "Portföyü tehdit eden 2-3 risk ve her biri için hedge/koruma stratejisi\n\n"
                + "<b>YAPMA LİSTESİ</b>\n"
                + "Şu an kesinlikle yapılmaması gereken 2-3 şey - somut, neden\n\n"
                + f"{FORMAT_KURALI_DETAY}\n"
                + "Kural: 'Senin portföyün', 'elindeki X' dili kullan. Her başlık somut fiyat/tarih içermeli. Türkçe yaz."
            )
        elif varlik and varlik.strip():
            prompt = (
                f"{birlestik_baglam}\n\n"
                + (f"{prob_notu}\n\n" if prob_notu else "")
                + f"{_MOD_KIMLIK['okwis']}\n{_ORTAK_KURALLAR}\n\n"
                + f"Görev: {ulke} / {ay_adi} {yil} — OKWİS VARLIK DETAYLI ANALİZ: {varlik}\n\n"
                + f"8 modun tüm verisini {varlik} için derinlemesine analiz et. Kullanıcıya kesin karar ver.\n\n"
                + "<b>MEVCUT DURUM</b>\n"
                + f"{varlik} şu an hangi fiyat/seviyede, momentum ne yönde - hangi modun verisi bunu destekliyor\n\n"
                + "<b>POZİSYON KARARI</b>\n"
                + "AL / TUT / SAT - kesin karar, hangi koşulda pozisyon aç, hangi koşulda kapat\n\n"
                + "<b>FİYAT HARİTASI</b>\n"
                + "3 kritik seviye: güçlü destek / direnç / stop-loss - neden bu seviyeler\n\n"
                + "<b>ZAMANLAMA</b>\n"
                + "Kısa (1-2 hafta) / orta (1-3 ay) / uzun (3-12 ay) - her dönem için ayrı aksiyon\n\n"
                + "<b>KATALİZ</b>\n"
                + "Fiyatı tetikleyecek olay nedir - hangi haber/veri/tarih izlenmeli, ne zaman\n\n"
                + "<b>RİSK</b>\n"
                + "En büyük 2 risk ve her biri için koruma stratejisi\n\n"
                + "<b>YAPMA</b>\n"
                + "Şu an kesinlikle yapılmaması gereken - somut, neden bu tezi bozar\n\n"
                + f"{FORMAT_KURALI_DETAY}\n"
                + "Kural: Her başlık somut fiyat/tarih/seviye içermeli. Türkçe yaz."
            )
        else:
            prompt = (
                f"{birlestik_baglam}\n\n"
                + (f"{prob_notu}\n\n" if prob_notu else "")
                + f"{_MOD_KIMLIK['okwis']}\n{_ORTAK_KURALLAR}\n\n"
                + f"Görev: {ulke} / {ay_adi} {yil} — OKWİS GENEL DETAYLI ANALİZ\n\n"
                + "8 modun tüm verisini derinlemesine sentezle. Kullanıcının parasını nereye koyacağını söyle.\n\n"
                + "<b>MAKRO TABLO</b>\n"
                + "8 moddan çıkan en güçlü 3 sinyal - ne görüyorum, neden önemli, ne kadar süre güçlü kalır\n\n"
                + "<b>EN GÜÇLÜ POZİSYONLAR</b>\n"
                + f"{ulke} piyasasından 3 somut varlık - giriş seviyesi / hedef / stop-loss / neden şimdi\n\n"
                + "<b>YÜKSELEN SEKTÖRLER</b>\n"
                + "Momentum kazanan 2-3 sektör - hangi mod destekliyor, ne kadar sürer, somut şirket/ETF\n\n"
                + "<b>ZAMANLAMA</b>\n"
                + "Kısa (1-2 hafta) / orta (1-3 ay) / uzun (3-12 ay) - her dönem için ayrı aksiyon\n\n"
                + "<b>UZAK DUR</b>\n"
                + "Momentum kaybeden 1-2 sektör/varlık - somut isim, neden şimdi çıkış\n\n"
                + "<b>TERS SENARYO</b>\n"
                + "Tüm tezi çökertecek 1 gelişme - hangi modun verisi bu riski işaret ediyor, ne zaman izle\n\n"
                + f"{FORMAT_KURALI_DETAY}\n"
                + "Kural: Her başlık somut isim/fiyat/tarih içermeli. Gerçek isim ver. Türkçe yaz."
            )

    try:
        text = llm_metin_uret(prompt, user_id)
        if not text:
            return "Şu an model boş yanıt döndü. Biraz sonra tekrar dene."
        return text.strip()
    except Exception as e:
        logger.exception("LLM Okwis analizi: %s", e)
        return _llm_hata_kullanici_metni(e)

def _karsilama_mesaji_html() -> str:
    return (
        "◆ Merhaba. Ben <b>Okwis AI</b>.\n\n"
        "Mevsimler, hava olayları, jeopolitik gelişmeler gibi "
        "büyük resim faktörlerin piyasalara etkisini analiz ediyorum.\n\n"
        f"🆓 Ücretsiz planınla günde <b>{ANALIZ_GUNLUK_LIMIT} analiz hakkın</b> var.\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "Başlamak için <b>/analiz</b> yaz.\n"
        "Planını görmek için <b>/hesabim</b> yaz.\n"
        "Analiz sırasında çıkmak için <b>/cancel</b> veya <b>/start</b> kullanabilirsin."
    )


# ─── Portföy Komutları ────────────────────────────────────────────────────────

async def portfoy_komut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /portfoy — portföy yönetimi
    /portfoy ekle BTC 0.5
    /portfoy ekle BTC 0.5 45000   (maliyet fiyatıyla)
    /portfoy cikar BTC
    /portfoy sil
    /portfoy risk agresif|orta|muhafazakar
    /portfoy ufuk kisa|orta|uzun
    /portfoy grafik
    """
    from portfoy import (
        kullanici_portfoy_al, varlik_ekle, varlik_cikar, portfoy_sil,
        portfoy_ozet_metni, portfoy_grafigi_olustur, varlik_parse,
        risk_profili_guncelle, yatirim_ufku_guncelle,
    )

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        await update.message.reply_text("Kullanıcı bilgisi alınamadı.")
        return

    args = context.args or []

    # ── /portfoy (argümansız) → özet göster ──────────────────────────────────
    if not args:
        ozet = portfoy_ozet_metni(user_id)
        portfoy = kullanici_portfoy_al(user_id)
        klavye_satirlari = []
        if portfoy.get("varliklar"):
            klavye_satirlari.append([
                InlineKeyboardButton("◈ Grafik", callback_data="portfoy_grafik"),
                InlineKeyboardButton("🗑 Sil", callback_data="portfoy_sil_onayla"),
            ])
        klavye_satirlari.append([InlineKeyboardButton("✕ Kapat", callback_data="portfoy_kapat")])

        await update.message.reply_text(
            ozet + "\n\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            "<b>Komutlar:</b>\n"
            "<code>/portfoy ekle BTC 0.5</code>\n"
            "<code>/portfoy ekle ALTIN 10</code>\n"
            "<code>/portfoy cikar BTC</code>\n"
            "<code>/portfoy risk orta</code>\n"
            "<code>/portfoy ufuk uzun</code>\n"
            "<code>/portfoy grafik</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(klavye_satirlari),
        )
        return

    alt_komut = args[0].lower()

    # ── ekle ─────────────────────────────────────────────────────────────────
    if alt_komut == "ekle":
        if len(args) < 3:
            await update.message.reply_text(
                "Kullanım: <code>/portfoy ekle SEMBOL MİKTAR [MALİYET]</code>\n\n"
                "Örnekler:\n"
                "<code>/portfoy ekle BTC 0.5</code>\n"
                "<code>/portfoy ekle ALTIN 10</code>\n"
                "<code>/portfoy ekle ETH 2 3200</code>  (maliyet: 3200 USD)",
                parse_mode=ParseMode.HTML,
            )
            return
        try:
            sembol, miktar, maliyet = varlik_parse(" ".join(args[1:]))
        except ValueError as e:
            await update.message.reply_text(
                f"Hata: {e}\n\n"
                "Kullanım: <code>/portfoy ekle BTC 0.5</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        varlik_ekle(user_id, sembol, miktar, maliyet)
        maliyet_str = f" (maliyet: {maliyet} USD)" if maliyet else ""
        await update.message.reply_text(
            f"<b>◆ Portföye Eklendi</b>\n\n"
            f"<b>{sembol}</b>: {miktar}{maliyet_str}\n\n"
            f"<i>Artık Okwis analizi bu varlığı dikkate alacak. /analiz ile dene.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ── çıkar ────────────────────────────────────────────────────────────────
    if alt_komut in ("cikar", "çıkar", "kaldir", "kaldır"):
        if len(args) < 2:
            await update.message.reply_text(
                "Kullanım: <code>/portfoy cikar SEMBOL</code>\n"
                "Örnek: <code>/portfoy cikar BTC</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        sembol = args[1].upper()
        basarili, _ = varlik_cikar(user_id, sembol)
        if basarili:
            await update.message.reply_text(
                f"<b>◆ Portföyden Çıkarıldı</b>\n\n"
                f"<b>{sembol}</b> portföyünden silindi.",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text(
                f"<b>{sembol}</b> portföyünde bulunamadı.\n"
                f"Portföyünü görmek için: /portfoy",
                parse_mode=ParseMode.HTML,
            )
        return

    # ── sil (tüm portföy) ────────────────────────────────────────────────────
    if alt_komut == "sil":
        if portfoy_sil(user_id):
            await update.message.reply_text(
                "<b>◆ Portföy Silindi</b>\n\n"
                "<i>Tüm varlıklar ve profil bilgileri silindi. "
                "Yeniden eklemek için /portfoy ekle kullan.</i>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_text("Portföy zaten boş.")
        return

    # ── risk ─────────────────────────────────────────────────────────────────
    if alt_komut == "risk":
        if len(args) < 2:
            await update.message.reply_text(
                "Kullanım: <code>/portfoy risk agresif|orta|muhafazakar</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        risk_map = {
            "agresif": "agresif", "aggressive": "agresif",
            "orta": "orta", "medium": "orta", "moderate": "orta",
            "muhafazakar": "muhafazakar", "conservative": "muhafazakar",
        }
        risk = risk_map.get(args[1].lower())
        if not risk:
            await update.message.reply_text(
                "Geçerli değerler: <code>agresif</code>, <code>orta</code>, <code>muhafazakar</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        risk_profili_guncelle(user_id, risk)
        risk_adi = {"agresif": "Agresif", "orta": "Orta", "muhafazakar": "Muhafazakar"}[risk]
        await update.message.reply_text(
            f"<b>◆ Risk Profili Güncellendi</b>\n\n"
            f"Risk toleransın: <b>{risk_adi}</b>\n\n"
            f"<i>Okwis analizi bu profile göre önerileri ayarlayacak.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ── ufuk ─────────────────────────────────────────────────────────────────
    if alt_komut in ("ufuk", "vade"):
        if len(args) < 2:
            await update.message.reply_text(
                "Kullanım: <code>/portfoy ufuk kisa|orta|uzun</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        ufuk_map = {
            "kisa": "kisa_vade", "kısa": "kisa_vade", "short": "kisa_vade",
            "orta": "orta_vade", "medium": "orta_vade",
            "uzun": "uzun_vade", "long": "uzun_vade",
            "kisa_vade": "kisa_vade", "orta_vade": "orta_vade", "uzun_vade": "uzun_vade",
        }
        ufuk = ufuk_map.get(args[1].lower())
        if not ufuk:
            await update.message.reply_text(
                "Geçerli değerler: <code>kisa</code>, <code>orta</code>, <code>uzun</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        yatirim_ufku_guncelle(user_id, ufuk)
        ufuk_adi = {"kisa_vade": "Kısa Vade (0-3 ay)", "orta_vade": "Orta Vade (3-12 ay)", "uzun_vade": "Uzun Vade (1+ yıl)"}[ufuk]
        await update.message.reply_text(
            f"<b>◆ Yatırım Ufku Güncellendi</b>\n\n"
            f"Yatırım ufkun: <b>{ufuk_adi}</b>\n\n"
            f"<i>Okwis analizi bu vadeye göre önerileri ağırlıklandıracak.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    # ── grafik ───────────────────────────────────────────────────────────────
    if alt_komut == "grafik":
        portfoy = kullanici_portfoy_al(user_id)
        if not portfoy.get("varliklar"):
            await update.message.reply_text(
                "Portföyün boş. Önce varlık ekle:\n"
                "<code>/portfoy ekle BTC 0.5</code>",
                parse_mode=ParseMode.HTML,
            )
            return
        try:
            grafik = await asyncio.to_thread(portfoy_grafigi_olustur, user_id)
            if grafik:
                await update.message.reply_photo(
                    photo=grafik,
                    caption="<b>Portfoy Ozeti</b>",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await update.message.reply_text(
                    "Grafik oluşturulamadı (matplotlib yüklü değil).\n"
                    "Portföyünü görmek için: /portfoy"
                )
        except Exception as e:
            logger.warning("Portföy grafiği hatası: %s", e)
            await update.message.reply_text("Grafik oluşturulurken hata oluştu.")
        return

    # ── bilinmeyen alt komut ──────────────────────────────────────────────────
    await update.message.reply_text(
        "<b>◆ Portföy Komutları</b>\n\n"
        "<code>/portfoy</code> — portföyünü göster\n"
        "<code>/portfoy ekle BTC 0.5</code> — varlık ekle\n"
        "<code>/portfoy ekle ETH 2 3200</code> — maliyet fiyatıyla ekle\n"
        "<code>/portfoy cikar BTC</code> — varlık çıkar\n"
        "<code>/portfoy sil</code> — tüm portföyü sil\n"
        "<code>/portfoy risk orta</code> — risk profili (agresif/orta/muhafazakar)\n"
        "<code>/portfoy ufuk uzun</code> — yatırım ufku (kisa/orta/uzun)\n"
        "<code>/portfoy grafik</code> — portföy grafiği",
        parse_mode=ParseMode.HTML,
    )


async def portfoy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Portföy inline buton tıklamaları"""
    from portfoy import portfoy_sil, portfoy_grafigi_olustur

    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id if update.effective_user else None

    if query.data == "portfoy_kapat":
        await query.edit_message_text("◆ Portföy ekranı kapatıldı.")
        return

    if query.data == "portfoy_sil_onayla":
        klavye = [
            [
                InlineKeyboardButton("✓ Evet, sil", callback_data="portfoy_sil_onay"),
                InlineKeyboardButton("✕ Vazgeç", callback_data="portfoy_kapat"),
            ]
        ]
        await query.edit_message_text(
            "<b>Portföyü silmek istediğinden emin misin?</b>\n\n"
            "Tüm varlıklar ve profil bilgileri silinecek.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(klavye),
        )
        return

    if query.data == "portfoy_sil_onay":
        if user_id:
            portfoy_sil(user_id)
        await query.edit_message_text(
            "<b>◆ Portföy Silindi</b>\n\n"
            "<i>Yeniden eklemek için /portfoy ekle kullan.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if query.data == "portfoy_grafik":
        if user_id is None:
            await query.answer("Kullanıcı bilgisi alınamadı.")
            return
        try:
            grafik = await asyncio.to_thread(portfoy_grafigi_olustur, user_id)
            if grafik:
                await query.message.reply_photo(
                    photo=grafik,
                    caption="<b>Portfoy Ozeti</b>",
                    parse_mode=ParseMode.HTML,
                )
                await query.edit_message_reply_markup(reply_markup=None)
            else:
                await query.answer("Grafik oluşturulamadı (matplotlib yüklü değil).")
        except Exception as e:
            logger.warning("Portföy grafik callback hatası: %s", e)
            await query.answer("Grafik oluşturulurken hata oluştu.")
        return


# ─── Profil Komutları ─────────────────────────────────────────────────────────

async def profil_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/profil komutu — profil görüntüle veya güncelleme akışını başlat"""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        await update.message.reply_text("Kullanıcı bilgisi alınamadı.")
        return ConversationHandler.END

    mevcut = _kullanici_profili_al(user_id)

    if mevcut:
        klavye = [
            [
                InlineKeyboardButton("✏️ Güncelle", callback_data="profil_guncelle"),
                InlineKeyboardButton("🗑 Sil", callback_data="profil_sil"),
            ],
            [InlineKeyboardButton("✕ Kapat", callback_data="profil_kapat")],
        ]
        await update.message.reply_text(
            _kullanici_profili_html(mevcut) + "\n\n<i>Ne yapmak istersin?</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(klavye),
        )
        return PROFIL_METIN_BEKLENIYOR
    else:
        await update.message.reply_text(
            "<b>◆ Okwis Kişisel Profil</b>\n"
            "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            "Profilini tanımlarsan Okwis analizi tamamen sana özel yapar.\n\n"
            "<b>Ne yazabilirsin?</b>\n"
            "- Elindeki varlıklar ve miktarları (bitcoin, altın, hisse vb.)\n"
            "- Risk toleransın (agresif / dengeli / muhafazakar)\n"
            "- Yatırım ufkun (kısa / orta / uzun vade)\n"
            "- İlgi alanların (kripto, emtia, teknoloji hisseleri vb.)\n"
            "- Hedeflerin (birikim, pasif gelir, büyüme vb.)\n\n"
            "<b>Örnek:</b>\n"
            "<i>0.5 BTC, 2 ETH, 10 gram altın var. Risk toleransım orta. "
            "Kripto ve emtiaya odaklanıyorum. 1-2 yıl vadeli düşünüyorum. "
            "Hedefim portföyü 3x büyütmek.</i>\n\n"
            "Profilini şimdi yaz:",
            parse_mode=ParseMode.HTML,
        )
        context.user_data["profil_mod"] = "yeni"
        return PROFIL_METIN_BEKLENIYOR


async def profil_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profil menüsü buton tıklamaları"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id if update.effective_user else None

    if query.data == "profil_kapat":
        await query.edit_message_text("◆ Profil ekranı kapatıldı.")
        return ConversationHandler.END

    if query.data == "profil_sil":
        if user_id and _kullanici_profili_sil(user_id):
            await query.edit_message_text(
                "◆ Profilin silindi.\n\n"
                "<i>Okwis artık genel analiz yapacak. "
                "Yeniden tanımlamak için /profil yaz.</i>",
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text("Profil bulunamadı.")
        return ConversationHandler.END

    if query.data == "profil_guncelle":
        await query.edit_message_text(
            "<b>◆ Profili Güncelle</b>\n\n"
            "Yeni profilini yaz. Mevcut profil tamamen değiştirilecek.\n\n"
            "<b>Örnek:</b>\n"
            "<i>0.5 BTC, 2 ETH, 10 gram altın var. Risk toleransım orta. "
            "Kripto ve emtiaya odaklanıyorum. 1-2 yıl vadeli düşünüyorum.</i>",
            parse_mode=ParseMode.HTML,
        )
        context.user_data["profil_mod"] = "guncelle"
        return PROFIL_METIN_BEKLENIYOR

    return PROFIL_METIN_BEKLENIYOR


async def profil_metin_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı profil metnini yazdı — kaydet"""
    if not update.message:
        return PROFIL_METIN_BEKLENIYOR

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        await update.message.reply_text("Kullanıcı bilgisi alınamadı.")
        return ConversationHandler.END

    metin = update.message.text.strip()

    if len(metin) < 10:
        await update.message.reply_text(
            "Profil çok kısa. En az birkaç cümle yaz — varlıkların, risk toleransın, hedeflerin gibi."
        )
        return PROFIL_METIN_BEKLENIYOR

    if len(metin) > 2000:
        await update.message.reply_text(
            f"Profil çok uzun ({len(metin)} karakter). 2000 karaktere kadar yazabilirsin."
        )
        return PROFIL_METIN_BEKLENIYOR

    _kullanici_profili_kaydet(user_id, metin)
    mod = context.user_data.get("profil_mod", "yeni")
    eylem = "güncellendi" if mod == "guncelle" else "kaydedildi"

    await update.message.reply_text(
        f"<b>◆ Profil {eylem}!</b>\n\n"
        f"{_tg_html_escape(metin[:300])}{'...' if len(metin) > 300 else ''}\n\n"
        "<i>Artık Okwis analizi tamamen sana özel olacak. "
        "/analiz ile dene.</i>",
        parse_mode=ParseMode.HTML,
    )
    context.user_data.pop("profil_mod", None)
    return ConversationHandler.END


async def profil_iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profil akışını iptal et"""
    context.user_data.pop("profil_mod", None)
    await update.message.reply_text(
        "Profil işlemi iptal edildi. /profil ile tekrar başlayabilirsin."
    )
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start komutu — kullanıcıyı karşıla, oturum verisini temizle"""
    context.user_data.clear()
    klavye = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Abonelik Planları", callback_data="abonelik_goster")],
    ])
    await update.message.reply_text(
        _karsilama_mesaji_html(),
        parse_mode=ParseMode.HTML,
        reply_markup=klavye,
    )


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


async def analiz_iptal_buton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buton ile analiz iptali"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    await query.edit_message_text(
        "<b>✕ Analiz iptal edildi.</b>\n\n"
        "İstediğinde <b>/analiz</b> ile yeniden başlayabilirsin.",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def okwis_detay_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Okwis kısa analizden sonra 'Daha derin analiz' veya 'Yeter' butonu"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id if update.effective_user else None

    if query.data == "okwis_kapat":
        await query.edit_message_text("◆ Tamam. Yeni analiz için /analiz yaz.")
        return ConversationHandler.END

    # Daha derin analiz — kaydedilmiş bağlamları kullan, tekrar çekme
    baglamlar = context.user_data.get("okwis_baglamlar")
    profil = context.user_data.get("okwis_profil")
    ulke = context.user_data.get("ulke", "")
    varlik = context.user_data.get("varlik", "")

    if not baglamlar or not ulke:
        await query.edit_message_text(
            "Oturum sıfırlandı. Yeniden başlamak için /analiz yaz."
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"◆ <b>{_tg_html_escape(ulke)}</b> · <i>Okwis Derin Analiz</i>\n\n"
        "🔬 Derinlemesine analiz yapılıyor…",
        parse_mode=ParseMode.HTML,
    )

    try:
        analiz = await asyncio.to_thread(okwis_analizi_yap, ulke, baglamlar, varlik, profil, "detay", user_id)
    except Exception as e:
        logger.exception("Okwis detay analizi hatası: %s", e)
        await query.edit_message_text("Detay analizi üretilirken bir hata oluştu. /analiz ile tekrar dene.")
        return ConversationHandler.END

    alt_cizgi = "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    varlik_satir = f" · <i>{_tg_html_escape(varlik)}</i>" if varlik else ""
    # Portföy veya profil aktif mi?
    _portfoy_aktif = False
    try:
        from portfoy import kullanici_portfoy_al as _pf_al
        _portfoy_aktif = bool(_pf_al(user_id).get("varliklar")) if user_id else False
    except Exception:
        pass
    if _portfoy_aktif:
        profil_satir = " · <i>Portföy Aktif</i>"
    elif profil:
        profil_satir = " · <i>Kişisel Profil Aktif</i>"
    else:
        profil_satir = ""

    birlestik_baglam_kart = " ".join(v for v in baglamlar.values() if v)
    guven_olayi_detay = _guven_skoru_hesapla("okwis", birlestik_baglam_kart)
    detay_guven_karti = _guven_karti_html("okwis", birlestik_baglam_kart, guven_olayi_detay, user_id)
    context.user_data["son_guven_karti"] = detay_guven_karti
    context.user_data["son_analiz_mod"] = "okwis_detay"

    mesaj = (
        f"<b>◆ Okwis — Tanrının Gözü</b> · <i>Derin Analiz</i>\n"
        f"{alt_cizgi}\n"
        f"▸ <b>{_tg_html_escape(ulke)}</b>{varlik_satir}{profil_satir}\n"
        f"{alt_cizgi}\n\n"
        f"{_analiz_html_temizle(analiz)}\n\n"
        f"{ANALIZ_FOOTER_HTML}"
    )
    
    # Kalite kartı butonu ekle
    keyboard = [[InlineKeyboardButton("📊 Kalite Kartını Göster", callback_data="show_quality_card")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await gonder_parcali_html(query, context, mesaj, reply_markup=reply_markup)
    return ConversationHandler.END


def _abonelik_mesaji_html() -> str:
    """Abonelik planları mesajı — şık kart formatı"""
    return (
        "◆ <b>Okwis Abonelik Planları</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"

        "⚡ <b>PREMIUM</b>  ·  <b>$60 / ay</b>\n"
        "◈ Sınırsız analiz\n"
        "◈ Tüm 8 mod + Okwis — Tanrının Gözü\n"
        "◈ Portföy takibi ve kişisel profil\n"
        "◈ Alarm bildirimleri\n\n"

        "🔥 <b>TAM GÜÇ</b>  ·  <b>$80 / ay</b>\n"
        "◈ Premium'un tüm özellikleri\n"
        "◈ Claude AI motoru (en güçlü analiz)\n"
        "◈ Öncelikli destek\n"
        "◈ PDF rapor çıktısı\n\n"

        "🔥 <b>TAM GÜÇ — 2 AYLIK</b>  ·  <b>$100</b>\n"
        "◈ Tam Güç'ün tüm özellikleri\n"
        "◈ 2 ay kesintisiz erişim\n"
        "◈ <i>Aylığa vurursak $50 — $30 tasarruf</i>\n\n"

        "👑 <b>TAM GÜÇ — YILLIK</b>  ·  <b>$399 / yıl</b>\n"
        "◈ Tam Güç'ün tüm özellikleri\n"
        "◈ 12 ay kesintisiz erişim\n"
        "◈ <i>Aylığa vurursak $33 — en avantajlı plan</i>\n"
        "◈ Yeni özellikler öncelikli erişim\n\n"

        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "📩 <b>Abone olmak için doğrudan yaz:</b>\n"
        "👉 @mehmethaneceye\n\n"
        "👥 <b>Topluluğumuza katıl:</b>\n"
        "👉 <a href=\"https://t.me/+ztlxRCC7UspmZTY0\">t.me/okwis topluluğu</a>\n\n"
        "<i>Ödeme sonrası planın aynı gün aktif edilir.</i>"
    )


async def abonelik_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abonelik planlarını göster — buton veya /abonelik komutu"""
    klavye = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Abone ol → @mehmethaneceye", url="https://t.me/mehmethaneceye")],
        [InlineKeyboardButton("👥 Topluluğa katıl", url="https://t.me/+ztlxRCC7UspmZTY0")],
    ])

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(
            _abonelik_mesaji_html(),
            parse_mode=ParseMode.HTML,
            reply_markup=klavye,
            disable_web_page_preview=True,
        )
    else:
        await update.message.reply_text(
            _abonelik_mesaji_html(),
            parse_mode=ParseMode.HTML,
            reply_markup=klavye,
            disable_web_page_preview=True,
        )


async def kalite_karti_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kalite kartını göster butonu"""
    query = update.callback_query
    await query.answer()
    
    guven_karti = context.user_data.get("son_guven_karti", "")
    analiz_mod = context.user_data.get("son_analiz_mod", "analiz")
    
    if not guven_karti:
        await query.answer("Kalite kartı bulunamadı. Yeni bir analiz yapın.", show_alert=True)
        return
    
    # Kalite kartını mesaj olarak gönder
    await query.message.reply_text(
        guven_karti,
        parse_mode=ParseMode.HTML,
    )
    await query.answer("✅ Kalite kartı gösterildi")


async def okwis_gorseller_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Okwis analizi için görselleri (güven skoru + olasılık zincirleri) gönder"""
    query = update.callback_query
    await query.answer("📈 Görseller hazırlanıyor…")
    
    user_id = update.effective_user.id if update.effective_user else None
    
    # Kaydedilmiş verileri al
    guven_olayi_kart = context.user_data.get("okwis_guven_kart_veri")
    ulke = context.user_data.get("okwis_gorsel_ulke", "")
    varlik = context.user_data.get("okwis_gorsel_varlik", "")
    
    if not guven_olayi_kart or not ulke:
        await query.answer("Görsel verisi bulunamadı. Yeni bir analiz yapın.", show_alert=True)
        return
    
    # Güven skoru grafiği gönder
    try:
        gorsel = gorsel_olusturucu_al()
        guven_grafik = await asyncio.to_thread(
            gorsel.guven_skoru_grafigi,
            guven_olayi_kart.get("toplam", 0),
            guven_olayi_kart.get("vkg", 0),
            guven_olayi_kart.get("mbs", 0),
            ulke,
            "Okwis"
        )
        if guven_grafik:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=guven_grafik,
                caption="<b>Analiz Kalite Metrikleri</b>\nGüven skoru, veri kalitesi ve mod başarısı değerlendirmesi",
                parse_mode=ParseMode.HTML,
            )
            logger.info("Güven skoru grafiği gönderildi (user=%s)", user_id)
    except Exception as e:
        logger.warning("Güven grafiği gönderilemedi: %s", e)
    
    # Olasılık zincirleri infografiği (eğer varsa)
    try:
        zincirler = _prob_zinciri_yukle()
        aktif_zincirler = []
        for z in zincirler[:5]:  # İlk 5 zincir
            # Zincirin ortalama olasılığını hesapla
            adimlar = z.get("zincir", [])
            if adimlar:
                ort_olasilik = sum(a.get("olasilik", 0) for a in adimlar) / len(adimlar)
                aktif_zincirler.append({
                    "baslik": z.get("baslik", ""),
                    "olasilik": ort_olasilik,
                    "kategori": z.get("ilgili_modlar", ["genel"])[0] if z.get("ilgili_modlar") else "genel"
                })
        
        if aktif_zincirler:
            prob_infografik = await asyncio.to_thread(
                gorsel.prob_zinciri_infografik,
                aktif_zincirler,
                ulke,
                varlik
            )
            if prob_infografik:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=prob_infografik,
                    caption="<b>Aktif Olasılık Zincirleri</b>\nAnaliz edilen sosyal ihtimal senaryoları",
                    parse_mode=ParseMode.HTML,
                )
                logger.info("Prob zinciri infografiği gönderildi (user=%s)", user_id)
    except Exception as e:
        logger.warning("Prob zinciri infografiği gönderilemedi: %s", e)
    
    await query.answer("✅ Görseller gönderildi", show_alert=False)


async def okwis_pdf_olustur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Okwis analizi için PDF rapor oluştur ve gönder (Pro özelliği)"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id if update.effective_user else None
    
    # Pro kontrolü
    if not user_id or not _kullanici_pro_mu(user_id):
        await query.answer("PDF rapor özelliği Pro/Claude plana özeldir.", show_alert=True)
        return
    
    # Kaydedilmiş analiz verilerini al
    baglamlar = context.user_data.get("okwis_baglamlar")
    ulke = context.user_data.get("ulke", "")
    varlik = context.user_data.get("varlik", "")
    profil = context.user_data.get("okwis_profil")
    
    if not baglamlar or not ulke:
        await query.answer("Analiz verisi bulunamadı. Yeni bir analiz yapın.", show_alert=True)
        return
    
    await query.edit_message_text(
        "📄 PDF rapor oluşturuluyor…",
        parse_mode=ParseMode.HTML,
    )
    
    try:
        # Detaylı analiz üret (eğer yoksa)
        analiz = await asyncio.to_thread(okwis_analizi_yap, ulke, baglamlar, varlik, profil, "detay", user_id)
        
        # Güven skorunu hesapla
        birlestik_baglam = " ".join(v for v in baglamlar.values() if v)
        guven_olayi = _guven_skoru_hesapla("okwis", birlestik_baglam)
        guven_skoru = guven_olayi.get("toplam", 0)
        
        # PDF oluştur
        gorsel = gorsel_olusturucu_al()
        pdf_buffer = await asyncio.to_thread(
            gorsel.pdf_rapor_olustur,
            analiz,
            ulke,
            "Okwis",
            varlik,
            guven_skoru,
            datetime.now()
        )
        
        if not pdf_buffer:
            await query.edit_message_text(
                "❌ PDF oluşturulamadı. reportlab kütüphanesi yüklü değil.",
                parse_mode=ParseMode.HTML,
            )
            return
        
        # PDF'i gönder
        dosya_adi = f"okwis_analiz_{ulke.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_buffer,
            filename=dosya_adi,
            caption=f"<b>Okwis Analiz Raporu</b>\n{ulke}{' · ' + varlik if varlik else ''}\n\n<i>Profesyonel PDF rapor</i>",
            parse_mode=ParseMode.HTML,
        )
        
        await query.edit_message_text(
            "✅ PDF rapor gönderildi!",
            parse_mode=ParseMode.HTML,
        )
        
        logger.info("PDF rapor gönderildi (user=%s, ulke=%s)", user_id, ulke)
        
    except Exception as e:
        logger.exception("PDF oluşturma hatası: %s", e)
        await query.edit_message_text(
            f"❌ PDF oluşturulurken hata: {_tg_html_escape(str(e))}",
            parse_mode=ParseMode.HTML,
        )



async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/yardim komutu"""
    mesaj = (
        "<b>📖 Nasıl kullanılır?</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>/analiz</b> — Yeni bir analiz başlat\n"
        "  🔒 <b>Okwis</b> — Tüm modları paralel tarar, ultra sade sonuç verir <i>(Premium)</i>\n"
        "  ◈ <b>Tüm Modlar</b> — 8 moddan istediğini seç (Mevsim, Hava, Jeopolitik, Sektör, Trendler, Magazin, Özel Günler, Doğal Afet)\n\n"
        "<b>◆ Portföy Sistemi</b>\n"
        "<b>/portfoy</b> — Portföyünü görüntüle\n"
        "<code>/portfoy ekle BTC 0.5</code> — Varlık ekle\n"
        "<code>/portfoy ekle ETH 2 3200</code> — Maliyet fiyatıyla ekle\n"
        "<code>/portfoy cikar BTC</code> — Varlık çıkar\n"
        "<code>/portfoy risk orta</code> — Risk profili (agresif/orta/muhafazakar)\n"
        "<code>/portfoy ufuk uzun</code> — Yatırım ufku (kisa/orta/uzun)\n"
        "<code>/portfoy grafik</code> — Portföy dağılım grafiği\n"
        "  Portföy tanımlarsan Okwis analizi tamamen sana özel olur.\n\n"
        "<b>◆ Profil ve Hesap</b>\n"
        "<b>/profil</b> — Serbest metin profil tanımla (portföye ek)\n"
        "<b>/hesabim</b> — Plan, kalan Pro gün ve kullanım durumu\n"
        "<b>/bildirim</b> — Alarm ayarları (aç/kapat, seviye, portföy filtresi)\n"
        "  <code>/bildirim seviye kritik</code> — sadece kritik alarmlar\n"
        "  <code>/bildirim portfoy kapat</code> — tüm alarmları al\n\n"
        "<b>◆ Analiz Geçmişi</b>\n"
        "<b>/performans</b> — Canlı güven skoru özeti + tahmin istatistikleri\n"
        "<b>/gecmis</b> — Son tahmin geçmişi (/gecmis 20 ile daha fazla gör)\n"
        "<b>/backtest</b> — Geçmiş tahminlerin performans raporu (/backtest 30 ile daha fazla)\n\n"
        "<b>◆ Diğer</b>\n"
        "<b>/start</b> — Karşılama; analiz akışındaysan akışı kapatır\n"
        "<b>/cancel</b> — Analiz akışını iptal eder\n"
        "<b>/skip</b> — Varlık sorusunu geç, genel analiz yap\n\n"
        f"Ücretsiz kullanım limiti: günde <b>{ANALIZ_GUNLUK_LIMIT}</b> analiz.\n"
        "Ülke seçtikten sonra varlık odağı yazabilir (altın, petrol, bitcoin vb.) veya <b>BOŞ</b> / <b>/skip</b> ile geçebilirsin.\n"
        "<b>Hava</b> modu için <code>OPENWEATHER_API_KEY</code> (.env) gerekir.\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
        "<b>📦 Abonelik Planları</b>\n"
        f"🆓 <b>Ücretsiz</b> — Günde {ANALIZ_GUNLUK_LIMIT} analiz hakkı\n"
        "⚡ <b>Premium</b> — <b>$60/ay</b> · Sınırsız analiz + tüm modlar\n"
        "🔥 <b>Tam Güç</b> — <b>$80/ay</b> · Sınırsız analiz + Claude AI + öncelikli destek\n\n"
        "📩 Abone olmak için: @mehmethaneceye\n"
        "👥 Topluluk: <a href=\"https://t.me/+ztlxRCC7UspmZTY0\">t.me/okwis</a>\n\n"
        f"<i>Bilgilendirme amaçlıdır; yatırım tavsiyesi değildir.</i>\n"
        "<i>Yatırım kararı için kendi araştırmanı yap.</i>"
    )
    await update.message.reply_text(mesaj, parse_mode=ParseMode.HTML)


async def fiyat_komut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/fiyat <varlık> — gerçek zamanlı fiyat + grafik"""
    if not context.args:
        await update.message.reply_text(
            "Kullanım: <code>/fiyat bitcoin</code> veya <code>/fiyat THYAO</code> veya <code>/fiyat altın</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    sorgu = " ".join(context.args).strip()
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        from fiyat_servisi import fiyat_sorgula, sembol_tespit
        # Direkt sembol sorgula (fiyat sorusu filtresi olmadan)
        tespit = sembol_tespit(sorgu)
        if not tespit:
            await update.message.reply_text(
                f"◆ <b>{sorgu}</b> için veri bulunamadı.\n\n"
                "Desteklenen varlıklar: BTC, ETH, altın, dolar, THYAO, AAPL vb.\n"
                "Örnek: <code>/fiyat bitcoin</code>",
                parse_mode=ParseMode.HTML,
            )
            return

        sonuc = await asyncio.to_thread(fiyat_sorgula, sorgu)
        if sonuc:
            if sonuc.get("grafik"):
                await update.message.reply_photo(
                    photo=io.BytesIO(sonuc["grafik"]),
                    caption=sonuc["mesaj"],
                    parse_mode=ParseMode.HTML,
                )
            else:
                await update.message.reply_text(
                    sonuc["mesaj"], parse_mode=ParseMode.HTML
                )
        else:
            await update.message.reply_text(
                f"◆ {sorgu} için şu an veri çekilemedi. Biraz sonra tekrar dene."
            )
    except Exception as e:
        logger.warning("Fiyat komutu hatası: %s", e)
        await update.message.reply_text(
            "Fiyat verisi alınırken hata oluştu. Biraz sonra tekrar dene."
        )


async def performans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/performans — canlı güven skoru özet paneli + tahmin istatistiği"""
    guven_metni = _performans_ozeti_hesapla()
    istat = _tahmin_istatistik()
    if istat["toplam"] > 0:
        istat_satir = (
            f"\n\n<b>◆ Tahmin İstatistikleri</b>\n"
            f"Toplam: <b>{istat['toplam']}</b> · Doğrulanan: <b>{istat['dogrulanan']}</b>"
        )
        if istat["oran"] is not None:
            istat_satir += f" · Doğruluk: <b>{istat['oran']:.0f}%</b>"
        istat_satir += "\n<i>/gecmis ile detayları gör.</i>"
        metin = guven_metni + istat_satir
    else:
        metin = guven_metni
    await update.message.reply_text(metin, parse_mode=ParseMode.HTML)


async def gecmis_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gecmis_sil — sohbet geçmişini temizle"""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id:
        from sohbet import gecmis_temizle
        gecmis_temizle(user_id)
    await update.message.reply_text("◆ Sohbet geçmişi temizlendi. Yeni konuşma başlayabilirsin.")


async def gecmis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gecmis [n] — son tahmin geçmişi"""
    n = 10
    if context.args:
        try:
            n = max(1, min(int(context.args[0]), 30))
        except ValueError:
            n = 10
    metin = _gecmis_tahminler_html(n)
    await update.message.reply_text(metin, parse_mode=ParseMode.HTML)


async def backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/backtest [n] — backtest raporu (geçmiş tahminlerin performansı)"""
    from backtest import backtest_raporu_html, performans_grafigi_olustur, detayli_analiz_grafigi_olustur
    
    n = 20
    if context.args:
        try:
            n = max(5, min(int(context.args[0]), 50))
        except ValueError:
            n = 20
    
    # Metin raporu
    rapor = backtest_raporu_html(n)
    await update.message.reply_text(rapor, parse_mode=ParseMode.HTML)
    
    # Performans grafiği (mod karşılaştırma)
    try:
        grafik = await asyncio.to_thread(performans_grafigi_olustur)
        if grafik:
            await update.message.reply_photo(
                photo=grafik,
                caption="<b>Mod Bazli Performans Karsilastirmasi</b>",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        logger.warning("Performans grafiği oluşturulamadı: %s", e)
    
    # Detaylı analiz grafiği
    try:
        detay_grafik = await asyncio.to_thread(detayli_analiz_grafigi_olustur)
        if detay_grafik:
            await update.message.reply_photo(
                photo=detay_grafik,
                caption="<b>Detayli Analiz</b>\nVarlik, ulke ve sure bazli performans",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        logger.warning("Detaylı analiz grafiği oluşturulamadı: %s", e)


async def bildirim_ayar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bildirim — alarm bildirim ayarları (sadece Pro/Claude)"""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        await update.message.reply_text("Kullanıcı bilgisi alınamadı.")
        return

    # Sadece Pro/Claude
    if not _kullanici_pro_mu(user_id):
        await update.message.reply_text(
            "◆ Alarm bildirimleri <b>Pro</b> veya <b>Claude</b> plan gerektiriyor.\n\n"
            "<i>/hesabim ile planını görüntüle.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    from alarm_sistemi import (
        kullanici_bildirim_acik_mi, kullanici_bildirim_ayarla,
        kullanici_min_seviye_al, kullanici_min_seviye_ayarla,
        kullanici_portfoy_filtre_al, kullanici_portfoy_filtre_ayarla,
        kullanici_gunluk_alarm_sayisi, GUNLUK_MAX_ALARM,
        ACILIYET_KRITIK, ACILIYET_ONEMLI, ACILIYET_BILGI,
    )

    args = context.args or []

    # ── Alt komutlar ──────────────────────────────────────────────────────────
    if args:
        alt = args[0].lower()

        # /bildirim kapat / ac
        if alt in ("kapat", "kapa"):
            kullanici_bildirim_ayarla(user_id, False)
            await update.message.reply_text(
                "🔕 <b>Alarm bildirimleri kapatıldı.</b>\n\n"
                "<i>Tekrar açmak için /bildirim ac yaz.</i>",
                parse_mode=ParseMode.HTML,
            )
            return

        if alt in ("ac", "aç", "open"):
            kullanici_bildirim_ayarla(user_id, True)
            await update.message.reply_text(
                "🔔 <b>Alarm bildirimleri açıldı.</b>\n\n"
                "<i>Kapatmak için /bildirim kapat yaz.</i>",
                parse_mode=ParseMode.HTML,
            )
            return

        # /bildirim seviye kritik|onemli|bilgi
        if alt in ("seviye", "level"):
            if len(args) < 2:
                await update.message.reply_text(
                    "Kullanım: <code>/bildirim seviye kritik|onemli|bilgi</code>\n\n"
                    "🔴 <b>kritik</b> — sadece 8-10 skorlu alarmlar\n"
                    "🟡 <b>onemli</b> — 6+ skorlu alarmlar\n"
                    "🟢 <b>bilgi</b> — tüm alarmlar (5+)",
                    parse_mode=ParseMode.HTML,
                )
                return
            seviye_map = {
                "kritik": ACILIYET_KRITIK,
                "onemli": ACILIYET_ONEMLI,
                "önemli": ACILIYET_ONEMLI,
                "bilgi": ACILIYET_BILGI,
            }
            seviye = seviye_map.get(args[1].lower())
            if seviye is None:
                await update.message.reply_text(
                    "Geçerli değerler: <code>kritik</code>, <code>onemli</code>, <code>bilgi</code>",
                    parse_mode=ParseMode.HTML,
                )
                return
            kullanici_min_seviye_ayarla(user_id, seviye)
            seviye_adi = {"kritik": "Kritik (8+)", "onemli": "Önemli (6+)", "bilgi": "Bilgi (5+)"}.get(args[1].lower(), args[1])
            await update.message.reply_text(
                f"🔔 <b>Alarm seviyesi güncellendi: {_tg_html_escape(seviye_adi)}</b>\n\n"
                "<i>Artık sadece bu seviyedeki alarmlar gelecek.</i>",
                parse_mode=ParseMode.HTML,
            )
            return

        # /bildirim portfoy ac|kapat
        if alt in ("portfoy", "portföy", "filtre"):
            if len(args) < 2:
                durum = "açık" if kullanici_portfoy_filtre_al(user_id) else "kapalı"
                await update.message.reply_text(
                    f"Portföy filtresi şu an: <b>{durum}</b>\n\n"
                    "Açıkken sadece portföyünle ilgili alarmlar gelir.\n"
                    "Kapalıyken tüm alarmlar gelir.\n\n"
                    "<code>/bildirim portfoy ac</code> — filtre aç\n"
                    "<code>/bildirim portfoy kapat</code> — filtre kapat",
                    parse_mode=ParseMode.HTML,
                )
                return
            durum_arg = args[1].lower()
            if durum_arg in ("ac", "aç", "open", "on"):
                kullanici_portfoy_filtre_ayarla(user_id, True)
                await update.message.reply_text(
                    "◈ <b>Portföy filtresi açıldı.</b>\n\n"
                    "<i>Artık sadece portföyünle ilgili alarmlar gelecek.</i>",
                    parse_mode=ParseMode.HTML,
                )
            elif durum_arg in ("kapat", "kapa", "off"):
                kullanici_portfoy_filtre_ayarla(user_id, False)
                await update.message.reply_text(
                    "◈ <b>Portföy filtresi kapatıldı.</b>\n\n"
                    "<i>Artık tüm alarmlar gelecek.</i>",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await update.message.reply_text(
                    "Geçerli değerler: <code>ac</code> veya <code>kapat</code>",
                    parse_mode=ParseMode.HTML,
                )
            return

    # ── Durum göster (argümansız) ─────────────────────────────────────────────
    acik = kullanici_bildirim_acik_mi(user_id)
    min_seviye = kullanici_min_seviye_al(user_id)
    portfoy_filtre = kullanici_portfoy_filtre_al(user_id)
    bugun_sayisi = kullanici_gunluk_alarm_sayisi(user_id)

    seviye_adi = {
        ACILIYET_KRITIK: "🔴 Kritik (8+)",
        ACILIYET_ONEMLI: "🟡 Önemli (6+)",
        ACILIYET_BILGI: "🟢 Bilgi (5+)",
    }.get(min_seviye, f"Özel ({min_seviye}+)")

    durum_ikon = "🔔" if acik else "🔕"
    durum_metin = "Açık" if acik else "Kapalı"
    portfoy_metin = "Açık (sadece portföyle ilgili)" if portfoy_filtre else "Kapalı (tüm alarmlar)"

    # Toggle butonu
    toggle_label = "🔕 Kapat" if acik else "🔔 Aç"
    toggle_data = "bildirim_kapat" if acik else "bildirim_ac"

    klavye = [
        [
            InlineKeyboardButton(toggle_label, callback_data=toggle_data),
        ],
        [
            InlineKeyboardButton("🔴 Sadece Kritik", callback_data="bildirim_seviye_kritik"),
            InlineKeyboardButton("🟡 Önemli+", callback_data="bildirim_seviye_onemli"),
            InlineKeyboardButton("🟢 Hepsi", callback_data="bildirim_seviye_bilgi"),
        ],
        [
            InlineKeyboardButton(
                "◈ Portföy Filtresi: " + ("Açık" if portfoy_filtre else "Kapalı"),
                callback_data="bildirim_portfoy_toggle",
            ),
        ],
        [InlineKeyboardButton("✕ Kapat", callback_data="bildirim_kapat_menu")],
    ]

    mesaj = (
        f"<b>◆ Alarm Bildirimleri</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"Durum: {durum_ikon} <b>{durum_metin}</b>\n"
        f"Min. Seviye: <b>{seviye_adi}</b>\n"
        f"Portföy Filtresi: <b>{portfoy_metin}</b>\n"
        f"Bugün gönderilen: <b>{bugun_sayisi}/{GUNLUK_MAX_ALARM}</b>\n\n"
        f"<b>Seviyeler:</b>\n"
        f"🔴 Kritik (8-10) — Savaş, borsa çöküşü, acil faiz kararı\n"
        f"🟡 Önemli (6-7) — Jeopolitik gerilim, önemli ekonomik veri\n"
        f"🟢 Bilgi (5) — Dikkat çekici piyasa hareketi\n\n"
        f"<i>Günde max {GUNLUK_MAX_ALARM} alarm gönderilir.</i>"
    )

    await update.message.reply_text(
        mesaj,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(klavye),
    )


async def bildirim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bildirim ayarları inline buton tıklamaları"""
    from alarm_sistemi import (
        kullanici_bildirim_ayarla, kullanici_min_seviye_ayarla,
        kullanici_portfoy_filtre_al, kullanici_portfoy_filtre_ayarla,
        ACILIYET_KRITIK, ACILIYET_ONEMLI, ACILIYET_BILGI,
    )

    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id if update.effective_user else None

    if query.data == "bildirim_kapat_menu":
        await query.edit_message_text("◆ Bildirim ayarları kapatıldı.")
        return

    if query.data == "bildirim_ac":
        if user_id:
            kullanici_bildirim_ayarla(user_id, True)
        await query.answer("🔔 Bildirimler açıldı", show_alert=False)
        await query.edit_message_text(
            "🔔 <b>Alarm bildirimleri açıldı.</b>\n\n"
            "<i>Ayarlar için tekrar /bildirim yaz.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if query.data == "bildirim_kapat":
        if user_id:
            kullanici_bildirim_ayarla(user_id, False)
        await query.answer("🔕 Bildirimler kapatıldı", show_alert=False)
        await query.edit_message_text(
            "🔕 <b>Alarm bildirimleri kapatıldı.</b>\n\n"
            "<i>Tekrar açmak için /bildirim yaz.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if query.data == "bildirim_seviye_kritik":
        if user_id:
            kullanici_min_seviye_ayarla(user_id, ACILIYET_KRITIK)
        await query.answer("🔴 Sadece kritik alarmlar", show_alert=False)
        await query.edit_message_text(
            "🔴 <b>Alarm seviyesi: Kritik (8+)</b>\n\n"
            "Artık sadece savaş, borsa çöküşü, acil faiz kararı gibi kritik gelişmelerde alarm alacaksın.\n\n"
            "<i>Değiştirmek için /bildirim yaz.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if query.data == "bildirim_seviye_onemli":
        if user_id:
            kullanici_min_seviye_ayarla(user_id, ACILIYET_ONEMLI)
        await query.answer("🟡 Önemli+ alarmlar", show_alert=False)
        await query.edit_message_text(
            "🟡 <b>Alarm seviyesi: Önemli (6+)</b>\n\n"
            "Jeopolitik gerilim, önemli ekonomik veri sürprizi gibi gelişmelerde alarm alacaksın.\n\n"
            "<i>Değiştirmek için /bildirim yaz.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if query.data == "bildirim_seviye_bilgi":
        if user_id:
            kullanici_min_seviye_ayarla(user_id, ACILIYET_BILGI)
        await query.answer("🟢 Tüm alarmlar", show_alert=False)
        await query.edit_message_text(
            "🟢 <b>Alarm seviyesi: Bilgi (5+)</b>\n\n"
            "Tüm dikkat çekici gelişmelerde alarm alacaksın.\n\n"
            "<i>Değiştirmek için /bildirim yaz.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    if query.data == "bildirim_portfoy_toggle":
        if user_id:
            mevcut = kullanici_portfoy_filtre_al(user_id)
            kullanici_portfoy_filtre_ayarla(user_id, not mevcut)
            yeni = not mevcut
            durum = "açıldı" if yeni else "kapatıldı"
            aciklama = "Artık sadece portföyünle ilgili alarmlar gelecek." if yeni else "Artık tüm alarmlar gelecek."
            await query.answer(f"Portföy filtresi {durum}", show_alert=False)
            await query.edit_message_text(
                f"◈ <b>Portföy filtresi {durum}.</b>\n\n"
                f"<i>{aciklama}</i>\n\n"
                "<i>Diğer ayarlar için /bildirim yaz.</i>",
                parse_mode=ParseMode.HTML,
            )
        return


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

    aktif_plan = plan.get("plan", "free")
    if aktif_plan == "claude":
        plan_satiri = "🔥 Tam Güç (Claude) ◆◆"
        pro_satiri = (
            f"Bitiş: <b>{_tg_html_escape(pro_until)}</b> · kalan <b>{kalan}</b> gün"
            if pro_until else "Aktif"
        )
        yukseltme_satiri = ""
    elif pro_mu:
        plan_satiri = "⚡ Premium ◆"
        pro_satiri = (
            f"Bitiş: <b>{_tg_html_escape(pro_until)}</b> · kalan <b>{kalan}</b> gün"
            if pro_until else "Aktif"
        )
        yukseltme_satiri = (
            "\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            "🔥 <b>Tam Güç'e yükselt:</b> $80/ay · Claude AI + öncelikli destek\n"
            "📩 Yükseltmek için: @mehmethaneceye · Planlar: /abonelik"
        )
    else:
        plan_satiri = "🆓 Ücretsiz"
        pro_satiri = f"Kalan günlük hak: <b>{max(0, ANALIZ_GUNLUK_LIMIT - gunluk)}/{ANALIZ_GUNLUK_LIMIT}</b>"
        yukseltme_satiri = (
            "\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n"
            "⚡ <b>Premium</b> — $60/ay · Sınırsız analiz + tüm modlar\n"
            "🔥 <b>Tam Güç</b> — $80/ay · Sınırsız analiz + Claude AI\n\n"
            "📩 Abone olmak için: @mehmethaneceye\n"
            "📋 Tüm planlar: /abonelik\n"
            "👥 Topluluk: <a href=\"https://t.me/+ztlxRCC7UspmZTY0\">t.me/okwis</a>"
        )

    mesaj = (
        "<b>👤 Hesabım</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"Kullanıcı ID: <code>{user_id}</code>\n"
        f"Plan: <b>{plan_satiri}</b>\n"
        f"{pro_satiri}\n"
        f"Günlük kullanım: <b>{gunluk}/{ANALIZ_GUNLUK_LIMIT}</b>"
        f"{yukseltme_satiri}"
    )
    await update.message.reply_text(mesaj, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


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
        f"◆ Pro atandı.\nuser_id={hedef_user_id}\npro_until={bitis.isoformat()}"
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
    await update.message.reply_text(f"◆ Pro iptal edildi. user_id={hedef_user_id}")


async def claude_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/claude_ver <user_id> <gun> — admin: Claude planı ata"""
    admin_id = update.effective_user.id if update.effective_user else None
    if not _admin_mi(admin_id):
        await update.message.reply_text("Bu komut yalnız admin için.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Kullanım: /claude_ver <user_id> <gun>")
        return
    try:
        hedef_user_id = int(context.args[0])
        gun = int(context.args[1])
        if gun <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Geçersiz parametre. Örnek: /claude_ver 123456789 30")
        return

    bitis = date.today() + timedelta(days=gun)
    data = _plan_kayitlarini_yukle()
    data[str(hedef_user_id)] = {"plan": "claude", "pro_until": bitis.isoformat()}
    _plan_kayitlarini_kaydet(data)
    _odeme_olayi_kaydet(
        action="claude_grant",
        hedef_user_id=hedef_user_id,
        admin_user_id=admin_id,
        detail=f"gun={gun}; pro_until={bitis.isoformat()}",
    )
    claude_durum = "✓ CLAUDE_API_KEY tanımlı" if CLAUDE_API_KEY else "⚠ CLAUDE_API_KEY eksik — .env'e ekle"
    await update.message.reply_text(
        f"◆ Claude planı atandı.\nuser_id={hedef_user_id}\npro_until={bitis.isoformat()}\n{claude_durum}"
    )


async def claude_iptal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/claude_iptal <user_id> — admin: Claude planını kaldır"""
    admin_id = update.effective_user.id if update.effective_user else None
    if not _admin_mi(admin_id):
        await update.message.reply_text("Bu komut yalnız admin için.")
        return
    if not context.args:
        await update.message.reply_text("Kullanım: /claude_iptal <user_id>")
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
        action="claude_revoke",
        hedef_user_id=hedef_user_id,
        admin_user_id=admin_id,
        detail="manual revoke",
    )
    await update.message.reply_text(f"◆ Claude planı iptal edildi. user_id={hedef_user_id}")


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
                    f"◆ Günlük ücretsiz limit doldu ({kullanilan}/{ANALIZ_GUNLUK_LIMIT}).\n\n"
                    "Daha fazla analiz için bir plan seç:\n"
                    "� /abonelik — tüm planları gör\n\n"
                    "📩 Abone olmak için: @mehmethaneceye\n"
                    "👥 Topluluk: <a href=\"https://t.me/+ztlxRCC7UspmZTY0\">t.me/okwis</a>\n\n"
                    "Yarın tekrar ücretsiz deneyebilirsin."
                ),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return ConversationHandler.END

    pro_mu = _kullanici_pro_mu(user_id) if user_id else False

    if pro_mu:
        # Pro/Claude: Okwis butonu aktif
        klavye = [
            [InlineKeyboardButton("◆ Okwis — Tanrının Gözü", callback_data="mod_okwis")],
            [InlineKeyboardButton("◈ Tüm Modlar", callback_data="menu_tum_modlar")],
        ]
        alt_metin = "Nasıl analiz yapalım?"
    else:
        # Free: Okwis kilitli, sadece Tüm Modlar aktif
        klavye = [
            [InlineKeyboardButton("🔒 Okwis — Tanrının Gözü (Premium)", callback_data="okwis_kilitli")],
            [InlineKeyboardButton("◈ Tüm Modlar", callback_data="menu_tum_modlar")],
        ]
        alt_metin = "Nasıl analiz yapalım?"

    reply_markup = InlineKeyboardMarkup(klavye)
    await update.message.reply_text(alt_metin, reply_markup=reply_markup)
    return MOD_SECIMI


async def mod_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı mod seçti"""
    query = update.callback_query
    await query.answer()

    if query.data == "yakinda":
        await query.edit_message_text("◆ Bu mod yakında geliyor. /analiz ile tekrar dene.")
        return ConversationHandler.END

    # Okwis kilitli butonu — free kullanıcı tıkladı
    if query.data == "okwis_kilitli":
        await query.answer(
            "Bu özellik Premium ve Tam Güç planlarına özeldir.",
            show_alert=True,
        )
        await query.edit_message_text(
            "🔒 <b>Okwis — Tanrının Gözü</b> Premium özelliğidir.\n\n"
            "8 modun tüm verisini aynı anda sentezleyen bu mod yalnızca ücretli planlarda kullanılabilir.\n\n"
            "📋 Tüm planları görmek için: /abonelik\n\n"
            "📩 Abone olmak için: @mehmethaneceye\n"
            "👥 Topluluk: <a href=\"https://t.me/+ztlxRCC7UspmZTY0\">t.me/okwis</a>\n\n"
            "Ücretsiz planda <b>◈ Tüm Modlar</b> ile 8 modu tek tek kullanabilirsin.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return ConversationHandler.END

    # mod_okwis seçildi — pro kontrolü (direkt callback ile gelenler için)
    if query.data == "mod_okwis":
        user_id = update.effective_user.id if update.effective_user else None
        if not _kullanici_pro_mu(user_id):
            await query.answer(
                "Bu özellik Premium ve Tam Güç planlarına özeldir.",
                show_alert=True,
            )
            return ConversationHandler.END

    # Tüm Modlar menüsü — 8 mod ekranını göster
    if query.data == "menu_tum_modlar":
        klavye = [
            [InlineKeyboardButton("◈ Mevsimler", callback_data="mod_mevsim"),
             InlineKeyboardButton("◈ Hava Durumu", callback_data="mod_hava")],
            [InlineKeyboardButton("◈ Jeopolitik", callback_data="mod_jeopolitik"),
             InlineKeyboardButton("◈ Sektör Trendleri", callback_data="mod_sektor")],
            [InlineKeyboardButton("◈ Dünya Trendleri", callback_data="mod_trendler"),
             InlineKeyboardButton("◈ Magazin/Viral", callback_data="mod_magazin")],
            [InlineKeyboardButton("◈ Özel Günler", callback_data="mod_ozel_gun"),
             InlineKeyboardButton("◈ Doğal Afet", callback_data="mod_dogal_afet")],
        ]
        await query.edit_message_text(
            "Hangi modu kullanmak istersin?",
            reply_markup=InlineKeyboardMarkup(klavye)
        )
        return MOD_SECIMI

    # Modu kaydet
    context.user_data["mod"] = query.data

    # Ülke seçim butonları
    klavye = []
    for i in range(0, len(ULKELER), 2):
        satir = [InlineKeyboardButton(ULKELER[i], callback_data=f"ulke_{ULKELER[i]}")]
        if i + 1 < len(ULKELER):
            satir.append(InlineKeyboardButton(ULKELER[i+1], callback_data=f"ulke_{ULKELER[i+1]}"))
        klavye.append(satir)

    mod_adi = "◆ Okwis — Tanrının Gözü" if query.data == "mod_okwis" else query.data.replace("mod_", "").capitalize()
    await query.edit_message_text(
        f"<b>{mod_adi}</b>\n\nHangi ülke için analiz yapalım?",
        reply_markup=InlineKeyboardMarkup(klavye),
        parse_mode=ParseMode.HTML,
    )
    return ULKE_SECIMI


async def ulke_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı ülke seçti — varlık sorusu sor"""
    query = update.callback_query
    await query.answer()

    ulke = query.data.replace("ulke_", "")
    context.user_data["ulke"] = ulke
    mod = context.user_data.get("mod", "")
    user_id = update.effective_user.id if update.effective_user else None

    # Okwis için varlık sorusu farklı — format seçimi yok
    if mod == "mod_okwis":
        # Profil var mı kontrol et
        profil = _kullanici_profili_al(user_id) if user_id else None
        profil_notu = ""
        if profil:
            profil_notu = "\n\n◆ <b>Kişisel profilin aktif</b> — analiz portföyüne göre özelleştirilecek."
        else:
            profil_notu = "\n\n<i>Profil tanımlanmamış. /profil ile portföyünü tanıtırsan analiz sana özel olur.</i>"

        await query.edit_message_text(
            f"◆ {ulke} seçildi.\n\n"
            "◆ <b>Okwis</b> tüm modları tarayacak.\n\n"
            "Odaklanmak istediğin bir varlık var mı?\n"
            "Örneğin: altın, petrol, bitcoin, dolar...\n\n"
            f"Yazarak cevap ver veya genel analiz için <b>BOŞ</b> yaz.{profil_notu}",
            parse_mode=ParseMode.HTML,
        )
        return VARLIK_SORGUSU

    await query.edit_message_text(
        f"◆ {ulke} seçildi.\n\n"
        "Özellikle odaklanmak istediğin bir varlık var mı?\n"
        "Örneğin: kripto, altın, petrol, doğalgaz, vs.\n\n"
        "Yazarak cevap ver veya boş geçmek için BOŞ yaz (genel analiz yapılır).",
    )
    return VARLIK_SORGUSU


async def varlik_sorgusu_cevap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı varlık adı yazdı veya BOŞ/boş yaptı"""
    if update.message:
        metin = update.message.text.strip()
        mod = context.user_data.get("mod", "")

        if metin.lower() in ("boş", "bos", ""):
            context.user_data["varlik"] = ""
            skip_msg = "Tamam, genel analiz yapacağım."
        else:
            context.user_data["varlik"] = metin
            skip_msg = f"Adım. <b>{_tg_html_escape(metin)}</b> üzerinde odaklanıp analiz yapacağım."

        # Okwis: format seçimi yok, direkt analiz başlat
        if mod == "mod_okwis":
            klavye = [[InlineKeyboardButton("◆ Okwis Analizi Başlat", callback_data="cikti_detay")]]
            await update.message.reply_text(
                f"{skip_msg}\n\n◆ Hazır olduğunda başlat:",
                reply_markup=InlineKeyboardMarkup(klavye),
                parse_mode=ParseMode.HTML,
            )
            return FORMAT_SECIMI

        # Diğer modlar: uzun/kısa seçimi
        klavye = [
            [
                InlineKeyboardButton("📖 Uzun anlatım", callback_data="cikti_detay"),
                InlineKeyboardButton("◆ Kısa Özet", callback_data="cikti_ozet"),
            ],
            [
                InlineKeyboardButton("✕ İptal", callback_data="analiz_iptal"),
            ],
        ]
        await update.message.reply_text(
            f"{skip_msg}\n\n"
            "Nasıl göstereyim?\n"
            "• Uzun anlatım — detaylı metin\n"
            "• Kısa özet — kritik satırlar, tek bakışta",
            reply_markup=InlineKeyboardMarkup(klavye),
            parse_mode=ParseMode.HTML,
        )
        return FORMAT_SECIMI

    return VARLIK_SORGUSU


async def varlik_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/skip komutu — varlık sorusunu geç, genel analiz yap"""
    context.user_data["varlik"] = ""
    mod = context.user_data.get("mod", "")

    if mod == "mod_okwis":
        klavye = [
            [InlineKeyboardButton("◆ Okwis Analizi Başlat", callback_data="cikti_detay")],
            [InlineKeyboardButton("✕ İptal", callback_data="analiz_iptal")],
        ]
        await update.message.reply_text(
            "Tamam, genel analiz yapacağım.\n\n◆ Hazır olduğunda başlat:",
            reply_markup=InlineKeyboardMarkup(klavye),
        )
        return FORMAT_SECIMI

    klavye = [
        [
            InlineKeyboardButton("📖 Uzun anlatım", callback_data="cikti_detay"),
            InlineKeyboardButton("◆ Kısa Özet", callback_data="cikti_ozet"),
        ],
        [
            InlineKeyboardButton("✕ İptal", callback_data="analiz_iptal"),
        ],
    ]
    await update.message.reply_text(
        "Tamam, genel analiz yapacağım.\n\n"
        "Nasıl göstereyim?\n"
        "• Uzun anlatım — detaylı metin\n"
        "• Kısa özet — kritik satırlar, tek bakışta",
        reply_markup=InlineKeyboardMarkup(klavye),
    )
    return FORMAT_SECIMI


async def cikti_format_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Çıktı stili seçildi — analizi üret ve gönder"""
    query = update.callback_query
    await query.answer()

    ulke = context.user_data.get("ulke")
    mod = context.user_data.get("mod", "mod_mevsim")
    varlik = context.user_data.get("varlik", "")

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
                    f"◆ Günlük ücretsiz limit doldu ({kullanilan}/{ANALIZ_GUNLUK_LIMIT}).\n\n"
                    "Daha fazla analiz için bir plan seç:\n"
                    "� /abonelik — tüm planları gör\n\n"
                    "📩 Abone olmak için: @mehmethaneceye\n"
                    "👥 Topluluk: <a href=\"https://t.me/+ztlxRCC7UspmZTY0\">t.me/okwis</a>\n\n"
                    "Yarın tekrar ücretsiz deneyebilirsin."
                ),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return ConversationHandler.END

    stil = CIKTI_OZET if query.data == "cikti_ozet" else CIKTI_DETAY
    stil_etiket = "kısa özet" if stil == CIKTI_OZET else "uzun anlatım"
    if mod == "mod_okwis":
        mod_kisa = "okwis"
        varlik_goster = f" · {varlik}" if varlik else ""
        await query.edit_message_text(f"◆ Okwis tarama başlıyor{varlik_goster}… Tüm modlar paralel çalışıyor.")
    elif mod == "mod_hava":
        mod_kisa = "hava"
    elif mod == "mod_jeopolitik":
        mod_kisa = "jeopolitik"
    elif mod == "mod_sektor":
        mod_kisa = "sektör"
    elif mod == "mod_trendler":
        mod_kisa = "trendler"
    elif mod == "mod_magazin":
        mod_kisa = "magazin"
    elif mod == "mod_ozel_gun":
        mod_kisa = "özel günler"
    elif mod == "mod_dogal_afet":
        mod_kisa = "doğal afet"
    else:
        mod_kisa = "mevsim"

    # Tüm modlar için adım adım bildirim yardımcısı
    async def bildirim(adim: str, detay: str = "") -> None:
        try:
            metin = f"◆ <b>{_tg_html_escape(ulke)}</b> · <i>{_tg_html_escape(mod_kisa)}</i>\n\n{_tg_html_escape(adim)}"
            if detay:
                metin += f"\n<i>{_tg_html_escape(detay)}</i>"
            await query.edit_message_text(metin, parse_mode=ParseMode.HTML)
        except Exception:
            pass

    # Okwis zaten kendi hazırlanıyor mesajını yazdı, diğer modlar için adım bildirimleri
    if mod != "mod_okwis":
        await bildirim("⏳ Veri kaynakları taranıyor…", "Canlı veriler çekiliyor")

    try:
        analiz_turu = ANALIZ_MEVSIM
        baglam = ""
        if mod == "mod_okwis":
            analiz_turu = "okwis"

            # Canlı ilerleme bildirimi
            tamamlanan_modlar: list[str] = []

            async def okwis_ilerleme(tamamlanan: int, toplam: int, mod_adi: str, basarili: bool) -> None:
                durum = "▸" if basarili else "▹"
                tamamlanan_modlar.append(f"{durum} {mod_adi}")
                kalan = toplam - tamamlanan
                satirlar = "\n".join(tamamlanan_modlar)
                devam = f"\n⏳ {kalan} mod daha…" if kalan > 0 else ""
                try:
                    await query.edit_message_text(
                        f"◆ <b>Okwis tarama yapıyor…</b>\n\n{satirlar}{devam}",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass  # Telegram rate limit vb. — sessizce geç

            baglamlar = await _topla_tum_baglamlari(ulke, ilerleme_cb=okwis_ilerleme)

            # Çıkarım aşaması bildirimleri
            await query.edit_message_text(
                f"◆ <b>Okwis tarama tamamlandı.</b>\n\n"
                + "\n".join(tamamlanan_modlar)
                + "\n\n🧠 Sosyal ihtimal zincirleri değerlendiriliyor…",
                parse_mode=ParseMode.HTML,
            )

            # Kullanıcı profilini al
            profil = _kullanici_profili_al(user_id) if user_id else None

            analiz = await asyncio.to_thread(okwis_analizi_yap, ulke, baglamlar, varlik, profil, "kisa", user_id)

            await query.edit_message_text(
                f"◆ <b>Okwis tarama tamamlandı.</b>\n\n"
                + "\n".join(tamamlanan_modlar)
                + "\n\n✨ Sonuç üretiliyor…",
                parse_mode=ParseMode.HTML,
            )

            alt_cizgi = "<b>━━━━━━━━━━━━━━━━━━━━</b>"
            varlik_satir = f" · <i>{_tg_html_escape(varlik)}</i>" if varlik else ""
            # Portföy veya profil aktif mi?
            _portfoy_aktif2 = False
            try:
                from portfoy import kullanici_portfoy_al as _pf_al2
                _portfoy_aktif2 = bool(_pf_al2(user_id).get("varliklar")) if user_id else False
            except Exception:
                pass
            if _portfoy_aktif2:
                profil_satir = " · <i>Portföy Aktif</i>"
            elif profil:
                profil_satir = " · <i>Kişisel Profil Aktif</i>"
            else:
                profil_satir = ""

            # Okwis güven kartı — context'e kaydet
            birlestik_baglam_kart = " ".join(v for v in baglamlar.values() if v)
            guven_olayi_kart = _guven_skoru_hesapla("okwis", birlestik_baglam_kart)
            okwis_guven_karti = _guven_karti_html("okwis", birlestik_baglam_kart, guven_olayi_kart, user_id)
            context.user_data["son_guven_karti"] = okwis_guven_karti
            context.user_data["son_analiz_mod"] = "okwis"
            # Görsel buton için güven verilerini sakla
            context.user_data["okwis_guven_kart_veri"] = guven_olayi_kart
            context.user_data["okwis_gorsel_ulke"] = ulke
            context.user_data["okwis_gorsel_varlik"] = varlik

            mesaj = (
                f"<b>◆ Okwis — Tanrının Gözü</b> · <i>Kısa Özet</i>\n"
                f"{alt_cizgi}\n"
                f"▸ <b>{_tg_html_escape(ulke)}</b>{varlik_satir}{profil_satir}\n"
                f"{alt_cizgi}\n\n"
                f"{_analiz_html_temizle(analiz)}\n\n"
                f"{ANALIZ_FOOTER_HTML}"
            )

            # Bağlamları ve profili kaydet — detay analizi için tekrar çekmeyeceğiz
            context.user_data["okwis_baglamlar"] = baglamlar
            context.user_data["okwis_profil"] = profil

            # Kısa analizi gönder + "Daha derin?" ve "Kalite Kartı" butonları
            detay_klavye = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Daha derin analiz", callback_data="okwis_detay")],
                [InlineKeyboardButton("📊 Kalite Kartı", callback_data="show_quality_card"),
                 InlineKeyboardButton("📈 Görseller", callback_data="okwis_gorseller")],
                [InlineKeyboardButton("✕ Kapat", callback_data="okwis_kapat")],
            ])
            await gonder_parcali_html(query, context, mesaj)
            
            # Son mesajın altına buton ekle
            try:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="Daha derin ve detaylı analiz ister misin?",
                    reply_markup=detay_klavye,
                )
            except Exception:
                pass
            
            # PDF rapor butonu ekle (Pro kullanıcılar için)
            if user_id and _kullanici_pro_mu(user_id):
                try:
                    pdf_klavye = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📄 PDF Rapor İndir", callback_data="okwis_pdf")],
                    ])
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text="<b>Pro Özellik:</b> Analizi PDF rapor olarak indirebilirsin.",
                        reply_markup=pdf_klavye,
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass
            # Metrik kaydı
            birlestik_baglam = " ".join(v for v in baglamlar.values() if v)
            guven_olayi = _guven_skoru_hesapla("okwis", birlestik_baglam)
            _analiz_olayi_kaydet(
                analiz_turu="okwis",
                ulke=ulke,
                cikti_stili="okwis",
                guven=guven_olayi,
                baglam_metni=birlestik_baglam[:500],
            )
            # Okwis tahmin kaydet
            _tahmin_kaydet(
                mod="okwis",
                ulke=ulke,
                varlik=varlik,
                analiz_metni=analiz,
                user_id=user_id,
            )
            if user_id is not None:
                yeni = _gunluk_kullanim_arttir(user_id)
                logger.info("Günlük kullanım arttı (okwis): user=%s %s/%s", user_id, yeni, ANALIZ_GUNLUK_LIMIT)
            return OKWIS_DETAY_SECIMI

        elif mod == "mod_mevsim":
            await bildirim("📡 Adım 1/3 — Mevsim verileri ve haber başlıkları çekiliyor…", "BBC Business RSS + ulke_mevsim.json")
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
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "prob_zinciri.json analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(mevsim_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_hava":
            analiz_turu = ANALIZ_HAVA
            await bildirim("📡 Adım 1/3 — Hava verisi çekiliyor…", "OpenWeatherMap API (anlık + 5 günlük tahmin)")
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
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Hava-lojistik-enerji zinciri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(hava_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_jeopolitik":
            analiz_turu = ANALIZ_JEOPOLITIK
            await bildirim("📡 Adım 1/3 — Jeopolitik haber başlıkları çekiliyor…", "BBC World News RSS")
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
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Jeopolitik-enerji-savunma zinciri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(jeopolitik_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_sektor":
            analiz_turu = ANALIZ_SEKTOR
            await bildirim("📡 Adım 1/3 — Sektör haber başlıkları çekiliyor…", "BBC Business, BBC Technology RSS")
            try:
                baglam = await asyncio.to_thread(topla_sektor_baglami, ulke)
            except Exception:
                logger.exception("Sektör bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Sektör bağlamı yüklenemedi</b>\n\nRSS kaynağı veya ağ sorunu olabilir. Lütfen bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Teknoloji-sektör dönüşüm zincirleri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(sektor_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_trendler":
            analiz_turu = ANALIZ_TRENDLER
            await bildirim("📡 Adım 1/3 — Dünya trend haberleri çekiliyor…", "BBC News, BBC World, BBC Technology RSS")
            try:
                baglam = await asyncio.to_thread(topla_trendler_baglami, ulke)
            except Exception:
                logger.exception("Trendler bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Trendler bağlamı yüklenemedi</b>\n\nRSS kaynağı veya ağ sorunu olabilir. Lütfen bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Teknoloji trendi-sektör dönüşüm zincirleri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(trendler_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_magazin":
            analiz_turu = ANALIZ_MAGAZIN
            await bildirim("📡 Adım 1/3 — Magazin ve viral haber başlıkları çekiliyor…", "BBC Entertainment, BBC Technology RSS")
            try:
                baglam = await asyncio.to_thread(topla_magazin_baglami, ulke)
            except Exception:
                logger.exception("Magazin bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Magazin bağlamı yüklenemedi</b>\n\nRSS kaynağı veya ağ sorunu olabilir. Lütfen bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Viral-marka-tüketici davranışı zincirleri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(magazin_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_ozel_gun":
            analiz_turu = ANALIZ_OZEL_GUN
            await bildirim("📡 Adım 1/3 — Özel gün takvimi ve haber başlıkları çekiliyor…", "ozel_gunler.json + BBC Business RSS")
            try:
                baglam = await asyncio.to_thread(topla_ozel_gunler_baglami, ulke)
            except Exception:
                logger.exception("Özel günler bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Özel günler bağlamı yüklenemedi</b>\n\nBir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Özel gün-tüketim dalgası zincirleri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(ozel_gun_analizi_yap, ulke, baglam, stil, varlik, user_id)
        elif mod == "mod_dogal_afet":
            analiz_turu = ANALIZ_DOGAL_AFET
            await bildirim("📡 Adım 1/3 — Deprem ve afet verileri çekiliyor…", "USGS Earthquake API (M5+, son 7 gün) + BBC World RSS")
            try:
                baglam = await asyncio.to_thread(topla_dogal_afet_baglami, ulke)
            except Exception:
                logger.exception("Doğal afet bağlamı toplanamadı (ülke=%s)", ulke)
                await query.edit_message_text(
                    "<b>Doğal afet bağlamı yüklenemedi</b>\n\nUSGS veya RSS kaynağı geçici olabilir. Bir süre sonra <b>/analiz</b> ile tekrar dene.",
                    parse_mode=ParseMode.HTML,
                )
                return ConversationHandler.END
            await bildirim("🧠 Adım 2/3 — Sosyal ihtimal zincirleri değerlendiriliyor…", "Afet-yeniden yapılanma ekonomisi zincirleri analiz ediliyor")
            await bildirim("✨ Adım 3/3 — AI çıkarım yapıyor…", "Gemini / DeepSeek analiz üretiyor")
            analiz = await asyncio.to_thread(dogal_afet_analizi_yap, ulke, baglam, stil, varlik, user_id)
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

        # Tahmin kaydet
        _tahmin_kaydet(
            mod=analiz_turu,
            ulke=ulke,
            varlik=varlik,
            analiz_metni=analiz,
            user_id=user_id,
        )

        # Güven kartını context'e kaydet (buton ile göstermek için)
        guven_karti = _guven_karti_html(analiz_turu, baglam, guven_olayi, user_id)
        context.user_data["son_guven_karti"] = guven_karti
        context.user_data["son_analiz_mod"] = analiz_turu
        
        # Mesajı güven kartı OLMADAN gönder
        mesaj_govde = sarmla_analiz_mesaji_html(ulke, stil, analiz, analiz_turu=analiz_turu)
        
        # Kalite kartı butonu ekle
        keyboard = [[InlineKeyboardButton("📊 Kalite Kartını Göster", callback_data="show_quality_card")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await gonder_parcali_html(query, context, mesaj_govde, reply_markup=reply_markup)
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
    """
    Yazılı mesajları yönet.
    Pro/Claude → niyet tespit et: analiz isteği mi sohbet mi?
    Free → fiyat sorusu ise cevapla, değilse /analiz yönlendir.
    """
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return

    kullanici_mesaji = update.message.text.strip()

    # ── Fiyat sorusu tespiti — tüm kullanıcılara açık ────────────────────────
    try:
        from fiyat_servisi import fiyat_sorusu_mu, fiyat_sorgula
        if fiyat_sorusu_mu(kullanici_mesaji):
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )
            sonuc = await asyncio.to_thread(fiyat_sorgula, kullanici_mesaji)
            if sonuc:
                if sonuc.get("grafik"):
                    await update.message.reply_photo(
                        photo=io.BytesIO(sonuc["grafik"]),
                        caption=sonuc["mesaj"],
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await update.message.reply_text(
                        sonuc["mesaj"], parse_mode=ParseMode.HTML
                    )
                return
    except Exception as _fe:
        logger.warning("Fiyat servisi hatası: %s", _fe)

    # ── Free kullanıcı → yönlendir ────────────────────────────────────────────
    if not _kullanici_pro_mu(user_id):
        await update.message.reply_text(
            "Analiz başlatmak için /analiz yaz.\n"
            "<i>Sohbet modu Pro/Claude plana özeldir.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    from sohbet import sohbet_cevabi_uret, gecmis_ekle
    profil = _kullanici_profili_al(user_id)

    gecmis_ekle(user_id, "user", kullanici_mesaji)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    cevap = await asyncio.to_thread(
        sohbet_cevabi_uret, kullanici_mesaji, user_id, profil
    )

    gecmis_ekle(user_id, "assistant", cevap)
    await update.message.reply_text(cevap)


async def sesli_mesaj_isle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sesli mesajları işle.
    Pro/Claude → STT → sohbet → TTS cevap. Free → yönlendir.
    """
    import io as _io
    if not update.message:
        return

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return

    if not _kullanici_pro_mu(user_id):
        await update.message.reply_text(
            "Sesli sohbet modu Pro/Claude plana özeldir.\n"
            "/analiz ile analiz başlatabilirsin.",
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    try:
        voice = update.message.voice or update.message.audio
        if not voice:
            return
        dosya = await context.bot.get_file(voice.file_id)
        ses_verisi = bytes(await dosya.download_as_bytearray())
    except Exception as e:
        logger.exception("Ses dosyası indirilemedi: %s", e)
        await update.message.reply_text("Ses dosyası alınamadı, tekrar dene.")
        return

    from sohbet import ses_metne_cevir, sohbet_cevabi_uret, gecmis_ekle, metin_sese_cevir

    kullanici_metni = await asyncio.to_thread(ses_metne_cevir, ses_verisi, "ses.ogg")

    if not kullanici_metni:
        await update.message.reply_text("Sesi anlayamadım, tekrar dener misin?")
        return

    logger.info("STT sonucu (user=%s): %s", user_id, kullanici_metni[:80])
    profil = _kullanici_profili_al(user_id)

    # Direkt sohbet modu - komut algılama kaldırıldı
    gecmis_ekle(user_id, "user", kullanici_metni)

    cevap = await asyncio.to_thread(
        sohbet_cevabi_uret, kullanici_metni, user_id, profil
    )
    gecmis_ekle(user_id, "assistant", cevap)

    # TTS — sesli cevap gönder
    ses_cevap = await asyncio.to_thread(metin_sese_cevir, cevap)
    logger.info("TTS sonucu: %s", "ses var" if ses_cevap else "ses yok")

    if ses_cevap:
        try:
            import io as _io
            await update.message.reply_voice(
                voice=_io.BytesIO(ses_cevap),
                caption=f"<i>{_tg_html_escape(kullanici_metni[:100])}</i>",
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception as e:
            logger.warning("Sesli cevap gönderilemedi, yazılı gönderiliyor: %s", e)

    # TTS başarısız → yazılı cevap
    await update.message.reply_text(
        f"<i>🎤 {_tg_html_escape(kullanici_metni)}</i>\n\n{_tg_html_escape(cevap)}",
        parse_mode=ParseMode.HTML,
    )


# ─── Botu Başlat ──────────────────────────────────────────────────────────────

def check_required_env_vars():
    """Gerekli environment variable'ları kontrol et"""
    required = {
        "TELEGRAM_TOKEN": "Telegram bot token",
        "GEMINI_API_KEY": "Gemini API anahtarı (veya GEMINI_API_KEYS)",
        "OPENWEATHER_API_KEY": "OpenWeather API anahtarı",
        "TAVILY_API_KEY": "Tavily API anahtarı",
    }
    
    missing = []
    for var, desc in required.items():
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            missing.append(f"{var} ({desc})")
    
    if missing:
        error_msg = (
            "❌ Eksik veya geçersiz environment variables:\n" +
            "\n".join(f"  - {m}" for m in missing) +
            "\n\n.env dosyasını kontrol edin ve gerçek API anahtarlarınızı girin."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("✅ Tüm gerekli environment variables mevcut")


def main():
    """Botu çalıştır"""
    # Environment variables kontrolü
    check_required_env_vars()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Konuşma akışını tanımla
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("analiz", analiz_baslat)],
        states={
            MOD_SECIMI: [CallbackQueryHandler(mod_secildi)],
            ULKE_SECIMI: [CallbackQueryHandler(ulke_secildi)],
            VARLIK_SORGUSU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, varlik_sorgusu_cevap),
                CommandHandler("skip", varlik_skip),
            ],
            FORMAT_SECIMI: [
                CallbackQueryHandler(analiz_iptal_buton, pattern="^analiz_iptal$"),
                CallbackQueryHandler(cikti_format_secildi),
            ],
            OKWIS_DETAY_SECIMI: [
                CallbackQueryHandler(okwis_detay_secildi, pattern="^okwis_(detay|kapat)$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_ve_konusmayi_bitir),
            CommandHandler("cancel", iptal),
        ],
        per_message=False,  # MessageHandler kullanıldığı için False olmalı
        per_chat=True,
        per_user=True,
    )

    # Konuşma önce: aktif akışta /start ve /cancel fallbacks ile biter.
    app.add_handler(conv_handler)

    # Profil ConversationHandler
    profil_handler = ConversationHandler(
        entry_points=[CommandHandler("profil", profil_baslat)],
        states={
            PROFIL_METIN_BEKLENIYOR: [
                CallbackQueryHandler(profil_callback, pattern="^profil_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, profil_metin_al),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", profil_iptal),
            CommandHandler("start", start_ve_konusmayi_bitir),
        ],
        per_message=False,  # MessageHandler kullanıldığı için False olmalı
        per_chat=True,
        per_user=True,
    )
    app.add_handler(profil_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("hesabim", hesabim))
    app.add_handler(CommandHandler("abonelik", abonelik_goster))
    app.add_handler(CommandHandler("fiyat", fiyat_komut))
    app.add_handler(CommandHandler("performans", performans))
    app.add_handler(CommandHandler("gecmis", gecmis))
    app.add_handler(CommandHandler("backtest", backtest))
    app.add_handler(CommandHandler("gecmis_sil", gecmis_sil))
    app.add_handler(CommandHandler("bildirim", bildirim_ayar))
    app.add_handler(CommandHandler("pro_ver", pro_ver))
    app.add_handler(CommandHandler("pro_iptal", pro_iptal))
    app.add_handler(CommandHandler("claude_ver", claude_ver))
    app.add_handler(CommandHandler("claude_iptal", claude_iptal))
    app.add_handler(CommandHandler("odeme_kayit", odeme_kayit))

    # Portföy komutları
    app.add_handler(CommandHandler("portfoy", portfoy_komut))
    app.add_handler(CallbackQueryHandler(portfoy_callback, pattern="^portfoy_"))

    # Bildirim ayarları callback
    app.add_handler(CallbackQueryHandler(bildirim_callback, pattern="^bildirim_"))

    # Kalite kartı butonu handler
    app.add_handler(CallbackQueryHandler(kalite_karti_goster, pattern="^show_quality_card$"))

    # Abonelik planları butonu handler
    app.add_handler(CallbackQueryHandler(abonelik_goster, pattern="^abonelik_goster$"))
    
    # Okwis görseller butonu handler
    app.add_handler(CallbackQueryHandler(okwis_gorseller_goster, pattern="^okwis_gorseller$"))
    
    # PDF rapor butonu handler (Pro özelliği)
    app.add_handler(CallbackQueryHandler(okwis_pdf_olustur, pattern="^okwis_pdf$"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, diger_mesajlar))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, sesli_mesaj_isle))

    logger.info(
        "Bot başlatıldı… AI_PROVIDER=%s AI_FALLBACK_GEMINI=%s AI_FALLBACK_DEEPSEEK=%s gemini_anahtar_sayısı=%s",
        AI_PROVIDER,
        AI_FALLBACK_GEMINI,
        AI_FALLBACK_DEEPSEEK,
        len(_gemini_anahtarlari()),
    )

    # ── Alarm sistemi ────────────────────────────────────────────────────────
    async def _alarm_job(context) -> None:
        try:
            await alarm_tara_ve_bildir(
                bot=context.bot,
                plan_kayitlari_yukle_fn=_plan_kayitlarini_yukle,
                kullanici_pro_mu_fn=_kullanici_pro_mu,
            )
        except Exception as e:
            logger.exception("Alarm job hatası: %s", e)

    job_queue = app.job_queue
    if job_queue is not None:
        job_queue.run_repeating(
            _alarm_job,
            interval=ALARM_ARALIK_SANIYE,
            first=60,  # Bot başladıktan 60 saniye sonra ilk tarama
            name="okwis_alarm",
        )
        logger.info("Alarm sistemi başlatıldı (her %d saniye)", ALARM_ARALIK_SANIYE)
    else:
        logger.warning("JobQueue mevcut değil — alarm sistemi başlatılamadı")

    app.run_polling()


if __name__ == "__main__":
    main()