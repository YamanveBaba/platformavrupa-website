# -*- coding: utf-8 -*-
"""
ALDI Belçika - Bira sayfası fiyat çekici
Platform Avrupa - Market Fiyat Modülü
Tüm ürünleri yüklemek için sayfayı kaydırır, sonra fiyatları JSON'a yazar.
"""

import json
import os
from datetime import datetime

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: Playwright yüklü değil.")
        print("Lütfen kurulum rehberindeki adımları uygulayın.")
        print("Özet: Komut satırında şunu yazın:  pip install playwright")
        print("Sonra:  playwright install chromium")
        input("\nÇıkmak için Enter'a basın...")
        return

    # Çıktı klasörü (script ile aynı yerde 'cikti' klasörü)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    url = "https://www.aldi.be/nl/producten/assortiment/alcoholische-dranken/bier.html"
    print("ALDI Belçika - Bira fiyatları çekiliyor...")
    print("Sayfa açılıyor:", url)

    with sync_playwright() as p:
        # Tarayıcıyı başlat (penceresi görünmez - arka planda çalışır)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Sayfaya git
            page.goto(url, wait_until="networkidle", timeout=60000)
            print("Sayfa yüklendi. Ürünler yükleniyor (sayfa kaydırılıyor)...")

            # Her kaydırmada gördüğümüz ürünleri topla (lazy load / sanal liste için)
            # Böylece DOM'da aynı anda az kart olsa bile hepsini biriktiririz
            products_by_id = {}

            def collect_visible_products():
                tiles = page.query_selector_all('[data-article]')
                for tile in tiles:
                    try:
                        raw = tile.get_attribute("data-article")
                        if not raw:
                            continue
                        json_str = raw.replace("&quot;", '"')
                        data = json.loads(json_str)
                        info = data.get("productInfo") or {}
                        cat = data.get("productCategory") or {}
                        pid = info.get("productID")
                        if not pid:
                            continue
                        products_by_id[pid] = {
                            "productID": pid,
                            "productName": info.get("productName", ""),
                            "brand": info.get("brand", ""),
                            "priceWithTax": info.get("priceWithTax"),
                            "inPromotion": info.get("inPromotion", False),
                            "category": cat.get("primaryCategory", ""),
                        }
                    except (json.JSONDecodeError, TypeError):
                        continue

            # İlk yüklemede görünenleri al
            page.wait_for_timeout(3000)
            collect_visible_products()

            # Azar azar aşağı kaydır: biraz kaydır → oku → biraz daha kaydır → oku (sonuna kadar)
            # Böylece her ekrandaki ürünler DOM'dayken toplanır (tam alta zıplamıyoruz)
            scroll_adim_piksel = 500
            adim = 0
            while True:
                adim += 1
                # Bir ekran kadar aşağı kaydır
                reached_bottom = page.evaluate(
                    f"""
                    () => {{
                        const step = {scroll_adim_piksel};
                        window.scrollBy(0, step);
                        const atBottom = (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 10;
                        return atBottom;
                    }}
                    """
                )
                page.wait_for_timeout(1200)
                collect_visible_products()
                n = len(products_by_id)
                if adim % 5 == 0 or reached_bottom:
                    print(f"  Adım {adim} — şu ana kadar {n} ürün toplandı.")
                if reached_bottom:
                    break
                if adim > 80:
                    print("  Maksimum kaydırma sayısına ulaşıldı, duruluyor.")
                    break

            # En alta bir kez daha gidip son ürünleri topla
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            collect_visible_products()

            products = list(products_by_id.values())
            print(f"Toplam toplanan benzersiz ürün: {len(products)}")

            browser.close()

            # Tarihli dosya adı
            tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
            dosya_adi = f"aldi_be_bier_{tarih}.json"
            dosya_yolu = os.path.join(cikti_dir, dosya_adi)

            # Meta bilgi ile kaydet
            cikti = {
                "kaynak": "ALDI Belçika",
                "kategori": "Bira",
                "url": url,
                "cekilme_tarihi": datetime.now().isoformat(),
                "urun_sayisi": len(products),
                "not_fiyat_gecerliligi": "ALDI Belçika fiyatları haftalık broşürle (Pzt-Cumartesi) güncellenir. Bu veri çekim anındaki sitedeki fiyatlardır.",
                "not_indirim": "Her üründe 'inPromotion': true/false vardır. true = kampanya/indirim, false = normal fiyat.",
                "urunler": products,
            }

            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(cikti, f, ensure_ascii=False, indent=2)

            print(f"\nTamamlandı. {len(products)} ürün kaydedildi.")
            print("Dosya:", dosya_yolu)
            print("\nBu dosyayı platforma yükleyebilir veya Excel'e aktarabilirsiniz.")

        except Exception as e:
            browser.close()
            print("HATA:", str(e))
            raise

    input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    main()
