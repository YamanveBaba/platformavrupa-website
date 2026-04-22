# -*- coding: utf-8 -*-
"""
Platform Avrupa — Belçika İş İlanı Orkestratörü
Kaynaklar: FOREM (Wallonia) + Actiris (Brüksel)
           (VDAB Flanders: vdab_cek.py ile ayrı çalıştırılır)

Kullanım:
  python belcika_is_ilanlari.py                   # FOREM + Actiris tam çekim
  python belcika_is_ilanlari.py --kaynak forem     # Sadece FOREM
  python belcika_is_ilanlari.py --kaynak actiris   # Sadece Actiris
  python belcika_is_ilanlari.py --dry-run          # Supabase'e yazma
  python belcika_is_ilanlari.py --quick            # Smoke test
  python belcika_is_ilanlari.py --temizle          # Süresi dolan tüm BE ilanlarını expired yap
  python belcika_is_ilanlari.py --visible          # Actiris scraper görünür tarayıcı
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import os
import time
import re
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    secrets_path = os.path.normpath(
        os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
    )
    if os.path.isfile(secrets_path):
        lines = [l.strip() for l in open(secrets_path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: Supabase credentials bulunamadı.")
    sys.exit(1)

def belcika_istatistik(sb_url: str, sb_key: str) -> None:
    """Kaynağa göre aktif Belçika ilanlarını say."""
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}", "Prefer": "count=exact", "Range": "0-0"}
    kaynaklar = ["forem", "actiris", "vdab", "adzuna_be"]
    print("\n── Belçika İlan İstatistiği ──")
    for kaynak in kaynaklar:
        params = {"source": f"eq.{kaynak}", "status": "eq.active", "select": "id"}
        r = requests.get(f"{sb_url}/rest/v1/ilanlar", params=params, headers=headers, timeout=15)
        m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
        sayi = int(m.group(1)) if m else "?"
        print(f"  {kaynak:15}: {sayi} aktif ilan")
    print()

def expired_yap_kaynak(sb_url: str, sb_key: str, kaynak: str, expiry_gun: int, dry_run: bool) -> int:
    sinir = (datetime.now(timezone.utc) - timedelta(days=expiry_gun)).isoformat()
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}",
               "Prefer": "count=exact", "Range": "0-0"}
    params = {"source": f"eq.{kaynak}", "status": "eq.active",
              "created_at": f"lt.{sinir}", "select": "id"}
    r = requests.get(f"{sb_url}/rest/v1/ilanlar", params=params, headers=headers, timeout=30)
    m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
    toplam = int(m.group(1)) if m else 0
    if toplam == 0:
        return 0
    if dry_run:
        print(f"  [dry-run] {toplam} {kaynak} ilanı expired yapılacaktı.")
        return toplam
    patch = requests.patch(
        f"{sb_url}/rest/v1/ilanlar?source=eq.{kaynak}&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"},
        headers={**headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
        timeout=60,
    )
    if patch.status_code in (200, 204):
        print(f"  {toplam} {kaynak} ilanı expired yapıldı.")
        return toplam
    return 0

# ─── ALT SCRIPT ÇALIŞTIRICI ──────────────────────────────────────────────────

def script_calistir(script_adi: str, ekstra_args: list[str]) -> bool:
    """Alt scripti çalıştır, çıkış kodunu döndür."""
    script_path = os.path.join(SCRIPT_DIR, script_adi)
    cmd = [sys.executable, "-X", "utf8", script_path] + ekstra_args
    print(f"\n{'='*60}")
    print(f"[{script_adi}] Başlatılıyor...")
    print(f"{'='*60}")
    result = subprocess.run(cmd, encoding="utf-8", errors="replace")
    return result.returncode == 0

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Platform Avrupa — Belçika İş İlanları (FOREM + Actiris)"
    )
    parser.add_argument(
        "--kaynak",
        choices=["forem", "actiris", "hepsi"],
        default="hepsi",
        help="Hangi kaynak çekilsin (varsayılan: hepsi)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Supabase'e yazma")
    parser.add_argument("--temizle", action="store_true", help="Süresi dolan ilanları expired yap")
    parser.add_argument("--quick", action="store_true", help="Her kaynakta kısa test (100 ilan)")
    parser.add_argument("--visible", action="store_true", help="Actiris için görünür tarayıcı")
    parser.add_argument("--istatistik", action="store_true", help="Sadece istatistik göster")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if args.istatistik:
        belcika_istatistik(sb_url, sb_key)
        return

    if args.dry_run:
        print("[DRY-RUN MODU]\n")
    if args.quick:
        print("[QUICK MODU — her kaynakta ~100 ilan]\n")

    start = time.time()

    # Temizlik
    if args.temizle:
        print("\n[Temizlik] Süresi dolan Belçika ilanları...")
        for kaynak, gun in [("forem", 45), ("actiris", 30)]:
            expired_yap_kaynak(sb_url, sb_key, kaynak, gun, args.dry_run)

    # FOREM
    if args.kaynak in ("forem", "hepsi"):
        forem_args = []
        if args.dry_run:
            forem_args.append("--dry-run")
        if args.quick:
            forem_args.append("--quick")
        if args.temizle:
            forem_args.append("--temizle")
        ok = script_calistir("forem_cek.py", forem_args)
        if not ok:
            print("  UYARI: FOREM scripti hata ile bitti.")

    # Actiris
    if args.kaynak in ("actiris", "hepsi"):
        actiris_args = []
        if args.dry_run:
            actiris_args.append("--dry-run")
        if args.quick:
            actiris_args.append("--quick")
        if args.visible:
            actiris_args.append("--visible")
        if args.temizle:
            actiris_args.append("--temizle")
        ok = script_calistir("actiris_cek.py", actiris_args)
        if not ok:
            print("  UYARI: Actiris scripti hata ile bitti.")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Tüm kaynaklar tamamlandı — {elapsed/60:.1f} dakika")
    print(f"{'='*60}")

    # Final istatistik
    belcika_istatistik(sb_url, sb_key)

if __name__ == "__main__":
    main()
