# -*- coding: utf-8 -*-
"""
cikti/*.json dosyalarını Supabase market_chain_products tablosuna yükler (upsert).

GÜVENLİK: Service Role anahtarı sadece bu scriptte / ortam değişkeninde kullanılır.
Asla GitHub'a veya site koduna (config.js) koymayın.

Kullanım:
  python json_to_supabase_yukle.py
  python json_to_supabase_yukle.py "cikti\\aldi_be_tum_urunler_platform_2026-01-01_12-00.json"
  python json_to_supabase_yukle.py --dry-run "cikti\\colruyt_be_playwright_....json"

Desteklenen zincirler: ALDI, Colruyt, Delhaize, Lidl, Carrefour (JSON icinde kaynak/chain_slug veya urun alanlari).

Supabase: market_chain_products tablosunda promo_valid_from sutunu yoksa supabase_market_chain_products.sql
icindeki ALTER satirini SQL Editor'da bir kez calistirin (aksi halde upsert 400 donebilir).

Kimlik bilgisi (birini kullanın):
 1) Ortam değişkenleri: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 2) Dosya: supabase_import_secrets.txt (ilk satır URL, ikinci satır service_role key)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

# Çeviri sistemi — aynı klasörde ceviri_sistemi.py varsa yükle
try:
    import importlib.util as _ilu
    _ceviri_path = Path(__file__).parent / "ceviri_sistemi.py"
    _spec = _ilu.spec_from_file_location("ceviri_sistemi", _ceviri_path)
    _ceviri_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_ceviri_mod)
    _glossary_cevir = _ceviri_mod.glossary_cevir
    print("  [çeviri] Glossary yüklendi — name_tr otomatik doldurulacak")
except Exception:
    _glossary_cevir = None

BATCH_SIZE = 300


def _cevir(isim: str) -> str | None:
    """Glossary ile Türkçeye çevir. Yüklenemezse None döner (DB'de boş kalır)."""
    if not _glossary_cevir or not isim:
        return None
    try:
        sonuc, _ = _glossary_cevir(isim)
        return sonuc[:2000] if sonuc != isim else sonuc[:2000]
    except Exception:
        return None


def _normalize_secret_line(line: str, *, is_url: bool) -> str:
    """Yanlışlıkla yapıştırılan SUPABASE_URL=, tırnak, BOM temizler."""
    s = line.strip().strip("\ufeff")
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    prefix = "SUPABASE_URL=" if is_url else "SUPABASE_SERVICE_ROLE_KEY="
    if s.upper().startswith(prefix.upper()):
        s = s.split("=", 1)[1].strip()
    if not is_url and s.lower().startswith("bearer "):
        s = s[6:].strip()
    return s


def load_secrets(script_dir: str) -> tuple[str, str]:
    url = _normalize_secret_line(os.environ.get("SUPABASE_URL", ""), is_url=True)
    key = _normalize_secret_line(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""), is_url=False)
    if url and key:
        return url.rstrip("/"), key
    path = os.path.join(script_dir, "supabase_import_secrets.txt")
    if not os.path.isfile(path):
        print(
            "HATA: SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY ortam değişkeninde yok,\n"
            f"       veya {path} dosyası bulunamadı.\n"
            "Supabase -> Project Settings -> API -> service_role key kopyalayın."
        )
        sys.exit(1)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) < 2:
        print("HATA: supabase_import_secrets.txt içinde ilk satır URL, ikinci satır service_role olmalı.")
        sys.exit(1)
    url = _normalize_secret_line(lines[0], is_url=True).rstrip("/")
    key = _normalize_secret_line(lines[1], is_url=False)
    if "supabase.co" not in url and not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
        print(
            "UYARI: 1. satırdaki adres genelde şöyle olur: https://xxxx.supabase.co\n"
            "       (kendi domain / Netlify adresi değil; Supabase panel -> Settings -> API -> Project URL)"
        )
    return url, key


