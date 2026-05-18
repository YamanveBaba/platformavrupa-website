# -*- coding: utf-8 -*-
"""
5 marketteki yumurta sayfalarından tüm ürün verisini + resim URL'lerini çeker.
D:\MARKET\YUMURTALAR klasöründeki HTML dosyalarını kullanır.
Çıktı: yumurta_data.json + yumurta_karsilastir.html
"""
import sys, re, json, os
from html.parser import HTMLParser
from urllib.parse import unquote
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

KLASOR = Path("D:/MARKET/YUMURTALAR")
CIKTI_JSON = Path("D:/MARKET/yumurta_data.json")
CIKTI_HTML = Path("C:/Users/yaman/Desktop/platformavrupa-website/yumurta_karsilastir.html")

MARKET_RENK = {
    'colruyt':  {'bg': '#005C8A', 'text': '#fff', 'label': 'COLRUYT'},
    'aldi':     {'bg': '#00A0E9', 'text': '#fff', 'label': 'ALDI'},
    'carrefour':{'bg': '#004F9F', 'text': '#fff', 'label': 'CARREFOUR'},
    'delhaize': {'bg': '#E31837', 'text': '#fff', 'label': 'DELHAIZE'},
    'lidl':     {'bg': '#FFD800', 'text': '#003087', 'label': 'LIDL'},
}

DISLAMA = [
    'chocolade','praline','fondant','caramel','paas','pâques','dragee',
    'eitjes zakje','madeleines','lasagne','macaroni','noodle','noedels',
    'wafels','spaghetti','tagliatelle','viseieren','lompviseieren',
    'foreleieren','zalmeieren','mayonaise','mayo ','eierwafels',
    'eiervorm','sproeier','kraan','advocaat','eierlikeur','eikenblad',
    'libeert','kattenvoeding','pannenkoek','granola','tortilla','penne',
    'instant noodle','macaroni','tortelloni',
]

def is_yumurta(name):
    n = name.lower()
    return not any(d in n for d in DISLAMA)

def kategori(name):
    n = name.lower()
    if any(k in n for k in ['kwart','bıldırcın','quail','caille','kwartelei']):
        return 'bildircin'
    if any(k in n for k in ['bio','biologisch','organik','organic','organique']):
        return 'bio'
    if any(k in n for k in ['scharrel','uitloop','vrij','vrije','serbest','plein air',
                              'fermier','gezen','free range','scharreleieren']):
        return 'serbest'
    return 'normal'

def adet_fiyat(fiyat, name, content=''):
    if not fiyat or fiyat <= 0:
        return None
    metin = ((content or '') + ' ' + name).lower()
    m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|pièces?|adet|stuk\b)', metin, re.I)
    if m:
        adet = int(m.group(1))
        if 3 <= adet <= 60:
            return round(fiyat / adet, 4)
    return None

# ─── COLRUYT ──────────────────────────────────────────────────────────────────
def parse_colruyt():
    dosya = KLASOR / "Eieren - Zuivel _ Colruyt.html"
    if not dosya.exists():
        dosya = KLASOR / "Yumurta - Süt Ürünleri _ Colruyt.html"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    class P(HTMLParser):
        def __init__(self):
            super().__init__(); self.urunler = []
        def handle_starttag(self, tag, attrs):
            if tag != 'a': return
            a = dict(attrs)
            if 'card--article' not in a.get('class', ''): return
            isim = (a.get('longname') or a.get('data-tms-product-name') or '').strip()
            if not isim: return
            try: fiyat = float(a.get('data-tms-product-price','') or 0) or None
            except: fiyat = None
            try: unit_f = float(a.get('data-tms-product-unitprice','') or 0) or None
            except: unit_f = None
            retail = a.get('retailproductnumber','')
            promo_str = a.get('data-tms-product-promotion','') or ''
            brand = a.get('seobrand','')
            nutri = a.get('nutriscore','')
            img = (f"https://ecustomermwstatic.colruytgroup.com/"
                   f"ecustomermwstatic/nl/assets/asset-{retail}.jpg") if retail else None
            self.urunler.append({
                'isim': isim, 'marka': brand, 'fiyat': fiyat, 'unit_fiyat': unit_f,
                'in_promo': bool(promo_str and promo_str.strip()),
                'image': img, 'nutriscore': nutri, 'market': 'colruyt',
            })

    p = P(); p.feed(html)
    return p.urunler

