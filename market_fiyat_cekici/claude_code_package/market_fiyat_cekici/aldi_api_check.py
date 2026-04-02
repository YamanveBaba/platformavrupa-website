"""ALDI API araştırması: Hangi endpoint fiyat veriyor?"""
import asyncio, json
from playwright.async_api import async_playwright

CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
ALDI_BASE = "https://www.aldi.be"

URLS_TO_CHECK = [
    ("Groenten",       f"{ALDI_BASE}/nl/producten/assortiment/groenten.html"),
    ("Aanbiedingen",   f"{ALDI_BASE}/nl/aanbiedingen/huidige-week-aanbiedingen.html"),
    ("Aanbiedingen 2", f"{ALDI_BASE}/nl/aanbiedingen/deze-week.html"),
    ("Vlees detail",   f"{ALDI_BASE}/nl/producten/assortiment/vlees-vis-en-gevogelte.html"),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=CHROME_UA, viewport={"width":1280,"height":900}, locale="nl-BE")
        page = await context.new_page()

        # Tüm response'ları yakala
        api_calls = []
        async def on_resp(r):
            ct = r.headers.get("content-type","")
            url = r.url
            if "json" in ct and "aldi" in url:
                try:
                    body = await r.json()
                    api_calls.append({"url": url[:150], "status": r.status, "body_keys": list(body.keys())[:5] if isinstance(body,dict) else "list"})
                except: pass

        page.on("response", on_resp)

        for cat_name, url in URLS_TO_CHECK:
            api_calls.clear()
            print(f"\n{'='*60}")
            print(f"{cat_name}: {url}")
            print('='*60)

            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=40000)
                print(f"HTTP: {resp.status}")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"HATA: {e}")
                continue

            # Cookie
            for sel in ["#onetrust-accept-btn-handler","button:has-text('Akkoord')"]:
                try:
                    btn = page.locator(sel)
                    if await btn.is_visible(timeout=2000):
                        await btn.click(); await asyncio.sleep(2); break
                except: pass

            # Scroll
            for _ in range(15):
                await page.evaluate("window.scrollBy(0, 600)")
                await asyncio.sleep(0.5)

            await asyncio.sleep(2)

            # API calls
            print(f"API çağrıları ({len(api_calls)}):")
            for call in api_calls[:10]:
                print(f"  {call['status']} {call['url']}")
                print(f"       keys: {call['body_keys']}")

            # DOM yapısı
            elems = await page.evaluate("""
            () => ({
                dataArticle: document.querySelectorAll('[data-article]').length,
                priceElems: document.querySelectorAll('[class*="price"], [class*="Price"]').length,
                cards: document.querySelectorAll('[class*="card"], [class*="Card"], [class*="product"]').length,
                imgs: document.querySelectorAll('img[src*="product"]').length,
            })
            """)
            print(f"DOM: data-article={elems['dataArticle']}, price-elems={elems['priceElems']}, cards={elems['cards']}")

            # Fiyat elementlerinin text'ini göster
            price_texts = await page.evaluate("""
            () => Array.from(document.querySelectorAll('[class*="price"], [class*="Price"], [class*="prijs"]'))
                       .map(el => el.textContent.trim())
                       .filter(t => t.length > 0 && t.length < 20)
                       .slice(0, 10)
            """)
            if price_texts:
                print(f"Fiyat elementleri: {price_texts}")

        await browser.close()

asyncio.run(main())
