"""
Colruyt Belçika SCRAPER — product-search-prs API
Supabase market_chain_products tablosuna upsert eder.
"""

import os
import random
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [COLRUYT] %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

CHAIN_SLUG   = "colruyt_be"
COUNTRY_CODE = "BE"
CURRENCY     = "EUR"

API_URL  = "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc/cg/nl/api/product-search-prs"
PLACE_ID = "762"
API_KEY  = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
PAGE_SIZE = 20
MAX_PRODUCTS = 60000
MAX_RETRIES  = 4

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.colruyt.be/nl/producten",
    "Origin":  "https://www.colruyt.be",
    "X-CG-APIKey": API_KEY,
}


def human_delay(min_s=2.0, max_s=6.0):
    time.sleep(random.uniform(min_s, max_s))


def fetch_page(session, skip: int) -> dict | None:
    params = {
        "placeId":     PLACE_ID,
        "size":        PAGE_SIZE,
        "skip":        skip,
        "isAvailable": "true",
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(API_URL, params=params, headers=HEADERS, timeout=25)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 456):
                wait = 120 * (2 ** attempt) + random.uniform(0, 60)
                log.warning(f"Rate limit ({resp.status_code}) — {wait:.0f}s bekleniyor...")
                time.sleep(wait)
                continue
            if resp.status_code in (401, 403, 406):
                log.error(f"HTTP {resp.status_code} — API key veya oturum geçersiz. colruyt_scraper.py içinde API_KEY'i güncelle.")
                return None
            log.warning(f"HTTP {resp.status_code} (skip={skip})")
            return None
        except Exception as e:
            wait = 15 * (2 ** attempt) + random.uniform(0, 10)
            log.warning(f"İstek hatası: {e} — {wait:.0f}s sonra tekrar...")
            time.sleep(wait)
    return None


def _to_iso_date(val: str) -> str | None:
    """DD-MM-YYYY veya YYYY-MM-DD formatını YYYY-MM-DD'ye çevirir."""
    if not val:
        return None
    val = val.strip()[:10]
    if len(val) == 10 and val[2] == "-" and val[5] == "-":
        # DD-MM-YYYY → YYYY-MM-DD
        return f"{val[6:10]}-{val[3:5]}-{val[0:2]}"
    return val  # zaten YYYY-MM-DD


def parse_product(p: dict) -> dict | None:
    try:
        product_code = str(p.get("retailProductNumber") or p.get("technicalArticleNumber") or "")
        name = (p.get("name") or "").strip()
        if not product_code or not name:
            return None

        price_info = p.get("price") or {}
        basic_price = price_info.get("basicPrice")
        if basic_price is None:
            return None
        price = float(basic_price)

        in_promo   = bool(p.get("inPromo") or price_info.get("isPromoActive"))
        promo_list = p.get("promotion") or []
        pr0        = promo_list[0] if promo_list and isinstance(promo_list[0], dict) else {}

        promo_price = None
        if in_promo and pr0:
            for key in ("promotionPrice", "price", "discountedPrice"):
                v = pr0.get(key)
                if v is not None:
                    promo_price = float(v)
                    break

        promo_from  = None
        promo_until = None
        if pr0:
            for key in ("publicationStartDate", "validFrom", "startDate", "fromDate"):
                if pr0.get(key):
                    promo_from = _to_iso_date(str(pr0[key]))
                    break
            for key in ("publicationEndDate", "validTo", "endDate", "toDate"):
                if pr0.get(key):
                    promo_until = _to_iso_date(str(pr0[key]))
                    break

        category = p.get("topCategoryName") or ""
        brand    = p.get("brand") or p.get("seoBrand") or ""

        # Görsel URL
        image_url = ""
        for img_key in ("squareImage", "mainImage", "imageUrl"):
            v = p.get(img_key)
            if v and isinstance(v, str):
                image_url = v
                break
            if v and isinstance(v, dict):
                image_url = v.get("url") or v.get("xlargeUrl") or ""
                if image_url:
                    break

        return {
            "chain_slug":           CHAIN_SLUG,
            "country_code":         COUNTRY_CODE,
            "external_product_id":  product_code,
            "name":                 name,
            "brand":                brand,
            "category_name":        category,
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


def upsert_products(sb: Client, products: list) -> int:
    if not products:
        return 0
    try:
        sb.table("market_chain_products").upsert(
            products, on_conflict="chain_slug,external_product_id"
        ).execute()
        return len(products)
    except Exception as e:
        log.error(f"Upsert hatası: {e}")
        # Küçük chunk'larla tekrar dene
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


def run() -> int:
    import requests as req

    log.info("=" * 60)
    log.info("COLRUYT SCRAPER BAŞLIYOR (product-search-prs API)")
    log.info("=" * 60)

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error(".env dosyasında SUPABASE_URL veya SUPABASE_SERVICE_KEY eksik!")
        return 0

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    session = req.Session()
    total_saved  = 0
    skip         = 0
    total_found  = None
    buffer       = []
    stale_pages  = 0
    seen_ids     = set()

    while skip < MAX_PRODUCTS:
        data = fetch_page(session, skip)
        if data is None:
            log.error("API yanıt vermedi, Colruyt durduruluyor.")
            break

        products_raw = data.get("products") or []
        if total_found is None:
            total_found = data.get("totalProductsFound") or 0
            log.info(f"Toplam ürün (API): {total_found}")

        if not products_raw:
            stale_pages += 1
            if stale_pages >= 3:
                log.info("Ardışık 3 boş sayfa — tamamlandı.")
                break
            skip += PAGE_SIZE
            human_delay(2, 5)
            continue
        stale_pages = 0

        new_products = []
        for raw in products_raw:
            parsed = parse_product(raw)
            if parsed and parsed["external_product_id"] not in seen_ids:
                seen_ids.add(parsed["external_product_id"])
                new_products.append(parsed)

        buffer.extend(new_products)
        log.info(f"skip={skip} → {len(products_raw)} ürün, yeni={len(new_products)}, buffer={len(buffer)}")

        if len(buffer) >= 200:
            saved = upsert_products(sb, buffer)
            total_saved += saved
            buffer = []
            log.info(f"  → {saved} kaydedildi (toplam: {total_saved})")

        skip += PAGE_SIZE
        if total_found and skip >= total_found:
            log.info("Tüm ürünler alındı.")
            break

        human_delay(4.0, 9.0)

    # Kalan buffer
    if buffer:
        saved = upsert_products(sb, buffer)
        total_saved += saved
        log.info(f"  → {saved} kaydedildi (toplam: {total_saved})")

    log.info("=" * 60)
    log.info(f"COLRUYT TAMAMLANDI — Toplam: {total_saved} ürün")
    log.info("=" * 60)
    return total_saved


if __name__ == "__main__":
    run()
