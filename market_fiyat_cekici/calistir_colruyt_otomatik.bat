@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Colruyt — TAM OTOMATİK (Playwright, tarayıcı açılır)
echo İlk seferde açılan pencerede giriş yapın; sonra tek tuş yeter.
echo.
python -m playwright install chromium 2>nul
python colruyt_playwright_otomatik_cek.py
pause
