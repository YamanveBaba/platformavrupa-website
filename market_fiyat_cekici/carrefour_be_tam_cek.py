# -*- coding: utf-8 -*-
"""
Carrefour BE — camoufox + "Meer tonen" buton tıklama ile tam katalog
Strateji:
  1. Ana sayfa + kategori URL keşfi
  2. Her kategori sayfasında "Meer tonen / Toon meer / Laad meer" butonuna bas
  3. Buton bitene kadar devam et -> tüm ürünler DOM'da -> data-pid ile topla
  4. Einstein-Recommendations JSON yanıtlarını da yakala

Kullanım:
  python carrefour_be_tam_cek.py                  (tam çekim)
  python carrefour_be_tam_cek.py --max-kat 3      (test)
  python carrefour_be_tam_cek.py --headed         (tarayıcı görünür)
"""
from __future__ import annotations
import argparse, json, os, re, time, random
from datetime import datetime
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin

script_dir = os.path.dirname(os.path.abspath(__file__))
CIKTI_DIR  = os.path.join(script_dir, "cikti")

BASE = "https://www.carrefour.be"

# Başlangıç kategori URL'leri (ana sayfa nav'ından alınır + bunlar eklenir)
SABIT_KAT = [
    (f"{BASE}/nl/al-onze-promoties",             "Alle promoties"),
    (f"{BASE}/nl/vb/melk-kopen",                 "Melk"),
    (f"{BASE}/nl/vb/brood-kopen",                "Brood"),
    (f"{BASE}/nl/vb/vlees-kopen",                "Vlees"),
    (f"{BASE}/nl/vb/vis-kopen",                  "Vis"),
    (f"{BASE}/nl/vb/groenten-kopen",             "Groenten"),
    (f"{BASE}/nl/vb/fruit-kopen",                "Fruit"),
    (f"{BASE}/nl/vb/kaas-kopen",                 "Kaas"),
    (f"{BASE}/nl/vb/yoghurt-kopen",              "Yoghurt"),
    (f"{BASE}/nl/vb/eieren-kopen",               "Eieren"),
    (f"{BASE}/nl/vb/pasta-kopen",                "Pasta"),
    (f"{BASE}/nl/vb/rijst-kopen",                "Rijst"),
    (f"{BASE}/nl/vb/soep-kopen",                 "Soep"),
    (f"{BASE}/nl/vb/sauzen-kopen",               "Sauzen"),
    (f"{BASE}/nl/vb/koffie-kopen",               "Koffie"),
    (f"{BASE}/nl/vb/thee-kopen",                 "Thee"),
    (f"{BASE}/nl/vb/water-kopen",                "Water"),
    (f"{BASE}/nl/vb/frisdrank-kopen",            "Frisdrank"),
    (f"{BASE}/nl/vb/bier-kopen",                 "Bier"),
    (f"{BASE}/nl/vb/wijn-kopen",                 "Wijn"),
    (f"{BASE}/nl/vb/chips-kopen",                "Chips"),
    (f"{BASE}/nl/vb/koeken-kopen",               "Koeken"),
    (f"{BASE}/nl/vb/chocolade-kopen",            "Chocolade"),
    (f"{BASE}/nl/vb/snoep-kopen",                "Snoep"),
    (f"{BASE}/nl/vb/ijs-kopen",                  "IJs"),
    (f"{BASE}/nl/vb/diepvries-kopen",            "Diepvries"),
    (f"{BASE}/nl/vb/babyvoeding-kopen",          "Babyvoeding"),
    (f"{BASE}/nl/vb/luiers-kopen",               "Luiers"),
    (f"{BASE}/nl/vb/wasmiddel-kopen",            "Wasmiddel"),
    (f"{BASE}/nl/vb/schoonmaak-kopen",           "Schoonmaak"),
    (f"{BASE}/nl/vb/tandpasta-kopen",            "Tandpasta"),
    (f"{BASE}/nl/vb/shampoo-kopen",              "Shampoo"),
    (f"{BASE}/nl/vb/kattenvoer-kopen",           "Kattenvoer"),
    (f"{BASE}/nl/vb/hondenvoer-kopen",           "Hondenvoer"),
    (f"{BASE}/nl/vb/ontbijtgranen-kopen",        "Ontbijtgranen"),
    (f"{BASE}/nl/vb/confituur-kopen",            "Confituur"),
    (f"{BASE}/nl/vb/olie-kopen",                 "Olie"),
    (f"{BASE}/nl/vb/azijn-kopen",                "Azijn"),
    (f"{BASE}/nl/vb/noten-kopen",                "Noten"),
    (f"{BASE}/nl/vb/snacks-kopen",               "Snacks"),
    (f"{BASE}/nl/vb/dranken-kopen",              "Dranken"),
    (f"{BASE}/nl/vb/voeding-kopen",              "Voeding"),
    (f"{BASE}/nl/vb/verse-producten-kopen",      "Verse producten"),
    (f"{BASE}/nl/vb/zuivel-kopen",               "Zuivel"),
    (f"{BASE}/nl/vb/charcuterie-kopen",          "Charcuterie"),
    (f"{BASE}/nl/vb/huishouden-kopen",           "Huishouden"),
    (f"{BASE}/nl/vb/verzorging-kopen",           "Verzorging"),
    (f"{BASE}/nl/vb/elektronica-kopen",          "Elektronica"),
    (f"{BASE}/nl/vb/speelgoed-kopen",            "Speelgoed"),
    (f"{BASE}/nl/vb/sport-kopen",                "Sport"),
    (f"{BASE}/nl/vb/tuin-kopen",                 "Tuin"),
    (f"{BASE}/nl/vb/dieren-kopen",               "Dieren"),
]


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def fiyat_al(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    try:
        return round(float(re.sub(r"[^\d.]", "", str(v).replace(",", "."))), 2)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# "Meer tonen" butonu
# ---------------------------------------------------------------------------

MEER_BUTON_SELS = [
    # Metin tabanlı (Playwright text matching)
    'button:has-text("Meer tonen")',
    'button:has-text("Toon meer")',
    'button:has-text("Laad meer")',
    'button:has-text("meer producten")',
    'button:has-text("Meer producten")',
    'button:has-text("Load more")',
    'button:has-text("Show more")',
    'a:has-text("Meer tonen")',
    'a:has-text("Toon meer")',
    # Class tabanlı
    '.load-more button',
    '.btn-load-more',
    '[class*="load-more"] button',
    '[class*="LoadMore"] button',
    '[class*="show-more"] button',
    '[class*="more-products"]',
    '[data-action*="more"]',
    '[data-testid*="load-more"]',
    # SFCC standart
    '.infinite-scroll-placeholder button',
    '.search-results-footer .btn',
    'button.more',
]


def meer_toon_tikla(page) -> bool:
    """
    'Meer tonen' butonunu bulur ve tıklar.
    Başarılı ise True döner.
    """
    for sel in MEER_BUTON_SELS:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1500):
                loc.scroll_into_view_if_needed(timeout=3000)
                time.sleep(0.5)
                loc.click(timeout=10000)
                return True
        except Exception:
            continue
    # JavaScript ile deneme
    try:
        found = page.evaluate("""
            () => {
                const patterns = [
                    /meer tonen/i, /toon meer/i, /laad meer/i,
                    /meer producten/i, /load more/i, /show more/i
                ];
                const btns = [...document.querySelectorAll('button, a[role="button"], a.btn')];
                for (const btn of btns) {
                    const txt = (btn.textContent || '').trim();
                    if (patterns.some(p => p.test(txt))) {
                        if (btn.offsetParent !== null) {  // görünür mü?
                            btn.scrollIntoView({behavior:'smooth', block:'center'});
                            btn.click();
                            return true;
                        }
                    }
                }
                return false;
            }
        """)
        if found:
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# DOM'dan ürün çıkarma
# ---------------------------------------------------------------------------

