"""
Supabase'deki market_chain_products ürünlerine otomatik L1-L4 kategori atar.

Mantık:
  1. Ürün adı (name) + mevcut category alanları normalize edilir
  2. Kural tablosu (KURALLAR) ile eşleştirilir — kural öncelik sırasıyla çalışır
  3. Eşleşen ilk kural kategori atar
  4. Supabase'e PATCH ile güncellenir

Çalıştırma:
  python kategorize_urunler.py              # tümünü kategorize et
  python kategorize_urunler.py --chain colruyt_be   # tek market
  python kategorize_urunler.py --limit 500          # test: ilk 500 ürün
  python kategorize_urunler.py --dry-run            # güncelleme yapma, sadece say
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import urllib.request
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from json_to_supabase_yukle import load_secrets
from kategori_ata import (
    KURALLAR, CATEGORY_NAME_MAP, CHAIN_FALLBACK, GENEL_FALLBACK,
    normalize_text, kategorize_et,
)


# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────────────────────

def supabase_get(url: str, key: str, path: str, params: dict) -> list:
    query = urllib.parse.urlencode(params)
    req_url = f"{url}/rest/v1/{path}?{query}"
    req = urllib.request.Request(
        req_url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Prefer": "count=exact",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def supabase_patch_batch(url: str, key: str, rows: list[dict]) -> int:
    """
    Kategori değerlerine göre gruplar, her grup için tek PATCH:
      PATCH /market_chain_products?id=in.(1,2,3)
      Body: {category_l1, category_l2, category_l3, category_l4}
    Bu yöntem NOT NULL kısıtlaması sorununu önler.
    """
    if not rows:
        return 0

    gruplar: dict[tuple, list[int]] = {}
    for row in rows:
        key_tuple = (
            row.get("category_l1", ""),
            row.get("category_l2", ""),
            row.get("category_l3", ""),
            row.get("category_l4") or "",
        )
        gruplar.setdefault(key_tuple, []).append(row["id"])

    toplam = 0
    for (l1, l2, l3, l4), id_list in gruplar.items():
        id_str = ",".join(str(i) for i in id_list)
        patch_url = f"{url}/rest/v1/market_chain_products?id=in.({id_str})"
        body = {"category_l1": l1, "category_l2": l2, "category_l3": l3}
        if l4:
            body["category_l4"] = l4
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            patch_url,
            data=payload,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                toplam += len(id_list)
        except urllib.error.HTTPError as e:
            body_err = e.read().decode(errors="replace")
            print(f"  [ERR] PATCH: HTTP {e.code} — {body_err[:200]}")
    return toplam


# ─────────────────────────────────────────────────────────────────────────────
# ANA DÖNGÜ
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", default=None, help="Belirli bir market (örn. colruyt_be)")
    parser.add_argument("--limit", type=int, default=0, help="Maksimum ürün sayısı (0=tümü)")
    parser.add_argument("--dry-run", action="store_true", help="Güncelleme yapma, sadece say")
    parser.add_argument("--force", action="store_true", help="Zaten kategorize edilenleri de işle")
    args = parser.parse_args()

    url, key = load_secrets(SCRIPT_DIR)
    print(f"Supabase: {url}")

    SAYFA = 1000
    offset = 0
    tum_urunler: list[dict] = []

    while True:
        params: dict = {
            "select": "id,external_product_id,chain_slug,name,category_name",
            "order": "id.asc",
            "offset": offset,
            "limit": SAYFA,
        }
        if args.chain:
            params["chain_slug"] = f"eq.{args.chain}"
        if not args.force and not args.dry_run:
            params["category_l1"] = "is.null"

        try:
            sayfa = supabase_get(url, key, "market_chain_products", params)
        except Exception as e:
            print(f"Supabase okuma hatasi: {e}")
            break

        if not sayfa:
            break
        tum_urunler.extend(sayfa)
        print(f"  Yuklendi: {len(tum_urunler)} urun...", end="\r")

        if args.limit and len(tum_urunler) >= args.limit:
            tum_urunler = tum_urunler[:args.limit]
            break
        if len(sayfa) < SAYFA:
            break
        offset += SAYFA

    print(f"\nToplam isleme alinacak: {len(tum_urunler)} urun")
    if not tum_urunler:
        print("Kategorize edilecek urun yok.")
        return

    katman1 = 0
    katman2 = 0
    katman3 = 0
    guncelle_batch: list[dict] = []
    BATCH_BOYUT = 200

    for urun in tum_urunler:
        name = urun.get("name", "")
        chain = urun.get("chain_slug", "")
        cat_name = urun.get("category_name", "") or ""

        hay = normalize_text(name)
        k1_sonuc = None
        for anahtar_list, d_id, l2, l3, l4 in KURALLAR:
            tum_eslesti = True
            for anahtar in anahtar_list:
                alternatifler = [a.strip() for a in anahtar.split("|")]
                if not any(alt in hay for alt in alternatifler if alt):
                    tum_eslesti = False
                    break
            if tum_eslesti:
                k1_sonuc = (d_id, l2, l3, l4)
                break

        if k1_sonuc:
            d_id, l2, l3, l4 = k1_sonuc
            katman1 += 1
        else:
            cat_hay = normalize_text(cat_name)
            k2_sonuc = None
            for anahtar_list, d_id, l2, l3, l4 in CATEGORY_NAME_MAP:
                tum_eslesti = True
                for anahtar in anahtar_list:
                    if anahtar not in cat_hay:
                        tum_eslesti = False
                        break
                if tum_eslesti:
                    k2_sonuc = (d_id, l2, l3, l4)
                    break

            if k2_sonuc:
                d_id, l2, l3, l4 = k2_sonuc
                katman2 += 1
            else:
                d_id, l2, l3, l4 = CHAIN_FALLBACK.get(chain, GENEL_FALLBACK)
                katman3 += 1

        if not args.dry_run:
            guncelle_batch.append({
                "id": urun["id"],
                "category_l1": d_id,
                "category_l2": l2,
                "category_l3": l3,
                "category_l4": l4 or None,
                "chain_slug": chain,
                "external_product_id": urun["external_product_id"],
            })
            if len(guncelle_batch) >= BATCH_BOYUT:
                guncellenen = supabase_patch_batch(url, key, guncelle_batch)
                print(f"  [OK] {guncellenen} urun guncellendi (K1:{katman1} K2:{katman2} K3:{katman3})")
                guncelle_batch = []

    if guncelle_batch and not args.dry_run:
        guncellenen = supabase_patch_batch(url, key, guncelle_batch)
        print(f"  [OK] {guncellenen} urun guncellendi (son batch)")

    toplam = len(tum_urunler)
    print()
    print(f"Sonuc ({toplam} urun):")
    print(f"  Katman 1 (isim kurali): {katman1} urun ({100*katman1/toplam:.1f}%)")
    print(f"  Katman 2 (category_name): {katman2} urun ({100*katman2/toplam:.1f}%)")
    print(f"  Katman 3 (fallback): {katman3} urun ({100*katman3/toplam:.1f}%)")
    print(f"  TOPLAM kategorize: {katman1+katman2+katman3} urun (%100)")
    if args.dry_run:
        print("  (dry-run modu — hicbir guncelleme yapilmadi)")


if __name__ == "__main__":
    main()
