# Okwis AI — Verimlilik ve Kalite Raporu

**Tarih:** 20 Nisan 2026  
**Kapsam:** Tüm analiz modları, prompt mimarisi, token verimliliği, çıktı kalitesi

---

## YÖNETİCİ ÖZETİ

Mevcut sistem teknik olarak sağlam ama **token israfı yüksek, prompt mimarisi tekrarlı, bağlam kalitesi mod bazında dengesiz.** Aşağıdaki 6 iyileştirme uygulandığında aynı token bütçesiyle **2-3x daha derin ve tutarlı çıktı** alınabilir.

---

## 1. MEVCUT DURUM ANALİZİ

### 1.1 Token Bütçesi Nereye Gidiyor?

Her analizde yaklaşık token dağılımı:

| Bileşen | Tahmini Token | Sorun |
|---------|--------------|-------|
| `_ANALIST_KIMLIK` | ~120 token | Her modda tekrar ediyor |
| `mod_direktifi` | ~80-120 token | Her modda benzer yapı |
| `baglam_metni` (RSS başlıkları) | ~300-600 token | Çoğu başlık ilgisiz |
| `varlik_detay_directive` | ~200-400 token | Çok uzun, tekrarlı |
| `prob_notu` (3 zincir × 4 adım) | ~150-250 token | Çoğu zaman ilgisiz |
| Analiz rehberi (bağlam modülünde) | ~100-150 token | Sonra prompt'ta tekrar soruluyor |
| Prompt'taki format talimatları | ~80-120 token | Her modda benzer |
| **TOPLAM GİRDİ** | **~1.000-1.700 token** | |
| **Model çıktısı** | ~400-800 token | |

**Sorun:** Girdi tokenlarının %40-50'si ya tekrarlı ya da düşük sinyal/gürültü oranına sahip.

---

### 1.2 Kritik Sorunlar

#### SORUN 1: Çift Analiz Rehberi (Yüksek Öncelik)

Her bağlam modülü (`mevsim_baglam.py`, `jeopolitik_baglam.py` vb.) kendi `### Analiz Rehberi` bölümünü üretiyor. Sonra `app.py`'deki analiz fonksiyonu aynı soruları `mod_direktifi` olarak tekrar soruyor.

```
mevsim_baglam.py → "1. MEVSİMSEL DÖNGÜ: ... 2. HABER ÖRTÜŞMESI: ..."
app.py → "SEN BİR MEVSİM ANALİSTİSİN... Odak noktaların: - Bu mevsimde hangi sektörler..."
```

**Etki:** ~150-200 token israfı + model kafası karışıyor (iki farklı rehber var).

---

#### SORUN 2: `_varlik_detay_directive` Aşırı Uzun (Yüksek Öncelik)

Petrol için kış direktifi ~400 token. Bunun %70'i genel bilgi ("OPEC kararları fiyatı belirler"), modelin zaten bildiği şeyler. Gerçekten değer katan kısım sadece ~80 token.

```python
# Şu an: 400 token
"— Isınma (doğalgaz, ısıtma yağı) talebinden petrol fiyatları tipik yükseliş gösterir
— Enerji enflasyonu → taşımacılık, lojistik maliyetleri artar
— Coğrafı riskler (Orta Doğu, Rusya) petrol volatilitesini arttırır
— OPEC karmaşası, dolar kuru, stok seviyeleri asıl belirleyiciler
**Soru:** {ulke}'de bu dönemde enerji talebinin fiyatlaşması..."
```

Model bu bilgileri zaten biliyor. Direktifin tek değeri: **modeli doğru çerçeveye kilitlemek.** Bunun için 80 token yeterli.

---

#### SORUN 3: Prob Zinciri Entegrasyonu Kör (Orta Öncelik)

`_ilgili_prob_zincirleri(mod)` her zaman 3 zincir döndürüyor, ülke veya varlıkla eşleşme yapmıyor. Türkiye + altın analizi yapılırken "Japonya seçim döngüsü" zinciri de gelebiliyor.

```python
# Şu an: mod bazlı filtreleme
ilgili = [z for z in zincirler if mod in z.get("ilgili_modlar", [])]

# Olması gereken: mod + ülke + varlık bazlı filtreleme
ilgili = [z for z in zincirler if 
    mod in z.get("ilgili_modlar", []) and
    (not z.get("ulke") or z.get("ulke") == ulke) and
    (not varlik or varlik.lower() in z.get("ilgili_varliklar", []))]
```

---

