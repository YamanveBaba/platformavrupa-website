# -*- coding: utf-8 -*-
"""
D:\MARKET\YUMURTALAR klasöründeki HTML dosyalarını parse eder.
Her marketten ürün adı, fiyat, adet fiyatı, resim URL'si çeker.
"""
import sys, re, json, os
from pathlib import Path
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')

KLASOR = Path("D:/MARKET/YUMURTALAR")

# ── Kategori belirleme ────────────────────────────────────────────
def kategori(name):
    n = name.lower()
    if any(k in n for k in ['kwart','bıldırcın','quail','caille']):
        return '🐦 Bıldırcın'
    if any(k in n for k in ['bio','biolog','organik','organic','organique']):
        return '🌿 Bio'
    if any(k in n for k in ['scharrel','uitloop','vrij','serbest','plein air',
                              'fermier','gezen','free','scharreleieren']):
        return '🐔 Serbest Gezen'
    if any(k in n for k in ['hardgekookt','hard gekookt','haşlanmış',
                              'gekleurd','pic nic','cuit']):
        return '⚡ Haşlanmış'
    if any(k in n for k in ['omega','verrijkt']):
        return '💊 Omega/Özel'
    return '🥚 Normal'

def adet_fiyat(fiyat, name, content=''):
    if not fiyat or fiyat <= 0:
        return None
    metin = ((content or '') + ' ' + name).lower()
    m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|pièces?|adet|eieren\b|oeufs?\b|parça)', metin, re.I)
    if m:
        adet = int(m.group(1))
        if 3 <= adet <= 60:
            return round(fiyat / adet, 4)
    return None

# ── COLRUYT parser ────────────────────────────────────────────────
def parse_colruyt(html, dosya_adi):
    """Colruyt: data-tms-* attribute'larından çeker"""
    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.urunler = []
            self._card = None
            self._img = None

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            cls = a.get('class', '')

            if tag == 'a' and 'card--article' in cls:
                isim = (a.get('longname') or a.get('data-tms-product-name') or '').strip()
                if not isim:
                    return
                try: fiyat = float(a.get('data-tms-product-price', '') or 0) or None
                except: fiyat = None
                try: unit_f = float(a.get('data-tms-product-unitprice', '') or 0) or None
                except: unit_f = None
                retail = a.get('retailproductnumber', '')
                promo = a.get('data-tms-product-promotion', '')
                ean = a.get('gtin', '').split(',')[0]
                ecoscore = a.get('ecoscorevalue', '')
                nutri = a.get('nutriscore', '')

                # Resim URL'sini yeniden kur (Colruyt CDN pattern)
                img_url = None
                if retail:
                    img_url = (f"https://ecustomermwstatic.colruytgroup.com/"
                               f"ecustomermwstatic/nl/assets/asset-{retail}.jpg")

                self._card = {
                    'isim': isim,
                    'fiyat': fiyat,
                    'unit_fiyat': unit_f,
                    'in_promo': bool(promo),
                    'ean': ean,
                    'retail_num': retail,
                    'ecoscore': ecoscore,
                    'nutriscore': nutri,
                    'image': img_url,
                    'market': 'colruyt_be',
                }

            # Kart içindeki resmi de bul (daha doğru URL için)
            if tag == 'img' and self._card:
                src = a.get('src', '')
                if src and ('asset' in src or 'product' in src.lower()):
                    # Local path'ten asset ID çıkar
                    m = re.search(r'asset-(\d+)', src)
                    if m:
                        self._card['image'] = (
                            f"https://ecustomermwstatic.colruytgroup.com/"
                            f"ecustomermwstatic/nl/assets/asset-{m.group(1)}.jpg"
                        )

        def handle_endtag(self, tag):
            if tag == 'a' and self._card:
                self.urunler.append(self._card)
                self._card = None

    p = P()
    p.feed(html)
    return p.urunler


