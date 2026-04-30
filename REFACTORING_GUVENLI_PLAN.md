# Güvenli Refactoring Planı

**Hedef:** app.py'yi 5,356 satırdan küçültmek  
**Yaklaşım:** Kademeli, geriye uyumlu, test edilebilir

---

## 🎯 Prensip: "Çalışan Kodu Bozmayalım"

### Altın Kurallar

1. **Asla** tüm kodu bir anda değiştirme
2. **Her zaman** geriye uyumlu wrapper'lar bırak
3. **Mutlaka** her adımda test et
4. **Önce** yeni kodu ekle, **sonra** eski kodu sil
5. **Git** kullan (her adımda commit)

---

## 📋 Faz 1: llm_service.py (Güvenli)

### Adım 1: Yeni Modül Oluştur

```bash
# Yeni dosya oluştur
touch services/llm_service.py
```

**Durum:** app.py değişmedi ✅

---

### Adım 2: Fonksiyonları Kopyala (Taşıma DEĞİL)

```python
# services/llm_service.py

# app.py'deki fonksiyonları KOPYALA
def _gemini_metin_uret(...):
    # Aynı kod
    pass

def llm_metin_uret(...):
    # Aynı kod
    pass
```

**Durum:** app.py hala çalışıyor ✅

---

### Adım 3: Test Et (İzole)

```python
# test_llm_service.py

from services.llm_service import llm_metin_uret

def test_gemini():
    result = llm_metin_uret("Test prompt")
    assert result
    print("✅ Gemini çalışıyor")

if __name__ == "__main__":
    test_gemini()
```

**Durum:** Yeni kod test edildi, app.py değişmedi ✅

---

### Adım 4: app.py'de Import Ekle

```python
# app.py (en üstte)

# Yeni import ekle
try:
    from services.llm_service import llm_metin_uret as llm_metin_uret_v2
    LLM_SERVICE_AVAILABLE = True
except ImportError:
    LLM_SERVICE_AVAILABLE = False
    llm_metin_uret_v2 = None
```

**Durum:** app.py hala çalışıyor, yeni kod opsiyonel ✅

---

### Adım 5: Wrapper Oluştur (Backward Compatibility)

```python
# app.py (eski fonksiyonun yerine)

def llm_metin_uret(prompt: str, user_id: int | str | None = None) -> str:
    """
    LLM metin üretimi (backward compatible wrapper)
    
    Yeni kod varsa onu kullan, yoksa eski kodu kullan.
    """
    if LLM_SERVICE_AVAILABLE:
        # Yeni servis kullan
        return llm_metin_uret_v2(prompt, user_id)
    else:
        # Eski kod (fallback)
        # ... (eski kod burada kalır)
        pass
```

**Durum:** 
- Yeni kod varsa kullanılır
- Yoksa eski kod çalışır
- Hiçbir şey bozulmaz ✅

---

### Adım 6: Test Et (Entegrasyon)

```bash
# Bot'u başlat
python main.py

# Telegram'da test et
/analiz
# Okwis seç
# Türkiye seç
# Bitcoin yaz
# Analiz gelmeli ✅
```

**Durum:** Bot çalışıyor, yeni kod aktif ✅

---

### Adım 7: Git Commit

```bash
git add services/llm_service.py
git add app.py
git commit -m "feat: Add llm_service.py (backward compatible)"
git push
```

**Durum:** Değişiklik kaydedildi, geri alınabilir ✅

---

### Adım 8: Eski Kodu Sil (Opsiyonel, Acele Etme)

```python
# app.py

# Eski kod artık silinebilir (ama acele etme!)
# def _gemini_metin_uret(...):  # SİLİNDİ
#     pass
```

**Durum:** Kod temizlendi, ama acele edilmedi ✅

---

## 🔄 Rollback Planı

### Sorun Çıkarsa Ne Yapmalı?

#### Senaryo 1: Yeni Kod Çalışmıyor

```python
# app.py

# Geçici olarak yeni kodu devre dışı bırak
LLM_SERVICE_AVAILABLE = False  # Manuel olarak False yap

# Eski kod çalışmaya devam eder
```

**Süre:** 30 saniye  
**Etki:** Sıfır (eski kod devreye girer)

---

#### Senaryo 2: Import Hatası

```python
# app.py

try:
    from services.llm_service import llm_metin_uret as llm_metin_uret_v2
    LLM_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"llm_service import edilemedi: {e}")
    LLM_SERVICE_AVAILABLE = False
    llm_metin_uret_v2 = None
```

**Süre:** Otomatik  
**Etki:** Sıfır (eski kod devreye girer)

---

#### Senaryo 3: Git Rollback

```bash
# Son commit'i geri al
git revert HEAD

# Veya belirli bir commit'e dön
git reset --hard abc123

# Push
git push --force
```

**Süre:** 1 dakika  
**Etki:** Tüm değişiklikler geri alınır

---

## 📊 Güvenlik Seviyeleri

### Seviye 1: Çok Güvenli (Önerilen)
```
1. Yeni modül oluştur
2. Fonksiyonları kopyala (taşıma değil)
3. Test et
4. Wrapper ekle (backward compatible)
5. 1 hafta bekle
6. Eski kodu sil
```

