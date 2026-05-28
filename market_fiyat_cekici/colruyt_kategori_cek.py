# -*- coding: utf-8 -*-
"""
Colruyt Belçika — KATEGORİ BAZLI tam ürün + fiyat + indirim tarihi çekici
==========================================================================
NEDEN YENİ SCRIPT?
  Eski script placeId+skip ile düz sayfalama yapıyordu.
  Colruyt API'si skip~7500'de susuyor -> 7548 üründe takılı kalıyorduk.
  Çözüm: Her kategoriyi ayrı ayrı sayfalamak (her biri <1000 ürün,
  pagination tavanına asla çarpmaz). 12.000+ ürün hedefi bu şekilde
  tutarlı şekilde ulaşılabilir.

ÇALIŞMA MANTIĞI
  1. Playwright ile kalıcı profil açılır (colruyt_browser_profile/).
  2. colruyt.be/nl/producten sayfası açılır; kategori linkleri toplanır.
  3. Her kategori linki ziyaret edilerek ağ trafiği dinlenir -> categoryId'ler
     otomatik keşfedilir (elle cURL kopyasına gerek yok).
  4. Her categoryId için API sayfalanır (skip=0,60,120,...).
  5. Tüm sonuçlar retailProductNumber ile birleştirilir (deduplicate).
  6. Mevcut json_to_supabase_yukle.py ile uyumlu JSON kaydedilir.

KULLANIM
  İlk çalıştırma (profilde oturum yok):
      python colruyt_kategori_cek.py --enter-sonra-devam
      (Tarayıcı açılır, giriş yap + mağaza seç, Enter'a bas -> devam)

  Sonraki çalıştırmalar (profilde oturum var):
      python colruyt_kategori_cek.py --zaten-giris

  Sadece keşif testi (ürün çekmeden):
      python colruyt_kategori_cek.py --zaten-giris --sadece-kesif

  Belirli kategori sayısı (test):
      python colruyt_kategori_cek.py --zaten-giris --max-kategori 3
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# ---------------------------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------------------------
PLACE_ID = "710"          # Gent Colruyt — değiştirmek istersen komut satırından: --place-id XXX
API_BASE = (
    "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc"
    "/cg/nl/api/product-search-prs"
)


def _auth_oku() -> tuple[str, str]:
    """colruyt_auth.txt'den API key ve cookie okur. Dosya yoksa hardcoded fallback kullanır."""
    auth_path = Path(__file__).parent.parent / "colruyt_auth.txt"
    key = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
    cookie = ""
    if auth_path.exists():
        try:
            for line in open(auth_path, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line.startswith("KEY=") and not line.startswith("#"):
                    v = line[4:].strip()
                    if v:
                        key = v
                elif line.startswith("COOKIE=") and not line.startswith("#"):
                    v = line[7:].strip()
                    if v:
                        cookie = v
        except Exception:
            pass
    return key, cookie


API_KEY, _AUTH_COOKIE = _auth_oku()

# 406/401 hata sayacı — 3 ardışık geçersiz auth → tüm çekim durdurulur
_HATA_406_SAYACI = 0
PAGE_SIZE = 60            # Kategori sorgusu için (20-60 arası API kabul eder)
MAX_URUN = 20000          # Güvenlik tavanı
SITE_URL = "https://www.colruyt.be/nl/producten"

# İnsan benzeri bekleme süreleri (saniye)
DELAY_SAYFA = (4.0, 9.0)       # Kategori sayfaları arası
DELAY_API = (0.5, 1.4)         # API istekleri arası
DELAY_YAVAS = (8.0, 18.0)      # Ara sıra yavaşla (%10)
DELAY_MOLA = (30.0, 70.0)      # Nadiren uzun mola (%3)


# ---------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------------------------

def insan_bekle(neden: str = "api") -> None:
    r = random.random()
    if r < 0.03:
        sure = random.uniform(*DELAY_MOLA)
        print(f"  [mola {neden}] {sure:.0f} sn...")
        time.sleep(sure)
    elif r < 0.13:
        sure = random.uniform(*DELAY_YAVAS)
        time.sleep(sure)
    elif neden == "sayfa":
        time.sleep(random.uniform(*DELAY_SAYFA))
    else:
        time.sleep(random.uniform(*DELAY_API))


def api_headers() -> Dict[str, str]:
    return {
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


def kategori_api_url(category_id: str, place_id: str, skip: int = 0) -> str:
    q = {
        "placeId": place_id,
        "categoryId": category_id,
        "size": str(PAGE_SIZE),
        "skip": str(skip),
        "isAvailable": "true",
    }
    return f"{API_BASE}?{urlencode(q)}"


def tam_katalog_url(place_id: str, skip: int = 0) -> str:
    """Kategori ID'siz düz sayfalama (tamamlama turunda kullanılır)."""
    q = {
        "placeId": place_id,
        "size": str(PAGE_SIZE),
        "skip": str(skip),
        "isAvailable": "true",
    }
    return f"{API_BASE}?{urlencode(q)}"


def urun_satirina_donustur(p: dict) -> dict:
    """API ürün objesini platform formatına çevirir."""
    # Fiyat bilgileri "price" sub-objesinde geliyor
    pr = p.get("price") or {}
    # Promo tarihleri "promotion" listesinin ilk elemanında
    promo_list = p.get("promotion") or []
    promo0 = promo_list[0] if promo_list else {}

    return {
        "retailProductNumber": p.get("retailProductNumber"),
        "technicalArticleNumber": p.get("technicalArticleNumber"),
        "name": p.get("name", ""),
        "brand": p.get("brand", "") or p.get("seoBrand", ""),
        "LongName": p.get("fullName") or p.get("LongName") or p.get("name", ""),
        "content": p.get("content", ""),
        "basicPrice": pr.get("basicPrice"),
        "quantityPrice": pr.get("quantityPrice"),
        "pricePerUOM": pr.get("pricePerUOM"),
        "measurementUnit": pr.get("measurementUnit"),
        "isRedPrice": pr.get("isRedPrice", False),
        "isPromoActive": pr.get("isPromoActive", "N"),
        "inPromo": bool(pr.get("isPromoActive") == "Y" or p.get("inPromo")),
        "promoPublicationStart": promo0.get("publicationStartDate"),
        "promoPublicationEnd": promo0.get("publicationEndDate"),
        "activationDate": pr.get("activationDate"),
        "topCategoryName": p.get("topCategoryName", ""),
        "topCategoryId": p.get("topCategoryId"),
        "nutriScore": p.get("nutriScore"),
        "countryOfOrigin": p.get("countryOfOrigin"),
        "isPriceAvailable": p.get("isPriceAvailable", True),
        "isAvailable": p.get("isAvailable", True),
        "price": pr.get("basicPrice"),
        "promo_price": pr.get("quantityPrice"),
        "promo_valid_from": promo0.get("publicationStartDate"),
        "promo_valid_until": promo0.get("publicationEndDate"),
        "image_url": (
            p.get("thumbNail") or
            p.get("fullImage") or
            p.get("imageUrl") or
            (
                f"https://static.colruytgroup.com/images/200x200/std.lang.all/"
                f"{p.get('retailProductNumber', '')}.jpg"
                if p.get("retailProductNumber") else None
            )
        ),
    }


def ara_kaydet(path: str, toplanan: Dict[str, Any], hedef: Optional[int] = None) -> None:
    veri = {
        "ara_kayit": True,
        "kaydedilme": datetime.now().isoformat(),
        "urun_sayisi": len(toplanan),
        "hedef": hedef,
        "urunler": list(toplanan.values()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)


# ---------------------------------------------------------------------------
# KATEGORİ KEŞFİ
# ---------------------------------------------------------------------------

def kategori_linklerini_tara(page) -> List[str]:
    """
    /nl/producten sayfasındaki kategori linklerini toplar.
    colruyt.be/nl/producten/XXX formatındaki her link bir kategoridir.
    """
    try:
        linkler = page.evaluate(
            """
            () => {
                const out = new Set();
                document.querySelectorAll('a[href]').forEach(a => {
                    const h = a.href || '';
                    if (h.includes('/nl/producten/') && h.endsWith('.html') === false
                        && !h.includes('?') && !h.includes('#')) {
                        out.add(h.split('?')[0].split('#')[0]);
                    }
                    // .html ile bitenler de olabilir
                    if (h.match(/[/]nl[/]producten[/][^/]+[/]?$/) && !h.includes('?')) {
                        out.add(h.split('?')[0].split('#')[0]);
                    }
                });
                return Array.from(out);
            }
            """
        )
        return [l for l in (linkler or []) if l and "colruyt.be" in l]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# TEMEL ÇEKİM: BİR KATEGORİ
# ---------------------------------------------------------------------------

def kategori_urunlerini_cek(
    context,
    category_id: str,
    place_id: str,
    toplanan: Dict[str, Any],
    *,
    kategori_adi: str = "",
    max_urun: int = MAX_URUN,
) -> int:
    """
    Tek kategori için API'yi sayfalayarak urunleri toplanan dict'e ekler.
    Döner: bu kategori için eklenen yeni ürün sayısı.
    """
    onceki = len(toplanan)
    skip = 0
    bos_sayfa = 0
    sayfa_idx = 0
    hedef: Optional[int] = None

    while len(toplanan) < max_urun:
        url = kategori_api_url(category_id, place_id, skip)
        try:
            resp = context.request.get(url, headers=api_headers(), timeout=60_000)
        except Exception as e:
            print(f"    ağ hatası (skip={skip}): {e}")
            time.sleep(5)
            break

        if resp.status == 429:
            print("    429 — 60 sn bekleniyor...")
            time.sleep(60 + random.uniform(0, 20))
            continue

        if resp.status != 200:
            print(f"    HTTP {resp.status} (categoryId={category_id}, skip={skip}) — atlandı")
            if resp.status in (401, 403, 406):
                global _HATA_406_SAYACI
                _HATA_406_SAYACI += 1
                print(f"    Auth hatası #{_HATA_406_SAYACI}/3 — API key geçersiz olabilir.")
                if _HATA_406_SAYACI >= 3:
                    raise RuntimeError(
                        "DURDURULDU: 3 ardışık auth hatası (401/403/406). "
                        "colruyt_auth.txt'deki API key'i güncelleyin."
                    )
            break

        try:
            veri = resp.json()
        except Exception:
            print(f"    JSON okunamadı (skip={skip})")
            break

        tf = veri.get("totalProductsFound")
        if tf is not None:
            try:
                hedef = max(hedef or 0, int(tf))
            except (TypeError, ValueError):
                pass

        urunler = veri.get("products") or []
        if not urunler:
            bos_sayfa += 1
            if bos_sayfa >= 2:
                break
            time.sleep(1)
            break  # Kategori bitti

        bos_sayfa = 0
        eklenen = 0
        for u in urunler:
            rpn = u.get("retailProductNumber")
            if rpn and str(rpn) not in toplanan:
                toplanan[str(rpn)] = urun_satirina_donustur(u)
                eklenen += 1

        sayfa_idx += 1
        skip += len(urunler)

        if sayfa_idx % 5 == 0:
            etiket = f"[{category_id}] {kategori_adi}" if kategori_adi else f"cat={category_id}"
            print(f"    {etiket}: sayfa {sayfa_idx}, bu tur+{len(toplanan)-onceki}, toplam {len(toplanan)}" +
                  (f" / hedef ~{hedef}" if hedef else ""))

        # Son sayfa kontrolü
        if hedef is not None and skip >= hedef:
            break
        if len(urunler) < PAGE_SIZE:
            break

        insan_bekle("api")

    yeni = len(toplanan) - onceki
    return yeni


# ---------------------------------------------------------------------------
# DÜZELTME TURU: Kategori ID'si olmayan ürünler için düz sayfalama
# ---------------------------------------------------------------------------

def duzeltme_turu(
    context,
    place_id: str,
    toplanan: Dict[str, Any],
    *,
    max_urun: int = MAX_URUN,
) -> int:
    """
    Kategori bazlı çekimde kaçan ürünler için tek tur düz sayfalama.
    Bu tur API'nin tavanına (~7500) çarpabilir; kabul edilebilir.
    """
    print("\n  [düzeltme turu] Kategori dışı ürünler için düz sayfalama başlıyor...")
    onceki = len(toplanan)
    skip = 0
    bos_sayfa = 0
    dur_limit = 4

    while len(toplanan) < max_urun:
        url = tam_katalog_url(place_id, skip)
        try:
            resp = context.request.get(url, headers=api_headers(), timeout=60_000)
        except Exception as e:
            print(f"    ağ hatası: {e}")
            break

        if resp.status == 429:
            time.sleep(60)
            continue
        if resp.status != 200:
            print(f"    HTTP {resp.status} — düzeltme turu durdu")
            break

        try:
            veri = resp.json()
        except Exception:
            break

        urunler = veri.get("products") or []
        if not urunler:
            bos_sayfa += 1
            if bos_sayfa >= dur_limit:
                break
            break

        yeni = 0
        for u in urunler:
            rpn = u.get("retailProductNumber")
            if rpn and str(rpn) not in toplanan:
                toplanan[str(rpn)] = urun_satirina_donustur(u)
                yeni += 1

        skip += len(urunler)
        if yeni == 0:
            bos_sayfa += 1
            if bos_sayfa >= dur_limit:
                print("    Yeni ürün gelmiyor, düzeltme turu tamamlandı.")
                break
        else:
            bos_sayfa = 0

        if skip % 500 == 0:
            print(f"    düzeltme skip={skip}, toplam {len(toplanan)}")

        if len(urunler) < PAGE_SIZE:
            break

        insan_bekle("api")

    eklenen = len(toplanan) - onceki
    print(f"  Düzeltme turu tamamlandı. Yeni eklenen: {eklenen}")
    return eklenen


# ---------------------------------------------------------------------------
# ANA FONKSİYON
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    place_id = args.place_id or PLACE_ID

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    profil_dir = os.path.join(script_dir, "colruyt_browser_profile")
    os.makedirs(profil_dir, exist_ok=True)
    checkpoint_yolu = os.path.join(cikti_dir, "colruyt_checkpoint_arakayit.json")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: playwright yüklü değil.")
        print("Çalıştır: pip install playwright  &&  playwright install chromium")
        return

    print("=" * 60)
    print("Colruyt Belçika — Kategori Bazlı Tam Çekici")
    print(f"placeId={place_id}  pageSize={PAGE_SIZE}")
    print("=" * 60)

    toplanan: Dict[str, Any] = {}
    kesfedilen_kategoriler: List[Dict[str, str]] = []
    agi_yakalanan_kategori_idleri: set = set()
    toplam_baslangic = time.time()

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=profil_dir,
            headless=False,
            locale="nl-BE",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_https_errors=False,
        )

        # ----------------------------------------------------------------
        # Ağ trafiğini dinle: product-search-prs isteklerinden
        # categoryId değerlerini otomatik yakala
        # ----------------------------------------------------------------
        def ag_yanitini_isle(response):
            url = response.url
            if "product-search-prs" not in url:
                return
            if response.status != 200:
                return
            try:
                parsed = urlparse(url)
                q = dict(parse_qsl(parsed.query))
                cid = q.get("categoryId")
                if cid and cid not in agi_yakalanan_kategori_idleri:
                    agi_yakalanan_kategori_idleri.add(cid)
                    # Anlık ürünleri de topla (performans)
                    try:
                        veri = response.json()
                        for u in (veri.get("products") or []):
                            rpn = u.get("retailProductNumber")
                            if rpn and str(rpn) not in toplanan:
                                toplanan[str(rpn)] = urun_satirina_donustur(u)
                    except Exception:
                        pass
            except Exception:
                pass

        page = context.pages[0] if context.pages else context.new_page()
        page.on("response", ag_yanitini_isle)

        # ----------------------------------------------------------------
        # Giriş bekleme
        # ----------------------------------------------------------------
        print(f"\nSayfa açılıyor: {SITE_URL}")
        try:
            page.goto(SITE_URL, wait_until="domcontentloaded", timeout=90_000)
        except Exception as e:
            print(f"Sayfa yüklenemedi: {e}")
            context.close()
            return

        if args.enter_sonra_devam:
            print(
                "\n>>> Colruyt penceresinde GİRİŞ YAP ve MAĞAZAYI SEÇ (Gent)."
                "\n>>> Hazır olunca bu siyah pencereye dönüp ENTER'a bas.\n"
            )
            try:
                input()
            except EOFError:
                pass
        elif args.zaten_giris:
            print("  Profilde oturum var kabul ediliyor; 12 sn bekleniyor...")
            time.sleep(12)
        else:
            print("  300 sn giriş bekleniyor... (--zaten-giris veya --enter-sonra-devam kullanabilirsin)")
            for _ in range(10):
                time.sleep(30)
                print("  ...")

        # ----------------------------------------------------------------
        # 1. AŞAMA: Kategori linklerini topla
        # ----------------------------------------------------------------
        print("\n[1/3] Kategori linkleri toplanıyor...")
        kategori_linkleri = kategori_linklerini_tara(page)
        print(f"  HTML'den {len(kategori_linkleri)} link bulundu.")

        # Biraz bekle ve scroll yap (lazy-load kategori menüsü için)
        try:
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(2)
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(2)
        except Exception:
            pass

        # Ağdan gelen kategori ID'leri zaten ag_yanitini_isle'de birikiyor
        time.sleep(3)
        kategori_linkleri_ek = kategori_linklerini_tara(page)
        tum_linkler = list(set(kategori_linkleri + kategori_linkleri_ek))
        print(f"  Toplam benzersiz kategori linki: {len(tum_linkler)}")

        # ----------------------------------------------------------------
        # 2. AŞAMA: categoryId keşfi
        # Önce colruyt_sub_kategoriler.json var mı bak (map scriptiyle oluşturuldu)
        # Varsa browser navigation'ı atla — çok daha hızlı ve stabil
        # ----------------------------------------------------------------
        sub_kat_dosya = os.path.join(script_dir, "colruyt_sub_kategoriler.json")
        harita_yuklendi = False

        if os.path.isfile(sub_kat_dosya):
            print(f"\n[2/3] colruyt_sub_kategoriler.json bulundu — browser navigation atlanıyor...")
            try:
                with open(sub_kat_dosya, encoding="utf-8") as f:
                    sub_harita = json.load(f)
                for cid in sub_harita.values():
                    if cid:
                        agi_yakalanan_kategori_idleri.add(str(cid))
                print(f"  {len(agi_yakalanan_kategori_idleri)} kategori ID yüklendi (kayıtlı dosyadan)")
                harita_yuklendi = True
            except Exception as e:
                print(f"  JSON yükleme hatası: {e} — browser navigation ile devam")

        if not harita_yuklendi:
            print("\n[2/3] Kategori sayfaları ziyaret ediliyor (categoryId keşfi)...")
            print("  İpucu: colruyt_kategori_map_olustur.py ile ID haritası oluşturabilirsin")
            print("         Bir kez çalıştırınca bu aşama her zaman atlanır.\n")

            max_k = args.max_kategori or len(tum_linkler)
            ziyaret_edilen = set()

            for i, link in enumerate(tum_linkler[:max_k]):
                if args.sadece_kesif and i >= 5:
                    break

                link_temiz = link.rstrip("/")
                if link_temiz in ziyaret_edilen:
                    continue
                ziyaret_edilen.add(link_temiz)

                kategori_adi = link_temiz.split("/nl/producten/")[-1].replace("-", " ").title()
                print(f"  [{i+1}/{min(max_k, len(tum_linkler))}] {kategori_adi}: {link_temiz}")

                # Browser alive kontrolü — çöktüyse yeniden aç
                browser_alive = True
                try:
                    _ = page.url
                except Exception:
                    browser_alive = False

                if not browser_alive:
                    print("  Browser kapandı! Yeniden açılıyor...")
                    try:
                        context.close()
                    except Exception:
                        pass
                    context = pw.chromium.launch_persistent_context(
                        user_data_dir=profil_dir,
                        headless=False,
                        locale="nl-BE",
                        viewport={"width": 1280, "height": 900},
                        args=["--disable-blink-features=AutomationControlled"],
                        ignore_https_errors=False,
                    )
                    page = context.pages[0] if context.pages else context.new_page()
                    page.on("response", ag_yanitini_isle)
                    try:
                        page.goto(SITE_URL, wait_until="domcontentloaded", timeout=60_000)
                        time.sleep(5)
                    except Exception:
                        pass

                try:
                    page.goto(link_temiz, wait_until="domcontentloaded", timeout=45_000)
                    time.sleep(2.5)
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(1.5)
                except Exception as e:
                    print(f"    Atlandı: {e}")
                    continue

                try:
                    import re
                    m = re.search(r"/c/(\d+)", page.url)
                    if m:
                        agi_yakalanan_kategori_idleri.add(m.group(1))
                except Exception:
                    pass

                insan_bekle("sayfa")

        # Tüm yakalanan kategori ID'lerini listeye çevir
        for cid in sorted(agi_yakalanan_kategori_idleri):
            kesfedilen_kategoriler.append({
                "categoryId": cid,
                "kaynak": "ag_yakalama" if not harita_yuklendi else "harita_dosyasi",
            })

        # Hardcoded bilinen ID'leri de ekle (backup)
        bilinen_idler = {"354","693","591","233","65","628","335","105","1675",
                         "124","129","421","347","670","188","33","761","306"}
        for cid in bilinen_idler:
            if not any(k["categoryId"] == cid for k in kesfedilen_kategoriler):
                kesfedilen_kategoriler.append({"categoryId": cid, "kaynak": "bilinen"})

        print(f"\n  Toplam kesfedilen kategori: {len(kesfedilen_kategoriler)}")
        print(f"  Anlık toplanan ürün: {len(toplanan)}")

        if args.sadece_kesif:
            print("\n--sadece-kesif aktif. Kategori ID'leri:")
            for k in kesfedilen_kategoriler:
                print(f"  categoryId={k['categoryId']}  ({k['kaynak']})")
            context.close()
            return

        # ----------------------------------------------------------------
        # 3. AŞAMA: Kategori bazlı API sayfalama
        # ----------------------------------------------------------------
        print(f"\n[3/3] Kategori bazlı API çekimi ({len(kesfedilen_kategoriler)} kategori)...")
        print("(Her 200 yeni üründe ara kayıt yapılacak)\n")

        onceki_kayit = len(toplanan)
        for ki, kat in enumerate(kesfedilen_kategoriler):
            cid = kat["categoryId"]
            print(f"  Kategori [{ki+1}/{len(kesfedilen_kategoriler)}] ID={cid} başlıyor "
                  f"(şu an {len(toplanan)} ürün)...")

            yeni = kategori_urunlerini_cek(
                context, cid, place_id, toplanan,
                kategori_adi=f"cat{cid}",
                max_urun=MAX_URUN,
            )
            print(f"    -> +{yeni} yeni ürün (toplam {len(toplanan)})")

            # Ara kayıt
            if len(toplanan) - onceki_kayit >= 200:
                ara_kaydet(checkpoint_yolu, toplanan)
                onceki_kayit = len(toplanan)
                print(f"    [ara kayıt] {len(toplanan)} ürün kaydedildi.")

            insan_bekle("sayfa")

        # ----------------------------------------------------------------
        # TAMAMLAMA TURU: Kategori dışı kalan ürünler
        # ----------------------------------------------------------------
        duzeltme_turu(context, place_id, toplanan, max_urun=MAX_URUN)

        context.close()

    # ----------------------------------------------------------------
    # SONUÇ KAYDET
    # ----------------------------------------------------------------
    urunler = list(toplanan.values())
    promo_sayisi = sum(1 for u in urunler if u.get("inPromo"))
    promo_tarihli = sum(1 for u in urunler if u.get("promoPublicationStart"))
    sure_dk = round((time.time() - toplam_baslangic) / 60, 1)

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya = os.path.join(cikti_dir, f"colruyt_be_producten_{tarih}.json")

    cikti = {
        "kaynak": "Colruyt Belçika",
        "chain_slug": "colruyt_be",
        "country_code": "BE",
        "yontem": "Playwright + kategori bazlı API sayfalama",
        "placeId": place_id,
        "cekilme_tarihi": datetime.now().isoformat(),
        "sure_dakika": sure_dk,
        "kesfedilen_kategori_sayisi": len(kesfedilen_kategoriler),
        "urun_sayisi": len(urunler),
        "promo_urun_sayisi": promo_sayisi,
        "promo_tarihli_urun_sayisi": promo_tarihli,
        "not_fiyat_gecerliligi": (
            "Colruyt fiyatları mağazaya göre değişebilir. "
            f"placeId={place_id} (Gent) için geçerlidir."
        ),
        "not_indirim": (
            "inPromo=true ve promoPublicationStart/End alanları indirim bilgisini içerir. "
            "isRedPrice=true = kırmızı fiyat etiketi (kalıcı indirim)."
        ),
        "urunler": urunler,
    }

    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"TAMAMLANDI!")
    print(f"  Toplam ürün   : {len(urunler)}")
    print(f"  Promo ürün    : {promo_sayisi}")
    print(f"  Promo tarihli : {promo_tarihli}")
    print(f"  Süre          : {sure_dk} dakika")
    print(f"  Dosya         : {dosya}")
    print("=" * 60)
    print("\nSonraki adım: json_to_supabase_yukle.py ile Supabase'e yükle")
    print(f'  python json_to_supabase_yukle.py --no-pause "{dosya}"')

    if not args.no_pause:
        input("\nÇıkmak için Enter...")


# ---------------------------------------------------------------------------
# ARG PARSER
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Colruyt BE — kategori bazlı tam ürün çekici"
    )
    ap.add_argument(
        "--zaten-giris", action="store_true",
        help="Profilde oturum var; giriş bekleme olmaz (~12 sn sonra başlar)"
    )
    ap.add_argument(
        "--enter-sonra-devam", action="store_true",
        help="Tarayıcıda giriş yaptıktan sonra Enter'a bas -> devam eder"
    )
    ap.add_argument(
        "--sadece-kesif", action="store_true",
        help="Ürün çekmeden sadece kategori ID'lerini keşfet ve göster"
    )
    ap.add_argument(
        "--max-kategori", type=int, default=0,
        help="Test için en fazla bu kadar kategori işle (0=hepsi)"
    )
    ap.add_argument(
        "--place-id", type=str, default=None,
        help=f"Mağaza ID (varsayılan: {PLACE_ID} = Gent)"
    )
    ap.add_argument(
        "--no-pause", action="store_true",
        help="Sonunda Enter bekleme"
    )
    return ap.parse_args()


if __name__ == "__main__":
    main()
