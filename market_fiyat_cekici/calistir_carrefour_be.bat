@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Carrefour BE Playwright (profil: playwright_user_data\carrefour_be)
echo Ilk seferde cerez icin: python carrefour_be_playwright_cek.py --headed
python carrefour_be_playwright_cek.py
pause
