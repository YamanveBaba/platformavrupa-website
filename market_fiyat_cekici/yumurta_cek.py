# -*- coding: utf-8 -*-
"""
5 marketin yumurta kategori sayfasından tüm ürünleri çeker.
Playwright + camoufox kullanır.
"""
import sys, json, re, time, random
sys.stdout.reconfigure(encoding='utf-8')

MARKET_URLS = {
    'colruyt': 'https://www.colruyt.be/nl/producten/alle-categorieen/zuivel/eieren',
    'aldi':    'https://www.aldi.be/nl/producten/verse-producten/eieren.html',
    'delhaize':'https://www.delhaize.be/nl/Eieren/c/MK020200',
    'lidl':    'https://www.lidl.be/nl/c/eieren/s10019022',
    'carrefour':'https://www.carrefour.be/nl/c/eieren/N-1z13zdl',
}

MARKET_RENK = {
    'colruyt':  'Colruyt  🔴',
    'aldi':     'ALDI     🔵',
    'delhaize': 'Delhaize 🔴',
    'lidl':     'Lidl     🔵',
    'carrefour':'Carrefour🔵',
}

def kategori_belirle(name, desc=''):
    n = (name + ' ' + desc).lower()
    if any(k in n for k in ['kwart','bıldırcın','quail','caille']):
        return '🐦 Bıldırcın'
    if any(k in n for k in ['bio','biolog','organik','organique','organic']):
        return '🌿 Bio'
    if any(k in n for k in ['scharrel','uitloop','vrij','free-range','serbest',
                              'plein air','fermier','poulet élevé','uitloopeier']):
        return '🐔 Serbest Gezen'
    if any(k in n for k in ['hardgekookt','hard gekookt','cuit dur','haşlanmış']):
        return '⚡ Haşlanmış'
    if any(k in n for k in ['omega','verrijkt','enrichi']):
        return '💊 Omega/Özel'
    return '🥚 Normal'

def adet_fiyat(fiyat, isim, content=''):
    if not fiyat: return None
    metin = (content + ' ' + isim).lower()
    m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|adet|pièces?|eieren\b|oeufs?\b)', metin, re.I)
    if m:
        adet = int(m.group(1))
        if 3 <= adet <= 60:
            return round(fiyat / adet, 4)
    return None

# ── Colruyt: data-tms-* attribute parse ──────────────────────────
def parse_colruyt(html):
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
            isim = (a.get('longname') or a.get('data-tms-product-name') or '').strip()
            if not isim: return
            try: fiyat = float(a.get('data-tms-product-price','')) or None
            except: fiyat = None
            try: unit_f = float(a.get('data-tms-product-unitprice','')) or None
            except: unit_f = None
            promo = a.get('data-tms-product-promotion','')
            ean = a.get('gtin','').split(',')[0]
            ecoscore = a.get('ecoscorevalue','')
            nutri = a.get('nutriscore','')
            retail = a.get('retailproductnumber','')
            # image URL reconstruct
            img_url = None
            if retail:
                img_url = f"https://www.colruyt.be/sites/default/files/styles/product_image_list/public/product_images/{retail}.jpg"
            self.urunler.append({
                'isim': isim,
                'fiyat': fiyat,
                'unit_fiyat': unit_f,
                'in_promo': bool(promo),
                'ean': ean,
                'ecoscore': ecoscore,
                'nutriscore': nutri,
                'image': img_url,
                'retail_num': retail,
            })
    p = P()
    p.feed(html)
    return p.urunler

