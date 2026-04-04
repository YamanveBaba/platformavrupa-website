# -*- coding: utf-8 -*-
"""
Platform Avrupa — Otomatik İş İlanı Çekici
Kaynaklar: Arbeitnow API (ücretsiz) + Adzuna API (key hazır)

Kullanım:
  python is_ilani_cekici.py              # Tüm kaynaklar, tüm ülkeler
  python is_ilani_cekici.py --kaynak arbeitnow
  python is_ilani_cekici.py --kaynak adzuna
  python is_ilani_cekici.py --ulke BE    # Sadece Belçika
  python is_ilani_cekici.py --dry-run    # Supabase'e yazma, sadece say
  python is_ilani_cekici.py --temizle    # Süresi dolan ilanları expired yap

Otomatik çalıştırma (Windows Görev Zamanlayıcı):
  Her gece 02:00 → python is_ilani_cekici.py --temizle
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── AYARLAR ──────────────────────────────────────────────────────────────────

ADZUNA_ID  = "c0c66624"
ADZUNA_KEY = "5a2d86df68a24e6fe8b1e9b4319347f0"

# Desteklenen Avrupa ülkeleri (Adzuna ülke kodu → Platform Avrupa ülke kodu)
ADZUNA_ULKELER = {
    "be": "BE",   # Belçika
    "de": "DE",   # Almanya
    "nl": "NL",   # Hollanda
    "fr": "FR",   # Fransa
    "at": "AT",   # Avusturya
    "ch": "CH",   # İsviçre
    "pl": "PL",   # Polonya
    "it": "IT",   # İtalya
    "es": "ES",   # İspanya
}

# İlan 30 gün sonra expired
EXPIRY_GUN = 30

# Arbeitnow: konum'da bu varsa Avrupa ilanı sayılır
AVRUPA_ANAHTAR = [
    "germany", "deutschland", "almanya",
    "belgium", "belgique", "belgie", "belçika",
    "netherlands", "nederland", "hollanda",
    "france", "frankreich", "fransa",
    "austria", "österreich", "avusturya",
    "switzerland", "schweiz", "svizzera", "isviçre",
    "luxembourg", "luxemburg",
    "sweden", "sverige", "isveç",
    "norway", "norwegen",
    "denmark", "dänemark",
    "spain", "españa", "spanien", "ispanya",
    "italy", "italien", "italya",
    "poland", "polen", "polonya",
    "remote", "avrupa", "europe",
    # Büyük şehirler
    "berlin", "münchen", "hamburg", "frankfurt", "köln", "stuttgart", "düsseldorf",
    "brussels", "bruxelles", "brussel", "brüssel", "antwerp", "antwerpen", "gent", "liège",
    "amsterdam", "rotterdam", "the hague", "den haag",
    "paris", "lyon", "marseille",
    "vienna", "wien",
    "zurich", "zürich", "geneva", "genève",
    "madrid", "barcelona",
    "rome", "roma", "milan", "milano",
    "warsaw", "warszawa",
]

# Sektör tespiti (Türkçe → başlık/açıklamada İngilizce kelime)
SEKTOR_ESLEME = {
    "Restoran": ["cook", "chef", "kitchen", "restaurant", "food", "horeca", "gastro", "bäcker", "küche"],
    "İnşaat":   ["construction", "builder", "electrician", "plumber", "bau", "handwerk", "monteur"],
    "Lojistik": ["driver", "logistics", "warehouse", "delivery", "transport", "fahrer", "lager"],
    "Temizlik": ["cleaning", "cleaner", "housekeeping", "reinigung"],
    "Sağlık":   ["nurse", "doctor", "care", "health", "medical", "pflege", "kranken", "arzt"],
    "Satış":    ["sales", "retail", "shop", "store", "verkauf", "handel"],
    "Bilişim":  ["software", "developer", "it ", "data", "cloud", "devops", "engineer", "programmer"],
    "Güvenlik": ["security", "guard", "bewachung"],
    "Ofis":     ["admin", "office", "hr ", "finance", "accounting", "manager", "secretary"],
    "Eğitim":   ["teacher", "trainer", "education", "lehrer", "schule"],
}

def sektor_bul(text: str) -> str:
    t = text.lower()
    for sektor, kelimeler in SEKTOR_ESLEME.items():
        if any(k in t for k in kelimeler):
            return sektor
    return "Diğer"

def ulke_bul_arbeitnow(location: str) -> str:
    l = location.lower()
    if any(k in l for k in ["germany", "deutschland", "berlin", "münchen", "hamburg", "frankfurt",
                              "köln", "stuttgart", "düsseldorf", "dortmund", "essen", "leipzig"]):
        return "DE"
    if any(k in l for k in ["belgium", "belgique", "belgie", "brussels", "bruxelles", "brussel",
                              "antwerp", "antwerpen", "gent", "liège", "charleroi"]):
        return "BE"
    if any(k in l for k in ["netherlands", "nederland", "amsterdam", "rotterdam", "den haag",
                              "utrecht", "eindhoven"]):
        return "NL"
    if any(k in l for k in ["france", "paris", "lyon", "marseille", "toulouse", "bordeaux"]):
        return "FR"
    if any(k in l for k in ["austria", "österreich", "vienna", "wien", "graz", "salzburg"]):
        return "AT"
    if any(k in l for k in ["switzerland", "schweiz", "zürich", "zurich", "geneva", "bern"]):
        return "CH"
    if any(k in l for k in ["spain", "españa", "madrid", "barcelona", "seville"]):
        return "ES"
    if any(k in l for k in ["italy", "italia", "rome", "milan", "milano", "roma"]):
        return "IT"
    if any(k in l for k in ["poland", "polska", "warsaw", "warszawa", "krakow"]):
        return "PL"
    if any(k in l for k in ["luxembourg", "luxemburg"]):
        return "LU"
    return "EU"  # Bilinmeyen Avrupa

# ─── SUPABASE ──────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    # 1. Ortam değişkenleri
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key

    # 2. ../market_fiyat_cekici/supabase_import_secrets.txt
    secrets_path = os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
    secrets_path = os.path.normpath(secrets_path)
    if os.path.isfile(secrets_path):
        lines = [l.strip() for l in open(secrets_path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]

    print("HATA: Supabase credentials bulunamadı.")
    print("  ../market_fiyat_cekici/supabase_import_secrets.txt dosyasını oluştur")
    print("  veya SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ortam değişkenlerini ayarla.")
    sys.exit(1)

def sb_headers(key: str) -> dict:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

def upsert_ilanlar(sb_url: str, sb_key: str, rows: list[dict], dry_run: bool) -> int:
    """source + source_id unique index'e göre upsert."""
    if dry_run or not rows:
        return len(rows)
    endpoint = f"{sb_url}/rest/v1/ilanlar"
    headers = sb_headers(sb_key)
    r = requests.post(endpoint, json=rows, headers=headers, timeout=60)
    if r.status_code not in (200, 201, 204):
        print(f"  UYARI: upsert hatası {r.status_code}: {r.text[:300]}")
        return 0
    return len(rows)

