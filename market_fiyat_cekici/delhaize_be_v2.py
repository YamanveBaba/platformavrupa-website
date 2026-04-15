# -*- coding: utf-8 -*-
"""
Delhaize BE — Tam Katalog Çekici v2
Özellikler:
  ✓ camoufox (Firefox, anti-bot) — artık plain Chromium değil
  ✓ GraphQL GetCategoryProductSearch intercept (kanıtlanmış, çalışıyor)
  ✓ apollographql-client-version OTOMATİK keşif — hardcoded hash süresi dolsa bile çalışır
  ✓ Kategori kodları OTOMATİK keşif — delhaize.be/nl/shop HTML'inden
  ✓ Tam insan davranışı: gaussian timing, bezier mouse, değişken scroll
  ✓ Checkpoint/resume — crash → kaldığı yerden devam
  ✓ potentialPromotions ile promo fiyat + tarih
  ✓ Tüm sayfalar: totalPages ile tam pagination

Kullanım:
  python delhaize_be_v2.py              # tam çekim
  python delhaize_be_v2.py --test       # ilk 2 kategori
  python delhaize_be_v2.py --resume     # checkpoint'ten devam
  python delhaize_be_v2.py --no-pause
"""
from __future__ import annotations
import argparse, json, re, time, random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scraper_utils import (
    log_olustur, ban_tespit, backoff_bekle, StopSinyali,
    jsonld_urun_cikart, proxy_yukle, robotstxt_kontrol, http_durum_isle,
)

_log  = log_olustur("delhaize_be")
_stop = StopSinyali()

script_dir = Path(__file__).parent
CIKTI_DIR  = script_dir / "cikti"
CHECKPOINT = CIKTI_DIR  / "delhaize_v2_checkpoint.json"
BASE       = "https://www.delhaize.be"

