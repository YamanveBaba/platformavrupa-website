@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Haftalik Delhaize: GraphQL cekimi + Supabase
echo  Onceden: supabase_import_secrets.txt
echo  Istege bagli: delhaize_cookie.txt (403 durumunda)
echo ============================================================
echo.
python haftalik_delhaize_supabase.py
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
