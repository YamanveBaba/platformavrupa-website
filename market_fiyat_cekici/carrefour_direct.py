# -*- coding: utf-8 -*-
"""
carrefour_direct.py — Carrefour BE urunlerini Playwright ile ceker.
Cookie consent otomatik kabul edilir, data-pid elementleri yuklenene kadar beklenir.
Urunler JSON olarak kaydedilir (HTML degil).

Calistir: python carrefour_direct.py
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
    ("Zuivel_Eieren",   "https://www.carrefour.be/nl/c/8000"),
    ("Vlees",           "https://www.carrefour.be/nl/c/6000"),
    ("Groenten_Fruit",  "https://www.carrefour.be/nl/c/9000"),
    ("Brood_Bakkerij",  "https://www.carrefour.be/nl/c/4000"),
    ("Dranken",         "https://www.carrefour.be/nl/c/11000"),
    ("Snacks_Koekjes",  "https://www.carrefour.be/nl/c/3000"),
    ("Hygieneproducten","https://www.carrefour.be/nl/c/14000"),
    ("Schoonmaak",      "https://www.carrefour.be/nl/c/15000"),
    ("Diepvries",       "https://www.carrefour.be/nl/c/13000"),
]

# JavaScript: DOM'dan urun verileri cikart
_DOM_JS = """
() => {
    const out = [];
    const seen = new Set();

    function extractPrice(el) {
        for (const a of ['data-price','data-sales-price','data-regular-price']) {
            const v = el.getAttribute(a); if(v && /\\d/.test(v)) return v.trim();
        }
        const sels = ['.price .sales .value','[class*="price"] .value',
                      '.price-sales','.js-price-value','[class*="price--sales"]',
                      '[class*="actualPrice"]','[class*="current-price"]','strong[class*="price"]',
                      '.product-price','[class*="product-price"]'];
        for (const s of sels) {
            try { const pe=el.querySelector(s); if(pe){const t=pe.textContent.trim();
                  if(/\\d+[.,]\\d{2}/.test(t)) return t; } } catch(e) {}
        }
        return '';
    }

    function extractName(el) {
        const img = el.querySelector('img[alt]');
        if (img) { const a=(img.getAttribute('alt')||'').trim();
                   if(a.length>3 && !/^\\d/.test(a)) return a; }
        for (const a of ['data-name','data-product-name','data-title']) {
            const v=(el.getAttribute(a)||'').trim(); if(v.length>2) return v;
        }
        const nsels=['.product-name','[class*="product-name"]','.product-title',
                     '[class*="product-title"]','h2','h3','h4'];
        for (const s of nsels) {
            try { const ne=el.querySelector(s); if(ne){const t=ne.textContent.trim();
                  if(t.length>2) return t;} } catch(e) {}
        }
        return '';
    }

    // Strateji 1: SFCC [data-pid]
    document.querySelectorAll('[data-pid]').forEach(el => {
        const pid=el.getAttribute('data-pid')||'';
        if(!pid||seen.has(pid)) return;
        seen.add(pid);
        const price=el.getAttribute('data-price')||extractPrice(el);
        const name=el.getAttribute('data-name')||el.getAttribute('data-product-name')||extractName(el);
        const brand=el.getAttribute('data-brand')||'';
        const inPromo=!!el.querySelector('[class*="promo"],[class*="badge-promo"],[class*="promotion"],[class*="actie"]');
        const imgEl=el.querySelector('img[data-src],img[src]');
        const img=imgEl?(imgEl.getAttribute('data-src')||imgEl.getAttribute('src')||''):'';
        const lnk=el.querySelector('a[href]');
        const href=lnk?lnk.getAttribute('href'):'';
        out.push({pid, price:price.trim().slice(0,60), name:name.trim().slice(0,300),
                  brand:brand.slice(0,100), inPromo, img:img.slice(0,400), href:(href||'').slice(0,200)});
    });

    // Strateji 2: Verbolia single-product-desktop
    if(out.length===0) {
        document.querySelectorAll('a[data-id][class*="single-product"]').forEach(el => {
            const pid=el.getAttribute('data-id')||'';
            if(!pid||seen.has(pid)) return;
            seen.add(pid);
            const price=extractPrice(el);
            const name=extractName(el);
            const inPromo=!!el.querySelector('[class*="promo"],[class*="actie"],[class*="korting"]');
            const imgEl=el.querySelector('img[data-src],img[src]');
            const img=imgEl?(imgEl.getAttribute('data-src')||imgEl.getAttribute('src')||''):'';
            out.push({pid, price:price.slice(0,60), name:name.slice(0,300),
                      brand:'', inPromo, img:img.slice(0,400), href:el.getAttribute('href')||''});
        });
    }

    return out;
}
"""


def consent_kabul(page):
    """OneTrust ve diger cookie consent butonlarini kabul et."""
    selectors = [
        "#onetrust-accept-btn-handler",
        "button:has-text('Alles accepteren')",
        "button:has-text('Accepteren')",
        "button:has-text('Accept all')",
        "button[aria-label*='Accept' i]",
        ".onetrust-close-btn-handler",
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


def kat_cek(page, kat_ad: str, kat_url: str) -> list:
    print(f"\n  >> {kat_ad}: {kat_url}")

    try:
        page.goto(kat_url, wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)

        # Cookie consent
        consent_kabul(page)
        time.sleep(2)

        # data-pid elementlerini bekle
        try:
            page.wait_for_selector("[data-pid]", timeout=20000)
        except PWTimeout:
            print("    UYARI: data-pid elementi bulunamadi, scroll deneniyor...")

        # Scroll — lazy load tetikle
        for i in range(8):
            page.evaluate("window.scrollBy(0, 600)")
            time.sleep(0.8)

        # Son kontrol
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)

        # Urunleri DOM'dan cikart
        urunler = page.evaluate(_DOM_JS)
        print(f"    DOM'dan {len(urunler)} urun alindi")
        return urunler

    except Exception as e:
        print(f"    HATA: {e}")
        return []


def carrefour_cek():
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
                # Her urun icin kategori bilgisi ekle
                for u in urunler:
                    u["category_nl"] = kat_ad

                # Kategori bazli JSON kaydet (html_analiz.py uyumlulugu icin .html uzantisi)
                dosya = CIKTI_DIR / f"carrefour_{kat_ad}_p01_{tarih}.json"
                dosya.write_text(
                    json.dumps({"products": urunler}, ensure_ascii=False),
                    encoding="utf-8"
                )
                print(f"    Kaydedildi: {dosya.name}")
                tum_urunler.extend(urunler)
            else:
                print(f"    UYARI: {kat_ad} icin urun alinamadi")

            # Kategoriler arasi bekleme
            time.sleep(random.uniform(3, 6))

        browser.close()

    print(f"\n  Toplam: {len(tum_urunler)} urun, {len(KATEGORILER)} kategori")
    return tum_urunler


if __name__ == "__main__":
    carrefour_cek()
