# -*- coding: utf-8 -*-
"""
Carrefour BE — Browser'dan cookie al, sonra direkt HTTP ile SFCC API çek.

Adım 1: --headed ile browser aç, promoties sayfasını yükle, cookie'leri kaydet.
Adım 2: Kaydedilen cookie'lerle tüm ürünleri HTTP ile çek (browser gerek yok).

Kullanım:
  python carrefour_cookie_cek.py --sadece-cookie   -> cookie.txt üretir
  python carrefour_cookie_cek.py                   -> cookie varsa direkt çeker
  python carrefour_cookie_cek.py --headed          -> browser aç + çek
"""
from __future__ import annotations
import argparse, json, os, re, time, random
from datetime import datetime
from typing import Dict, List, Optional

script_dir = os.path.dirname(os.path.abspath(__file__))
COOKIE_DOSYA = os.path.join(script_dir, "carrefour_cf_cookie.json")
CIKTI_DIR = os.path.join(script_dir, "cikti")

# SFCC site ID (kesiften öğrendik)
SITE_ID = "Sites-carrefour-be-Site"
BASE = "https://www.carrefour.be"

# Tüm kategori ID'leri (SFCC cgid parametresi)
KATEGORILER = [
    # Ana gıda kategorileri
    ("food",            "Voeding"),
    ("fresh",           "Vers"),
    ("drinks",          "Dranken"),
    ("bakery",          "Bakkerij"),
    ("frozen",          "Diepvries"),
    ("snacks",          "Snacks"),
    # Ev / non-food
    ("household",       "Huishouden"),
    ("personal-care",   "Verzorging"),
    ("baby",            "Baby"),
    ("pet",             "Dieren"),
    ("garden",          "Tuin"),
    ("electronics",     "Elektronica"),
    ("sports",          "Sport"),
    ("toys",            "Speelgoed"),
    # Promosyonlar
    ("promotions",      "Promoties"),
]


# ────────────────────────────────────────────────────────
# 1. Browser'dan cookie alma
# ────────────────────────────────────────────────────────

