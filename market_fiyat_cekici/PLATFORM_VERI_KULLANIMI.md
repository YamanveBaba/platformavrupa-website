# Platformda Fiyat ve İndirim Verilerinin Kullanımı

## Nereye kaydedilecek? (net karar — 2026-02)

| Aşama | Nerede |
|--------|--------|
| **Çekim / doğrulama** | Laptop’ta `market_fiyat_cekici/cikti/*.json` (ALDI birleşik çıktı, Colruyt Playwright/API çıktısı vb.) |
| **Canlı sitede kullanım** | **Supabase** tablosu **`market_chain_products`** (son fiyat satırları; haftalık `upsert`) |
| **İsteğe bağlı log** | **`market_price_import_runs`** (her job: kaç satır, başarı/hata) |
| **Frontend** | `market.html` vb. sayfalar yalnızca **Supabase anon key** ile `SELECT` (yazma yok) |

1. Supabase SQL Editor’da şu dosyayı çalıştır: **`supabase_market_chain_products.sql`**  
2. İsteğe bağlı (market sayfası özet + çapraz eşleme): **`supabase_market_stats_and_cross_chain.sql`** — `market_chain_products_stats` görünümü ve `product_cross_chain_match` tabloları.  
3. Laptop’ta JSON üretildikten sonra **`json_to_supabase_yukle.py`** ile `upsert` (`supabase_import_secrets.txt` veya ortam değişkenleri).  
4. Haftalık Colruyt otomasyonu: **`calistir_colruyt_haftalik.bat`** veya `python haftalik_colruyt_supabase.py`. Oturum hatası (406): **`SESSION_VE_406_COZUMU.md`**.  
5. Eski ALDI akışındaki `aldi_be_tum_urunler_platform_*.json` alanları, `market_chain_products` sütunlarına **map** edilir (`chain_slug='aldi_be'`, `external_product_id` = `productID` vb.).

Belçika zincir matrisi ve test: **`BELCIKA_ZINCIR_VERI_HATTI.md`**, **`PIPELINE_TEST_NOTLARI.md`**, haftalık zamanlama: **`HAFTALIK_CEKIM_TAKVIMI_VE_GOREV_ZAMANLAYICI.md`**.

Ana proje dokümantasyonu: **`PLATFORMAVRUPA_PROJE_DOKUMANTASYONU.md`** (v3.1) — Veritabanı bölümünde aynı şema metni var.

---

## Amaç

- **Tüm fiyatlar** sistemde olacak: Kullanıcı arama yaptığında veya karşılaştırma yaptığında platform fiyatı gösterebilecek.
- **İndirimli ürünler listesi** ayrı yayınlanacak: "Bu haftanın fırsatları" gibi ayrı bir bölümde sadece indirimde olan ürünler ve geçerlilik tarihleri gösterilecek.

---

## Veri Akışı (Özet)

1. **Tam ürün listesi:** `aldi_tum_yeme_icme_cek.py` → `cikti/aldi_be_tum_yeme_icme_*.json` (tüm ürünler, normal fiyatlar).
2. **Bu haftanın teklifleri:** "Bu haftanın fırsatları" sayfası kaydedilir (Ctrl+S) → `parse_aldi_teklifler_html.py` → `cikti/aldi_be_teklifler_*.json` (indirimli ürünler + geçerlilik tarihi).
3. **Birleştirme:** `merge_teklifler_with_assortiment.py` → iki çıktı:
   - **aldi_be_tum_urunler_platform_*.json** → Platforma yüklenecek **tam liste** (herkes fiyat görsün, indirimde olanlarda promo alanları dolu).
   - **aldi_be_indirimde_olanlar_*.json** → Ayrı yayınlanacak **sadece indirimde olanlar** listesi (geçerlilik tarihiyle).

---

## Platformda Kullanım

### 1) Tüm fiyatlar (arama / karşılaştırma)

- **Dosya:** `aldi_be_tum_urunler_platform_*.json`
- **İçerik:** Tüm ürünler (productID, productName, brand, priceWithTax, category, …). İndirimde olanlarda ek alanlar: `inPromotion: true`, `promoPrice`, `promoValidFrom`, `promoValidFromLabel`.
- **Kullanım:** Bu dosyayı platforma (Supabase tablosu, statik JSON veya API) yüklersiniz. Kullanıcı ürün aradığında veya karşılaştırma yaptığında bu listeden fiyat gösterilir.

### 2) İndirimde olanlar (ayrı liste yayını)

- **Dosya:** `aldi_be_indirimde_olanlar_*.json`
- **İçerik:** Sadece bu hafta teklifte olan ürünler; her birinde fiyat, indirimli fiyat, **geçerlilik tarihi** (validFrom / promoValidFromLabel).
- **Kullanım:** Platformda "Bu haftanın fırsatları" / "İndirimdeki ürünler" sayfasında ayrı liste olarak yayınlanır. Geçerlilik tarihi (örn. "16/03 Pazartesi gününden itibaren") kullanıcıya gösterilir.

---

## Çalıştırma Sırası

1. (İsteğe bağlı) Tam listeyi güncelle: `calistir_aldi_tum_yeme_icme.bat` veya `python aldi_tum_yeme_icme_cek.py`
2. Tarayıcıda ALDI "Bu haftanın fırsatları" sayfasını aç, **Ctrl+S** ile kaydet (örn. Downloads’a).
3. Teklifleri çıkar:  
   `python parse_aldi_teklifler_html.py "C:\Users\yaman\Downloads\Bu haftanın fırsatları – ALDI Belçika.html"`
4. Birleştir:  
   `python merge_teklifler_with_assortiment.py`  
   (En son `aldi_be_teklifler_*.json` ve `aldi_be_tum_yeme_icme_*.json` otomatik kullanılır.)
5. **cikti** klasöründen:
   - `aldi_be_tum_urunler_platform_*.json` → platforma tam fiyat listesi
   - `aldi_be_indirimde_olanlar_*.json` → ayrı indirim listesi yayını

Tek tık için: `calistir_teklifler_parse_ve_birlestir.bat` (önce parse, sonra merge; HTML yolunu bat içinde düzenleyebilirsiniz).
