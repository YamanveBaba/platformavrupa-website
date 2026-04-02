"""
Lidl Belçika SCRAPER — Playwright + .product-grid-box
Supabase market_chain_products tablosuna upsert eder.
"""

import asyncio
import json
import os
import random
import re
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LIDL] %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

CHAIN_SLUG   = "lidl_be"
COUNTRY_CODE = "BE"
CURRENCY     = "EUR"
LIDL_BASE    = "https://www.lidl.be"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Lidl BE gıda+günlük ürün kategorileri (hub sayfaları en geniş)
CATEGORY_URLS = [
    ("Voeding & Drank",        f"{LIDL_BASE}/c/nl-BE/voeding-drank/s10068374"),
    ("Groenten & Fruit",       f"{LIDL_BASE}/c/nl-BE/assortiment-groenten-en-fruit/s10008178"),
    ("Bakkerij",               f"{LIDL_BASE}/c/nl-BE/assortiment-bakkerij/s10008262"),
    ("Vlees & Vis",            f"{LIDL_BASE}/c/nl-BE/assortiment-vlees-en-vis/s10008141"),
    ("Veggie & Vegan",         f"{LIDL_BASE}/c/nl-BE/assortiment-veggie-en-vegan/s10008163"),
    ("Zuivel",                 f"{LIDL_BASE}/c/nl-BE/assortiment-zuivel/s10008308"),
    ("Dranken",                f"{LIDL_BASE}/c/nl-BE/assortiment-dranken/s10008275"),
    ("Reiniging & Huishouden", f"{LIDL_BASE}/c/nl-BE/assortiment-reiniging-en-huishouden/s10008306"),
    ("Baby & Kind",            f"{LIDL_BASE}/c/nl-BE/baby-kind-speelgoed/s10067767"),
]

LOAD_MORE_SEL  = ".s-load-more__button"
COOKIE_SEL     = ".ot-button-order-2, button:has-text('Alle toestaan'), button:has-text('Aanvaarden')"


def _parse_price(text: str) -> float | None:
    """Metinden ilk fiyatı çıkarır: '4.79 200 ml ...' → 4.79"""
    if not text:
        return None
    m = re.search(r'(\d+)[,.](\d{2})', text.replace(",", "."))
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    return None


def _parse_promo_price(price_text: str) -> float | None:
    """'5.98 2E AAN -50% 4.49 ...' → 4.49 (ikinci fiyat)"""
    if not price_text or "AAN" not in price_text.upper():
        return None
    nums = re.findall(r'(\d+)[,.](\d{2})', price_text.replace(",", "."))
    if len(nums) >= 2:
        return float(f"{nums[-1][0]}.{nums[-1][1]}")
    return None