def expired_yap(sb_url: str, sb_key: str, dry_run: bool) -> int:
    """30 günden eski otomatik ilanları expired yap."""
    sinir = (datetime.now(timezone.utc) - timedelta(days=EXPIRY_GUN)).isoformat()
    endpoint = f"{sb_url}/rest/v1/ilanlar"
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    # Kaç tane etkilenecek? (count)
    count_headers = dict(headers)
    count_headers["Prefer"] = "count=exact"
    count_headers["Range"] = "0-0"
    params = {
        "source": "not.eq.user",
        "status": "eq.active",
        "created_at": f"lt.{sinir}",
        "select": "id",
    }
    r = requests.get(endpoint, params=params, headers=count_headers, timeout=30)
    cr = r.headers.get("Content-Range", "")
    m = re.search(r"/(\d+)", cr)
    toplam = int(m.group(1)) if m else 0

    if toplam == 0:
        print("  Süresi dolan ilan yok.")
        return 0

    if dry_run:
        print(f"  [dry-run] {toplam} ilan expired yapılacaktı.")
        return toplam

    patch = requests.patch(
        endpoint + f"?source=not.eq.user&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"},
        headers=headers,
        timeout=60,
    )
    if patch.status_code not in (200, 204):
        print(f"  UYARI: expired güncelleme hatası {patch.status_code}: {patch.text[:200]}")
        return 0
    print(f"  {toplam} ilan expired yapıldı.")
    return toplam

