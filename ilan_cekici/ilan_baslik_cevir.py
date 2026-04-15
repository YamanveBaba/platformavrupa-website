# -*- coding: utf-8 -*-
"""
Platform Avrupa - İlan Başlıklarını Türkçe'ye Çevirir
ilanlar tablosundaki otomatik (source != 'user') ilanların title alanını
Google Translate ile orijinal dil → Türkçe'ye çevirir.

Kullanım:
  python ilan_baslik_cevir.py              # Tüm çevrilmemiş başlıklar
  python ilan_baslik_cevir.py --limit 100  # Test: sadece 100 ilan
  python ilan_baslik_cevir.py --dry-run    # DB'ye yazma, sadece göster

Kurulum (bir kez çalıştır):
  pip install deep-translator requests
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
    print("HATA: pip install requests"); sys.exit(1)

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("HATA: pip install deep-translator")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_DB   = 200   # Supabase'den kaç ilan çek
SAVE_EVERY = 100   # Kaç çeviriden sonra DB'ye yaz
DELAY_SEC  = 0.15  # Google rate limit için bekleme (saniye)

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt"))
    if os.path.isfile(path):
        lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: supabase_import_secrets.txt bulunamadi.")
    sys.exit(1)

def fetch_batch(url: str, key: str, limit: int) -> list[dict]:
    """source != user olan ve title_original IS NULL olan ilanları çek (hep offset=0)."""
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    r = requests.get(
        f"{url}/rest/v1/ilanlar",
        params={
            "select": "id,title,country",
            "source": "neq.user",
            "title_original": "is.null",
            "status": "eq.active",
            "order": "id.asc",
            "limit": str(limit),
            "offset": "0",
        },
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def count_pending(url: str, key: str) -> int:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    r = requests.get(
        f"{url}/rest/v1/ilanlar",
        params={"select": "id", "source": "neq.user", "title_original": "is.null", "status": "eq.active"},
        headers=headers,
        timeout=30,
    )
    m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
    return int(m.group(1)) if m else 0

def save_batch(url: str, key: str, rows: list[dict], dry_run: bool):
    if dry_run:
        print(f"  [dry-run] {len(rows)} baslik yazilacakti.")
        return
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    errors = 0
    for row in rows:
        r = requests.patch(
            f"{url}/rest/v1/ilanlar?id=eq.{row['id']}",
            json={"title": row["title_tr"], "title_original": row["title_original"]},
            headers=headers,
            timeout=30,
        )
        if r.status_code not in (200, 204):
            errors += 1
    if errors:
        print(f"  UYARI: {errors}/{len(rows)} satir yazilamadi.")
    else:
        print(f"  DB'ye {len(rows)} baslik yazildi.")

# ─── ÇEVİRİ ──────────────────────────────────────────────────────────────────

def cevir(title: str) -> str:
    """Google Translate ile otomatik dil tespiti + Turkce cevirisi."""
    if not title or not title.strip():
        return title
    try:
        result = GoogleTranslator(source="auto", target="tr").translate(title.strip())
        return result if result else title
    except Exception as e:
        # Rate limit veya bağlantı hatası - biraz bekle, tekrar dene
        time.sleep(2)
        try:
            result = GoogleTranslator(source="auto", target="tr").translate(title.strip())
            return result if result else title
        except Exception:
            return title

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ilan basliklarini Turkce'ye cevirir (Google Translate)")
    parser.add_argument("--limit", type=int, default=0, help="Max ilan sayisi (0=hepsi)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    print("Cevirici: Google Translate (deep-translator)\n")

    total = count_pending(sb_url, sb_key)
    if args.limit and args.limit < total:
        total = args.limit
    print(f"Cevrilecek ilan: {total}")
    if total == 0:
        print("Cevrilecek ilan yok.")
        return

    done = 0
    pending_save: list[dict] = []
    start = time.time()

    while done < total:
        fetch_limit = min(BATCH_DB, total - done)
        batch = fetch_batch(sb_url, sb_key, fetch_limit)
        if not batch:
            break

        for row in batch:
            title_orig = row.get("title", "") or ""
            title_tr = cevir(title_orig)
            pending_save.append({
                "id": row["id"],
                "title_tr": title_tr,
                "title_original": title_orig,
            })
            done += 1
            time.sleep(DELAY_SEC)  # Google rate limit

        elapsed = time.time() - start
        rate = done / elapsed if elapsed > 0 else 1
        kalan = (total - done) / rate / 60
        last_orig = batch[-1].get("title", "")[:35]
        last_tr = pending_save[-1]["title_tr"][:35]
        print(f"  [{done}/{total}] ~{kalan:.0f} dk kaldi | {last_orig} >> {last_tr}")

        if len(pending_save) >= SAVE_EVERY:
            save_batch(sb_url, sb_key, pending_save, args.dry_run)
            pending_save = []

    if pending_save:
        save_batch(sb_url, sb_key, pending_save, args.dry_run)

    elapsed = time.time() - start
    print(f"\nTamamlandi. {done} baslik cevrildi, {elapsed/60:.1f} dakika.")

if __name__ == "__main__":
    main()
