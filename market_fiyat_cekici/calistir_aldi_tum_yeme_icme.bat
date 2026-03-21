@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ========================================
echo  ALDI Belçika - Tüm Yeme-Içme Fiyatları
echo  (Tüm kategoriler taranır, 5-15 dk sürebilir)
echo ========================================
echo.
python aldi_tum_yeme_icme_cek.py
if errorlevel 1 (
    echo.
    echo Bir hata oluştu.
    pause
)
