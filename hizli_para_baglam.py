"""
Hızlı Para Modu — Agresif Kısa Vadeli Trade Önerileri
Kripto, Forex, Hisse, Emtia için 2-7 günlük trade setup'ları.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from dogal_afet_baglam import topla_dogal_afet_baglami
from hava_baglam import topla_hava_baglami
from jeopolitik_baglam import topla_jeopolitik_baglami
from magazin_baglam import topla_magazin_baglami
from mevsim_baglam import topla_mevsim_baglami
from ozel_gunler_baglam import topla_ozel_gunler_baglami
from sektor_baglam import topla_sektor_baglami
from trendler_baglam import topla_trendler_baglami
from fiyat_servisi import fiyat_sorgula, sembol_tespit

logger = logging.getLogger(__name__)

_HIZLI_PARA_DURUM_PATH = Path(__file__).resolve().parent / "metrics" / "hizli_para_modu.json"
_HIZLI_PARA_ISLEMLER_PATH = Path(__file__).resolve().parent / "metrics" / "hizli_para_islemler.jsonl"


# ─── Durum Yönetimi ───────────────────────────────────────────────────────────

def _durum_yukle() -> dict:
    """Hızlı Para Modu kullanıcı durumlarını yükle."""
    try:
        if _HIZLI_PARA_DURUM_PATH.exists():
            with open(_HIZLI_PARA_DURUM_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Hızlı Para durum yüklenemedi: %s", e)
    return {}


def _durum_kaydet(durum: dict):
    """Hızlı Para Modu durumunu kaydet."""
    try:
        _HIZLI_PARA_DURUM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_HIZLI_PARA_DURUM_PATH, "w", encoding="utf-8") as f:
            json.dump(durum, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Hızlı Para durum kaydedilemedi: %s", e)


def hizli_para_aktif_mi(user_id: int | str) -> bool:
    """Kullanıcının Hızlı Para Modu aktif mi?"""
    durum = _durum_yukle()
    return durum.get(str(user_id), {}).get("aktif", False)


def hizli_para_ayarla(user_id: int | str, aktif: bool):
    """Kullanıcının Hızlı Para Modu durumunu ayarla."""
    durum = _durum_yukle()
    user_key = str(user_id)
    if user_key not in durum:
        durum[user_key] = {}
    durum[user_key]["aktif"] = aktif
    durum[user_key]["son_guncelleme"] = datetime.now(timezone.utc).isoformat()
    _durum_kaydet(durum)
    logger.info("Hızlı Para Modu %s: user=%s", "AKTİF" if aktif else "KAPALI", user_id)


def hizli_para_son_varlik_kaydet(user_id: int | str, varlik: str):
    """Son analiz edilen varlığı kaydet."""
    durum = _durum_yukle()
    user_key = str(user_id)
    if user_key not in durum:
        durum[user_key] = {"aktif": True}
    durum[user_key]["son_varlik"] = varlik
    durum[user_key]["son_analiz"] = datetime.now(timezone.utc).isoformat()
    _durum_kaydet(durum)


# ─── Trade Kaydı (Backtest için) ──────────────────────────────────────────────

def hizli_para_trade_kaydet(
    user_id: int | str,
    varlik: str,
    ulke: str,
    pozisyon: str,
    giris_min: float,
    giris_max: float,
    tp1: float,
    tp2: float,
    tp3: float,
    stop_loss: float,
    sure: str,
    risk_odul: float,
    kaldirac_max: int,
    guven: int,
):
    """Trade önerisini kaydet (backtest için)."""
    try:
        _HIZLI_PARA_ISLEMLER_PATH.parent.mkdir(parents=True, exist_ok=True)
        kayit = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "tarih": datetime.now(timezone.utc).date().isoformat(),
            "user_id": str(user_id),
            "varlik": varlik,
            "ulke": ulke,
            "pozisyon": pozisyon,
            "giris_min": giris_min,
            "giris_max": giris_max,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "stop_loss": stop_loss,
            "sure": sure,
            "risk_odul": risk_odul,
            "kaldirac_max": kaldirac_max,
            "guven": guven,
            "dogrulandi": False,
            "sonuc": None,  # "tp1", "tp2", "tp3", "stop_loss", "bekleyen"
        }
        with open(_HIZLI_PARA_ISLEMLER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        logger.info("Hızlı Para trade kaydedildi: %s %s", pozisyon, varlik)
    except Exception as e:
        logger.error("Hızlı Para trade kaydedilemedi: %s", e)


# ─── Varlık Tipi Tespiti ─────────────────────────────────────────────────────

def _varlik_tipi_tespit(varlik: str) -> str:
    """Varlık tipini tespit et: kripto, forex, hisse, emtia."""
    varlik_lower = varlik.lower()
    
    # Kripto
    kriptolar = [
        "btc", "bitcoin", "eth", "ethereum", "xrp", "ripple",
        "ada", "cardano", "sol", "solana", "doge", "dogecoin",
        "bnb", "binance", "avax", "avalanche", "dot", "polkadot",
        "matic", "polygon", "link", "chainlink", "uni", "uniswap",
        "ltc", "litecoin", "atom", "cosmos", "xlm", "stellar"
    ]
    
    # Forex (para çiftleri)
    forex_pairs = [
        "eur/usd", "eurusd", "gbp/usd", "gbpusd", "usd/jpy", "usdjpy",
        "usd/chf", "usdchf", "aud/usd", "audusd", "usd/cad", "usdcad",
        "nzd/usd", "nzdusd", "eur/gbp", "eurgbp", "eur/jpy", "eurjpy",
        "gbp/jpy", "gbpjpy", "try/usd", "tryusd", "usd/try", "usdtry"
    ]
    
    # Emtia
    emtialar = [
        "gold", "xauusd", "altın", "altin", "silver", "xagusd", "gümüş", "gumus",
        "oil", "wti", "brent", "petrol", "gas", "gaz", "doğalgaz", "dogalgaz",
        "copper", "bakır", "bakir", "wheat", "buğday", "bugday",
        "corn", "mısır", "misir", "soybean", "soya"
    ]
    
    # Hisse (semboller ve şirket adları)
    hisseler = [
        "aapl", "apple", "msft", "microsoft", "googl", "google", "amzn", "amazon",
        "tsla", "tesla", "meta", "facebook", "nvda", "nvidia", "amd",
        "nflx", "netflix", "dis", "disney", "ba", "boeing",
        "thyao", "turkcell", "garan", "garanti", "akbnk", "akbank",
        "isctr", "isbank", "tuprs", "tupras", "sahol", "sabanci"
    ]
    
    # Tespit
    for kripto in kriptolar:
        if kripto in varlik_lower:
            return "kripto"
    
    for forex in forex_pairs:
        if forex in varlik_lower.replace(" ", "").replace("/", ""):
            return "forex"
    
    for emtia in emtialar:
        if emtia in varlik_lower:
            return "emtia"
    
    for hisse in hisseler:
        if hisse in varlik_lower:
            return "hisse"
    
    # Varsayılan: kripto (çoğu kullanıcı kripto soracak)
    return "kripto"


# ─── 8 Mod Bağlam Toplama ─────────────────────────────────────────────────────

def _8_mod_baglam_topla(ulke: str, varlik: str) -> str:
    """8 modu paralel tara, bağlamı topla (Okwis gibi ama kısa vadeli odak)."""
    baglamlar = []
    
    # 1. Mevsim
    try:
        mevsim = topla_mevsim_baglami(ulke)
        if mevsim:
            baglamlar.append(f"[MEVSIM]\n{mevsim[:400]}")
    except Exception as e:
        logger.warning("Mevsim bağlamı alınamadı: %s", e)
    
    # 2. Hava
    try:
        hava = topla_hava_baglami(ulke)
        if hava:
            baglamlar.append(f"[HAVA]\n{hava[:400]}")
    except Exception as e:
        logger.warning("Hava bağlamı alınamadı: %s", e)
    
    # 3. Jeopolitik (EN ÖNEMLİ — kısa vadeli volatilite)
    try:
        jeopolitik = topla_jeopolitik_baglami(ulke)
        if jeopolitik:
            baglamlar.append(f"[JEOPOLİTİK — YÜKSEK ÖNCELİK]\n{jeopolitik[:600]}")
    except Exception as e:
        logger.warning("Jeopolitik bağlamı alınamadı: %s", e)
    
    # 4. Sektör
    try:
        sektor = topla_sektor_baglami(ulke)
        if sektor:
            baglamlar.append(f"[SEKTÖR]\n{sektor[:400]}")
    except Exception as e:
        logger.warning("Sektör bağlamı alınamadı: %s", e)
    
    # 5. Trendler
    try:
        trendler = topla_trendler_baglami(ulke)
        if trendler:
            baglamlar.append(f"[TRENDLER]\n{trendler[:400]}")
    except Exception as e:
        logger.warning("Trendler bağlamı alınamadı: %s", e)
    
    # 6. Magazin (düşük öncelik)
    try:
        magazin = topla_magazin_baglami(ulke)
        if magazin:
            baglamlar.append(f"[MAGAZİN]\n{magazin[:300]}")
    except Exception as e:
        logger.warning("Magazin bağlamı alınamadı: %s", e)
    
    # 7. Özel Günler
    try:
        ozel_gun = topla_ozel_gunler_baglami(ulke)
        if ozel_gun:
            baglamlar.append(f"[ÖZEL GÜNLER]\n{ozel_gun[:300]}")
    except Exception as e:
        logger.warning("Özel günler bağlamı alınamadı: %s", e)
    
    # 8. Doğal Afet
    try:
        dogal_afet = topla_dogal_afet_baglami(ulke)
        if dogal_afet:
            baglamlar.append(f"[DOĞAL AFET]\n{dogal_afet[:300]}")
    except Exception as e:
        logger.warning("Doğal afet bağlamı alınamadı: %s", e)
    
    return "\n\n".join(baglamlar) if baglamlar else "Bağlam verisi alınamadı."


# ─── Hızlı Para Analizi ───────────────────────────────────────────────────────

def hizli_para_analizi(
    varlik: str,
    ulke: str,
    user_id: int | str,
    llm_fn,
) -> dict:
    """
    Kısa vadeli trade önerisi üret.
    
    Args:
        varlik: Varlık adı (BTC, EUR/USD, AAPL, XAUUSD)
        ulke: Ülke (Türkiye, ABD, vb.)
        user_id: Kullanıcı ID
        llm_fn: LLM fonksiyonu (llm_metin_uret)
    
    Returns:
        {
            "pozisyon": "LONG" | "SHORT" | "BEKLE",
            "giris_min": float,
            "giris_max": float,
            "tp1": float,
            "tp2": float,
            "tp3": float,
            "stop_loss": float,
            "sure": str,
            "risk_odul": float,
            "kaldirac_max": int,
            "neden": str,
            "riskler": list[str],
            "guven": int,
            "fiyat_verisi": dict,
            "varlik_tipi": str,
        }
    """
    logger.info("Hızlı Para analizi başladı: %s, %s, user=%s", varlik, ulke, user_id)
    
    # Varlık tipi tespit
    varlik_tipi = _varlik_tipi_tespit(varlik)
    
    # Fiyat verisi al (fiyat_sorgula kullan)
    fiyat_sonuc = fiyat_sorgula(varlik)
    
    if not fiyat_sonuc or not fiyat_sonuc.get("mesaj"):
        logger.warning("Fiyat verisi alınamadı: %s", varlik)
        fiyat_str = f"Fiyat verisi alınamadı ({varlik}). Genel piyasa verisiyle analiz yap."
        fiyat_verisi = {}
    else:
        # fiyat_sorgula'dan gelen mesajı parse et
        mesaj = fiyat_sonuc.get("mesaj", "")
        
        # Basit fiyat çıkarımı (mesajdan)
        import re
        fiyat_match = re.search(r'\$?([\d,]+\.?\d*)', mesaj)
        fiyat = float(fiyat_match.group(1).replace(',', '')) if fiyat_match else 0
        
        fiyat_verisi = {
            "fiyat": fiyat,
            "mesaj": mesaj,
        }
        
        fiyat_str = f"""