# ── ALDI: product-item class parse ───────────────────────────────
def parse_aldi(html):
    urunler = []
    # JSON-LD'den ürün verisi al
    ld_matches = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for ld in ld_matches:
        try:
            data = json.loads(ld)
            if isinstance(data, dict) and data.get('@type') == 'ItemList':
                for item in data.get('itemListElement', []):
                    p = item.get('item', {})
                    isim = p.get('name','')
                    if not isim: continue
                    offers = p.get('offers', {})
                    if isinstance(offers, list): offers = offers[0] if offers else {}
                    fiyat_str = offers.get('price','')
                    try: fiyat = float(str(fiyat_str).replace(',','.')) if fiyat_str else None
                    except: fiyat = None
                    img = p.get('image','')
                    if isinstance(img, list): img = img[0] if img else ''
                    desc = p.get('description','')
                    urunler.append({
                        'isim': isim, 'fiyat': fiyat, 'unit_fiyat': None,
                        'in_promo': False, 'image': img, 'desc': desc,
                    })
        except: pass

    # Fallback: product card class'larını ara
    if not urunler:
        from html.parser import HTMLParser
        class P(HTMLParser):
            def __init__(self):
                super().__init__()
                self.urunler = []
                self._current = {}
                self._in_card = self._in_title = self._in_price = False
            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                cls = a.get('class','')
                if any(c in cls for c in ['product-tile','article-tile','product-item','mod-article-tile']):
                    self._in_card = True
                    self._current = {}
                if self._in_card:
                    if tag == 'img' and a.get('alt') and 'data-src' in a:
                        self._current['isim'] = a['alt']
                        self._current['image'] = a.get('data-src') or a.get('src','')
                    if 'price' in cls.lower() and tag in ('span','div','p','strong'):
                        self._in_price = True
            def handle_data(self, data):
                if self._in_price:
                    m = re.search(r'(\d+[.,]\d+)', data)
                    if m:
                        try: self._current['fiyat'] = float(m.group(1).replace(',','.'))
                        except: pass
                    self._in_price = False
            def handle_endtag(self, tag):
                if tag in ('article','li','div') and self._current.get('isim'):
                    self.urunler.append({**self._current, 'unit_fiyat': None, 'in_promo': False})
                    self._current = {}
                    self._in_card = False
        pp = P()
        pp.feed(html)
        urunler = pp.urunler
    return urunler

# ── Delhaize parse ────────────────────────────────────────────────
def parse_delhaize(html):
    urunler = []
    # JSON-LD
    ld_matches = re.findall(r'application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
    for ld in ld_matches:
        try:
            data = json.loads(ld)
            items = []
            if isinstance(data, dict):
                if data.get('@type') == 'ItemList':
                    items = [i.get('item',{}) for i in data.get('itemListElement',[])]
                elif data.get('@type') == 'Product':
                    items = [data]
            for p in items:
                isim = p.get('name','')
                if not isim: continue
                offers = p.get('offers',{})
                if isinstance(offers, list): offers = offers[0] if offers else {}
                try: fiyat = float(offers.get('price',0)) or None
                except: fiyat = None
                img = p.get('image','')
                if isinstance(img, list): img = img[0] if img else ''
                urunler.append({'isim': isim, 'fiyat': fiyat, 'unit_fiyat': None,
                                'in_promo': False, 'image': img})
        except: pass

    # Delhaize data-product attribute
    matches = re.findall(r'data-product="([^"]+)"', html)
    for m in matches:
        try:
            p = json.loads(m.replace('&quot;','"'))
            isim = p.get('name','')
            if not isim or isim in [u['isim'] for u in urunler]: continue
            fiyat = p.get('price')
            urunler.append({'isim': isim, 'fiyat': fiyat, 'unit_fiyat': None,
                            'in_promo': bool(p.get('isPromo')), 'image': p.get('image','')})
        except: pass
    return urunler

# ── Lidl parse ────────────────────────────────────────────────────
def parse_lidl(html):
    urunler = []
    # Lidl ürün verisi script içinde
    matches = re.findall(r'"name"\s*:\s*"([^"]+)"[^}]*"price"\s*:\s*"?(\d+[.,]\d+)"?', html)
    seen = set()
    for isim, fiyat_str in matches:
        if isim in seen: continue
        seen.add(isim)
        try: fiyat = float(fiyat_str.replace(',','.'))
        except: fiyat = None
        urunler.append({'isim': isim, 'fiyat': fiyat, 'unit_fiyat': None,
                        'in_promo': False, 'image': None})
    return urunler

# ── Carrefour parse ───────────────────────────────────────────────
def parse_carrefour(html):
    urunler = []
    # Carrefour JSON verisi
    matches = re.findall(r'data-cnstrc-item-name="([^"]+)"[^>]*data-cnstrc-item-price="([^"]+)"', html)
    for isim, fiyat_str in matches:
        try: fiyat = float(fiyat_str)
        except: fiyat = None
        urunler.append({'isim': isim, 'fiyat': fiyat, 'unit_fiyat': None,
                        'in_promo': False, 'image': None})

    # Fallback: JSON-LD
    if not urunler:
        ld_matches = re.findall(r'application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
        for ld in ld_matches:
            try:
                data = json.loads(ld)
                if isinstance(data, dict) and data.get('@type') in ('Product','ItemList'):
                    items = [data] if data.get('@type') == 'Product' else [i.get('item',{}) for i in data.get('itemListElement',[])]
                    for p in items:
                        isim = p.get('name','')
                        if not isim: continue
                        offers = p.get('offers',{})
                        if isinstance(offers, list): offers = offers[0] if offers else {}
                        try: fiyat = float(offers.get('price',0)) or None
                        except: fiyat = None
                        img = p.get('image','')
                        urunler.append({'isim': isim, 'fiyat': fiyat, 'unit_fiyat': None,
                                        'in_promo': False, 'image': img})
            except: pass
    return urunler

PARSERS = {
    'colruyt':  parse_colruyt,
    'aldi':     parse_aldi,
    'delhaize': parse_delhaize,
    'lidl':     parse_lidl,
    'carrefour':parse_carrefour,
}

# ── Playwright HTML çekici ────────────────────────────────────────
def cek_html(market, url):
    print(f"  → {url}")
    try:
        from camoufox.sync_api import Camoufox
        use_camoufox = True
    except:
        use_camoufox = False

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  HATA: playwright yüklü değil")
        return None

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        ctx = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 900},
            locale='nl-BE',
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            time.sleep(3)
            # Cookie banner kapat
            for sel in ['#onetrust-accept-btn-handler',
                        'button[id*="accept"]',
                        'button:has-text("Accepteer")',
                        'button:has-text("Accepter")',
                        'button:has-text("Akkoord")',
                        'button:has-text("Alles")',
                        '.cookie-accept']:
                try:
                    page.click(sel, timeout=2000)
                    time.sleep(1)
                    break
                except: pass

            # Ürünlerin yüklenmesini bekle
            time.sleep(5)
            # Sayfa aşağı kaydır - lazy load tetikle
            for _ in range(8):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1.2)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(3)

            html = page.content()
            print(f"  HTML alındı: {len(html):,} karakter")

            # Debug: ürün var mı kontrol et
            card_count = html.count('card--article')
            product_count = html.count('data-tms-product-name')
            print(f"  card--article: {card_count}, data-tms-product-name: {product_count}")
        except Exception as e:
            print(f"  HATA: {e}")
            html = None
        finally:
            browser.close()
    return html

