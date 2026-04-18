"""
Delhaize Belçika SCRAPER — Playwright + API response interception
Supabase market_chain_products tablosuna upsert eder.

Strateji:
  - HTML'den doğrulanan 17 top-level /c/v2XXX kodu kullan
  - Her top-level kod TÜM alt kategori ürünlerini döndürür (API güvencesi)
  - GetCategoryProductSearch intercept, totalPages ile tam pagination
  - İnsan gibi davran: rastgele gecikme + scroll
"""

import asyncio
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
    format="%(asctime)s [DELHAIZE] %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

CHAIN_SLUG   = "delhaize_be"
COUNTRY_CODE = "BE"
CURRENCY     = "EUR"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

DELHAIZE_BASE = "https://www.delhaize.be"

# HTML'den doğrulanmış top-level kategori kodları — her biri tüm alt ürünleri getirir
CATEGORIES = [
    ("Vlees vis vegetarisch",  "v2MEA"),
    ("Zuivel kaas eieren",     "v2DAI"),
    ("Brood banket",           "v2BAK"),
    ("Traiteur aperitiefhapjes", "v2DEL"),
    ("Diepvries",              "v2FRO"),
    ("Kruidenierswaren",       "v2CON"),
    ("Groenten fruit",         "v2FRU"),
    ("Snacks koekjes snoep",   "v2SWE"),
    ("Dranken",                "v2DRI"),
    ("Wijn bubbels",           "v2WIN"),
    ("Alcoholische dranken",   "v2ALC"),
    ("Aperitief",              "v2APE"),
    ("Schoonmaak huishouden",  "v2CLE"),
    ("Hygiene lichaamsverzorging", "v2HYG"),
    ("Baby kind",              "v2BAB"),
    ("Huisdieren",             "v2PET"),
    ("Bio eco fairtrade",      "v2BIO"),
]


# ─────────────────────── YARDIMCI ───────────────────────

async def human_pause(min_s: float = 1.5, max_s: float = 4.5):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def accept_cookies(page) -> bool:
    for sel in [
        "#onetrust-accept-btn-handler",
        "button:has-text('Alles accepteren')",
        "button:has-text('Accepteer')",
    ]:
        try:
            btn = page.locator(sel)
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await asyncio.sleep(2)
                return True
        except Exception:
            pass
    return False


