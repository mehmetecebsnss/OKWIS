#!/bin/bash
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
echo "  Versiyon: 2026-04-20 (Güvenlik Güncellemesi)"
echo "════════════════════════════════════════"
echo ""

# ── 1. Sistem bağımlılıkları ──────────────────────────────
echo "[1/7] Sistem paketleri kuruluyor..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git curl rsync

# Python versiyonunu kontrol et
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "    Python $PY_VER tespit edildi"

if [[ "$PY_VER" < "3.11" ]]; then
    echo "    ⚠️  Python 3.11+ önerilir (mevcut: $PY_VER)"
    echo "    Devam ediliyor ama bazı özellikler sınırlı olabilir..."
fi

# ── 2. Proje klasörü ──────────────────────────────────────
echo "[2/7] Proje klasörü hazırlanıyor: $PROJE_DIZIN"
sudo mkdir -p "$PROJE_DIZIN"
sudo chown "$USER:$USER" "$PROJE_DIZIN"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rsync -a --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='metrics/' \
    "$SCRIPT_DIR/" "$PROJE_DIZIN/"

mkdir -p "$PROJE_DIZIN/metrics"
echo "    OK"

# ── 3. Python sanal ortam ─────────────────────────────────
echo "[3/7] Python sanal ortam kuruluyor..."
cd "$PROJE_DIZIN"

# Eski venv varsa sil, temiz başla
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q

# requirements.txt'i kur — python-telegram-bot[job-queue]>=22.0 her Python versiyonuyla çalışır
echo "    Bağımlılıklar kuruluyor (bu birkaç dakika sürebilir)..."
pip install -q -r requirements.txt

deactivate
echo "    OK: venv hazır"

# ── 4. .env dosyası ───────────────────────────────────────
echo "[4/7] .env kontrolü..."
if [ ! -f "$PROJE_DIZIN/.env" ]; then
    if [ -f "$SCRIPT_DIR/.env" ]; then
        # Kaynak .env'yi kontrol et - placeholder değerler varsa uyar
        if grep -q "your_.*_here" "$SCRIPT_DIR/.env" 2>/dev/null; then
            echo "    ⚠️  Kaynak .env dosyası placeholder değerler içeriyor!"
            echo "    .env.example'dan yeni bir .env oluşturuluyor..."
            cp "$SCRIPT_DIR/.env.example" "$PROJE_DIZIN/.env"
            echo "    ⚠️  ZORUNLU: Gerçek API anahtarlarınızı girin!"
            echo "    Düzenle: nano $PROJE_DIZIN/.env"
        else
            cp "$SCRIPT_DIR/.env" "$PROJE_DIZIN/.env"
            echo "    OK: .env kopyalandı"
        fi
    else
        # .env.example varsa onu kullan
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$PROJE_DIZIN/.env"
            echo "    ⚠️  .env.example'dan oluşturuldu"
        else
            # Hiçbiri yoksa minimal .env oluştur
            cat > "$PROJE_DIZIN/.env" << 'ENVEOF'
# ⚠️ UYARI: Gerçek API anahtarlarınızı buraya yazın!
AI_PROVIDER=gemini
TELEGRAM_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
ADMIN_USER_IDS=your_telegram_user_id_here
ANALIZ_GUNLUK_LIMIT=3
ENVEOF
            echo "    ⚠️  Minimal .env oluşturuldu"
        fi
        echo "    ⚠️  ZORUNLU: Gerçek API anahtarlarınızı girin!"
        echo "    Düzenle: nano $PROJE_DIZIN/.env"
    fi
else
    echo "    OK: .env zaten var"
    # Mevcut .env'yi kontrol et
    if grep -q "your_.*_here" "$PROJE_DIZIN/.env" 2>/dev/null; then
        echo "    ⚠️  UYARI: .env dosyası placeholder değerler içeriyor!"
        echo "    Gerçek API anahtarlarınızı girin: nano $PROJE_DIZIN/.env"
    fi
fi

# ── 5. Systemd servis ─────────────────────────────────────
echo "[5/7] Systemd servis kuruluyor..."
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

# ── 6. Environment Variables Kontrolü ─────────────────────
echo "[6/7] Environment variables kontrolü..."
ENV_OK=true

# Gerekli anahtarları kontrol et
for KEY in TELEGRAM_TOKEN GEMINI_API_KEY OPENWEATHER_API_KEY TAVILY_API_KEY; do
    VALUE=$(grep "^${KEY}=" "$PROJE_DIZIN/.env" 2>/dev/null | cut -d'=' -f2-)
    if [ -z "$VALUE" ] || [[ "$VALUE" == "your_"* ]]; then
        echo "    ❌ $KEY eksik veya geçersiz"
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

echo "    ✅ Tüm gerekli environment variables mevcut"

# ── 7. Başlat ─────────────────────────────────────────────
echo "[7/7] Bot başlatılıyor..."

sudo systemctl restart "$SERVIS_ADI"
sleep 4
STATUS=$(sudo systemctl is-active "$SERVIS_ADI")
if [ "$STATUS" = "active" ]; then
    echo "    ✅ Bot çalışıyor!"
else
    echo "    ❌ Başlamadı. Log: sudo journalctl -u $SERVIS_ADI -n 20 --no-pager"
    exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo "  ✅ Kurulum tamamlandı!"
echo "════════════════════════════════════════"
echo "  Log:       sudo journalctl -u $SERVIS_ADI -f"
echo "  Durum:     sudo systemctl status $SERVIS_ADI"
echo "  Güncelle:  bash $PROJE_DIZIN/update.sh"
echo "  Durdur:    sudo systemctl stop $SERVIS_ADI"
echo "  Başlat:    sudo systemctl start $SERVIS_ADI"
echo "════════════════════════════════════════"
echo ""
