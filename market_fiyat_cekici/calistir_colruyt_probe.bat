@echo off

chcp 65001 >nul

cd /d "%~dp0"

echo Colruyt API — tek sayfa PROBE (200/403/406; JSON yazilmaz)

echo cookie.txt veya curl.txt guncel olmali.

echo.

python colruyt_product_search_api_cek.py --probe --no-pause --minimal-query

pause