GERÇEK ZAMANLI FİYAT — {varlik.upper()}
{mesaj}

Not: Fiyat servisi üzerinden alınan gerçek zamanlı veri.
"""
    
    # 8 mod bağlamı topla
    mod_baglami = _8_mod_baglam_topla(ulke, varlik)
    
    # Prompt oluştur
    prompt = f"""
Sen agresif kısa vadeli trader'sın. Hedge fon scalping masasında 8 yıl çalıştın.
Şimdi bağımsız trade danışmanısın. Müşterilerine net, cesur, kısa vadeli trade önerileri veriyorsun.

GÖREV: {varlik.upper()} için 2-7 günlük trade setup'ı ver.

VARLIK TİPİ: {varlik_tipi.upper()}
ÜLKE: {ulke}

{fiyat_str}

8 MOD BAĞLAMI (Jeopolitik, Mevsim, Hava, Sektör, Trendler, Magazin, Özel Günler, Doğal Afet):
{mod_baglami}

ÇIKTI FORMATI (JSON):
{{
  "pozisyon": "LONG" veya "SHORT" veya "BEKLE",
  "giris_min": sayı (giriş aralığı alt sınır),
  "giris_max": sayı (giriş aralığı üst sınır),
  "tp1": sayı (ilk kar al hedefi),
  "tp2": sayı (ikinci kar al hedefi),
  "tp3": sayı (üçüncü kar al hedefi),
  "stop_loss": sayı (zarar durdur seviyesi),
  "sure": "X-Y gün" (tahmini süre),
  "risk_odul": sayı (risk/ödül oranı, örn: 2.5),
  "kaldirac_max": sayı (önerilen max kaldıraç, 1-10 arası),
  "neden": "2-3 cümle, somut gerekçe",
  "riskler": ["risk1", "risk2", "risk3"],
  "guven": sayı (0-100, analiz güven skoru)
}}