_DOM_JS = """
() => {
    const out = [];
    const seen = new Set();

    function extractPrice(el) {
        const priceAttrs = ['data-price', 'data-sales-price', 'data-regular-price'];
        for (const a of priceAttrs) {
            const v = el.getAttribute(a);
            if (v && /\\d/.test(v)) return v.trim();
        }
        const priceSels = [
            '.price .sales .value', '[class*="price"] .value',
            '.price__sales', '.price-sales', '.js-price-value',
            '[class*="price--sales"]', '[class*="actualPrice"]',
            '[class*="current-price"]', '[class*="sale-price"]',
            '[class*="Price"] strong', 'strong[class*="price"]',
            '[class*="price"][class*="current"]',
            '[class*="prijs"]', '[class*="Prijs"]',
        ];
        for (const sel of priceSels) {
            try {
                const ps = el.querySelector(sel);
                if (ps) {
                    const txt = ps.textContent.trim();
                    if (/\\d+[.,]\\d{2}/.test(txt)) return txt;
                }
            } catch(e) {}
        }
        // Fallback: any short element whose text is purely a price
        const allPrice = el.querySelectorAll('[class*="price"],[class*="Price"],[class*="prijs"]');
        for (const pe of allPrice) {
            const txt = pe.textContent.trim();
            if (/^[€£$]?\\s*\\d+[.,]\\d{2}$/.test(txt)) return txt;
        }
        return '';
    }

    function extractName(el) {
        const nameAttrs = ['data-name', 'data-product-name', 'data-title'];
        for (const a of nameAttrs) {
            const v = el.getAttribute(a);
            if (v && v.length > 2) return v.trim();
        }
        const nameSels = [
            '.pdp-link a', '.product-name a', '[class*="product-name"]',
            '[class*="ProductName"]', '[class*="pdp-link"]', '.tile-body .link',
            '[class*="product-title"]', '[class*="ProductTitle"]',
            '[class*="article-name"]', '[class*="ArticleName"]',
            'h2', 'h3', 'h4',
            'a[class*="product"]', '[class*="product"][class*="title"]',
        ];
        for (const sel of nameSels) {
            try {
                const ns = el.querySelector(sel);
                if (ns) {
                    const txt = (ns.textContent || ns.getAttribute('title') || '').trim();
                    if (txt.length > 2) return txt;
                }
            } catch(e) {}
        }
        // Fallback: first link text
        const lnk = el.querySelector('a');
        if (lnk) {
            const t = lnk.getAttribute('title') || lnk.textContent.trim();
            if (t && t.length > 2) return t;
        }
        return '';
    }

    function extractId(el) {
        const idAttrs = [
            'data-pid', 'data-product-id', 'data-article-id', 'data-sku',
            'data-id', 'data-item-id', 'data-product', 'data-verbolia-id',
            'data-tracking-product-id', 'data-gtm-product-id',
        ];
        for (const a of idAttrs) {
            const v = el.getAttribute(a);
            if (v) return v.trim();
        }
        // Extract from product URL
        const link = el.querySelector('a[href*="/nl/p/"], a[href*="/product/"], a[href]');
        if (link) {
            const href = link.getAttribute('href') || '';
            const m = href.match(/\\/p\\/([^\\/\\?#]+)/);
            if (m) return m[1];
        }
        return '';
    }

    // ── Strategy 1: SFCC [data-pid] (promoties + SFCC category pages) ────────
    document.querySelectorAll('[data-pid]').forEach(el => {
        const pid = el.getAttribute('data-pid') || '';
        if (!pid || seen.has(pid)) return;
        seen.add(pid);
        let price = el.getAttribute('data-price') || extractPrice(el);
        let name = el.getAttribute('data-name') || el.getAttribute('data-product-name') || extractName(el);
        const brand = el.getAttribute('data-brand') || '';
        const cat   = el.getAttribute('data-category') || el.getAttribute('data-item-list-name') || '';
        const inPromo = !!el.querySelector('[class*="promo"],[class*="badge-promo"],[class*="promotion"],[class*="actie"]');
        const imgEl = el.querySelector('img[data-src],img[src]');
        const img = imgEl ? (imgEl.getAttribute('data-src') || imgEl.getAttribute('src') || '') : '';
        out.push({
            pid,
            price: price.trim().slice(0, 60),
            name: name.trim().slice(0, 300),
            brand: brand.slice(0, 100),
            cat: cat.slice(0, 200),
            inPromo,
            img: img.slice(0, 400),
        });
    });

    // ── Strategy 2: Verbolia carrefour.be — a[data-id].single-product-desktop ─
    if (out.length === 0) {
        document.querySelectorAll('a[data-id][class*="single-product-desktop"]').forEach(el => {
            const pid = el.getAttribute('data-id') || '';
            if (!pid || seen.has(pid)) return;
            seen.add(pid);

            const priceEl = el.querySelector('.product-price');
            const price = priceEl ? priceEl.textContent.trim() : '';

            // İsim: çeşitli class'lara bak
            let name = '';
            const nameSelOrder = [
                '.product-name', '[class*="product-name"]',
                '.product-title', '[class*="product-title"]',
                'h2', 'h3', 'h4',
                '[class*="title"]', '[class*="name"]',
            ];
            for (const ns of nameSelOrder) {
                try {
                    const ne = el.querySelector(ns);
                    if (ne) { name = ne.textContent.trim(); if (name) break; }
                } catch(e) {}
            }
            // Fallback: <a> title attribute
            if (!name) name = el.getAttribute('title') || '';

            const inPromo = !!el.querySelector('[class*="promo"],[class*="actie"],[class*="korting"],[class*="promotion"],[class*="badge"]');
            const imgEl = el.querySelector('img[data-src],img[src]');
            const img = imgEl ? (imgEl.getAttribute('data-src') || imgEl.getAttribute('src') || '') : '';

            out.push({
                pid,
                price: price.slice(0, 60),
                name: name.slice(0, 300),
                brand: '',
                cat: '',
                inPromo,
                img: img.slice(0, 400),
            });
        });
    }

    // ── Strategy 3: Other generic containers (fallback) ──────────────────────
    if (out.length === 0) {
        const containerSels = [
            '[data-product-id]', '[data-article-id]', '[data-sku]',
            '[class*="ProductCard"]', '[class*="product-card"]',
            '[class*="ProductTile"]', '[class*="product-tile"]',
            '[class*="ArticleTile"]', '[class*="article-tile"]',
            '[class*="ProductItem"]', '[class*="product-item"]',
            'article[class*="tile"]', 'article[class*="product"]',
            'li[class*="product"]', 'li[class*="article"]',
            '[itemtype*="Product"]',
            '[class*="product-grid"] > *', '[class*="product-list"] > li',
        ];
        for (const csel of containerSels) {
            let els;
            try { els = document.querySelectorAll(csel); } catch(e) { continue; }
            if (els.length < 2) continue;
            els.forEach(el => {
                const pid = extractId(el);
                const lnk = el.querySelector('a');
                const linkKey = lnk ? (lnk.getAttribute('href') || '') : '';
                const key = pid || linkKey || '';
                if (!key || seen.has(key)) return;
                seen.add(key);
                const price = extractPrice(el);
                const name  = extractName(el);
                const brand = el.getAttribute('data-brand') || '';
                const cat   = el.getAttribute('data-category') || '';
                const inPromo = !!el.querySelector('[class*="promo"],[class*="badge"],[class*="promotion"],[class*="actie"],[class*="korting"]');
                const imgEl = el.querySelector('img[data-src],img[src]');
                const img = imgEl ? (imgEl.getAttribute('data-src') || imgEl.getAttribute('src') || '') : '';
                out.push({
                    pid: (pid || key).slice(0, 200),
                    price: price.trim().slice(0, 60),
                    name: name.trim().slice(0, 300),
                    brand: brand.slice(0, 100),
                    cat: cat.slice(0, 200),
                    inPromo,
                    img: img.slice(0, 400),
                });
            });
            if (out.length > 0) break;
        }
    }

    return out;
}
"""


