# -*- coding: utf-8 -*-
"""
Scrapling ile Colruyt antibot testi.
Çalıştır: python colruyt_scrapling_test.py
"""
import sys, re, time
sys.stdout.reconfigure(encoding='utf-8')

URL = 'https://www.colruyt.be/nl/producten/alle-categorieen/zuivel/kaas'

print(f'Scrapling test başlıyor: {URL}')
print('DynamicFetcher (Playwright tabanlı, stealth)...')

try:
    from scrapling.fetchers import DynamicFetcher

    fetcher = DynamicFetcher(
        headless=True,
        network_idle=True,
    )

    page = fetcher.fetch(URL, timeout=30000)

    # Antibot tespiti
    title = page.find('title')
    title_text = title.text if title else ''
    print(f'Sayfa başlığı: {title_text}')

    if 'antibot' in title_text.lower() or 'bot' in title_text.lower():
        print('❌ AntiBot sayfası — DynamicFetcher yetmedi')
        print('PlayWrightFetcher ile tekrar deniyor...')
    else:
        print('✅ Normal sayfa yüklendi!')

    # Ürün kartlarını ara
    cards = page.find_all('a', class_='card--article')
    print(f'Kart sayısı: {len(cards)}')

    # Eğer kart varsa veri çek
    for card in cards[:3]:
        name = card.attrib.get('longname') or card.attrib.get('data-tms-product-name', '')
        price = card.attrib.get('data-tms-product-price', '')
        unit  = card.attrib.get('data-tms-product-unitprice', '')
        img_el = card.find('img')
        img = img_el.attrib.get('src', '') if img_el else ''
        print(f'  {name[:45]:<45} {price} EUR  unit={unit}  img={img[:50]}')

except Exception as e:
    print(f'DynamicFetcher hatası: {e}')

print()
print('StealthyFetcher deneniyor (HTTP, daha hızlı)...')
try:
    from scrapling.fetchers import StealthyFetcher

    fetcher2 = StealthyFetcher()
    page2 = fetcher2.fetch(URL)

    title2 = page2.find('title')
    print(f'Sayfa başlığı: {title2.text if title2 else "?"}')

    cards2 = page2.find_all('a', class_='card--article')
    print(f'Kart sayısı: {len(cards2)}')

except Exception as e:
    print(f'StealthyFetcher hatası: {e}')
