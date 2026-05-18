# -*- coding: utf-8 -*-
"""
Yumurta fiyat güncelleme scripti.
Kullanım: 3 gün sonra sayfaları tekrar D:\MARKET\YUMURTALAR\ klasörüne kaydet (Ctrl+S),
ardından bu scripti çalıştır.

    python yumurta_guncelle.py

Script:
  1. Yeni HTML'leri parse eder (tam_veri_cek.py'nin parse fonksiyonlarını kullanır)
  2. Mevcut veriyle karşılaştırır
  3. Fiyat değişikliklerini geçmişe yazar
  4. market.html'deki YUMURTA_DATA'yı günceller
"""

import sys, re, json, os
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

MARKET_HTML  = Path("C:/Users/yaman/Desktop/platformavrupa-website/market.html")
HISTORIEK    = Path("D:/MARKET/yumurta_historiek.json")
WEB_DATA     = Path("D:/MARKET/yumurta_web_data.json")
BUGÜN        = date.today().isoformat()

# tam_veri_cek.py'yi import et
sys.path.insert(0, str(Path(__file__).parent))
from tam_veri_cek import parse_colruyt, parse_aldi, parse_carrefour, parse_delhaize, parse_lidl, is_yumurta, kategori

# ── Veri çek ──────────────────────────────────────────────────────────────────
def yeni_veri_cek():
    """D:\MARKET\YUMURTALAR'daki güncel HTML'leri parse et."""
    all_new = []
    parsers = [('COLRUYT', parse_colruyt), ('ALDI', parse_aldi),
               ('CARREFOUR', parse_carrefour), ('DELHAIZE', parse_delhaize),
               ('LIDL', parse_lidl)]
    for market_name, fn in parsers:
        try:
            items = fn()
            print(f"  [{market_name}] {len(items)} ürün çekildi")
            all_new.extend(items)
        except Exception as e:
            print(f"  [{market_name}] HATA: {e}")
    return all_new

# ── Eşleştirme anahtarı ───────────────────────────────────────────────────────
def urun_key(u):
    """Ürünü benzersiz şekilde tanımla: market + normalize isim."""
    isim = (u.get('name') or u.get('isim') or '').lower().strip()
    isim = re.sub(r'\s+', ' ', isim)
    return f"{u.get('chain_slug','')}|{isim}"

# ── Karşılaştır ve güncelle ───────────────────────────────────────────────────
def karsilastir_ve_guncelle(mevcut_liste, yeni_liste):
    """
    mevcut_liste: market.html'deki mevcut YUMURTA_DATA listesi
    yeni_liste:   yeni parse edilen ürünler
    Döner: (güncellenmiş_liste, rapor_dict)
    """
    # Mevcut ürünleri key → index map
    mevcut_map = {urun_key(u): i for i, u in enumerate(mevcut_liste)}
    yeni_map   = {urun_key(u): u for u in yeni_liste}

    rapor = {
        'fiyat_degisen': [],
        'yeni_eklenen':  [],
        'kayboldu':      [],
        'degismedi':     0,
    }

    guncel = [dict(u) for u in mevcut_liste]

    # 1. Mevcut ürünleri güncelle
    for key, u_yeni in yeni_map.items():
        yeni_fiyat = u_yeni.get('price') or u_yeni.get('fiyat')
        yeni_unit  = u_yeni.get('_unit_fiyat')

        if key in mevcut_map:
            idx = mevcut_map[key]
            u   = guncel[idx]
            eski_fiyat = u.get('price')

            # price_history başlat
            if 'price_history' not in u:
                u['price_history'] = []

            if yeni_fiyat and eski_fiyat and abs(float(yeni_fiyat) - float(eski_fiyat)) > 0.005:
                # Fiyat değişti
                u['price_history'].append({'date': BUGÜN, 'price': eski_fiyat})
                u['price'] = yeni_fiyat
                if yeni_unit: u['_unit_fiyat'] = yeni_unit
                u['last_seen'] = BUGÜN
                u['unavailable'] = False
                rapor['fiyat_degisen'].append({
                    'isim':   u.get('name'),
                    'market': u.get('chain_slug'),
                    'eski':   eski_fiyat,
                    'yeni':   yeni_fiyat,
                    'fark':   round(float(yeni_fiyat) - float(eski_fiyat), 2),
                })
            else:
                u['last_seen'] = BUGÜN
                u['unavailable'] = False
                rapor['degismedi'] += 1
        else:
            # Yeni ürün
            yeni_u = {
                'chain_slug':    u_yeni.get('chain_slug'),
                'name':          u_yeni.get('name') or u_yeni.get('isim'),
                'name_tr':       None,
                'price':         yeni_fiyat,
                'promo_price':   u_yeni.get('promo_price'),
                'currency':      'EUR',
                'in_promo':      u_yeni.get('in_promo', False),
                'promo_valid_until': None,
                'unit_or_content': u_yeni.get('unit_or_content',''),
                'image_url':     u_yeni.get('image_url',''),
                '_unit_fiyat':   yeni_unit,
                'kategori':      u_yeni.get('kategori','normal'),
                'brand':         u_yeni.get('brand',''),
                'price_history': [],
                'last_seen':     BUGÜN,
                'unavailable':   False,
            }
            guncel.append(yeni_u)
            rapor['yeni_eklenen'].append({
                'isim': yeni_u['name'], 'market': yeni_u['chain_slug'], 'fiyat': yeni_fiyat
            })

    # 2. Kayboldu mu?
    for key, idx in mevcut_map.items():
        if key not in yeni_map:
            u = guncel[idx]
            if not u.get('unavailable'):
                u['unavailable'] = True
                rapor['kayboldu'].append({
                    'isim': u.get('name'), 'market': u.get('chain_slug')
                })

    return guncel, rapor

