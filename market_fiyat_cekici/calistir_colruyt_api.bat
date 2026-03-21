@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Colruyt Belçika - API ile ürün+fiyat çekimi
echo.
python colruyt_product_search_api_cek.py
pause
