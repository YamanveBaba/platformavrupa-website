# -*- coding: utf-8 -*-
"""
colruyt_cookie_yenile.py — reese84 ve diger oturum cookie'lerini Chrome'dan tazeler.
Colruyt sitesine gidip sayfanin yuklenmesini bekler, cookie'leri kaydeder.
Her haftalik calismayla cagrilmasi gerekebilir.
"""
import json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("pip install playwright && playwright install chromium")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent

def _chrome_yolu_bul():
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "chrome"

def _cdp_acik(port=9222):
    try:
        s = socket.socket(); s.settimeout(1)
        r = s.connect_ex(("localhost", port)); s.close()
        return r == 0
    except: return False

def cookie_yenile():
    print("Colruyt cookie yenileniyor...")

    # Mevcut oturum bilgilerini yukle
    state_dosya = SCRIPT_DIR / "colruyt_state.json"
    if not state_dosya.exists():
        print("HATA: colruyt_state.json yok — once ilk kurulumu calistir.")
        return False

    saved = json.loads(state_dosya.read_text(encoding="utf-8"))
    mevcut_cookies = saved.get("cookies", [])
    ls_items = []
    for origin_data in saved.get("origins", []):
        ls_items.extend(origin_data.get("localStorage", []))

    temp_dir = tempfile.mkdtemp(prefix="colruyt_renew_")
    chrome_exe = _chrome_yolu_bul()
    chrome_proc = None

    try:
        # Acik Chrome'u kapat
        tlist = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True
        )
        if "chrome.exe" in tlist.stdout.lower():
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
            time.sleep(3)

        chrome_proc = subprocess.Popen([
            chrome_exe,
            "--remote-debugging-port=9222",
            f"--user-data-dir={temp_dir}",
            "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--window-size=1366,768",
            "about:blank",
        ])

        print("Chrome bekleniyor", end="", flush=True)
        time.sleep(3)
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
            if _cdp_acik():
                print(f" hazir! ({i+4}s)")
                break
        else:
            print("\nHATA: CDP acilmadi")
            return False

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()

            # Mevcut cookie'leri yukle
            ctx.add_cookies(mevcut_cookies)

            page = ctx.new_page()
            page.set_default_timeout(45000)

            # Siteye git — reese84 otomatik yenilenir
            print("Colruyt yukleniyor...")
            page.goto("https://www.colruyt.be/nl", wait_until="domcontentloaded", timeout=45000)
            time.sleep(2)

            # localStorage geri yukle
            if ls_items:
                page.evaluate("""(items) => {
                    items.forEach(i => { try { localStorage.setItem(i.name, i.value); } catch(e) {} });
                }""", ls_items)

            page.reload(wait_until="domcontentloaded", timeout=45000)

            # Sayfanin tamamen yuklenmesini bekle (reese84 yenilenmesi icin)
            print("Sayfa yukleniyor (reese84 icin 15s bekleniyor)...")
            time.sleep(15)

            # Guncel cookie'leri kaydet
            yeni_cookies = ctx.cookies()
            yeni_ls = page.evaluate("""() => {
                const items = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items.push({name: key, value: localStorage.getItem(key)});
                }
                return items;
            }""")

            # State'i guncelle
            yeni_state = {
                "cookies": yeni_cookies,
                "origins": [{"origin": "https://www.colruyt.be", "localStorage": yeni_ls or []}],
            }
            state_dosya.write_text(json.dumps(yeni_state, ensure_ascii=False), encoding="utf-8")

            # colruyt_cookies.json de guncelle (direct.py icin)
            cookie_dosya = SCRIPT_DIR / "colruyt_cookies.json"
            cookie_dosya.write_text(json.dumps(yeni_cookies, ensure_ascii=False), encoding="utf-8")

            reese = next((c for c in yeni_cookies if c["name"] == "reese84"), None)
            print(f"Kaydedildi: {len(yeni_cookies)} cookie, {len(yeni_ls or [])} localStorage")
            if reese:
                print(f"reese84: {reese['value'][:30]}... (taze)")
            else:
                print("UYARI: reese84 bulunamadi")

            page.close()

        return True

    except Exception as e:
        print(f"HATA: {e}")
        return False
    finally:
        if chrome_proc:
            chrome_proc.terminate()
            time.sleep(2)
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    ok = cookie_yenile()
    if ok:
        print("\nCookie yenilendi. Simdi colruyt_direct.py calistirabilirsin.")
    else:
        print("\nHATA: Cookie yenilenemedi.")
