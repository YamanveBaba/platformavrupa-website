# -*- coding: utf-8 -*-
"""
D:\MARKET\YUMURTALAR klasöründeki HTML dosyalarından tüm yumurta verilerini eksiksiz çeker.
Her ürün: isim, fiyat, birim fiyat, resim, market, kategori, promosyon bilgisi.
"""
import sys, re, json, os, shutil
from pathlib import Path
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')

KLASOR = Path("D:/MARKET/YUMURTALAR")
IMG_DEST = Path("C:/Users/yaman/Desktop/platformavrupa-website/img/yumurta")
IMG_DEST.mkdir(parents=True, exist_ok=True)

MARKET_SLUG = {
    'colruyt': 'colruyt_be', 'aldi': 'aldi_be',
    'carrefour': 'carrefour_be', 'delhaize': 'delhaize_be', 'lidl': 'lidl_be'
}

# ── Yardımcı fonksiyonlar ──────────────────────────────────────────────────────

DISLAMA = ['chocolade','praline','caramel','paas','pâques','madeleines','lasagne',
           'macaroni','noodle','wafels','spaghetti','tagliatelle','viseieren',
           'foreleieren','zalmeieren','mayonaise','eiervorm','sproeier','advocaat',
           'eierlikeur','kattenvoeding','pannenkoek','granola','tortilla','penne',
           'instant noodle','tortelloni','pasta','rijst','meel','bakpoeder']

def is_yumurta(name):
    n = name.lower()
    return not any(d in n for d in DISLAMA)

def kategori(name):
    n = name.lower()
    if any(k in n for k in ['kwart','kwartel','caille','quail']):
        return 'bildircin'
    if any(k in n for k in ['bio','biologisch','organique','organic']):
        return 'bio'
    if any(k in n for k in ['scharrel','uitloop','vrij','vrije','serbest','plein air',
                              'fermier','free range','gezen','scharreleieren']):
        return 'serbest'
    return 'normal'

def extract_adet(text):
    """İsim veya içerikten yumurta adedini çıkar."""
    t = text.lower()
    # Açık birim: "12 stuks", "6 st.", "10 eieren"
    m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|stuk\b|pièces?|adet)\b', t, re.I)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 60: return n
    # "Bio 12 Verse Eieren" veya "12 Verse Eieren"
    m = re.search(r'\b(\d+)\s+(?:verse|bio|scharrel|vrije|large|medium|extra)', t, re.I)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 60: return n
    # Başlangıçta sayı: "6 Verse Scharreleieren", "30 Scharreleieren"
    m = re.match(r'^(\d+)\s', t.strip())
    if m:
        n = int(m.group(1))
        if 2 <= n <= 60: return n
    # Sonda: "M 12st", "L 6st", "M/L 10st"
    m = re.search(r'[ML/]+\s*(\d+)\s*st\b', t, re.I)
    if m:
        n = int(m.group(1))
        if 2 <= n <= 60: return n
    return None

def kopya_img(src_path, fname):
    """Resmi website img klasörüne kopyalar, relative path döner."""
    src = Path(src_path)
    if not src.exists(): return None
    dst = IMG_DEST / fname
    if not dst.exists():
        shutil.copy2(src, dst)
    return f"img/yumurta/{fname}"

