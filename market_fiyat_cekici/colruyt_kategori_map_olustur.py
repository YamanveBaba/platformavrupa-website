# -*- coding: utf-8 -*-
"""
Colruyt — Tek Seferlik Kategori ID Haritası Oluşturucu
=======================================================
Her Colruyt alt-kategori URL'si için categoryId değerini bulur ve
colruyt_sub_kategoriler.json dosyasına kaydeder.

Bu dosya bir kez oluşturulunca colruyt_kategori_cek.py onu kullanır;
her hafta 219 sayfayı tekrar ziyaret etmek gerekmez.

KULLANIM:
  İlk çalıştırma (giriş gerekli):
      python colruyt_kategori_map_olustur.py --enter-sonra-devam

  Profilde oturum varsa:
      python colruyt_kategori_map_olustur.py --zaten-giris

  Sonraki haftalık çekim (harita hazırsa):
      python colruyt_kategori_cek.py --zaten-giris --no-pause
"""

from __future__ import annotations

import argparse
import json
import os
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import parse_qsl, urlparse

SCRIPT_DIR = Path(__file__).parent
PROFIL_DIR = SCRIPT_DIR / "colruyt_browser_profile"
CIKTI_DOSYA = SCRIPT_DIR / "colruyt_sub_kategoriler.json"
SITE_URL = "https://www.colruyt.be/nl/producten"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def kategori_linklerini_tara(page) -> list[str]:
    """Ana sayfadan tüm alt-kategori linklerini toplar."""
    try:
        linkler = page.evaluate("""
        () => {
            const out = new Set();
            document.querySelectorAll('a[href]').forEach(a => {
                const h = a.href || '';
                if (h.includes('/nl/producten/') && !h.includes('?') && !h.includes('#')) {
                    const clean = h.split('?')[0].split('#')[0].replace(/\\/$/, '');
                    if (clean.length > 40) out.add(clean);
                }
            });
            return Array.from(out);
        }
        """)
        return [l for l in (linkler or []) if "colruyt.be" in l]
    except Exception:
        return []


