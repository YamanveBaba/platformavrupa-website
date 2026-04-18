# Plan: ALDI Ana Sayfa Teklifleri + Geçerlilik Tarihi + 1880 Ürünle Eşleştirme

## Amaç

1. **Ana sayfadaki** “Bu haftaki tüm teklifleri göster” ile açılan sayfadan indirimli ürünleri çekmek (ürün adı, eski fiyat, indirimli fiyat, indirim %, **geçerli olduğu tarih**).
2. Bu teklifleri **tarih başlıklarına** göre kaydetmek (örn. “13.03 tarihinden itibaren”, “16.03 tarihinden itibaren”).
3. Çektiğimiz **1880 ürünlük** assortiment listesiyle **eşleştirip** hangi ürünlerin bu hafta indirimde olduğunu, indirimli fiyatını ve geçerlilik tarihini işaretlemek.

---

## Adım 1: Teklifler sayfasına ulaşma

- **Seçenek A:** Ana sayfa `https://www.aldi.be/nl/` açılır, mavi düğme **“Bekijk alle aanbiedingen van deze week”** (veya TR’de “Bu haftaki tüm teklifleri göster”) bulunup tıklanır; açılan sayfa teklifler sayfasıdır.
- **Seçenek B:** Doğrudan teklifler URL’si kullanılır (ALDI BE’de genelde `aanbiedingen.html` veya `aanbiedingen-deze-week.html` benzeri). Önce A denenir; buton selector’ı veya link hedefi loglanarak kalıcı URL çıkarılır.

**Çıktı:** Teklifler sayfasının nihai URL’si (ileride doğrudan bu URL’den başlamak için).

---

## Adım 2: Teklifler sayfasında veri yapısını çıkarma

Sayfada görünen yapı (resimden ve tarifinden):

- **Üst banner:** “16/03 Pazartesi – 21/03 Cumartesi” gibi genel hafta aralığı (opsiyonel kayıt).
- **Tarih başlıkları:** “13.03 tarihinden itibaren”, “16.03 tarihinden itibaren”, “18.03 tarihinden itibaren” gibi başlıklar; her biri bir **geçerlilik başlangıç tarihi** (validFrom).
- **Ürün kartları:** Her kartta:
  - Ürün adı
  - Eski fiyat (çizgili)
  - İndirimli fiyat
  - İndirim oranı (örn. -35%, 2º -50%, 1+1 GRATIS)
  - Birim fiyat (opsiyonel)
  - Bazı ürünlerde dipnot: “*Geçerlilik tarihi: 20/03 - 26/03” gibi **farklı geçerlilik** (validFrom–validTo) olabilir.

Yapılacak iş:

- Sayfa DOM’u incelenir (Playwright ile açılıp selector’lar tespit edilir veya sen “Teklifler” sayfasını kaydedip bir örnek HTML verirsin).
- Her **tarih başlığı** için `validFrom` (örn. 13.03.2026) parse edilir.
- Her **ürün kartı** için: `productName`, `originalPrice`, `promoPrice`, `discountLabel` (örn. “-35%”, “2+3 GRATIS”), `validFrom` (başlıktan veya karttaki dipnottan) çıkarılır.
- Mümkünse karttaki **ürün linki** veya **productID** (varsa) alınır; eşleştirmede kullanılır.

**Çıktı:** `aldi_be_teklifler_YYYY-MM-DD.json`:

```json
{
  "kaynak": "ALDI Belçika - Bu haftanın teklifleri",
  "hafta_araligi": "16.03 - 21.03.2026",
  "cekilme_tarihi": "...",
  "teklifler": [
    {
      "validFrom": "16.03.2026",
      "validTo": null,
      "productName": "Kipfilet à la minute",
      "originalPrice": 7.79,
      "promoPrice": 5.00,
      "discountLabel": "-35%",
      "quantity": "600 g",
      "productUrl": "..."
    }
  ]
}
```

---

## Adım 3: Assortiment listesi (1880 ürün) ile eşleştirme

- **Girdi 1:** Adım 2’den gelen `aldi_be_teklifler_*.json`.
- **Girdi 2:** Mevcut `aldi_be_tum_yeme_icme_*.json` (1880 ürün; `productID`, `productName`, `priceWithTax`, `brand`, `category` vb.).

