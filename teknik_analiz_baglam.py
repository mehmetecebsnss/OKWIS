"""
Okwis AI — Teknik Analiz Modu
Grafik desenleri, göstergeler (RSI, MACD, Bollinger Bands, vb.)
"""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# TA-Lib import (opsiyonel, yoksa basit hesaplamalar)
try:
    import talib
    TALIB_VAR = True
except ImportError:
    TALIB_VAR = False
    logger.warning("TA-Lib yüklü değil, basit teknik analiz kullanılacak")

# yfinance import
try:
    import yfinance as yf
    YFINANCE_VAR = True
except ImportError:
    YFINANCE_VAR = False
    logger.error("yfinance yüklü değil, teknik analiz çalışmayacak")


# ─── Varlık Sembol Eşleme ─────────────────────────────────────────────────────

VARLIK_SEMBOL_MAP = {
    # Kripto (yfinance sembolleri)
    "btc": "BTC-USD",
    "bitcoin": "BTC-USD",
    "eth": "ETH-USD",
    "ethereum": "ETH-USD",
    "xrp": "XRP-USD",
    "sol": "SOL-USD",
    "solana": "SOL-USD",
    "ada": "ADA-USD",
    "cardano": "ADA-USD",
    "doge": "DOGE-USD",
    "dogecoin": "DOGE-USD",
    
    # Hisse (doğrudan sembol)
    "aapl": "AAPL",
    "apple": "AAPL",
    "msft": "MSFT",
    "microsoft": "MSFT",
    "googl": "GOOGL",
    "google": "GOOGL",
    "tsla": "TSLA",
    "tesla": "TSLA",
    "amzn": "AMZN",
    "amazon": "AMZN",
    
    # Türk hisseleri
    "thyao": "THYAO.IS",
    "garan": "GARAN.IS",
    "akbnk": "AKBNK.IS",
    
    # Emtia
    "altın": "GC=F",
    "gold": "GC=F",
    "xauusd": "GC=F",
    "petrol": "CL=F",
    "wti": "CL=F",
    "oil": "CL=F",
}


def _sembol_bul(varlik: str) -> Optional[str]:
    """Varlık adından yfinance sembolü bul"""
    varlik_lower = varlik.lower().strip()
    
    # Direkt eşleşme
    if varlik_lower in VARLIK_SEMBOL_MAP:
        return VARLIK_SEMBOL_MAP[varlik_lower]
    
    # Kısmi eşleşme
    for key, sembol in VARLIK_SEMBOL_MAP.items():
        if key in varlik_lower or varlik_lower in key:
            return sembol
    
    # Bulunamadı, varlık adını olduğu gibi dene
    return varlik.upper()


# ─── Fiyat Verisi Alma ────────────────────────────────────────────────────────

def _fiyat_verisi_al(sembol: str, gun: int = 90) -> Optional[Dict]:
    """
    yfinance ile fiyat verisi al.
    
    Returns:
        {
            "close": [fiyat listesi],
            "high": [...],
            "low": [...],
            "volume": [...],
            "dates": [tarih listesi],
        }
    """
    if not YFINANCE_VAR:
        return None
    
    try:
        ticker = yf.Ticker(sembol)
        df = ticker.history(period=f"{gun}d")
        
        if df.empty:
            logger.warning(f"Fiyat verisi bulunamadı: {sembol}")
            return None
        
        return {
            "close": df["Close"].tolist(),
            "high": df["High"].tolist(),
            "low": df["Low"].tolist(),
            "volume": df["Volume"].tolist(),
            "dates": df.index.tolist(),
        }
    except Exception as e:
        logger.error(f"Fiyat verisi alma hatası ({sembol}): {e}")
        return None


# ─── Basit Teknik Göstergeler (TA-Lib yoksa) ──────────────────────────────────

