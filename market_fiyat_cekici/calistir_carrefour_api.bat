@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Carrefour BE - Tam Urun + Fiyat Cekici (API Interception)
echo ============================================================
echo.
echo [IPUCU] Ilk seferde Cloudflare icin:
echo   python carrefour_be_api_cek.py --headed
echo.
echo [IPUCU] API endpoint kesfetmek icin:
echo   python carrefour_be_api_cek.py --kesfet --headed
echo.
python carrefour_be_api_cek.py %*
pause
