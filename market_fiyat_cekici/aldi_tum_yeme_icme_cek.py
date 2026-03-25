# -*- coding: utf-8 -*-
"""
ALDI Belçika — tam producten ağacı fiyat çekici (Playwright).
- Çoklu tohum: /nl/producten.html + /nl/producten/assortiment.html
- BFS: /nl/producten/.../*.html (kara liste ile gürültü elenir)
- İnsansı mod: rastgele gecikme, UA, viewport, nl-BE locale
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections import Counter, deque
from datetime import datetime
from typing import Callable, List, Optional, Set
from urllib.parse import urljoin, urlparse

# Varsayılan tohum URL'leri (plan)
DEFAULT_SEEDS = [
    "https://www.aldi.be/nl/producten.html",
    "https://www.aldi.be/nl/producten/assortiment.html",
]

def _is_allowed_product_path(path: str) -> bool:
    """Hub /nl/producten.html ve alt yollar /nl/producten/.../*.html"""
    if not path:
        return False
    pl = path.lower()
    if not pl.endswith(".html"):
        return False
    if pl == "/nl/producten.html":
        return True
    return pl.startswith("/nl/producten/") and len(pl) > len("/nl/producten/")

# Kara liste: path veya tam URL parçası (küçük harf)
PATH_DENY_SUBSTRINGS = (
    "zoekresultaten",
    "winkelwagen",
    "mandje",
    "checkout",
    "bestellen",
    "mijn-aldi",
    "mijn_aldi",
    "/login",
    "registr",
    "algemene-voorwaarden",
    "privacy",
    "cookie",
    "gegevensbescherming",
    "/help/",
    "/hulp/",
    "contact",
    "javascript:",
    ".pdf",
)

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _aldi_promo_dates_from_product_info(info: dict) -> tuple[Optional[str], Optional[str]]:
    """
    data-article içindeki productInfo'dan kampanya başlangıç/bitiş (site sürümüne göre alan adları değişebilir).
    """
    if not isinstance(info, dict):
        return None, None

    def pick(*keys: str) -> Optional[str]:
        for k in keys:
            v = info.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return None

    start = pick(
        "promotionStartDate",
        "promotionalPriceValidFrom",
        "promoValidFrom",
        "offerStartDate",
        "discountStartDate",
        "priceValidFrom",
    )
    end = pick(
        "promotionEndDate",
        "promotionalPriceValidTo",
        "promoValidUntil",
        "offerEndDate",
        "discountEndDate",
        "priceValidTo",
    )
    if start or end:
        return start, end

    start_f, end_f = None, None
    for k, v in info.items():
        if not isinstance(v, (str, int, float)) or v is None:
            continue
        kl = k.lower()
        vs = str(v).strip()
        if not vs:
            continue
        if start_f is None and (
            ("start" in kl or "from" in kl or "begin" in kl)
            and ("promo" in kl or "offer" in kl or "discount" in kl or "price" in kl or "valid" in kl)
        ):
            start_f = vs
        if end_f is None and (
            ("end" in kl or "until" in kl)
            and ("promo" in kl or "offer" in kl or "discount" in kl or "price" in kl or "valid" in kl)
        ):
            end_f = vs
    return start_f, end_f


def _normalize_aldi_product_url(href: str, base: str = "https://www.aldi.be") -> Optional[str]:
    if not href or href.startswith("javascript:"):
        return None
    abs_url = urljoin(base + "/", href.strip())
    p = urlparse(abs_url)
    if p.netloc.lower() not in ("www.aldi.be", "aldi.be"):
        return None
    if p.netloc.lower() == "aldi.be":
        abs_url = abs_url.replace("://aldi.be/", "://www.aldi.be/", 1)
        p = urlparse(abs_url)
    path = p.path or ""
    if not path.lower().endswith(".html"):
        return None
    if not _is_allowed_product_path(path):
        return None
    low = abs_url.lower()
    plow = path.lower()
    for bad in PATH_DENY_SUBSTRINGS:
        if bad in low or bad in plow:
            return None
    # Fragment kaldır
    return abs_url.split("#")[0].rstrip("/") or None


def _page_delay_seconds(args: argparse.Namespace) -> float:
    if args.human:
        return random.uniform(args.page_delay_min, args.page_delay_max)
    return float(args.page_delay_min)


def _scroll_pause_ms(args: argparse.Namespace) -> int:
    if args.human:
        return int(random.uniform(args.scroll_delay_min, args.scroll_delay_max))
    return int(args.scroll_delay_min)


def _scroll_step_px(args: argparse.Namespace) -> int:
    if args.human:
        return int(random.uniform(args.scroll_step_min, args.scroll_step_max))
    return int((args.scroll_step_min + args.scroll_step_max) / 2)


def main() -> None:
    args = _parse_args()
    no_pause = args.no_pause

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: Playwright yüklü değil.")
        print("Lütfen: pip install playwright   sonra   playwright install chromium")
        if not no_pause:
            input("\nÇıkmak için Enter'a basın...")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    seeds = [s.strip() for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        seeds = list(DEFAULT_SEEDS)

    print("ALDI Belçika — producten ağacı (tam katalog) çekiliyor...")
    print(f"  Tohumlar: {len(seeds)} adet")
    print(f"  max_pages={args.max_pages or 'sınırsız'}  max_scroll_steps={args.max_scroll_steps}")
    print(f"  human={args.human}  headed={args.headed}\n")

    skipped_deny = 0
    products_by_id: dict = {}
    to_visit: List[str] = []
    visited: Set[str] = set()
    for s in seeds:
        n = _normalize_aldi_product_url(s)
        if n:
            to_visit.append(n)
        else:
            to_visit.append(s.strip())

    def enqueue_from_page() -> int:
        nonlocal skipped_deny
        links = page.evaluate(
            """
            () => {
                const out = new Set();
                document.querySelectorAll('a[href]').forEach(a => {
                    const h = a.getAttribute('href');
                    if (h) out.add(a.href || h);
                });
                return Array.from(out);
            }
            """
        )
        added = 0
        for href in links or []:
            nu = _normalize_aldi_product_url(href)
            if not nu:
                if href and "/nl/producten/" in href.lower() and href.lower().endswith(".html"):
                    skipped_deny += 1
                continue
            if nu not in visited and nu not in to_visit:
                to_visit.append(nu)
                added += 1
        return added

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            slow_mo=int(args.slow_mo),
        )
        context = browser.new_context(
            user_agent=CHROME_UA,
            viewport={"width": args.viewport_w, "height": args.viewport_h},
            locale="nl-BE",
            timezone_id="Europe/Brussels",
        )
        page = context.new_page()

        def collect_visible_products() -> None:
            tiles = page.query_selector_all("[data-article]")
            for tile in tiles:
                try:
                    raw = tile.get_attribute("data-article")
                    if not raw:
                        continue
                    json_str = raw.replace("&quot;", '"')
                    data = json.loads(json_str)
                    info = data.get("productInfo") or {}
                    cat = data.get("productCategory") or {}
                    pid = info.get("productID")
                    if not pid:
                        continue
                    promo_start, promo_end = _aldi_promo_dates_from_product_info(info)
                    row = {
                        "productID": pid,
                        "productName": info.get("productName", ""),
                        "brand": info.get("brand", ""),
                        "priceWithTax": info.get("priceWithTax"),
                        "promoPrice": info.get("promoPrice") or info.get("strikePrice"),
                        "inPromotion": info.get("inPromotion", False),
                        "category": cat.get("primaryCategory", ""),
                    }
                    if promo_start:
                        row["promotionStartDate"] = promo_start
                    if promo_end:
                        row["promotionEndDate"] = promo_end
                    products_by_id[pid] = row
                except (json.JSONDecodeError, TypeError):
                    continue

        def scroll_and_collect() -> None:
            page.wait_for_timeout(_scroll_pause_ms(args) + (500 if not args.human else random.randint(200, 800)))
            collect_visible_products()
            step = 0
            counts_tail: deque = deque(maxlen=max(4, args.scroll_stable_rounds))
            while True:
                step += 1
                if args.max_scroll_steps and step > args.max_scroll_steps:
                    break
                px = _scroll_step_px(args)
                reached_bottom = page.evaluate(
                    f"""
                    () => {{
                        window.scrollBy(0, {px});
                        return (window.innerHeight + window.scrollY) >= document.body.scrollHeight - 12;
                    }}
                    """
                )
                page.wait_for_timeout(_scroll_pause_ms(args))
                collect_visible_products()
                n = len(products_by_id)
                counts_tail.append(n)
                if reached_bottom:
                    if len(counts_tail) >= args.scroll_stable_rounds:
                        if len(set(counts_tail)) == 1:
                            break
                if step % 10 == 0 and args.human:
                    time.sleep(random.uniform(0.15, 0.45))

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(_scroll_pause_ms(args))
            collect_visible_products()

        try:
            while to_visit:
                url = to_visit.pop(0)
                nu = _normalize_aldi_product_url(url) or url
                if nu in visited:
                    continue
                if args.max_pages and len(visited) >= args.max_pages:
                    to_visit.insert(0, nu)
                    print(f"  Maksimum sayfa ({args.max_pages}) doldu; duruluyor.")
                    break
                visited.add(nu)
                page_idx = len(visited)

                try:
                    page.goto(nu, wait_until="domcontentloaded", timeout=45000)
                except Exception as e:
                    print(f"  Atlandı (yüklenemedi): {nu[:72]}… — {e}")
                    continue

                delay = _page_delay_seconds(args)
                time.sleep(delay)

                has_products = page.query_selector("[data-article]") is not None

                if has_products:
                    n_before = len(products_by_id)
                    scroll_and_collect()
                    n_after = len(products_by_id)
                    added = n_after - n_before
                    short = nu.rstrip("/").split("/")[-1].replace(".html", "")
                    print(f"  [{page_idx}] {short}: +{added} ürün (toplam {n_after})")
                else:
                    new_links = enqueue_from_page()
                    short = nu.rstrip("/").split("/")[-1].replace(".html", "")
                    print(f"  [{page_idx}] {short}: hub/kategori, kuyruğa +{new_links} yeni URL")

            context.close()
            browser.close()

        except Exception:
            context.close()
            browser.close()
            raise

    products = list(products_by_id.values())
    sayfa_sayisi = len(visited)
    print(f"\nOzet: taranan_sayfa={sayfa_sayisi}  benzersiz_urun={len(products)}  kara_liste_atlanan_link~{skipped_deny}")

    cat_ctr = Counter((p.get("category") or "(kategori yok)") for p in products)
    print("Kategori dağılımı (özet, en çok ürün olan 12):")
    for name, cnt in cat_ctr.most_common(12):
        label = (name[:56] + "…") if len(str(name)) > 57 else name
        print(f"  {cnt:5}  {label}")
    if len(cat_ctr) > 12:
        print(f"  ... toplam {len(cat_ctr)} farklı kategori etiketi")

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya_adi = f"aldi_be_tum_yeme_icme_{tarih}.json"
    dosya_yolu = os.path.join(cikti_dir, dosya_adi)

    cikti = {
        "kaynak": "ALDI Belçika",
        "chain_slug": "aldi_be",
        "country_code": "BE",
        "kapsam": "Tüm producten ağacı (nl/producten, kara liste filtreli; assortiment + verse producten vb.)",
        "tohum_url_listesi": seeds,
        "cekilme_tarihi": datetime.now().isoformat(),
        "taranan_sayfa_sayisi": sayfa_sayisi,
        "urun_sayisi": len(products),
        "kara_liste_atlanan_link_tahmini": skipped_deny,
        "insansı_mod": args.human,
        "not_fiyat_gecerliligi": "ALDI Belçika fiyatları genelde haftalık broşürle (Pazartesi-Cumartesi) güncellenir. Bu veri çekim anındaki sitedeki fiyatlardır; pratikte çekim yapılan hafta için geçerli kabul edilebilir.",
        "not_indirim": "Her üründe 'inPromotion': true/false alanı vardır. true = sitede kampanya/indirim işaretli, false = normal fiyat. Broşürdeki ürünler sitede listeleniyorsa dahildir.",
        "urunler": products,
    }

    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print(f"Tamamlandı. Dosya: {dosya_yolu}")
    if not no_pause:
        input("\nÇıkmak için Enter'a basın...")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="ALDI BE — tam producten katalog (Playwright BFS + data-article)"
    )
    ap.add_argument("--no-pause", action="store_true", help="Sonunda Enter bekleme")
    ap.add_argument(
        "--seeds",
        type=str,
        default=",".join(DEFAULT_SEEDS),
        help="Virgülle ayrılmış tohum URL'leri",
    )
    ap.add_argument(
        "--max-pages",
        type=int,
        default=600,
        help="Taranacak en fazla sayfa (0=sınırsız, dikkatli kullanın)",
    )
    ap.add_argument(
        "--max-scroll-steps",
        type=int,
        default=200,
        help="Ürün sayfası başına en fazla kaydırma adımı (0=sadece alt + doygunluk)",
    )
    ap.add_argument(
        "--scroll-stable-rounds",
        type=int,
        default=5,
        help="Altta ürün sayısı bu kadar adım sabit kalırsa kaydırmayı bitir",
    )
    ap.add_argument(
        "--human",
        action="store_true",
        help="Rastgele gecikmeler + scroll adım/jitter (önerilen)",
    )
    ap.add_argument(
        "--page-delay-min",
        type=float,
        default=2.0,
        help="Sayfalar arası min bekleme (sn); human'da rastgele min-max arası",
    )
    ap.add_argument(
        "--page-delay-max",
        type=float,
        default=4.5,
        help="human modda sayfalar arası max bekleme (sn)",
    )
    ap.add_argument(
        "--scroll-delay-min",
        type=float,
        default=700,
        help="Kaydırma sonrası min bekleme (ms)",
    )
    ap.add_argument(
        "--scroll-delay-max",
        type=float,
        default=1600,
        help="human modda kaydırma sonrası max bekleme (ms)",
    )
    ap.add_argument(
        "--scroll-step-min",
        type=int,
        default=400,
        help="Kaydırma adımı min (px)",
    )
    ap.add_argument(
        "--scroll-step-max",
        type=int,
        default=700,
        help="Kaydırma adımı max (px); human'da rastgele",
    )
    ap.add_argument("--viewport-w", type=int, default=1366)
    ap.add_argument("--viewport-h", type=int, default=768)
    ap.add_argument(
        "--slow-mo",
        type=int,
        default=0,
        help="Playwright slow_mo (ms); insansı his için örn. 30-80",
    )
    ap.add_argument("--headed", action="store_true", help="Tarayıcı penceresini göster")
    return ap.parse_args()


if __name__ == "__main__":
    main()
