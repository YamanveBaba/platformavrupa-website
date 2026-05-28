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

REM FOREM/Actiris/VDAB GitHub Actions üzerinden çalışıyor.
REM Arbeitnow/Jobicy/Remotive/Adzuna/Bundesagentur artık kullanılmıyor.

echo [%date% %time%] Tamamlandi. >> calistir_log.txt
echo. >> calistir_log.txt