# ── ALDI parser ───────────────────────────────────────────────────
def parse_aldi(html, dosya_adi):
    """ALDI: data-article JSON attribute kullanır"""
    import html as html_lib
    urunler = []

    # data-article attribute'larını bul
    tile_pattern = re.compile(
        r'data-article="({[^"]+})".*?<img[^>]+(?:src|data-src)="([^"]+)"',
        re.DOTALL
    )
    tiles_raw = re.findall(r'data-article="([^"]+)"', html)

    for raw in tiles_raw:
        try:
            decoded = html_lib.unescape(raw)
            data = json.loads(decoded)
            info = data.get('productInfo', {})
            isim = info.get('productName', '').strip()
            if not isim:
                continue
            fiyat = info.get('priceWithTax') or info.get('price')
            try: fiyat = float(fiyat) if fiyat else None
            except: fiyat = None
            marka = info.get('brand', '')
            in_promo = bool(info.get('inPromotion', False))
            prod_id = info.get('productID', '')
            urunler.append({
                'isim': isim,
                'marka': marka,
                'fiyat': fiyat,
                'unit_fiyat': None,
                'in_promo': in_promo,
                'prod_id': prod_id,
                'image': None,  # Sonra eşleştir
                'market': 'aldi_be',
            })
        except:
            pass

    # srcset'ten gerçek resim URL'lerini al (lazy-load bypass)
    # Her tile'ın img srcset'inden ilk URL'yi çek
    tile_img_pattern = re.compile(
        r'data-article="[^"]*"[^>]*>.*?<img[^>]+srcset="([^"]+)"',
        re.DOTALL
    )
    tile_imgs = tile_img_pattern.findall(html)

    ALDI_BASE = "https://www.aldi.be"
    for i, u in enumerate(urunler):
        if i < len(tile_imgs):
            srcset = tile_imgs[i]
            # İlk URL'yi al (288w versiyonu)
            first = srcset.strip().split(',')[0].strip().split(' ')[0]
            if first:
                img_url = (ALDI_BASE + first) if first.startswith('/') else first
                u['image'] = img_url

    return urunler


# ── CARREFOUR parser ──────────────────────────────────────────────
def parse_carrefour(html, dosya_adi):
    """Carrefour: dataLayer view_item_list event"""
    import html as html_lib
    urunler = []

    # dataLayer içindeki view_item_list items'ı çek
    dl_matches = re.findall(
        r'const dlDataItems\s*=\s*(\[.*?\])\s*;',
        html, re.DOTALL
    )
    if not dl_matches:
        dl_matches = re.findall(
            r'"view_item_list".*?"items"\s*:\s*(\[.*?\])\s*[,}]',
            html, re.DOTALL
        )

    for raw in dl_matches:
        try:
            data = json.loads(html_lib.unescape(raw))
            for event in (data if isinstance(data, list) else [data]):
                items = []
                if isinstance(event, dict):
                    items = (event.get('ecommerce', {}).get('items', []) or
                             event.get('items', []))
                for p in items:
                    isim = p.get('item_name', '').strip()
                    if not isim:
                        continue
                    try: fiyat = float(p.get('price', 0)) or None
                    except: fiyat = None
                    marka = p.get('item_brand', '')
                    item_id = p.get('item_id', '')
                    unit_f = adet_fiyat(fiyat, isim)
                    urunler.append({
                        'isim': isim,
                        'marka': marka,
                        'fiyat': fiyat,
                        'unit_fiyat': unit_f,
                        'in_promo': False,
                        'item_id': item_id,
                        'image': None,  # Sonra eşleştir
                        'market': 'carrefour_be',
                    })
        except:
            pass

    # Resim URL'lerini bul ve eşleştir (product ID'ye göre)
    img_matches = re.findall(
        r'href="/[^"]*?/p/([^"]+)"[^>]*>.*?<img[^>]+srcset="([^"]+)"',
        html, re.DOTALL
    )
    img_map = {}
    for prod_id, srcset in img_matches:
        first_url = srcset.split(',')[0].strip().split(' ')[0]
        if first_url.startswith('http'):
            img_map[prod_id] = first_url

    for u in urunler:
        item_id = u.get('item_id', '')
        car_files = KLASOR / "Eieren _ Carrefour België_files"
        if item_id in img_map:
            u['image'] = img_map[item_id]
        elif item_id:
            # Pattern 1: 420_{item_id}_T1.webp
            p1 = car_files / f"420_{item_id}_T1.webp"
            if p1.exists():
                u['image'] = str(p1)
            else:
                # Pattern 2: 420_{item_id}_M1_*.webp (glob)
                matches = list(car_files.glob(f"420_{item_id}_M1_*.webp"))
                if matches:
                    u['image'] = str(matches[0])
                else:
                    # CDN URL dene
                    u['image'] = f"https://www.carrefour.be/medias/420_{item_id}_T1.webp"

    return urunler


