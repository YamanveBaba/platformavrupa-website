# Zincir keşif şablonu (ülke × market)

Her yeni **ülke × zincir** hücresi için aşağıyı doldurun. “Sayfayı kaydet” çoğu modern market sitesinde fiyat vermez; hedef her zaman **JSON API** veya **gerçek tarayıcı oturumu** (Playwright).

## 1. Kimlik

| Alan | Değer |
|------|--------|
| Ülke | |
| Zincir | |
| Hedef `chain_slug` | örn. `lidl_be` |
| Hedef `country_code` | örn. `BE` |
| Referans mağaza / posta kodu gerekiyor mu? | evet/hayır |

## 2. Kaynak

| Soru | Not |
|------|-----|
| Ürün listesi URL’i | |
| Fiyat mağazaya mı bağlı? | |
| Giriş / çerez / WAF (Akamai vb.) | |

## 3. Teknik keşif (Chrome DevTools)

1. Sayfayı açın → F12 → **Network** → **Fetch/XHR** (veya **Tümü**).
2. Ürün veya “daha fazla” ile liste yenileyin.
3. JSON dönen istekleri bulun; **Copy → Copy as cURL** ile ham isteği kaydedin (`curl.txt` benzeri).
4. Parametreler: sayfalama (`skip`/`page`), mağaza id, sıralama.

## 4. Yöntem kararı

- [ ] Doğrudan HTTP (Python `requests`) — header/cookie ile mümkün mü?
- [ ] Playwright — oturum veya tıklama zorunlu mu?

## 5. Uygulama

| Madde | Dosya / not |
|-------|-------------|
| Çıktı JSON şeması | |
| `json_to_supabase_yukle.py` mapping | |
| Haftalık tetik | bkz. `HAFTALIK_CEKIM_TAKVIMI_VE_GOREV_ZAMANLAYICI.md` |
