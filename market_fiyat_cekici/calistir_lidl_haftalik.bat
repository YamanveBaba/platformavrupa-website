@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Haftalik Lidl BE + Supabase
python haftalik_lidl_supabase.py
if %ERRORLEVEL% NEQ 0 pause
exit /b %ERRORLEVEL%
