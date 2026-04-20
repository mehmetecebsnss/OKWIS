# 📊 Kalite Kartı Güncelleme

**Tarih:** 20 Nisan 2026  
**Durum:** ✅ TAMAMLANDI

---

## 🎯 Amaç

Analiz sonunda otomatik gösterilen kalite kartı çok detaylı ve çıktıyı kalabalık gösteriyordu. Kullanıcı deneyimini iyileştirmek için kalite kartı **isteğe bağlı** hale getirildi.

---

## 📝 Önceki Durum

Her analiz sonunda kalite kartı otomatik olarak gösteriliyordu:

```
━━━━━━━━━━━━━━━━━━━━
◆ Analiz Kalite Kartı
Veri: 81 haber başlığı, 70 web sonucu, 11 deprem kaydı, hava verisi
Bağlam: 🟢 Yüksek
Motor: Gemini 2.5 Flash
Güven: 67/100 🟢 Yüksek — sinyaller net, web araması destekledi (70 sonuç)
Kaynaklar:
  ▸ 8 mod paralel (Mevsim, Hava, Jeopolitik, Sektör, Trendler, Magazin, Özel Günler, Doğal Afet)
  ▸ Tavily Web Araması (70 sonuç)
Yatırım tavsiyesi değildir. Kendi araştırmanı yap.
```

**Sorun:** Çıktı çok uzun ve kalabalık görünüyordu.

---

## ✅ Yeni Durum

Analiz sonunda sadece **buton** gösteriliyor:

```
[Analiz metni burada...]

━━━━━━━━━━━━━━━━━━━━
Yatırım tavsiyesi değildir. Kendi araştırmanı yap.

[📊 Kalite Kartını Göster]  ← Buton
```

Kullanıcı isterse butona tıklayıp kalite kartını görebilir.

---

## 🔧 Yapılan Değişiklikler

### 1. Güven Kartı Context'e Kaydedildi

```python
# Güven kartını context'e kaydet (buton ile göstermek için)
guven_karti = _guven_karti_html(analiz_turu, baglam, guven_olayi, user_id)
context.user_data["son_guven_karti"] = guven_karti
context.user_data["son_analiz_mod"] = analiz_turu
```

### 2. Mesaj Güven Kartı Olmadan Gönderildi

```python
# Mesajı güven kartı OLMADAN gönder
mesaj_govde = sarmla_analiz_mesaji_html(ulke, stil, analiz, analiz_turu=analiz_turu)

# Kalite kartı butonu ekle
keyboard = [[InlineKeyboardButton("📊 Kalite Kartını Göster", callback_data="show_quality_card")]]
reply_markup = InlineKeyboardMarkup(keyboard)

await gonder_parcali_html(query, context, mesaj_govde, reply_markup=reply_markup)
```

### 3. Callback Handler Eklendi

```python
async def kalite_karti_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kalite kartını göster butonu"""
    query = update.callback_query
    await query.answer()
    
    guven_karti = context.user_data.get("son_guven_karti", "")
    
    if not guven_karti:
        await query.answer("Kalite kartı bulunamadı. Yeni bir analiz yapın.", show_alert=True)
        return
    
    # Kalite kartını mesaj olarak gönder
    await query.message.reply_text(
        guven_karti,
        parse_mode=ParseMode.HTML,
    )
    await query.answer("✅ Kalite kartı gösterildi")
```

### 4. Handler Kaydedildi

```python
# Kalite kartı butonu handler
app.add_handler(CallbackQueryHandler(kalite_karti_goster, pattern="^show_quality_card$"))
```

### 5. `gonder_parcali_html` Fonksiyonu Güncellendi

```python
async def gonder_parcali_html(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    tam_metin: str,
    reply_markup: InlineKeyboardMarkup | None = None,  # ← Yeni parametre
) -> None:
    # ... (buton son mesaja eklenir)
```

---

## 📍 Güncellenen Yerler

1. ✅ **Normal Analiz Modları** (Mevsim, Hava, Jeopolitik, vb.)
   - `cikti_format_secildi()` fonksiyonu
   - Analiz sonunda tek buton: "📊 Kalite Kartını Göster"

2. ✅ **Okwis Kısa Analiz**
   - `ulke_secildi()` fonksiyonu (Okwis modu)
   - İki satır buton:
     - Satır 1: "🔍 Daha derin analiz"
     - Satır 2: "📊 Kalite Kartı" | "✕ Kapat"

3. ✅ **Okwis Detay Analiz**
   - `okwis_detay_secildi()` fonksiyonu
   - Analiz sonunda tek buton: "📊 Kalite Kartını Göster"

