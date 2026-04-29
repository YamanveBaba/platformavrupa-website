@echo off
:: Cift tikla — yonetici gerekmez
:: Her 5 gunde bir saat 08:00'da market verisi ceker

schtasks /delete /tn "PlatformAvrupa_Market_Cekim" /f 2>nul

schtasks /create /tn "PlatformAvrupa_Market_Cekim" ^
  /tr "cmd /c \"%~dp0market_guncelle.bat\"" ^
  /sc DAILY /mo 5 /st 08:00 ^
  /f

if %errorlevel%==0 (
    echo.
    echo BASARILI! Gorev olusturuldu.
    echo Her 5 gunde bir saat 08:00'da otomatik calisacak.
    echo Bilgisayar o saatte acik olmali.
    echo.
    schtasks /query /tn "PlatformAvrupa_Market_Cekim" /fo LIST
) else (
    echo.
    echo HATA: Gorev olusturulamadi.
    echo Bu dosyayi Sag Tikla ^> Yonetici olarak calistir deneyin.
)
pause
