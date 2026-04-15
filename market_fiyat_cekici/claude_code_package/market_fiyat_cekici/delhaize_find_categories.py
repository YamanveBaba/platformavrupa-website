"""Delhaize FullHeader API ile tüm kategorileri ve GetCategoryProductSearch ile ürün yapısını keşfeder."""
import json
import urllib.parse
import requests

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

API_BASE = "https://www.delhaize.be/api/v1/"
HEADERS = {
    "User-Agent": CHROME_UA,
    "Accept": "application/json",
    "Accept-Language": "nl-BE,nl;q=0.9",
    "Referer": "https://www.delhaize.be/nl/shop",
    "Origin": "https://www.delhaize.be",
}

FULL_HEADER_HASH    = "071789a7a9a9f4ec596ddeb155ebbbf6c98c5da05ca60d84088e4aa17efc008d"
PRODUCT_SEARCH_HASH = "189e7cb5a6ba93e55dc63e4eef0ad063ca3e8aedb0bdf2a58124e02d5d5d69a2"

def gql_get(op_name, variables, hash_val):
    params = {
        "operationName": op_name,
        "variables": json.dumps(variables, separators=(",",":")),
        "extensions": json.dumps({"persistedQuery":{"version":1,"sha256Hash":hash_val}}, separators=(",",":")),
    }
    r = requests.get(API_BASE, params=params, headers=HEADERS, timeout=30)
    print(f"HTTP {r.status_code}: {r.url[:100]}")
    return r.json() if r.ok else None

def find_all_cats(obj, result=None, depth=0):
    if result is None: result = []
    if depth > 6: return result
    if isinstance(obj, dict):
        if "code" in obj and "name" in obj and isinstance(obj.get("name"), str):
            code = obj["code"]
            name = obj["name"]
            if code.startswith("v2") and len(name) > 2:
                result.append({"code": code, "name": name})
        for v in obj.values():
            find_all_cats(v, result, depth+1)
    elif isinstance(obj, list):
        for item in obj:
            find_all_cats(item, result, depth+1)
    return result

# 1. FullHeader
print("=== FullHeader (kategori ağacı) ===")
body = gql_get("FullHeader", {"lang": "nl"}, FULL_HEADER_HASH)
if body:
    cats = find_all_cats(body)
    seen = {}
    for c in cats:
        seen[c["code"]] = c["name"]
    print(f"\nBulunan v2 kategoriler ({len(seen)}):")
    for code, name in sorted(seen.items()):
        print(f"  {code:20} {name.encode('utf-8','replace').decode()}")
else:
    print("FullHeader calismadi")

# 2. GetCategoryProductSearch - bir kategori test et
print("\n=== GetCategoryProductSearch (v2MEAMEA - Vers vlees) ===")
body2 = gql_get("GetCategoryProductSearch", {
    "lang": "nl", "searchQuery": "", "category": "v2MEAMEA",
    "pageNumber": 0, "pageSize": 5, "filterFlag": True,
    "fields": "PRODUCT_TILE", "plainChildCategories": True
}, PRODUCT_SEARCH_HASH)

if body2:
    cps = body2.get("data", {}).get("categoryProductSearch", {})
    pagination = cps.get("pagination", {})
    prods = cps.get("products", [])
    print(f"pagination: {pagination}")
    print(f"Bu sayfada: {len(prods)} urun")
    if prods:
        p0 = prods[0]
        print(f"\nOrnek urun:")
        print(f"  code: {p0.get('code')}")
        print(f"  name: {str(p0.get('name','')).encode('utf-8','replace').decode()}")
        print(f"  price: {p0.get('price')}")
        print(f"  potentialPromotions: {p0.get('potentialPromotions')}")
        print(f"  manufacturerName: {p0.get('manufacturerName')}")
        print(f"  firstLevelCategory: {p0.get('firstLevelCategory')}")

    # categorySearchTree ile alt kategorileri bul
    tree = cps.get("categorySearchTree", {})
    if tree:
        sub_cats = find_all_cats(tree)
        seen2 = {}
        for c in sub_cats:
            seen2[c["code"]] = c["name"]
        print(f"\ncategorySearchTree kategoriler ({len(seen2)}):")
        for code, name in sorted(seen2.items()):
            print(f"  {code:25} {name.encode('utf-8','replace').decode()}")
