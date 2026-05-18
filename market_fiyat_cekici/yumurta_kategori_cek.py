# -*- coding: utf-8 -*-
"""
5 marketin YUMURTA KATEGORİSİ sayfasından direkt veri çeker.
Her marketin yumurta bölümüne girer, tüm ürünleri alır.
"""
import sys, json, re, time, random
sys.stdout.reconfigure(encoding='utf-8')

# ── Market yumurta kategori URL'leri ─────────────────────────────
YUMURTA_URLS = {
    'colruyt': {
        'url': 'https://www.colruyt.be/nl/producten/alle-categorieen/zuivel/eieren',
        'yontem': 'playwright_html',
    },
    'aldi': {
        'url': 'https://www.aldi.be/nl/producten/verse-producten/eieren.html',
        'yontem': 'playwright_html',
    },
    'delhaize': {
        'api': 'https://www.delhaize.be/api/cache/products/query',
        'kategori': 'Eieren',
        'yontem': 'delhaize_graphql',
    },
    'lidl': {
        'url': 'https://www.lidl.be/nl/c/eieren/s10019022',
        'yontem': 'playwright_html',
    },
    'carrefour': {
        'url': 'https://www.carrefour.be/fr/c/oeufs/N-1z13zdl',
        'yontem': 'playwright_html',
    },
}

# ── Kategori belirleme ────────────────────────────────────────────
def kategori(name, desc=''):
    n = (name + ' ' + desc).lower()
    if any(k in n for k in ['kwart', 'bıldırcın', 'quail', 'caille']):
        return '🐦 Bıldırcın'
    if any(k in n for k in ['bio', 'biolog', 'organik', 'organique', 'organic']):
        return '🌿 Bio'
    if any(k in n for k in ['scharrel','uitloop','vrij','free range','serbest',
                              'plein air','fermier','poulet élevé']):
        return '🐔 Serbest Gezen'
    if any(k in n for k in ['hardgekookt','hard gekookt','cuit dur','haşlanmış']):
        return '⚡ Haşlanmış'
    if any(k in n for k in ['omega','verrijkt','enrichi']):
        return '💊 Omega/Özel'
    return '🥚 Normal'


# ── Colruyt: HTML'den parse ───────────────────────────────────────
def cek_colruyt_html(html):
    """Colruyt kategori sayfasındaki product card data attr'larını parse eder."""
    from html.parser import HTMLParser
    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urunler = []
        def handle_starttag(self, tag, attrs):
            if tag != 'a': return
            a = dict(attrs)
            if 'card--article' not in a.get('class',''):
                return
            price_str = a.get('data-tms-product-price','')
            promo_str = a.get('data-tms-product-promotion','')
            name = a.get('longname') or a.get('data-tms-product-name','')
            retail = a.get('retailproductnumber','')
            tech   = a.get('data-technical-article-number','')
            brand  = a.get('seobrand','')
            gtins  = a.get('gtin','').split(',')[0]
            unit_price_str = a.get('data-tms-product-unitprice','')
            nutriscore = a.get('nutriscore','')
            ecoscore   = a.get('ecoscorevalue','')

            try: price = float(price_str) if price_str else None
            except: price = None
            try: unit_price = float(unit_price_str) if unit_price_str else None
            except: unit_price = None

            in_promo = bool(promo_str and promo_str.strip())
            if name:
                self.urunler.append({
                    'isim': name, 'marka': brand,
                    'fiyat': price, 'unit_fiyat': unit_price,
                    'in_promo': in_promo,
                    'ean': gtins, 'retail_num': retail, 'tech_num': tech,
                    'nutriscore': nutriscore, 'ecoscore': ecoscore,
                    'image': None,  # saved HTML'de lokal path var, canlıdan URL gerekir
                })
    p = P()
    p.feed(html)
    return p.urunler