KURALLAR:
1. Net yön ver: LONG (al), SHORT (sat), BEKLE (pozisyon açma)
2. Giriş aralığı dar olsun (max %2-3 fark)
3. 3 TP seviyesi ver (kademeli kar al stratejisi)
   - TP1: Konservatif (%2-3)
   - TP2: Orta (%4-6)
   - TP3: Agresif (%7-12)
4. Stop loss net olsun (max %3-5 risk)
5. Risk/ödül min 1:2 olsun (ideal 1:3)
6. Kaldıraç konservatif öner:
   - Kripto: max 3-5x
   - Forex: max 5-10x
   - Hisse: max 2-3x
   - Emtia: max 3-5x
7. Belirsiz dil YASAK ("olabilir", "muhtemelen", "belki" yasak)
8. Her çıkarım somut veriye dayansın (fiyat, bağlam, teknik seviye)
9. Riskler net olsun (Fed kararı, destek kırılması, vb.)
10. Türkçe yaz (sembol/teknik terimler İngilizce kalabilir)

ÖNEMLİ: Sadece JSON çıktısı ver. Açıklama, yorum, markdown YASAK.
JSON geçerli olmalı (virgül, tırnak, parantez kontrolü yap).
"""
    
    # LLM'den yanıt al
    try:
        yanit = llm_fn(prompt, user_id)
        
        # JSON parse et
        # Model bazen ```json ... ``` ile sarabilir, temizle
        yanit = yanit.strip()
        if yanit.startswith("```json"):
            yanit = yanit[7:]
        if yanit.startswith("```"):
            yanit = yanit[3:]
        if yanit.endswith("```"):
            yanit = yanit[:-3]
        yanit = yanit.strip()
        
        analiz = json.loads(yanit)
        
        # Zorunlu alanları kontrol et
        gerekli_alanlar = [
            "pozisyon", "giris_min", "giris_max", "tp1", "tp2", "tp3",
            "stop_loss", "sure", "risk_odul", "kaldirac_max", "neden", "riskler", "guven"
        ]
        for alan in gerekli_alanlar:
            if alan not in analiz:
                raise ValueError(f"Eksik alan: {alan}")
        
        # Ek bilgiler ekle
        analiz["fiyat_verisi"] = fiyat_verisi
        analiz["varlik_tipi"] = varlik_tipi
        analiz["varlik"] = varlik.upper()
        analiz["ulke"] = ulke
        
        # Trade kaydı
        hizli_para_trade_kaydet(
            user_id=user_id,
            varlik=varlik.upper(),
            ulke=ulke,
            pozisyon=analiz["pozisyon"],
            giris_min=analiz["giris_min"],
            giris_max=analiz["giris_max"],
            tp1=analiz["tp1"],
            tp2=analiz["tp2"],
            tp3=analiz["tp3"],
            stop_loss=analiz["stop_loss"],
            sure=analiz["sure"],
            risk_odul=analiz["risk_odul"],
            kaldirac_max=analiz["kaldirac_max"],
            guven=analiz["guven"],
        )
        
        # Son varlık kaydet
        hizli_para_son_varlik_kaydet(user_id, varlik.upper())
        
        logger.info("Hızlı Para analizi tamamlandı: %s %s", analiz["pozisyon"], varlik)
        return analiz
        
    except json.JSONDecodeError as e:
        logger.error("JSON parse hatası: %s\nYanıt: %s", e, yanit[:500])
        raise ValueError(f"Model geçersiz JSON döndü: {e}")
    except Exception as e:
        logger.error("Hızlı Para analizi hatası: %s", e)
        raise


# ─── HTML Formatter ───────────────────────────────────────────────────────────

def hizli_para_html_formatla(analiz: dict) -> str:
    """Hızlı Para analizini Telegram HTML formatına çevir."""
    import html
    
    def esc(text):
        return html.escape(str(text), quote=False)
    
    varlik = analiz.get("varlik", "N/A")
    pozisyon = analiz.get("pozisyon", "BEKLE")
    giris_min = analiz.get("giris_min", 0)
    giris_max = analiz.get("giris_max", 0)
    tp1 = analiz.get("tp1", 0)
    tp2 = analiz.get("tp2", 0)
    tp3 = analiz.get("tp3", 0)
    stop_loss = analiz.get("stop_loss", 0)
    sure = analiz.get("sure", "N/A")
    risk_odul = analiz.get("risk_odul", 0)
    kaldirac_max = analiz.get("kaldirac_max", 1)
    neden = analiz.get("neden", "")
    riskler = analiz.get("riskler", [])
    guven = analiz.get("guven", 0)
    varlik_tipi = analiz.get("varlik_tipi", "").upper()
    
    # Pozisyon emoji
    if pozisyon == "LONG":
        poz_emoji = "🟢"
        poz_text = "LONG (AL)"
    elif pozisyon == "SHORT":
        poz_emoji = "🔴"
        poz_text = "SHORT (SAT)"
    else:
        poz_emoji = "🟡"
        poz_text = "BEKLE"
    
    # TP yüzdeleri hesapla
    giris_orta = (giris_min + giris_max) / 2
    if giris_orta > 0:
        tp1_yuzde = ((tp1 - giris_orta) / giris_orta) * 100
        tp2_yuzde = ((tp2 - giris_orta) / giris_orta) * 100
        tp3_yuzde = ((tp3 - giris_orta) / giris_orta) * 100
        sl_yuzde = ((stop_loss - giris_orta) / giris_orta) * 100
    else:
        tp1_yuzde = tp2_yuzde = tp3_yuzde = sl_yuzde = 0
    
    # Riskler formatla
    risk_satirlari = "\n".join(f"  • {esc(r)}" for r in riskler[:3])
    
    # HTML oluştur
    html_text = f"""<b>⚡ HIZLI PARA ANALİZİ — {esc(varlik)}</b>
