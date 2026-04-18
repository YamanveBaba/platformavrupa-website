# Delhaize Belçika — yakaladığınız isteklerin anlamı

## Yeter mi?

**Katalog + fiyat için doğru yolu bulmuşsunuz:** asıl veri **`GetCategoryProductSearch`** (sayfalı kategori listesi) ve **`GetProductsDetails`** (ürün kodlarına göre detay/fiyat) GraphQL uçlarında. Bu ikisi, betik yazmak için **yeterli keşif**.

## İstek türleri (özet)

| İstek | Dosya / amaç | Veri çekmek için |
|--------|----------------|------------------|
| `product-loader-delhaize-secondary.json` | Lottie animasyon | Hayır — atlanır |
| **GetCategoryProductSearch** | `operationName` + `variables` (category, pageNumber, pageSize, …) | Evet — kategori kategori, `pageNumber` artırarak |
| GetSponsoredProductsV2 | Sponsorlu grid | İsteğe bağlı — genelde atlanır |
| **GetProductsDetails** | `productCodes` listesi | Evet — tile’dan gelen kodlarla toplu fiyat/detay |

## Teknik notlar

- Uç: `https://www.delhaize.be/api/v1/` — query string’de `operationName`, `variables`, `extensions.persistedQuery` (Apollo persisted queries).
- Header’larda **`apollographql-client-name`**, **`apollographql-client-version`**, **`x-apollo-operation-name`** vb. tarayıcıyla aynı kalmalı.
- **`x-dtpc`**, **`traceparent`**, cookie’lerde **`_abck`**, **`bm_*`**: bot koruması (Akamai/Bot Manager). Cookie’ler kısa ömürlü; haftalık job’da tıpkı Colruyt’ta olduğu gibi **güncel `curl.txt`** veya **Playwright oturumu** gerekir.
- **Tüm mağaza:** Tek kategori (`v2FRU`) yetmez; sitedeki diğer kategori kodları için aynı operasyon tekrarlanır (veya üst seviye gezinim keşfi).

## Güvenlik

- Sohbet veya GitHub’a **tam cookie** yapıştırmayın. Bu metinde ham çerez yok; sizinkileri döndürün ve yalnızca yerel `curl.txt` / `cookie.txt` kullanın.

## Sonraki kod adımı

- Python `requests` ile `GetCategoryProductSearch` döngüsü (kategori listesi + sayfa) → ürün kodları → `GetProductsDetails` chunk’ları.
- 403/Challenge olursa: Colruyt’taki gibi **Playwright** ile ağ dinleme veya oturum yenileme.
