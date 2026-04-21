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

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS   = sys.platform.startswith("darwin")

# ── Data files ────────────────────────────────────────────────────────────────
added_datas = [
    ("templates",       "templates"),
    ("static",          "static"),
    (".env.production",  "."),
]

# ── Hidden imports ────────────────────────────────────────────────────────────
# HANYA sertakan modul Qt yang benar-benar digunakan oleh kode.
# JANGAN gunakan collect_submodules("PySide6") — itu menyertakan seluruh Qt (>400MB)!
hidden = [
    # Qt — hanya 3 modul yang dipakai seluruh codebase
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",

    # Flask & web (mode offline = Flask server lokal)
    "flask",
    "flask_sqlalchemy",
    "jinja2",
    "werkzeug",
    "werkzeug.serving",
    "itsdangerous",
    "click",

    # DB — hanya SQLite, tidak perlu MySQL/PostgreSQL/Oracle
    "sqlite3",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.orm",
    "sqlalchemy.ext.declarative",
    "sqlalchemy.pool",

    # Utilities
    "requests",
    "serial",
    "usb",
    "dotenv",
    "openpyxl",       # Dibutuhkan pandas untuk baca .xlsx
    "pandas",
    "numpy",           # Dependency pandas
]

# Flask & Werkzeug perlu submodulnya untuk routing dinamis
hidden += collect_submodules("flask")
hidden += collect_submodules("werkzeug")
hidden += collect_submodules("jinja2")

# ── Excludes: paket besar yang PASTI tidak digunakan ─────────────────────────
excludes = [
    # Qt modul besar yang tidak dipakai
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebChannel",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtLocation",
    "PySide6.QtPositioning",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtVirtualKeyboard",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtSensors",
    "PySide6.QtStateMachine",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtTest",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtSql",

    # SQLAlchemy dialects yang tidak dipakai (hanya butuh sqlite)
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.postgresql",
    "sqlalchemy.dialects.oracle",
    "sqlalchemy.dialects.mssql",
    "sqlalchemy.dialects.firebird",
    "sqlalchemy.testing",

    # Standard lib — hanya yang benar-benar aman dibuang
    "tkinter",

    # Scientific/ML yang tidak dipakai
    "scipy",
    "matplotlib",
    "PIL",
    "cv2",
    "sklearn",
    "tensorflow",
    "torch",
    "IPython",
    "notebook",
]

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
    excludes=excludes,
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
        name="IDLAPS-Offline",
        debug=False, bootloader_ignore_signals=False,
        strip=True, upx=False, console=False, target_arch=None,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=True, upx=False, name="IDLAPS-Offline",
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
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name="IDLAPS-Offline",
        debug=False, bootloader_ignore_signals=False,
        strip=False, upx=True, upx_exclude=[],
        runtime_tmpdir=None, console=False,
        disable_windowed_traceback=False,
        target_arch=None, codesign_identity=None, entitlements_file=None,
    )
