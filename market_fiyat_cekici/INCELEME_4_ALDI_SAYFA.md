# 4 ALDI Belçika Sayfası – İnceleme Özeti

Tarih: 15.03.2026 kayıtları. Dört HTML dosyası incelendi.

---

## 1. Dosyalar ve içerdikleri ürün sayısı

| Dosya | Sayfa türü | `data-article` (ürün kartı) sayısı | Yapı |
|-------|------------|-------------------------------------|------|
| **Yeni ürünler, bilinen düşük fiyatlar** | Ürün listesi (yeni ürünler) | 69 | `mod-article-tile` + `data-article` (tek tırnak içinde JSON) |
| **Aanbiedingen van deze week** | Bu haftanın teklifleri (NL başlık) | 247 | `mod-offers__day` (data-rel=2026-03-11 vb.) + `mod-article-tile` + `data-article` |
| **Sığır eti satın alın ｜ Geniş ürün yelpazesi** | Kategori (sığır eti) | 24 | `mod-article-tile` + `data-article` |
| **Bu haftanın fırsatları** | Bu haftanın teklifleri (TR başlık) | 247 | Aanbiedingen ile aynı yapı |

---

## 2. Ortak veri yapısı (hepsinde aynı)

Tüm sayfalarda ürün bilgisi **`data-article`** attribute’unda. İçerik örnek:

```json
{
  "id": "/nl/producten/.../snippet-3013188-1-0.shoppinglisttile.article.html",
  "productInfo": {
    "productName": "Baba ganoush of tomaat-bruschetta",
    "productID": "3013188",
    "brand": "DAYLICIOUS®",
    "ownedBrand": "Not Owned",
    "priceWithTax": 2.49,
    "quantity": 1,
    "inPromotion": false
  },
  "productCategory": {
    "primaryCategory": "Dips-sauzen-en-dressing",
    "subCategory1": "n/a",
    "subCategory2": "n/a"
  }
}
```

Teklif sayfalarında ek alan: **`"inPromotion": true`** ve **`"promotionDate": 1773183600000`** (timestamp).  
Tarih bilgisi ayrıca **`mod-article-tile__promotionData`** içinde: `data-promotion-date-formatted-with-prefix="sinds wo 11/03"`, `data-promotion-date-millis="1773183600000"`.

---

## 3. İki sayfa tipi

- **Tip A – Ürün / kategori listesi**  
  (Yeni ürünler, Sığır eti sayfası)  
  - Sadece `mod-article-tile` + `data-article`.  
  - Tarih bloğu yok (`mod-offers__day` yok).  
  - Parser: Sayfadaki tüm `[data-article]` bulunur, JSON parse edilir → productID, productName, brand, priceWithTax, inPromotion, primaryCategory.

- **Tip B – Teklif sayfası**  
  (Bu haftanın fırsatları, Aanbiedingen van deze week)  
  - `mod-offers__day` ile `data-rel="2026-03-11"` (ve diğer tarihler).  
  - Her blokta `mod-article-tile` + `data-article`; bazı kartlarda `mod-article-tile__promotionData` ile geçerlilik tarihi.  
  - Mevcut **parse_aldi_teklifler_html.py** bu yapıyı destekliyor (tarih + ürün + inPromotion + promotionDate).

---

## 4. Küçük fark: attribute tırnakları

- **Yeni ürünler / Sığır eti:** `data-article='{"id":...}'` → tek tırnak, JSON içinde çift tırnak; HTML entity yok.
- **Bu haftanın fırsatları (eski kayıt):** Bazen `data-article="{&quot;id&quot;:...}"` → çift tırnak + `&quot;`.

Parser tarafında: `data-article` değeri alındıktan sonra `&quot;` → `"` yapılırsa her iki format da çalışır. Mevcut teklif parser’ında bu zaten var.

---

## 5. Sonuç ve öneri

- **Dört sayfa da aynı ALDI BE yapısını kullanıyor;** hepsinden **ürün adı, productID, marka, fiyat, indirim bilgisi, kategori** güvenle çıkarılabilir.
- **Bu haftanın fırsatları / Aanbiedingen:** Mevcut **parse_aldi_teklifler_html.py** ile işlenebilir (dosya yolu verilerek). Tarih blokları (`data-rel`) ve `promotionData` ile geçerlilik tarihi de alınır.
- **Yeni ürünler** ve **Sığır eti** sayfaları için: Aynı `data-article` mantığını kullanan, ancak **tarih bloğu aramayan** tek bir “genel ALDI ürün listesi” parser’ı yazılabilir. Girdi: kaydedilmiş HTML; çıktı: ürün listesi JSON (productID, productName, brand, priceWithTax, inPromotion, primaryCategory, sayfa_türü: "yeni_urunler" / "kategori" gibi).

İsterseniz bir sonraki adımda: (1) Bu dört dosyayı tek bir “ALDI BE kaydedilmiş HTML toplu parser” ile işleyecek kısa bir script taslağı, veya (2) Sadece “Yeni ürünler” ve “Sığır eti” için ayrı bir parser örneği çıkarılabilir.
