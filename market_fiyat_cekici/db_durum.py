import sys
sys.stdout.reconfigure(encoding='utf-8')
from supabase import create_client

sb = create_client(
    'https://vhietrqljahdmloazgpp.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoaWV0cnFsamFoZG1sb2F6Z3BwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUwNTk5MTcsImV4cCI6MjA4MDYzNTkxN30.sxpUrTnR40XuEBPUeQXj352xMziGr_lDqdA8H69ejBA'
)

anahtar = ['scharrel','uitloop','vrij','vrije','free']

for market in ['colruyt_be','aldi_be','delhaize_be','lidl_be','carrefour_be']:
    print(f"\n{'='*60}")
    print(f"  {market}")
    print(f"{'='*60}")

    for kw in anahtar:
        r = sb.table('market_chain_products')\
               .select('name,price,unit_or_content,image_url')\
               .eq('chain_slug', market)\
               .ilike('name', f'%{kw}%')\
               .gt('price', 0)\
               .limit(5)\
               .execute()
        if r.data:
            for p in r.data:
                img = '✓' if p.get('image_url') else '✗'
                unit = p.get('unit_or_content') or '?'
                print(f"  [{kw}] {p['name'][:40]:<40} {p['price']:>6} EUR | adet:{unit:<12} | resim:{img}")
            break
    else:
        print(f"  Hiç eşleşme yok (price>0 ile)")
