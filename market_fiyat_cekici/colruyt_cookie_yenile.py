# -*- coding: utf-8 -*-
"""
colruyt_cookie_yenile.py — reese84 ve diger oturum cookie'lerini Playwright ile tazeler.
Colruyt sitesine gidip sayfanin yuklenmesini bekler, cookie'leri kaydeder.
Chrome kurulu olmasi gerekmez — Playwright Chromium kullanir.
"""
import json, sys, time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && python -m playwright install chromium")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent


def cookie_yenile():
    print("Colruyt cookie yenileniyor (Playwright Chromium)...")

    state_dosya = SCRIPT_DIR / "colruyt_state.json"

    mevcut_cookies = []
    ls_items = []
    if state_dosya.exists():
        try:
            saved = json.loads(state_dosya.read_text(encoding="utf-8"))
            mevcut_cookies = saved.get("cookies", [])
            for origin_data in saved.get("origins", []):
                ls_items.extend(origin_data.get("localStorage", []))
            print(f"  Mevcut state yuklendi: {len(mevcut_cookies)} cookie")
        except Exception as e:
            print(f"  State okuma hatasi: {e}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--lang=nl-BE",
                ],
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

            # Mevcut cookie'leri yukle (reese84 tazeleme icin)
            if mevcut_cookies:
                try:
                    ctx.add_cookies(mevcut_cookies)
                except Exception as e:
                    print(f"  Mevcut cookie yuklenemedi: {e}")

            page = ctx.new_page()

            # localStorage geri yukle
            if ls_items:
                page.goto("https://www.colruyt.be", wait_until="domcontentloaded", timeout=30000)
                page.evaluate("""(items) => {
                    items.forEach(i => {
                        try { localStorage.setItem(i.name, i.value); } catch(e) {}
                    });
                }""", ls_items)

            print("  Colruyt yukleniyor...")
            page.goto("https://www.colruyt.be/nl", wait_until="domcontentloaded", timeout=45000)

            # reese84'un yenilenmesi icin bekle
            print("  reese84 icin 15s bekleniyor...")
            time.sleep(15)

            yeni_cookies = ctx.cookies()
            yeni_ls = page.evaluate("""() => {
                const items = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items.push({name: key, value: localStorage.getItem(key)});
                }
                return items;
            }""")

            browser.close()

        # State'i kaydet
        yeni_state = {
            "cookies": yeni_cookies,
            "origins": [{"origin": "https://www.colruyt.be", "localStorage": yeni_ls or []}],
        }
        state_dosya.write_text(json.dumps(yeni_state, ensure_ascii=False), encoding="utf-8")

        # colruyt_cookies.json de guncelle
        cookie_dosya = SCRIPT_DIR / "colruyt_cookies.json"
        cookie_dosya.write_text(json.dumps(yeni_cookies, ensure_ascii=False), encoding="utf-8")

        reese = next((c for c in yeni_cookies if c["name"] == "reese84"), None)
        print(f"  Kaydedildi: {len(yeni_cookies)} cookie, {len(yeni_ls or [])} localStorage")
        if reese:
            print(f"  reese84: {str(reese.get('value',''))[:30]}... (taze)")
        else:
            print("  UYARI: reese84 bulunamadi")

        return True

    except Exception as e:
        print(f"  HATA: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = cookie_yenile()
    if ok:
        print("\nCookie yenilendi. Simdi colruyt_direct.py calistirabilirsin.")
    else:
        print("\nHATA: Cookie yenilenemedi.")
