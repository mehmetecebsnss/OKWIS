# PROB ZİNCİRİ ENTEGRASYON REHBERİ

## ADIM 1: AI'DAN ZİNCİRLERİ AL

### Hangi AI'ları Kullanabilirsin?

1. **Claude 3.5 Sonnet** (Önerilen) ✅
   - En iyi yapılandırılmış çıktı
   - JSON formatında hata yapmaz
   - Tarihsel referanslar güçlü
   
2. **GPT-4** ✅
   - İyi kalite
   - Bazen JSON formatında hata yapabilir
   
3. **Gemini 2.0** ⚠️
   - Orta kalite
   - JSON formatını kontrol et

### Prompt Kullanımı

```bash
# 1. prob_zinciri_uretim_promptu.md dosyasını aç
# 2. Tüm içeriği kopyala
# 3. AI'ya yapıştır
# 4. "BAŞLA!" de
# 5. Çıktıyı al
```

### Beklenen Süre
- Claude: 10-15 dakika (200 zincir için)
- GPT-4: 15-20 dakika
- Gemini: 20-30 dakika

---

## ADIM 2: JSON DOĞRULAMA

AI'dan gelen çıktıyı doğrula:

```bash
# Terminal'de
cd /path/to/Makro-Lens
python -c "import json; json.load(open('prob_zinciri_full.json'))"
```

**Hata varsa:**
```bash
# Online JSON validator kullan
# https://jsonlint.com/
# Veya VS Code'da aç (otomatik hata gösterir)
```

---

## ADIM 3: MEVCUT DOSYAYLA BİRLEŞTİR

```python
# merge_prob_zincirleri.py
import json

# Mevcut zincirleri yükle
with open('data/prob_zinciri.json', 'r', encoding='utf-8') as f:
    mevcut = json.load(f)

# Yeni zincirleri yükle
with open('prob_zinciri_full.json', 'r', encoding='utf-8') as f:
    yeni = json.load(f)

# Birleştir (ID'ye göre dedupe)
mevcut_ids = {z['id'] for z in mevcut}
for zincir in yeni:
    if zincir['id'] not in mevcut_ids:
        mevcut.append(zincir)

# Kaydet
with open('data/prob_zinciri.json', 'w', encoding='utf-8') as f:
    json.dump(mevcut, f, ensure_ascii=False, indent=2)

print(f"Toplam zincir sayısı: {len(mevcut)}")
```

```bash
python merge_prob_zincirleri.py
```

---

## ADIM 4: PROMPT ENTEGRASYONUNİ İYİLEŞTİR

Mevcut `_ilgili_prob_zincirleri()` fonksiyonunu güçlendir:

```python
def _ilgili_prob_zincirleri(mod: str, ulke: str = "", varlik: str = "") -> str:
    """
    Mod + ülke + varlık kombinasyonuna göre en ilgili zincirleri getir.
    Gerçekleşme oranı ve güven seviyesine göre sırala.
    """
    zincirler = _prob_zinciri_yukle()
    
    # 1. Mod filtresi
    ilgili = [z for z in zincirler if mod in z.get("ilgili_modlar", [])]
    
    # 2. Varlık filtresi (varsa)
    if varlik:
        varlik_lower = varlik.lower()
        ilgili = [
            z for z in ilgili 
            if varlik_lower in str(z.get("ilgili_varliklar", [])).lower()
            or varlik_lower in z.get("baslik", "").lower()
        ]
    
    # 3. Ülke filtresi (opsiyonel - bazı zincirler ülke-spesifik olabilir)
    # Şimdilik genel zincirleri kullanıyoruz
    
    # 4. Sıralama: Önce güven seviyesi, sonra gerçekleşme oranı
    guven_sira = {"yuksek": 3, "orta": 2, "dusuk": 1}
    ilgili.sort(
        key=lambda x: (
            guven_sira.get(x.get("guven_seviyesi", "orta"), 2),
            x.get("gerceklesme_orani", 0)
        ),
        reverse=True
    )
    
    # 5. En iyi 5-10 zinciri al
    secili = ilgili[:10]
    
    if not secili:
        return ""
    
    # 6. Formatla
    satirlar = [
        "### 🔗 Sosyal İhtimal Zincirleri",
        f"({len(secili)}/{len(zincirler)} zincir bu analize uygun)\n"
    ]
    
    for idx, z in enumerate(secili, 1):
        baslik = z.get("baslik", "")
        gerceklesme = int(z.get("gerceklesme_orani", 0) * 100)
        guven = z.get("guven_seviyesi", "orta")
        guven_emoji = {"yuksek": "🟢", "orta": "🟡", "dusuk": "🟠"}.get(guven, "🟡")
        
        satirlar.append(
            f"{idx}. **{baslik}** {guven_emoji}\n"
            f"   Doğruluk: %{gerceklesme} | Tetikleyici: {z.get('tetikleyici', 'N/A')}"
        )
        
        # İlk 3 adımı göster
        for adim in z.get("zincir", [])[:3]:
            olay = adim.get("olay", "")
            etki = adim.get("etki", "")
            olasilik = int(adim.get("olasilik", 0) * 100)
            satirlar.append(f"   → {olay}: {etki} (olasılık: %{olasilik})")
        
        # Net etki
        satirlar.append(f"   ✓ Net etki: {z.get('net_etki', 'N/A')}\n")
    
    return "\n".join(satirlar)
```

---

## ADIM 5: ANALİZ FONKSİYONLARINI GÜNCELLE

