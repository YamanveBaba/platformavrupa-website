# -*- coding: utf-8 -*-
"""
Colruyt Belçika — Playwright ile TAM OTOMATİK ürün + fiyat toplama

Tarayıcı gerçek oturumu kullanır (cookie/script copy gerekmez).
İlk çalıştırmada açılan pencerede giriş yapmanız yeterli; profil kaydedilir,
sonraki seferlerde genelde tekrar giriş gerekmez.

Mantık: Sayfada "daha fazla ürün" butonuna otomatik tıklar,
Network'ten gelen product-search-prs JSON yanıtlarını birleştirir.
"""

import argparse
import json
import os
import random
import re
import time
from datetime import datetime

# Aynı klasörde normalize fonksiyonunu kullan
from colruyt_product_search_api_cek import product_to_platform

CONFIG = {
    "start_url": "https://www.colruyt.be/nl/producten",
    "max_products": 15000,
    "stale_limit": 8,  # Ardışık "yeni ürün yok" / tıklanamadı sayısı
    "save_every_new": 200,  # Bu kadar yeni üründe ara kayıt
    "goto_timeout_ms": 120000,
}


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


def profile_looks_logged_in(profile_dir: str) -> bool:
    """Basit kontrol: Chromium profilinde Cookies dosyası var mı, büyük mü?"""
    cookies_path = os.path.join(profile_dir, "Default", "Network", "Cookies")
    try:
        if os.path.isfile(cookies_path) and os.path.getsize(cookies_path) > 2500:
            return True
    except OSError:
        pass
    return False


def click_load_more(page) -> bool:
    """Colruyt 'daha fazla' butonunu bulup tıklar (birkaç seçici)."""
    selectors = [
        "button.load-more",
        "[class*='load-more'] button",
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
        for sel in selectors[:4]:
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


def save_checkpoint(path: str, collected: dict, total_found):
    payload = {
        "saved_at": datetime.now().isoformat(),
        "urun_sayisi": len(collected),
        "totalProductsFound": total_found,
        "urunler": list(collected.values()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Colruyt Playwright otomatik çekici")
    parser.add_argument(
        "--bekle-ilk-sn",
        type=int,
        default=0,
        help="İlk açılışta giriş için ekstra bekleme (0=otomatik tahmin).",
    )
    args = parser.parse_args()

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
        tf = data.get("totalProductsFound")
        if tf is not None:
            total_found_holder["v"] = tf
        for p in data.get("products") or []:
            rpn = p.get("retailProductNumber")
            if not rpn:
                continue
            collected[str(rpn)] = product_to_platform(p)

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
        page.goto(
            CONFIG["start_url"],
            wait_until="domcontentloaded",
            timeout=CONFIG["goto_timeout_ms"],
        )

        if args.bekle_ilk_sn > 0:
            print(f"\n>>> {args.bekle_ilk_sn} sn içinde gerekirse giriş yapın / mağaza seçin <<<\n")
            time.sleep(args.bekle_ilk_sn)
        else:
            if profile_looks_logged_in(profile_dir):
                print("\nProfil mevcut; kısa bekleyip devam ediliyor...\n")
                time.sleep(6)
            else:
                print("\n>>> İLK ÇALIŞTIRMA: Açılan pencerede giriş + mağaza seçin. 90 sn sonra otomatik devam. <<<\n")
                time.sleep(90)

        # İlk API yanıtları için kısa bekle
        time.sleep(4)

        stale = 0
        prev_count = len(collected)
        last_checkpoint_count = 0

        while len(collected) < CONFIG["max_products"]:
            n = len(collected)
            tf = total_found_holder["v"]
            if tf is not None and n >= tf:
                print(f"  API toplam ({tf}) kadar ürün toplandı.")
                break

            ok = click_load_more(page)
            if not ok:
                stale += 1
                print(f"  'Daha fazla' tıklanamadı ({stale}/{CONFIG['stale_limit']})")
            else:
                human_pause()

            # Yanıtların gelmesi için
            time.sleep(random.uniform(1.2, 2.8))

            n2 = len(collected)
            if n2 == prev_count:
                stale += 1
            else:
                stale = 0
            prev_count = n2

            print(f"  Toplanan: {n2}" + (f" / hedef API: {tf}" if tf else ""))

            if n2 - last_checkpoint_count >= CONFIG["save_every_new"]:
                save_checkpoint(checkpoint_path, collected, tf)
                print(f"  Ara kayıt → {checkpoint_path}")
                last_checkpoint_count = n2

            if stale >= CONFIG["stale_limit"]:
                print("  Yeni ürün gelmiyor veya buton yok; güvenli durduruldu.")
                break

        context.close()

    elapsed = time.time() - start_all
    urunler = list(collected.values())
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya_yolu = os.path.join(cikti_dir, f"colruyt_be_playwright_{tarih}.json")

    cikti = {
        "kaynak": "Colruyt Belçika",
        "yontem": "Playwright + product-search-prs (Network dinleme)",
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
