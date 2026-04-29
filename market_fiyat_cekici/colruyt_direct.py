# -*- coding: utf-8 -*-
"""
colruyt_direct.py — Colruyt urunlerini API ile ceker.
Playwright browser context ile istek atar — reese84 antibot bypass.
"""
import json, time, random
from datetime import datetime
from pathlib import Path
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && python -m playwright install chromium")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
CIKTI_DIR  = SCRIPT_DIR / "cikti" / "html_pages"
CIKTI_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc/cg/nl/api/product-search-prs"
API_KEY  = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
PLACE_ID = 710
PAGE_SIZE = 48
MIN_DELAY = 2.0
MAX_DELAY = 4.0


def load_state() -> dict:
    state_file = SCRIPT_DIR / "colruyt_state.json"
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text(encoding="utf-8"))


def colruyt_cek():
    state = load_state()
    cookies = state.get("cookies", [])
    ls_items = []
    for od in state.get("origins", []):
        ls_items.extend(od.get("localStorage", []))

    if not cookies:
        print("colruyt_state.json bulunamadi! Once colruyt_cookie_yenile.py calistir.")
        return

    print(f"  {len(cookies)} cookie yuklendi")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="nl-BE",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "nl-BE,nl;q=0.9"},
        )

        # Mevcut cookie'leri yukle
        try:
            ctx.add_cookies(cookies)
        except Exception as e:
            print(f"  Cookie yukleme hatasi: {e}")

        page = ctx.new_page()

        # reese84 tazele
        print("  Colruyt'a baglaniliyor (reese84 icin)...")
        try:
            page.goto("https://www.colruyt.be/nl", wait_until="domcontentloaded", timeout=45000)
            time.sleep(8)
        except Exception as e:
            print(f"  Site yukleme hatasi: {e}")

        # Toplam urun sayisi
        def api_get(skip, size=1):
            return ctx.request.get(
                API_BASE,
                params={
                    "placeId": PLACE_ID,
                    "size": size,
                    "skip": skip,
                    "isAvailable": "true",
                },
                headers={
                    "x-cg-apikey": API_KEY,
                    "accept": "*/*",
                    "origin": "https://www.colruyt.be",
                    "referer": "https://www.colruyt.be/",
                },
            )

        print("\n  --- API TEST ---")
        try:
            r = api_get(0, 2)
            print(f"  Test: HTTP {r.status}")
            if r.status == 200:
                d = r.json()
                total = d.get("totalProductsFound", 0)
                print(f"  Toplam katalog: {total} urun")
            else:
                print(f"  Test yaniti: {r.text()[:200]}")
                browser.close()
                return
        except Exception as e:
            print(f"  Test hatasi: {e}")
            browser.close()
            return
        print("  --- TEST BITTI ---\n")

        # Tum katalogu cek
        print("  Tum katalog cekiliyor...")
        tum_urunler = []
        skip = 0
        MAX_RETRY = 3

        while skip < total:
            retry = 0
            while retry < MAX_RETRY:
                try:
                    r = api_get(skip, PAGE_SIZE)
                    if r.status == 456:
                        bekleme = 30 + retry * 30
                        print(f"  HTTP 456 (antibot) — {bekleme}s bekleniyor...")
                        time.sleep(bekleme)
                        retry += 1
                        continue
                    if r.status != 200:
                        print(f"  HTTP {r.status} — duruyorum")
                        browser.close()
                        return
                    data = r.json()
                    break
                except Exception as e:
                    print(f"  Hata: {e}")
                    retry += 1
                    time.sleep(5)
            else:
                print("  Max retry asildi, duruyorum")
                break

            prods = data.get("products", [])
            if not prods:
                break

            tum_urunler.extend(prods)
            total = data.get("totalProductsFound") or total
            print(f"  skip={skip} -> +{len(prods)} ({len(tum_urunler)}/{total})")

            skip += PAGE_SIZE
            if not prods or skip >= total:
                break

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        browser.close()

    print(f"\n  Toplam urun: {len(tum_urunler)}")

    if tum_urunler:
        tarih = datetime.now().strftime("%Y-%m-%d")
        dosya = CIKTI_DIR / f"colruyt_Genel_p01_{tarih}.json"
        dosya.write_text(
            json.dumps({"products": tum_urunler}, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"  Kaydedildi: {dosya.name}")
    else:
        print("  UYARI: Hic urun alinamadi!")


if __name__ == "__main__":
    colruyt_cek()
