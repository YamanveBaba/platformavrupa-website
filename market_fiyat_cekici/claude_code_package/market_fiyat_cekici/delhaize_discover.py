"""
Delhaize tüm kategori URL'lerini nav hover + sidebar gezme ile keşfeder.
Çıktıyı delhaize_categories.json'a kaydeder.
"""
import asyncio
import json
from playwright.async_api import async_playwright

CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
BASE = "https://www.delhaize.be"


def safe_print(s):
    print(str(s).encode('utf-8', 'replace').decode('utf-8'))


async def get_cat_links(page) -> dict:
    return await page.evaluate("""
    () => {
        const unique = {};
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href.split('?')[0].split('#')[0];
            const text = (a.textContent || '').trim();
            if (href.includes('/shop/') && href.includes('/c/') && text.length > 1) {
                unique[href] = text.substring(0, 50);
            }
        });
        return unique;
    }
    """)


async def accept_cookies(page):
    for sel in ["#onetrust-accept-btn-handler", "button:has-text('Alles accepteren')"]:
        try:
            btn = page.locator(sel)
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(2)
                return
        except Exception:
            pass


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=CHROME_UA,
            viewport={"width": 1400, "height": 900},
            locale="nl-BE",
            timezone_id="Europe/Brussels",
        )
        page = await context.new_page()

        safe_print("Ana sayfa yükleniyor...")
        await page.goto(f"{BASE}/nl/shop", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        await accept_cookies(page)
        await asyncio.sleep(2)

        all_links = {}

        # 1. Başlangıç linkleri
        links = await get_cat_links(page)
        all_links.update(links)
        safe_print(f"Başlangıç: {len(all_links)} link")

        # 2. Nav'daki tüm üst düzey linklere hover et
        nav_links = await page.evaluate("""
        () => {
            const items = [];
            document.querySelectorAll(
                'header nav a, header [class*="nav"] a, nav[class*="main"] a, ' +
                '[class*="navigation"] > li > a, [class*="menu"] > li > a, ' +
                '[class*="category-nav"] > li > a'
            ).forEach((a, i) => {
                const text = (a.textContent || '').trim();
                if (text.length > 1 && text.length < 50) {
                    items.push({ index: i, text: text.substring(0, 40), href: a.href });
                }
            });
            return items;
        }
        """)
        safe_print(f"\nNav linkleri ({len(nav_links)}):")
        for item in nav_links:
            safe_print(f"  [{item['index']}] '{item['text']}' -> {item['href']}")

        # 3. Her nav öğesine hover et ve dropdown'ları topla
        safe_print("\nHover ediliyor...")
        for item in nav_links[:40]:
            try:
                el = page.locator(
                    'header nav a, header [class*="nav"] a, nav[class*="main"] a, '
                    '[class*="navigation"] > li > a, [class*="menu"] > li > a, '
                    '[class*="category-nav"] > li > a'
                ).nth(item['index'])
                if await el.is_visible(timeout=1000):
                    await el.hover()
                    await asyncio.sleep(1.0)
                    new_links = await get_cat_links(page)
                    added = {k: v for k, v in new_links.items() if k not in all_links}
                    if added:
                        safe_print(f"  Hover '{item['text'][:25]}': +{len(added)} link")
                        for href, text in list(added.items())[:8]:
                            safe_print(f"    {text:40} {href.replace(BASE, '')}")
                    all_links.update(new_links)
            except Exception:
                pass

        # 4. Header/nav'daki li elementlerine de hover et
        safe_print("\nHeader li elementleri hover ediliyor...")
        nav_lis = await page.evaluate("""
        () => {
            const items = [];
            document.querySelectorAll('header li, nav > ul > li, [class*="nav"] > ul > li').forEach((el, i) => {
                const text = (el.textContent || '').trim().substring(0, 30);
                if (text.length > 1) items.push({ index: i, text: text });
            });
            return items.slice(0, 50);
        }
        """)
        for item in nav_lis[:30]:
            try:
                el = page.locator('header li, nav > ul > li, [class*="nav"] > ul > li').nth(item['index'])
                if await el.is_visible(timeout=500):
                    await el.hover()
                    await asyncio.sleep(0.8)
                    new_links = await get_cat_links(page)
                    added = {k: v for k, v in new_links.items() if k not in all_links}
                    if added:
                        safe_print(f"  LI hover '{item['text'][:25]}': +{len(added)} link")
                    all_links.update(new_links)
            except Exception:
                pass

        safe_print(f"\nAna sayfadan toplam: {len(all_links)} kategori linki")

        # 5. Bulunan linkleri ziyaret et - sidebar'dan daha fazla link topla
        safe_print("\nKategori sayfaları geziliyor (sidebar'lar)...")
        visited = set()
        queue = list(all_links.keys())[:60]  # İlk 60 linki ziyaret et

        for url in queue:
            if url in visited:
                continue
            visited.add(url)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(1.5)
                new_links = await get_cat_links(page)
                added = {k: v for k, v in new_links.items() if k not in all_links}
                if added:
                    safe_print(f"  {url.split('/c/')[-1]}: +{len(added)} yeni link")
                all_links.update(new_links)
            except Exception as e:
                safe_print(f"  HATA {url.split('/c/')[-1]}: {e}")

        await browser.close()

    # Sonuçları kaydet
    safe_print(f"\n{'='*60}")
    safe_print(f"TOPLAM: {len(all_links)} kategori linki")
    safe_print('='*60)

    # Kod → URL mapping oluştur
    code_map = {}
    for href, text in sorted(all_links.items()):
        code = href.split('/c/')[-1] if '/c/' in href else ''
        code_map[code] = {"name": text, "url": href}
        safe_print(f"  {code:25} {text:40} {href.replace(BASE, '')}")

    with open("delhaize_categories.json", "w", encoding="utf-8") as f:
        json.dump(code_map, f, ensure_ascii=False, indent=2)
    safe_print(f"\ndelhaize_categories.json kaydedildi ({len(code_map)} kategori)")


asyncio.run(main())
