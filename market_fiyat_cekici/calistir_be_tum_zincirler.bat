@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo BE 5 zincir: ALDI, Colruyt, Delhaize, Lidl (categories), Carrefour
echo Zincirler arasi 2-5 dk beklenir. Colruyt icin cookie.txt gerekir.
echo.
python be_tum_zincirler_cek.py --continue-on-error
pause
