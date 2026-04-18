# -*- coding: utf-8 -*-
"""
html_analiz.py — Kaydedilen HTML sayfalarından ürün verisi çeker ve DB'ye yazar.

sayfa_kaydet.py ile kaydedilen HTML dosyalarını okur,
her market için uygun parser ile ürünleri çıkarır,
Supabase'e upsert eder.

Kullanım:
  python html_analiz.py                          # cikti/html_pages/ altındaki tüm dosyalar
  python html_analiz.py --market delhaize        # sadece Delhaize dosyaları
  python html_analiz.py --dry-run                # DB'ye yazmadan test
  python html_analiz.py --dosya dosya.html       # tek dosya
"""
from __future__ import annotations
import argparse, json, os, re, sys, time, random
import importlib.util as _ilu
from pathlib import Path
from typing import Optional

# Çeviri sistemi
try:
    _ceviri_path = Path(__file__).parent / "ceviri_sistemi.py"
    _spec = _ilu.spec_from_file_location("ceviri_sistemi", _ceviri_path)
    _ceviri_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_ceviri_mod)
    _glossary_cevir = _ceviri_mod.glossary_cevir
except Exception:
    _glossary_cevir = None

def _cevir(isim: str):
    if not _glossary_cevir or not isim:
        return None
    try:
        sonuc, _ = _glossary_cevir(isim)
        return sonuc[:300]
    except Exception:
        return None

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install beautifulsoup4")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

SCRIPT_DIR  = Path(__file__).parent
HTML_DIR    = SCRIPT_DIR / "cikti" / "html_pages"
ALDI_BASE   = "https://www.aldi.be"
_aldi_sess  = None


def _aldi_session():
    global _aldi_sess
    if _aldi_sess is None:
        _aldi_sess = requests.Session()
        _aldi_sess.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "nl-BE,nl;q=0.9",
            "Referer": "https://www.aldi.be/",
        })
    return _aldi_sess


# ─── Supabase ────────────────────────────────────────────────────────────────

def load_secrets():
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = SCRIPT_DIR / "supabase_import_secrets.txt"
    lines = [l.strip() for l in path.read_text(encoding="utf-8", errors="ignore").splitlines()
             if l.strip() and not l.strip().startswith("#")]
    return lines[0].rstrip("/"), lines[1]


