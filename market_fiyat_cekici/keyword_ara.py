import sys
sys.stdout.reconfigure(encoding='utf-8')
from supabase import create_client

sb = create_client(
    'https://vhietrqljahdmloazgpp.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTcsImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA'
)

# Carrefour serbest gezen keywords
print("=== CARREFOUR ===")
for kw in ['fermier', 'vrije', 'uitloop', 'plein air', 'gallina', 'gallo', 'mamie', 'poule']:
    r = sb.table('market_chain_products').select('name,price') \
           .eq('chain_slug', 'carrefour_be') \
           .ilike('name', f'%{kw}%') \
           .gt('price', 0) \
           .limit(5).execute()
    if r.data:
        print(f'\n[{kw}]:')
        for p in r.data:
            print(f'  {p["name"][:60]} | {p["price"]}')

# ALDI tam isimler + name_tr
print("\n\n=== ALDI ===")
r2 = sb.table('market_chain_products') \
       .select('name,name_tr,price,external_product_id') \
       .eq('chain_slug', 'aldi_be') \
       .or_('name.ilike.%eier%,name.ilike.%uitloop%,name.ilike.%scharrel%') \
       .gt('price', 0) \
       .limit(15).execute()
for p in r2.data:
    nm = p['name']
    tr = (p.get('name_tr') or '')[:35]
    print(f'  {nm:<45} / {tr:<35} | {p["price"]}')

# Lidl
print("\n\n=== LİDL ===")
r3 = sb.table('market_chain_products') \
       .select('name,price,unit_or_content') \
       .eq('chain_slug', 'lidl_be') \
       .or_('name.ilike.%eier%,name.ilike.%uitloop%,name.ilike.%scharrel%,name.ilike.%kip%') \
       .gt('price', 0) \
       .limit(10).execute()
for p in r3.data:
    print(f'  {p["name"][:60]} | {p["price"]} | {p.get("unit_or_content","?")}')
