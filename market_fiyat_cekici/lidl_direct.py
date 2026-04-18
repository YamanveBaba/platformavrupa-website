# -*- coding: utf-8 -*-
"""
lidl_direct.py — Lidl BE urunlerini Playwright ile ceker.
Cookie consent otomatik kabul edilir, urun kartlari yuklenene kadar beklenir.
Urunler JSON olarak kaydedilir.

Calistir: python lidl_direct.py
"""
import json, time, random
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"])
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

SCRIPT_DIR = Path(__file__).parent
CIKTI_DIR  = SCRIPT_DIR / "cikti" / "html_pages"
CIKTI_DIR.mkdir(parents=True, exist_ok=True)

KATEGORILER = [
    ("Zuivel",          "https://www.lidl.be/c/zuivel-kaas-en-eieren/a10063448"),
    ("Vlees",           "https://www.lidl.be/c/vlees-en-vis/a10063449"),
    ("Groenten_Fruit",  "https://www.lidl.be/c/groenten-en-fruit/a10063450"),
    ("Dranken",         "https://www.lidl.be/c/dranken/a10063453"),
    ("Brood_Bakkerij",  "https://www.lidl.be/c/bakkerij/a10063452"),
    ("Snacks",          "https://www.lidl.be/c/chips-en-snacks/a10063455"),
    ("Diepvries",       "https://www.lidl.be/c/diepvries/a10063451"),
]

# JS: DOM'dan Lidl urun verilerini cikart
_DOM_JS = """
() => {
    const out = [];
    const seen = new Set();

    function extractPrice(el) {
        // Lidl: nuc-m-product-price element
        const pEl = el.querySelector('.nuc-m-product-price, [class*="product-price"], [class*="ProductPrice"]');
        if (pEl) {
            const t = pEl.textContent.trim();
            const m = t.match(/\\d+[,.]\\d{2}/);
            if (m) return m[0];
        }
        // aria-label on price
        const ariaEls = el.querySelectorAll('[aria-label*="euro" i], [aria-label*="€"]');
        for (const a of ariaEls) {
            const t = a.getAttribute('aria-label') || '';
            const m = t.match(/[\\d]+[,.]\\d{2}/);
            if (m) return m[0];
        }
        // Any text with euro pattern
        const texts = el.querySelectorAll('span, p, div');
        for (const t of texts) {
            const txt = t.textContent.trim();
            if (/^\\d+[,.]\\d{2}$/.test(txt)) return txt;
        }
        return '';
    }

    function extractName(el) {
        // Lidl product name in h2/h3 or product-title
        const nameEl = el.querySelector('h2, h3, [class*="product-title"], [class*="ProductTitle"], [class*="product-name"]');
        if (nameEl) {
            const t = nameEl.textContent.trim();
            if (t.length > 2) return t;
        }
        // img alt
        const img = el.querySelector('img[alt]');
        if (img) {
            const a = (img.getAttribute('alt') || '').trim();
            if (a.length > 2 && !/^\\d/.test(a)) return a;
        }
        return '';
    }

    // Strategy 1: article.nuc-a-product (Lidl NUC components)
    document.querySelectorAll('article.nuc-a-product, [class*="nuc-a-product"], article[class*="product"]').forEach(el => {
        const lnk = el.querySelector('a[href]');
        const href = lnk ? lnk.getAttribute('href') : '';
        const key = href || el.textContent.slice(0, 50);
        if (!key || seen.has(key)) return;
        seen.add(key);
        const name = extractName(el);
        const price = extractPrice(el);
        if (!name && !price) return;
        const imgEl = el.querySelector('img[src], img[data-src]');
        const img = imgEl ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '') : '';
        const inPromo = !!el.querySelector('[class*="promo"], [class*="actie"], [class*="korting"], [class*="discount"]');
        // Extract PID from URL
        const m = (href || '').match(/\\/p\\d+\\/([^/]+)/);
        const pid = m ? m[1] : href;
        out.push({pid: pid.slice(0,100), name: name.slice(0,300), price: price.slice(0,30),
                  img: img.slice(0,400), inPromo, href: href.slice(0,200)});
    });

    // Strategy 2: Generic product cards
    if (out.length === 0) {
        const csels = ['[class*="ProductCard"]', '[class*="product-card"]',
                       '[class*="product-item"]', 'li[class*="product"]',
                       '[data-product-id]', '[data-testid*="product"]'];
        for (const cs of csels) {
            let els; try { els = document.querySelectorAll(cs); } catch(e) { continue; }
            if (els.length < 2) continue;
            els.forEach(el => {
                const lnk = el.querySelector('a[href]');
                const href = lnk ? lnk.getAttribute('href') : '';
                const key = href || el.textContent.slice(0, 50);
                if (!key || seen.has(key)) return;
                seen.add(key);
                const name = extractName(el);
                const price = extractPrice(el);
                if (!name && !price) return;
                const imgEl = el.querySelector('img[src], img[data-src]');
                const img = imgEl ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src') || '') : '';
                out.push({pid: href.slice(0,100), name: name.slice(0,300), price: price.slice(0,30),
                          img: img.slice(0,400), inPromo: false, href: href.slice(0,200)});
            });
            if (out.length > 0) break;
        }
    }

    return out;
}
"""


