# Lidl Belçika — veri çekme keşif notu ve yöntem kararı

## Durum (2026-03)

Resmî, belgelenmiş bir **halka açık ürün fiyat API’si** bulunmuyor. Kamuya yönelik çözümler genelde **web kazıma** (Apify, özel scraper vb.) veya tarayıcı otomasyonu ile çalışır; bunlar Platform Avrupa repo’sunun dışında üçüncü parti hizmet olabilir.

## Önerilen yaklaşım (sizin Colruyt/ALDI hattıyla uyumlu)

1. **Manuel teknik keşif (zorunlu)**  
   - Tarayıcı: `lidl.be` (veya güncel Lidl BE çevrimiçi mağaza URL’i) → ürün listesi veya arama.  
   - F12 → **Network** → **Fetch/XHR** → ürün yüklenirken giden istekler.  
   - JSON dönen uç varsa: parametreler (sayfa, mağaza, dil), gerekli header/cookie, hız sınırı.  
   - Sonuçları [`ZINCIR_KESIF_SABLONU.md`](ZINCIR_KESIF_SABLONU.md) ile dokümante edin.

2. **Yöntem kararı (tahmini)**

| Senaryo | Öneri |
|---------|--------|
| Stabil JSON API + makul koruma | Python `requests` + gecikme + `curl.txt` benzeri oturum (Colruyt modeli). |
| Çoğunlukla istemci tarafı render, WAF ağır | **Playwright** ile kalıcı profil + network yanıtı toplama veya DOM (son çare). |
| API yok, sadece üçüncü parti scraper | Repo dışı hizmet veya kendi Playwright döngünüz; hukuki/ToS değerlendirmesi sizin sorumluluğunuzda. |

3. **Supabase entegrasyonu**  
   - Hedef `chain_slug`: `lidl_be`, `country_code`: `BE`.  
   - [`json_to_supabase_yukle.py`](json_to_supabase_yukle.py) içinde Lidl JSON şeması için `detect_format` + `row_lidl` eklenmeli (keşif sonrası alan adları netleşince).

4. **Sonraki kod adımı**  
   Repo’da deneysel betik: [`lidl_be_playwright_cek.py`](lidl_be_playwright_cek.py) → `cikti/lidl_be_producten_*.json`; haftalık: [`calistir_lidl_haftalik.bat`](calistir_lidl_haftalik.bat). Site DOM’u değişirse seçiciler güncellenmelidir.

## Ban / oran sınırı

Colruyt ile aynı ilkeler: haftada bir, istekler arası rastgele gecikme, mümkünse **aynı makinede** (residential IP) çalıştırma; datacenter IP’lerde çoğu market sitesi daha agresif davranır.
