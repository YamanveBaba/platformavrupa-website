# -*- coding: utf-8 -*-
"""
Colruyt Belçika — Tam Katalog Çekici
======================================
Tarayıcısız, async, fiyat geçmişli Colruyt scraper.

Özellikler:
  - facets.categoryTree → tek API çağrısıyla tüm leaf kategoriler
  - categoryIds (çoğul) parametresi → gerçek kategori filtresi
  - aiohttp async + max 5 paralel istek
  - Fiyat değişimi takibi
  - Kaldığı yerden devam (progress.json)

KULLANIM:
  python colruyt_tam_cekici.py                  # tam çekim, detay yok
  python colruyt_tam_cekici.py --detay           # ürün açıklaması + tüm resimler
  python colruyt_tam_cekici.py --otomatik        # cookie sormadan (Task Scheduler)
  python colruyt_tam_cekici.py --no-pause        # Enter bekleme
  python colruyt_tam_cekici.py --probe           # sadece kategori ağacını göster
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiohttp
except ImportError:
    print("HATA: pip install aiohttp")
    sys.exit(1)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Sabitler ────────────────────────────────────────────────────────────────
API_BASE   = ("https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc"
              "/cg/nl/api/product-search-prs")
DETAIL_URL = ("https://www.colruyt.be/content/clp/nl/producten/product-detail"
              "/jcr:content/root/responsivegrid/product_detail.model.{}.json")
API_KEY    = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
PLACE_ID   = "604"
PAGE_SIZE  = 100
MAX_PARALLEL = 2

SCRIPT_DIR = Path(__file__).parent
CIKTI_DIR  = SCRIPT_DIR / "cikti"

def _headers(cookie: str) -> dict:
    return {
        "x-cg-apikey":    API_KEY,
        "cookie":         cookie,
        "user-agent":     ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/148.0.0.0 Safari/537.36"),
        "origin":         "https://www.colruyt.be",
        "referer":        "https://www.colruyt.be/",
        "accept":         "*/*",
        "accept-language":"nl-BE,nl;q=0.9",
        "accept-encoding":"gzip, deflate, br",
    }

def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Cookie Yönetimi ─────────────────────────────────────────────────────────

def cookie_yukle(script_dir: Path, *, otomatik: bool = False) -> str:
    cookie_dosya = script_dir / "cookie.txt"

    if cookie_dosya.exists():
        with open(cookie_dosya, encoding="utf-8", errors="ignore") as f:
            mevcut = f.read().strip().split("\n")[0].strip()
        if mevcut.lower().startswith("cookie:"):
            mevcut = mevcut[7:].strip()
        if mevcut:
            if otomatik:
                return mevcut
            cevap = input("Kayıtlı cookie bulundu. Kullanılsın mı? (E/H): ").strip().upper()
            if cevap != "H":
                return mevcut

    if otomatik:
        _log("UYARI: cookie.txt yok ve --otomatik modda. colruyt_cookie_gerekli.txt yazılıyor.")
        with open(script_dir / "colruyt_cookie_gerekli.txt", "a", encoding="utf-8") as f:
            f.write(f"Tarih: {date.today()} - Cookie yenilenmesi gerekiyor\n")
        return ""

    print("\nColruyt.be sitesini Chrome'da aç > F12 > Network > sayfayı yenile >")
    print("sol listede herhangi bir isteğe tıkla > Request Headers > cookie: satırını kopyala > buraya yapıştır:")
    try:
        cookie = input("Cookie: ").strip()
    except EOFError:
        cookie = ""

    if cookie:
        if cookie.lower().startswith("cookie:"):
            cookie = cookie[7:].strip()
        with open(cookie_dosya, "w", encoding="utf-8") as f:
            f.write(cookie)
        _log("Cookie cookie.txt dosyasına kaydedildi.")

    return cookie


def cookie_yenile(script_dir: Path, *, otomatik: bool) -> str:
    """403 alınınca çağrılır."""
    if otomatik:
        with open(script_dir / "colruyt_cookie_gerekli.txt", "a", encoding="utf-8") as f:
            f.write(f"Tarih: {date.today()} - 403 hatası, cookie yenilenmesi gerekiyor\n")
        _log("403: colruyt_cookie_gerekli.txt güncellendi.")
        return ""
    _log("403 alındı — cookie geçersiz. Yeni cookie girin:")
    cookie_dosya = script_dir / "cookie.txt"
    if cookie_dosya.exists():
        cookie_dosya.unlink()
    return cookie_yukle(script_dir, otomatik=False)


# ── Kategori Ağacı ──────────────────────────────────────────────────────────

def _leaf_idleri_cek(node_list: list, sonuc: list) -> None:
    """facets.categoryTree'yi recursive tarar, leaf node ID'lerini toplar."""
    for node in node_list:
        cocuklar = node.get("children") or []
        if not cocuklar:
            nid = str(node.get("id") or "")
            if nid:
                sonuc.append(nid)
        else:
            _leaf_idleri_cek(cocuklar, sonuc)


LEAF_CACHE = SCRIPT_DIR / "colruyt_leaf_kategoriler.json"

async def kategori_agaci_cek(session: aiohttp.ClientSession, cookie: str) -> List[str]:
    """
    Tüm leaf kategori ID'lerini API'nin facets.categoryTree'sinden çeker.
    Sonucu colruyt_leaf_kategoriler.json'a kaydeder — bir sonraki çalışmada tekrar çekmez.
    """
    # Cache varsa direkt yükle
    if LEAF_CACHE.exists():
        with open(LEAF_CACHE, encoding="utf-8") as f:
            leafler = json.load(f)
        _log(f"  Kategori cache'den yüklendi: {len(leafler)} leaf ID")
        return leafler

    kok_listesi = [
        ("1675", "Groenten en fruit"),
        ("65",   "Zuivel"),
        ("105",  "Vleeswaren"),
        ("124",  "Brood & ontbijt"),
        ("129",  "Diepvries"),
        ("188",  "Dranken"),
        ("233",  "Conserven"),
        ("306",  "Baby"),
        ("335",  "Chips & borrelhapjes"),
        ("347",  "Koeken, chocolade, snoep"),
        ("354",  "Kruidenierswaren"),
        ("421",  "Sauzen & kruiden"),
        ("591",  "Lichaamsverzorging"),
        ("628",  "Onderhoud & huishouden"),
        ("670",  "Huisdieren"),
        ("693",  "Huishoudartikelen"),
        ("761",  "Wijn"),
        ("33",   "Gezondheid"),
        ("308",  "Niet voeding"),
    ]

    tum_leafler: List[str] = []
    goruldu: set = set()

    for i, (kok_id, kok_adi) in enumerate(kok_listesi, 1):
        params = {
            "placeId":     PLACE_ID,
            "size":        "1",
            "sort":        "relevancy+asc",
            "isAvailable": "true",
            "skip":        "0",
            "categoryIds": kok_id,
        }
        veri = None
        for deneme in range(4):
            try:
                async with session.get(
                    API_BASE, params=params,
                    headers=_headers(cookie),
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as r:
                    if r.status == 200:
                        veri = await r.json(content_type=None)
                        break
                    elif r.status in (429, 456):
                        bekle = 60 + deneme * 30
                        _log(f"  [{i}/{len(kok_listesi)}] {kok_adi}: {r.status} — {bekle}sn bekleniyor...")
                        await asyncio.sleep(bekle)
                    else:
                        _log(f"  [{i}/{len(kok_listesi)}] {kok_adi}: HTTP {r.status}")
                        break
            except Exception as e:
                _log(f"  [{i}/{len(kok_listesi)}] {kok_adi} hatası: {e}")
                await asyncio.sleep(10)

        if veri:
            facets = veri.get("facets") or {}
            tree = facets.get("categoryTree") or []
            leafler: List[str] = []
            if tree:
                _leaf_idleri_cek(tree, leafler)
            else:
                leafler = [kok_id]
            yeni = 0
            for lid in leafler:
                if lid not in goruldu:
                    goruldu.add(lid)
                    tum_leafler.append(lid)
                    yeni += 1
            _log(f"  [{i}/{len(kok_listesi)}] {kok_adi}: {yeni} leaf ID")
        else:
            _log(f"  [{i}/{len(kok_listesi)}] {kok_adi}: ATLANDI")

        # Kategoriler arası uzun bekleme
        await asyncio.sleep(random.uniform(5.0, 10.0))

    # Cache'e kaydet
    with open(LEAF_CACHE, "w", encoding="utf-8") as f:
        json.dump(tum_leafler, f)
    _log(f"  Toplam {len(tum_leafler)} leaf ID colruyt_leaf_kategoriler.json'a kaydedildi")

    return tum_leafler


# ── Ürün Dönüşümü ────────────────────────────────────────────────────────────

def urun_donustur(p: dict) -> dict:
    pr = p.get("price") or {}
    promos = p.get("promotion") or []
    promo0 = promos[0] if promos else {}
    return {
        # Kimlik
        "technicalArticleNumber": p.get("technicalArticleNumber"),
        "retailProductNumber":    p.get("retailProductNumber"),
        # İsim
        "name":      p.get("name") or "",
        "LongName":  p.get("LongName") or p.get("fullName") or p.get("name") or "",
        "ShortName": p.get("ShortName") or "",
        # Marka
        "brand":     p.get("brand") or p.get("seoBrand") or "",
        "seoBrand":  p.get("seoBrand") or "",
        # İçerik
        "content":   p.get("content") or "",
        # Fiyat (spec alanları)
        "normal_fiyat":          pr.get("basicPrice"),
        "birim_fiyat":           pr.get("measurementUnitPrice") or pr.get("pricePerUOM"),
        "birim":                 pr.get("measurementUnit"),
        "miktar_indirim_fiyat":  pr.get("quantityPrice"),
        "miktar_indirim_adet":   pr.get("quantityPriceQuantity"),
        "kirmizi_fiyat":         pr.get("isRedPrice", False),
        "promo_aktif":           pr.get("isPromoActive", "N"),
        "promoda_mi":            bool(p.get("inPromo") or pr.get("isPromoActive") == "Y"),
        # Promo tarihleri
        "promo_baslangic":       promo0.get("publicationStartDate"),
        "promo_bitis":           promo0.get("publicationEndDate"),
        # json_to_supabase_yukle.py uyumluluğu (mevcut field isimleri)
        "basicPrice":            pr.get("basicPrice"),
        "pricePerUOM":           pr.get("measurementUnitPrice") or pr.get("pricePerUOM"),
        "measurementUnit":       pr.get("measurementUnit"),
        "quantityPrice":         pr.get("quantityPrice"),
        "quantityPriceQuantity": pr.get("quantityPriceQuantity"),
        "inPromo":               bool(p.get("inPromo")),
        "promoPublicationStart": promo0.get("publicationStartDate"),
        "promoPublicationEnd":   promo0.get("publicationEndDate"),
        # Resim
        "kucuk_resim_url": p.get("thumbNail") or "",
        "buyuk_resim_url": p.get("fullImage") or "",
        "image_url":       p.get("thumbNail") or p.get("fullImage") or "",
        # Kategori
        "kategori_adi": p.get("topCategoryName") or "",
        "kategori_id":  p.get("topCategoryId") or "",
        "topCategoryName": p.get("topCategoryName") or "",
        "topCategoryId":   p.get("topCategoryId"),
        # Ek bilgi
        "bio":          p.get("IsBio", False),
        "nutriscore":   p.get("nutriScore"),
        "mensei_ulke":  p.get("countryOfOrigin"),
        "isPriceAvailable": p.get("isPriceAvailable", True),
        "isAvailable":      p.get("isAvailable", True),
    }


# ── Async Ürün Çekimi ────────────────────────────────────────────────────────

istek_sayaci = 0

async def kategori_urunlerini_cek(
    session: aiohttp.ClientSession,
    category_id: str,
    cookie: str,
    semaphore: asyncio.Semaphore,
    script_dir: Path,
    *,
    otomatik: bool,
) -> List[dict]:
    global istek_sayaci

    urunler: Dict[str, dict] = {}
    skip = 0
    hedef: Optional[int] = None
    retry_cookie = cookie

    async with semaphore:
        while True:
            params = {
                "placeId":     PLACE_ID,
                "categoryIds": category_id,
                "size":        str(PAGE_SIZE),
                "skip":        str(skip),
                "sort":        "relevancy+asc",
                "isAvailable": "true",
            }

            # Rate limiter
            istek_sayaci += 1
            if istek_sayaci % 30 == 0:
                await asyncio.sleep(15)
            else:
                await asyncio.sleep(random.uniform(3.0, 7.0))

            # İstek
            veri = None
            for deneme in range(3):
                try:
                    async with session.get(
                        API_BASE, params=params,
                        headers=_headers(retry_cookie),
                        timeout=aiohttp.ClientTimeout(total=25),
                    ) as r:
                        if r.status == 200:
                            veri = await r.json(content_type=None)
                            break
                        elif r.status == 429:
                            _log(f"  429 rate limit (cat={category_id}) — 60 sn bekleniyor...")
                            await asyncio.sleep(60)
                            continue
                        elif r.status == 403:
                            retry_cookie = cookie_yenile(script_dir, otomatik=otomatik)
                            if not retry_cookie:
                                return list(urunler.values())
                            continue
                        elif r.status >= 500:
                            _log(f"  {r.status} (cat={category_id}, deneme {deneme+1}/3)")
                            await asyncio.sleep(30)
                            continue
                        elif r.status == 456:
                            _log(f"  456 rate limit (cat={category_id}) — 90 sn bekleniyor...")
                            await asyncio.sleep(90)
                            continue
                        else:
                            _log(f"  HTTP {r.status} (cat={category_id}) — atlanıyor")
                            with open(script_dir / "errors.log", "a", encoding="utf-8") as f:
                                f.write(f"{datetime.now().isoformat()} cat={category_id} HTTP {r.status}\n")
                            return list(urunler.values())
                except Exception as e:
                    _log(f"  Bağlantı hatası (cat={category_id}, deneme {deneme+1}): {e}")
                    await asyncio.sleep(15)

            if veri is None:
                with open(script_dir / "errors.log", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now().isoformat()} cat={category_id} skip={skip} — 3 denemede başarısız\n")
                break

            # Hedef
            if hedef is None:
                tf = veri.get("totalProductsFound") or veri.get("productsFound")
                if tf:
                    try:
                        hedef = int(tf)
                    except (TypeError, ValueError):
                        pass

            urunler_sayfa = veri.get("products") or []
            if not urunler_sayfa:
                break

            for u in urunler_sayfa:
                rpn = u.get("retailProductNumber")
                if rpn and str(rpn) not in urunler:
                    urunler[str(rpn)] = urun_donustur(u)

            skip += len(urunler_sayfa)

            if hedef is not None and skip >= hedef:
                break
            if len(urunler_sayfa) < PAGE_SIZE:
                break

    return list(urunler.values())


# ── Ürün Detay ───────────────────────────────────────────────────────────────

async def urun_detay_cek(
    session: aiohttp.ClientSession,
    article_number: str,
    cookie: str,
) -> dict:
    url = DETAIL_URL.format(article_number)
    try:
        async with session.get(
            url, headers=_headers(cookie),
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            if r.status != 200:
                return {}
            veri = await r.json(content_type=None)
            return {
                "aciklama":          veri.get("description") or "",
                "tum_resimler":      ",".join(veri.get("imageList") or []),
                "kategori_agaci":    json.dumps(veri.get("categories") or [], ensure_ascii=False),
                "besin_degerleri_url": veri.get("ficUrl") or "",
            }
    except Exception:
        return {}


# ── Fiyat Geçmişi ────────────────────────────────────────────────────────────

def fiyat_guncelle(
    urun: dict,
    eski_urunler: Dict[str, dict],
    price_history: Dict[str, list],
    price_changes: Dict[str, dict],
    bugun: str,
) -> Optional[dict]:
    """Fiyat değiştiyse change dict döner, yoksa None."""
    rpn = str(urun.get("retailProductNumber") or urun.get("technicalArticleNumber") or "")
    if not rpn:
        return None

    yeni_fiyat = urun.get("normal_fiyat")
    if yeni_fiyat is None:
        return None

    # Geçmiş kaydı ekle
    kayit = {
        "tarih":                 bugun,
        "normal_fiyat":          yeni_fiyat,
        "birim_fiyat":           urun.get("birim_fiyat"),
        "birim":                 urun.get("birim"),
        "miktar_indirim_fiyat":  urun.get("miktar_indirim_fiyat"),
        "miktar_indirim_adet":   urun.get("miktar_indirim_adet"),
        "kirmizi_fiyat":         urun.get("kirmizi_fiyat", False),
        "promoda_mi":            urun.get("promoda_mi", False),
    }
    if rpn not in price_history:
        price_history[rpn] = []
    price_history[rpn].append(kayit)

    # Fiyat değişimi kontrolü
    eski = eski_urunler.get(rpn)
    if not eski:
        return None

    eski_fiyat = eski.get("normal_fiyat")
    if eski_fiyat is None or abs(float(eski_fiyat) - float(yeni_fiyat)) < 0.001:
        return None

    pct = ((float(yeni_fiyat) - float(eski_fiyat)) / float(eski_fiyat)) * 100
    pct_str = f"{'+' if pct >= 0 else ''}{pct:.1f}%"
    urun_adi = urun.get("name") or urun.get("LongName") or rpn

    degisim = {
        "tarih":           bugun,
        "eski_fiyat":      float(eski_fiyat),
        "yeni_fiyat":      float(yeni_fiyat),
        "degisim_yuzde":   pct_str,
    }

    if rpn not in price_changes:
        price_changes[rpn] = {
            "urun_adi":            urun_adi,
            "son_degisim_tarihi":  bugun,
            "degisimler":          [],
        }
    price_changes[rpn]["son_degisim_tarihi"] = bugun
    price_changes[rpn]["degisimler"].append(degisim)

    arrow = "↑" if pct >= 0 else "↓"
    _log(f"  Fiyat değişimi: {urun_adi[:50]} → €{eski_fiyat:.2f} → €{yeni_fiyat:.2f} ({pct_str}) {arrow}")

    return {
        "article_number": rpn,
        "urun_adi":        urun_adi,
        "eski_fiyat":      float(eski_fiyat),
        "yeni_fiyat":      float(yeni_fiyat),
        "degisim_yuzde":   pct_str,
        "tarih":           bugun,
    }


# ── Çıktı Dosyaları ──────────────────────────────────────────────────────────

def cikti_kaydet(
    urunler: List[dict],
    price_history: Dict[str, list],
    price_changes: Dict[str, dict],
    degisen_bugun: List[dict],
    script_dir: Path,
    bugun: str,
    sure_sn: float,
) -> None:
    CIKTI_DIR.mkdir(parents=True, exist_ok=True)

    # 1. products_latest.json
    with open(script_dir / "products_latest.json", "w", encoding="utf-8") as f:
        json.dump({"tarih": bugun, "urun_sayisi": len(urunler), "urunler": urunler},
                  f, ensure_ascii=False)

    # 2. products_latest.csv (UTF-8 BOM)
    if urunler:
        alanlar = list(urunler[0].keys())
        with open(script_dir / "products_latest.csv", "w", encoding="utf-8-sig",
                  newline="") as f:
            w = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
            w.writeheader()
            w.writerows(urunler)

    # 3. price_history.json (hiç silme)
    ph_dosya = script_dir / "price_history.json"
    if ph_dosya.exists():
        with open(ph_dosya, encoding="utf-8") as f:
            mevcut_ph = json.load(f)
        for rpn, kayitlar in price_history.items():
            if rpn not in mevcut_ph:
                mevcut_ph[rpn] = []
            mevcut_ph[rpn].extend(kayitlar)
        price_history = mevcut_ph
    with open(ph_dosya, "w", encoding="utf-8") as f:
        json.dump(price_history, f, ensure_ascii=False)

    # 4. price_changes.json
    with open(script_dir / "price_changes.json", "w", encoding="utf-8") as f:
        json.dump(price_changes, f, ensure_ascii=False, indent=2)

    # 5. price_changes_YYYY-MM-DD.csv
    if degisen_bugun:
        pc_dosya = script_dir / f"price_changes_{bugun}.csv"
        with open(pc_dosya, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["article_number", "urun_adi",
                               "eski_fiyat", "yeni_fiyat", "degisim_yuzde", "tarih"])
            w.writeheader()
            w.writerows(degisen_bugun)

    # 6. cikti/colruyt_be_producten_*.json (mevcut pipeline uyumlu)
    tarih_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    cikti_dosya = CIKTI_DIR / f"colruyt_be_producten_{tarih_str}.json"
    promo_say = sum(1 for u in urunler if u.get("promoda_mi"))
    with open(cikti_dosya, "w", encoding="utf-8") as f:
        json.dump({
            "kaynak":         "Colruyt Belçika",
            "chain_slug":     "colruyt_be",
            "country_code":   "BE",
            "yontem":         "Direkt API async (categoryIds + facets.categoryTree)",
            "placeId":        PLACE_ID,
            "cekilme_tarihi": datetime.now().isoformat(),
            "sure_dakika":    round(sure_sn / 60, 1),
            "urun_sayisi":    len(urunler),
            "promo_sayisi":   promo_say,
            "urunler":        urunler,
        }, f, ensure_ascii=False, indent=2)

    _log(f"  → {cikti_dosya.name}")


# ── Windows Task Scheduler ───────────────────────────────────────────────────

def task_scheduler_ekle(script_path: Path) -> None:
    try:
        cevap = input("\nHer gün saat 08:00'de otomatik çalışsın mı? (E/H): ").strip().upper()
    except EOFError:
        return
    if cevap != "E":
        return

    py_exe = sys.executable
    task_cmd = (
        f'$action = New-ScheduledTaskAction -Execute "{py_exe}" '
        f'-Argument "{script_path} --otomatik --no-pause"; '
        f'$trigger = New-ScheduledTaskTrigger -Daily -At 08:00; '
        f'$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable; '
        f'Register-ScheduledTask -TaskName "ColruytFiyatCekici" '
        f'-Action $action -Trigger $trigger -Settings $settings -Force'
    )
    try:
        result = subprocess.run(
            ["powershell", "-Command", task_cmd],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            _log("✓ Windows Task Scheduler'a eklendi (her gün 08:00).")
        else:
            _log(f"Task Scheduler hatası: {result.stderr[:200]}")
    except Exception as e:
        _log(f"Task Scheduler eklenemedi: {e}")


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────────

async def ana(args: argparse.Namespace) -> None:
    bugun = date.today().isoformat()
    baslangic = time.time()
    global istek_sayaci
    istek_sayaci = 0

    # Cookie
    cookie = cookie_yukle(SCRIPT_DIR, otomatik=args.otomatik)
    if not cookie:
        _log("Cookie alınamadı. Çıkılıyor.")
        return

    # Önceki ürünleri yükle (fiyat karşılaştırması için)
    eski_urunler: Dict[str, dict] = {}
    pl_dosya = SCRIPT_DIR / "products_latest.json"
    if pl_dosya.exists():
        try:
            with open(pl_dosya, encoding="utf-8") as f:
                pl = json.load(f)
            for u in (pl.get("urunler") or []):
                rpn = str(u.get("retailProductNumber") or u.get("technicalArticleNumber") or "")
                if rpn:
                    eski_urunler[rpn] = u
            _log(f"Önceki veri: {len(eski_urunler)} ürün yüklendi (fiyat karşılaştırması için)")
        except Exception:
            pass

    # Progress (kaldığı yerden devam)
    progress_dosya = SCRIPT_DIR / "progress.json"
    tamamlanan_kategoriler: set = set()
    tum_urunler: Dict[str, dict] = {}
    if progress_dosya.exists() and not args.sifirla:
        try:
            with open(progress_dosya, encoding="utf-8") as f:
                prog = json.load(f)
            tamamlanan_kategoriler = set(prog.get("tamamlanan", []))
            for u in (prog.get("urunler") or []):
                rpn = str(u.get("retailProductNumber") or "")
                if rpn:
                    tum_urunler[rpn] = u
            _log(f"Checkpoint: {len(tamamlanan_kategoriler)} kategori tamamlanmış, {len(tum_urunler)} ürün mevcut")
        except Exception:
            pass

    price_history: Dict[str, list] = {}
    price_changes: Dict[str, dict] = {}
    degisen_bugun: List[dict] = []

    connector = aiohttp.TCPConnector(limit=MAX_PARALLEL, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Kategori ağacını çek
        _log("Kategori ağacı çekiliyor (facets.categoryTree)...")
        leaf_idler = await kategori_agaci_cek(session, cookie)
        _log(f"Toplam {len(leaf_idler)} leaf kategori bulundu.")

        if args.probe:
            print("\n─── Leaf Kategori ID'leri ───")
            for lid in leaf_idler:
                print(f"  {lid}")
            return

        # Bekleyen kategoriler
        bekleyen = [cid for cid in leaf_idler if cid not in tamamlanan_kategoriler]
        _log(f"İşlenecek: {len(bekleyen)} kategori "
             f"(tamamlanan: {len(tamamlanan_kategoriler)})")

        semaphore = asyncio.Semaphore(MAX_PARALLEL)
        toplam_kat = len(bekleyen)
        tahmini_toplam = 12000  # başlangıç tahmini
        baslangic_urun_sayi = len(tum_urunler)

        for i, category_id in enumerate(bekleyen, 1):
            t0 = time.time()
            urunler_kat = await kategori_urunlerini_cek(
                session, category_id, cookie, semaphore, SCRIPT_DIR,
                otomatik=args.otomatik,
            )

            yeni = 0
            for u in urunler_kat:
                rpn = str(u.get("retailProductNumber") or "")
                if rpn and rpn not in tum_urunler:
                    tum_urunler[rpn] = u
                    yeni += 1
                    # Fiyat güncelle
                    degisim = fiyat_guncelle(
                        u, eski_urunler, price_history, price_changes, bugun
                    )
                    if degisim:
                        degisen_bugun.append(degisim)

            sure_kat = time.time() - t0
            gecen = time.time() - baslangic
            mevcut_hiz = (len(tum_urunler) - baslangic_urun_sayi) / max(gecen, 1)
            kalan_urun  = max(0, tahmini_toplam - len(tum_urunler))
            tahmini_kal = int(kalan_urun / max(mevcut_hiz, 0.1))
            pct = min(100, (len(tum_urunler) / tahmini_toplam) * 100)

            _log(f"Kategori {i}/{toplam_kat} (ID={category_id}): "
                 f"+{yeni} ürün | Toplam: {len(tum_urunler)} ({pct:.1f}%) "
                 f"| Hız: {mevcut_hiz:.1f}/sn | Kalan: ~{tahmini_kal//60}dk")

            # Tamamlanan kategorileri kaydet
            tamamlanan_kategoriler.add(category_id)

            # Her 10 kategoride progress kaydet
            if i % 10 == 0:
                with open(progress_dosya, "w", encoding="utf-8") as f:
                    json.dump({
                        "tamamlanan": list(tamamlanan_kategoriler),
                        "urunler":    list(tum_urunler.values()),
                    }, f, ensure_ascii=False)

        # Detay çekimi (--detay ile)
        if args.detay:
            _log(f"\nÜrün detayları çekiliyor ({len(tum_urunler)} ürün)...")
            detay_sem = asyncio.Semaphore(3)
            detay_sayac = 0

            async def detay_isle(rpn: str, u: dict) -> None:
                nonlocal detay_sayac
                async with detay_sem:
                    art_no = u.get("technicalArticleNumber") or rpn
                    detay = await urun_detay_cek(session, str(art_no), cookie)
                    u.update(detay)
                    detay_sayac += 1
                    if detay_sayac % 100 == 0:
                        _log(f"  Detay: {detay_sayac}/{len(tum_urunler)}")
                    await asyncio.sleep(random.uniform(0.5, 1.5))

            await asyncio.gather(*[
                detay_isle(rpn, u) for rpn, u in tum_urunler.items()
            ])

    # Kaydet
    sure_sn = time.time() - baslangic
    urunler = list(tum_urunler.values())
    promo_say = sum(1 for u in urunler if u.get("promoda_mi"))
    degisen_say = len(degisen_bugun)

    _log("\nKaydediliyor...")
    cikti_kaydet(
        urunler, price_history, price_changes, degisen_bugun,
        SCRIPT_DIR, bugun, sure_sn,
    )

    # Progress sil (başarılı bitiş)
    if progress_dosya.exists():
        progress_dosya.unlink()

    # Özet
    sure_dk = int(sure_sn // 60)
    sure_sn_kalan = int(sure_sn % 60)
    print(f"\n{'='*50}")
    print(f"✓ TAMAMLANDI")
    print(f"✓ Toplam ürün: {len(urunler):,}")
    print(f"✓ Fiyat değişimi tespit edilen: {degisen_say} ürün")
    print(f"✓ Promo ürün: {promo_say}")
    print(f"✓ Hata: (errors.log)")
    print(f"✓ Süre: {sure_dk} dakika {sure_sn_kalan} saniye")
    print(f"{'='*50}\n")

    # Task Scheduler
    if not args.otomatik and not args.no_pause:
        task_scheduler_ekle(Path(__file__).resolve())
        input("\nÇıkmak için Enter...")
    elif not args.otomatik and args.no_pause:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Colruyt BE — tam katalog çekici (async)")
    ap.add_argument("--detay",     action="store_true", help="Ürün açıklaması + tüm resimler (yavaş)")
    ap.add_argument("--otomatik",  action="store_true", help="Cookie sormadan çalış (Task Scheduler)")
    ap.add_argument("--no-pause",  action="store_true", help="Sonunda Enter bekleme")
    ap.add_argument("--probe",     action="store_true", help="Sadece kategori ağacını göster")
    ap.add_argument("--sifirla",   action="store_true", help="progress.json'u sil, baştan başla")
    args = ap.parse_args()

    asyncio.run(ana(args))


if __name__ == "__main__":
    main()
