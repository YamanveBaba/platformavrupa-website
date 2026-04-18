# -*- coding: utf-8 -*-
"""
Market Karsilastirma Testi
Kullanicinin "urun ara ve markette fiyat karsilastir" yapacagini simule eder.
Sorunlari raporlar: eksik ceviri, eksik kategori, eslesme kalitesi, vb.

Kullanim:
  python karsilastirma_test.py                  # Genel rapor
  python karsilastirma_test.py --ara "melk"     # Belirli urun ara
  python karsilastirma_test.py --kategori "Sut" # Kategori bazli
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict

try:
    import requests
except ImportError:
    print("HATA: pip install requests"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_secrets():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = os.path.join(SCRIPT_DIR, "supabase_import_secrets.txt")
    lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
             if l.strip() and not l.strip().startswith("#")]
    return lines[0].rstrip("/"), lines[1]

def fetch_all(sb_url, sb_key, filtre_zincir=None, filtre_kategori=None, arama=None, limit=5000):
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    params = {
        "select": "id,name,name_tr,category_tr,price,chain_slug,unit,promo_price",
        "limit": str(limit),
        "order": "chain_slug.asc,name.asc",
    }
    if filtre_zincir:
        params["chain_slug"] = f"eq.{filtre_zincir}"
    if filtre_kategori:
        params["category_tr"] = f"eq.{filtre_kategori}"
    if arama:
        params["name_tr"] = f"ilike.*{arama}*"

    r = requests.get(f"{sb_url}/rest/v1/market_chain_products",
                     params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def genel_istatistik(sb_url, sb_key):
    headers = {
        "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        "Prefer": "count=exact", "Range": "0-0",
    }

    def say(params):
        r = requests.get(f"{sb_url}/rest/v1/market_chain_products",
                         params={**params, "select": "id"}, headers=headers, timeout=15)
        m = __import__("re").search(r"/(\d+)", r.headers.get("Content-Range", ""))
        return int(m.group(1)) if m else 0

    toplam     = say({})
    cevrilmis  = say({"name_tr": "not.is.null"})
    kategorili = say({"category_tr": "not.is.null"})
    fiyatli    = say({"price": "not.is.null"})

    print("\n" + "="*55)
    print("  GENEL ISTATISTIK")
    print("="*55)
    print(f"  Toplam urun       : {toplam:>8,}")
    print(f"  Turkce isim var   : {cevrilmis:>8,}  ({cevrilmis/toplam*100:.1f}%)" if toplam else "")
    print(f"  Kategori var      : {kategorili:>8,}  ({kategorili/toplam*100:.1f}%)" if toplam else "")
    print(f"  Fiyat var         : {fiyatli:>8,}  ({fiyatli/toplam*100:.1f}%)" if toplam else "")

    # Zincir bazli
    print("\n  ZINCIR BAZLI:")
    print(f"  {'Zincir':<20} {'Urun':>7} {'Ceviri':>7} {'Kategori':>9}")
    print(f"  {'-'*20} {'-'*7} {'-'*7} {'-'*9}")
    for zincir in ["colruyt_be", "delhaize_be", "lidl_be", "aldi_be", "carrefour_be",
                   "colruyt", "delhaize", "lidl", "aldi", "carrefour"]:
        t = say({"chain_slug": f"eq.{zincir}"})
        if t == 0:
            continue
        c = say({"chain_slug": f"eq.{zincir}", "name_tr": "not.is.null"})
        k = say({"chain_slug": f"eq.{zincir}", "category_tr": "not.is.null"})
        print(f"  {zincir:<20} {t:>7,} {c:>7,} {k:>9,}")

def karsilastirma_simule(sb_url, sb_key, arama_terimi):
    """Kullanici 'melk' aradığında ne gorecek?"""
    print(f"\n{'='*55}")
    print(f"  KULLANICI ARAMASI: '{arama_terimi}'")
    print(f"{'='*55}")

    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}

    # name_tr'de ara
    r = requests.get(
        f"{sb_url}/rest/v1/market_chain_products",
        params={
            "select": "name,name_tr,price,promo_price,chain_slug,unit,category_tr",
            "name_tr": f"ilike.*{arama_terimi}*",
            "limit": "100",
            "order": "name_tr.asc",
        },
        headers=headers, timeout=20,
    )
    raw = r.json()
    sonuclar = [u for u in raw if isinstance(u, dict)] if isinstance(raw, list) else []

    # Hollandaca da ara, birleştir
    r2 = requests.get(
        f"{sb_url}/rest/v1/market_chain_products",
        params={
            "select": "name,name_tr,price,promo_price,chain_slug,unit,category_tr",
            "name": f"ilike.*{arama_terimi}*",
            "limit": "100",
            "order": "chain_slug.asc",
        },
        headers=headers, timeout=20,
    )
    raw2 = r2.json()
    nl_sonuclar = [u for u in raw2 if isinstance(u, dict)] if isinstance(raw2, list) else []
    mevcut = {u.get("name") for u in sonuclar}
    for u in nl_sonuclar:
        if u.get("name") not in mevcut:
            sonuclar.append(u)

    if not sonuclar:
        print(f"  Hic sonuc yok!")
        return

    print(f"  {len(sonuclar)} sonuc bulundu\n")

    # Zincir bazli grupla
    zincirlere_gore = defaultdict(list)
    for u in sonuclar:
        zincirlere_gore[u.get("chain_slug", "?")].append(u)

    sorunlar = []

    for zincir, urunler in sorted(zincirlere_gore.items()):
        print(f"  [{zincir.upper()}] - {len(urunler)} sonuc")
        for u in urunler[:5]:  # zincir basina max 5 goster
            isim = u.get("name_tr") or u.get("name", "?")
            fiyat = u.get("promo_price") or u.get("price") or "?"
            birim = u.get("unit", "")
            kategori = u.get("category_tr", "")

            # Sorun tespiti
            if not u.get("name_tr"):
                sorunlar.append(f"Ceviri eksik: {u.get('name')} ({zincir})")
            if not kategori:
                sorunlar.append(f"Kategori eksik: {isim} ({zincir})")
            if fiyat == "?":
                sorunlar.append(f"Fiyat eksik: {isim} ({zincir})")

            print(f"    {isim[:40]:<40} {str(fiyat):>8} EUR  {birim:<10} {kategori}")
        if len(urunler) > 5:
            print(f"    ... ve {len(urunler)-5} urun daha")

    if sorunlar:
        print(f"\n  TESPIT EDILEN SORUNLAR ({len(sorunlar)}):")
        for s in sorunlar[:10]:
            print(f"    - {s}")
        if len(sorunlar) > 10:
            print(f"    ... ve {len(sorunlar)-10} sorun daha")

def fiyat_karsilastir(sb_url, sb_key, arama_terimi):
    """Ayni urun farkli marketlerde kac para?"""
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}

    r = requests.get(
        f"{sb_url}/rest/v1/market_chain_products",
        params={
            "select": "name_tr,price,promo_price,chain_slug,unit",
            "name_tr": f"ilike.*{arama_terimi}*",
            "price": "not.is.null",
            "limit": "200",
        },
        headers=headers, timeout=20,
    )
    urunler = r.json()
    if not urunler:
        print(f"  '{arama_terimi}' icin fiyatli urun bulunamadi.")
        return

    # Fiyat bazli sirala
    def fiyat_al(u):
        try:
            return float(u.get("promo_price") or u.get("price") or 999)
        except:
            return 999

    urunler.sort(key=fiyat_al)

    print(f"\n  FIYAT KARSILASTIRMA: '{arama_terimi}'")
    print(f"  {'Urun':<40} {'Zincir':<12} {'Fiyat':>8}  {'Birim'}")
    print(f"  {'-'*40} {'-'*12} {'-'*8}  {'-'*10}")

    for u in urunler[:20]:
        isim = (u.get("name_tr") or "?")[:40]
        zincir = u.get("chain_slug", "?")[:12]
        fiyat = u.get("promo_price") or u.get("price")
        birim = u.get("unit", "")
        print(f"  {isim:<40} {zincir:<12} {str(fiyat):>8}  {birim}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ara", help="Urun ara (Turkce veya Hollandaca)")
    parser.add_argument("--kategori", help="Kategori filtrele")
    parser.add_argument("--karsilastir", help="Fiyat karsilastir")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")

    # Her zaman genel istatistik goster
    genel_istatistik(sb_url, sb_key)

    if args.ara:
        karsilastirma_simule(sb_url, sb_key, args.ara)
        fiyat_karsilastir(sb_url, sb_key, args.ara)
    elif args.karsilastir:
        fiyat_karsilastir(sb_url, sb_key, args.karsilastir)
    else:
        # Varsayilan: birkaç ornek arama simule et
        print("\n" + "="*55)
        print("  ORNEK ARAMALAR")
        print("="*55)
        for terim in ["sut", "ekmek", "peynir", "tavuk", "cikolata"]:
            karsilastirma_simule(sb_url, sb_key, terim)
            time.sleep(0.3)

if __name__ == "__main__":
    main()
