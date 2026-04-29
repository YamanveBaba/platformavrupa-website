# -*- coding: utf-8 -*-
"""
urun_eslestir.py — Marketler arası ürün eşleştirme

Her ürüne match_group_id atar.
Aynı match_group_id = aynı ürün (farklı markette).

Eşleştirme mantığı:
  1. Branded: marka + tip + miktar -> tam eşleşme
     "Alpro Volle Melk 1L" ↔ "Alpro Volle Melk 1L" (farklı market)
  2. Own-brand: tip + miktar + özellik -> fonksiyonel eşdeğer
     "Milbona Volle Melk 1L" ↔ "Boni Volle Melk 1L" ↔ "Delhaize Volle Melk 1L"

Kullanım:
  python urun_eslestir.py            # tüm ürünleri eşleştir + DB'ye yaz
  python urun_eslestir.py --dry-run  # sadece istatistik, DB'ye yazma
  python urun_eslestir.py --test     # ilk 500 ürün ile test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests

SCRIPT_DIR = Path(__file__).parent
BATCH_SIZE = 500
FETCH_SIZE = 1000

# ── Birim normalizasyon tablosu ────────────────────────────────────────────────
BIRIM_MAP = {
    'liter': 'l', 'litre': 'l', 'lt': 'l',
    'cl': 'cl', 'dl': 'dl', 'ml': 'ml',
    'gram': 'g', 'gr': 'g', 'kg': 'kg', 'mg': 'mg',
    'stuks': 'st', 'stuk': 'st', 'pcs': 'st', 'pieces': 'st',
    'vel': 'st', 'zakjes': 'st', 'zakje': 'st',
    'rollen': 'st', 'rol': 'st',
    'portie': 'st', 'porties': 'st',
    'tablet': 'st', 'tabletten': 'st',
    'capsule': 'st', 'capsules': 'st',
}

# ── Dutch/French stopwords (eşleştirmeye katkısı yok) ─────────────────────────
STOPWORDS = {
    # Dutch
    'van', 'de', 'het', 'een', 'voor', 'met', 'zonder', 'en', 'of', 'in',
    'op', 'aan', 'bij', 'uit', 'over', 'door', 'naar', 'als', 'per', 'ook',
    'vers', 'verse', 'nieuwe', 'nieuw', 'extra', 'super', 'ultra', 'lekker',
    'lekkere', 'heerlijk', 'heerlijke', 'klein', 'kleine', 'groot', 'grote',
    'naturel', 'natural', 'nature', 'original', 'originale', 'classic',
    'premium', 'select', 'special', 'speciale', 'traditioneel', 'artisanaal',
    # French
    'le', 'la', 'les', 'du', 'des', 'un', 'une', 'et', 'ou', 'au', 'aux',
    'avec', 'sans', 'pour', 'sur', 'par', 'en', 'du',
}

# ── Karakter normalizasyonu ────────────────────────────────────────────────────
KARAKTER_MAP = str.maketrans(
    'àáâãäåæçèéêëìíîïðòóôõöùúûüýÿñ',
    'aaaaaaaceeeeiiiioooooouuuuyyn'
)


# ══════════════════════════════════════════════════════════════════════════════
# MİKTAR NORMALİZASYON
# ══════════════════════════════════════════════════════════════════════════════
def _to_float(s: str) -> float:
    return float(s.replace(',', '.'))


def miktar_normalize(text: str) -> Optional[str]:
    """
    "1 liter" / "500ml" / "6x100g" / "2 x 1L" -> standart string
    "1l", "500ml", "600g", "2l"
    None döner = miktar bulunamadı
    """
    if not text:
        return None
    t = text.lower().strip()
    t = t.translate(KARAKTER_MAP)

    birim_re = r'(?:ml|cl|dl|l|liter|litre|lt|g|gr|gram|kg|mg|st|stuks?|vel|rollen?|rol|pcs|pieces|portie[s]?|tablet[s]?|capsule[s]?)'

    # Çoklama: 6x100g | 6 x 100 g | 2x1l
    m = re.search(
        r'(\d+(?:[.,]\d+)?)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*(' + birim_re + r')',
        t
    )
    if m:
        count = _to_float(m.group(1))
        val   = _to_float(m.group(2))
        unit  = BIRIM_MAP.get(m.group(3), m.group(3))
        return _birim_formatla(count * val, unit)

    # Tek: 1L | 500 ml | 250g
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(' + birim_re + r')', t)
    if m:
        val  = _to_float(m.group(1))
        unit = BIRIM_MAP.get(m.group(2), m.group(2))
        return _birim_formatla(val, unit)

    return None


def _birim_formatla(val: float, unit: str) -> str:
    if unit in ('l', 'liter', 'litre', 'lt'):
        if val >= 1:
            s = f"{val:.4g}l"
        else:
            s = f"{int(round(val * 1000))}ml"
        return s
    if unit == 'ml':
        if val >= 1000:
            return f"{val/1000:.4g}l"
        return f"{int(val)}ml"
    if unit == 'cl':
        ml = val * 10
        return f"{int(ml)}ml" if ml < 1000 else f"{ml/1000:.4g}l"
    if unit == 'dl':
        ml = val * 100
        return f"{int(ml)}ml" if ml < 1000 else f"{ml/1000:.4g}l"
    if unit in ('g', 'gram', 'gr'):
        if val >= 1000:
            return f"{val/1000:.4g}kg"
        return f"{int(val)}g"
    if unit == 'kg':
        return f"{val:.4g}kg"
    if unit == 'mg':
        return f"{int(val)}mg"
    if unit == 'st':
        return f"{int(val)}st"
    return f"{val:.4g}{unit}"


# ══════════════════════════════════════════════════════════════════════════════
# İSİM NORMALİZASYON
# ══════════════════════════════════════════════════════════════════════════════
def isim_normalize(name: str, brand: str = '') -> str:
    """
    Ürün isminden marka + stopwords + miktar + özel karakter kaldır.
    Kalan kelimeler alfabetik sıraya sokulur.
    "Milbona Volle Melk" -> "melk volle"
    "Boni Selection Volle Melk" -> "melk volle"
    Aynı sonuç -> aynı match group!
    """
    text = (name or '').lower()
    text = text.translate(KARAKTER_MAP)

    # Marka kaldır
    if brand:
        bl = brand.lower().translate(KARAKTER_MAP)
        # Tam marka
        text = text.replace(bl, ' ')
        # Marka içindeki tek kelimeler (3+ harf)
        for word in re.split(r'\W+', bl):
            if len(word) >= 3:
                text = re.sub(r'\b' + re.escape(word) + r'\b', ' ', text)

    # Miktar ifadelerini kaldır
    birim_re = r'(?:ml|cl|dl|l|liter|litre|lt|g|gr|gram|kg|mg|st|stuks?|vel|rollen?|pcs|portie[s]?|tablet[s]?|capsule[s]?)'
    text = re.sub(r'\d+(?:[.,]\d+)?\s*[xX]\s*\d+(?:[.,]\d+)?\s*' + birim_re, ' ', text)
    text = re.sub(r'\d+(?:[.,]\d+)?\s*' + birim_re, ' ', text)
    text = re.sub(r'\b\d+\b', ' ', text)

    # Noktalama / özel karakterler
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'_', ' ', text)

    # Kelimeleri filtrele: min 3 harf, stopword değil
    words = [
        w for w in text.split()
        if len(w) >= 3 and w not in STOPWORDS
    ]

    # Alfabetik sırala — "melk volle" == "volle melk"
    words.sort()
    return ' '.join(words)


# ══════════════════════════════════════════════════════════════════════════════
# MATCH GROUP ID
# ══════════════════════════════════════════════════════════════════════════════
def match_group_id_hesapla(name: str, brand: str, unit_or_content: str) -> str:
    """
    Ürünün eşleştirme anahtarını hesapla.
    Aynı key -> aynı ürün (farklı market).

    Sadece normalize edilmiş isim kullanılır.
    Miktar (qty) key'e dahil edilmez çünkü:
    - Delhaize/Lidl/ALDI/Carrefour ürünlerinin %75-93'ünde qty verisi yok
    - qty|norm key'i kullansak eşleşme sayısı dramatik düşüyor (~552)
    - Boyut farkı (400g vs 750g) UI'da gösterilen fiyattan zaten anlaşılır
    """
    norm = isim_normalize(name or '', brand or '')

    if not norm or len(norm) < 4:
        return ''  # Çok kısa/anlamsız — eşleştirme yok

    return 'mg' + hashlib.md5(norm.encode('utf-8')).hexdigest()[:14]


# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE BAĞLANTISI
# ══════════════════════════════════════════════════════════════════════════════
def load_secrets() -> tuple[str, str]:
    url = os.environ.get('SUPABASE_URL', '').strip()
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if url and key:
        return url.rstrip('/'), key

    path = SCRIPT_DIR / 'supabase_import_secrets.txt'
    if not path.exists():
        print('HATA: supabase_import_secrets.txt bulunamadı.')
        sys.exit(1)
    lines = [l.strip() for l in path.read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.strip().startswith('#')]
    if len(lines) < 2:
        print('HATA: supabase_import_secrets.txt — 1. satır URL, 2. satır key olmalı.')
        sys.exit(1)
    return lines[0].rstrip('/'), lines[1]


def fetch_all_products(url: str, key: str) -> list[dict]:
    """Tüm ürünleri Supabase'den çek (sadece eşleştirme için gereken alanlar)."""
    endpoint = f"{url}/rest/v1/market_chain_products"
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Range-Unit': 'items',
    }
    params_base = {
        'select': 'id,chain_slug,external_product_id,name,brand,unit_or_content',
        'order': 'id.asc',
    }

    all_rows = []
    offset   = 0
    print('Supabase\'den ürünler çekiliyor...')
    while True:
        params = {**params_base, 'limit': FETCH_SIZE, 'offset': offset}
        r = requests.get(endpoint, headers=headers, params=params, timeout=60)
        if r.status_code not in (200, 206):
            print(f'HATA HTTP {r.status_code}: {r.text[:300]}')
            sys.exit(1)
        batch = r.json()
        if not batch:
            break
        all_rows.extend(batch)
        print(f'  {len(all_rows)} ürün alındı...')
        if len(batch) < FETCH_SIZE:
            break
        offset += FETCH_SIZE
    return all_rows


