import os, requests
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supabase_import_secrets.txt")
lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore") if l.strip() and not l.strip().startswith("#")]
sb_url, sb_key = lines[0].rstrip("/"), lines[1]
headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}

# ilike ile ara - farkli syntax dene
print("Test 1: ilike.*ekmek*")
r = requests.get(f"{sb_url}/rest/v1/market_chain_products",
    params={"select": "name,name_tr", "name_tr": "ilike.*ekmek*", "limit": "3"},
    headers=headers)
print(f"  Status: {r.status_code}, Sonuc: {r.json()[:2] if isinstance(r.json(), list) else r.json()}")

print("Test 2: ilike ile %ekmek%")
r2 = requests.get(f"{sb_url}/rest/v1/market_chain_products",
    params={"select": "name,name_tr", "limit": "3"},
    headers={**headers, "Prefer": ""},
)
# URL encode ile dene
import urllib.parse
url = f"{sb_url}/rest/v1/market_chain_products?select=name,name_tr&name_tr=ilike.%25ekmek%25&limit=3"
r3 = requests.get(url, headers=headers)
print(f"  Status: {r3.status_code}, Sonuc: {r3.json()[:2] if isinstance(r3.json(), list) else r3.json()}")

print("\nTest 3: name'de Hollandaca ara")
r4 = requests.get(f"{sb_url}/rest/v1/market_chain_products",
    params={"select": "name,name_tr", "name": "ilike.*melk*", "limit": "3"},
    headers=headers)
print(f"  Status: {r4.status_code}, Sonuc: {r4.json()[:2] if isinstance(r4.json(), list) else r4.json()}")
