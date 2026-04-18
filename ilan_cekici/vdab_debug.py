# VDAB veri yapısını göster
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(locale="nl-BE")
    page = ctx.new_page()

    captured = {}
    def on_response(resp):
        if "vacatureLight/zoek" in resp.url and resp.status == 200:
            try:
                captured["data"] = resp.json()
            except:
                pass

    page.on("response", on_response)
    page.goto("https://www.vdab.be/vindeenjob/vacatures", wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(4000)
    browser.close()

if captured.get("data"):
    data = captured["data"]
    print(f"totaalAantal: {data.get('totaalAantal')}")
    print(f"pagina: {data.get('pagina')}")
    print(f"paginaGrootte: {data.get('paginaGrootte')}")
    resultaten = data.get("resultaten", [])
    print(f"resultaten sayisi: {len(resultaten)}")
    if resultaten:
        print("\nIlk ilan yapisi:")
        print(json.dumps(resultaten[0], indent=2, ensure_ascii=False)[:1500])
else:
    print("Hic veri yakalanamadi!")