def _basit_rsi(fiyatlar: List[float], period: int = 14) -> Optional[float]:
    """Basit RSI hesaplama"""
    if len(fiyatlar) < period + 1:
        return None
    
    degisimler = [fiyatlar[i] - fiyatlar[i-1] for i in range(1, len(fiyatlar))]
    kazanclar = [max(0, d) for d in degisimler]
    kayiplar = [abs(min(0, d)) for d in degisimler]
    
    ort_kazanc = sum(kazanclar[-period:]) / period
    ort_kayip = sum(kayiplar[-period:]) / period
    
    if ort_kayip == 0:
        return 100
    
    rs = ort_kazanc / ort_kayip
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def _basit_sma(fiyatlar: List[float], period: int) -> Optional[float]:
    """Basit hareketli ortalama"""
    if len(fiyatlar) < period:
        return None
    return sum(fiyatlar[-period:]) / period


# ─── Teknik Analiz Ana Fonksiyon ──────────────────────────────────────────────

def teknik_analiz_yap(varlik: str) -> Optional[Dict]:
    """
    Varlık için teknik analiz yap.
    
    Returns:
        {
            "rsi": float,
            "rsi_sinyal": str,
            "sma_20": float,
            "sma_50": float,
            "trend": str,
            "destek": List[float],
            "direnc": List[float],
            "sinyal": str,  # "bullish", "bearish", "neutral"
            "guc": float,  # 0-10
        }
    """
    # Sembol bul
    sembol = _sembol_bul(varlik)
    if not sembol:
        logger.warning(f"Sembol bulunamadı: {varlik}")
        return None
    
    # Fiyat verisi al
    veri = _fiyat_verisi_al(sembol, gun=90)
    if not veri or not veri["close"]:
        return None
    
    fiyatlar = veri["close"]
    son_fiyat = fiyatlar[-1]
    
    # RSI hesapla
    if TALIB_VAR:
        import numpy as np
        rsi = talib.RSI(np.array(fiyatlar), timeperiod=14)[-1]
    else:
        rsi = _basit_rsi(fiyatlar, period=14)
    
    # RSI sinyali
    if rsi is not None:
        if rsi < 30:
            rsi_sinyal = "oversold"  # Aşırı satım (bullish)
        elif rsi > 70:
            rsi_sinyal = "overbought"  # Aşırı alım (bearish)
        else:
            rsi_sinyal = "neutral"
    else:
        rsi_sinyal = "unknown"
    
    # SMA hesapla
    sma_20 = _basit_sma(fiyatlar, 20)
    sma_50 = _basit_sma(fiyatlar, 50)
    
    # Trend belirleme
    if sma_20 and sma_50:
        if sma_20 > sma_50 and son_fiyat > sma_20:
            trend = "uptrend"
            trend_guc = 7.5
        elif sma_20 < sma_50 and son_fiyat < sma_20:
            trend = "downtrend"
            trend_guc = 7.5
        else:
            trend = "sideways"
            trend_guc = 5.0
    else:
        trend = "unknown"
        trend_guc = 5.0
    
    # Destek ve direnç (basit: son 30 günün min/max'ı)
    son_30_gun = fiyatlar[-30:] if len(fiyatlar) >= 30 else fiyatlar
    destek = [min(son_30_gun)]
    direnc = [max(son_30_gun)]
    
    # Genel sinyal
    sinyal_puanlari = []
    
    # RSI sinyali
    if rsi_sinyal == "oversold":
        sinyal_puanlari.append(("bullish", 7.0))
    elif rsi_sinyal == "overbought":
        sinyal_puanlari.append(("bearish", 7.0))
    else:
        sinyal_puanlari.append(("neutral", 5.0))
    
    # Trend sinyali
    if trend == "uptrend":
        sinyal_puanlari.append(("bullish", trend_guc))
    elif trend == "downtrend":
        sinyal_puanlari.append(("bearish", trend_guc))
    else:
        sinyal_puanlari.append(("neutral", 5.0))
    
    # Ortalama sinyal
    bullish_puan = sum(p for s, p in sinyal_puanlari if s == "bullish")
    bearish_puan = sum(p for s, p in sinyal_puanlari if s == "bearish")
    neutral_puan = sum(p for s, p in sinyal_puanlari if s == "neutral")
    
    if bullish_puan > bearish_puan and bullish_puan > neutral_puan:
        genel_sinyal = "bullish"
        guc = bullish_puan / len(sinyal_puanlari)
    elif bearish_puan > bullish_puan and bearish_puan > neutral_puan:
        genel_sinyal = "bearish"
        guc = bearish_puan / len(sinyal_puanlari)
    else:
        genel_sinyal = "neutral"
        guc = 5.0
    
    return {
        "rsi": rsi,
        "rsi_sinyal": rsi_sinyal,
        "sma_20": sma_20,
        "sma_50": sma_50,
        "trend": trend,
        "destek": destek,
        "direnc": direnc,
        "sinyal": genel_sinyal,
        "guc": guc,
        "son_fiyat": son_fiyat,
    }


