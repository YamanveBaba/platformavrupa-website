@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Lidl BE — Playwright ile API kategori URL listesi (BFS, /s ve /h)
echo Cikti: lidl_be_api_categories_autogen.txt
echo Sonra: python lidl_be_mindshift_api_cek.py --categories-file lidl_be_api_categories_autogen.txt --no-pause
python lidl_be_playwright_cek.py --mode discover_urls --no-pause
pause
