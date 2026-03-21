Colruyt — Tam otomatik çekim (Playwright)
========================================

Önemli: Hiçbir site "sıfır tıklama / sıfır oturum" ile kişisel veriyi vermez.
Colruyt için en az iş: BİR KEZ tarayıcıda giriş.

Nasıl kullanılır?
-----------------
1) pip install -r requirements.txt
2) python -m playwright install chromium
3) calistir_colruyt_otomatik.bat çift tıkla

İlk çalıştırma:
- Chromium penceresi açılır.
- 90 saniye içinde colruyt.be'de giriş yapın ve mağazanızı seçin (gerekliyse).
- Süre bitince script otomatik "daha fazla ürün"e tıklamaya başlar.
- Ürünler Network'ten API ile toplanır (product-search-prs).

Sonraki çalıştırmalar:
- Giriş bilgisi "colruyt_browser_profile" klasöründe kalır.
- Genelde tekrar giriş gerekmez; script kısa bekleyip devam eder.

Çıktı:
- cikti/colruyt_be_playwright_YYYY-MM-DD_HH-MM.json

İsteğe bağlı (daha uzun ilk bekleme):
- python colruyt_playwright_otomatik_cek.py --bekle-ilk-sn 120

Not: curl.txt / token.txt bu yöntemde ZORUNLU DEĞİL.
