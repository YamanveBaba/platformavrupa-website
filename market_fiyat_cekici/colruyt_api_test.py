# -*- coding: utf-8 -*-
"""
Colruyt API — Direkt requests testi (Playwright olmadan)
=========================================================
Önce bunu çalıştır: python colruyt_api_test.py
Eğer ürünler geliyorsa colruyt_api_direkt.py'yi kullanabiliriz (çok daha hızlı).
Eğer 401/403 geliyorsa Playwright şart — session cookie lazım.
"""

import json
import requests

API_BASE = (
    "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc"
    "/cg/nl/api/product-search-prs"
)
API_KEY = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
PLACE_ID = "710"  # Gent

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.colruyt.be/nl/producten",
    "Origin": "https://www.colruyt.be",
    "X-CG-APIKey": API_KEY,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

# Kaas (peynir) kategorisi — ID 91
params = {
    "placeId": PLACE_ID,
    "categoryId": "91",
    "size": "10",
    "skip": "0",
    "isAvailable": "true",
}

print("Colruyt API test ediliyor (auth cookie olmadan)...")
print(f"URL: {API_BASE}")
print(f"Params: {params}\n")

try:
    r = requests.get(API_BASE, params=params, headers=HEADERS, timeout=15)
    print(f"HTTP Status: {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        bulunan = data.get("productsFound", 0)
        urunler = data.get("products", [])
        print(f"\nBULUNDU! {bulunan} ürün var, {len(urunler)} döndü.")
        print("\nIlk 3 ürün:")
        for u in urunler[:3]:
            pr = u.get("price") or {}
            print(f"  - {u.get('LongName') or u.get('name')} | {pr.get('basicPrice')} EUR | {u.get('thumbNail','')[:60]}")
        print("\nSONUÇ: API key yeterli — Playwright GEREKMEZ!")
        print("Direkt API scripti yazabiliriz, çok daha hızlı çalışır.")
    elif r.status_code in (401, 403):
        print(f"\nERIŞIM REDDEDILDI ({r.status_code})")
        print("Session cookie gerekli — Playwright şart.")
        print(f"Response: {r.text[:300]}")
    elif r.status_code == 429:
        print("\nRATE LIMIT (429) — Çok fazla istek.")
    else:
        print(f"Response: {r.text[:500]}")

except requests.exceptions.RequestException as e:
    print(f"Bağlantı hatası: {e}")
