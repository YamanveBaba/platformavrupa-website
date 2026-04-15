# -*- coding: utf-8 -*-
"""
Lidl ürün resimlerini çeker ve Supabase'e yazar.

Her Lidl ürününün external_product_id'si (örn. p100395311) ile
https://www.lidl.be/p/nl-BE/x/{pid} adresini ziyaret eder,
application/ld+json'dan ilk resim URL'ini alır, DB'de günceller.

Kullanım:
  python lidl_resim_cek.py              # Tüm resimsiz Lidl ürünleri
  python lidl_resim_cek.py --limit 500  # İlk 500 ürün
  python lidl_resim_cek.py --dry-run    # DB'ye yazmadan test

Süre: ~9000 ürün için yaklaşık 20-40 dakika (10 paralel istek).
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
WORKERS      = 50    # paralel istek sayısı
BATCH_SIZE   = 500   # DB'den kaçar kayıt çekilir
LIDL_BASE    = "https://www.lidl.be/p/nl-BE/x"
DELAY        = 0.0   # istek arası bekleme (saniye)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "nl-BE,nl;q=0.9",
}


# ─── Supabase ────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = os.path.join(SCRIPT_DIR, "supabase_import_secrets.txt")
    lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
             if l.strip() and not l.strip().startswith("#")]
    return lines[0].rstrip("/"), lines[1]


def sb_headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"}


def fetch_lidl_rows(sb_url: str, sb_key: str, limit: Optional[int]) -> list[dict]:
    """image_url boş olan Lidl ürünlerini çek."""
    rows = []
    offset = 0
    chunk  = BATCH_SIZE
    hdrs   = sb_headers(sb_key)
    print("Lidl ürünleri DB'den çekiliyor…")
    while True:
        params = {
            "select":    "id,external_product_id",
            "chain_slug": "eq.lidl_be",
            "image_url": "is.null",
            "external_product_id": "not.is.null",
            "order":     "id.asc",
            "limit":     str(chunk),
            "offset":    str(offset),
        }
        r = requests.get(f"{sb_url}/rest/v1/market_chain_products",
                         params=params, headers=hdrs, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        offset += chunk
        if len(batch) < chunk:
            break
        if limit and len(rows) >= limit:
            rows = rows[:limit]
            break
    print(f"  {len(rows)} resimsiz Lidl ürünü bulundu.")
    return rows


def patch_image(sb_url: str, sb_key: str, row_id: int, image_url: str) -> bool:
    hdrs = {**sb_headers(sb_key), "Prefer": "return=minimal"}
    r = requests.patch(
        f"{sb_url}/rest/v1/market_chain_products?id=eq.{row_id}",
        json={"image_url": image_url},
        headers=hdrs, timeout=15,
    )
    return r.status_code in (200, 204)


# ─── Resim çekme ─────────────────────────────────────────────────────────────

def fetch_image_url(pid: str) -> Optional[str]:
    """Lidl ürün sayfasından ilk resim URL'ini döner, bulamazsa None."""
    url = f"{LIDL_BASE}/{pid}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if r.status_code != 200:
            return None
        # application/ld+json içindeki ilk ürün resmini al
        ld_blocks = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\']>(.*?)</script>',
            r.text, re.DOTALL
        )
        for block in ld_blocks:
            try:
                d = json.loads(block)
                typ = str(d.get("@type", ""))
                if "Product" in typ or "product" in typ.lower():
                    imgs = d.get("image", [])
                    if isinstance(imgs, list) and imgs:
                        return str(imgs[0])
                    if isinstance(imgs, str) and imgs:
                        return imgs
            except Exception:
                continue
        # Fallback: doğrudan gcp URL regex
        m = re.search(r'"(https://www\.lidl\.be/assets/gcp[a-f0-9]+\.jpg)"', r.text)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


# ─── Ana akış ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=None, help="Max kaç ürün işlensin")
    parser.add_argument("--dry-run", action="store_true",    help="DB'ye yazma")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    rows = fetch_lidl_rows(sb_url, sb_key, args.limit)
    if not rows:
        print("Güncellenecek ürün yok.")
        return

    bulundu   = 0
    bulunamadi = 0
    guncellendi = 0
    hata       = 0
    toplam     = len(rows)

    def isle(row: dict) -> tuple[int, Optional[str]]:
        pid = row.get("external_product_id", "")
        if not pid:
            return row["id"], None
        time.sleep(DELAY)
        img = fetch_image_url(pid)
        return row["id"], img

    print(f"\n{toplam} ürün işleniyor ({WORKERS} paralel istek)…")
    start = time.time()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(isle, row): row for row in rows}
        done = 0
        for fut in as_completed(futures):
            done += 1
            row_id, img_url = fut.result()
            if img_url:
                bulundu += 1
                if not args.dry_run:
                    ok = patch_image(sb_url, sb_key, row_id, img_url)
                    if ok:
                        guncellendi += 1
                    else:
                        hata += 1
            else:
                bulunamadi += 1

            if done % 100 == 0 or done == toplam:
                elapsed = time.time() - start
                speed   = done / elapsed if elapsed > 0 else 0
                kalan   = (toplam - done) / speed if speed > 0 else 0
                print(f"  [{done}/{toplam}] resim={bulundu} | yok={bulunamadi} | "
                      f"hata={hata} | ~{kalan/60:.1f} dk kaldı")

    elapsed = time.time() - start
    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Bitti!")
    print(f"  Toplam    : {toplam}")
    print(f"  Resim bulundu : {bulundu}  ({bulundu/toplam*100:.1f}%)")
    print(f"  Bulunamadı    : {bulunamadi}")
    print(f"  DB güncellendi: {guncellendi}")
    print(f"  Hata          : {hata}")
    print(f"  Süre          : {elapsed/60:.1f} dakika")


if __name__ == "__main__":
    main()
