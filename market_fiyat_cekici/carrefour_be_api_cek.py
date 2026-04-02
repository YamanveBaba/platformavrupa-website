# -*- coding: utf-8 -*-
"""
Carrefour Belçika — Tam Ürün + Fiyat Çekici
Strateji: Playwright ile network interception → JSON API yanıtlarını yakala
SFCC (Salesforce Commerce Cloud) tabanlı; tüm kategori ağacını gezer.

Kullanım:
  python carrefour_be_api_cek.py --headed       # ilk kurulum (Cloudflare/cookie)
  python carrefour_be_api_cek.py                # headless (profil kaydedilmişse)
  python carrefour_be_api_cek.py --kesfet       # sadece API endpoint keşfi + logla
  python carrefour_be_api_cek.py --no-pause

Çıktı: cikti/carrefour_be_producten_YYYY-MM-DD_HH-MM.json
       cikti/carrefour_be_api_log_YYYY-MM-DD_HH-MM.jsonl  (keşif modu)
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
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, urlencode, urljoin

# ---------------------------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------------------------
CONFIG = {
    "ana_url": "https://www.carrefour.be/nl",
    "kategori_nav_url": "https://www.carrefour.be/nl/alle-producten",
    "promosyon_url": "https://www.carrefour.be/nl/al-onze-promoties",

    # SFCC site ID (keşif sırasında otomatik güncellenir)
    "sfcc_site_id": "",           # ör: "CarrefourBE" – keşif modunda loglanır

    # Her kategori sayfasında kaç scroll yapılacak
    "scroll_per_kategori": 25,
    # Bir sayfadan max kaç ürün (SFCC varsayılan 24, bazıları 48)
    "sayfa_basi_urun": 48,
    # Kaç kategori sonra uzun ara ver
    "uzun_ara_her": 8,
    # Timeout (ms)
    "goto_timeout_ms": 120_000,
    # JSON yanıt max boyut (byte); daha büyükleri atla
    "json_max_bytes": 10_000_000,
    # Minimum ürün uzunluğu (bir kez çekmeyi durdurmak için)
    "stale_limit": 5,
}

# JSON yanıtlarda ürün verisi içerdiğine dair anahtar kelimeler
URUN_ANAHTAR = ("name", "title", "productName", "naam", "product_name",
                "ean", "gtin", "barcode", "sku", "articleNumber",
                "price", "prijs", "unitPrice", "sellPrice", "regularPrice")

# URL filtresi: bu desenleri içeren endpoint'ler ürün datası verir (muhtemelen)
URL_URUN_DESENLERI = re.compile(
    r"(search|product|category|catalog|assortment|artikel|voeding|"
    r"Browse|Search|Category|Product|Grid|UpdateGrid|Load|listing|"
    r"facet|filter|promo|offer|promotie|aanbieding)",
    re.IGNORECASE,
)

# Bu URL'leri kesinlikle atla (analytics, tracking vb.)
URL_ATLA_DESENLERI = re.compile(
    r"(google-analytics|googletagmanager|gtag|adobe|newrelic|"
    r"sentry|facebook\.net|twitter\.com|cookiepro|onetrust|"
    r"\.css|\.js\?|\.woff|\.png|\.jpg|\.svg|favicon)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def insan_bekle(min_s: float = 1.2, max_s: float = 3.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def uzun_bekle() -> None:
    t = random.uniform(6, 14)
    print(f"  [bekleme] {t:.1f}s …")
    time.sleep(t)


def cerez_kabul(page) -> None:
    for sel in (
        'button:has-text("Alles accepteren")',
        'button:has-text("Tout accepter")',
        'button:has-text("Accepteren")',
        'button:has-text("Accept all")',
        '#onetrust-accept-btn-handler',
        '[data-testid="accept-all-cookies"]',
        'button[aria-label*="Accept" i]',
    ):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2500):
                loc.click(timeout=8000)
                time.sleep(1.5)
                print("  [cookie] kabul edildi.")
                return
        except Exception:
            continue


def json_icerik_urun_mu(data: Any, min_alan: int = 2) -> bool:
    """Bir JSON nesnesinin ürün datası içerip içermediğini tahmin et."""
    if isinstance(data, list) and len(data) > 0:
        ornek = data[0]
        if isinstance(ornek, dict):
            anahtarlar = {k.lower() for k in ornek.keys()}
            eslesme = sum(1 for a in URUN_ANAHTAR if a.lower() in anahtarlar)
            return eslesme >= min_alan
    if isinstance(data, dict):
        # Ürün listesi içeren bir wrapper olabilir
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0:
                if json_icerik_urun_mu(v, min_alan):
                    return True
    return False


def urunleri_cikart(data: Any) -> List[Dict]:
    """JSON yanıtından ürün listesini bul ve döndür."""
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], dict):
            return data
    if isinstance(data, dict):
        # Yaygın SFCC alanları
        for k in ("hits", "products", "items", "records", "data",
                  "productList", "results", "productSearchResult",
                  "product_list", "producten", "artikelen"):
            val = data.get(k)
            if isinstance(val, list) and len(val) > 0:
                return val
        # İç içe wrapper
        for v in data.values():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                if json_icerik_urun_mu(v):
                    return v
            if isinstance(v, dict):
                res = urunleri_cikart(v)
                if res:
                    return res
    return []


def toplam_urun_say(data: Any) -> Optional[int]:
    """Toplam ürün sayısını döndür (SFCC 'total', 'count', 'nbHits' vb.)."""
    if isinstance(data, dict):
        for k in ("total", "count", "nbHits", "numberOfResults", "totalRecords",
                  "totalHits", "totalCount", "productCount", "numResults",
                  "totalProducts", "nb_hits"):
            if k in data and isinstance(data[k], int):
                return data[k]
        # İç içe
        for v in data.values():
            if isinstance(v, dict):
                res = toplam_urun_say(v)
                if res is not None:
                    return res
    return None


def urun_normalize(ham: Dict, kaynak_url: str = "", kategori: str = "") -> Dict:
    """Ham ürün dict'ini standart alanlara dönüştür."""
    def al(*anahtarlar):
        for a in anahtarlar:
            v = ham.get(a)
            if v is not None and v != "":
                return v
            # Hiyerarşik: price.regular, price.value
            if "." in a:
                parcalar = a.split(".", 1)
                ust = ham.get(parcalar[0])
                if isinstance(ust, dict):
                    v = ust.get(parcalar[1])
                    if v is not None:
                        return v
        return None

    # Fiyat yardımcıları
    def fiyat_float(deger):
        if deger is None:
            return None
        if isinstance(deger, (int, float)):
            return round(float(deger), 2)
        s = str(deger).replace(",", ".").replace("€", "").strip()
        try:
            return round(float(re.sub(r"[^\d.]", "", s)), 2)
        except Exception:
            return None

    pid = str(al("id", "productId", "pid", "sku", "articleId",
                  "articleNumber", "product_id", "itemId", "code") or "")
    ean = str(al("ean", "gtin", "barcode", "upc", "ean13") or "")
    ad = str(al("name", "title", "productName", "naam", "product_name",
                "displayName", "longName") or "")
    marka = str(al("brand", "brandName", "merk", "manufacturer") or "")
    kategori_ad = str(al("category", "categoryName", "breadcrumb",
                         "primaryCategory", "categoryId") or kategori)
    fiyat = fiyat_float(al("price", "sellPrice", "unitPrice",
                            "regularPrice", "listPrice",
                            "price.regular", "price.value",
                            "normalPrice", "currentPrice"))
    promo_fiyat = fiyat_float(al("promoPrice", "discountedPrice",
                                  "salePrice", "reducedPrice",
                                  "price.reduced", "promotionPrice"))
    birim_fiyat = str(al("pricePerUnit", "unitPriceString",
                         "comparativePrice", "basePrice") or "")
    icerik = str(al("content", "quantity", "packagingSize",
                    "unitOfMeasure", "description", "hoeveelheid") or "")
    resim = str(al("image", "imageUrl", "thumbnail", "image.href",
                   "primaryImage", "images") or "")
    if isinstance(resim, list):
        resim = str(resim[0]) if resim else ""

    in_promo = promo_fiyat is not None and fiyat is not None and promo_fiyat < fiyat
    if not in_promo:
        in_promo = bool(al("onPromotion", "isPromo", "inPromotion",
                           "hasPromotion", "isOnSale", "promoted"))

    return {
        "carrefourPid": pid or ean[:30],
        "ean": ean,
        "name": ad[:300],
        "brand": marka[:120],
        "topCategoryName": kategori_ad[:200],
        "basicPrice": fiyat,
        "promoPrice": promo_fiyat,
        "inPromo": bool(in_promo),
        "unitContent": icerik[:100],
        "pricePerUnit": birim_fiyat[:80],
        "imageUrl": resim[:400],
        "kaynak_url": kaynak_url[:400],
    }