#### SORUN 4: RSS Başlıkları Ham Geliyor (Orta Öncelik)

Bağlam modülleri RSS başlıklarını filtreli gönderiyor ama başlıklar hâlâ çok genel. "Apple reports record earnings" başlığı Türkiye + altın analizinde hiçbir değer taşımıyor ama token harcıyor.

**Çözüm:** Başlıkları ülke + varlık + mod kombinasyonuna göre skorla, en ilgili 5'i gönder.

---

#### SORUN 5: Okwis Bağlam Kesimi Verimsiz (Yüksek Öncelik)

```python
# Şu an: her mod için sabit limit
limit = 300 if stil == "kisa" else 600
parcalar.append(f"[{etiket}]\n{v[:limit]}")
```

8 modun bağlamı birleştirilirken her mod eşit ağırlık alıyor. Ama Okwis analizinde jeopolitik ve mevsim genellikle daha değerli, magazin ve trendler daha az. Sabit kesim yerine **dinamik önem sıralaması** gerekiyor.

---

#### SORUN 6: `_ANALIST_KIMLIK` Her Modda Aynı (Düşük Öncelik)

120 tokenlik kimlik bloğu her modda tekrar ediyor ve mod-agnostik. Mevsim analisti ile doğal afet analisti aynı kimliği paylaşıyor. Mod-spesifik kısa kimlik daha etkili olur.

---

#### SORUN 7: Güven Skoru Prompt'a Enjekte Ediliyor (Düşük Öncelik)

```python
f"Güven: {g_toplam}/100 ({g_etiket})\n\n"
```

Bu satır modele "bu analizin güveni düşük" diye söylüyor ve model bunu çıktıya yansıtıyor. Ama güven skoru kullanıcıya gösterilmeli, modele değil. Model kendi çıktısını kısıtlamamalı.

---

## 2. ÖNERİLEN İYİLEŞTİRMELER

### İYİLEŞTİRME 1: Çift Analiz Rehberini Kaldır

**Etki:** ~150 token tasarruf + daha net model yönlendirmesi  
**Zorluk:** Düşük  
**Uygulama:** Bağlam modüllerindeki `### Analiz Rehberi` bölümlerini kaldır. Tüm yönlendirme `app.py`'deki `mod_direktifi`'nde kalsın.

```python
# mevsim_baglam.py'den kaldırılacak:
analiz_rehberi = f"""### Analiz Rehberi
Yukarıdaki mevsim ve haber verilerinden şu soruları yanıtla:
1. MEVSİMSEL DÖNGÜ: ...
"""
parcalar.append(analiz_rehberi)  # BU SATIR KALDIRILACAK
```

Bağlam modülleri sadece **ham veri** döndürmeli. Yorum talimatı `app.py`'de.

---

### İYİLEŞTİRME 2: `_varlik_detay_directive` Sıkıştır

**Etki:** ~200-300 token tasarruf, daha keskin yönlendirme  
**Zorluk:** Orta  

Direktifler şu an "genel bilgi + soru" formatında. Sadece "soru + kısıtlayıcı çerçeve" formatına geç:

```python
# ÖNCE (~400 token):
"""**VARLIK ANALİZİ — PETROL (Ocak):**
Ocak kış döneminin ortası/sonu; enerji talebinin pik noktası.
— Isınma talebinden petrol fiyatları tipik yükseliş gösterir
— Enerji enflasyonu → taşımacılık, lojistik maliyetleri artar
— OPEC karmaşası, dolar kuru, stok seviyeleri asıl belirleyiciler
**Soru:** Türkiye'de bu dönemde enerji talebinin fiyatlaşması nasıl?"""

# SONRA (~80 token):
"""VARLIK ODAĞI — PETROL/KIŞ: Kış enerji talebi piki + OPEC/dolar/stok üçgenini
analiz et. Türkiye net ithalatçı — dış Brent fiyatı belirleyici. 
Kısa vade: ısınma talebi vs. stok seviyeleri. Somut fiyat seviyeleri ver."""
```

---

### İYİLEŞTİRME 3: Prob Zinciri Akıllı Filtreleme

**Etki:** Daha ilgili zincirler → daha derin çıktı  
**Zorluk:** Düşük  

