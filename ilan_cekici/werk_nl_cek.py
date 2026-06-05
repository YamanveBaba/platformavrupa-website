# -*- coding: utf-8 -*-
"""
Werk.nl (UWV Hollanda) — Gunluk Is Ilani Cekici
Lisans: CC0 (kamu verisi, kayit gerekmez)

RSS feed: son 24 saatin yeni ilanlari (max 200 sonuc)
JSON dump: tam katalog (~250K), gunluk (haftalik calisimda kullan)

Kullanim:
  python werk_nl_cek.py             # RSS + DB upsert
  python werk_nl_cek.py --dump      # JSON dump (tam liste)
  python werk_nl_cek.py --temizle   # 30 gunluk ilanlari expired yap
  python werk_nl_cek.py --dry-run   # DB'ye yazma, sadece say
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

try:
    import feedparser
except ImportError:
    print("HATA: pip install feedparser")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

RSS_URL  = "https://www.werk.nl/werkzoekenden/vacatures/zoeken/rss?geplaatstSinds=1"
DUMP_URL = "https://www.werk.nl/downloads/werk_nl_vacatures.json"

EXPIRY_GUN = 30
SOURCE     = "werk_nl"
COUNTRY    = "NL"

# ─── Supabase ─────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    secrets_path = os.path.normpath(
        os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
    )
    if os.path.isfile(secrets_path):
        lines = [l.strip() for l in open(secrets_path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: Supabase credentials bulunamadi.")
    sys.exit(1)


def upsert(sb_url: str, sb_key: str, rows: list[dict], dry_run: bool) -> int:
    if dry_run or not rows:
        return len(rows)
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    r = requests.post(
        f"{sb_url}/rest/v1/ilanlar?on_conflict=source,source_id",
        json=rows, headers=headers, timeout=60,
    )
    if r.status_code in (200, 201, 204):
        return len(rows)
    if len(rows) > 1:
        y = len(rows) // 2
        return upsert(sb_url, sb_key, rows[:y], dry_run) + upsert(sb_url, sb_key, rows[y:], dry_run)
    print(f"  UYARI: upsert {r.status_code}: {r.text[:200]}")
    return 0


def expired_yap(sb_url: str, sb_key: str, dry_run: bool) -> int:
    sinir = (datetime.now(timezone.utc) - timedelta(days=EXPIRY_GUN)).isoformat()
    headers = {
        "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json", "Prefer": "return=minimal",
    }
    if dry_run:
        print(f"  [dry-run] werk_nl expired adayi kontrol edilmedi.")
        return 0
    r = requests.patch(
        f"{sb_url}/rest/v1/ilanlar?source=eq.{SOURCE}&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"}, headers=headers, timeout=30,
    )
    if r.status_code not in (200, 204):
        print(f"  UYARI: expired guncelleme {r.status_code}")
        return 0
    print(f"  {SOURCE} suresi dolan ilanlar expired yapildi.")
    return 1

# ─── Sektor tespiti ───────────────────────────────────────────────────────────

SEKTOR_MAP = {
    "Saglik":   ["verpleeg", "zorg", "dokter", "arts", "apotheek", "thuiszorg", "care"],
    "Lojistik": ["chauffeur", "logistiek", "magazijn", "bezorg", "transport", "vrachtwagen"],
    "Insaat":   ["bouw", "elektricien", "loodgieter", "monteur", "timmerman", "installatie"],
    "Temizlik": ["schoonmaak", "reinig", "huishouding", "toezicht"],
    "Restoran": ["kok", "chef", "horeca", "restaurant", "keuken", "catering", "bakker"],
    "Bilisim":  ["software", "developer", "it ", "data", "cloud", "devops", "programmeur"],
    "Satis":    ["verkoop", "sales", "retail", "winkel", "account"],
    "Guvenlik": ["beveilig", "beveiliging", "bewaking"],
    "Egitim":   ["leraar", "docent", "onderwijs", "coach", "trainer"],
    "Uretim":   ["productie", "assemblage", "operator", "fabriek", "montage"],
    "Ofis":     ["admin", "office", "hr ", "financieel", "boekhouding", "secretaresse"],
}

def sektor_bul(tekst: str) -> str:
    t = tekst.lower()
    for sektor, kelimeler in SEKTOR_MAP.items():
        if any(k in t for k in kelimeler):
            return sektor
    return "Diger"


def subcat_bul(tekst: str) -> str:
    t = tekst.lower()
    if any(k in t for k in ["parttime", "part-time", "deeltijd", "deel-tijd"]):
        return "Yari Zamanli"
    if any(k in t for k in ["thuis", "remote", "thuiswerk"]):
        return "Uzaktan"
    return "Tam Zamanli"


def sehir_cikart(text: str) -> str:
    """RSS location veya basliktan sehir cikart."""
    if not text:
        return ""
    # "Amsterdam (Noord-Holland)" → "Amsterdam"
    m = re.match(r"^([^(,]+)", text.strip())
    return m.group(1).strip() if m else text.strip()[:100]

# ─── RSS cekimi ───────────────────────────────────────────────────────────────

def rss_cek(sb_url: str, sb_key: str, dry_run: bool) -> int:
    print(f"  werk.nl RSS cekiliyor: {RSS_URL}")
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        print("  RSS bos veya ulasılamadi.")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for entry in feed.entries:
        title   = (entry.get("title") or "").strip()[:300]
        url     = entry.get("link") or ""
        summary = re.sub(r"<[^>]+>", " ", entry.get("summary") or "")[:2000]
        # source_id: URL'nin son parcasi veya id alanı
        sid = entry.get("id") or url.split("/")[-1] or title[:50]
        sid = re.sub(r"[^a-zA-Z0-9_-]", "", sid)[:100]
        if not sid or not title:
            continue
        location = entry.get("tags", [{}])[0].get("term", "") if entry.get("tags") else ""
        city = sehir_cikart(location or title)
        tekst = f"{title} {summary}"
        rows.append({
            "source":       SOURCE,
            "source_id":    sid,
            "title":        title,
            "description":  summary,
            "city":         city,
            "country":      COUNTRY,
            "source_url":   url,
            "status":       "active",
            "category":     "Is Ilani",
            "sub_category": subcat_bul(tekst),
            "sektor":       sektor_bul(tekst),
            "price":        "",
            "created_at":   now,
            "last_seen_at": now,
        })

    if not rows:
        print("  Islenecek ilan yok.")
        return 0

    eklenen = upsert(sb_url, sb_key, rows, dry_run)
    print(f"  RSS: {len(rows)} ilan islendi, {eklenen} DB'ye yazildi.")
    return eklenen

# ─── JSON dump cekimi ─────────────────────────────────────────────────────────

def dump_cek(sb_url: str, sb_key: str, dry_run: bool) -> int:
    print(f"  werk.nl JSON dump indiriliyor (buyuk dosya, bekleniyor)...")
    try:
        r = requests.get(DUMP_URL, timeout=180, stream=True)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"  UYARI: Dump URL erisilemedi ({e}). RSS ile devam.")
        return 0
    except Exception as e:
        print(f"  UYARI: Dump indirme hatasi: {e}")
        return 0

    try:
        jobs = r.json()
    except Exception:
        print("  UYARI: Dump JSON parse hatasi.")
        return 0

    if not isinstance(jobs, list):
        jobs = jobs.get("vacatures") or jobs.get("jobs") or []

    now = datetime.now(timezone.utc).isoformat()
    toplam = 0
    batch: list[dict] = []

    for job in jobs:
        title = (str(job.get("titel") or job.get("title") or "")).strip()[:300]
        sid   = str(job.get("id") or job.get("vacatureId") or "")[:100]
        if not title or not sid:
            continue
        url     = job.get("url") or job.get("link") or ""
        city    = sehir_cikart(job.get("plaats") or job.get("city") or "")
        summary = str(job.get("vacaturetekst") or job.get("description") or "")[:2000]
        tekst   = f"{title} {summary}"
        batch.append({
            "source":       SOURCE,
            "source_id":    sid,
            "title":        title,
            "description":  summary,
            "city":         city,
            "country":      COUNTRY,
            "source_url":   url,
            "status":       "active",
            "category":     "Is Ilani",
            "sub_category": subcat_bul(tekst),
            "sektor":       sektor_bul(tekst),
            "price":        "",
            "created_at":   now,
            "last_seen_at": now,
        })
        if len(batch) >= 200:
            toplam += upsert(sb_url, sb_key, batch, dry_run)
            batch = []
            time.sleep(0.5)

    if batch:
        toplam += upsert(sb_url, sb_key, batch, dry_run)

    print(f"  Dump: {toplam} ilan DB'ye yazildi.")
    return toplam

# ─── Ana akis ─────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="werk.nl Hollanda is ilanlari")
    ap.add_argument("--dump",     action="store_true", help="JSON dump (tam liste, yavas)")
    ap.add_argument("--temizle",  action="store_true", help="Suresi dolan ilanlari expired yap")
    ap.add_argument("--dry-run",  action="store_true", help="DB'ye yazma")
    args = ap.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"werk_nl_cek.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Kaynak: werk.nl (UWV), Ulke: {COUNTRY}")

    if args.temizle:
        expired_yap(sb_url, sb_key, args.dry_run)

    if args.dump:
        dump_cek(sb_url, sb_key, args.dry_run)
    else:
        rss_cek(sb_url, sb_key, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
