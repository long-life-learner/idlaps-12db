@echo off

:: Pindah ke direktori home
cd %HOMEPATH%

:: Pindah ke folder IDLAPS CHECKPOINT
cd "IDLAPS CHECKPOINT"

:: Periksa apakah Python tersedia di PATH
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python tidak ditemukan di PATH. Silakan instal atau tambahkan ke PATH.
    pause
    exit /b
)
CALL .\venv\Scripts\activate.bat
:: Jalankan script Python
python main.py
pause