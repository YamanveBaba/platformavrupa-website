"""
ALDI Belçika SCRAPER — Playwright + data-article
Supabase market_chain_products tablosuna upsert eder.

Strateji:
  1. Haftalık aanbiedingen sayfaları (gerçek fiyatlar var, food + non-food)
  2. Sabit koleksiyon kategorileri (fiyat > 0 olanları kaydet)
  3. promotionDate = Unix timestamp ms → ISO tarih
  4. Fiyat = 0 ürünleri kaydetme
"""

import asyncio
import json
import os
import random
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ALDI] %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

CHAIN_SLUG   = "aldi_be"
COUNTRY_CODE = "BE"
CURRENCY     = "EUR"
ALDI_BASE    = "https://www.aldi.be"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Haftalık aanbiedingen — gerçek fiyatlar burada (her zaman çalışır)
DEAL_URLS = [
    ("Aanbiedingen deze week",    f"{ALDI_BASE}/nl/onze-aanbiedingen.html"),
    ("Aanbiedingen volgende week", f"{ALDI_BASE}/nl/aanbiedingen-volgende-week.html"),
]

# Sabit koleksiyon — sadece fiyat > 0 olanlar kaydedilir (çoğunun fiyatı 0)
PERMANENT_URLS = [
    ("Groenten",            f"{ALDI_BASE}/nl/producten/assortiment/groenten.html"),
    ("Fruit",               f"{ALDI_BASE}/nl/producten/assortiment/fruit.html"),
    ("Vlees",               f"{ALDI_BASE}/nl/producten/assortiment/vlees.html"),
    ("Vis Zeevruchten",     f"{ALDI_BASE}/nl/producten/assortiment/vis-zeevruchten.html"),
    ("Melkproducten Kaas",  f"{ALDI_BASE}/nl/producten/assortiment/melkproducten-kaas.html"),
    ("Brood Banket",        f"{ALDI_BASE}/nl/producten/assortiment/brood-en-banket.html"),
    ("Broodbeleg",          f"{ALDI_BASE}/nl/producten/assortiment/broodbeleg.html"),
    ("Alcoholvrije Dranken",f"{ALDI_BASE}/nl/producten/assortiment/alcoholvrije-dranken.html"),
    ("Alcoholische Dranken",f"{ALDI_BASE}/nl/producten/assortiment/alcoholische-dranken.html"),
    ("IJsjes",              f"{ALDI_BASE}/nl/producten/assortiment/ijsjes.html"),
    ("Pasta Rijst",         f"{ALDI_BASE}/nl/producten/assortiment/pasta-rijst.html"),
    ("Conserven",           f"{ALDI_BASE}/nl/producten/assortiment/conserven.html"),
    ("Bakken Koken",        f"{ALDI_BASE}/nl/producten/assortiment/bakken-en-koken.html"),
    ("Koffie Thee",         f"{ALDI_BASE}/nl/producten/assortiment/koffie-thee-cacao.html"),
    ("Muesli Cornflakes",   f"{ALDI_BASE}/nl/producten/assortiment/muesli-cornflakes-granen.html"),
    ("Snacks Zoetigheden",  f"{ALDI_BASE}/nl/producten/assortiment/snacks-zoetigheden.html"),
    ("Kant-en-klaar",       f"{ALDI_BASE}/nl/producten/assortiment/kant-en-klaar.html"),
    ("Vegetarisch Vegan",   f"{ALDI_BASE}/nl/producten/assortiment/vegetarisch-vegan.html"),
    ("Cosmetica Verzorging",f"{ALDI_BASE}/nl/producten/assortiment/cosmetica-verzorging.html"),
    ("Huishouden",          f"{ALDI_BASE}/nl/producten/assortiment/huishouden.html"),
    ("Dierenvoeding",       f"{ALDI_BASE}/nl/producten/assortiment/dierenvoeding.html"),
    ("Babyproducten",       f"{ALDI_BASE}/nl/producten/assortiment/babyproducten.html"),
]


# ─────────────────────── YARDIMCI ───────────────────────

def _unix_ms_to_iso(val) -> str | None:
    """Unix timestamp (ms veya sn) → 'YYYY-MM-DD'"""
    if not val:
        return None
    try:
        ts = int(val)
        if ts > 1e12:  # ms → sn
            ts = ts // 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def _to_iso_date(val) -> str | None:
    """DD-MM-YYYY → 'YYYY-MM-DD' veya Unix ms → 'YYYY-MM-DD'"""
    if not val:
        return None
    # Unix timestamp (sayısal)
    if isinstance(val, (int, float)):
        return _unix_ms_to_iso(val)
    s = str(val).strip()
    # Sadece rakam → Unix timestamp
    if s.isdigit():
        return _unix_ms_to_iso(int(s))
    # DD-MM-YYYY
    if len(s) >= 10 and s[2] == "-" and s[5] == "-":
        return f"{s[6:10]}-{s[3:5]}-{s[0:2]}"
    # YYYY-MM-DD zaten
    if len(s) >= 10 and s[4] == "-":
        return s[:10]
    return None


