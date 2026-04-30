# API Key Sorunları ve Çözüm

**Tarih:** 30 Nisan 2026  
**Durum:** 🔴 **KRİTİK - API Key'ler Çalışmıyor**

---

## 🔴 Tespit Edilen Sorunlar

### 1. Gemini API Key Sızdırılmış
```
403 Your API key was reported as leaked. Please use another API key.
```

**Neden:** API key'ler muhtemelen GitHub'a commit edildi ve Google tarafından tespit edildi.

**Etki:** Tüm Gemini key'leri (8 adet) kullanılamıyor.

---

### 2. DeepSeek Bakiyesi Bitti
```
402 - {'error': {'message': 'Insufficient Balance'}}
```

**Neden:** DeepSeek hesabında kredi kalmadı.

**Etki:** Fallback provider çalışmıyor, analiz yapılamıyor.

---

### 3. Tavily API Hatası
```
432 - Client error '432 ' for url 'https://api.tavily.com/search'
```

**Neden:** Tavily API key'i geçersiz veya limit aşıldı.

**Etki:** Web araması çalışmıyor.

---

## ✅ Çözüm Adımları

### Adım 1: Yeni Gemini API Key'leri Al

1. **Google AI Studio'ya git:**
   https://aistudio.google.com/app/apikey

2. **Eski key'leri SİL:**
   - Sızdırılmış key'leri devre dışı bırak
   - Güvenlik için tüm eski key'leri iptal et

3. **Yeni key'ler oluştur:**
   - En az 5-8 yeni key oluştur
   - Her key için farklı proje kullan (rate limit için)

4. **.env dosyasını güncelle:**
   ```env
   GEMINI_API_KEY=YENİ_KEY_1
   GEMINI_API_KEY_2=YENİ_KEY_2
   GEMINI_API_KEY_3=YENİ_KEY_3
   # ... devamı
   ```

---

### Adım 2: DeepSeek Hesabına Kredi Ekle

1. **DeepSeek Dashboard'a git:**
   https://platform.deepseek.com/

2. **Billing bölümünden kredi ekle:**
   - Minimum $5-10 yeterli
   - Veya yeni bir hesap aç (ücretsiz kredi için)

3. **API key'i güncelle:**
   ```env
   DEEPSEEK_API_KEY=YENİ_DEEPSEEK_KEY
   ```

---

### Adım 3: Tavily API Key'i Düzelt

1. **Tavily Dashboard'a git:**
   https://tavily.com/

2. **API key'i kontrol et:**
   - Limit aşıldı mı?
   - Key geçerli mi?

3. **Gerekirse yeni key al:**
   ```env
   TAVILY_API_KEY=YENİ_TAVILY_KEY
   ```

---

### Adım 4: .env Dosyasını Güvenli Tut

1. **.gitignore'a ekle:**
   ```
   .env
   .env.local
   .env.production
   ```

2. **GitHub'da kontrol et:**
   ```bash
   git log --all --full-history -- .env
   ```
   
   Eğer .env commit edilmişse:
   ```bash
   # Geçmişten sil (DİKKAT: Tehlikeli!)
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **Örnek dosya oluştur:**
   ```bash
   cp .env .env.example
   # .env.example'da gerçek key'leri sil, sadece format bırak
   ```

---

## 🔧 Geçici Çözüm (Hemen Kullanmak İçin)

Eğer hemen test etmek istiyorsan, şimdilik sadece **ücretsiz Gemini key'leri** kullanabilirsin:

### Seçenek 1: Yeni Gemini Key Al (Ücretsiz)

1. https://aistudio.google.com/app/apikey
2. "Create API Key" tıkla
3. Yeni key'i kopyala
4. .env dosyasında `GEMINI_API_KEY` değiştir
5. Bot'u yeniden başlat

### Seçenek 2: DeepSeek'i Devre Dışı Bırak

Eğer sadece Gemini kullanmak istiyorsan:

```env
AI_PROVIDER=gemini
AI_FALLBACK_GEMINI=true
AI_FALLBACK_DEEPSEEK=false  # DeepSeek'i kapat
```

---

## 📝 .env Dosyası Şablonu

```env
# AI Provider Configuration
AI_PROVIDER=gemini
AI_FALLBACK_GEMINI=true
AI_FALLBACK_DEEPSEEK=true