# ── Rapor yazdır ──────────────────────────────────────────────────────────────
def rapor_yazdir(rapor, eski_sayi, yeni_sayi):
    print(f"\n{'='*55}")
    print(f"  GÜNCELLEME RAPORU — {BUGÜN}")
    print(f"{'='*55}")
    print(f"  Toplam ürün: {eski_sayi} → {yeni_sayi}")
    print(f"  Değişmeyen : {rapor['degismedi']}")

    if rapor['fiyat_degisen']:
        print(f"\n  FİYAT DEĞİŞİKLİKLERİ ({len(rapor['fiyat_degisen'])}):")
        for d in sorted(rapor['fiyat_degisen'], key=lambda x: x['fark']):
            yon = '+' if d['fark'] > 0 else ''
            print(f"    {d['market']:<15} {d['isim'][:38]:<38}  {d['eski']:.2f} → {d['yeni']:.2f} ({yon}{d['fark']:.2f}€)")
    else:
        print("\n  Fiyat değişikliği: YOK")

    if rapor['yeni_eklenen']:
        print(f"\n  YENİ ÜRÜNLER ({len(rapor['yeni_eklenen'])}):")
        for u in rapor['yeni_eklenen']:
            print(f"    {u['market']:<15} {u['isim'][:38]}  {u['fiyat']} EUR")

    if rapor['kayboldu']:
        print(f"\n  SAYFADAN KALKAN ({len(rapor['kayboldu'])}) — silinmedi, unavailable=true:")
        for u in rapor['kayboldu']:
            print(f"    {u['market']:<15} {u['isim'][:38]}")

    print(f"\n{'='*55}")

# ── market.html'i güncelle ────────────────────────────────────────────────────
def market_html_guncelle(guncel_liste):
    # Sadece available ürünleri göster (unavailable=true olanları filtrele)
    goster = [u for u in guncel_liste if not u.get('unavailable')]
    json_str = json.dumps(goster, ensure_ascii=False, separators=(',',':'))

    with open(MARKET_HTML, encoding='utf-8') as f:
        html = f.read()

    html = re.sub(r'<script>const YUMURTA_DATA=\[.*?\];</script>\n?', '', html, flags=re.DOTALL)
    html = html.replace('</body>', f'<script>const YUMURTA_DATA={json_str};</script>\n</body>')

    with open(MARKET_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  market.html güncellendi ({len(goster)} ürün gösteriliyor)")

# ── Ana ───────────────────────────────────────────────────────────────────────
def main():
    print("=== YUMURTA FİYAT GÜNCELLEME ===\n")

    # 1. Yeni veriyi çek
    print("Yeni HTML'ler parse ediliyor...")
    yeni_liste = yeni_veri_cek()
    print(f"  Toplam: {len(yeni_liste)} ürün\n")

    # 2. Mevcut veriyi yükle
    if WEB_DATA.exists():
        with open(WEB_DATA, encoding='utf-8') as f:
            mevcut_liste = json.load(f)
        print(f"Mevcut veri: {len(mevcut_liste)} ürün")
    else:
        print("Mevcut veri yok — ilk çalıştırma")
        mevcut_liste = []

    # 3. Karşılaştır
    guncel_liste, rapor = karsilastir_ve_guncelle(mevcut_liste, yeni_liste)

    # 4. Raporu yazdır
    rapor_yazdir(rapor, len(mevcut_liste), len(guncel_liste))

    # 5. Kaydet
    with open(WEB_DATA, 'w', encoding='utf-8') as f:
        json.dump(guncel_liste, f, ensure_ascii=False, indent=2)
    print(f"\n  yumurta_web_data.json kaydedildi ({len(guncel_liste)} ürün)")

    # 6. Geçmiş dosyasına ekle
    historiek = []
    if HISTORIEK.exists():
        with open(HISTORIEK, encoding='utf-8') as f:
            historiek = json.load(f)
    historiek.append({'date': BUGÜN, 'degisiklikler': rapor['fiyat_degisen']})
    with open(HISTORIEK, 'w', encoding='utf-8') as f:
        json.dump(historiek, f, ensure_ascii=False, indent=2)

    # 7. market.html güncelle
    market_html_guncelle(guncel_liste)

if __name__ == '__main__':
    main()
