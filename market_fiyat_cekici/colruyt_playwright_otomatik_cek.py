# -*- coding: utf-8 -*-
"""
Colruyt Belçika — Playwright ile TAM OTOMATİK ürün + fiyat toplama

Tarayıcı gerçek oturumu kullanır (cookie/script copy gerekmez).
İlk çalıştırmada açılan pencerede giriş yapmanız yeterli; profil kaydedilir,
sonraki seferlerde genelde tekrar giriş gerekmez.

Mantık: Sayfa ilk product-search-prs isteğinin URL şablonunu yakalar;
aynı Chromium oturumunun çerezleriyle API'yi skip/size ile sayfalayarak
tüm ürünleri toplar (yanlış "Meer" butonuna takılmaz).
Yedek: URL alınamazsa kaydırma / buton denemesi.
"""

import argparse
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

# Aynı klasörde normalize + tarayıcıya yakın API başlıkları + varsayılan API tabanı
from colruyt_product_search_api_cek import API_HEADERS_BASE, CONFIG as CR_API_CONFIG, product_to_platform

CONFIG = {
    "start_url": "https://www.colruyt.be/nl/producten",
    "max_products": 60000,
    "api_page_size": 25,  # Tam katalog sayfalama (20–60 arası API genelde kabul eder)
    # Ardışık turda yeni ürün gelmezse çık (buton yok + scroll da yetmez)
    "stale_limit": 14,
    "stale_limit_hedef_var": 28,  # API hedef > toplanan iken daha sabırlı
    "save_every_new": 200,  # Bu kadar yeni üründe ara kayıt
    "goto_timeout_ms": 120000,
    # Profilde oturum yokken: giriş + mağaza seçimi için (90 sn yetmeyebiliyor)
    "ilk_giris_bekle_sn": 300,
}


def sleep_login_countdown(total_sec: int, label: str = "Giriş / mağaza seçimi için kalan") -> None:
    """Uzun beklerken ekranda kalan süreyi gösterir (dondu sanılmasın)."""
    left = int(total_sec)
    if left <= 0:
        return
    print(f"  ({label}: {left} sn — her ~30 sn bir güncellenir)\n")
    while left > 0:
        chunk = min(30, left)
        time.sleep(chunk)
        left -= chunk
        if left > 0:
            print(f"  … {label}: ~{left} sn")


def human_pause():
    r = random.random()
    if r < 0.02:
        sec = random.uniform(35.0, 85.0)
        print(f"  [mola] {sec:.0f} sn...")
    elif r < 0.12:
        sec = random.uniform(6.0, 14.0)
        print(f"  [yavaş] {sec:.1f} sn...")
    else:
        sec = random.uniform(2.5, 5.8)
    time.sleep(sec)


def scroll_to_trigger_lazy_load(page) -> None:
    """Sonsuz kaydırma ile yeni ürün isteği (product-search-prs) tetiklenir."""
    try:
        for _ in range(6):
            page.evaluate(
                "window.scrollBy(0, Math.min(950, Math.floor(window.innerHeight * 0.92)))"
            )
            time.sleep(0.4)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.2)
        try:
            page.keyboard.press("End")
            time.sleep(0.4)
        except Exception:
            pass
    except Exception:
        pass


def click_load_more(page) -> bool:
    """Colruyt 'daha fazla' butonunu bulup tıklar (birkaç seçici)."""
    role_names = (
        r"Meer bekijken",
        r"meer laden",
        r"toon meer",
        r"meer producten",
        r"^meer$",
        r"voir plus",
        r"afficher plus",
    )
    for pat in role_names:
        try:
            loc = page.get_by_role("button", name=re.compile(pat, re.I)).first
            if loc.count() > 0 and loc.is_visible(timeout=800):
                loc.scroll_into_view_if_needed(timeout=8000)
                loc.click(timeout=20000)
                return True
        except Exception:
            continue

    selectors = [
        "button.load-more",
        "[class*='load-more'] button",
        "[class*='LoadMore' i] button",
        "button:has-text('Meer')",
        "button:has-text('meer')",
        "text=/^Meer bekijken$/i",
        "text=/meer laden/i",
        "text=/toon meer/i",
        "[data-testid*='load-more' i]",
        "a[role='button']:has-text('Meer')",
    ]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() > 0:
                try:
                    if not loc.is_visible(timeout=1500):
                        continue
                except Exception:
                    continue
                loc.scroll_into_view_if_needed(timeout=8000)
                loc.click(timeout=20000)
                return True
        except Exception:
            continue
    # Son çare: sayfa sonuna kaydır, yine dene
    try:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.2)
        for sel in selectors[:6]:
            loc = page.locator(sel).first
            try:
                if loc.count() > 0 and loc.is_visible(timeout=800):
                    loc.scroll_into_view_if_needed(timeout=5000)
                    loc.click(timeout=15000)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def trigger_more_products(page) -> str:
    """
    Yeni ürün yüklemeyi dener. Dönüş: 'click' | 'scroll' | 'none'
    """
    if click_load_more(page):
        return "click"
    scroll_to_trigger_lazy_load(page)
    return "scroll"


