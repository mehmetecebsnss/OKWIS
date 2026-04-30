# Raspberry Pi Güncelleme Sorunu Çözümü

## 🔴 Sorun

```
error: Your local changes to the following files would be overwritten by merge:
    metrics/analiz_olaylari.jsonl
    metrics/kullanim_limitleri.json
    metrics/tahmin_kayitlari.jsonl
Please commit your changes or stash them before you merge.
Aborting
```

## 🔧 Hızlı Çözüm

Raspberry Pi'de şu komutları çalıştır:

```bash
# 1. Okwis klasörüne git
cd /opt/okwis

# 2. Çözüm scriptini çalıştır
bash fix_metrics.sh

# 3. Normal güncellemeyi yap
bash update.sh
```

## 📝 Manuel Çözüm

Eğer script çalışmazsa manuel olarak:

```bash
cd /opt/okwis

# 1. Metrics dosyalarını Git'ten kaldır
git rm -r --cached metrics/

# 2. Yerel değişiklikleri sakla
git stash

# 3. GitHub'dan güncellemeyi çek
git pull origin main

# 4. Bot'u başlat
sudo systemctl start okwis
```

## 🎯 Neden Oluyor?

`metrics/` klasörü kullanıcı verisi içerir ve `.gitignore`'da olmasına rağmen, daha önce Git'e eklenmiş olabilir. Bu yüzden güncelleme sırasında çakışma oluyor.

## ✅ Kalıcı Çözüm

`update.sh` scripti artık bu sorunu otomatik çözer. Gelecek güncellemelerde sorun yaşanmayacak.

## 📊 Kontrol

Bot çalışıyor mu kontrol et:

```bash
# Durum kontrolü
sudo systemctl status okwis

# Log kontrolü
sudo journalctl -u okwis -f
```

## 🆘 Hala Sorun Varsa

1. Bot'u durdur:
```bash
sudo systemctl stop okwis
```

2. Tüm değişiklikleri sıfırla:
```bash
cd /opt/okwis
git reset --hard origin/main
```

3. Bot'u başlat:
```bash
sudo systemctl start okwis
```

**Not:** Bu işlem metrics verilerini sıfırlar!