async def _collect_products_from_page(page) -> dict:
    """JS ile tüm [data-article] attribute'larını toplar."""
    raw_list = await page.evaluate("""
        () => Array.from(document.querySelectorAll('[data-article]'))
                   .map(el => el.getAttribute('data-article'))
                   .filter(Boolean)
    """)
    products = {}
    for raw in raw_list:
        try:
            data = json.loads(raw.replace("&quot;", '"'))
            info = data.get("productInfo") or {}
            cat  = data.get("productCategory") or {}
            pid  = str(info.get("productID") or "").strip()
            name = str(info.get("productName") or "").strip()
            if not pid or not name:
                continue

            price_raw = info.get("priceWithTax")
            if price_raw is None:
                continue
            price = float(price_raw)
            if price <= 0:
                continue  # Fiyatsız ürünü kaydetme

            in_promo    = bool(info.get("inPromotion", False))
            promo_price = None
            pp = info.get("promoPrice") or info.get("strikePrice")
            if pp is not None:
                try:
                    p_f = float(pp)
                    if p_f > 0 and p_f < price:
                        promo_price = p_f
                except Exception:
                    pass

            # promotionDate = Unix ms timestamp (geçerlilik tarihi)
            promo_date_raw = info.get("promotionDate") or info.get("promotionStartDate") or info.get("priceValidFrom")
            promo_from     = _to_iso_date(promo_date_raw)

            promo_until_raw = info.get("promotionEndDate") or info.get("priceValidTo") or info.get("validTo")
            promo_until     = _to_iso_date(promo_until_raw)

            category = cat.get("primaryCategory") or cat.get("category") or ""
            brand    = str(info.get("brand") or "").strip()
            image    = str(info.get("imageUrl") or info.get("image") or "").strip()

            products[pid] = {
                "chain_slug":           CHAIN_SLUG,
                "country_code":         COUNTRY_CODE,
                "external_product_id":  pid,
                "name":                 name,
                "brand":                brand,
                "category_name":        category,
                "price":                price,
                "currency":             CURRENCY,
                "in_promo":             in_promo,
                "promo_price":          promo_price,
                "promo_valid_from":     promo_from,
                "promo_valid_until":    promo_until,
                "image_url":            image,
                "captured_at":          datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            continue
    return products


async def scrape_page(page, cat_name: str, url: str) -> list:
    log.info(f"  -> {cat_name}: {url}")
    products = {}
    try:
        resp = await page.goto(url, wait_until="networkidle", timeout=50000)
        if resp and resp.status in (404, 410):
            log.warning(f"    {cat_name}: HTTP {resp.status} — atlanıyor")
            return []

        await asyncio.sleep(random.uniform(2, 4))

        # Cookie banner
        for sel in [
            "#onetrust-accept-btn-handler",
            "button:has-text('Akkoord')",
            "button:has-text('Accepteer')",
            "button:has-text('Alle cookies')",
        ]:
            try:
                btn = page.locator(sel)
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    await asyncio.sleep(1.5)
                    break
            except Exception:
                pass

        await asyncio.sleep(2)

        # Scroll — lazy-load için
        prev_count  = 0
        stable_rounds = 0
        ever_found    = False
        for step in range(60):
            at_bottom = await page.evaluate("""
                () => {
                    window.scrollBy(0, 800);
                    return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 20;
                }
            """)
            await asyncio.sleep(random.uniform(0.4, 0.8))

            prods = await _collect_products_from_page(page)
            products.update(prods)

            if len(products) > 0:
                ever_found = True

            if len(products) == prev_count:
                stable_rounds += 1
                if ever_found and stable_rounds >= 5:
                    break
                if not ever_found and step >= 15:
                    break
            else:
                stable_rounds = 0
            prev_count = len(products)

            if at_bottom and stable_rounds >= 3:
                break

        log.info(f"    {cat_name}: {len(products)} ürün (fiyatlı)")
    except Exception as e:
        log.warning(f"    {cat_name} hatası: {e}")
    return list(products.values())


def upsert_products(sb: Client, products: list) -> int:
    if not products:
        return 0
    seen = {p["external_product_id"]: p for p in products}
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
                log.error(f"Chunk upsert hatası: {e2}")
        return saved


async def _run_async() -> int:
    log.info("=" * 60)
    log.info("ALDI SCRAPER BAŞLIYOR (Playwright + data-article)")
    log.info("  Haftalık aanbiedingen + sabit koleksiyon (fiyat > 0)")
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

        # 1. Haftalık aanbiedingen (fiyatlar burada)
        log.info("\n[1/2] Haftalık aanbiedingen...")
        for cat_name, url in DEAL_URLS:
            prods = await scrape_page(page, cat_name, url)
            if prods:
                saved = upsert_products(sb, prods)
                total_saved += saved
                log.info(f"    -> {saved} kaydedildi (toplam: {total_saved})")
            await asyncio.sleep(random.uniform(3, 6))

        # 2. Sabit koleksiyon (sadece fiyat > 0 olanlar)
        log.info("\n[2/2] Sabit koleksiyon (fiyatlı ürünler)...")
        for cat_name, url in PERMANENT_URLS:
            prods = await scrape_page(page, cat_name, url)
            if prods:
                saved = upsert_products(sb, prods)
                total_saved += saved
                log.info(f"    -> {saved} kaydedildi (toplam: {total_saved})")
            await asyncio.sleep(random.uniform(3, 7))

        await browser.close()

    log.info("=" * 60)
    log.info(f"ALDI TAMAMLANDI — Toplam: {total_saved} ürün")
    log.info("=" * 60)
    return total_saved


def run() -> int:
    return asyncio.run(_run_async())


if __name__ == "__main__":
    run()
