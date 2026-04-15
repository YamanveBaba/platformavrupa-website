@echo off
cd /d C:\Users\yaman\Desktop\04.01.2026\ilan_cekici

echo [%date% %time%] Ilan cekici basliyor... >> calistir_log.txt

REM 1. Yeni ilanları çek + 30 günlük eskileini expire et
python is_ilani_cekici.py --temizle >> calistir_log.txt 2>&1

REM 2. Yeni ilanların başlıklarını Türkçeye çevir
python ilan_baslik_cevir.py >> calistir_log.txt 2>&1

echo [%date% %time%] Tamamlandi. >> calistir_log.txt
echo. >> calistir_log.txt
