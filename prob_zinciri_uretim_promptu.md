# PROB ZİNCİRİ ÜRETİM PROMPTU

## GÖREV
Okwis AI yatırım asistanı için **200+ sosyal ihtimal zinciri** üret. Bu zincirler, makro olayların finansal piyasalara etkisini modelleyen neden-sonuç ilişkileridir.

---

## HEDEF YAPISAL FORMAT (JSON)

```json
{
  "id": "benzersiz_id_snake_case",
  "baslik": "Kısa Açıklayıcı Başlık",
  "kategori": "mevsimsel|emtia|kripto|jeopolitik|makro|sektor|afet|sosyal",
  "tetikleyici": "Hangi olay bu zinciri başlatır?",
  "zincir": [
    {
      "adim": 1,
      "olay": "İlk olay",
      "etki": "Bu olayın somut etkisi (sayısal tahmin varsa ekle)",
      "olasilik": 0.85,
      "tarihsel_referans": "2021 Aralık, Avrupa gaz krizi"
    },
    {
      "adim": 2,
      "olay": "İkinci olay",
      "etki": "Zincirleme etki",
      "olasilik": 0.70,
      "tarihsel_referans": "2008 Finansal Kriz"
    }
    // 3-7 adım arası
  ],
  "anti_tez": "Hangi durumda bu zincir çalışmaz? Ters senaryo",
  "net_etki": "Özet: Bu zincirin sonucu ne?",
  "ilgili_modlar": ["mevsim", "hava", "jeopolitik", "sektor", "trendler", "magazin", "ozel_gun", "dogal_afet"],
  "ilgili_varliklar": ["petrol", "altın", "bitcoin", "hisse", "tahvil", "dolar"],
  "gerceklesme_orani": 0.78,
  "guven_seviyesi": "yuksek|orta|dusuk",
  "zaman_ufku": "kisa_vade|orta_vade|uzun_vade",
  "son_guncelleme": "2026-04-20",
  "kaynaklar": ["Tarihsel veri", "Akademik çalışma", "Piyasa gözlemi"]
}
```

---

## KATEGORİLER VE HEDEF SAYILAR

### 1. MevsimSEL İHTİMALLER (50 zincir)

**Alt Kategoriler:**
- **Kış Etkileri** (15 zincir)
  - Enerji talebi artışı (doğalgaz, elektrik, kömür)
  - Isınma ekipmanları satışı
  - Kış turizmi (kayak, termal)
  - Lojistik maliyetleri (kar, buz)
  - Emlak piyasası durgunluğu
  - E-ticaret artışı (evde kalma)
  - Gıda stoklaması
  - Sağlık harcamaları (grip, soğuk algınlığı)
  
- **Yaz Etkileri** (15 zincir)
  - Klima/soğutma talebi
  - Turizm patlaması
  - Tarımsal hasat dönemleri
  - İnşaat sektörü hızlanması
  - Enerji talebi (klima)
  - Havayolu trafiği
  - Dondurma/içecek satışları
  - Tatil harcamaları
  
- **İlkbahar Etkileri** (10 zincir)
  - Tarım ekimi
  - İnşaat başlangıcı
  - Otomotiv satışları
  - Moda/giyim sezonu
  - Emlak hareketliliği
  
- **Sonbahar Etkileri** (10 zincir)
  - Okul dönemi harcamaları
  - Hasat sonrası emtia fiyatları
  - Kış hazırlığı stoklaması
  - Teknoloji ürünleri (yeni sezon)

