# -*- coding: utf-8 -*-
"""
Platform Avrupa — Otomatik İş İlanı Çekici
Kaynaklar: Arbeitnow + Adzuna + Bundesagentur + Jobicy + Remotive

Kullanım:
  python is_ilani_cekici.py                       # Tüm kaynaklar
  python is_ilani_cekici.py --kaynak arbeitnow
  python is_ilani_cekici.py --kaynak adzuna
  python is_ilani_cekici.py --kaynak bundesagentur
  python is_ilani_cekici.py --kaynak jobicy
  python is_ilani_cekici.py --kaynak remotive
  python is_ilani_cekici.py --ulke DE             # Sadece Almanya
  python is_ilani_cekici.py --dry-run             # Supabase'e yazma
  python is_ilani_cekici.py --temizle             # Süresi dolan ilanları expired yap
  python is_ilani_cekici.py --quick               # Her kaynakta min. istek (smoke test)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── AYARLAR ──────────────────────────────────────────────────────────────────

ADZUNA_ID  = "c0c66624"
ADZUNA_KEY = "5a2d86df68a24e6fe8b1e9b4319347f0"

ADZUNA_ULKELER = {
    "be": "BE", "de": "DE", "nl": "NL", "fr": "FR",
    "at": "AT", "ch": "CH", "pl": "PL", "it": "IT", "es": "ES",
}

EXPIRY_GUN = 30

AVRUPA_ANAHTAR = [
    "germany", "deutschland", "almanya",
    "belgium", "belgique", "belgie", "belcika",
    "netherlands", "nederland", "hollanda",
    "france", "frankreich", "fransa",
    "austria", "osterreich", "avusturya",
    "switzerland", "schweiz", "svizzera", "isvicre",
    "luxembourg", "luxemburg",
    "sweden", "sverige", "isvec",
    "norway", "norwegen",
    "denmark", "danemark",
    "spain", "espana", "spanien", "ispanya",
    "italy", "italien", "italya",
    "poland", "polen", "polonya",
    "remote", "avrupa", "europe",
    "berlin", "munchen", "hamburg", "frankfurt", "koln", "stuttgart", "dusseldorf",
    "brussels", "bruxelles", "brussel", "antwerp", "antwerpen", "gent",
    "amsterdam", "rotterdam", "den haag",
    "paris", "lyon", "marseille",
    "vienna", "wien",
    "zurich", "zurich", "geneva",
    "madrid", "barcelona",
    "rome", "roma", "milan", "milano",
    "warsaw", "warszawa",
]

SEKTOR_ESLEME = {
    "Restoran": ["cook", "chef", "kitchen", "restaurant", "food", "horeca", "gastro", "backer", "kuche", "catering"],
    "Insaat":   ["construction", "builder", "electrician", "plumber", "bau", "handwerk", "monteur", "architect"],
    "Lojistik": ["driver", "logistics", "warehouse", "delivery", "transport", "fahrer", "lager", "chauffeur"],
    "Temizlik": ["cleaning", "cleaner", "housekeeping", "reinigung", "schoonmaak"],
    "Saglik":   ["nurse", "doctor", "care", "health", "medical", "pflege", "kranken", "arzt", "pharmacist"],
    "Satis":    ["sales", "retail", "shop", "store", "verkauf", "handel", "account manager", "verkoops"],
    "Bilisim":  ["software", "developer", "it ", "data", "cloud", "devops", "engineer", "programmer", "frontend", "backend", "fullstack"],
    "Guvenlik": ["security", "guard", "bewachung", "beveiliging"],
    "Ofis":     ["admin", "office", "hr ", "finance", "accounting", "manager", "secretary", "receptionist", "buchhalter"],
    "Egitim":   ["teacher", "trainer", "education", "lehrer", "schule", "coach"],
    "Uretim":   ["production", "manufacturing", "assembly", "operator", "fabrik", "montage"],
}

def sektor_bul(text: str) -> str:
    t = text.lower()
    for sektor, kelimeler in SEKTOR_ESLEME.items():
        if any(k in t for k in kelimeler):
            return sektor
    return "Diger"

def ulke_bul(location: str) -> str:
    l = location.lower()
    if any(k in l for k in ["germany", "deutschland", "berlin", "munchen", "hamburg",
                              "frankfurt", "koln", "stuttgart", "dusseldorf"]):
        return "DE"
    if any(k in l for k in ["belgium", "belgique", "belgie", "brussels", "bruxelles",
                              "brussel", "antwerp", "antwerpen", "gent"]):
        return "BE"
    if any(k in l for k in ["netherlands", "nederland", "amsterdam", "rotterdam", "den haag", "utrecht"]):
        return "NL"
    if any(k in l for k in ["france", "paris", "lyon", "marseille", "toulouse", "bordeaux"]):
        return "FR"
    if any(k in l for k in ["austria", "osterreich", "vienna", "wien", "graz", "salzburg"]):
        return "AT"
    if any(k in l for k in ["switzerland", "schweiz", "zurich", "geneva", "bern"]):
        return "CH"
    if any(k in l for k in ["spain", "espana", "madrid", "barcelona", "seville"]):
        return "ES"
    if any(k in l for k in ["italy", "italia", "rome", "milan", "milano", "roma"]):
        return "IT"
    if any(k in l for k in ["poland", "polska", "warsaw", "warszawa", "krakow"]):
        return "PL"
    if any(k in l for k in ["luxembourg", "luxemburg"]):
        return "LU"
    return "EU"

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    secrets_path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt"))
    if os.path.isfile(secrets_path):
        lines = [l.strip() for l in open(secrets_path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: Supabase credentials bulunamiadi.")
    sys.exit(1)

def mevcut_source_idler(sb_url: str, sb_key: str, source: str) -> set:
    """Verilen source için DB'deki tüm source_id'leri çek."""
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    idler = set()
    offset = 0
    while True:
        r = requests.get(
            f"{sb_url}/rest/v1/ilanlar",
            params={"select": "source_id", "source": f"eq.{source}", "limit": "1000", "offset": str(offset)},
            headers=headers, timeout=30,
        )
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        for row in data:
            if row.get("source_id"):
                idler.add(str(row["source_id"]))
        if len(data) < 1000:
            break
        offset += 1000
    return idler

def upsert_ilanlar(sb_url: str, sb_key: str, rows: list[dict], dry_run: bool) -> int:
    """(source, source_id) çakışınca satırı güncelle — 409 spam'ini önler."""
    if dry_run or not rows:
        return len(rows)
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    url = f"{sb_url}/rest/v1/ilanlar?on_conflict=source,source_id"
    r = requests.post(url, json=rows, headers=headers, timeout=120)
    if r.status_code in (200, 201, 204):
        return len(rows)
    if len(rows) > 1:
        yari = len(rows) // 2
        return upsert_ilanlar(sb_url, sb_key, rows[:yari], dry_run) + upsert_ilanlar(
            sb_url, sb_key, rows[yari:], dry_run
        )
    print(f"  UYARI: upsert {r.status_code}: {r.text[:300]}")
    return 0

