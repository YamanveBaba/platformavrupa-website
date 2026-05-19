@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   Colruyt Urun Cekici
echo ============================================
echo.
echo colruyt_auth.txt dosyasindaki KEY guncel mi?
echo Guncelse devam etmek icin bir tusa basin...
pause >nul
echo.

echo [1/2] Colruyt'tan urunler cekiliyor...
python market_fiyat_cekici/colruyt_product_search_api_cek.py --no-pause
if errorlevel 1 (
    echo HATA: Urun cekilemedi!
    pause
    exit /b 1
)

echo.
echo [2/2] Supabase'e yukleniyor...

:: En son olusturulan colruyt JSON dosyasini bul
set LATEST=
for /f "delims=" %%f in ('dir /b /o-d "market_fiyat_cekici\cikti\colruyt_be_*.json" 2^>nul') do (
    if not defined LATEST set LATEST=%%f
)

if not defined LATEST (
    echo UYARI: JSON dosyasi bulunamadi, Supabase yukleme atlandi.
    pause
    exit /b 0
)

echo Yukleniyor: %LATEST%
python market_fiyat_cekici/json_to_supabase_yukle.py "market_fiyat_cekici/cikti/%LATEST%"

echo.
echo ============================================
echo   Tamamlandi! Colruyt verileri guncellendi.
echo ============================================
pause
