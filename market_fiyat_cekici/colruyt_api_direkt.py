# -*- coding: utf-8 -*-
"""
Colruyt Belçika — Direkt API Çekici (Playwright olmadan)
=========================================================
Playwright gereksiz: API key + requests yeterli.

KULLANIM:
    python colruyt_api_direkt.py                    # Tüm kategoriler
    python colruyt_api_direkt.py --test             # Sadece 3 kategori (hızlı test)
    python colruyt_api_direkt.py --place-id 955     # Farklı mağaza
    python colruyt_api_direkt.py --no-pause         # Enter bekleme
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import re

import requests

# ── Sabitler ────────────────────────────────────────────────────────────────
API_BASE = (
    "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc"
    "/cg/nl/api/product-search-prs"
)
API_KEY   = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
PLACE_ID  = "710"   # Gent — değiştirmek için --place-id
PAGE_SIZE = 60      # Maksimum sayfa boyutu

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.colruyt.be/nl/producten",
    "Origin": "https://www.colruyt.be",
    "X-CG-APIKey": API_KEY,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}


def _cookie_from_curl(script_dir: str) -> Optional[str]:
    """curl.txt veya cookie.txt varsa Cookie değerini döndürür."""
    for fname in ("curl.txt", "cookie.txt"):
        path = os.path.join(script_dir, fname)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read().replace("\r\n", "\n").replace("\r", "\n")
            # curl.txt: -H "cookie: ..." satırından çıkar
            for pat in [
                r'(?i)-H\s+[\'"]cookie:\s*([^\'"]{20,})[\'"]',
                r'(?i)--cookie\s+[\'"]([^\'"]{20,})[\'"]',
            ]:
                m = re.search(pat, text)
                if m:
                    return m.group(1).strip()
            # cookie.txt: tek satır değer
            first = text.strip().split("\n")[0].strip()
            if first.lower().startswith("cookie:"):
                first = first[7:].strip()
            if len(first) > 20:
                return first
        except Exception:
            pass
    return None

# Tüm bilinen üst kategori ID'leri
KATEGORILER: List[Tuple[str, str]] = [
    ("65",   "Zuivel"),
    ("91",   "Kaas"),
    ("105",  "Vleeswaren"),
    ("124",  "Brood & gebak"),
    ("129",  "Ontbijt & beleg"),
    ("188",  "Dranken"),
    ("233",  "Diepvries"),
    ("306",  "Baby"),
    ("335",  "Snoep & koekjes"),
    ("347",  "Chips & noten"),
    ("354",  "Pasta, rijst & granen"),
    ("421",  "Sauzen & kruiden"),
    ("591",  "Lichaamsverzorging"),
    ("628",  "Onderhoud & huishouden"),
    ("670",  "Dier"),
    ("693",  "Huishoudartikelen"),
    ("761",  "Sterk & licht bier"),
    ("1675", "Groenten en fruit"),
    # Alt kategoriler (daha az çakışma için)
    ("10",   "Bananen"),
    ("21",   "Tomaten"),
    ("1171", "Harde kazen"),
    ("1172", "Verse kazen"),
    ("1173", "Verse kazen natuur"),
    ("1677", "Vers fruit"),
    ("1684", "Verse groenten"),
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CIKTI_DIR  = os.path.join(SCRIPT_DIR, "cikti")


# ── Yardımcılar ─────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def insan_bekle() -> None:
    r = random.random()
    if r < 0.03:
        t = random.uniform(20, 40)
        log(f"  [mola] {t:.0f} sn...")
        time.sleep(t)
    elif r < 0.12:
        time.sleep(random.uniform(3, 8))
    else:
        time.sleep(random.uniform(0.4, 1.2))


def urun_donustur(p: dict) -> dict:
    pr      = p.get("price") or {}
    promos  = p.get("promotion") or []
    promo0  = promos[0] if promos else {}
    return {
        "retailProductNumber":   p.get("retailProductNumber"),
        "technicalArticleNumber":p.get("technicalArticleNumber"),
        "name":                  p.get("name", ""),
        "brand":                 p.get("brand", "") or p.get("seoBrand", ""),
        "LongName":              p.get("LongName") or p.get("fullName") or p.get("name", ""),
        "content":               p.get("content", ""),
        "price":                 pr.get("basicPrice"),
        "basicPrice":            pr.get("basicPrice"),
        "quantityPrice":         pr.get("quantityPrice"),
        "pricePerUOM":           pr.get("pricePerUOM"),
        "measurementUnit":       pr.get("measurementUnit"),
        "isRedPrice":            pr.get("isRedPrice", False),
        "isPromoActive":         pr.get("isPromoActive", "N"),
        "inPromo":               bool(pr.get("isPromoActive") == "Y" or p.get("inPromo")),
        "promoPublicationStart": promo0.get("publicationStartDate"),
        "promoPublicationEnd":   promo0.get("publicationEndDate"),
        "promo_valid_from":      promo0.get("publicationStartDate"),
        "promo_valid_until":     promo0.get("publicationEndDate"),
        "activationDate":        pr.get("activationDate"),
        "topCategoryName":       p.get("topCategoryName", ""),
        "topCategoryId":         p.get("topCategoryId"),
        "nutriScore":            p.get("nutriScore"),
        "countryOfOrigin":       p.get("countryOfOrigin"),
        "isPriceAvailable":      p.get("isPriceAvailable", True),
        "isAvailable":           p.get("isAvailable", True),
        "image_url":             p.get("thumbNail") or p.get("fullImage"),
        "chain_slug":            "colruyt_be",
        "captured_at":           datetime.now().isoformat(),
    }


def api_cek(place_id: str, category_id: str, skip: int) -> Optional[dict]:
    params = {
        "placeId":    place_id,
        "categoryId": category_id,
        "size":       str(PAGE_SIZE),
        "skip":       str(skip),
        "isAvailable":"true",
    }
    for deneme in range(3):
        try:
            r = requests.get(API_BASE, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 456):
                bekleme = 90 + random.uniform(0, 30)
                log(f"  {r.status_code} rate limit — {bekleme:.0f} sn bekleniyor...")
                time.sleep(bekleme)
                continue
            log(f"  HTTP {r.status_code} (cat={category_id}, skip={skip})")
            return None
        except requests.exceptions.RequestException as e:
            log(f"  Bağlantı hatası (deneme {deneme+1}): {e}")
            time.sleep(5 * (deneme + 1))
    return None


def kategori_cek(
    category_id: str,
    place_id: str,
    toplanan: Dict[str, Any],
    *,
    kat_adi: str = "",
) -> int:
    onceki = len(toplanan)
    skip   = 0
    hedef: Optional[int] = None

    while True:
        veri = api_cek(place_id, category_id, skip)
        if veri is None:
            break

        tf = veri.get("totalProductsFound") or veri.get("productsFound")
        if tf is not None and hedef is None:
            try:
                hedef = int(tf)
            except (TypeError, ValueError):
                pass

        urunler = veri.get("products") or []
        if not urunler:
            break

        eklenen = 0
        for u in urunler:
            rpn = u.get("retailProductNumber")
            if rpn and str(rpn) not in toplanan:
                toplanan[str(rpn)] = urun_donustur(u)
                eklenen += 1

        skip += len(urunler)

        if hedef is not None and skip >= hedef:
            break
        if len(urunler) < PAGE_SIZE:
            break

        if skip % 300 == 0:
            etiket = f"{kat_adi} (ID={category_id})" if kat_adi else f"cat={category_id}"
            log(f"    {etiket}: skip={skip}/{hedef}, toplam={len(toplanan)}")

        insan_bekle()

    yeni = len(toplanan) - onceki
    return yeni


def tam_katalog_turu(
    place_id: str,
    toplanan: Dict[str, Any],
) -> int:
    """Kategorisiz düz tarama — kategori bazlı çekimde kaçanları yakalar."""
    log("\n  [tamamlama turu] Kategorisiz düz API taraması başlıyor...")
    onceki = len(toplanan)
    skip   = 0

    while True:
        params = {
            "placeId":    place_id,
            "size":       str(PAGE_SIZE),
            "skip":       str(skip),
            "isAvailable":"true",
        }
        try:
            r = requests.get(API_BASE, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 429:
                time.sleep(60)
                continue
            if r.status_code != 200:
                break
            veri = r.json()
        except Exception as e:
            log(f"  Hata: {e}")
            break

        urunler = veri.get("products") or []
        if not urunler:
            break

        yeni_bu_tur = 0
        for u in urunler:
            rpn = u.get("retailProductNumber")
            if rpn and str(rpn) not in toplanan:
                toplanan[str(rpn)] = urun_donustur(u)
                yeni_bu_tur += 1

        skip += len(urunler)

        if yeni_bu_tur == 0:
            log(f"  Tamamlama turu: skip={skip}, yeni ürün yok — dur.")
            break

        if skip % 500 == 0:
            log(f"  Tamamlama: skip={skip}, toplam={len(toplanan)}")

        if len(urunler) < PAGE_SIZE:
            break

        insan_bekle()

    eklenen = len(toplanan) - onceki
    log(f"  Tamamlama turu bitti. Yeni: {eklenen}")
    return eklenen


# ── Ana fonksiyon ────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Colruyt BE — direkt API çekici (Playwright yok)")
    ap.add_argument("--place-id",  default=PLACE_ID,      help=f"Mağaza ID (varsayılan: {PLACE_ID}=Gent)")
    ap.add_argument("--test",      action="store_true",   help="Sadece ilk 3 kategori (hızlı test)")
    ap.add_argument("--no-pause",  action="store_true",   help="Sonunda Enter bekleme")
    args = ap.parse_args()

    os.makedirs(CIKTI_DIR, exist_ok=True)
    place_id  = args.place_id
    kategoriler = KATEGORILER[:3] if args.test else KATEGORILER

    # curl.txt / cookie.txt'ten Cookie yükle (categoryId filtresi için gerekli)
    cookie = _cookie_from_curl(SCRIPT_DIR)
    if cookie:
        HEADERS["Cookie"] = cookie
        log("  curl.txt/cookie.txt Cookie yüklendi (categoryId filtresi aktif)")
    else:
        log("  UYARI: curl.txt/cookie.txt yok — categoryId filtresi çalışmayabilir")

    log("=" * 60)
    log("Colruyt BE — Kategori Bazlı API Çekici (Playwright yok)")
    log(f"placeId={place_id}  pageSize={PAGE_SIZE}  kategoriler={len(kategoriler)}")
    log("=" * 60)

    toplanan: Dict[str, Any] = {}
    baslangic = time.time()

    for i, (cat_id, cat_adi) in enumerate(kategoriler, 1):
        log(f"\n[{i}/{len(kategoriler)}] {cat_adi} (ID={cat_id}) — şu an {len(toplanan)} ürün")
        yeni = kategori_cek(cat_id, place_id, toplanan, kat_adi=cat_adi)
        log(f"  -> +{yeni} yeni ürün (toplam: {len(toplanan)})")

        # Ara kayıt (her kategoriden sonra)
        if not args.test:
            ara_dosya = os.path.join(CIKTI_DIR, "colruyt_ara_kayit.json")
            with open(ara_dosya, "w", encoding="utf-8") as f:
                json.dump({"urunler": list(toplanan.values()), "urun_sayisi": len(toplanan)},
                          f, ensure_ascii=False)

        insan_bekle()

    # Tamamlama turu
    if not args.test:
        tam_katalog_turu(place_id, toplanan)

    # Final kayıt
    urunler    = list(toplanan.values())
    promo_say  = sum(1 for u in urunler if u.get("inPromo"))
    sure_dk    = round((time.time() - baslangic) / 60, 1)
    tarih      = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya      = os.path.join(CIKTI_DIR, f"colruyt_be_producten_{tarih}.json")

    cikti = {
        "kaynak":         "Colruyt Belçika",
        "chain_slug":     "colruyt_be",
        "country_code":   "BE",
        "yontem":         "Direkt API (requests, Playwright yok)",
        "placeId":        place_id,
        "cekilme_tarihi": datetime.now().isoformat(),
        "sure_dakika":    sure_dk,
        "urun_sayisi":    len(urunler),
        "promo_sayisi":   promo_say,
        "urunler":        urunler,
    }

    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    log("\n" + "=" * 60)
    log(f"TAMAMLANDI!")
    log(f"  Toplam ürün : {len(urunler)}")
    log(f"  Promo ürün  : {promo_say}")
    log(f"  Süre        : {sure_dk} dakika")
    log(f"  Dosya       : {dosya}")
    log("=" * 60)
    log(f"\nSonraki adım: python json_to_supabase_yukle.py --no-pause \"{dosya}\"")

    if not args.no_pause:
        input("\nÇıkmak için Enter...")


if __name__ == "__main__":
    main()
