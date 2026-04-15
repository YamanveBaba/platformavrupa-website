"""
Carrefour Belçika SCRAPER — Playwright (headed+stealth) + dataLayer interception
Supabase market_chain_products tablosuna upsert eder.

Strateji:
  - Headed browser (Cloudflare headless tespitini atlar)
  - playwright-stealth ile otomasyon işaretleri gizlenir
  - Ana sayfadan doğru kategori URL'leri alınır (/nl/fruit-en-groenten vb.)
  - Her sayfada scroll ile tüm ürünler yüklenir
  - dataLayer (dlDataItems) + DOM fiyat elementlerinden veri çekilir
  - İnsan gibi davranış: rastgele gecikme + scroll
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
from playwright_stealth import Stealth

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CARREFOUR] %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

CHAIN_SLUG   = "carrefour_be"
COUNTRY_CODE = "BE"
CURRENCY     = "EUR"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

CARREFOUR_BASE = "https://www.carrefour.be"

# Ana sayfadan doğrulanan kategori URL'leri (/nl/... formatı)
CATEGORIES = [
    ("Fruit en groenten",              "/nl/fruit-en-groenten"),
    ("Vlees en vis",                   "/nl/vlees-en-vis"),
    ("Zuivel",                         "/nl/zuivel"),
    ("Dranken",                        "/nl/dranken"),
    ("Brood toast gebak",              "/nl/brood-toast-en-gebak"),
    ("Chocolade koekjes snoep",        "/nl/chocolade-koekjes-en-snoep"),
    ("Diepvries",                      "/nl/diepvries"),
    ("Chips aperitief",                "/nl/chips-en-aperitief"),
    ("Pasta rijst granen",             "/nl/pasta-rijst-granen-en-peulvruchten"),
    ("Conserven smaakmakers",          "/nl/conserven-en-smaakmakers"),
    ("Sauzen kookhulp",                "/nl/sauzen-en-kookhulp"),
    ("Ontbijtgranen smeerpastas",      "/nl/ontbijtgranen-en-smeerpastas"),
    ("Traiteur bereide maaltijden",    "/nl/traiteur-en-bereide-maaltijden"),
    ("Vegan vegetarisch",              "/nl/vegan-en-vegetarisch"),
    ("Gezonde voeding",                "/nl/gezonde-voeding-en-dieet"),
    ("Wereldkeuken",                   "/nl/wereldkeuken"),
    ("Huishouden",                     "/nl/huishouden"),
    ("Verzorging hygiene",             "/nl/verzorging-en-hygiene"),
    ("Baby",                           "/nl/baby"),
    ("Huisdieren",                     "/nl/huisdieren"),
    ("Promoties",                      "/nl/al-onze-promoties"),
]


# ─────────────────────── YARDIMCI ───────────────────────

async def human_pause(min_s: float = 1.5, max_s: float = 4.5):
    await asyncio.sleep(random.uniform(min_s, max_s))


def _parse_price(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else None
    if isinstance(val, str):
        m = re.search(r'(\d+)[,.](\d{2})', val.replace(",", "."))
        if m:
            return float(f"{m.group(1)}.{m.group(2)}")
        # "2,69 €" → 2.69
        clean = re.sub(r'[€\s]', '', val.replace(",", "."))
        try:
            v = float(clean)
            return v if v > 0 else None
        except Exception:
            pass
    return None


def _parse_product_from_datalayer(item: dict, cat_name: str) -> dict | None:
    """dataLayer view_item_list eventindeki ürünü parse eder."""
    try:
        pid  = str(item.get("item_id") or "").strip()
        name = str(item.get("item_name") or "").strip()
        if not pid or not name:
            return None

        price = _parse_price(item.get("price"))
        if price is None:
            return None

        brand    = str(item.get("item_brand") or "").strip()
        category = str(item.get("item_category") or item.get("item_category2") or cat_name).strip()

        return {
            "chain_slug":           CHAIN_SLUG,
            "country_code":         COUNTRY_CODE,
            "external_product_id":  pid,
            "name":                 name,
            "brand":                brand,
            "category_name":        cat_name,
            "price":                price,
            "currency":             CURRENCY,
            "in_promo":             False,
            "promo_price":          None,
            "promo_valid_from":     None,
            "promo_valid_until":    None,
            "image_url":            "",
            "captured_at":          datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.debug(f"Parse hatası: {e}")
        return None


def _parse_product_from_dom(pid: str, name: str, price_text: str,
                             old_price_text: str, cat_name: str) -> dict | None:
    """DOM'dan çekilen ham verileri parse eder."""
    try:
        if not pid or not name:
            return None
        price = _parse_price(price_text)
        if price is None:
            return None

        in_promo    = False
        promo_price = None
        if old_price_text:
            old = _parse_price(old_price_text)
            if old and old > price:
                in_promo    = True
                promo_price = price
                price       = old

        return {
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
            "image_url":            "",
            "captured_at":          datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.debug(f"DOM parse hatası: {e}")
        return None


_EXTRACT_PRODUCTS_JS = """
() => {
    // 1. DOM'dan ürünleri çek
    const domProducts = [];
    document.querySelectorAll(".js-product-tile").forEach(tile => {
        const parent = tile.closest("[data-pid]");
        const pid  = parent?.getAttribute("data-pid") || tile.getAttribute("data-item-id");
        const name = tile.getAttribute("data-item-name");
        const salesEl = tile.querySelector(".sales .value, .price-value, .price .value");
        const oldEl   = tile.querySelector(".strike-through .value, .old-price .value");
        const priceText = salesEl?.textContent?.trim();
        const oldText   = oldEl?.textContent?.trim();

        // Promo badge
        const badge = tile.querySelector(".product-badge, [class*=badge]")?.textContent?.trim()?.substring(0,30);
        const promoEl = tile.querySelector("[class*=promo], [class*=promotion]");

        if (pid && priceText) {
            domProducts.push({ pid, name, priceText, oldText, badge });
        }
    });

    // 2. dataLayer'dan ürünleri çek
    const dlProducts = [];
    document.querySelectorAll("script").forEach(s => {
        const text = s.textContent || "";
        if (text.includes("view_item_list") && text.includes("item_id")) {
            const m = text.match(/dlDataItems = (\\[[\\s\\S]+?\\]);/);
            if (m) {
                try {
                    const events = JSON.parse(m[1]);
                    events.forEach(ev => {
                        if (ev.ecommerce?.items) {
                            dlProducts.push(...ev.ecommerce.items);
                        }
                    });
                } catch(e) {}
            }
        }
    });

    // 3. Toplam ürün sayısı
    const countEl = document.querySelector(".pagination-count, [class*=result-count]");
    const totalText = countEl?.textContent?.trim();
    const totalMatch = totalText?.match(/\\d+/);
    const total = totalMatch ? parseInt(totalMatch[0]) : 0;

    return { domProducts, dlProducts, total };
}
"""


async def scrape_category(context, cat_name: str, cat_path: str) -> list:
    """
    Carrefour kategori sayfasını scrape eder.
    dataLayer + DOM fiyat elementlerinden ürünleri çeker.
    Scroll ile lazy-loaded ürünleri de yükler.
    """
    url = f"{CARREFOUR_BASE}{cat_path}"
    log.info(f"  -> {cat_name}: {url}")
    products = {}

    page = await context.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        if resp and resp.status in (404, 410):
            log.warning(f"    {cat_name}: HTTP {resp.status} — atlanıyor")
            await page.close()
            return []

        if resp and resp.status != 200:
            log.warning(f"    {cat_name}: HTTP {resp.status} — atlanıyor")
            await page.close()
            return []

        await asyncio.sleep(random.uniform(2.5, 4.5))

        # Country selector overlay kaldır
        await page.evaluate(
            'document.querySelectorAll(".country-selector__backdrop,[class*=backdrop]").forEach(e=>e.remove())'
        )

        # İlk veri al
        result = await page.evaluate(_EXTRACT_PRODUCTS_JS)
        dl_prods = result.get("dlProducts", [])
        dom_prods = result.get("domProducts", [])
        total = result.get("total", 0)

        log.info(f"    {cat_name}: toplam={total}, dL={len(dl_prods)}, DOM={len(dom_prods)}")

        # dataLayer ürünleri — brand ve tam fiyat var
        dl_map = {}  # pid → item
        for item in dl_prods:
            pid = str(item.get("item_id") or "").strip()
            if pid:
                dl_map[pid] = item

        # DOM'dan fiyat bilgisi al (dataLayer'da olmayan veya promo kontrolü için)
        dom_price_map = {}  # pid → {priceText, oldText}
        for dp in dom_prods:
            pid = str(dp.get("pid") or "").strip()
            if pid:
                dom_price_map[pid] = dp

        def merge_product(pid, item, dom_info, cat):
            """dataLayer + DOM'dan en iyi ürün kaydını oluştur."""
            try:
                name  = str(item.get("item_name") or dom_info.get("name") or "").strip()
                brand = str(item.get("item_brand") or "").strip()
                if not pid or not name:
                    return None

                # Fiyat: dataLayer önce, sonra DOM
                price = _parse_price(item.get("price"))

                in_promo    = False
                promo_price = None

                if dom_info:
                    old_text   = dom_info.get("oldText")
                    price_text = dom_info.get("priceText")
                    dom_price  = _parse_price(price_text)
                    old_price  = _parse_price(old_text)

                    if price is None:
                        price = dom_price

                    if old_price and dom_price and old_price > dom_price:
                        in_promo    = True
                        promo_price = dom_price
                        price       = old_price
                    elif dom_info.get("badge"):
                        in_promo = True

                if price is None:
                    return None

                cat_name_str = str(item.get("item_category") or cat).strip()

                return {
                    "chain_slug":           CHAIN_SLUG,
                    "country_code":         COUNTRY_CODE,
                    "external_product_id":  pid,
                    "name":                 name,
                    "brand":                brand,
                    "category_name":        cat,
                    "price":                price,
                    "currency":             CURRENCY,
                    "in_promo":             in_promo,
                    "promo_price":          promo_price,
                    "promo_valid_from":     None,
                    "promo_valid_until":    None,
                    "image_url":            "",
                    "captured_at":          datetime.now(timezone.utc).isoformat(),
                }
            except Exception:
                return None

        # Mevcut ürünleri birleştir
        all_pids = set(dl_map.keys()) | set(dom_price_map.keys())
        for pid in all_pids:
            item     = dl_map.get(pid, {})
            dom_info = dom_price_map.get(pid, {})
            p = merge_product(pid, item, dom_info, cat_name)
            if p:
                products[pid] = p

        # Scroll ile daha fazla ürün yükle
        if total > len(products):
            log.info(f"    {cat_name}: Scroll ile kalan {total - len(products)} ürün yükleniyor...")
            prev_count    = len(products)
            stable_rounds = 0

            for step in range(120):  # max 120 scroll adımı (çok büyük kategoriler için)
                at_bottom = await page.evaluate("""
                    () => {
                        window.scrollBy(0, 600);
                        return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 100;
                    }
                """)
                await asyncio.sleep(random.uniform(0.4, 0.9))

                result = await page.evaluate(_EXTRACT_PRODUCTS_JS)
                new_dl   = result.get("dlProducts", [])
                new_dom  = result.get("domProducts", [])

                new_dl_map  = {str(x.get("item_id","")).strip(): x for x in new_dl if x.get("item_id")}
                new_dom_map = {str(x.get("pid","")).strip(): x for x in new_dom if x.get("pid")}

                new_pids = set(new_dl_map.keys()) | set(new_dom_map.keys())
                for pid in new_pids:
                    if pid and pid not in products:
                        item     = new_dl_map.get(pid, {})
                        dom_info = new_dom_map.get(pid, {})
                        p = merge_product(pid, item, dom_info, cat_name)
                        if p:
                            products[pid] = p

                if len(products) == prev_count:
                    stable_rounds += 1
                    if stable_rounds >= 6:
                        break
                    if at_bottom and stable_rounds >= 3:
                        break
                else:
                    stable_rounds = 0
                prev_count = len(products)

                if at_bottom and stable_rounds >= 2:
                    break

                await human_pause(0.2, 0.8)

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
    log.info("CARREFOUR SCRAPER BAŞLIYOR")
    log.info("  headed browser + playwright-stealth (Cloudflare bypass)")
    log.info("  dataLayer + DOM fiyat extraction")
    log.info("  scroll ile lazy-load pagination")
    log.info("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error(".env eksik!")
        return 0

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    total_saved = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Cloudflare headless tespitini atlar
            args=[
                "--no-sandbox",
                "--window-size=1280,900",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = await browser.new_context(
            user_agent=CHROME_UA,
            viewport={"width": 1280, "height": 900},
            locale="nl-BE",
            timezone_id="Europe/Brussels",
            extra_http_headers={"Accept-Language": "nl-BE,nl;q=0.9,fr;q=0.8,en;q=0.7"},
        )
        await Stealth().apply_stealth_async(context)

        # ── Session başlat (ana sayfa + cookie banner) ──
        log.info("\nSession başlatılıyor...")
        init_page = await context.new_page()
        try:
            await init_page.goto(f"{CARREFOUR_BASE}/nl/", wait_until="networkidle", timeout=40000)
            await asyncio.sleep(3)
            await init_page.evaluate(
                'document.querySelectorAll(".country-selector__backdrop,[class*=backdrop]").forEach(e=>e.remove())'
            )
            for sel in [
                "#onetrust-accept-btn-handler",
                "button:has-text('Alle cookies accepteren')",
                "button:has-text('Accepteer alles')",
            ]:
                try:
                    btn = init_page.locator(sel)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    pass
        except Exception as e:
            log.warning(f"Session init hatası: {e}")
        finally:
            await init_page.close()

        # ── Her kategoriyi scrape et ──
        for i, (cat_name, cat_path) in enumerate(CATEGORIES):
            log.info(f"\n  [{i+1}/{len(CATEGORIES)}] {cat_name}")
            prods = await scrape_category(context, cat_name, cat_path)
            if prods:
                saved = upsert_products(sb, prods)
                total_saved += saved
                log.info(f"    -> {saved} kaydedildi (toplam: {total_saved})")
            await human_pause(3.0, 7.0)

        await browser.close()

    log.info("=" * 60)
    log.info(f"CARREFOUR TAMAMLANDI — Toplam: {total_saved} ürün")
    log.info("=" * 60)
    return total_saved


def run() -> int:
    return asyncio.run(_run_async())


if __name__ == "__main__":
    run()
