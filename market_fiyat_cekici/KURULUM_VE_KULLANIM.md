# Market Fiyat Çekici – Kurulum ve Kullanım Rehberi

Bu rehber, kod yazmadan bilgisayarınızda ALDI Belçika bira fiyatlarını otomatik çekmeniz için gereken her adımı anlatır. Sırayla yapmanız yeterli.

**Önemli:** Komut İstemi (siyah pencere) açıldığında, rehberde gördüğünüz komutları **aynen** yazın. ` ```text ` veya ` ``` ` gibi işaretler rehberin formatıdır; bunları **yazmayın**. Sadece komut satırını (örn. `python --version`) yazıp Enter’a basın.

---

## Bölüm 1: Python Kurulumu (Bir kez yapılır)

Python, script’in çalışması için gereken programdır. Ücretsizdir.

### Adım 1.1 – Python’u indirin

1. İnternet tarayıcınızı açın.
2. Adres çubuğuna şunu yazın: **https://www.python.org/downloads/**
3. Enter’a basın.
4. Sarı **“Download Python 3.x.x”** butonuna tıklayın (sürüm numarası değişebilir).
5. İndirilen dosya genelde **İndirilenler** klasörünüzde olur (`python-3.x.x-amd64.exe` gibi).

### Adım 1.2 – Python’u kurun

1. İndirdiğiniz dosyaya çift tıklayın.
2. İlk ekranda **en altta** şu seçeneği mutlaka işaretleyin:
   - **“Add python.exe to PATH”** (veya “Add Python to PATH”)
3. Sonra **“Install Now”** (Şimdi Yükle) butonuna tıklayın.
4. Kurulum bitene kadar bekleyin.
5. **“Close”** (Kapat) ile kapatın.

### Adım 1.3 – Kurulumu kontrol edin

1. **Windows tuşu + R** ile “Çalıştır” penceresini açın.
2. **cmd** yazıp Enter’a basın. Siyah/beyaz bir pencere (Komut İstemi) açılacak.
3. Komut satırına **sadece** şunu yazıp Enter’a basın:

   **python --version**

4. Örneğin `Python 3.12.0` gibi bir satır görüyorsanız kurulum doğrudur.  
   “python tanınmıyor” gibi bir hata alırsanız: Python’u kaldırıp tekrar kurun ve **“Add Python to PATH”** kutusunu işaretleyin.

---

## Bölüm 2: Script Klasörünü Bulma

1. **Bu dosyanın bulunduğu klasör** şudur:
   - Projenizin içindeki **market_fiyat_cekici** klasörü.
   - Örnek tam yol: `C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici`
2. Bu klasörün içinde şunlar olmalı:
   - `aldi_bier_cek.py`
   - `calistir_aldi_bier.bat`
   - `requirements.txt`
   - `KURULUM_VE_KULLANIM.md` (bu dosya)

---

## Bölüm 2b: Beş zincir (geliştirici) — ortam ve gizli dosyalar

- **Python paketleri:** Komut İstemi’nde `market_fiyat_cekici` içindeyken: `pip install -r requirements.txt` ve `playwright install chromium`.
- **İsteğe bağlı sanal ortam:** `python -m venv .venv` → `.venv\Scripts\activate` → aynı `pip install` komutları.
- **Supabase:** `supabase_import_secrets.txt` (1. satır Project URL, 2. satır service_role). Git’e eklenmez.
- **Ortak yükleme:** `python json_to_supabase_yukle.py --dry-run "cikti\....json"` ile format kontrolü; otomasyon: `--no-pause`.
- **JSON üst alanları (önerilen):** `kaynak`, `cekilme_tarihi`, `chain_slug`, `country_code` — `json_to_supabase_yukle.py` format seçiminde kullanılır.
- **Zincir betikleri (Belçika):** Delhaize [`delhaize_be_graphql_cek.py`](delhaize_be_graphql_cek.py), Lidl [`lidl_be_playwright_cek.py`](lidl_be_playwright_cek.py), Carrefour [`carrefour_be_playwright_cek.py`](carrefour_be_playwright_cek.py). Haftalık toplu: `haftalik_*_supabase.py` ve `calistir_*_haftalik.bat` dosyalarına bakın.
- **Gizli / yerel:** `delhaize_cookie.txt`, `playwright_user_data/` Git’e eklenmez (`.gitignore`).

Pilot ülke (NL) şablonu: [`PILOT_ULKE_NL_SABLON.md`](PILOT_ULKE_NL_SABLON.md).

---

## Bölüm 3: Playwright Kurulumu (Bir kez yapılır)

Playwright, script’in ALDI sayfasını açıp veri çekmesini sağlayan kütüphanedir. Ücretsizdir.

### Adım 3.1 – Komut İstemi’ni açın

