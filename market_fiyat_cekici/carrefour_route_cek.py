# -*- coding: utf-8 -*-
"""
Carrefour BE — page.route() ile güvenilir JSON yakalama + browser-içi fetch
page.route() response.body()'yi TÜKETMEDEN önce yakalar.

Strateji:
  1. al-onze-promoties sayfasını aç (CF geçiyor)
  2. page.route() ile TÜM JSON yanıtlarını kaydet
  3. Scroll yaparak Einstein/SFCC API'lerini tetikle
  4. Ardından evaluate() ile browser içinden kategori URL'lerine fetch at

Kullanım:
  python carrefour_route_cek.py --headed
"""
from __future__ import annotations
import argparse, json, os, re, time, random
from datetime import datetime
from typing import Dict, List, Optional

script_dir = os.path.dirname(os.path.abspath(__file__))
CIKTI_DIR  = os.path.join(script_dir, "cikti")
tarih      = datetime.now().strftime("%Y-%m-%d_%H-%M")
JSONL_DOSYA = os.path.join(script_dir, f"carrefour_route_log_{tarih}.jsonl")

BASE    = "https://www.carrefour.be"
SITE_ID = "Sites-carrefour-be-Site"

# Kategori cgid listesi — browser içi fetch ile denenecek
KATEGORI_CGID = [
    "food", "fresh", "drinks", "bakery", "frozen", "snacks",
    "dairy", "meat", "fish", "vegetables", "fruit",
    "household", "cleaning", "personal-care", "beauty",
    "baby", "pet", "garden", "electronics", "sports", "toys",
    "promotions",
]


def insan_bekle(mn=1.0, mx=2.5):
    time.sleep(random.uniform(mn, mx))


