# -*- coding: utf-8 -*-
"""
Colruyt DOM Tabanlı Tam Çekici
================================
API yerine sayfa HTML'inden (data-tms-* attribute'ları) ürün verisi çeker.
Fiyat, eski fiyat, multi-buy, promo tarihleri, resim CDN URL dahil.

Kullanım:
    python colruyt_dom_cek.py --giris          # İlk çalıştırma, tarayıcıda giriş yap
    python colruyt_dom_cek.py --devam          # Kayıtlı profil ile devam
    python colruyt_dom_cek.py --devam --test   # Sadece 1 kategori test et
    python colruyt_dom_cek.py --devam --kat kaas   # Sadece kaas içeren kategoriler
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.stdout.reconfigure(encoding='utf-8')

# ── Ayarlar ──────────────────────────────────────────────────────────────────
SCRIPT_DIR    = Path(__file__).parent
CIKTI_DIR     = SCRIPT_DIR / "cikti"
PROFIL_DIR    = SCRIPT_DIR / "colruyt_browser_profile"
CHECKPOINT    = CIKTI_DIR / "colruyt_dom_checkpoint.json"
CIKTI_JSON    = CIKTI_DIR / f"colruyt_dom_{datetime.now().strftime('%Y-%m-%d')}.json"

SITE_URL      = "https://www.colruyt.be/nl/producten"
CDN_IMG       = "https://ecustomermwstatic.colruytgroup.com/ecustomermwstatic/nl/assets/asset-{}.jpg"

SCROLL_TEKRAR = 4       # Her sayfada kaç kez scroll yap (lazy load için)
SCROLL_BEKLEME= 1.5     # Her scroll sonrası bekleme (sn)
SAYFA_BEKLEME = (3, 7)  # Kategori sayfaları arası bekleme (sn)

CIKTI_DIR.mkdir(parents=True, exist_ok=True)
PROFIL_DIR.mkdir(parents=True, exist_ok=True)


# ── Log yardımcısı ───────────────────────────────────────────────────────────
def log(msg: str) -> None:
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)


# ── Checkpoint sistemi ────────────────────────────────────────────────────────
def checkpoint_yukle() -> dict:
    if CHECKPOINT.exists():
        try:
            with open(CHECKPOINT, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"tamamlanan": [], "urunler": {}}

def checkpoint_kaydet(state: dict) -> None:
    with open(CHECKPOINT, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

def ara_kaydet(urunler: dict) -> None:
    """Her kategori sonrası ara JSON kaydet."""
    veri = {
        "kayit_zamani": datetime.now().isoformat(),
        "urun_sayisi": len(urunler),
        "urunler": list(urunler.values()),
    }
    with open(CIKTI_JSON, 'w', encoding='utf-8') as f:
        json.dump(veri, f, ensure_ascii=False)


# ── DOM'dan ürün çekme ────────────────────────────────────────────────────────
def sayfadan_urun_cek(page) -> List[dict]:
    """
    Açık sayfadaki a.card--article elementlerinden tüm ürün bilgisini çeker.
    Lazy load için önce scroll yapılmış olmalı.
    """
    try:
        cards_data = page.evaluate("""
        () => {
            const results = [];
            const cards = document.querySelectorAll('a.card--article');
            cards.forEach(card => {
                const get = (attr) => card.getAttribute(attr) || null;

                // İsim
                const name = get('longname') || get('data-tms-product-name') || '';
                if (!name) return;

                // Fiyatlar
                const priceStr    = get('data-tms-product-price');
                const unitPStr    = get('data-tms-product-unitprice');
                const promoStr    = get('data-tms-product-promotion') || '';

                // Promo tarihleri (attribute veya data-*)
                const promoStart  = get('promoPublicationStart') ||
                                    get('data-promo-start') || null;
                const promoEnd    = get('promoPublicationEnd') ||
                                    get('data-promo-end') || null;

                // Eski fiyat — API alanından veya sayfadan
                let priceOld = get('previousPrice') ||
                               get('data-previous-price') ||
                               get('priceBeforePromo') || null;

                // Multi-buy: "2,89 vanaf 2 st" veya "2 voor 3,50" gibi
                const multiBuy    = get('data-tms-product-discounts-name') ||
                                    get('quantityPrice') ||
                                    get('data-quantity-price') || null;

                // Kimlik
                const retailNum   = get('retailproductnumber') || '';
                const techNum     = get('data-technical-article-number') || '';

                // Resim: currentSrc (yüklenen gerçek URL) önce, sonra src/data-src
                let imgUrl = null;
                const imgEl = card.querySelector('img');
                if (imgEl) {
                    // currentSrc: tarayıcının gerçekte yüklediği URL
                    const csrc = imgEl.currentSrc || '';
                    const src  = imgEl.getAttribute('src') || '';
                    const dsrc = imgEl.getAttribute('data-src') || '';
                    const best = csrc || src || dsrc;
                    if (best && !best.startsWith('data:') && best.length > 10) {
                        imgUrl = best;
                    }
                }

                // Diğer alanlar
                const brand       = get('seobrand') || get('data-brand') || '';
                const nutri       = get('nutriscore') || null;
                const eco         = get('ecoscorevalue') || null;
                const topCat      = get('topCategoryName') || get('data-top-category') || '';
                const catPath     = get('data-category-path') || topCat;
                const content     = get('data-content') || get('content') || '';
                const isRedPrice  = get('data-is-red-price') === 'true' ||
                                    promoStr.toLowerCase().includes('rood');
                const gtin        = get('gtin') || '';

                results.push({
                    name, priceStr, unitPStr, promoStr,
                    promoStart, promoEnd, priceOld, multiBuy,
                    retailNum, techNum, imgUrl,
                    brand, nutri, eco, topCat, catPath,
                    content, isRedPrice, gtin
                });
            });
            return results;
        }
        """)
    except Exception as e:
        log(f"  DOM okuma hatası: {e}")
        return []

    urunler = []
    for d in (cards_data or []):
        try:
            price = float(d['priceStr']) if d.get('priceStr') else None
            unit_p = float(d['unitPStr']) if d.get('unitPStr') else None
        except (ValueError, TypeError):
            price = unit_p = None

        # Eski fiyat parse
        price_old = None
        if d.get('priceOld'):
            try:
                price_old = float(str(d['priceOld']).replace(',', '.'))
            except (ValueError, TypeError):
                pass

        # Resim CDN URL oluştur
        img_url = d.get('imgUrl') or ''

        in_promo = bool(d.get('promoStr') and d['promoStr'].strip())

        urunler.append({
            "chain_slug":        "colruyt_be",
            "name":              d['name'],
            "brand":             d.get('brand') or '',
            "price":             price,
            "price_old":         price_old,
            "unit_price":        unit_p,
            "unit_type":         None,  # API olmadan tip bilinmiyor
            "in_promo":          in_promo,
            "promo_label":       d.get('promoStr') or '',
            "promo_valid_from":  d.get('promoStart'),
            "promo_valid_until": d.get('promoEnd'),
            "multi_buy":         d.get('multiBuy'),
            "image_url":         img_url,
            "nutriscore":        d.get('nutri'),
            "ecoscore":          d.get('eco'),
            "category_raw":      d.get('catPath') or d.get('topCat') or '',
            "retail_num":        d.get('retailNum') or '',
            "gtin":              d.get('gtin') or '',
            "content":           d.get('content') or '',
            "is_red_price":      d.get('isRedPrice', False),
            "captured_at":       datetime.now().isoformat(),
        })
    return urunler


def lazy_load_scroll(page) -> None:
    """Sayfayı aşağı kaydırarak lazy-load içeriği tetikler."""
    for i in range(SCROLL_TEKRAR):
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(SCROLL_BEKLEME)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            time.sleep(0.5)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)
        except Exception:
            pass


def infinite_scroll_yukle(page, maks_deneme: int = 50) -> int:
    """
    Colruyt infinite scroll: sayfa dibine kadar scroll et,
    yeni kartlar yüklenene kadar devam et.
    Döner: toplam kart sayısı.
    """
    onceki = 0
    degismedi = 0
    for i in range(maks_deneme):
        simdiki = len(page.query_selector_all('a.card--article'))
        if simdiki == onceki:
            degismedi += 1
            if degismedi >= 3:
                break  # 3 denemede yeni kart gelmediyse dur
        else:
            degismedi = 0
            if simdiki > onceki:
                log(f"    Scroll {i+1}: {simdiki} kart ({simdiki - onceki} yeni)")
        onceki = simdiki
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)
        except Exception:
            break
    return onceki


def toon_meer_tikla(page, maks_tikla: int = 30) -> int:
    """
    'Toon meer' / 'Meer laden' / 'Volgende' gibi butonları tıklayarak
    tüm ürünlerin yüklenmesini sağlar.
    Döner: tıklama sayısı.
    """
    tiklamalar = 0
    BUTON_SELECTORS = [
        '.load-more__btn',
        'button.load-more__btn',
        'a.load-more__btn',
        'button.btn--primary.load-more__btn',
        '[class*="load-more__btn"]',
        'button:has-text("Meer bekijken")',
        'button:has-text("Toon meer")',
        'button:has-text("Meer laden")',
        'button:has-text("Laad meer")',
        '[class*="load-more"]',
    ]
    while tiklamalar < maks_tikla:
        buton_bulundu = False
        for sel in BUTON_SELECTORS:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    onceki_kart = len(page.query_selector_all('a.card--article'))
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    time.sleep(2)
                    # Yeni kartlar yüklendi mi?
                    yeni_kart = len(page.query_selector_all('a.card--article'))
                    if yeni_kart > onceki_kart:
                        tiklamalar += 1
                        log(f"    [+{yeni_kart - onceki_kart}] Toon meer tıklandı (toplam: {yeni_kart})")
                        buton_bulundu = True
                        break
            except Exception:
                continue
        if not buton_bulundu:
            break
        # Scroll ile yeni içerikleri tetikle
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
    return tiklamalar


# ── Kategori linkleri ─────────────────────────────────────────────────────────
def kategori_linklerini_topla(page) -> List[dict]:
    """
    /nl/producten altındaki tüm alt kategori linklerini çeker.
    """
    try:
        linkler = page.evaluate("""
        () => {
            const out = [];
            const seen = new Set();
            document.querySelectorAll('a[href]').forEach(el => {
                const href = el.href || '';
                const m = href.match(/colruyt\\.be\\/nl\\/producten\\/([^/?#]+)\\/([^/?#]+)/);
                if (m && !seen.has(href)) {
                    seen.add(href);
                    out.push({
                        url: href.split('?')[0],
                        ust: m[1],
                        alt: m[2],
                        ad: el.textContent.trim() || m[2]
                    });
                }
            });
            document.querySelectorAll('a[href]').forEach(el => {
                const href = el.href || '';
                const m = href.match(/colruyt\\.be\\/nl\\/producten\\/([^/?#]+)\\/?$/);
                if (m && !seen.has(href) && !href.endsWith('/producten/')) {
                    seen.add(href);
                    out.push({
                        url: href.split('?')[0],
                        ust: m[1],
                        alt: '',
                        ad: el.textContent.trim() || m[1]
                    });
                }
            });
            return out;
        }
        """)
        return linkler or []
    except Exception as e:
        log(f"Kategori link hatası: {e}")
        return []


# ── Tek kategori sayfası çekimi ───────────────────────────────────────────────
def kategori_cek(page, kat: dict, maks_sayfa: int = 30) -> List[dict]:
    """
    Bir kategori sayfasını sayfalayarak tüm ürünleri çeker.
    Colruyt sayfalama: ?currentPage=2 veya ?page=2
    """
    tum_urunler = {}
    baz_url = kat['url'].rstrip('/')

    for sayfa_no in range(1, maks_sayfa + 1):
        if sayfa_no == 1:
            url = baz_url
        else:
            url = f"{baz_url}?currentPage={sayfa_no}"

        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if resp and resp.status in (404, 410):
                log(f"  Sayfa yok: {url}")
                break
        except Exception as e:
            log(f"  Sayfa açma hatası (deneme): {e}")
            time.sleep(5)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            except Exception:
                break

        # Ürünlerin yüklenmesini bekle
        try:
            page.wait_for_selector('a.card--article', timeout=10_000)
        except Exception:
            log(f"  Kart bulunamadı: {url} → sonraki kategori")
            break

        # Lazy load için scroll
        lazy_load_scroll(page)

        # "Toon meer" ile tüm ürünleri yükle (ilk sayfada)
        if sayfa_no == 1:
            # "Meer bekijken" butonuna tıklayarak tüm ürünleri yükle
            tikla = toon_meer_tikla(page, maks_tikla=50)
            if tikla > 0:
                lazy_load_scroll(page)
            else:
                log(f"  'Meer bekijken' butonu yok, {len(page.query_selector_all('a.card--article'))} kart mevcut")

        # DOM'dan oku
        urunler = sayfadan_urun_cek(page)

        if not urunler:
            log(f"  Sayfa {sayfa_no}: ürün yok → dur")
            break

        onceki = len(tum_urunler)
        for u in urunler:
            key = u['retail_num'] or u['name']
            if key and key not in tum_urunler:
                u['kategori_ust']  = kat.get('ust', '')
                u['kategori_alt']  = kat.get('alt', '')
                tum_urunler[key] = u

        yeni = len(tum_urunler) - onceki
        log(f"  Sayfa {sayfa_no}: {len(urunler)} ürün, {yeni} yeni (toplam: {len(tum_urunler)})")

        if yeni == 0 or len(urunler) < 24:
            break  # Son sayfa

        time.sleep(random.uniform(*SAYFA_BEKLEME))

    return list(tum_urunler.values())


# ── Hata yönetimli çekim ──────────────────────────────────────────────────────
def guvenceli_cek(page, kat: dict, maks_deneme: int = 3) -> List[dict]:
    """Retry + exponential backoff ile güvenli kategori çekimi."""
    for deneme in range(maks_deneme):
        try:
            return kategori_cek(page, kat)
        except Exception as e:
            bekleme = [5, 15, 45][deneme]
            log(f"  HATA (deneme {deneme+1}/{maks_deneme}): {e}")
            if deneme < maks_deneme - 1:
                log(f"  {bekleme}s bekleniyor...")
                time.sleep(bekleme)
    log(f"  ATILDI: {kat['url']}")
    return []


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--giris',   action='store_true', help='Tarayıcıda giriş yap')
    parser.add_argument('--devam',   action='store_true', help='Kayıtlı profil ile devam')
    parser.add_argument('--test',    action='store_true', help='Sadece ilk 2 kategori')
    parser.add_argument('--kat',     default='',          help='Sadece bu kelimeyi içeren kategoriler (ör: kaas)')
    parser.add_argument('--sifirla', action='store_true', help='Checkpoint sil, baştan başla')
    args = parser.parse_args()

    if args.sifirla and CHECKPOINT.exists():
        CHECKPOINT.unlink()
        log("Checkpoint silindi.")

    state = checkpoint_yukle()
    tum_urunler: dict = {u['retail_num'] or u['name']: u
                         for u in state.get('urunler', [])
                         if u.get('retail_num') or u.get('name')}
    tamamlanan: list = state.get('tamamlanan', [])

    log(f"Başlangıç: {len(tum_urunler)} mevcut ürün, {len(tamamlanan)} tamamlanan kategori")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("HATA: playwright yüklü değil. Çalıştır: pip install playwright && playwright install chromium")
        return

    try:
        from playwright_stealth import stealth_sync as stealth
        STEALTH = True
    except ImportError:
        STEALTH = False
        log("Uyarı: playwright-stealth yüklü değil (isteğe bağlı). pip install playwright-stealth")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFIL_DIR),
            headless=False,
            locale="nl-BE",
            viewport={"width": 1366, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = context.pages[0] if context.pages else context.new_page()
        if STEALTH:
            stealth(page)

        page.set_default_timeout(30_000)

        # ── Giriş bekleme ───────────────────────────────────────────────
        log(f"Ana sayfa açılıyor: {SITE_URL}")
        try:
            page.goto(SITE_URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception as e:
            log(f"Ana sayfa açılamadı: {e}")
            context.close()
            return

        if args.giris:
            log("\n>>> Colruyt penceresinde GİRİŞ YAP ve MAĞAZAYI SEÇ.")
            log(">>> Hazır olunca ENTER'a bas.")
            try:
                input()
            except EOFError:
                time.sleep(5)
        elif args.devam:
            log("Profilde oturum var kabul ediliyor; 8s bekleniyor...")
            time.sleep(8)
        else:
            log("HATA: --giris veya --devam parametresi gerekli.")
            context.close()
            return

        # ── Kategori keşfi ───────────────────────────────────────────────
        log("\n[1/2] Kategori linkleri toplanıyor...")
        try:
            page.goto(SITE_URL, wait_until="domcontentloaded", timeout=60_000)
            time.sleep(3)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
        except Exception as e:
            log(f"Ana sayfa yeniden açılamadı: {e}")

        kategoriler = kategori_linklerini_topla(page)
        log(f"  Ana sayfadan {len(kategoriler)} kategori linki bulundu")

        # Filtre varsa — o kategori sayfasını da ziyaret et ve alt kategorileri topla
        if args.kat:
            kat_url = f"https://www.colruyt.be/nl/producten/alle-categorieen/{args.kat}"
            log(f"  '{args.kat}' sayfası ziyaret ediliyor: {kat_url}")
            try:
                page.goto(kat_url, wait_until="domcontentloaded", timeout=30_000)
                time.sleep(3)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                alt_linkler = kategori_linklerini_topla(page)
                # Yeni linkleri ekle
                mevcut_urls = {k['url'] for k in kategoriler}
                for k in alt_linkler:
                    if k['url'] not in mevcut_urls and args.kat in k['url']:
                        kategoriler.append(k)
                        mevcut_urls.add(k['url'])
                log(f"  Alt kategorilerle birlikte toplam: {len(kategoriler)} link")
                # Ana sayfaya geri dön
                page.goto(SITE_URL, wait_until="domcontentloaded", timeout=30_000)
                time.sleep(2)
            except Exception as e:
                log(f"  Alt kategori ziyaret hatası: {e}")

        # Filtrele
        if args.kat:
            kategoriler = [k for k in kategoriler
                           if args.kat.lower() in k['url'].lower()
                           or args.kat.lower() in k.get('ad', '').lower()]
            log(f"  '{args.kat}' filtresi: {len(kategoriler)} kategori")

        if args.test:
            kategoriler = kategoriler[:2]
            log(f"  TEST modu: sadece {len(kategoriler)} kategori")

        # Tamamlananları çıkar
        kategoriler = [k for k in kategoriler if k['url'] not in tamamlanan]
        log(f"  İşlenecek: {len(kategoriler)} kategori (tamamlananlar hariç)")

        # ── Ürün çekimi ──────────────────────────────────────────────────
        log("\n[2/2] Ürünler çekiliyor...\n")

        browser_acilis = 0
        for i, kat in enumerate(kategoriler, 1):
            log(f"[{i}/{len(kategoriler)}] {kat.get('ad', '')} → {kat['url']}")

            # Her 50 kategoride tarayıcıyı yenile (bellek sızıntısı önleme)
            browser_acilis += 1
            if browser_acilis % 50 == 0:
                log("  Tarayıcı yenileniyor (bellek optimizasyonu)...")
                try:
                    page.reload(wait_until="domcontentloaded")
                    time.sleep(3)
                except Exception:
                    pass

            urunler = guvenceli_cek(page, kat)

            for u in urunler:
                key = u['retail_num'] or u['name']
                if key:
                    tum_urunler[key] = u

            tamamlanan.append(kat['url'])
            log(f"  ✓ {len(urunler)} ürün | Genel toplam: {len(tum_urunler)}")

            # Checkpoint + ara kayıt
            state = {"tamamlanan": tamamlanan, "urunler": list(tum_urunler.values())}
            checkpoint_kaydet(state)
            ara_kaydet(tum_urunler)

            time.sleep(random.uniform(*SAYFA_BEKLEME))

        context.close()

    # ── Final kayıt ──────────────────────────────────────────────────────────
    final = {
        "kayit_zamani": datetime.now().isoformat(),
        "urun_sayisi":  len(tum_urunler),
        "urunler":      list(tum_urunler.values()),
    }
    with open(CIKTI_JSON, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False)

    log(f"\n{'='*60}")
    log(f"TAMAMLANDI — {len(tum_urunler)} ürün")
    log(f"JSON: {CIKTI_JSON}")
    log(f"{'='*60}")


if __name__ == '__main__':
    main()
