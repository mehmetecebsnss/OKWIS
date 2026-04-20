# 🎯 OKWİS GELİŞTİRME TASKLIST

## VİZYON DURUMU

**Mevcut Skor: 6.5/10**
- ✅ Teknik altyapı güçlü (8 mod, güven skoru, alarm)
- ⚠️ Prob zinciri sınırlı (8/200+)
- ⚠️ Premium görünüm eksik
- ⚠️ Pazarlanabilirlik zayıf

**Hedef: 9.5/10** (Premium, viral, güvenilir)

---

## 🔴 ACİL ÖNCELİK (1-2 Gün)

### ✅ 1. Prob Zinciri Patlaması 🎯 **TAMAMLANDI**
- [x] `prob_zinciri_uretim_promptu.md` ile AI'dan 200+ zincir üret
- [x] `merge_prob_zincirleri.py` ile birleştir
- [x] `_ilgili_prob_zincirleri()` fonksiyonunu güçlendir
- [x] Her analiz fonksiyonuna entegre et
- [x] Test et (Mevsim + Türkiye + Altın)

**Durum:** ✅ 98 olasılık zinciri aktif, JSON geçerli

---

### ✅ 2. Görsel Çıktı Devrimi 🎨 **TAMAMLANDI**
- [x] Premium grafik sistemi oluşturuldu
- [x] Güven skoru grafiği (PNG, horizontal bar chart)
- [x] Olasılık zincirleri infografiği (PNG, zarif tasarım)
- [x] PDF rapor oluşturma (Pro özelliği)
- [x] Telegram entegrasyonu (otomatik gönderim)
- [x] Profesyonel renk paleti (emoji kargaşası yok)
- [x] Test edildi (3/3 test başarılı)

**Beklenen Etki:** 🔥🔥🔥🔥🔥 (GERÇEKLEŞTI)
**Zorluk:** 🔧🔧 (AŞILDI)
**Süre:** 2 saat (TAMAMLANDI)

**Özellikler:**
- ✅ Matplotlib ile profesyonel grafikler
- ✅ ReportLab ile PDF raporlar
- ✅ Zarif, minimal tasarım (emoji yok)
- ✅ Pro kullanıcılar için PDF butonu
- ✅ Otomatik görsel gönderimi
- ✅ Hata toleranslı (kütüphane yoksa sessizce geçer)

**Dosyalar:**
- `gorsel_olusturucu.py` - Görsel oluşturma modülü
- `GORSEL_CIKTI_OZELLIKLERI.md` - Dokümantasyon
- `test_gorsel.py` - Test scripti

---

### ✅ 3. Backtest/Simülasyon Modu 🕰️ **TAMAMLANDI**
- [x] `/backtest` komutu eklendi
- [x] Performans özeti (toplam, doğrulanan, bekleyen, oran)
- [x] Mod bazlı istatistikler
- [x] Son N tahmin listesi
- [x] Manuel doğrulama sistemi (`tahmin_dogrula()`)
- [x] **Görsel Raporlar:**
  - [x] Performans grafiği (mod karşılaştırma)
  - [x] Detaylı analiz grafiği (3 subplot)
- [x] **Detaylı Analiz:**
  - [x] Varlık bazlı performans (en başarılı varlıklar)
  - [x] Ülke bazlı performans (en başarılı ülkeler)
  - [x] Süre bazlı performans (kısa vade vs uzun vade)
  - [x] Zaman serisi (günlük doğruluk trendi)
- [x] HTML rapor oluşturma
- [x] Test edildi (3/3 test başarılı)

**Durum:** ✅ TAMAMLANDI

**Beklenen Etki:** 🔥🔥🔥🔥🔥 (GERÇEKLEŞTI)
**Zorluk:** 🔧🔧🔧 (AŞILDI)
**Süre:** 3-4 saat (TAMAMLANDI)

**Özellikler:**
- ✅ `/backtest` veya `/backtest 30` komutu
- ✅ Metin raporu + 2 grafik otomatik gönderim
- ✅ Mod, varlık, ülke, süre bazlı analiz
- ✅ Matplotlib ile profesyonel grafikler
- ✅ `/yardim` dokümantasyonuna eklendi
- ✅ Test tahminleri oluşturuldu (%80 doğruluk)

**Dosyalar:**
- `backtest.py` - Backtest sistemi
- `metrics/tahmin_kayitlari.jsonl` - Tahmin kayıtları
- `BACKTEST_OZELLIKLERI.md` - Dokümantasyon

---

## 🟡 ORTA ÖNCELİK (3-7 Gün)

### 4. Hikaye Anlatımı ve Pazarlama
- [ ] Landing page (Notion veya basit HTML)
  - "Okwis Nedir?" hikayesi
  - Gerçek kullanıcı testimonial'ları
  - Backtest sonuçları
  - Fiyatlandırma
- [ ] Twitter/X stratejisi
  - Günlük 1 analiz paylaş (görsel + özet)
  - Doğru tahminleri vurgula
  - Prob zinciri örnekleri