def browser_cookie_al(headed: bool) -> dict:
    """Playwright ile promoties sayfasını aç, CF cookie'lerini döndür."""
    from playwright.sync_api import sync_playwright

    profil = os.path.join(script_dir, "playwright_user_data", "carrefour_be_v2")
    os.makedirs(profil, exist_ok=True)

    cookies_dict = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profil,
            headless=not headed,
            locale="nl-BE",
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Stealth
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

        target = f"{BASE}/nl/al-onze-promoties"
        print(f"[browser] Açılıyor: {target}")
        try:
            page.goto(target, wait_until="domcontentloaded", timeout=120_000)
        except Exception as e:
            print(f"[browser] goto hata: {e}")

        # Cloudflare challenge bekleme
        for _ in range(30):
            title = page.title()
            if "Cloudflare" not in title and "Attention" not in title:
                break
            print(f"  [CF] Bekleniyor… title={title}")
            time.sleep(2)

        title = page.title()
        print(f"[browser] Sayfa: {title}")

        # Cookie kabul
        for sel in ('button:has-text("Alles accepteren")', '#onetrust-accept-btn-handler'):
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=2000):
                    loc.click()
                    time.sleep(1.5)
                    break
            except Exception:
                pass

        time.sleep(3)

        # Cookie'leri al
        all_cookies = ctx.cookies()
        for c in all_cookies:
            cookies_dict[c["name"]] = c["value"]

        onemli = {k: v for k, v in cookies_dict.items()
                  if k in ("cf_clearance", "__cf_bm", "dwsid", "dw_store",
                           "cc-at_carrefour-be", "sid", "session-id")}
        print(f"[browser] {len(cookies_dict)} cookie alındı. Önemli: {list(onemli.keys())}")

        # Browser içinden bir SFCC API isteği dene (CF cookie var, çalışmalı)
        print("[browser] İçeriden SFCC isteği deneniyor…")
        try:
            result = page.evaluate(f"""
                async () => {{
                    const r = await fetch(
                        '/on/demandware.store/{SITE_ID}/default/Search-Show?cgid=food&start=0&sz=24&format=ajax',
                        {{credentials: 'include', headers: {{'Accept': 'application/json, text/html, */*'}}}}
                    );
                    return {{status: r.status, ct: r.headers.get('content-type'), text: await r.text()}};
                }}
            """)
            status = result.get("status")
            ct = result.get("ct", "")
            text = result.get("text", "")
            print(f"  [fetch] status={status} ct={ct[:40]} boyut={len(text)}")
            if len(text) > 100:
                print(f"  [fetch] ilk 300: {text[:300]}")
                # Cookie + fetch sonucunu kaydet
                with open(os.path.join(script_dir, "carrefour_sfcc_test.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
        except Exception as e:
            print(f"  [fetch] hata: {e}")

        ctx.close()

    # Cookie'leri kaydet
    with open(COOKIE_DOSYA, "w", encoding="utf-8") as f:
        json.dump(cookies_dict, f, ensure_ascii=False, indent=2)
    print(f"[cookie] kaydedildi: {COOKIE_DOSYA}")
    return cookies_dict


# ────────────────────────────────────────────────────────
# 2. HTTP ile SFCC ürün çekimi
# ────────────────────────────────────────────────────────

def sfcc_urunler_cek(cookies: dict) -> List[Dict]:
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "nl-BE,nl;q=0.9",
        "Referer": "https://www.carrefour.be/nl/alle-producten",
        "X-Requested-With": "XMLHttpRequest",
    })
    for k, v in cookies.items():
        session.cookies.set(k, v, domain=".carrefour.be")

    urunler: Dict[str, Dict] = {}
    sz = 24

    for cgid, kat_ad in KATEGORILER:
        print(f"\n[kat] {kat_ad} ({cgid})")
        start = 0
        bos = 0

        while True:
            url = (
                f"{BASE}/on/demandware.store/{SITE_ID}/default/"
                f"Search-Show?cgid={cgid}&start={start}&sz={sz}&format=ajax"
            )
            try:
                r = session.get(url, timeout=20)
                ct = r.headers.get("content-type", "")
                print(f"  start={start} status={r.status} boyut={len(r.content)} ct={ct[:30]}")

                sc = r.status_code
                if sc == 403:
                    print(f"  [403] CF bloğu — cookie geçersiz olabilir.")
                    bos += 1
                    if bos >= 2:
                        break
                    time.sleep(5)
                    continue

                if sc != 200:
                    print(f"  [{sc}] beklenmedik durum")
                    bos += 1
                    if bos >= 2:
                        break
                    time.sleep(3)
                    continue

                # JSON mu HTML mi?
                if "json" in ct:
                    data = r.json()
                    urun_listesi = _urun_cikart(data)
                    yeni = _ekle(urun_listesi, urunler, cgid)
                    print(f"  +{yeni} ürün (toplam {len(urunler)})")
                    if yeni == 0:
                        bos += 1
                        if bos >= 2:
                            break
                    else:
                        bos = 0

                elif "html" in ct:
                    # HTML döndü — sayfa içindeki JSON'u parse et
                    urun_listesi = _html_urun_cikart(r.text, cgid)
                    yeni = _ekle(urun_listesi, urunler, cgid)
                    print(f"  +{yeni} ürün HTML'den (toplam {len(urunler)})")
                    if yeni == 0:
                        bos += 1
                        if bos >= 2:
                            break
                    else:
                        bos = 0
                else:
                    print(f"  [?] ct={ct[:40]}")
                    bos += 1
                    if bos >= 2:
                        break

            except Exception as e:
                print(f"  hata: {e}")
                bos += 1
                if bos >= 3:
                    break

            start += sz
            time.sleep(random.uniform(1.0, 2.5))

    return list(urunler.values())