**Örnek Zincir:**
```json
{
  "id": "kis_dogalgaz_talep_artisi",
  "baslik": "Kış Ayı Doğalgaz Talep Patlaması",
  "kategori": "mevsimsel",
  "tetikleyici": "Hava sıcaklığı 5°C altına düşer ve 2+ hafta kalır",
  "zincir": [
    {
      "adim": 1,
      "olay": "Isınma talebi patlar",
      "etki": "Konut ve ticari doğalgaz tüketimi %40-60 artar",
      "olasilik": 0.95,
      "tarihsel_referans": "2021 Aralık Avrupa, 2022 Ocak Türkiye"
    },
    {
      "adim": 2,
      "olay": "Spot gaz fiyatları yükselir",
      "etki": "TTF ve spot LNG fiyatları %20-50 premium yapar",
      "olasilik": 0.85,
      "tarihsel_referans": "2021-2022 Avrupa enerji krizi"
    },
    {
      "adim": 3,
      "olay": "Enerji hisseleri yükselir",
      "etki": "SNGAZ, AKSEN, AKENR gibi hisseler %15-30 kazanır",
      "olasilik": 0.75,
      "tarihsel_referans": "BIST Enerji endeksi 2021 Q4"
    },
    {
      "adim": 4,
      "olay": "Elektrik üretim maliyeti artar",
      "etki": "Elektrik fiyatları %10-25 yükselir",
      "olasilik": 0.70,
      "tarihsel_referans": "2022 Ocak Türkiye"
    },
    {
      "adim": 5,
      "olay": "Enflasyon baskısı",
      "etki": "Enerji enflasyonu genel TÜFE'yi %0.5-1.5 puan iter",
      "olasilik": 0.60,
      "tarihsel_referans": "2022 Şubat TÜFE"
    }
  ],
  "anti_tez": "Sıcak kış senaryosu: Sıcaklık 10°C üzerinde kalırsa talep düşer, fiyatlar baskıda",
  "net_etki": "Kış aylarında enerji sektörü %15-30 outperform yapar, enflasyon riski artar",
  "ilgili_modlar": ["mevsim", "hava", "sektor"],
  "ilgili_varliklar": ["dogalgaz", "petrol", "enerji_hisseleri"],
  "gerceklesme_orani": 0.88,
  "guven_seviyesi": "yuksek",
  "zaman_ufku": "kisa_vade",
  "son_guncelleme": "2026-04-20",
  "kaynaklar": ["EPDK verileri", "BIST tarihsel", "IEA raporları"]
}
```

---

### 2. EMTİA İHTİMALLERİ (40 zincir)

**Alt Kategoriler:**
- **Petrol** (10 zincir)
  - OPEC kararları
  - Jeopolitik riskler (Orta Doğu)
  - Stok seviyeleri (EIA, IEA)
  - Dolar kuru ilişkisi
  - Talep döngüleri (yaz/kış)
  - Rafineri marjları
  - Alternatif enerji rekabeti
  
- **Altın** (8 zincir)
  - Enflasyon koruması
  - Faiz oranı ilişkisi (ters korelasyon)
  - Dolar kuru (ters korelasyon)
  - Jeopolitik güvenli liman
  - Merkez bankası alımları
  - Takı talebi (Hindistan, Çin)
  
- **Tarım Emtiaları** (12 zincir)
  - Buğday: Kuraklık, Ukrayna üretimi
  - Mısır: ABD hasadı, etanol talebi
  - Soya: Çin talebi, Brezilya üretimi
  - Kahve: Brezilya don olayları
  - Kakao: Fildişi Sahili üretimi
  - Şeker: Hindistan, Brezilya
  
- **Endüstriyel Metaller** (10 zincir)
  - Bakır: Küresel büyüme göstergesi
  - Demir: Çin inşaat sektörü
  - Alüminyum: Enerji maliyetleri
  - Lityum: EV talebi

**Örnek:**
```json
{
  "id": "altin_enflasyon_faiz_iliskisi",
  "baslik": "Altın: Enflasyon-Faiz Dengesi",
  "kategori": "emtia",
  "tetikleyici": "Enflasyon %5+ ama reel faiz negatif",
  "zincir": [
    {
      "adim": 1,
      "olay": "Yüksek enflasyon açıklanır",
      "etki": "Satın alma gücü erozyonu korkusu",
      "olasilik": 0.90,
      "tarihsel_referans": "2021-2022 küresel enflasyon dalgası"
    },
    {
      "adim": 2,
      "olay": "Merkez bankası faiz artırımı yetersiz",
      "etki": "Reel faiz negatif kalır (nominal faiz < enflasyon)",
      "olasilik": 0.75,
      "tarihsel_referans": "Fed 2021 geç kaldı"
    },
    {
      "adim": 3,
      "olay": "Altına talep artar",
      "etki": "Altın fiyatı %10-30 yükselir",
      "olasilik": 0.80,
      "tarihsel_referans": "2020-2021 altın rallisi"
    },
    {
      "adim": 4,
      "olay": "Dolar zayıflar",
      "etki": "Altın daha da güçlenir (ters korelasyon)",
      "olasilik": 0.65,
      "tarihsel_referans": "2020 dolar zayıflığı"
    }
  ],
  "anti_tez": "Agresif faiz artırımı: Reel faiz pozitife döner, altın baskılanır",
  "net_etki": "Negatif reel faiz ortamında altın %15-40 kazandırır",
  "ilgili_modlar": ["mevsim", "jeopolitik", "sektor"],
  "ilgili_varliklar": ["altın", "gümüş", "tahvil"],
  "gerceklesme_orani": 0.82,
  "guven_seviyesi": "yuksek",
  "zaman_ufku": "orta_vade",
  "son_guncelleme": "2026-04-20",
  "kaynaklar": ["Fed verileri", "Altın tarihsel fiyat", "Akademik çalışmalar"]
}
```