# ─── Bağlam Metni Oluşturma ───────────────────────────────────────────────────

def topla_teknik_analiz_baglami(varlik: str) -> str:
    """
    Teknik analiz bağlam metni oluştur.
    
    Args:
        varlik: Varlık adı (BTC, AAPL, vb.)
    
    Returns:
        Bağlam metni
    """
    analiz = teknik_analiz_yap(varlik)
    
    if not analiz:
        return "Teknik analiz verisi alınamadı."
    
    rsi = analiz.get("rsi")
    rsi_sinyal = analiz.get("rsi_sinyal", "unknown")
    sma_20 = analiz.get("sma_20")
    sma_50 = analiz.get("sma_50")
    trend = analiz.get("trend", "unknown")
    destek = analiz.get("destek", [])
    direnc = analiz.get("direnc", [])
    sinyal = analiz.get("sinyal", "neutral")
    guc = analiz.get("guc", 5.0)
    son_fiyat = analiz.get("son_fiyat", 0)
    
    # RSI açıklama
    if rsi_sinyal == "oversold":
        rsi_aciklama = "Aşırı satım bölgesinde, potansiyel sıçrama"
    elif rsi_sinyal == "overbought":
        rsi_aciklama = "Aşırı alım bölgesinde, potansiyel düzeltme"
    else:
        rsi_aciklama = "Normal bölgede"
    
    # Trend açıklama
    if trend == "uptrend":
        trend_aciklama = "Yükseliş trendi (SMA 20 > SMA 50)"
    elif trend == "downtrend":
        trend_aciklama = "Düşüş trendi (SMA 20 < SMA 50)"
    else:
        trend_aciklama = "Yatay hareket"
    
    # Sinyal açıklama
    if sinyal == "bullish":
        sinyal_aciklama = "BULLISH (Alım sinyali)"
    elif sinyal == "bearish":
        sinyal_aciklama = "BEARISH (Satım sinyali)"
    else:
        sinyal_aciklama = "NEUTRAL (Bekle)"
    
    baglam = f"""
TEKNİK ANALİZ — {varlik.upper()}

Son Fiyat: ${son_fiyat:,.2f}

RSI (14): {f'{rsi:.1f}' if rsi else 'N/A'} — {rsi_aciklama}
SMA 20: {f'${sma_20:,.2f}' if sma_20 else 'N/A'}
SMA 50: {f'${sma_50:,.2f}' if sma_50 else 'N/A'}

Trend: {trend_aciklama}
Destek: {f'${destek[0]:,.2f}' if destek else 'N/A'}
Direnç: {f'${direnc[0]:,.2f}' if direnc else 'N/A'}

Teknik Sinyal: {sinyal_aciklama}
Sinyal Gücü: {guc:.1f}/10
"""
    
    return baglam.strip()


# ─── Test ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("TEKNİK ANALİZ MODU TEST")
    print("=" * 50)
    
    test_varliklari = ["BTC", "AAPL", "THYAO"]
    
    for varlik in test_varliklari:
        print(f"\n{varlik}:")
        print("-" * 50)
        baglam = topla_teknik_analiz_baglami(varlik)
        print(baglam)
