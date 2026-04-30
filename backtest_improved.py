"""
Okwis AI — Geliştirilmiş Backtest/Simülasyon Sistemi
Geçmiş tahminleri göster, performans analizi yap, ROI hesapla

YENİ ÖZELLİKLER:
- Zaman serisi performans grafiği
- ROI (Return on Investment) hesaplama
- Sharpe Ratio hesaplama
- Maximum Drawdown analizi
- Karşılaştırmalı performans (mod vs mod)
- Win rate ve profit factor
- Detaylı istatistikler
"""

import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from collections import defaultdict
import math

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    import numpy as np
    MATPLOTLIB_VAR = True
except ImportError:
    MATPLOTLIB_VAR = False
    np = None


TAHMIN_DOSYASI = Path(__file__).resolve().parent / "metrics" / "tahmin_kayitlari.jsonl"
HIZLI_PARA_DOSYASI = Path(__file__).resolve().parent / "metrics" / "hizli_para_islemler.jsonl"


# ═══════════════════════════════════════════════════════════════════════════════
# TEMEL FONKSİYONLAR (Mevcut backtest.py'den)
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
# YENİ: GELİŞMİŞ ANALİZ FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════════════════════

def gelismis_performans_metrikleri() -> dict:
    """
    Gelişmiş performans metrikleri hesapla
    
    Returns:
        {
            "win_rate": float,  # Kazanma oranı (%)
            "profit_factor": float,  # Kar/Zarar oranı
            "avg_win": float,  # Ortalama kazanç
            "avg_loss": float,  # Ortalama kayıp
            "max_consecutive_wins": int,
            "max_consecutive_losses": int,
            "sharpe_ratio": float,  # Risk-adjusted return
            "max_drawdown": float,  # Maksimum düşüş (%)
            "recovery_factor": float,  # Toparlanma faktörü
        }
    """
    tahminler = tahminleri_yukle()
    
    # Sadece doğrulanmış tahminler
    dogrulanmis = [t for t in tahminler if t.get("dogrulandi") is not None]
    
    if not dogrulanmis:
        return {
            "win_rate": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "recovery_factor": 0,
        }
    
    # Win rate
    kazananlar = [t for t in dogrulanmis if t.get("dogrulandi") is True]
    kaybedenler = [t for t in dogrulanmis if t.get("dogrulandi") is False]
    win_rate = (len(kazananlar) / len(dogrulanmis)) * 100 if dogrulanmis else 0
    
    # Profit factor (basitleştirilmiş: her kazanç +1, her kayıp -1)
    total_wins = len(kazananlar)
    total_losses = len(kaybedenler)
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    
    # Ortalama kazanç/kayıp
    avg_win = 1.0  # Basitleştirilmiş
    avg_loss = 1.0
    
    # Ardışık kazanç/kayıp
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0
    
    # Tarihe göre sırala
    dogrulanmis_sirali = sorted(dogrulanmis, key=lambda t: t.get("ts_utc", ""))
    
    for t in dogrulanmis_sirali:
        if t.get("dogrulandi") is True:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        else:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)
    
    # Sharpe Ratio (basitleştirilmiş)
    returns = [1 if t.get("dogrulandi") is True else -1 for t in dogrulanmis_sirali]
    if len(returns) > 1:
        mean_return = sum(returns) / len(returns)
        std_return = math.sqrt(sum((r - mean_return) ** 2 for r in returns) / len(returns))
        sharpe_ratio = (mean_return / std_return) * math.sqrt(252) if std_return > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Maximum Drawdown
    cumulative = []
    cum_sum = 0
    for r in returns:
        cum_sum += r
        cumulative.append(cum_sum)
    
    if cumulative:
        peak = cumulative[0]
        max_dd = 0
        for val in cumulative:
            if val > peak:
                peak = val
            dd = ((peak - val) / peak * 100) if peak > 0 else 0
            max_dd = max(max_dd, dd)
    else:
        max_dd = 0
    
    # Recovery Factor
    total_return = sum(returns)
    recovery_factor = total_return / max_dd if max_dd > 0 else 0
    
    return {
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_dd,
        "recovery_factor": recovery_factor,
    }