# ---------------------------------------------------------------------------
# Playwright yanıt izleyici
# ---------------------------------------------------------------------------

class YanitIzleyici:
    """Playwright response event'lerini yakalar ve ürün verisi içerenleri kaydeder."""

    def __init__(self, kesfet_modu: bool = False):
        self.kesfet_modu = kesfet_modu
        self.urunler: Dict[str, Dict] = {}   # pid/ean → normalized ürün
        self.api_log: List[Dict] = []        # keşif modunda tüm ilginç URL'ler
        self.yakalanan_url: Set[str] = set() # toplam sayfa bazlı tekrar atla
        self._kategori_simdiki: str = ""

    def kategori_guncelle(self, k: str) -> None:
        self._kategori_simdiki = k

    def handle(self, response) -> None:
        """Playwright response event handler."""
        try:
            url = response.url
            if URL_ATLA_DESENLERI.search(url):
                return
            ct = response.headers.get("content-type", "")
            if "json" not in ct and "javascript" not in ct:
                return
            # Boyut kontrolü
            try:
                body_bytes = response.body()
            except Exception:
                return
            if len(body_bytes) > CONFIG["json_max_bytes"] or len(body_bytes) < 20:
                return

            try:
                data = json.loads(body_bytes)
            except Exception:
                return

            if self.kesfet_modu:
                if URL_URUN_DESENLERI.search(url) or json_icerik_urun_mu(data):
                    self.api_log.append({
                        "url": url,
                        "content_type": ct,
                        "boyut_bytes": len(body_bytes),
                        "urun_gibi": json_icerik_urun_mu(data),
                        "toplam": toplam_urun_say(data),
                        "keys": list(data.keys())[:20] if isinstance(data, dict) else None,
                        "zaman": datetime.now().isoformat(),
                    })
                return  # keşif modunda veri ekleme

            # Normal mod: ürün çıkarımı
            if not json_icerik_urun_mu(data):
                return
            urun_listesi = urunleri_cikart(data)
            if not urun_listesi:
                return

            yeni = 0
            for ham in urun_listesi:
                if not isinstance(ham, dict):
                    continue
                norm = urun_normalize(ham, url, self._kategori_simdiki)
                key = norm["carrefourPid"] or norm["ean"] or norm["name"][:60]
                if not key or key in self.urunler:
                    continue
                self.urunler[key] = norm
                yeni += 1

            if yeni > 0:
                print(f"    [api] {yeni} yeni ürün ← {url[:90]}")
        except Exception:
            pass  # Yanıt zaten gitmiş olabilir


