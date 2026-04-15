"""ALDI check: data-article yapısını ve ürün sayısını kontrol eder."""
import asyncio, json
from playwright.async_api import async_playwright

CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
ALDI_BASE = "https://www.aldi.be"

TEST_CATS = [
    ("Groenten",    f"{ALDI_BASE}/nl/producten/assortiment/groenten.html"),
    ("Vlees",       f"{ALDI_BASE}/nl/producten/assortiment/vlees.html"),
    ("Aanbiedingen",f"{ALDI_BASE}/nl/aanbiedingen.html"),
]


async def collect_products(page):
    raw_list = await page.evaluate("""
        () => Array.from(document.querySelectorAll('[data-article]'))
                   .map(el => el.getAttribute('data-article'))
                   .filter(Boolean)
    """)
    products = []
    for raw in raw_list:
        try:
            data = json.loads(raw.replace("&quot;", '"'))
            products.append(data)
        except Exception:
            pass
    return products


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=CHROME_UA, viewport={"width":1280,"height":900}, locale="nl-BE"
        )
        page = await context.new_page()

        for cat_name, url in TEST_CATS:
            print(f"\n{'='*55}")
            print(f"KATEGORİ: {cat_name}")
            print(f"URL: {url}")
            print('='*55)

            await page.goto(url, wait_until="networkidle", timeout=50000)
            await asyncio.sleep(3)

            # Cookie
            for sel in ["#onetrust-accept-btn-handler","button:has-text('Akkoord')"]:
                try:
                    btn = page.locator(sel)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except: pass

            # Scroll
            for _ in range(20):
                at_bottom = await page.evaluate("""
                    () => { window.scrollBy(0, 800); return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 20; }
                """)
                await asyncio.sleep(0.5)
                if at_bottom:
                    break

            prods = await collect_products(page)
            print(f"Bulunan ürün: {len(prods)}")

            if prods:
                # İlk ürünün yapısını göster
                p0 = prods[0]
                info = p0.get("productInfo", {})
                print(f"\nİlk ürün data yapısı (productInfo anahtarları):")
                for k, v in info.items():
                    print(f"  {k}: {v}")

                # Promo olanlar
                promo = [x for x in prods if x.get("productInfo", {}).get("inPromotion")]
                print(f"\nİndirimli ürünler: {len(promo)}")
                if promo:
                    pp = promo[0].get("productInfo", {})
                    print(f"Promo ürün örneği: {pp.get('productName')} | fiyat:{pp.get('priceWithTax')} | promoPrice:{pp.get('promoPrice')} | strikePrice:{pp.get('strikePrice')}")
                    print(f"  promotionStartDate: {pp.get('promotionStartDate')}")
                    print(f"  promotionEndDate: {pp.get('promotionEndDate')}")
                    print(f"  priceValidFrom: {pp.get('priceValidFrom')}")
                    print(f"  priceValidTo: {pp.get('priceValidTo')}")

        await browser.close()

asyncio.run(main())
