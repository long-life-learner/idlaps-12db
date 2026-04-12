# =============================================================================
# app-offline.spec — IDLAPS Checkpoint (Offline Mode)
# Runs a local Flask web server (localhost:5001). No internet required.
#
# Windows : pyinstaller --clean --noconfirm app-offline.spec  → dist/IDLAPS-Offline.exe
# macOS   : pyinstaller --clean --noconfirm app-offline.spec  → dist/IDLAPS-Offline.app
# =============================================================================

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# ── Detect platform ────────────────────────────────────────────────────────────
IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS   = sys.platform.startswith("darwin")

# ── Data files to bundle ───────────────────────────────────────────────────────
added_datas = [
    ("templates",        "templates"),
    ("static",           "static"),
    (".env.production",  "."),
]

# ── Hidden imports ─────────────────────────────────────────────────────────────
hidden = [
    "sqlite3",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    "flask",
    "flask_sqlalchemy",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "jinja2",
    "werkzeug",
    "werkzeug.serving",
    "requests",
    "serial",
    "usb",
    "dotenv",
]
hidden += collect_submodules("PySide6")
hidden += collect_submodules("flask")
hidden += collect_submodules("werkzeug")
hidden += collect_submodules("sqlalchemy")

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
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

# ── Platform-specific output ───────────────────────────────────────────────────
if IS_MACOS:
    # ── macOS : one-dir .app bundle ───────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="IDLAPS-Offline",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        target_arch=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name="IDLAPS-Offline",
    )
    app = BUNDLE(
        coll,
        name="IDLAPS-Offline.app",
        bundle_identifier="com.idlaps.checkpoint.offline",
        info_plist={
            "CFBundleDisplayName": "IDLAPS Offline",
            "CFBundleShortVersionString": os.environ.get("VERSION", "1.0.0"),
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
        },
    )

else:
    # ── Windows : single .exe ─────────────────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="IDLAPS-Offline",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
