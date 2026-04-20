#!/bin/bash
# ============================================================
# Okwis AI — Güncelleme Scripti (Raspberry Pi)
# Kullanım: bash update.sh
#
# GitHub'dan güncelleme için:
#   cd /opt/okwis && git pull && bash update.sh
# ============================================================

set -e

PROJE_DIZIN="/opt/okwis"
SERVIS_ADI="okwis"
GITHUB_REPO="https://github.com/mehmetecebsnss/OKWIS.git"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis AI — Güncelleme"
echo "════════════════════════════════════════"
echo ""

if [ ! -d "$PROJE_DIZIN" ]; then
    echo "❌ $PROJE_DIZIN bulunamadı. Önce deploy.sh çalıştır."
    exit 1
fi

# ── 1. Bot durdur ─────────────────────────────────────────
echo "[1/4] Bot durduruluyor..."
sudo systemctl stop "$SERVIS_ADI" 2>/dev/null || true
echo "    OK"

# ── 2. Kodu güncelle ──────────────────────────────────────
echo "[2/4] Kod güncelleniyor..."
cd "$PROJE_DIZIN"

# Git repo varsa pull yap, yoksa rsync ile güncelle
if [ -d "$PROJE_DIZIN/.git" ]; then
    echo "    GitHub'dan çekiliyor..."
    git pull origin main
else
    # push.sh ile gönderilmişse rsync ile güncelle
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    rsync -a --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='.git' --exclude='metrics/' \
        "$SCRIPT_DIR/" "$PROJE_DIZIN/"
fi
echo "    OK"

# ── 3. Bağımlılıkları güncelle ────────────────────────────
echo "[3/4] Python paketleri güncelleniyor..."
source venv/bin/activate
pip install -q -r requirements.txt
deactivate
echo "    OK"

# ── 4. Bot başlat ─────────────────────────────────────────
echo "[4/4] Bot yeniden başlatılıyor..."
sudo systemctl start "$SERVIS_ADI"
sleep 4

STATUS=$(sudo systemctl is-active "$SERVIS_ADI")
if [ "$STATUS" = "active" ]; then
    echo "    ✅ Bot çalışıyor!"
else
    echo "    ❌ Bot başlamadı."
    sudo journalctl -u "$SERVIS_ADI" -n 10 --no-pager
    exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo "  Güncelleme tamamlandı!"
echo "  Log: sudo journalctl -u $SERVIS_ADI -f"
echo "════════════════════════════════════════"
echo ""