def upsert_urunler(sb_url: str, sb_key: str, urunler: list[dict], dry_run: bool):
    if not urunler:
        return 0
    if dry_run:
        for u in urunler[:3]:
            print(f"    [DRY] {u.get('chain_slug')} | {u.get('name','')[:50]} | {u.get('price')} | {u.get('unit_or_content')}")
        return len(urunler)

    hdrs = {
        "apikey": sb_key,
        "Authorization": "Bearer " + sb_key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    # Batch upsert — 200'erli gruplar
    # external_product_id NULL olan ürünleri ayır — conflict key olmadan güncelleme yapamayız
    with_pid   = [u for u in urunler if u.get("external_product_id")]
    without_pid = [u for u in urunler if not u.get("external_product_id")]

    toplam = 0
    # PID olanlar: upsert (on conflict update)
    for i in range(0, len(with_pid), 200):
        batch = with_pid[i:i+200]
        r = requests.post(
            sb_url + "/rest/v1/market_chain_products?on_conflict=chain_slug,external_product_id",
            json=batch,
            headers=hdrs,
        )
        if r.status_code in (200, 201):
            toplam += len(batch)
        else:
            print(f"    UPSERT HATA {r.status_code}: {r.text[:200]}")

    # PID olmayanlar: sadece unit_or_content ve image_url güncelle (isim+zincir eşleşmesiyle)
    for u in without_pid:
        if not u.get("unit_or_content") and not u.get("image_url"):
            continue
        patch_data = {}
        if u.get("unit_or_content"):
            patch_data["unit_or_content"] = u["unit_or_content"]
        if u.get("image_url"):
            patch_data["image_url"] = u["image_url"]
        if patch_data:
            r2 = requests.patch(
                sb_url + "/rest/v1/market_chain_products",
                params={"chain_slug": "eq." + u["chain_slug"], "name": "eq." + u["name"], "price": "eq." + str(u["price"])},
                json=patch_data,
                headers={**hdrs, "Prefer": "return=minimal"},
            )
            if r2.status_code == 204:
                toplam += 1

    return toplam


# ─── Fiyat yardımcıları ──────────────────────────────────────────────────────

def fiyat_parse(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.replace(",", ".").replace("€", "").replace("\xa0", "").strip()
    m = re.search(r"\d+\.?\d*", s)
    return float(m.group()) if m else None


def unit_parse(s: str) -> str:
    """'6 st', '12 stuks', '250 g', '1 l' gibi biçimleri normalize et."""
    if not s:
        return ""
    s = s.strip().lower()
    # "6 st" → "6 stuks"
    s = re.sub(r"\bst\b\.?", "stuks", s)
    return s[:200]


# ─── DELHAIZE parser ─────────────────────────────────────────────────────────

def parse_delhaize(html: str, kategori: str) -> list[dict]:
    """
    Delhaize ürün kartlarını parse eder.
    data-testid attribute'ları ile güvenilir şekilde veri çeker.
    """
    soup = BeautifulSoup(html, "html.parser")
    urunler = []

    # Kart wrapper: product-tile-title içeren h3'ün 3 üstü
    title_els = soup.select("[class*='product-tile-title']")
    if not title_els:
        return urunler

    for title_el in title_els:
        try:
            wrapper = title_el.parent.parent.parent

            # İsim: data-testid="product-name" span
            name_el = wrapper.select_one("[data-testid='product-name']")
            if not name_el:
                name_el = wrapper.select_one("a[data-testid='product-block-name-link']")
            name = name_el.get_text(" ", strip=True) if name_el else ""
            if not name:
                continue

            # Marka: data-testid="product-brand"
            brand_el = wrapper.select_one("[data-testid='product-brand']")
            brand = brand_el.get_text(strip=True) if brand_el else ""

            # Tam isim: marka + ürün adı (Delhaize'in orijinal formatı)
            full_name = (brand + " " + name).strip() if brand else name

            # Adet/içerik: data-testid="product-block-supplementary-price" ilk span
            unit_el = wrapper.select_one("[data-testid='product-block-supplementary-price']")
            unit = ""
            if unit_el:
                # "6 st" veya "250 gr" → ilk token
                raw = unit_el.get_text(" ", strip=True)
                m = re.match(r"(\d+[\.,]?\d*\s*(?:stuks?|st\.?|gr?|kg|cl|ml|l\b|x\s*\d+))", raw, re.I)
                if m:
                    unit = unit_parse(m.group(1))

            # Fiyat: data-testid="product-block-price"
            # Format: €[euro_el][sup_cent] → "€" + "2" + sup"19" = 2.19
            price_block = wrapper.select_one("[data-testid='product-block-price']")
            price = None
            if price_block:
                full_text = price_block.get_text(strip=True)
                # Temizle: €219 → 2.19, €1025 → 10.25
                digits = re.sub(r"[^\d]", "", full_text)
                if len(digits) >= 2:
                    # Son 2 rakam cent, öncekiler euro
                    euro  = digits[:-2] or "0"
                    cent  = digits[-2:]
                    price = float(euro + "." + cent)

            if not price or price <= 0:
                continue

            # İndirim: promo badge
            promo_el = wrapper.select_one(
                "[data-testid*='promo'], [data-testid*='promotion'], "
                "[class*='promo'], [class*='discount']"
            )
            in_promo = bool(promo_el)

            # İndirim fiyatı (eski fiyat strikethrough varsa)
            promo_price = None
            old_price_el = wrapper.select_one("[data-testid='product-block-old-price'], [class*='strikethrough']")
            if old_price_el and in_promo:
                old_digits = re.sub(r"[^\d]", "", old_price_el.get_text(strip=True))
                if len(old_digits) >= 2:
                    # Eski fiyat = normal, yeni fiyat = indirimli
                    old_price = float(old_digits[:-2] + "." + old_digits[-2:])
                    if old_price > price:
                        promo_price = price
                        price = old_price

            # Resim
            img_el = wrapper.select_one("img[data-testid='product-block-image']")
            if not img_el:
                img_el = wrapper.select_one("img[src]")
            img = img_el.get("src", "") if img_el else ""
            if img and img.startswith("//"):
                img = "https:" + img

            # External PID: href'ten
            pid_link = wrapper.select_one("a[data-testid='product-block-image-link']")
            pid = ""
            if pid_link and pid_link.get("href"):
                m2 = re.search(r"/p/([A-Za-z0-9]+)$", pid_link["href"])
                if m2:
                    pid = m2.group(1)

            urunler.append({
                "chain_slug":          "delhaize_be",
                "country_code":        "BE",
                "external_product_id": pid or None,
                "name":                full_name[:300],
                "name_tr":             _cevir(full_name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         promo_price,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue

    return urunler


# ─── ALDI snippet fetcher ────────────────────────────────────────────────────

def _aldi_snippet_cek(soup: BeautifulSoup, bulunan_pidler: set, kategori: str) -> list[dict]:
    """
    ALDI sayfasındaki yüklenmemiş placeholder'ları (data-loading-state=unloaded)
    HTTP ile çekip ürün verisini döndürür.
    Her placeholder'ın data-tile-url'si tek bir ürün snippet'ine işaret eder.
    """
    placeholders = soup.find_all(
        "div",
        attrs={"data-loading-state": "unloaded", "data-tile-url": True},
    )
    if not placeholders:
        return []

    # Unique URL'leri topla
    urls = []
    seen = set()
    for el in placeholders:
        raw_url = el.get("data-tile-url", "")
        if not raw_url or raw_url in seen:
            continue
        seen.add(raw_url)
        full_url = raw_url if raw_url.startswith("http") else ALDI_BASE + raw_url
        urls.append(full_url)

    if not urls:
        return []

    print(f"    [ALDI snippets] {len(urls)} placeholder fetchleniyor...")
    sess = _aldi_session()
    urunler = []
    hatalar = 0

    for i, url in enumerate(urls):
        try:
            r = sess.get(url, timeout=12)
            if r.status_code != 200:
                hatalar += 1
                continue

            sn = BeautifulSoup(r.text, "html.parser")
            tile = sn.find(attrs={"data-article": True})
            if not tile:
                continue

            d  = json.loads(tile.get("data-article", ""))
            pi = d.get("productInfo", {})

            name     = pi.get("productName", "").strip()
            pid      = str(pi.get("productID", "")).strip()
            brand    = pi.get("brand", "").strip()
            price    = pi.get("priceWithTax")
            in_promo = bool(pi.get("inPromotion", False))

            if not name or not price:
                continue
            if pid and pid in bulunan_pidler:
                continue  # Zaten yüklü

            try:
                price = float(price)
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue

            if pid:
                bulunan_pidler.add(pid)

            # Adet/içerik
            unit = ""
            m = re.search(
                r",?\s*(\d+\s*(?:x\s*\d+\s*(?:ml|cl|g|kg|l\b)|\s*(?:stuks?|st\.?|gr?|kg|cl|ml|l\b)))\s*$",
                name, re.I,
            )
            if m:
                unit = unit_parse(m.group(1))
                name = name[: m.start()].rstrip(", ").strip()

            # Resim
            img = ""
            img_el = tile.select_one("img[srcset]")
            if img_el:
                first = img_el.get("srcset", "").split(",")[0].strip().split(" ")[0]
                if first:
                    img = first if first.startswith("http") else ALDI_BASE + first
            if not img:
                img_el2 = tile.select_one("img[src]")
                if img_el2:
                    src = img_el2.get("src", "")
                    if src and not src.startswith("data:"):
                        img = src if src.startswith("http") else ALDI_BASE + src

            urunler.append({
                "chain_slug":          "aldi_be",
                "country_code":        "BE",
                "external_product_id": pid or None,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "brand":               brand[:200] or None,
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         None,
                "category_tr":         kategori_tr(kategori),
            })

            if (i + 1) % 20 == 0:
                print(f"      {i+1}/{len(urls)} snippet islendi...")

            time.sleep(random.uniform(0.25, 0.6))

        except Exception:
            hatalar += 1
            continue

    if hatalar:
        print(f"    [ALDI snippets] {hatalar} hata atlandı")

    return urunler


# ─── ALDI parser ──────────────────────────────────────────────────────────────

def parse_aldi(html: str, kategori: str) -> list[dict]:
    """
    ALDI ürün kartlarını parse eder.
    Her kart: <div class="mod mod-article-tile" data-article='{...JSON...}'>
    JSON içinde: productName, productID, brand, priceWithTax, inPromotion
    Adet bilgisi ismin sonunda: "Actimel aardbei, 12 st." → "12 st."
    """
    soup = BeautifulSoup(html, "html.parser")
    urunler = []

    kartlar = soup.select("[class*='mod-article-tile']")
    if not kartlar:
        # Fallback
        kartlar = soup.select("div[data-article]")

    for kart in kartlar:
        try:
            # data-article JSON'u parse et
            data_str = kart.get("data-article", "")
            if not data_str:
                continue
            d = json.loads(data_str)
            pi = d.get("productInfo", {})

            name      = pi.get("productName", "").strip()
            pid       = str(pi.get("productID", "")).strip()
            brand     = pi.get("brand", "").strip()
            price     = pi.get("priceWithTax")
            in_promo  = bool(pi.get("inPromotion", False))

            if not name or not price:
                continue
            try:
                price = float(price)
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue

            # Adet/içerik: ismin sonundaki "12 st.", "500 g", "6 x 100 ml" gibi
            unit = ""
            m = re.search(
                r",?\s*(\d+\s*(?:x\s*\d+\s*(?:ml|cl|g|kg|l\b)|\s*(?:stuks?|st\.?|gr?|kg|cl|ml|l\b)))\s*$",
                name, re.I
            )
            if m:
                unit = unit_parse(m.group(1))
                # İsimden adet bilgisini çıkar (temiz isim)
                name = name[:m.start()].rstrip(", ").strip()

            # Resim: srcset'teki ilk URL veya src
            img = ""
            img_el = kart.select_one("img[srcset]")
            if img_el:
                srcset = img_el.get("srcset", "")
                first = srcset.split(",")[0].strip().split(" ")[0]
                if first:
                    img = first if first.startswith("http") else "https://www.aldi.be" + first
            if not img:
                img_el2 = kart.select_one("img[src]")
                if img_el2:
                    src = img_el2.get("src", "")
                    if src and not src.startswith("data:"):
                        img = src if src.startswith("http") else "https://www.aldi.be" + src

            # İndirim fiyatı
            promo_price = None
            if in_promo:
                old_el = kart.select_one("s.price__previous, [class*='price__previous']")
                if old_el:
                    old_p = fiyat_parse(old_el.get_text(strip=True))
                    if old_p and old_p > price:
                        promo_price = price
                        price = old_p

            urunler.append({
                "chain_slug":          "aldi_be",
                "country_code":        "BE",
                "external_product_id": pid or None,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "brand":               brand[:200] or None,
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         promo_price,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue

    # Yüklenmemiş placeholder snippet'lerinden kalan ürünleri çek
    bulunan_pidler = {u["external_product_id"] for u in urunler if u.get("external_product_id")}
    ek_urunler = _aldi_snippet_cek(soup, bulunan_pidler, kategori)
    if ek_urunler:
        print(f"    [ALDI snippets] +{len(ek_urunler)} ürün eklendi")
        urunler.extend(ek_urunler)

    return urunler


# ─── COLRUYT parser ───────────────────────────────────────────────────────────

def parse_colruyt(html: str, kategori: str) -> list[dict]:
    """
    Colruyt Vue-rendered sayfa parser.
    CSS Modules hash'li sınıflar olduğu için kısmi eşleşme kullanır.
    """
    soup = BeautifulSoup(html, "html.parser")
    urunler = []

    # Colruyt'un Vue bileşenleri: ProductCard, ProductTile veya article
    kartlar = (
        soup.select("[class*='ProductCard']") or
        soup.select("[class*='product-card']") or
        soup.select("[class*='ProductTile']") or
        soup.select("article[class]") or
        []
    )

    # Çok genel article seçicisi sadece ürün içerikli kartlar için kullan
    if not kartlar:
        kartlar = soup.select("article")

    for kart in kartlar:
        try:
            # İsim: name / title / description sınıflı element
            name_el = (
                kart.select_one("[class*='name']") or
                kart.select_one("[class*='title']") or
                kart.select_one("[class*='description']") or
                kart.select_one("h2") or
                kart.select_one("h3")
            )
            name = name_el.get_text(" ", strip=True) if name_el else ""
            # Çok uzun veya çok kısa isimler geçersiz
            if not name or len(name) > 200 or len(name) < 2:
                continue

            # Fiyat: Price / price sınıflı element
            price = None
            price_el = (
                kart.select_one("[class*='Price']") or
                kart.select_one("[class*='price']")
            )
            if price_el:
                price = fiyat_parse(price_el.get_text(strip=True))
            # Fallback: € işareti içeren text node
            if not price:
                for el in kart.find_all(string=re.compile(r"€\s*\d")):
                    price = fiyat_parse(str(el))
                    if price:
                        break
            if not price or price <= 0:
                continue

            # Adet/içerik
            unit_el = (
                kart.select_one("[class*='unit']") or
                kart.select_one("[class*='Unit']") or
                kart.select_one("[class*='content']") or
                kart.select_one("[class*='weight']") or
                kart.select_one("[class*='quantity']")
            )
            unit = unit_parse(unit_el.get_text(strip=True)) if unit_el else ""

            # Ürün ID: /producten/ içeren href'ten
            pid = ""
            link = kart.select_one("a[href*='/producten/']") or kart.select_one("a[href]")
            if link:
                m = re.search(r"/([a-z0-9-]+-p\d+|p\d+)/?(?:\?|$)", link.get("href", ""), re.I)
                if m:
                    pid = m.group(1)

            # Resim
            img = ""
            img_el = kart.select_one("img[src]") or kart.select_one("img[data-src]")
            if img_el:
                img = img_el.get("src", "") or img_el.get("data-src", "")

            # İndirim
            promo_el = (
                kart.select_one("[class*='promo']") or
                kart.select_one("[class*='Promo']") or
                kart.select_one("[class*='badge']") or
                kart.select_one("[class*='Badge']") or
                kart.select_one("[class*='discount']")
            )
            in_promo = bool(promo_el)

            promo_price = None
            if in_promo:
                old_el = (
                    kart.select_one("[class*='old']") or
                    kart.select_one("[class*='previous']") or
                    kart.select_one("s") or
                    kart.select_one("del")
                )
                if old_el:
                    old_p = fiyat_parse(old_el.get_text(strip=True))
                    if old_p and old_p > price:
                        promo_price = price
                        price = old_p

            urunler.append({
                "chain_slug":          "colruyt_be",
                "country_code":        "BE",
                "external_product_id": pid or None,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         promo_price,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue

    return urunler


# ─── CARREFOUR parser ─────────────────────────────────────────────────────────

def parse_carrefour_json(data: dict, kategori: str) -> list[dict]:
    """carrefour_direct.py JSON ciktisini parse eder."""
    urunler = []
    products = data.get("products", [])
    for item in products:
        try:
            name = (item.get("name") or "").strip()
            if not name or len(name) > 300:
                continue

            raw_price = item.get("price", "")
            price = fiyat_parse(str(raw_price)) if raw_price else None
            if not price or price <= 0:
                continue

            pid = str(item.get("pid") or "").strip() or None
            img = (item.get("img") or "").strip() or None
            in_promo = bool(item.get("inPromo"))
            brand = (item.get("brand") or "").strip() or None
            href = (item.get("href") or "").strip()
            # Unit: href'ten /nl/p/URUNADI-100g gibi yapidan
            unit = None

            urunler.append({
                "chain_slug":          "carrefour_be",
                "country_code":        "BE",
                "external_product_id": pid,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit,
                "image_url":           img,
                "in_promo":            in_promo,
                "promo_price":         None,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue
    return urunler


def parse_carrefour(html: str, kategori: str) -> list[dict]:
    """Carrefour Belgium React-rendered sayfa parser."""
    soup = BeautifulSoup(html, "html.parser")
    urunler = []

    kartlar = (
        soup.select("[class*='product-card']") or
        soup.select("[class*='ProductCard']") or
        soup.select("[class*='product-item']") or
        soup.select("[data-testid*='product']") or
        soup.select("article") or
        []
    )

    for kart in kartlar:
        try:
            name_el = (
                kart.select_one("[class*='product-name']") or
                kart.select_one("[class*='product-title']") or
                kart.select_one("[data-testid='product-name']") or
                kart.select_one("[class*='name']") or
                kart.select_one("h2") or
                kart.select_one("h3")
            )
            name = name_el.get_text(" ", strip=True) if name_el else ""
            if not name or len(name) > 200:
                continue

            price_el = (
                kart.select_one("[class*='product-price']") or
                kart.select_one("[data-testid='price']") or
                kart.select_one("[class*='price']") or
                kart.select_one("[class*='Price']")
            )
            price = fiyat_parse(price_el.get_text(strip=True)) if price_el else None
            if not price or price <= 0:
                continue

            # PID: /p/XXXX href'ten
            pid = ""
            pid_link = kart.select_one("a[href]")
            if pid_link:
                m = re.search(r"/p/(\d+)", pid_link.get("href", ""))
                if m:
                    pid = m.group(1)

            unit_el = (
                kart.select_one("[class*='unit']") or
                kart.select_one("[class*='quantity']") or
                kart.select_one("[class*='weight']")
            )
            unit = unit_parse(unit_el.get_text(strip=True)) if unit_el else ""

            img_el = kart.select_one("img[src]")
            img = img_el.get("src", "") if img_el else ""

            promo_el = (
                kart.select_one("[class*='promo']") or
                kart.select_one("[class*='badge']") or
                kart.select_one("[class*='discount']")
            )
            in_promo = bool(promo_el)

            promo_price = None
            if in_promo:
                old_el = kart.select_one("s") or kart.select_one("del") or kart.select_one("[class*='old']")
                if old_el:
                    old_p = fiyat_parse(old_el.get_text(strip=True))
                    if old_p and old_p > price:
                        promo_price = price
                        price = old_p

            urunler.append({
                "chain_slug":          "carrefour_be",
                "country_code":        "BE",
                "external_product_id": pid or None,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         promo_price,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue

    return urunler


# ─── LIDL parser ─────────────────────────────────────────────────────────────

def parse_lidl_json(data: dict, kategori: str) -> list[dict]:
    """lidl_direct.py JSON ciktisini parse eder."""
    urunler = []
    products = data.get("products", [])
    for item in products:
        try:
            name = (item.get("name") or "").strip()
            if not name or len(name) > 300:
                continue
            raw_price = item.get("price", "")
            price = fiyat_parse(str(raw_price)) if raw_price else None
            if not price or price <= 0:
                continue
            pid = str(item.get("pid") or "").strip() or None
            img = (item.get("img") or "").strip() or None
            in_promo = bool(item.get("inPromo"))
            urunler.append({
                "chain_slug":          "lidl_be",
                "country_code":        "BE",
                "external_product_id": pid,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     None,
                "image_url":           img,
                "in_promo":            in_promo,
                "promo_price":         None,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue
    return urunler


def parse_lidl(html: str, kategori: str) -> list[dict]:
    """
    Lidl Belgium Nuxt/Vue-rendered sayfa parser.
    NUC bileşen kütüphanesi: nuc-a-product, nuc-m-product-price vb.
    JSON-LD structured data fallback olarak kullanılır.
    """
    soup = BeautifulSoup(html, "html.parser")
    urunler = []

    # NUC bileşen seçicileri (Lidl'in component kütüphanesi)
    kartlar = (
        soup.select("article.nuc-a-product") or
        soup.select("[class*='nuc-a-product']") or
        soup.select("[class*='product-item']") or
        soup.select("[class*='ProductGridItem']") or
        soup.select("[class*='product-grid-item']") or
        []
    )

    for kart in kartlar:
        try:
            # İsim
            name_el = (
                kart.select_one("[class*='product-headline']") or
                kart.select_one("[class*='product-title']") or
                kart.select_one("[class*='product-name']") or
                kart.select_one("[class*='headline']") or
                kart.select_one("h3") or
                kart.select_one("h2")
            )
            name = name_el.get_text(" ", strip=True) if name_el else ""
            if not name or len(name) > 200:
                continue

            # Fiyat: m-price__price veya price__price
            price_el = (
                kart.select_one("[class*='m-price__price']") or
                kart.select_one("[class*='price__price']") or
                kart.select_one("[class*='product-price']") or
                kart.select_one("[class*='price']")
            )
            price = fiyat_parse(price_el.get_text(strip=True)) if price_el else None
            if not price or price <= 0:
                continue

            # Adet/içerik: per-unit bilgisi
            unit_el = (
                kart.select_one("[class*='per-unit']") or
                kart.select_one("[class*='price__per-unit']") or
                kart.select_one("[class*='unit']")
            )
            unit = unit_parse(unit_el.get_text(strip=True)) if unit_el else ""
            # Eğer unit içinde fiyat bilgisi varsa (ör: "0,87 €/100g"), sadece birimi al
            if unit and re.search(r"[€\d].*[€\d]", unit):
                m = re.search(r"(?:per|/)\s*(\d+\s*(?:g|kg|ml|cl|l\b|stuks?))", unit, re.I)
                unit = m.group(1) if m else ""

            # Ürün kodu
            pid = kart.get("data-code", "") or kart.get("data-product-id", "") or kart.get("data-articleid", "")

            # Resim
            img = ""
            img_el = kart.select_one("img[src]") or kart.select_one("img[data-src]")
            if img_el:
                img = img_el.get("src", "") or img_el.get("data-src", "")
                if img and img.startswith("//"):
                    img = "https:" + img

            # İndirim / badge
            promo_el = (
                kart.select_one("[class*='badge']") or
                kart.select_one("[class*='promo']") or
                kart.select_one("[class*='offer']") or
                kart.select_one("[class*='discount']")
            )
            in_promo = bool(promo_el)

            promo_price = None
            if in_promo:
                old_el = kart.select_one("s") or kart.select_one("del") or kart.select_one("[class*='old']")
                if old_el:
                    old_p = fiyat_parse(old_el.get_text(strip=True))
                    if old_p and old_p > price:
                        promo_price = price
                        price = old_p

            urunler.append({
                "chain_slug":          "lidl_be",
                "country_code":        "BE",
                "external_product_id": str(pid)[:200] if pid else None,
                "name":                name[:300],
                "name_tr":             _cevir(name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         promo_price,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue

    # JSON-LD fallback (script tag içinde structured data)
    if not urunler:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = []
                if isinstance(data, dict):
                    if data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                    elif data.get("@type") == "Product":
                        items = [{"item": data}]
                elif isinstance(data, list):
                    items = data
                for item in items:
                    product = item.get("item", item) if isinstance(item, dict) else {}
                    if product.get("@type") not in ("Product", None):
                        continue
                    name = product.get("name", "")
                    offers = product.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    price = fiyat_parse(str(offers.get("price", "")))
                    pid   = str(product.get("sku", "") or product.get("productID", ""))
                    img   = product.get("image", "")
                    if isinstance(img, list):
                        img = img[0] if img else ""
                    if name and price:
                        urunler.append({
                            "chain_slug":          "lidl_be",
                            "country_code":        "BE",
                            "external_product_id": pid[:200] if pid else None,
                            "name":                name[:300],
                "name_tr":             _cevir(name),
                            "price":               price,
                            "currency":            "EUR",
                            "image_url":           str(img)[:1000] or None,
                            "in_promo":            False,
                            "promo_price":         None,
                            "category_tr":         kategori_tr(kategori),
                        })
            except Exception:
                continue

    return urunler


# ─── COLRUYT JSON parser (API intercept çıktısı) ─────────────────────────────

def parse_colruyt_json(data: dict, kategori: str) -> list[dict]:
    """
    Colruyt API intercept çıktısını ayrıştırır.
    Gerçek veri yapısı (apip.colruyt.be):
      item["price"]["basicPrice"]       → float fiyat
      item["price"]["isPromoActive"]    → "Y" / "N"
      item["technicalArticleNumber"]    → ürün ID
      item["name"], item["brand"]       → isim, marka
      item["content"]                   → içerik/miktar ("12st", "250 g")
      item["thumbNail"] / item["fullImage"] → resim
    """
    urunler = []

    # Ürün listesini bul
    product_list = None
    for key in ("products", "productDetails", "results", "items", "data"):
        val = data.get(key)
        if isinstance(val, list) and val:
            product_list = val
            break

    if not product_list:
        return []

    for item in product_list:
        try:
            if not isinstance(item, dict):
                continue

            # İsim
            name = (
                item.get("name") or
                item.get("LongName") or
                item.get("ShortName") or
                item.get("description") or
                item.get("productName") or
                ""
            ).strip()
            if not name:
                continue

            # Ürün kodu (gerçek format: technicalArticleNumber)
            pid = str(
                item.get("technicalArticleNumber") or
                item.get("commercialArticleNumber") or
                item.get("GTIN") or
                item.get("productCode") or
                item.get("id") or
                ""
            ).strip()

            # Fiyat: gerçek format item["price"]["basicPrice"]
            price = None
            price_obj = item.get("price")
            if isinstance(price_obj, dict):
                # Gerçek format
                raw = (price_obj.get("basicPrice") or
                       price_obj.get("recommendedPrice") or
                       price_obj.get("price"))
                try:
                    price = float(raw) if raw is not None else None
                except (TypeError, ValueError):
                    price = None
            elif price_obj is not None:
                try:
                    price = float(price_obj)
                except (TypeError, ValueError):
                    price = None

            # Eski format fallback (prices.price.basicPrice)
            if not price or price <= 0:
                prices = item.get("prices", {}) or {}
                old_obj = prices.get("price", {}) or {}
                raw = (old_obj.get("basicPrice") or
                       prices.get("recommendedPrice") or
                       prices.get("basicPrice"))
                try:
                    price = float(raw) if raw is not None else None
                except (TypeError, ValueError):
                    price = None

            if not price or price <= 0:
                continue

            # Promo: gerçek format item["price"]["isPromoActive"] == "Y"
            in_promo = False
            promo_price = None
            if isinstance(price_obj, dict):
                in_promo = price_obj.get("isPromoActive", "N") == "Y"
            # item["inPromo"] boolean alternatif
            if not in_promo:
                in_promo = bool(item.get("inPromo") or item.get("inPromotion") or item.get("hasPromotion"))
            # Promo fiyatı
            if in_promo and isinstance(price_obj, dict):
                p_raw = price_obj.get("quantityPrice") or price_obj.get("pricePerUOM")
                if p_raw:
                    try:
                        pp = float(p_raw)
                        if pp > 0 and pp < price:
                            promo_price = pp
                    except (TypeError, ValueError):
                        pass

            # Adet/içerik: gerçek format item["content"] = "12st", "250 g" vb.
            unit = ""
            for uk in ("content", "quantityN", "contentN", "quantity",
                       "packageDescription", "unitContent"):
                uv = item.get(uk, "")
                if uv:
                    unit = unit_parse(str(uv))
                    break
            if not unit:
                m = re.search(
                    r",?\s*(\d+\s*(?:x\s*\d+\s*(?:ml|cl|g|kg|l\b)|\s*(?:stuks?|st\.?|gr?|kg|cl|ml|l\b)))\s*$",
                    name, re.I,
                )
                if m:
                    unit = unit_parse(m.group(1))
                    name = name[: m.start()].rstrip(", ").strip()

            # Resim: gerçek format item["thumbNail"] veya item["fullImage"]
            img = (item.get("thumbNail") or item.get("fullImage") or
                   item.get("image") or item.get("thumbnail") or "")
            if isinstance(img, dict):
                img = img.get("url", "") or img.get("src", "")
            elif isinstance(img, list):
                img = img[0] if img else ""
            if img and str(img).startswith("//"):
                img = "https:" + str(img)

            # Marka
            brand = (item.get("brand") or item.get("seoBrand") or
                     item.get("trademark") or "").strip()
            full_name = (brand + " " + name).strip() if brand else name

            urunler.append({
                "chain_slug":          "colruyt_be",
                "country_code":        "BE",
                "external_product_id": pid or None,
                "name":                full_name[:300],
                "name_tr":             _cevir(full_name),
                "price":               price,
                "currency":            "EUR",
                "unit_or_content":     unit or None,
                "image_url":           str(img)[:1000] or None,
                "in_promo":            in_promo,
                "promo_price":         promo_price,
                "category_tr":         kategori_tr(kategori),
            })
        except Exception:
            continue

    return urunler


# ─── Kategori adı → Türkçe eşlemesi ─────────────────────────────────────────

KAT_MAP = {
    "zuivel": "Süt Ürünleri",
    "melkproducten": "Süt Ürünleri",
    "kaas": "Peynir",
    "eieren": "Yumurta",
    "vlees": "Et & Şarküteri",
    "vis": "Balık & Deniz Ürünleri",
    "groenten": "Sebze & Meyve",
    "fruit": "Sebze & Meyve",
    "brood": "Ekmek & Unlu Mamüller",
    "banket": "Ekmek & Unlu Mamüller",
    "dranken": "İçecekler",
    "pasta": "Tahıllar & Makarna",
    "rijst": "Tahıllar & Makarna",
    "conserven": "Konserve & Hazır Yemek",
    "snacks": "Atıştırmalık & Tatlı",
    "koekjes": "Atıştırmalık & Tatlı",
    "hygiene": "Kişisel Bakım",
    "cosmetica": "Kişisel Bakım",
    "schoonmaak": "Temizlik & Ev Bakımı",
    "huishouden": "Temizlik & Ev Bakımı",
    "diepvries": "Donmuş Ürünler",
    "vers": "Taze Ürünler",
    "sauzen": "Yağ, Sos & Baharat",
    "kant_en_klaar": "Konserve & Hazır Yemek",
}


def kategori_tr(kat_ad: str) -> str:
    kat_lower = kat_ad.lower()
    for k, v in KAT_MAP.items():
        if k in kat_lower:
            return v
    return "Diğer"


# ─── Dosya işleme ────────────────────────────────────────────────────────────

PARSER_MAP = {
    "delhaize":  parse_delhaize,
    "aldi":      parse_aldi,
    "colruyt":   parse_colruyt,
    "carrefour": parse_carrefour,
    "lidl":      parse_lidl,
}


def market_ve_kategori_bul(dosya_adi: str) -> tuple[str, str]:
    """Dosya adından market ve kategori çıkar. Örn: 'delhaize_Zuivel_p01_...' → ('delhaize','Zuivel')"""
    ad = Path(dosya_adi).stem  # uzantısız
    parcalar = ad.split("_")
    market = parcalar[0] if parcalar else "bilinmiyor"
    # Sayfa numarası ve tarihi çıkar
    kategori_parcalari = []
    for p in parcalar[1:]:
        if re.match(r"p\d+$", p) or re.match(r"\d{4}-\d{2}-\d{2}", p):
            break
        kategori_parcalari.append(p)
    kategori = "_".join(kategori_parcalari) if kategori_parcalari else "Genel"
    return market, kategori


def dosyayi_isle(dosya: Path, sb_url: str, sb_key: str, dry_run: bool, market_filtre: Optional[str]) -> int:
    market, kategori = market_ve_kategori_bul(dosya.name)

    if market_filtre and market != market_filtre:
        return 0

    # JSON dosyaları için özel akış (Colruyt ve Carrefour direct)
    if dosya.suffix == ".json" and market in ("colruyt", "carrefour", "lidl"):
        print(f"\n  {dosya.name}")
        print(f"    Market: {market} | Kategori: {kategori} [JSON]")
        try:
            data = json.loads(dosya.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            print(f"    JSON parse hatasi: {e}")
            return 0
        if market == "colruyt":
            urunler = parse_colruyt_json(data, kategori)
        elif market == "carrefour":
            urunler = parse_carrefour_json(data, kategori)
        else:  # lidl
            urunler = parse_lidl_json(data, kategori)
        print(f"    Bulunan urun: {len(urunler)}")
        if not urunler:
            print("    UYARI: Hic urun bulunamadi — JSON yapisi farkli olabilir.")
            return 0
        if dry_run:
            for u in urunler[:5]:
                print(f"      {str(u.get('price','')):>6} | {str(u.get('unit_or_content') or ''):>8} | {u.get('name','')[:50]}")
            return len(urunler)
        yazilan = upsert_urunler(sb_url, sb_key, urunler, dry_run)
        print(f"    DB'ye yazilan: {yazilan}")
        return yazilan

    parser = PARSER_MAP.get(market)
    if not parser:
        print(f"  [ATLANDI] Bilinmeyen market: {market} ({dosya.name})")
        return 0

    print(f"\n  {dosya.name}")
    print(f"    Market: {market} | Kategori: {kategori}")

    html = dosya.read_text(encoding="utf-8", errors="replace")
    urunler = parser(html, kategori)

    print(f"    Bulunan ürün: {len(urunler)}")
    if not urunler:
        print("    UYARI: Hiç ürün bulunamadı — HTML yapısı değişmiş olabilir.")
        # Diagnostic: HTML uzunluğu ve ilk 200 karakter
        print(f"    HTML uzunluğu: {len(html)} karakter")
        return 0

    if dry_run:
        print(f"    Örnek ürünler:")
        for u in urunler[:5]:
            print(f"      {str(u.get('price','')):>6} | {str(u.get('unit_or_content') or ''):>8} | {u.get('name','')[:50]}")
        return len(urunler)

    yazilan = upsert_urunler(sb_url, sb_key, urunler, dry_run)
    print(f"    DB'ye yazilan: {yazilan}")
    return yazilan


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default=None, help="Sadece bu market (delhaize/aldi/colruyt/carrefour)")
    parser.add_argument("--dry-run", action="store_true", help="DB'ye yazma, sadece göster")
    parser.add_argument("--dosya", default=None, help="Tek dosya işle")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()

    if args.dosya:
        dosyalar = [Path(args.dosya)]
    else:
        dosyalar = sorted(
            list(HTML_DIR.glob("*.html")) + list(HTML_DIR.glob("*.json"))
        )

    if not dosyalar:
        print(f"HTML dosyası bulunamadı: {HTML_DIR}")
        print("Önce sayfa_kaydet.py çalıştırın.")
        return

    print(f"{'='*60}")
    print(f"Toplam {len(dosyalar)} HTML dosyası işlenecek")
    if args.dry_run:
        print("  [DRY-RUN] DB'ye yazılmıyor")
    print(f"{'='*60}")

    toplam_urun = 0
    for dosya in dosyalar:
        toplam_urun += dosyayi_isle(dosya, sb_url, sb_key, args.dry_run, args.market)

    print(f"\n{'='*60}")
    print(f"TAMAMLANDI — Toplam {toplam_urun} ürün {'görüldü' if args.dry_run else 'DB güncellendi'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
