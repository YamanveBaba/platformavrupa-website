@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Lidl BE Playwright cekimi (cikti/lidl_be_producten_*.json)
python lidl_be_playwright_cek.py
pause
