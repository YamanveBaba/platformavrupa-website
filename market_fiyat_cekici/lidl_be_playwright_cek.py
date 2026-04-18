# -*- coding: utf-8 -*-
"""
Lidl Belçika — Playwright ile urun+fiyat (DOM).

- search: sabit arama kelimeleri + "Meer laden" (hizli ornek / kismi liste).
- categories: ana sayfa + /c/nl-BE ... keşfi veya lidl_be_category_urls.txt;
  her kategori URL'sinde "Meer laden" ile mumkun oldugunca tum grid (tam katalogya yakin).
- discover_urls: BFS ile /c/nl-BE/.../s* ve /h/nl-BE/.../h* liste URL'lerini toplar;
  cikti: lidl_be_api_categories_autogen.txt (Mindshift API dosyasi ile birlestirilebilir).

Cikti: cikti/lidl_be_producten_*.json (json_to_supabase_yukle.py -> lidl_be)
  veya discover_urls modunda script klasorundeki *_autogen.txt
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from datetime import datetime
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set
from urllib.parse import urlparse

CONFIG = {
    "base": "https://www.lidl.be",
    "search_queries": ["melk", "brood", "kaas", "appel", "water", "pasta", "koffie", "yoghurt"],
    "max_load_more_clicks": 25,
    "max_load_more_clicks_categories": 220,
    "category_discovery_urls": (
        "https://www.lidl.be/",
        "https://www.lidl.be/c/nl-BE",
    ),
    # /c/nl-BE/.../s* cogu "hub"; asil grid alt kategorilerde. BFS ile genislet.
    "bfs_max_pages": 220,
    "category_url_block_substrings": (
        "algemene-voorwaarden",
        "privacy",
        "cookie",
        "contact",
        "vacature",
        "folder",
        "nieuwsbrief",
        "impressum",
        "disclaimer",
        "retour",
        "wettelijk",
        "klantenservice",
        "veelgestelde-vragen",
    ),
    "stale_rounds_limit": 4,
    # Kategoride Meer laden sonrasi DOM gec gelir; "yeni urun yok" yanlis tetiklenmesin.
    "stale_rounds_limit_categories": 14,
    "goto_timeout_ms": 90000,
}


def human_pause() -> None:
    time.sleep(random.uniform(1.2, 3.2))


def try_accept_cookies(page) -> None:
    selectors = [
        'button:has-text("Alles accepteren")',
        'button:has-text("Accepteren")',
        'button:has-text("Accept all")',
        '[id*="accept-all" i]',
        '[class*="cookie" i] button',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2000):
                loc.click(timeout=5000)
                time.sleep(1.0)
                return
        except Exception:
            continue


def extract_products_from_page(page) -> List[Dict[str, Any]]:
    return page.evaluate(
        """
        () => {
          const out = [];
          const seen = new Set();
          function productKeyFromHref(href) {
            try {
              const u = new URL(href, window.location.origin);
              const path = u.pathname || '';
              const m = path.match(/\\/(p\\d+)(?:\\/|$)/i);
              if (m) return m[1];
              const seg = path.split('/').filter(Boolean).pop();
              return seg || path;
            } catch (e) {
              const path = (href || '').split('?')[0];
              const m = path.match(/\\/(p\\d+)(?:\\/|$)/i);
              return m ? m[1] : path;
            }
          }
          document.querySelectorAll('a[href*="/p/"]').forEach(a => {
            const href = a.getAttribute('href') || '';
            const key = productKeyFromHref(href);
            if (!key || seen.has(key)) return;
            seen.add(key);
            const tile =
              a.closest('.odsc-tile') ||
              a.closest('[class*="product-grid-box"]') ||
              a.closest('article') ||
              a.closest('[class*="tile"]') ||
              a.parentElement;
            const text = (tile && tile.innerText) ? tile.innerText : (a.innerText || '');
            out.push({ key, href, text });
          });
          return out;
        }
        """
    )


def parse_lidl_tile_prices(text: str) -> tuple[Optional[float], Optional[float], bool]:
    """
    Lidl kart metninden EUR fiyatlari: genelde '4.99 -20% 3.99' (iki ondalik).
    Degerlendirme '4.7/5' tek ondalik oldugu icin \\d+[.,]\\d{2} ile alinmaz.
    """
    if not text:
        return None, None, False
    norm = text.replace("\xa0", " ")
    amounts: List[float] = []
    for m in re.finditer(r"\b(\d+[.,]\d{2})\b", norm):
        try:
            v = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        if 0.05 <= v < 500:
            amounts.append(v)
    if not amounts:
        m = re.search(r"€\s*(\d+[.,]\d{2})|(\d+[.,]\d{2})\s*(?:€|EUR)", norm)
        if m:
            raw = m.group(1) or m.group(2)
            try:
                amounts = [float(raw.replace(",", "."))]
            except ValueError:
                amounts = []
    if not amounts:
        return None, None, False
    pct = bool(re.search(r"-\s*\d+\s*%", norm)) or ("%" in norm and len(amounts) >= 2)
    if pct and len(amounts) >= 2:
        hi, lo = max(amounts), min(amounts)
        return hi, lo, True
    return amounts[-1], None, False


def parse_name_from_tile(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines:
        if re.match(r"^[\d,.\s€]+$", ln):
            continue
        if len(ln) > 2:
            return ln[:500]
    return (lines[0] if lines else "")[:500]


def category_label_from_url(url: str) -> str:
    try:
        path = urlparse(url).path.strip("/").split("/")
        if len(path) >= 3 and path[0] == "c" and path[1] == "nl-BE":
            return path[2][:200]
    except Exception:
        pass
    return "category"


def category_url_blocked(url: str) -> bool:
    u = (url or "").lower()
    return any(b in u for b in CONFIG["category_url_block_substrings"])


COLLECT_CATEGORY_LINKS_JS = r"""
() => {
  const s = new Set();
  document.querySelectorAll('a[href*="/c/nl-BE/"]').forEach(a => {
    let h = a.getAttribute('href') || '';
    if (!/\/s\d+(\?|$)/i.test(h)) return;
    try { h = new URL(h, location.origin).href; } catch (e) { return; }
    s.add(h.split('?')[0]);
  });
  return Array.from(s);
}
"""


def prepare_plp_page(page, *, deep: bool = True) -> None:
    """Kategori / liste: lazy grid icin kaydir + bekle."""
    time.sleep(2.0 if deep else 1.2)
    n_scroll = 6 if deep else 4
    pause = 0.9 if deep else 0.55
    for _ in range(n_scroll):
        try:
            page.evaluate(
                "window.scrollBy(0, Math.floor(window.innerHeight * 0.88))"
            )
        except Exception:
            break
        time.sleep(pause)
    time.sleep(1.8 if deep else 1.0)


def collect_category_links_on_page(page) -> List[str]:
    hrefs = page.evaluate(COLLECT_CATEGORY_LINKS_JS)
    out: List[str] = []
    for h in hrefs or []:
        if not isinstance(h, str) or "/c/nl-BE/" not in h:
            continue
        u = h.split("?")[0]
        if category_url_blocked(u):
            continue
        out.append(u)
    return out


# Mindshift API ile uyumlu: hem /c/.../s123 hem hub /h/.../h123
COLLECT_API_CATEGORY_LINKS_JS = r"""
() => {
  const s = new Set();
  document.querySelectorAll('a[href]').forEach(a => {
    let h = a.getAttribute('href') || '';
    try { h = new URL(h, location.origin).href; } catch (e) { return; }
    let p = h.split('?')[0].split('#')[0].replace(/\/+$/, '');
    if (/\/c\/nl-BE\/.+\/s\d+$/i.test(p)) s.add(p);
    if (/\/h\/nl-BE\/.+\/h\d+$/i.test(p)) s.add(p);
  });
  return Array.from(s);
}
"""


def collect_api_category_links_on_page(page) -> List[str]:
    hrefs = page.evaluate(COLLECT_API_CATEGORY_LINKS_JS)
    out: List[str] = []
    for h in hrefs or []:
        if not isinstance(h, str):
            continue
        u = h.split("?")[0].rstrip("/")
        if category_url_blocked(u):
            continue
        out.append(u)
    return out


def discover_all_seed_category_urls(page) -> List[str]:
    """Ana sayfa + /c/nl-BE tohumlarindan /s ve /h kategori linkleri."""
    seen: Set[str] = set()
    first = True
    for seed in CONFIG["category_discovery_urls"]:
        try:
            page.goto(seed, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
        except Exception:
            continue
        time.sleep(2.0 if first else 1.2)
        if first:
            try_accept_cookies(page)
            time.sleep(1.0)
            first = False
        for u in collect_api_category_links_on_page(page):
            if not category_url_blocked(u):
                seen.add(u)
    return sorted(seen)


def bfs_collect_api_category_urls(page, *, bfs_max_pages: int) -> List[str]:
    """Kategori sayfalari arasinda BFS: API'ye verilecek tum plp/hub URL'leri."""
    try:
        page.goto(f"{CONFIG['base']}/", wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
        time.sleep(1.8)
        try_accept_cookies(page)
        time.sleep(0.9)
    except Exception:
        pass
    seeds = discover_all_seed_category_urls(page)
    if not seeds:
        seeds = discover_category_urls(page)
    queue: Deque[str] = deque(seeds)
    queued: Set[str] = set(seeds)
    all_found: Set[str] = set(seeds)
    visited = 0

    while queue and visited < bfs_max_pages:
        url = queue.popleft()
        visited += 1
        if visited % 35 == 0:
            print(
                f"  [discover_urls] ziyaret {visited}/{bfs_max_pages}, "
                f"kuyruk {len(queue)}, benzersiz {len(all_found)}"
            )
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
        except Exception:
            continue
        prepare_plp_page(page, deep=False)
        for child in collect_api_category_links_on_page(page):
            all_found.add(child)
            if child not in queued and not category_url_blocked(child):
                queued.add(child)
                queue.append(child)

    return sorted(all_found)


def bfs_discover_product_listing_urls(page, *, bfs_max_pages: int) -> List[str]:
    """
    Hub sayfalarindan alt /c/nl-BE/.../s* linklerini topla; /p/ gorunen URL'leri
    urun cekecegimiz 'yaprak' adaylari olarak dondur.
    """
    seeds = discover_category_urls(page)
    seeds = [u for u in seeds if not category_url_blocked(u)]
    queue: Deque[str] = deque(seeds)
    seen: Set[str] = set(seeds)
    listing_urls: List[str] = []
    visited = 0

    while queue and visited < bfs_max_pages:
        url = queue.popleft()
        visited += 1
        if visited % 25 == 0:
            print(f"  [BFS] ziyaret {visited}/{bfs_max_pages}, kuyruk {len(queue)}, liste adayi {len(listing_urls)}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
        except Exception:
            continue
        prepare_plp_page(page, deep=False)
        try:
            p_count = page.locator("a[href*='/p/']").count()
        except Exception:
            p_count = 0
        if p_count > 0:
            listing_urls.append(url)

        for child in collect_category_links_on_page(page):
            if child not in seen:
                seen.add(child)
                queue.append(child)

    # Sirayi koru, tekrar yok
    out: List[str] = []
    dup: Set[str] = set()
    for u in listing_urls:
        if u not in dup:
            dup.add(u)
            out.append(u)
    return out


def load_category_urls_file(script_dir: str) -> Optional[List[str]]:
    path = os.path.join(script_dir, "lidl_be_category_urls.txt")
    if not os.path.isfile(path):
        return None
    out: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#"):
                out.append(s)
    return out or None


def discover_category_urls(page) -> List[str]:
    seen: set[str] = set()
    first = True
    for seed in CONFIG["category_discovery_urls"]:
        try:
            page.goto(seed, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
        except Exception:
            continue
        time.sleep(2.0 if first else 1.2)
        if first:
            try_accept_cookies(page)
            time.sleep(1.2)
            first = False
        hrefs = page.evaluate(
            r"""
            () => {
              const s = new Set();
              document.querySelectorAll('a[href*="/c/nl-BE/"]').forEach(a => {
                let h = a.getAttribute('href') || '';
                if (!/\/s\d+(\?|$)/i.test(h)) return;
                try { h = new URL(h, location.origin).href; } catch (e) { return; }
                s.add(h.split('?')[0]);
              });
              return Array.from(s);
            }
            """
        )
        for h in hrefs or []:
            if isinstance(h, str) and "/c/nl-BE/" in h:
                u = h.split("?")[0]
                if not category_url_blocked(u):
                    seen.add(u)
    return sorted(seen)


def merge_tiles_into(
    raw_list: List[Dict[str, Any]],
    by_key: Dict[str, Dict[str, Any]],
    top_category_name: str,
) -> None:
    for item in raw_list:
        key = item.get("key") or ""
        text = item.get("text") or ""
        hi, lo, in_promo = parse_lidl_tile_prices(text)
        if in_promo:
            if hi is None or lo is None:
                continue
            basic_f, promo_f = hi, lo
        else:
            if hi is None:
                continue
            basic_f, promo_f = hi, None
        name = parse_name_from_tile(text)
        href = item.get("href") or ""
        if href.startswith("/"):
            href = CONFIG["base"] + href
        by_key[key] = {
            "lidlProductKey": key,
            "lidlUrlPath": href[:2000],
            "name": name,
            "brand": None,
            "basicPrice": basic_f,
            "promoPrice": promo_f if in_promo else None,
            "inPromo": in_promo,
            "topCategoryName": top_category_name[:500],
            "unitContent": None,
        }


def click_load_more(page) -> bool:
    for sel in (
        'button:has-text("Meer laden")',
        'button:has-text("meer laden")',
        'button:has-text("Toon meer")',
        '[class*="load-more" i] button',
    ):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1500):
                loc.click(timeout=8000)
                return True
        except Exception:
            continue
    return False


def settle_after_load_more(page) -> None:
    """Yeni grid satirlari icin bekle + hafif kaydir."""
    time.sleep(random.uniform(2.6, 4.8))
    prepare_plp_page(page, deep=False)


def scroll_before_extract(page) -> None:
    """Lazy tile'lar icin kisa tarama."""
    try:
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.35)
        for _ in range(4):
            page.evaluate(
                "window.scrollBy(0, Math.floor(window.innerHeight * 0.92))"
            )
            time.sleep(0.45)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
    except Exception:
        pass