def update_match_groups(url: str, key: str, products: list[dict],
                         multi_market_groups: dict[str, list], dry_run: bool) -> int:
    """
    match_group_id alanını Supabase'e yaz.
    Strateji: PATCH kullan (upsert değil — upsert NOT NULL constraint ihlali yaratır).
    1. Tüm match_group_id'leri NULL yap (temiz başlangıç)
    2. Cross-market gruplar için PATCH ile GID yaz
    """
    # GID -> [product id list] (sadece cross-market gruplar için)
    gid_to_ids: dict[str, list] = defaultdict(list)
    for p in products:
        gid = match_group_id_hesapla(
            p.get('name') or '', p.get('brand') or '', p.get('unit_or_content') or '')
        if gid and gid in multi_market_groups:
            gid_to_ids[gid].append(p['id'])

    total_to_write = sum(len(v) for v in gid_to_ids.values())

    if dry_run:
        print(f'[DRY-RUN] {len(gid_to_ids)} cross-market GID, {total_to_write} urun yazilacakti.')
        if gid_to_ids:
            sample_gid = next(iter(gid_to_ids))
            print(f'  Ornek GID={sample_gid}, product_ids={gid_to_ids[sample_gid][:3]}...')
        return 0

    endpoint = f"{url}/rest/v1/market_chain_products"
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }

    # 1. Tüm mevcut match_group_id'leri temizle
    print('Mevcut match_group_id\'ler temizleniyor...')
    r = requests.patch(f"{endpoint}?id=gt.0", headers=headers,
                       json={"match_group_id": None}, timeout=60)
    if r.status_code not in (200, 204):
        print(f'HATA (temizleme) HTTP {r.status_code}: {r.text[:200]}')
        return 0
    print('  Temizlendi.')

    # 2. Cross-market GID'leri PATCH ile yaz
    written = 0
    gid_count = 0
    for gid, ids in gid_to_ids.items():
        for i in range(0, len(ids), BATCH_SIZE):
            batch = ids[i:i + BATCH_SIZE]
            id_list = ','.join(str(x) for x in batch)
            r = requests.patch(
                f"{endpoint}?id=in.({id_list})",
                headers=headers,
                json={"match_group_id": gid},
                timeout=60,
            )
            if r.status_code not in (200, 204):
                print(f'HATA HTTP {r.status_code}: {r.text[:200]}')
                return written
            written += len(batch)
        gid_count += 1
        if gid_count % 100 == 0:
            print(f'  {gid_count}/{len(gid_to_ids)} GID islendi, {written} urun...')
    return written


