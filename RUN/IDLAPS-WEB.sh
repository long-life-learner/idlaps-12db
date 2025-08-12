#!/bin/bash

# Masuk ke direktori home
cd ~

# Masuk ke folder IDLAPS CHECKPOINT
cd "IDLAPS CHECKPOINT" || { echo "Folder tidak ditemukan"; read -p "Press enter to exit..."; exit 1; }

# Cek apakah Python tersedia
if ! command -v python &> /dev/null
then
    echo "Python tidak ditemukan di PATH. Silakan instal atau tambahkan ke PATH."
    read -p "Press enter to exit..."
    exit 1
fi

# Aktifkan virtual environment
source ./venv/Scripts/activate

# Jalankan script python
python web.py

read -p "Press enter to exit..."
