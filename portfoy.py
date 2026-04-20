"""
Okwis AI — Portföy Yönetim Sistemi
Kullanıcıların varlıklarını yapılandırılmış şekilde saklar ve analiz entegrasyonu sağlar.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PORTFOY_PATH = Path(__file__).resolve().parent / "metrics" / "portfoy.json"

# Desteklenen varlık kategorileri
VARLIK_KATEGORILERI = {
    "kripto": ["btc", "bitcoin", "eth", "ethereum", "bnb", "sol", "solana", "avax",
               "ada", "cardano", "doge", "xrp", "ripple", "dot", "polkadot",
               "link", "chainlink", "matic", "polygon", "ltc", "litecoin"],
    "emtia": ["altin", "altın", "gold", "xau", "gumus", "gümüş", "silver", "xag",
              "petrol", "oil", "wti", "brent", "dogalgaz", "doğalgaz", "gas",
              "bakir", "bakır", "copper", "nikel", "nickel", "platinyum", "platinum"],
    "hisse": ["aapl", "apple", "msft", "microsoft", "tsla", "tesla", "nvda", "nvidia",
              "amzn", "amazon", "googl", "google", "meta", "bist", "thyao", "garan",
              "akbnk", "eregl", "kchol", "sahol", "sise", "tuprs"],
    "doviz": ["dolar", "dollar", "usd", "euro", "eur", "sterlin", "gbp", "yen", "jpy",
              "chf", "frank", "try", "tl", "lira"],
    "diger": [],
}


def _varlik_kategori_tespit(sembol: str) -> str:
    """Varlık sembolünden kategori tespit et."""
    s = sembol.lower().strip()
    for kategori, liste in VARLIK_KATEGORILERI.items():
        if any(k in s for k in liste):
            return kategori
    return "diger"


def _portfoy_yukle() -> dict[str, dict]:
    """Tüm kullanıcı portföylerini yükle."""
    if not _PORTFOY_PATH.exists():
        return {}
    try:
        with open(_PORTFOY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("Portföy dosyası okunamadı: %s", e)
    return {}


def _portfoy_kaydet(data: dict) -> None:
    """Portföy verisini kaydet."""
    try:
        _PORTFOY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_PORTFOY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Portföy dosyası yazılamadı: %s", e)


def kullanici_portfoy_al(user_id: int | str) -> dict:
    """
    Kullanıcının portföyünü döndür.

    Returns:
        {
            "varliklar": [
                {
                    "sembol": "BTC",
                    "ad": "Bitcoin",
                    "miktar": 0.5,
                    "maliyet": 45000.0,   # opsiyonel, USD
                    "kategori": "kripto",
                    "eklendi": "2026-04-20T10:00:00Z"
                },
                ...
            ],
            "risk_profili": "orta",   # agresif / orta / muhafazakar
            "yatirim_ufku": "orta_vade",  # kisa_vade / orta_vade / uzun_vade
            "hedef": "",
            "guncelleme": "2026-04-20T10:00:00Z"
        }
    """
    data = _portfoy_yukle()
    uid = str(user_id)
    if uid not in data:
        return {"varliklar": [], "risk_profili": "", "yatirim_ufku": "", "hedef": "", "guncelleme": ""}
    return data[uid]


def kullanici_portfoy_kaydet(user_id: int | str, portfoy: dict) -> None:
    """Kullanıcının portföyünü kaydet."""
    data = _portfoy_yukle()
    portfoy["guncelleme"] = datetime.now(timezone.utc).isoformat()
    data[str(user_id)] = portfoy
    _portfoy_kaydet(data)


def varlik_ekle(
    user_id: int | str,
    sembol: str,
    miktar: float,
    maliyet: Optional[float] = None,
    ad: Optional[str] = None,
) -> dict:
    """
    Portföye varlık ekle veya güncelle.

    Returns:
        Güncellenmiş portföy
    """
    portfoy = kullanici_portfoy_al(user_id)
    varliklar = portfoy.get("varliklar", [])

    sembol_temiz = sembol.upper().strip()
    kategori = _varlik_kategori_tespit(sembol)

    # Mevcut varlığı bul
    mevcut_idx = None
    for i, v in enumerate(varliklar):
        if v.get("sembol", "").upper() == sembol_temiz:
            mevcut_idx = i
            break

    varlik = {
        "sembol": sembol_temiz,
        "ad": ad or sembol_temiz,
        "miktar": miktar,
        "kategori": kategori,
        "eklendi": datetime.now(timezone.utc).isoformat(),
    }
    if maliyet is not None:
        varlik["maliyet"] = maliyet

    if mevcut_idx is not None:
        varliklar[mevcut_idx] = varlik
    else:
        varliklar.append(varlik)

    portfoy["varliklar"] = varliklar
    kullanici_portfoy_kaydet(user_id, portfoy)
    return portfoy


def varlik_cikar(user_id: int | str, sembol: str) -> tuple[bool, dict]:
    """
    Portföyden varlık çıkar.

    Returns:
        (başarılı_mı, güncellenmiş_portföy)
    """
    portfoy = kullanici_portfoy_al(user_id)
    varliklar = portfoy.get("varliklar", [])
    sembol_temiz = sembol.upper().strip()

    yeni_varliklar = [v for v in varliklar if v.get("sembol", "").upper() != sembol_temiz]

    if len(yeni_varliklar) == len(varliklar):
        return False, portfoy  # Bulunamadı

    portfoy["varliklar"] = yeni_varliklar
    kullanici_portfoy_kaydet(user_id, portfoy)
    return True, portfoy


def portfoy_sil(user_id: int | str) -> bool:
    """Kullanıcının tüm portföyünü sil."""
    data = _portfoy_yukle()
    uid = str(user_id)
    if uid in data:
        del data[uid]
        _portfoy_kaydet(data)
        return True
    return False


def risk_profili_guncelle(user_id: int | str, risk: str) -> None:
    """Risk profilini güncelle: agresif / orta / muhafazakar"""
    portfoy = kullanici_portfoy_al(user_id)
    portfoy["risk_profili"] = risk
    kullanici_portfoy_kaydet(user_id, portfoy)


def yatirim_ufku_guncelle(user_id: int | str, ufuk: str) -> None:
    """Yatırım ufkunu güncelle: kisa_vade / orta_vade / uzun_vade"""
    portfoy = kullanici_portfoy_al(user_id)
    portfoy["yatirim_ufku"] = ufuk
    kullanici_portfoy_kaydet(user_id, portfoy)


def hedef_guncelle(user_id: int | str, hedef: str) -> None:
    """Yatırım hedefini güncelle."""
    portfoy = kullanici_portfoy_al(user_id)
    portfoy["hedef"] = hedef
    kullanici_portfoy_kaydet(user_id, portfoy)


def portfoy_analiz_blogu(user_id: int | str) -> str:
    """
    Analiz prompt'una eklenecek portföy bloğunu üret.
    Portföy yoksa boş string döner.
    """
    portfoy = kullanici_portfoy_al(user_id)
    varliklar = portfoy.get("varliklar", [])

    if not varliklar:
        return ""

    satirlar = [
        "### Kullanıcı Portföyü (KİŞİSELLEŞTİRME — bu portföye göre analizi özelleştir)",
        "",
    ]

    # Varlıkları kategoriye göre grupla
    kategoriler: dict[str, list] = {}
    for v in varliklar:
        kat = v.get("kategori", "diger")
        kategoriler.setdefault(kat, []).append(v)

    for kat, liste in kategoriler.items():
        kat_adi = {
            "kripto": "Kripto",
            "emtia": "Emtia",
            "hisse": "Hisse",
            "doviz": "Döviz",
            "diger": "Diğer",
        }.get(kat, kat.capitalize())
        satirlar.append(f"[{kat_adi}]")
        for v in liste:
            satir = f"  - {v['sembol']}"
            if v.get("ad") and v["ad"] != v["sembol"]:
                satir += f" ({v['ad']})"
            satir += f": {v['miktar']}"
            if v.get("maliyet"):
                satir += f" @ {v['maliyet']} USD maliyet"
            satirlar.append(satir)
        satirlar.append("")

    # Risk profili ve ufuk
    risk = portfoy.get("risk_profili", "")
    ufuk = portfoy.get("yatirim_ufku", "")
    hedef = portfoy.get("hedef", "")

    if risk:
        risk_adi = {"agresif": "Agresif", "orta": "Orta", "muhafazakar": "Muhafazakar"}.get(risk, risk)
        satirlar.append(f"Risk Profili: {risk_adi}")
    if ufuk:
        ufuk_adi = {"kisa_vade": "Kısa Vade (0-3 ay)", "orta_vade": "Orta Vade (3-12 ay)", "uzun_vade": "Uzun Vade (1+ yıl)"}.get(ufuk, ufuk)
        satirlar.append(f"Yatırım Ufku: {ufuk_adi}")
    if hedef:
        satirlar.append(f"Hedef: {hedef}")

    satirlar.append("")
    satirlar.append("ÖNEMLI: Yukarıdaki portföy bilgilerini kullanarak analizi tamamen bu kişiye özelleştir.")
    satirlar.append("- Portföydeki her varlık için ayrı değerlendirme yap.")
    satirlar.append("- 'Senin BTC'in', 'portföyündeki altın' gibi sahiplenme dili kullan.")
    satirlar.append("- Risk profiline uygun aksiyon öner (agresif → daha büyük pozisyon, muhafazakar → küçük pozisyon).")
    satirlar.append("- Yatırım ufkuna göre kısa/orta/uzun vade önerilerini ağırlıklandır.")
    satirlar.append("- Portföydeki varlıklar arasındaki korelasyonu ve çeşitlendirmeyi değerlendir.")

    return "\n".join(satirlar)


def portfoy_ozet_metni(user_id: int | str) -> str:
    """
    Telegram'da gösterilecek portföy özet metni (HTML).
    """
    portfoy = kullanici_portfoy_al(user_id)
    varliklar = portfoy.get("varliklar", [])

    if not varliklar:
        return (
            "<b>◆ Portföyün Boş</b>\n\n"
            "Henüz varlık eklemedin.\n"
            "Eklemek için: <code>/portfoy ekle BTC 0.5</code>\n"
            "Yardım için: <code>/portfoy</code>"
        )

    satirlar = [
        "<b>◆ Portföyün</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "",
    ]

    # Kategoriye göre grupla
    kategoriler: dict[str, list] = {}
    for v in varliklar:
        kat = v.get("kategori", "diger")
        kategoriler.setdefault(kat, []).append(v)

    kat_ikonlari = {
        "kripto": "◈",
        "emtia": "◆",
        "hisse": "◇",
        "doviz": "◉",
        "diger": "○",
    }

    for kat, liste in kategoriler.items():
        ikon = kat_ikonlari.get(kat, "○")
        kat_adi = {
            "kripto": "Kripto",
            "emtia": "Emtia",
            "hisse": "Hisse",
            "doviz": "Döviz",
            "diger": "Diğer",
        }.get(kat, kat.capitalize())
        satirlar.append(f"<b>{ikon} {kat_adi}</b>")
        for v in liste:
            satir = f"  {v['sembol']}"
            if v.get("ad") and v["ad"] != v["sembol"]:
                satir += f" ({v['ad']})"
            satir += f"  <b>{v['miktar']}</b>"
            if v.get("maliyet"):
                satir += f"  <i>@ {v['maliyet']} USD</i>"
            satirlar.append(satir)
        satirlar.append("")

    # Risk ve ufuk
    risk = portfoy.get("risk_profili", "")
    ufuk = portfoy.get("yatirim_ufku", "")
    hedef = portfoy.get("hedef", "")

    if risk or ufuk or hedef:
        satirlar.append("<b>◆ Profil</b>")
        if risk:
            risk_adi = {"agresif": "Agresif", "orta": "Orta", "muhafazakar": "Muhafazakar"}.get(risk, risk)
            satirlar.append(f"  Risk: {risk_adi}")
        if ufuk:
            ufuk_adi = {"kisa_vade": "Kısa Vade", "orta_vade": "Orta Vade", "uzun_vade": "Uzun Vade"}.get(ufuk, ufuk)
            satirlar.append(f"  Ufuk: {ufuk_adi}")
        if hedef:
            satirlar.append(f"  Hedef: {hedef[:80]}")
        satirlar.append("")

    guncelleme = (portfoy.get("guncelleme") or "")[:10]
    if guncelleme:
        satirlar.append(f"<i>Son güncelleme: {guncelleme}</i>")

    return "\n".join(satirlar)


def portfoy_grafigi_olustur(user_id: int | str):
    """
    Portföy dağılım grafiği oluştur (pie chart + bar chart).

    Returns:
        BytesIO buffer (PNG) veya None
    """
    try:
        import io
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.gridspec as gridspec
    except ImportError:
        return None

    portfoy = kullanici_portfoy_al(user_id)
    varliklar = portfoy.get("varliklar", [])

    if not varliklar:
        return None

    # Kategoriye göre grupla
    kat_sayilari: dict[str, int] = {}
    for v in varliklar:
        kat = v.get("kategori", "diger")
        kat_sayilari[kat] = kat_sayilari.get(kat, 0) + 1

    kat_isimleri = {
        "kripto": "Kripto",
        "emtia": "Emtia",
        "hisse": "Hisse",
        "doviz": "Doviz",
        "diger": "Diger",
    }

    renkler = {
        "kripto": "#16213e",
        "emtia": "#0f3460",
        "hisse": "#533483",
        "doviz": "#e94560",
        "diger": "#888888",
    }

    # Grafik
    fig = plt.figure(figsize=(12, 5), facecolor="white")
    gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.4)

    # Sol: Pie chart (kategori dağılımı)
    ax1 = fig.add_subplot(gs[0])
    etiketler = [kat_isimleri.get(k, k) for k in kat_sayilari.keys()]
    degerler = list(kat_sayilari.values())
    pie_renkler = [renkler.get(k, "#888888") for k in kat_sayilari.keys()]

    wedges, texts, autotexts = ax1.pie(
        degerler,
        labels=etiketler,
        colors=pie_renkler,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.75,
        wedgeprops={"linewidth": 2, "edgecolor": "white"},
    )
    for text in texts:
        text.set_fontsize(10)
        text.set_fontweight("600")
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color("white")
        autotext.set_fontweight("bold")

    ax1.set_title("Kategori Dagilimi", fontsize=12, fontweight="bold", color="#1a1a2e", pad=15)

    # Sağ: Bar chart (varlık listesi)
    ax2 = fig.add_subplot(gs[1])

    semboller = [v["sembol"] for v in varliklar[:8]]  # max 8 varlık
    miktarlar = [v["miktar"] for v in varliklar[:8]]
    bar_renkler = [renkler.get(v.get("kategori", "diger"), "#888888") for v in varliklar[:8]]

    bars = ax2.barh(semboller, miktarlar, color=bar_renkler, height=0.6, alpha=0.85)

    for bar, miktar in zip(bars, miktarlar):
        ax2.text(
            bar.get_width() * 1.02,
            bar.get_y() + bar.get_height() / 2,
            f"{miktar:g}",
            va="center",
            fontsize=9,
            fontweight="600",
            color="#1a1a2e",
        )

    ax2.set_xlabel("Miktar", fontsize=10, fontweight="600", color="#1a1a2e")
    ax2.set_title("Varlik Miktarlari", fontsize=12, fontweight="bold", color="#1a1a2e", pad=15)
    ax2.grid(axis="x", alpha=0.3, linestyle="--", linewidth=0.5)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_color("#e0e0e0")
    ax2.spines["bottom"].set_color("#e0e0e0")
    ax2.tick_params(axis="y", labelsize=10)

    plt.suptitle(
        "Portfoy Ozeti",
        fontsize=14,
        fontweight="bold",
        color="#1a1a2e",
        y=1.02,
    )

    import io
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    plt.close(fig)

    return buf


def varlik_parse(metin: str) -> tuple[str, float, Optional[float]]:
    """
    Kullanıcı girişini parse et.
    Formatlar:
      "BTC 0.5"
      "BTC 0.5 45000"   (sembol miktar maliyet)
      "0.5 BTC"
      "Bitcoin 0.5"

    Returns:
        (sembol, miktar, maliyet_veya_None)

    Raises:
        ValueError: Parse edilemezse
    """
    parcalar = metin.strip().split()
    if len(parcalar) < 2:
        raise ValueError("En az sembol ve miktar gerekli")

    sembol = ""
    miktar = 0.0
    maliyet = None

    # İlk parça sayı mı sembol mü?
    try:
        miktar = float(parcalar[0].replace(",", "."))
        sembol = parcalar[1]
        if len(parcalar) >= 3:
            maliyet = float(parcalar[2].replace(",", "."))
    except ValueError:
        sembol = parcalar[0]
        try:
            miktar = float(parcalar[1].replace(",", "."))
        except ValueError:
            raise ValueError(f"Miktar sayı olmalı: {parcalar[1]}")
        if len(parcalar) >= 3:
            try:
                maliyet = float(parcalar[2].replace(",", "."))
            except ValueError:
                pass  # Maliyet opsiyonel

    if miktar <= 0:
        raise ValueError("Miktar sıfırdan büyük olmalı")

    return sembol, miktar, maliyet
