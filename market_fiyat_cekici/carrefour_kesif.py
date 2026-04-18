# -*- coding: utf-8 -*-
"""
Carrefour BE — API Keşif Scripti
Playwright ile promosyon + ürün sayfalarını açar, TÜM network yanıtlarını loglar.
Ayrıca sayfadaki __NEXT_DATA__, __NUXT_DATA__ vb. gömülü JSON'ları çeker.

Kullanım:
  python carrefour_kesif.py --headed

Çıktı:
  carrefour_kesif_log.txt   — konsol çıktısı
  carrefour_kesif_json.jsonl — yakalanan JSON yanıtları (1 satır = 1 yanıt)
"""
from __future__ import annotations
import json, os, re, time, random
from datetime import datetime

HEDEF_SAYFALAR = [
    "https://www.carrefour.be/nl/al-onze-promoties",
    "https://www.carrefour.be/nl/alle-producten",
    "https://www.carrefour.be/nl",
]

script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_TXT   = os.path.join(script_dir, "carrefour_kesif_log.txt")
LOG_JSONL = os.path.join(script_dir, "carrefour_kesif_json.jsonl")


def _log(msg: str, f_txt):
    print(msg)
    f_txt.write(msg + "\n")
    f_txt.flush()


def calistir(headed: bool):
    from playwright.sync_api import sync_playwright

    profil = os.path.join(script_dir, "playwright_user_data", "carrefour_be")
    os.makedirs(profil, exist_ok=True)

    with open(LOG_TXT, "w", encoding="utf-8") as f_txt, \
         open(LOG_JSONL, "w", encoding="utf-8") as f_json:

        _log(f"=== Carrefour Keşif Başlıyor {datetime.now()} ===", f_txt)

        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                profil,
                headless=not headed,
                locale="nl-BE",
                viewport={"width": 1440, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-web-security",
                ],
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()

            # Stealth modu: navigator.webdriver ve diğer bot izlerini gizle
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
                _log("  [stealth] playwright-stealth aktif", f_txt)
            except ImportError:
                _log("  [stealth] playwright-stealth yüklü değil (pip install playwright-stealth)", f_txt)

            # Bot izlerini JS ile de temizle
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['nl-BE','nl','fr','en']});
                window.chrome = { runtime: {} };
            """)

            # ── Response handler: TÜM yanıtları yakala ──────────────────────
            def on_response(response):
                try:
                    url = response.url
                    status = response.status
                    ct = response.headers.get("content-type", "")

                    # Statik dosyaları atla
                    if re.search(r"\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|css|mp4|webp)(\?|$)", url, re.I):
                        return
                    # Tracking/analytics atla
                    if re.search(r"(google-analytics|googletagmanager|facebook\.net|newrelic|sentry|adobe)", url, re.I):
                        return

                    # JSON yanıtları kaydet
                    if "json" in ct or re.search(r"\.(json)(\?|$)", url):
                        try:
                            body = response.body()
                            if len(body) < 10:
                                return
                            try:
                                data = json.loads(body)
                            except Exception:
                                data = None

                            entry = {
                                "url": url,
                                "status": status,
                                "content_type": ct,
                                "boyut": len(body),
                                "data": data,
                            }
                            f_json.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            f_json.flush()

                            # Özet logla
                            toplam = None
                            if isinstance(data, dict):
                                for k in ("total", "count", "nbHits", "numberOfResults",
                                          "totalRecords", "totalProducts", "totalCount"):
                                    if k in data:
                                        toplam = data[k]
                                        break
                            _log(
                                f"  [JSON] {status} {url[:100]}\n"
                                f"         ct={ct[:40]} boyut={len(body)} toplam={toplam}",
                                f_txt,
                            )
                        except Exception as e:
                            _log(f"  [JSON body hata] {url[:80]} → {e}", f_txt)
                        return

                    # JSON olmayan ama ilginç URL'leri logla
                    if re.search(r"(search|product|catalog|category|promo|offer|assortment|artikel)", url, re.I):
                        _log(f"  [URL] {status} {url[:110]}  ct={ct[:30]}", f_txt)

                except Exception:
                    pass

            page.on("response", on_response)

            # ── Her sayfayı gez ──────────────────────────────────────────────
            for url in HEDEF_SAYFALAR:
                _log(f"\n{'─'*60}\n[SAYFA] {url}", f_txt)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                except Exception as e:
                    _log(f"  [goto hata] {e}", f_txt)
                    continue

                time.sleep(3)

                # Cookie kabul
                for sel in (
                    'button:has-text("Alles accepteren")',
                    'button:has-text("Tout accepter")',
                    '#onetrust-accept-btn-handler',
                    '[data-testid="accept-all-cookies"]',
                ):
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible(timeout=2000):
                            loc.click()
                            _log("  [cookie] kabul edildi", f_txt)
                            time.sleep(1.5)
                            break
                    except Exception:
                        pass

                # Sayfa içi gömülü JSON: __NEXT_DATA__, __NUXT_DATA__, vb.
                for var in ("__NEXT_DATA__", "__NUXT_DATA__", "__INITIAL_STATE__",
                            "__REDUX_STATE__", "__APP_STATE__", "window.__data__"):
                    try:
                        val = page.evaluate(f"() => JSON.stringify(window.{var.replace('window.', '')} || null)")
                        if val and val != "null" and len(val) > 10:
                            _log(f"  [GOMULU] {var} bulundu! boyut={len(val)}", f_txt)
                            entry = {"kaynak": var, "url": url, "data_str_ilk500": val[:500]}
                            f_json.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            f_json.flush()
                    except Exception:
                        pass

                # Scroll yaparak lazy-load API'leri tetikle
                _log("  [scroll] başlıyor …", f_txt)
                for i in range(20):
                    page.evaluate("window.scrollBy(0, 600)")
                    time.sleep(random.uniform(0.6, 1.2))
                    if i == 10:
                        time.sleep(2)  # yarıda uzun bekleme

                # Son durum
                son_url = page.url
                baslik = page.title()
                _log(f"  [son] url={son_url[:80]}  baslik={baslik[:60]}", f_txt)

            ctx.close()

        _log(f"\n=== Bitti {datetime.now()} ===", f_txt)
        _log(f"Log: {LOG_TXT}", f_txt)
        _log(f"JSON: {LOG_JSONL}", f_txt)

    print(f"\nDosyalar:\n  {LOG_TXT}\n  {LOG_JSONL}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()
    calistir(headed=args.headed)
