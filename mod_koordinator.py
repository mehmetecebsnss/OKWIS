"""
Okwis AI — Mod Koordinatör Sistemi
14 modun ağırlıklandırılması, sentezlenmesi ve uyum skoru hesaplama.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─── Veri Yapıları ────────────────────────────────────────────────────────────

@dataclass
class ModSinyal:
    """Bir modun ürettiği sinyal"""
    mod_adi: str
    yon: str  # "bullish", "bearish", "neutral"
    guc: float  # 0-10 arası
    guven: int  # 0-100 arası
    aciklama: str  # Kısa açıklama


@dataclass
class ModBaglam:
    """Bir modun ürettiği bağlam metni"""
    mod_adi: str
    baglam: str
    uzunluk: int


@dataclass
class UyumSkoru:
    """Modlar arası uyum skoru"""
    consensus: str  # "bullish", "bearish", "neutral"
    uyum_skoru: float  # 0-100
    uyumlu_mod_sayisi: int
    uyumsuz_mod_sayisi: int
    guven_carpani: float  # 1.0-1.5 arası
    detay: str  # Açıklama


# ─── Mod Ağırlıkları ──────────────────────────────────────────────────────────

MOD_AGIRLIKLARI: Dict[str, Dict[str, float]] = {
    "kripto": {
        # Teknik ve sosyal faktörler ön planda
        "teknik_analiz": 1.5,
        "sentiment": 1.4,
        "whale_takip": 1.3,
        "korelasyon": 1.2,
        "jeopolitik": 1.1,
        "makro_ekonomi": 1.0,
        "sektor": 0.9,
        "trendler": 1.0,
        "mevsim": 0.7,
        "hava": 0.5,
        "magazin": 0.6,
        "ozel_gun": 0.6,
        "dogal_afet": 0.7,
        "insider": 0.3,  # Kripto için insider yok
    },
    "hisse": {
        # Insider ve makro faktörler ön planda
        "insider": 1.5,
        "teknik_analiz": 1.4,
        "makro_ekonomi": 1.3,
        "sektor": 1.3,
        "korelasyon": 1.2,
        "sentiment": 1.1,
        "jeopolitik": 1.0,
        "trendler": 0.9,
        "mevsim": 0.8,
        "magazin": 0.7,
        "ozel_gun": 0.7,
        "hava": 0.6,
        "dogal_afet": 0.6,
        "whale_takip": 0.2,  # Hisse için whale yok
    },
    "forex": {
        # Makro ve jeopolitik faktörler ön planda
        "makro_ekonomi": 1.6,
        "jeopolitik": 1.5,
        "korelasyon": 1.4,
        "teknik_analiz": 1.3,
        "sentiment": 1.0,
        "sektor": 0.8,
        "trendler": 0.8,
        "mevsim": 0.7,
        "dogal_afet": 0.7,
        "ozel_gun": 0.6,
        "hava": 0.5,
        "magazin": 0.5,
        "insider": 0.3,
        "whale_takip": 0.2,
    },
    "emtia": {
        # Hava ve mevsim faktörler ön planda
        "hava": 1.5,
        "mevsim": 1.4,
        "jeopolitik": 1.4,
        "dogal_afet": 1.3,
        "makro_ekonomi": 1.3,
        "teknik_analiz": 1.2,
        "korelasyon": 1.2,
        "sektor": 1.0,
        "sentiment": 0.9,
        "trendler": 0.8,
        "ozel_gun": 0.7,
        "magazin": 0.6,
        "insider": 0.4,
        "whale_takip": 0.2,
    },
}


# ─── Mod Ağırlık Alma ─────────────────────────────────────────────────────────

def mod_agirliklarini_al(varlik_tipi: str) -> Dict[str, float]:
    """
    Varlık tipine göre mod ağırlıklarını döndür.
    
    Args:
        varlik_tipi: "kripto", "hisse", "forex", "emtia"
    
    Returns:
        Mod ağırlıkları dict
    """
    varlik_tipi = varlik_tipi.lower()
    if varlik_tipi not in MOD_AGIRLIKLARI:
        logger.warning(f"Bilinmeyen varlık tipi: {varlik_tipi}, kripto ağırlıkları kullanılıyor")
        varlik_tipi = "kripto"
    
    return MOD_AGIRLIKLARI[varlik_tipi]


def mod_agirligini_al(varlik_tipi: str, mod_adi: str) -> float:
    """
    Belirli bir mod için ağırlık döndür.
    
    Args:
        varlik_tipi: "kripto", "hisse", "forex", "emtia"
        mod_adi: Mod adı (örn: "teknik_analiz")
    
    Returns:
        Ağırlık (float)
    """
    agirliklar = mod_agirliklarini_al(varlik_tipi)
    return agirliklar.get(mod_adi, 1.0)


# ─── Uyum Skoru Hesaplama ─────────────────────────────────────────────────────

def uyum_skoru_hesapla(
    mod_sinyalleri: List[ModSinyal],
    varlik_tipi: str = "kripto"
) -> UyumSkoru:
    """
    Tüm modların sinyallerini karşılaştır, uyum skorunu hesapla.
    
    Args:
        mod_sinyalleri: ModSinyal listesi
        varlik_tipi: Varlık tipi (ağırlıklandırma için)
    
    Returns:
        UyumSkoru
    """
    if not mod_sinyalleri:
        return UyumSkoru(
            consensus="neutral",
            uyum_skoru=0,
            uyumlu_mod_sayisi=0,
            uyumsuz_mod_sayisi=0,
            guven_carpani=1.0,
            detay="Hiç mod sinyali yok"
        )
    
    # Ağırlıklı oy sayımı
    agirliklar = mod_agirliklarini_al(varlik_tipi)
    
    bullish_agirlik = 0.0
    bearish_agirlik = 0.0
    neutral_agirlik = 0.0
    
    bullish_modlar = []
    bearish_modlar = []
    neutral_modlar = []
    
    for sinyal in mod_sinyalleri:
        agirlik = agirliklar.get(sinyal.mod_adi, 1.0)
        
        # Güç faktörünü de hesaba kat (0-10 → 0.0-1.0)
        guc_carpani = sinyal.guc / 10.0
        efektif_agirlik = agirlik * guc_carpani
        
        if sinyal.yon == "bullish":
            bullish_agirlik += efektif_agirlik
            bullish_modlar.append(sinyal.mod_adi)
        elif sinyal.yon == "bearish":
            bearish_agirlik += efektif_agirlik
            bearish_modlar.append(sinyal.mod_adi)
        else:
            neutral_agirlik += efektif_agirlik
            neutral_modlar.append(sinyal.mod_adi)
    
    toplam_agirlik = bullish_agirlik + bearish_agirlik + neutral_agirlik
    
    # Consensus belirleme
    if bullish_agirlik > bearish_agirlik and bullish_agirlik > neutral_agirlik:
        consensus = "bullish"
        uyum_skoru = (bullish_agirlik / toplam_agirlik) * 100 if toplam_agirlik > 0 else 0
        uyumlu_modlar = bullish_modlar
        uyumsuz_modlar = bearish_modlar + neutral_modlar
    elif bearish_agirlik > bullish_agirlik and bearish_agirlik > neutral_agirlik:
        consensus = "bearish"
        uyum_skoru = (bearish_agirlik / toplam_agirlik) * 100 if toplam_agirlik > 0 else 0
        uyumlu_modlar = bearish_modlar
        uyumsuz_modlar = bullish_modlar + neutral_modlar
    else:
        consensus = "neutral"
        uyum_skoru = (neutral_agirlik / toplam_agirlik) * 100 if toplam_agirlik > 0 else 50
        uyumlu_modlar = neutral_modlar
        uyumsuz_modlar = bullish_modlar + bearish_modlar
    
    # Güven çarpanı hesaplama
    if uyum_skoru >= 85:
        guven_carpani = 1.5  # Çok yüksek uyum
    elif uyum_skoru >= 75:
        guven_carpani = 1.3
    elif uyum_skoru >= 65:
        guven_carpani = 1.2
    elif uyum_skoru >= 55:
        guven_carpani = 1.1
    else:
        guven_carpani = 1.0  # Düşük uyum, güven artışı yok
    
    # Detay açıklama
    detay = f"{len(uyumlu_modlar)}/{len(mod_sinyalleri)} mod {consensus} yönünde"
    if uyum_skoru >= 80:
        detay += " (güçlü konsensüs)"
    elif uyum_skoru >= 60:
        detay += " (orta konsensüs)"
    else:
        detay += " (zayıf konsensüs)"
    
    return UyumSkoru(
        consensus=consensus,
        uyum_skoru=uyum_skoru,
        uyumlu_mod_sayisi=len(uyumlu_modlar),
        uyumsuz_mod_sayisi=len(uyumsuz_modlar),
        guven_carpani=guven_carpani,
        detay=detay
    )


# ─── Bağlam Ağırlıklandırma ───────────────────────────────────────────────────

def baglam_agirliklandir(
    mod_baglamlari: List[ModBaglam],
    varlik_tipi: str = "kripto",
    toplam_token_limit: int = 6000
) -> str:
    """
    Mod bağlamlarını ağırlıklarına göre kırp ve birleştir.
    
    Args:
        mod_baglamlari: ModBaglam listesi
        varlik_tipi: Varlık tipi
        toplam_token_limit: Toplam token limiti
    
    Returns:
        Birleştirilmiş bağlam metni
    """
    agirliklar = mod_agirliklarini_al(varlik_tipi)
    
    # Her mod için token limiti hesapla
    toplam_agirlik = sum(agirliklar.get(mb.mod_adi, 1.0) for mb in mod_baglamlari)
    
    agirlikli_baglamlar = []
    for mb in mod_baglamlari:
        agirlik = agirliklar.get(mb.mod_adi, 1.0)
        # Token limiti = (mod ağırlığı / toplam ağırlık) * toplam limit
        mod_token_limit = int((agirlik / toplam_agirlik) * toplam_token_limit)
        
        # Yaklaşık token sayısı = karakter sayısı / 4
        karakter_limit = mod_token_limit * 4
        
        # Bağlamı kırp
        kirpilmis_baglam = mb.baglam[:karakter_limit]
        
        agirlikli_baglamlar.append(
            f"[{mb.mod_adi.upper()}] (ağırlık: {agirlik:.1f})\n{kirpilmis_baglam}"
        )
    
    return "\n\n".join(agirlikli_baglamlar)


# ─── Divergence Tespiti ───────────────────────────────────────────────────────

def divergence_tespit(mod_sinyalleri: List[ModSinyal]) -> Optional[str]:
    """
    Modlar arasında önemli uyumsuzluk (divergence) var mı tespit et.
    
    Args:
        mod_sinyalleri: ModSinyal listesi
    
    Returns:
        Divergence açıklaması (varsa), yoksa None
    """
    if len(mod_sinyalleri) < 3:
        return None
    
    # Önemli modlar arasında uyumsuzluk ara
    onemli_modlar = ["teknik_analiz", "sentiment", "makro_ekonomi", "jeopolitik"]
    
    onemli_sinyaller = [s for s in mod_sinyalleri if s.mod_adi in onemli_modlar]
    
    if len(onemli_sinyaller) < 2:
        return None
    
    # Farklı yönler var mı?
    yonler = set(s.yon for s in onemli_sinyaller)
    
    if len(yonler) >= 2 and "neutral" not in yonler:
        # Bullish ve bearish aynı anda var
        bullish_modlar = [s.mod_adi for s in onemli_sinyaller if s.yon == "bullish"]
        bearish_modlar = [s.mod_adi for s in onemli_sinyaller if s.yon == "bearish"]
        
        return (
            f"⚠️ DIVERGENCE TESPİT EDİLDİ:\n"
            f"Bullish: {', '.join(bullish_modlar)}\n"
            f"Bearish: {', '.join(bearish_modlar)}\n"
            f"Bu uyumsuzluk yüksek volatilite sinyali olabilir."
        )
    
    return None


# ─── Güven Skoru Hesaplama ────────────────────────────────────────────────────

def guven_skoru_hesapla(
    base_guven: int,
    uyum: UyumSkoru,
    mod_sayisi: int
) -> int:
    """
    Uyum skoruna göre güven skorunu hesapla.
    
    Args:
        base_guven: Temel güven skoru (0-100)
        uyum: UyumSkoru
        mod_sayisi: Kullanılan mod sayısı
    
    Returns:
        Final güven skoru (0-100)
    """
    # Uyum çarpanını uygula
    guven_uyum = base_guven * uyum.guven_carpani
    
    # Mod sayısı bonusu (daha fazla mod = daha güvenilir)
    if mod_sayisi >= 12:
        mod_bonusu = 1.1
    elif mod_sayisi >= 10:
        mod_bonusu = 1.05
    else:
        mod_bonusu = 1.0
    
    final_guven = guven_uyum * mod_bonusu
    
    # 0-100 aralığında tut
    return min(100, max(0, int(final_guven)))


# ─── Test Fonksiyonu ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test: Örnek sinyaller
    test_sinyaller = [
        ModSinyal("teknik_analiz", "bullish", 7.5, 80, "RSI oversold, MACD bullish"),
        ModSinyal("sentiment", "bullish", 6.5, 75, "Twitter pozitif"),
        ModSinyal("whale_takip", "bullish", 8.0, 85, "Whale birikimi"),
        ModSinyal("jeopolitik", "bearish", 5.0, 60, "Gerilim artıyor"),
        ModSinyal("makro_ekonomi", "neutral", 5.5, 65, "Fed beklemede"),
    ]
    
    # Uyum skoru hesapla
    uyum = uyum_skoru_hesapla(test_sinyaller, "kripto")
    
    print("=" * 50)
    print("MOD KOORDİNATÖR TEST")
    print("=" * 50)
    print(f"\nConsensus: {uyum.consensus}")
    print(f"Uyum Skoru: {uyum.uyum_skoru:.1f}/100")
    print(f"Uyumlu Modlar: {uyum.uyumlu_mod_sayisi}")
    print(f"Uyumsuz Modlar: {uyum.uyumsuz_mod_sayisi}")
    print(f"Güven Çarpanı: {uyum.guven_carpani}x")
    print(f"Detay: {uyum.detay}")
    
    # Divergence tespiti
    div = divergence_tespit(test_sinyaller)
    if div:
        print(f"\n{div}")
    
    # Güven skoru
    final_guven = guven_skoru_hesapla(70, uyum, len(test_sinyaller))
    print(f"\nFinal Güven Skoru: {final_guven}/100")
