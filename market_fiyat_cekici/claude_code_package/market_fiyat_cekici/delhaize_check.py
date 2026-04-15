"""Delhaize nav hover/click ile tüm kategori linklerini toplar."""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
BASE = "https://www.delhaize.be"

def safe_print(s):
    print(s.encode('utf-8', 'replace').decode('utf-8'))

async def collect_links(page) -> dict:
    return await page.evaluate("""
    () => {
        const unique = {};
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.href.split('?')[0].split('#')[0];
            const text = a.textContent.trim();
            if ((href.includes('/c/v2') || (href.includes('/shop/') && href.includes('/c/'))) && text.length > 0) {
                unique[href] = text.substring(0,40);
            }
        });
        return unique;
    }
    """)

async def main():
    async with async_playwright() as p_:
        browser = await p_.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=CHROME_UA, viewport={"width":1400,"height":900}, locale="nl-BE")
        page = await context.new_page()

        await page.goto(f"{BASE}/nl/shop", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(3)
        for sel in ["#onetrust-accept-btn-handler", "button:has-text('Alles accepteren')"]:
            try:
                btn = page.locator(sel)
                if await btn.is_visible(timeout=2000):
                    await btn.click(); await asyncio.sleep(2); break
            except Exception: pass
        await asyncio.sleep(3)

        all_links = {}

        # Ilk linkler
        links = await collect_links(page)
        all_links.update(links)
        safe_print(f"Başlangıç linkleri: {len(all_links)}")

        # Nav'daki tüm butonlara/linklere hover et
        nav_elements = await page.evaluate("""
        () => Array.from(document.querySelectorAll(
            'header button, header li, header [class*="item"], nav li, nav button'
        )).map((el, i) => ({
            index: i,
            text: el.textContent.trim().substring(0,30),
            tag: el.tagName,
            class: el.className.substring(0,50)
        })).filter(x => x.text.length > 0)
        """)
        safe_print(f"Nav elementler ({len(nav_elements)}):")
        for el in nav_elements[:20]:
            safe_print(f"  [{el['index']}] {el['tag']} '{el['text']}' class={el['class'][:30]}")

        # Her nav öğesine hover et
        safe_print("\nHovering üzerinden linkler aranıyor...")
        for i in range(min(20, len(nav_elements))):
            try:
                elements = page.locator('header button, header li, header [class*="item"], nav li, nav button')
                el = elements.nth(i)
                if await el.is_visible(timeout=500):
                    await el.hover()
                    await asyncio.sleep(0.5)
                    new_links = await collect_links(page)
                    added = {k:v for k,v in new_links.items() if k not in all_links}
                    if added:
                        safe_print(f"  Hover {i} ({nav_elements[i]['text'][:20]}): {len(added)} yeni link")
                        for href, text in list(added.items())[:5]:
                            safe_print(f"    {text:35} -> {href.split('delhaize.be')[-1]}")
                    all_links.update(new_links)
            except Exception:
                pass

        safe_print(f"\nToplam /c/v2 ve /shop/ linkleri: {len(all_links)}")

        # Şimdi GetCategoryProductSearch'i vlees sayfasından çağır ve tüm pagination'ı kontrol et
        safe_print("\n\nVlees sayfasına gidiliyor - pagination test...")
        responses = []
        async def on_resp(r):
            if "GetCategoryProductSearch" in r.url:
                try:
                    body = await r.json()
                    cps = body.get("data",{}).get("categoryProductSearch",{})
                    if cps:
                        responses.append(cps)
                except Exception: pass
        page.on("response", on_resp)

        await page.goto(f"{BASE}/nl/shop/Vlees-vis-en-vegetarische-producten/Vers-vlees/c/v2MEAMEA",
                       wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        if responses:
            pag = responses[0].get("pagination", {})
            safe_print(f"Vers vlees pagination: {pag}")
            safe_print(f"Products count: {len(responses[0].get('products',[]))}")

        safe_print("\n\nFinal linkler:")
        for href, text in sorted(all_links.items()):
            safe_print(f"  {text:40} -> {href.split('delhaize.be')[-1]}")

        await browser.close()

asyncio.run(main())