def expired_yap(sb_url: str, sb_key: str, dry_run: bool) -> int:
    sinir = (datetime.now(timezone.utc) - timedelta(days=EXPIRY_GUN)).isoformat()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    params = {"source": "not.eq.user", "status": "eq.active", "created_at": f"lt.{sinir}", "select": "id"}
    r = requests.get(f"{sb_url}/rest/v1/ilanlar", params=params, headers=headers, timeout=30)
    m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
    toplam = int(m.group(1)) if m else 0
    if toplam == 0:
        print("  Suresi dolan ilan yok.")
        return 0
    if dry_run:
        print(f"  [dry-run] {toplam} ilan expired yapilacakti.")
        return toplam
    patch_headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    patch = requests.patch(
        f"{sb_url}/rest/v1/ilanlar?source=not.eq.user&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"},
        headers=patch_headers,
        timeout=60,
    )
    if patch.status_code not in (200, 204):
        print(f"  UYARI: expired guncelleme hatasi {patch.status_code}")
        return 0
    print(f"  {toplam} ilan expired yapildi.")
    return toplam

def _yeni_ilan(title, aciklama, source, source_id, source_url, firma, sehir, ulke) -> dict:
    return {
        "title":        (title or "")[:300],
        "description":  (aciklama or "")[:2000],
        "category":     "Is Ilani",
        "sub_category": "Tam Zamanli",
        "status":       "active",
        "source":       source,
        "source_id":    str(source_id),
        "source_url":   source_url or "",
        "owner_name":   (firma or "")[:200],
        "city":         (sehir or "")[:100],
        "country":      ulke,
        "sektor":       sektor_bul(title + " " + aciklama),
        "pozisyon":     "Ofis",
        "price":        "",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "expires_at":   (datetime.now(timezone.utc) + timedelta(days=EXPIRY_GUN)).isoformat(),
    }

# ─── ARBEITNOW ────────────────────────────────────────────────────────────────

