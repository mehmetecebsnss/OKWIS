"""
Görsel oluşturucu test scripti
"""

from gorsel_olusturucu import gorsel_olusturucu_al
from datetime import datetime

def test_guven_grafigi():
    """Güven skoru grafiği testi"""
    print("🧪 Güven skoru grafiği oluşturuluyor...")
    
    gorsel = gorsel_olusturucu_al()
    buffer = gorsel.guven_skoru_grafigi(
        guven_skoru=78,
        veri_kalitesi=85,
        mod_basarisi=72,
        ulke="Türkiye",
        mod="Okwis"
    )
    
    if buffer:
        # Test için dosyaya kaydet
        with open("test_guven_grafigi.png", "wb") as f:
            f.write(buffer.getvalue())
        print("✅ Güven grafiği oluşturuldu: test_guven_grafigi.png")
        return True
    else:
        print("❌ Güven grafiği oluşturulamadı")
        return False


def test_prob_zinciri_infografik():
    """Olasılık zincirleri infografiği testi"""
    print("\n🧪 Olasılık zincirleri infografiği oluşturuluyor...")
    
    gorsel = gorsel_olusturucu_al()
    
    test_zincirler = [
        {"baslik": "Mevsimsel Tüketim Döngüsü", "olasilik": 0.75, "kategori": "mevsimsel"},
        {"baslik": "Jeopolitik Enerji Kanalı", "olasilik": 0.68, "kategori": "jeopolitik"},
        {"baslik": "Enflasyon Beklenti Zinciri", "olasilik": 0.55, "kategori": "makro"},
        {"baslik": "Teknoloji Sektör Rotasyonu", "olasilik": 0.82, "kategori": "sektor"},
        {"baslik": "Kripto Düzenleme Etkisi", "olasilik": 0.45, "kategori": "kripto"},
    ]
    
    buffer = gorsel.prob_zinciri_infografik(
        aktif_zincirler=test_zincirler,
        ulke="Türkiye",
        varlik="Altın"
    )
    
    if buffer:
        with open("test_prob_zinciri.png", "wb") as f:
            f.write(buffer.getvalue())
        print("✅ Prob zinciri infografiği oluşturuldu: test_prob_zinciri.png")
        return True
    else:
        print("❌ Prob zinciri infografiği oluşturulamadı")
        return False


def test_pdf_rapor():
    """PDF rapor testi"""
    print("\n🧪 PDF rapor oluşturuluyor...")
    
    gorsel = gorsel_olusturucu_al()
    
    test_analiz = """
Türkiye ekonomisi Mayıs 2026'da kritik bir dönemden geçiyor. Enflasyon baskısı devam ederken, 
merkez bankası sıkı para politikasını sürdürüyor.

KISA VADE (1-2 hafta):
Altın fiyatları dolar kuru baskısı altında. Yerel yatırımcılar için gram altın 2.500 TL 
seviyesinde direniş gösteriyor. Kısa vadede yatay seyir bekleniyor.

ORTA VADE (1-3 ay):
Jeopolitik riskler artarsa altın güvenli liman olarak öne çıkabilir. Merkez bankası faiz 
kararları kritik. Faiz artışı altını baskılayabilir.

UZUN VADE (3-12 ay):
Enflasyon düşüş trendine girerse altın talebi azalabilir. Ancak küresel belirsizlik devam 
ederse altın portföyde yer almalı.

TERS SENARYO:
Dolar/TL 35'in altına düşerse ve enflasyon hızla düşerse altın cazibesini kaybeder. 
Bu durumda hisse senetleri ve tahviller daha cazip olabilir.
"""
    
    buffer = gorsel.pdf_rapor_olustur(
        analiz_metni=test_analiz,
        ulke="Türkiye",
        mod="Okwis",
        varlik="Altın",
        guven_skoru=78,
        tarih=datetime.now()
    )
    
    if buffer:
        with open("test_rapor.pdf", "wb") as f:
            f.write(buffer.getvalue())
        print("✅ PDF rapor oluşturuldu: test_rapor.pdf")
        return True
    else:
        print("❌ PDF rapor oluşturulamadı")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("🎨 OKWIS GÖRSEL OLUŞTURUCU TEST")
    print("=" * 50)
    
    sonuclar = []
    
    sonuclar.append(("Güven Grafiği", test_guven_grafigi()))
    sonuclar.append(("Prob Zinciri İnfografiği", test_prob_zinciri_infografik()))
    sonuclar.append(("PDF Rapor", test_pdf_rapor()))
    
    print("\n" + "=" * 50)
    print("📊 TEST SONUÇLARI")
    print("=" * 50)
    
    for isim, basarili in sonuclar:
        durum = "✅ BAŞARILI" if basarili else "❌ BAŞARISIZ"
        print(f"{isim}: {durum}")
    
    basarili_sayisi = sum(1 for _, b in sonuclar if b)
    print(f"\nToplam: {basarili_sayisi}/{len(sonuclar)} test başarılı")
    
    if basarili_sayisi == len(sonuclar):
        print("\n🎉 Tüm testler başarılı! Görsel çıktı sistemi hazır.")
    else:
        print("\n⚠️ Bazı testler başarısız. Loglara bakın.")