def dom_urun_ekle(tiles: list, hedef: Dict, varsayilan_kat: str) -> int:
    yeni = 0
    for t in tiles:
        pid = str(t.get("pid") or "").strip()
        if not pid or pid in hedef:
            continue
        price_raw = t.get("price") or ""
        floats = sorted(
            [f for f in [fiyat_al(p) for p in re.findall(r"\d+[.,]\d{1,2}", price_raw)] if f],
            reverse=True,
        )
        basic = floats[0] if floats else None
        promo = floats[1] if len(floats) > 1 else None
        hedef[pid] = {
            "carrefourPid": pid,
            "name": t.get("name", "")[:300],
            "brand": t.get("brand", "")[:120],
            "topCategoryName": (t.get("cat") or varsayilan_kat)[:200],
            "basicPrice": basic,
            "promoPrice": promo,
            "inPromo": bool(t.get("inPromo")) or promo is not None,
            "imageUrl": t.get("img", "")[:400],
        }
        yeni += 1
    return yeni


# ---------------------------------------------------------------------------
# Ana çekim
# ---------------------------------------------------------------------------

def sayfayi_tam_cek(page, kat_ad: str, urunler: Dict,
                    max_tiklama: int = 200) -> int:
    """
    Bir sayfadaki tüm ürünleri 'Meer tonen' butonuna basarak topla.
    Döner: bu sayfadan eklenen yeni ürün sayısı.
    """
    onceki = len(urunler)
    tiklama = 0
    bos_tiklama = 0   # yeni ürün gelmeden yapılan ardışık tıklama sayısı
    MAX_BOS = 6       # 6 kez tıkla, ürün gelmezse bitir

    # İlk yükleme — sayfada zaten olan ürünleri al
    try:
        tiles = page.evaluate(_DOM_JS)
        dom_urun_ekle(tiles, urunler, kat_ad)
    except Exception:
        pass

    while True:
        # Buton var mı?
        buton_tiklandi = meer_toon_tikla(page)
        if not buton_tiklandi:
            # Buton yok -> sayfa bitti
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)
            try:
                tiles = page.evaluate(_DOM_JS)
                dom_urun_ekle(tiles, urunler, kat_ad)
            except Exception:
                pass
            break

        tiklama += 1

        # Yükleme bekle: Verbolia AJAX için yeterince uzun
        time.sleep(random.uniform(2.5, 4.0))
        # Sayfa sonuna scroll -> lazy-load tetikle, buton görünsün
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.0)

        # Yeni ürünleri topla
        before = len(urunler)
        try:
            tiles = page.evaluate(_DOM_JS)
            dom_urun_ekle(tiles, urunler, kat_ad)
        except Exception:
            pass

        if len(urunler) > before:
            bos_tiklama = 0
        else:
            bos_tiklama += 1
            if bos_tiklama >= MAX_BOS:
                print(f"    [!] {MAX_BOS} ardışık tıklamada yeni ürün gelmedi — durduruluyor")
                break

        if tiklama >= max_tiklama:
            break

    eklenen = len(urunler) - onceki
    print(f"    {tiklama} klik, +{eklenen} ürün")
    return eklenen


