# -*- coding: utf-8 -*-
"""
Kaydedilmiş Colruyt HTML sayfalarından ürün fiyatlarını çekip
market_chain_products tablosundaki fiyatsız kayıtları günceller.

Çalıştırma:
    python html_fiyat_guncelle.py "C:/Users/yaman/Downloads/Yumurta*.html"
    python html_fiyat_guncelle.py  (Downloads klasöründeki tüm Colruyt HTML'leri)
"""

import sys, glob, re, json
from html.parser import HTMLParser
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Supabase bağlantısı
try:
    from supabase import create_client
    SUPABASE_URL = "https://vhietrqljahdmloazgpp.supabase.co"
    SUPABASE_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6"
                    "InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTc"
                    "sImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA")
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    DB_VAR = True
except Exception as e:
    print(f"[UYARI] Supabase bağlanamadı: {e}")
    print("Sadece parse modu — DB güncelleme yapılmayacak")
    DB_VAR = False


class ColruytHTMLParser(HTMLParser):
    """Colruyt kategori sayfasından ürün kartlarını parse eder."""

    def __init__(self):
        super().__init__()
        self.urunler = []

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')
        if 'card--article' not in cls:
            return

        a = attrs_dict

        # Fiyatlar
        price = a.get('data-tms-product-price', '').strip()
        unit_price = a.get('data-tms-product-unitprice', '').strip()

        # Promo
        promo_str = a.get('data-tms-product-promotion', '') or ''
        in_promo = bool(promo_str and promo_str.strip())

        # İsimler
        longname = a.get('longname', '').strip()
        short_name = a.get('shortname', '').strip()
        name = a.get('data-tms-product-name', '').strip()

        # Kimlik
        retail_num = a.get('retailproductnumber', '').strip()
        tech_num = a.get('data-technical-article-number', '').strip()
        product_id = a.get('data-tms-product-id', '').strip()

        # EAN (virgülle ayrılmış, ilkini al)
        gtin_raw = a.get('gtin', '').strip()
        ean = gtin_raw.split(',')[0].strip() if gtin_raw else ''

        # Ek bilgiler
        brand = a.get('seobrand', '').strip()
        nutriscore = a.get('nutriscore', '').strip()
        ecoscore = a.get('ecoscorevalue', '').strip()
        country = a.get('countryoforigin', '').strip()

        if not (name or longname):
            return

        # Sayısal dönüşüm
        price_f = None
        unit_price_f = None
        try:
            if price:
                price_f = float(price)
        except ValueError:
            pass
        try:
            if unit_price:
                unit_price_f = float(unit_price)
        except ValueError:
            pass

        self.urunler.append({
            'retail_num': retail_num,
            'tech_num': tech_num,
            'product_id': product_id,
            'ean': ean,
            'name': longname or name,
            'short_name': short_name,
            'brand': brand,
            'price': price_f,
            'unit_price': unit_price_f,
            'in_promo': in_promo,
            'promo_str': promo_str,
            'nutriscore': nutriscore,
            'ecoscore': ecoscore,
            'country': country,
        })


def html_parse(dosya_yolu: str) -> list:
    """Bir HTML dosyasını parse edip ürün listesi döner."""
    with open(dosya_yolu, encoding='utf-8', errors='ignore') as f:
        html = f.read()
    parser = ColruytHTMLParser()
    parser.feed(html)
    return parser.urunler


