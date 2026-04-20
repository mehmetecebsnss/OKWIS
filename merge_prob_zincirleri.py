#!/usr/bin/env python3
"""
Prob Zinciri Birleştirme Script'i

AI'dan gelen yeni zincirleri mevcut dosyayla birleştirir.
Duplicate kontrolü yapar, istatistik gösterir.
"""

import json
from pathlib import Path
from datetime import datetime

# Dosya yolları
MEVCUT_DOSYA = Path(__file__).parent / "data" / "prob_zinciri.json"
YENI_DOSYA = Path(__file__).parent / "prob_zinciri_full.json"
YEDEK_KLASOR = Path(__file__).parent / "data" / "backups"


def yukle_json(dosya_yolu: Path) -> list:
    """JSON dosyasını yükle."""
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except FileNotFoundError:
        print(f"❌ Dosya bulunamadı: {dosya_yolu}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse hatası: {e}")
        return []


def kaydet_json(dosya_yolu: Path, data: list):
    """JSON dosyasını kaydet."""
    dosya_yolu.parent.mkdir(parents=True, exist_ok=True)
    with open(dosya_yolu, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def yedek_al(dosya_yolu: Path):
    """Mevcut dosyanın yedeğini al."""
    if not dosya_yolu.exists():
        return
    
    YEDEK_KLASOR.mkdir(parents=True, exist_ok=True)
    zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
    yedek_dosya = YEDEK_KLASOR / f"prob_zinciri_{zaman_damgasi}.json"
    
    with open(dosya_yolu, 'r', encoding='utf-8') as f:
        data = f.read()
    with open(yedek_dosya, 'w', encoding='utf-8') as f:
        f.write(data)
    
    print(f"✅ Yedek alındı: {yedek_dosya.name}")


def zincir_istatistik(zincirler: list) -> dict:
    """Zincir istatistiklerini hesapla."""
    if not zincirler:
        return {}
    
    kategoriler = {}
    modlar = {}
    varliklar = {}
    guven_seviyeleri = {"yuksek": 0, "orta": 0, "dusuk": 0}
    
    for z in zincirler:
        # Kategori
        kat = z.get("kategori", "bilinmeyen")
        kategoriler[kat] = kategoriler.get(kat, 0) + 1
        
        # Modlar
        for mod in z.get("ilgili_modlar", []):
            modlar[mod] = modlar.get(mod, 0) + 1
        
        # Varlıklar
        for varlik in z.get("ilgili_varliklar", []):
            varliklar[varlik] = varliklar.get(varlik, 0) + 1
        
        # Güven seviyesi
        guven = z.get("guven_seviyesi", "orta")
        if guven in guven_seviyeleri:
            guven_seviyeleri[guven] += 1
    
    return {
        "toplam": len(zincirler),
        "kategoriler": kategoriler,
        "modlar": modlar,
        "varliklar": varliklar,
        "guven_seviyeleri": guven_seviyeleri
    }


def birlestirilmis_istatistik_goster(mevcut: list, yeni: list, birlesik: list):
    """Birleştirme istatistiklerini göster."""
    print("\n" + "="*60)
    print("📊 BİRLEŞTİRME İSTATİSTİKLERİ")
    print("="*60)
    
    print(f"\n📁 Mevcut dosya: {len(mevcut)} zincir")
    print(f"📁 Yeni dosya: {len(yeni)} zincir")
    print(f"📁 Birleşik: {len(birlesik)} zincir")
    print(f"✨ Eklenen: {len(birlesik) - len(mevcut)} zincir")
    
    # Kategori dağılımı
    istat = zincir_istatistik(birlesik)
    
    print(f"\n📂 Kategori Dağılımı:")
    for kat, sayi in sorted(istat["kategoriler"].items(), key=lambda x: x[1], reverse=True):
        print(f"   {kat:15s}: {sayi:3d} zincir")
    
    print(f"\n🎯 Mod Dağılımı:")
    for mod, sayi in sorted(istat["modlar"].items(), key=lambda x: x[1], reverse=True):
        print(f"   {mod:15s}: {sayi:3d} zincir")
    
    print(f"\n💰 En Çok Kullanılan Varlıklar:")
    for varlik, sayi in sorted(istat["varliklar"].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {varlik:15s}: {sayi:3d} zincir")
    
    print(f"\n🎯 Güven Seviyesi:")
    for guven, sayi in istat["guven_seviyeleri"].items():
        emoji = {"yuksek": "🟢", "orta": "🟡", "dusuk": "🟠"}.get(guven, "⚪")
        print(f"   {emoji} {guven:10s}: {sayi:3d} zincir")
    
    print("\n" + "="*60)


def main():
    print("🔗 PROB ZİNCİRİ BİRLEŞTİRME ARACI")
    print("="*60)
    
    # 1. Dosyaları yükle
    print("\n📂 Dosyalar yükleniyor...")
    mevcut = yukle_json(MEVCUT_DOSYA)
    yeni = yukle_json(YENI_DOSYA)
    
    if not yeni:
        print("❌ Yeni dosya bulunamadı veya boş: prob_zinciri_full.json")
        print("💡 Önce AI'dan zincirleri üret ve bu dosyaya kaydet.")
        return
    
    print(f"✅ Mevcut: {len(mevcut)} zincir")
    print(f"✅ Yeni: {len(yeni)} zincir")
    
    # 2. Yedek al
    print("\n💾 Yedek alınıyor...")
    yedek_al(MEVCUT_DOSYA)
    
    # 3. Birleştir (ID'ye göre dedupe)
    print("\n🔄 Birleştiriliyor...")
    mevcut_ids = {z.get("id") for z in mevcut if z.get("id")}
    eklenen = 0
    duplicate = 0
    
    for zincir in yeni:
        zincir_id = zincir.get("id")
        if not zincir_id:
            print(f"⚠️  ID eksik zincir atlandı: {zincir.get('baslik', 'N/A')}")
            continue
        
        if zincir_id in mevcut_ids:
            duplicate += 1
        else:
            mevcut.append(zincir)
            mevcut_ids.add(zincir_id)
            eklenen += 1
    
    print(f"✅ {eklenen} yeni zincir eklendi")
    if duplicate > 0:
        print(f"⚠️  {duplicate} duplicate zincir atlandı")
    
    # 4. Kaydet
    print("\n💾 Kaydediliyor...")
    kaydet_json(MEVCUT_DOSYA, mevcut)
    print(f"✅ Kaydedildi: {MEVCUT_DOSYA}")
    
    # 5. İstatistik göster
    birlestirilmis_istatistik_goster(
        yukle_json(YEDEK_KLASOR / sorted(YEDEK_KLASOR.glob("*.json"))[-1]) if YEDEK_KLASOR.exists() else [],
        yeni,
        mevcut
    )
    
    print("\n✨ Birleştirme tamamlandı!")
    print(f"📁 Toplam zincir sayısı: {len(mevcut)}")


if __name__ == "__main__":
    main()
