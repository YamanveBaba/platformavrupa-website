@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ========================================
echo  ALDI Belçika - Tam producten katalog
echo  Insansi mod + max 600 sayfa (uzun surebilir)
echo ========================================
echo.
python aldi_tum_yeme_icme_cek.py --human --max-pages 600
if errorlevel 1 (
    echo.
    echo Bir hata oluştu.
    pause
)