# ══════════════════════════════════════════════════════════════════════════════
# ANA MANTIK
# ══════════════════════════════════════════════════════════════════════════════
def debug_analysis(products: list[dict]) -> None:
    """Eşleşme kalitesini incele: dil dağılımı, qty coverage, market çiftleri."""
    from collections import Counter

    print('\n== DEBUG ANALIZ ===========================================')

    # 1. Market başına ürün sayısı
    by_chain: dict[str, list[dict]] = defaultdict(list)
    for p in products:
        by_chain[p['chain_slug']].append(p)
    print('\n[1] Market başına ürün sayısı:')
    for chain, prods in sorted(by_chain.items()):
        print(f'  {chain:<20} : {len(prods):>6,}')

    # 2. Qty coverage
    print('\n[2] Miktar (qty) bulunabilen ürün oranı:')
    for chain, prods in sorted(by_chain.items()):
        has_qty = sum(
            1 for p in prods
            if miktar_normalize(p.get('unit_or_content') or '')
            or miktar_normalize(p.get('name') or '')
        )
        print(f'  {chain:<20} : {has_qty:>6,} / {len(prods):,} ({100*has_qty//max(len(prods),1)}%)')

    # 3. İsim normalizasyon örnekleri (her marketten 5)
    print('\n[3] Normalizasyon örnekleri (her marketten 5):')
    for chain, prods in sorted(by_chain.items()):
        print(f'\n  -- {chain} --')
        for p in prods[:5]:
            norm = isim_normalize(p.get('name') or '', p.get('brand') or '')
            qty  = (miktar_normalize(p.get('unit_or_content') or '')
                    or miktar_normalize(p.get('name') or '') or 'q?')
            print(f'    {(p.get("name") or "")[:45]:<46} => norm="{norm}" qty={qty}')

    # 4. İsim-bazlı (qty yoksay) cross-market grup sayısı
    name_groups: dict[str, list[str]] = defaultdict(list)
    for p in products:
        norm = isim_normalize(p.get('name') or '', p.get('brand') or '')
        if norm and len(norm) >= 4:
            name_groups[norm].append(p['chain_slug'])
    name_cross = {k: v for k, v in name_groups.items() if len(set(v)) >= 2}
    print(f'\n[4] Sadece isme göre (qty yoksayılırsa) cross-market grup: {len(name_cross):,}')

    # 5. Market çiftleri arası eşleşme (qty dahil)
    gid_chains: dict[str, set[str]] = defaultdict(set)
    for p in products:
        gid = match_group_id_hesapla(
            p.get('name') or '', p.get('brand') or '', p.get('unit_or_content') or '')
        if gid:
            gid_chains[gid].add(p['chain_slug'])
    pairs: Counter = Counter()
    for chains in gid_chains.values():
        cl = sorted(chains)
        for i in range(len(cl)):
            for j in range(i+1, len(cl)):
                pairs[f'{cl[i]} <-> {cl[j]}'] += 1
    print('\n[5] Market çiftleri arası eşleşme (qty+isim):')
    for pair, cnt in pairs.most_common(20):
        print(f'  {pair:<45} : {cnt:>5,}')

    # 6. En çok eşleşen isim-bazlı gruplardan örnekler (Carrefour vs diğer)
    print('\n[6] İsim-bazlı eşleşen ama qty farklı olan gruplar (örnek 10):')
    shown = 0
    for norm, slugs in name_cross.items():
        if shown >= 10:
            break
        # qty'leri topla
        qtys_by_chain: dict[str, set[str]] = defaultdict(set)
        for p in products:
            pnorm = isim_normalize(p.get('name') or '', p.get('brand') or '')
            if pnorm == norm:
                qty = (miktar_normalize(p.get('unit_or_content') or '')
                       or miktar_normalize(p.get('name') or '') or 'q?')
                qtys_by_chain[p['chain_slug']].add(qty)
        if len(set(slugs)) >= 2:
            print(f'  norm="{norm}"')
            for chain, qtys in sorted(qtys_by_chain.items()):
                print(f'    {chain:<20} qty={sorted(qtys)}')
            shown += 1

    print('\n== DEBUG BITTI ==========================================\n')