# ---------------------------------------------------------------------------
# Kategori URL'lerini keşfet
# ---------------------------------------------------------------------------

def kategori_urllerini_bul(page, temel_url: str) -> List[Dict[str, str]]:
    """Ana nav veya sitemap'ten kategori URL'lerini topla."""
    kategoriler = []
    gorulen: Set[str] = set()

    # Ana sayfadan navigation linklerini çek
    linkler = page.evaluate("""
        () => {
          const links = [];
          // Nav menüsü
          document.querySelectorAll('nav a, [class*="nav"] a, [class*="menu"] a, [class*="category"] a, [class*="categorie"] a').forEach(a => {
            const href = a.href || '';
            const text = (a.textContent || '').trim().slice(0, 100);
            if (href && !href.includes('#') && !href.includes('javascript:')) {
              links.push({ href, text });
            }
          });
          // Breadcrumb / kategori listing linkleri
          document.querySelectorAll('[class*="product"] a, [class*="listing"] a').forEach(a => {
            const href = a.href || '';
            const text = (a.textContent || '').trim().slice(0, 100);
            if (href) links.push({ href, text });
          });
          return links;
        }
    """)

    domain = urlparse(temel_url).netloc

    for link in linkler:
        href = link.get("href", "")
        text = link.get("text", "")
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != domain:
            continue
        # Carrefour BE kategori URL desenleri
        if not re.search(
            r"/(c/|categorie|category|rayon|afdeling|voeding|"
            r"dranken|huishoud|persoonlijke|baby|dier|tuin|"
            r"electronica|sport|speelgoed|kleding|nl/[a-z])",
            href,
            re.IGNORECASE,
        ):
            continue
        # Tekrar ve anlamsız URL filtresi
        if any(skip in href.lower() for skip in
               ("login", "account", "winkel", "winkelwagen", "checkout",
                "contact", "footer", "sitemap", "help", "faq")):
            continue
        norm_href = href.split("?")[0].rstrip("/")
        if norm_href in gorulen:
            continue
        gorulen.add(norm_href)
        kategoriler.append({"url": href, "ad": text or href.split("/")[-1]})

    return kategoriler