**Süre:** 1 hafta  
**Risk:** %0

---

### Seviye 2: Güvenli
```
1. Yeni modül oluştur
2. Fonksiyonları kopyala
3. Test et
4. Wrapper ekle
5. 1 gün bekle
6. Eski kodu sil
```

**Süre:** 1 gün  
**Risk:** %5

---

### Seviye 3: Hızlı (Riskli)
```
1. Yeni modül oluştur
2. Fonksiyonları taşı (kopyalama değil)
3. Import'ları güncelle
4. Test et
```

**Süre:** 1 saat  
**Risk:** %30 (önerilmez!)

---

## 🧪 Test Stratejisi

### Unit Test (İzole)

```python
# tests/test_llm_service.py

import pytest
from services.llm_service import LLMService

def test_gemini_generate():
    service = LLMService()
    result = service.generate("Test", provider="gemini")
    assert result
    assert len(result) > 0

def test_fallback():
    service = LLMService()
    # Gemini başarısız olursa DeepSeek'e düşmeli
    result = service.generate("Test", provider="gemini", fallback=True)
    assert result
```

---

### Integration Test (Gerçek Akış)

```python
# tests/test_integration.py

import pytest
from app import llm_metin_uret

def test_llm_metin_uret_backward_compatible():
    # Eski API hala çalışmalı
    result = llm_metin_uret("Test prompt", user_id=123)
    assert result
    assert len(result) > 0

def test_okwis_flow():
    # Okwis akışı çalışmalı
    # (Telegram bot'u mock'layarak)
    pass
```

---

### Manuel Test (Telegram)

```
1. Bot'u başlat: python main.py
2. /analiz komutunu gönder
3. Her modu test et:
   - Mevsim ✅
   - Hava ✅
   - Jeopolitik ✅
   - Okwis ✅
   - Hızlı Para ✅
   - Teknik Analiz ✅
4. Hata mesajı olmamalı
5. Analiz sonuçları gelmeli
```

---

## 📈 İlerleme Takibi

### Faz 1: llm_service.py

- [ ] Modül oluşturuldu
- [ ] Fonksiyonlar kopyalandı
- [ ] Unit testler yazıldı
- [ ] Unit testler geçti
- [ ] app.py'de import eklendi
- [ ] Wrapper oluşturuldu
- [ ] Integration testler geçti
- [ ] Manuel test yapıldı
- [ ] Git commit
- [ ] 1 gün production'da çalıştı
- [ ] Eski kod silindi

**Durum:** 0/11 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜

---

### Faz 2: user_service.py

- [ ] Modül oluşturuldu
- [ ] Fonksiyonlar kopyalandı
- [ ] Unit testler yazıldı
- [ ] Unit testler geçti
- [ ] app.py'de import eklendi
- [ ] Wrapper oluşturuldu
- [ ] Integration testler geçti
- [ ] Manuel test yapıldı
- [ ] Git commit
- [ ] 1 gün production'da çalıştı
- [ ] Eski kod silindi

**Durum:** 0/11 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜

---

## 🎯 Başarı Kriterleri

### Her Faz İçin

✅ **Kod çalışıyor** (bot başlıyor)  
✅ **Testler geçiyor** (unit + integration)  
✅ **Manuel test başarılı** (Telegram'da çalışıyor)  
✅ **Hata yok** (log'larda error yok)  
✅ **Performans aynı** (süre değişmedi)  
✅ **Geriye uyumlu** (eski API çalışıyor)

---

## 💡 Öneriler

### DO (Yap)

✅ Küçük adımlarla ilerle  
✅ Her adımda test et  
✅ Git commit kullan  
✅ Backward compatibility sağla  
✅ Dokümantasyon yaz  
✅ Ekibi bilgilendir  

### DON'T (Yapma)

❌ Tüm kodu bir anda değiştirme  
❌ Test etmeden commit etme  
❌ Eski kodu hemen silme  
❌ Production'da direkt test etme  
❌ Rollback planı olmadan ilerle  

---

## 🚀 Özet

**Refactoring güvenli mi?**  
✅ **EVET**, eğer:
- Kademeli yapılırsa
- Her adımda test edilirse
- Geriye uyumlu olursa
- Rollback planı varsa

**Yapı bozulur mu?**  
❌ **HAYIR**, çünkü:
- Eski kod kalıyor (wrapper)
- Yeni kod opsiyonel
- Import hatası otomatik handle ediliyor
- Her adımda test ediliyor

**Ne kadar sürer?**  
⏱️ **1-2 hafta** (güvenli yaklaşım)
- Faz 1 (llm_service): 3 gün
- Faz 2 (user_service): 3 gün
- Faz 3 (subscription_service): 2 gün
- Faz 4 (handlers): 5 gün

**Risk nedir?**  
🛡️ **Çok düşük** (%5)
- Backward compatibility sayesinde
- Otomatik fallback sayesinde
- Test coverage sayesinde

---

**Hazırlayan:** Kiro AI  
**Tarih:** 30 Nisan 2026  
**Durum:** 📋 Plan Hazır, Onay Bekleniyor
