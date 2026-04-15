@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ========================================
echo  ALDI Belçika - Bira Fiyat Çekici
echo ========================================
echo.
python aldi_bier_cek.py
if errorlevel 1 (
    echo.
    echo Bir hata oluştu. Kurulum rehberini kontrol edin.
    pause
)
