# Varlık Odaklı Analiz Özelliği

**Uygulandı:** 2026-04-10  
**Durum:** ✅ Aktif  
**Parça:** Güncelleme-Önerileri.md — Satır 243 İşleme Alındı

---

## Özellik Açıklama

Kullanıcı bir mod (Mevsim, Hava, jeopolitik) ile ülke seçiminden sonra, bot **"Özellikle odaclanmak istediğin bir varlık var mı?"** sorusu sorar.

### Kullanıcı Seçeneği:
1. **Varlık adı yazma** (kripto, altın, petrol, doğalgaz, hisse, emtia vb.)
   - Yazı ile input (seçenek menüsü YOK)
   - Bu varlığa odaklı analiz yapılır
   
2. **Geçme** (`/skip` komutu)
   - Genel analiz yapılır (varlık odağı yok)

---

## Akış Değişikliği

### Önceki Akış
```
/analiz
  ↓
Mod seç (inline keyboard)
  ↓
Ülke seç (inline keyboard)
  ↓
Çıktı stili seç (uzun/kısa, inline keyboard)
  ↓
Analiz gösterilir
```

### Yeni Akış (Bu sürüm)
```
/analiz
  ↓
Mod seç (inline keyboard)
  ↓
Ülke seç (inline keyboard)
  ↓
✨ VARLIK SORUSU (metin giriş veya /skip) ← YENİ
  ↓
Çıktı stili seç (uzun/kısa, inline keyboard)
  ↓
Analiz gösterilir (varlik odaklı veya genel)
```

---

## Teknik Uygulama

### State Machine
```python
MOD_SECIMI = 0       # Kullanıcı analiz modu seçiyor
ULKE_SECIMI = 1      # Kullanıcı ülke seçiyor
VARLIK_SORGUSU = 2   # ✨ YENİ: Kullanıcı varlık adı yazıyor (metin girişi)
FORMAT_SECIMI = 3    # Çıktı stili seç (formattan artırıldı)
```

### ConversationHandler
```python
states={
    MOD_SECIMI: [CallbackQueryHandler(mod_secildi)],
    ULKE_SECIMI: [CallbackQueryHandler(ulke_secildi)],
    VARLIK_SORGUSU: [MessageHandler(filters.TEXT & ~filters.COMMAND, varlik_sorgusu_cevap)],  # ✨ YENİ
    FORMAT_SECIMI: [CallbackQueryHandler(cikti_format_secildi)],
},
```

### Fonksiyon Güncellemeleri

**`ulke_secildi()`** — Varlık sorusu sorar
```python
await query.edit_message_text(
    f"✅ {ulke} seçildi.\n\n"
    "Özellikle odaklanmak istediğin bir varlık var mı?\n"
    "Örneğin: kripto, altın, petrol, doğalgaz, vs.\n\n"
    "Yazarak cevap ver veya boş geçmek için /skip yaz (genel analiz yapılır).",
)
return VARLIK_SORGUSU
```

**`varlik_sorgusu_cevap()`** — Metin input alır ✨ YENİ
```python
async def varlik_sorgusu_cevap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metin = update.message.text.strip()
    
    if metin.lower() == "/skip":
        context.user_data["varlik"] = ""
        skip_msg = "Tamam, genel analiz yapacağım."
    else:
        context.user_data["varlik"] = metin
        skip_msg = f"Adım. {metin} üzerinde odaklanıp analiz yapacağım."
    
    # Çıktı stili sorusu
    # FORMAT_SECIMI'ye git
    return FORMAT_SECIMI
```

**`mevsim_analizi_yap()`, `hava_analizi_yap()`, `jeopolitik_analizi_yap()`** — Varlık parametresi
```python
def mevsim_analizi_yap(ulke: str, baglam_metni: str, cikti_stili: str = CIKTI_DETAY, varlik: str = "") -> str:
    # ...
    varlik_notu = ""
    if varlik and varlik.strip():
        varlik_notu = f"\n\n**ODAKLANAN VARLIK:** Kullanıcı özellikle **{varlik}** üzerinde odaklanmak istiyor. Bu varlığın bu mevsim/dönemde nasıl etkileneceğini ön planda tut."
    
    # Prompt'a enjekte: {baglam_metni}{varlik_notu}
```

**`cikti_format_secildi()`** — Varlik'i çıkarmak ve geçmek
```python
varlik = context.user_data.get("varlik", "")

# Analiz fonksiyonlarına geçir:
analiz = await asyncio.to_thread(mevsim_analizi_yap, ulke, baglam, stil, varlik)
analiz = await asyncio.to_thread(hava_analizi_yap, ulke, baglam, stil, varlik)
analiz = await asyncio.to_thread(jeopolitik_analizi_yap, ulke, baglam, stil, varlik)
```

---

## Prompt Entegrasyonu

