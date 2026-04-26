"""
Okwis AI — Fiyat Servisi
Kripto, hisse, forex ve emtia için gerçek zamanlı fiyat verisi.

Kaynaklar:
  - Kripto: CoinGecko API (ücretsiz, API key gerekmez)
  - Hisse / Forex / Emtia: yfinance (Yahoo Finance, ücretsiz)

Grafik: matplotlib ile 30 günlük fiyat hareketi
"""

from __future__ import annotations

import io
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Sembol Eşleme Tabloları ──────────────────────────────────────────────────

# Türkçe isim → CoinGecko ID
KRIPTO_ISIMLER: dict[str, str] = {
    # Büyük coinler
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "binance coin": "binancecoin", "bnb": "binancecoin",
    "solana": "solana", "sol": "solana",
    "xrp": "ripple", "ripple": "ripple",
    "cardano": "cardano", "ada": "cardano",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "polkadot": "polkadot", "dot": "polkadot",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "shiba inu": "shiba-inu", "shib": "shiba-inu",
    "polygon": "matic-network", "matic": "matic-network",
    "chainlink": "chainlink", "link": "chainlink",
    "litecoin": "litecoin", "ltc": "litecoin",
    "tron": "tron", "trx": "tron",
    "uniswap": "uniswap", "uni": "uniswap",
    "stellar": "stellar", "xlm": "stellar",
    "monero": "monero", "xmr": "monero",
    "ton": "the-open-network", "toncoin": "the-open-network",
    "pepe": "pepe", "floki": "floki",
    "sui": "sui", "aptos": "aptos",
    "near": "near", "near protocol": "near",
    "internet computer": "internet-computer", "icp": "internet-computer",
    "filecoin": "filecoin", "fil": "filecoin",
    "aave": "aave", "maker": "maker", "mkr": "maker",
    "injective": "injective-protocol", "inj": "injective-protocol",
    "arbitrum": "arbitrum", "arb": "arbitrum",
    "optimism": "optimism", "op": "optimism",
}

# Türkçe isim → Yahoo Finance sembolü
HISSE_ISIMLER: dict[str, str] = {
    # Türk hisseleri (BIST)
    "thyao": "THYAO.IS", "türk hava yolları": "THYAO.IS", "thy": "THYAO.IS",
    "garan": "GARAN.IS", "garanti": "GARAN.IS", "garanti bankası": "GARAN.IS",
    "akbnk": "AKBNK.IS", "akbank": "AKBNK.IS",
    "isctr": "ISCTR.IS", "iş bankası": "ISCTR.IS",
    "eregl": "EREGL.IS", "ereğli": "EREGL.IS", "erdemir": "EREGL.IS",
    "kchol": "KCHOL.IS", "koç holding": "KCHOL.IS",
    "sahol": "SAHOL.IS", "sabancı": "SAHOL.IS",
    "sise": "SISE.IS", "şişecam": "SISE.IS",
    "bimas": "BIMAS.IS", "bim": "BIMAS.IS",
    "asels": "ASELS.IS", "aselsan": "ASELS.IS",
    "tuprs": "TUPRS.IS", "tüpraş": "TUPRS.IS",
    "froto": "FROTO.IS", "ford otosan": "FROTO.IS",
    "toaso": "TOASO.IS", "tofaş": "TOASO.IS",
    "pgsus": "PGSUS.IS", "pegasus": "PGSUS.IS",
    "tavhl": "TAVHL.IS", "tav havalimanları": "TAVHL.IS",
    "ekgyo": "EKGYO.IS", "emlak konut": "EKGYO.IS",
    "vestl": "VESTL.IS", "vestel": "VESTL.IS",
    "tcell": "TCELL.IS", "turkcell": "TCELL.IS",
    "ttkom": "TTKOM.IS", "türk telekom": "TTKOM.IS",
    "halkb": "HALKB.IS", "halkbank": "HALKB.IS",
    "vakbn": "VAKBN.IS", "vakıfbank": "VAKBN.IS",
    "ykbnk": "YKBNK.IS", "yapı kredi": "YKBNK.IS",
    "xu100": "XU100.IS", "bist 100": "XU100.IS", "bist100": "XU100.IS",
    # ABD hisseleri
    "apple": "AAPL", "aapl": "AAPL",
    "microsoft": "MSFT", "msft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL",
    "amazon": "AMZN", "amzn": "AMZN",
    "nvidia": "NVDA", "nvda": "NVDA",
    "tesla": "TSLA", "tsla": "TSLA",
    "meta": "META", "facebook": "META",
    "netflix": "NFLX", "nflx": "NFLX",
    "sp500": "^GSPC", "s&p 500": "^GSPC", "s&p500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow jones": "^DJI", "dow": "^DJI",
    # Emtia
    "altın": "GC=F", "gold": "GC=F", "xau": "GC=F",
    "gümüş": "SI=F", "silver": "SI=F", "xag": "SI=F",
    "petrol": "CL=F", "wti": "CL=F", "crude oil": "CL=F",
    "brent": "BZ=F", "brent petrol": "BZ=F",
    "doğalgaz": "NG=F", "natural gas": "NG=F",
    "bakır": "HG=F", "copper": "HG=F",
    "buğday": "ZW=F", "wheat": "ZW=F",
    "mısır": "ZC=F", "corn": "ZC=F",
    # Forex
    "dolar": "USDTRY=X", "usd/try": "USDTRY=X", "dolar/tl": "USDTRY=X",
    "euro": "EURTRY=X", "eur/try": "EURTRY=X", "euro/tl": "EURTRY=X",
    "sterlin": "GBPTRY=X", "gbp/try": "GBPTRY=X",
    "eur/usd": "EURUSD=X", "eurusd": "EURUSD=X",
    "gbp/usd": "GBPUSD=X", "gbpusd": "GBPUSD=X",
    "usd/jpy": "USDJPY=X", "usdjpy": "USDJPY=X",
    "usd/chf": "USDCHF=X",
}