# ── COLRUYT ───────────────────────────────────────────────────────────────────
def parse_colruyt():
    dosya = KLASOR / "Eieren - Zuivel _ Colruyt.html"
    files_dir = KLASOR / "Eieren - Zuivel _ Colruyt_files"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    urunler = []
    for m in re.finditer(r'<a[^>]+card--article[^>]+>', html):
        a = m.group(0)
        isim = (re.search(r'(?:longname|data-tms-product-name)="([^"]+)"', a) or re.search(r"(?:longname|data-tms-product-name)='([^']+)'", a))
        if not isim: continue
        isim = isim.group(1).strip()
        if not is_yumurta(isim): continue

        def get(attr):
            r = re.search(rf'{attr}="([^"]*)"', a)
            return r.group(1) if r else ''

        fiyat_str = get('data-tms-product-price')
        unit_str   = get('data-tms-product-unitprice')
        promo_str  = get('data-tms-product-promotion')
        brand      = get('seobrand')
        nutri      = get('nutriscore')

        try: fiyat = float(fiyat_str) if fiyat_str else None
        except: fiyat = None
        try: unit_fiyat = float(unit_str) if unit_str else None
        except: unit_fiyat = None

        # İndirimli fiyat: promo_str formatı "actie|xtra promo" veya "x,xx"
        promo_fiyat = None
        in_promo = bool(promo_str and promo_str.strip())
        if in_promo:
            pf = re.search(r'(\d+[,.]\d+)', promo_str)
            if pf:
                try: promo_fiyat = float(pf.group(1).replace(',','.'))
                except: pass

        # Resim
        rest = html[m.end():m.end()+2000]
        img_m = re.search(r'src="(\./[^"]+/asset-(\d+)\.jpg)"', rest)
        img_url = None
        if img_m:
            fname = f"asset-{img_m.group(2)}.jpg"
            src = files_dir / fname
            img_url = kopya_img(src, fname)

        adet = extract_adet(isim)
        if not unit_fiyat and fiyat and adet:
            unit_fiyat = round(fiyat / adet, 4)

        urunler.append({
            'chain_slug': 'colruyt_be', 'name': isim, 'name_tr': None,
            'price': fiyat, 'promo_price': promo_fiyat, 'currency': 'EUR',
            'in_promo': in_promo, 'promo_valid_until': None,
            'unit_or_content': str(adet) + ' st' if adet else '',
            'image_url': img_url or '', '_unit_fiyat': unit_fiyat,
            'kategori': kategori(isim), 'brand': brand, 'nutriscore': nutri,
        })
    return urunler

# ── ALDI ──────────────────────────────────────────────────────────────────────
def parse_aldi():
    dosya = KLASOR / "Verse eieren kopen (scharreleieren, bio, etc.) _ ALDI België.html"
    files_dir = KLASOR / "Verse eieren kopen (scharreleieren, bio, etc.) _ ALDI België_files"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    # Ürün kartı pozisyonlarını bul
    positions = list(re.finditer(r'data-article="([^"]+)"', html))

    # srcset -> pid -> img URL
    srcset_map = {}
    for s in re.findall(r'srcset="([^"]+)"', html):
        if 'vast_assortiment' not in s: continue
        first = s.split(',')[0].strip().split(' ')[0]
        pid_m = re.search(r'vast_assortiment/(\d+)/', first)
        if pid_m and 'BILD_INTERNET' in first:
            srcset_map[pid_m.group(1)] = 'https://www.aldi.be' + first

    # Local img files
    local_imgs = {}
    if files_dir.exists():
        for f in files_dir.iterdir():
            if f.suffix in ('.png','.jpg','.webp'):
                local_imgs[f.name] = f

    urunler = []
    seen = set()

    for m in positions:
        raw = m.group(1).replace('&quot;','"')
        try:
            art = json.loads(raw)
        except: continue

        pi = art.get('productInfo', {})
        isim = pi.get('productName', '').strip()
        if not isim or not is_yumurta(isim): continue
        price_tmp = pi.get('priceWithTax')
        key = f"{isim}_{price_tmp}"
        if key in seen: continue
        seen.add(key)

        price = pi.get('priceWithTax')
        in_promo = pi.get('inPromotion', False)

        # Adet: HTML'deki sonraki 3000 karaktere bak
        rest = html[m.end():m.end()+3000]
        adet_m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|stuk\b)', rest, re.I)
        adet = int(adet_m.group(1)) if adet_m else None
        unit_fiyat = round(price/adet, 4) if (price and adet) else None

        # Resim
        pid_path = art.get('id','')
        pid_m = re.search(r'vast_assortiment/(\d+)|snippet-(\d+)', pid_path)
        pid = (pid_m.group(1) or pid_m.group(2)) if pid_m else ''
        img_url = srcset_map.get(pid) if pid else None

        urunler.append({
            'chain_slug': 'aldi_be', 'name': isim, 'name_tr': None,
            'price': price, 'promo_price': None, 'currency': 'EUR',
            'in_promo': in_promo, 'promo_valid_until': None,
            'unit_or_content': str(adet) + ' st' if adet else '',
            'image_url': img_url or '', '_unit_fiyat': unit_fiyat,
            'kategori': kategori(isim), 'brand': 'MAMIE POULE', 'nutriscore': None,
        })
    return urunler