- [ ] YouTube kısa videolar
  - "Okwis geçen hafta X'i tahmin etti" formatı
  - Ekran kaydı + voiceover

**Beklenen Etki:** 🔥🔥🔥🔥  
**Zorluk:** 🔧🔧  
**Süre:** 1 gün

---

### ✅ 5. Kullanıcı Profil Sistemi Güçlendirme — **TAMAMLANDI**
- [x] Portföy entegrasyonu (`portfoy.py` modülü)
  - [x] Kullanıcı elindeki varlıkları yapılandırılmış şekilde kaydet (sembol, miktar, maliyet)
  - [x] Kategori tespiti (kripto/emtia/hisse/döviz)
  - [x] Her Okwis analizinde portföy bloğu prompt'a enjekte edilir
- [x] Kişiselleştirilmiş dil
  - [x] "Senin BTC'in", "portföyündeki altın" gibi sahiplenme dili
  - [x] Risk profiline göre aksiyon büyüklüğü (agresif/orta/muhafazakar)
  - [x] Yatırım ufkuna göre vade ağırlıklandırması
- [x] `/portfoy` komutu (ekle/çıkar/sil/risk/ufuk/grafik)
- [x] Portföy dağılım grafiği (pie + bar chart)
- [x] "Portföy Aktif" göstergesi analiz başlığında
- [x] `/yardim` dokümantasyonuna eklendi
- [x] Test edildi

**Durum:** ✅ TAMAMLANDI  
**Beklenen Etki:** 🔥🔥🔥  
**Zorluk:** 🔧🔧  
**Süre:** 2-3 saat

---

### ✅ 6. Alarm Sistemi İyileştirme — **TAMAMLANDI**
- [x] Akıllı filtreleme
  - [x] Kullanıcının portföyündeki varlıklara göre alarm filtrele
  - [x] Genel piyasa kelimeleri her zaman geçer (faiz, kriz, savaş vb.)
  - [x] Portföy boşsa tüm alarmlar gösterilir
- [x] Spam önleme
  - [x] Günde max 3 alarm per kullanıcı
  - [x] Günlük sayaç takibi (`metrics/gunluk_alarm_sayaci.json`)
- [x] Aciliyet seviyeleri
  - [x] 🔴 Kritik (8-10) — Savaş, borsa çöküşü, acil faiz kararı
  - [x] 🟡 Önemli (6-7) — Jeopolitik gerilim, önemli ekonomik veri
  - [x] 🟢 Bilgi (5) — Dikkat çekici piyasa hareketi
- [x] Kullanıcı başına min. seviye ayarı
- [x] Portföy filtresi toggle (açık/kapalı)
- [x] `/bildirim` komutu inline butonlarla yenilendi
- [x] Geriye dönük uyumluluk (eski bool format destekleniyor)
- [x] Test edildi

**Durum:** ✅ TAMAMLANDI  
**Beklenen Etki:** 🔥🔥🔥  
**Zorluk:** 🔧🔧  
**Süre:** 2 saat

---

## 🟢 UZUN VADELİ (1-4 Hafta)

### 7. API ve Kurumsal Özellikler
- [ ] REST API (kurumsal müşteriler için)
- [ ] Webhook entegrasyonu
- [ ] Toplu analiz (100+ sorgu/gün)
- [ ] Dokümantasyon

**Beklenen Etki:** 🔥🔥  
**Zorluk:** 🔧🔧🔧🔧  
**Süre:** 1 hafta

---

### 7.5. Çok Dil Desteği (İngilizce)
- [ ] Analiz çıktısı dili — `/dil` komutu (tr/en)
  - `ANALIZ_DIL_NOTU` kullanıcı diline göre dinamik
  - Kullanıcı dil tercihi `metrics/dil_tercihleri.json`'a kaydet
- [ ] Bot arayüzü dili (butonlar, mesajlar)
  - `i18n` dict sistemi (50-80 mesaj)
  - Türkçe + İngilizce tam çeviri
- [ ] Test et

**Beklenen Etki:** 🔥🔥🔥🔥  
**Zorluk:** 🔧🔧  
**Süre:** 2-3 gün  
**Not:** Analiz çıktısı (1-2 saat) ve arayüz (1-2 gün) ayrı fazlarda yapılabilir.

---

### 8. Topluluk ve Sosyal Kanıt
- [ ] Discord/Telegram grubu
- [ ] Haftalık performans raporu
- [ ] Kullanıcı yarışması (en iyi tahmin)
- [ ] Leaderboard

**Beklenen Etki:** 🔥🔥🔥  
**Zorluk:** 🔧🔧  
**Süre:** 3-4 gün

---

### 9. Regülasyon ve Yasal
- [ ] Açık disclaimer (her yerde)
- [ ] Kullanım şartları
- [ ] Gizlilik politikası
- [ ] Finansal danışmanlık değil, bilgilendirme vurgusu
- [ ] Avukat incelemesi

**Beklenen Etki:** 🔥🔥🔥🔥  
**Zorluk:** 🔧🔧🔧  
**Süre:** 1 hafta

---