# ---------------------------------------------------------------------------
# Ana çekim döngüsü
# ---------------------------------------------------------------------------

def sayfayi_cek(page, izleyici: YanitIzleyici, url: str, kategori_ad: str,
                scroll_sayisi: int = 25) -> int:
    """
    Bir kategori/liste sayfasını yükle, scroll yap, API yanıtlarını yakala.
    Döndürür: bu sayfada yakalanan yeni ürün sayısı (tahmini)
    """
    izleyici.kategori_guncelle(kategori_ad)
    onceki_say = len(izleyici.urunler)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=CONFIG["goto_timeout_ms"])
    except Exception as e:
        print(f"  [goto hata] {e}")
        return 0

    insan_bekle(2.0, 4.5)

    # Scroll yaparak lazy-load / infinite scroll API'yi tetikle
    stale_sayac = 0
    onceki_toplam = len(izleyici.urunler)
    for i in range(scroll_sayisi):
        page.evaluate(
            "window.scrollBy(0, Math.min(900, document.body.scrollHeight * 0.08))"
        )
        insan_bekle(0.8, 2.2)

        if (i + 1) % 5 == 0:
            sonraki = len(izleyici.urunler)
            if sonraki == onceki_toplam:
                stale_sayac += 1
                if stale_sayac >= CONFIG["stale_limit"]:
                    break
            else:
                stale_sayac = 0
            onceki_toplam = sonraki

    yeni = len(izleyici.urunler) - onceki_say
    return yeni


def sfcc_sayfalama_cek(page, izleyici: YanitIzleyici,
                       kategori_url: str, kategori_ad: str) -> int:
    """
    SFCC tarzı URL parametreli sayfalama:
    ?start=0&sz=48, ?start=48&sz=48 … toplam bitene kadar.
    """
    yeni_toplam = 0
    start = 0
    sz = CONFIG["sayfa_basi_urun"]
    bos_sayac = 0

    while True:
        # URL'e start/sz ekle
        sep = "&" if "?" in kategori_url else "?"
        paginated_url = f"{kategori_url}{sep}start={start}&sz={sz}"
        onceki = len(izleyici.urunler)
        sayfayi_cek(page, izleyici, paginated_url, kategori_ad, scroll_sayisi=10)
        yeni = len(izleyici.urunler) - onceki
        yeni_toplam += yeni

        if yeni == 0:
            bos_sayac += 1
            if bos_sayac >= 2:
                break
        else:
            bos_sayac = 0

        start += sz
        if start > 10000:
            break
        insan_bekle(1.5, 3.5)

    return yeni_toplam