# ── DELHAIZE parser ───────────────────────────────────────────────
def parse_delhaize(html, dosya_adi):
    """Delhaize: aria-label pattern + srcset resim URL"""
    urunler = []

    # Ürün ismi: aria-label="Delhaize XXXX" link'lerinden
    # Fiyat: aria-label="Prijs: X euro Y cent"
    # Birim fiyat: aria-label="Prijs per stuk: X euro Y cent per st"
    # Resim: srcset="https://static.delhaize.be/..."

    # Tüm product block'larını bul
    # Her block: ürün linki + resim + fiyat bilgisi
    blocks = re.findall(
        r'aria-label="Delhaize ([^"]+)"[^>]*href="([^"]+)"[^>]*>.*?'
        r'srcset="(https://static\.delhaize\.be[^"]+?(?:jpg|png|webp))',
        html, re.DOTALL
    )

    # Fiyatları ayrı topla
    prices = re.findall(
        r'aria-label="Prijs:\s*(\d+)\s*euro\s*(\d+)\s*cent"',
        html
    )
    unit_prices = re.findall(
        r'aria-label="Prijs per stuk:\s*(\d+)\s*euro\s*(\d+)\s*cent\s*per\s*(\w+)"',
        html
    )

    # Nutri-score
    nutri_scores = re.findall(r'alt="Nutri-Score:\s*([A-E][+]?)"', html)

    for i, (isim, href, img_srcset) in enumerate(blocks):
        isim = isim.strip()
        # Resim URL'sinin ilkini al ve temizle
        img_url = img_srcset.split('?')[0] if '?' in img_srcset else img_srcset
        img_url = img_url.replace('&amp;', '&').split(' ')[0]
        # Local dosya adını çıkar (CDN URL'sinin son kısmı)
        local_fname = img_url.split('/')[-1].split('.')[0] + '.jpg'
        local_path = KLASOR / "www.delhaize.be_files" / local_fname
        if local_path.exists():
            img_url = str(local_path)  # Local resim dosyası

        # Fiyatı al
        fiyat = None
        if i < len(prices):
            euro, cent = prices[i]
            fiyat = float(euro) + float(cent) / 100

        # Birim fiyatı
        unit_f = None
        if i < len(unit_prices):
            euro, cent, birim = unit_prices[i]
            unit_f = float(euro) + float(cent) / 100

        # Nutri
        nutri = nutri_scores[i] if i < len(nutri_scores) else ''

        urunler.append({
            'isim': isim,
            'fiyat': fiyat,
            'unit_fiyat': unit_f,
            'in_promo': False,
            'image': img_url,
            'nutriscore': nutri,
            'url': href,
            'market': 'delhaize_be',
        })

    return urunler


# ── LIDL parser ───────────────────────────────────────────────────
LIDL_YUMURTA_KW = [
    'eieren', 'uitloop', 'scharrel', 'kwartel',
    'bio ei', 'bio-ei', 'verse ei', 'vers ei',
]

