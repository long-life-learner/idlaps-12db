@echo off
setlocal enabledelayedexpansion

set MODE=%1
if "%MODE%"=="" set MODE=all

echo ==================================================
echo  IDLAPS Checkpoint - Windows Build Script
echo  Mode: %MODE%
echo ==================================================

:: Validasi Python tersedia
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak ditemukan. Pastikan Python sudah masuk ke PATH.
    pause
    exit /b 1
)

:: Validasi PyInstaller tersedia
where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] PyInstaller tidak ditemukan. Mencoba menginstall via pip...
    pip install pyinstaller
)

:: Pastikan .env.production tersedia
if not exist ".env.production" (
    echo [WARNING] .env.production tidak ditemukan.
    echo           Menyalin dari .env.example...
    copy .env.example .env.production
)

:: Bersihkan cache build lama
echo [INFO] Membersihkan cache build lama (build/ dan dist/)...
if exist build rd /s /q build
if exist dist rd /s /q dist

:: Jalankan kompilasi berdasarkan mode
if /i "%MODE%"=="online" (
    call :build_online
    goto :final
)
if /i "%MODE%"=="offline" (
    call :build_offline
    goto :final
)
if /i "%MODE%"=="all" (
    call :build_online
    call :build_offline
    goto :final
)

echo [ERROR] Mode tidak dikenal: %MODE%
echo Gunakan: build_exe.bat online ^| offline ^| all
goto :final

:: ─── Helper: Build Online ────────────────────────────────────────────────────
:build_online
echo.
echo --- [1/2] Building: IDLAPS-Online.exe ---
pyinstaller --clean --noconfirm app-online.spec
if %errorlevel% neq 0 (
    echo [ERROR] Gagal membuat IDLAPS-Online.exe
) else (
    echo [OK] IDLAPS-Online selesai -^> dist/IDLAPS-Online.exe
)
exit /b

:: ─── Helper: Build Offline ───────────────────────────────────────────────────
:build_offline
echo.
echo --- [2/2] Building: IDLAPS-Offline.exe ---
pyinstaller --clean --noconfirm app-offline.spec
if %errorlevel% neq 0 (
    echo [ERROR] Gagal membuat IDLAPS-Offline.exe
) else (
    echo [OK] IDLAPS-Offline selesai -^> dist/IDLAPS-Offline.exe
)
exit /b

:final
echo.
echo ==================================================
echo  Build Selesai! Cek folder dist/
echo ==================================================
if not defined CI pause
exit /b
