@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================
echo   Aldi Urun Cekici (SingleFile + Parse)
echo ============================================
echo.
echo HAZIRLIK:
echo   1. Chrome acik olmali
echo   2. SingleFile extension auto-save ACIK olmali
echo   3. aldi.be'ye giris gerekmez (urun sayfalari acik)
echo.
echo Devam etmek icin bir tusa basin...
pause >nul
echo.

echo [1/2] Kategori sayfaları acılıyor...
python aldi_cek.py
if errorlevel 1 (
    echo HATA: aldi_cek.py basarisiz
    pause
    exit /b 1
)

echo.
echo Tum sayfalar acıldı. SingleFile kaydetmeyi bitirmis olmali.
echo Parse etmek icin bir tusa basin...
pause >nul
echo.

echo [2/2] HTML dosyalar parse ediliyor ve Supabase'e yukleniyor...
python aldi_parse.py
if errorlevel 1 (
    echo HATA: aldi_parse.py basarisiz
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Tamamlandi!
echo ============================================
pause