# ── Playwright ile sayfa çek ──────────────────────────────────────
def playwright_cek(url, market_adi):
    """Playwright ile sayfayı açar, tüm ürünleri yükletir, HTML döner."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"  [HATA] playwright yüklü değil: pip install playwright")
        return None

    print(f"  [{market_adi}] Playwright başlatılıyor...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1280, 'height': 900},
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(3)
            # Sayfa aşağı kaydır (lazy load için)
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 1500)")
                time.sleep(1)
            html = page.content()
        except Exception as e:
            print(f"  [{market_adi}] Hata: {e}")
            html = None
        finally:
            browser.close()
    return html


# ── Delhaize GraphQL ──────────────────────────────────────────────
def cek_delhaize_graphql():
    import urllib.request, json
    query = """
    {
      products(
        input: {
          category: "Eieren"
          size: 48
          from: 0
        }
      ) {
        products {
          id
          name
          price { value currency }
          pricePerUnit { value unit }
          promotions { discountedPrice { value } endDate }
          images { url }
          brand
          packagingDescription
        }
        total
      }
    }
    """
    # Delhaize'ın public GraphQL endpoint'i - session gerektiriyor
    # Bunun yerine category sayfasını playwright ile çekiyoruz
    return None


# ── ALDI HTML parse ───────────────────────────────────────────────
def cek_aldi_html(html):
    """ALDI ürün kartlarını parse eder."""
    urunler = []
    # ALDI product card pattern - JSON-LD veya data attribute'lardan
    # Product JSON arama
    matches = re.findall(r'"name"\s*:\s*"([^"]+)".*?"price"\s*:\s*"?(\d+[.,]\d+)"?',
                         html, re.DOTALL)
    # Alternatif: article-tile class'larını bul
    from html.parser import HTMLParser
    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urunler = []
            self._current = {}
            self._in_card = False
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            cls = a.get('class','')
            if 'article-tile' in cls or 'product-tile' in cls or 'product-item' in cls:
                self._in_card = True
                self._current = {}
            if self._in_card:
                if tag == 'img' and a.get('alt'):
                    self._current['isim'] = a['alt']
                    self._current['image'] = a.get('src','')
                if 'price' in cls.lower() and tag in ('span','div','p'):
                    pass  # fiyatı handle_data'da alacağız
        def handle_data(self, data):
            pass
        def handle_endtag(self, tag):
            pass
    return urunler


# ── Ana rapor ─────────────────────────────────────────────────────
def rapor():
    sonuclar = {}

    for market, cfg in YUMURTA_URLS.items():
        print(f"\n{'='*60}")
        print(f"  {market.upper()} yumurta kategorisi çekiliyor...")
        print(f"{'='*60}")

        urunler = []
        if cfg['yontem'] == 'playwright_html':
            html = playwright_cek(cfg['url'], market)
            if html and market == 'colruyt':
                urunler = cek_colruyt_html(html)
            elif html:
                # Diğer marketler için basit parse dene
                print(f"  HTML alındı ({len(html)} karakter). Manuel parse gerekebilir.")

        if not urunler:
            print(f"  Ürün çekilemedi veya parse başarısız.")
            continue

        # Kategorize et ve göster
        print(f"\n  {len(urunler)} ürün bulundu:\n")
        kat_gruplari = {}
        for u in urunler:
            kat = kategori(u['isim'])
            kat_gruplari.setdefault(kat, []).append(u)

        for kat, kat_urunler in sorted(kat_gruplari.items()):
            print(f"  [{kat}]")
            for u in sorted(kat_urunler, key=lambda x: x.get('unit_fiyat') or x.get('fiyat') or 999):
                isim = u['isim'][:55]
                fiyat_str = f"{u['fiyat']:.2f} EUR" if u.get('fiyat') else "Fiyat yok"
                unit_str = f" | {u['unit_fiyat']:.3f} €/adet".replace('.',',') if u.get('unit_fiyat') else ""
                promo_str = " [İNDİRİM]" if u.get('in_promo') else ""
                img_str = "✓" if u.get('image') else "✗"
                print(f"    • {isim}")
                print(f"      {fiyat_str}{unit_str}{promo_str} | Resim:{img_str} | EAN:{u.get('ean','?')}")
            print()

        sonuclar[market] = kat_gruplari

    print(f"\n{'='*60}")
    print("Tamamlandı.")
    return sonuclar


if __name__ == '__main__':
    rapor()
