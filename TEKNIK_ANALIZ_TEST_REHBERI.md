# Teknik Analiz Modu - Test Rehberi

**Tarih:** 30 Nisan 2026  
**Amaç:** Teknik Analiz modunun düzgün çalıştığını doğrulama

---

## 🧪 Manuel Test Senaryoları

### Test 1: BTC Analizi (Temel)

**Adımlar:**
1. Telegram'da `/analiz` komutunu gönder
2. "Tüm Modlar" butonuna tıkla
3. "⚡ Teknik Analiz" butonuna tıkla
4. "BTC" yaz ve gönder

**Beklenen Sonuç:**
```
⚡ BTC için teknik analiz başlıyor...
(2-3 saniye bekle)

⚡ TEKNİK ANALİZ — BTC
━━━━━━━━━━━━━━━━━━━━
📊 MEVCUT DURUM
Son Fiyat: $XX,XXX.XX
...
🟢 TEKNİK SİNYAL: BULLISH/BEARISH/NEUTRAL
```

**Kontrol Listesi:**
- [ ] Ülke sorusu SORULMADI
- [ ] Format seçimi (uzun/kısa) SORULMADI
- [ ] Analiz 2-3 saniyede geldi
- [ ] Fiyat verisi gösteriliyor
- [ ] RSI, SMA değerleri gösteriliyor
- [ ] Sinyal (BULLISH/BEARISH/NEUTRAL) gösteriliyor

---

### Test 2: Bitcoin (Türkçe İsim)

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "Bitcoin" yaz (büyük B ile)

**Beklenen Sonuç:**
- BTC-USD olarak algılanmalı
- Analiz başarıyla gösterilmeli

**Kontrol:**
- [ ] "Bitcoin" → "BTC-USD" dönüşümü çalıştı
- [ ] Analiz gösterildi

---

### Test 3: Apple Hissesi (İngilizce İsim)

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "Apple" yaz

**Beklenen Sonuç:**
- AAPL olarak algılanmalı
- Analiz başarıyla gösterilmeli

**Kontrol:**
- [ ] "Apple" → "AAPL" dönüşümü çalıştı
- [ ] Hisse fiyatı gösterildi

---

### Test 4: Altın (Türkçe Emtia)

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "Altın" yaz (Türkçe)

**Beklenen Sonuç:**
- GC=F olarak algılanmalı
- Altın fiyatı gösterilmeli

**Kontrol:**
- [ ] "Altın" → "GC=F" dönüşümü çalıştı
- [ ] Emtia fiyatı gösterildi

---

### Test 5: Turkcell (Türk Hissesi)

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "Turkcell" yaz

**Beklenen Sonuç:**
- THYAO.IS olarak algılanmalı
- Borsa İstanbul fiyatı gösterilmeli

**Kontrol:**
- [ ] "Turkcell" → "THYAO.IS" dönüşümü çalıştı
- [ ] BIST fiyatı gösterildi

---

### Test 6: Geçersiz Varlık

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "ASDFGHJKL" yaz (geçersiz)

**Beklenen Sonuç:**
```
⚡ ASDFGHJKL için fiyat verisi bulunamadı.

Lütfen geçerli bir varlık adı dene:
  • Kripto: Bitcoin, BTC, Ethereum, ETH
  • Hisse: Apple, AAPL, Microsoft, MSFT, Turkcell, THYAO
  • Emtia: Altın, Gold, XAUUSD, Petrol, WTI
```

**Kontrol:**
- [ ] Hata mesajı gösterildi
- [ ] Örnek varlıklar listelendi
- [ ] Bot çökmedi

---

### Test 7: Boş Varlık

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "BOŞ" yaz veya hiçbir şey yazmadan gönder

**Beklenen Sonuç:**
```
⚠️ Teknik analiz için varlık adı gerekli.

Lütfen bir varlık adı yaz: BTC, Bitcoin, AAPL, Apple, vb.
```

**Kontrol:**
- [ ] Uyarı mesajı gösterildi
- [ ] Varlık adı tekrar soruldu
- [ ] Bot çökmedi

---

### Test 8: Küçük Harf Varyasyonları

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. Sırayla test et:
   - "btc" (küçük harf)
   - "bitcoin" (küçük harf)
   - "apple" (küçük harf)
   - "gold" (küçük harf)

**Beklenen Sonuç:**
- Tüm varyasyonlar çalışmalı
- Büyük/küçük harf duyarlılığı olmamalı

**Kontrol:**
- [ ] "btc" → BTC-USD ✅
- [ ] "bitcoin" → BTC-USD ✅
- [ ] "apple" → AAPL ✅
- [ ] "gold" → GC=F ✅

---

### Test 9: Günlük Limit (Ücretsiz Kullanıcı)

**Adımlar:**
1. Ücretsiz kullanıcı hesabıyla giriş yap
2. 5 kez Teknik Analiz yap (günlük limit)
3. 6. kez dene

**Beklenen Sonuç:**
```
◆ Günlük ücretsiz limit doldu (5/5).

Daha fazla analiz için bir plan seç:
📊 /abonelik — tüm planları gör
...
```

**Kontrol:**
- [ ] İlk 5 analiz çalıştı
- [ ] 6. analizde limit mesajı gösterildi
- [ ] Abonelik bilgisi verildi

---

### Test 10: Hız Testi

**Adımlar:**
1. `/analiz` → Tüm Modlar → Teknik Analiz
2. "BTC" yaz
3. Kronometre başlat
4. Analiz gelene kadar bekle

