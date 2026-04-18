@echo off
chcp 65001 >nul
echo ================================================
echo  Colruyt Kategori Cekici - Platform Avrupa
echo ================================================
echo.
cd /d "%~dp0"

REM Profilde daha önce giriş yaptıysan --zaten-giris kullan (hızlı başlar)
REM İlk kez çalıştırıyorsan --enter-sonra-devam kullan (giriş için süre verir)

python colruyt_kategori_cek.py --zaten-giris

pause
