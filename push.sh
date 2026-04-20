#!/bin/bash
# ============================================================
# push.sh — Bilgisayarından çalıştır
# GitHub'a push et + Pi'yi otomatik güncelle
#
# Kullanım: bash push.sh
# ============================================================

PI_IP="192.168.1.144"
PI_USER="pi"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis — GitHub Push + Pi Güncelle"
echo "════════════════════════════════════════"
echo ""

# ── 1. GitHub'a push et ───────────────────────────────────
echo "[1/2] GitHub'a gönderiliyor..."
git add .
git status --short
git commit -m "güncelleme $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || echo "    (commit yok, zaten güncel)"
git push
echo "    OK"

# ── 2. Pi'de git pull + update.sh ────────────────────────
echo "[2/2] Pi güncelleniyor ($PI_IP)..."
ssh "$PI_USER@$PI_IP" "cd /opt/okwis && git pull && bash update.sh"

echo ""
echo "════════════════════════════════════════"
echo "  Tamamlandı!"
echo "════════════════════════════════════════"
echo ""
