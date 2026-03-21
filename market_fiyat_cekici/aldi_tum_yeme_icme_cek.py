# -*- coding: utf-8 -*-
"""
ALDI Belçika - Tüm yeme-içme (assortiment) ürünleri fiyat çekici
Platform Avrupa - Market Fiyat Modülü
Assortiment sayfasından kategori linklerini bulur, her kategoride azar azar kaydırıp ürünleri toplar.
"""

import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: Playwright yüklü değil.")
        print("Lütfen: pip install playwright   sonra   playwright install chromium")
        input("\nÇıkmak için Enter'a basın...")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    base_url = "https://www.aldi.be"
    # Assortiment ana sayfası - buradan tüm kategori linkleri toplanacak
    start_url = "https://www.aldi.be/nl/producten/assortiment.html"

    # Assortiment altındaki tüm kategori ve ürün sayfaları (.html)
    link_pattern = re.compile(r"/nl/producten/assortiment[\w\-/]*\.html", re.I)

    print("ALDI Belçika - Tüm yeme-içme ürünleri çekiliyor...")
    print("Kategori linkleri bulunuyor, sonra her sayfa taranacak (uzun sürebilir).\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        products_by_id = {}
        to_visit = [start_url]
        visited = set()
        # Sayfa başına kısa bekleme (ban riskini azaltır)
        delay_between_pages = 2.5

        def get_category_links():
            """Mevcut sayfadaki assortiment kategori linklerini döndür."""
            links = page.evaluate("""
                () => {
                    const a = document.querySelectorAll('a[href*="/producten/assortiment/"]');
                    return Array.from(a).map(el => el.href).filter(h => h && h.endsWith('.html'));
                }
            """)
            out = []
            for href in links or []:
                if link_pattern.search(href) and href not in visited:
                    out.append(href)
            return out

        def collect_visible_products():
            """Sayfadaki tüm [data-article] ürünlerini products_by_id'ye ekler."""
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

        def scroll_and_collect():
            """Mevcut sayfada azar azar kaydırıp tüm ürünleri toplar (bira script'i gibi)."""
            page.wait_for_timeout(2500)
            collect_visible_products()
            scroll_step = 500
            step = 0
            while True:
                step += 1
                reached_bottom = page.evaluate(
                    f"""
                    () => {{
                        window.scrollBy(0, {scroll_step});
                        return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 10;
                    }}
                    """
                )
                page.wait_for_timeout(1200)
                collect_visible_products()
                if reached_bottom or step > 80:
                    break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
            collect_visible_products()

        page_count = 0
        try:
            while to_visit:
                url = to_visit.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                page_count += 1
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print(f"  Atlandı (yüklenemedi): {url[:60]}... — {e}")
                    continue

                time.sleep(delay_between_pages)

                # Bu sayfada ürün kartı var mı?
                has_products = page.query_selector('[data-article]') is not None

                if has_products:
                    # Ürün listesi sayfası: azar azar kaydırıp topla
                    n_before = len(products_by_id)
                    scroll_and_collect()
                    n_after = len(products_by_id)
                    added = n_after - n_before
                    name = url.rstrip("/").split("/")[-1].replace(".html", "")
                    print(f"  [{page_count}] {name}: +{added} ürün (toplam {n_after})")
                else:
                    # Kategori listesi sayfası: alt kategorileri kuyruğa ekle
                    new_links = get_category_links()
                    for L in new_links:
                        if L not in visited and L not in to_visit:
                            to_visit.append(L)
                    name = url.rstrip("/").split("/")[-1].replace(".html", "")
                    print(f"  [{page_count}] {name}: kategori sayfası, {len(new_links)} alt link eklendi.")

                # Güvenlik: çok sayfa sınırı
                if page_count >= 150:
                    print("  Maksimum sayfa sayısına ulaşıldı (150).")
                    break

            browser.close()

        except Exception as e:
            browser.close()
            print("HATA:", str(e))
            raise

    products = list(products_by_id.values())
    print(f"\nToplam benzersiz ürün: {len(products)}")

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya_adi = f"aldi_be_tum_yeme_icme_{tarih}.json"
    dosya_yolu = os.path.join(cikti_dir, dosya_adi)

    cikti = {
        "kaynak": "ALDI Belçika",
        "kapsam": "Tüm assortiment (yeme-içme vb.)",
        "baslangic_url": start_url,
        "cekilme_tarihi": datetime.now().isoformat(),
        "taranan_sayfa_sayisi": page_count,
        "urun_sayisi": len(products),
        "not_fiyat_gecerliligi": "ALDI Belçika fiyatları genelde haftalık broşürle (Pazartesi-Cumartesi) güncellenir. Bu veri çekim anındaki sitedeki fiyatlardır; pratikte çekim yapılan hafta için geçerli kabul edilebilir.",
        "not_indirim": "Her üründe 'inPromotion': true/false alanı vardır. true = sitede kampanya/indirim işaretli, false = normal fiyat. Broşürdeki ürünler sitede listeleniyorsa dahildir.",
        "urunler": products,
    }

    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print(f"Tamamlandı. Dosya: {dosya_yolu}")
    input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    main()
