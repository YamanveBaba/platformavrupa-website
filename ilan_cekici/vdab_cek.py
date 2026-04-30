# -*- coding: utf-8 -*-
"""
VDAB is ilani cekici - Playwright ile API intercept eder, jobdomein filtresi
ile 3k sayfalama limitini aser, tum ilanları ceker.

Kullanim:
  python vdab_cek.py --max 200000
  python vdab_cek.py --gunler 1 --max 5000   # gunluk
  python vdab_cek.py --gunler 6              # haftalik (tum kategoriler)
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
import json
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

BE_PROVINCE_MAP = {
    "oost-vlaanderen": "Gent",
    "west-vlaanderen": "Brugge",
    "vlaams-brabant":  "Leuven",
    "limburg":         "Hasselt",
    "hainaut":         "Charleroi",
    "brabant wallon":  "Wavre",
    "walloon brabant": "Wavre",
    "luxemburg":       "Arlon",
    "namur":           "Namur",
    "liège":           "Liège",
    "liege":           "Liège",
}

BE_POSTAL_CITY = {
    "10": "Brussels (Bruxelles)", "11": "Brussels (Bruxelles)", "12": "Brussels (Bruxelles)",
    "20": "Antwerpen", "21": "Antwerpen", "22": "Antwerpen", "23": "Antwerpen",
    "24": "Mechelen",
    "30": "Leuven", "31": "Leuven",
    "32": "Hasselt", "33": "Hasselt", "34": "Hasselt", "35": "Hasselt",
    "36": "Turnhout",
    "40": "Liège", "41": "Liège", "42": "Liège", "43": "Liège", "44": "Liège", "45": "Liège",
    "46": "Verviers",
    "50": "Namur", "51": "Namur", "52": "Namur",
    "60": "Charleroi", "61": "Charleroi", "62": "Charleroi",
    "63": "La Louvière",
    "70": "Mons", "71": "Mons", "72": "Mons", "73": "Mons", "74": "Tournai",
    "80": "Brugge", "81": "Brugge", "82": "Brugge", "83": "Brugge",
    "84": "Kortrijk", "85": "Kortrijk",
    "86": "Roeselare",
    "88": "Ostend (Oostende)",
    "90": "Gent", "91": "Gent", "92": "Gent", "93": "Aalst",
    "94": "Sint-Niklaas",
    "96": "Genk", "97": "Genk",
    "98": "Hasselt",
}

def normalize_city(raw: str) -> str:
    if not raw or raw.strip().lower() in ("belgie", "belgique", "belgium", ""):
        return "Belgie"
    s = raw.strip()
    m = re.match(r'^\d{4}\s+(.+)', s)
    if m:
        return m.group(1).strip()
    m2 = re.match(r'^(\d{4})$', s)
    if m2:
        return BE_POSTAL_CITY.get(s[:2], "Belgie")
    lower = s.lower()
    for key, city in BE_PROVINCE_MAP.items():
        if key in lower:
            return city
    return s


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
    seen = set()
    unique_rows = []
    for r in rows:
        key = r.get("source_id", "")
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)
    rows = unique_rows
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    r = requests.post(f"{sb_url}/rest/v1/ilanlar?on_conflict=source,source_id", json=rows, headers=headers, timeout=60)
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
    sehir = normalize_city(job.get("tewerkstellingsLocatieRegioOfAdres", "") or "Belgie")
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
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["pagina"] = [str(sayfa)]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))

LIMIT = 2800  # 3000'e yakin ama guvenli sinir — asildiysa alt filtrele

def _cek_sayfalar(ctx, req_url, req_headers, method, body_template,
                  etiket, hedef, goruldu, tum_ilanlar, pending_save, start, page) -> int:
    """Verilen body ile tum sayfalari ceker. Yeni ilan sayisini dondurur."""
    yeni = 0
    sayfa = 1
    bos_sayaci = 0

    while len(tum_ilanlar) < hedef:
        try:
            if sayfa > 1:
                bekleme = int(random.uniform(600, 1500)) if sayfa % 20 != 0 else int(random.uniform(4000, 8000))
                page.wait_for_timeout(bekleme)

            body = json.loads(json.dumps(body_template))
            body["pagina"] = sayfa

            if method == "POST":
                api_resp = ctx.request.post(req_url, data=json.dumps(body),
                                            headers={**req_headers, "content-type": "application/json"})
            else:
                api_resp = ctx.request.get(_build_page_url(req_url, sayfa), headers=req_headers)

            if api_resp.status != 200:
                print(f"    HTTP {api_resp.status} — atlandi.")
                break

            data = api_resp.json()
            resultaten = data.get("resultaten", []) if isinstance(data, dict) else []
            if not resultaten:
                break

            onceki = len(tum_ilanlar)
            for job in resultaten:
                if len(tum_ilanlar) >= hedef:
                    break
                ilan = parse_ilan(job)
                if ilan and ilan["source_id"] not in goruldu:
                    goruldu.add(ilan["source_id"])
                    tum_ilanlar.append(ilan)
                    pending_save.append(ilan)
                    yeni += 1

            sayfa_yeni = len(tum_ilanlar) - onceki
            bos_sayaci = 0 if sayfa_yeni > 0 else bos_sayaci + 1
            if bos_sayaci >= 5:
                break

            print(f"    [{etiket}] Sayfa {sayfa}: {len(resultaten)} | yeni: {yeni} | toplam: {len(tum_ilanlar):,}")
            sayfa += 1

        except Exception as e:
            print(f"    [{etiket}] Hata: {str(e)[:60]}")
            break

    return yeni


def _body_ile(base_body, jobdomein=None, arbeidsduur=None, ervaring=None) -> dict:
    body = json.loads(json.dumps(base_body))
    criteria = body.get("criteria", body)
    if jobdomein:
        criteria["jobdomeinCodes"] = [jobdomein]
    if arbeidsduur:
        criteria["arbeidsduurCodes"] = [arbeidsduur]
    if ervaring is not None:
        criteria["ervaringCodes"] = [str(ervaring)]
    return body


def cek_kategori(ctx, req_url, req_headers, method, base_body,
                 jobdomein_code, jobdomein_naam, tahmini_adet,
                 hedef, goruldu, tum_ilanlar, pending_save, start, page) -> int:
    """
    Kategoriyi ceker. Buyuk kategorileri arbeidsduur ve ervaring ile boler.
    """
    ARBEIDSDUUR = ["V", "D"]           # Voltijds, Deeltijds
    ERVARINGEN  = ["0", "1", "2", "3", "4"]

    yeni_toplam = 0

    if tahmini_adet <= LIMIT:
        # Kucuk kategori — direkt cek
        body = _body_ile(base_body, jobdomein=jobdomein_code)
        yeni_toplam += _cek_sayfalar(ctx, req_url, req_headers, method, body,
                                     jobdomein_naam, hedef, goruldu,
                                     tum_ilanlar, pending_save, start, page)
    else:
        # Buyuk kategori — arbeidsduur ile bol
        for ad in ARBEIDSDUUR:
            if len(tum_ilanlar) >= hedef:
                break
            etiket = f"{jobdomein_naam}/{ad}"

            # Bu alt-kombinasyonun tahmini boyutunu bulmak icin 1 sorgu at
            body = _body_ile(base_body, jobdomein=jobdomein_code, arbeidsduur=ad)
            body["pagina"] = 1
            try:
                if method == "POST":
                    r = ctx.request.post(req_url, data=json.dumps(body),
                                         headers={**req_headers, "content-type": "application/json"})
                else:
                    r = ctx.request.get(_build_page_url(req_url, 1), headers=req_headers)
                alt_adet = r.json().get("totaalAantal", 0) if r.status == 200 else 0
            except Exception:
                alt_adet = 0

            if alt_adet <= LIMIT:
                yeni_toplam += _cek_sayfalar(ctx, req_url, req_headers, method, body,
                                              etiket, hedef, goruldu,
                                              tum_ilanlar, pending_save, start, page)
            else:
                # Hala buyuk — ervaring ile de bol
                for erv in ERVARINGEN:
                    if len(tum_ilanlar) >= hedef:
                        break
                    body2 = _body_ile(base_body, jobdomein=jobdomein_code,
                                      arbeidsduur=ad, ervaring=erv)
                    etiket2 = f"{jobdomein_naam}/{ad}/erv{erv}"
                    yeni_toplam += _cek_sayfalar(ctx, req_url, req_headers, method, body2,
                                                  etiket2, hedef, goruldu,
                                                  tum_ilanlar, pending_save, start, page)
                    page.wait_for_timeout(int(random.uniform(1000, 2000)))

            page.wait_for_timeout(int(random.uniform(1500, 3000)))

    return yeni_toplam

def expired_yap(sb_url: str, sb_key: str, dry_run: bool) -> int:
    sinir = (datetime.now(timezone.utc) - timedelta(days=EXPIRY_GUN)).isoformat()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    params = {"source": "eq.vdab", "status": "eq.active",
              "created_at": f"lt.{sinir}", "select": "id"}
    r = requests.get(f"{sb_url}/rest/v1/ilanlar", params=params, headers=headers, timeout=30)
    m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
    toplam = int(m.group(1)) if m else 0
    if toplam == 0:
        print("  Süresi dolan VDAB ilanı yok.")
        return 0
    if dry_run:
        print(f"  [dry-run] {toplam} VDAB ilanı expired yapılacaktı.")
        return toplam
    patch = requests.patch(
        f"{sb_url}/rest/v1/ilanlar?source=eq.vdab&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"},
        headers={**headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
        timeout=60,
    )
    if patch.status_code not in (200, 204):
        print(f"  UYARI: VDAB expired güncelleme hatası {patch.status_code}")
        return 0
    print(f"  {toplam} VDAB ilanı expired yapıldı.")
    return toplam


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=200000)
    parser.add_argument("--gunler", type=int, default=0,
                        help="0=hepsi, 1=bugun/dun, 6=gecen hafta")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--temizle", action="store_true",
                        help=f"30 günden eski VDAB ilanlarını expired yap")
    args = parser.parse_args()

    ONLINE_SINDS_CODE = "9000" if args.gunler == 0 else str(args.gunler)

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN]\n")

    tum_ilanlar: list[dict] = []
    pending_save: list[dict] = []
    goruldu: set = set()
    basarili_yazilan = 0
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

        toplam_vdab = first_data.get("totaalAantal", 0)
        sayfa_boyutu = first_data.get("paginaGrootte", 15) or 15
        print(f"VDAB toplam ilan: {toplam_vdab:,} | Sayfa boyutu: {sayfa_boyutu}")

        hedef = min(args.max, toplam_vdab) if toplam_vdab else args.max
        print(f"Hedef: {hedef:,}\n")

        # Jobdomein kategorilerini al
        kategoriler = first_data.get("filters", {}).get("jobdomein", [])
        if not kategoriler:
            print("HATA: Jobdomein filtreleri alinamadi.")
            browser.close()
            sys.exit(1)

        print(f"{len(kategoriler)} jobdomein kategorisi bulundu:\n")
        for k in kategoriler:
            print(f"  {k['omschrijving']}: {k['aantalResultaten']:,}")
        print()

        method = captured_url.get("method", "GET").upper()
        req_url = captured_url["url"]
        req_headers = captured_url.get("req_headers", {})
        post_data_raw = captured_url.get("post_data")

        base_body: dict = {}
        if method == "POST" and post_data_raw:
            try:
                base_body = json.loads(post_data_raw)
                if base_body.get("criteria") is not None:
                    base_body["criteria"]["onlineSindsCode"] = ONLINE_SINDS_CODE
                else:
                    base_body["onlineSindsCode"] = ONLINE_SINDS_CODE
            except Exception:
                base_body = {"criteria": {"onlineSindsCode": ONLINE_SINDS_CODE}}

        # Her kategori icin ayri cekis
        for i, kategori in enumerate(kategoriler):
            if len(tum_ilanlar) >= hedef:
                break

            kod = kategori["code"]
            naam = kategori["omschrijving"]
            tahmini = kategori["aantalResultaten"]

            print(f"[{i+1}/{len(kategoriler)}] {naam} (~{tahmini:,} ilan)...")

            yeni = cek_kategori(
                ctx, req_url, req_headers, method, base_body,
                kod, naam, tahmini,
                hedef, goruldu, tum_ilanlar, pending_save, start, page
            )

            print(f"  --> {naam}: {yeni} yeni benzersiz ilan | Toplam: {len(tum_ilanlar):,}\n")

            if len(pending_save) >= 500:
                yazilan = upsert_ilanlar(sb_url, sb_key, pending_save, args.dry_run)
                if not args.dry_run:
                    basarili_yazilan += yazilan
                    print(f"  --> DB'ye {yazilan} ilan yazildi. (toplam: {basarili_yazilan:,})\n")
                pending_save = []

            # Kategoriler arasi kisa mola
            page.wait_for_timeout(int(random.uniform(2000, 5000)))

        browser.close()

    if pending_save:
        yazilan = upsert_ilanlar(sb_url, sb_key, pending_save, args.dry_run)
        if not args.dry_run:
            basarili_yazilan += yazilan
            print(f"  --> DB'ye {yazilan} ilan yazildi.")

    elapsed = time.time() - start
    print(f"\nTamamlandi. {len(tum_ilanlar):,} benzersiz ilan cekildi, "
          f"{basarili_yazilan:,} DB'ye yazildi, {elapsed/60:.1f} dakika.")

    if args.temizle:
        print(f"\n[Temizle] {EXPIRY_GUN} günden eski VDAB ilanları expire ediliyor...")
        expired_yap(sb_url, sb_key, args.dry_run)

if __name__ == "__main__":
    main()
