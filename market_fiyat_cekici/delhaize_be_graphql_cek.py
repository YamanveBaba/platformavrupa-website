# -*- coding: utf-8 -*-
"""
Delhaize Belçika — GetCategoryProductSearch (Apollo GraphQL, persisted query) ile kategori sayfalama.
Ürün karosu zaten fiyat içerir; tüm ana kategoriler https://www.delhaize.be/nl/shop HTML'inden toplanır.

İnsan benzeri: istekler arası rastgele gecikme. Cookie gerekmez (çoğu ortamda); 403 olursa delhaize_cookie.txt ekleyin.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

try:
    import requests
except ImportError:
    raise SystemExit("HATA: pip install requests")

# Apollo persisted query sabitleri (tarayıcıdan; client-version site güncellenince degisebilir)
CONFIG: Dict[str, Any] = {
    "api_base": "https://www.delhaize.be/api/v1/",
    "shop_url": "https://www.delhaize.be/nl/shop",
    "lang": "nl",
    "customer_segment": "W70T930_A",
    "page_size": 20,
    "graphql_client_name": "be-dll-web-stores",
    "graphql_client_version": "1beae2758b4bf4b63f79d933767834fed191a746",
    "hash_category_search": "189e7cb5a6ba93e55dc63e4eef0ad063ca3e8aedb0bdf2a58124e02d5d5d69a2",
    "op_id_category_search": "841bc048e809cf7f460d0473995516d39464c46b70952bd8b26235f881f571b5",
    "max_categories": 0,  # 0 = hepsi
    "max_total_products": 80000,
    "max_pages_per_category": 0,  # 0 = tum sayfalar
    "request_timeout": 35,
}

DELAY_NORMAL = (0.9, 2.6)
DELAY_SLOW = (4.0, 9.0)


def human_delay() -> None:
    if random.random() < 0.1:
        time.sleep(random.uniform(*DELAY_SLOW))
    else:
        time.sleep(random.uniform(*DELAY_NORMAL))


def load_cookie(script_dir: str) -> Optional[str]:
    for name in ("delhaize_cookie.txt", "cookie_delhaize.txt"):
        path = os.path.join(script_dir, name)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                line = f.read().strip().split("\n")[0].strip()
            if line.lower().startswith("cookie:"):
                line = line[7:].strip()
            return line or None
    return None


def discover_category_codes(session: requests.Session, headers: dict) -> List[str]:
    r = session.get(
        CONFIG["shop_url"],
        headers={**headers, "Accept": "text/html"},
        timeout=CONFIG["request_timeout"],
    )
    r.raise_for_status()
    raw = re.findall(r"/c/(v2[A-Za-z0-9]{2,20})", r.text, flags=re.I)

    def norm_code(c: str) -> str:
        c = c.strip()
        if len(c) < 3:
            return c
        return "v2" + c[2:].upper()

    return sorted({norm_code(c) for c in raw})


def load_categories_file(script_dir: str) -> Optional[List[str]]:
    path = os.path.join(script_dir, "delhaize_be_categories.txt")
    if not os.path.isfile(path):
        return None
    out: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out or None


def graphql_headers(operation_name: str, operation_id: str) -> dict:
    return {
        "accept": "*/*",
        "apollographql-client-name": CONFIG["graphql_client_name"],
        "apollographql-client-version": CONFIG["graphql_client_version"],
        "content-type": "application/json",
        "x-apollo-operation-name": operation_name,
        "x-apollo-operation-id": operation_id,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.delhaize.be/nl/shop",
        "Origin": "https://www.delhaize.be",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def fetch_category_page(
    session: requests.Session,
    headers: dict,
    category: str,
    page_number: int,
    page_size: int,
) -> dict:
    variables = {
        "lang": CONFIG["lang"],
        "searchQuery": ":relevance",
        "sort": "relevance",
        "category": category,
        "pageNumber": page_number,
        "pageSize": page_size,
        "filterFlag": True,
        "fields": "PRODUCT_TILE",
        "plainChildCategories": True,
        "customerSegment": CONFIG["customer_segment"],
    }
    extensions = {
        "persistedQuery": {"version": 1, "sha256Hash": CONFIG["hash_category_search"]},
    }
    params = {
        "operationName": "GetCategoryProductSearch",
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(extensions, separators=(",", ":")),
    }
    h = graphql_headers("GetCategoryProductSearch", CONFIG["op_id_category_search"])
    h.update(headers)
    r = session.get(
        CONFIG["api_base"],
        params=params,
        headers=h,
        timeout=CONFIG["request_timeout"],
    )
    r.raise_for_status()
    return r.json()


def tile_to_record(tile: dict) -> Optional[dict]:
    code = str(tile.get("code") or "").strip()
    if not code:
        return None
    price_obj = tile.get("price") or {}
    try:
        val = float(price_obj.get("value")) if price_obj.get("value") is not None else 0.0
    except (TypeError, ValueError):
        val = 0.0
    was = price_obj.get("wasPrice")
    try:
        was_f = float(was) if was is not None else None
    except (TypeError, ValueError):
        was_f = None
    strikethrough = bool(price_obj.get("showStrikethroughPrice"))
    in_promo = strikethrough or (was_f is not None and was_f > val)
    promo_price = was_f if in_promo and was_f and was_f > val else None
    flc = tile.get("firstLevelCategory") or {}
    cat_name = flc.get("name") if isinstance(flc, dict) else None
    parts = [price_obj.get("supplementaryPriceLabel1"), price_obj.get("supplementaryPriceLabel2")]
    supp = " ".join(str(p) for p in parts if p) or None
    return {
        "productCode": code,
        "name": (tile.get("name") or "")[:2000],
        "brand": ((tile.get("manufacturerName") or "")[:500] or None),
        "basicPrice": val,
        "promoPrice": promo_price,
        "inPromo": bool(in_promo),
        "topCategoryName": ((cat_name or "")[:500] or None),
        "unitContent": ((supp or "")[:200] or None),
        "url": tile.get("url"),
    }


def run_scrape(
    *,
    dry_run: bool,
    limit_categories: int,
    max_pages_per_category: int,
    no_pause: bool,
) -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    cookie = load_cookie(script_dir)
    extra_h: dict = {}
    if cookie:
        extra_h["Cookie"] = cookie

    session = requests.Session()
    categories = load_categories_file(script_dir)
    if not categories:
        print("Kategori listesi: delhaize.be/nl/shop uzerinden kesif...")
        categories = discover_category_codes(session, extra_h)
    if limit_categories > 0:
        categories = categories[:limit_categories]
    print(f"Islenecek kategori sayisi: {len(categories)}")

    by_code: Dict[str, dict] = {}
    errors = 0

    for ci, cat in enumerate(categories):
        print(f"\n[{ci + 1}/{len(categories)}] Kategori {cat}")
        page = 0
        total_pages = 1
        while page < total_pages:
            human_delay()
            try:
                data = fetch_category_page(session, extra_h, cat, page, CONFIG["page_size"])
            except Exception as e:
                print(f"  HATA sayfa {page}: {e}")
                errors += 1
                break
            if data.get("errors"):
                print(f"  GraphQL errors: {data['errors'][:1]}")
                errors += 1
                break
            cps = (data.get("data") or {}).get("categoryProductSearch") or {}
            products = cps.get("products") or []
            pag = cps.get("pagination") or {}
            total_pages = int(pag.get("totalPages") or 1)
            if max_pages_per_category > 0:
                total_pages = min(total_pages, max_pages_per_category)
            current = int(pag.get("currentPage") or page)
            print(f"  sayfa {current + 1}/{total_pages} urun {len(products)}")

            for tile in products:
                if not isinstance(tile, dict):
                    continue
                rec = tile_to_record(tile)
                if rec:
                    by_code[rec["productCode"]] = rec

            if dry_run:
                print("  [DRY-RUN] ilk kategoride durduruluyor.")
                break

            if len(by_code) >= CONFIG["max_total_products"]:
                print("  max_total_products limite ulasildi.")
                break

            page += 1

        if dry_run:
            break
        if len(by_code) >= CONFIG["max_total_products"]:
            break

    urunler = list(by_code.values())
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = os.path.join(cikti_dir, f"delhaize_be_producten_{tarih}.json")
    payload = {
        "kaynak": "Delhaize Belçika GraphQL",
        "chain_slug": "delhaize_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "kategori_sayisi": len(categories),
        "urun_sayisi": len(urunler),
        "dry_run": dry_run,
        "hata_sayisi": errors,
        "urunler": urunler,
    }

    if not dry_run:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nTamam: {len(urunler)} benzersiz urun -> {out_path}")
    else:
        print(f"\n[DRY-RUN] {len(urunler)} urun toplandi; dosya yazilmadi.")

    if not no_pause:
        input("\nCikmak icin Enter...")
    return 0 if urunler or dry_run else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Delhaize BE GraphQL urun+fiyat cekici")
    ap.add_argument("--dry-run", action="store_true", help="Sadece ilk kategorinin bir kismini dene")
    ap.add_argument("--limit-categories", type=int, default=0, help="Ilk N kategori (0=hepsi)")
    ap.add_argument(
        "--max-pages-per-category",
        type=int,
        default=0,
        help="Kategori basina max sayfa (0=tum sayfalar; test icin or. 2)",
    )
    ap.add_argument("--no-pause", action="store_true", help="Sonunda Enter bekleme")
    args = ap.parse_args()
    return run_scrape(
        dry_run=args.dry_run,
        limit_categories=args.limit_categories or 0,
        max_pages_per_category=args.max_pages_per_category or 0,
        no_pause=args.no_pause,
    )


if __name__ == "__main__":
    raise SystemExit(main())
