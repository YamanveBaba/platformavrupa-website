@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Colruyt — TAM OTOMATİK (Playwright, tarayıcı açılır)
echo Profilde zaten giris varsa kisa bekleme ile: --zaten-giris
echo Ilk kurulum: Enter ile devam icin --enter-sonra-devam kullanin.
echo Mağaza placeId (ornek Gent 710): --place-id 710
echo.
python -m playwright install chromium 2>nul
python colruyt_playwright_otomatik_cek.py --zaten-giris
pause
