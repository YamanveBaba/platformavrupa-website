@echo off
:: Platform Avrupa - 5 günde bir otomatik fiyat güncelleme
:: Bu dosyayı bir kez çalıştır — Windows Görev Zamanlayıcı'ya ekler
:: Siler: schtasks /delete /tn "PlatformAvrupa_FiyatGuncelle" /f

set SCRIPT=%~dp0haftalik_tam.py

:: Python yolu — py launcher > python > hardcoded fallback
set PYTHON=py -3
where py >nul 2>&1
if not %errorlevel% == 0 (
    where python >nul 2>&1
    if %errorlevel% == 0 (
        set PYTHON=python
    ) else (
        set PYTHON="%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    )
)

echo Windows Gorev Zamanlayici'ya ekleniyor...

schtasks /create ^
  /tn "PlatformAvrupa_FiyatGuncelle" ^
  /tr "cmd /c \"cd /d %~dp0 && %PYTHON% haftalik_tam.py >> loglar\otomasyon.log 2>&1\"" ^
  /sc DAILY ^
  /mo 5 ^
  /st 03:00 ^
  /f

if %errorlevel% == 0 (
    echo.
    echo TAMAM! Her 5 gunde bir saat 03:00'da otomatik calisacak.
    echo Log: %~dp0loglar\otomasyon.log
    echo.
    echo Gormek icin: schtasks /query /tn "PlatformAvrupa_FiyatGuncelle"
    echo Silmek icin: schtasks /delete /tn "PlatformAvrupa_FiyatGuncelle" /f
) else (
    echo.
    echo HATA: Gorev eklenemedi. Yonetici olarak calistir.
    echo Sagclick ^> Yonetici olarak calistir
)
pause
