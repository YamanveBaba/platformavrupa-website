# -*- coding: utf-8 -*-
"""
Aldi BE — Tam Katalog Çekici v2
Özellikler:
  OK camoufox (Firefox, Cloudflare bypass)
  OK Network interception — Aldi JSON API'sini otomatik yakala
  OK window.__NEXT_DATA__ / embedded JSON taraması
  OK Çoklu DOM fallback (eski data-article dahil)
  OK Tam insan davranışı: gaussian timing, bezier mouse, değişken scroll
  OK Checkpoint/resume — crash -> kaldığı yerden devam
  OK Site yapısı değişirse akıllı hata yönetimi

Kullanım:
  python aldi_be_v2.py              # tam çekim
  python aldi_be_v2.py --test       # ilk 3 kategori
  python aldi_be_v2.py --resume     # checkpoint'ten devam
  python aldi_be_v2.py --diag       # DOM/API diagnostic (çekim yapma)
  python aldi_be_v2.py --no-pause
"""
from __future__ import annotations
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import argparse, json, re, time, random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from scraper_utils import (
    log_olustur, ban_tespit, backoff_bekle, StopSinyali,
    jsonld_urun_cikart, proxy_yukle, robotstxt_kontrol, http_durum_isle,
)

_log  = log_olustur("aldi_be")
_stop = StopSinyali()

script_dir = Path(__file__).parent
CIKTI_DIR  = script_dir / "cikti"
CHECKPOINT = CIKTI_DIR  / "aldi_v2_checkpoint.json"
BASE       = "https://www.aldi.be"

# ─── Kategori URL'leri ────────────────────────────────────────────────────────
# (ad, url, zorunlu_mu: False=0 ürün olabilir sil geçme)
KATEGORILER: List[Tuple[str, str]] = [
    # Haftalık fırsatlar (her zaman fiyatlı)
    ("Aanbiedingen deze week",     f"{BASE}/nl/onze-aanbiedingen.html"),
    ("Aanbiedingen volgende week", f"{BASE}/nl/aanbiedingen-volgende-week.html"),
    # Sabit koleksiyon
    ("Groenten",                   f"{BASE}/nl/producten/assortiment/groenten.html"),
    ("Fruit",                      f"{BASE}/nl/producten/assortiment/fruit.html"),
    ("Vlees",                      f"{BASE}/nl/producten/assortiment/vlees.html"),
    ("Vis Zeevruchten",            f"{BASE}/nl/producten/assortiment/vis-zeevruchten.html"),
    ("Melkproducten Kaas",         f"{BASE}/nl/producten/assortiment/melkproducten-kaas.html"),
    ("Brood Banket",               f"{BASE}/nl/producten/assortiment/brood-en-banket.html"),
    ("Broodbeleg",                 f"{BASE}/nl/producten/assortiment/broodbeleg.html"),
    ("Alcoholvrije Dranken",       f"{BASE}/nl/producten/assortiment/alcoholvrije-dranken.html"),
    ("Alcoholische Dranken",       f"{BASE}/nl/producten/assortiment/alcoholische-dranken.html"),
    ("IJsjes",                     f"{BASE}/nl/producten/assortiment/ijsjes.html"),
    ("Pasta Rijst",                f"{BASE}/nl/producten/assortiment/pasta-rijst.html"),
    ("Conserven",                  f"{BASE}/nl/producten/assortiment/conserven.html"),
    ("Bakken Koken",               f"{BASE}/nl/producten/assortiment/bakken-en-koken.html"),
    ("Koffie Thee",                f"{BASE}/nl/producten/assortiment/koffie-thee-cacao.html"),
    ("Muesli Cornflakes",          f"{BASE}/nl/producten/assortiment/muesli-cornflakes-granen.html"),
    ("Snacks Zoetigheden",         f"{BASE}/nl/producten/assortiment/snacks-zoetigheden.html"),
    ("Kant-en-klaar",              f"{BASE}/nl/producten/assortiment/kant-en-klaar.html"),
    ("Vegetarisch Vegan",          f"{BASE}/nl/producten/assortiment/vegetarisch-vegan.html"),
    ("Cosmetica Verzorging",       f"{BASE}/nl/producten/assortiment/cosmetica-verzorging.html"),
    ("Huishouden",                 f"{BASE}/nl/producten/assortiment/huishouden.html"),
    ("Dierenvoeding",              f"{BASE}/nl/producten/assortiment/dierenvoeding.html"),
    ("Babyproducten",              f"{BASE}/nl/producten/assortiment/babyproducten.html"),
    ("Diepvrieskost",              f"{BASE}/nl/producten/assortiment/diepvrieskost.html"),
    ("Sauzen Kruiden",             f"{BASE}/nl/producten/assortiment/sauzen-kruiden-specerijen.html"),
    ("Verse producten",            f"{BASE}/nl/producten/assortiment/verse-producten.html"),
    ("Thee Hub",                   f"{BASE}/nl/producten.html"),
]


