# -*- coding: utf-8 -*-
"""
DB'deki yumurta ürünlerini temiz çeker.
Her market için kesin yumurta filtresi kullanır.
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
from supabase import create_client

sb = create_client(
    'https://vhietrqljahdmloazgpp.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTcsImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA'
)

# Her market için kesin yumurta eşleşme kalıpları
MARKET_FILTRELER = {
    'colruyt_be': [
        'eieren', 'uitloop', 'scharrel', 'kwartelei',
    ],
    'aldi_be': [
        'eieren', 'uitloop', 'scharrel', 'kwartelei', 'kwarteleieren',
    ],
    'delhaize_be': [
        'eieren', 'uitloop', 'scharrel', 'kwartelei',
    ],
    'lidl_be': [
        'eieren', 'uitloop', 'scharrel',
    ],
    'carrefour_be': [
        'eieren', 'uitloop', 'scharrel', 'yumurta',
    ],
}

# Kesin yumurta OLMAYAN şeyler (isimde geçse bile)
DISLAMA = [
    # Çikolata ve şeker yumurtaları
    'chocolade', 'praline', 'fondant', 'croquant', 'choco', 'biscuit',
    'caramel', 'vulling', 'smaak', 'zakje eieren', 'dragee', 'eitjes',
    # Paskalya çikolataları
    'paas', 'pâques', 'paque', 'passeieren',
    # Balık yumurtaları
    'viseieren', 'lompviseieren', 'foreleieren', 'zalmeieren',
    # Yumurtalı yiyecekler (gerçek yumurta değil)
    'madeleines', 'lasagne', 'macaroni', 'noodle', 'noedels',
    'wafels', 'wafeltjes', 'spaghetti', 'tagliatelle', 'pasta ',
    'salade', 'quiche', 'broodje', 'driehoek', 'croque',
    # Diğer
    'mayonaise', 'mayo', 'confituur', 'aardbei', 'gelei kat',
    'kattenvoeding', 'hondenvoeding', 'prei ', 'sproeier', 'kraan',
    'badkamer', 'tapijt', 'boetseer', 'tonijn', 'sardien', 'makreel',
    'advocaat', 'eierlikeur', 'eikenblad', 'eikenhout', 'eiken vaten',
    'proteinen ', 'eiwitconcentraat', 'eiwitrijke',
    'livarno', 'silvercrest', 'lupilu', 'gardena', 'parkside',
    'libeert', 'original | eieren | wit', 'original | eieren | melk',
    'original | eieren | puur',
]

def is_yumurta(name: str) -> bool:
    n = name.lower()
    if any(d in n for d in DISLAMA):
        return False
    return True

def kategori(name: str, name_tr: str = '') -> str:
    n = (name + ' ' + (name_tr or '')).lower()
    if any(k in n for k in ['kwart', 'bıldırcın', 'quail']):
        return '🐦 Bıldırcın'
    if any(k in n for k in ['bio', 'biolog', 'organik', 'organic']):
        return '🌿 Bio'
    if any(k in n for k in ['scharrel', 'uitloop', 'vrij', 'serbest', 'plein air', 'fermier']):
        return '🐔 Serbest Gezen'
    if any(k in n for k in ['hardgekookt', 'hard gekookt', 'haşlanmış', 'gekleurd']):
        return '⚡ Haşlanmış'
    if any(k in n for k in ['omega', 'verrijkt']):
        return '💊 Omega/Özel'
    return '🥚 Normal'

def adet_fiyat(fiyat, name, content=''):
    if not fiyat or fiyat <= 0:
        return None
    metin = ((content or '') + ' ' + name).lower()
    m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|pièces?|eieren\b|oeufs?\b)', metin, re.I)
    if m:
        adet = int(m.group(1))
        if 3 <= adet <= 60:
            return round(fiyat / adet, 4)
    return None

MARKET_ADI = {
    'colruyt_be':  'COLRUYT',
    'aldi_be':     'ALDI',
    'delhaize_be': 'DELHAIZE',
    'lidl_be':     'LIDL',
    'carrefour_be':'CARREFOUR',
}

print("5 marketten yumurta verileri çekiliyor...\n")

for slug, filtreler in MARKET_FILTRELER.items():
    market_urunler = {}

    for kw in filtreler:
        r = sb.table('market_chain_products') \
               .select('external_product_id,name,name_tr,price,promo_price,'
                       'in_promo,promo_valid_until,unit_or_content,image_url,'
                       'chain_slug,currency,captured_at') \
               .eq('chain_slug', slug) \
               .ilike('name', f'%{kw}%') \
               .limit(80).execute()

        for p in (r.data or []):
            fiyat = p.get('price') or 0
            if fiyat <= 0:
                continue  # fiyatsızları atla
            key = p.get('external_product_id') or p.get('name')
            if key and key not in market_urunler:
                if is_yumurta(p.get('name', '')):
                    market_urunler[key] = p

    urunler = list(market_urunler.values())

    print(f"\n{'='*70}")
    print(f"  {MARKET_ADI[slug]}  —  {len(urunler)} ürün")
    print(f"{'='*70}")

    if not urunler:
        print("  Ürün bulunamadı.")
        continue

    # Kategoriye göre grupla
    gruplar = {}
    for p in urunler:
        kat = kategori(p.get('name',''), p.get('name_tr',''))
        gruplar.setdefault(kat, []).append(p)

    for kat in ['🌿 Bio', '🐔 Serbest Gezen', '🥚 Normal', '🐦 Bıldırcın', '⚡ Haşlanmış', '💊 Omega/Özel']:
        if kat not in gruplar:
            continue
        print(f"\n  [{kat}]")
        for p in sorted(gruplar[kat], key=lambda x: (x.get('price') or 0)):
            name   = p.get('name', '?')[:55]
            name_tr = (p.get('name_tr') or '')[:40]
            price  = p.get('price') or 0
            promo  = p.get('promo_price')
            in_pr  = p.get('in_promo', False)
            unit_c = p.get('unit_or_content') or ''
            img    = '✓' if p.get('image_url') else '✗'

            # Fiyat
            if in_pr and promo and float(promo) > 0:
                f_str = f"{price:.2f} → {float(promo):.2f} EUR [İNDİRİM]"
            elif price > 0:
                f_str = f"{price:.2f} EUR"
            else:
                f_str = "Fiyat yok"

            # Adet fiyatı
            eff_price = float(promo) if (in_pr and promo) else price
            adet_f = adet_fiyat(eff_price, name, unit_c)
            a_str = f" | {adet_f:.3f} €/adet".replace('.',',') if adet_f else ""

            # İçerik
            ic_str = f" | {unit_c}" if unit_c else ""

            print(f"    • {name}")
            if name_tr and name_tr.strip() and name_tr != name:
                print(f"      TR: {name_tr}")
            print(f"      {f_str}{a_str}{ic_str} | Resim:{img}")

print(f"\n{'='*70}")
print("TAMAMLANDI")
print(f"{'='*70}")
