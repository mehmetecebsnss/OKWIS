#!/bin/bash
# ============================================================
# Okwis AI — Güncelleme Scripti (Raspberry Pi)
# Kullanım: bash update.sh
# Yeni kod dosyalarını kopyala, bağımlılıkları güncelle, botu yeniden başlat.
# ============================================================

set -e

PROJE_DIZIN="/opt/okwis"
SERVIS_ADI="okwis"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis AI — Güncelleme"
echo "════════════════════════════════════════"
echo ""

# Scriptin çalıştığı dizin = yeni kod
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$PROJE_DIZIN" ]; then
    echo "❌ $PROJE_DIZIN bulunamadı. Önce deploy.sh çalıştır."
    exit 1
fi

# ── 1. Bot durdur ─────────────────────────────────────────
echo "[1/4] Bot durduruluyor..."
sudo systemctl stop "$SERVIS_ADI" 2>/dev/null || true
echo "    OK"

# ── 2. Kodu güncelle ──────────────────────────────────────
echo "[2/4] Dosyalar güncelleniyor..."
rsync -av --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='metrics/' \
    "$SCRIPT_DIR/" "$PROJE_DIZIN/"
echo "    OK"

# ── 3. Bağımlılıkları güncelle ────────────────────────────
echo "[3/4] Python paketleri güncelleniyor..."
cd "$PROJE_DIZIN"
source venv/bin/activate
pip install -r requirements.txt -q
deactivate
echo "    OK"

# ── 4. Bot başlat ─────────────────────────────────────────
echo "[4/4] Bot yeniden başlatılıyor..."
sudo systemctl start "$SERVIS_ADI"
sleep 3

STATUS=$(sudo systemctl is-active "$SERVIS_ADI")
if [ "$STATUS" = "active" ]; then
    echo "    ✅ Bot çalışıyor!"
else
    echo "    ❌ Bot başlamadı."
    echo "    Log için: sudo journalctl -u $SERVIS_ADI -n 30"
    exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo "  Güncelleme tamamlandı!"
echo "  Log: sudo journalctl -u $SERVIS_ADI -f"
echo "════════════════════════════════════════"
echo ""