# ── CARREFOUR ─────────────────────────────────────────────────────────────────
def parse_carrefour():
    dosya = KLASOR / "Eieren _ Carrefour België.html"
    files_dir = KLASOR / "Eieren _ Carrefour België_files"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    # Local img -> item_id map
    img_id_map = {}
    if files_dir.exists():
        for f in files_dir.iterdir():
            if f.suffix in ('.webp','.jpg','.png'):
                mid = re.search(r'420_(\d+)', f.name)
                if mid:
                    img_id_map[mid.group(1).lstrip('0')] = f

    # dataLayer
    dl = re.search(r'const dlDataItems\s*=\s*(\[.*?\])\s*;', html, re.DOTALL)
    items_raw = []
    if dl:
        try:
            evs = json.loads(re.sub(r'&#x27;', "'", dl.group(1)))
            for ev in evs:
                items_raw.extend(ev.get('ecommerce',{}).get('items',[]))
        except: pass

    # JSON-LD'den img + description
    ld_info = {}
    for blk in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            d = json.loads(blk)
            prods = []
            if d.get('@type') == 'ItemList':
                prods = [i.get('item',{}) for i in d.get('itemListElement',[])]
            elif d.get('@type') == 'Product':
                prods = [d]
            for p in prods:
                name = p.get('name','').strip()
                if not name: continue
                offers = p.get('offers', {})
                if isinstance(offers, list): offers = offers[0] if offers else {}
                img = p.get('image','')
                if isinstance(img, list): img = img[0] if img else ''
                ld_info[name] = {'img_cdn': img, 'price': offers.get('price')}
        except: pass

    urunler = []
    seen = set()

    for it in items_raw:
        isim = it.get('item_name','').strip()
        if not isim or not is_yumurta(isim): continue
        if isim in seen: continue
        seen.add(isim)

        fiyat = it.get('price')
        iid = it.get('item_id','').lstrip('0')
        in_promo = bool(it.get('discount') or it.get('in_promo'))
        brand = it.get('item_brand','')

        # Resim: önce local _files, yoksa CDN
        img_url = None
        if iid in img_id_map:
            fname = img_id_map[iid].name
            img_url = kopya_img(img_id_map[iid], fname)
        if not img_url and isim in ld_info:
            img_url = ld_info[isim].get('img_cdn')

        adet = extract_adet(isim)
        unit_fiyat = round(fiyat/adet, 4) if (fiyat and adet) else None

        urunler.append({
            'chain_slug': 'carrefour_be', 'name': isim, 'name_tr': None,
            'price': fiyat, 'promo_price': None, 'currency': 'EUR',
            'in_promo': in_promo, 'promo_valid_until': None,
            'unit_or_content': str(adet) + ' st' if adet else '',
            'image_url': img_url or '', '_unit_fiyat': unit_fiyat,
            'kategori': kategori(isim), 'brand': brand, 'nutriscore': None,
        })

    # JSON-LD'den eksik kalanları ekle
    for name, d in ld_info.items():
        if name not in seen and is_yumurta(name):
            seen.add(name)
            fiyat = d.get('price')
            adet = extract_adet(name)
            unit_fiyat = round(float(fiyat)/adet, 4) if (fiyat and adet) else None
            img_url = kopya_img(None, '') if False else d.get('img_cdn')
            urunler.append({
                'chain_slug': 'carrefour_be', 'name': name, 'name_tr': None,
                'price': fiyat, 'promo_price': None, 'currency': 'EUR',
                'in_promo': False, 'promo_valid_until': None,
                'unit_or_content': str(adet) + ' st' if adet else '',
                'image_url': img_url or '', '_unit_fiyat': unit_fiyat,
                'kategori': kategori(name), 'brand': '', 'nutriscore': None,
            })
    return urunler