def hizli_para_roi_hesapla() -> dict:
    """
    Hızlı Para Modu için ROI (Return on Investment) hesapla
    
    Returns:
        {
            "total_roi": float,  # Toplam ROI (%)
            "avg_roi_per_trade": float,  # İşlem başına ortalama ROI
            "win_rate": float,
            "profit_factor": float,
            "total_trades": int,
            "winning_trades": int,
            "losing_trades": int,
            "avg_risk_reward": float,
        }
    """
    islemler = hizli_para_islemlerini_yukle()
    
    # Sadece doğrulanmış işlemler
    dogrulanmis = [i for i in islemler if i.get("dogrulandi") is not None]
    
    if not dogrulanmis:
        return {
            "total_roi": 0,
            "avg_roi_per_trade": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "avg_risk_reward": 0,
        }
    
    # ROI hesaplama (basitleştirilmiş: TP1=1R, TP2=2R, TP3=3R, SL=-1R)
    roi_list = []
    for i in dogrulanmis:
        sonuc = i.get("sonuc", "")
        if sonuc == "tp1":
            roi_list.append(1.0)
        elif sonuc == "tp2":
            roi_list.append(2.0)
        elif sonuc == "tp3":
            roi_list.append(3.0)
        elif sonuc == "stop_loss":
            roi_list.append(-1.0)
        else:
            roi_list.append(0.0)
    
    total_roi = sum(roi_list)
    avg_roi = total_roi / len(roi_list) if roi_list else 0
    
    # Win rate
    winning = [r for r in roi_list if r > 0]
    losing = [r for r in roi_list if r < 0]
    win_rate = (len(winning) / len(roi_list)) * 100 if roi_list else 0
    
    # Profit factor
    total_profit = sum(winning)
    total_loss = abs(sum(losing))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    # Ortalama risk/ödül
    risk_rewards = [i.get("risk_odul", 0) for i in dogrulanmis if i.get("risk_odul")]
    avg_rr = sum(risk_rewards) / len(risk_rewards) if risk_rewards else 0
    
    return {
        "total_roi": total_roi * 100,  # R cinsinden -> % ye çevir
        "avg_roi_per_trade": avg_roi * 100,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": len(dogrulanmis),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "avg_risk_reward": avg_rr,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# YENİ: GELİŞMİŞ GRAFİKLER
# ═══════════════════════════════════════════════════════════════════════════════

def zaman_serisi_performans_grafigi() -> Optional[io.BytesIO]:
    """
    Zaman içinde kümülatif performans grafiği
    
    Returns:
        BytesIO buffer (PNG) veya None
    """
    if not MATPLOTLIB_VAR:
        return None
    
    tahminler = tahminleri_yukle()
    dogrulanmis = [t for t in tahminler if t.get("dogrulandi") is not None]
    
    if not dogrulanmis:
        return None
    
    # Tarihe göre sırala
    dogrulanmis_sirali = sorted(dogrulanmis, key=lambda t: t.get("ts_utc", ""))
    
    # Kümülatif skor hesapla
    tarihler = []
    kumul_skor = []
    skor = 0
    
    for t in dogrulanmis_sirali:
        try:
            tarih = datetime.fromisoformat(t.get("ts_utc", ""))
            tarihler.append(tarih)
            skor += 1 if t.get("dogrulandi") is True else -1
            kumul_skor.append(skor)
        except Exception:
            continue
    
    if not tarihler:
        return None
    
    # Grafik oluştur
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    
    # Çizgi grafiği
    ax.plot(tarihler, kumul_skor, color='#16213e', linewidth=2.5, marker='o', 
            markersize=4, markerfacecolor='#0f3460', markeredgecolor='white', markeredgewidth=1)
    
    # Sıfır çizgisi
    ax.axhline(y=0, color='#e0e0e0', linestyle='--', linewidth=1, alpha=0.7)
    
    # Pozitif/negatif bölgeleri renklendir
    ax.fill_between(tarihler, kumul_skor, 0, where=[s >= 0 for s in kumul_skor],
                     color='#16213e', alpha=0.1, label='Pozitif')
    ax.fill_between(tarihler, kumul_skor, 0, where=[s < 0 for s in kumul_skor],
                     color='#e94560', alpha=0.1, label='Negatif')
    
    # Stil
    ax.set_xlabel('Tarih', fontsize=11, fontweight='600', color='#1a1a2e')
    ax.set_ylabel('Kümülatif Skor', fontsize=11, fontweight='600', color='#1a1a2e')
    ax.set_title('Zaman İçinde Performans Trendi', fontsize=14, fontweight='bold', 
                 color='#1a1a2e', pad=20)
    
    # Tarih formatı
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45, ha='right')
    
    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    ax.legend(loc='upper left', framealpha=0.9)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    return buf