def parse_lidl(html, dosya_adi):
    """Lidl: URL-encoded JSON data attributes + JSON-LD"""
    from urllib.parse import unquote
    urunler = []
    seen = set()

    # 1. URL-encoded JSON blokları — Lidl geniş kategori sayfası
    # Format: %7B%22brand%22%3A%22X%22...%22name%22%3A%22Y%22...%22price%22%3AZ...%7D
    encoded_blobs = re.findall(r'%7B%22(?:brand|name|id)%22[^"\'>\s]{50,}%7D', html)
    for blob in encoded_blobs:
        try:
            decoded = unquote(blob)
            data = json.loads(decoded)
            isim = data.get('name', '').strip()
            if not isim or isim in seen:
                continue
            # Sadece yumurta ilgilisi
            n = isim.lower()
            if not any(kw in n for kw in LIDL_YUMURTA_KW):
                continue
            seen.add(isim)
            try: fiyat = float(data.get('price', 0)) or None
            except: fiyat = None
            marka = data.get('brand', '')
            prod_id = str(data.get('id', ''))
            unit_f = adet_fiyat(fiyat, isim)
            urunler.append({
                'isim': isim, 'marka': marka,
                'fiyat': fiyat, 'unit_fiyat': unit_f,
                'in_promo': False, 'image': None,
                'prod_id': prod_id,
                'market': 'lidl_be',
            })
        except:
            pass

    # 2. JSON-LD (ürün sayfası için)
    ld_blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                            html, re.DOTALL | re.IGNORECASE)
    for ld in ld_blocks:
        try:
            data = json.loads(ld)
            items = []
            if isinstance(data, dict):
                t = data.get('@type', '')
                if t == 'ItemList':
                    items = [i.get('item', {}) for i in data.get('itemListElement', [])]
                elif t == 'Product':
                    items = [data]
            for p in items:
                isim = p.get('name', '').strip()
                if not isim or isim in seen:
                    continue
                n = isim.lower()
                if not any(kw in n for kw in LIDL_YUMURTA_KW):
                    continue
                seen.add(isim)
                offers = p.get('offers', {})
                if isinstance(offers, list): offers = offers[0] if offers else {}
                try: fiyat = float(offers.get('price', 0)) or None
                except: fiyat = None
                img = p.get('image', '')
                if isinstance(img, list): img = img[0] if img else ''
                unit_f = adet_fiyat(fiyat, isim, p.get('description', ''))
                urunler.append({
                    'isim': isim, 'fiyat': fiyat, 'unit_fiyat': unit_f,
                    'in_promo': False, 'image': img, 'market': 'lidl_be'
                })
        except:
            pass

    # 3. Resim eşleştirme — Lidl _files klasöründen
    dosya_adi_clean = dosya_adi.replace('.html', '')
    lidl_files = KLASOR / f"{dosya_adi_clean}_files"
    if lidl_files.exists():
        imgs = sorted(lidl_files.glob("*.jpg")) + sorted(lidl_files.glob("*.webp"))
        # prod_id ile eşleştirmeye çalış
        img_map = {f.stem: str(f) for f in imgs}
        for u in urunler:
            pid = u.get('prod_id', '')
            if pid and pid in img_map:
                u['image'] = img_map[pid]

    return urunler


# ── Dışlama filtresi ──────────────────────────────────────────────
DISLAMA = [
    'chocolade','praline','fondant','croquant','caramel','vulling',
    'paas','pâques','dragee','eitjes zakje',
    'madeleines','lasagne','macaroni','noodle','noedels',
    'wafels','wafeltjes','spaghetti','tagliatelle',
    'viseieren','lompviseieren','foreleieren','zalmeieren',
    'mayonaise','mayo','eierwafels','eierkoeken','eiervorm',
    'sproeier','kraan','badkamer','tapijt','parkside','silvercrest',
    'advocaat','eierlikeur','eikenblad','eiwitconcentraat',
    'libeert','original | eieren | wit','kattenvoeding',
]

def is_yumurta(isim):
    n = isim.lower()
    return not any(d in n for d in DISLAMA)