```python
def _ilgili_prob_zincirleri(mod: str, ulke: str = "", varlik: str = "") -> str:
    zincirler = _prob_zinciri_yukle()
    
    def skor(z):
        puan = 0
        if mod in z.get("ilgili_modlar", []):
            puan += 3
        if ulke and ulke.lower() in z.get("baslik", "").lower():
            puan += 2
        if varlik and varlik.lower() in z.get("baslik", "").lower():
            puan += 2
        if ulke and ulke.lower() in z.get("tetikleyici", "").lower():
            puan += 1
        return puan
    
    ilgili = sorted(
        [z for z in zincirler if skor(z) > 0],
        key=skor, reverse=True
    )[:2]  # 3 yerine 2 — daha az ama daha ilgili
    
    # ... geri kalan aynı
```

---

### İYİLEŞTİRME 4: Okwis Bağlam Dinamik Ağırlıklandırma

**Etki:** Okwis çıktı kalitesi belirgin artış  
**Zorluk:** Orta  

```python
# Şu an: sabit limit
limit = 300 if stil == "kisa" else 600

# Önerilen: mod önem sıralaması
MOD_ONEM = {
    "jeopolitik": 1.5,   # En yüksek sinyal
    "mevsim": 1.3,
    "sektor": 1.2,
    "dogal_afet": 1.1,
    "hava": 1.0,
    "trendler": 0.8,
    "ozel_gun": 0.7,
    "magazin": 0.6,      # En düşük sinyal
}

baz_limit = 250 if stil == "kisa" else 500
for key, etiket in etiketler.items():
    v = baglamlar.get(key, "").strip()
    if v:
        mod_limit = int(baz_limit * MOD_ONEM.get(key, 1.0))
        parcalar.append(f"[{etiket}]\n{v[:mod_limit]}")
```

Bu değişiklikle Okwis toplam bağlam token'ı azalırken **bilgi yoğunluğu artar.**

---

### İYİLEŞTİRME 5: RSS Başlık Skoru

**Etki:** Bağlam kalitesi artışı, token tasarrufu  
**Zorluk:** Orta  

Bağlam modüllerine ülke + varlık bazlı başlık skoru ekle:

```python
def _baslik_skoru(baslik: str, ulke: str, varlik: str = "") -> int:
    """Başlığın bu analiz için ne kadar ilgili olduğunu skorla."""
    b = baslik.lower()
    ulke_lower = ulke.lower()
    puan = 0
    
    # Ülke adı geçiyor mu?
    if ulke_lower in b or ULKE_INGILIZCE.get(ulke, "").lower() in b:
        puan += 3
    
    # Varlık adı geçiyor mu?
    if varlik and varlik.lower() in b:
        puan += 2
    
    # Yüksek değerli finansal kelimeler
    for kelime in ["rate", "inflation", "gdp", "crisis", "war", "oil", "gold", "fed"]:
        if kelime in b:
            puan += 1
            break
    
    return puan

# Kullanım:
basliklar_skorlu = sorted(
    [(b, _baslik_skoru(b, ulke, varlik)) for b in tum_basliklar],
    key=lambda x: x[1], reverse=True
)
en_iyi_5 = [b for b, _ in basliklar_skorlu[:5]]
```

---

### İYİLEŞTİRME 6: Güven Skoru Prompt'tan Çıkar

**Etki:** Model kendi çıktısını kısıtlamaz, daha cesur analiz  
**Zorluk:** Düşük  

```python
# ÖNCE (modele söylüyoruz):
f"Güven: {g_toplam}/100 ({g_etiket})\n\n"

# SONRA (sadece kullanıcıya göster, modele söyleme):
# Güven skoru sadece _guven_karti_html() içinde kullanılsın
# Prompt'tan bu satır kaldırılsın
```

---

### İYİLEŞTİRME 7: Mod-Spesifik Kısa Kimlik

**Etki:** Daha odaklı model davranışı  
**Zorluk:** Düşük  

```python
# Şu an: tek evrensel kimlik (120 token)
_ANALIST_KIMLIK = """Sen kıdemli bir makro yatırım analistisin..."""

# Önerilen: mod başına kısa kimlik (40-50 token)
_MOD_KIMLIK = {
    "mevsim": "Mevsimsel döngü uzmanısın. Sadece mevsimsel veriden çıkarım yap.",
    "hava": "Hava-ekonomi analistisin. Sadece hava verisinden ekonomik çıkarım yap.",
    "jeopolitik": "Jeopolitik risk analistisin. Haber başlıklarından risk kanallarını tespit et.",
    "sektor": "Sektör analistisin. Haber başlıklarından sektörel momentum tespit et.",
    "trendler": "Trend analistisin. Viral/sosyal olayların piyasa yansımasını analiz et.",
    "magazin": "Marka-piyasa analistisin. Ünlü/viral olayların şirket değerine etkisini analiz et.",
    "ozel_gun": "Takvim-ekonomi analistisin. Özel günlerin tüketim ve piyasa etkisini analiz et.",
    "dogal_afet": "Afet ekonomisi analistisin. Doğal afetlerin yeniden yapılanma ekonomisini analiz et.",
}

# Ortak kurallar ayrı, kısa (60 token):
_ORTAK_KURALLAR = """Net yön ver. al/izle/kaçın kullan. Somut fiyat/tarih ver.
Kaçamak dil yok. Ters senaryo somut olsun. Türkçe yaz."""
```

