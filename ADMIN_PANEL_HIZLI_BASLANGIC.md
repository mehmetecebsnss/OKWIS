# Admin Panel - Hızlı Başlangıç 🚀

## 🎯 Ne Eklendi?

Sadece adminlerin kullanabileceği 2 yeni komut:

### `/admin` - Özet Panel
- 📊 Toplam kullanıcı sayısı
- 🟢 Aktif kullanıcı sayısı (bugün)
- 💎 Plan dağılımı (Free/Pro/Claude)
- 👥 En aktif 15 kullanıcı
- 🚀 Start komutu istatistikleri

### `/admin_detay` - Detaylı Liste
- Tüm kullanıcıların tam listesi
- Her kullanıcı için:
  - Kullanıcı adı / Ad-Soyad
  - User ID (kopyalanabilir)
  - Plan durumu
  - /start kullanım sayısı
  - İlk kayıt ve son görülme tarihi

---

## ⚙️ Kurulum

### 1. Admin Kullanıcı Tanımla
`.env` dosyasına admin user ID'lerini ekle:

```env
ADMIN_USER_IDS=123456789,987654321
```

**User ID'ni nasıl bulursun?**
- Bot'a `/hesabim` yaz
- Veya @userinfobot'a mesaj at

### 2. Bot'u Yeniden Başlat
```bash
python app.py
```

---

## 📱 Kullanım

### Admin Olarak:
```
/admin          → Özet paneli aç
/admin_detay    → Detaylı listeyi gör
```

### Örnek Çıktı:
```
👑 OKWIS AI - ADMIN PANELİ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 GENEL İSTATİSTİKLER
• Toplam Kullanıcı: 127
• Aktif Kullanıcı (Bugün): 34
• Bugünkü Analiz Sayısı: 89

💎 PLAN DAĞILIMI
• Free: 98 kullanıcı
• Pro: 24 kullanıcı
• Claude: 5 kullanıcı

🚀 START KOMUTU İSTATİSTİKLERİ
• Toplam /start: 456

👥 EN AKTİF KULLANICILAR (Top 15)
1. @mehmethanece | 45x | 2026-04-30
2. @kullanici2 | 32x | 2026-04-29
...
```

---

## 🔐 Güvenlik

- ✅ Sadece `.env`'de tanımlı adminler erişebilir
- ✅ Admin olmayan kullanıcılar "Bu komut yalnız admin için." mesajı alır
- ✅ Hassas bilgiler (şifre, token) saklanmaz
- ✅ Sadece public bilgiler (username, ad-soyad, ID) kaydedilir

---

## 📁 Yeni Dosya

`metrics/kullanici_kayitlari.json` - Kullanıcı bilgileri burada saklanır (otomatik oluşturulur)

---

## ✅ Test

1. Admin olarak bot'a `/start` yaz
2. `/admin` komutunu kullan
3. İstatistikleri gör
4. `/admin_detay` ile detaylı listeyi kontrol et

---

## 🎉 Hazır!

Admin panel kullanıma hazır. Detaylı bilgi için `ADMIN_PANEL_OZELLIGI.md` dosyasına bak.