# ─── Önbellek (60 saniye TTL) ─────────────────────────────────────────────────
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 60  # saniye


def _cache_al(anahtar: str) -> Optional[dict]:
    if anahtar in _CACHE:
        ts, veri = _CACHE[anahtar]
        if time.time() - ts < _CACHE_TTL:
            return veri
    return None


def _cache_kaydet(anahtar: str, veri: dict) -> None:
    _CACHE[anahtar] = (time.time(), veri)


# ─── Sembol Tespiti ───────────────────────────────────────────────────────────

def sembol_tespit(metin: str) -> Optional[tuple[str, str]]:
    """
    Metinden varlık sembolü tespit et.
    Döner: (tip, sembol/id) veya None
    tip: 'kripto' | 'hisse'
    """
    temiz = metin.lower().strip()
    # Kripto kontrolü
    for isim, cg_id in KRIPTO_ISIMLER.items():
        if isim in temiz:
            return ("kripto", cg_id)
    # Hisse/forex/emtia kontrolü
    for isim, yf_sembol in HISSE_ISIMLER.items():
        if isim in temiz:
            return ("hisse", yf_sembol)
    return None


def fiyat_sorusu_mu(metin: str) -> bool:
    """Mesaj bir fiyat sorusu mu?"""
    anahtar_kelimeler = [
        "fiyat", "kaç", "kaç dolar", "kaç tl", "ne kadar",
        "fiyatı", "fiyatı nedir", "fiyatı ne", "değeri",
        "değeri nedir", "değeri ne kadar", "kac", "kac dolar",
        "nerede işlem", "seviyesi", "seviyesi nedir",
        "grafik", "chart", "analiz et", "durum nedir",
        "son fiyat", "güncel fiyat", "anlık fiyat",
        "yüksek", "düşük", "high", "low",
    ]
    temiz = metin.lower()
    # Anahtar kelime var mı?
    kelime_var = any(k in temiz for k in anahtar_kelimeler)
    # Bilinen bir varlık adı var mı?
    varlik_var = sembol_tespit(metin) is not None
    return kelime_var and varlik_var


# ─── CoinGecko — Kripto Fiyat ─────────────────────────────────────────────────

