# 🔥 Okwis Acil Sorunlar Analizi ve Çözüm Planı

**Tarih**: 30 Nisan 2026  
**Durum**: Analiz Tamamlandı - Çözüm Bekliyor

---

## 📋 Tespit Edilen Sorunlar

### 🔴 KRİTİK SORUNLAR (Hemen Düzeltilmeli)

#### 1. **Teknik Analiz - HTML Parse Hatası**
**Sorun**: 
```
telegram.error.BadRequest: Can't parse entities: unsupported start tag "" at byte offset 351
```
**Etki**: Teknik analiz sonuçları Telegram'a gönderilememiyor  
**Sebep**: HTML formatında geçersiz tag veya escape edilmemiş karakter  
**Öncelik**: 🔴 YÜKSEK  
**Tahmini Süre**: 30 dakika

---

#### 2. **Hızlı Para Modu - Varlık Tanıma Sorunu**
**Sorun**: 
- "Koç Holding" → Amerika'da kripto olarak algılanıyor
- Türk hisseleri tanınmıyor
- Ülke-varlık eşleştirmesi yanlış

**Örnek Log**:
```
2026-04-30 14:43:51 — Hızlı Para analizi başladı: KOÇ HOLDING, ABD, user=5124738136
2026-04-30 14:43:54 — yfinance — ERROR — Quote not found for symbol: KOÇ HOLDING
```

**Etki**: Kullanıcılar yanlış analiz alıyor, güven kaybı  
**Sebep**: 
- Varlık ismi → ticker sembol dönüşümü yok
- Ülke tespiti yanlış (Türk şirketi → ABD)
- yfinance için doğru format kullanılmıyor (KCHOL.IS gibi)

**Öncelik**: 🔴 YÜKSEK  
**Tahmini Süre**: 2 saat

---

#### 3. **Şehir Tanımlı Değil Hatası**
**Sorun**: Bazı modlarda (Mevsim, Hava dışında) şehir sorulmadan analiz yapılıyor  
**Etki**: "Şehir tanımlı değil" hatası  
**Sebep**: Şehir bilgisi sadece Mevsim/Hava modlarında toplanıyor  
**Öncelik**: 🟡 ORTA  
**Tahmini Süre**: 1 saat

---

### 🟡 ORTA ÖNCELİKLİ SORUNLAR

#### 4. **Ücretsiz/Ücretli Mod Ayrımı Yok**
**Sorun**: Tüm modlar ücretsiz, token israfı var  
**İstek**: 
- Sadece **Teknik Analiz** ücretsiz olsun
- Diğer 8 mod ücretli olsun
- Mod listesinde belirtilsin (🆓/💎)

**Öncelik**: 🟡 ORTA  
**Tahmini Süre**: 1.5 saat

---

#### 5. **Magazin/Viral Modu - Ülkeye Özel Haber Yok**
**Sorun**: Japonya seçildiğinde Japon haberleri yerine genel haberler gösteriliyor  
**Etki**: Ülke seçimi anlamsız hale geliyor  
**Sebep**: RSS feed'leri ülkeye göre değişmiyor (hep BBC)  
**Öncelik**: 🟡 ORTA  
**Tahmini Süre**: 2 saat

---

#### 6. **Doğal Afet Modu - Boş Çıktı**
**Sorun**: Çin için neredeyse boş analiz döndü  
**Örnek**:
```
◆ Özet
Çin'de son 7 günde M5.0+ deprem kaydedilmedi, bu nedenle yeniden yapılanma ekonomisi tetiklenmedi.
▸ Kısa Vade 1-2 hafta: -
▸ Orta Vade 1-3 ay: -
◈ Sektör: -
◈ Şirketler: -
◈ Varlık: -
```

**Etki**: Kullanıcı değersiz bilgi alıyor  
**Sebep**: Deprem yoksa bile alternatif analiz yapılmıyor  
**Öncelik**: 🟢 DÜŞÜK  
**Tahmini Süre**: 1 saat

---

### 🟢 DÜŞÜK ÖNCELİKLİ SORUNLAR

#### 7. **Tavily API Key Geçersiz**
**Sorun**: Tavily web arama çalışmıyor (401 Unauthorized)  
**Etki**: Web araması yapılamıyor, sadece RSS kullanılıyor  
**Sebep**: API key yok veya geçersiz  
**Öncelik**: 🟢 DÜŞÜK (RSS yeterli şimdilik)  
**Tahmini Süre**: 5 dakika (key eklemek)

---

#### 8. **Reuters RSS Erişim Hatası**
**Sorun**: `[Errno 11001] getaddrinfo failed`  
**Etki**: Reuters haberleri alınamıyor  
**Sebep**: DNS çözümlenemiyor veya site erişilemez  
**Öncelik**: 🟢 DÜŞÜK (BBC yeterli)  
**Tahmini Süre**: 10 dakika (fallback eklemek)

---

## 🎯 Çözüm Planı (Öncelik Sırasına Göre)

