"""
Delhaize scraper quick smoke test:
- 2 kategori scrape et (vlees + zuivel)
- Pagination çalışıyor mu?
- Promo/tarih alanları doluyor mu?
- Kaç ürün çekti?
"""
import asyncio, sys
sys.path.insert(0, '.')

from delhaize_scraper import scrape_category, _parse_product, CHROME_UA, DELHAIZE_BASE
from playwright.async_api import async_playwright

TEST_CATS = [
    ("Vers vlees",  f"{DELHAIZE_BASE}/nl/shop/Vlees-vis-en-vegetarische-producten/Vers-vlees/c/v2MEAMEA"),
    ("Zuivel",      f"{DELHAIZE_BASE}/c/v2DAI"),  # redirect test
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=CHROME_UA,
            viewport={"width": 1280, "height": 900},
            locale="nl-BE",
        )

        for cat_name, url in TEST_CATS:
            print(f"\n{'='*55}")
            print(f"TEST: {cat_name}")
            print(f"URL:  {url}")
            print('='*55)

            prods = await scrape_category(context, cat_name, url)
            print(f"\nToplam ürün: {len(prods)}")

            if prods:
                # Promo olanları göster
                promo_prods = [p for p in prods if p['in_promo']]
                print(f"İndirimli:   {len(promo_prods)}")

                # Tarih alanları dolu mu?
                with_from  = [p for p in prods if p['promo_valid_from']]
                with_until = [p for p in prods if p['promo_valid_until']]
                print(f"promo_valid_from dolu:  {len(with_from)}")
                print(f"promo_valid_until dolu: {len(with_until)}")

                # Örnek ürünler
                print("\nÖrnek ürünler (ilk 5):")
                for prod in prods[:5]:
                    promo_str = f" → promo:{prod['promo_price']} ({prod['promo_valid_from']}~{prod['promo_valid_until']})" if prod['in_promo'] else ""
                    print(f"  [{prod['external_product_id']}] {prod['name'][:40]:40} {prod['price']:.2f}€{promo_str}")

                if promo_prods:
                    print("\nÖrnek indirimli ürünler:")
                    for prod in promo_prods[:5]:
                        print(f"  [{prod['external_product_id']}] {prod['name'][:35]:35} {prod['price']:.2f}€ → {prod['promo_price']} ({prod['promo_valid_from']} ~ {prod['promo_valid_until']})")

        await browser.close()
    print("\nSmoke test tamamlandı!")

asyncio.run(main())
