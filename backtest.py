"""
Okwis AI — Backtest/Simülasyon Sistemi
Geçmiş tahminleri göster, performans analizi yap
"""

import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_VAR = True
except ImportError:
    MATPLOTLIB_VAR = False


TAHMIN_DOSYASI = Path(__file__).resolve().parent / "metrics" / "tahmin_kayitlari.jsonl"
HIZLI_PARA_DOSYASI = Path(__file__).resolve().parent / "metrics" / "hizli_para_islemler.jsonl"


def tahminleri_yukle() -> list[dict]:
    """Tüm tahminleri yükle"""
    if not TAHMIN_DOSYASI.exists():
        return []
    
    tahminler = []
    with open(TAHMIN_DOSYASI, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir:
                try:
                    tahminler.append(json.loads(satir))
                except json.JSONDecodeError:
                    continue
    
    return tahminler


def hizli_para_islemlerini_yukle() -> list[dict]:
    """Hızlı Para Modu işlemlerini yükle"""
    if not HIZLI_PARA_DOSYASI.exists():
        return []
    
    islemler = []
    with open(HIZLI_PARA_DOSYASI, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir:
                try:
                    islemler.append(json.loads(satir))
                except json.JSONDecodeError:
                    continue
    
    return islemler


def performans_ozeti() -> dict:
    """
    Genel performans özeti
    
    Returns:
        {
            "toplam": int,
            "dogrulanan": int,
            "bekleyen": int,
            "oran": float | None,
            "mod_bazli": {mod: {"toplam": int, "dogrulanan": int}},
        }
    """
    tahminler = tahminleri_yukle()
    
    toplam = len(tahminler)
    dogrulanan = sum(1 for t in tahminler if t.get("dogrulandi") is True)
    bekleyen = sum(1 for t in tahminler if t.get("dogrulandi") is None)
    
    oran = None
    if toplam - bekleyen > 0:
        oran = (dogrulanan / (toplam - bekleyen)) * 100
    
    # Mod bazlı
    mod_bazli = {}
    for t in tahminler:
        mod = t.get("mod", "bilinmeyen")
        if mod not in mod_bazli:
            mod_bazli[mod] = {"toplam": 0, "dogrulanan": 0, "bekleyen": 0}
        
        mod_bazli[mod]["toplam"] += 1
        if t.get("dogrulandi") is True:
            mod_bazli[mod]["dogrulanan"] += 1
        elif t.get("dogrulandi") is None:
            mod_bazli[mod]["bekleyen"] += 1
    
    return {
        "toplam": toplam,
        "dogrulanan": dogrulanan,
        "bekleyen": bekleyen,
        "oran": oran,
        "mod_bazli": mod_bazli,
    }


def son_n_tahmin(n: int = 10) -> list[dict]:
    """Son N tahmini getir (en yeni önce)"""
    tahminler = tahminleri_yukle()
    # Tarihe göre sırala (en yeni önce)
    tahminler.sort(key=lambda t: t.get("ts_utc", ""), reverse=True)
    return tahminler[:n]


def ulke_bazli_tahminler(ulke: str) -> list[dict]:
    """Belirli bir ülke için tahminler"""
    tahminler = tahminleri_yukle()
    return [t for t in tahminler if t.get("ulke", "").lower() == ulke.lower()]


def varlik_bazli_tahminler(varlik: str) -> list[dict]:
    """Belirli bir varlık için tahminler"""
    tahminler = tahminleri_yukle()
    return [t for t in tahminler if varlik.lower() in t.get("varlik", "").lower()]


def tahmin_dogrula(tahmin_id: str, dogru_mu: bool, gercek_yon: Optional[str] = None) -> bool:
    """
    Bir tahmini manuel olarak doğrula
    
    Args:
        tahmin_id: Tahmin timestamp'i (ts_utc)
        dogru_mu: Tahmin doğru muydu?
        gercek_yon: Gerçekte ne oldu? (up/down/neutral)
    
    Returns:
        Başarılı mı?
    """
    if not TAHMIN_DOSYASI.exists():
        return False
    
    tahminler = []
    degisti = False
    
    with open(TAHMIN_DOSYASI, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir:
                continue
            
            try:
                tahmin = json.loads(satir)
                if tahmin.get("ts_utc") == tahmin_id:
                    tahmin["dogrulandi"] = dogru_mu
                    if gercek_yon:
                        tahmin["gercek_yon"] = gercek_yon
                    degisti = True
                tahminler.append(tahmin)
            except json.JSONDecodeError:
                continue
    
    if degisti:
        # Dosyayı yeniden yaz
        with open(TAHMIN_DOSYASI, "w", encoding="utf-8") as f:
            for t in tahminler:
                f.write(json.dumps(t, ensure_ascii=False) + "\n")
        return True
    
    return False


def detayli_analiz() -> dict:
    """
    Detaylı performans analizi
    
    Returns:
        {
            "varlik_bazli": {varlik: {"toplam": int, "dogrulanan": int, "oran": float}},
            "ulke_bazli": {ulke: {"toplam": int, "dogrulanan": int, "oran": float}},
            "sure_bazli": {sure: {"toplam": int, "dogrulanan": int, "oran": float}},
            "zaman_serisi": [(tarih, dogru_sayisi, toplam_sayisi)],
        }
    """
    tahminler = tahminleri_yukle()
    
    # Varlık bazlı
    varlik_bazli = defaultdict(lambda: {"toplam": 0, "dogrulanan": 0, "bekleyen": 0})
    for t in tahminler:
        varlik = t.get("varlik", "genel").lower()
        varlik_bazli[varlik]["toplam"] += 1
        if t.get("dogrulandi") is True:
            varlik_bazli[varlik]["dogrulanan"] += 1
        elif t.get("dogrulandi") is None:
            varlik_bazli[varlik]["bekleyen"] += 1
    
    # Oran hesapla
    for varlik, veri in varlik_bazli.items():
        tamamlanan = veri["toplam"] - veri["bekleyen"]
        if tamamlanan > 0:
            veri["oran"] = (veri["dogrulanan"] / tamamlanan) * 100
        else:
            veri["oran"] = None
    
    # Ülke bazlı
    ulke_bazli = defaultdict(lambda: {"toplam": 0, "dogrulanan": 0, "bekleyen": 0})
    for t in tahminler:
        ulke = t.get("ulke", "Bilinmeyen")
        ulke_bazli[ulke]["toplam"] += 1
        if t.get("dogrulandi") is True:
            ulke_bazli[ulke]["dogrulanan"] += 1
        elif t.get("dogrulandi") is None:
            ulke_bazli[ulke]["bekleyen"] += 1
    
    # Oran hesapla
    for ulke, veri in ulke_bazli.items():
        tamamlanan = veri["toplam"] - veri["bekleyen"]
        if tamamlanan > 0:
            veri["oran"] = (veri["dogrulanan"] / tamamlanan) * 100
        else:
            veri["oran"] = None
    
    # Süre bazlı
    sure_bazli = defaultdict(lambda: {"toplam": 0, "dogrulanan": 0, "bekleyen": 0})
    for t in tahminler:
        sure = t.get("sure", "belirsiz")
        sure_bazli[sure]["toplam"] += 1
        if t.get("dogrulandi") is True:
            sure_bazli[sure]["dogrulanan"] += 1
        elif t.get("dogrulandi") is None:
            sure_bazli[sure]["bekleyen"] += 1
    
    # Oran hesapla
    for sure, veri in sure_bazli.items():
        tamamlanan = veri["toplam"] - veri["bekleyen"]
        if tamamlanan > 0:
            veri["oran"] = (veri["dogrulanan"] / tamamlanan) * 100
        else:
            veri["oran"] = None
    
    # Zaman serisi (günlük)
    tarih_bazli = defaultdict(lambda: {"toplam": 0, "dogrulanan": 0})
    for t in tahminler:
        if t.get("dogrulandi") is not None:  # Sadece doğrulanmış tahminler
            tarih = t.get("tarih", "")
            tarih_bazli[tarih]["toplam"] += 1
            if t.get("dogrulandi") is True:
                tarih_bazli[tarih]["dogrulanan"] += 1
    
    # Sırala ve liste yap
    zaman_serisi = []
    for tarih in sorted(tarih_bazli.keys()):
        veri = tarih_bazli[tarih]
        zaman_serisi.append((tarih, veri["dogrulanan"], veri["toplam"]))
    
    return {
        "varlik_bazli": dict(varlik_bazli),
        "ulke_bazli": dict(ulke_bazli),
        "sure_bazli": dict(sure_bazli),
        "zaman_serisi": zaman_serisi,
    }


def performans_grafigi_olustur() -> Optional[io.BytesIO]:
    """
    Performans grafiği oluştur (mod karşılaştırma)
    
    Returns:
        BytesIO buffer (PNG) veya None
    """
    if not MATPLOTLIB_VAR:
        return None
    
    ozet = performans_ozeti()
    mod_bazli = ozet["mod_bazli"]
    
    if not mod_bazli:
        return None
    
    # Sadece tamamlanmış tahminleri olan modları göster
    modlar = []
    dogruluk_oranlari = []
    toplam_sayilari = []
    
    for mod, veri in mod_bazli.items():
        tamamlanan = veri["toplam"] - veri["bekleyen"]
        if tamamlanan > 0:
            modlar.append(mod.upper())
            oran = (veri["dogrulanan"] / tamamlanan) * 100
            dogruluk_oranlari.append(oran)
            toplam_sayilari.append(tamamlanan)
    
    if not modlar:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
    
    # Bar chart
    bars = ax.barh(modlar, dogruluk_oranlari, color='#16213e', alpha=0.85)
    
    # Değerleri bar'ların üzerine yaz
    for i, (bar, oran, toplam) in enumerate(zip(bars, dogruluk_oranlari, toplam_sayilari)):
        ax.text(
            oran + 2,
            bar.get_y() + bar.get_height() / 2,
            f'{oran:.1f}% ({toplam} tahmin)',
            va='center',
            fontsize=10,
            fontweight='600',
            color='#1a1a2e'
        )
    
    # Stil
    ax.set_xlim(0, 110)
    ax.set_xlabel('Dogruluk Orani (%)', fontsize=11, color='#1a1a2e', fontweight='600')
    ax.set_title(
        'Mod Bazli Performans Karsilastirmasi',
        fontsize=14,
        fontweight='bold',
        color='#1a1a2e',
        pad=20
    )
    
    # Grid ve çerçeve
    ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e0e0e0')
    ax.spines['bottom'].set_color('#e0e0e0')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    return buf


def detayli_analiz_grafigi_olustur() -> Optional[io.BytesIO]:
    """
    Detaylı analiz grafiği (varlık, ülke, süre bazlı)
    
    Returns:
        BytesIO buffer (PNG) veya None
    """
    if not MATPLOTLIB_VAR:
        return None
    
    analiz = detayli_analiz()
    
    # 3 subplot: varlık, ülke, süre
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 14), facecolor='white')
    
    # 1. Varlık bazlı (en çok tahmin edilen 5 varlık)
    varlik_bazli = analiz["varlik_bazli"]
    varlik_sirali = sorted(
        [(v, d["toplam"], d.get("oran", 0)) for v, d in varlik_bazli.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    if varlik_sirali:
        varliklar = [v[0].capitalize() for v in varlik_sirali]
        oranlar = [v[2] if v[2] else 0 for v in varlik_sirali]
        
        bars1 = ax1.barh(varliklar, oranlar, color='#0f3460', alpha=0.85)
        for bar, oran in zip(bars1, oranlar):
            if oran > 0:
                ax1.text(oran + 2, bar.get_y() + bar.get_height() / 2,
                        f'{oran:.1f}%', va='center', fontsize=9, fontweight='600')
        
        ax1.set_xlim(0, 110)
        ax1.set_xlabel('Dogruluk Orani (%)', fontsize=10, fontweight='600')
        ax1.set_title('En Cok Tahmin Edilen Varliklar', fontsize=12, fontweight='bold', pad=15)
        ax1.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
    
    # 2. Ülke bazlı (en çok tahmin edilen 5 ülke)
    ulke_bazli = analiz["ulke_bazli"]
    ulke_sirali = sorted(
        [(u, d["toplam"], d.get("oran", 0)) for u, d in ulke_bazli.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    if ulke_sirali:
        ulkeler = [u[0] for u in ulke_sirali]
        oranlar = [u[2] if u[2] else 0 for u in ulke_sirali]
        
        bars2 = ax2.barh(ulkeler, oranlar, color='#533483', alpha=0.85)
        for bar, oran in zip(bars2, oranlar):
            if oran > 0:
                ax2.text(oran + 2, bar.get_y() + bar.get_height() / 2,
                        f'{oran:.1f}%', va='center', fontsize=9, fontweight='600')
        
        ax2.set_xlim(0, 110)
        ax2.set_xlabel('Dogruluk Orani (%)', fontsize=10, fontweight='600')
        ax2.set_title('Ulke Bazli Performans', fontsize=12, fontweight='bold', pad=15)
        ax2.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
    
    # 3. Süre bazlı
    sure_bazli = analiz["sure_bazli"]
    sure_sirali = sorted(
        [(s, d["toplam"], d.get("oran", 0)) for s, d in sure_bazli.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    if sure_sirali:
        sureler = [s[0] for s in sure_sirali]
        oranlar = [s[2] if s[2] else 0 for s in sure_sirali]
        
        bars3 = ax3.barh(sureler, oranlar, color='#16213e', alpha=0.85)
        for bar, oran in zip(bars3, oranlar):
            if oran > 0:
                ax3.text(oran + 2, bar.get_y() + bar.get_height() / 2,
                        f'{oran:.1f}%', va='center', fontsize=9, fontweight='600')
        
        ax3.set_xlim(0, 110)
        ax3.set_xlabel('Dogruluk Orani (%)', fontsize=10, fontweight='600')
        ax3.set_title('Kisa Vade vs Uzun Vade Basarisi', fontsize=12, fontweight='bold', pad=15)
        ax3.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    return buf


def backtest_raporu_html(n: int = 20) -> str:
    """
    Backtest raporu HTML formatında
    
    Args:
        n: Kaç tahmin gösterilsin
    
    Returns:
        HTML formatında rapor
    """
    ozet = performans_ozeti()
    son_tahminler = son_n_tahmin(n)
    
    # Başlık
    html = [
        "<b>◆ BACKTEST RAPORU</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "",
    ]
    
    # Genel özet
    html.append("<b>📊 Genel Performans</b>")
    html.append(f"Toplam Tahmin: <b>{ozet['toplam']}</b>")
    html.append(f"Doğrulanan: <b>{ozet['dogrulanan']}</b>")
    html.append(f"Bekleyen: <b>{ozet['bekleyen']}</b>")
    
    if ozet['oran'] is not None:
        html.append(f"Doğruluk Oranı: <b>{ozet['oran']:.1f}%</b>")
    else:
        html.append("Doğruluk Oranı: <i>Henüz doğrulanmış tahmin yok</i>")
    
    html.append("")
    
    # Mod bazlı
    if ozet['mod_bazli']:
        html.append("<b>📈 Mod Bazlı Performans</b>")
        for mod, veri in ozet['mod_bazli'].items():
            toplam_mod = veri['toplam']
            dogru_mod = veri['dogrulanan']
            bekleyen_mod = veri['bekleyen']
            
            if toplam_mod - bekleyen_mod > 0:
                oran_mod = (dogru_mod / (toplam_mod - bekleyen_mod)) * 100
                html.append(f"▸ <b>{mod.upper()}</b>: {dogru_mod}/{toplam_mod - bekleyen_mod} ({oran_mod:.0f}%)")
            else:
                html.append(f"▸ <b>{mod.upper()}</b>: {toplam_mod} tahmin (henüz doğrulanmadı)")
        
        html.append("")
    
    # Son tahminler
    html.append(f"<b>🕰️ Son {min(n, len(son_tahminler))} Tahmin</b>")
    html.append("")
    
    for i, t in enumerate(son_tahminler, 1):
        tarih = t.get("tarih", "?")
        mod = t.get("mod", "?")
        ulke = t.get("ulke", "?")
        varlik = t.get("varlik", "genel")
        yon = t.get("yon", "?")
        sure = t.get("sure", "?")
        dogrulandi = t.get("dogrulandi")
        
        # Durum ikonu
        if dogrulandi is True:
            durum = "✅"
        elif dogrulandi is False:
            durum = "❌"
        else:
            durum = "⏳"
        
        html.append(f"{durum} <b>{i}.</b> {tarih} · {mod.upper()}")
        html.append(f"   {ulke} · {varlik}")
        html.append(f"   Yön: {yon} · Süre: {sure}")
        
        if dogrulandi is not None:
            gercek = t.get("gercek_yon", "?")
            html.append(f"   Gerçek: {gercek}")
        
        html.append("")
    
    html.append("<b>━━━━━━━━━━━━━━━━━━━━</b>")
    html.append("<i>Tahminleri manuel olarak doğrulamak için admin ile iletişime geç.</i>")
    
    return "\n".join(html)


if __name__ == "__main__":
    # Test
    print("=" * 50)
    print("BACKTEST SİSTEMİ TEST")
    print("=" * 50)
    
    ozet = performans_ozeti()
    print(f"\nToplam Tahmin: {ozet['toplam']}")
    print(f"Doğrulanan: {ozet['dogrulanan']}")
    print(f"Bekleyen: {ozet['bekleyen']}")
    
    if ozet['oran']:
        print(f"Doğruluk Oranı: {ozet['oran']:.1f}%")
    
    print("\nMod Bazlı:")
    for mod, veri in ozet['mod_bazli'].items():
        print(f"  {mod}: {veri['toplam']} tahmin")
    
    print("\nSon 5 Tahmin:")
    for i, t in enumerate(son_n_tahmin(5), 1):
        print(f"  {i}. {t['tarih']} - {t['ulke']} - {t['varlik']}")


# ─── Hızlı Para Modu Backtest ────────────────────────────────────────────────

def hizli_para_performans_ozeti() -> dict:
    """
    Hızlı Para Modu performans özeti
    
    Returns:
        {
            "toplam": int,
            "dogrulanan": int,
            "bekleyen": int,
            "tp1_hit": int,
            "tp2_hit": int,
            "tp3_hit": int,
            "stop_loss_hit": int,
            "basari_orani": float | None,
            "ortalama_risk_odul": float,
            "varlik_tipi_bazli": {tip: {"toplam": int, "dogrulanan": int}},
        }
    """
    islemler = hizli_para_islemlerini_yukle()
    
    toplam = len(islemler)
    dogrulanan = sum(1 for i in islemler if i.get("dogrulandi") is True)
    bekleyen = sum(1 for i in islemler if i.get("dogrulandi") is None)
    
    # Sonuç bazlı
    tp1_hit = sum(1 for i in islemler if i.get("sonuc") == "tp1")
    tp2_hit = sum(1 for i in islemler if i.get("sonuc") == "tp2")
    tp3_hit = sum(1 for i in islemler if i.get("sonuc") == "tp3")
    stop_loss_hit = sum(1 for i in islemler if i.get("sonuc") == "stop_loss")
    
    basari_orani = None
    if toplam - bekleyen > 0:
        basarili = tp1_hit + tp2_hit + tp3_hit
        basari_orani = (basarili / (toplam - bekleyen)) * 100
    
    # Ortalama risk/ödül
    risk_odul_listesi = [i.get("risk_odul", 0) for i in islemler if i.get("risk_odul")]
    ortalama_risk_odul = sum(risk_odul_listesi) / len(risk_odul_listesi) if risk_odul_listesi else 0
    
    # Varlık tipi bazlı (kripto, forex, hisse, emtia)
    varlik_tipi_bazli = defaultdict(lambda: {"toplam": 0, "dogrulanan": 0, "bekleyen": 0})
    for i in islemler:
        # Varlık tipini tahmin et (basit)
        varlik = i.get("varlik", "").lower()
        if any(k in varlik for k in ["btc", "eth", "xrp", "sol", "ada"]):
            tip = "kripto"
        elif "/" in varlik or "usd" in varlik or "eur" in varlik:
            tip = "forex"
        elif any(k in varlik for k in ["xau", "wti", "gold", "oil"]):
            tip = "emtia"
        else:
            tip = "hisse"
        
        varlik_tipi_bazli[tip]["toplam"] += 1
        if i.get("dogrulandi") is True:
            varlik_tipi_bazli[tip]["dogrulanan"] += 1
        elif i.get("dogrulandi") is None:
            varlik_tipi_bazli[tip]["bekleyen"] += 1
    
    return {
        "toplam": toplam,
        "dogrulanan": dogrulanan,
        "bekleyen": bekleyen,
        "tp1_hit": tp1_hit,
        "tp2_hit": tp2_hit,
        "tp3_hit": tp3_hit,
        "stop_loss_hit": stop_loss_hit,
        "basari_orani": basari_orani,
        "ortalama_risk_odul": ortalama_risk_odul,
        "varlik_tipi_bazli": dict(varlik_tipi_bazli),
    }


def hizli_para_son_n_islem(n: int = 10) -> list[dict]:
    """Son N Hızlı Para işlemini getir (en yeni önce)"""
    islemler = hizli_para_islemlerini_yukle()
    islemler.sort(key=lambda i: i.get("ts_utc", ""), reverse=True)
    return islemler[:n]


def hizli_para_raporu_html(n: int = 20) -> str:
    """
    Hızlı Para Modu backtest raporu HTML formatında
    
    Args:
        n: Kaç işlem gösterilsin
    
    Returns:
        HTML formatında rapor
    """
    ozet = hizli_para_performans_ozeti()
    son_islemler = hizli_para_son_n_islem(n)
    
    # Başlık
    html = [
        "<b>⚡ HIZLI PARA MODU — BACKTEST RAPORU</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "",
    ]
    
    # Genel özet
    html.append("<b>📊 Genel Performans</b>")
    html.append(f"Toplam İşlem: <b>{ozet['toplam']}</b>")
    html.append(f"Doğrulanan: <b>{ozet['dogrulanan']}</b>")
    html.append(f"Bekleyen: <b>{ozet['bekleyen']}</b>")
    
    if ozet['basari_orani'] is not None:
        html.append(f"Başarı Oranı: <b>{ozet['basari_orani']:.1f}%</b>")
    else:
        html.append("Başarı Oranı: <i>Henüz doğrulanmış işlem yok</i>")
    
    html.append(f"Ort. Risk/Ödül: <b>1:{ozet['ortalama_risk_odul']:.1f}</b>")
    html.append("")
    
    # Sonuç dağılımı
    if ozet['dogrulanan'] > 0:
        html.append("<b>🎯 Sonuç Dağılımı</b>")
        html.append(f"  TP1: <b>{ozet['tp1_hit']}</b>")
        html.append(f"  TP2: <b>{ozet['tp2_hit']}</b>")
        html.append(f"  TP3: <b>{ozet['tp3_hit']}</b>")
        html.append(f"  Stop Loss: <b>{ozet['stop_loss_hit']}</b>")
        html.append("")
    
    # Varlık tipi bazlı
    if ozet['varlik_tipi_bazli']:
        html.append("<b>📈 Varlık Tipi Bazlı</b>")
        for tip, veri in ozet['varlik_tipi_bazli'].items():
            toplam_tip = veri['toplam']
            dogru_tip = veri['dogrulanan']
            bekleyen_tip = veri['bekleyen']
            
            if toplam_tip - bekleyen_tip > 0:
                oran_tip = (dogru_tip / (toplam_tip - bekleyen_tip)) * 100
                html.append(f"▸ <b>{tip.upper()}</b>: {dogru_tip}/{toplam_tip - bekleyen_tip} ({oran_tip:.0f}%)")
            else:
                html.append(f"▸ <b>{tip.upper()}</b>: {toplam_tip} işlem (henüz doğrulanmadı)")
        
        html.append("")
    
    # Son işlemler
    html.append(f"<b>🕰️ Son {min(n, len(son_islemler))} İşlem</b>")
    html.append("")
    
    for i, islem in enumerate(son_islemler, 1):
        tarih = islem.get("tarih", "?")
        varlik = islem.get("varlik", "?")
        pozisyon = islem.get("pozisyon", "?")
        giris_min = islem.get("giris_min", 0)
        giris_max = islem.get("giris_max", 0)
        tp1 = islem.get("tp1", 0)
        stop_loss = islem.get("stop_loss", 0)
        sure = islem.get("sure", "?")
        dogrulandi = islem.get("dogrulandi")
        sonuc = islem.get("sonuc")
        
        # Durum ikonu
        if dogrulandi is True:
            if sonuc in ["tp1", "tp2", "tp3"]:
                durum = "✅"
            else:
                durum = "❌"
        else:
            durum = "⏳"
        
        # Pozisyon emoji
        poz_emoji = "🟢" if pozisyon == "LONG" else ("🔴" if pozisyon == "SHORT" else "🟡")
        
        html.append(f"{durum} <b>{i}.</b> {tarih} · {poz_emoji} {pozisyon}")
        html.append(f"   {varlik} · Giriş: ${giris_min:,.2f}-${giris_max:,.2f}")
        html.append(f"   TP1: ${tp1:,.2f} · SL: ${stop_loss:,.2f}")
        html.append(f"   Süre: {sure}")
        
        if dogrulandi is not None and sonuc:
            html.append(f"   Sonuç: <b>{sonuc.upper()}</b>")
        
        html.append("")
    
    html.append("<b>━━━━━━━━━━━━━━━━━━━━</b>")
    html.append("<i>İşlemleri manuel olarak doğrulamak için admin ile iletişime geç.</i>")
    
    return "\n".join(html)
