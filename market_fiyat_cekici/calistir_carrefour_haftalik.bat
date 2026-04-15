@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Haftalik Carrefour BE + Supabase
python haftalik_carrefour_supabase.py
if %ERRORLEVEL% NEQ 0 pause
exit /b %ERRORLEVEL%