def main():
    ap = argparse.ArgumentParser(description='Marketler arası ürün eşleştirme')
    ap.add_argument('--dry-run', action='store_true',
                    help='Hesapla ama DB\'ye yazma')
    ap.add_argument('--test', action='store_true',
                    help='İlk 500 ürün ile test et')
    ap.add_argument('--stats', action='store_true',
                    help='Sadece istatistik göster, yazma')
    ap.add_argument('--debug', action='store_true',
                    help='Derin debug analizi: dil, qty coverage, market çiftleri')
    args = ap.parse_args()

    url, key = load_secrets()
    print(f'Supabase: {url[:40]}...\n')

    # Ürünleri çek
    products = fetch_all_products(url, key)
    if args.test:
        products = products[:500]
        print(f'TEST modu: {len(products)} ürün\n')
    else:
        print(f'Toplam: {len(products)} ürün\n')

    # Her ürüne match_group_id hesapla
    print('Match group ID hesaplanıyor...')
    group_counter: dict[str, list[str]] = defaultdict(list)  # gid -> [chain_slug, ...]
    no_gid = 0

    for p in products:
        gid = match_group_id_hesapla(
            p.get('name') or '',
            p.get('brand') or '',
            p.get('unit_or_content') or '',
        )
        if gid:
            group_counter[gid].append(p['chain_slug'])
        else:
            no_gid += 1

    # İstatistikler
    multi_market_groups = {
        gid: slugs for gid, slugs in group_counter.items()
        if len(set(slugs)) >= 2
    }
    total_matched = sum(len(v) for v in multi_market_groups.values())

    print(f'\n== Eslestirme Istatistikleri ===========================')
    print(f'  Toplam urun          : {len(products):,}')
    print(f'  GID atanan           : {len(products) - no_gid:,}')
    print(f'  GID atanamayan       : {no_gid:,}  (isim cok kisa/belirsiz)')
    print(f'  Benzersiz grup       : {len(group_counter):,}')
    print(f'  2+ markette grup     : {len(multi_market_groups):,}')
    print(f'  2+ markette urun     : {total_matched:,}')

    # En çok eşleşen grupları göster
    print(f'\n== En Iyi Eslesmeler (ornek) ==========================')
    top = sorted(multi_market_groups.items(),
                 key=lambda x: len(set(x[1])), reverse=True)[:15]

    # Ürün isimlerini grup ID'ye göre bul
    gid_to_name: dict[str, str] = {}
    for p in products:
        gid = match_group_id_hesapla(
            p.get('name') or '',
            p.get('brand') or '',
            p.get('unit_or_content') or '',
        )
        if gid and gid not in gid_to_name:
            gid_to_name[gid] = f"{(p.get('name') or '')[:50]} ({(p.get('unit_or_content') or '')[:15]})"

    for gid, slugs in top:
        markets = sorted(set(slugs))
        name_ex = gid_to_name.get(gid, gid)
        print(f'  [{len(markets)} market] {name_ex}')
        print(f'    -> {", ".join(markets)}')

    if args.debug:
        debug_analysis(products)

    if args.stats or args.dry_run:
        if args.dry_run:
            update_match_groups(url, key, products, multi_market_groups, dry_run=True)
        print('\nSadece istatistik/dry-run -- DB degistirilmedi.')
        return

    # DB'ye yaz
    print(f'\n== Supabase Yazimi =====================================')
    written = update_match_groups(url, key, products, multi_market_groups, dry_run=False)
    print(f'\nTAMAM: {written:,} urun guncellendi.')
    print(f'  {len(multi_market_groups):,} grup, {total_matched:,} urun eslesti.')


if __name__ == '__main__':
    main()
