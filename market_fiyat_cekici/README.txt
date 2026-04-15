MARKET FİYAT ÇEKİCİ - ALDI Belçika
=========================================

İlk kez kullanıyorsanız:
  → KURULUM_VE_KULLANIM.md dosyasını açın ve adımları sırayla uygulayın.

TAM FİYAT LİSTESİ (platform: arama/karşılaştırma):
  → calistir_aldi_tum_yeme_icme.bat — tüm ürünler (5-15 dk).
  → Sonra teklifleri birleştirince: cikti/aldi_be_tum_urunler_platform_*.json

BU HAFTANIN TEKLİFLERİ (indirim listesi + geçerlilik tarihi):
  1) Tarayıcıda "Bu haftanın fırsatları" sayfasını Ctrl+S ile kaydedin.
  2) python parse_aldi_teklifler_html.py "Downloads\Bu haftanın fırsatları – ALDI Belçika.html"
  3) python merge_teklifler_with_assortiment.py
  → cikti/aldi_be_indirimde_olanlar_*.json (ayrı yayın için)
  → cikti/aldi_be_tum_urunler_platform_*.json (tüm fiyatlar + indirim bilgisi)

Kısa yol: calistir_teklifler_parse_ve_birlestir.bat (HTML yolunu düzenleyin)

Detay: PLATFORM_VERI_KULLANIMI.md

Platform Avrupa - www.platformavrupa.com