# ─── ALDI ─────────────────────────────────────────────────────────────────────
def parse_aldi():
    dosya = KLASOR / "Verse eieren kopen (scharreleieren, bio, etc.) _ ALDI België.html"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    # data-article JSON'dan çek
    articles = re.findall(r'data-article=[\"\'](\{[^>]+?\})[\"\'>\s]', html)
    # Alternatif: &quot; ile encoded
    articles2 = re.findall(r'data-article=\"(\{&quot;.+?&quot;\})', html)

    urunler = []
    seen_ids = set()

    for art_raw in articles + articles2:
        try:
            clean = art_raw.replace('&quot;', '"').replace('&amp;', '&')
            art = json.loads(clean)
            pi = art.get('productInfo', {})
            name = pi.get('productName', '').strip()
            if not name: continue
            pid_path = art.get('id', '')
            # ID'yi path'ten çıkar: .../vast_assortiment/3002728/...
            pid_m = re.search(r'vast_assortiment/(\d+)', pid_path)
            if not pid_m:
                pid_m = re.search(r'snippet-(\d+)', pid_path)
            pid = pid_m.group(1) if pid_m else ''
            if pid in seen_ids: continue
            seen_ids.add(pid)
            price = pi.get('priceWithTax')
            img = None
            if pid:
                img = (f"https://www.aldi.be/content/aldi/belgium/promotions/"
                       f"source-localenhancement/2019/2019-01/2019-01-02/"
                       f"vast_assortiment/{pid}/1/0/jcr:content/assets/img.png")
            urunler.append({
                'isim': name, 'marka': 'MAMIE POULE', 'fiyat': price,
                'unit_fiyat': adet_fiyat(price, name),
                'in_promo': pi.get('inPromotion', False),
                'image': img, 'nutriscore': None, 'market': 'aldi',
            })
        except: pass

    return urunler

# ─── CARREFOUR ────────────────────────────────────────────────────────────────
def parse_carrefour():
    dosya = KLASOR / "Eieren _ Carrefour België.html"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    # dataLayer içindeki ürün listesi
    dl_match = re.search(
        r'const dlDataItems\s*=\s*(\[.*?\])\s*;?\s*\n',
        html, re.DOTALL)
    if not dl_match:
        dl_match = re.search(r'dlDataItems\s*=\s*(\[.+?\])', html, re.DOTALL)

    items = []
    if dl_match:
        try:
            raw = dl_match.group(1)
            raw = re.sub(r'&#x27;', "'", raw)
            raw = re.sub(r'&amp;', '&', raw)
            all_items = json.loads(raw)
            for ev in all_items:
                ec = ev.get('ecommerce', {})
                items.extend(ec.get('items', []))
        except: pass

    # JSON-LD'den de çek (daha fazla bilgi var)
    ld_blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
    ld_products = {}
    for blk in ld_blocks:
        try:
            d = json.loads(blk)
            elems = []
            if d.get('@type') == 'ItemList':
                elems = [i.get('item', {}) for i in d.get('itemListElement', [])]
            elif d.get('@type') == 'Product':
                elems = [d]
            for p in elems:
                name = p.get('name','').strip()
                if not name: continue
                offers = p.get('offers', {})
                if isinstance(offers, list): offers = offers[0] if offers else {}
                try: price = float(offers.get('price', 0)) or None
                except: price = None
                img = p.get('image', '')
                if isinstance(img, list): img = img[0] if img else ''
                brand = p.get('brand', {})
                if isinstance(brand, dict): brand = brand.get('name', '')
                ld_products[name] = {'price': price, 'image': img, 'brand': brand}
        except: pass

    urunler = []
    seen = set()
    for it in items:
        name = it.get('item_name','').strip()
        if not name or name in seen: continue
        seen.add(name)
        try: price = float(it.get('price', 0)) or None
        except: price = None
        brand = it.get('item_brand','')
        item_id = it.get('item_id','')
        img = None
        if name in ld_products:
            img = ld_products[name].get('image')
            if not price: price = ld_products[name].get('price')
            if not brand: brand = ld_products[name].get('brand','')
        if not img and item_id:
            img = (f"https://static.carrefour.be/medias/sys_master/master/{item_id}.jpg")
        urunler.append({
            'isim': name, 'marka': brand, 'fiyat': price,
            'unit_fiyat': adet_fiyat(price, name),
            'in_promo': False, 'image': img, 'nutriscore': None, 'market': 'carrefour',
        })

    # Sadece JSON-LD'dekiler de ekle
    for name, d in ld_products.items():
        if name not in seen:
            seen.add(name)
            urunler.append({
                'isim': name, 'marka': d.get('brand',''), 'fiyat': d.get('price'),
                'unit_fiyat': adet_fiyat(d.get('price'), name),
                'in_promo': False, 'image': d.get('image'), 'nutriscore': None,
                'market': 'carrefour',
            })
    return urunler