# API Keys (YENİ KEY'LERİ BURAYA YAZ)
DEEPSEEK_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_2=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_3=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_4=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_5=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_6=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_7=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_8=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Telegram
TELEGRAM_TOKEN=XXXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXX

# Other APIs
OPENWEATHER_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TAVILY_API_KEY=tvly-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
ELEVENLABS_API_KEY=sk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Bot Configuration
ANALIZ_GUNLUK_LIMIT=1
ADMIN_USER_IDS=5124738136

# Voice Configuration
EDGE_TTS_VOICE=tr-TR-AhmetNeural
WHISPER_PROMPT=Okwis, senin adın, portföy, kripto
WHISPER_MODEL=medium
```

---

## 🧪 Test Adımları

Yeni key'leri ekledikten sonra:

1. **Bot'u yeniden başlat:**
   ```bash
   # Eski bot'u durdur
   Get-Process python | Where-Object {$_.Path -like "*Python310*"} | Stop-Process -Force
   
   # Yeni bot'u başlat
   python main.py
   ```

2. **Log'ları kontrol et:**
   ```bash
   # "403 leaked" hatası OLMAMALI
   # "402 Insufficient Balance" hatası OLMAMALI
   ```

3. **Hızlı Para modunu test et:**
   - Telegram'da /hizlipara
   - Bir varlık seç (örn: Bitcoin)
   - Analiz gelmeli ✅

---

## 🔒 Güvenlik Önerileri

### 1. .env Dosyasını Asla Commit Etme
```bash
# .gitignore'a ekle
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

### 2. Environment Variables Kullan (Production)
```bash
# Sunucuda environment variable olarak ayarla
export GEMINI_API_KEY="AIzaSy..."
export DEEPSEEK_API_KEY="sk-..."
```

### 3. Secrets Manager Kullan (İleri Seviye)
- AWS Secrets Manager
- Google Cloud Secret Manager
- Azure Key Vault

### 4. API Key Rotation
- Her 30 günde bir key'leri değiştir
- Eski key'leri iptal et
- Yeni key'leri güvenli şekilde sakla

---

## 📊 Maliyet Tahmini

### Gemini API (Ücretsiz)
- **Ücretsiz Tier:** 15 request/minute
- **Yeterli mi?** Evet, çoğu kullanım için yeterli
- **Maliyet:** $0

### DeepSeek API (Ücretli)
- **Fiyat:** ~$0.14 / 1M token (input)
- **Ortalama Kullanım:** ~100K token/gün
- **Aylık Maliyet:** ~$4-5

### Tavily API (Ücretsiz/Ücretli)
- **Ücretsiz Tier:** 1000 search/ay
- **Pro Plan:** $49/ay (unlimited)
- **Maliyet:** $0 (ücretsiz tier yeterli)

**Toplam Aylık Maliyet:** ~$5-10

---

## 🆘 Acil Durum Çözümü

Eğer hiçbir API key'in yoksa ve hemen test etmek istiyorsan:

### Geçici Olarak AI'yi Devre Dışı Bırak

1. **Mock response kullan:**
   ```python
   # app.py veya hizli_para_baglam.py içinde
   if not GEMINI_API_KEY:
       return "⚠️ API key eksik. Lütfen .env dosyasını kontrol edin."
   ```

2. **Veya basit analiz yap:**
   ```python
   # AI olmadan sadece veri göster
   return f"📊 {varlik} Fiyat: ${fiyat}\nRSI: {rsi}\nTrend: {trend}"
   ```

---

## ✅ Kontrol Listesi

Sorun çözüldü mü?

- [ ] Yeni Gemini API key'leri alındı
- [ ] .env dosyası güncellendi
- [ ] DeepSeek hesabına kredi eklendi (veya devre dışı bırakıldı)
- [ ] Tavily API key'i düzeltildi
- [ ] .gitignore'a .env eklendi
- [ ] Bot yeniden başlatıldı
- [ ] Log'larda "403 leaked" hatası YOK
- [ ] Log'larda "402 Insufficient Balance" hatası YOK
- [ ] Hızlı Para modu test edildi ve çalışıyor

---

**Hazırlayan:** Kiro AI  
**Tarih:** 30 Nisan 2026  
**Öncelik:** 🔴 KRİTİK
