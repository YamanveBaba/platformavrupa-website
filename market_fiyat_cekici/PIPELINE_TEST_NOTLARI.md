# Belçika pipeline test notları (ALDI + Colruyt)

Bu dosya, repo içinde **JSON → `json_to_supabase_yukle` eşlemesinin** çalıştığını doğrulamak için otomatik/manuel adımları özetler.

## 1. Dry-run (yerel, Supabase gerekmez)

PowerShell veya CMD:

```bat
cd market_fiyat_cekici
python json_to_supabase_yukle.py --dry-run --no-pause "cikti\aldi_be_tum_yeme_icme_2026-03-15_16-38.json"
python json_to_supabase_yukle.py --dry-run --no-pause "test_fixtures\colruyt_be_minimal.json"
```

Tek tık: [`calistir_pipeline_dryrun_test.bat`](calistir_pipeline_dryrun_test.bat)

**Son çalıştırma (repo ortamı):**

| Kaynak | Satır sayısı | `chain_slug` | Sonuç |
|--------|----------------|--------------|--------|
| ALDI `aldi_be_tum_yeme_icme_*.json` | 1880 | `aldi_be` | OK |
| Colruyt minimal fixture | 1 | `colruyt_be` | OK |

**Not:** `cikti/colruyt_be_producten_*.json` örnekleri bu repoda **ürün listesi boş** (`urun_sayisi: 0`); gerçek Colruyt çekimi sonrası dosya dolu olmalı. Boş dosyada yükleme scripti bilerek çıkar.

## 2. Gerçek Supabase upsert (manuel)

1. `supabase_import_secrets.txt` (URL + service_role) hazır olsun.
2. `python json_to_supabase_yukle.py --no-pause "<json_yolu>"`
3. Supabase Table Editor: `market_chain_products` filtre `country_code = BE`, `chain_slug` ile kontrol.

## 3. Canlı site (`market.html`)

1. Supabase’te `market_chain_products_stats` görünümü oluşturulmuş olsun ([`supabase_market_stats_and_cross_chain.sql`](supabase_market_stats_and_cross_chain.sql)).
2. Netlify’a güncel `market.html` deploy.
3. Tarayıcıda `market.html` → ülke **Belçika** → özet ve arama.

## 4. `json_to_supabase_yukle.py` Windows konsolu

Çıktı satırında Unicode ok yerine ASCII kullanıldı (`->`); Türkçe karakter içeren ürün adlarında konsol kod sayfası yüzünden bozulma görülebilir; dosya ve UTF-8 doğrudur.