def kripto_fiyat_al(cg_id: str) -> Optional[dict]:
    """CoinGecko'dan anlık fiyat + 24s istatistik al."""
    cache_key = f"kripto_{cg_id}"
    cached = _cache_al(cache_key)
    if cached:
        return cached

    try:
        import urllib.request
        import json as _json

        url = (
            f"https://api.coingecko.com/api/v3/coins/{cg_id}"
            "?localization=false&tickers=false&community_data=false&developer_data=false"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "OkwisBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())

        md = data.get("market_data", {})
        sonuc = {
            "isim": data.get("name", cg_id),
            "sembol": data.get("symbol", "").upper(),
            "fiyat_usd": md.get("current_price", {}).get("usd"),
            "fiyat_try": md.get("current_price", {}).get("try"),
            "yuksek_24s": md.get("high_24h", {}).get("usd"),
            "dusuk_24s": md.get("low_24h", {}).get("usd"),
            "degisim_24s": md.get("price_change_percentage_24h"),
            "degisim_7g": md.get("price_change_percentage_7d"),
            "piyasa_deger": md.get("market_cap", {}).get("usd"),
            "hacim_24s": md.get("total_volume", {}).get("usd"),
            "tip": "kripto",
        }
        _cache_kaydet(cache_key, sonuc)
        return sonuc
    except Exception as e:
        logger.warning("CoinGecko fiyat hatası (%s): %s", cg_id, e)
        return None


def kripto_gecmis_al(cg_id: str, gun: int = 30) -> Optional[list[tuple[datetime, float]]]:
    """CoinGecko'dan geçmiş fiyat verisi al (günlük)."""
    cache_key = f"kripto_gecmis_{cg_id}_{gun}"
    cached = _cache_al(cache_key)
    if cached:
        return cached

    try:
        import urllib.request
        import json as _json

        url = (
            f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
            f"?vs_currency=usd&days={gun}&interval=daily"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "OkwisBot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())

        fiyatlar = [
            (datetime.fromtimestamp(p[0] / 1000), p[1])
            for p in data.get("prices", [])
        ]
        _cache_kaydet(cache_key, fiyatlar)
        return fiyatlar
    except Exception as e:
        logger.warning("CoinGecko geçmiş hatası (%s): %s", cg_id, e)
        return None


# ─── Yahoo Finance — Hisse / Forex / Emtia ────────────────────────────────────

def hisse_fiyat_al(yf_sembol: str) -> Optional[dict]:
    """yfinance ile anlık fiyat + istatistik al."""
    cache_key = f"hisse_{yf_sembol}"
    cached = _cache_al(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf

        ticker = yf.Ticker(yf_sembol)
        info = ticker.fast_info

        # fast_info'dan temel veriler
        fiyat = getattr(info, "last_price", None)
        yuksek = getattr(info, "day_high", None)
        dusuk = getattr(info, "day_low", None)
        onceki_kapanis = getattr(info, "previous_close", None)
        para_birimi = getattr(info, "currency", "USD")

        if fiyat is None:
            # Fallback: history
            hist = ticker.history(period="2d")
            if not hist.empty:
                fiyat = float(hist["Close"].iloc[-1])
                yuksek = float(hist["High"].iloc[-1])
                dusuk = float(hist["Low"].iloc[-1])
                onceki_kapanis = float(hist["Close"].iloc[-2]) if len(hist) > 1 else fiyat

        degisim_yuzde = None
        if fiyat and onceki_kapanis and onceki_kapanis > 0:
            degisim_yuzde = ((fiyat - onceki_kapanis) / onceki_kapanis) * 100

        # İsim tespiti
        isim = yf_sembol
        try:
            isim = ticker.info.get("longName") or ticker.info.get("shortName") or yf_sembol
        except Exception:
            pass

        sonuc = {
            "isim": isim,
            "sembol": yf_sembol,
            "fiyat": fiyat,
            "yuksek_gun": yuksek,
            "dusuk_gun": dusuk,
            "onceki_kapanis": onceki_kapanis,
            "degisim_yuzde": degisim_yuzde,
            "para_birimi": para_birimi,
            "tip": "hisse",
        }
        _cache_kaydet(cache_key, sonuc)
        return sonuc
    except ImportError:
        logger.warning("yfinance kurulu değil")
        return None
    except Exception as e:
        logger.warning("yfinance fiyat hatası (%s): %s", yf_sembol, e)
        return None


def hisse_gecmis_al(yf_sembol: str, gun: int = 30) -> Optional[list[tuple[datetime, float]]]:
    """yfinance ile geçmiş fiyat verisi al."""
    cache_key = f"hisse_gecmis_{yf_sembol}_{gun}"
    cached = _cache_al(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf

        period = f"{gun}d"
        ticker = yf.Ticker(yf_sembol)
        hist = ticker.history(period=period)

        if hist.empty:
            return None

        fiyatlar = [
            (dt.to_pydatetime(), float(kapani))
            for dt, kapani in zip(hist.index, hist["Close"])
        ]
        _cache_kaydet(cache_key, fiyatlar)
        return fiyatlar
    except ImportError:
        logger.warning("yfinance kurulu değil")
        return None
    except Exception as e:
        logger.warning("yfinance geçmiş hatası (%s): %s", yf_sembol, e)
        return None


# ─── Grafik Oluşturucu ────────────────────────────────────────────────────────

def fiyat_grafigi_olustur(
    isim: str,
    sembol: str,
    fiyatlar: list[tuple[datetime, float]],
    para_birimi: str = "USD",
    guncel_fiyat: Optional[float] = None,
) -> Optional[bytes]:
    """30 günlük fiyat grafiği oluştur, PNG bytes döndür."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import numpy as np

        if not fiyatlar or len(fiyatlar) < 2:
            return None

        tarihler = [f[0] for f in fiyatlar]
        degerler = [f[1] for f in fiyatlar]

        # Renk: yükselen yeşil, düşen kırmızı
        renk = "#2ECC71" if degerler[-1] >= degerler[0] else "#E74C3C"
        zemin = "#0D0D0D"
        izgara = "#2A2A2A"
        metin_renk = "#F0EDE8"
        altin = "#C9A84C"

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor(zemin)
        ax.set_facecolor(zemin)

        # Alan grafiği
        ax.fill_between(tarihler, degerler, alpha=0.15, color=renk)
        ax.plot(tarihler, degerler, color=renk, linewidth=2, zorder=3)

        # Güncel fiyat yatay çizgisi
        if guncel_fiyat:
            ax.axhline(y=guncel_fiyat, color=altin, linewidth=0.8,
                       linestyle="--", alpha=0.7, zorder=2)

        # Min/Max noktaları
        min_idx = int(np.argmin(degerler))
        max_idx = int(np.argmax(degerler))
        ax.scatter([tarihler[min_idx]], [degerler[min_idx]],
                   color="#E74C3C", s=60, zorder=5)
        ax.scatter([tarihler[max_idx]], [degerler[max_idx]],
                   color="#2ECC71", s=60, zorder=5)

        # Eksen formatı
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.xticks(rotation=30, color=metin_renk, fontsize=9)
        plt.yticks(color=metin_renk, fontsize=9)

        # Izgara
        ax.grid(True, color=izgara, linewidth=0.5, alpha=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(izgara)
        ax.spines["bottom"].set_color(izgara)

        # Başlık
        degisim = ((degerler[-1] - degerler[0]) / degerler[0]) * 100
        isaret = "▲" if degisim >= 0 else "▼"
        baslik = f"◆ {isim} ({sembol})  {isaret} {abs(degisim):.1f}%  — 30 Günlük"
        ax.set_title(baslik, color=altin, fontsize=12, fontweight="bold", pad=12)

        # Para birimi etiketi
        ax.set_ylabel(para_birimi, color=metin_renk, fontsize=9)

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                    facecolor=zemin)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except ImportError:
        logger.warning("matplotlib kurulu değil, grafik oluşturulamadı")
        return None
    except Exception as e:
        logger.warning("Grafik oluşturma hatası: %s", e)
        return None


# ─── Ana Fiyat Sorgulama Fonksiyonu ──────────────────────────────────────────

def fiyat_sorgula(metin: str) -> Optional[dict]:
    """
    Metinden varlık tespit et, fiyat ve geçmiş veri çek.
    Döner: {
        'bilgi': dict,          # anlık fiyat bilgisi
        'gecmis': list,         # (datetime, float) listesi
        'grafik': bytes|None,   # PNG grafik
        'mesaj': str,           # Telegram'a gönderilecek metin
    }
    """
    tespit = sembol_tespit(metin)
    if not tespit:
        return None

    tip, sembol = tespit

    if tip == "kripto":
        bilgi = kripto_fiyat_al(sembol)
        if not bilgi:
            return None
        gecmis = kripto_gecmis_al(sembol, gun=30)
        para_birimi = "USD"
        fiyat_goster = bilgi.get("fiyat_usd")
        fiyat_try = bilgi.get("fiyat_try")
        yuksek = bilgi.get("yuksek_24s")
        dusuk = bilgi.get("dusuk_24s")
        degisim = bilgi.get("degisim_24s")
        degisim_7g = bilgi.get("degisim_7g")
        isim = bilgi.get("isim", sembol)
        sembol_goster = bilgi.get("sembol", sembol.upper())

    else:  # hisse / forex / emtia
        bilgi = hisse_fiyat_al(sembol)
        if not bilgi:
            return None
        gecmis = hisse_gecmis_al(sembol, gun=30)
        para_birimi = bilgi.get("para_birimi", "USD")
        fiyat_goster = bilgi.get("fiyat")
        fiyat_try = None
        yuksek = bilgi.get("yuksek_gun")
        dusuk = bilgi.get("dusuk_gun")
        degisim = bilgi.get("degisim_yuzde")
        degisim_7g = None
        isim = bilgi.get("isim", sembol)
        sembol_goster = sembol

    if fiyat_goster is None:
        return None

    # Grafik oluştur
    grafik = None
    if gecmis:
        grafik = fiyat_grafigi_olustur(
            isim=isim,
            sembol=sembol_goster,
            fiyatlar=gecmis,
            para_birimi=para_birimi,
            guncel_fiyat=fiyat_goster,
        )

    # Mesaj oluştur
    def _fmt(sayi, ondalik=2):
        if sayi is None:
            return "—"
        if sayi >= 1_000_000:
            return f"${sayi/1_000_000:.2f}M"
        if sayi >= 1_000:
            return f"{sayi:,.{ondalik}f}"
        return f"{sayi:.{ondalik}f}"

    def _degisim_satiri(pct, etiket="24s"):
        if pct is None:
            return ""
        isaret = "▲" if pct >= 0 else "▼"
        renk_emoji = "🟢" if pct >= 0 else "🔴"
        return f"{renk_emoji} {etiket}: {isaret} {abs(pct):.2f}%\n"

    fiyat_str = _fmt(fiyat_goster)
    try_str = f"  (~₺{_fmt(fiyat_try, 0)})" if fiyat_try else ""

    mesaj = (
        f"◆ <b>{isim}</b>  <code>{sembol_goster}</code>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"💰 <b>Fiyat:</b> <b>${fiyat_str}</b>{try_str}\n\n"
        f"📈 <b>Gün İçi Yüksek:</b> ${_fmt(yuksek)}\n"
        f"📉 <b>Gün İçi Düşük:</b> ${_fmt(dusuk)}\n\n"
        f"{_degisim_satiri(degisim, '24 Saat')}"
        f"{_degisim_satiri(degisim_7g, '7 Gün') if degisim_7g is not None else ''}"
        f"\n<i>Kaynak: {'CoinGecko' if tip == 'kripto' else 'Yahoo Finance'} · "
        f"{datetime.now().strftime('%H:%M')}</i>"
    )

    return {
        "bilgi": bilgi,
        "gecmis": gecmis,
        "grafik": grafik,
        "mesaj": mesaj,
        "isim": isim,
        "sembol": sembol_goster,
    }
