# -*- coding: utf-8 -*-
"""Haftalık Delhaize: GraphQL çekimi -> en son delhaize_be_producten_*.json -> Supabase."""
from __future__ import annotations

import glob
import os
import subprocess
import sys


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    fetch = subprocess.run(
        [sys.executable, "delhaize_be_v2.py", "--no-pause"],
        cwd=script_dir,
    )
    if fetch.returncode != 0:
        print("HATA: Delhaize çekimi başarısız.")
        return fetch.returncode

    cikti = os.path.join(script_dir, "cikti")
    matches = glob.glob(os.path.join(cikti, "delhaize_be_v2_*.json"))
    if not matches:
        print("HATA: cikti/delhaize_be_producten_*.json bulunamadı.")
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
