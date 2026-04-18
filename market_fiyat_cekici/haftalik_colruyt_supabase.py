# -*- coding: utf-8 -*-
"""
Haftalık Colruyt akışı: API çekimi → en son colruyt_be_producten_*.json → Supabase upsert.

Görev Zamanlayıcı: bu dosyayı çalıştırın (veya calistir_colruyt_haftalik.bat).
Önkoşul: supabase_import_secrets.txt ve geçerli curl.txt / cookie.txt / token.txt.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    fetch = subprocess.run(
        [sys.executable, "colruyt_product_search_api_cek.py", "--no-pause"],
        cwd=script_dir,
    )
    if fetch.returncode != 0:
        print("HATA: Colruyt çekimi başarısız.")
        return fetch.returncode

    cikti = os.path.join(script_dir, "cikti")
    matches = glob.glob(os.path.join(cikti, "colruyt_be_producten_*.json"))
    if not matches:
        print("HATA: cikti/colruyt_be_producten_*.json bulunamadı.")
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
