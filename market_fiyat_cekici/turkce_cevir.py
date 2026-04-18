# -*- coding: utf-8 -*-
"""
Supabase'deki market_chain_products tablosundaki ürün isimlerini
Hollandaca'dan Türkçe'ye çevirir ve name_tr kolonuna yazar.

Kullanım:
  python turkce_cevir.py                    # Tüm marketi çevir (name_tr IS NULL)
  python turkce_cevir.py --zincir aldi      # Sadece Aldi ürünleri
  python turkce_cevir.py --limit 100        # En fazla 100 ürün (test)
  python turkce_cevir.py --dry-run          # Çeviriyi yap ama DB'ye yazma

Motor: argostranslate (tamamen offline, rate limit yok, ücretsiz)
Pivot: Hollandaca (nl) → İngilizce (en) → Türkçe (tr)

Kurulum (bir kez çalıştır):
  pip install argostranslate
  python turkce_cevir.py --kur-modeller

Önkoşul:
  Supabase SQL Editor'da bir kez çalıştır:
    ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS name_tr TEXT;
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_SIZE  = 200   # Kaç ürünü bir seferde DB'den çek
SAVE_EVERY  = 200   # Kaç çeviriden sonra DB'ye yaz
TRANS_BATCH = 50    # argostranslate'e kaç ürün tek seferde ver

# ─── SUPABASE CREDENTIALS ─────────────────────────────────────────────────────

def _clean(line: str, is_url: bool) -> str:
    s = line.strip().strip("\ufeff").strip('"').strip("'")
    prefix = "SUPABASE_URL=" if is_url else "SUPABASE_SERVICE_ROLE_KEY="
    if s.upper().startswith(prefix.upper()):
        s = s.split("=", 1)[1].strip()
    if not is_url and s.lower().startswith("bearer "):
        s = s[6:].strip()
    return s

def load_secrets() -> tuple[str, str]:
    url = _clean(os.environ.get("SUPABASE_URL", ""), is_url=True)
    key = _clean(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""), is_url=False)
    if url and key:
        return url.rstrip("/"), key
    path = os.path.join(SCRIPT_DIR, "supabase_import_secrets.txt")
    if not os.path.isfile(path):
        print(f"HATA: {path} bulunamadı ve ortam değişkenleri yok.")
        sys.exit(1)
    lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
             if l.strip() and not l.strip().startswith("#")]
    if len(lines) < 2:
        print("HATA: supabase_import_secrets.txt → 1. satır URL, 2. satır service_role key")
        sys.exit(1)
    return _clean(lines[0], is_url=True).rstrip("/"), _clean(lines[1], is_url=False)

# ─── SUPABASE HELPERS ─────────────────────────────────────────────────────────

def fetch_batch(url: str, key: str, zincir: str | None, offset: int) -> list[dict]:
    """name_tr IS NULL olan ürünleri sayfalı çek."""
    endpoint = f"{url}/rest/v1/market_chain_products"
    params = {
        "select": "id,name,chain_slug",
        "name_tr": "is.null",
        "order": "id.asc",
        "limit": str(BATCH_SIZE),
        "offset": str(offset),
    }
    if zincir:
        params["chain_slug"] = f"ilike.{zincir}*"
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    r = requests.get(endpoint, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def count_pending(url: str, key: str, zincir: str | None) -> int:
    endpoint = f"{url}/rest/v1/market_chain_products"
    params = {"select": "id", "name_tr": "is.null"}
    if zincir:
        params["chain_slug"] = f"ilike.{zincir}*"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    r = requests.get(endpoint, params=params, headers=headers, timeout=30)
    cr = r.headers.get("Content-Range", "")
    m = re.search(r"/(\d+)", cr)
    return int(m.group(1)) if m else 0

def save_batch(url: str, key: str, rows: list[dict], dry_run: bool):
    if dry_run:
        print(f"  [dry-run] {len(rows)} satır yazılacaktı.")
        return
    endpoint = f"{url}/rest/v1/market_chain_products"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    errors = 0
    for row in rows:
        resp = requests.patch(
            endpoint + f"?id=eq.{row['id']}",
            json={"name_tr": row["name_tr"]},
            headers=headers,
            timeout=30,
        )
        if resp.status_code not in (200, 204):
            errors += 1
    if errors:
        print(f"  UYARI: {errors}/{len(rows)} satır yazılamadı.")
    else:
        print(f"  DB'ye {len(rows)} satır yazıldı.")

# ─── YEREL SÖZLÜK ─────────────────────────────────────────────────────────────

LOCAL_DICT: dict[str, str] = {
    "melk": "süt", "volle melk": "tam yağlı süt", "halfvolle melk": "yarım yağlı süt",
    "boter": "tereyağı", "kaas": "peynir", "eieren": "yumurta", "yoghurt": "yoğurt",
    "brood": "ekmek", "witbrood": "beyaz ekmek", "volkoren": "tam buğday",
    "vlees": "et", "kip": "tavuk", "rund": "sığır", "varken": "domuz",
    "vis": "balık", "zalm": "somon", "garnalen": "karides",
    "groenten": "sebze", "fruit": "meyve", "appel": "elma", "peer": "armut",
    "banaan": "muz", "tomaat": "domates", "ui": "soğan", "aardappel": "patates",
    "rijst": "pirinç", "pasta": "makarna", "meel": "un",
    "suiker": "şeker", "zout": "tuz", "peper": "biber", "azijn": "sirke",
    "olie": "yağ", "olijfolie": "zeytinyağı",
    "koffie": "kahve", "thee": "çay", "sap": "meyve suyu", "water": "su",
    "bier": "bira", "wijn": "şarap",
    "chips": "cips", "koeken": "kurabiye", "chocolade": "çikolata",
    "soep": "çorba", "saus": "sos",
    "waspoeder": "çamaşır deterjanı", "shampoo": "şampuan",
    "tandpasta": "diş macunu", "zeep": "sabun",
}

def local_translate(name: str) -> str | None:
    lower = name.lower().strip()
    if lower in LOCAL_DICT:
        return LOCAL_DICT[lower]
    words = lower.split()
    translated = [LOCAL_DICT.get(w, w) for w in words]
    if any(translated[i] != words[i] for i in range(len(words))):
        return " ".join(translated)
    return None

# ─── ARGOSTRANSLATE ───────────────────────────────────────────────────────────

def kur_modeller():
    """nl→en ve en→tr modellerini indir (bir kez çalıştır)."""
    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError:
        print("HATA: pip install argostranslate")
        sys.exit(1)

    print("Mevcut paketler güncelleniyor...")
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()

    hedefler = [("nl", "en"), ("en", "tr")]
    for from_code, to_code in hedefler:
        pkg = next(
            (p for p in available if p.from_code == from_code and p.to_code == to_code),
            None
        )
        if pkg is None:
            print(f"UYARI: {from_code}→{to_code} paketi bulunamadı.")
            continue
        installed = argostranslate.package.get_installed_packages()
        already = any(p.from_code == from_code and p.to_code == to_code for p in installed)
        if already:
            print(f"  {from_code}→{to_code}: zaten kurulu.")
        else:
            print(f"  {from_code}→{to_code} indiriliyor (~150MB)...")
            argostranslate.package.install_from_path(pkg.download())
            print(f"  {from_code}→{to_code}: kuruldu.")

    print("\nModeller hazır. Şimdi çalıştırabilirsin:\n  python turkce_cevir.py\n")


def _get_translator():
    """nl→en ve en→tr çeviricilerini döndür."""
    try:
        import argostranslate.translate
    except ImportError:
        print("HATA: pip install argostranslate")
        sys.exit(1)

    installed = argostranslate.translate.get_installed_languages()
    lang_map = {lang.code: lang for lang in installed}

    nl = lang_map.get("nl")
    en = lang_map.get("en")
    tr = lang_map.get("tr")

    missing = []
    if not nl: missing.append("nl (Hollandaca)")
    if not en: missing.append("en (İngilizce)")
    if not tr: missing.append("tr (Türkçe)")
    if missing:
        print(f"HATA: Şu modeller eksik: {', '.join(missing)}")
        print("Çalıştır: python turkce_cevir.py --kur-modeller")
        sys.exit(1)

    nl_en = nl.get_translation(en)
    en_tr = en.get_translation(tr)

    if not nl_en or not en_tr:
        print("HATA: nl→en veya en→tr çeviri paketi yüklü değil.")
        print("Çalıştır: python turkce_cevir.py --kur-modeller")
        sys.exit(1)

    return nl_en, en_tr


def argo_translate_batch(names: list[str], nl_en, en_tr) -> list[str]:
    """nl→en→tr pivot ile toplu çeviri."""
    results = []
    for name in names:
        try:
            en_text = nl_en.translate(name)
            tr_text = en_tr.translate(en_text)
            results.append(tr_text if tr_text else name)
        except Exception:
            results.append(name)
    return results

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ürün isimlerini nl→tr çevirir (argostranslate)")
    parser.add_argument("--zincir", help="Sadece bu zincir (örn: aldi, delhaize)")
    parser.add_argument("--limit", type=int, default=0, help="En fazla kaç ürün (0=hepsi)")
    parser.add_argument("--dry-run", action="store_true", help="DB'ye yazma, sadece göster")
    parser.add_argument("--kur-modeller", action="store_true", help="nl→en ve en→tr modellerini indir")
    args = parser.parse_args()

    if args.kur_modeller:
        kur_modeller()
        return

    SB_URL, SB_KEY = load_secrets()
    print(f"Supabase: {SB_URL}")
    print("argostranslate modelleri yükleniyor...")
    nl_en, en_tr = _get_translator()
    print("Modeller hazır.\n")

    total = count_pending(SB_URL, SB_KEY, args.zincir)
    if args.limit and args.limit < total:
        total = args.limit
    print(f"Çevrilecek ürün: {total}" + (f" (zincir: {args.zincir})" if args.zincir else ""))
    if total == 0:
        print("Çevrilecek ürün yok. Hepsi zaten çevrilmiş veya zincir adı hatalı.")
        return

    done = 0
    pending_save: list[dict] = []
    start = time.time()

    while done < total:
        # offset=0 her zaman — kaydedilenler IS NULL filtresinden çıkar, hep baştan çek
        batch = fetch_batch(SB_URL, SB_KEY, args.zincir, 0)
        if not batch:
            break

        # Limit uygula
        if args.limit:
            batch = batch[:max(0, args.limit - done)]

        # Yerel sözlükten çevrilebilenleri ayır, gerisini argostranslate'e ver
        needs_argo: list[int] = []   # batch index
        results: list[str] = []

        for i, row in enumerate(batch):
            name = row.get("name", "") or ""
            local = local_translate(name)
            if local:
                results.append(local)
            else:
                results.append("")   # placeholder
                needs_argo.append(i)

        # argostranslate toplu çeviri
        if needs_argo:
            names_to_translate = [batch[i].get("name", "") or "" for i in needs_argo]
            # TRANS_BATCH boyutunda parçala (bellek dostu)
            argo_results = []
            for chunk_start in range(0, len(names_to_translate), TRANS_BATCH):
                chunk = names_to_translate[chunk_start:chunk_start + TRANS_BATCH]
                argo_results.extend(argo_translate_batch(chunk, nl_en, en_tr))
            for idx, argo_idx in enumerate(needs_argo):
                results[argo_idx] = argo_results[idx] if argo_results[idx] else batch[argo_idx].get("name", "")

        # Kayıt listesine ekle
        for i, row in enumerate(batch):
            pending_save.append({"id": row["id"], "name_tr": results[i]})
            done += 1

        # İlerleme
        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 else 0
        print(f"  [{done}/{total}] ~{remaining/60:.0f} dk kaldı | "
              f"Son: {batch[-1].get('name','')[:30]} → {results[-1][:30]}")

        # Periyodik kayıt
        if len(pending_save) >= SAVE_EVERY:
            save_batch(SB_URL, SB_KEY, pending_save, args.dry_run)
            pending_save = []


    # Kalan kayıtları yaz
    if pending_save:
        save_batch(SB_URL, SB_KEY, pending_save, args.dry_run)

    elapsed = time.time() - start
    print(f"\nTamamlandı. {done} ürün çevrildi, {elapsed/60:.1f} dakika.")

if __name__ == "__main__":
    main()