def yeni_context_ac(pw, profil_dir: str):
    """Kalıcı profil ile yeni Playwright context açar."""
    return pw.chromium.launch_persistent_context(
        user_data_dir=profil_dir,
        headless=False,
        locale="nl-BE",
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Colruyt kategori ID haritası oluştur")
    ap.add_argument("--enter-sonra-devam", action="store_true",
                    help="Tarayıcıda giriş yap, Enter'a bas → devam")
    ap.add_argument("--zaten-giris", action="store_true",
                    help="Profilde oturum var, 12 sn bekleyip başla")
    ap.add_argument("--no-pause", action="store_true", help="Sonunda Enter bekleme")
    args = ap.parse_args()

    PROFIL_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: playwright yüklü değil. pip install playwright && playwright install chromium")
        return

    # Mevcut haritayı yükle (kaldığı yerden devam)
    harita: Dict[str, Optional[str]] = {}
    if CIKTI_DOSYA.exists():
        try:
            with open(CIKTI_DOSYA, encoding="utf-8") as f:
                harita = json.load(f)
            log(f"Mevcut harita yüklendi: {len(harita)} URL, "
                f"{sum(1 for v in harita.values() if v)} ID bulunmuş")
        except Exception:
            harita = {}

    def kaydet() -> None:
        with open(CIKTI_DOSYA, "w", encoding="utf-8") as f:
            json.dump(harita, f, ensure_ascii=False, indent=2)

    with sync_playwright() as pw:
        context = yeni_context_ac(pw, str(PROFIL_DIR))
        page = context.pages[0] if context.pages else context.new_page()

        # Giriş bekleme
        log(f"Ana sayfa açılıyor: {SITE_URL}")
        page.goto(SITE_URL, wait_until="domcontentloaded", timeout=90_000)

        if args.enter_sonra_devam:
            print("\n>>> Colruyt'a GİRİŞ YAP ve MAĞAZAYI SEÇ (Gent).")
            print(">>> Hazır olunca ENTER'a bas.\n")
            try:
                input()
            except EOFError:
                pass
        elif args.zaten_giris:
            log("Profilde oturum var, 12 sn bekleniyor...")
            time.sleep(12)
        else:
            log("HATA: --enter-sonra-devam veya --zaten-giris gerekli.")
            context.close()
            return

        # Tüm kategori linklerini topla
        log("Kategori linkleri toplanıyor...")
        try:
            page.goto(SITE_URL, wait_until="domcontentloaded", timeout=60_000)
            time.sleep(3)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
        except Exception as e:
            log(f"Ana sayfa hatası: {e}")

        tum_linkler = list(set(kategori_linklerini_tara(page)))
        log(f"Toplam {len(tum_linkler)} kategori linki bulundu.")

        # Haritada olmayan URL'leri filtrele
        bekleyen = [l for l in tum_linkler if l not in harita or harita[l] is None]
        log(f"Keşfedilecek: {len(bekleyen)} URL (zaten bilinen: {len(tum_linkler) - len(bekleyen)})")

        # Handler döngü DIŞINDA — mutable dict ile state paylaşımı
        state = {"cid": None}

        def api_yanitini_isle(response):
            if state["cid"]:
                return
            if "product-search-prs" not in response.url:
                return
            if response.status != 200:
                return
            try:
                parsed = urlparse(response.url)
                q = dict(parse_qsl(parsed.query))
                cid = q.get("categoryId")
                if cid:
                    state["cid"] = cid
            except Exception:
                pass

        page.on("response", api_yanitini_isle)

        tamamlanan = 0
        for i, url in enumerate(bekleyen):
            if url in harita and harita[url]:
                continue

            kat_adi = url.split("/nl/producten/")[-1]
            log(f"  [{i+1}/{len(bekleyen)}] {kat_adi}")

            # Her iterasyon başında state sıfırla
            state["cid"] = None

            # Browser alive kontrolü — çöktüyse yeniden aç
            try:
                _ = page.url
            except Exception:
                log("  Browser kapandı! Yeniden açılıyor...")
                try:
                    context.close()
                except Exception:
                    pass
                context = yeni_context_ac(pw, str(PROFIL_DIR))
                page = context.pages[0] if context.pages else context.new_page()
                page.on("response", api_yanitini_isle)
                try:
                    page.goto(SITE_URL, wait_until="domcontentloaded", timeout=60_000)
                    time.sleep(5)
                except Exception:
                    pass

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                # Scroll yaparak lazy-load API çağrısını tetikle
                time.sleep(1.5)
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(1.0)
                page.evaluate("window.scrollBy(0, 600)")
                time.sleep(1.0)
                # API çağrısını bekle (maks 8 sn)
                for _ in range(16):
                    if state["cid"]:
                        break
                    time.sleep(0.5)
            except Exception as e:
                log(f"    Atlandı: {str(e)[:80]}")
                harita[url] = None
                continue

            harita[url] = state["cid"]

            if yakalanan_id:
                log(f"    categoryId = {yakalanan_id} ✓")
                tamamlanan += 1
            else:
                log(f"    categoryId bulunamadı")

            # Her 10 URL'de ara kayıt
            if (i + 1) % 10 == 0:
                kaydet()
                log(f"  → Ara kayıt: {tamamlanan} ID bulundu")

            # İnsan benzeri bekleme
            time.sleep(random.uniform(2.5, 5.0))
            if random.random() < 0.1:
                time.sleep(random.uniform(8, 15))

        context.close()

    # Final kayıt
    kaydet()
    bulunan = sum(1 for v in harita.values() if v)
    log("=" * 60)
    log(f"TAMAMLANDI!")
    log(f"  Toplam URL    : {len(harita)}")
    log(f"  ID bulunan    : {bulunan}")
    log(f"  ID bulunamayan: {len(harita) - bulunan}")
    log(f"  Dosya         : {CIKTI_DOSYA}")
    log("=" * 60)
    log("")
    log("Sonraki adım — tam katalog çekimi:")
    log("  python colruyt_kategori_cek.py --zaten-giris --no-pause")

    if not args.no_pause:
        input("\nÇıkmak için Enter...")


if __name__ == "__main__":
    main()
