@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo 1) Kaydedilmis "Bu haftanin firsatlari" HTML dosyasindan teklifler cikariliyor...
echo    (Varsayilan: Downloads\Bu haftanin firsatlari – ALDI Belcika.html)
echo.
python parse_aldi_teklifler_html.py "C:\Users\yaman\Downloads\Bu haftanın fırsatları – ALDI Belçika.html"
if errorlevel 1 (
    echo Hata: parse tamamlanamadi.
    pause
    exit /b 1
)
echo.
echo 2) Teklifler + tum urun listesi birlestiriliyor (platform + indirimde olanlar)...
python merge_teklifler_with_assortiment.py
if errorlevel 1 (
    echo Hata: birlestirme tamamlanamadi.
    pause
    exit /b 1
)
echo.
echo Tamamlandi. cikti klasorune bakin.
pause
