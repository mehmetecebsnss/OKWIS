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
echo "  Versiyon: 2026-04-20 (Güvenlik Güncellemesi)"
echo "════════════════════════════════════════"
echo ""

if [ ! -d "$PROJE_DIZIN" ]; then
    echo "❌ $PROJE_DIZIN bulunamadı. Önce deploy.sh çalıştır."
    exit 1
fi

# ── 1. Bot durdur ─────────────────────────────────────────
echo "[1/5] Bot durduruluyor..."
sudo systemctl stop "$SERVIS_ADI" 2>/dev/null || true
echo "    OK"

# ── 2. Kodu güncelle ──────────────────────────────────────
echo "[2/5] Kod güncelleniyor..."
cd "$PROJE_DIZIN"

# Git repo varsa pull yap, yoksa rsync ile güncelle
if [ -d "$PROJE_DIZIN/.git" ]; then
    echo "    GitHub'dan çekiliyor..."
    
    # Metrics dosyalarını Git'ten kaldır (eğer track ediliyorsa)
    git rm -r --cached metrics/ 2>/dev/null || true
    
    # Yerel değişiklikleri stash et
    if ! git diff-index --quiet HEAD --; then
        echo "    Yerel değişiklikler saklanıyor..."
        git stash push -m "Auto-stash before update $(date +%Y%m%d_%H%M%S)"
    fi
    
    # GitHub'dan güncellemeyi çek
    git pull origin main
    
    echo "    ✅ Kod güncellendi"
else
    # push.sh ile gönderilmişse rsync ile güncelle
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    rsync -a --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='.git' --exclude='metrics/' \
        "$SCRIPT_DIR/" "$PROJE_DIZIN/"
    echo "    ✅ Kod güncellendi"
fi

# ── 3. Bağımlılıkları güncelle ────────────────────────────
echo "[3/5] Python paketleri güncelleniyor..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -q -r requirements.txt
deactivate
echo "    OK"

# ── 4. Environment Variables Kontrolü ─────────────────────
echo "[4/5] Environment variables kontrolü..."
ENV_OK=true

# .env dosyası var mı?
if [ ! -f "$PROJE_DIZIN/.env" ]; then
    echo "    ❌ .env dosyası bulunamadı!"
    if [ -f "$PROJE_DIZIN/.env.example" ]; then
        echo "    .env.example'dan oluşturuluyor..."
        cp "$PROJE_DIZIN/.env.example" "$PROJE_DIZIN/.env"
        echo "    ⚠️  ZORUNLU: Gerçek API anahtarlarınızı girin!"
        echo "    Düzenle: nano $PROJE_DIZIN/.env"
        exit 1
    else
        echo "    ❌ .env.example de bulunamadı!"
        exit 1
    fi
fi

# Gerekli anahtarları kontrol et
for KEY in TELEGRAM_TOKEN GEMINI_API_KEY OPENWEATHER_API_KEY TAVILY_API_KEY; do
    VALUE=$(grep "^${KEY}=" "$PROJE_DIZIN/.env" 2>/dev/null | cut -d'=' -f2-)
    if [ -z "$VALUE" ] || [[ "$VALUE" == "your_"* ]]; then
        echo "    ⚠️  $KEY eksik veya geçersiz"
        ENV_OK=false
    fi
done

if [ "$ENV_OK" = false ]; then
    echo ""
    echo "  ⚠️  Bazı API anahtarları eksik veya geçersiz!"
    echo "  Düzenle: nano $PROJE_DIZIN/.env"
    echo "  Sonra:   sudo systemctl start $SERVIS_ADI"
    echo ""
    exit 1
fi

echo "    ✅ Environment variables OK"

# ── 5. Bot başlat ─────────────────────────────────────────
echo "[5/5] Bot yeniden başlatılıyor..."
sudo systemctl start "$SERVIS_ADI"
sleep 4

STATUS=$(sudo systemctl is-active "$SERVIS_ADI")
if [ "$STATUS" = "active" ]; then
    echo "    ✅ Bot çalışıyor!"
else
    echo "    ❌ Bot başlamadı."
    echo ""
    echo "Son 20 log satırı:"
    sudo journalctl -u "$SERVIS_ADI" -n 20 --no-pager
    exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo "  ✅ Güncelleme tamamlandı!"
echo "════════════════════════════════════════"
echo "  Log:    sudo journalctl -u $SERVIS_ADI -f"
echo "  Durum:  sudo systemctl status $SERVIS_ADI"
echo "════════════════════════════════════════"
echo ""
