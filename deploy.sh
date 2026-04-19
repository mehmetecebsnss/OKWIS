#!/bin/bash
# ============================================================
# Okwis AI — İlk Kurulum Scripti (Raspberry Pi)
# Kullanım: bash deploy.sh
# ============================================================

set -e  # hata olursa dur

PROJE_ADI="okwis"
PROJE_DIZIN="/opt/okwis"
SERVIS_ADI="okwis"
PYTHON="python3"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis AI — Raspberry Pi Kurulum"
echo "════════════════════════════════════════"
echo ""

# ── 1. Sistem bağımlılıkları ──────────────────────────────
echo "[1/6] Sistem paketleri güncelleniyor..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git curl

# ── 2. Proje klasörü ──────────────────────────────────────
echo "[2/6] Proje klasörü hazırlanıyor: $PROJE_DIZIN"
sudo mkdir -p "$PROJE_DIZIN"
sudo chown "$USER:$USER" "$PROJE_DIZIN"

# Mevcut dosyaları kopyala
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "    Kaynak: $SCRIPT_DIR"
echo "    Hedef:  $PROJE_DIZIN"

rsync -av --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='metrics/' \
    "$SCRIPT_DIR/" "$PROJE_DIZIN/"

# metrics klasörünü oluştur (silme, varsa koru)
mkdir -p "$PROJE_DIZIN/metrics"

# ── 3. Python sanal ortam ─────────────────────────────────
echo "[3/6] Python sanal ortam kuruluyor..."
cd "$PROJE_DIZIN"
$PYTHON -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
deactivate
echo "    OK: venv hazır"

# ── 4. .env dosyası ───────────────────────────────────────
echo "[4/6] .env kontrolü..."
if [ ! -f "$PROJE_DIZIN/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env" ]; then
        cp "$SCRIPT_DIR/.env" "$PROJE_DIZIN/.env"
        echo "    OK: .env kopyalandı"
    else
        echo ""
        echo "  ⚠️  .env bulunamadı!"
        echo "  Şimdi oluşturuyorum — değerleri kendin gir:"
        echo ""
        cat > "$PROJE_DIZIN/.env" << 'ENVEOF'
TELEGRAM_TOKEN=
GEMINI_API_KEY=
ADMIN_USER_IDS=
ANALIZ_GUNLUK_LIMIT=3
# İsteğe bağlı:
# CLAUDE_API_KEY=
# TAVILY_API_KEY=
# OPENWEATHER_API_KEY=
# DEEPSEEK_API_KEY=
ENVEOF
        echo "  📝 $PROJE_DIZIN/.env oluşturuldu."
        echo "  ➡️  Düzenle: nano $PROJE_DIZIN/.env"
        echo "  ➡️  Sonra servisi başlat: sudo systemctl start $SERVIS_ADI"
        echo ""
    fi
else
    echo "    OK: .env zaten var, dokunulmadı"
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
echo "    OK: servis kaydedildi ve otomatik başlatma açıldı"

# ── 6. Başlat ─────────────────────────────────────────────
echo "[6/6] Bot başlatılıyor..."

# .env doluysa başlat, boşsa uyar
if grep -q "TELEGRAM_TOKEN=$" "$PROJE_DIZIN/.env" 2>/dev/null; then
    echo ""
    echo "  ⚠️  .env içinde TELEGRAM_TOKEN boş!"
    echo "  Düzenle: nano $PROJE_DIZIN/.env"
    echo "  Sonra:   sudo systemctl start $SERVIS_ADI"
else
    sudo systemctl start "$SERVIS_ADI"
    sleep 3
    STATUS=$(sudo systemctl is-active "$SERVIS_ADI")
    if [ "$STATUS" = "active" ]; then
        echo "    ✅ Bot çalışıyor!"
    else
        echo "    ❌ Bot başlamadı. Log: sudo journalctl -u $SERVIS_ADI -n 30"
    fi
fi

echo ""
echo "════════════════════════════════════════"
echo "  Kurulum tamamlandı!"
echo ""
echo "  Komutlar:"
echo "  Durum:     sudo systemctl status $SERVIS_ADI"
echo "  Log:       sudo journalctl -u $SERVIS_ADI -f"
echo "  Durdur:    sudo systemctl stop $SERVIS_ADI"
echo "  Güncelle:  bash $PROJE_DIZIN/update.sh"
echo "════════════════════════════════════════"
echo ""