4. ✅ **Sesli/Yazılı Okwis Analizi**
   - `_sesli_okwis_analizi_calistir()` fonksiyonu
   - İki satır buton (kısa analiz ile aynı)

---

## 🎨 Kullanıcı Deneyimi

### Önceki Akış
1. Kullanıcı analiz ister
2. Bot analiz + kalite kartı gönderir (uzun mesaj)
3. Kullanıcı kaydırarak okur

### Yeni Akış
1. Kullanıcı analiz ister
2. Bot sadece analiz gönderir (kısa, temiz)
3. Kullanıcı isterse "📊 Kalite Kartını Göster" butonuna tıklar
4. Bot kalite kartını ayrı mesaj olarak gönderir

**Avantajlar:**
- ✅ Çıktı daha temiz ve okunabilir
- ✅ Kullanıcı sadece ilgilendiği bilgiyi görür
- ✅ Kalite kartı hala erişilebilir (kaybolmadı)
- ✅ Mobil cihazlarda daha iyi deneyim

---

## 🧪 Test Senaryoları

### Test 1: Normal Analiz
```
1. /analiz → Mevsim → Türkiye → Detaylı Analiz
2. Analiz sonunda "📊 Kalite Kartını Göster" butonu görünmeli
3. Butona tıkla
4. Kalite kartı ayrı mesaj olarak gelmeli
```

### Test 2: Okwis Kısa Analiz
```
1. /analiz → Okwis → ABD
2. Kısa analiz sonunda iki satır buton görünmeli:
   - "🔍 Daha derin analiz"
   - "📊 Kalite Kartı" | "✕ Kapat"
3. "📊 Kalite Kartı" butonuna tıkla
4. Kalite kartı ayrı mesaj olarak gelmeli
```

### Test 3: Okwis Detay Analiz
```
1. Okwis kısa analizden sonra "🔍 Daha derin analiz" tıkla
2. Detay analiz sonunda "📊 Kalite Kartını Göster" butonu görünmeli
3. Butona tıkla
4. Kalite kartı ayrı mesaj olarak gelmeli
```

### Test 4: Sesli Komut
```
1. Sesli mesaj gönder: "Japonya için çip analizi yap"
2. Okwis analizi gelsin
3. "📊 Kalite Kartı" butonu görünmeli
4. Butona tıkla
5. Kalite kartı ayrı mesaj olarak gelmeli
```

---

## 📊 Kalite Kartı İçeriği

Kalite kartı şu bilgileri içerir:

- **Veri:** Kaç haber başlığı, web sonucu, deprem kaydı, hava verisi kullanıldı
- **Bağlam:** Veri zenginliği (🟢 Yüksek, 🟡 Orta, 🟠 Düşük)
- **Motor:** Hangi AI motoru kullanıldı (Gemini, DeepSeek, Claude)
- **Güven:** Analiz güven skoru (0-100) ve açıklama
- **Kaynaklar:** Hangi veri kaynakları kullanıldı

Bu bilgiler kullanıcının analizin kalitesini değerlendirmesine yardımcı olur.

---

## 🔄 Geriye Dönük Uyumluluk

- ✅ Eski analizler etkilenmez (kalite kartı yok, buton da yok)
- ✅ Yeni analizlerde buton görünür
- ✅ Context temizlenirse (bot yeniden başlatılırsa) kalite kartı kaybolur, ama yeni analiz yapılınca tekrar gelir

---

## 📁 Değiştirilen Dosyalar

- ✅ `app.py` (5 fonksiyon güncellendi, 1 yeni fonksiyon eklendi)
  - `gonder_parcali_html()` - reply_markup parametresi eklendi
  - `cikti_format_secildi()` - güven kartı kaldırıldı, buton eklendi
  - `ulke_secildi()` (Okwis) - güven kartı kaldırıldı, buton eklendi
  - `okwis_detay_secildi()` - güven kartı kaldırıldı, buton eklendi
  - `_sesli_okwis_analizi_calistir()` - güven kartı kaldırıldı, buton eklendi
  - `kalite_karti_goster()` - yeni callback handler
  - Handler kaydı eklendi

- ✅ `GUNCELLEME_GUNLUGU.md` - güncelleme kaydedildi
- ✅ `KALITE_KARTI_GUNCELLEME.md` - bu dosya (detaylı dokümantasyon)

---

## 🚀 Sonraki Adımlar

1. ⏳ Botu yeniden başlat
2. ⏳ Test senaryolarını çalıştır
3. ⏳ Kullanıcı geri bildirimlerini topla
4. ⏳ Gerekirse buton metnini/stilini ayarla

---

**Hazırlayan:** Kiro AI  
**Tarih:** 20 Nisan 2026  
**Durum:** ✅ TAMAMLANDI
