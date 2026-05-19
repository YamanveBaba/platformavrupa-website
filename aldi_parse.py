# -*- coding: utf-8 -*-
"""
Aldi BE — SingleFile HTML Parse + Supabase Yükleme
Downloads klasöründeki Aldi HTML dosyalarını parse eder.

Kullanım:
  python aldi_parse.py                    # Downloads'tan otomatik bul
  python aldi_parse.py --klasor C:/baska  # Farklı klasör
  python aldi_parse.py --dry-run          # Supabase'e yazma, sadece say
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    import requests
except ImportError:
    print("HATA: pip install beautifulsoup4 requests"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = Path.home() / "Downloads"


# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def load_secrets():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        path = os.path.normpath(
            os.path.join(SCRIPT_DIR, "market_fiyat_cekici", "supabase_import_secrets.txt")
        )
        if os.path.isfile(path):
            lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                     if l.strip() and not l.startswith("#")]
            if len(lines) >= 2:
                url, key = lines[0].rstrip("/"), lines[1]
    if not url or not key:
        print("HATA: Supabase credentials bulunamadı."); sys.exit(1)
    return url, key


def supabase_upsert(sb_url, sb_key, rows, dry_run):
    if dry_run or not rows:
        return len(rows)
    headers = {
        "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    r = requests.post(
        f"{sb_url}/rest/v1/market_chain_products?on_conflict=chain_slug,external_product_id",
        json=rows, headers=headers, timeout=60
    )
    if r.status_code not in (200, 201, 204):
        # Yarıya böl ve tekrar dene
        if len(rows) > 1:
            yari = len(rows) // 2
            return (supabase_upsert(sb_url, sb_key, rows[:yari], dry_run) +
                    supabase_upsert(sb_url, sb_key, rows[yari:], dry_run))
        print(f"  UYARI: {r.status_code}: {r.text[:100]}")
        return 0
    return len(rows)


# ─── PARSE ────────────────────────────────────────────────────────────────────

def fiyat_cikart(text):
    """'€ 1,99' veya '1.99' → float."""
    if not text:
        return None
    text = text.replace('\xa0', ' ').strip()
    m = re.search(r'(\d+)[,.](\d{2})', text)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    return None


def html_parse(dosya: Path) -> list[dict]:
    """Tek bir Aldi HTML dosyasından ürünleri çıkar."""
    try:
        soup = BeautifulSoup(dosya.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    except Exception as e:
        print(f"  HATA: {dosya.name}: {e}")
        return []

    urunler = []

    # Aldi ürün kartları — farklı selector kombinasyonları dene
    kartlar = (
        soup.select(".product-tile") or
        soup.select(".mod-article-tile") or
        soup.select("[class*='product-tile']") or
        soup.select("article") or
        []
    )

    for kart in kartlar:
        try:
            # İsim
            isim_el = (
                kart.select_one(".product-tile__name") or
                kart.select_one(".mod-article-tile__title") or
                kart.select_one("h2") or
                kart.select_one("h3") or
                kart.select_one("[class*='name']") or
                kart.select_one("[class*='title']")
            )
            isim = isim_el.get_text(strip=True) if isim_el else ""
            if not isim:
                continue

            # Fiyat
            fiyat_el = (
                kart.select_one(".product-tile__price--current") or
                kart.select_one(".product-tile__price") or
                kart.select_one("[class*='price']")
            )
            fiyat = fiyat_cikart(fiyat_el.get_text() if fiyat_el else "")

            # Promo fiyat
            promo_el = (
                kart.select_one(".product-tile__price--old") or
                kart.select_one("[class*='old-price']") or
                kart.select_one("[class*='was-price']")
            )
            promo = fiyat_cikart(promo_el.get_text() if promo_el else "")

            # Resim
            img = kart.select_one("img")
            resim = ""
            if img:
                resim = img.get("src") or img.get("data-src") or img.get("data-lazy") or ""
                # base64 placeholder'ı atla
                if resim.startswith("data:"):
                    resim = img.get("data-src") or img.get("data-lazy") or ""

            # Kategori (dosya adından)
            kategori = dosya.stem.replace("www.aldi.be_nl_producten_assortiment_", "").replace("_", " ")

            # Basit ID: isim hash
            import hashlib
            pid = hashlib.md5(isim.encode()).hexdigest()[:12]

            row = {
                "chain_slug": "aldi_be",
                "country_code": "BE",
                "external_product_id": pid,
                "name": isim[:300],
                "brand": "",
                "price": fiyat or 0,
                "currency": "EUR",
                "promo_price": promo,
                "in_promo": promo is not None,
                "category_name": kategori,
                "image_url": resim[:400] if resim else None,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
            urunler.append(row)
        except Exception:
            continue

    return urunler


def aldi_dosyalari_bul(klasor: Path) -> list[Path]:
    """Klasörde Aldi HTML dosyalarını bul."""
    dosyalar = []
    for f in klasor.glob("*.html"):
        name = f.name.lower()
        if "aldi" in name or "assortiment" in name or "producten" in name:
            dosyalar.append(f)
    return sorted(dosyalar)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--klasor", default=str(DOWNLOADS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sb_url, sb_key = load_secrets()
    klasor = Path(args.klasor)

    dosyalar = aldi_dosyalari_bul(klasor)
    if not dosyalar:
        print(f"Aldi HTML dosyası bulunamadı: {klasor}")
        print("Önce python aldi_cek.py çalıştır.")
        sys.exit(0)

    print(f"{len(dosyalar)} Aldi HTML dosyası bulundu.")

    tum_urunler = []
    for dosya in dosyalar:
        urunler = html_parse(dosya)
        print(f"  {dosya.name}: {len(urunler)} ürün")
        tum_urunler.extend(urunler)

    print(f"\nToplam: {len(tum_urunler)} ürün")

    if not tum_urunler:
        print("Ürün çıkarılamadı. HTML selector'lar farklı olabilir.")
        print("İlk dosyayı açıp ürün kartı class adlarını kontrol et.")
        sys.exit(0)

    # Supabase'e yükle
    print("\nSupabase'e yükleniyor...")
    BATCH = 200
    toplam = 0
    for i in range(0, len(tum_urunler), BATCH):
        batch = tum_urunler[i:i + BATCH]
        n = supabase_upsert(sb_url, sb_key, batch, args.dry_run)
        toplam += n
        print(f"  {min(i + BATCH, len(tum_urunler))} / {len(tum_urunler)}")

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Tamamlandı: {toplam} ürün yüklendi.")


if __name__ == "__main__":
    main()