def calistir(max_kat: int = 0, no_pause: bool = False) -> int:
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        print("HATA: pip install camoufox && python -m camoufox fetch")
        return 1

    os.makedirs(CIKTI_DIR, exist_ok=True)
    urunler: Dict[str, Dict] = {}
    einstein_pool: List[str] = []

    def on_response(response):
        """Einstein-Recommendations JSON'larını yakala."""
        try:
            if "Einstein-Recommendation" not in response.url:
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            data = json.loads(response.body())
            for rec in (data.get("recommendations") or []):
                html = rec.get("html") or ""
                if html:
                    einstein_pool.append(html)
        except Exception:
            pass

    def einstein_isle(kat: str) -> int:
        """Biriken Einstein HTML'lerini parse et ve ürünlere ekle."""
        if not einstein_pool:
            return 0
        combined = "\n".join(einstein_pool)
        einstein_pool.clear()
        yeni = 0
        pid_re = re.compile(r'data-pid=["\']([^"\']+)["\']')
        name_re = re.compile(r'(?:data-name|aria-label)[^>]*=["\']([^"\']{4,200})["\']', re.I)
        price_re = re.compile(r'data-price=["\']([0-9.,]+)["\']|class=["\'][^"\']*sales[^"\']*["\'][^>]*>\s*([0-9]+[.,][0-9]{2})', re.I)
        brand_re = re.compile(r'data-brand=["\']([^"\']{1,80})["\']', re.I)
        seen: Set[str] = set()
        for m in pid_re.finditer(combined):
            pid = m.group(1).strip()
            if not pid or pid in urunler or pid in seen:
                continue
            seen.add(pid)
            s = max(0, m.start() - 100)
            chunk = combined[s:min(len(combined), m.end() + 1200)]
            nm = name_re.search(chunk)
            name = nm.group(1).strip() if nm else ""
            prices = []
            for pm in price_re.finditer(chunk):
                v = fiyat_al(pm.group(1) or pm.group(2))
                if v and v > 0:
                    prices.append(v)
            prices.sort(reverse=True)
            basic = prices[0] if prices else None
            promo = prices[1] if len(prices) > 1 else None
            bm = brand_re.search(chunk)
            urunler[pid] = {
                "carrefourPid": pid,
                "name": name[:300],
                "brand": bm.group(1).strip() if bm else "",
                "topCategoryName": kat[:200],
                "basicPrice": basic,
                "promoPrice": promo,
                "inPromo": promo is not None,
            }
            yeni += 1
        return yeni

    # Tüm kategori listesini hazırla
    tum_kat = list(SABIT_KAT)
    if max_kat > 0:
        tum_kat = tum_kat[:max_kat]

    with Camoufox(
        headless=False,
        firefox_user_prefs={
            "browser.startup.page": 0,
            "browser.sessionstore.resume_from_crash": False,
            "browser.sessionstore.enabled": False,
        },
    ) as browser:
        page = browser.new_page()
        page.on("response", on_response)
        time.sleep(2)

        def goto_safe(url: str, bekle: float = 3.5) -> bool:
            for _ in range(3):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                    time.sleep(bekle)
                    return True
                except Exception as e:
                    print(f"  [goto hata] {str(e)[:80]}")
                    time.sleep(3)
            return False

        def cookie_kabul():
            for sel in (
                'button:has-text("Alles accepteren")',
                '#onetrust-accept-btn-handler',
                '[data-testid="accept-all-cookies"]',
            ):
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible(timeout=2000):
                        loc.click()
                        time.sleep(1.5)
                        return
                except Exception:
                    pass

        # ── İlk sayfa: cookie al ──────────────────────────────────────────
        print("\n[0] İlk açılış (cookie)…")
        if goto_safe(f"{BASE}/nl/al-onze-promoties", 4):
            cookie_kabul()
            time.sleep(2)

        # ── Kategori döngüsü ──────────────────────────────────────────────
        for i, (url, kat_ad) in enumerate(tum_kat):
            if i > 0 and i % 8 == 0:
                bekle = random.uniform(8, 15)
                print(f"\n  ── Ara bekleme {bekle:.0f}s (ürün={len(urunler)}) ──")
                time.sleep(bekle)

            print(f"\n[{i+1}/{len(tum_kat)}] {kat_ad}  {url[:60]}")
            if not goto_safe(url, 3.5):
                print("  [atlandı]")
                continue

            son_url = page.url
            baslik  = page.title()

            # 404 / hata kontrolü
            if "Sites-carrefour-be-Site" in baslik or "404" in baslik:
                print(f"  [404/hata] {baslik} — atlandı")
                continue

            print(f"  -> {son_url[:70]}  [{baslik[:50]}]")

            # Sayfa tam yüklensin, spinner bitsin
            time.sleep(1)
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(1.5)

            # Ürünleri topla (buton tıklama + DOM)
            yeni = sayfayi_tam_cek(page, kat_ad, urunler, max_tiklama=300)

            # Einstein pool
            ein = einstein_isle(kat_ad)
            if ein:
                print(f"  Einstein: +{ein}")

            print(f"  Toplam: {len(urunler)}")

            # Ara kayıt — her kategori sonrası yaz (crash olursa kaybolmaz)
            ara_out = os.path.join(CIKTI_DIR, "carrefour_be_ara_kayit.json")
            try:
                with open(ara_out, "w", encoding="utf-8") as f:
                    json.dump({
                        "kaynak": "Carrefour BE — ara kayıt",
                        "chain_slug": "carrefour_be",
                        "country_code": "BE",
                        "cekilme_tarihi": datetime.now().isoformat(),
                        "tamamlanan_kat": i + 1,
                        "toplam_kat": len(tum_kat),
                        "urun_sayisi": len(urunler),
                        "urunler": list(urunler.values()),
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  [ara kayıt hata] {e}")

    # ── Kaydet ────────────────────────────────────────────────────────────
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    urun_listesi = list(urunler.values())
    out = os.path.join(CIKTI_DIR, f"carrefour_be_producten_{tarih}.json")
    payload = {
        "kaynak": "Carrefour BE — camoufox + Meer tonen buton tıklama",
        "chain_slug": "carrefour_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi": len(urun_listesi),
        "urunler": urun_listesi,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"TAMAM: {len(urun_listesi)} ürün -> {out}")
    print(f"{'='*60}")

    if not no_pause:
        input("\nÇıkmak için Enter…")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-kat", type=int, default=0)
    ap.add_argument("--no-pause", action="store_true")
    args = ap.parse_args()
    return calistir(max_kat=args.max_kat, no_pause=args.no_pause)


if __name__ == "__main__":
    raise SystemExit(main())