---

### 3. KRİPTO İHTİMALLERİ (30 zincir)

**Alt Kategoriler:**
- **Bitcoin** (12 zincir)
  - Halving döngüsü
  - Makro risk ortamı
  - Kurumsal benimseme
  - Regülasyon haberleri
  - Hash rate değişimleri
  - ETF onayları
  
- **Altcoin/DeFi** (10 zincir)
  - Ethereum: Gas ücretleri, DeFi TVL
  - Layer 2 çözümleri
  - NFT trendleri
  - Stablecoin regülasyonu
  
- **Kripto-Makro İlişkisi** (8 zincir)
  - Fed faiz kararları
  - Dolar kuru
  - Teknoloji hisseleri korelasyonu
  - Risk iştahı

**Örnek:**
```json
{
  "id": "bitcoin_halving_dongusu",
  "baslik": "Bitcoin Halving Döngüsü",
  "kategori": "kripto",
  "tetikleyici": "Bitcoin halving olayı (her 4 yılda bir)",
  "zincir": [
    {
      "adim": 1,
      "olay": "Halving gerçekleşir",
      "etki": "Madenci ödülü yarıya iner, arz şoku",
      "olasilik": 1.0,
      "tarihsel_referans": "2012, 2016, 2020 halving'leri"
    },
    {
      "adim": 2,
      "olay": "Arz daralması algısı",
      "etki": "Yatırımcılar stoklamaya başlar",
      "olasilik": 0.85,
      "tarihsel_referans": "2020 halving öncesi birikim"
    },
    {
      "adim": 3,
      "olay": "Fiyat yükselişi (6-18 ay sonra)",
      "etki": "Bitcoin %200-500 kazanır",
      "olasilik": 0.75,
      "tarihsel_referans": "2013, 2017, 2021 bull run'ları"
    },
    {
      "adim": 4,
      "olay": "Altcoin sezonu",
      "etki": "Bitcoin dominansı düşer, altcoinler patlar",
      "olasilik": 0.70,
      "tarihsel_referans": "2017 Q4, 2021 Q1"
    },
    {
      "adim": 5,
      "olay": "Zirve ve düzeltme",
      "etki": "Halving sonrası 12-18 ayda zirve, sonra %50-80 düşüş",
      "olasilik": 0.80,
      "tarihsel_referans": "2018, 2022 bear market'leri"
    }
  ],
  "anti_tez": "Makro kriz: Halving olsa da risk iştahı yoksa fiyat yükselmez",
  "net_etki": "Halving sonrası 12-18 ayda Bitcoin tarihi zirve yapar, sonra düzeltme",
  "ilgili_modlar": ["trendler", "sektor"],
  "ilgili_varliklar": ["bitcoin", "ethereum", "altcoin"],
  "gerceklesme_orani": 0.75,
  "guven_seviyesi": "yuksek",
  "zaman_ufku": "uzun_vade",
  "son_guncelleme": "2026-04-20",
  "kaynaklar": ["Bitcoin tarihsel fiyat", "Glassnode verileri"]
}
```

---

### 4. JEOPOLİTİK İHTİMALLER (40 zincir)

**Alt Kategoriler:**
- **Savaş/Çatışma** (15 zincir)
  - Orta Doğu: Petrol, savunma
  - Ukrayna: Tahıl, enerji
  - Tayvan: Yarı iletken
  - Kore: Teknoloji, savunma
  
- **Yaptırım/Ambargo** (10 zincir)
  - Rusya: Enerji, tahıl
  - İran: Petrol
  - Çin: Teknoloji, nadir toprak
  
- **Ticaret Savaşları** (8 zincir)
  - ABD-Çin: Teknoloji, tarım
  - AB-ABD: Otomotiv, tarım
  
- **Seçimler** (7 zincir)
  - ABD başkanlık: Vergi, regülasyon
  - Avrupa: Enerji politikaları
  - Gelişmekte olan: Döviz, tahvil

---

### 5. MAKRO İHTİMALLER (30 zincir)

