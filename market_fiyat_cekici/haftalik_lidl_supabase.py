# -*- coding: utf-8 -*-
"""Haftalık Lidl BE: Mindshift API (cookie + kategori dosyasi varsa) yoksa Playwright → JSON → Supabase."""
from __future__ import annotations

import glob
import os
import subprocess
import sys


def _lidl_use_mindshift_api(script_dir: str) -> bool:
    cookie_path = os.path.join(script_dir, "lidl_cookie.txt")
    cats_path = os.path.join(script_dir, "lidl_be_api_categories.txt")
    if not os.path.isfile(cookie_path) or not os.path.isfile(cats_path):
        return False
    with open(cookie_path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#") and "=" in s and len(s) > 20:
                return True
    return False


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if _lidl_use_mindshift_api(script_dir):
        print("Lidl: Mindshift API (lidl_cookie.txt + lidl_be_api_categories.txt)\n")
        fetch_cmd = [sys.executable, "lidl_be_mindshift_api_cek.py", "--no-pause"]
    else:
        print("Lidl: Playwright categories (cookie dosyasi bos/eksik — API atlandi)\n")
        fetch_cmd = [
            sys.executable,
            "lidl_be_playwright_cek.py",
            "--mode",
            "categories",
            "--no-pause",
        ]

    fetch = subprocess.run(fetch_cmd, cwd=script_dir)
    if fetch.returncode != 0:
        print("HATA: Lidl çekimi başarısız veya ürün çıkmadı (çerez/WAF kontrol edin).")
        return fetch.returncode

    cikti = os.path.join(script_dir, "cikti")
    matches = glob.glob(os.path.join(cikti, "lidl_be_producten_*.json"))
    if not matches:
        print("HATA: cikti/lidl_be_producten_*.json bulunamadı.")
        return 1

    latest = max(matches, key=os.path.getmtime)
    print(f"\nSupabase yüklemesi: {latest}\n")

    upload = subprocess.run(
        [sys.executable, "json_to_supabase_yukle.py", "--no-pause", latest],
        cwd=script_dir,
    )
    return upload.returncode


if __name__ == "__main__":
    sys.exit(main())
