# -*- coding: utf-8 -*-
"""
Platform Avrupa — Döviz & Altın Fiyat Çekici
Her 30 dakikada GitHub Actions tarafından çalıştırılır.
Supabase doviz_cache tablosuna yazar. Kullanıcılar buradan okur.

Kullanım:
  python doviz_cek.py           # Döviz + altın çek, Supabase'e yaz
  python doviz_cek.py --dry-run # Supabase'e yazma, sadece göster
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("HATA: pip install requests"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Altın fiyatı kaynakları (CORS proxy'siz — sunucudan çağrılıyor)
GOLD_SOURCES = [
    "https://freegoldapi.com/data/latest.json",
    "https://metals-api.com/api/latest?access_key=demo&base=USD&symbols=XAU",
]

# Gram altın çarpanları (market prim dahil)
GOLD_MULTIPLIERS = {
    "gram":       1.033,
    "ceyrek":     1.033 * 1.635,
    "yarim":      1.033 * 3.27,
    "tam":        1.033 * 6.54,
    "cumhuriyet": 1.033 * 6.72,
    "ata":        1.033 * 7.216,
    "ikibuçuk":   1.033 * 16.35,
    "beşli":      1.033 * 32.7,
    "gremse":     1.033 * 16.35,
    "bilezik22":  0.916,
    "bilezik18":  0.75,
    "bilezik14":  0.585,
}

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = os.path.normpath(
        os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
    )
    if os.path.isfile(path):
        lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: Supabase credentials bulunamadı."); sys.exit(1)


def supabase_upsert(sb_url: str, sb_key: str, row_id: str, data: dict, dry_run: bool) -> bool:
    if dry_run:
        print(f"  [dry-run] {row_id} yazılacaktı: {json.dumps(data, ensure_ascii=False)[:200]}")
        return True
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    payload = {
        "id": row_id,
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    r = requests.post(
        f"{sb_url}/rest/v1/doviz_cache?on_conflict=id",
        json=payload, headers=headers, timeout=30
    )
    if r.status_code in (200, 201, 204):
        return True
    print(f"  UYARI: Supabase upsert {r.status_code}: {r.text[:200]}")
    return False

# ─── DÖVİZ ────────────────────────────────────────────────────────────────────

def fetch_exchange_rates() -> dict | None:
    """ExchangeRate-API'den TRY bazlı kurları çek. Hepsi 1 birim = X TRY formatında."""
    print("[Döviz] ExchangeRate-API çekiliyor...")
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/TRY",
            headers={"User-Agent": "PlatformAvrupa/1.0"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        rates = {}
        for currency, rate in data.get("rates", {}).items():
            if rate > 0:
                rates[currency] = round(1 / rate, 6)
        rates["TRY"] = 1.0
        print(f"  EUR/TRY: {rates.get('EUR', '?'):.2f}  USD/TRY: {rates.get('USD', '?'):.2f}")
        return rates
    except Exception as e:
        print(f"  HATA: {e}")
        return None


def fetch_yesterday_rates() -> dict | None:
    """Frankfurter API'den dünkü kurları çek (değişim oranı için)."""
    print("[Döviz] Dünkü kurlar çekiliyor...")
    try:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        r = requests.get(
            f"https://api.frankfurter.app/{yesterday}?from=TRY",
            headers={"User-Agent": "PlatformAvrupa/1.0"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        yesterday_rates = {}
        for currency, rate in data.get("rates", {}).items():
            if rate > 0:
                yesterday_rates[currency] = round(1 / rate, 6)
        print(f"  Dünkü EUR/TRY: {yesterday_rates.get('EUR', '?')}")
        return yesterday_rates
    except Exception as e:
        print(f"  UYARI: Dünkü kurlar alınamadı: {e}")
        return None

# ─── ALTIN ────────────────────────────────────────────────────────────────────

def fetch_gold_ons_usd() -> float | None:
    """Ons altın fiyatını USD olarak çek."""
    print("[Altın] Ons fiyatı çekiliyor...")

    # FreeGoldAPI
    try:
        r = requests.get(
            "https://freegoldapi.com/data/latest.json",
            headers={"User-Agent": "PlatformAvrupa/1.0"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            price = data.get("price", 0)
            if 1000 < price < 10000:
                print(f"  FreeGoldAPI: {price:.2f} USD/ons")
                return float(price)
    except Exception as e:
        print(f"  FreeGoldAPI hata: {e}")

    # Metals API demo
    try:
        r = requests.get(
            "https://api.metals.live/v1/spot/gold",
            headers={"User-Agent": "PlatformAvrupa/1.0"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            price = data[0].get("gold", 0) if isinstance(data, list) else data.get("gold", 0)
            if 1000 < float(price) < 10000:
                print(f"  metals.live: {price:.2f} USD/ons")
                return float(price)
    except Exception as e:
        print(f"  metals.live hata: {e}")

    # Fallback: güncel piyasa tahmini
    print("  UYARI: Canlı ons fiyatı alınamadı, tahmini kullanılıyor (2800 USD)")
    return 2800.0


def calculate_gold_prices(ons_usd: float, usd_try: float) -> dict:
    """Ons fiyatından tüm altın türlerini hesapla."""
    ons_try = ons_usd * usd_try
    gram_spot = ons_try / 31.1035
    prices = {}
    for key, multiplier in GOLD_MULTIPLIERS.items():
        prices[key] = round(gram_spot * multiplier, 2)
    print(f"  Gram altın: {prices['gram']:.0f} TL  (ons: {ons_usd:.0f} USD, USD/TRY: {usd_try:.2f})")
    return prices

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Döviz & Altın Supabase cache güncelleyici")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN]\n")

    start = time.time()

    # 1. Döviz kurları
    rates = fetch_exchange_rates()
    if not rates:
        print("HATA: Döviz kurları alınamadı, çıkılıyor."); sys.exit(1)

    yesterday = fetch_yesterday_rates()

    rates_payload = {
        "rates": rates,
        "yesterday": yesterday or {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    ok = supabase_upsert(sb_url, sb_key, "rates", rates_payload, args.dry_run)
    print(f"  Döviz kurları Supabase'e {'yazıldı' if ok else 'YAZILAMADI'}")

    # 2. Altın fiyatları
    ons_usd = fetch_gold_ons_usd()
    usd_try = rates.get("USD", 0)

    if ons_usd and usd_try > 0:
        gold_prices = calculate_gold_prices(ons_usd, usd_try)
        gold_payload = {
            "prices": gold_prices,
            "ons_usd": ons_usd,
            "usd_try": usd_try,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        ok2 = supabase_upsert(sb_url, sb_key, "gold", gold_payload, args.dry_run)
        print(f"  Altın fiyatları Supabase'e {'yazıldı' if ok2 else 'YAZILAMADI'}")
    else:
        print("  HATA: Altın fiyatları hesaplanamadı.")

    print(f"\nTamamlandı ({time.time() - start:.1f} sn)")


if __name__ == "__main__":
    main()