# ── DELHAIZE ──────────────────────────────────────────────────────────────────
def parse_delhaize():
    # Dutch versiyonu
    dosya = KLASOR / "www.delhaize.be.html"
    files_dir = KLASOR / "www.delhaize.be_files"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    urunler = []
    blocks = re.split(r'(?=<[^>]+data-testid="product-block-image-link")', html)

    for blk in blocks[1:]:
        # Hem "Delhaize X" hem "Columbus X" hem "Ferme bois du roi X" vb.
        name_m = re.search(r'aria-label="([^"]{10,120})"', blk)
        if not name_m: continue
        isim = name_m.group(1).strip()
        # UI eleman isimlerini atla
        if any(x in isim for x in ['boodschappenlijst','Informatie','Voeg','tooltip','aria']): continue
        # "Delhaize " prefix'ini temizle
        isim = re.sub(r'^Delhaize\s+', '', isim)
        if not is_yumurta(isim): continue

        # Resim
        img_m = re.search(r'src="(\./www\.delhaize\.be_files/(\d+\.jpg))"', blk)
        img_url = None
        if img_m and files_dir.exists():
            fname = img_m.group(2)
            img_url = kopya_img(files_dir / fname, fname)

        # Fiyatlar
        price_m = re.search(r'aria-label="Prijs:\s*(\d+)\s*euro\s*(\d+)\s*cent"', blk)
        fiyat = (float(price_m.group(1)) + float(price_m.group(2))/100) if price_m else None

        unit_m = re.search(r'Prijs per stuk:\s*(\d+)\s*euro\s*(\d+)\s*cent', blk)
        unit_fiyat = (float(unit_m.group(1)) + float(unit_m.group(2))/100) if unit_m else None

        # Promo: "Prijs voor leden" veya oud fiyat
        promo_m = re.search(r'(?:was|promo|actie|reduction|korting)', blk, re.I)
        in_promo = bool(promo_m)
        promo_fiyat = None

        # Nutriscore
        nutri_m = re.search(r'Nutri-Score:\s*([A-E])', blk)
        nutri = nutri_m.group(1) if nutri_m else None

        adet = extract_adet(isim)
        # Bazı Delhaize ürünleri lazy-load ile geldiğinden HTML'de adet yok — bilinen değerler:
        DELHAIZE_ADET_OVERRIDE = {
            'Eieren | Verschillende grootte | Bio': 12,
            'Eieren | Bruin | Groot': 12,
            'Columbus Eieren | Omega-3 | Bio': 6,
        }
        if not adet and isim in DELHAIZE_ADET_OVERRIDE:
            adet = DELHAIZE_ADET_OVERRIDE[isim]
        if not unit_fiyat and fiyat and adet:
            unit_fiyat = round(fiyat / adet, 4)

        urunler.append({
            'chain_slug': 'delhaize_be', 'name': isim, 'name_tr': None,
            'price': fiyat, 'promo_price': promo_fiyat, 'currency': 'EUR',
            'in_promo': in_promo, 'promo_valid_until': None,
            'unit_or_content': str(adet) + ' st' if adet else '',
            'image_url': img_url or '', '_unit_fiyat': unit_fiyat,
            'kategori': kategori(isim), 'brand': 'Delhaize', 'nutriscore': nutri,
        })
    return urunler