def detect_format(data: dict) -> Optional[str]:
    slug = str(data.get("chain_slug") or "").lower()
    if slug == "delhaize_be":
        return "delhaize"
    if slug == "lidl_be":
        return "lidl"
    if slug == "carrefour_be":
        return "carrefour"
    if slug.startswith("colruyt_"):
        return "colruyt"
    if slug.startswith("aldi_"):
        return "aldi"
    kaynak = str(data.get("kaynak") or "")
    if "Colruyt" in kaynak or "colruyt" in kaynak.lower():
        return "colruyt"
    if "ALDI" in kaynak or "aldi" in kaynak.lower():
        return "aldi"
    if "delhaize" in kaynak.lower():
        return "delhaize"
    if "lidl" in kaynak.lower():
        return "lidl"
    if "carrefour" in kaynak.lower():
        return "carrefour"
    urunler = data.get("urunler") or data.get("products") or []
    if not urunler:
        return None
    s0 = urunler[0]
    if isinstance(s0, dict):
        if s0.get("retailProductNumber") is not None:
            return "colruyt"
        if s0.get("productID") is not None:
            return "aldi"
        pc = s0.get("productCode")
        if pc and str(pc).startswith("F"):
            return "delhaize"
        if s0.get("lidlProductKey") or s0.get("lidlUrlPath"):
            return "lidl"
        if s0.get("carrefourPid"):
            return "carrefour"
    return None


def parse_promo_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # "24-03-2026" gibi
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:10] if len(s) >= 10 else s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def row_aldi(
    u: dict,
    captured_at: str,
    import_run_id: str,
    include_raw: bool,
    *,
    chain_slug: str = "aldi_be",
    country_code: str = "BE",
) -> dict:
    # v2: aldiPid / name / basicPrice — eski: productID / productName / priceWithTax
    pid = str(u.get("productID") or u.get("aldiPid") or u.get("pid") or "").strip()
    if not pid:
        return {}
    price = u.get("basicPrice") if u.get("basicPrice") is not None else u.get("priceWithTax")
    try:
        price_f = float(price) if price is not None else 0.0
    except (TypeError, ValueError):
        price_f = 0.0
    promo = u.get("promoPrice")
    try:
        promo_f = float(promo) if promo is not None else None
    except (TypeError, ValueError):
        promo_f = None
    in_promo = bool(u.get("inPromo") or u.get("inPromotion"))
    promo_from = parse_promo_date(u.get("promoValidFrom") or u.get("promotionStartDate"))
    promo_until = parse_promo_date(u.get("promoValidUntil") or u.get("promotionEndDate"))
    name = u.get("name") or u.get("productName") or ""
    image = u.get("imageUrl") or ""
    # base64 placeholder'ları atla
    if image.startswith("data:"):
        image = ""
    row = {
        "chain_slug": chain_slug[:80],
        "country_code": country_code[:8],
        "external_product_id": pid,
        "place_or_store_ref": None,
        "name": name[:2000],
        "name_tr": _cevir(name),
        "brand": (u.get("brand") or "")[:500] or None,
        "unit_or_content": None,
        "price": price_f,
        "currency": "EUR",
        "promo_price": promo_f if in_promo else None,
        "in_promo": in_promo,
        "promo_valid_from": promo_from,
        "promo_valid_until": promo_until,
        "category_name": (u.get("topCategoryName") or u.get("category") or "")[:500] or None,
        "image_url": image[:1000] or None,
        "captured_at": captured_at,
        "import_run_id": import_run_id,
        "raw_json": u if include_raw else None,
    }
    return row


def row_colruyt(
    p: dict,
    place_id: Optional[str],
    captured_at: str,
    import_run_id: str,
    include_raw: bool,
    *,
    chain_slug: str = "colruyt_be",
    country_code: str = "BE",
) -> dict:
    rpn = p.get("retailProductNumber")
    if rpn is None or str(rpn).strip() == "":
        return {}
    try:
        price_f = float(p.get("basicPrice"))
    except (TypeError, ValueError):
        price_f = 0.0
    qp = p.get("quantityPrice")
    try:
        promo_f = float(qp) if qp is not None else None
    except (TypeError, ValueError):
        promo_f = None
    in_promo = bool(p.get("inPromo"))
    promo_start = parse_promo_date(p.get("promoPublicationStart"))
    promo_end = parse_promo_date(p.get("promoPublicationEnd"))
    row = {
        "chain_slug": chain_slug[:80],
        "country_code": country_code[:8],
        "external_product_id": str(rpn).strip(),
        "place_or_store_ref": place_id,
        "name": (p.get("name") or p.get("LongName") or "")[:2000],
        "name_tr": _cevir(p.get("name") or p.get("LongName") or ""),
        "brand": (p.get("brand") or "")[:500] or None,
        "unit_or_content": (p.get("content") or "")[:200] or None,
        "price": price_f,
        "currency": "EUR",
        "promo_price": promo_f if in_promo else None,
        "in_promo": in_promo,
        "promo_valid_from": promo_start,
        "promo_valid_until": promo_end,
        "category_name": (p.get("topCategoryName") or "")[:500] or None,
        "image_url": None,
        "captured_at": captured_at,
        "import_run_id": import_run_id,
        "raw_json": p if include_raw else None,
    }
    return row