1. **Windows tuşu + R** tuşlarına basın.
2. **cmd** yazıp Enter’a basın.

### Adım 3.2 – Script klasörüne gidin

1. Komut İstemi’nde **sadece** şunu yazın (kendi bilgisayarınıza göre yolu değiştirin), sonra Enter’a basın:

   **cd C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici**

2. Enter’a basın.  
   Artık komutlar bu klasör için çalışacak.

### Adım 3.3 – Playwright’ı yükleyin

1. **Sadece** şunu yazıp Enter’a basın:

   **pip install playwright**

2. “Successfully installed” gibi bir mesaj gelene kadar bekleyin.
3. Sonra **sadece** şunu yazıp Enter’a basın:

   **playwright install chromium**

4. Chromium (tarayıcı motoru) indirilip kurulacak. Bitene kadar bekleyin.

Bu adımlar tamamlandıysa kurulum bitti demektir. Bir daha yapmanız gerekmez.

---

## Bölüm 4: Fiyatları Çekmek (Her kullanımda)

İki script var:

| Ne çekmek istiyorsunuz?      | Hangi dosya?                         | Süre    |
|-----------------------------|--------------------------------------|--------|
| Sadece **bira**             | **calistir_aldi_bier.bat**           | ~1–2 dk |
| **Tüm yeme-içme** kategorileri | **calistir_aldi_tum_yeme_icme.bat** | ~5–15 dk |
| **Colruyt** tüm ürün+fiyat (API) | **calistir_colruyt_api.bat**       | uzun (insan benzeri bekleme) |
| **Colruyt** tam otomatik (tarayıcı) | **calistir_colruyt_otomatik.bat** | Playwright; curl/token gerekmez; ilk seferde giriş |
| **Delhaize** GraphQL | **calistir_delhaize_haftalik.bat** veya `python delhaize_be_graphql_cek.py` | `cikti/delhaize_be_producten_*.json` |
| **Lidl BE** Playwright | **calistir_lidl_be.bat** / **calistir_lidl_haftalik.bat** | `cikti/lidl_be_producten_*.json` |
| **Carrefour BE** Playwright | **calistir_carrefour_be.bat** / **calistir_carrefour_haftalik.bat** | Kalıcı profil; ilk sefer `--headed` önerilir |
| **JSON → Supabase** | **calistir_supabase_yukle.bat** | `supabase_import_secrets.txt`; ALDI, Colruyt, Delhaize, Lidl, Carrefour `cikti/*.json` |

İki yöntem var. İstediğinizi kullanın.

### Yöntem A – Çift tıklama (en kolay)

1. **market_fiyat_cekici** klasörünü açın.
2. **calistir_aldi_bier.bat** dosyasına çift tıklayın.
3. Siyah pencerede şunlar görünecek:
   - “ALDI Belçika - Bira fiyatları çekiliyor...”
   - “Sayfa yüklendi. Ürünler yükleniyor...”
   - “Tamamlandı. XX ürün kaydedildi.”
4. Pencerede “Çıkmak için Enter’a basın” yazınca Enter’a basarak kapatın.

### Yöntem B – Komut satırından

1. **Windows + R** → **cmd** → Enter.
2. Klasöre gidin (**sadece** şu satırı yazın):

   **cd C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici**

3. Sonra **sadece** şunu yazıp Enter’a basın:

   **python aldi_bier_cek.py**

4. Bittiğinde pencerede yazan “Dosya: ...” satırındaki konum, sonucun kaydedildiği yerdir.

---

## Bölüm 5: Sonuç Dosyasını Bulma

1. **market_fiyat_cekici** klasörünün içinde **cikti** adlı bir klasör oluşur.
2. **cikti** klasörünü açın.
3. İçinde şu tip dosyalar görürsünüz:
   - **aldi_be_bier_2026-02-24_14-30.json** (tarih ve saat sizin çalıştırma anınıza göre değişir)
4. Bu dosyayı:
   - Not Defteri veya VS Code ile açıp inceleyebilirsiniz,
   - Platforma yükleyebilirsiniz,
   - İleride Excel’e aktaran bir araçla kullanabilirsiniz.

Dosyanın içinde ürün adı, marka, fiyat (priceWithTax), indirimde mi (inPromotion) gibi bilgiler JSON formatında durur.

---

## Bölüm 5b: Bu Haftanın Teklifleri (İndirim Listesi + Platform Listesi)

Platformda hem **tüm fiyatlar** (arama/karşılaştırma) hem de **indirimde olanlar** listesinin ayrı yayınlanması için iki ek script kullanılır.

### Gereken ek paket

Komut İstemi’nde script klasöründeyken **bir kez** şunu yazın:

**pip install beautifulsoup4**

### Adımlar

1. **Tam ürün listesini** daha önce çekmiş olun (calistir_aldi_tum_yeme_icme.bat).  
   Çıktı: **cikti/aldi_be_tum_yeme_icme_....json**