# ── LIDL ──────────────────────────────────────────────────────────────────────
def parse_lidl():
    dosya = KLASOR / "Ferme Flement Vrije-uitloopeieren M_L _ Lidl.html"
    files_dir = KLASOR / "Ferme Flement Vrije-uitloopeieren M_L _ Lidl_files"
    with open(dosya, encoding='utf-8', errors='ignore') as f:
        html = f.read()

    urunler = []
    for blk in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            d = json.loads(blk)
            if d.get('@type') != 'Product': continue
            isim = d.get('name','').strip()
            if not isim or not is_yumurta(isim): continue
            offers = d.get('offers', [{}])
            if isinstance(offers, list): offers = offers[0] if offers else {}
            fiyat = float(offers.get('price',0)) or None
            img_cdn = d.get('image','')
            if isinstance(img_cdn, list): img_cdn = img_cdn[0] if img_cdn else ''
            brand = d.get('brand', {})
            if isinstance(brand, dict): brand = brand.get('name','')

            # Resim: local .webp dosyası
            img_url = img_cdn
            if files_dir.exists():
                webp_files = list(files_dir.glob('F3E53A*.webp'))
                if webp_files:
                    fname = webp_files[0].name
                    img_url = kopya_img(webp_files[0], 'lidl_vrije_uitloop.webp')

            adet = extract_adet(isim)
            # Lidl sayfasında adet bilgisi ara
            if not adet:
                for pat in [r'(\d+)\s*stuks', r'(\d+)\s*eieren', r'Inhoud.*?(\d+)', r'per\s+(\d+)']:
                    rm = re.search(pat, html, re.I)
                    if rm:
                        n = int(rm.group(1))
                        if 2 <= n <= 30: adet = n; break
            unit_fiyat = round(fiyat/adet, 4) if (fiyat and adet) else None

            urunler.append({
                'chain_slug': 'lidl_be', 'name': isim, 'name_tr': None,
                'price': fiyat, 'promo_price': None, 'currency': 'EUR',
                'in_promo': False, 'promo_valid_until': None,
                'unit_or_content': str(adet) + ' st' if adet else '',
                'image_url': img_url or '', '_unit_fiyat': unit_fiyat,
                'kategori': kategori(isim), 'brand': brand, 'nutriscore': None,
            })
        except: pass
    return urunler

# ── ANA ───────────────────────────────────────────────────────────────────────
print("Tüm veriler çekiliyor...\n")

all_data = []
parsers = [('COLRUYT',parse_colruyt),('ALDI',parse_aldi),
           ('CARREFOUR',parse_carrefour),('DELHAIZE',parse_delhaize),('LIDL',parse_lidl)]

for market_name, fn in parsers:
    try:
        items = fn()
        print(f"[{market_name}] {len(items)} ürün")
        for u in items:
            unit_ok = '✓' if u['_unit_fiyat'] else '✗'
            img_ok  = '✓' if u['image_url']   else '✗'
            print(f"  [{u['kategori'][:7]:<7}] {u['name'][:42]:<42} {str(u['price']):<6} | unit{unit_ok} {str(u['_unit_fiyat'])[:6] if u['_unit_fiyat'] else '     '} | img{img_ok}")
        all_data.extend(items)
    except Exception as e:
        import traceback
        print(f"[{market_name}] HATA: {e}")
        traceback.print_exc()

print(f"\nTOPLAM: {len(all_data)} ürün")
print(f"Resimli: {sum(1 for u in all_data if u['image_url'])}")
print(f"Birim fiyatlı: {sum(1 for u in all_data if u['_unit_fiyat'])}")

# Web formatına çevir ve kaydet
out = []
for u in all_data:
    out.append({k: v for k, v in u.items()})

json_str = json.dumps(out, ensure_ascii=False, separators=(',',':'))
# market.html'e göm
market_html_path = Path("C:/Users/yaman/Desktop/platformavrupa-website/market.html")
with open(market_html_path, encoding='utf-8') as f:
    mhtml = f.read()

# Eski YUMURTA_DATA'yı sil
mhtml = re.sub(r'<script>const YUMURTA_DATA=\[.*?\];</script>\n?', '', mhtml, flags=re.DOTALL)
# Yenisini ekle
mhtml = mhtml.replace('</body>', f'<script>const YUMURTA_DATA={json_str};</script>\n</body>')

with open(market_html_path, 'w', encoding='utf-8') as f:
    f.write(mhtml)

print(f"\nmarket.html güncellendi.")
print(f"img/yumurta klasöründe: {len(list(IMG_DEST.iterdir()))} resim")