Eşleştirme mantığı:

1. **Öncelik 1:** Teklifler sayfasında **productID** veya ürün detay linkinden ID varsa, assortiment’taki `productID` ile birebir eşle.
2. **Öncelik 2:** Yoksa **ürün adı** ile eşle: normalize et (küçük harf, tire/boşluk birleştir, Türkçe/Felemenkçe karakterleri düzelt), assortiment’taki `productName` ile karşılaştır; en iyi eşleşen (örn. tam eşleşme veya kelime benzerliği yüksek) kayıt seçilir.
3. Eşleşen her assortiment ürününe şu alanlar eklenir (veya ayrı “indirimde olanlar” listesi üretilir):
   - `inPromotion`: true  
   - `promoPrice`, `promoValidFrom` (ve varsa `promoValidTo`)  
   - `promoDiscountLabel` (örn. “-35%”)  
   - `originalPrice` (teklifteki eski fiyat)

**Çıktı seçenekleri:**

- **A)** Zenginleştirilmiş tam liste: `aldi_be_tum_yeme_icme_zengin_*.json` (1880 ürün; indirimde olanlarda ek alanlar dolu).
- **B)** Sadece eşleşenler: `aldi_be_indirimde_olanlar_*.json` (sadece bu hafta teklifte olan ürünler, assortiment bilgisi + teklif bilgisi + geçerlilik tarihi).
- **C)** İkisi de: (A) tam liste, (B) özet rapor.

---

## Adım 4: Çalıştırma sırası (önerilen akış)

1. **Önce teklifler:**  
   Yeni script: “Ana sayfayı aç → mavi düğmeye tıkla (veya doğrudan teklifler URL’si) → tarih başlıklarını + ürün kartlarını parse et → `aldi_be_teklifler_*.json` yaz.”
2. **Sonra (isteğe bağlı) assortiment:**  
   Mevcut `aldi_tum_yeme_icme_cek.py` ile tam liste yeniden çekilebilir; veya elindeki en güncel `aldi_be_tum_yeme_icme_*.json` kullanılır.
3. **Eşleştirme script’i:**  
   `aldi_be_teklifler_*.json` + `aldi_be_tum_yeme_icme_*.json` → eşleştir → (A) ve/veya (B) çıktıları üret.

İstersen 2 ve 3 tek komutda da birleştirilebilir: “önce teklifleri çek, sonra en son assortiment JSON’unu bul, eşleştir, raporu yaz.”

---

## Teknik notlar

- **Dil:** Ana sayfa/sayfa NL (Felemenkçe) olabilir; buton metni “Bekijk alle aanbiedingen van deze week” gibi. TR ekran “Bu haftaki tüm teklifleri göster” ise tarayıcı dili veya site dil seçimine bağlıdır; selector’lar metin yerine class/aria/data attribute ile yazılırsa dil değişse de çalışır.
- **Dinamik yükleme:** Teklifler sayfası da lazy load kullanıyorsa, bira script’indeki gibi “azar azar kaydır + her adımda kartları topla” mantığı uygulanır.
- **Geçerlilik:** Bir üründe hem “16.03’ten itibaren” hem dipnotta “20/03–26/03” varsa, ikisi de saklanır; eşleştirme çıktısında `validFrom` / `validTo` net gösterilir.

---

## Senden istenen (uygulamaya geçerken)

1. **Teklifler sayfası HTML’i (opsiyonel ama hızlılaştırır):**  
   “Bu haftaki tüm teklifleri göster”e tıkladıktan sonra açılan sayfayı **Ctrl+S** ile kaydedip (veya Elements’ten ilgili bölümü kopyalayıp) bir kere paylaşırsan, tarih başlığı ve ürün kartı için doğru selector’ları tek seferde yazabilirim.
2. **Tercih:** Çıktı olarak sadece “indirimde olanlar” (B) mi, yoksa “1880 ürün + indirim bilgisi eklenmiş tam liste” (A) mi, yoksa ikisi de mi istiyorsun?

Bu plan onayından sonra sırayla: (1) teklifler sayfası scraper’ı, (2) eşleştirme script’i yazılabilir.
