@echo off
chcp 65001 >nul
echo ================================================
echo  Colruyt - ILK KURULUM (giriş yapman gerekiyor)
echo ================================================
echo.
echo ADIMLAR:
echo 1. Tarayici acilacak
echo 2. Colruyt hesabinla GIRIS YAP
echo 3. GENT magazasini sec
echo 4. Bu siyah pencereye don ve ENTER'a bas
echo.
cd /d "%~dp0"
python colruyt_kategori_cek.py --enter-sonra-devam
pause