def calistir(headed: bool, no_pause: bool):
    from playwright.sync_api import sync_playwright, Route, Request

    os.makedirs(CIKTI_DIR, exist_ok=True)
    profil = os.path.join(script_dir, "playwright_user_data", "carrefour_be_v3")
    os.makedirs(profil, exist_ok=True)

    urunler: Dict[str, Dict] = {}
    yakalanan_jsonl = []

    def route_handler(route: Route):
        """page.route() handler — response body'yi güvenilir şekilde yakala."""
        request = route.request
        url = request.url

        # Statik dosyaları direkt geçir
        if re.search(r"\.(png|jpg|gif|svg|ico|woff|css|mp4|webp|ttf)(\?|$)", url, re.I):
            route.continue_()
            return
        if re.search(r"(google-analytics|gtm|facebook\.net|newrelic|sentry|doubleclick|outbrain|pinterest|teads|abtasty|fullstory|cookielaw)", url, re.I):
            route.continue_()
            return

        # Yanıtı al
        try:
            response = route.fetch()
        except Exception:
            route.continue_()
            return

        ct = response.headers.get("content-type", "")
        body = response.body()

        # JSON yanıtları işle
        if "json" in ct and len(body) > 30:
            try:
                data = json.loads(body)
                entry = {
                    "url": url,
                    "status": response.status,
                    "ct": ct,
                    "boyut": len(body),
                    "data": data,
                    "zaman": datetime.now().isoformat(),
                }
                yakalanan_jsonl.append(entry)

                # Ürün çıkarımı
                urun_listesi = _urun_listesi_bul(data)
                yeni = _ekle(urun_listesi, urunler, url)
                toplam_sayisi = _toplam_bul(data)

                if urun_listesi or toplam_sayisi:
                    print(f"  [JSON] {len(body):7d}b  +{yeni} ürün  "
                          f"toplam={toplam_sayisi}  {url[:90]}")
                elif len(body) > 5000:
                    print(f"  [JSON] {len(body):7d}b  {url[:90]}")

            except Exception as e:
                pass

        # Continue with the fetched response
        route.fulfill(
            status=response.status,
            headers=dict(response.headers),
            body=body,
        )

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profil,
            headless=not headed,
            locale="nl-BE",
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

        # Route handler'ı bağla
        page.route("**/*", route_handler)

        # ── 1. Promoties sayfasını yükle ───────────────────────────────────
        target = f"{BASE}/nl/al-onze-promoties"
        print(f"\n[1] Yükleniyor: {target}")
        try:
            page.goto(target, wait_until="domcontentloaded", timeout=120_000)
        except Exception as e:
            print(f"  [goto hata] {e}")

        # CF bekleme
        for _ in range(20):
            title = page.title()
            if "Cloudflare" not in title and "Attention" not in title:
                break
            print(f"  [CF] {title} — 3s bekleniyor…")
            time.sleep(3)

        title = page.title()
        url_simdi = page.url
        print(f"  Sayfa: {title}  URL: {url_simdi}")

        if "Cloudflare" in title or "Attention" in title:
            print("  [!] Cloudflare geçilemedi. --headed ile tarayıcıda challenge'ı geçin.")
            ctx.close()
            return 1

        # Cookie kabul
        for sel in ('button:has-text("Alles accepteren")', '#onetrust-accept-btn-handler',
                    '[data-testid="accept-all-cookies"]'):
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=2000):
                    loc.click()
                    print("  [cookie] kabul edildi")
                    time.sleep(1.5)
                    break
            except Exception:
                pass

        insan_bekle(2, 4)
        print(f"  Şu ana kadar {len(urunler)} ürün yakalandı.")

        # ── 2. Scroll ile Einstein API'lerini tetikle ──────────────────────
        print(f"\n[2] Scroll (30 tur)…")
        for i in range(30):
            page.evaluate("window.scrollBy(0, 700)")
            insan_bekle(0.6, 1.4)
            if i % 10 == 9:
                print(f"  scroll {i+1}/30 — ürün: {len(urunler)}")

        print(f"  Scroll sonrası: {len(urunler)} ürün")

        # ── 3. Browser içinden kategori fetch'leri ─────────────────────────
        print(f"\n[3] Browser içi kategori fetch'leri…")

        # Önce hangi SFCC endpoint'in çalıştığını test et
        test_js = f"""
            async () => {{
                const urls = [
                    '/on/demandware.store/{SITE_ID}/default/Search-Show?cgid=food&start=0&sz=5&format=ajax',
                    '/on/demandware.store/{SITE_ID}/nl_BE/Search-Show?cgid=food&start=0&sz=5&format=ajax',
                    '/nl/search?q=melk&format=json',
                ];
                const results = [];
                for (const url of urls) {{
                    try {{
                        const r = await fetch(url, {{credentials: 'include'}});
                        const text = await r.text();
                        results.push({{url, status: r.status, boyut: text.length, ilk100: text.slice(0,100)}});
                    }} catch(e) {{
                        results.push({{url, hata: e.toString()}});
                    }}
                }}
                return results;
            }}
        """
        try:
            test_sonuc = page.evaluate(test_js)
            print("  [test] SFCC endpoint sonuçları:")
            for r in test_sonuc:
                print(f"    status={r.get('status')} boyut={r.get('boyut',0)} {r.get('url','')}")
                print(f"    ilk100: {r.get('ilk100','')[:100]}")
        except Exception as e:
            print(f"  [test hata] {e}")

        # Her kategori için fetch
        basarili_endpoint = None
        for cgid in KATEGORI_CGID:
            # Farklı endpoint formatları dene
            for endpoint_tpl in [
                f"/on/demandware.store/{SITE_ID}/default/Search-Show?cgid={{cgid}}&start=0&sz=24&format=ajax",
                f"/on/demandware.store/{SITE_ID}/nl_BE/Search-Show?cgid={{cgid}}&start=0&sz=24&format=ajax",
            ]:
                endpoint = endpoint_tpl.format(cgid=cgid)
                js = f"""
                    async () => {{
                        const r = await fetch('{endpoint}', {{credentials: 'include', headers: {{'X-Requested-With': 'XMLHttpRequest'}}}});
                        const text = await r.text();
                        return {{status: r.status, ct: r.headers.get('content-type'), text}};
                    }}
                """
                try:
                    res = page.evaluate(js)
                    status = res.get("status")
                    ct = res.get("ct", "")
                    text = res.get("text", "")
                    print(f"  [{cgid}] status={status} boyut={len(text)} ct={ct[:30]}")

                    if status == 200 and len(text) > 100:
                        basarili_endpoint = endpoint_tpl
                        # JSON parse et
                        if "json" in ct:
                            data = json.loads(text)
                            urun_listesi = _urun_listesi_bul(data)
                            yeni = _ekle(urun_listesi, urunler, cgid)
                            print(f"    +{yeni} ürün (toplam {len(urunler)})")
                        elif "html" in ct:
                            from_html = _html_urun_cikart(text, cgid)
                            yeni = _ekle(from_html, urunler, cgid)
                            print(f"    +{yeni} ürün HTML'den (toplam {len(urunler)})")
                        break
                    elif status == 403:
                        print(f"    [403] bu endpoint de bloklu")
                        break
                except Exception as e:
                    print(f"  [{cgid}] fetch hata: {e}")

            insan_bekle(0.5, 1.5)

        ctx.close()

    # ── 4. JSONL kaydet ────────────────────────────────────────────────────
    with open(JSONL_DOSYA, "w", encoding="utf-8") as f:
        for entry in yakalanan_jsonl:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\n[log] {len(yakalanan_jsonl)} JSON yanıt -> {JSONL_DOSYA}")

    # ── 5. Ürünleri kaydet ─────────────────────────────────────────────────
    urun_listesi_final = list(urunler.values())
    if urun_listesi_final:
        out = os.path.join(CIKTI_DIR, f"carrefour_be_producten_{tarih}.json")
        payload = {
            "kaynak": "Carrefour BE route-intercept + browser-fetch",
            "chain_slug": "carrefour_be",
            "country_code": "BE",
            "cekilme_tarihi": datetime.now().isoformat(),
            "urun_sayisi": len(urun_listesi_final),
            "urunler": urun_listesi_final,
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"TAMAM: {len(urun_listesi_final)} ürün -> {out}")
    else:
        print("\n[!] Hiç ürün yakalanamadı.")
        print(f"    JSON log ({len(yakalanan_jsonl)} kayıt): {JSONL_DOSYA}")

    if not no_pause:
        input("\nÇıkmak için Enter…")
    return 0


