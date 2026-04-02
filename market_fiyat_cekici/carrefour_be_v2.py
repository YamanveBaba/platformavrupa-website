# -*- coding: utf-8 -*-
"""
Carrefour BE — Tam Katalog Çekici v2
Özellikler:
  ✓ İnsan gibi davranış: gaussian bekleme, bezier mouse, değişken scroll
  ✓ Oturum simülasyonu: her 10-14 kategoride uzun mola
  ✓ Checkpoint: crash → --resume ile kaldığı yerden devam
  ✓ Akıllı redirect tespiti: az ürün + farklı URL → alternatif URL dene
  ✓ Cloudflare tespiti: bloklandığında otomatik bekle
  ✓ Çoklu DOM stratejisi: SFCC + Verbolia + generic fallback
  ✓ Einstein JSON yakalama

Kullanım:
  python carrefour_be_v2.py              # tam çekim
  python carrefour_be_v2.py --test       # ilk 3 kategori
  python carrefour_be_v2.py --resume     # checkpoint'ten devam
  python carrefour_be_v2.py --no-pause   # Enter bekleme yok
"""
from __future__ import annotations
import argparse, json, re, time, random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from scraper_utils import (
    log_olustur, ban_tespit, backoff_bekle, StopSinyali,
    jsonld_urun_cikart, proxy_yukle, robotstxt_kontrol, http_durum_isle,
)

_log  = log_olustur("carrefour_be")
_stop = StopSinyali()

# ─── Dizinler ─────────────────────────────────────────────────────────────────
script_dir = Path(__file__).parent
CIKTI_DIR  = script_dir / "cikti"
CHECKPOINT = CIKTI_DIR  / "carrefour_v2_checkpoint.json"
BASE       = "https://www.carrefour.be"