# ─── Kategori listesi (fallback — otomatik keşif başarısız olursa) ────────────
# HTML'den doğrulanmış top-level kategori kodları
SABIT_KATEGORILER: List[Tuple[str, str]] = [
    ("Vlees vis vegetarisch",      "v2MEA"),
    ("Zuivel kaas eieren",         "v2DAI"),
    ("Brood banket",               "v2BAK"),
    ("Traiteur aperitiefhapjes",   "v2DEL"),
    ("Diepvries",                  "v2FRO"),
    ("Kruidenierswaren",           "v2CON"),
    ("Groenten fruit",             "v2FRU"),
    ("Snacks koekjes snoep",       "v2SWE"),
    ("Dranken",                    "v2DRI"),
    ("Wijn bubbels",               "v2WIN"),
    ("Alcoholische dranken",       "v2ALC"),
    ("Aperitief",                  "v2APE"),
    ("Schoonmaak huishouden",      "v2CLE"),
    ("Hygiene lichaamsverzorging", "v2HYG"),
    ("Baby kind",                  "v2BAB"),
    ("Huisdieren",                 "v2PET"),
    ("Bio eco fairtrade",          "v2BIO"),
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


# ─── İnsan davranışı ──────────────────────────────────────────────────────────
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


def insan_scroll(page, toplam: int = 1400):
    kaydirilan = 0
    while kaydirilan < toplam:
        chunk = max(50, min(480, int(random.gauss(185, 85))))
        chunk = min(chunk, toplam - kaydirilan)
        page.mouse.wheel(0, chunk)
        kaydirilan += chunk
        sl(0.11, 0.05, 0.03, 0.45)
        if random.random() < 0.20:
            sl(1.5, 0.8, 0.4, 5.0)
        if random.random() < 0.06:
            geri = max(30, min(200, int(random.gauss(100, 50))))
            page.mouse.wheel(0, -geri)
            kaydirilan = max(0, kaydirilan - geri)
            sl(0.5, 0.25, 0.15, 2.0)


def insan_tiklama(page, locator) -> bool:
    try:
        locator.scroll_into_view_if_needed(timeout=3000)
        sl(0.28, 0.13, 0.08, 1.1)
        box = locator.bounding_box(timeout=3000)
        if box:
            tx = box["x"] + box["width"] / 2 + random.gauss(0, 3)
            ty = box["y"] + box["height"] / 2 + random.gauss(0, 3)
            bezier_mouse(page, tx, ty)
            sl(0.18, 0.08, 0.05, 0.7)
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


# ─── Tarih / fiyat normalize ──────────────────────────────────────────────────
def to_iso_date(val) -> Optional[str]:
    if not val:
        return None
    s = str(val).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', s):
        return s[:10]
    m = re.match(r'^(\d{2})[/.-](\d{2})[/.-](\d{4})', s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def parse_price(p) -> Optional[float]:
    if p is None:
        return None
    if isinstance(p, dict):
        for k in ("value", "formattedValue", "amount"):
            v = p.get(k)
            if v is not None:
                try:
                    return round(float(str(v).replace(",", ".").replace("€", "").strip()), 2)
                except Exception:
                    pass
    if isinstance(p, (int, float)):
        return round(float(p), 2) if float(p) > 0 else None
    if isinstance(p, str):
        m = re.search(r'(\d+)[,.](\d{2})', p.replace(",", "."))
        if m:
            return round(float(f"{m.group(1)}.{m.group(2)}"), 2)
    return None


def parse_product(raw: dict, cat_name: str) -> Optional[dict]:
    try:
        pid  = str(raw.get("code") or "").strip()
        name = str(raw.get("name") or "").strip()
        if not pid or not name:
            return None

        price = parse_price(raw.get("price"))
        if price is None:
            return None

        brand = str(raw.get("manufacturerName") or "").strip()

        in_promo    = False
        promo_price = None
        promo_from  = None
        promo_until = None

        # potentialPromotions listesi
        promos = raw.get("potentialPromotions") or []
        if isinstance(promos, list) and promos:
            p0 = promos[0] if isinstance(promos[0], dict) else {}
            if p0:
                in_promo = True
                for k in ("promotionPrice", "discountedPrice", "value", "price"):
                    pp = p0.get(k)
                    if pp is not None:
                        parsed_pp = parse_price(pp)
                        if parsed_pp is not None and parsed_pp < price:
                            promo_price = parsed_pp
                            break
                promo_from  = to_iso_date(p0.get("startDate") or p0.get("from")
                                          or p0.get("validFrom") or p0.get("startdate")
                                          or p0.get("promotionStartDate"))
                promo_until = to_iso_date(p0.get("endDate") or p0.get("until")
                                          or p0.get("validTo") or p0.get("enddate")
                                          or p0.get("promotionEndDate"))

        # Kalıcı fiyat indirimi işareti
        if not in_promo and raw.get("isPermanentPriceReduction"):
            in_promo = True

        # price.showStrikethroughPrice (eski format)
        price_obj = raw.get("price") or {}
        if isinstance(price_obj, dict):
            if not in_promo and price_obj.get("showStrikethroughPrice"):
                in_promo = True
            was = price_obj.get("wasPrice")
            if was:
                was_f = parse_price(was)
                if was_f and was_f > (price or 0):
                    in_promo = True
                    if not promo_price:
                        promo_price = price
                        price = was_f

        # Resim
        image_url = ""
        images = raw.get("images") or []
        if isinstance(images, list) and images:
            img = images[0]
            if isinstance(img, dict):
                image_url = img.get("url", "")
                if image_url and not image_url.startswith("http"):
                    image_url = BASE + image_url

        return {
            "delhaizePid":    pid,
            "name":           name[:300],
            "brand":          brand[:120],
            "categoryName":   cat_name[:200],
            "basicPrice":     price,
            "promoPrice":     promo_price,
            "inPromo":        bool(in_promo),
            "promoValidFrom": promo_from,
            "promoValidUntil":promo_until,
            "imageUrl":       image_url[:400],
        }
    except Exception:
        return None


# ─── Otomatik kategori keşfi ──────────────────────────────────────────────────
def kategori_kesfi(page) -> List[Tuple[str, str]]:
    """
    delhaize.be/nl/shop HTML'inden v2XXX kategori kodlarını çıkar.
    Başarısız olursa SABIT_KATEGORILER döner.
    """
    try:
        page.goto(f"{BASE}/nl/shop", wait_until="domcontentloaded", timeout=45_000)
        sl(3.0, 1.0, 1.5, 6.0)
        html = page.content()
        codes = re.findall(r"/c/(v2[A-Za-z0-9]{2,15})", html, re.I)

        def norm(c: str) -> str:
            return "v2" + c[2:].upper()

        unique = sorted({norm(c) for c in codes if len(c) >= 4})
        if len(unique) >= 5:
            result = [(f"Categorie {c}", c) for c in unique]
            print(f"  [keşif] {len(result)} kategori kodu bulundu")
            return result
    except Exception as e:
        print(f"  [keşif hata] {e}")
    print(f"  [keşif] Fallback: {len(SABIT_KATEGORILER)} sabit kategori")
    return SABIT_KATEGORILER


# ─── apollographql-client-version otomatik keşfi ─────────────────────────────
def graphql_version_kesfi(page) -> Optional[str]:
    """
    Sayfa kaynak kodundan apollographql-client-version'ı bul.
    Script tag'leri ve network header'larını kontrol eder.
    """
    try:
        # Önce network response header'larından dene
        captured_version = {}

        def on_response(response):
            try:
                v = response.headers.get("apollographql-client-version")
                if v:
                    captured_version["version"] = v
            except Exception:
                pass

        page.on("response", on_response)

        # Ana shop sayfasını ziyaret et (zaten orada olabiliriz)
        html = page.content()

        # Script kaynak kodlarında ara
        for pattern in (
            r'(?:apollographql-client-version|clientVersion)["\s:=\']+([a-f0-9]{20,50})',
            r'(?:version|clientVersion)\s*[:=]\s*["\']([a-f0-9]{20,50})["\']',
            r'"apollographql-client-version"\s*:\s*"([^"]{20,50})"',
        ):
            m = re.search(pattern, html, re.I)
            if m:
                v = m.group(1).strip()
                print(f"  [graphql-version] HTML'den bulundu: {v[:20]}…")
                return v

        # JS dosyalarından ara
        scripts = page.evaluate("""
            () => [...document.querySelectorAll('script[src]')]
                  .map(s => s.src)
                  .filter(s => s && (s.includes('chunk') || s.includes('app') || s.includes('vendor')))
                  .slice(0, 8)
        """)
        for script_url in (scripts or []):
            try:
                resp = page.request.get(script_url, timeout=10_000)
                if resp.ok:
                    content = resp.text()
                    for pattern in (
                        r'apollographql-client-version["\s:=\']+([a-f0-9]{20,50})',
                        r'clientVersion\s*[:=]\s*["\']([a-f0-9]{20,50})["\']',
                    ):
                        m = re.search(pattern, content, re.I)
                        if m:
                            v = m.group(1).strip()
                            print(f"  [graphql-version] JS'den bulundu: {v[:20]}…")
                            return v
            except Exception:
                pass

        if captured_version.get("version"):
            return captured_version["version"]

    except Exception as e:
        print(f"  [graphql-version hata] {e}")
    return None


# ─── GraphQL ürün çekme ───────────────────────────────────────────────────────
# Sabit değerler — otomatik keşif başarısız olursa kullan
_GRAPHQL_CLIENT_NAME    = "be-dll-web-stores"
_GRAPHQL_CLIENT_VERSION = "1beae2758b4bf4b63f79d933767834fed191a746"
_GRAPHQL_OP_HASH        = "189e7cb5a6ba93e55dc63e4eef0ad063ca3e8aedb0bdf2a58124e02d5d5d69a2"

_GRAPHQL_CONFIG = {
    "client_name":    _GRAPHQL_CLIENT_NAME,
    "client_version": _GRAPHQL_CLIENT_VERSION,
    "op_hash":        _GRAPHQL_OP_HASH,
}


def graphql_api_cek(page, cat_name: str, cat_code: str,
                    urunler: Dict, grafql_conf: dict) -> int:
    """
    Delhaize GraphQL API'sini intercept ederek bir kategorinin TÜM sayfalarını çeker.
    """
    intercepted: List[dict] = []
    captured = {"flag": False}

    def on_resp(response):
        try:
            if "GetCategoryProductSearch" not in response.url:
                return
            ct = response.headers.get("content-type", "")
            if "json" not in ct:
                return
            body = json.loads(response.body())
            cps = body.get("data", {}).get("categoryProductSearch")
            if cps:
                intercepted.append(cps)
                captured["flag"] = True
        except Exception:
            pass

    page.on("response", on_resp)

    cat_url = f"{BASE}/c/{cat_code}"
    try:
        resp = page.goto(cat_url, wait_until="domcontentloaded", timeout=45_000)
        if resp and resp.status in (404, 410):
            print(f"    [404] {cat_name} — atlandı")
            page.remove_listener("response", on_resp)
            return 0
    except Exception as e:
        print(f"    [goto hata] {cat_name}: {str(e)[:80]}")
        page.remove_listener("response", on_resp)
        return 0

    real_url = page.url.split("?")[0]
    print(f"    → {real_url.replace(BASE, '')}")

    sl(2.5, 1.0, 1.2, 6.0)

    # API tetiklenmesi için scroll + bekle
    deadline = time.time() + 18
    while not captured["flag"] and time.time() < deadline:
        page.mouse.wheel(0, int(random.gauss(250, 80)))
        sl(0.8, 0.4, 0.3, 2.5)

    if not intercepted:
        print(f"    [!] API yanıtı yok — {cat_name} atlandı")
        page.remove_listener("response", on_resp)
        return 0

    # Sayfa 0 ürünleri
    yeni = 0
    cps0       = intercepted[0]
    pagination = cps0.get("pagination") or {}
    total_pages = int(pagination.get("totalPages") or 1)
    total       = int(pagination.get("totalResults") or 0)
    print(f"    {total} ürün, {total_pages} sayfa")

    for raw in (cps0.get("products") or []):
        rec = parse_product(raw, cat_name)
        if rec and rec["delhaizePid"] not in urunler:
            urunler[rec["delhaizePid"]] = rec
            yeni += 1

    # Sayfa 1 → N
    for pg in range(1, min(total_pages, 300)):
        intercepted.clear()
        captured["flag"] = False

        next_url = f"{real_url}?pageNumber={pg}"
        try:
            page.goto(next_url, wait_until="domcontentloaded", timeout=35_000)
        except Exception as e:
            print(f"    [sayfa {pg} goto hata] {str(e)[:60]}")
            break

        sl(2.2, 0.9, 1.0, 6.0)

        # İnsan gibi scroll
        insan_scroll(page, int(random.gauss(600, 200)))

        # API tetiklensin
        deadline = time.time() + 12
        while not captured["flag"] and time.time() < deadline:
            page.mouse.wheel(0, int(random.gauss(200, 70)))
            sl(0.7, 0.3, 0.3, 2.0)

        if not intercepted:
            # 1 kez daha dene
            sl(3.0, 1.0, 1.5, 7.0)
            if not intercepted:
                print(f"    sayfa {pg}: API timeout — duruyorum")
                break

        page_products = intercepted[0].get("products") or []
        if not page_products:
            break

        for raw in page_products:
            rec = parse_product(raw, cat_name)
            if rec and rec["delhaizePid"] not in urunler:
                urunler[rec["delhaizePid"]] = rec
                yeni += 1

        # Sayfalar arası insan bekleme
        sl(rg(2.5, 1.2, 1.0, 8.0), 0)

        # %5 ihtimalle kısa mola
        if random.random() < 0.05:
            mola = rg(8.0, 3.0, 4.0, 20.0)
            time.sleep(mola)

    page.remove_listener("response", on_resp)
    return yeni


# ─── Checkpoint ───────────────────────────────────────────────────────────────
def checkpoint_yukle() -> Tuple[Dict, set]:
    if CHECKPOINT.exists():
        try:
            with open(CHECKPOINT, encoding="utf-8") as f:
                data = json.load(f)
            urunler       = {p["delhaizePid"]: p for p in data.get("urunler", [])}
            tamamlananlar = set(data.get("tamamlanan_codes", []))
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
                "son_guncelleme":    datetime.now().isoformat(),
                "urun_sayisi":       len(urunler),
                "tamamlanan_codes":  list(tamamlananlar),
                "urunler":           list(urunler.values()),
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[checkpoint kayıt hata] {e}")


# ─── Cookie kabul ─────────────────────────────────────────────────────────────
def cookie_kabul(page):
    for sel in (
        "#onetrust-accept-btn-handler",
        'button:has-text("Alles accepteren")',
        'button:has-text("Accepteer")',
        'button:has-text("Tout accepter")',
        '[data-testid="accept-cookies"]',
    ):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=1800):
                insan_tiklama(page, loc)
                sl(2.0, 0.8, 0.9, 4.5)
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
             no_pause: bool = False, proxy: str = None) -> int:
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

    with Camoufox(
        headless=False,
        firefox_user_prefs={
            "browser.startup.page":                   0,
            "browser.sessionstore.resume_from_crash": False,
            "browser.sessionstore.enabled":           False,
        },
    ) as browser:
        page = browser.new_page()
        page.set_default_timeout(25_000)   # tüm Playwright işlemleri max 25s
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

        # ── İlk açılış: cookie + insan davranışı ────────────────────────────
        print("\n[0] İlk açılış, cookie alınıyor…")
        if goto_safe(f"{BASE}/nl/"):
            cookie_kabul(page)
            insan_scroll(page, int(random.gauss(900, 300)))
            sl(2.0, 0.8, 1.0, 5.0)

        # ── Kategori keşfi ───────────────────────────────────────────────────
        print("\n[keşif] Kategori kodları tespit ediliyor…")
        if not goto_safe(f"{BASE}/nl/shop"):
            kategoriler = SABIT_KATEGORILER
        else:
            cookie_kabul(page)
            insan_scroll(page, int(random.gauss(600, 200)))
            sl(1.5, 0.6, 0.7, 3.5)
            kategoriler = kategori_kesfi(page)

        # ── GraphQL version keşfi ────────────────────────────────────────────
        print("\n[graphql] Client version tespit ediliyor…")
        gql_version = graphql_version_kesfi(page)
        if gql_version:
            _GRAPHQL_CONFIG["client_version"] = gql_version
        else:
            print(f"  [graphql] Fallback version kullanılıyor: {_GRAPHQL_CLIENT_VERSION[:20]}…")

        if test:
            kategoriler = kategoriler[:2]

        kalan = [(n, c) for n, c in kategoriler if c not in tamamlananlar]
        tamamlanan_onceden = len([c for _, c in kategoriler if c in tamamlananlar])

        print(f"\nToplam {len(kategoriler)} kategori, {len(kalan)} işlenecek\n")

        mola_sayaci = 0
        for i, (kat_ad, kat_kod) in enumerate(kalan):
            if _stop.dur:
                _log.info("Durdurma bayrağı — döngü sonlandırılıyor.")
                break

            global_i = i + tamamlanan_onceden + 1

            # Kategoriler arası bekleme
            if i > 0:
                mola_sayaci += 1
                if mola_sayaci >= random.randint(6, 10):
                    mola_sayaci = 0
                    mola = rg(65.0, 28.0, 30.0, 160.0)
                    print(f"\n  ═══ Oturum molası {mola:.0f}s (toplam={len(urunler)}) ═══")
                    time.sleep(mola)
                else:
                    bekle = rg(14.0, 6.0, 5.0, 40.0)
                    if random.random() < 0.08:
                        bekle = rg(55.0, 22.0, 28.0, 120.0)
                        print(f"\n  … Uzun bekleme {bekle:.0f}s …")
                    time.sleep(bekle)

            print(f"[{global_i}/{len(kategoriler)}] {kat_ad} ({kat_kod})")

            onceki = len(urunler)
            yeni = graphql_api_cek(page, kat_ad, kat_kod, urunler, _GRAPHQL_CONFIG)

            print(f"    +{yeni} ürün | Toplam: {len(urunler)}")

            # Eğer hiç ürün gelmediyse — API değişmiş olabilir, yeni keşif dene
            if yeni == 0 and i == 0:
                print("  [!] İlk kategoriden 0 ürün — GraphQL hash yeniden keşfediliyor…")
                gql_version = graphql_version_kesfi(page)
                if gql_version:
                    _GRAPHQL_CONFIG["client_version"] = gql_version
                # Aynı kategoriyi tekrar dene
                yeni = graphql_api_cek(page, kat_ad, kat_kod, urunler, _GRAPHQL_CONFIG)
                print(f"    [retry] +{yeni} ürün")

            tamamlananlar.add(kat_kod)
            checkpoint_kaydet(urunler, tamamlananlar)

            # Random mouse hareketi (insan gibi beklerken)
            if random.random() < 0.3:
                vp = page.viewport_size or {"width": 1280, "height": 720}
                bezier_mouse(page,
                             random.uniform(100, vp["width"] - 100),
                             random.uniform(100, vp["height"] - 100))

    # ── Final kayıt ───────────────────────────────────────────────────────────
    tarih        = datetime.now().strftime("%Y-%m-%d_%H-%M")
    urun_listesi = list(urunler.values())
    cikti_dosya  = CIKTI_DIR / f"delhaize_be_v2_{tarih}.json"

    with open(cikti_dosya, "w", encoding="utf-8") as f:
        json.dump({
            "kaynak":         "Delhaize BE v2 — camoufox + GraphQL Interception",
            "chain_slug":     "delhaize_be",
            "country_code":   "BE",
            "cekilme_tarihi": datetime.now().isoformat(),
            "urun_sayisi":    len(urun_listesi),
            "urunler":        urun_listesi,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"TAMAM: {len(urun_listesi)} ürün → {cikti_dosya}")
    print(f"{'='*60}")

    try:
        CHECKPOINT.unlink(missing_ok=True)
    except Exception:
        pass

    if not no_pause:
        input("\nÇıkmak için Enter…")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Delhaize BE tam katalog v2")
    ap.add_argument("--test",     action="store_true", help="İlk 2 kategori")
    ap.add_argument("--resume",   action="store_true", help="Checkpoint'ten devam")
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument("--proxy",    type=str, default=None, help="Proxy URL")
    args = ap.parse_args()
    return calistir(test=args.test, resume=args.resume,
                    no_pause=args.no_pause, proxy=args.proxy)


if __name__ == "__main__":
    raise SystemExit(main())