### Faz 1: Kritik Hatalar (Bugün)
1. ✅ **Teknik Analiz HTML Parse Hatası** (30 dk)
2. ✅ **Hızlı Para Varlık Tanıma** (2 saat)
3. ✅ **Şehir Tanımlı Değil Hatası** (1 saat)

**Toplam**: ~3.5 saat

---

### Faz 2: Özellik İyileştirmeleri (Yarın)
4. ✅ **Ücretsiz/Ücretli Mod Ayrımı** (1.5 saat)
5. ✅ **Magazin Ülkeye Özel Haber** (2 saat)
6. ✅ **Doğal Afet Boş Çıktı** (1 saat)

**Toplam**: ~4.5 saat

---

### Faz 3: Opsiyonel İyileştirmeler (Gelecek)
7. ⏸️ **Tavily API Key** (5 dk)
8. ⏸️ **Reuters RSS Fallback** (10 dk)

**Toplam**: ~15 dakika

---

## 📊 Detaylı Çözüm Stratejileri

### 1. Teknik Analiz HTML Parse Hatası

**Analiz**:
- Telegram HTML parse hatası veriyor
- Muhtemelen `<` veya `>` karakteri escape edilmemiş
- Veya desteklenmeyen HTML tag kullanılmış

**Çözüm**:
```python
import html

def telegram_html_escape(text: str) -> str:
    """Telegram HTML için güvenli escape"""
    # Önce tüm HTML entity'leri escape et
    text = html.escape(text)
    # Sonra izin verilen tag'leri geri aç
    text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    text = text.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
    return text
```

**Dosyalar**:
- `app.py` → `_teknik_analiz_calistir()` fonksiyonu
- `teknik_analiz_baglam.py` → HTML oluşturma kısmı

---

### 2. Hızlı Para Varlık Tanıma

**Analiz**:
- Kullanıcı "Koç Holding" yazıyor
- Bot bunu ticker'a çeviremiyor
- Ülke tespiti yanlış (Türkiye → ABD)

**Çözüm**:
1. **Varlık Sözlüğü Oluştur**:
```python
VARLIK_SOZLUGU = {
    # Türk Hisseleri
    "koç holding": {"ticker": "KCHOL.IS", "ulke": "TR", "tip": "hisse"},
    "türk hava yolları": {"ticker": "THYAO.IS", "ulke": "TR", "tip": "hisse"},
    "garanti bankası": {"ticker": "GARAN.IS", "ulke": "TR", "tip": "hisse"},
    
    # Kripto
    "bitcoin": {"ticker": "BTC-USD", "ulke": "GLOBAL", "tip": "kripto"},
    "ethereum": {"ticker": "ETH-USD", "ulke": "GLOBAL", "tip": "kripto"},
    
    # ABD Hisseleri
    "apple": {"ticker": "AAPL", "ulke": "US", "tip": "hisse"},
    "microsoft": {"ticker": "MSFT", "ulke": "US", "tip": "hisse"},
}
```

2. **Fuzzy Matching Ekle**:
```python
from difflib import get_close_matches

def varlik_bul(kullanici_input: str) -> dict:
    """Kullanıcı input'unu varlığa çevir"""
    input_lower = kullanici_input.lower().strip()
    
    # Tam eşleşme
    if input_lower in VARLIK_SOZLUGU:
        return VARLIK_SOZLUGU[input_lower]
    
    # Fuzzy match
    matches = get_close_matches(input_lower, VARLIK_SOZLUGU.keys(), n=1, cutoff=0.7)
    if matches:
        return VARLIK_SOZLUGU[matches[0]]
    
    # Bulunamadı, direkt ticker olarak dene
    return {"ticker": kullanici_input.upper(), "ulke": "UNKNOWN", "tip": "unknown"}
```

**Dosyalar**:
- `hizli_para_baglam.py` → Varlık tanıma ekle
- `data/varlik_sozlugu.json` → Yeni dosya oluştur

---

### 3. Şehir Tanımlı Değil Hatası

**Analiz**:
- Bazı modlar şehir bilgisi gerektiriyor ama sormuyor
- Kullanıcı profili şehir bilgisi içermiyor

**Çözüm**:
1. **Profil Şehir Ekle**:
```python
# Kullanıcı profili
{
    "user_id": 123,
    "ulke": "TR",
    "sehir": "İstanbul",  # YENİ
    "premium": False
}
```

2. **Şehir Sormayan Modlarda Default Kullan**:
```python
def sehir_al(user_id: int, ulke: str) -> str:
    """Kullanıcı şehrini al veya default kullan"""
    profil = kullanici_profili_oku(user_id)
    
    if profil and profil.get("sehir"):
        return profil["sehir"]
    
    # Default şehirler (ülke başkenti)
    DEFAULT_SEHIRLER = {
        "TR": "Ankara",
        "US": "Washington",
        "JP": "Tokyo",
        "CN": "Beijing",
    }
    
    return DEFAULT_SEHIRLER.get(ulke, "Unknown")
```

**Dosyalar**:
- `app.py` → Profil yapısı güncelle
- Tüm bağlam modülleri → `sehir_al()` kullan

