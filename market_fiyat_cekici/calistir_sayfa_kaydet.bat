@echo off
cd /d "%~dp0"
echo ===================================================
echo  SAYFA KAYDET — Kategori sayfalarini kaydeder
echo ===================================================
echo.
echo  Hangi market?
echo  [1] Delhaize
echo  [2] ALDI
echo  [3] Colruyt
echo  [4] Carrefour
echo  [5] Hepsi
echo.
set /p secim=Seciminiz (1-5):

if "%secim%"=="1" python sayfa_kaydet.py --market delhaize
if "%secim%"=="2" python sayfa_kaydet.py --market aldi
if "%secim%"=="3" python sayfa_kaydet.py --market colruyt
if "%secim%"=="4" python sayfa_kaydet.py --market carrefour
if "%secim%"=="5" python sayfa_kaydet.py --market hepsi

echo.
echo Sayfalar kaydedildi. Simdi html analiz calistirabilirsiniz.
pause