def hizli_para_roi_grafigi() -> Optional[io.BytesIO]:
    """
    Hızlı Para Modu ROI grafiği (kümülatif)
    
    Returns:
        BytesIO buffer (PNG) veya None
    """
    if not MATPLOTLIB_VAR:
        return None
    
    islemler = hizli_para_islemlerini_yukle()
    dogrulanmis = [i for i in islemler if i.get("dogrulandi") is not None]
    
    if not dogrulanmis:
        return None
    
    # Tarihe göre sırala
    dogrulanmis_sirali = sorted(dogrulanmis, key=lambda i: i.get("ts_utc", ""))
    
    # Kümülatif ROI hesapla
    tarihler = []
    kumul_roi = []
    roi = 0
    
    for i in dogrulanmis_sirali:
        try:
            tarih = datetime.fromisoformat(i.get("ts_utc", ""))
            tarihler.append(tarih)
            
            sonuc = i.get("sonuc", "")
            if sonuc == "tp1":
                roi += 1.0
            elif sonuc == "tp2":
                roi += 2.0
            elif sonuc == "tp3":
                roi += 3.0
            elif sonuc == "stop_loss":
                roi -= 1.0
            
            kumul_roi.append(roi)
        except Exception:
            continue
    
    if not tarihler:
        return None
    
    # Grafik oluştur
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    
    # Çizgi grafiği
    ax.plot(tarihler, kumul_roi, color='#16213e', linewidth=2.5, marker='o',
            markersize=4, markerfacecolor='#0f3460', markeredgecolor='white', markeredgewidth=1)
    
    # Sıfır çizgisi
    ax.axhline(y=0, color='#e0e0e0', linestyle='--', linewidth=1, alpha=0.7)
    
    # Pozitif/negatif bölgeleri renklendir
    ax.fill_between(tarihler, kumul_roi, 0, where=[r >= 0 for r in kumul_roi],
                     color='#16213e', alpha=0.1)
    ax.fill_between(tarihler, kumul_roi, 0, where=[r < 0 for r in kumul_roi],
                     color='#e94560', alpha=0.1)
    
    # Stil
    ax.set_xlabel('Tarih', fontsize=11, fontweight='600', color='#1a1a2e')
    ax.set_ylabel('Kümülatif ROI (R)', fontsize=11, fontweight='600', color='#1a1a2e')
    ax.set_title('Hızlı Para Modu — ROI Performansı', fontsize=14, fontweight='bold',
                 color='#1a1a2e', pad=20)
    
    # Tarih formatı
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45, ha='right')
    
    # Grid
    ax.grid(axis='both', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Final ROI göster
    final_roi = kumul_roi[-1] if kumul_roi else 0
    ax.text(0.02, 0.98, f'Final ROI: {final_roi:+.1f}R ({final_roi*100:+.0f}%)',
            transform=ax.transAxes, fontsize=12, fontweight='bold',
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    return buf


def karsilastirmali_performans_grafigi() -> Optional[io.BytesIO]:
    """
    Modlar arası karşılaştırmalı performans grafiği
    
    Returns:
        BytesIO buffer (PNG) veya None
    """
    if not MATPLOTLIB_VAR:
        return None
    
    tahminler = tahminleri_yukle()
    
    # Mod bazlı performans
    mod_performans = {}
    for t in tahminler:
        if t.get("dogrulandi") is None:
            continue
        
        mod = t.get("mod", "bilinmeyen")
        if mod not in mod_performans:
            mod_performans[mod] = {"dogru": 0, "yanlis": 0}
        
        if t.get("dogrulandi") is True:
            mod_performans[mod]["dogru"] += 1
        else:
            mod_performans[mod]["yanlis"] += 1
    
    if not mod_performans:
        return None
    
    # Verileri hazırla
    modlar = []
    win_rates = []
    toplam_sayilar = []
    
    for mod, veri in mod_performans.items():
        toplam = veri["dogru"] + veri["yanlis"]
        if toplam > 0:
            modlar.append(mod.upper())
            win_rate = (veri["dogru"] / toplam) * 100
            win_rates.append(win_rate)
            toplam_sayilar.append(toplam)
    
    if not modlar:
        return None
    
    # Grafik oluştur
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor='white')
    
    # Sol: Win Rate
    bars1 = ax1.barh(modlar, win_rates, color='#16213e', alpha=0.85)
    for bar, rate, total in zip(bars1, win_rates, toplam_sayilar):
        ax1.text(rate + 2, bar.get_y() + bar.get_height() / 2,
                f'{rate:.1f}% ({total})',
                va='center', fontsize=9, fontweight='600')
    
    ax1.set_xlim(0, 110)
    ax1.set_xlabel('Win Rate (%)', fontsize=10, fontweight='600')
    ax1.set_title('Mod Bazlı Başarı Oranı', fontsize=12, fontweight='bold', pad=15)
    ax1.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Sağ: Toplam İşlem Sayısı
    bars2 = ax2.barh(modlar, toplam_sayilar, color='#0f3460', alpha=0.85)
    for bar, total in zip(bars2, toplam_sayilar):
        ax2.text(total + 0.5, bar.get_y() + bar.get_height() / 2,
                str(total), va='center', fontsize=9, fontweight='600')
    
    ax2.set_xlabel('Toplam İşlem', fontsize=10, fontweight='600')
    ax2.set_title('Mod Bazlı İşlem Hacmi', fontsize=12, fontweight='bold', pad=15)
    ax2.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    
    return buf


# ═══════════════════════════════════════════════════════════════════════════════
# YENİ: GELİŞMİŞ RAPORLAMA
# ═══════════════════════════════════════════════════════════════════════════════

def gelismis_backtest_raporu_html() -> str:
    """
    Gelişmiş backtest raporu HTML formatında
    
    Returns:
        HTML formatında detaylı rapor
    """
    # Temel metrikler
    from backtest import performans_ozeti, son_n_tahmin
    ozet = performans_ozeti()
    
    # Gelişmiş metrikler
    gelismis = gelismis_performans_metrikleri()
    
    # Hızlı Para ROI
    hp_roi = hizli_para_roi_hesapla()
    
    html = [
        "<b>◆ GELİŞMİŞ BACKTEST RAPORU</b>",
        "<b>━━━━━━━━━━━━━━━━━━━━</b>",
        "",
        "<b>📊 Temel Performans</b>",
        f"Toplam Tahmin: <b>{ozet['toplam']}</b>",
        f"Doğrulanan: <b>{ozet['dogrulanan']}</b>",
        f"Bekleyen: <b>{ozet['bekleyen']}</b>",
    ]
    
    if ozet['oran'] is not None:
        html.append(f"Win Rate: <b>{ozet['oran']:.1f}%</b>")
    
    html.append("")
    html.append("<b>📈 Gelişmiş Metrikler</b>")
    html.append(f"Profit Factor: <b>{gelismis['profit_factor']:.2f}</b>")
    html.append(f"Sharpe Ratio: <b>{gelismis['sharpe_ratio']:.2f}</b>")
    html.append(f"Max Drawdown: <b>{gelismis['max_drawdown']:.1f}%</b>")
    html.append(f"Max Ardışık Kazanç: <b>{gelismis['max_consecutive_wins']}</b>")
    html.append(f"Max Ardışık Kayıp: <b>{gelismis['max_consecutive_losses']}</b>")
    
    if hp_roi['total_trades'] > 0:
        html.append("")
        html.append("<b>⚡ Hızlı Para ROI</b>")
        html.append(f"Toplam ROI: <b>{hp_roi['total_roi']:+.1f}%</b>")
        html.append(f"İşlem Başına Ort: <b>{hp_roi['avg_roi_per_trade']:+.1f}%</b>")
        html.append(f"Win Rate: <b>{hp_roi['win_rate']:.1f}%</b>")
        html.append(f"Profit Factor: <b>{hp_roi['profit_factor']:.2f}</b>")
        html.append(f"Ort Risk/Ödül: <b>1:{hp_roi['avg_risk_reward']:.1f}</b>")
    
    html.append("")
    html.append("<b>━━━━━━━━━━━━━━━━━━━━</b>")
    html.append("<i>Detaylı grafikler için /backtest_grafik komutunu kullan</i>")
    
    return "\n".join(html)


if __name__ == "__main__":
    # Test
    print("=" * 60)
    print("GELİŞMİŞ BACKTEST SİSTEMİ TEST")
    print("=" * 60)
    
    gelismis = gelismis_performans_metrikleri()
    print(f"\nWin Rate: {gelismis['win_rate']:.1f}%")
    print(f"Profit Factor: {gelismis['profit_factor']:.2f}")
    print(f"Sharpe Ratio: {gelismis['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {gelismis['max_drawdown']:.1f}%")
    
    hp_roi = hizli_para_roi_hesapla()
    print(f"\nHızlı Para ROI: {hp_roi['total_roi']:+.1f}%")
    print(f"Win Rate: {hp_roi['win_rate']:.1f}%")
    
    print("\nGrafik oluşturuluyor...")
    if zaman_serisi_performans_grafigi():
        print("✓ Zaman serisi grafiği oluşturuldu")
    if hizli_para_roi_grafigi():
        print("✓ ROI grafiği oluşturuldu")
    if karsilastirmali_performans_grafigi():
        print("✓ Karşılaştırmalı grafik oluşturuldu")
