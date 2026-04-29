# -*- coding: utf-8 -*-
"""
Carrefour BE — camoufox (Firefox) ile Cloudflare bypass + API keşfi
camoufox: pip install camoufox && python -m camoufox fetch

Kullanım:
  python carrefour_kesif3.py

Çıktı:
  carrefour_kesif_log.txt
  carrefour_kesif_json.jsonl
"""
from __future__ import annotations
import json, os, re, time, random
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
from datetime import datetime as _dt
_ts = _dt.now().strftime("%H%M%S")
LOG_TXT   = os.path.join(script_dir, f"carrefour_kesif_log_{_ts}.txt")
LOG_JSONL = os.path.join(script_dir, f"carrefour_kesif_json_{_ts}.jsonl")

HEDEF_SAYFALAR = [
    "https://www.carrefour.be/nl/al-onze-promoties",
    "https://www.carrefour.be/nl/",
    "https://www.carrefour.be/nl/c/food",
    "https://www.carrefour.be/nl/c/drinks",
    "https://www.carrefour.be/nl/c/fresh",
    "https://www.carrefour.be/nl/vb/melk",
    "https://www.carrefour.be/nl/vb/bier-duvel",
]


def _log(msg, f):
    print(msg)
    f.write(msg + "\n")
    f.flush()


def calistir():
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        print("HATA: pip install camoufox && python -m camoufox fetch")
        return

    with open(LOG_TXT, "w", encoding="utf-8") as f_txt, \
         open(LOG_JSONL, "w", encoding="utf-8") as f_json:

        _log(f"=== Carrefour camoufox Keşif {datetime.now()} ===", f_txt)

        with Camoufox(
            headless=False,
            firefox_user_prefs={
                "browser.startup.page": 0,          # Boş sayfa aç
                "browser.sessionstore.resume_from_crash": False,
                "browser.sessionrestore.max_resumed_crashes": 0,
                "browser.sessionstore.enabled": False,
            },
        ) as browser:
            page = browser.new_page()
            time.sleep(2)  # Tarayıcının tamamen açılmasını bekle

            # Response dinleyici — sadece carrefour.be ve ilgili domainler
            def on_response(response):
                try:
                    url = response.url
                    # Sadece carrefour domainleri
                    if not re.search(r"(carrefour\.be|carrefour\.eu|verbolia\.com)", url, re.I):
                        return
                    if re.search(r"\.(png|jpg|gif|svg|ico|woff|css|mp4|webp)(\?|$)", url, re.I):
                        return
                    if re.search(r"(google-analytics|gtm|facebook\.net|newrelic|sentry)", url, re.I):
                        return
                    ct = response.headers.get("content-type", "")
                    status = response.status
                    if "json" in ct:
                        try:
                            body = response.body()
                            data = json.loads(body)
                            entry = {
                                "url": url, "status": status,
                                "content_type": ct, "boyut": len(body),
                                "data": data,
                            }
                            f_json.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            f_json.flush()
                            toplam = None
                            if isinstance(data, dict):
                                for k in ("total","count","nbHits","numberOfResults","totalProducts"):
                                    if k in data:
                                        toplam = data[k]; break
                            _log(f"  [JSON] {status} boyut={len(body)} toplam={toplam}\n"
                                 f"         {url[:100]}", f_txt)
                        except Exception as e:
                            _log(f"  [JSON hata] {url[:80]} -> {e}", f_txt)
                    elif re.search(r"(search|product|catalog|categor|promo|offer|assortment|api)", url, re.I):
                        _log(f"  [URL] {status} {url[:110]}", f_txt)
                except Exception:
                    pass

            page.on("response", on_response)

            for hedef_url in HEDEF_SAYFALAR:
                _log(f"\n{'─'*60}\n[SAYFA] {hedef_url}", f_txt)
                yuklendi = False
                for deneme in range(3):
                    try:
                        page.goto(hedef_url, wait_until="domcontentloaded", timeout=90_000)
                        yuklendi = True
                        break
                    except Exception as e:
                        _log(f"  [goto hata deneme {deneme+1}] {str(e)[:120]}", f_txt)
                        time.sleep(3)
                if not yuklendi:
                    _log("  [!] 3 denemede yüklenemedi, geçiliyor.", f_txt)
                    continue

                time.sleep(4)

                # Sayfa başlığı kontrol (Cloudflare mı?)
                baslik = page.title()
                _log(f"  [baslik] {baslik}", f_txt)
                if "cloudflare" in baslik.lower() or "attention" in baslik.lower():
                    _log("  [!] Cloudflare ekranı — 10 saniye bekleniyor …", f_txt)
                    time.sleep(10)
                    baslik = page.title()
                    _log(f"  [baslik sonra] {baslik}", f_txt)

                # Cookie
                for sel in ('button:has-text("Alles accepteren")',
                            'button:has-text("Tout accepter")',
                            '#onetrust-accept-btn-handler'):
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible(timeout=2000):
                            loc.click()
                            _log("  [cookie] kabul edildi", f_txt)
                            time.sleep(1.5)
                            break
                    except Exception:
                        pass

                # Gömülü JSON'lar
                for var in ("__NEXT_DATA__", "__NUXT_DATA__", "__INITIAL_STATE__", "__APP_STATE__"):
                    try:
                        val = page.evaluate(f"() => JSON.stringify(window.{var} || null)")
                        if val and val != "null" and len(val) > 20:
                            _log(f"  [GOMULU] {var} boyut={len(val)}", f_txt)
                            entry = {"tip": "gomulu", "var": var, "url": hedef_url,
                                     "boyut": len(val), "icerik": json.loads(val)}
                            f_json.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            f_json.flush()
                    except Exception:
                        pass

                # Scroll
                _log("  [scroll] …", f_txt)
                for i in range(35):
                    page.evaluate("window.scrollBy(0, 600)")
                    time.sleep(random.uniform(0.6, 1.2))
                    if i % 10 == 9:
                        time.sleep(1.5)  # ara bekleme

                # Performance entries (hangi fetch/XHR yapıldı)
                try:
                    perf = page.evaluate("""
                        () => JSON.stringify(
                            performance.getEntriesByType('resource')
                            .filter(e => e.initiatorType==='fetch'||e.initiatorType==='xmlhttprequest')
                            .map(e => ({url: e.name, ms: Math.round(e.duration)}))
                            .slice(0, 150)
                        )
                    """)
                    if perf and perf != "null":
                        entries = json.loads(perf)
                        ilginc = [e for e in entries if re.search(
                            r"(search|product|catalog|categor|promo|api|assortment)", e["url"], re.I)]
                        _log(f"  [perf] {len(entries)} istek, {len(ilginc)} ilginç:", f_txt)
                        for e in ilginc[:30]:
                            _log(f"    {e['ms']}ms  {e['url'][:110]}", f_txt)
                        f_json.write(json.dumps(
                            {"tip": "perf", "url": hedef_url, "ilginc": ilginc},
                            ensure_ascii=False) + "\n")
                        f_json.flush()
                except Exception as e:
                    _log(f"  [perf hata] {e}", f_txt)

                son_url = page.url
                _log(f"  [son_url] {son_url}", f_txt)

            page.close()

        _log(f"\n=== Bitti {datetime.now()} ===", f_txt)

    print(f"\nLog: {LOG_TXT}\nJSON: {LOG_JSONL}")


if __name__ == "__main__":
    calistir()
