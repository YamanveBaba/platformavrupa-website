#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

BASE_DIR = Path(r'C:\Users\yaman\Desktop\04.01.2026\market_fiyat_cekici')

dosya1 = BASE_DIR / 'colruyt_kategori_cek.py'
if dosya1.exists():
    icerik = dosya1.read_text(encoding='utf-8')
    icerik = icerik.replace('"isAvailable": p.get("isAvailable", True),', 
        '"isAvailable": p.get("isAvailable", True),\n        "price": p.get("basicPrice"),\n        "promo_price": p.get("promoPrice"),\n        "promo_valid_from": None,\n        "promo_valid_until": None,')
    dosya1.write_text(icerik, encoding='utf-8')
    print('✅ Colruyt bitti')

dosya2 = BASE_DIR / 'carrefour_be_v2.py'
if dosya2.exists():
    icerik = dosya2.read_text(encoding='utf-8')
    icerik = icerik.replace('"imageUrl":', '"price": None,\n            "promo_price": None,\n            "promo_valid_from": None,\n            "promo_valid_until": None,\n            "imageUrl":')
    dosya2.write_text(icerik, encoding='utf-8')
    print('✅ Carrefour bitti')

dosya3 = BASE_DIR / 'lidl_be_mindshift_api_cek.py'
if dosya3.exists():
    icerik = dosya3.read_text(encoding='utf-8')
    icerik = icerik.replace('"unitContent": unit_content,', 
        '"unitContent": unit_content,\n        "imageUrl": "",\n        "price": None,\n        "promo_price": None,')
    dosya3.write_text(icerik, encoding='utf-8')
    print('✅ Lidl bitti')

print('✅ HEPSI BITTI')