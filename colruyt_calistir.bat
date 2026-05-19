@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   Colruyt Urun Cekici Baslatiliyor...
echo ============================================
echo.
echo colruyt_auth.txt dosyasindaki KEY ve COOKIE guncel mi?
echo Guncelse devam etmek icin bir tusa basin...
pause >nul
echo.
python market_fiyat_cekici/colruyt_product_search_api_cek.py
echo.
echo ============================================
echo   Tamamlandi!
echo ============================================
pause
