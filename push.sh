#!/bin/bash
# ============================================================
# push.sh — Bilgisayarından çalıştır
# Kodu Raspberry Pi'ye gönder ve otomatik güncelle.
#
# Kullanım:
#   bash push.sh
#
# İlk kullanımdan önce PI_IP ve PI_USER'ı doldur.
# ============================================================

PI_IP="192.168.1.144"    # Pi'nin IP adresi
PI_USER="pi"              # <- Pi kullanıcı adı (genelde 'pi')
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis AI — Pi'ye Gönder & Güncelle"
echo "════════════════════════════════════════"
echo ""
echo "  Hedef: $PI_USER@$PI_IP"
echo ""

if [ "$PI_IP" = "192.168.1.XXX" ]; then
    echo "❌ PI_IP ayarlanmamış!"
    echo "   push.sh dosyasını aç, PI_IP değerini Pi'nin IP adresiyle değiştir."
    echo "   Pi'de IP öğrenmek için: hostname -I"
    exit 1
fi

# ── Dosyaları kopyala ─────────────────────────────────────
echo "[1/2] Dosyalar Pi'ye kopyalanıyor..."
rsync -av --progress \
    --exclude='.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='metrics/' \
    --exclude='push.sh' \
    "$LOCAL_DIR/" "$PI_USER@$PI_IP:/home/$PI_USER/okwis/"

echo "    OK"

# ── Pi'de update.sh çalıştır ──────────────────────────────
echo "[2/2] Pi'de güncelleme başlatılıyor..."
ssh "$PI_USER@$PI_IP" "cd /home/$PI_USER/okwis && bash update.sh"

echo ""
echo "════════════════════════════════════════"
echo "  Tamamlandı!"
echo "  Log: ssh $PI_USER@$PI_IP 'sudo journalctl -u okwis -f'"
echo "════════════════════════════════════════"
echo ""
