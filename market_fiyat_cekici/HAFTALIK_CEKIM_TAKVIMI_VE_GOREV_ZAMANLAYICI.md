# Haftalık çekim takvimi ve Windows Görev Zamanlayıcı

Amaç: zincirleri **aynı saatte üst üste** çalıştırmayıp hem sunucu tarafında hem IP tarafında yükü dağıtmak. Sıklık: **zincir başına haftada bir**.

## Önerilen dağılım (Belçika — 5 zincir)

| Gün | Zincir | Ne çalışır |
|-----|--------|------------|
| Pazartesi (ör. 03:00) | ALDI BE | [`calistir_aldi_tum_yeme_icme.bat`](calistir_aldi_tum_yeme_icme.bat); platform listesi için [`merge_teklifler_with_assortiment.py`](merge_teklifler_with_assortiment.py) sonrası `python json_to_supabase_yukle.py --no-pause` veya doğrudan en yeni `aldi_be_tum_urunler_platform_*.json`. |
| Salı (ör. 03:30) | Delhaize | [`calistir_delhaize_haftalik.bat`](calistir_delhaize_haftalik.bat) → `haftalik_delhaize_supabase.py` |
| Çarşamba (ör. 03:00) | Colruyt | [`calistir_colruyt_haftalik.bat`](calistir_colruyt_haftalik.bat) veya `python haftalik_colruyt_supabase.py` |
| Perşembe (ör. 03:30) | Lidl | [`calistir_lidl_haftalik.bat`](calistir_lidl_haftalik.bat) (Playwright; site yapısı değişirse güncelleme gerekebilir) |
| Cumartesi (ör. 04:00) | Carrefour | [`calistir_carrefour_haftalik.bat`](calistir_carrefour_haftalik.bat); ilk kurulumda bir kez `python carrefour_be_playwright_cek.py --headed` ile `playwright_user_data/carrefour_be` profilinde çerez önerilir. |

Saatleri kendi trafiğinize göre kaydırın; önemli olan **çakışmayı** önlemek.

## Görev Zamanlayıcı ayarı (Windows)

1. **Görev Zamanlayıcı**’yı açın → **Temel görev oluştur**.  
2. Tetikleyici: Haftalık → ilgili gün ve saat.  
3. Eylem: **Program başlat**  
   - Program: `C:\Windows\System32\cmd.exe`  
   - Bağımsız değişkenler (örnek Colruyt):  
     `/c "cd /d C:\YOL\proje\market_fiyat_cekici && python haftalik_colruyt_supabase.py"`  
   - Tüm yolları kendi makinenize göre düzenleyin.  
4. **Seçenekler:** “Kullanıcı oturum açmış olsa da olmasa da çalıştır” genelde sunucu/PC açık kalıyorsa işe yarar; dizüstünde uyku modu görevi engelleyebilir.

## Ortam

- `supabase_import_secrets.txt` veya `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`  
- Colruyt için güncel [`curl.txt`](curl.txt) / oturum ([`SESSION_VE_406_COZUMU.md`](SESSION_VE_406_COZUMU.md))  

## Log

İsteğe bağlı: her koşudan sonra Supabase `market_price_import_runs` tablosuna kayıt (`json_to_supabase_yukle.py` başarılı upsert sonrası yazar).