def _to_iso_date(val) -> str | None:
    """'25/03/2026 23:00:00' veya '25-03-2026' → '2026-03-25'"""
    if not val:
        return None
    s = str(val).strip()
    m = re.match(r'^(\d{2})[/.-](\d{2})[/.-](\d{4})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        return s[:10]
    return None


def _parse_price(p) -> float | None:
    if p is None:
        return None
    if isinstance(p, dict):
        for k in ("value", "formattedValue", "amount"):
            v = p.get(k)
            if v is not None:
                try:
                    return float(str(v).replace(",", ".").replace("€", "").strip())
                except Exception:
                    pass
    if isinstance(p, (int, float)):
        return float(p)
    if isinstance(p, str):
        m = re.search(r'(\d+)[,.](\d{2})', p.replace(",", "."))
        if m:
            return float(f"{m.group(1)}.{m.group(2)}")
    return None


def _parse_product(raw: dict, cat_name: str) -> dict | None:
    try:
        pid  = str(raw.get("code") or "").strip()
        name = str(raw.get("name") or "").strip()
        if not pid or not name:
            return None

        price = _parse_price(raw.get("price"))
        if price is None:
            return None

        brand = str(raw.get("manufacturerName") or "").strip()

        in_promo    = False
        promo_price = None
        promo_from  = None
        promo_until = None

        promos = raw.get("potentialPromotions") or []
        if isinstance(promos, list) and promos:
            p0 = promos[0] if isinstance(promos[0], dict) else {}
            if p0:  # Herhangi bir promo var → in_promo = True
                in_promo = True
                # İndirimli fiyatı bul
                for k in ("promotionPrice", "discountedPrice", "value", "price"):
                    pp = p0.get(k)
                    if pp is not None:
                        parsed_pp = _parse_price(pp)
                        if parsed_pp is not None and parsed_pp < price:
                            promo_price = parsed_pp
                            break
                # Tarihleri al
                promo_from  = _to_iso_date(
                    p0.get("startDate") or p0.get("from")
                    or p0.get("validFrom") or p0.get("startdate")
                    or p0.get("promotionStartDate")
                )
                promo_until = _to_iso_date(
                    p0.get("endDate")   or p0.get("until")
                    or p0.get("validTo") or p0.get("enddate")
                    or p0.get("promotionEndDate")
                )

        # Kalıcı fiyat indirimi
        if not in_promo and raw.get("isPermanentPriceReduction"):
            in_promo = True

        image_url = ""
        images = raw.get("images") or []
        if isinstance(images, list) and images:
            img = images[0]
            if isinstance(img, dict):
                image_url = img.get("url", "")
                if image_url and not image_url.startswith("http"):
                    image_url = DELHAIZE_BASE + image_url

        return {
            "chain_slug":           CHAIN_SLUG,
            "country_code":         COUNTRY_CODE,
            "external_product_id":  pid,
            "name":                 name,
            "brand":                brand,
            "category_name":        cat_name,
            "price":                price,
            "currency":             CURRENCY,
            "in_promo":             in_promo,
            "promo_price":          promo_price,
            "promo_valid_from":     promo_from,
            "promo_valid_until":    promo_until,
            "image_url":            image_url,
            "captured_at":          datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.debug(f"Parse hatası: {e}")
        return None


# ─────────────────────── ÜRÜN ÇEKME ───────────────────────

async def scrape_category(context, cat_name: str, cat_code: str) -> list:
    """
    /c/{cat_code} URL'sini açar → Playwright redirect takip eder.
    GetCategoryProductSearch intercept, totalPages ile tam pagination.
    """
    products      = {}
    last_api_data = {}
    captured      = asyncio.Event()

    url = f"{DELHAIZE_BASE}/c/{cat_code}"

    page = await context.new_page()

    async def on_resp(r):
        if "GetCategoryProductSearch" not in r.url:
            return
        try:
            body = await r.json()
            cps  = body.get("data", {}).get("categoryProductSearch", {})
            if cps:
                last_api_data.clear()
                last_api_data.update(cps)
                captured.set()
        except Exception:
            pass

    page.on("response", on_resp)

    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        if resp and resp.status in (404, 410):
            log.warning(f"    {cat_name}: HTTP {resp.status} — atlanıyor")
            await page.close()
            return []

        # Redirect sonrası gerçek URL
        real_url = page.url.split("?")[0]
        log.info(f"    {cat_name} ({cat_code}): {real_url.replace(DELHAIZE_BASE, '')}")

        await asyncio.sleep(random.uniform(1.8, 3.5))
        await accept_cookies(page)

        # API cevabını bekle
        try:
            await asyncio.wait_for(captured.wait(), timeout=15)
        except asyncio.TimeoutError:
            for _ in range(3):
                await page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
                await asyncio.sleep(1.2)
            try:
                await asyncio.wait_for(captured.wait(), timeout=8)
            except asyncio.TimeoutError:
                log.warning(f"    {cat_name}: API timeout — atlanıyor")
                await page.close()
                return []

        # Sayfa 0 ürünleri
        for raw in last_api_data.get("products", []):
            p = _parse_product(raw, cat_name)
            if p:
                products[p["external_product_id"]] = p

        pagination  = last_api_data.get("pagination", {})
        total       = pagination.get("totalResults", 0) or 0
        total_pages = pagination.get("totalPages", 1) or 1

        if total == 0:
            log.info(f"    {cat_name}: ürün yok — atlanıyor")
            await page.close()
            return []

        log.info(f"    {cat_name}: {total} ürün, {total_pages} sayfa")

        # Sayfa 1 → N
        for pg in range(1, min(total_pages, 200)):
            captured.clear()
            last_api_data.clear()

            next_url = f"{real_url}?pageNumber={pg}"
            await page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(1.2, 2.8))

            # İnsan gibi scroll
            await page.evaluate(f"window.scrollBy(0, {random.randint(200, 600)})")
            await asyncio.sleep(random.uniform(0.3, 0.8))

            try:
                await asyncio.wait_for(captured.wait(), timeout=12)
                page_products = last_api_data.get("products", [])
                if not page_products:
                    log.info(f"    {cat_name} sayfa {pg}: boş — tamamlandı")
                    break
                for raw in page_products:
                    p = _parse_product(raw, cat_name)
                    if p:
                        products[p["external_product_id"]] = p
            except asyncio.TimeoutError:
                log.warning(f"    {cat_name} sayfa {pg}: timeout — duruyorum")
                break

            # İnsan gibi bekleme (sayfalar arası)
            await human_pause(1.5, 4.0)

    except Exception as e:
        log.warning(f"    {cat_name} hatası: {e}")
    finally:
        await page.close()

    log.info(f"    {cat_name}: {len(products)} ürün toplandı")
    return list(products.values())


# ─────────────────────── SUPABASE UPSERT ───────────────────────

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
                log.error(f"Chunk: {e2}")
        return saved


# ─────────────────────── ANA FONKSİYON ───────────────────────

async def _run_async() -> int:
    log.info("=" * 60)
    log.info("DELHAIZE SCRAPER BAŞLIYOR")
    log.info(f"  {len(CATEGORIES)} top-level kategori")
    log.info("  GetCategoryProductSearch + totalPages pagination")
    log.info("  İnsan davranışı: rastgele gecikme + scroll")
    log.info("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error(".env eksik (SUPABASE_URL veya SUPABASE_SERVICE_KEY)!")
        return 0

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    total_saved = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        context = await browser.new_context(
            user_agent=CHROME_UA,
            viewport={"width": 1280, "height": 900},
            locale="nl-BE",
            timezone_id="Europe/Brussels",
            extra_http_headers={"Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7"},
        )

        for cat_name, cat_code in CATEGORIES:
            log.info(f"\n  [{CATEGORIES.index((cat_name, cat_code))+1}/{len(CATEGORIES)}] {cat_name} ({cat_code})")
            prods = await scrape_category(context, cat_name, cat_code)
            if prods:
                saved = upsert_products(sb, prods)
                total_saved += saved
                log.info(f"    -> {saved} kaydedildi (toplam: {total_saved})")
            await human_pause(3.0, 7.0)

        await browser.close()

    log.info("=" * 60)
    log.info(f"DELHAIZE TAMAMLANDI — Toplam: {total_saved} ürün")
    log.info("=" * 60)
    return total_saved


def run() -> int:
    return asyncio.run(_run_async())


if __name__ == "__main__":
    run()