# ─── ARBEITNOW ────────────────────────────────────────────────────────────────

def arbeitnow_cek(filtre_ulke: Optional[str] = None) -> list[dict]:
    """Arbeitnow API'den Avrupa ilanlarını çek."""
    print("\n[Arbeitnow] Çekiliyor...")
    ilanlar = []
    sayfa = 1
    bos_sayfa = 0

    while True:
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
            print("  Rate limit — 60 sn bekleniyor...")
            time.sleep(60)
            continue
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}, duruldu.")
            break

        data = r.json().get("data", [])
        if not data:
            bos_sayfa += 1
            if bos_sayfa >= 2:
                break
            sayfa += 1
            continue

        bos_sayfa = 0
        for job in data:
            loc = job.get("location", "") or ""
            # Avrupa filtresi
            if not any(k in loc.lower() for k in AVRUPA_ANAHTAR):
                continue
            ulke = ulke_bul_arbeitnow(loc)
            if filtre_ulke and ulke != filtre_ulke:
                continue

            sehir = loc.split(",")[0].strip()[:100] if loc else "Avrupa"
            baslik = (job.get("title") or "")[:300]
            aciklama = (job.get("description") or "")[:2000]

            ilanlar.append({
                "title":      baslik,
                "description": aciklama,
                "category":   "İş İlanı",
                "sub_category": "Tam Zamanlı",
                "status":     "active",
                "source":     "arbeitnow",
                "source_id":  str(job.get("slug", "")),
                "source_url": job.get("url", ""),
                "owner_name": (job.get("company_name") or "")[:200],
                "city":       sehir,
                "country":    ulke,
                "sektor":     sektor_bul(baslik + " " + aciklama),
                "pozisyon":   "Uzaktan" if job.get("remote") else "Ofis",
                "price":      "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=EXPIRY_GUN)).isoformat(),
            })

        print(f"  Sayfa {sayfa}: {len(data)} ilan (toplam Avrupa: {len(ilanlar)})")
        sayfa += 1
        time.sleep(random.uniform(0.8, 1.5))

        # Arbeitnow genellikle 10-15 sayfa döndürür
        if sayfa > 20:
            break

    print(f"  Arbeitnow toplam: {len(ilanlar)} Avrupa ilanı")
    return ilanlar

# ─── ADZUNA ───────────────────────────────────────────────────────────────────

