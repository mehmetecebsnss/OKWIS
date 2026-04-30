"""
Okwis AI - Varlık Tanımlayıcı
Kullanıcı input'unu ticker sembolüne ve ülkeye çevir.

Özellikler:
- Fuzzy matching (benzer isimleri bul)
- Türkçe karakter desteği
- Alternatif isimler
- Ülke tespiti
"""

import json
import logging
from difflib import get_close_matches
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SOZLUK_PATH = Path(__file__).resolve().parent / "data" / "varlik_sozlugu.json"
_SOZLUK_CACHE: Optional[dict] = None


def _sozluk_yukle() -> dict:
    """Varlık sözlüğünü yükle (cache ile)"""
    global _SOZLUK_CACHE
    
    if _SOZLUK_CACHE is not None:
        return _SOZLUK_CACHE
    
    try:
        with open(_SOZLUK_PATH, encoding="utf-8") as f:
            _SOZLUK_CACHE = json.load(f)
            logger.info("Varlık sözlüğü yüklendi: %s varlık", _sozluk_sayisi(_SOZLUK_CACHE))
            return _SOZLUK_CACHE
    except Exception as e:
        logger.error("Varlık sözlüğü yüklenemedi: %s", e)
        return {}


def _sozluk_sayisi(sozluk: dict) -> int:
    """Sözlükteki toplam varlık sayısı"""
    sayi = 0
    for kategori, varliklar in sozluk.items():
        if kategori.startswith("_"):
            continue
        sayi += len(varliklar)
    return sayi


def _turkce_normalize(metin: str) -> str:
    """Türkçe karakterleri normalize et (küçük harf + özel karakter temizleme)"""
    metin = metin.lower().strip()
    # Türkçe karakterler
    tr_map = {
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c",
    }
    for tr_char, en_char in tr_map.items():
        metin = metin.replace(tr_char, en_char)
    return metin


def varlik_tanimla(kullanici_input: str) -> Optional[dict]:
    """
    Kullanıcı input'unu varlık bilgisine çevir.
    
    Args:
        kullanici_input: Kullanıcının yazdığı varlık adı (örn: "Koç Holding", "BTC", "AAPL")
    
    Returns:
        {
            "isim": str,  # Orijinal isim
            "ticker": str,  # Yahoo Finance / yfinance ticker
            "ulke": str,  # TR, US, GLOBAL
            "tip": str,  # hisse, kripto, emtia, forex, endeks
            "kategori": str,  # turkiye_hisseleri, abd_hisseleri, kripto, emtia, forex
            "eslesme_tipi": str,  # tam, alternatif, fuzzy, ticker
        }
        
        None: Varlık bulunamadı
    """
    sozluk = _sozluk_yukle()
    if not sozluk:
        return None
    
    input_lower = kullanici_input.lower().strip()
    input_normalized = _turkce_normalize(kullanici_input)
    
    # 1. TAM EŞLEŞME (ana isim)
    for kategori, varliklar in sozluk.items():
        if kategori.startswith("_"):
            continue
        
        for isim, bilgi in varliklar.items():
            if input_lower == isim.lower() or input_normalized == _turkce_normalize(isim):
                return {
                    "isim": isim,
                    "ticker": bilgi["ticker"],
                    "ulke": bilgi["ulke"],
                    "tip": bilgi["tip"],
                    "kategori": kategori,
                    "eslesme_tipi": "tam",
                }
    
    # 2. ALTERNATİF İSİMLER
    for kategori, varliklar in sozluk.items():
        if kategori.startswith("_"):
            continue
        
        for isim, bilgi in varliklar.items():
            for alt in bilgi.get("alternatifler", []):
                if input_lower == alt.lower() or input_normalized == _turkce_normalize(alt):
                    return {
                        "isim": isim,
                        "ticker": bilgi["ticker"],
                        "ulke": bilgi["ulke"],
                        "tip": bilgi["tip"],
                        "kategori": kategori,
                        "eslesme_tipi": "alternatif",
                    }
    
    # 3. TICKER EŞLEŞME (direkt ticker girilmiş olabilir)
    for kategori, varliklar in sozluk.items():
        if kategori.startswith("_"):
            continue
        
        for isim, bilgi in varliklar.items():
            ticker_base = bilgi["ticker"].split(".")[0].split("-")[0].split("=")[0].upper()
            if input_lower.upper() == ticker_base:
                return {
                    "isim": isim,
                    "ticker": bilgi["ticker"],
                    "ulke": bilgi["ulke"],
                    "tip": bilgi["tip"],
                    "kategori": kategori,
                    "eslesme_tipi": "ticker",
                }
    
    # 4. FUZZY MATCHING (benzer isimler)
    tum_isimler = []
    isim_bilgi_map = {}
    
    for kategori, varliklar in sozluk.items():
        if kategori.startswith("_"):
            continue
        
        for isim, bilgi in varliklar.items():
            tum_isimler.append(isim.lower())
            isim_bilgi_map[isim.lower()] = (isim, bilgi, kategori)
            
            # Alternatifleri de ekle
            for alt in bilgi.get("alternatifler", []):
                tum_isimler.append(alt.lower())
                isim_bilgi_map[alt.lower()] = (isim, bilgi, kategori)
    
    # Fuzzy match (cutoff=0.6 → %60 benzerlik)
    matches = get_close_matches(input_lower, tum_isimler, n=1, cutoff=0.6)
    
    if matches:
        match_key = matches[0]
        isim, bilgi, kategori = isim_bilgi_map[match_key]
        
        logger.info("Fuzzy match: '%s' → '%s' (ticker: %s)", kullanici_input, isim, bilgi["ticker"])
        
        return {
            "isim": isim,
            "ticker": bilgi["ticker"],
            "ulke": bilgi["ulke"],
            "tip": bilgi["tip"],
            "kategori": kategori,
            "eslesme_tipi": "fuzzy",
        }
    
    # 5. BULUNAMADI
    logger.warning("Varlık tanımlanamadı: '%s'", kullanici_input)
    return None