# ─── Gaussian timing ──────────────────────────────────────────────────────────
def rg(mu: float, sigma: float, lo: float = 0.05, hi: float = None) -> float:
    v = random.gauss(mu, sigma)
    v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v

def sl(mu: float, sigma: float, lo: float = 0.05, hi: float = None):
    time.sleep(rg(mu, sigma, lo, hi))


# ─── İnsan mouse / scroll ─────────────────────────────────────────────────────
def bezier_mouse(page, tx: float, ty: float):
    try:
        vp = page.viewport_size or {"width": 1280, "height": 720}
        sx = random.uniform(80, vp["width"] - 80)
        sy = random.uniform(80, vp["height"] - 80)
        cx = random.uniform(min(sx, tx), max(sx, tx))
        cy = random.uniform(min(sy, ty), max(sy, ty))
        steps = random.randint(7, 18)
        for i in range(1, steps + 1):
            t = i / steps
            x = (1-t)**2*sx + 2*(1-t)*t*cx + t**2*tx + random.gauss(0, 1.2)
            y = (1-t)**2*sy + 2*(1-t)*t*cy + t**2*ty + random.gauss(0, 1.2)
            page.mouse.move(x, y)
            sl(0.020, 0.008, 0.005, 0.08)
    except Exception:
        pass


def insan_scroll(page, toplam: int = 1600):
    kaydirilan = 0
    while kaydirilan < toplam:
        chunk = max(50, min(500, int(random.gauss(190, 90))))
        chunk = min(chunk, toplam - kaydirilan)
        page.mouse.wheel(0, chunk)
        kaydirilan += chunk
        sl(0.12, 0.06, 0.03, 0.5)
        if random.random() < 0.22:
            sl(1.8, 0.9, 0.4, 6.0)
        if random.random() < 0.07:
            geri = max(30, min(220, int(random.gauss(110, 55))))
            page.mouse.wheel(0, -geri)
            kaydirilan = max(0, kaydirilan - geri)
            sl(0.5, 0.25, 0.15, 2.0)


def insan_tiklama(page, locator) -> bool:
    try:
        locator.scroll_into_view_if_needed(timeout=3000)
        sl(0.30, 0.15, 0.08, 1.2)
        box = locator.bounding_box(timeout=3000)
        if box:
            tx = box["x"] + box["width"] / 2 + random.gauss(0, 3)
            ty = box["y"] + box["height"] / 2 + random.gauss(0, 3)
            bezier_mouse(page, tx, ty)
            sl(0.18, 0.09, 0.05, 0.7)
        locator.hover(timeout=3000)
        sl(0.20, 0.09, 0.05, 0.8)
        locator.click(timeout=10_000)
        return True
    except Exception:
        try:
            locator.click(timeout=8000)
            return True
        except Exception:
            return False


