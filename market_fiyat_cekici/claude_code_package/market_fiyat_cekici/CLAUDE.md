# Platform Avrupa — Market Fiyat Çekici

## Proje Amacı
Belçika'daki 5 büyük market zincirinin (Colruyt, ALDI, Lidl, Delhaize, Carrefour)
tüm ürün fiyatlarını ve indirim tarihlerini haftalık olarak çekip
Supabase veritabanına kaydetmek.

## Klasör Yapısı
```
market_fiyat_cekici/
├── CLAUDE.md                    ← Bu dosya (talimatlar)
├── .env                         ← Supabase bilgileri (oluşturulacak)
├── .env.example                 ← Örnek .env
├── requirements.txt             ← Python bağımlılıkları
├── supabase_market_schema.sql   ← Supabase'e yüklenecek SQL
├── main.py                      ← Ana çalıştırıcı
├── colruyt_scraper.py           ← Colruyt BE scraper
├── aldi_scraper.py              ← ALDI BE scraper
├── lidl_scraper.py              ← Lidl BE scraper
├── delhaize_scraper.py          ← Delhaize BE scraper
└── carrefour_scraper.py         ← Carrefour BE scraper
```

## Görev Sırası (Claude Code bunu takip et)

### ADIM 1 — Ortamı hazırla
```bash
pip install -r requirements.txt
playwright install chromium
```

### ADIM 2 — .env dosyasını oluştur
Kullanıcıdan şunları iste:
- SUPABASE_URL (Supabase Dashboard > Settings > API > Project URL)
- SUPABASE_SERVICE_KEY (Settings > API > service_role key — anon key DEĞİL)

.env dosyası formatı:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### ADIM 3 — SQL tablosunu kontrol et
Kullanıcıya söyle:
"Supabase Dashboard > SQL Editor'a gir, supabase_market_schema.sql
dosyasının içeriğini yapıştır ve çalıştır."

Sonra bağlantıyı test et:
```bash
python main.py --test
```

### ADIM 4 — Colruyt'u test et (İLK MARKET)
```bash
python main.py --market colruyt
```

Beklenen çıktı: ürün sayıları kategori kategori loglanacak.
Hata olursa düzelt ve tekrar dene.

### ADIM 5 — ALDI'yi test et
```bash
python main.py --market aldi
```

### ADIM 6 — Lidl'i test et
```bash
python main.py --market lidl
```

### ADIM 7 — Delhaize'yi test et
```bash
python main.py --market delhaize
```

### ADIM 8 — Carrefour'u test et
```bash
python main.py --market carrefour
```

### ADIM 9 — Tümünü çalıştır
```bash
python main.py
```

## Önemli Notlar

### Hata Çözümleri
- **HTTP 403**: Market botu tespit etti. İlgili scraper'da `human_delay`
  değerlerini artır (min 5s, max 15s yap).
- **HTTP 429**: Rate limit. 120s bekle, sonra tekrar dene.
- **"table does not exist"**: SQL henüz Supabase'e yüklenmemiş.
- **"Invalid API key"**: .env'deki key anon key — service_role key lazım.
- **Playwright hatası**: `playwright install chromium` tekrar çalıştır.

### Scraper Mimarisi
Her scraper şu alanları Supabase'e yazar:
```
chain_slug, country_code, product_code, name, brand,
category, price, currency, in_promo, promo_price,
promo_valid_from, promo_valid_until, image_url, captured_at
```

Unique constraint: `chain_slug + product_code`
Yani aynı ürün tekrar çekilirse UPDATE olur, yeni kayıt açılmaz.

### Colruyt Özel Not
Colruyt anti-bot koruması var. Playwright ile headless browser
açılıyor, session alınıyor, sonra API çağrılıyor.
X-CG-APIKEY değişirse colruyt_scraper.py içinde güncelle.

### Ban Riski Minimizasyonu
- Her market arasında 30-90 saniye bekleme var (main.py içinde)
- Her sayfa arasında 2-8 saniye rastgele bekleme var
- User-Agent rotasyonu var (Delhaize, Carrefour için)
- Haftada 1 kez çalıştır (GitHub Actions Salı 03:00)

## Supabase Tablo Yapısı
Ana tablo: `market_chain_products`
View: `market_chain_products_stats` (market.html bunu kullanır)

## GitHub Actions
.github/workflows/market_scraper.yml dosyası:
- Her Salı 03:00 UTC'de otomatik çalışır
- GitHub Secrets'a SUPABASE_URL ve SUPABASE_SERVICE_KEY ekle
- Elle de çalıştırılabilir (Actions > Run workflow)
