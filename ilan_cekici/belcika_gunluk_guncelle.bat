@echo off
:: Platform Avrupa — Belçika İş İlanları Günlük Güncelleme
:: Her gün sabah 06:00'da Windows Görev Zamanlayıcı ile çalıştırılır
:: Görev Zamanlayıcı'ya eklemek için: schtasks /create /tn "PlatformAvrupa-Belcika" /tr "C:\Users\yaman\Desktop\04.01.2026\ilan_cekici\belcika_gunluk_guncelle.bat" /sc daily /st 06:00

cd /d "C:\Users\yaman\Desktop\04.01.2026\ilan_cekici"

echo [%date% %time%] Belcika is ilanlari guncelleniyor...

:: FOREM (Wallonia) — ~8 dakika
python -X utf8 forem_cek.py --temizle >> "%~dp0guncelleme_log.txt" 2>&1

:: Actiris (Brüksel) — ~15 dakika
python -X utf8 actiris_cek.py --temizle >> "%~dp0guncelleme_log.txt" 2>&1

:: VDAB (Flandriya) — ~10 dakika
python -X utf8 vdab_cek.py --max 2000 >> "%~dp0guncelleme_log.txt" 2>&1

echo [%date% %time%] Guncelleme tamamlandi. >> "%~dp0guncelleme_log.txt"
echo Tamamlandi.
