# -*- coding: utf-8 -*-
"""
VDAB network trafiğini dinle — API endpoint bul.
pip install playwright && python -m playwright install chromium
"""
import json
import time
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # görünür aç
        page = browser.new_page()

        api_calls = []

        def on_response(response):
            url = response.url
            # Sadece JSON döndüren çağrıları yakala
            ct = response.headers.get("content-type", "")
            if "json" in ct and ("vdab" in url or "vacature" in url.lower()):
                try:
                    body = response.json()
                    api_calls.append({"url": url, "status": response.status, "body_preview": str(body)[:200]})
                    print(f"\n[API] {url}")
                    print(f"      Status: {response.status}")
                    print(f"      Preview: {str(body)[:300]}")
                except Exception:
                    pass

        page.on("response", on_response)

        print("VDAB aciliyor...")
        page.goto("https://www.vdab.be/vindeenjob/vacatures", wait_until="networkidle", timeout=30000)
        print("Sayfa yuklendi. 5 sn bekleniyor...")
        time.sleep(5)

        # Scroll yaparak daha fazla ilan yükle
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(3)

        print(f"\nToplam {len(api_calls)} API çağrısı yakalandı.")
        for c in api_calls:
            print(f"\nURL: {c['url']}")
            print(f"Preview: {c['body_preview'][:200]}")

        # Sonuçları dosyaya yaz
        with open("vdab_api_calls.json", "w", encoding="utf-8") as f:
            json.dump(api_calls, f, ensure_ascii=False, indent=2)
        print("\nvdab_api_calls.json dosyasına yazildi.")

        input("\nDevam etmek için Enter'a bas...")
        browser.close()

if __name__ == "__main__":
    main()