def row_delhaize(p: dict, captured_at: str, import_run_id: str, include_raw: bool) -> dict:
    # v2 formatı delhaizePid kullanıyor, eski format productCode
    code = str(p.get("productCode") or p.get("delhaizePid") or p.get("external_product_id") or "").strip()
    if not code:
        return {}
    try:
        price_f = float(p.get("basicPrice"))
    except (TypeError, ValueError):
        price_f = 0.0
    pp = p.get("promoPrice")
    try:
        promo_f = float(pp) if pp is not None else None
    except (TypeError, ValueError):
        promo_f = None
    in_promo = bool(p.get("inPromo"))
    row = {
        "chain_slug": "delhaize_be",
        "country_code": str(p.get("country_code") or "BE")[:8],
        "external_product_id": code,
        "place_or_store_ref": None,
        "name": (p.get("name") or "")[:2000],
        "name_tr": _cevir(p.get("name") or ""),
        "brand": (p.get("brand") or "")[:500] or None,
        "unit_or_content": (p.get("unitContent") or "")[:200] or None,
        "price": price_f,
        "currency": "EUR",
        "promo_price": promo_f if in_promo else None,
        "in_promo": in_promo,
        "promo_valid_from": parse_promo_date(p.get("promoValidFrom")),
        "promo_valid_until": parse_promo_date(p.get("promoValidUntil")),
        "category_name": (p.get("topCategoryName") or p.get("categoryName") or "")[:500] or None,
        "image_url": (p.get("imageUrl") or "")[:1000] or None,
        "captured_at": captured_at,
        "import_run_id": import_run_id,
        "raw_json": p if include_raw else None,
    }
    return row


def row_lidl(p: dict, captured_at: str, import_run_id: str, include_raw: bool) -> dict:
    pid = str(p.get("lidlProductKey") or p.get("external_product_id") or "").strip()
    if not pid:
        return {}
    try:
        price_f = float(p.get("basicPrice"))
    except (TypeError, ValueError):
        price_f = 0.0
    in_promo = bool(p.get("inPromo"))
    try:
        promo_f = float(p.get("promoPrice")) if p.get("promoPrice") is not None else None
    except (TypeError, ValueError):
        promo_f = None
    promo_from = parse_promo_date(p.get("promotionStartDate"))
    promo_until = parse_promo_date(p.get("promotionEndDate"))
    row = {
        "chain_slug": "lidl_be",
        "country_code": "BE",
        "external_product_id": pid[:500],
        "place_or_store_ref": None,
        "name": (p.get("name") or "")[:2000],
        "name_tr": _cevir(p.get("name") or ""),
        "brand": (p.get("brand") or "")[:500] or None,
        "unit_or_content": (p.get("unitContent") or "")[:200] or None,
        "price": price_f,
        "currency": "EUR",
        "promo_price": promo_f if in_promo else None,
        "in_promo": in_promo,
        "promo_valid_from": promo_from,
        "promo_valid_until": promo_until,
        "category_name": (p.get("topCategoryName") or "")[:500] or None,
        "image_url": (p.get("imageUrl") or p.get("lidlImageUrl") or "")[:1000] or None,
        "captured_at": captured_at,
        "import_run_id": import_run_id,
        "raw_json": p if include_raw else None,
    }
    return row


