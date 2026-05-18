import sys
sys.stdout.reconfigure(encoding='utf-8')
from supabase import create_client

sb = create_client(
    'https://vhietrqljahdmloazgpp.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTcsImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA'
)

# DB'deki Colruyt eieren ürünleri
r = sb.table('market_chain_products').select(
    'external_product_id,name,price,chain_slug,in_promo'
).eq('chain_slug', 'colruyt_be').ilike('name', '%eieren%').limit(15).execute()

print(f"DB'deki Colruyt eieren ürünleri: {len(r.data)}")
for p in r.data:
    eid = p.get('external_product_id', '?')
    name = p.get('name', '?')
    price = p.get('price', '?')
    print(f"  ext_id={eid} | price={price} | {name[:50]}")

# Serbest gezen / vrij uitloop kontrolü
print()
r2 = sb.table('market_chain_products').select(
    'external_product_id,name,price,chain_slug'
).eq('chain_slug', 'colruyt_be').ilike('name', '%uitloop%').limit(10).execute()
print(f"Colruyt 'uitloop' ürünleri: {len(r2.data)}")
for p in r2.data:
    print(f"  {p.get('external_product_id')} | {p.get('price')} EUR | {p.get('name', '')[:50]}")

# Toplam Colruyt sayısı
r3 = sb.table('market_chain_products').select('external_product_id', count='exact').eq('chain_slug', 'colruyt_be').execute()
print(f"\nToplam Colruyt ürünü DB'de: {r3.count}")