def save_checkpoint(path: str, collected: dict, total_found):
    payload = {
        "saved_at": datetime.now().isoformat(),
        "urun_sayisi": len(collected),
        "totalProductsFound": total_found,
        "urunler": list(collected.values()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def _playwright_api_headers() -> Dict[str, str]:
    """Çerez Playwright context'ten gider; gzip decode sorunları için Accept-Encoding çıkarılır."""
    skip = {"cookie", "Cookie", "Accept-Encoding", "accept-encoding"}
    return {k: v for k, v in API_HEADERS_BASE.items() if k not in skip}


def _merge_total_found(holder: Dict[str, Any], tf: Any) -> None:
    """Dar arama yanıtı totalProductsFound=0 ile gerçek katalog sayısının ezilmesini engeller."""
    if tf is None:
        return
    try:
        v = int(tf)
    except (TypeError, ValueError):
        return
    if v < 0:
        return
    if holder["v"] is None:
        holder["v"] = v
    else:
        holder["v"] = max(int(holder["v"]), v)


def is_narrow_filtered_prs_url(url: str) -> bool:
    """Tek ürün / arama / öneri isteği; tüm katalog değil (technicalArtNos vb.)."""
    ul = url.lower()
    markers = (
        "technicalartnos",
        "retailproductnumber",
        "productids=",
        "searchquery",
        "searchtext",
        "query=",
    )
    return any(m in ul for m in markers)


def pick_best_prs_template(candidates: List[dict]) -> Optional[str]:
    """En yüksek totalProductsFound + ürün sayısına sahip şablonu seçer; mümkünse filtrelenmemiş URL."""
    if not candidates:
        return None
    wide = [c for c in candidates if not is_narrow_filtered_prs_url(c["url"])]
    pool = wide if wide else candidates
    best = max(pool, key=lambda c: (c["tf"], c["n"]))
    return best["url"]


def normalize_to_full_catalog_prs_url(template_url: str) -> str:
    """
    Yalnızca placeId çıkarıp minimal tam katalog URL'si üretir (sort/kategori vb. alt küme riski yok).
    """
    pid = extract_place_id_from_prs_url(template_url)
    if not pid:
        return template_url
    return minimal_catalog_prs_url(pid, skip=0, page_size=int(CONFIG.get("api_page_size") or 25))


def minimal_catalog_prs_url(place_id: str, skip: int = 0, page_size: Optional[int] = None) -> str:
    """Tam katalog: sadece placeId, skip, size, isAvailable — başka query parametresi yok."""
    base = CR_API_CONFIG["base_url"].split("?")[0].rstrip("/")
    sz = page_size if page_size is not None else int(CONFIG.get("api_page_size") or 25)
    sz = max(15, min(int(sz), 60))
    q = {
        "placeId": str(place_id).strip(),
        "size": str(sz),
        "skip": str(int(skip)),
        "isAvailable": "true",
    }
    return f"{base}?{urlencode(q)}"


def build_catalog_prs_url_from_place(place_id: str) -> str:
    return minimal_catalog_prs_url(place_id, skip=0, page_size=int(CONFIG.get("api_page_size") or 25))


def extract_place_id_from_prs_url(url: str) -> Optional[str]:
    q = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    pid = q.get("placeId") or q.get("placeid")
    return str(pid).strip() if pid else None


def prs_url_with_skip_size(template_url: str, skip: int, page_size: int) -> str:
    u = template_url.split("#")[0].strip()
    p = urlparse(u)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q["skip"] = str(int(skip))
    q["size"] = str(int(page_size))
    new_q = urlencode(list(q.items()))
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_q, p.fragment))