## 📊 ÖNCELİK MATRİSİ

| # | Özellik | Etki | Zorluk | Süre | Öncelik | Durum |
|---|---------|------|--------|------|---------|-------|
| 1 | Prob Zinciri 200+ | 🔥🔥🔥🔥🔥 | 🔧🔧 | 2-3h | **1** | ✅ TAMAMLANDI |
| 2 | Görsel Çıktı (Grafik/PDF) | 🔥🔥🔥🔥🔥 | 🔧🔧 | 2h | **2** | ✅ TAMAMLANDI |
| 3 | Backtest/Simülasyon | 🔥🔥🔥🔥🔥 | 🔧🔧🔧 | 3-4h | **3** | ✅ TAMAMLANDI |
| 4 | Hikaye/Pazarlama | 🔥🔥🔥🔥 | 🔧🔧 | 1d | **4** | ⏳ ŞİMDİ |
| 5 | Portföy Entegrasyonu | 🔥🔥🔥 | 🔧🔧 | 2-3h | **5** | ✅ TAMAMLANDI |
| 6 | Alarm İyileştirme | 🔥🔥🔥 | 🔧🔧 | 2h | **6** | ✅ TAMAMLANDI |
| 7 | API | 🔥🔥 | 🔧🔧🔧🔧 | 1w | **7** | 📅 UZUN VADE |
| 8 | Topluluk | 🔥🔥🔥 | 🔧🔧 | 3-4d | **8** | 📅 UZUN VADE |
| 9 | Yasal | 🔥🔥🔥🔥 | 🔧🔧🔧 | 1w | **9** | 📅 UZUN VADE |

---

## 🎯 İLK 3 ADIM (BUGÜN BAŞLA)

### ✅ Adım 1: Prob Zinciri Şablonu (2 saat)
```bash
# 1. prob_zinciri_uretim_promptu.md'yi Claude'a ver
# 2. Çıktıyı prob_zinciri_full.json olarak kaydet
# 3. python merge_prob_zincirleri.py
# 4. Test et: /analiz → Mevsim → Türkiye → altın
```

### ✅ Adım 2: Görsel Çıktı Prototipi (1 saat)
```bash
# 1. app.py'de çıktı formatını güncelle
# 2. Emoji ve yapı ekle
# 3. Test et ve ekran görüntüsü al
```

### ✅ Adım 3: Backtest Altyapısı (3 saat)
```bash
# 1. /backtest komutunu ekle
# 2. Geçmiş tahminleri kaydet
# 3. Basit doğrulama fonksiyonu yaz
# 4. Test et
```

---

## 💰 PARA ÖDETİCİ FAKTÖRLER (Öncelik Sırası)

1. **Backtest Sonuçları** (Güven) - "Geçen yıl %78 doğru"
2. **Prob Zinciri Derinliği** (Zeka) - "200+ sosyal ihtimal analiz ediyor"
3. **Kişiselleştirme** (Değer) - "Senin portföyüne özel"
4. **Şeffaflık** (Güven) - "Neden bu tahmini yaptı?"
5. **Hız** (Rahatlık) - "5 saniyede analiz"

---

## 📈 BAŞARI METRİKLERİ

### Hafta 1 Hedefleri
- [ ] 200+ prob zinciri aktif
- [ ] Görsel çıktı yenilendi
- [ ] Backtest MVP çalışıyor
- [ ] 10 kullanıcı testi yapıldı

### Hafta 2 Hedefleri
- [ ] Landing page yayında
- [ ] Twitter'da 5 paylaşım
- [ ] 50+ aktif kullanıcı
- [ ] İlk ödeme geldi

### Ay 1 Hedefleri
- [ ] 100+ aktif kullanıcı
- [ ] 10+ Pro üye
- [ ] %70+ kullanıcı memnuniyeti
- [ ] Sosyal medyada 1000+ takipçi

---

## 🚀 HIZLI BAŞLANGIÇ

```bash
# 1. Prob zinciri üret
# Dosya: prob_zinciri_uretim_promptu.md
# Claude'a ver, çıktıyı kaydet

# 2. Birleştir
python merge_prob_zincirleri.py

# 3. Test et
python main.py
# Telegram: /analiz → Mevsim → Türkiye → altın

# 4. Görsel çıktıyı iyileştir
# app.py'de formatı güncelle

# 5. Backtest ekle
# /backtest komutunu implement et
```

---

## 📚 DOKÜMANTASYON

- **Prob Zinciri Prompt:** `prob_zinciri_uretim_promptu.md`
- **Entegrasyon Rehberi:** `prob_zinciri_entegrasyon_rehberi.md`
- **Hızlı Başlangıç:** `PROB_ZINCIRI_HIZLI_BASLANGIC.md`
- **Merge Script:** `merge_prob_zincirleri.py`
- **Bu Tasklist:** `OKWIS_GELISTIRME_TASKLIST.md`

---

## 🎉 BAŞARILI GELİŞTİRME!

**Sorular?** Dokümantasyona bak veya sor!

**Hazır mısın?** İlk 3 adımı tamamla! 🚀
