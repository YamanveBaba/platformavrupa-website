Colruyt — Tam otomatik çekim (Playwright)
========================================

Önemli: Hiçbir site "sıfır tıklama / sıfır oturum" ile kişisel veriyi vermez.
Colruyt için en az iş: BİR KEZ tarayıcıda giriş.

Nasıl kullanılır?
-----------------
1) pip install -r requirements.txt
2) python -m playwright install chromium
3) calistir_colruyt_otomatik.bat çift tıkla
   (BAT dosyası --enter-sonra-devam kullanır: giriş bitince CMD penceresinde Enter'a basın.)

İlk çalıştırma:
- Chromium penceresi açılır.
- colruyt.be'de giriş + mağaza seçin.
- Bittiğinde siyah CMD penceresine dönüp Enter'a basın (süre sınırı yok).
- Sonra script "daha fazla ürün"e tıklamaya başlar.

Süreli bekleme (Enter istemezseniz):
- python colruyt_playwright_otomatik_cek.py --bekle-ilk-sn 600

Zaten giriş yaptığınız profille hızlı:
- python colruyt_playwright_otomatik_cek.py --hizli-profil
- Ürünler Network'ten API ile toplanır (product-search-prs).

Sonraki çalıştırmalar:
- Giriş bilgisi "colruyt_browser_profile" klasöründe kalır.
- Genelde tekrar giriş gerekmez; script kısa bekleyip devam eder.

Çıktı:
- cikti/colruyt_be_playwright_YYYY-MM-DD_HH-MM.json

İsteğe bağlı (ilk giriş için süreyi kendin vermek):
- python colruyt_playwright_otomatik_cek.py --bekle-ilk-sn 600

Not: curl.txt / token.txt bu yöntemde ZORUNLU DEĞİL.
