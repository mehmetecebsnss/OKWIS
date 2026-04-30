# Okwis AI - Hızlı Aksiyon Planı

**Tarih:** 30 Nisan 2026  
**Hedef:** Satılabilirliği 6/10'dan 9/10'a çıkarmak

---

## 🔴 ACİL (Bu Hafta)

### 1. API Key Güvenliği (1 gün)
```bash
☐ Yeni Gemini API key'leri al
☐ .env dosyasını .gitignore'a ekle
☐ .env.example oluştur (template)
☐ GitHub geçmişinden .env'i temizle
☐ Bot'u yeni key'lerle test et
```

**Neden Önemli:** Güvenlik riski, API key'ler sızdırılmış

---

### 2. Dokümantasyon Temizliği (2 gün)
```bash
☐ docs/ klasörü oluştur
☐ README.md yaz (kullanıcı için)
☐ ARCHITECTURE.md yaz (geliştirici için)
☐ 40+ MD dosyasını docs/archive/ taşı
☐ Sadece 5-6 ana dosya bırak
```

**Neden Önemli:** Yeni geliştirici onboarding, profesyonellik

---

### 3. Pazarlama Başlat (devam eden)
```bash
☐ Twitter hesabı aktif et (@okwis_ai)
☐ İlk tweet: "Okwis nedir?" (thread)
☐ YouTube kanalı aç
☐ İlk video: "5 Dakikada Okwis" (demo)
☐ Telegram grubu oluştur (topluluk)
```

**Neden Önemli:** Kullanıcı kazanımı, marka bilinirliği

---

## 🟡 ÖNEMLİ (Bu Ay)

### 4. app.py Refactoring - Faz 1 (1 hafta)
```bash
☐ llm_service.py oluştur
   - _gemini_metin_uret()
   - _deepseek_metin_uret()
   - _claude_metin_uret()
   - llm_metin_uret()

☐ user_service.py oluştur
   - _kullanici_profili_al()
   - _kullanici_profili_kaydet()
   - _gunluk_kullanim_arttir()
   - _gunluk_limit_asildi_mi()

☐ subscription_service.py oluştur
   - _kullanici_plan_bilgisi()
   - _kullanici_pro_mu()
   - _kullanici_claude_mi()
   - _odeme_olayi_kaydet()

☐ app.py'den import et ve test et
```

**Neden Önemli:** Kod kalitesi, bakım kolaylığı, ekip çalışması

---

### 5. Performans Optimizasyonu (1 hafta)
```bash
☐ RSS feed cache ekle (15 dakika TTL)
☐ Rate limiting decorator ekle
☐ Async/await optimizasyonu
☐ Profiling yap (bottleneck bul)
☐ Okwis süresini 15s → 8s düşür
```

**Neden Önemli:** Kullanıcı deneyimi, maliyet azaltma

---

### 6. Test Altyapısı (1 hafta)
```bash
☐ pytest kurulumu
☐ tests/ klasörü oluştur
☐ Unit testler yaz (llm_service, user_service)
☐ Integration testler yaz (Okwis flow)
☐ CI/CD pipeline (GitHub Actions)
```

**Neden Önemli:** Güvenilirlik, regression önleme

---

## 🟢 GELECEK (Gelecek Ay)

### 7. Veritabanı Geçişi (2 hafta)
```bash
☐ SQLite schema tasarımı
☐ Migration scriptleri
☐ JSON → SQLite migration
☐ Test ve doğrulama
☐ PostgreSQL'e geçiş (production)
```

**Neden Önemli:** Ölçeklenebilirlik, 10,000+ kullanıcı desteği

---

### 8. Monitoring & Analytics (1 hafta)
```bash
☐ Prometheus metrics ekle
☐ Grafana dashboard oluştur
☐ Sentry hata takibi
☐ User analytics (mixpanel/amplitude)
```

**Neden Önemli:** Veri odaklı kararlar, hata tespiti

---

## 📊 BAŞARI KRİTERLERİ

### Bu Hafta
- ✅ API key güvenliği çözüldü
- ✅ Dokümantasyon temiz ve anlaşılır
- ✅ İlk 10 beta kullanıcı

### Bu Ay
- ✅ app.py 5,356 → 2,000 satır
- ✅ Test coverage %50+
- ✅ Okwis süresi 15s → 8s
- ✅ 100 aktif kullanıcı, 10 Pro abone

### 3 Ay
- ✅ Veritabanı geçişi tamamlandı
- ✅ 1,000 aktif kullanıcı, 100 Pro abone
- ✅ MRR: ₺10,000

---

## 💰 BÜTÇE TAHMİNİ

### Geliştirme Maliyeti
```
Geliştirici (freelance): ₺15,000/ay
Sunucu (Railway/Heroku): ₺500/ay
API maliyetleri: ₺1,000/ay
Toplam: ₺16,500/ay
```

### Pazarlama Maliyeti
```
Google Ads: ₺3,000/ay
Facebook Ads: ₺2,000/ay
Influencer: ₺5,000/ay
Toplam: ₺10,000/ay
```

### Toplam Aylık Maliyet: ₺26,500

### Break-even: 268 Pro abone (₺99/ay)

---

## 🎯 6 AYLIK HEDEF

| Metrik | Şu An | 6 Ay Sonra |
|--------|-------|------------|
| **Aktif Kullanıcı** | 50 | 10,000 |
| **Pro Abone** | 5 | 1,000 |
| **MRR** | ₺500 | ₺100,000 |
| **Kod Kalitesi** | 4/10 | 8/10 |
| **Test Coverage** | 0% | 70% |
| **Satılabilirlik** | 6/10 | 9/10 |

---

## ✅ CHECKLIST

### Bugün
- [ ] Yeni Gemini API key al
- [ ] .env'i güvenli hale getir
- [ ] Twitter hesabı aç

### Bu Hafta
- [ ] Dokümantasyon temizliği
- [ ] İlk blog yazısı
- [ ] 10 beta kullanıcı bul

### Bu Ay
- [ ] app.py refactoring (Faz 1)
- [ ] Performans optimizasyonu
- [ ] Test altyapısı
- [ ] 100 kullanıcı, 10 Pro abone

---

**Hazırlayan:** Kiro AI  
**Tarih:** 30 Nisan 2026  
**Durum:** 🚀 Hazır, Başlayalım!
