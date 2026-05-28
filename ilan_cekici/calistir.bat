@echo off
cd /d C:\Users\yaman\Desktop\04.01.2026\ilan_cekici

echo [%date% %time%] Ilan cekici basliyor... >> calistir_log.txt

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

REM 1. Yeni ilanları çek (Arbeitnow, Adzuna, Bundesagentur, Jobicy, Remotive)
REM    + 30 günlük eskileini expire et
REM    NOT: FOREM/Actiris/VDAB zaten GitHub Actions üzerinden çalışıyor
%PYTHON% is_ilani_cekici.py --temizle >> calistir_log.txt 2>&1

REM 2. Çeviri GitHub Actions'daki cevir_v2.py tarafından yapılıyor (title_tr)
REM    ilan_baslik_cevir.py kaldırıldı — cevir_v2.py ile çakışıyordu

echo [%date% %time%] Tamamlandi. >> calistir_log.txt
echo. >> calistir_log.txt