**Alt Kategoriler:**
- **Faiz Döngüleri** (10 zincir)
  - Faiz artırımı: Tahvil, hisse, döviz
  - Faiz indirimi: Risk iştahı, büyüme
  - Ters yield curve: Resesyon sinyali
  
- **Enflasyon** (8 zincir)
  - Yüksek enflasyon: Emtia, altın
  - Deflasyon: Tahvil, nakit
  
- **Büyüme/Resesyon** (7 zincir)
  - Güçlü büyüme: Hisse, emtia
  - Resesyon: Tahvil, savunmacı sektörler
  
- **Döviz Kuru** (5 zincir)
  - Dolar güçlenmesi: Emtia baskısı
  - Dolar zayıflaması: Emtia yükselişi

---

### 6. SEKTÖREL İHTİMALLER (20 zincir)

- **Teknoloji** (5 zincir)
  - AI patlaması
  - Yarı iletken döngüsü
  - Cloud computing
  
- **Enerji** (5 zincir)
  - Yeşil enerji geçişi
  - Nükleer rönesans
  
- **Sağlık** (5 zincir)
  - Yaşlanan nüfus
  - Biyoteknoloji
  
- **Finans** (5 zincir)
  - Faiz marjları
  - Fintech rekabeti

---

### 7. DOĞAL AFET İHTİMALLERİ (15 zincir)

- **Deprem** (5 zincir)
  - İnşaat, sigorta, yeniden yapılanma
  
- **Sel/Kasırga** (5 zincir)
  - Tarım hasarı, sigorta
  
- **Kuraklık** (5 zincir)
  - Tarım emtiaları, su teknolojileri

---

### 8. SOSYAL/VİRAL İHTİMALLER (15 zincir)

- **Boykot Hareketleri** (5 zincir)
- **Viral Trendler** (5 zincir)
- **Ünlü Etkileri** (5 zincir)

---

## KALİTE KRİTERLERİ

Her zincir için:

1. **Olasılık Değerleri Gerçekçi Olmalı**
   - İlk adım: 0.80-0.95 (yüksek kesinlik)
   - Son adımlar: 0.50-0.70 (belirsizlik artar)

2. **Tarihsel Referans Zorunlu**
   - En az 1 somut örnek
   - Tarih + olay adı

3. **Sayısal Tahminler**
   - "Yükselir" değil "%10-30 yükselir"
   - "Düşer" değil "%5-15 düşer"

4. **Anti-Tez Mutlaka Olmalı**
   - Hangi durumda zincir çalışmaz?
   - Ters senaryo nedir?

5. **Gerçekleşme Oranı**
   - Geçmiş 10 yılda kaç kez doğru çıktı?
   - 0.60-0.70: Orta güven
   - 0.70-0.85: Yüksek güven
   - 0.85+: Çok yüksek güven

---

## ÇIKTI FORMATI

**Tek bir JSON dosyası oluştur:**
```json
[
  {zincir1},
  {zincir2},
  ...
  {zincir200}
]
```

**Dosya adı:** `prob_zinciri_full.json`

---

## ÖNCELİKLENDİRME

1. **Önce yüksek güvenilirlik zincirleri** (gerçekleşme oranı 0.75+)
2. **Sonra orta güvenilirlik** (0.60-0.75)
3. **En son düşük güvenilirlik** (0.50-0.60)

---

## ÖRNEKLER (Her Kategoriden 1)

### Mevsimsel
✅ Yukarıda verildi (Kış doğalgaz)

### Emtia
✅ Yukarıda verildi (Altın-enflasyon)

### Kripto
✅ Yukarıda verildi (Bitcoin halving)