---

## 3. BEKLENEN KAZANIMLAR

| İyileştirme | Token Tasarrufu | Kalite Artışı |
|-------------|----------------|---------------|
| 1. Çift rehber kaldır | ~150 token/analiz | Orta |
| 2. Direktif sıkıştır | ~200 token/analiz | Yüksek |
| 3. Prob zinciri filtrele | ~50 token/analiz | Yüksek |
| 4. Okwis dinamik ağırlık | ~100 token/Okwis | Çok Yüksek |
| 5. RSS başlık skoru | ~100 token/analiz | Yüksek |
| 6. Güven skoru çıkar | ~20 token/analiz | Orta |
| 7. Mod-spesifik kimlik | ~70 token/analiz | Orta |
| **TOPLAM** | **~690 token/analiz** | |

**Net etki:** Her analizde ~690 token tasarruf = **%40-45 daha verimli prompt.**  
Bu tasarruf ya daha derin bağlam (daha fazla RSS başlığı, daha uzun Tavily özeti) ya da daha uzun model çıktısı için kullanılabilir.

---

## 4. UYGULAMA ÖNCELİK SIRASI

### Faz 1 — Hızlı Kazanımlar (1-2 saat)
1. **Güven skoru prompt'tan çıkar** (6 analiz fonksiyonu, tek satır değişiklik)
2. **Çift analiz rehberini kaldır** (7 bağlam modülü, son `parcalar.append(analiz_rehberi)` satırı)
3. **Prob zinciri akıllı filtreleme** (`_ilgili_prob_zincirleri` fonksiyonu)

### Faz 2 — Orta Efor (2-3 saat)
4. **Direktif sıkıştırma** (`_varlik_detay_directive` fonksiyonu)
5. **Mod-spesifik kimlik** (`_ANALIST_KIMLIK` yerine `_MOD_KIMLIK` dict)

### Faz 3 — Derin İyileştirme (3-4 saat)
6. **Okwis dinamik ağırlıklandırma** (`okwis_analizi_yap` fonksiyonu)
7. **RSS başlık skoru** (tüm bağlam modülleri)

---

## 5. EK: BAĞLAM KALİTESİ MOD BAZINDA

| Mod | Bağlam Kalitesi | Sorun | Çözüm |
|-----|----------------|-------|-------|
| Mevsim | ★★★★☆ | Analiz rehberi çift | Rehberi kaldır |
| Hava | ★★★★★ | İyi — OpenWeather verisi zengin | — |
| Jeopolitik | ★★★★☆ | Başlıklar bazen ilgisiz | RSS başlık skoru |
| Sektör | ★★★☆☆ | Çok genel başlıklar | RSS başlık skoru + ülke filtresi |
| Trendler | ★★★☆☆ | Viral haber bulmak zor | Tavily ağırlığı artır |
| Magazin | ★★☆☆☆ | Magazin başlığı az geliyor | Tavily zorunlu yap |
| Özel Günler | ★★★★☆ | JSON verisi iyi | — |
| Doğal Afet | ★★★★★ | USGS verisi çok değerli | — |
| **Okwis** | ★★★☆☆ | 8 mod eşit ağırlık | Dinamik ağırlıklandırma |

---

## 6. SONUÇ

Mevcut sistem **doğru yönde** ama token bütçesi verimsiz kullanılıyor. En kritik sorun: **bağlam modülleri ile analiz fonksiyonları arasındaki çift yönlendirme.** Bu tek sorun çözülse bile çıktı kalitesi belirgin artacak.

Faz 1 uygulandığında:
- Her analiz ~690 token daha verimli
- Model daha az "kafası karışık" yönlendirme alıyor
- Prob zincirleri gerçekten ilgili geliyor
- Okwis en değerli modlara daha fazla bağlam veriyor

**Tavsiye:** Faz 1'i hemen uygula, sonuçları gözlemle, Faz 2-3'e geç.