def fetch_all_prs_via_browser_context(
    context: Any,
    template_url: str,
    collected: Dict[str, Any],
    total_found_holder: Dict[str, Any],
    *,
    max_products: int,
) -> bool:
    """
    Minimal product-search-prs URL ile skip ilerletir (tam katalog).
    Tarayıcı context.request çerezleri Colruyt'a iletir.
    """
    q = dict(parse_qsl(urlparse(template_url).query, keep_blank_values=True))
    try:
        page_size = int(q.get("size") or CONFIG.get("api_page_size") or 25)
    except (TypeError, ValueError):
        page_size = int(CONFIG.get("api_page_size") or 25)
    page_size = max(15, min(page_size, 60))
    skip = int(q.get("skip") or 0)
    place_id = q.get("placeId") or q.get("placeid")
    base_template = (
        minimal_catalog_prs_url(str(place_id), skip=0, page_size=page_size)
        if place_id
        else template_url
    )
    headers = _playwright_api_headers()
    got_any = False
    page_idx = 0
    no_new_rows = 0
    while len(collected) < max_products:
        url = prs_url_with_skip_size(base_template, skip, page_size)
        before = len(collected)
        try:
            resp = context.request.get(url, headers=headers, timeout=90_000)
        except Exception as e:
            print(f"  API istek hatası: {e}")
            break
        if resp.status == 429:
            time.sleep(45 + random.uniform(0, 20))
            continue
        if resp.status != 200:
            print(f"  API HTTP {resp.status} (sayfa skip={skip})")
            if resp.status == 401 or resp.status == 406:
                print("  Oturum süresi dolmuş olabilir; tarayıcıda colruyt.be yenileyip tekrar deneyin.")
            break
        try:
            data = resp.json()
        except Exception:
            print("  API yanıtı JSON değil; duruldu.")
            break
        tf = data.get("totalProductsFound")
        _merge_total_found(total_found_holder, tf)
        products = data.get("products") or []
        if not products:
            print(f"  API: skip={skip} ürün yok; liste sonu.")
            break
        got_any = True
        for p in products:
            try:
                rpn = p.get("retailProductNumber")
                if rpn:
                    collected[str(rpn)] = product_to_platform(p)
            except Exception:
                continue
        added_unique = len(collected) - before
        if added_unique == 0:
            no_new_rows += 1
            print(f"  Uyarı: bu sayfada yeni benzersiz ürün yok ({no_new_rows}/6) skip={skip}")
            if no_new_rows >= 6:
                print("  Aynı sayfalar dönüyor gibi; duruldu.")
                break
        else:
            no_new_rows = 0
        page_idx += 1
        if page_idx % 6 == 0 or (tf is not None and int(tf) > 0 and len(collected) >= int(tf)):
            print(f"  API sayfa {page_idx}, toplanan: {len(collected)}" + (f" / hedef: {tf}" if tf else ""))
        skip += len(products)
        if tf is not None and int(tf) > 0 and len(collected) >= int(tf):
            print(f"  Hedef ürün sayısına ulaşıldı ({tf}).")
            break
        if len(products) < page_size:
            print("  Son sayfa (ürün sayısı < sayfa boyutu).")
            break
        time.sleep(random.uniform(0.35, 1.05))
    return got_any


