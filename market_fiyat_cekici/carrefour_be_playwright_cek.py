# -*- coding: utf-8 -*-
"""
Carrefour Belçika — Playwright ile promosyon / liste sayfasi DOM'dan urun+fiyat.
Cloudflare icin kalici profil: playwright_user_data/carrefour_be (ilk calistirmada cerez kabulu icin headful onerilir).

Cikti: cikti/carrefour_be_producten_*.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

CONFIG = {
    "start_urls": [
        "https://www.carrefour.be/nl/al-onze-promoties",
        "https://www.carrefour.be/nl/alle-producten",
    ],
    "scroll_rounds": 35,
    "goto_timeout_ms": 120000,
}


def human_pause() -> None:
    time.sleep(random.uniform(1.5, 3.8))


def try_accept_cookies(page) -> None:
    for sel in (
        'button:has-text("Alles accepteren")',
        'button:has-text("Accepteren")',
        'button:has-text("Accept")',
        '#onetrust-accept-btn-handler',
        'button[aria-label*="Accept" i]',
    ):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2500):
                loc.click(timeout=8000)
                time.sleep(1.2)
                return
        except Exception:
            continue


def extract_tiles(page) -> List[Dict[str, Any]]:
    return page.evaluate(
        """
        () => {
          const out = [];
          const tiles = document.querySelectorAll(
            '[data-pid], [data-product-id], .product-tile, .product--tile, li.grid__item'
          );
          tiles.forEach(el => {
            const pid =
              el.getAttribute('data-pid') ||
              el.getAttribute('data-product-id') ||
              el.getAttribute('data-master-id');
            const text = el.innerText || '';
            if (!pid && text.length < 8) return;
            out.push({ pid: pid || '', text: text.slice(0, 800) });
          });
          return out;
        }
        """
    )


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.replace("\xa0", " ")
    for pat in (
        r"€\s*(\d+[.,]\d{2})",
        r"(\d+[.,]\d{2})\s*€",
        r"(?:^|\s)(\d+[.,]\d{2})(?:\s|$)",
    ):
        m = re.search(pat, t)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except (ValueError, IndexError):
                continue
    return None


def first_title_line(text: str) -> str:
    for ln in text.splitlines():
        s = ln.strip()
        if len(s) > 3 and not re.match(r"^[\d€,.\s/-]+$", s):
            return s[:500]
    return ""


def run(*, headless: bool, dry_run: bool, no_pause: bool) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: pip install playwright && playwright install chromium")
        return 1

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    profile = os.path.join(script_dir, "playwright_user_data", "carrefour_be")
    os.makedirs(profile, exist_ok=True)

    by_pid: Dict[str, Dict[str, Any]] = {}

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            profile,
            headless=headless,
            locale="nl-BE",
            viewport={"width": 1400, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.pages[0] if context.pages else context.new_page()

        for ui, start in enumerate(CONFIG["start_urls"]):
            if dry_run and ui > 0:
                break
            print(f"\nSayfa: {start}")
            try:
                page.goto(start, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
            except Exception as e:
                print(f"  Yukleme: {e}")
                continue
            time.sleep(2.5)
            try_accept_cookies(page)
            time.sleep(1.5)

            for _ in range(CONFIG["scroll_rounds"] if not dry_run else 8):
                human_pause()
                for item in extract_tiles(page):
                    pid = (item.get("pid") or "").strip()
                    text = item.get("text") or ""
                    price = parse_price(text)
                    if price is None:
                        continue
                    key = pid or re.sub(r"\W+", "_", first_title_line(text).lower())[:80] + "_" + str(price)
                    if key in by_pid:
                        continue
                    by_pid[key] = {
                        "carrefourPid": key[:200],
                        "name": first_title_line(text) or key[:120],
                        "brand": None,
                        "basicPrice": price,
                        "promoPrice": None,
                        "inPromo": "promo" in text.lower() or "%" in text,
                        "topCategoryName": start.split("/")[-1][:200],
                        "unitContent": None,
                    }
                page.evaluate("window.scrollBy(0, Math.min(700, window.innerHeight * 0.85))")
                if dry_run:
                    break

        context.close()

    urunler = list(by_pid.values())
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = os.path.join(cikti_dir, f"carrefour_be_producten_{tarih}.json")
    payload = {
        "kaynak": "Carrefour Belçika Playwright (DOM)",
        "chain_slug": "carrefour_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi": len(urunler),
        "dry_run": dry_run,
        "urunler": urunler,
    }

    if dry_run:
        print(f"\n[DRY-RUN] {len(urunler)} satir; dosya yazilmadi.")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nTamam: {len(urunler)} satir -> {out_path}")

    if not no_pause:
        input("\nCikmak icin Enter...")
    return 0 if urunler else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Carrefour BE Playwright cekici")
    ap.add_argument("--headed", action="store_true", help="Gorsel tarayici (cerez/CF icin)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-pause", action="store_true")
    args = ap.parse_args()
    return run(headless=not args.headed, dry_run=args.dry_run, no_pause=args.no_pause)


if __name__ == "__main__":
    raise SystemExit(main())
