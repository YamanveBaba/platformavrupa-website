# Belçika — zincir × veri yöntemi × script dosyaları

Ülke kodu: **BE**. Supabase’te satırlar `country_code = 'BE'` ve `chain_slug` ile ayrılır (`aldi_be`, `colruyt_be`, ileride `lidl_be` vb.).

| Öncelik | Zincir | `chain_slug` (hedef) | Veri yöntemi | Ana script / dosya | Yükleme | Not |
|--------|--------|----------------------|--------------|-------------------|---------|-----|
| 1 | ALDI Belçika | `aldi_be` | Mevcut ALDI API/akış (yeme-içme vb.) | [`aldi_tum_yeme_icme_cek.py`](aldi_tum_yeme_icme_cek.py), teklif birleştirme: [`merge_teklifler_with_assortiment.py`](merge_teklifler_with_assortiment.py) | [`json_to_supabase_yukle.py`](json_to_supabase_yukle.py) | Tam liste için merge çıktısı tercih edilir. |
| 2 | Colruyt | `colruyt_be` | `product-search-prs` API + cookie; yedek Playwright | [`colruyt_product_search_api_cek.py`](colruyt_product_search_api_cek.py), [`colruyt_playwright_otomatik_cek.py`](colruyt_playwright_otomatik_cek.py) | `json_to_supabase_yukle.py` veya [`haftalik_colruyt_supabase.py`](haftalik_colruyt_supabase.py) | Oturum: [`SESSION_VE_406_COZUMU.md`](SESSION_VE_406_COZUMU.md), [`curl.txt`](curl.txt) |
| 3 | Delhaize BE | `delhaize_be` | Apollo GraphQL `GetCategoryProductSearch` | [`delhaize_be_graphql_cek.py`](delhaize_be_graphql_cek.py) | [`haftalik_delhaize_supabase.py`](haftalik_delhaize_supabase.py) / `json_to_supabase_yukle.py` | Kategoriler: `/nl/shop` veya [`delhaize_be_categories.txt`](delhaize_be_categories.txt). İsteğe bağlı: `delhaize_cookie.txt`. Not: [`DELHAIZE_BE_GRAPHQL_NOTLARI.md`](DELHAIZE_BE_GRAPHQL_NOTLARI.md) |
| 4 | Lidl BE | `lidl_be` | Öncelik: [`lidl_be_mindshift_api_cek.py`](lidl_be_mindshift_api_cek.py) (`lidl_cookie.txt` + `lidl_be_api_categories.txt`); yoksa Playwright `--mode categories` / `search` | [`lidl_be_playwright_cek.py`](lidl_be_playwright_cek.py) | [`haftalik_lidl_supabase.py`](haftalik_lidl_supabase.py) | Cookie şablon: `lidl_cookie_SABLON.txt` → `lidl_cookie.txt`; profil: `playwright_user_data/lidl_be`; orkestratör: [`be_tum_zincirler_cek.py`](be_tum_zincirler_cek.py) |
| 5 | Carrefour BE | `carrefour_be` | Playwright + promosyon/liste DOM | [`carrefour_be_playwright_cek.py`](carrefour_be_playwright_cek.py) | [`haftalik_carrefour_supabase.py`](haftalik_carrefour_supabase.py) | Cloudflare: kalıcı profil + ilk sefer `--headed`. Not: [`CARREFOUR_BE_KESIF_NOTLARI.md`](CARREFOUR_BE_KESIF_NOTLARI.md) |

## Test ve haftalık işletme

- Pipeline dry-run ve notlar: [`PIPELINE_TEST_NOTLARI.md`](PIPELINE_TEST_NOTLARI.md), [`calistir_pipeline_dryrun_test.bat`](calistir_pipeline_dryrun_test.bat)
- Haftalık takvim ve Görev Zamanlayıcı: [`HAFTALIK_CEKIM_TAKVIMI_VE_GOREV_ZAMANLAYICI.md`](HAFTALIK_CEKIM_TAKVIMI_VE_GOREV_ZAMANLAYICI.md)

## Ortak boru hattı

- Çıktı: `cikti/*.json`
- Tablo: [`supabase_market_chain_products.sql`](supabase_market_chain_products.sql) — `market_chain_products`
- İsteğe bağlı özet görünüm: [`supabase_market_stats_and_cross_chain.sql`](supabase_market_stats_and_cross_chain.sql)
- Frontend: [`../market.html`](../market.html) — ülke **BE** seçildiğinde arama ve özet

## Yeni zincir ekleme

[`ZINCIR_KESIF_SABLONU.md`](ZINCIR_KESIF_SABLONU.md) şablonunu kullanın; ardından `json_to_supabase_yukle.py` içinde yeni format için `row_*` ve `detect_format` genişletilir.