def row_carrefour(p: dict, captured_at: str, import_run_id: str, include_raw: bool) -> dict:
    pid = str(p.get("carrefourPid") or "").strip()
    if not pid:
        return {}
    try:
        price_f = float(p.get("basicPrice"))
    except (TypeError, ValueError):
        price_f = 0.0
    in_promo = bool(p.get("inPromo"))
    try:
        promo_f = float(p.get("promoPrice")) if p.get("promoPrice") is not None else None
    except (TypeError, ValueError):
        promo_f = None
    row = {
        "chain_slug": "carrefour_be",
        "country_code": "BE",
        "external_product_id": pid[:500],
        "place_or_store_ref": None,
        "name": (p.get("name") or "")[:2000],
        "name_tr": _cevir(p.get("name") or ""),
        "brand": (p.get("brand") or "")[:500] or None,
        "unit_or_content": (p.get("unitContent") or "")[:200] or None,
        "price": price_f,
        "currency": "EUR",
        "promo_price": promo_f if in_promo else None,
        "in_promo": in_promo,
        "promo_valid_from": None,
        "promo_valid_until": None,
        "category_name": (p.get("topCategoryName") or "")[:500] or None,
        "image_url": (p.get("imageUrl") or "")[:1000] or None,
        "captured_at": captured_at,
        "import_run_id": import_run_id,
        "raw_json": p if include_raw else None,
    }
    return row


def json_to_rows(data: dict, include_raw: bool) -> List[dict]:
    fmt = detect_format(data)
    if not fmt:
        print("HATA: JSON formatı tanınamadı (desteklenen zincir: ALDI, Colruyt, Delhaize, Lidl, Carrefour).")
        return []

    now = datetime.now(timezone.utc).isoformat()
    captured = data.get("cekilme_tarihi") or now
    if isinstance(captured, str):
        captured_at = captured
    else:
        captured_at = now

    import_run_id = str(uuid.uuid4())
    urunler = data.get("urunler") or data.get("products") or []
    place_id = str(data.get("placeId") or "") or None
    cc = str(data.get("country_code") or "BE")[:8]
    colruyt_slug = str(data.get("chain_slug") or "colruyt_be")[:80]
    aldi_slug = str(data.get("chain_slug") or "aldi_be")[:80]

    rows: List[dict] = []
    if fmt == "aldi":
        for u in urunler:
            if not isinstance(u, dict):
                continue
            r = row_aldi(
                u,
                captured_at,
                import_run_id,
                include_raw,
                chain_slug=aldi_slug,
                country_code=cc,
            )
            if r:
                rows.append(r)
    elif fmt == "colruyt":
        for p in urunler:
            if not isinstance(p, dict):
                continue
            r = row_colruyt(
                p,
                place_id,
                captured_at,
                import_run_id,
                include_raw,
                chain_slug=colruyt_slug,
                country_code=cc,
            )
            if r:
                rows.append(r)
    elif fmt == "delhaize":
        for p in urunler:
            if not isinstance(p, dict):
                continue
            p = {**p, "country_code": cc}
            r = row_delhaize(p, captured_at, import_run_id, include_raw)
            if r:
                rows.append(r)
    elif fmt == "lidl":
        for p in urunler:
            if not isinstance(p, dict):
                continue
            r = row_lidl(p, captured_at, import_run_id, include_raw)
            if r:
                rows.append(r)
    elif fmt == "carrefour":
        for p in urunler:
            if not isinstance(p, dict):
                continue
            r = row_carrefour(p, captured_at, import_run_id, include_raw)
            if r:
                rows.append(r)

    return rows


def upsert_batches(
    supabase_url: str,
    service_key: str,
    rows: List[dict],
    dry_run: bool,
) -> bool:
    if not rows:
        print("Yüklenecek satır yok.")
        return False

    base = supabase_url.rstrip("/")
    endpoint = f"{base}/rest/v1/market_chain_products"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    params = {"on_conflict": "chain_slug,external_product_id"}

    if dry_run:
        print(f"[DRY-RUN] {len(rows)} satır gönderilecek (ilk örnek):")
        print(json.dumps(rows[0], ensure_ascii=False, indent=2)[:2000])
        return True

    total = len(rows)
    for i in range(0, total, BATCH_SIZE):
        chunk = rows[i : i + BATCH_SIZE]
        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                params=params,
                json=chunk,
                timeout=180,
            )
        except requests.RequestException as e:
            print(f"İstek hatası: {e}")
            return False
        if resp.status_code not in (200, 201, 204):
            print(f"HATA HTTP {resp.status_code}: {resp.text[:1500]}")
            print(f"İstek adresi: {endpoint}")
            if resp.status_code == 405:
                print(
                    "405 = Bu adrese POST kabul edilmiyor. 1. satırda Supabase 'Project URL' olmalı:\n"
                    "   Panel -> Project Settings -> API -> Project URL -> örn. https://abcdefgh.supabase.co\n"
                    "   (platformavrupa.com / Netlify / dashboard.supabase.com adresi YAZMA.)"
                )
            return False
        print(f"  Gönderildi: {min(i + BATCH_SIZE, total)} / {total}")

    print(f"Tamam: {total} satır upsert edildi.")
    return True