# ─── Kategoriler: (url, ad, [alternatifler]) ──────────────────────────────────
# Alternatifler: az ürün/yanlış redirect durumunda denenecek URL'ler
KATEGORILER: List[Tuple[str, str, List[str]]] = [
    (f"{BASE}/nl/al-onze-promoties",       "Promoties",      []),
    (f"{BASE}/nl/vb/melk-kopen",           "Melk",           [f"{BASE}/nl/vb/melk"]),
    (f"{BASE}/nl/vb/brood-kopen",          "Brood",          [f"{BASE}/nl/vb/brood"]),
    (f"{BASE}/nl/vb/vlees-kopen",          "Vlees",          [f"{BASE}/nl/vb/vlees"]),
    (f"{BASE}/nl/vb/vis-kopen",            "Vis",            [f"{BASE}/nl/vb/vis", f"{BASE}/nl/vb/visproducten-kopen"]),
    (f"{BASE}/nl/vb/groenten-kopen",       "Groenten",       [f"{BASE}/nl/vb/groenten", f"{BASE}/nl/vb/verse-groenten-kopen"]),
    (f"{BASE}/nl/vb/fruit-kopen",          "Fruit",          [f"{BASE}/nl/vb/fruit", f"{BASE}/nl/vb/vers-fruit-kopen"]),
    (f"{BASE}/nl/vb/kaas-kopen",           "Kaas",           [f"{BASE}/nl/vb/kaas"]),
    (f"{BASE}/nl/vb/yoghurt-kopen",        "Yoghurt",        [f"{BASE}/nl/vb/yoghurt", f"{BASE}/nl/vb/yoghurts"]),
    (f"{BASE}/nl/vb/eieren-kopen",         "Eieren",         [f"{BASE}/nl/vb/eieren"]),
    (f"{BASE}/nl/vb/pasta-kopen",          "Pasta",          [f"{BASE}/nl/vb/pasta", f"{BASE}/nl/vb/spaghetti-kopen"]),
    (f"{BASE}/nl/vb/rijst-kopen",          "Rijst",          [f"{BASE}/nl/vb/rijst"]),
    (f"{BASE}/nl/vb/soep-kopen",           "Soep",           [f"{BASE}/nl/vb/soep"]),
    (f"{BASE}/nl/vb/sauzen-kopen",         "Sauzen",         [f"{BASE}/nl/vb/sauzen"]),
    (f"{BASE}/nl/vb/koffie-kopen",         "Koffie",         [f"{BASE}/nl/vb/koffie"]),
    (f"{BASE}/nl/vb/thee-kopen",           "Thee",           [f"{BASE}/nl/vb/thee"]),
    (f"{BASE}/nl/vb/water-kopen",          "Water",          [f"{BASE}/nl/vb/water"]),
    (f"{BASE}/nl/vb/frisdrank-kopen",      "Frisdrank",      [f"{BASE}/nl/vb/frisdrank"]),
    (f"{BASE}/nl/vb/bier-kopen",           "Bier",           [f"{BASE}/nl/vb/bier"]),
    (f"{BASE}/nl/vb/wijn-kopen",           "Wijn",           [f"{BASE}/nl/vb/wijn"]),
    (f"{BASE}/nl/vb/chips-kopen",          "Chips",          [f"{BASE}/nl/vb/chips"]),
    (f"{BASE}/nl/vb/koeken-kopen",         "Koeken",         [f"{BASE}/nl/vb/koek"]),
    (f"{BASE}/nl/vb/chocolade-kopen",      "Chocolade",      [f"{BASE}/nl/vb/chocolade"]),
    (f"{BASE}/nl/vb/snoep-kopen",          "Snoep",          [f"{BASE}/nl/vb/snoep"]),
    (f"{BASE}/nl/vb/ijs-kopen",            "IJs",            [f"{BASE}/nl/vb/ijs"]),
    (f"{BASE}/nl/vb/diepvries-kopen",      "Diepvries",      [f"{BASE}/nl/vb/diepvries"]),
    (f"{BASE}/nl/vb/babyvoeding-kopen",    "Babyvoeding",    [f"{BASE}/nl/vb/babyvoeding"]),
    (f"{BASE}/nl/vb/luiers-kopen",         "Luiers",         [f"{BASE}/nl/vb/luiers"]),
    (f"{BASE}/nl/vb/wasmiddel-kopen",      "Wasmiddel",      [f"{BASE}/nl/vb/wasmiddel"]),
    (f"{BASE}/nl/vb/schoonmaak-kopen",     "Schoonmaak",     [f"{BASE}/nl/vb/schoonmaakmiddelen-kopen",
                                                               f"{BASE}/nl/vb/reinigingsmiddelen-kopen"]),
    (f"{BASE}/nl/vb/tandpasta-kopen",      "Tandpasta",      [f"{BASE}/nl/vb/tandpasta"]),
    (f"{BASE}/nl/vb/shampoo-kopen",        "Shampoo",        [f"{BASE}/nl/vb/shampoo"]),
    (f"{BASE}/nl/vb/kattenvoer-kopen",     "Kattenvoer",     [f"{BASE}/nl/vb/kattenvoer"]),
    (f"{BASE}/nl/vb/hondenvoer-kopen",     "Hondenvoer",     [f"{BASE}/nl/vb/hondenvoer"]),
    (f"{BASE}/nl/vb/ontbijtgranen-kopen",  "Ontbijtgranen",  [f"{BASE}/nl/vb/ontbijtgranen"]),
    (f"{BASE}/nl/vb/confituur-kopen",      "Confituur",      [f"{BASE}/nl/vb/confituur"]),
    (f"{BASE}/nl/vb/olie-kopen",           "Olie",           [f"{BASE}/nl/vb/olie"]),
    (f"{BASE}/nl/vb/azijn-kopen",          "Azijn",          [f"{BASE}/nl/vb/azijn"]),
    (f"{BASE}/nl/vb/noten-kopen",          "Noten",          [f"{BASE}/nl/vb/noten"]),
    (f"{BASE}/nl/vb/snacks-kopen",         "Snacks",         [f"{BASE}/nl/vb/snacks"]),
    (f"{BASE}/nl/vb/dranken-kopen",        "Dranken",        [f"{BASE}/nl/vb/drank-kopen"]),
    (f"{BASE}/nl/vb/zuivel-kopen",         "Zuivel",         [f"{BASE}/nl/vb/zuivel", f"{BASE}/nl/vb/zuivelproducten-kopen"]),
    (f"{BASE}/nl/vb/charcuterie-kopen",    "Charcuterie",    [f"{BASE}/nl/vb/charcuterie"]),
    (f"{BASE}/nl/vb/huishouden-kopen",     "Huishouden",     [f"{BASE}/nl/vb/huishoudproducten-kopen"]),
    (f"{BASE}/nl/vb/verzorging-kopen",     "Verzorging",     [f"{BASE}/nl/vb/lichaamsverzorging-kopen",
                                                               f"{BASE}/nl/vb/persoonlijke-verzorging-kopen"]),
    (f"{BASE}/nl/vb/elektronica-kopen",    "Elektronica",    [f"{BASE}/nl/vb/elektrische-apparaten-kopen"]),
    (f"{BASE}/nl/vb/speelgoed-kopen",      "Speelgoed",      [f"{BASE}/nl/vb/speelgoed"]),
    (f"{BASE}/nl/vb/sport-kopen",          "Sport",          [f"{BASE}/nl/vb/sportartikelen-kopen"]),
    (f"{BASE}/nl/vb/tuin-kopen",           "Tuin",           [f"{BASE}/nl/vb/tuin"]),
    (f"{BASE}/nl/vb/voeding-kopen",        "Voeding",        [f"{BASE}/nl/vb/verse-producten-kopen"]),
    (f"{BASE}/nl/vb/verse-producten-kopen","Verse producten",[f"{BASE}/nl/vb/verse-producten"]),
    (f"{BASE}/nl/vb/dieren-kopen",         "Dieren",         [f"{BASE}/nl/vb/dierenvoeding-kopen"]),
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


# ─── Fiyat normalize ──────────────────────────────────────────────────────────
def fiyat_al(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    try:
        return round(float(re.sub(r"[^\d.]", "", str(v).replace(",", "."))), 2)
    except Exception:
        return None


# ─── İnsan davranışı ──────────────────────────────────────────────────────────
def insan_scroll(page, toplam_px: int = 1800):
    """
    Mouse wheel ile insan gibi scroll:
    değişken chunk boyutu, okuma duraklamaları, bazen geri scroll.
    """
    kaydirilan = 0
    while kaydirilan < toplam_px:
        chunk = int(random.gauss(180, 80))
        chunk = max(60, min(450, chunk))
        chunk = min(chunk, toplam_px - kaydirilan)

        page.mouse.wheel(0, chunk)
        kaydirilan += chunk

        sl(0.13, 0.06, 0.04, 0.45)

        # %25 olasılıkla okuma duraklaması
        if random.random() < 0.25:
            sl(2.0, 1.0, 0.5, 6.0)

        # %8 olasılıkla geri scroll (dikkati dağınık insan)
        if random.random() < 0.08:
            geri = int(random.gauss(120, 60))
            geri = max(30, min(200, geri))
            page.mouse.wheel(0, -geri)
            sl(0.7, 0.3, 0.2, 2.5)
            kaydirilan = max(0, kaydirilan - geri)


def insan_mouse_hareket(page, hedef_x: float, hedef_y: float):
    """
    Mouse'u bezier eğrisi üzerinde hedef koordinata götür.
    """
    try:
        vp = page.viewport_size or {"width": 1280, "height": 720}
        sx = random.uniform(80, vp["width"] - 80)
        sy = random.uniform(80, vp["height"] - 80)

        # Quadratic bezier kontrol noktası
        cx = random.uniform(min(sx, hedef_x), max(sx, hedef_x))
        cy = random.uniform(min(sy, hedef_y), max(sy, hedef_y))
        adim = random.randint(7, 16)

        for i in range(1, adim + 1):
            t = i / adim
            x = (1-t)**2 * sx + 2*(1-t)*t * cx + t**2 * hedef_x + random.gauss(0, 1.5)
            y = (1-t)**2 * sy + 2*(1-t)*t * cy + t**2 * hedef_y + random.gauss(0, 1.5)
            page.mouse.move(x, y)
            sl(0.022, 0.009, 0.006, 0.09)
    except Exception:
        pass


def insan_tiklama(page, locator) -> bool:
    """
    Butona insan gibi tıkla:
    scroll_into_view → mouse hareketi → hover → küçük bekleme → click
    """
    try:
        locator.scroll_into_view_if_needed(timeout=3000)
        sl(0.35, 0.18, 0.1, 1.2)

        box = locator.bounding_box(timeout=3000)
        if box:
            tx = box["x"] + box["width"] / 2 + random.gauss(0, 3)
            ty = box["y"] + box["height"] / 2 + random.gauss(0, 3)
            insan_mouse_hareket(page, tx, ty)
            sl(0.20, 0.09, 0.06, 0.7)

        locator.hover(timeout=3000)
        sl(0.25, 0.12, 0.08, 0.9)
        locator.click(timeout=10_000)
        return True
    except Exception:
        try:
            locator.click(timeout=10_000)
            return True
        except Exception:
            return False


# ─── DOM ürün çıkarma ─────────────────────────────────────────────────────────
_DOM_JS = """
() => {
    const out = [];
    const seen = new Set();

    function extractPrice(el) {
        // Verbolia
        const pEl = el.querySelector('.product-price');
        if (pEl) { const t=pEl.textContent.trim(); if(/\\d+[.,]\\d{2}/.test(t)) return t; }
        // SFCC attrs
        for (const a of ['data-price','data-sales-price','data-regular-price']) {
            const v = el.getAttribute(a); if(v&&/\\d/.test(v)) return v.trim();
        }
        // Class tabanlı
        const sels = ['.price .sales .value','[class*="price"] .value','.price__sales',
                      '.price-sales','.js-price-value','[class*="price--sales"]',
                      '[class*="actualPrice"]','[class*="current-price"]','strong[class*="price"]'];
        for (const s of sels) {
            try { const pe=el.querySelector(s); if(pe){const t=pe.textContent.trim();
                  if(/\\d+[.,]\\d{2}/.test(t)) return t; } } catch(e) {}
        }
        return '';
    }

    function extractName(el) {
        // 1. img alt (Verbolia çoğunlukla buraya koyar)
        const img = el.querySelector('img[alt]');
        if (img) { const a=(img.getAttribute('alt')||'').trim();
                   if(a.length>3 && !/^\\d/.test(a)) return a; }
        // 2. data attrs
        for (const a of ['data-name','data-product-name','data-title']) {
            const v=(el.getAttribute(a)||'').trim(); if(v.length>2) return v;
        }
        // 3. class tabanlı
        const nsels=['.product-name','[class*="product-name"]','.product-title',
                     '[class*="product-title"]','[class*="ProductName"]','h2','h3','h4'];
        for (const s of nsels) {
            try { const ne=el.querySelector(s); if(ne){const t=ne.textContent.trim();
                  if(t.length>2) return t;} } catch(e) {}
        }
        // 4. product-info içindeki metin (fiyat hariç)
        const info = el.querySelector('.product-info');
        if (info) {
            const priceText=(info.querySelector('.product-price')||{}).textContent||'';
            const cleaned=[...info.childNodes]
                .filter(n=>n.nodeType===3||(n.nodeType===1&&!(n.className||'').includes('price')))
                .map(n=>n.textContent.trim()).filter(Boolean).join(' ').trim();
            if(cleaned.length>3) return cleaned;
        }
        // 5. link title attr
        const lnk=el.querySelector('a');
        if(lnk){const t=lnk.getAttribute('title')||''; if(t.length>2) return t;}
        return '';
    }

    function extractId(el) {
        for (const a of ['data-pid','data-product-id','data-article-id','data-sku','data-id','data-item-id']) {
            const v=el.getAttribute(a); if(v) return v.trim();
        }
        const lnk=el.querySelector('a[href]');
        if(lnk){
            const m=(lnk.getAttribute('href')||'').match(/\\/(?:p|nl)\\/([^/?#]+\\.html)|\\/([0-9]{6,})/);
            if(m) return (m[1]||m[2]||'').replace('.html','');
        }
        return '';
    }

    // ── Strateji 1: SFCC [data-pid] ──────────────────────────────────────────
    document.querySelectorAll('[data-pid]').forEach(el => {
        const pid=el.getAttribute('data-pid')||'';
        if(!pid||seen.has(pid)) return;
        seen.add(pid);
        const price=el.getAttribute('data-price')||extractPrice(el);
        const name=el.getAttribute('data-name')||el.getAttribute('data-product-name')||extractName(el);
        const brand=el.getAttribute('data-brand')||'';
        const cat=el.getAttribute('data-category')||el.getAttribute('data-item-list-name')||'';
        const inPromo=!!el.querySelector('[class*="promo"],[class*="badge-promo"],[class*="promotion"],[class*="actie"]');
        const imgEl=el.querySelector('img[data-src],img[src]');
        const img=imgEl?(imgEl.getAttribute('data-src')||imgEl.getAttribute('src')||''):'';
        out.push({pid,price:price.trim().slice(0,60),name:name.trim().slice(0,300),
                  brand:brand.slice(0,100),cat:cat.slice(0,200),inPromo,img:img.slice(0,400)});
    });

    // ── Strateji 2: Verbolia a[data-id].single-product-desktop ───────────────
    if(out.length===0) {
        document.querySelectorAll('a[data-id][class*="single-product-desktop"]').forEach(el => {
            const pid=el.getAttribute('data-id')||'';
            if(!pid||seen.has(pid)) return;
            seen.add(pid);
            const price=extractPrice(el);
            const name=extractName(el);
            const inPromo=!!el.querySelector('[class*="promo"],[class*="actie"],[class*="korting"],[class*="promotion"],[class*="badge"]');
            const imgEl=el.querySelector('img[data-src],img[src]');
            const img=imgEl?(imgEl.getAttribute('data-src')||imgEl.getAttribute('src')||''):'';
            out.push({pid,price:price.slice(0,60),name:name.slice(0,300),
                      brand:'',cat:'',inPromo,img:img.slice(0,400)});
        });
    }

    // ── Strateji 3: Generic fallback ─────────────────────────────────────────
    if(out.length===0) {
        const csels=['[data-product-id]','[data-article-id]','[data-sku]',
                     '[class*="ProductCard"]','[class*="product-card"]',
                     '[class*="ProductTile"]','[class*="product-tile"]',
                     'article[class*="product"]','li[class*="product"]',
                     '[itemtype*="Product"]'];
        for(const cs of csels){
            let els; try{els=document.querySelectorAll(cs);}catch(e){continue;}
            if(els.length<2) continue;
            els.forEach(el=>{
                const pid=extractId(el);
                const lnk=el.querySelector('a');
                const key=pid||(lnk?(lnk.getAttribute('href')||''):'');
                if(!key||seen.has(key)) return;
                seen.add(key);
                const price=extractPrice(el); const name=extractName(el);
                const inPromo=!!el.querySelector('[class*="promo"],[class*="badge"],[class*="promotion"]');
                const imgEl=el.querySelector('img[data-src],img[src]');
                const img=imgEl?(imgEl.getAttribute('data-src')||imgEl.getAttribute('src')||''):'';
                out.push({pid:(pid||key).slice(0,200),price:price.trim().slice(0,60),
                          name:name.trim().slice(0,300),brand:'',cat:'',inPromo,img:img.slice(0,400)});
            });
            if(out.length>0) break;
        }
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
        price_raw = t.get("price") or ""
        floats = sorted(
            [f for f in [fiyat_al(p) for p in re.findall(r"\d+[.,]\d{1,2}", price_raw)] if f],
            reverse=True,
        )
        hedef[pid] = {
            "carrefourPid":    pid,
            "name":            t.get("name", "")[:300],
            "brand":           t.get("brand", "")[:120],
            "topCategoryName": (t.get("cat") or kat)[:200],
            "basicPrice":      floats[0] if floats else None,
            "promoPrice":      floats[1] if len(floats) > 1 else None,
            "inPromo":         bool(t.get("inPromo")) or len(floats) > 1,
            "imageUrl":        t.get("img", "")[:400],
        }
        yeni += 1
    return yeni


# ─── "Meer tonen" buton tıklama ──────────────────────────────────────────────
MEER_SELS = [
    'button:has-text("Meer tonen")', 'button:has-text("Toon meer")',
    'button:has-text("Laad meer")', 'button:has-text("meer producten")',
    'button:has-text("Meer producten")', 'button:has-text("Load more")',
    'a:has-text("Meer tonen")', 'a:has-text("Toon meer")',
    '.load-more button', '.btn-load-more',
    '[class*="load-more"] button', '[class*="LoadMore"] button',
    '[class*="show-more"] button', '[data-testid*="load-more"]',
    '.infinite-scroll-placeholder button',
]


def meer_toon_tikla(page) -> bool:
    """'Meer tonen' butonunu bulur, insan gibi tıklar."""
    for sel in MEER_SELS:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1200):
                return insan_tiklama(page, loc)
        except Exception:
            continue

    # JS ile tara — butonu scroll_into_view ile göster, sonra Playwright ile tıkla
    try:
        found = page.evaluate("""
            () => {
                const pats=[/meer tonen/i,/toon meer/i,/laad meer/i,
                             /meer producten/i,/load more/i,/show more/i];
                for(const btn of [...document.querySelectorAll('button,a[role="button"],a.btn')]){
                    if(btn.offsetParent===null) continue;
                    if(pats.some(p=>p.test((btn.textContent||'').trim()))){
                        btn.scrollIntoView({behavior:'smooth',block:'center'});
                        return true;
                    }
                }
                return false;
            }
        """)
        if found:
            sl(0.6, 0.25, 0.2, 1.8)
            for sel in MEER_SELS[:8]:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0:
                        return insan_tiklama(page, loc)
                except Exception:
                    pass
    except Exception:
        pass
    return False


# ─── Cloudflare tespiti ───────────────────────────────────────────────────────
def cloudflare_var_mi(page) -> bool:
    title = (page.title() or "").lower()
    return any(x in title for x in ("cloudflare", "attention required",
                                     "just a moment", "checking your"))


# ─── Yanlış redirect tespiti ──────────────────────────────────────────────────
def redirect_sorunlu_mu(hedef_url: str, final_url: str, urun_sayisi: int) -> bool:
    """Az ürün VE URL değişti → sorunlu redirect."""
    if urun_sayisi >= 15:
        return False
    return urlparse(hedef_url).path != urlparse(final_url).path


# ─── Checkpoint ───────────────────────────────────────────────────────────────
def checkpoint_yukle() -> Tuple[Dict, set]:
    if CHECKPOINT.exists():
        try:
            with open(CHECKPOINT, encoding="utf-8") as f:
                data = json.load(f)
            urunler       = {p["carrefourPid"]: p for p in data.get("urunler", [])}
            tamamlananlar = set(data.get("tamamlanan_urls", []))
            print(f"[checkpoint] {len(urunler)} ürün, {len(tamamlananlar)} kategori yüklendi")
            return urunler, tamamlananlar
        except Exception as e:
            print(f"[checkpoint] Yükleme hatası: {e}")
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
        print(f"[checkpoint] Kayıt hatası: {e}")


# ─── Einstein JSON yakalama ───────────────────────────────────────────────────
def einstein_handler_olustur(pool: List[str]):
    def on_response(response):
        try:
            if "Einstein-Recommendation" not in response.url:
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            data = json.loads(response.body())
            for rec in (data.get("recommendations") or []):
                html = rec.get("html") or ""
                if html:
                    pool.append(html)
        except Exception:
            pass
    return on_response


def einstein_isle(pool: List[str], urunler: Dict, kat: str) -> int:
    if not pool:
        return 0
    combined = "\n".join(pool)
    pool.clear()
    yeni = 0
    pid_re   = re.compile(r'data-pid=["\']([^"\']+)["\']')
    name_re  = re.compile(r'(?:data-name|aria-label)[^>]*=["\']([^"\']{4,200})["\']', re.I)
    price_re = re.compile(r'data-price=["\']([0-9.,]+)["\']'
                          r'|class=["\'][^"\']*sales[^"\']*["\'][^>]*>\s*([0-9]+[.,][0-9]{2})', re.I)
    brand_re = re.compile(r'data-brand=["\']([^"\']{1,80})["\']', re.I)
    seen: set = set()
    for m in pid_re.finditer(combined):
        pid = m.group(1).strip()
        if not pid or pid in urunler or pid in seen:
            continue
        seen.add(pid)
        s     = max(0, m.start() - 100)
        chunk = combined[s:min(len(combined), m.end() + 1200)]
        nm    = name_re.search(chunk)
        name  = nm.group(1).strip() if nm else ""
        prices = sorted(
            [f for f in [fiyat_al(pm.group(1) or pm.group(2)) for pm in price_re.finditer(chunk)] if f],
            reverse=True,
        )
        bm = brand_re.search(chunk)
        urunler[pid] = {
            "carrefourPid":    pid,
            "name":            name[:300],
            "brand":           bm.group(1).strip() if bm else "",
            "topCategoryName": kat[:200],
            "basicPrice":      prices[0] if prices else None,
            "promoPrice":      prices[1] if len(prices) > 1 else None,
            "inPromo":         len(prices) > 1,
        }
        yeni += 1
    return yeni


# ─── Sayfa çekimi ─────────────────────────────────────────────────────────────
def sayfayi_cek(page, kat_ad: str, urunler: Dict, max_tiklama: int = 300) -> int:
    """
    Bir kategorinin tüm ürünlerini 'Meer tonen' döngüsüyle topla.
    İnsan gibi: değişken bekleme, scroll, mouse hareketi.
    """
    onceki    = len(urunler)
    tiklama   = 0
    bos_tikla = 0
    MAX_BOS   = 5

    # Sayfada hâlihazırda yüklü olan ürünleri al
    try:
        tiles = page.evaluate(_DOM_JS)
        dom_urun_ekle(tiles, urunler, kat_ad)
    except Exception:
        pass

    while tiklama < max_tiklama:
        onceki_sayi = len(urunler)

        if not meer_toon_tikla(page):
            # Buton yok → sayfa bitti
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            sl(1.3, 0.5, 0.6, 3.5)
            try:
                tiles = page.evaluate(_DOM_JS)
                dom_urun_ekle(tiles, urunler, kat_ad)
            except Exception:
                pass
            break

        tiklama += 1

        # Verbolia/SFCC AJAX yüklensin — gaussian bekleme
        sl(3.2, 1.0, 1.5, 8.0)

        # Sayfada biraz dolaş: scroll + bazen rastgele mouse hareketi
        insan_scroll(page, int(random.gauss(700, 250)))

        if random.random() < 0.25:
            vp = page.viewport_size or {"width": 1280, "height": 720}
            insan_mouse_hareket(page,
                                random.uniform(100, vp["width"] - 100),
                                random.uniform(100, vp["height"] - 100))

        # Ürünleri topla
        try:
            tiles = page.evaluate(_DOM_JS)
            dom_urun_ekle(tiles, urunler, kat_ad)
        except Exception:
            pass

        if len(urunler) > onceki_sayi:
            bos_tikla = 0
        else:
            bos_tikla += 1
            if bos_tikla >= MAX_BOS:
                print(f"    [!] {MAX_BOS} ardışık tıklamada yeni ürün gelmedi — durduruluyor")
                break

        # %5 olasılıkla kısa mola (insan gibi dağılan dikkat)
        if random.random() < 0.05:
            mola = rg(10.0, 4.0, 4.0, 25.0)
            print(f"    [~] Kısa mola {mola:.0f}s…")
            time.sleep(mola)

    eklenen = len(urunler) - onceki
    print(f"    {tiklama} klik, +{eklenen} ürün")
    return eklenen


# ─── Ana çekim ────────────────────────────────────────────────────────────────
def calistir(test: bool = False, resume: bool = False,
             no_pause: bool = False, proxy: str = None) -> int:
    try:
        from camoufox.sync_api import Camoufox
    except ImportError:
        print("HATA: pip install camoufox && python -m camoufox fetch")
        return 1

    CIKTI_DIR.mkdir(exist_ok=True)
    _stop.sinyal_kaydet(_log)   # Ctrl+C → graceful shutdown

    # Proxy (proxies.txt veya --proxy argümanı)
    proxiler = proxy_yukle() if not proxy else [proxy]
    _log.info(f"Proxy: {proxiler[0][:40] if proxiler[0] else 'yok'}")

    urunler, tamamlananlar = checkpoint_yukle() if resume else ({}, set())
    einstein_pool: List[str] = []
    kategoriler = KATEGORILER[:3] if test else KATEGORILER

    with Camoufox(
        headless=False,
        firefox_user_prefs={
            "browser.startup.page":                    0,
            "browser.sessionstore.resume_from_crash":  False,
            "browser.sessionstore.enabled":            False,
        },
    ) as browser:
        page = browser.new_page()
        page.on("response", einstein_handler_olustur(einstein_pool))
        sl(2.5, 0.8, 1.5, 5.0)

        def goto_safe(url: str) -> bool:
            if _stop.dur:
                return False
            for deneme in range(3):
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                    sl(3.8, 1.3, 2.0, 8.0)

                    # HTTP hata kodu kontrolü
                    if resp:
                        eylem = http_durum_isle(resp.status, url, _log)
                        if eylem == "dur":
                            _stop.durdur()
                            return False
                        if eylem == "backoff":
                            backoff_bekle(deneme, _log)
                            continue

                    if cloudflare_var_mi(page) or ban_tespit(page, _log):
                        _log.warning("CF/Ban tespit edildi, bekleniyor…")
                        sl(22.0, 7.0, 12.0, 45.0)
                        if cloudflare_var_mi(page) or ban_tespit(page, _log):
                            _log.error("Hâlâ bloklu, atlanıyor.")
                            return False
                    return True
                except Exception as e:
                    _log.warning(f"goto hata deneme {deneme+1}: {str(e)[:80]}")
                    backoff_bekle(deneme, _log)
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
                        insan_tiklama(page, loc)
                        sl(2.0, 0.7, 1.0, 4.0)
                        return
                except Exception:
                    pass

        # ── İlk açılış: cookie al, biraz dolaş ──────────────────────────────
        print("\n[0] Tarayıcı açılıyor, cookie alınıyor…")
        if goto_safe(f"{BASE}/nl/al-onze-promoties"):
            cookie_kabul()
            # İlk sayfada insan gibi gezin
            insan_scroll(page, int(random.gauss(1400, 400)))
            sl(2.5, 1.0, 1.0, 6.0)

        # Zaten tamamlananları atla
        kalan = [(u, a, al) for (u, a, al) in kategoriler if u not in tamamlananlar]
        tamamlanan_onceden = len([u for u in kategoriler if u[0] in tamamlananlar])

        if not kalan:
            print("Tüm kategoriler zaten tamamlanmış.")

        mola_sayaci = 0
        for i, (url, kat_ad, alternatifler) in enumerate(kalan):
            if _stop.dur:
                _log.info("Durdurma bayrağı — döngü sonlandırılıyor.")
                break

            global_i = i + tamamlanan_onceden + 1

            # Oturum molası: her 10-14 kategoride bir
            if i > 0:
                mola_sayaci += 1
                if mola_sayaci >= random.randint(10, 14):
                    mola_sayaci = 0
                    mola = rg(55.0, 22.0, 25.0, 130.0)
                    print(f"\n  ═══ Oturum molası {mola:.0f}s (toplam={len(urunler)}) ═══")
                    time.sleep(mola)
                else:
                    # Normal kategoriler arası bekleme
                    bekle = rg(10.0, 4.5, 4.0, 28.0)
                    # %7 olasılıkla çok uzun bekleme (insan çay içiyor)
                    if random.random() < 0.07:
                        bekle = rg(45.0, 18.0, 20.0, 100.0)
                        print(f"\n  … Uzun bekleme {bekle:.0f}s …")
                    time.sleep(bekle)

            print(f"\n[{global_i}/{len(kategoriler)}] {kat_ad}  {url[:70]}")

            if not goto_safe(url):
                print("  [atlandı — yüklenemedi]")
                continue

            son_url = page.url
            baslik  = page.title()

            if "Sites-carrefour-be-Site" in baslik or "404" in baslik:
                print(f"  [404/hata] {baslik} — atlandı")
                tamamlananlar.add(url)
                checkpoint_kaydet(urunler, tamamlananlar)
                continue

            print(f"  → {son_url[:80]}  [{baslik[:50]}]")

            # Sayfa yüklendi, biraz scroll
            insan_scroll(page, int(random.gauss(900, 350)))
            sl(1.2, 0.5, 0.5, 3.0)

            # Ürünleri çek
            yeni = sayfayi_cek(page, kat_ad, urunler, max_tiklama=300)

            # Az ürün + farklı URL → alternatif dene
            if redirect_sorunlu_mu(url, son_url, yeni) and alternatifler:
                print(f"  [?] Az ürün ({yeni}) ve redirect var → alternatifler deneniyor")
                for alt_url in alternatifler:
                    print(f"      → {alt_url}")
                    sl(5.0, 2.0, 2.0, 12.0)
                    if not goto_safe(alt_url):
                        continue
                    alt_baslik = page.title()
                    if "404" in alt_baslik or "Sites-carrefour-be-Site" in alt_baslik:
                        continue
                    print(f"        [{alt_baslik[:50]}]")
                    insan_scroll(page, int(random.gauss(700, 250)))
                    sl(1.0, 0.4, 0.4, 2.5)
                    alt_yeni = sayfayi_cek(page, kat_ad, urunler, max_tiklama=300)
                    yeni += alt_yeni
                    if alt_yeni > 10:
                        break

            # Einstein pool
            ein = einstein_isle(einstein_pool, urunler, kat_ad)
            if ein:
                print(f"  Einstein: +{ein}")

            tamamlananlar.add(url)
            print(f"  Toplam: {len(urunler)}")

            # Her kategori sonrası checkpoint kaydet
            checkpoint_kaydet(urunler, tamamlananlar)

    # ── Final kayıt ───────────────────────────────────────────────────────────
    tarih        = datetime.now().strftime("%Y-%m-%d_%H-%M")
    urun_listesi = list(urunler.values())
    cikti        = CIKTI_DIR / f"carrefour_be_v2_{tarih}.json"
    payload = {
        "kaynak":         "Carrefour BE v2 — İnsan simülasyonu + Checkpoint",
        "chain_slug":     "carrefour_be",
        "country_code":   "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi":    len(urun_listesi),
        "urunler":        urun_listesi,
    }
    with open(cikti, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"TAMAM: {len(urun_listesi)} ürün → {cikti}")
    print(f"{'='*60}")

    # Başarılı tamamlandı → checkpoint temizle
    try:
        CHECKPOINT.unlink(missing_ok=True)
    except Exception:
        pass

    if not no_pause:
        input("\nÇıkmak için Enter…")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Carrefour BE tam katalog v2")
    ap.add_argument("--test",     action="store_true", help="İlk 3 kategori")
    ap.add_argument("--resume",   action="store_true", help="Checkpoint'ten devam")
    ap.add_argument("--no-pause", action="store_true", help="Bitince Enter bekleme")
    ap.add_argument("--proxy",    type=str, default=None, help="Proxy URL (http://user:pass@ip:port)")
    args = ap.parse_args()
    return calistir(test=args.test, resume=args.resume,
                    no_pause=args.no_pause, proxy=args.proxy)


if __name__ == "__main__":
    raise SystemExit(main())
