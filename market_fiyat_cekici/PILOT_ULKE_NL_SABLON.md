# Pilot ülke genişlemesi (örnek: Hollanda / NL)

Amaç: Belçika boru hattını kopyalayıp `country_code` ve `chain_slug` ile ayırmak.

## Adımlar

1. **Supabase:** `market_chain_products` satırlarında `country_code = 'NL'`, `chain_slug = 'colruyt_nl'` (veya ilgili zincir) kullanın. Upsert anahtarı `chain_slug, external_product_id` olduğundan BE satırlarıyla çakışmaz.
2. **Script:** Mevcut Colruyt betiğini kopyalayın veya `CONFIG` içinde `base_url` / `place_id` / `Referer` değerlerini **nl** sitesine göre değiştirin. Çıktı dosya adı: `colruyt_nl_producten_*.json`.
3. **Yükleme:** `json_to_supabase_yukle.py` için `detect_format` + `row_colruyt` içinde `country_code` ve `chain_slug` kök JSON’dan okunmalıdır (şu an Colruyt satırı `colruyt_be` sabit; NL için kökte `"chain_slug": "colruyt_nl"` ve `"country_code": "NL"` verin ve `row_colruyt`’u bu alanları kullanacak şekilde genişletin — tek seferlik küçük kod değişikliği).
4. **Frontend:** `market.html` içinde ülke seçici NL iken aynı `market_chain_products` sorgusu `country_code=eq.NL` filtresi ile çalıştırılabilir.
5. **Görev Zamanlayıcı:** BE zincirleriyle aynı gün çakıştırmayın; NL için ayrı geceler.

## PoC kapsamı

İlk sprintte yalnızca **bir zincir × bir ülke** (ör. Colruyt NL) ile doğrulama yeterlidir; ardından diğer zincirler aynı kalıpla eklenir.
