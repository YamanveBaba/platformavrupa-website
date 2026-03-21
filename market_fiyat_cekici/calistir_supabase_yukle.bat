@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo JSON → Supabase market_chain_products yukleme
echo.
echo Once supabase_import_secrets.txt olusturun (ORNEK dosyasina bakin).
echo.
python json_to_supabase_yukle.py %*
pause