def consent_kabul(page):
    selectors = [
        "button:has-text('Alles accepteren')",
        "button:has-text('Accepteren')",
        "#onetrust-accept-btn-handler",
        "button:has-text('Accept all')",
        "[class*='cookie'] button:has-text('Accept')",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=3000):
                loc.click(timeout=5000)
                time.sleep(1.5)
                print("    Cookie consent kabul edildi.")
                return True
        except Exception:
            continue
    return False


def meer_laden_tikla(page, max_clicks: int = 10) -> int:
    """Meer laden / Load more butonuna tikla, daha fazla urun yukle."""
    clicked = 0
    for _ in range(max_clicks):
        try:
            btn = page.locator("button:has-text('Meer laden'), button:has-text('Toon meer'), button:has-text('Laden')").first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click(timeout=5000)
                time.sleep(2.5)
                clicked += 1
            else:
                break
        except Exception:
            break
    return clicked


def kat_cek(page, kat_ad: str, kat_url: str) -> list:
    print(f"\n  >> {kat_ad}: {kat_url}")
    try:
        page.goto(kat_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Cookie consent
        consent_kabul(page)
        time.sleep(2)

        # Urun kartlarini bekle
        product_selectors = [
            "article.nuc-a-product",
            "[class*='nuc-a-product']",
            "article[class*='product']",
            "[class*='ProductCard']",
            "[class*='product-card']",
        ]
        loaded = False
        for sel in product_selectors:
            try:
                page.wait_for_selector(sel, timeout=15000)
                loaded = True
                print(f"    Selector bulundu: {sel}")
                break
            except PWTimeout:
                continue

        if not loaded:
            print("    UYARI: Urun selector bulunamadi, scroll deneniyor...")

        # Scroll — lazy load tetikle
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(0.8)

        # Meer laden — daha fazla urun yukle
        loaded_more = meer_laden_tikla(page, max_clicks=5)
        if loaded_more > 0:
            print(f"    'Meer laden' {loaded_more}x tiklandi")
            time.sleep(1)

        # Basladiktan sonra tekrar scroll
        for _ in range(3):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(0.5)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.5)

        # DOM'dan urunleri cikart
        urunler = page.evaluate(_DOM_JS)
        print(f"    DOM'dan {len(urunler)} urun alindi")
        return urunler

    except Exception as e:
        print(f"    HATA: {e}")
        return []


def lidl_cek():
    tarih = datetime.now().strftime("%Y-%m-%d")
    tum_urunler = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="nl-BE",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = ctx.new_page()

        for kat_ad, kat_url in KATEGORILER:
            urunler = kat_cek(page, kat_ad, kat_url)

            if urunler:
                for u in urunler:
                    u["category_nl"] = kat_ad

                dosya = CIKTI_DIR / f"lidl_{kat_ad}_p01_{tarih}.json"
                dosya.write_text(
                    json.dumps({"products": urunler}, ensure_ascii=False),
                    encoding="utf-8"
                )
                print(f"    Kaydedildi: {dosya.name}")
                tum_urunler.extend(urunler)
            else:
                print(f"    UYARI: {kat_ad} icin urun alinamadi")

            time.sleep(random.uniform(3, 5))

        browser.close()

    print(f"\n  Toplam: {len(tum_urunler)} urun, {len(KATEGORILER)} kategori")
    return tum_urunler


if __name__ == "__main__":
    lidl_cek()