# ── Dosya → parser eşleşmesi ─────────────────────────────────────
DOSYA_PARSER = {
    'colruyt': parse_colruyt,
    'carrefour': parse_carrefour,
    'aldi': parse_aldi,
    'delhaize': parse_delhaize,
    'lidl': parse_lidl,
}

MARKET_ADI = {
    'colruyt_be': 'COLRUYT',
    'aldi_be': 'ALDI',
    'delhaize_be': 'DELHAIZE',
    'lidl_be': 'LIDL',
    'carrefour_be': 'CARREFOUR',
}

def market_tespiti(dosya_adi):
    adi = dosya_adi.lower()
    for m in DOSYA_PARSER:
        if m in adi:
            return m
    return None


# ── Ana ───────────────────────────────────────────────────────────
print(f"Klasör: {KLASOR}\n")

html_dosyalar = list(KLASOR.glob("*.html"))
print(f"{len(html_dosyalar)} HTML dosyası bulundu:\n")
for f in html_dosyalar:
    print(f"  {f.name}")

print()

# Sadece Dutch versiyonlarını kullan (daha güvenilir isimler için)
# Turkish versiyonları çeviriden bozulmuş olabilir
TERCIH_SIRASI = {
    'colruyt': 'Eieren - Zuivel _ Colruyt.html',
    'aldi': 'Verse eieren kopen (scharreleieren, bio, etc.) _ ALDI België.html',
    'carrefour': 'Eieren _ Carrefour België.html',
    'delhaize': 'www.delhaize.be.html',
    'lidl': 'Voeding & drank.html',  # Geniş kategori — yumurtaları filtreler
}

tum_urunler = []

for market, dosya_adi in TERCIH_SIRASI.items():
    dosya = KLASOR / dosya_adi
    if not dosya.exists():
        # Alternatif ara
        alts = [f for f in html_dosyalar if market in f.name.lower()]
        if not alts:
            print(f"  [{market.upper()}] Dosya bulunamadı: {dosya_adi}")
            continue
        dosya = alts[0]

    print(f"\n{'='*65}")
    print(f"  {market.upper()} — {dosya.name}")
    print(f"{'='*65}")

    try:
        with open(dosya, encoding='utf-8', errors='ignore') as f:
            html = f.read()
    except:
        print(f"  Dosya açılamadı.")
        continue

    parser_fn = DOSYA_PARSER[market]
    urunler = parser_fn(html, dosya.name)
    print(f"  Ham parse: {len(urunler)} ürün")

    # Filtrele
    temiz = [u for u in urunler if is_yumurta(u.get('isim', ''))]
    print(f"  Filtrelenmiş: {len(temiz)} yumurta ürünü")

    if not temiz:
        print("  Ürün bulunamadı — farklı HTML yapısı olabilir.")
        continue

    # Kategorize
    gruplari = {}
    for u in temiz:
        kat = kategori(u.get('isim', ''))
        gruplari.setdefault(kat, []).append(u)

    for kat in ['🌿 Bio', '🐔 Serbest Gezen', '🥚 Normal', '🐦 Bıldırcın', '⚡ Haşlanmış', '💊 Omega/Özel']:
        if kat not in gruplari: continue
        print(f"\n  [{kat}]")
        for u in sorted(gruplari[kat], key=lambda x: x.get('fiyat') or 999):
            isim = u['isim'][:55]
            fiyat = u.get('fiyat')
            unit_f = u.get('unit_fiyat') or adet_fiyat(fiyat, u['isim'])
            img = '✓' if u.get('image') else '✗'
            marka = u.get('marka', '')

            f_str = f"{fiyat:.2f} EUR" if fiyat else "Fiyat yok"
            u_str = f" | {unit_f:.3f} €/adet".replace('.', ',') if unit_f else ""
            m_str = f" [{marka}]" if marka else ""

            print(f"    • {isim}{m_str}")
            print(f"      {f_str}{u_str} | Resim:{img}")

    tum_urunler.extend(temiz)

print(f"\n\n{'='*65}")
print(f"TOPLAM: {len(tum_urunler)} ürün, 5 market")
print(f"{'='*65}")
