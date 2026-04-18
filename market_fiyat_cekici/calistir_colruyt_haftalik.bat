@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Haftalik Colruyt: API cekimi + Supabase market_chain_products
echo  Onceden: supabase_import_secrets.txt, curl.txt veya cookie/token
echo ============================================================
echo.
python haftalik_colruyt_supabase.py
set EXITCODE=%ERRORLEVEL%
echo.
if %EXITCODE% NEQ 0 (
  echo HATA: Cikis kodu %EXITCODE%
  pause
  exit /b %EXITCODE%
)
echo Tamam.
pause
exit /b 0