2. Tarayıcıda ALDI Belçika **“Bu haftanın fırsatları”** sayfasını açın:  
   https://www.aldi.be/nl/onze-aanbiedingen.html  
   Sayfayı **Ctrl+S** ile kaydedin (örn. İndirilenler’e: **Bu haftanın fırsatları – ALDI Belçika.html**).

3. Teklifleri HTML’den çıkarın (yolu kendi bilgisayarınıza göre düzenleyin):

   **python parse_aldi_teklifler_html.py "C:\Users\yaman\Downloads\Bu haftanın fırsatları – ALDI Belçika.html"**

   Çıktı: **cikti/aldi_be_teklifler_....json**

4. Teklifleri tam liste ile birleştirin:

   **python merge_teklifler_with_assortiment.py**

   Bu komut iki dosya üretir:
   - **aldi_be_tum_urunler_platform_....json** → Platforma yüklenecek **tüm ürün fiyatları** (indirimde olanlarda promo alanları dolu).
   - **aldi_be_indirimde_olanlar_....json** → Ayrı yayın için **sadece indirimde olanlar** (geçerlilik tarihiyle).

Detaylı açıklama: **PLATFORM_VERI_KULLANIMI.md** dosyasında.

---

## Bölüm 5c: Colruyt Belçika – API ile ürün + fiyat çekimi

Colruyt’ın product-search-prs API’si ile tüm ürünlerin fiyatları çekilir. Script **insan benzeri** aralıklarla istek atar (bazen yavaş, nadiren uzun mola); süre uzun sürebilir, ban riski düşüktür.

### Gereken paket

Komut İstemi’nde script klasöründeyken **bir kez**:

**pip install requests**

### Nasıl çalıştırılır

1. **calistir_colruyt_api.bat** dosyasına çift tıklayın **veya**
2. Komut İstemi’nde: **python colruyt_product_search_api_cek.py**

### Çıktı

- **cikti/colruyt_be_producten_YYYY-MM-DD_HH-MM.json**  
  İçinde: kaynak, çekim tarihi, ürün sayısı, her ürün için ad, marka, basicPrice, inPromo, activationDate, kategori vb.

### placeId değiştirmek

Kendi mağazanız farklıysa, **colruyt_product_search_api_cek.py** dosyasını Not Defteri ile açın; en üstteki `CONFIG` içinde **"place_id": "762"** satırındaki sayıyı tarayıcıda gördüğünüz placeId ile değiştirin.

### 401 / 406 alırsanız – Token veya Cookie

API oturum isteyebilir. **A) Token:** Script ile aynı klasörde **token.txt** oluşturup içine ya sadece token string'ini ya da `{"token": "...", "renewInSec": 376, "cookieDomain": ".colruyt.be"}` JSON'unu yapıştırın; script otomatik kullanır. (Token süresi kısa, süresi dolunca yenileyin; örnek: **token_ornek.txt**.) **B) Cookie:** Tarayıcıda colruyt.be'ye giriş yapıp Network'te product-search-prs isteğindeki **Cookie** değerini **cookie.txt**'e veya cURL'ü **curl.txt**'e yapıştırın. Tarayıcıda colruyt.be’ye giriş yapıp, Geliştirici Araçları → Network’te product-search-prs isteğine tıklayıp **Request Headers** içindeki **Cookie** değerini kopyalayın. Script’te `API_HEADERS` içine `"Cookie": "buraya yapıştır"` ekleyin (tek satır, tırnak içinde).

---

## Bölüm 5d: Çekilen veriyi Supabase’e kaydetme (platform hedefi)

**Karar:** Ürün + fiyatlar **`cikti/*.json`** ile doğrulandıktan sonra canlı sitede **Supabase** tablosu **`market_chain_products`** içinde tutulur (haftalık `upsert`). Ayrıntı: **`PLATFORM_VERI_KULLANIMI.md`** ve ana doküman **`PLATFORMAVRUPA_PROJE_DOKUMANTASYONU.md`**.

1. Supabase → **SQL Editor** → **`supabase_market_chain_products.sql`** dosyasının içeriğini yapıştırıp çalıştırın.  
2. **Service role** anahtarını yalnızca laptop’ta kullanın: **`supabase_import_secrets_ORNEK.txt`** dosyasına bakıp aynı klasörde **`supabase_import_secrets.txt`** oluşturun (1. satır Project URL, 2. satır service_role). Bu dosya **Git’e eklenmez** (`.gitignore`).  
3. Yükleme: **`calistir_supabase_yukle.bat`** veya `python json_to_supabase_yukle.py` — `cikti/` içinde sırayla aranır: **`aldi_be_tum_urunler_platform_*.json`** → **`aldi_be_tum_yeme_icme_*.json`** → **`colruyt_be_*.json`** → **`delhaize_be_producten_*.json`** → **`lidl_be_producten_*.json`** → **`carrefour_be_producten_*.json`** (her grupta en yeni dosya). Belirli dosya: `python json_to_supabase_yukle.py "cikti\\dosya.json"`. Görev Zamanlayıcı / otomasyon için Enter beklemeden bitirmek: **`--no-pause`**.  
4. Önce deneme: `python json_to_supabase_yukle.py --dry-run "cikti\\..."` veya otomatik seçimle: `python json_to_supabase_yukle.py --dry-run --no-pause`  
5. `market.html` tarafında sorgu: `from('market_chain_products').select(...)` ile **salt okunur** (anon key).

