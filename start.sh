#!/bin/bash

echo "======================================================="
echo " Selamat Datang di Aplikasi Pelabelan Otomatis"
echo "======================================================="
echo ""
echo "Script ini akan menyiapkan environment dan menjalankan aplikasi."
echo "Pastikan Python 3 sudah terinstal."
echo ""

# Cek apakah direktori venv sudah ada
if [ ! -d "venv" ]; then
    echo "[1/4] Direktori 'venv' tidak ditemukan. Membuat virtual environment baru..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Gagal membuat virtual environment. Pastikan 'python3' terinstal."
        exit 1
    fi
else
    echo "[1/4] Virtual environment sudah ada. Melewati pembuatan."
fi

echo ""
echo "[2/4] Mengaktifkan virtual environment..."
source venv/bin/activate

echo ""
echo "[3/4] Menginstal atau memperbarui library yang dibutuhkan dari requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Gagal menginstal library. Periksa koneksi internet atau file requirements.txt."
    exit 1
fi

echo ""
echo "[4/4] Semua persiapan selesai. Menjalankan aplikasi GUI..."
echo ""
python3 main.py

echo ""
echo "Aplikasi telah ditutup."