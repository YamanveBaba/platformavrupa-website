# Colruyt: oturum, 406 ve token — yenileme prosedürü

Bu dosya `colruyt_product_search_api_cek.py` ve `json_to_supabase_yukle.py` ile uyumludur.

## Ne zaman gerekir?

- API yanıtı **406 Not Acceptable** veya sürekli boş ürün listesi.
- Script mesajı: *"Token süresi dolmuş olabilir"* veya *"Oturum (Cookie) gerekli"*.

## Neden olur?

Colruyt BFF, tarayıcı oturumu ve WAF çerezleri (`reese84`, `clpbff_session`, vb.) ile istekleri eşleştirir. Sadece `X-CG-APIKey` çoğu zaman yeterli değildir; anahtar genelde kamuya yakın sabit bir değerken, **oturum kısa ömürlüdür**.

## Yöntem A — cURL ile güncelleme (önerilen, hızlı)

1. Chrome’da [colruyt.be](https://www.colruyt.be) → `/nl/producten` açın; gerekirse çerez onayı verin.
2. F12 → **Network** → `product-search-prs` isteğini bulun (filtre: Fetch/XHR).
3. İsteğe sağ tık → **Copy** → **Copy as cURL (bash)**.
4. İçeriği `market_fiyat_cekici/curl.txt` dosyasına yapıştırın (tek dosya, üzerine yazın).
5. Script `curl.txt` içinden `Cookie`, `placeId`, `sort`, `x-cg-apikey` vb. otomatik okur.

İsteğe bağlı: Sadece cookie satırını `cookie.txt` içine de koyabilirsiniz (ilk satır ham Cookie değeri).

## Yöntem B — `token.txt`

Bazı ortamlarda BFF kısa ömürlü **token** döner. Network’te token içeren yanıt veya istek başlığı varsa, token string’ini `token.txt` içine koyun (tek satır veya JSON). Script bunu Cookie’ye `token=...` olarak ekler.

Token süresi dolduğunda (~birkaç dakika) yeniden kopyalama gerekebilir; uzun koşularda **Yöntem C** daha stabil olabilir.

## Yöntem C — Playwright (tam otomatik oturum)

Manuel curl kopyası istemiyorsanız:

- `calistir_colruyt_otomatik.bat` → `colruyt_playwright_otomatik_cek.py`  
- Kalıcı Chromium profili ile siteyi açar; çerezler profilde kalır.  
- Çıkan JSON: `cikti/colruyt_be_playwright_*.json` → `python json_to_supabase_yukle.py --no-pause "cikti\..."`

API doğrudan çağrısı 406 verirken Playwright genelde çalışır.

## Haftalık job

- `calistir_colruyt_haftalik.bat` → çekim + en son `colruyt_be_producten_*.json` ile Supabase upsert.
- 406 alırsanız job’dan önce **Yöntem A veya C** ile oturumu yenileyin.
- GitHub Actions gibi datacenter IP’lerinde çerez taşımak zor olabilir; **ev PC veya residential IP** daha tutarlıdır.