<b>━━━━━━━━━━━━━━━━━━━━</b>

{poz_emoji} <b>POZİSYON:</b> {esc(poz_text)}
📊 <b>VARLIK TİPİ:</b> {esc(varlik_tipi)}

📍 <b>GİRİŞ:</b> ${giris_min:,.2f} - ${giris_max:,.2f}

🎯 <b>KAR AL SEVİYELERİ:</b>
  TP1: ${tp1:,.2f} ({tp1_yuzde:+.1f}%)
  TP2: ${tp2:,.2f} ({tp2_yuzde:+.1f}%)
  TP3: ${tp3:,.2f} ({tp3_yuzde:+.1f}%)

🛑 <b>STOP LOSS:</b> ${stop_loss:,.2f} ({sl_yuzde:+.1f}%)

⏱️ <b>SÜRE:</b> {esc(sure)}
💰 <b>RİSK/ÖDÜL:</b> 1:{risk_odul:.1f}
📊 <b>KALDIRAÇ:</b> Max {kaldirac_max}x (dikkatli!)
🎯 <b>GÜVEN:</b> {guven}/100

<b>🔍 NEDEN?</b>
{esc(neden)}

<b>⚠️ RİSKLER:</b>
{risk_satirlari}

<i>⚠️ Yüksek riskli kısa vadeli işlem. Stop loss MUTLAKA kullan.
Portföyünün max %5'i ile işlem yap. Yatırım tavsiyesi değildir.</i>"""
    
    return html_text
