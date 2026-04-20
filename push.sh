#!/bin/bash
# ============================================================
# push.sh — Bilgisayarından çalıştır
# GitHub'a push et + Pi'yi otomatik güncelle
#
# Kullanım: bash push.sh ["commit mesajı"]
# ============================================================

PI_IP="192.168.1.144"
PI_USER="pi"

# Commit mesajı parametreden al, yoksa otomatik oluştur
COMMIT_MSG="${1:-güncelleme $(date '+%Y-%m-%d %H:%M')}"

echo ""
echo "════════════════════════════════════════"
echo "  Okwis — GitHub Push + Pi Güncelle"
echo "  Versiyon: 2026-04-20 (Güvenlik Güncellemesi)"
echo "════════════════════════════════════════"
echo ""

# ── 0. Güvenlik Kontrolü ──────────────────────────────────
echo "[0/3] Güvenlik kontrolü..."

# .env dosyasının staged olup olmadığını kontrol et
if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "    ❌ HATA: .env dosyası commit edilmeye çalışılıyor!"
    echo "    Bu dosya hassas API anahtarları içeriyor."
    echo ""
    echo "    Düzeltme:"
    echo "    git reset HEAD .env"
    echo "    git rm --cached .env  # (eğer daha önce commit edildiyse)"
    echo ""
    exit 1
fi

# .env dosyasının Git'te olup olmadığını kontrol et
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    echo "    ⚠️  UYARI: .env dosyası Git'te tracked durumda!"
    echo "    Bu güvenlik riski oluşturur."
    echo ""
    echo "    Düzeltme:"
    echo "    git rm --cached .env"
    echo "    # Sonra Git geçmişinden temizlemek için debug-operasyonu-1.md'ye bakın"
    echo ""
    read -p "    Devam etmek istiyor musunuz? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "    ✅ Güvenlik kontrolü OK"

# ── 1. GitHub'a push et ───────────────────────────────────
echo "[1/3] GitHub'a gönderiliyor..."
git add .
git status --short

# Değişiklik var mı kontrol et
if git diff --cached --quiet; then
    echo "    (değişiklik yok, zaten güncel)"
else
    git commit -m "$COMMIT_MSG"
    echo "    Commit: $COMMIT_MSG"
fi

git push
echo "    ✅ GitHub push tamamlandı"

# ── 2. Pi'de git pull + update.sh ────────────────────────
echo "[2/3] Pi güncelleniyor ($PI_IP)..."

# Pi'ye erişilebilir mi kontrol et
if ! ping -c 1 -W 2 "$PI_IP" >/dev/null 2>&1; then
    echo "    ⚠️  Pi'ye erişilemiyor ($PI_IP)"
    echo "    IP adresini kontrol edin veya Pi'nin açık olduğundan emin olun"
    exit 1
fi

# SSH ile güncelleme
if ssh "$PI_USER@$PI_IP" "cd /opt/okwis && git pull && bash update.sh"; then
    echo "    ✅ Pi güncelleme tamamlandı"
else
    echo "    ❌ Pi güncelleme başarısız"
    echo "    Manuel kontrol: ssh $PI_USER@$PI_IP"
    exit 1
fi

# ── 3. Özet ───────────────────────────────────────────────
echo "[3/3] Özet..."
echo "    ✅ GitHub: push edildi"
echo "    ✅ Pi: güncellendi ve çalışıyor"

echo ""
echo "════════════════════════════════════════"
echo "  ✅ Tamamlandı!"
echo "════════════════════════════════════════"
echo "  Pi Log:    ssh $PI_USER@$PI_IP 'sudo journalctl -u okwis -f'"
echo "  Pi Durum:  ssh $PI_USER@$PI_IP 'sudo systemctl status okwis'"
echo "════════════════════════════════════════"
echo ""
