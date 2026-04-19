# Okwis AI — Raspberry Pi Kurulum & Güncelleme

## İlk Kurulum

### 1. Dosyaları Raspberry Pi'ye kopyala

Bilgisayarından Raspberry Pi'ye kopyala (aynı ağdaysanız):

```bash
# Raspberry Pi IP adresini bul (Pi'de çalıştır)
hostname -I

# Bilgisayarından kopyala (Pi'nin IP'sini yaz)
scp -r /proje/klasoru pi@192.168.1.XXX:/home/pi/okwis
```

Veya USB bellek ile kopyala.

### 2. Kurulum scriptini çalıştır

Raspberry Pi'de terminal aç:

```bash
cd /home/pi/okwis
bash deploy.sh
```

Script otomatik olarak:
- Python ve bağımlılıkları kurar
- `/opt/okwis` klasörüne kopyalar
- Systemd servisi oluşturur (boot'ta otomatik başlar)
- Botu başlatır

### 3. .env dosyasını doldur

Eğer `.env` yoksa script oluşturur, doldur:

```bash
nano /opt/okwis/.env
```

Zorunlu değerler:
```
TELEGRAM_TOKEN=bot_tokenin
GEMINI_API_KEY=gemini_anahtarin
ADMIN_USER_IDS=telegram_kullanici_idin
```

Sonra başlat:
```bash
sudo systemctl start okwis
```

---

## Güncelleme (Yeni Kod Gelince)

Yeni kodları bilgisayarından Pi'ye kopyala, sonra:

```bash
cd /home/pi/okwis
bash update.sh
```

Tek komutla: durdur → güncelle → yeniden başlat.

---

## Yararlı Komutlar

```bash
# Bot durumu
sudo systemctl status okwis

# Canlı log izle
sudo journalctl -u okwis -f

# Son 50 log satırı
sudo journalctl -u okwis -n 50

# Botu durdur
sudo systemctl stop okwis

# Botu başlat
sudo systemctl start okwis

# Botu yeniden başlat
sudo systemctl restart okwis

# Otomatik başlatmayı kapat
sudo systemctl disable okwis
```

---

## Kopyalama Kısayolu

Bilgisayarından Pi'ye hızlı kopyalama için `push.sh` oluşturabilirsin:

```bash
#!/bin/bash
# push.sh — bilgisayarında çalıştır
PI_IP="192.168.1.XXX"   # Pi'nin IP adresi
PI_USER="pi"             # Pi kullanıcı adı
LOCAL_DIR="."            # proje klasörün

rsync -av --exclude='.env' --exclude='__pycache__' \
    --exclude='.git' --exclude='metrics/' \
    "$LOCAL_DIR/" "$PI_USER@$PI_IP:/home/pi/okwis/"

# Sonra Pi'de update.sh çalıştır
ssh "$PI_USER@$PI_IP" "cd /home/pi/okwis && bash update.sh"
```

Kullanım: `bash push.sh` — tek komutla gönder ve güncelle.