def main():
    parser = argparse.ArgumentParser(description="Colruyt Playwright otomatik çekici")
    parser.add_argument(
        "--bekle-ilk-sn",
        type=int,
        default=0,
        help="İlk açılışta giriş için saniye (0=varsayılan uzun bekleme veya --enter-sonra-devam kullan).",
    )
    parser.add_argument(
        "--enter-sonra-devam",
        action="store_true",
        help="Tarayıcı açıldıktan sonra süre sayımı yok; konsolda Enter'a basıncaya kadar bekler (giriş için en güvenilir).",
    )
    parser.add_argument(
        "--hizli-profil",
        action="store_true",
        help="Zaten giriş yaptığın profille kısa bekle (~20 sn); ilk kurulumda kullanma.",
    )
    parser.add_argument(
        "--zaten-giris",
        action="store_true",
        help="Profilde zaten giriş + mağaza seçiliyse: 300 sn beklemez (~15 sn sonra ürün çekimine geçer).",
    )
    parser.add_argument(
        "--place-id",
        type=str,
        default=None,
        help="Mağaza placeId (ör. Gent 710). Verilirse tam katalog URL doğrudan buna göre oluşturulur.",
    )
    args = parser.parse_args()
    forced_place = (args.place_id or "").strip() or None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    profile_dir = os.path.join(script_dir, "colruyt_browser_profile")
    os.makedirs(profile_dir, exist_ok=True)
    checkpoint_path = os.path.join(cikti_dir, "colruyt_playwright_checkpoint.json")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: playwright yüklü değil. Komut: pip install playwright")
        print("Sonra: python -m playwright install chromium")
        input("\nEnter ile çıkın...")
        return

    collected = {}
    total_found_holder = {"v": None}
    prs_candidates: List[dict] = []

    def on_response(response):
        url = response.url
        if "product-search-prs" not in url:
            return
        try:
            if response.status != 200:
                return
            data = response.json()
        except Exception:
            return
        clean = url.split("#")[0].strip()
        tf = data.get("totalProductsFound")
        try:
            tf_i = int(tf) if tf is not None else 0
        except (TypeError, ValueError):
            tf_i = 0
        npr = len(data.get("products") or [])
        prs_candidates.append({"url": clean, "tf": tf_i, "n": npr})
        _merge_total_found(total_found_holder, tf)
        for p in data.get("products") or []:
            try:
                rpn = p.get("retailProductNumber")
                if not rpn:
                    continue
                collected[str(rpn)] = product_to_platform(p)
            except Exception:
                continue

    print("Colruyt — Playwright OTOMATİK çekici")
    print(f"Profil klasörü: {profile_dir}")
    print("(İlk seferde giriş yaptıktan sonra cookie burada kalır.)\n")

    start_all = time.time()
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            locale="nl-BE",
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_https_errors=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("response", on_response)

        print(f"Sayfa açılıyor: {CONFIG['start_url']}")
        try:
            page.goto(
                CONFIG["start_url"],
                wait_until="domcontentloaded",
                timeout=CONFIG["goto_timeout_ms"],
            )
        except Exception as e:
            print(f"\nSayfa yüklenemedi: {e}\n")
            context.close()
            input("Çıkmak için Enter...")
            return

        if args.enter_sonra_devam:
            print(
                "\n>>> Colruyt penceresinde giriş yapın ve mağazanızı seçin.\n"
                ">>> Hazır olunca bu siyah pencereye dönüp Enter tuşuna basın (süre sınırı yok).\n"
            )
            try:
                input()
            except EOFError:
                pass
        elif args.bekle_ilk_sn > 0:
            print(f"\n>>> {args.bekle_ilk_sn} sn içinde giriş yapın / mağaza seçin; süre bitince otomatik devam eder. <<<\n")
            sleep_login_countdown(args.bekle_ilk_sn, "Kalan")
        elif args.hizli_profil:
            print("\nProfil güvenilir kabul edildi; ~20 sn bekleniyor...\n")
            time.sleep(20)
        elif args.zaten_giris:
            print(
                "\n  --zaten-giris: Giriş penceresi beklenmiyor; sayfa ve API istekleri için ~15 sn.\n"
                "  (İlk kurulumda --enter-sonra-devam veya uzun süreli bekleme kullanın.)\n"
            )
            time.sleep(15)
        else:
            w = int(CONFIG.get("ilk_giris_bekle_sn") or 300)
            print(
                f"\n>>> Açılan pencerede giriş + mağaza seçin. Yaklaşık {w} sn sonra otomatik devam eder. <<<\n"
                f"    Zaten girişliyse: python colruyt_playwright_otomatik_cek.py --zaten-giris\n"
                f"    Süresiz: --enter-sonra-devam (Enter'a basınca devam)\n"
            )
            sleep_login_countdown(w, "Giriş için kalan")

        # Ağdan product-search-prs adayları (--place-id yoksa geniş istek için kaydır/bekle)
        if forced_place:
            time.sleep(2)
        else:
            time.sleep(4)
            for wait_i in range(36):
                has_wide = any(not is_narrow_filtered_prs_url(c["url"]) for c in prs_candidates)
                if prs_candidates and (has_wide or wait_i >= 24):
                    break
                if wait_i % 3 == 2:
                    scroll_to_trigger_lazy_load(page)
                time.sleep(1.5)

        raw_tpl = pick_best_prs_template(prs_candidates)
        place_fallback: Optional[str] = None
        for c in prs_candidates:
            place_fallback = extract_place_id_from_prs_url(c["url"])
            if place_fallback:
                break

        if forced_place:
            template_url = minimal_catalog_prs_url(forced_place)
            print(
                f"\n  --place-id={forced_place}: minimal tam katalog URL (tüm ürünler, sayfalı).\n"
                f"  …{template_url[-95:]}\n"
            )
        elif raw_tpl:
            template_url = normalize_to_full_catalog_prs_url(raw_tpl)
            was_narrow = is_narrow_filtered_prs_url(raw_tpl)
            print(
                "\n  Ağdan placeId alındı; minimal tam katalog URL kullanılıyor.\n"
                f"  (Yakalanan istek dar filtreydi: {was_narrow})\n"
                f"  …{template_url[-95:]}\n"
            )
        elif place_fallback:
            template_url = minimal_catalog_prs_url(place_fallback)
            print(
                f"\n  placeId={place_fallback} (ağdan); minimal tam katalog URL.\n"
                f"  …{template_url[-95:]}\n"
            )
        else:
            pid = str(CR_API_CONFIG.get("place_id") or "762")
            template_url = minimal_catalog_prs_url(pid)
            print(
                "\n  UYARI: placeId ağdan gelmedi; colruyt_product_search_api_cek.py varsayılan "
                f"place_id={pid}. Mağazanız farklıysa: --place-id 710 gibi verin.\n"
                f"  …{template_url[-95:]}\n"
            )

        api_ok = fetch_all_prs_via_browser_context(
            context,
            template_url,
            collected,
            total_found_holder,
            max_products=CONFIG["max_products"],
        )
        print(f"  API taraması bitti; toplanan: {len(collected)}\n")

        tf = total_found_holder["v"]
        need_ui = (not api_ok) or (
            tf is not None
            and int(tf) > 0
            and len(collected) < int(tf)
            and len(collected) < CONFIG["max_products"]
        )
        if need_ui:
            print("  Eksik ürün veya API başarısız; arayüzden tamamlama deneniyor…\n")
            stale = 0
            prev_count = len(collected)
            last_checkpoint_count = 0
            while len(collected) < CONFIG["max_products"]:
                n = len(collected)
                tf2 = total_found_holder["v"]
                if tf2 is not None and int(tf2) > 0 and n >= int(tf2):
                    print(f"  API toplam ({tf2}) kadar ürün toplandı.")
                    break

                stale_cap = CONFIG["stale_limit"]
                if tf2 is not None and n < tf2:
                    stale_cap = int(CONFIG.get("stale_limit_hedef_var") or stale_cap)

                how = trigger_more_products(page)
                if how == "click":
                    human_pause()
                else:
                    time.sleep(random.uniform(0.8, 1.6))

                time.sleep(random.uniform(1.8, 3.4))

                n2 = len(collected)
                if n2 == prev_count:
                    stale += 1
                    print(
                        f"  Tur sonunda yeni ürün yok ({stale}/{stale_cap}) "
                        f"[son işlem: {how}]"
                    )
                else:
                    stale = 0
                prev_count = n2

                print(f"  Toplanan: {n2}" + (f" / hedef API: {tf2}" if tf2 else ""))

                if n2 - last_checkpoint_count >= CONFIG["save_every_new"]:
                    save_checkpoint(checkpoint_path, collected, tf2)
                    print(f"  Ara kayıt → {checkpoint_path}")
                    last_checkpoint_count = n2

                if stale >= stale_cap:
                    print(
                        "  Arayüz modu: yeni ürün gelmiyor; durduruldu. "
                        "(API adımı çoğu ürünü zaten almış olmalı.)"
                    )
                    break

        context.close()

    elapsed = time.time() - start_all
    urunler = list(collected.values())
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya_yolu = os.path.join(cikti_dir, f"colruyt_be_playwright_{tarih}.json")

    cikti = {
        "kaynak": "Colruyt Belçika",
        "chain_slug": "colruyt_be",
        "country_code": "BE",
        "yontem": "Playwright oturumu + product-search-prs API sayfalama (şablon URL; yedek: UI)",
        "cekilme_tarihi": datetime.now().isoformat(),
        "sure_dakika": round(elapsed / 60, 1),
        "urun_sayisi": len(urunler),
        "totalProductsFound_siteden": total_found_holder["v"],
        "urunler": urunler,
    }

    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    if os.path.isfile(checkpoint_path):
        try:
            os.remove(checkpoint_path)
        except OSError:
            pass

    print(f"\nBitti: {len(urunler)} ürün, {elapsed/60:.1f} dk")
    print(f"Kayıt: {dosya_yolu}")
    input("\nÇıkmak için Enter...")


if __name__ == "__main__":
    main()
