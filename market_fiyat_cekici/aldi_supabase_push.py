# -*- coding: utf-8 -*-
"""
Aldi BE — aldi_be_v2_*.json dosyasını Supabase'e push eder.
aldi_be_v2.py'nin ürettiği JSON'u okur, html_analiz.py'deki upsert mantığını kullanır.

Kullanım:
  python aldi_supabase_push.py           # en son JSON'u push et
  python aldi_supabase_push.py --dry-run # DB'ye yazma, sadece say
"""
from __future__ import annotations
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import argparse
import glob
import json
import os
import re
from pathlib import Path
from typing import Optional

import requests

SCRIPT_DIR = Path(__file__).parent
CIKTI_DIR  = SCRIPT_DIR / "cikti"

# ─── Supabase ────────────────────────────────────────────────────────────────

def load_secrets():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = SCRIPT_DIR / "supabase_import_secrets.txt"
    lines = [l.strip() for l in path.read_text(encoding="utf-8", errors="ignore").splitlines()
             if l.strip() and not l.strip().startswith("#")]
    return lines[0].rstrip("/"), lines[1]


def upsert_urunler(sb_url: str, sb_key: str, urunler: list, dry_run: bool) -> int:
    if not urunler:
        return 0
    if dry_run:
        for u in urunler[:5]:
            print(f"  [DRY] {u.get('name','')[:50]} | {u.get('price')} EUR")
        return len(urunler)

    hdrs = {
        "apikey": sb_key,
        "Authorization": "Bearer " + sb_key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    with_pid    = [u for u in urunler if u.get("external_product_id")]
    without_pid = [u for u in urunler if not u.get("external_product_id")]

    toplam = 0
    for i in range(0, len(with_pid), 200):
        batch = with_pid[i:i+200]
        r = requests.post(
            sb_url + "/rest/v1/market_chain_products?on_conflict=chain_slug,external_product_id",
            json=batch, headers=hdrs, timeout=60,
        )
        if r.status_code in (200, 201):
            toplam += len(batch)
        else:
            print(f"  [HATA] Upsert (pid) {i}: {r.status_code} {r.text[:120]}")

    for i in range(0, len(without_pid), 200):
        batch = without_pid[i:i+200]
        r = requests.post(
            sb_url + "/rest/v1/market_chain_products",
            json=batch, headers=hdrs, timeout=60,
        )
        if r.status_code in (200, 201):
            toplam += len(batch)
        else:
            print(f"  [HATA] Insert (no-pid) {i}: {r.status_code} {r.text[:120]}")

    return toplam


# ─── Kategori çevirisi ────────────────────────────────────────────────────────

KATEGORI_CEVIRI = {
    "groenten": "Sebzeler", "fruit": "Meyveler", "vlees": "Et",
    "vis": "Balık", "melk": "Süt ürünleri", "kaas": "Peynir",
    "brood": "Ekmek", "banket": "Pasta", "broodbeleg": "Ekmek üstü",
    "dranken": "İçecekler", "koffie": "Kahve", "thee": "Çay",
    "pasta": "Makarna", "rijst": "Pirinç", "conserven": "Konserve",
    "snacks": "Atıştırmalıklar", "aanbiedingen": "Fırsatlar",
    "ijsjes": "Dondurma", "diepvries": "Dondurulmuş",
    "vegetarisch": "Vejetaryen", "cosmetica": "Kozmetik",
    "huishouden": "Ev ürünleri", "dierenvoeding": "Evcil hayvan",
    "baby": "Bebek ürünleri", "sauzen": "Soslar",
    "muesli": "Tahıllar", "cornflakes": "Cornflakes",
    "kant-en-klaar": "Hazır yemek",
}


def kategori_tr(kat: str) -> str:
    low = kat.lower()
    for k, v in KATEGORI_CEVIRI.items():
        if k in low:
            return v
    return kat


# ─── JSON → Supabase satırı ───────────────────────────────────────────────────

def urun_donustur(u: dict) -> Optional[dict]:
    name  = str(u.get("name") or "").strip()
    price = u.get("basicPrice")
    pid   = str(u.get("aldiPid") or "").strip() or None
    if not name:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None

    img = str(u.get("imageUrl") or "").strip()
    if img.startswith("data:"):
        img = ""

    promo_price = u.get("promoPrice")
    if promo_price:
        try:
            promo_price = float(promo_price)
            if promo_price >= price:
                promo_price = None
        except (TypeError, ValueError):
            promo_price = None

    return {
        "chain_slug":          "aldi_be",
        "country_code":        "BE",
        "external_product_id": pid,
        "name":                name[:300],
        "brand":               str(u.get("brand") or "")[:200] or None,
        "price":               price,
        "currency":            "EUR",
        "unit_or_content":     None,
        "image_url":           img[:1000] or None,
        "in_promo":            bool(u.get("inPromo")),
        "promo_price":         promo_price,
        "category_tr":         kategori_tr(str(u.get("topCategoryName") or "")),
    }


# ─── Ana ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # En son aldi_be_v2_*.json bul
    dosyalar = sorted(
        glob.glob(str(CIKTI_DIR / "aldi_be_v2_*.json")),
        key=os.path.getmtime,
    )
    if not dosyalar:
        print("HATA: cikti/aldi_be_v2_*.json bulunamadı. Önce aldi_be_v2.py çalıştırın.")
        sys.exit(1)

    dosya = dosyalar[-1]
    print(f"JSON: {Path(dosya).name}")

    with open(dosya, encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    ham_urunler = data.get("urunler", [])
    print(f"JSON'da {len(ham_urunler)} ürün")

    urunler = [r for u in ham_urunler if (r := urun_donustur(u))]
    print(f"Geçerli: {len(urunler)} ürün")

    if not urunler:
        print("Geçerli ürün yok — çıkılıyor.")
        sys.exit(1)

    sb_url, sb_key = load_secrets()
    yazilan = upsert_urunler(sb_url, sb_key, urunler, args.dry_run)
    print(f"TAMAMLANDI — Toplam {yazilan} ürün {'görüldü' if args.dry_run else 'DB güncellendi'}")


if __name__ == "__main__":
    main()