Her analiz fonksiyonunun prompt'u, eğer `varlik` boş değilse, başa şu satırı ekler:

```
**ODAKLANAN VARLIK:** Kullanıcı özellikle **{varlik}** üzerinde odaklanmak istiyor. 
Bu varlığın [mod konteksti]'nde nasıl etkileneceğini ön planda tut.
```

### Örnek Prompt (Mevsim + Altın):
```
[Bağlam verileri...]

**ODAKLANAN VARLIK:** Kullanıcı özellikle **altın** üzerinde odaklanmak istiyor. 
Bu varlığın bu mevsim/dönemde nasıl etkileneceğini ön planda tut.

---

### Görev (kısa özet kartı)
Sen deneyimli bir makro yatırım analistsin...
```

---

## Kullanıcı Deneyimi

### Örnek 1: Altın odaklı mevsim analizi (Türkiye, Mayıs)
```
Bot: ✅ Türkiye seçildi.

Özellikle odaklanmak istediğin bir varlık var mı?
Örneğin: kripto, altın, petrol, doğalgaz, vs.

Yazarak cevap ver veya boş geçmek için /skip yaz.

Kullanıcı: altın

Bot: Adım. Altın üzerinde odaklanıp analiz yapacağım.

Nasıl göstereyim?
• 📖 Uzun anlatım — detaylı metin
• ⚡ Kısa özet — kritik satırlar, tek bakışta

[Kullanıcı seçer] → Bot altına odaklı mevsim analizi yapar
```

### Örnek 2: Genel jeopolitik analizi (ABD, Haziran)
```
Bot: ✅ ABD seçildi.

Özellikle odaklanmak istediğin bir varlık var mı?
...

Kullanıcı: /skip

Bot: Tamam, genel analiz yapacağım.

Nasıl göstereyim?
...

[Kullanıcı seçer] → Bot genel jeopolitik analizi yapar (varlık odağı yok)
```

---

## Dosya Değişiklikleri

| Dosya | Satır | Değişiklik |
|-------|-------|-----------|
| `app.py` | 238 | VARLIK_SORGUSU state'i eklendi |
| `app.py` | 1583-1618 | `ulke_secildi()` güncellendi (varlık sorusu ekle) |
| `app.py` | 1621-1652 | `varlik_sorgusu_cevap()` ✨ YENİ fonksiyon |
| `app.py` | 1058 | `mevsim_analizi_yap(varlik: str = "")` parametresi |
| `app.py` | 1156 | `hava_analizi_yap(varlik: str = "")` parametresi |
| `app.py` | 1254 | `jeopolitik_analizi_yap(varlik: str = "")` parametresi |
| `app.py` | 1662 | `cikti_format_secildi()` varlik çıkarma |
| `app.py` | 1797 | ConversationHandler state'e VARLIK_SORGUSU ekleme |
| `app.py` | 1658, 1688, 1707-... | Prompt'lara varlik_notu enjeksiyonu |

---

## Test Listeesi

- [ ] `/analiz` → Mevsim → Türkiye → "kripto" yazma → Çıktı seç → Analiz kontrol
- [ ] `/analiz` → Hava → ABD → "/skip" yazma → Çıktı seç → Genel analiz kontrol
- [ ] `/analiz` → Jeopolitik → Diğer → "petrol" yazma → Çıktı seç → Analiz kontrol
- [ ] Varlık adı yazıp komut girmeme (sadece yazı): `/cancel` test
- [ ] Çok uzun varlık adı girme: prompt'ta doğru biçimlenme kontrolü

---

## Sonraki İyileştirmeler (İsteğe Bağlı)

1. **Önerilen varlık listesi** — Varlık sorusu yerine küçük inline keyboard öneri (seçenek menüsü)
   - Fakat brief'te "seçenek vermemeli" dendiği için şu anda yazı girdisi tercih edildi

2. **Varlık takviyesi** — Aynı sohbettayken tekrar `/analiz` yapıldığında varlık hafızada kalıp kalmadığı
   - Şu anda her /analiz sonrası context.user_data oğlanmıyor

3. **Varlık validasyonu** — Yazılan varlık tanınabilir mi kontrol; yanlış yazılan varlıkları uyar
   - Şu anda herhangi yazı inputs alınıyor

---

## Notlar

- **Metin input:** Seçenek menüsü yok, tamamen yazı ile (brief'te istenci: "yazı ile yazmalıyız bize seçenek vermemeli")
- **Varlık defaultü:** Boş ("") => genel analiz yapılır
- **Skip komutu:** `/skip` yazarsa varlık boş kalır ve genel analiz yapılır
- **Prompt'a ek:** Varlik odağı, prompt'un başında açık direktif olarak yer alır; model bu direktifi dikkate almalı

---

**Tarih:** 2026-04-10  
**Durum:** ✅ Uygulandı ve Syntax kontrol tamamlandı
