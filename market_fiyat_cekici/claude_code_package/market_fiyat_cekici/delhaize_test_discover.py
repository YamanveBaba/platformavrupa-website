"""
Delhaize kategori keşfini test eder — kaç kategori buluyor?
Scrape etmez, sadece URL listesini gösterir.
"""
import asyncio
import sys
sys.path.insert(0, '.')
from delhaize_scraper import discover_all_categories, DELHAIZE_BASE, CHROME_UA
from playwright.async_api import async_playwright

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
            timezone_id="Europe/Brussels",
        )

        print("Kategori keşfi başlıyor...")
        categories = await discover_all_categories(context)

        print(f"\n{'='*60}")
        print(f"TOPLAM: {len(categories)} kategori")
        print('='*60)
        for name, url in sorted(categories, key=lambda x: x[1]):
            code = url.split("/c/")[-1] if "/c/" in url else "?"
            print(f"  {code:25} {name[:40]:40} {url.replace(DELHAIZE_BASE, '')}")

        await browser.close()

asyncio.run(main())
