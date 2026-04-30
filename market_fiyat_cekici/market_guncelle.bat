@echo off
:: Platform Avrupa — Market Fiyatlari Haftalik Guncelleme
:: Son calisma tarihini kontrol eder — 5 gunden eskiyse ceker

set LOCKFILE=%~dp0son_calisma.txt
set LOGFILE=%~dp0market_log.txt

echo [%date% %time%] Market guncelleme kontrol ediliyor... >> "%LOGFILE%"

:: Son calisma tarihini oku
if not exist "%LOCKFILE%" (
    echo Ilk calisma, hemen baslaniyor...
    goto CALIS
)

:: 5 gun = 432000 saniye — PowerShell ile yas hesapla
for /f %%i in ('powershell -NoProfile -Command "$d=Get-Content \"%LOCKFILE%\" -ErrorAction SilentlyContinue; if($d){[int](New-TimeSpan -Start ([datetime]$d) -End (Get-Date)).TotalDays}else{999}"') do set GUN_FARK=%%i

echo Son cekimden bu yana %GUN_FARK% gun gecmis. >> "%LOGFILE%"

if %GUN_FARK% LSS 5 (
    echo 5 gun dolmadi, atlanıyor. >> "%LOGFILE%"
    exit /b 0
)

:CALIS
echo [%date% %time%] Market cekim basliyor... >> "%LOGFILE%"

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
"%LOCALAPPDATA%\Programs\Python\Python314\python.exe" haftalik_tam.py >> "%LOGFILE%" 2>&1

:: Basarili bitis tarihini kaydet
powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')" > "%LOCKFILE%"

echo [%date% %time%] Market cekim tamamlandi. >> "%LOGFILE%"
