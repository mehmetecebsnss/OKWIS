#!/bin/bash
# ============================================================
# Okwis AI — Metrics Sorunu Çözümü
# Kullanım: bash fix_metrics.sh
# ============================================================

echo ""
echo "════════════════════════════════════════"
echo "  Okwis AI — Metrics Sorunu Çözümü"
echo "════════════════════════════════════════"
echo ""

cd /opt/okwis

# 1. Metrics dosyalarını Git'ten kaldır
echo "[1/3] Metrics dosyaları Git'ten kaldırılıyor..."
git rm -r --cached metrics/ 2>/dev/null || true
echo "    ✅ Tamamlandı"

# 2. Yerel değişiklikleri stash et
echo "[2/3] Yerel değişiklikler saklanıyor..."
git stash push -m "Metrics files backup $(date +%Y%m%d_%H%M%S)"
echo "    ✅ Tamamlandı"

# 3. GitHub'dan güncellemeyi çek
echo "[3/3] GitHub'dan güncelleme çekiliyor..."
git pull origin main
echo "    ✅ Tamamlandı"

echo ""
echo "════════════════════════════════════════"
echo "  ✅ Sorun çözüldü!"
echo "════════════════════════════════════════"
echo ""
echo "Şimdi update.sh'yi çalıştırabilirsin:"
echo "  bash update.sh"
echo ""
