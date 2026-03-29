@echo off
echo =========================================================
echo Memulai Proses Pembuatan Executable IDLAPS CHECKPOINT
echo =========================================================

REM Bersihkan cache lama (recursive) untuk mencegah error dis.py IndexError saat kompilasi
if exist build rmdir /s /q build
FOR /d /r . %%d in (__pycache__) DO @IF EXIST "%%d" rd /s /q "%%d"

REM SQLite sudah built-in Python — tidak perlu psycopg2 atau PostgreSQL.
REM Database file (inventory.db) akan dibuat otomatis di sebelah file .exe.
pyinstaller --clean --noconfirm --onefile --windowed --add-data "templates;templates" --add-data "static;static" --add-data ".env.production;." --add-data "C:/Windows/System32/libusb0.dll;." --hidden-import sqlite3 "main.py"

echo =========================================================
echo Proses Selesai! Cek folder "dist" untuk file main.exe
echo Database (inventory.db) akan dibuat otomatis saat pertama kali dijalankan.
echo =========================================================
pause
