# -*- coding: utf-8 -*-
"""
Scrapling ile Colruyt ürün çekici.
Antibot bypass + "Meer bekijken" tıklama + tüm veri.

Kullanım:
    python colruyt_scrapling_cek.py --kat kaas          # sadece kaas
    python colruyt_scrapling_cek.py --kat zuivel        # tüm zuivel
    python colruyt_scrapling_cek.py --kat kaas --test   # 1 kategori test
"""

import sys, re, json, os, time, random, argparse
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

CIKTI_DIR = Path(__file__).parent / 'cikti'
CIKTI_DIR.mkdir(exist_ok=True)
CHECKPOINT = CIKTI_DIR / 'colruyt_scrapling_checkpoint.json'
CDN_BASE   = 'https://static.colruytgroup.com'

# ── Log ───────────────────────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── Checkpoint ────────────────────────────────────────────────────────────────
def cp_yukle():
    if CHECKPOINT.exists():
        try:
            with open(CHECKPOINT, encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {'tamamlanan': [], 'urunler': {}}

def cp_kaydet(state):
    with open(CHECKPOINT, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

# ── page_action: scroll + Meer bekijken ──────────────────────────────────────
def meer_bekijken_action(page):
    """Sayfadaki 'Meer bekijken' butonuna tıklayarak tüm ürünleri yükler."""
    import time as t

    # İlk kartların yüklenmesini bekle
    try:
        page.wait_for_selector('a.card--article', timeout=15000)
    except Exception:
        return

    t.sleep(2)

    # Cookie popup'ı kapat (engellemesin)
    for cookie_sel in [
        'button:has-text("Alle cookies weigeren")',
        'button:has-text("Alle cookies aanvaarden")',
        '[data-testid="cookie-reject"]',
        '.cookie-consent button',
        '#onetrust-reject-all-handler',
        '#onetrust-accept-btn-handler',
    ]:
        try:
            btn_c = page.query_selector(cookie_sel)
            if btn_c and btn_c.is_visible():
                btn_c.click()
                t.sleep(1)
                log("  Cookie popup kapatıldı")
                break
        except: pass

    start_time = t.time()
    MAX_SURE = 120  # max 2 dakika

    # Tüm ürünler yüklenene kadar scroll + button tıkla
    tikla = 0
    degismedi = 0
    for _ in range(80):
        if t.time() - start_time > MAX_SURE:
            break  # Zaman aşımı
        onceki = len(page.query_selector_all('a.card--article'))

        # Sayfanın altına scroll et (lazy load + butonu görünür yap)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        t.sleep(1.5)

        # "Meer bekijken" butonunu bul
        btn = None
        for sel in ['.load-more__btn', 'button.btn--primary.load-more__btn',
                    'a.load-more__btn', '[class*="load-more__btn"]']:
            try:
                b = page.query_selector(sel)
                if b and b.is_visible():
                    btn = b
                    break
            except: pass

        if not btn:
            degismedi += 1
            if degismedi >= 3:
                break
            t.sleep(1)
            continue

        try:
            btn.scroll_into_view_if_needed()
            t.sleep(random.uniform(0.6, 1.3))
            btn.click()
            t.sleep(random.uniform(2.0, 3.0))
            tikla += 1
            degismedi = 0

            yeni = len(page.query_selector_all('a.card--article'))
            if yeni > onceki:
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                t.sleep(0.8)
        except Exception as e:
            degismedi += 1

    # Son scroll: tüm resimleri yükle
    for _ in range(3):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        t.sleep(1)
        page.evaluate('window.scrollTo(0, 0)')
        t.sleep(0.5)

    final = len(page.query_selector_all('a.card--article'))
    log(f"  Meer bekijken: {tikla} tıklama → {final} kart")

    # Tüm kartları JavaScript ile çek ve temp dosyaya yaz
    try:
        data = page.evaluate("""
        () => {
            const cards = [...document.querySelectorAll('a.card--article')];
            return cards.map(c => {
                const get = k => c.getAttribute(k) || null;
                const img = c.querySelector('img');
                let imgUrl = null;
                if (img) {
                    const cs = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                    if (cs && !cs.startsWith('data:')) imgUrl = cs;
                }
                return {
                    name:       get('longname') || get('data-tms-product-name'),
                    price:      get('data-tms-product-price'),
                    unit_price: get('data-tms-product-unitprice'),
                    promo:      get('data-tms-product-promotion'),
                    promo_from: get('promoPublicationStart'),
                    promo_to:   get('promoPublicationEnd'),
                    multi_buy:  get('data-tms-product-discounts-name'),
                    retail_num: get('retailproductnumber'),
                    brand:      get('seobrand'),
                    nutri:      get('nutriscore'),
                    top_cat:    get('topCategoryName'),
                    content:    get('data-content'),
                    image_url:  imgUrl,
                };
            }).filter(u => u.name);
        }
        """)
        import json as _json, tempfile as _tf, os as _os
        tmp = _os.path.join(_tf.gettempdir(), '_colruyt_cards.json')
        with open(tmp, 'w', encoding='utf-8') as f:
            _json.dump(data, f, ensure_ascii=False)
        log(f"  {len(data)} kart verisi temp dosyaya yazıldı")
    except Exception as e:
        log(f"  JS veri çekme hatası: {e}")


# ── DOM'dan ürün verisi çek ───────────────────────────────────────────────────
def urun_cek(page_obj):
    """Temp dosyadan (page_action yazdı) veya Scrapling'den ürünleri çeker."""
    import tempfile, os as _os

    tmp = _os.path.join(tempfile.gettempdir(), '_colruyt_cards.json')
    if _os.path.exists(tmp):
        try:
            with open(tmp, encoding='utf-8') as f:
                raw_cards = json.load(f)
            _os.remove(tmp)
            log(f"  Temp dosyadan {len(raw_cards)} kart")
            urunler = []
            for d in raw_cards:
                if not d.get('name'): continue
                try:    price = float(d['price']) if d.get('price') else None
                except: price = None
                try:    unit_p = float(d['unit_price']) if d.get('unit_price') else None
                except: unit_p = None
                promo_str = d.get('promo', '') or ''
                urunler.append({
                    'chain_slug': 'colruyt_be',
                    'name': d['name'],
                    'brand': d.get('brand') or '',
                    'price': price,
                    'price_old': None,
                    'unit_price': unit_p,
                    'unit_type': 'kg',
                    'in_promo': bool(promo_str.strip()),
                    'promo_label': promo_str,
                    'promo_valid_from': d.get('promo_from'),
                    'promo_valid_until': d.get('promo_to'),
                    'multi_buy': d.get('multi_buy'),
                    'image_url': d.get('image_url') or '',
                    'nutriscore': d.get('nutri'),
                    'content': d.get('content') or '',
                    'category_raw': d.get('top_cat') or '',
                    'retail_num': d.get('retail_num') or '',
                    'captured_at': datetime.now().isoformat(),
                })
            return urunler
        except Exception as e:
            log(f"  Temp dosya hatası: {e}")

    # Fallback: Scrapling CSS selector
    urunler = []
    cards = page_obj.find_all('a.card--article')
    log(f"  Scrapling fallback: {len(cards)} kart")

    for card in cards:
        a = card.attrib

        name = a.get('longname') or a.get('data-tms-product-name', '')
        if not name:
            continue

        # Fiyatlar
        try:    price = float(a.get('data-tms-product-price', '') or 0) or None
        except: price = None
        try:    unit_p = float(a.get('data-tms-product-unitprice', '') or 0) or None
        except: unit_p = None

        promo_str  = a.get('data-tms-product-promotion', '') or ''
        multi_buy  = a.get('data-tms-product-discounts-name', '') or None
        promo_from = a.get('promoPublicationStart') or None
        promo_to   = a.get('promoPublicationEnd') or None
        retail_num = a.get('retailproductnumber', '')
        brand      = a.get('seobrand', '')
        nutri      = a.get('nutriscore') or None
        top_cat    = a.get('topCategoryName', '')
        content    = a.get('data-content', '') or a.get('content', '')

        # Eski fiyat (promo varsa)
        price_old = None
        if promo_str:
            pm = re.search(r'(\d+[,.]\d+)', promo_str)
            if pm:
                try: price_old = float(pm.group(1).replace(',', '.'))
                except: pass

        # Resim: img currentSrc → static.colruytgroup.com
        img_url = ''
        img_el = card.find('img')
        if img_el:
            src = img_el.attrib.get('src', '')
            if src and 'static.colruytgroup.com' in src:
                img_url = src
            elif src and 'asset-' in src:
                # Göreceli URL → tam URL
                img_url = CDN_BASE + src if src.startswith('/') else src

        urunler.append({
            'chain_slug':       'colruyt_be',
            'name':             name,
            'brand':            brand,
            'price':            price,
            'price_old':        price_old,
            'unit_price':       unit_p,
            'unit_type':        'kg',  # Colruyt varsayılan
            'in_promo':         bool(promo_str.strip()),
            'promo_label':      promo_str,
            'promo_valid_from': promo_from,
            'promo_valid_until':promo_to,
            'multi_buy':        multi_buy,
            'image_url':        img_url,
            'nutriscore':       nutri,
            'content':          content,
            'category_raw':     top_cat,
            'retail_num':       retail_num,
            'captured_at':      datetime.now().isoformat(),
        })

    return urunler


# ── Kategori linkleri ─────────────────────────────────────────────────────────
def kategori_linklerini_topla(page_obj, filtre=''):
    """Sayfadaki Colruyt kategori linklerini çeker."""
    linkler = []
    seen = set()
    for a in page_obj.find_all('a'):
        href = a.attrib.get('href', '')
        if not href or '/nl/producten/' not in href:
            continue
        href = href.split('?')[0]
        if href in seen:
            continue
        seen.add(href)
        m = re.search(r'/nl/producten/([^/]+)/([^/]+)(?:/([^/]+))?', href)
        if m:
            linkler.append({
                'url': href if href.startswith('http') else 'https://www.colruyt.be' + href,
                'ust': m.group(1),
                'alt': m.group(2),
                'alt2': m.group(3) or '',
            })
    if filtre:
        linkler = [l for l in linkler if filtre in l['url']]
    return linkler


# ── Tek kategori çek ──────────────────────────────────────────────────────────
def _sayfa_cek(fetcher, url):
    """Tek sayfa çeker, antibot kontrolü ile."""
    page = fetcher.fetch(
        url,
        headless=False,
        wait=2000,
        wait_selector='a.card--article',
        page_action=meer_bekijken_action,
        locale='nl-BE',
        timeout=60000,
    )
    title = page.find('title')
    t = title.text if title else ''
    if 'antibot' in t.lower() or 'bot' in t.lower():
        raise Exception(f"AntiBot: {t}")
    return urun_cek(page)


def kategori_cek(fetcher, url, retries=3):
    """
    Colruyt kategori sayfasını ?page=N ile sayfalayarak çeker.
    Her sayfada 22 ürün → tüm sayfaları toplar.
    """
    delays = [5, 30, 90]
    tum = {}

    # İlk sayfa: cookie popup + ilk 22 ürün
    for attempt in range(retries):
        try:
            urunler = _sayfa_cek(fetcher, url)
            for u in urunler:
                key = u.get('retail_num') or u['name']
                if key: tum[key] = u
            log(f"  Sayfa 1: {len(urunler)} ürün ({len(tum)} toplam)")
            break
        except Exception as e:
            wait = delays[attempt] if attempt < len(delays) else 90
            log(f"  Hata (deneme {attempt+1}): {e} → {wait}s")
            if attempt < retries - 1:
                time.sleep(wait)
    else:
        log(f"  ATILDI: {url}")
        return []

    # Sonraki sayfalar: ?page=2, ?page=3, ... (cookie yok, hızlı)
    bos_sayfa = 0
    for sayfa_no in range(2, 30):
        sayfa_url = f"{url.rstrip('/')}?page={sayfa_no}"
        try:
            # Ürünlerin tam yüklenmesini bekle
            page = fetcher.fetch(
                sayfa_url,
                headless=False,
                wait=5000,           # 5 saniye bekle — render için yeterli
                wait_selector='a.card--article',
                locale='nl-BE',
                timeout=30000,
            )
            title = page.find('title')
            t_txt = title.text if title else ''
            if 'antibot' in t_txt.lower():
                log(f"  Sayfa {sayfa_no}: AntiBot → dur")
                break

            urunler = urun_cek(page)
            if not urunler:
                bos_sayfa += 1
                if bos_sayfa >= 2:
                    break
                continue

            bos_sayfa = 0
            yeni = 0
            for u in urunler:
                key = u.get('retail_num') or u['name']
                if key and key not in tum:
                    tum[key] = u
                    yeni += 1

            log(f"  Sayfa {sayfa_no}: {len(urunler)} ürün, {yeni} yeni ({len(tum)} toplam)")
            if yeni == 0:
                bos_sayfa += 1
                if bos_sayfa >= 2:
                    break

            time.sleep(random.uniform(4, 8))  # İnsan gibi bekle, bot algılama önle

        except Exception as e:
            log(f"  Sayfa {sayfa_no} hata: {e}")
            break

    return list(tum.values())


# ── Ana ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kat',     default='zuivel', help='Filtre kelimesi (kaas, zuivel, vlees...)')
    parser.add_argument('--test',    action='store_true', help='Sadece ilk 2 kategori')
    parser.add_argument('--sifirla', action='store_true', help='Checkpointu sil')
    args = parser.parse_args()

    if args.sifirla and CHECKPOINT.exists():
        CHECKPOINT.unlink()
        log('Checkpoint silindi.')

    state = cp_yukle()
    tum_urunler = {u.get('retail_num') or u['name']: u for u in state.get('urunler', {}).values() if u.get('name')}
    tamamlanan  = list(state.get('tamamlanan', []))

    log(f'Başlangıç: {len(tum_urunler)} ürün, {len(tamamlanan)} tamamlanan')

    try:
        from scrapling.fetchers import DynamicFetcher
    except ImportError:
        log('HATA: pip install "scrapling[fetchers]" && scrapling install')
        return

    fetcher = DynamicFetcher()

    # 1. Ana sayfadan kategori linkleri topla
    log(f'\nKategori linkleri toplanıyor ({args.kat})...')
    try:
        main_page = fetcher.fetch(
            'https://www.colruyt.be/nl/producten',
            headless=True,
            network_idle=True,
            locale='nl-BE',
            timeout=30000,
        )
        kategoriler = kategori_linklerini_topla(main_page, args.kat)
        log(f'  {len(kategoriler)} kategori bulundu')
    except Exception as e:
        log(f'Ana sayfa hatası: {e}')
        # Bilinen URL'leri kullan
        kategoriler = [
            {'url': f'https://www.colruyt.be/nl/producten/alle-categorieen/{args.kat}', 'ust': 'alle-categorieen', 'alt': args.kat, 'alt2': ''},
        ]

    if args.test:
        kategoriler = kategoriler[:2]
        log(f'TEST modu: {len(kategoriler)} kategori')

    # Tamamlananları çıkar
    kategoriler = [k for k in kategoriler if k['url'] not in tamamlanan]
    log(f'İşlenecek: {len(kategoriler)} kategori\n')

    # 2. Her kategoriyi çek
    for i, kat in enumerate(kategoriler, 1):
        log(f'[{i}/{len(kategoriler)}] {kat["url"]}')

        urunler = kategori_cek(fetcher, kat['url'])
        log(f'  ✓ {len(urunler)} ürün')

        for u in urunler:
            key = u.get('retail_num') or u['name']
            if key:
                u['kategori_ust'] = kat.get('ust', '')
                u['kategori_alt'] = kat.get('alt', '')
                tum_urunler[key] = u

        tamamlanan.append(kat['url'])
        state = {'tamamlanan': tamamlanan, 'urunler': tum_urunler}
        cp_kaydet(state)

        # Özet
        log(f'  Toplam: {len(tum_urunler)} ürün')
        time.sleep(random.uniform(3, 7))

    # 3. JSON kaydet
    cikti_dosya = CIKTI_DIR / f'colruyt_scrapling_{args.kat}_{datetime.now().strftime("%Y-%m-%d")}.json'
    final = {
        'kayit_zamani': datetime.now().isoformat(),
        'urun_sayisi': len(tum_urunler),
        'urunler': list(tum_urunler.values()),
    }
    with open(cikti_dosya, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False)

    # Özet
    fiyatli = sum(1 for u in tum_urunler.values() if u.get('price'))
    resimli  = sum(1 for u in tum_urunler.values() if u.get('image_url'))
    promolu  = sum(1 for u in tum_urunler.values() if u.get('in_promo'))
    multi    = sum(1 for u in tum_urunler.values() if u.get('multi_buy'))

    log(f'\n{"="*55}')
    log(f'TAMAMLANDI — {len(tum_urunler)} ürün')
    log(f'  Fiyatlı:    {fiyatli}')
    log(f'  Resimli:    {resimli}')
    log(f'  İndirimli:  {promolu}')
    log(f'  Multi-buy:  {multi}')
    log(f'  JSON: {cikti_dosya}')
    log(f'{"="*55}')


if __name__ == '__main__':
    main()