# ─── DELHAIZE ─────────────────────────────────────────────────────────────────
def parse_delhaize():
    dosya = KLASOR / "www.delhaize.be.html"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    urunler = []
    # aria-label="Delhaize NAAM" + srcset CDN URL + prijs aria-label
    # Ürün bloklarını yakala
    blocks = re.split(r'(?=<[^>]+data-testid="product-block-image-link")', html)
    for blk in blocks[1:]:
        # isim
        name_m = re.search(r'aria-label="Delhaize ([^"]+)"', blk)
        if not name_m: continue
        name = name_m.group(1).strip()

        # resim - srcset'ten CDN URL
        img_m = re.search(r'srcset="(https://static\.delhaize\.be[^"]+)"', blk)
        img = None
        if img_m:
            # srcset'teki ilk URL (1x versiyonu)
            first = img_m.group(1).split(',')[0].strip().split(' ')[0]
            img = first

        # fiyat - aria-label="Prijs: X euro Y cent"
        price_m = re.search(r'aria-label="Prijs:\s*(\d+)\s*euro\s*(\d+)\s*cent"', blk)
        price = None
        if price_m:
            price = float(price_m.group(1)) + float(price_m.group(2)) / 100

        # unit fiyat - aria-label="Prijs per stuk: X euro Y cent"
        unit_m = re.search(r'Prijs per stuk:\s*(\d+)\s*euro\s*(\d+)\s*cent', blk)
        unit_f = None
        if unit_m:
            unit_f = float(unit_m.group(1)) + float(unit_m.group(2)) / 100
        else:
            unit_f = adet_fiyat(price, name)

        # unit_or_content (6 st vs 12 st)
        cont_m = re.search(r'aria-label="(\d+)\s*st"', blk)
        content = cont_m.group(0) if cont_m else ''

        urunler.append({
            'isim': name, 'marka': 'Delhaize', 'fiyat': price,
            'unit_fiyat': unit_f, 'in_promo': False,
            'image': img, 'nutriscore': None, 'market': 'delhaize',
        })

    return urunler

# ─── LIDL ─────────────────────────────────────────────────────────────────────
def parse_lidl():
    # Önce SingleFile versiyonu dene
    dosya = Path(r"C:\Users\yaman\Downloads\LIDL\Voeding & drank (12_05_2026 03：50：02).html")
    if not dosya.exists():
        dosya = KLASOR / "Ferme Flement Vrije-uitloopeieren M_L _ Lidl.html"

    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    urunler = []
    # JSON-LD Product
    ld_blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
    for blk in ld_blocks:
        try:
            d = json.loads(blk)
            if d.get('@type') != 'Product': continue
            name = d.get('name','').strip()
            if not name or not is_yumurta(name): continue
            offers = d.get('offers', [{}])
            if isinstance(offers, list): offers = offers[0] if offers else {}
            try: price = float(offers.get('price',0)) or None
            except: price = None
            img = d.get('image','')
            if isinstance(img, list): img = img[0] if img else ''
            brand = d.get('brand',{})
            if isinstance(brand, dict): brand = brand.get('name','')
            sku = d.get('sku','')
            # Imgproxy URL'den daha temiz URL yap
            if img and 'imgproxy' in img:
                img = f"https://www.lidl.be/p/nl-BE/{d.get('url','').split('/')[-1].replace('p10','')}/thumbnail"
                img = d.get('image','')
                if isinstance(img, list): img = img[0] if img else ''
            urunler.append({
                'isim': name, 'marka': brand, 'fiyat': price,
                'unit_fiyat': adet_fiyat(price, name),
                'in_promo': False, 'image': img, 'nutriscore': None, 'market': 'lidl',
            })
        except: pass

    # data-gridbox-impression (tırnaksız)
    impressions = re.findall(r'data-gridbox-impression[=\s]+["\']?(%7B[^>\s"\']+%7D)', html)
    for raw in impressions:
        try:
            d = json.loads(unquote(raw))
            name = d.get('name','').strip()
            if not name or not is_yumurta(name): continue
            if any(u['isim'] == name for u in urunler): continue
            price = d.get('price')
            pid = d.get('id','')
            img = None
            if pid:
                img = f"https://imgproxy-retcat.assets.schwarz/product/{pid}.jpg"
            urunler.append({
                'isim': name, 'marka': d.get('brand',''), 'fiyat': price,
                'unit_fiyat': adet_fiyat(price, name),
                'in_promo': False, 'image': img, 'nutriscore': None, 'market': 'lidl',
            })
        except: pass

    return urunler

# ─── ANA ──────────────────────────────────────────────────────────────────────
print("Veriler çekiliyor...\n")

all_data = []
parsers = [
    ('COLRUYT', parse_colruyt),
    ('ALDI',    parse_aldi),
    ('CARREFOUR', parse_carrefour),
    ('DELHAIZE', parse_delhaize),
    ('LIDL',    parse_lidl),
]

for market_name, fn in parsers:
    try:
        items = fn()
        temiz = [u for u in items if is_yumurta(u.get('isim',''))]
        print(f"[{market_name}] {len(temiz)} yumurta ürünü")
        for u in temiz:
            kat = kategori(u['isim'])
            u['kategori'] = kat
            u['unit_fiyat'] = u.get('unit_fiyat') or adet_fiyat(u.get('fiyat'), u['isim'])
            img_ok = '✓' if u.get('image') else '✗'
            print(f"  [{kat[:7]:<7}] {u['isim'][:45]:<45} {u.get('fiyat','?')} EUR  img={img_ok}")
        all_data.extend(temiz)
    except Exception as e:
        print(f"[{market_name}] HATA: {e}")

print(f"\nTOPLAM: {len(all_data)} ürün")

# JSON kaydet
CIKTI_JSON.parent.mkdir(parents=True, exist_ok=True)
with open(CIKTI_JSON, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print(f"JSON kaydedildi: {CIKTI_JSON}")