def varlik_ulke_tespit(varlik_bilgi: dict) -> str:
    """
    Varlık bilgisinden ülke tespit et.
    
    Args:
        varlik_bilgi: varlik_tanimla() çıktısı
    
    Returns:
        Ülke kodu (TR, US, JP, CN, vb.) veya "GLOBAL"
    """
    if not varlik_bilgi:
        return "GLOBAL"
    
    ulke = varlik_bilgi.get("ulke", "GLOBAL")
    
    # Ülke kodu → Tam isim
    ulke_map = {
        "TR": "Türkiye",
        "US": "ABD",
        "GLOBAL": "Global",
    }
    
    return ulke_map.get(ulke, ulke)


def varlik_tip_tespit(varlik_bilgi: dict) -> str:
    """
    Varlık bilgisinden tip tespit et.
    
    Args:
        varlik_bilgi: varlik_tanimla() çıktısı
    
    Returns:
        Varlık tipi (hisse, kripto, emtia, forex, endeks)
    """
    if not varlik_bilgi:
        return "unknown"
    
    return varlik_bilgi.get("tip", "unknown")


# ─── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    test_inputs = [
        "Koç Holding",
        "koc holding",
        "KOC",
        "KCHOL",
        "Bitcoin",
        "BTC",
        "Apple",
        "AAPL",
        "Altın",
        "XAUUSD",
        "Garanti Bankası",
        "garanti",
        "Turkcell",
        "THYAO",
        "Ethereum",
        "Petrol",
        "Dolar/TL",
    ]
    
    print("=" * 80)
    print("VARLIK TANIMLAYICI TEST")
    print("=" * 80)
    
    for inp in test_inputs:
        sonuc = varlik_tanimla(inp)
        if sonuc:
            print(f"\n✅ '{inp}' → {sonuc['isim']}")
            print(f"   Ticker: {sonuc['ticker']}")
            print(f"   Ülke: {sonuc['ulke']}")
            print(f"   Tip: {sonuc['tip']}")
            print(f"   Eşleşme: {sonuc['eslesme_tipi']}")
        else:
            print(f"\n❌ '{inp}' → BULUNAMADI")
    
    print("\n" + "=" * 80)