Her analiz fonksiyonunda prob zincirlerini kullan:

```python
def mevsim_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "") -> str:
    """Mevsim analizi + prob zincirleri."""
    
    # Prob zincirlerini al
    prob_zincirleri = _ilgili_prob_zincirleri(
        mod=ANALIZ_MEVSIM,
        ulke=ulke,
        varlik=varlik
    )
    
    # Prompt'a ekle
    prompt = f"""
{_ANALIST_KIMLIK}

### Verilen Bağlam
{baglam_metni}

{prob_zincirleri}

### Görev
Sen deneyimli bir makro yatırım analistisin...

**KRİTİK:** Yukarıdaki sosyal ihtimal zincirlerini MUTLAKA analiz et.
- Hangi zincirler şu an aktif?
- Hangi adımlardayız?
- Sonraki adımlar ne olabilir?
- Gerçekleşme olasılıkları ne diyor?

{ANALIZ_DIL_NOTU}
"""
    
    # ... geri kalan kod
```

---

## ADIM 6: ÇIKTI FORMATINI İYİLEŞTİR

Kullanıcıya prob zincirlerini göster:

```python
async def cikti_format_secildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... mevcut kod ...
    
    # Analiz yap
    analiz = await asyncio.to_thread(mevsim_analizi_yap, ulke, baglam, stil, varlik)
    
    # Prob zincirleri özeti ekle (opsiyonel)
    prob_ozet = _prob_zinciri_ozeti(mod, ulke, varlik)
    
    # Mesaj oluştur
    mesaj = f"""
<b>🎯 OKWIS ANALİZİ</b>
<b>━━━━━━━━━━━━━━━━━━━━</b>

{_tg_html_escape(analiz)}

{prob_ozet}

{ANALIZ_FOOTER_HTML}
"""
    
    # ... geri kalan kod
```

---

## ADIM 7: TEST ET

```bash
# Bot'u başlat
python main.py

# Telegram'da test et
/analiz
→ Mevsim seç
→ Türkiye seç
→ Altın yaz
→ Uzun anlatım seç

# Kontrol et:
# ✅ Prob zincirleri gösteriliyor mu?
# ✅ İlgili zincirler mi?
# ✅ Analiz zincirleri kullanıyor mu?
```

---

## ADIM 8: İZLEME VE İYİLEŞTİRME

### Metrik Topla

```python
def _prob_zinciri_kullanim_kaydet(mod: str, kullanilan_zincir_sayisi: int):
    """Hangi modda kaç zincir kullanıldığını logla."""
    try:
        kayit = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mod": mod,
            "zincir_sayisi": kullanilan_zincir_sayisi
        }
        with open("metrics/prob_zinciri_kullanim.jsonl", "a") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Prob zinciri kullanım kaydedilemedi: %s", e)
```

### Performans Analizi

```python
def _prob_zinciri_performans():
    """Hangi zincirler en çok kullanılıyor? Hangileri doğru çıkıyor?"""
    # TODO: Gelecekte implement et
    pass
```

---

## ADIM 9: KULLANICI GERİ BİLDİRİMİ

```python
# /zincir_geri_bildirim komutu ekle
async def zincir_geri_bildirim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı bir zincirin doğru/yanlış çıktığını bildirir."""
    # TODO: Implement et
    pass
```

---

## ADIM 10: SÜREKLI GÜNCELLEME

### Aylık Güncelleme Rutini

```python
# update_prob_zincirleri.py
"""
Her ay:
1. Gerçekleşen olayları kontrol et
2. Doğru çıkan zincirlerin gerçekleşme_orani'nı artır
3. Yanlış çıkanları düşür
4. Yeni olaylar ekle
"""

def aylik_prob_zinciri_guncelleme():
    zincirler = _prob_zinciri_yukle()
    
    for z in zincirler:
        # Gerçekleşme oranını güncelle
        # (Manuel veya otomatik)
        pass
    
    # Kaydet
    with open('data/prob_zinciri.json', 'w', encoding='utf-8') as f:
        json.dump(zincirler, f, ensure_ascii=False, indent=2)
```

---

## SORUN GİDERME

### Problem: JSON parse hatası
**Çözüm:**
```bash
# JSON'u düzelt
python -m json.tool prob_zinciri_full.json > prob_zinciri_fixed.json
```

### Problem: Çok fazla zincir, prompt çok uzun
**Çözüm:**
```python
# En iyi 5 zinciri al (10 yerine)
secili = ilgili[:5]
```

### Problem: İlgisiz zincirler geliyor
**Çözüm:**
```python
# Filtreleme kriterlerini sıkılaştır
# Kategori filtresi ekle
ilgili = [
    z for z in zincirler 
    if mod in z.get("ilgili_modlar", [])
    and z.get("kategori") in ["mevsimsel", "emtia"]  # Örnek
]
```

---

## BAŞARI KRİTERLERİ

✅ 200+ zincir yüklendi
✅ JSON hatasız
✅ Prompt entegrasyonu çalışıyor
✅ Analiz zincirleri kullanıyor
✅ Kullanıcıya gösteriliyor
✅ Test edildi

---

## SONRAKI ADIMLAR

1. **Zincir Kütüphanesi Büyüt** (300, 500, 1000+)
2. **Otomatik Doğrulama** (Fiyat API'si ile)
3. **Makine Öğrenmesi** (Hangi zincirler en doğru?)
4. **Kullanıcı Katkısı** (Topluluk zincirleri)

---

**BAŞARILI ENTEGRASYON! 🎉**
