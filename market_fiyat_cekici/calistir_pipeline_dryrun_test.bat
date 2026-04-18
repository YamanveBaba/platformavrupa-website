@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Pipeline dry-run: ALDI BE + Colruyt test fixture
echo.
python json_to_supabase_yukle.py --dry-run --no-pause "cikti\aldi_be_tum_yeme_icme_2026-03-15_16-38.json"
if errorlevel 1 exit /b 1
echo.
python json_to_supabase_yukle.py --dry-run --no-pause "test_fixtures\colruyt_be_minimal.json"
if errorlevel 1 exit /b 1
echo.
echo Tamam.
exit /b 0
