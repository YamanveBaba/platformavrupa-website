from html.parser import HTMLParser
import glob, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

class ProductParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.products = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'card--article' in attrs.get('class', ''):
            price = attrs.get('data-tms-product-price', '')
            unit_price = attrs.get('data-tms-product-unitprice', '')
            name = attrs.get('data-tms-product-name', '')
            longname = attrs.get('longname', '')
            brand = attrs.get('seobrand', '')
            gtins = attrs.get('gtin', '')
            ean = gtins.split(',')[0] if gtins else ''
            retail_num = attrs.get('retailproductnumber', '')
            nutriscore = attrs.get('nutriscore', '')
            ecoscore = attrs.get('ecoscorevalue', '')
            promo = attrs.get('data-tms-product-promotion', '')
            if name or longname:
                self.products.append({
                    'name': longname or name,
                    'price': price,
                    'unit_price': unit_price,
                    'brand': brand,
                    'ean': ean,
                    'retail_num': retail_num,
                    'nutriscore': nutriscore,
                    'ecoscore': ecoscore,
                    'promo': promo,
                })

# Indirilenler klasöründeki tüm Colruyt HTML'lerini bul
files = glob.glob(r'C:\Users\yaman\Downloads\*Yumurta*.html') + \
        glob.glob(r'C:\Users\yaman\Downloads\*colruyt*.html') + \
        glob.glob(r'C:\Users\yaman\Downloads\*Colruyt*.html') + \
        glob.glob(r'C:\Users\yaman\Downloads\*Carrefour*.html')

files = list(set(files))
print(f"Bulunan HTML dosyalar: {len(files)}")
for f in files:
    print(f"  - {f}")

print()

all_products = []
for filepath in files:
    with open(filepath, encoding='utf-8', errors='ignore') as fh:
        html = fh.read()
    p = ProductParser()
    p.feed(html)
    print(f"\n=== {filepath.split(chr(92))[-1]} === ({len(p.products)} urun)")
    for u in p.products:
        print(f"  {u['name']:<50} | {u['price']:>6} EUR | {u['unit_price']:>8} EUR/birim | EAN: {u['ean']} | Promo: {u['promo']}")
    all_products.extend(p.products)

print(f"\nToplam: {len(all_products)} urun")