### Jeopolitik
```json
{
  "id": "orta_dogu_gerilim_petrol",
  "baslik": "Orta Doğu Gerilimi → Petrol Fiyat Şoku",
  "kategori": "jeopolitik",
  "tetikleyici": "İran-İsrail veya Suudi Arabistan bölgesinde askeri gerilim",
  "zincir": [
    {
      "adim": 1,
      "olay": "Gerilim tırmanır",
      "etki": "Risk algısı artar, güvenli liman talebi",
      "olasilik": 0.85,
      "tarihsel_referans": "2020 Ocak Süleymani suikastı"
    },
    {
      "adim": 2,
      "olay": "Petrol arz riski",
      "etki": "Hormuz Boğazı veya boru hatları risk altında",
      "olasilik": 0.70,
      "tarihsel_referans": "2019 Suudi Aramco saldırısı"
    },
    {
      "adim": 3,
      "olay": "Petrol fiyatı patlar",
      "etki": "Brent %15-40 yükselir",
      "olasilik": 0.75,
      "tarihsel_referans": "2019 Eylül +%15 tek günde"
    },
    {
      "adim": 4,
      "olay": "Enerji hisseleri yükselir",
      "etki": "XLE, enerji ETF'leri %10-25 kazanır",
      "olasilik": 0.70,
      "tarihsel_referans": "2022 Ukrayna sonrası"
    },
    {
      "adim": 5,
      "olay": "Enflasyon baskısı",
      "etki": "Küresel enflasyon %0.5-1.5 puan artar",
      "olasilik": 0.60,
      "tarihsel_referans": "2022 enerji enflasyonu"
    }
  ],
  "anti_tez": "Hızlı diplomasi: Gerilim 1-2 hafta içinde çözülürse fiyatlar normale döner",
  "net_etki": "Orta Doğu gerilimi petrol ve enerji hisselerini %15-40 yukarı iter",
  "ilgili_modlar": ["jeopolitik", "sektor"],
  "ilgili_varliklar": ["petrol", "dogalgaz", "enerji_hisseleri", "altin"],
  "gerceklesme_orani": 0.80,
  "guven_seviyesi": "yuksek",
  "zaman_ufku": "kisa_vade",
  "son_guncelleme": "2026-04-20",
  "kaynaklar": ["EIA verileri", "Tarihsel petrol fiyat", "Jeopolitik analiz"]
}
```

### Makro
```json
{
  "id": "fed_faiz_artirimi_hisse_baski",
  "baslik": "Fed Faiz Artırımı → Hisse Baskısı",
  "kategori": "makro",
  "tetikleyici": "Fed 0.50%+ faiz artırımı açıklar veya sinyali verir",
  "zincir": [
    {
      "adim": 1,
      "olay": "Faiz artırımı açıklanır",
      "etki": "Tahvil getirileri yükselir",
      "olasilik": 0.95,
      "tarihsel_referans": "2022-2023 Fed döngüsü"
    },
    {
      "adim": 2,
      "olay": "Hisse değerlemeleri baskılanır",
      "etki": "P/E oranları düşer, özellikle büyüme hisseleri",
      "olasilik": 0.85,
      "tarihsel_referans": "2022 teknoloji hisse düşüşü"
    },
    {
      "adim": 3,
      "olay": "Dolar güçlenir",
      "etki": "DXY endeksi %2-5 yükselir",
      "olasilik": 0.75,
      "tarihsel_referans": "2022 dolar rallisi"
    },
    {
      "adim": 4,
      "olay": "Gelişmekte olan piyasalar baskıda",
      "etki": "EM hisseleri ve dövizleri %5-15 düşer",
      "olasilik": 0.70,
      "tarihsel_referans": "2022 EM düşüşü"
    },
    {
      "adim": 5,
      "olay": "Resesyon riski artar",
      "etki": "Savunmacı sektörler (sağlık, gıda) outperform yapar",
      "olasilik": 0.55,
      "tarihsel_referans": "2023 Q1 banka krizi"
    }
  ],
  "anti_tez": "Soft landing: Enflasyon hızla düşer, Fed duraklar, hisseler toparlanır",
  "net_etki": "Faiz artırımı döngüsünde hisseler %10-30 düşer, tahvil ve dolar güçlenir",
  "ilgili_modlar": ["mevsim", "jeopolitik", "sektor"],
  "ilgili_varliklar": ["hisse", "tahvil", "dolar", "altin"],
  "gerceklesme_orani": 0.82,
  "guven_seviyesi": "yuksek",
  "zaman_ufku": "orta_vade",
  "son_guncelleme": "2026-04-20",
  "kaynaklar": ["Fed verileri", "S&P 500 tarihsel", "Akademik çalışmalar"]
}
```

---

## SON TALİMATLAR

1. **200+ zincir üret** (kategorilere göre dağıt)
2. **Her zincir 3-7 adım** olsun
3. **Tarihsel referans zorunlu**
4. **Sayısal tahminler ekle**
5. **Anti-tez mutlaka olsun**
6. **Gerçekleşme oranı gerçekçi olsun**
7. **JSON formatı hatasız olsun**

---

## BAŞARI KRİTERLERİ

✅ 200+ zincir
✅ Her kategori dolu
✅ Tarihsel referanslar var
✅ Sayısal tahminler var
✅ Anti-tezler var
✅ JSON formatı geçerli
✅ Gerçekleşme oranları mantıklı

---

**BAŞLA!** 🚀
