@echo off
REM 
TITLE "Auto Labeling App - Setup & Launch"

ECHO =======================================================
ECHO  Selamat Datang di Aplikasi Pelabelan Otomatis
ECHO =======================================================
ECHO.
ECHO Script ini akan menyiapkan environment dan menjalankan aplikasi.
ECHO Pastikan Python 3 sudah terinstal dan ditambahkan ke PATH.
ECHO.

REM Cek apakah direktori venv sudah ada
IF NOT EXIST venv (
    ECHO [1/4] Direktori 'venv' tidak ditemukan. Membuat virtual environment baru...
    py -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Gagal membuat virtual environment. Pastikan 'py' atau 'python' ada di PATH.
        PAUSE
        EXIT /B
    )
) ELSE (
    ECHO [1/4] Virtual environment sudah ada. Melewati pembuatan.
)

ECHO.
ECHO [2/4] Mengaktifkan virtual environment...
CALL venv\Scripts\activate.bat

ECHO.
ECHO [3/4] Menginstal atau memperbarui library yang dibutuhkan dari requirements.txt...

REM 
py -m pip install --upgrade pip

pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO Gagal menginstal library. Periksa koneksi internet atau file requirements.txt.
    PAUSE
    EXIT /B
)

ECHO.
ECHO [4/4] Semua persiapan selesai. Menjalankan aplikasi GUI...
ECHO.
py main.py

ECHO.
ECHO Aplikasi telah ditutup. Tekan tombol apa saja untuk keluar.
PAUSE