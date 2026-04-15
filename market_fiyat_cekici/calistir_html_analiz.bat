@echo off
cd /d "%~dp0"
echo ===================================================
echo  HTML ANALIZ — Kaydedilen sayfalardan veri ceker
echo ===================================================
echo.
echo  [1] Tum dosyalari isle (DB guncelle)
echo  [2] Sadece Delhaize
echo  [3] Sadece ALDI
echo  [4] Sadece Colruyt
echo  [5] Test (DB'ye yazma — dry-run)
echo.
set /p secim=Seciminiz (1-5):

if "%secim%"=="1" python html_analiz.py
if "%secim%"=="2" python html_analiz.py --market delhaize
if "%secim%"=="3" python html_analiz.py --market aldi
if "%secim%"=="4" python html_analiz.py --market colruyt
if "%secim%"=="5" python html_analiz.py --dry-run

echo.
pause