def _urun_cikart(data) -> List[Dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("hits", "products", "items", "productSearchResult",
                  "records", "product_list", "data"):
            v = data.get(k)
            if isinstance(v, list) and v:
                return v
        for v in data.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def _html_urun_cikart(html: str, kategori: str) -> List[Dict]:
    """HTML içindeki ürün JSON bloklarını çıkart."""
    urunler = []
    # data-pid'li elementleri bul
    pid_re = re.compile(r'data-pid=["\']([^"\']+)["\']')
    name_re = re.compile(r'(?:aria-label|data-name)=["\']([^"\']{5,150})["\']')
    price_re = re.compile(r'(?:data-price|itemprop="price")=["\']([0-9.,]+)["\']|<span[^>]*class="[^"]*price[^"]*"[^>]*>\s*€?\s*([0-9]+[.,][0-9]{2})')

    pids = set()
    for m in pid_re.finditer(html):
        pid = m.group(1)
        if pid in pids:
            continue
        pids.add(pid)
        # Etrafındaki ~500 karaktere bak
        start = max(0, m.start() - 50)
        end = min(len(html), m.end() + 500)
        chunk = html[start:end]
        name = ""
        nm = name_re.search(chunk)
        if nm:
            name = nm.group(1)
        price = None
        pm = price_re.search(chunk)
        if pm:
            raw = pm.group(1) or pm.group(2)
            if raw:
                try:
                    price = float(raw.replace(",", "."))
                except Exception:
                    pass
        urunler.append({
            "carrefourPid": pid,
            "name": name,
            "basicPrice": price,
            "topCategoryName": kategori,
            "kaynak": "html_parse",
        })
    return urunler


def _ekle(liste, hedef: Dict, kat: str) -> int:
    yeni = 0
    for item in liste:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or item.get("productId") or item.get("pid") or
                  item.get("sku") or item.get("carrefourPid") or "")
        name = str(item.get("name") or item.get("title") or "")
        key = pid or name[:60]
        if not key or key in hedef:
            continue
        hedef[key] = {
            "carrefourPid": pid,
            "name": name[:300],
            "brand": str(item.get("brand") or item.get("brandName") or ""),
            "topCategoryName": str(item.get("category") or kat),
            "basicPrice": _fiyat(item.get("price") or item.get("sellPrice") or
                                  item.get("regularPrice") or item.get("basicPrice")),
            "promoPrice": _fiyat(item.get("promoPrice") or item.get("salePrice") or
                                  item.get("reducedPrice") or item.get("discountedPrice")),
            "inPromo": bool(item.get("onPromotion") or item.get("isPromo") or
                            item.get("inPromotion") or item.get("promoted")),
            "unitContent": str(item.get("content") or item.get("quantity") or ""),
        }
        yeni += 1
    return yeni


def _fiyat(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    try:
        return round(float(re.sub(r"[^\d.]", "", str(v).replace(",", "."))), 2)
    except Exception:
        return None


# ────────────────────────────────────────────────────────
# Ana akış
# ────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true", help="Browser ile cookie al")
    ap.add_argument("--sadece-cookie", action="store_true", help="Sadece cookie al, çekme")
    ap.add_argument("--no-pause", action="store_true")
    args = ap.parse_args()

    os.makedirs(CIKTI_DIR, exist_ok=True)

    # Cookie var mı?
    cookies = {}
    if os.path.exists(COOKIE_DOSYA):
        with open(COOKIE_DOSYA, encoding="utf-8") as f:
            cookies = json.load(f)
        print(f"[cookie] mevcut: {list(cookies.keys())[:8]}")

    # CF cookie yoksa veya --headed ise browser aç
    if not cookies.get("cf_clearance") or args.headed or args.sadece_cookie:
        print("[browser] CF cookie alınıyor…")
        cookies = browser_cookie_al(headed=True)

    if args.sadece_cookie:
        print("Cookie alındı. Çekim yapılmadı.")
        return

    # Ürün çek
    print("\n[çekim] SFCC HTTP çekimi başlıyor…")
    urunler = sfcc_urunler_cek(cookies)

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out = os.path.join(CIKTI_DIR, f"carrefour_be_producten_{tarih}.json")
    payload = {
        "kaynak": "Carrefour BE SFCC HTTP (cookie)",
        "chain_slug": "carrefour_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi": len(urunler),
        "urunler": urunler,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nTAMAM: {len(urunler)} ürün -> {out}")

    if not args.no_pause:
        input("\nÇıkmak için Enter…")


if __name__ == "__main__":
    main()
