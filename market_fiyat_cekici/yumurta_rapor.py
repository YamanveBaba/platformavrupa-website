# -*- coding: utf-8 -*-
"""
5 marketten tüm yumurta ürünlerini çeker, kategorize eder, rapor üretir.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from supabase import create_client

sb = create_client(
    'https://vhietrqljahdmloazgpp.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTcsImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA'
)

MARKET_ISIMLER = {
    'colruyt_be': 'Colruyt',
    'aldi_be':    'ALDI',
    'delhaize_be':'Delhaize',
    'lidl_be':    'Lidl',
    'carrefour_be':'Carrefour',
}

# Yumurta keyword'leri - geniş net
YUMURTA_KW = [
    'eieren', 'eier', 'ei ', ' ei', 'scharreleieren', 'scharrelei',
    'uitloopeieren', 'kwarteleieren', 'kwartelei', 'bio-eieren',
    'vrije-uitloop', 'hardgekookt', 'yumurta', 'tavuk yumurtası',
    'ücretsiz değişen', 'serbest', 'organik yumurta', 'bıldırcın',
]

# Yanlış eşleşme olabilecekler - exclude
EXCLUDE_KW = [
    'mayonaise', 'mayo', 'eierwafels', 'eierkoeken', 'tagliatelle',
    'pasta', 'pannenkoeken', 'impulssproeier', 'sproeier', 'skipak',
    'wafel', 'koeken', 'kippenborstfilet', 'kip tomaat', 'parkside',
    'paaseieren belgische chocolade', 'holle paaseieren',
    'livarno', 'lupilu', 'gardena',
]


def kategori_belirle(name: str, name_tr: str) -> str:
    """Ürün adına bakarak kategori belirler."""
    n = (name + ' ' + (name_tr or '')).lower()

    # Önce yanlış pozitif kontrolü
    for ex in EXCLUDE_KW:
        if ex in n:
            return 'DIŞLA'

    # Bıldırcın
    if any(k in n for k in ['kwart', 'bıldırcın', 'quail']):
        return 'Bıldırcın Yumurtası'

    # Bio
    if any(k in n for k in ['bio', 'biolog', 'organik', 'organic']):
        return 'Bio Yumurta'

    # Serbest gezen
    if any(k in n for k in ['scharrel', 'uitloop', 'vrij', 'free range',
                              'serbest', 'plein air', 'fermier', 'ücretsiz değişen']):
        return 'Serbest Gezen Yumurta'

    # Haşlanmış
    if 'hardgekookt' in n or 'haşlanmış' in n or 'pâques' in n:
        return 'Haşlanmış Yumurta'

    # Normal yumurta
    if any(k in n for k in ['eieren', 'eier', 'yumurta', 'ei ']):
        return 'Normal Yumurta'

    return 'Diğer'


def adet_fiyat(price, unit_or_content, name):
    """Adet başına fiyat hesaplar."""
    if not price or price <= 0:
        return None
    # Önce unit_or_content'e bak
    content = (unit_or_content or '') + ' ' + (name or '')
    import re
    m = re.search(r'(\d+)\s*(?:stuks?|st\.?|adet|pièces?|stück|pcs)', content, re.I)
    if m:
        adet = int(m.group(1))
        if adet > 0:
            return round(price / adet, 4)
    # isimde "18 st." gibi
    m2 = re.search(r'(\d{1,2})\s*st', content, re.I)
    if m2:
        adet = int(m2.group(1))
        if 3 <= adet <= 60:
            return round(price / adet, 4)
    return None


def tum_yumurtalari_cek():
    """Tüm marketlerden yumurta ürünlerini çeker."""
    tum = []
    for market_slug in MARKET_ISIMLER.keys():
        # Her keyword için ayrı sorgu at
        bulunanlar = {}
        for kw in YUMURTA_KW:
            r = sb.table('market_chain_products') \
                   .select('external_product_id,name,name_tr,price,promo_price,in_promo,'
                           'promo_valid_from,promo_valid_until,unit_or_content,image_url,'
                           'chain_slug,currency') \
                   .eq('chain_slug', market_slug) \
                   .ilike('name', f'%{kw}%') \
                   .limit(100) \
                   .execute()
            for p in (r.data or []):
                key = p.get('external_product_id') or p.get('name', '')
                if key and key not in bulunanlar:
                    bulunanlar[key] = p
        tum.extend(bulunanlar.values())
    return tum


def rapor_yaz(urunler):
    market_gruplari = {}
    for p in urunler:
        slug = p.get('chain_slug', '?')
        market_gruplari.setdefault(slug, []).append(p)

    toplam_gosterilen = 0
    toplam_dislanan = 0

    for slug, market_urunler in sorted(market_gruplari.items()):
        market_adi = MARKET_ISIMLER.get(slug, slug)
        print(f'\n{"="*70}')
        print(f'  {market_adi}  ({len(market_urunler)} ürün bulundu)')
        print(f'{"="*70}')

        kat_gruplari = {}
        for p in market_urunler:
            kat = kategori_belirle(p.get('name', ''), p.get('name_tr', ''))
            kat_gruplari.setdefault(kat, []).append(p)

        # Önce DIŞLA'ları göster
        disla = kat_gruplari.pop('DIŞLA', [])
        if disla:
            toplam_dislanan += len(disla)

        for kat, kati_urunler in sorted(kat_gruplari.items()):
            print(f'\n  [{kat}]')
            for p in sorted(kati_urunler, key=lambda x: x.get('price') or 0):
                name = p.get('name', '?')[:55]
                name_tr = (p.get('name_tr') or '')[:40]
                price = p.get('price') or 0
                promo = p.get('promo_price')
                in_promo = p.get('in_promo', False)
                unit_c = p.get('unit_or_content') or ''
                img = '✓' if p.get('image_url') else '✗'
                currency = p.get('currency') or 'EUR'

                # Adet fiyatı
                adet_f = adet_fiyat(price, unit_c, p.get('name', ''))

                # Fiyat gösterimi
                if in_promo and promo and float(promo) > 0:
                    fiyat_str = f'{price:.2f} → {float(promo):.2f} {currency} (İNDİRİM)'
                elif price > 0:
                    fiyat_str = f'{price:.2f} {currency}'
                else:
                    fiyat_str = f'Fiyat yok'

                adet_str = f' | {adet_f:.3f} €/adet'.replace('.', ',') if adet_f else ''
                icerik_str = f' | {unit_c}' if unit_c else ''

                print(f'    • {name}')
                if name_tr and name_tr != name:
                    print(f'      TR: {name_tr}')
                print(f'      Fiyat: {fiyat_str}{adet_str}{icerik_str} | Resim:{img}')
                toplam_gosterilen += 1

    print(f'\n{"="*70}')
    print(f'TOPLAM: {toplam_gosterilen} ürün gösterildi, {toplam_dislanan} yanlış eşleşme dışlandı')


if __name__ == '__main__':
    print('5 marketten yumurta verileri çekiliyor...\n')
    urunler = tum_yumurtalari_cek()
    print(f'Ham sonuç: {len(urunler)} ürün (filtreleme öncesi)')
    rapor_yaz(urunler)