def run(
    *,
    mode: str,
    queries: List[str],
    max_categories: int,
    bfs_max_pages: int,
    no_bfs: bool,
    dry_run: bool,
    no_pause: bool,
    discover_output: str,
) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: pip install playwright && playwright install chromium")
        return 1

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    profile = os.path.join(script_dir, "playwright_user_data", "lidl_be")
    os.makedirs(profile, exist_ok=True)

    by_key: Dict[str, Dict[str, Any]] = {}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            profile,
            headless=True,
            locale="nl-BE",
            viewport={"width": 1360, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.pages[0] if context.pages else context.new_page()

        if mode == "discover_urls":
            lim = min(bfs_max_pages, 12) if dry_run else bfs_max_pages
            out_file = discover_output.strip() or os.path.join(
                script_dir, "lidl_be_api_categories_autogen.txt"
            )
            print(f"discover_urls: BFS ile kategori URL (max {lim} sayfa)...")
            urls = bfs_collect_api_category_urls(page, bfs_max_pages=lim)
            if dry_run:
                print(f"\n[DRY-RUN] {len(urls)} benzersiz URL; dosya yazilmadi.")
                for u in urls[:20]:
                    print(f"  {u}")
                if len(urls) > 20:
                    print(f"  ... +{len(urls) - 20} daha")
                context.close()
                if not no_pause:
                    input("\nCikmak icin Enter...")
                return 0 if urls else 1
            header = (
                "# Otomatik kesif: lidl_be_playwright_cek.py --mode discover_urls\n"
                "# Mindshift API: python lidl_be_mindshift_api_cek.py --categories-file "
                "lidl_be_api_categories_autogen.txt\n"
                "# veya bu satirlari lidl_be_api_categories.txt ile birlestir.\n#\n"
            )
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(header)
                for u in urls:
                    f.write(u + "\n")
            print(f"\nTamam: {len(urls)} URL -> {out_file}")
            context.close()
            if not no_pause:
                input("\nCikmak icin Enter...")
            return 0 if urls else 1

        if mode == "categories":
            cat_urls = load_category_urls_file(script_dir)
            if not cat_urls:
                print("Kategori kesfi (lidl_be_category_urls.txt yok)...")
                try:
                    page.goto(f"{CONFIG['base']}/", wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
                    time.sleep(2.0)
                    try_accept_cookies(page)
                    time.sleep(1.0)
                except Exception:
                    pass
                if no_bfs:
                    cat_urls = discover_category_urls(page)
                    print(f"  (BFS kapali) duz liste: {len(cat_urls)} URL")
                else:
                    print("  BFS: hub sayfalarindan alt kategorilere iniliyor (biraz surer)...")
                    cat_urls = bfs_discover_product_listing_urls(
                        page, bfs_max_pages=bfs_max_pages
                    )
                    print(f"  BFS bitti: {len(cat_urls)} sayfada urun linki (/p/) bulundu.")
            if not cat_urls:
                print("HATA: Hic urun listesi URL'si yok. lidl_be_category_urls.txt ile yaprak URL verin.")
                context.close()
                return 1
            if max_categories > 0:
                cat_urls = cat_urls[:max_categories]
            print(f"Islenecek urun listesi URL sayisi: {len(cat_urls)}")
            max_clicks = CONFIG["max_load_more_clicks_categories"]

            try:
                page.goto(
                    f"{CONFIG['base']}/",
                    wait_until="domcontentloaded",
                    timeout=CONFIG["goto_timeout_ms"],
                )
                time.sleep(1.5)
                try_accept_cookies(page)
                time.sleep(0.8)
            except Exception:
                pass

            for ci, cat_url in enumerate(cat_urls):
                if dry_run and ci > 0:
                    break
                label = category_label_from_url(cat_url)
                print(f"\n[{ci + 1}/{len(cat_urls)}] {label}\n  {cat_url}")
                try:
                    page.goto(cat_url, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
                except Exception as e:
                    print(f"  Yukleme hatasi: {e}")
                    continue
                prepare_plp_page(page, deep=True)
                try:
                    page.wait_for_selector("a[href*='/p/']", timeout=35000)
                except Exception:
                    print("  Urun linki yok (veya zaman asimi); atlaniyor.")
                    continue

                clicks = 0
                prev_total = len(by_key)
                stale = 0
                stale_lim = int(CONFIG["stale_rounds_limit_categories"])
                while clicks < max_clicks:
                    human_pause()
                    scroll_before_extract(page)
                    raw_list = extract_products_from_page(page)
                    merge_tiles_into(raw_list, by_key, f"cat:{label}")
                    grew = len(by_key) > prev_total
                    print(f"  +{len(raw_list)} kutu, benzersiz (tum kategoriler): {len(by_key)}")

                    if dry_run:
                        break

                    expanded = False
                    if click_load_more(page):
                        expanded = True
                        settle_after_load_more(page)
                    else:
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.9)
                        if click_load_more(page):
                            expanded = True
                            settle_after_load_more(page)

                    if not expanded:
                        break

                    if grew:
                        stale = 0
                    else:
                        stale += 1
                        if stale >= stale_lim:
                            break

                    prev_total = len(by_key)
                    clicks += 1
                if ci < len(cat_urls) - 1 and not dry_run:
                    time.sleep(random.uniform(5.0, 14.0))
        else:
            for qi, q in enumerate(queries):
                if dry_run and qi > 0:
                    break
                url = f"{CONFIG['base']}/q/search?query={q}"
                print(f"\nArama: {q}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
                except Exception as e:
                    print(f"  Yukleme hatasi: {e}")
                    continue
                time.sleep(2.0)
                try_accept_cookies(page)
                time.sleep(1.5)

                try:
                    page.wait_for_selector("a[href*='/p/']", timeout=45000)
                except Exception:
                    print("  Urun linki bulunamadi (cerez/ban veya sayfa yapisi).")
                    continue

                clicks = 0
                while clicks < CONFIG["max_load_more_clicks"]:
                    human_pause()
                    raw_list = extract_products_from_page(page)
                    merge_tiles_into(raw_list, by_key, f"search:{q}")
                    print(f"  +{len(raw_list)} link gorundu, benzersiz fiyatli: {len(by_key)}")

                    if dry_run:
                        break
                    if not click_load_more(page):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)
                        if not click_load_more(page):
                            break
                    clicks += 1

        context.close()

    urunler = list(by_key.values())
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = os.path.join(cikti_dir, f"lidl_be_producten_{tarih}.json")
    kaynak = (
        "Lidl Belçika Playwright (DOM, kategori gezintisi)"
        if mode == "categories"
        else "Lidl Belçika Playwright (DOM, arama)"
    )
    payload = {
        "kaynak": kaynak,
        "chain_slug": "lidl_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi": len(urunler),
        "dry_run": dry_run,
        "lidl_mode": mode,
        "urunler": urunler,
    }

    if dry_run:
        print(f"\n[DRY-RUN] {len(urunler)} urun; dosya yazilmadi.")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nTamam: {len(urunler)} urun -> {out_path}")

    if not no_pause:
        input("\nCikmak icin Enter...")
    return 0 if urunler else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Lidl BE Playwright cekici")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument(
        "--mode",
        choices=("search", "categories", "discover_urls"),
        default="search",
        help="search|categories|discover_urls (API icin /s ve /h URL listesi uretir)",
    )
    ap.add_argument(
        "--max-categories",
        type=int,
        default=0,
        help="categories modunda en fazla kategori (0=tumu)",
    )
    ap.add_argument(
        "--bfs-max-pages",
        type=int,
        default=0,
        help="BFS ile en fazla kategori sayfasi ziyaret (0=CONFIG)",
    )
    ap.add_argument(
        "--no-bfs",
        action="store_true",
        help="BFS yok: sadece ilk keşif listesi (cogu hub, cogu bos)",
    )
    ap.add_argument("--queries", type=str, default="", help="Virgulle ayri arama terimleri (bos=varsayilan liste)")
    ap.add_argument(
        "--discover-output",
        type=str,
        default="",
        help="discover_urls: cikti txt (bos=lidl_be_api_categories_autogen.txt)",
    )
    args = ap.parse_args()
    qlist = [s.strip() for s in args.queries.split(",") if s.strip()] if args.queries else list(CONFIG["search_queries"])
    bfs_lim = args.bfs_max_pages if args.bfs_max_pages > 0 else int(CONFIG["bfs_max_pages"])
    return run(
        mode=args.mode,
        queries=qlist,
        max_categories=args.max_categories,
        bfs_max_pages=bfs_lim,
        no_bfs=args.no_bfs,
        dry_run=args.dry_run,
        no_pause=args.no_pause,
        discover_output=args.discover_output.strip(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
