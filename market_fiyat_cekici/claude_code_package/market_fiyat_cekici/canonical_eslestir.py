"""
canonical_eslestir.py
=====================
Kanonik 300 ürünü market_chain_products tablosundaki veriye karşı eşleştirir.
Sonuçları product_offers tablosuna yazar.

Adımlar:
  1. canonical_products tablosundan 300 ürünü yükle
  2. market_chain_products'tan her market için tüm ürünleri yükle (cache)
  3. Her canonical ürün için nl_search terimi + fuzzy ile en iyi eşleşmeyi bul
  4. Birim fiyatı hesapla
  5. Promo metnini Türkçeye çevir (promo_ceviri.py)
  6. product_offers tablosuna upsert et

Kullanım:
  python canonical_eslestir.py            # tüm 300 ürünü işle
  python canonical_eslestir.py --dry-run  # yazma, sadece raporla
  python canonical_eslestir.py --limit 50 # test için ilk 50 ürün
"""

import argparse
import os
import sys
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client
from rapidfuzz import fuzz

from product_normalize import norm_text, parse_quantity, unit_price as calc_unit_price
from promo_ceviri import promo_ceviri

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CANONICAL] %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

CHAINS = ["colruyt_be", "aldi_be", "delhaize_be", "lidl_be", "carrefour_be"]
FUZZY_MIN = 75
FETCH_CHUNK = 5000


def load_canonical(sb: Client) -> list[dict]:
    resp = sb.table("canonical_products").select("*").order("name_tr").execute()
    return resp.data or []


def load_chain_products(sb: Client, chain: str) -> list[dict]:
    """market_chain_products'tan bir zincirin tüm ürünlerini çek (sayfalanmış)."""
    all_rows = []
    offset = 0
    while True:
        resp = (
            sb.table("market_chain_products")
            .select("external_product_id,name,brand,price,promo_price,in_promo,"
                    "promo_valid_from,promo_valid_until,image_url,captured_at,category_name")
            .eq("chain_slug", chain)
            .range(offset, offset + FETCH_CHUNK - 1)
            .execute()
        )
        batch = resp.data or []
        all_rows.extend(batch)
        log.debug(f"  {chain}: {len(all_rows)} satır yüklendi...")
        if len(batch) < FETCH_CHUNK:
            break
        offset += FETCH_CHUNK

    log.info(f"  {chain}: {len(all_rows)} ürün yüklendi")
    return all_rows


def find_best_match(canonical: dict, chain_products: list[dict]) -> dict | None:
    """
    Bir canonical ürün için en iyi zincir eşleşmesini bul.

    Strateji:
      1. EAN varsa tam eşleşme (marka ürünler için)
      2. nl_search terimi ile fuzzy eşleştirme
      3. En yüksek skorlu eşleşmeyi döndür (threshold: FUZZY_MIN)
    """
    if not chain_products:
        return None

    nl_search = norm_text(canonical.get("nl_search", ""))
    tip = canonical.get("tip", "sepet")

    best_score = 0
    best_match = None

    for p in chain_products:
        name_n = norm_text(p.get("name", ""))
        if not name_n:
            continue

        # EAN eşleşme (en güvenilir, marka ürünler için)
        if canonical.get("ean") and p.get("ean"):
            if canonical["ean"] == p["ean"]:
                return p

        # Fuzzy eşleşme
        score = fuzz.token_set_ratio(nl_search, name_n)

        # Sepet ürünleri için marka cezası: aynı zincirin kendi markaları öncelikli
        if tip == "marka" and score < 90:
            # Marka ürünlerde yüksek eşik iste
            continue

        if score > best_score:
            best_score = score
            best_match = p

    if best_score >= FUZZY_MIN:
        return best_match
    return None


def calc_offer_unit_price(p: dict, canonical: dict) -> float | None:
    """Ürün için birim fiyat hesapla (€/kg, €/L veya €/adet)."""
    effective_price = p.get("promo_price") or p.get("price")
    if not effective_price:
        return None
    up, _ = calc_unit_price(float(effective_price), p.get("name", ""))
    return up