async def scrape_category(page, cat_name: str, url: str) -> list:
    log.info(f"  → {cat_name}: {url}")
    products = {}

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)

        # Cookie banner — click then forcibly remove the SDK overlay
        try:
            btn = page.locator(COOKIE_SEL).first
            if await btn.is_visible(timeout=4000):
                await btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

        # Remove OneTrust overlay via JS so it never intercepts clicks
        await page.evaluate("""
            () => {
                const sdk = document.getElementById('onetrust-consent-sdk');
                if (sdk) sdk.remove();
                // Also remove any lingering dark-filter divs
                document.querySelectorAll('.onetrust-pc-dark-filter').forEach(el => el.remove());
            }
        """)
        await asyncio.sleep(3)

        # Scroll + "Meer laden" ile tüm ürünleri yükle
        for round_num in range(50):
            # Sayfanın sonuna kaydır
            for __ in range(6):
                await page.evaluate("window.scrollBy(0, 700)")
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)

            # "Meer laden" butonu var mı?
            try:
                btn = page.locator(LOAD_MORE_SEL).first
                if await btn.is_visible(timeout=2000):
                    await btn.scroll_into_view_if_needed()
                    # Use JS click to bypass any remaining overlay
                    await page.evaluate("document.querySelector('.s-load-more__button')?.click()")
                    await asyncio.sleep(random.uniform(2, 4))
                else:
                    break  # Buton yok = tüm ürünler yüklendi
            except Exception:
                break

        # Ürünleri JS ile topla
        prods = await page.evaluate("""
        () => {
            const boxes = document.querySelectorAll('.product-grid-box');
            return Array.from(boxes).map(box => {
                const link = box.querySelector('a[href*="/p/nl-BE/"]');
                if (!link) return null;
                const href = link.href || '';
                const pidMatch = href.match(/\\/p([0-9]+)(#|$)/);
                const pid = pidMatch ? pidMatch[1] : '';
                if (!pid) return null;
                const name = link.textContent.trim();
                const priceBox = box.querySelector('.product-grid-box__price, .price-wrapper');
                const priceText = priceBox ? priceBox.textContent.trim() : '';
                const img = box.querySelector('img');
                const imgUrl = img ? (img.src || img.dataset.src || '') : '';
                return {pid, name, priceText, imgUrl};
            }).filter(Boolean);
        }
        """)

        for p in prods:
            try:
                pid  = str(p["pid"]).strip()
                name = str(p["name"]).strip()
                if not pid or not name:
                    continue
                price = _parse_price(p["priceText"])
                if price is None:
                    continue
                promo_price = _parse_promo_price(p["priceText"])
                in_promo    = promo_price is not None
                products[pid] = {
                    "chain_slug":           CHAIN_SLUG,
                    "country_code":         COUNTRY_CODE,
                    "external_product_id":  pid,
                    "name":                 name,
                    "brand":                "",
                    "category_name":        cat_name,
                    "price":                price,
                    "currency":             CURRENCY,
                    "in_promo":             in_promo,
                    "promo_price":          promo_price,
                    "promo_valid_from":     None,
                    "promo_valid_until":    None,
                    "image_url":            p.get("imgUrl", ""),
                    "captured_at":          datetime.now(timezone.utc).isoformat(),
                }
            except Exception:
                continue

        log.info(f"    {cat_name}: {len(products)} ürün")
    except Exception as e:
        log.warning(f"    {cat_name} hatası: {e}")

    return list(products.values())


def upsert_products(sb: Client, products: list) -> int:
    if not products:
        return 0
    seen = {}
    for p in products:
        seen[p["external_product_id"]] = p
    products = list(seen.values())
    try:
        sb.table("market_chain_products").upsert(
            products, on_conflict="chain_slug,external_product_id"
        ).execute()
        return len(products)
    except Exception as e:
        log.error(f"Upsert hatası: {e}")
        saved = 0
        for chunk in [products[i:i+10] for i in range(0, len(products), 10)]:
            try:
                sb.table("market_chain_products").upsert(
                    chunk, on_conflict="chain_slug,external_product_id"
                ).execute()
                saved += len(chunk)
            except Exception as e2:
                log.error(f"Chunk: {e2}")
        return saved


async def _run_async() -> int:
    log.info("=" * 60)
    log.info("LIDL SCRAPER BAŞLIYOR (Playwright + product-grid-box)")
    log.info("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error(".env eksik!")
        return 0

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    total_saved = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent=CHROME_UA,
            viewport={"width": 1280, "height": 900},
            locale="nl-BE",
            timezone_id="Europe/Brussels",
        )
        page = await context.new_page()

        for cat_name, url in CATEGORY_URLS:
            prods = await scrape_category(page, cat_name, url)
            if prods:
                saved = upsert_products(sb, prods)
                total_saved += saved
                log.info(f"    → {saved} kaydedildi (toplam: {total_saved})")
            await asyncio.sleep(random.uniform(3, 6))

        await browser.close()

    log.info("=" * 60)
    log.info(f"LIDL TAMAMLANDI — Toplam: {total_saved} ürün")
    log.info("=" * 60)
    return total_saved


def run() -> int:
    return asyncio.run(_run_async())


if __name__ == "__main__":
    run()
