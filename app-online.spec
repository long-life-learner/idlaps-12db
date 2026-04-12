# =============================================================================
# app-online.spec — IDLAPS Checkpoint (Online Mode)
# Connects to time.idlaps.com for NTP sync & data upload.
#
# Windows : pyinstaller --clean --noconfirm app-online.spec  → dist/IDLAPS-Online.exe
# macOS   : pyinstaller --clean --noconfirm app-online.spec  → dist/IDLAPS-Online.app
# =============================================================================

import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS   = sys.platform.startswith("darwin")

# ── Data files ────────────────────────────────────────────────────────────────
added_datas = [
    ("templates",       "templates"),
    ("static",          "static"),
    (".env.production",  "."),
]

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden = [
    "sqlite3",
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtNetwork",
    "flask", "flask_sqlalchemy",
    "sqlalchemy", "sqlalchemy.dialects.sqlite",
    "jinja2", "requests", "serial", "usb", "dotenv",
]
hidden += collect_submodules("PySide6")
hidden += collect_submodules("flask")
hidden += collect_submodules("sqlalchemy")

# ── Binaries: bundle libusb so pyusb works inside .app on macOS ───────────────
def _find_libusb():
    for p in [
        "/opt/homebrew/lib/libusb-1.0.dylib",
        "/opt/homebrew/lib/libusb-1.0.0.dylib",
        "/usr/local/lib/libusb-1.0.dylib",
        "/usr/local/lib/libusb-1.0.0.dylib",
    ]:
        if os.path.exists(p):
            return (p, ".")
    return None

_lib = _find_libusb()
added_binaries = [_lib] if _lib else []

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=added_binaries,
    datas=added_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "PIL", "cv2"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Platform output ───────────────────────────────────────────────────────────
if IS_MACOS:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="IDLAPS-Online",
        debug=False, bootloader_ignore_signals=False,
        strip=False, upx=False, console=False, target_arch=None,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False, name="IDLAPS-Online",
    )
    app = BUNDLE(
        coll,
        name="IDLAPS-Online.app",
        bundle_identifier="com.idlaps.checkpoint.online",
        info_plist={
            "CFBundleDisplayName": "IDLAPS Online",
            "CFBundleShortVersionString": os.environ.get("VERSION", "1.0.0"),
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
        },
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name="IDLAPS-Online",
        debug=False, bootloader_ignore_signals=False,
        strip=False, upx=True, upx_exclude=[],
        runtime_tmpdir=None, console=False,
        disable_windowed_traceback=False,
        target_arch=None, codesign_identity=None, entitlements_file=None,
    )