def build_offer(canonical: dict, chain: str, match: dict) -> dict:
    """canonical + market eşleşmesinden product_offers satırı oluştur."""
    eff_price = match.get("promo_price") or match.get("price")
    unit_p = calc_offer_unit_price(match, canonical)
    promo_nl = None
    promo_tr = None

    if match.get("in_promo"):
        promo_nl = match.get("promo_description") or match.get("promo_label")
        if promo_nl:
            promo_tr = promo_ceviri(promo_nl)

    return {
        "canonical_id": canonical["id"],
        "chain": chain,
        "market_name": (match.get("name") or "")[:255],
        "price": match.get("price"),
        "promo_price": match.get("promo_price"),
        "in_promo": bool(match.get("in_promo")),
        "promo_text_nl": promo_nl,
        "promo_text_tr": promo_tr,
        "promo_valid_from": match.get("promo_valid_from"),
        "promo_valid_until": match.get("promo_valid_until"),
        "unit_price": unit_p,
        "image_url": match.get("image_url"),
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_offers(sb: Client, offers: list[dict], dry_run: bool = False) -> int:
    if not offers or dry_run:
        return len(offers)
    try:
        sb.table("product_offers").upsert(
            offers, on_conflict="canonical_id,chain"
        ).execute()
        return len(offers)
    except Exception as e:
        log.error(f"Upsert hatası: {e}")
        saved = 0
        for chunk in [offers[i:i+50] for i in range(0, len(offers), 50)]:
            try:
                sb.table("product_offers").upsert(
                    chunk, on_conflict="canonical_id,chain"
                ).execute()
                saved += len(chunk)
            except Exception as e2:
                log.error(f"Chunk upsert: {e2}")
        return saved


def run(dry_run: bool = False, limit: int | None = None):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log.error("SUPABASE_URL veya SUPABASE_SERVICE_KEY eksik")
        sys.exit(1)

    sb = create_client(url, key)

    log.info("=" * 60)
    log.info("CANONICAL EŞLEŞTİRME BAŞLIYOR")
    if dry_run:
        log.info("  [DRY-RUN] Yazma yapılmayacak")
    log.info("=" * 60)

    # 1. Canonical ürünleri yükle
    canonical_list = load_canonical(sb)
    if limit:
        canonical_list = canonical_list[:limit]
    log.info(f"Canonical ürün: {len(canonical_list)}")

    # 2. Her zincir için ürünleri yükle (cache)
    log.info("\nMarket ürünleri yükleniyor...")
    chain_data: dict[str, list[dict]] = {}
    for chain in CHAINS:
        chain_data[chain] = load_chain_products(sb, chain)

    # 3. Her canonical ürün için eşleştir
    log.info("\nEşleştirme başlıyor...")
    total_offers = 0
    not_found: list[str] = []

    for idx, canon in enumerate(canonical_list, 1):
        offers_batch = []
        found_chains = []

        for chain in CHAINS:
            match = find_best_match(canon, chain_data[chain])
            if match:
                offer = build_offer(canon, chain, match)
                offers_batch.append(offer)
                found_chains.append(chain.replace("_be", ""))

        if offers_batch:
            saved = upsert_offers(sb, offers_batch, dry_run=dry_run)
            total_offers += saved

        if found_chains:
            log.info(f"  [{idx:3}/{len(canonical_list)}] {canon['name_tr']:35} → {', '.join(found_chains)}")
        else:
            not_found.append(canon["name_tr"])
            log.warning(f"  [{idx:3}/{len(canonical_list)}] {canon['name_tr']:35} → hiçbir markette bulunamadı")

    log.info("\n" + "=" * 60)
    log.info(f"TAMAMLANDI — {total_offers} teklif {'yazıldı' if not dry_run else 'bulundu (dry-run)'}")
    log.info(f"  Eşleşmeyen ürünler: {len(not_found)}/{len(canonical_list)}")
    if not_found:
        log.info("  Eşleşmeyen: " + ", ".join(not_found[:10]) + ("..." if len(not_found) > 10 else ""))
    log.info("=" * 60)

    return total_offers


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Canonical ürün eşleştirici")
    ap.add_argument("--dry-run", action="store_true", help="Yazma, sadece raporla")
    ap.add_argument("--limit", type=int, help="Test için ilk N ürün")
    args = ap.parse_args()
    run(dry_run=args.dry_run, limit=args.limit)