# ── Rapor ─────────────────────────────────────────────────────────
def rapor_yazdir(market, urunler):
    if not urunler:
        print(f"  Ürün bulunamadı.\n")
        return

    # Yanlış ürünleri filtrele (açıkça yumurta olmayan)
    DISLA = ['tonijn','tuna','sardien','makreel','sproeier','kraan','kast',
             'tapijt','klei','boetseer','bakgerei','eierkoker aparaat',
             'chocolade','snoep','wafer','aardbei','gelei kat','kattenvoeding',
             'hondenvoeding','prei ','confituur','yoghurt aardbei']
    gercek = []
    for u in urunler:
        n = u['isim'].lower()
        if not any(d in n for d in DISLA):
            gercek.append(u)

    print(f"  {len(gercek)} ürün ({len(urunler)-len(gercek)} yanlış eşleşme dışlandı)\n")

    # Kategorize
    kat_gruplari = {}
    for u in gercek:
        kat = kategori_belirle(u['isim'], u.get('desc',''))
        kat_gruplari.setdefault(kat, []).append(u)

    for kat, liste in sorted(kat_gruplari.items()):
        print(f"  [{kat}]")
        for u in sorted(liste, key=lambda x: x.get('unit_fiyat') or x.get('fiyat') or 999):
            isim = u['isim'][:55]
            fiyat = u.get('fiyat')
            unit_f = u.get('unit_fiyat') or adet_fiyat(fiyat, u['isim'])
            in_promo = u.get('in_promo', False)

            f_str = f"{fiyat:.2f} EUR" if fiyat else "Fiyat yok"
            u_str = f" | {unit_f:.3f} €/adet".replace('.',',') if unit_f else ""
            p_str = " [İNDİRİM]" if in_promo else ""
            img_str = "✓" if u.get('image') else "✗"

            print(f"    • {isim}")
            print(f"      {f_str}{u_str}{p_str} | Resim:{img_str}")
        print()

# ── ANA ───────────────────────────────────────────────────────────
def main():
    tum_sonuclar = {}

    for market, url in MARKET_URLS.items():
        print(f"\n{'='*65}")
        print(f"  {MARKET_RENK[market]}")
        print(f"{'='*65}")

        html = cek_html(market, url)
        if not html:
            print("  Sayfa çekilemedi.\n")
            continue

        parser = PARSERS[market]
        urunler = parser(html)
        print(f"  Parse sonucu: {len(urunler)} ürün")

        rapor_yazdir(market, urunler)
        tum_sonuclar[market] = urunler

        # Marketler arası bekleme
        time.sleep(random.uniform(3, 6))

    print(f"\n{'='*65}")
    print("TAMAMLANDI")
    print(f"{'='*65}")

if __name__ == '__main__':
    main()
