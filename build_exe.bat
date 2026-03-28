@echo off
echo =========================================================
echo Memulai Proses Pembuatan Executable IDLAPS CHECKPOINT
echo =========================================================

REM Anda perlu memastikan pip library pyinstaller, PySide6, Flask, dsbnya sudah terinstall!
pyinstaller --noconfirm --onefile --windowed --add-data "templates;templates" --add-data "static;static" --add-data ".env.production;." --add-data "C:/Windows/System32/libusb0.dll;." --hidden-import psycopg2 "main.py"

echo =========================================================
echo Proses Selesai! Cek folder "dist" untuk file main.exe
echo =========================================================
pause
