# -*- coding: utf-8 -*-
"""
VDAB is ilani cekici - Playwright ile API intercept eder, requests ile sayfalama yapar.

Kullanim:
  python vdab_cek.py --max 2000
  python vdab_cek.py --max 500 --dry-run
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import unicodedata
import random
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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
    "Restoran":  ["kok", "chef", "keuken", "restaurant", "horeca", "bakker", "slager", "catering",
                  "cuisinier", "patissier", "traiteur", "boulanger"],
    "Saglik":    ["verpleeg", "zorg", "arts", "dokter", "apotheek", "kine", "medisch", "thuiszorg",
                  "infirmier", "soignant", "medecin", "pharmacien", "aide-soignant"],
    "Bilisim":   ["software", "developer", "it ", "data", "cloud", "programmeur", "analist", "ict",
                  "developpeur", "informaticien", "systeme", "reseau", "cyber"],
    "Teknik":    ["elektricien", "elektro", "mechatronica", "lasser", "cnc", "onderhoud",
                  "technicien", "mecanicien", "electricien", "soudeur", "automaticien"],
    "Insaat":    ["bouw", "loodgieter", "monteur", "architect", "timmerman", "aannemer",
                  "construction", "plombier", "menuisier", "charpentier", "genie civil"],
    "Lojistik":  ["chauffeur", "transport", "logistiek", "magazijn", "koerier", "vrachtwagen",
                  "livreur", "conducteur", "magasinier", "supply chain"],
    "Temizlik":  ["schoonmaak", "poetsen", "reiniging", "huishoudelijk",
                  "nettoyage", "agent d entretien", "femme de menage"],
    "Guvenlik":  ["bewaking", "beveiliging", "security", "bewaker",
                  "agent de securite", "gardien", "vigile"],
    "Ofis":      ["admin", "office", "hr ", "boekhouding", "secretar", "receptie", "manager", "directeur",
                  "comptable", "secretaire", "ressources humaines", "directeur", "commercial"],
    "Egitim":    ["leerkracht", "leraar", "trainer", "onderwijs", "begeleider", "coach",
                  "enseignant", "professeur", "formateur", "educateur"],
    "Satis":     ["verkoop", "sales", "winkel", "retail", "handelaar", "account",
                  "vendeur", "commercial", "conseiller de vente"],
    "Uretim":    ["productie", "operator", "fabriek", "assemblage", "machinebediener",
                  "operateur", "production", "montage", "usine"],
}

def _normalize(text: str) -> str:
    return unicodedata.normalize('NFD', text.lower()).encode('ascii', 'ignore').decode('ascii')

def sektor_bul(text: str) -> str:
    t = _normalize(text)
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
        "Prefer": "resolution=merge-duplicates,return=minimal",
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

def _build_page_url(base_url: str, sayfa: int) -> str:
    """base_url'deki pagina parametresini guncelle."""
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["pagina"] = [str(sayfa)]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=2000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN]\n")

    tum_ilanlar: list[dict] = []
    pending_save: list[dict] = []
    start = time.time()

    captured_url: dict = {}
    first_data: dict = {}

    print("VDAB aciliyor (headless)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="nl-BE",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        def on_response(resp):
            if "vacatureLight/zoek" in resp.url and resp.status == 200:
                try:
                    if not captured_url:
                        captured_url["url"] = resp.url
                        captured_url["method"] = resp.request.method
                        try:
                            captured_url["post_data"] = resp.request.post_data
                        except Exception:
                            captured_url["post_data"] = None
                        captured_url["req_headers"] = dict(resp.request.headers)
                    if not first_data:
                        first_data.update(resp.json())
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto("https://www.vdab.be/vindeenjob/vacatures", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)

        # Cookie banner kapat
        for selector in [
            "button#uc-accept-all-button",
            "button[data-testid='uc-accept-all-button']",
            "button:has-text('Alles accepteren')",
            "button:has-text('Accepteer')",
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        page.wait_for_timeout(2000)

        if not captured_url:
            print("HATA: VDAB API endpoint yakalanamadi.")
            browser.close()
            sys.exit(1)

        base_url = captured_url["url"]
        toplam_vdab = first_data.get("totaalAantal", 0)
        sayfa_boyutu = first_data.get("paginaGrootte", 15) or 15
        print(f"VDAB toplam ilan: {toplam_vdab:,} | Sayfa boyutu: {sayfa_boyutu}")

        hedef = min(args.max, toplam_vdab) if toplam_vdab else args.max
        print(f"Cekilecek: {hedef:,}\n")

        # İlk sayfayı işle
        for job in first_data.get("resultaten", []):
            if len(tum_ilanlar) >= hedef:
                break
            ilan = parse_ilan(job)
            if ilan:
                tum_ilanlar.append(ilan)
                pending_save.append(ilan)

        print(f"  Sayfa 1: {len(first_data.get('resultaten', []))} ilan | Toplam: {len(tum_ilanlar)}/{hedef}")

        # --- Kalan sayfaları ctx.request ile çek (Playwright API client, cookie+session paylaşır) ---
        import json as _json

        method = captured_url.get("method", "GET").upper()
        req_url = captured_url["url"]
        req_headers = captured_url.get("req_headers", {})
        post_data_raw = captured_url.get("post_data")

        # POST body varsa parse et (pagination parametresini değiştireceğiz)
        post_body: dict | None = None
        if method == "POST" and post_data_raw:
            try:
                post_body = _json.loads(post_data_raw)
            except Exception:
                post_body = None

        sayfa = 2
        deneme = 0
        max_sayfa = (hedef // sayfa_boyutu) + 2

        while len(tum_ilanlar) < hedef and sayfa <= max_sayfa:
            try:
                page.wait_for_timeout(int(random.uniform(1200, 2500)))

                if method == "POST" and post_body is not None:
                    # POST body'de pagina güncelle
                    body = dict(post_body)
                    body["pagina"] = sayfa
                    api_resp = ctx.request.post(
                        req_url,
                        data=_json.dumps(body),
                        headers={**req_headers, "content-type": "application/json"},
                    )
                else:
                    # GET ile URL'de pagina güncelle
                    url = _build_page_url(req_url, sayfa)
                    api_resp = ctx.request.get(url, headers=req_headers)

                if api_resp.status != 200:
                    print(f"  UYARI: Sayfa {sayfa} HTTP {api_resp.status} — duruldu.")
                    break

                data = api_resp.json()
                resultaten = data.get("resultaten", []) if isinstance(data, dict) else []
                if not resultaten:
                    print(f"  Sayfa {sayfa}: sonuc yok, duruldu.")
                    break

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
                print(f"  Sayfa {sayfa}: {len(resultaten)} ilan | Toplam: {len(tum_ilanlar)}/{hedef} | ~{kalan_dk:.0f} dk kaldi")

                if len(pending_save) >= 500:
                    upsert_ilanlar(sb_url, sb_key, pending_save, args.dry_run)
                    if not args.dry_run:
                        print(f"  --> DB'ye {len(pending_save)} ilan yazildi.")
                    pending_save = []

            except Exception as e:
                deneme += 1
                if deneme >= 3:
                    print(f"  HATA sayfa {sayfa} (3 deneme basti): {str(e)[:80]}")
                    break
                print(f"  Sayfa {sayfa} hata (deneme {deneme}/3), tekrar deneniyor...")
                page.wait_for_timeout(3000)
                continue

            deneme = 0
            sayfa += 1

        browser.close()

    if pending_save:
        upsert_ilanlar(sb_url, sb_key, pending_save, args.dry_run)
        if not args.dry_run:
            print(f"  --> DB'ye {len(pending_save)} ilan yazildi.")

    elapsed = time.time() - start
    print(f"\nTamamlandi. {len(tum_ilanlar)} ilan cekildi, {elapsed/60:.1f} dakika.")

if __name__ == "__main__":
    main()
