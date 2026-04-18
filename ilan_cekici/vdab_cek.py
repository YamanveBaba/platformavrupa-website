# -*- coding: utf-8 -*-
"""
VDAB is ilani cekici - Playwright ile pagination butonuna tiklar.

Kullanim:
  python vdab_cek.py --max 2000
  python vdab_cek.py --max 500 --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import random
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("HATA: pip install requests"); sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("HATA: pip install playwright && python -m playwright install chromium"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPIRY_GUN = 30

SEKTOR_ESLEME = {
    "Restoran":  ["kok", "chef", "keuken", "restaurant", "horeca", "bakker", "slager", "catering"],
    "Insaat":    ["bouw", "elektricien", "loodgieter", "monteur", "architect", "timmerman"],
    "Lojistik":  ["chauffeur", "transport", "logistiek", "magazijn", "koerier", "vrachtwagen"],
    "Temizlik":  ["schoonmaak", "poetsen", "reiniging", "huishoudelijk"],
    "Saglik":    ["verpleeg", "zorg", "arts", "dokter", "apotheek", "kine", "medisch", "thuiszorg"],
    "Satis":     ["verkoop", "sales", "winkel", "retail", "handelaar", "account"],
    "Bilisim":   ["software", "developer", "it ", "data", "cloud", "programmeur", "analist", "ict"],
    "Guvenlik":  ["bewaking", "beveiliging", "security", "bewaker"],
    "Ofis":      ["admin", "office", "hr ", "boekhouding", "secretar", "receptie", "manager", "directeur"],
    "Egitim":    ["leerkracht", "leraar", "trainer", "onderwijs", "begeleider", "coach"],
    "Uretim":    ["productie", "operator", "fabriek", "assemblage", "lasser", "machinebediener"],
}

def sektor_bul(text: str) -> str:
    t = text.lower()
    for sektor, kelimeler in SEKTOR_ESLEME.items():
        if any(k in t for k in kelimeler):
            return sektor
    return "Diger"

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt"))
    if os.path.isfile(path):
        lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: Supabase credentials bulunamadi."); sys.exit(1)

def upsert_ilanlar(sb_url: str, sb_key: str, rows: list[dict], dry_run: bool) -> int:
    if dry_run or not rows:
        return len(rows)
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }
    r = requests.post(f"{sb_url}/rest/v1/ilanlar", json=rows, headers=headers, timeout=60)
    if r.status_code not in (200, 201, 204):
        print(f"  UYARI: upsert hatasi {r.status_code}: {r.text[:200]}")
        return 0
    return len(rows)

def parse_ilan(job: dict) -> dict | None:
    job_id = str(job.get("id", {}).get("id", ""))
    if not job_id:
        return None
    vf = job.get("vacaturefunctie", {}) or {}
    baslik = vf.get("naam", "") or ""
    if not baslik:
        return None
    firma = job.get("vacatureBedrijfsnaam", "") or ""
    sehir = job.get("tewerkstellingsLocatieRegioOfAdres", "") or "Belgie"
    tijds = " ".join(job.get("tijdsregeling", []) or []).lower()
    pozisyon = "Uzaktan" if "thuis" in tijds else ("Yari Zamanli" if "deel" in tijds else "Ofis")
    contract = vf.get("arbeidscircuitLijn", "") or ""
    return {
        "title":        baslik[:300],
        "description":  contract[:500],
        "category":     "Is Ilani",
        "sub_category": "Tam Zamanli",
        "status":       "active",
        "source":       "vdab",
        "source_id":    job_id,
        "source_url":   f"https://www.vdab.be/vindeenjob/vacatures/{job_id}",
        "owner_name":   firma[:200],
        "city":         sehir[:100],
        "country":      "BE",
        "sektor":       sektor_bul(baslik + " " + firma),
        "pozisyon":     pozisyon,
        "price":        "",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "expires_at":   (datetime.now(timezone.utc) + timedelta(days=EXPIRY_GUN)).isoformat(),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=2000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN]\n")

    tum_ilanlar = []
    pending_save = []
    sayfa_no = 0
    start = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="nl-BE",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        api_queue: list[dict] = []
        captured_request = {}  # ilk başarılı isteği sakla

        def on_response(resp):
            if "vacatureLight/zoek" in resp.url and resp.status == 200:
                try:
                    # İsteğin tam bilgilerini sakla
                    if not captured_request:
                        captured_request["headers"] = dict(resp.request.headers)
                        captured_request["method"] = resp.request.method
                    api_queue.append(resp.json())
                except Exception:
                    pass

        page.on("response", on_response)

        print("VDAB aciliyor...")
        page.goto("https://www.vdab.be/vindeenjob/vacatures", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # Cookie banner'i kapat
        for selector in [
            "button#uc-accept-all-button",
            "button[data-testid='uc-accept-all-button']",
            "button.uc-accepting",
            "#usercentrics-root button",
            "button:has-text('Alles accepteren')",
            "button:has-text('Accepteer')",
            "button:has-text('OK')",
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    print("  Cookie banner kapatildi.")
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        page.wait_for_timeout(4000)  # Angular render icin bekle

        # Kullanicidan login bekle
        print("\nTabrayici acildi. VDAB hesabina giris yap, sonra terminale don ve Enter'a bas.")
        input("Giris yapinca Enter'a bas: ")
        page.wait_for_timeout(2000)

        toplam_vdab = 0
        if api_queue:
            toplam_vdab = api_queue[0].get("totaalAantal", 0)
            print(f"VDAB toplam ilan: {toplam_vdab:,}")

        hedef = min(args.max, toplam_vdab) if toplam_vdab else args.max
        print(f"Cekilecek: {hedef:,}\n")

        while len(tum_ilanlar) < hedef:
            # Kuyruktaki veriyi işle
            if api_queue:
                data = api_queue.pop(0)
                resultaten = data.get("resultaten", [])

                for job in resultaten:
                    if len(tum_ilanlar) >= hedef:
                        break
                    ilan = parse_ilan(job)
                    if ilan:
                        tum_ilanlar.append(ilan)
                        pending_save.append(ilan)

                elapsed = time.time() - start
                rate = len(tum_ilanlar) / max(elapsed, 1)
                kalan_dk = (hedef - len(tum_ilanlar)) / max(rate, 1) / 60
                print(f"  Sayfa {sayfa_no}: {len(resultaten)} ilan | Toplam: {len(tum_ilanlar)}/{hedef} | ~{kalan_dk:.0f} dk kaldi")

                if len(pending_save) >= 500:
                    upsert_ilanlar(sb_url, sb_key, pending_save, args.dry_run)
                    if not args.dry_run:
                        print(f"  --> DB'ye {len(pending_save)} ilan yazildi.")
                    pending_save = []

                sayfa_no += 1

                if len(tum_ilanlar) >= hedef:
                    break

                # Playwright APIRequestContext ile — Chrome TLS fingerprint, tam cookie
                # Keyboard End + Page Down ile scroll tetikle
                try:
                    page.keyboard.press("End")
                    page.wait_for_timeout(1000)
                    for _ in range(8):
                        page.keyboard.press("PageDown")
                        page.wait_for_timeout(600)
                        if api_queue:
                            break

                    if not api_queue:
                        # Son ilanın altındaki elementi bul ve oraya scroll et
                        page.evaluate("""
                            () => {
                                const all = document.querySelectorAll('*');
                                let deepest = null;
                                let maxTop = 0;
                                all.forEach(el => {
                                    const r = el.getBoundingClientRect();
                                    if (r.top > maxTop && r.height > 0) {
                                        maxTop = r.top;
                                        deepest = el;
                                    }
                                });
                                if (deepest) deepest.scrollIntoView();
                            }
                        """)
                        page.wait_for_timeout(2000)

                    if not api_queue:
                        print("  Yeni ilan yuklenemedi, duruldu.")
                        break
                except Exception as e:
                    print(f"  Hata: {e}")
                    break

                if not api_queue:
                    print("  Yeni ilan alinamadi, duruldu.")
                    break

            else:
                # Kuyruk boş, bekle
                page.wait_for_timeout(1000)
                if not api_queue:
                    print("  API yaniti bekleniyor...")
                    page.wait_for_timeout(2000)
                    if not api_queue:
                        break

        browser.close()

    if pending_save:
        upsert_ilanlar(sb_url, sb_key, pending_save, args.dry_run)
        if not args.dry_run:
            print(f"  --> DB'ye {len(pending_save)} ilan yazildi.")

    elapsed = time.time() - start
    print(f"\nTamamlandi. {len(tum_ilanlar)} ilan cekildi, {elapsed/60:.1f} dakika.")

if __name__ == "__main__":
    main()