**Beklenen Sonuç:**
- Analiz 2-3 saniyede gelmeli
- 5 saniyeden uzun sürerse sorun var

**Kontrol:**
- [ ] Süre: _____ saniye (hedef: <3 saniye)

---

## 🔧 Otomatik Test Komutları

### Test 1: Syntax Kontrolü
```bash
python -m py_compile app.py teknik_analiz_baglam.py
```
**Beklenen:** Hata yok

### Test 2: BTC Analizi
```bash
python -c "from teknik_analiz_baglam import teknik_analiz_yap; result = teknik_analiz_yap('BTC'); print('SUCCESS!' if result else 'FAILED')"
```
**Beklenen:** SUCCESS!

### Test 3: Varlık Normalizasyonu
```bash
python -c "from teknik_analiz_baglam import _sembol_bul; test_cases = ['BTC', 'Bitcoin', 'bitcoin', 'AAPL', 'Apple', 'Altın', 'Gold']; print('\n'.join([f'{tc} -> {_sembol_bul(tc)}' for tc in test_cases]))"
```
**Beklenen:**
```
BTC -> BTC-USD
Bitcoin -> BTC-USD
bitcoin -> BTC-USD
AAPL -> AAPL
Apple -> AAPL
Altın -> GC=F
Gold -> GC=F
```

### Test 4: yfinance Bağlantısı
```bash
python -c "import yfinance as yf; df = yf.Ticker('BTC-USD').history(period='5d'); print('SUCCESS!' if not df.empty else 'FAILED')"
```
**Beklenen:** SUCCESS!

### Test 5: Tam Analiz Testi
```bash
python -c "from teknik_analiz_baglam import topla_teknik_analiz_baglami; print(topla_teknik_analiz_baglami('BTC'))"
```
**Beklenen:** Tam analiz metni

---

## 📊 Test Sonuç Tablosu

| Test No | Test Adı | Durum | Notlar |
|---------|----------|-------|--------|
| 1 | BTC Analizi | ⬜ | |
| 2 | Bitcoin (Türkçe) | ⬜ | |
| 3 | Apple Hissesi | ⬜ | |
| 4 | Altın (Türkçe) | ⬜ | |
| 5 | Turkcell | ⬜ | |
| 6 | Geçersiz Varlık | ⬜ | |
| 7 | Boş Varlık | ⬜ | |
| 8 | Küçük Harf | ⬜ | |
| 9 | Günlük Limit | ⬜ | |
| 10 | Hız Testi | ⬜ | |

**Durum Kodları:**
- ⬜ Test edilmedi
- ✅ Başarılı
- ❌ Başarısız
- ⚠️ Kısmi başarı

---

## 🐛 Hata Ayıklama

### Sorun: "BTC için fiyat verisi bulunamadı"

**Olası Nedenler:**
1. yfinance yüklü değil
2. İnternet bağlantısı yok
3. yfinance API'si yanıt vermiyor

**Çözüm:**
```bash
# yfinance kontrolü
pip install yfinance

# Manuel test
python -c "import yfinance as yf; print(yf.Ticker('BTC-USD').history(period='1d'))"
```

---

### Sorun: "Format seçimi hala görünüyor"

**Olası Nedenler:**
1. Kod değişiklikleri uygulanmadı
2. Bot yeniden başlatılmadı

**Çözüm:**
```bash
# Bot'u yeniden başlat
pkill -f app.py
python app.py
```

---

### Sorun: "Ülke sorusu hala soruluyor"

**Olası Nedenler:**
1. `mod_teknik_analiz` handler'da ülke "Global" olarak ayarlanmadı

**Çözüm:**
- `app.py` dosyasında `mod_teknik_analiz` handler'ı kontrol et
- `context.user_data["ulke"] = "Global"` satırının olduğundan emin ol

---

## ✅ Test Tamamlama Kriterleri

Teknik Analiz modu **başarılı** sayılır eğer:

1. ✅ Tüm 10 manuel test başarılı
2. ✅ Tüm 5 otomatik test başarılı
3. ✅ Ortalama yanıt süresi <3 saniye
4. ✅ Hiçbir test çökme yaratmadı
5. ✅ Kullanıcı deneyimi akıcı

---

## 📝 Test Raporu Şablonu

```
TEKNIK ANALİZ MODU TEST RAPORU
Tarih: ___________
Test Eden: ___________

MANUEL TESTLER:
- Test 1 (BTC): ⬜ ✅ ❌
- Test 2 (Bitcoin): ⬜ ✅ ❌
- Test 3 (Apple): ⬜ ✅ ❌
- Test 4 (Altın): ⬜ ✅ ❌
- Test 5 (Turkcell): ⬜ ✅ ❌
- Test 6 (Geçersiz): ⬜ ✅ ❌
- Test 7 (Boş): ⬜ ✅ ❌
- Test 8 (Küçük Harf): ⬜ ✅ ❌
- Test 9 (Limit): ⬜ ✅ ❌
- Test 10 (Hız): ⬜ ✅ ❌

OTOMATİK TESTLER:
- Syntax: ⬜ ✅ ❌
- BTC Analizi: ⬜ ✅ ❌
- Normalizasyon: ⬜ ✅ ❌
- yfinance: ⬜ ✅ ❌
- Tam Analiz: ⬜ ✅ ❌

GENEL SONUÇ: ⬜ BAŞARILI ⬜ BAŞARISIZ

NOTLAR:
___________________________________________
___________________________________________
___________________________________________
```

---

**Hazırlayan:** Kiro AI  
**Tarih:** 30 Nisan 2026  
**Versiyon:** 1.0
