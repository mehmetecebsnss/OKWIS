#!/bin/bash22
# ============================================================
# Okwis AI — İlk Kurulum Scripti (Raspberry Pi)
# Kullanım: bash deploy.sh
# ============================================================

set -e

PROJE_DIZIN="/opt/okwis"
SERVIS_ADI="okwis"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis AI — Raspberry Pi Kurulum"
echo "════════════════════════════════════════"
echo ""

# ── 1. Sistem bağımlılıkları ──────────────────────────────
echo "[1/6] Sistem paketleri kuruluyor..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git curl rsync

# ── 2. Proje klasörü ──────────────────────────────────────
echo "[2/6] Proje klasörü hazırlanıyor: $PROJE_DIZIN"
sudo mkdir -p "$PROJE_DIZIN"
sudo chown "$USER:$USER" "$PROJE_DIZIN"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rsync -a --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='metrics/' \
    "$SCRIPT_DIR/" "$PROJE_DIZIN/"

mkdir -p "$PROJE_DIZIN/metrics"
echo "    OK"

# ── 3. Python sanal ortam ─────────────────────────────────
echo "[3/6] Python sanal ortam kuruluyor..."
cd "$PROJE_DIZIN"

# Eski venv varsa sil, temiz başla
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q

# Python versiyonunu tespit et
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "    Python $PY_VER tespit edildi"

# requirements.txt'i kur — python-telegram-bot>=22.0 her Python versiyonuyla çalışır
pip install -q -r requirements.txt

deactivate
echo "    OK: venv hazır"

# ── 4. .env dosyası ───────────────────────────────────────
echo "[4/6] .env kontrolü..."
if [ ! -f "$PROJE_DIZIN/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env" ]; then
        cp "$SCRIPT_DIR/.env" "$PROJE_DIZIN/.env"
        echo "    OK: .env kopyalandı"
    else
        cat > "$PROJE_DIZIN/.env" << 'ENVEOF'
TELEGRAM_TOKEN=
GEMINI_API_KEY=
ADMIN_USER_IDS=
ANALIZ_GUNLUK_LIMIT=3
# CLAUDE_API_KEY=
# TAVILY_API_KEY=
# OPENWEATHER_API_KEY=
ENVEOF
        echo "    ⚠️  .env oluşturuldu — düzenle: nano $PROJE_DIZIN/.env"
    fi
else
    echo "    OK: .env zaten var"
fi

# ── 5. Systemd servis ─────────────────────────────────────
echo "[5/6] Systemd servis kuruluyor..."
sudo tee /etc/systemd/system/${SERVIS_ADI}.service > /dev/null << EOF
[Unit]
Description=Okwis AI Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJE_DIZIN
EnvironmentFile=$PROJE_DIZIN/.env
ExecStart=$PROJE_DIZIN/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVIS_ADI

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVIS_ADI"
echo "    OK: servis hazır"

# ── 6. Başlat ─────────────────────────────────────────────
echo "[6/6] Bot başlatılıyor..."

if grep -q "TELEGRAM_TOKEN=$" "$PROJE_DIZIN/.env" 2>/dev/null; then
    echo ""
    echo "  ⚠️  TELEGRAM_TOKEN boş!"
    echo "  Düzenle: nano $PROJE_DIZIN/.env"
    echo "  Sonra:   sudo systemctl start $SERVIS_ADI"
else
    sudo systemctl restart "$SERVIS_ADI"
    sleep 4
    STATUS=$(sudo systemctl is-active "$SERVIS_ADI")
    if [ "$STATUS" = "active" ]; then
        echo "    ✅ Bot çalışıyor!"
    else
        echo "    ❌ Başlamadı. Log: sudo journalctl -u $SERVIS_ADI -n 20 --no-pager"
    fi
fi

echo ""
echo "════════════════════════════════════════"
echo "  Kurulum tamamlandı!"
echo "  Log:       sudo journalctl -u $SERVIS_ADI -f"
echo "  Güncelle:  bash $PROJE_DIZIN/update.sh"
echo "════════════════════════════════════════"
echo ""
