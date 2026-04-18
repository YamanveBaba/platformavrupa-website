# -*- coding: utf-8 -*-
"""
name_tr alanındaki sorunları DB'de temizler:
1. \n ile çift yazılmış metinleri kırpar (ilk satırı al)
2. Sadece nokta/boşluk/tire içerenleri NULL yap (çeviride bozulmuş)
3. 2 karakterden kısa olanları NULL yap
4. Giriş/çıkış boşluklarını temizle
Sonuç: kullanıcıya yanlış çeviri yerine doğru Hollandaca isim gösterilir
"""
from __future__ import annotations
import os, sys, re, time
try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH = 200  # kaç kayıt bir seferde güncellenir

def load_secrets():
    url = os.environ.get("SUPABASE_URL","").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY","").strip()
    if url and key:
        return url.rstrip("/"), key
    path = os.path.join(SCRIPT_DIR, "supabase_import_secrets.txt")
    lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
             if l.strip() and not l.strip().startswith("#")]
    return lines[0].rstrip("/"), lines[1]

def is_bozuk(name_tr: str) -> bool:
    """Çeviri bozuksa True döner → NULL yapılacak"""
    t = name_tr.strip()
    if len(t) < 3:
        return True
    # Sadece nokta/boşluk/tire karışımı: ". . . ." veya "Deo ."
    # Temiz metinden nokta/boşluk/harf oranı: nokta sayısı > harf sayısı ise bozuk
    letters = len(re.sub(r'[^a-zA-ZğüşöçıİĞÜŞÖÇ]', '', t))
    dots    = t.count('.')
    if dots >= 3 and letters < dots * 2:
        return True
    return False

def clean_name_tr(name_tr: str) -> str | None:
    """name_tr'yi temizle. Bozuksa None döner."""
    if not name_tr:
        return None
    # \n ile çift yazılmış → ilk satırı al
    t = name_tr.split('\n')[0].strip()
    # Çok sayıda boşluk temizle
    t = re.sub(r'  +', ' ', t)
    if is_bozuk(t):
        return None
    return t if t != name_tr.split('\n')[0].strip() or t != name_tr else t

def main():
    sb_url, sb_key = load_secrets()
    headers = {
        "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }
    base = f"{sb_url}/rest/v1/market_chain_products"

    # Tüm market'lerden name_tr dolu kayıtları çek (offset ile)
    print("name_tr kayıtları taranıyor...")
    offset = 0
    limit  = 1000
    guncellenen = 0
    nulllanan   = 0

    while True:
        r = requests.get(base,
            params={"select":"id,name_tr","name_tr":"not.is.null",
                    "limit": str(limit), "offset": str(offset)},
            headers=headers, timeout=30)
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            break

        to_fix_clean = []  # (id, new_val)
        to_fix_null  = []  # id list

        for row in rows:
            nt = row.get("name_tr") or ""
            if not nt:
                continue
            cleaned = clean_name_tr(nt)
            if cleaned is None:
                to_fix_null.append(row["id"])
            elif cleaned != nt:
                to_fix_clean.append((row["id"], cleaned))

        # NULL güncelle — tek tek PATCH (Supabase REST limitation)
        for row_id in to_fix_null:
            rp = requests.patch(f"{base}?id=eq.{row_id}",
                json={"name_tr": None},
                headers={**headers, "Prefer": "return=minimal"}, timeout=15)
            if rp.status_code in (200,204):
                nulllanan += 1
            time.sleep(0.01)

        # Temizlenmiş güncelle
        for row_id, new_val in to_fix_clean:
            rp = requests.patch(f"{base}?id=eq.{row_id}",
                json={"name_tr": new_val},
                headers={**headers, "Prefer": "return=minimal"}, timeout=15)
            if rp.status_code in (200,204):
                guncellenen += 1
            time.sleep(0.01)

        offset += limit
        print(f"  offset={offset} | temizlenen={guncellenen} | null={nulllanan}")
        if len(rows) < limit:
            break

    print(f"\nBitti. Temizlenen: {guncellenen}, NULL yapılan: {nulllanan}")

if __name__ == "__main__":
    main()