def db_guncelle(urunler: list, dry_run: bool = False) -> dict:
    """Fiyatı olan ürünleri DB'de retail_num ile eşleştirip günceller."""
    if not DB_VAR:
        return {'atlandı': len(urunler), 'güncellendi': 0, 'fiyatsız': 0}

    fiyatli = [u for u in urunler if u['price'] is not None]
    fiyatsiz = len(urunler) - len(fiyatli)

    guncellendi = 0
    hata = 0

    print(f"  Toplam: {len(urunler)} ürün | Fiyatlı: {len(fiyatli)} | Fiyatsız: {fiyatsiz}")

    for u in fiyatli:
        retail = u['retail_num']
        if not retail:
            continue

        update_data = {
            'price': u['price'],
            'in_promo': u['in_promo'],
        }
        # Sadece var olan kolonları güncelle
        if u['nutriscore']:
            update_data['nutriScore'] = u['nutriscore']

        if dry_run:
            print(f"  [DRY] {u['name'][:45]:<45} fiyat={u['price']} EUR | birim={u['unit_price']}")
            guncellendi += 1
            continue

        try:
            # external_product_id = retailProductNumber (Colruyt için)
            result = sb.table('market_chain_products') \
                       .update(update_data) \
                       .eq('chain_slug', 'colruyt_be') \
                       .eq('external_product_id', retail) \
                       .execute()
            if result.data:
                guncellendi += 1
                print(f"  ✓ {u['name'][:45]:<45} {u['price']} EUR")
            else:
                print(f"  ? DB'de yok: {u['name'][:40]} (retail={retail})")
        except Exception as e:
            hata += 1
            print(f"  ✗ HATA: {u['name'][:40]} — {e}")

    return {
        'toplam': len(urunler),
        'fiyatlı': len(fiyatli),
        'fiyatsız': fiyatsiz,
        'güncellendi': guncellendi,
        'hata': hata,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('dosyalar', nargs='*',
                       default=[r'C:\Users\yaman\Downloads\*Colruyt*.html',
                                r'C:\Users\yaman\Downloads\*colruyt*.html',
                                r'C:\Users\yaman\Downloads\*umurta*.html'])
    parser.add_argument('--dry-run', action='store_true',
                       help='DB güncellemeden sadece parse et')
    args = parser.parse_args()

    # Dosya listesini topla
    dosya_listesi = []
    for pattern in args.dosyalar:
        dosya_listesi.extend(glob.glob(pattern))
    dosya_listesi = list(set(dosya_listesi))

    if not dosya_listesi:
        print("HTML dosyası bulunamadı.")
        return

    print(f"\nBulunan HTML dosyalar: {len(dosya_listesi)}")

    tum_urunler = []
    for dosya in sorted(dosya_listesi):
        kisa_ad = dosya.split('\\')[-1]
        urunler = html_parse(dosya)
        print(f"\n{'='*60}")
        print(f"Dosya: {kisa_ad}")
        print(f"  Parse edilen ürün: {len(urunler)}")

        if urunler:
            # Özet göster
            fiyatli = [u for u in urunler if u['price'] is not None]
            print(f"  Fiyatlı ürün: {len(fiyatli)}")
            for u in urunler[:5]:
                print(f"  → {u['name'][:50]:<50} {u['price'] or '?':>7} EUR | birim: {u['unit_price'] or '?'}")
            if len(urunler) > 5:
                print(f"  ... ve {len(urunler)-5} ürün daha")

        tum_urunler.extend(urunler)

    print(f"\n{'='*60}")
    print(f"TOPLAM: {len(tum_urunler)} ürün parse edildi")

    # Duplikat temizle (retail_num'a göre)
    tekil = {}
    for u in tum_urunler:
        key = u['retail_num'] or u['ean'] or u['name']
        if key and key not in tekil:
            tekil[key] = u

    print(f"Tekil ürün: {len(tekil)}")

    if args.dry_run:
        print("\n[DRY RUN] DB güncellenmeyecek:")
        for u in list(tekil.values())[:20]:
            if u['price']:
                print(f"  {u['name'][:50]:<50} {u['price']:>7} EUR | {u['unit_price'] or '?'} EUR/birim")
    else:
        print("\nDB güncelleniyor...")
        sonuc = db_guncelle(list(tekil.values()))
        print(f"\nSONUÇ: {sonuc['güncellendi']} güncellendi, "
              f"{sonuc['fiyatsız']} fiyatsız atlandı, "
              f"{sonuc.get('hata',0)} hata")


if __name__ == '__main__':
    main()
