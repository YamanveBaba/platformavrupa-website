# -*- coding: utf-8 -*-
"""
Carrefour BE — nodriver ile Cloudflare bypass + API keşfi
nodriver: https://github.com/ultrafunkamsterdam/nodriver

Kurulum:
  pip install nodriver

Kullanım:
  python carrefour_kesif2.py

Çıktı:
  carrefour_kesif_log.txt
  carrefour_kesif_json.jsonl
"""
from __future__ import annotations
import asyncio, json, os, re, time
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_TXT   = os.path.join(script_dir, "carrefour_kesif_log.txt")
LOG_JSONL = os.path.join(script_dir, "carrefour_kesif_json.jsonl")

HEDEF_SAYFALAR = [
    "https://www.carrefour.be/nl/al-onze-promoties",
    "https://www.carrefour.be/nl/alle-producten",
]


def _log(msg: str, f):
    print(msg)
    f.write(msg + "\n")
    f.flush()


async def calistir():
    try:
        import nodriver as uc
    except ImportError:
        print("HATA: pip install nodriver")
        return

    with open(LOG_TXT, "w", encoding="utf-8") as f_txt, \
         open(LOG_JSONL, "w", encoding="utf-8") as f_json:

        _log(f"=== Carrefour nodriver Keşif {datetime.now()} ===", f_txt)

        browser = await uc.start(
            headless=False,
            lang="nl-BE",
        )

        for hedef_url in HEDEF_SAYFALAR:
            _log(f"\n{'─'*60}\n[SAYFA] {hedef_url}", f_txt)

            tab = await browser.get(hedef_url)
            await asyncio.sleep(4)

            # Cookie banner
            for metin in ("Alles accepteren", "Tout accepter", "Accept all"):
                try:
                    btn = await tab.find(metin, timeout=3)
                    if btn:
                        await btn.click()
                        _log(f"  [cookie] '{metin}' tıklandı", f_txt)
                        await asyncio.sleep(2)
                        break
                except Exception:
                    pass

            # Sayfa içi gömülü JSON'ları çek
            for var in ("__NEXT_DATA__", "__NUXT_DATA__", "__INITIAL_STATE__",
                        "__REDUX_STATE__", "__APP_STATE__"):
                try:
                    val = await tab.evaluate(f"JSON.stringify(window.{var} || null)")
                    if val and val != "null" and len(val) > 20:
                        _log(f"  [GOMULU] {var} bulundu! boyut={len(val)}", f_txt)
                        entry = {
                            "tip": "gomulu_json",
                            "degisken": var,
                            "sayfa_url": hedef_url,
                            "boyut": len(val),
                            "icerik": json.loads(val),
                        }
                        f_json.write(json.dumps(entry, ensure_ascii=False) + "\n")
                        f_json.flush()
                except Exception as e:
                    pass

            # Network isteklerini yakala (CDP üzerinden)
            try:
                cdp = tab.browser.connection
                # CDP Network.enable
                await cdp.send("Network.enable", tab_id=tab.target_id if hasattr(tab, 'target_id') else None)
            except Exception:
                pass

            # Scroll yaparak API'leri tetikle
            _log("  [scroll] başlıyor …", f_txt)
            for i in range(20):
                try:
                    await tab.evaluate("window.scrollBy(0, 600)")
                    await asyncio.sleep(0.8)
                except Exception:
                    break

            # Scroll sonrası tekrar gömülü JSON kontrol
            for var in ("__NEXT_DATA__",):
                try:
                    val = await tab.evaluate(f"JSON.stringify(window.{var} || null)")
                    if val and val != "null" and len(val) > 20:
                        try:
                            parsed = json.loads(val)
                            entry = {
                                "tip": "gomulu_json_sonra_scroll",
                                "degisken": var,
                                "sayfa_url": hedef_url,
                                "boyut": len(val),
                                "icerik": parsed,
                            }
                            f_json.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            f_json.flush()
                        except Exception:
                            pass
                except Exception:
                    pass

            # Sayfadaki tüm fetch/XHR sonuçlarını performans entries üzerinden dene
            try:
                perf = await tab.evaluate("""
                    JSON.stringify(
                        performance.getEntriesByType('resource')
                        .filter(e => e.initiatorType === 'fetch' || e.initiatorType === 'xmlhttprequest')
                        .map(e => ({url: e.name, duration: Math.round(e.duration), size: e.transferSize}))
                        .slice(0, 100)
                    )
                """)
                if perf and perf != "null":
                    entries = json.loads(perf)
                    _log(f"  [perf] {len(entries)} fetch/XHR isteği bulundu:", f_txt)
                    for e in entries:
                        url = e.get("url", "")
                        if re.search(r"(search|product|catalog|category|promo|offer|assortment|api)", url, re.I):
                            _log(f"    -> {url[:110]}", f_txt)
                    f_json.write(json.dumps({"tip": "perf_entries", "sayfa": hedef_url, "entries": entries}, ensure_ascii=False) + "\n")
                    f_json.flush()
            except Exception as e:
                _log(f"  [perf hata] {e}", f_txt)

            son_url = await tab.evaluate("window.location.href")
            baslik = await tab.evaluate("document.title")
            _log(f"  [son] url={son_url}  baslik={baslik}", f_txt)

            await asyncio.sleep(2)

        await browser.stop()
        _log(f"\n=== Bitti {datetime.now()} ===", f_txt)

    print(f"\nDosyalar:\n  {LOG_TXT}\n  {LOG_JSONL}")


if __name__ == "__main__":
    asyncio.run(calistir())