# ---------------------------------------------------------------------------
# Ana fonksiyon
# ---------------------------------------------------------------------------

def calistir(*, headed: bool, kesfet_modu: bool, no_pause: bool,
             max_kategori: int = 0) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("HATA: pip install playwright && playwright install chromium")
        return 1

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    profil = os.path.join(script_dir, "playwright_user_data", "carrefour_be")
    os.makedirs(profil, exist_ok=True)

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    izleyici = YanitIzleyici(kesfet_modu=kesfet_modu)

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
            extra_http_headers={
                "Accept-Language": "nl-BE,nl;q=0.9,fr-BE;q=0.8,fr;q=0.7,en;q=0.6",
            },
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Yanıt izleyiciyi bağla
        page.on("response", izleyici.handle)

        # ── 1. Ana sayfa + cookie kabul ──────────────────────────────────────
        print(f"\n[1] Ana sayfa yükleniyor: {CONFIG['ana_url']}")
        try:
            page.goto(CONFIG["ana_url"], wait_until="domcontentloaded",
                      timeout=CONFIG["goto_timeout_ms"])
        except Exception as e:
            print(f"  [goto] {e}")
        insan_bekle(2, 4)
        cerez_kabul(page)
        insan_bekle(1.5, 3)

        if kesfet_modu:
            # ── KESİF MODU ───────────────────────────────────────────────────
            print("\n[KESİF] Promosyon ve ürün sayfaları inceleniyor …")
            for url in [CONFIG["promosyon_url"], CONFIG["kategori_nav_url"]]:
                print(f"  → {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded",
                              timeout=CONFIG["goto_timeout_ms"])
                except Exception as e:
                    print(f"    [goto] {e}")
                    continue
                insan_bekle(2, 4)
                cerez_kabul(page)
                for _ in range(15):
                    page.evaluate("window.scrollBy(0, 700)")
                    insan_bekle(0.8, 1.8)

            log_dosya = os.path.join(cikti_dir, f"carrefour_be_api_log_{tarih}.jsonl")
            with open(log_dosya, "w", encoding="utf-8") as f:
                for entry in izleyici.api_log:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            print(f"\n[KESİF TAMAM] {len(izleyici.api_log)} endpoint kaydedildi → {log_dosya}")
            ctx.close()
            if not no_pause:
                input("\nÇıkmak için Enter …")
            return 0

        # ── 2. Promosyon sayfası ─────────────────────────────────────────────
        print(f"\n[2] Promosyon sayfası: {CONFIG['promosyon_url']}")
        sayfayi_cek(page, izleyici, CONFIG["promosyon_url"], "promoties",
                    scroll_sayisi=CONFIG["scroll_per_kategori"])
        print(f"  Toplam ürün: {len(izleyici.urunler)}")

        # ── 3. Tüm ürünler sayfası ───────────────────────────────────────────
        print(f"\n[3] Tüm ürünler: {CONFIG['kategori_nav_url']}")
        sayfayi_cek(page, izleyici, CONFIG["kategori_nav_url"], "alle-producten",
                    scroll_sayisi=CONFIG["scroll_per_kategori"])
        print(f"  Toplam ürün: {len(izleyici.urunler)}")

        # ── 4. Kategori keşfi ────────────────────────────────────────────────
        print(f"\n[4] Kategori linkleri aranıyor …")
        try:
            page.goto(CONFIG["ana_url"], wait_until="domcontentloaded",
                      timeout=CONFIG["goto_timeout_ms"])
            insan_bekle(2, 4)
        except Exception:
            pass

        kategoriler = kategori_urllerini_bul(page, CONFIG["ana_url"])

        # Sabit başlangıç kategorileri (sitenin değişmemesi halinde)
        sabit_kategoriler = [
            {"url": "https://www.carrefour.be/nl/c/FOOD", "ad": "Voeding"},
            {"url": "https://www.carrefour.be/nl/c/DRINKS", "ad": "Dranken"},
            {"url": "https://www.carrefour.be/nl/c/HOUSEHOLD", "ad": "Huishouden"},
            {"url": "https://www.carrefour.be/nl/c/PERSONAL_CARE", "ad": "Verzorging"},
            {"url": "https://www.carrefour.be/nl/c/BABY", "ad": "Baby"},
            {"url": "https://www.carrefour.be/nl/c/PET", "ad": "Dieren"},
            {"url": "https://www.carrefour.be/nl/c/GARDEN", "ad": "Tuin"},
            {"url": "https://www.carrefour.be/nl/c/ELECTRONICS", "ad": "Elektronica"},
            {"url": "https://www.carrefour.be/nl/c/SPORTS", "ad": "Sport"},
            {"url": "https://www.carrefour.be/nl/c/TOYS", "ad": "Speelgoed"},
            {"url": "https://www.carrefour.be/nl/c/CLOTHING", "ad": "Kleding"},
        ]

        # Keşfedilen + sabit, tekrarsız birleştir
        gorulen_url: Set[str] = {k["url"].split("?")[0].rstrip("/")
                                  for k in kategoriler}
        for k in sabit_kategoriler:
            norm = k["url"].rstrip("/")
            if norm not in gorulen_url:
                kategoriler.append(k)
                gorulen_url.add(norm)

        if max_kategori > 0:
            kategoriler = kategoriler[:max_kategori]

        print(f"  {len(kategoriler)} kategori bulundu.")

        # ── 5. Her kategoriyi gez ────────────────────────────────────────────
        for i, kat in enumerate(kategoriler):
            url = kat["url"]
            ad = kat["ad"]
            print(f"\n[kat {i+1}/{len(kategoriler)}] {ad}  ({url[:70]})")

            if (i + 1) % CONFIG["uzun_ara_her"] == 0:
                uzun_bekle()

            # Hem scroll hem sayfalama dene
            yeni_scroll = sayfayi_cek(page, izleyici, url, ad,
                                      scroll_sayisi=CONFIG["scroll_per_kategori"])

            # Scroll ile yeni ürün geldiyse sayfalama da dene
            if yeni_scroll > 0:
                yeni_page = sfcc_sayfalama_cek(page, izleyici, url, ad)
                print(f"  → scroll: {yeni_scroll}, sayfalama: {yeni_page} | "
                      f"toplam: {len(izleyici.urunler)}")
            else:
                # Scroll işe yaramadıysa sayfalama stratejisi uygula
                yeni_page = sfcc_sayfalama_cek(page, izleyici, url, ad)
                print(f"  → sadece sayfalama: {yeni_page} | "
                      f"toplam: {len(izleyici.urunler)}")

        ctx.close()

    # ── 6. Kaydet ────────────────────────────────────────────────────────────
    urunler = list(izleyici.urunler.values())
    out_path = os.path.join(cikti_dir, f"carrefour_be_producten_{tarih}.json")
    payload = {
        "kaynak": "Carrefour Belçika – API Network Interception (Playwright)",
        "chain_slug": "carrefour_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi": len(urunler),
        "urunler": urunler,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*60}")
    print(f"TAMAM: {len(urunler)} ürün → {out_path}")
    print(f"{'='*60}")

    if not no_pause:
        input("\nÇıkmak için Enter …")

    return 0 if urunler else 2


# ---------------------------------------------------------------------------
# Argüman ayrıştırma
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Carrefour BE Tam Çekici (API Interception)")
    ap.add_argument("--headed", action="store_true",
                    help="Görsel tarayıcı (ilk Cloudflare/cookie için)")
    ap.add_argument("--kesfet", action="store_true",
                    help="Sadece API endpoint keşfi yap, ürün çekme")
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument("--max-kategori", type=int, default=0,
                    help="Test: sadece ilk N kategoriyi çek (0=hepsi)")
    args = ap.parse_args()
    return calistir(
        headed=args.headed,
        kesfet_modu=args.kesfet,
        no_pause=args.no_pause,
        max_kategori=args.max_kategori,
    )


if __name__ == "__main__":
    raise SystemExit(main())