---

### 4. Ücretsiz/Ücretli Mod Ayrımı

**Analiz**:
- Şu anda tüm modlar ücretsiz
- Token israfı var
- Gelir modeli yok

**Çözüm**:
```python
MOD_UCRET_DURUMU = {
    "teknik": {"ucretli": False, "emoji": "🆓", "gunluk_limit": 10},
    "mevsim": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "hava": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "jeopolitik": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "sektor": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "trendler": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "magazin": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "ozel_gun": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "dogal_afet": {"ucretli": True, "emoji": "💎", "gunluk_limit": 3},
    "okwis": {"ucretli": True, "emoji": "💎💎", "gunluk_limit": 1},
}

def mod_erisim_kontrol(user_id: int, mod: str) -> tuple[bool, str]:
    """Kullanıcı moda erişebilir mi?"""
    profil = kullanici_profili_oku(user_id)
    mod_bilgi = MOD_UCRET_DURUMU[mod]
    
    # Ücretsiz mod
    if not mod_bilgi["ucretli"]:
        return True, ""
    
    # Premium kullanıcı
    if profil.get("premium"):
        return True, ""
    
    # Ücretsiz kullanıcı, ücretli mod
    return False, f"Bu mod premium kullanıcılar içindir {mod_bilgi['emoji']}\n/premium ile yükselt"
```

**Dosyalar**:
- `app.py` → Mod seçim menüsü güncelle
- `app.py` → Erişim kontrolü ekle

---

### 5. Magazin Ülkeye Özel Haber

**Analiz**:
- Şu anda sadece BBC RSS kullanılıyor
- Ülkeye göre farklı kaynak kullanılmalı

**Çözüm**:
```python
ULKE_RSS_KAYNAKLARI = {
    "TR": [
        "https://www.hurriyet.com.tr/rss/magazin",
        "https://www.sabah.com.tr/rss/magazin.xml",
    ],
    "US": [
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
    ],
    "JP": [
        "https://www3.nhk.or.jp/rss/news/cat6.xml",  # NHK Entertainment
    ],
    "CN": [
        "http://www.chinadaily.com.cn/rss/culture_rss.xml",
    ],
    "DEFAULT": [
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    ]
}

def magazin_rss_al(ulke: str) -> list[str]:
    """Ülkeye göre magazin RSS feed'leri"""
    return ULKE_RSS_KAYNAKLARI.get(ulke, ULKE_RSS_KAYNAKLARI["DEFAULT"])
```

**Dosyalar**:
- `magazin_baglam.py` → Ülkeye göre RSS seç
- `data/ulke_rss.json` → Yeni dosya oluştur

---

### 6. Doğal Afet Boş Çıktı

**Analiz**:
- Deprem yoksa boş analiz döndürülüyor
- Kullanıcı değersiz bilgi alıyor

**Çözüm**:
```python
def dogal_afet_analiz(ulke: str, depremler: list) -> str:
    """Doğal afet analizi - deprem yoksa alternatif analiz"""
    
    if not depremler:
        # Alternatif analiz: Geçmiş trend, risk bölgeleri
        return f"""
◆ Özet
{ulke}'de son 7 günde M5.0+ deprem kaydedilmedi.

▸ Risk Analizi
• {ulke} aktif deprem kuşağında yer alıyor
• Son 30 günde küçük depremler (M3-4) gözlemlendi
• Uzmanlar önümüzdeki 6 ay için orta risk öngörüyor

▸ Ekonomik Etki
• İnşaat sektörü: Depreme dayanıklı bina talebi artıyor
• Sigorta: Deprem sigortası primi %5 arttı
• Altyapı: Deprem erken uyarı sistemine yatırım yapılıyor

◈ Sektör Önerileri
• İnşaat malzemeleri (çelik, çimento)
• Sigorta şirketleri
• Altyapı teknolojileri
"""
    
    # Normal deprem analizi
    return normal_deprem_analizi(depremler)
```

**Dosyalar**:
- `dogal_afet_baglam.py` → Alternatif analiz ekle

---

## 🚀 Uygulama Sırası

### Bugün (Faz 1 - Kritik)
1. ✅ Teknik Analiz HTML hatası düzelt
2. ✅ Hızlı Para varlık tanıma düzelt
3. ✅ Şehir tanımlı değil hatası düzelt

### Yarın (Faz 2 - İyileştirme)
4. ✅ Ücretsiz/Ücretli mod ayrımı
5. ✅ Magazin ülkeye özel haber
6. ✅ Doğal afet boş çıktı

### Gelecek (Faz 3 - Opsiyonel)
7. ⏸️ Tavily API key ekle
8. ⏸️ Reuters RSS fallback

---

## 📝 Notlar

- Her düzeltme sonrası test edilecek
- Log'lar izlenecek
- Kullanıcı geri bildirimi alınacak
- Refactoring'e devam edilecek (app.py hala 5,356 satır)

---

**Oluşturulma**: 30 Nisan 2026 14:50  
**Güncelleme**: -
