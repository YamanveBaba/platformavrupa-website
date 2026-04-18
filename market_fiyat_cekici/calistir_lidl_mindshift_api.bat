@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Lidl BE Mindshift API — lidl_cookie.txt + lidl_be_api_categories.txt gerekir
python lidl_be_mindshift_api_cek.py --no-pause
pause