---

## Bölüm 6: Gece Otomatik Çalıştırma (İsteğe bağlı)

Script’i her Pazar gece 02:00’de kendiliğinden çalıştırmak isterseniz:

### Adım 6.1 – Görev Zamanlayıcı’yı açın

1. **Windows tuşu**na basın.
2. Arama kutusuna **Görev Zamanlayıcı** veya **Task Scheduler** yazın.
3. **Görev Zamanlayıcı** uygulamasını açın.

### Adım 6.2 – Yeni görev oluşturun

1. Sağ tarafta **“Temel Görev Oluştur”** (Create Basic Task) tıklayın.
2. **Ad:** Örneğin “ALDI Bira Fiyat Cek” yazın. İleri.
3. **Tetikleyici:** “Günlük” veya “Haftalık” seçin. İleri.
4. **Başlangıç:** Örneğin Pazar 02:00. İleri.
5. **Eylem:** “Program başlat” seçin. İleri.
6. **Program/komut** alanına şunu yazın (kendi kullanıcı adınıza göre düzeltin):

   **C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici\calistir_aldi_bier.bat**

7. **Başlangıç konumu** (isteğe bağlı) alanına:

   **C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici**
8. İleri → Son.

### Önemli

- Gece çalışması için **bilgisayar o saatte açık** olmalı (veya uykuya geçmemeli).
- İsterseniz “Bilgisayar açıldığında çalıştır” gibi tetikleyici de seçebilirsiniz.

---

## Ban (Engellenme) Riski Var mı?

- **Haftada bir** veya **günde bir** çalıştırıyorsanız, tek kişi sayfayı geziyormuş gibi görünür; risk **düşük** kabul edilir.
- Risk, aynı siteden **dakikada çok sayfa** taramak veya **çok sık** tekrarlamakla artar.
- **Öneri:** Tüm yeme-içme script’ini günde en fazla 1–2 kez, mümkünse haftada bir çalıştırın. Gece Zamanlayıcı ile haftada bir çalıştırmak genelde güvenli sayılır.

---

## Sık Karşılaşılan Sorunlar

### “python tanınmıyor” / “pip tanınmıyor”

- Python’u tekrar kurun ve **“Add Python to PATH”** kutusunu işaretleyin.
- Kurulumdan sonra **Komut İstemi’ni kapatıp yeniden açın** ve tekrar deneyin.

### “playwright yüklü değil”

- Komut İstemi’nde script klasöründeyken şunları **sırayla** yazın (her birinden sonra Enter):
  - **pip install playwright**
  - **playwright install chromium**

### “8 ürün çıktı, 25 bekliyordum”

- Script sayfayı zaten birkaç kez kaydırıyor. Bazen site yavaş yanıt verir.
- İnternet bağlantınızı kontrol edin ve script’i tekrar çalıştırmayı deneyin.
- ALDI sayfası yapısını değiştirdiyse, script’in güncellenmesi gerekebilir.

### Pencere hemen kapanıyor

- **calistir_aldi_bier.bat** kullanıyorsanız, script sonunda “Enter’a basın” diye bekler; hata olsa bile pencere kapanmadan önce mesajı okuyabilirsiniz.
- Hata mesajını not alıp destek alırken paylaşın.

---

## Özet Kontrol Listesi

- [ ] Python kuruldu ve “Add Python to PATH” işaretlendi.
- [ ] Komut İstemi’nde `python --version` çalışıyor.
- [ ] `market_fiyat_cekici` klasörüne `cd` ile girdim.
- [ ] `pip install playwright` ve `playwright install chromium` çalıştırıldı.
- [ ] `calistir_aldi_bier.bat` ile veya `python aldi_bier_cek.py` ile script çalıştı.
- [ ] **cikti** klasöründe **aldi_be_bier_...json** dosyası oluştu.

Hepsi tamamsa kurulum ve ilk kullanım tamam demektir. İleride başka marketler (Lidl, Rewe vb.) için benzer script’ler eklenebilir; onların da kurulumu aynı klasör ve aynı Python/Playwright üzerinden yapılır.