# ────────────────────────────────────────────────────────
# Yardımcı fonksiyonlar
# ────────────────────────────────────────────────────────

def _urun_listesi_bul(data) -> List[Dict]:
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data
    if isinstance(data, dict):
        for k in ("hits", "products", "items", "productSearchResult",
                  "records", "product_list", "data", "results",
                  "recommendations", "recs", "productRecs"):
            v = data.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        for v in data.values():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                if any(k in v[0] for k in ("id","pid","name","price","ean","productId")):
                    return v
            if isinstance(v, dict):
                r = _urun_listesi_bul(v)
                if r:
                    return r
    return []


def _toplam_bul(data) -> Optional[int]:
    if isinstance(data, dict):
        for k in ("total", "count", "nbHits", "numberOfResults", "totalRecords",
                  "totalHits", "totalCount", "productCount", "numResults"):
            if isinstance(data.get(k), int):
                return data[k]
        for v in data.values():
            if isinstance(v, dict):
                r = _toplam_bul(v)
                if r:
                    return r
    return None


def _fiyat(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    try:
        return round(float(re.sub(r"[^\d.]", "", str(v).replace(",", "."))), 2)
    except Exception:
        return None


def _ekle(liste, hedef: Dict, kaynak: str) -> int:
    yeni = 0
    for item in liste:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or item.get("productId") or item.get("pid") or
                  item.get("sku") or item.get("articleId") or item.get("itemId") or "")
        name = str(item.get("name") or item.get("title") or item.get("displayName") or "")
        key = pid or name[:60]
        if not key or key in hedef:
            continue
        price_raw = (item.get("price") or item.get("sellPrice") or
                     item.get("regularPrice") or item.get("listPrice"))
        promo_raw = (item.get("promoPrice") or item.get("salePrice") or
                     item.get("reducedPrice") or item.get("discountedPrice"))
        # price dict mi?
        if isinstance(price_raw, dict):
            price_raw = price_raw.get("sales", {}).get("value") or price_raw.get("regular", {}).get("value") or price_raw.get("value")
        hedef[key] = {
            "carrefourPid": pid,
            "ean": str(item.get("ean") or item.get("gtin") or item.get("barcode") or ""),
            "name": name[:300],
            "brand": str(item.get("brand") or item.get("brandName") or ""),
            "topCategoryName": str(item.get("category") or item.get("categoryId") or kaynak),
            "basicPrice": _fiyat(price_raw),
            "promoPrice": _fiyat(promo_raw),
            "inPromo": bool(item.get("onPromotion") or item.get("isPromo") or
                            item.get("inPromotion") or item.get("promoted")),
            "unitContent": str(item.get("content") or item.get("quantity") or ""),
            "imageUrl": str(item.get("image") or item.get("imageUrl") or "")[:400],
        }
        yeni += 1
    return yeni


def _html_urun_cikart(html: str, kategori: str) -> List[Dict]:
    urunler = []
    pid_re = re.compile(r'data-pid=["\']([^"\']+)["\']')
    pids_seen = set()
    for m in pid_re.finditer(html):
        pid = m.group(1)
        if pid in pids_seen:
            continue
        pids_seen.add(pid)
        start = max(0, m.start() - 50)
        chunk = html[start:min(len(html), m.end() + 600)]
        nm = re.search(r'(?:aria-label|data-name|data-product-name)=["\']([^"\']{5,150})["\']', chunk)
        name = nm.group(1) if nm else ""
        pm = re.search(r'data-price=["\']([0-9.,]+)["\']|itemprop="price"\s+content=["\']([0-9.,]+)["\']', chunk)
        price = None
        if pm:
            raw = pm.group(1) or pm.group(2)
            try:
                price = float(raw.replace(",", "."))
            except Exception:
                pass
        urunler.append({"carrefourPid": pid, "name": name,
                        "basicPrice": price, "topCategoryName": kategori})
    return urunler


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--no-pause", action="store_true")
    args = ap.parse_args()
    return calistir(headed=args.headed, no_pause=args.no_pause)


if __name__ == "__main__":
    raise SystemExit(main())
