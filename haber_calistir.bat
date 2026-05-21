@echo off
chcp 65001 >nul
cd /d "%~dp0"

set TELEGRAM_BOT_TOKEN=8695279896:AAGX1y5R7_DnR4NX_lGEqVSBh7_ZC8kDsos
set TELEGRAM_CHAT_ID=8427447352
set GEMINI_API_KEY=AIzaSyAe_dzhnqVwzfOAXpvQBp__gIUieU_dJzc

echo Haberler cekiliyor ve Telegram'a gonderiliyor...
python ilan_cekici/haber_cek.py

echo.
echo Tamamlandi. Telegram'i kontrol et.
pause
