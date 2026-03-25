# Belçika: betiği henüz olmayan üç zincir (Lidl, Delhaize, Carrefour)

Bu dosya, “ne yapacağız?” sorusuna **teknik olmayan** ve **eylem odaklı** cevap verir.

## Gerçek durum

- **ALDI** ve **Colruyt** için repoda Python betikleri ve Supabase yükleme yolu var.
- **Lidl, Delhaize, Carrefour** için henüz aynı seviyede betik yok; her sitenin arayüzü ve koruma (WAF) farklı olduğu için **tek tek** keşif + kod gerekir.

## Ne yapmayacağız

- Sadece “Ctrl+S ile sayfa kaydet” ile tüm ürün+fiyat listesini beklemek (çoğu modern sitede fiyatlar sonradan yüklenir; dosyada çıkmaz).
- `service_role` veya `supabase_import_secrets.txt` içeriğini GitHub’a koymak.

## Ne yapacağız (sırayla)

### 1) Kısa vade: platformu boş bırakmamak

- **Supabase’te** ve **market sayfasında** kullanıcılar en azından **ALDI + Colruyt** fiyat karşılaştırmasını görsün (veri job’ları çalışıyorsa).
- Lidl / Delhaize / Carrefour için: aynı ekranda **broşür / mağaza linkleri** (`market_chains` veya mevcut kartlar) açık kalsın; fiyat satırı o zincirler için **henüz yoksa** arayüzde “fiyat verisi yakında” gibi dürüst bir durum (isteğe bağlı UI metni) — yanıltıcı “karşılaştırma” iddiası vermeyin.

### 2) Orta vade: üç zinciri tek tek “keşif → betik” ile kapatmak

Her zincir için aynı şablon:

1. Chrome’da ilgili **Belçika** sitesinde ürün listesi veya kampanya sayfası açılır.
2. **F12 → Ağ (Network) → Fetch/XHR**; sayfa veya “daha fazla” ile liste yenilenir.
3. **JSON dönen istek** bulunur → sağ tık → **Copy → Copy as cURL (bash)** → metin dosyasına yapıştırılır.
4. Geliştirici (veya Cursor oturumu) bu cURL’e göre `chain_slug` (örn. `lidl_be`) ile Python betiği ve `json_to_supabase_yukle.py` içinde satır eşlemesi yazar.
5. Haftada bir **Windows Görev Zamanlayıcı** ile çalıştırılır (ALDI/Colruyt ile **aynı gün/saatte değil**).

Şablon form: [`ZINCIR_KESIF_SABLONU.md`](ZINCIR_KESIF_SABLONU.md).

### 3) Colruyt’taki gibi API zorlanırsa

- **Playwright** ile gerçek tarayıcı oturumu + ağdan JSON toplama (projede Colruyt için örnek: `colruyt_playwright_otomatik_cek.py`). Aynı kalıp başka siteye uyarlanır; yine geliştirme işi.

### 4) Alternatif (ticari / zaman kazanma)

- Üçüncü parti “fiyat / ürün” API’leri (ücretli olabilir); hukuki lisans ve sözleşme size aittir.

## Özet cümle

Betiği olmayan üç zincir için yapılacak iş: **beklemek değil** — sırayla **keşif çıktısı (cURL/JSON örneği) toplamak** ve her biri için **aynı boru hattına** (JSON → `json_to_supabase_yukle` → `market_chain_products`) bağlamak. Bu, otomatik olarak olmaz; **her zincir için bir geliştirme turu** demektir.
