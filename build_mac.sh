#!/usr/bin/env bash
# =================================================================
# IDLAPS Checkpoint — Build Script for macOS
# Usage:
#   chmod +x build_mac.sh
#   ./build_mac.sh online     → Build IDLAPS-Online.app
#   ./build_mac.sh offline    → Build IDLAPS-Offline.app
#   ./build_mac.sh all        → Build both (default)
# =================================================================

set -e

MODE="${1:-all}"

echo "=================================================="
echo " IDLAPS Checkpoint — macOS Build Script"
echo " Mode: $MODE"
echo "=================================================="

# Validasi Python & pyinstaller tersedia
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan. Install dulu via: brew install python3"
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

# Bersihkan cache build lama
echo "[INFO] Membersihkan cache build lama..."
rm -rf build/
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

build_online() {
    echo ""
    echo "--- [1/2] Building: IDLAPS-Online.app ---"
    python3 -m PyInstaller --clean --noconfirm app-online.spec
    echo "[OK] IDLAPS-Online.app selesai → dist/IDLAPS-Online.app"
}

build_offline() {
    echo ""
    echo "--- [2/2] Building: IDLAPS-Offline.app ---"
    python3 -m PyInstaller --clean --noconfirm app-offline.spec
    echo "[OK] IDLAPS-Offline.app selesai → dist/IDLAPS-Offline.app"
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
echo " - dist/IDLAPS-Online.app"
echo " - dist/IDLAPS-Offline.app"
echo "=================================================="
