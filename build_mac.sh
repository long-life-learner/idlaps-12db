#!/usr/bin/env bash
# =================================================================
# IDLAPS Checkpoint — Build Script for macOS
# Usage:
#   chmod +x build_mac.sh
#   ./build_mac.sh online     → Build IDLAPS-Online.app
#   ./build_mac.sh offline    → Build IDLAPS-Offline.app
#   ./build_mac.sh all        → Build both (default)
#
# Fix: Ad-hoc codesign + xattr -cr so macOS doesn't block the app
# =================================================================

set -e

MODE="${1:-all}"

echo "=================================================="
echo " IDLAPS Checkpoint — macOS Build Script"
echo " Mode: $MODE"
echo "=================================================="

# Validasi Python & pyinstaller tersedia
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan."
    exit 1
fi

if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "[INFO] PyInstaller belum terinstall. Menginstall..."
    pip3 install pyinstaller
fi

# Pastikan .env.production tersedia
if [ ! -f ".env.production" ]; then
    echo "[WARNING] .env.production tidak ditemukan."
    echo "          Menyalin dari .env.example..."
    cp .env.example .env.production
fi

# Bersihkan cache build lama (termasuk dist agar tidak ada NotADirectoryError)
echo "[INFO] Membersihkan cache build lama..."
rm -rf build/
rm -rf dist/IDLAPS-Online dist/IDLAPS-Online.app 2>/dev/null || true
rm -rf dist/IDLAPS-Offline dist/IDLAPS-Offline.app 2>/dev/null || true
find . -maxdepth 2 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ─── Helper: sign & strip quarantine ──────────────────────────────────────────
# codesign --deep -s - : ad-hoc signature (tidak perlu Apple Developer Account)
# xattr -cr            : hapus com.apple.quarantine agar Gatekeeper tidak blokir
sign_and_clear_quarantine() {
    local APP="$1"
    if [ -d "$APP" ]; then
        echo "[INFO] Signing (ad-hoc): $APP"
        codesign --force --deep --sign - "$APP" 2>&1 || echo "[WARN] codesign gagal (lanjut saja)"
        echo "[INFO] Clearing quarantine: $APP"
        xattr -cr "$APP" 2>/dev/null || true
        echo "[OK] App siap dibuka tanpa Gatekeeper block."
    fi
}

# ─── Helper: create DMG ───────────────────────────────────────────────────────
# hdiutil create: standar macOS disk image
create_dmg() {
    local APP_PATH="$1"
    local DMG_NAME="$2"
    local VOL_NAME="$3"

    echo "[INFO] Creating DMG: $DMG_NAME"

    # Create temporary directory for DMG content
    local TMP_DMG="dist/tmp_dmg"
    rm -rf "$TMP_DMG"
    mkdir -p "$TMP_DMG"

    # Copy the app to the temporary directory
    cp -R "$APP_PATH" "$TMP_DMG/"

    # Create link to Applications
    ln -s /Applications "$TMP_DMG/Applications"

    # Create the DMG
    hdiutil create -volname "$VOL_NAME" -srcfolder "$TMP_DMG" -ov -format UDZO "dist/$DMG_NAME"

    # Clean up
    rm -rf "$TMP_DMG"

    echo "[OK] DMG created: dist/$DMG_NAME"
}

build_online() {
    echo ""
    echo "--- [1/2] Building: IDLAPS-Online.app ---"
    python3 -m PyInstaller --clean --noconfirm app-online.spec
    sign_and_clear_quarantine "dist/IDLAPS-Online.app"
    create_dmg "dist/IDLAPS-Online.app" "IDLAPS-Online.dmg" "IDLAPS Online"
    echo "[OK] IDLAPS-Online selesai → dist/IDLAPS-Online.dmg"
}

build_offline() {
    echo ""
    echo "--- [2/2] Building: IDLAPS-Offline.app ---"
    python3 -m PyInstaller --clean --noconfirm app-offline.spec
    sign_and_clear_quarantine "dist/IDLAPS-Offline.app"
    create_dmg "dist/IDLAPS-Offline.app" "IDLAPS-Offline.dmg" "IDLAPS Offline"
    echo "[OK] IDLAPS-Offline selesai → dist/IDLAPS-Offline.dmg"
}

case "$MODE" in
    online)  build_online ;;
    offline) build_offline ;;
    all)
        build_online
        build_offline
        ;;
    *)
        echo "[ERROR] Mode tidak dikenal: $MODE. Gunakan: online | offline | all"
        exit 1
        ;;
esac

echo ""
echo "=================================================="
echo " Build Selesai! Cek folder dist/"
[ "$MODE" = "online" ] || [ "$MODE" = "all" ]  && echo " - dist/IDLAPS-Online.dmg"
[ "$MODE" = "offline" ] || [ "$MODE" = "all" ] && echo " - dist/IDLAPS-Offline.dmg"
echo ""
echo " Cara buka jika masih terblokir Gatekeeper:"
echo "   Kanan-klik .app → Open → Open"
echo "   atau: System Preferences → Privacy & Security → Open Anyway"
echo "=================================================="
