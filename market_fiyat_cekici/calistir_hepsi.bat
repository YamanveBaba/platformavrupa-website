@echo off
cd /d "%~dp0"
echo ===================================================
echo  HAFTALIK FIYAT GUNCELLEME — 5 MARKET
echo ===================================================
echo.

echo [1/5] Delhaize — camoufox + GraphQL interception + Supabase yukleme...
python haftalik_delhaize_supabase.py
echo.

echo [2/6] ALDI — HTML sayfa kaydet + analiz (DB'ye yaz)...
python sayfa_kaydet.py --market aldi
python html_analiz.py --market aldi
echo.

echo [3/6] Colruyt — Cookie yenile + API cek + DB'ye yaz...
python colruyt_cookie_yenile.py
python colruyt_direct.py
python html_analiz.py --market colruyt
echo.

echo [4/5] Carrefour — camoufox + Meer tonen tiklama + Supabase yukleme...
python haftalik_carrefour_supabase.py
echo.

echo [5/5] Lidl — Mindshift API (lidl_cookie.txt) + Supabase yukleme...
python haftalik_lidl_supabase.py
echo.

echo ===================================================
echo  TAMAMLANDI! 5 market fiyatlari guncellendi.
echo ===================================================
pause