# ─── Tarih normalize ──────────────────────────────────────────────────────────
def to_iso_date(val) -> Optional[str]:
    if not val:
        return None
    if isinstance(val, (int, float)):
        ts = int(val)
        if ts > 1e12:
            ts //= 1000
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return None
    s = str(val).strip()
    if s.isdigit():
        return to_iso_date(int(s))
    if len(s) >= 10 and s[4] == "-":
        return s[:10]
    m = re.match(r'^(\d{2})[\/.-](\d{2})[\/.-](\d{4})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def fiyat_parse(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        f = float(v)
        return round(f, 2) if f > 0 else None
    try:
        f = float(re.sub(r"[^\d.]", "", str(v).replace(",", ".")))
        return round(f, 2) if f > 0 else None
    except Exception:
        return None


# ─── JSON yanıtından ürün çıkarma — evrensel ─────────────────────────────────
def json_urunleri_cikart(data, kat_ad: str, hedef: Dict) -> int:
    """
    Herhangi bir JSON yapısından ürün çıkarmaya çalışır.
    Aldi'nin hem eski hem yeni API formatlarını destekler.
    """
    yeni = 0

    def isle_urun(obj: dict) -> bool:
        nonlocal yeni
        if not isinstance(obj, dict):
            return False

        # PID tespiti — birçok alan adı dene
        pid = None
        for k in ("productID", "product_id", "id", "sku", "articleNumber",
                  "productId", "itemId", "eanCode", "ean"):
            v = obj.get(k)
            if v:
                pid = str(v).strip()
                break
        if not pid:
            return False
        if pid in hedef:
            return False

        # İsim
        name = ""
        for k in ("productName", "name", "title", "productTitle", "description"):
            v = obj.get(k)
            if v and str(v).strip():
                name = str(v).strip()
                break
        if not name:
            return False

        # Fiyat
        price = None
        for k in ("priceWithTax", "price", "regularPrice", "normalPrice",
                  "salePrice", "currentPrice", "basePrice"):
            v = obj.get(k)
            if isinstance(v, dict):
                for kk in ("value", "amount", "current"):
                    vv = v.get(kk)
                    if vv is not None:
                        price = fiyat_parse(vv)
                        break
            else:
                price = fiyat_parse(v)
            if price and price > 0:
                break

        in_promo = bool(obj.get("inPromotion") or obj.get("isOnSale")
                        or obj.get("hasPromotion") or obj.get("promotion"))
        promo_price_raw = obj.get("promoPrice") or obj.get("strikePrice") \
                          or obj.get("originalPrice") or obj.get("wasPrice")
        promo_price = fiyat_parse(promo_price_raw)
        if promo_price and price and promo_price >= price:
            promo_price = None
        if promo_price:
            in_promo = True

        brand = str(obj.get("brand") or obj.get("manufacturer") or "").strip()
        image = str(obj.get("imageUrl") or obj.get("image") or
                    obj.get("thumbnail") or obj.get("img") or "").strip()
        category = str(obj.get("category") or obj.get("categoryName")
                       or obj.get("primaryCategory") or kat_ad).strip()

        promo_from  = to_iso_date(obj.get("promotionStartDate") or
                                  obj.get("promo_start") or obj.get("validFrom") or
                                  obj.get("promotionDate"))
        promo_until = to_iso_date(obj.get("promotionEndDate") or
                                  obj.get("promo_end") or obj.get("validTo") or
                                  obj.get("validUntil"))

        hedef[pid] = {
            "aldiPid":         pid,
            "name":            name[:300],
            "brand":           brand[:120],
            "topCategoryName": category[:200],
            "basicPrice":      price,
            "promoPrice":      promo_price,
            "inPromo":         in_promo,
            "promoValidFrom":  promo_from,
            "promoValidUntil": promo_until,
            "imageUrl":        image[:400],
        }
        yeni += 1
        return True

    def tara(obj, derinlik: int = 0):
        if derinlik > 8:
            return
        if isinstance(obj, list):
            for item in obj[:2000]:
                if isinstance(item, dict):
                    isle_urun(item)
                    # Nested: productInfo, data, product
                    for nested_key in ("productInfo", "data", "product", "item"):
                        nested = item.get(nested_key)
                        if isinstance(nested, dict):
                            isle_urun(nested)
                    tara(item, derinlik + 1)
                elif isinstance(item, list):
                    tara(item, derinlik + 1)
        elif isinstance(obj, dict):
            # Direkt ürün mü?
            isle_urun(obj)
            # Bilinen container key'leri
            for k in ("products", "items", "results", "data", "entries",
                      "productList", "articles", "assortment", "hits"):
                v = obj.get(k)
                if v:
                    tara(v, derinlik + 1)

    tara(data)
    return yeni


# ─── DOM'dan ürün çekme ───────────────────────────────────────────────────────
_DOM_JS = """
() => {
    const out = [];
    const seen = new Set();

    function extractPriceText(el) {
        // data-article'dan
        const raw = el.getAttribute('data-article');
        if(raw) {
            try {
                const d = JSON.parse(raw.replace(/&quot;/g,'"'));
                const info = d.productInfo || {};
                if(info.priceWithTax) return String(info.priceWithTax);
            } catch(e) {}
        }
        // class tabanlı
        const sels = [
            '[class*="article-tile__price"] [class*="price__regular"]',
            '[class*="article-tile__price"]',
            '[class*="price--regular"]', '[class*="price__regular"]',
            '[class*="price-regular"]',  '[class*="regular-price"]',
            '[class*="price--actual"]',  '[class*="actual-price"]',
            '[class*="price"][class*="current"]',
            '.price', '[class*="price"]',
        ];
        for(const s of sels) {
            try {
                const pe = el.querySelector(s);
                if(pe) {
                    const t = pe.textContent.trim();
                    if(/\\d+[.,]\\d{2}/.test(t)) return t;
                }
            } catch(e) {}
        }
        return '';
    }

    function extractName(el) {
        // data-article'dan
        const raw = el.getAttribute('data-article');
        if(raw) {
            try {
                const d = JSON.parse(raw.replace(/&quot;/g,'"'));
                const n = (d.productInfo||{}).productName;
                if(n) return n;
            } catch(e) {}
        }
        const sels = [
            '[class*="article-tile__name"]', '[class*="article-tile__title"]',
            '[class*="article__name"]', '[class*="article__title"]',
            '[class*="product-name"]', '[class*="product-title"]',
            'h2', 'h3', 'h4',
            '[class*="name"]', '[class*="title"]',
        ];
        for(const s of sels) {
            try {
                const ne = el.querySelector(s);
                if(ne) {
                    const t = ne.textContent.trim();
                    if(t.length > 2) return t;
                }
            } catch(e) {}
        }
        // img alt fallback
        const img = el.querySelector('img[alt]');
        if(img) {
            const a = (img.getAttribute('alt')||'').trim();
            if(a.length > 2 && !/^\\d/.test(a)) return a;
        }
        return '';
    }

    function extractPid(el) {
        // data-article
        const raw = el.getAttribute('data-article');
        if(raw) {
            try {
                const d = JSON.parse(raw.replace(/&quot;/g,'"'));
                const pid = String((d.productInfo||{}).productID||'').trim();
                if(pid) return pid;
            } catch(e) {}
        }
        // data attrs
        for(const a of ['data-product-id','data-sku','data-id','data-article-id']) {
            const v = el.getAttribute(a);
            if(v && v.trim()) return v.trim();
        }
        // URL'den
        const lnk = el.querySelector('a[href]');
        if(lnk) {
            const href = lnk.getAttribute('href')||'';
            const m = href.match(/\/([a-z0-9_-]{5,})\\.html/i);
            if(m) return m[1];
        }
        return '';
    }

    function extractImage(el) {
        const raw = el.getAttribute('data-article');
        if(raw) {
            try {
                const d = JSON.parse(raw.replace(/&quot;/g,'"'));
                const img = (d.productInfo||{}).imageUrl;
                if(img) return img;
            } catch(e) {}
        }
        const imgEl = el.querySelector('img[data-src],img[src]');
        if(imgEl) return imgEl.getAttribute('data-src')||imgEl.getAttribute('src')||'';
        return '';
    }

    function extractPromo(el) {
        const raw = el.getAttribute('data-article');
        if(raw) {
            try {
                const d = JSON.parse(raw.replace(/&quot;/g,'"'));
                const info = d.productInfo || {};
                return {
                    inPromo: !!info.inPromotion,
                    promoPrice: info.promoPrice||info.strikePrice||null,
                    brand: info.brand||'',
                    category: (d.productCategory||{}).primaryCategory||'',
                    promoFrom: info.promotionStartDate||info.promotionDate||null,
                    promoUntil: info.promotionEndDate||null,
                };
            } catch(e) {}
        }
        const inPromo = !!el.querySelector(
            '[class*="promo"],[class*="actie"],[class*="korting"],[class*="promotion"],[class*="badge"]'
        );
        return {inPromo, promoPrice:null, brand:'', category:'', promoFrom:null, promoUntil:null};
    }

    // ── Strateji 1: tile containers ──────────────────────────────────────────
    const tileSels = [
        '[class*="article-tile"]',
        '[class*="article__tile"]',
        '[class*="ArticleTile"]',
        '[class*="product-item"]',
    ];
    for(const tsel of tileSels) {
        let tiles; try{tiles=document.querySelectorAll(tsel);}catch(e){continue;}
        if(tiles.length < 2) continue;
        tiles.forEach(el => {
            // Sadece en dıştaki tile'ı al (iç içe olanları atla)
            if(el.closest(tsel + ' ' + tsel)) return;
            const pid = extractPid(el);
            const name = extractName(el);
            const key = pid || name.slice(0,60);
            if(!key || seen.has(key)) return;
            seen.add(key);
            const price = extractPriceText(el);
            const promo = extractPromo(el);
            const image = extractImage(el);
            out.push({
                pid: key, name, brand: promo.brand,
                price, promoPrice: promo.promoPrice,
                inPromo: promo.inPromo, category: promo.category,
                image, promoFrom: promo.promoFrom, promoUntil: promo.promoUntil,
            });
        });
        if(out.length > 0) break;
    }

    // ── Strateji 2: eski data-article (lazy-load sonrası hâlâ çalışan sayfalar) ─
    if(out.length === 0) {
        document.querySelectorAll('[data-article]').forEach(el => {
            try {
                const raw = el.getAttribute('data-article');
                if(!raw) return;
                const data = JSON.parse(raw.replace(/&quot;/g,'"'));
                const info = data.productInfo || {};
                const cat  = data.productCategory || {};
                const pid  = String(info.productID || '').trim();
                if(!pid || seen.has(pid)) return;
                seen.add(pid);
                out.push({
                    pid, name: info.productName||'', brand: info.brand||'',
                    price: String(info.priceWithTax||''),
                    promoPrice: info.promoPrice||info.strikePrice||null,
                    inPromo: !!info.inPromotion,
                    category: cat.primaryCategory||'',
                    image: info.imageUrl||'',
                    promoFrom: info.promotionStartDate||info.promotionDate||null,
                    promoUntil: info.promotionEndDate||null,
                });
            } catch(e) {}
        });
    }

    return out;
}
"""


def dom_urun_ekle(tiles: list, hedef: Dict, kat: str) -> int:
    yeni = 0
    for t in tiles:
        pid = str(t.get("pid") or "").strip()
        if not pid or pid in hedef:
            continue
        price = fiyat_parse(t.get("price"))
        promo_price = fiyat_parse(t.get("promoPrice"))
        if promo_price and price and promo_price >= price:
            promo_price = None
        in_promo = bool(t.get("inPromo")) or promo_price is not None
        hedef[pid] = {
            "aldiPid":         pid,
            "name":            str(t.get("name") or "")[:300],
            "brand":           str(t.get("brand") or "")[:120],
            "topCategoryName": (str(t.get("category") or "") or kat)[:200],
            "basicPrice":      price,
            "promoPrice":      promo_price,
            "inPromo":         in_promo,
            "promoValidFrom":  to_iso_date(t.get("promoFrom")),
            "promoValidUntil": to_iso_date(t.get("promoUntil")),
            "imageUrl":        str(t.get("image") or "")[:400],
        }
        yeni += 1
    return yeni


# ─── window.__NEXT_DATA__ ve embedded JSON ────────────────────────────────────
def embedded_json_tara(page, hedef: Dict, kat: str) -> int:
    yeni = 0
    scripts_to_check = [
        "() => { try { return JSON.stringify(window.__NEXT_DATA__ || null); } catch(e){return null;} }",
        "() => { try { return JSON.stringify(window.__NUXT__ || null); } catch(e){return null;} }",
        "() => { try { return JSON.stringify(window.__APP_STATE__ || null); } catch(e){return null;} }",
        "() => { try { return JSON.stringify(window.__INITIAL_STATE__ || null); } catch(e){return null;} }",
        "() => { try { return JSON.stringify(window.digitalData || null); } catch(e){return null;} }",
        "() => { try { return JSON.stringify(window.dataLayer || null); } catch(e){return null;} }",
        # Inline script tag'lerden büyük JSON blokları
        """() => {
            const scripts = document.querySelectorAll('script[type="application/json"], script:not([src])');
            const out = [];
            scripts.forEach(s => {
                const t = (s.textContent||'').trim();
                if(t.length > 500 && (t.startsWith('{') || t.startsWith('['))) {
                    out.push(t.slice(0, 500000));
                }
            });
            return out.length ? JSON.stringify(out) : null;
        }""",
    ]
    for expr in scripts_to_check:
        try:
            raw = page.evaluate(expr)
            if not raw or raw == "null":
                continue
            if isinstance(raw, str):
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
            elif isinstance(raw, list):
                # Inline script listesi
                for item in raw:
                    try:
                        data = json.loads(item)
                        n = json_urunleri_cikart(data, kat, hedef)
                        yeni += n
                    except Exception:
                        pass
                continue
            else:
                data = raw
            n = json_urunleri_cikart(data, kat, hedef)
            yeni += n
        except Exception:
            continue
    return yeni


# ─── Network interception pool ────────────────────────────────────────────────
def network_handler_olustur(pool: List[dict], kat_ad: str):
    def on_response(response):
        try:
            url = response.url
            if "aldi.be" not in url and "aldi-service" not in url:
                return
            # Görseller, fontlar, CSS atla
            if re.search(r"\.(png|jpg|gif|svg|ico|woff|css|mp4|webp)(\?|$)", url, re.I):
                return
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = response.body()
            if len(body) < 200:
                return
            data = json.loads(body)
            pool.append({"url": url, "data": data, "kat": kat_ad})
        except Exception:
            pass
    return on_response


# ─── Checkpoint ───────────────────────────────────────────────────────────────
def checkpoint_yukle() -> Tuple[Dict, set]:
    if CHECKPOINT.exists():
        try:
            with open(CHECKPOINT, encoding="utf-8") as f:
                data = json.load(f)
            urunler       = {p["aldiPid"]: p for p in data.get("urunler", [])}
            tamamlananlar = set(data.get("tamamlanan_urls", []))
            print(f"[checkpoint] {len(urunler)} ürün, {len(tamamlananlar)} kategori")
            return urunler, tamamlananlar
        except Exception as e:
            print(f"[checkpoint hata] {e}")
    return {}, set()


def checkpoint_kaydet(urunler: Dict, tamamlananlar: set):
    CIKTI_DIR.mkdir(exist_ok=True)
    try:
        with open(CHECKPOINT, "w", encoding="utf-8") as f:
            json.dump({
                "son_guncelleme":  datetime.now().isoformat(),
                "urun_sayisi":     len(urunler),
                "tamamlanan_urls": list(tamamlananlar),
                "urunler":         list(urunler.values()),
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[checkpoint kayıt hata] {e}")


# ─── Cookie kabul ─────────────────────────────────────────────────────────────
def cookie_kabul(page):
    for sel in (
        "#onetrust-accept-btn-handler",
        'button:has-text("Akkoord")',
        'button:has-text("Accepteer")',
        'button:has-text("Alle cookies")',
        'button:has-text("Accepteren")',
        'button:has-text("Alles accepteren")',
        '[data-testid="cookie-accept"]',
    ):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1800):
                insan_tiklama(page, loc)
                sl(1.8, 0.7, 0.8, 4.0)
                return
        except Exception:
            pass


# ─── Cloudflare tespiti ───────────────────────────────────────────────────────
def cloudflare_var_mi(page) -> bool:
    title = (page.title() or "").lower()
    return any(x in title for x in ("cloudflare", "attention required",
                                     "just a moment", "checking your"))


# ─── Ana çekim ────────────────────────────────────────────────────────────────
def calistir(test: bool = False, resume: bool = False,
             no_pause: bool = False, diag: bool = False,
             proxy: str = None, kat: str = None) -> int:
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        print("HATA: pip install camoufox && python -m camoufox fetch")
        return 1

    CIKTI_DIR.mkdir(exist_ok=True)
    _stop.sinyal_kaydet(_log)

    proxiler = proxy_yukle() if not proxy else [proxy]
    _log.info(f"Proxy: {proxiler[0][:40] if proxiler[0] else 'yok'}")

    urunler, tamamlananlar = checkpoint_yukle() if resume else ({}, set())
    if kat:
        kategoriler = [(n, u) for n, u in KATEGORILER if kat.lower() in n.lower()]
        if not kategoriler:
            print(f"HATA: '{kat}' adında kategori bulunamadı. Mevcut kategoriler:")
            for n, _ in KATEGORILER:
                print(f"  {n}")
            return 1
    elif test:
        kategoriler = KATEGORILER[:3]
    else:
        kategoriler = KATEGORILER

    api_pool: List[dict] = []

    with Camoufox(
        headless=False,
        firefox_user_prefs={
            "browser.startup.page":                   0,
            "browser.sessionstore.resume_from_crash": False,
            "browser.sessionstore.enabled":           False,
        },
    ) as browser:
        page = browser.new_page()
        sl(2.5, 0.9, 1.5, 5.0)

        def goto_safe(url: str) -> bool:
            if _stop.dur:
                return False
            for deneme in range(3):
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    sl(3.5, 1.2, 1.8, 8.0)

                    if resp:
                        eylem = http_durum_isle(resp.status, url, _log)
                        if eylem == "dur":
                            _stop.durdur()
                            return False
                        if eylem == "backoff":
                            backoff_bekle(deneme, _log)
                            continue

                    if cloudflare_var_mi(page) or ban_tespit(page, _log):
                        _log.warning("CF/Ban — bekleniyor…")
                        sl(22.0, 7.0, 12.0, 45.0)
                        if cloudflare_var_mi(page) or ban_tespit(page, _log):
                            _log.error("Hâlâ bloklu.")
                            return False
                    return True
                except Exception as e:
                    _log.warning(f"goto {deneme+1}/3: {str(e)[:80]}")
                    backoff_bekle(deneme, _log)
            return False

        # İlk açılış
        print("\n[0] İlk açılış, cookie alınıyor…")
        if goto_safe(f"{BASE}/nl/"):
            cookie_kabul(page)
            insan_scroll(page, int(random.gauss(900, 300)))
            sl(2.0, 0.8, 1.0, 5.0)

        # Network handler ekle — tüm kategoriler için aktif
        def on_response(response):
            try:
                url = response.url
                if "aldi.be" not in url:
                    return
                if re.search(r"\.(png|jpg|gif|svg|ico|woff|css|mp4|webp)(\?|$)", url, re.I):
                    return
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                body = response.body()
                if len(body) < 200:
                    return
                data = json.loads(body)
                api_pool.append({"url": url, "data": data})
            except Exception:
                pass

        page.on("response", on_response)

        kalan = [(a, b) for a, b in kategoriler if b not in tamamlananlar]
        tamamlanan_onceden = len([b for _, b in kategoriler if b in tamamlananlar])

        mola_sayaci = 0
        for i, (kat_ad, url) in enumerate(kalan):
            if _stop.dur:
                _log.info("Durdurma bayrağı — döngü sonlandırılıyor.")
                break

            global_i = i + tamamlanan_onceden + 1

            # Kategoriler arası bekleme
            if i > 0:
                mola_sayaci += 1
                if mola_sayaci >= random.randint(8, 12):
                    mola_sayaci = 0
                    mola = rg(60.0, 25.0, 30.0, 150.0)
                    print(f"\n  ═══ Oturum molası {mola:.0f}s (toplam={len(urunler)}) ═══")
                    time.sleep(mola)
                else:
                    bekle = rg(12.0, 5.0, 5.0, 35.0)
                    if random.random() < 0.07:
                        bekle = rg(50.0, 20.0, 25.0, 110.0)
                        print(f"\n  … Uzun bekleme {bekle:.0f}s …")
                    time.sleep(bekle)

            print(f"\n[{global_i}/{len(kategoriler)}] {kat_ad}")
            api_pool.clear()

            if not goto_safe(url):
                print("  [atlandı — yüklenemedi]")
                continue

            baslik = page.title()
            if "404" in baslik or "niet gevonden" in baslik.lower():
                print(f"  [404] {baslik[:60]} — atlandı")
                tamamlananlar.add(url)
                checkpoint_kaydet(urunler, tamamlananlar)
                continue

            print(f"  -> {page.url[:80]}  [{baslik[:50]}]")

            if diag:
                _diagnostic(page, kat_ad)
                continue

            onceki = len(urunler)

            def urunleri_topla():
                # Network API
                for entry in list(api_pool):
                    json_urunleri_cikart(entry["data"], kat_ad, urunler)
                api_pool.clear()
                # JSON-LD
                jsonld_tiles = jsonld_urun_cikart(page)
                for tile in jsonld_tiles:
                    key = tile.get("barcode") or tile.get("url") or tile.get("name", "")[:80]
                    if key and key not in urunler:
                        urunler[key] = {
                            "aldiPid": key, "name": tile.get("name","")[:300],
                            "brand": tile.get("brand","")[:120],
                            "topCategoryName": kat_ad[:200],
                            "basicPrice": tile.get("price"), "promoPrice": None,
                            "inPromo": False, "promoValidFrom": None,
                            "promoValidUntil": None, "imageUrl": tile.get("image_url","")[:400],
                        }
                # Embedded JSON
                embedded_json_tara(page, urunler, kat_ad)
                # DOM (article-tile)
                try:
                    tiles = page.evaluate(_DOM_JS)
                    dom_urun_ekle(tiles, urunler, kat_ad)
                except Exception:
                    pass

            # 1. tur scroll: insan gibi, lazy-load tetikle
            insan_scroll(page, int(random.gauss(2500, 700)))
            sl(1.5, 0.6, 0.7, 4.0)
            urunleri_topla()

            # 2. tur: az ürün geldiyse sayfa sonuna git ve bekle
            if len(urunler) - onceki < 5:
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    sl(2.5, 1.0, 1.5, 6.0)
                    urunleri_topla()
                    if len(urunler) - onceki >= 5:
                        break
                    # Scroll başa dönüp tekrar aşağı (lazy-load farklı tetikler)
                    page.evaluate("window.scrollTo(0, 0)")
                    sl(1.0, 0.4, 0.5, 2.5)
                    insan_scroll(page, int(random.gauss(3000, 800)))
                    sl(2.0, 0.8, 1.0, 5.0)
                    urunleri_topla()
                    if len(urunler) - onceki >= 5:
                        break

            # Eğer hâlâ az ürün geldiyse ekstra scroll tur
            if len(urunler) - onceki < 5:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                sl(2.5, 1.0, 1.2, 6.0)
                for entry in list(api_pool):
                    json_urunleri_cikart(entry["data"], kat_ad, urunler)
                api_pool.clear()
                embedded_json_tara(page, urunler, kat_ad)
                try:
                    tiles = page.evaluate(_DOM_JS)
                    dom_urun_ekle(tiles, urunler, kat_ad)
                except Exception:
                    pass

            yeni = len(urunler) - onceki

            # 0 ürün geldiyse -> hub sayfa olabilir, alt kategori linklerini tara
            if yeni == 0:
                alt_urls = page.evaluate("""
                    () => {
                        const links = new Set();
                        document.querySelectorAll('a[href]').forEach(a => {
                            const h = a.href || '';
                            if(h.includes('/producten/assortiment/') &&
                               h.endsWith('.html') &&
                               !h.includes('#')) {
                                links.add(h.split('?')[0]);
                            }
                        });
                        return Array.from(links);
                    }
                """) or []
                # Zaten ziyaret edilenleri çıkar
                alt_urls = [u for u in alt_urls
                            if u not in tamamlananlar and u != url][:20]
                if alt_urls:
                    _log.info(f"  Hub sayfa: {len(alt_urls)} alt kategori bulundu")
                    for j, alt_url in enumerate(alt_urls):
                        if _stop.dur:
                            break
                        sl(rg(8.0, 3.5, 4.0, 20.0), 0)
                        _log.info(f"    [{j+1}/{len(alt_urls)}] {alt_url.split('/')[-1]}")
                        if not goto_safe(alt_url):
                            continue
                        if "404" in page.title() or "niet gevonden" in page.title().lower():
                            continue
                        api_pool.clear()
                        insan_scroll(page, int(random.gauss(2200, 600)))
                        sl(1.5, 0.6, 0.7, 4.0)
                        urunleri_topla()
                        if len(urunler) - onceki - yeni < 3:
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            sl(2.5, 1.0, 1.2, 5.0)
                            urunleri_topla()
                        tamamlananlar.add(alt_url)
                        sub_yeni = len(urunler) - onceki - yeni
                        yeni = len(urunler) - onceki
                        _log.info(f"      +{sub_yeni} ürün")

            print(f"  +{yeni} ürün | Toplam: {len(urunler)}")

            tamamlananlar.add(url)
            checkpoint_kaydet(urunler, tamamlananlar)

            # %5 ihtimalle kısa mola
            if random.random() < 0.05:
                mola = rg(12.0, 5.0, 5.0, 30.0)
                print(f"  [~] Kısa mola {mola:.0f}s…")
                time.sleep(mola)

    if diag:
        print("\n[diag] Tamamlandı.")
        return 0

    # ── Final kayıt ───────────────────────────────────────────────────────────
    tarih        = datetime.now().strftime("%Y-%m-%d_%H-%M")
    urun_listesi = list(urunler.values())
    cikti_dosya  = CIKTI_DIR / f"aldi_be_v2_{tarih}.json"

    with open(cikti_dosya, "w", encoding="utf-8") as f:
        json.dump({
            "kaynak":         "Aldi BE v2 — camoufox + Network Interception",
            "chain_slug":     "aldi_be",
            "country_code":   "BE",
            "cekilme_tarihi": datetime.now().isoformat(),
            "urun_sayisi":    len(urun_listesi),
            "urunler":        urun_listesi,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"TAMAM: {len(urun_listesi)} ürün -> {cikti_dosya}")
    print(f"{'='*60}")

    try:
        CHECKPOINT.unlink(missing_ok=True)
    except Exception:
        pass

    if not no_pause:
        input("\nÇıkmak için Enter…")
    return 0


def _diagnostic(page, kat_ad: str):
    """Site yapısını analiz et — selectors, API URL'leri, embedded JSON."""
    print(f"\n  [DIAG] {kat_ad}")
    result = page.evaluate("""
    () => {
        const sels = ['[data-article]','[data-product]','[data-item]','[data-sku]',
                      '[data-product-id]','[class*="ProductCard"]','[class*="product-card"]',
                      '[class*="ProductTile"]','[class*="product-tile"]',
                      '[class*="article-tile"]','li[class*="product"]'];
        const counts = {};
        sels.forEach(s => { try{counts[s]=document.querySelectorAll(s).length;}catch(e){} });
        const wvars = [];
        ['__NEXT_DATA__','__NUXT__','__APP_STATE__','__INITIAL_STATE__','dataLayer'].forEach(v=>{
            try{const d=eval(v);if(d)wvars.push({var:v,len:JSON.stringify(d).length});}catch(e){}
        });
        return {counts,wvars};
    }
    """)
    counts = {k: v for k, v in result["counts"].items() if v > 0}
    print(f"    Selectors: {counts}")
    print(f"    Window vars: {result['wvars']}")


def main():
    ap = argparse.ArgumentParser(description="Aldi BE tam katalog v2")
    ap.add_argument("--test",     action="store_true", help="İlk 3 kategori")
    ap.add_argument("--resume",   action="store_true", help="Checkpoint'ten devam")
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument("--diag",     action="store_true", help="Sadece DOM/API analizi")
    ap.add_argument("--proxy",    type=str, default=None, help="Proxy URL")
    ap.add_argument("--kat",      type=str, default=None, help="Tek kategori adı (örn: vlees)")
    args = ap.parse_args()
    return calistir(test=args.test, resume=args.resume,
                    no_pause=args.no_pause, diag=args.diag, proxy=args.proxy, kat=args.kat)


if __name__ == "__main__":
    raise SystemExit(main())