def adzuna_cek(filtre_ulke: Optional[str] = None) -> list[dict]:
    """Adzuna API'den Avrupa iş ilanlarını çek."""
    print("\n[Adzuna] Çekiliyor...")
    ilanlar = []

    ulkeler = ADZUNA_ULKELER
    if filtre_ulke:
        # Sadece istenen ülkeyi çek
        ulkeler = {k: v for k, v in ADZUNA_ULKELER.items() if v == filtre_ulke}
        if not ulkeler:
            print(f"  Adzuna'da {filtre_ulke} için ülke kodu bulunamadı.")
            return []

    for az_kod, pa_kod in ulkeler.items():
        sayfa = 1
        ulke_sayac = 0

        while sayfa <= 5:  # Ülke başına max 5 sayfa = 250 ilan
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
                print(f"  {az_kod} rate limit — 60 sn bekleniyor...")
                time.sleep(60)
                continue
            if r.status_code != 200:
                print(f"  {az_kod} HTTP {r.status_code}")
                break

            results = r.json().get("results", [])
            if not results:
                break

            for job in results:
                job_id = str(job.get("id", ""))
                baslik = (job.get("title") or "")[:300]
                aciklama = (job.get("description") or "")[:2000]
                sehir = ""
                loc = job.get("location", {})
                if loc:
                    area = loc.get("area", [])
                    sehir = area[-1] if area else loc.get("display_name", "")
                sehir = (sehir or "")[:100]

                firma = ""
                company = job.get("company", {})
                if company:
                    firma = company.get("display_name", "")[:200]

                maas = ""
                sal_min = job.get("salary_min")
                sal_max = job.get("salary_max")
                if sal_min and sal_max:
                    maas = f"{int(sal_min):,}–{int(sal_max):,} EUR/yıl"
                elif sal_min:
                    maas = f"{int(sal_min):,}+ EUR/yıl"

                cat_label = ""
                cat = job.get("category", {})
                if cat:
                    cat_label = cat.get("label", "")

                ilanlar.append({
                    "title":       baslik,
                    "description": aciklama,
                    "category":    "İş İlanı",
                    "sub_category": "Tam Zamanlı",
                    "status":      "active",
                    "source":      f"adzuna_{az_kod}",
                    "source_id":   job_id,
                    "source_url":  job.get("redirect_url", ""),
                    "owner_name":  firma,
                    "city":        sehir,
                    "country":     pa_kod,
                    "sektor":      sektor_bul(baslik + " " + aciklama + " " + cat_label),
                    "pozisyon":    "Ofis",
                    "price":       maas,
                    "created_at":  datetime.now(timezone.utc).isoformat(),
                    "expires_at":  (datetime.now(timezone.utc) + timedelta(days=EXPIRY_GUN)).isoformat(),
                })
                ulke_sayac += 1

            print(f"  {az_kod.upper()} sayfa {sayfa}: {len(results)} ilan")
            sayfa += 1
            time.sleep(random.uniform(0.5, 1.0))

        print(f"  {az_kod.upper()} toplam: {ulke_sayac} ilan")

    print(f"  Adzuna toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Platform Avrupa iş ilanı çekici")
    parser.add_argument("--kaynak", choices=["arbeitnow", "adzuna", "hepsi"], default="hepsi")
    parser.add_argument("--ulke", help="Sadece bu ülke (örn: BE, DE, NL)")
    parser.add_argument("--dry-run", action="store_true", help="Supabase'e yazma, sadece say")
    parser.add_argument("--temizle", action="store_true", help="Süresi dolan ilanları expired yap")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN MODU — Supabase'e hiçbir şey yazılmayacak]\n")

    start = time.time()
    toplam_eklenen = 0

    # Süresi dolan ilanları temizle
    if args.temizle:
        print("\n[Temizlik] Süresi dolan ilanlar...")
        expired_yap(sb_url, sb_key, args.dry_run)

    # İlan çek
    tum_ilanlar: list[dict] = []

    if args.kaynak in ("arbeitnow", "hepsi"):
        tum_ilanlar += arbeitnow_cek(filtre_ulke=args.ulke)

    if args.kaynak in ("adzuna", "hepsi"):
        tum_ilanlar += adzuna_cek(filtre_ulke=args.ulke)

    if not tum_ilanlar:
        print("\nHiç ilan çekilemedi.")
        return

    print(f"\nToplam çekilen: {len(tum_ilanlar)} ilan")

    # Supabase'e upsert (300'er batch)
    BATCH = 300
    for i in range(0, len(tum_ilanlar), BATCH):
        batch = tum_ilanlar[i:i + BATCH]
        n = upsert_ilanlar(sb_url, sb_key, batch, args.dry_run)
        toplam_eklenen += n
        if not args.dry_run:
            print(f"  Upsert: {min(i + BATCH, len(tum_ilanlar))} / {len(tum_ilanlar)}")
        time.sleep(0.3)

    elapsed = time.time() - start
    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Tamamlandı.")
    print(f"  Upsert edilen: {toplam_eklenen} ilan")
    print(f"  Süre: {elapsed:.1f} sn")
    print(f"\nSonraki adım: is_vitrini.html artık dolu olmalı.")

if __name__ == "__main__":
    main()