def log_import_run(
    supabase_url: str,
    service_key: str,
    chain_slug: str,
    row_count: int,
    status: str,
    notes: str,
) -> None:
    base = supabase_url.rstrip("/")
    endpoint = f"{base}/rest/v1/market_price_import_runs"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = {
        "chain_slug": chain_slug,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "status": status,
        "notes": notes[:2000] if notes else None,
    }
    try:
        r = requests.post(endpoint, headers=headers, json=body, timeout=60)
        if r.status_code not in (200, 201, 204):
            print(f"(Uyarı) import log yazılamadı: {r.status_code} {r.text[:300]}")
    except requests.RequestException as e:
        print(f"(Uyarı) import log: {e}")


def main():
    parser = argparse.ArgumentParser(description="JSON -> Supabase market_chain_products")
    parser.add_argument(
        "json_path",
        nargs="?",
        default=None,
        help="Yüklenecek JSON (cikti/). Verilmezse sırayla: aldi platform -> aldi yeme-içme -> colruyt playwright -> colruyt producten (her grupta en yeni dosya).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Sadece format kontrolü ve ilk satır örneği")
    parser.add_argument("--raw", action="store_true", help="raw_json sütununu doldur (daha büyük veri)")
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Bittiğinde Enter bekleme (otomasyon / toplu iş için)",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")

    json_path = args.json_path
    if not json_path:
        import glob

        # Önce ALDI platform listesi (dolu olma ihtimali yüksek), sonra diğerleri
        patterns_in_order = [
            "aldi_be_tum_urunler_platform_*.json",
            "aldi_be_tum_yeme_icme_*.json",
            "colruyt_be_playwright_*.json",
            "colruyt_be_producten_*.json",
            "delhaize_be_producten_*.json",
            "lidl_be_producten_*.json",
            "carrefour_be_producten_*.json",
        ]
        json_path = None
        for name in patterns_in_order:
            matches = glob.glob(os.path.join(cikti_dir, name))
            if matches:
                json_path = max(matches, key=os.path.getmtime)
                break
        if not json_path:
            print("HATA: cikti/ klasöründe uygun JSON bulunamadı. Dosya yolunu parametre olarak verin.")
            sys.exit(1)
        print(f"Otomatik seçilen dosya: {json_path}\n")

    if not os.path.isfile(json_path):
        print(f"HATA: Dosya yok: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    urunler = data.get("urunler") or data.get("products") or []
    if len(urunler) == 0:
        print("HATA: Bu JSON dosyasında hiç ürün yok (urunler / products boş).")
        print("  Colruyt API 406/401 ile bittiğinde böyle kalır; yükleme yapılamaz.")
        print("  Çözüm: ALDI için merge sonrası dosyayı seçin, örn.:")
        print('    python json_to_supabase_yukle.py --dry-run "cikti\\aldi_be_tum_urunler_platform_....json"')
        print("  veya önce Colruyt/ALDI çekimini başarılı bir JSON üretin.")
        sys.exit(1)

    fmt = detect_format(data)
    if not fmt:
        print("HATA: Dosya formatı tanınamadı (ALDI veya Colruyt alanları eksik olabilir).")
        sys.exit(1)

    rows = json_to_rows(data, include_raw=args.raw)
    if not rows:
        print("HATA: Ürünler vardı ama tablo satırına dönüştürülemedi (eksik alan?).")
        sys.exit(1)

    chain_slug = rows[0]["chain_slug"]
    print(f"Format: {fmt} -> {len(rows)} rows (chain_slug={chain_slug})")

    url, key = load_secrets(script_dir)

    ok = upsert_batches(url, key, rows, dry_run=args.dry_run)
    if ok and not args.dry_run:
        log_import_run(
            url,
            key,
            chain_slug,
            len(rows),
            "ok",
            os.path.basename(json_path),
        )
    if not args.no_pause:
        input("\nÇıkmak için Enter...")


if __name__ == "__main__":
    main()