def arbeitnow_cek(filtre_ulke: Optional[str] = None, max_sayfa: int = 20) -> list[dict]:
    print("\n[Arbeitnow] Cekiliyor...")
    ilanlar = []
    sayfa = 1

    while sayfa <= max_sayfa:
        try:
            r = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"page": sayfa},
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0"},
            )
        except Exception as e:
            print(f"  Sayfa {sayfa} hata: {e}")
            break

        if r.status_code == 429:
            time.sleep(60)
            continue
        if r.status_code != 200:
            break

        data = r.json().get("data", [])
        if not data:
            break

        for job in data:
            loc = job.get("location", "") or ""
            if not any(k in loc.lower() for k in AVRUPA_ANAHTAR):
                continue
            ulke = ulke_bul(loc)
            if filtre_ulke and ulke != filtre_ulke:
                continue
            sehir = loc.split(",")[0].strip()
            ilan = _yeni_ilan(
                job.get("title"), job.get("description", ""),
                "arbeitnow", job.get("slug", ""),
                job.get("url", ""), job.get("company_name", ""),
                sehir, ulke
            )
            if job.get("remote"):
                ilan["pozisyon"] = "Uzaktan"
            ilanlar.append(ilan)

        print(f"  Sayfa {sayfa}: {len(data)} ilan (Avrupa: {len(ilanlar)})")
        sayfa += 1
        time.sleep(random.uniform(0.8, 1.5))

    print(f"  Arbeitnow toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── ADZUNA ───────────────────────────────────────────────────────────────────

def adzuna_cek(
    filtre_ulke: Optional[str] = None,
    max_sayfa_baslama: int = 10,
    max_ulkeler: Optional[int] = None,
) -> list[dict]:
    print("\n[Adzuna] Cekiliyor...")
    ilanlar = []
    ulkeler = ADZUNA_ULKELER
    if filtre_ulke:
        ulkeler = {k: v for k, v in ADZUNA_ULKELER.items() if v == filtre_ulke}

    ulke_iter = 0
    for az_kod, pa_kod in ulkeler.items():
        if max_ulkeler is not None and ulke_iter >= max_ulkeler:
            break
        ulke_iter += 1
        ulke_sayac = 0
        for sayfa in range(1, max_sayfa_baslama + 1):
            try:
                r = requests.get(
                    f"https://api.adzuna.com/v1/api/jobs/{az_kod}/search/{sayfa}",
                    params={
                        "app_id": ADZUNA_ID,
                        "app_key": ADZUNA_KEY,
                        "results_per_page": 50,
                        "content-type": "application/json",
                    },
                    timeout=20,
                )
            except Exception as e:
                print(f"  {az_kod} sayfa {sayfa} hata: {e}")
                break

            if r.status_code == 429:
                time.sleep(60)
                continue
            if r.status_code != 200:
                break

            results = r.json().get("results", [])
            if not results:
                break

            for job in results:
                sehir = ""
                loc = job.get("location", {})
                if loc:
                    area = loc.get("area", [])
                    sehir = area[-1] if area else loc.get("display_name", "")
                firma = (job.get("company") or {}).get("display_name", "")
                sal_min = job.get("salary_min")
                sal_max = job.get("salary_max")
                maas = ""
                if sal_min and sal_max:
                    maas = f"{int(sal_min):,}-{int(sal_max):,} EUR/yil"
                elif sal_min:
                    maas = f"{int(sal_min):,}+ EUR/yil"

                ilan = _yeni_ilan(
                    job.get("title"), job.get("description", ""),
                    f"adzuna_{az_kod}", str(job.get("id", "")),
                    job.get("redirect_url", ""), firma, sehir, pa_kod
                )
                ilan["price"] = maas
                cat = (job.get("category") or {}).get("label", "")
                ilan["sektor"] = sektor_bul(
                    (job.get("title") or "") + " " + (job.get("description") or "") + " " + cat
                )
                ilanlar.append(ilan)
                ulke_sayac += 1

            print(f"  {az_kod.upper()} sayfa {sayfa}: {len(results)} ilan")
            time.sleep(random.uniform(0.5, 1.0))

        print(f"  {az_kod.upper()} toplam: {ulke_sayac} ilan")

    print(f"  Adzuna toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── BUNDESAGENTUR ────────────────────────────────────────────────────────────

BA_TOKEN_URL = "https://rest.arbeitsagentur.de/oauth/gettoken_cc"
BA_CLIENT_ID = "c003a37f-024f-462a-b36d-b001be4cd24a"
BA_CLIENT_SECRET = "32a39620-32b3-4307-9aa1-511e3d7f48a8"


def bundesagentur_token_al() -> tuple[Optional[str], str]:
    """OAuth token; hata stringi UTF-8 ve Content-Type ile detaylı."""
    try:
        r = requests.post(
            BA_TOKEN_URL,
            data={
                "client_id": BA_CLIENT_ID,
                "client_secret": BA_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "User-Agent": "Jobsuche/2.9.2",
            },
            timeout=20,
        )
    except Exception as e:
        return None, str(e)

    raw = (r.text or "").strip()
    if r.status_code != 200:
        return None, f"HTTP {r.status_code} Content-Type={r.headers.get('Content-Type','')} ilk300={raw[:300]!r}"

    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")

    if not raw:
        return None, "Bos cevap govdesi"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"JSON degil ({e}); baslangic={raw[:400]!r}"

    tok = data.get("access_token")
    if not tok:
        return None, f"access_token yok; keys={list(data.keys())}"
    return str(tok), ""


def bundesagentur_cek(max_sayfa: int = 20) -> list[dict]:
    """Almanya Bundesagentur fur Arbeit resmi API (ucretsiz, kayit gerektirmez)."""
    print("\n[Bundesagentur] Cekiliyor...")

    token, err = bundesagentur_token_al()
    if not token:
        print(f"  Token alinamadi: {err}")
        return []

    ilanlar = []
    sayfa = 1

    while sayfa <= max_sayfa:
        try:
            r = requests.get(
                "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs",
                params={
                    "angebotsart": 1,       # 1=Arbeit, 4=Ausbildung
                    "page":        sayfa,
                    "size":        50,
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Jobsuche/2.9.2",
                },
                timeout=20,
            )
        except Exception as e:
            print(f"  Sayfa {sayfa} hata: {e}")
            break

        if r.status_code == 401:
            print("  Token suresi doldu, yenileniyor...")
            token, err = bundesagentur_token_al()
            if not token:
                print(f"  Yenileme basarisiz: {err}")
                break
            continue

        if r.status_code != 200:
            print(f"  HTTP {r.status_code}, duruldu.")
            break

        data = r.json()
        stellenangebote = data.get("stellenangebote", [])
        if not stellenangebote:
            break

        for job in stellenangebote:
            ref_nr = job.get("refnr", "")
            baslik = job.get("titel", "") or ""
            firma = job.get("arbeitgeber", "") or ""
            ort = job.get("arbeitsort", {}) or {}
            sehir = ort.get("ort", "") or ""
            plz = ort.get("plz", "") or ""

            # Detay URL
            source_url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_nr}" if ref_nr else ""

            ilan = _yeni_ilan(
                baslik, "",
                "bundesagentur", ref_nr,
                source_url, firma, sehir, "DE"
            )
            ilanlar.append(ilan)

        gesamt = data.get("maxErgebnisse", "?")
        print(f"  Sayfa {sayfa}: {len(stellenangebote)} ilan (toplam: {len(ilanlar)}, mevcut: {gesamt})")
        sayfa += 1
        time.sleep(random.uniform(0.3, 0.6))

    print(f"  Bundesagentur toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── JOBICY ───────────────────────────────────────────────────────────────────

def jobicy_cek() -> list[dict]:
    """Jobicy - remote is ilanlari (ucretsiz JSON API)."""
    print("\n[Jobicy] Cekiliyor...")
    ilanlar = []

    try:
        r = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 50, "geo": "europe"},
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0"},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            return []
        jobs = r.json().get("jobs", [])
    except Exception as e:
        print(f"  Hata: {e}")
        return []

    for job in jobs:
        job_id = str(job.get("id", ""))
        baslik = job.get("jobTitle", "") or ""
        firma = job.get("companyName", "") or ""
        url = job.get("url", "") or ""
        aciklama = job.get("jobExcerpt", "") or ""
        lokasyon = job.get("jobGeo", "") or "Europe"

        ulke = ulke_bul(lokasyon)

        ilan = _yeni_ilan(baslik, aciklama, "jobicy", job_id, url, firma, lokasyon, ulke)
        ilan["pozisyon"] = "Uzaktan"
        ilanlar.append(ilan)

    # Ikinci istek - genel (geo filtresi olmadan, farkli ilanlar)
    try:
        r2 = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 50},
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0"},
            timeout=20,
        )
        if r2.status_code == 200:
            mevcut_idler = {i["source_id"] for i in ilanlar}
            for job in r2.json().get("jobs", []):
                job_id = str(job.get("id", ""))
                if job_id in mevcut_idler:
                    continue
                baslik = job.get("jobTitle", "") or ""
                firma = job.get("companyName", "") or ""
                url = job.get("url", "") or ""
                aciklama = job.get("jobExcerpt", "") or ""
                ilan = _yeni_ilan(baslik, aciklama, "jobicy", job_id, url, firma, "Remote", "EU")
                ilan["pozisyon"] = "Uzaktan"
                ilanlar.append(ilan)
    except Exception:
        pass

    print(f"  Jobicy toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── REMOTIVE ─────────────────────────────────────────────────────────────────

def remotive_cek() -> list[dict]:
    """Remotive - uzaktan calisma ilanlari (ucretsiz JSON API)."""
    print("\n[Remotive] Cekiliyor...")
    ilanlar = []

    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"limit": 100},
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0"},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}")
            return []
        jobs = r.json().get("jobs", [])
    except Exception as e:
        print(f"  Hata: {e}")
        return []

    for job in jobs:
        job_id = str(job.get("id", ""))
        baslik = job.get("title", "") or ""
        firma = job.get("company_name", "") or ""
        url = job.get("url", "") or ""
        aciklama = job.get("description", "") or ""
        aciklama = aciklama[:2000]

        # candidate_required_location: "Europe", "Germany", vb.
        konum = job.get("candidate_required_location", "") or "Remote"
        ulke = ulke_bul(konum)

        ilan = _yeni_ilan(baslik, aciklama, "remotive", job_id, url, firma, konum, ulke)
        ilan["pozisyon"] = "Uzaktan"
        ilanlar.append(ilan)

    print(f"  Remotive toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Platform Avrupa is ilani cekici")
    parser.add_argument("--kaynak",
        choices=["arbeitnow", "adzuna", "bundesagentur", "jobicy", "remotive", "hepsi"],
        default="hepsi")
    parser.add_argument("--ulke", help="Sadece bu ulke (BE, DE, NL...)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--temizle", action="store_true", help="Suresi dolan ilanlar expired yap")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Her kaynakta az istek (Arbeitnow 1 sayfa, Adzuna 1 ulke x 1 sayfa, BA 1 sayfa)",
    )
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN MODU]\n")
    if args.quick:
        print("[QUICK — smoke test]\n")

    start = time.time()
    an_max = 1 if args.quick else 20
    ad_max_sayfa = 1 if args.quick else 10
    ad_max_ulke = 1 if args.quick else None
    ba_max = 1 if args.quick else 20

    start = time.time()
    toplam_eklenen = 0

    if args.temizle:
        print("\n[Temizlik] Suresi dolan ilanlar...")
        expired_yap(sb_url, sb_key, args.dry_run)

    tum_ilanlar: list[dict] = []

    if args.kaynak in ("arbeitnow", "hepsi"):
        tum_ilanlar += arbeitnow_cek(filtre_ulke=args.ulke, max_sayfa=an_max)

    if args.kaynak in ("adzuna", "hepsi"):
        tum_ilanlar += adzuna_cek(
            filtre_ulke=args.ulke,
            max_sayfa_baslama=ad_max_sayfa,
            max_ulkeler=ad_max_ulke,
        )

    if args.kaynak in ("bundesagentur", "hepsi") and not args.ulke:
        tum_ilanlar += bundesagentur_cek(max_sayfa=ba_max)

    if args.kaynak in ("jobicy", "hepsi") and not args.ulke:
        tum_ilanlar += jobicy_cek()

    if args.kaynak in ("remotive", "hepsi") and not args.ulke:
        tum_ilanlar += remotive_cek()

    if not tum_ilanlar:
        print("\nHic ilan cekilemedi.")
        return

    print(f"\nToplam cekilen: {len(tum_ilanlar)} ilan")

    # Upsert (300'er batch)
    BATCH = 300
    for i in range(0, len(tum_ilanlar), BATCH):
        batch = tum_ilanlar[i:i + BATCH]
        n = upsert_ilanlar(sb_url, sb_key, batch, args.dry_run)
        toplam_eklenen += n
        if not args.dry_run:
            print(f"  Upsert: {min(i + BATCH, len(tum_ilanlar))} / {len(tum_ilanlar)}")
        time.sleep(0.3)

    elapsed = time.time() - start
    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Tamamlandi.")
    print(f"  Upsert edilen: {toplam_eklenen} ilan")
    print(f"  Sure: {elapsed:.1f} sn")

if __name__ == "__main__":
    main()
