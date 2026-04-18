# -*- coding: utf-8 -*-
"""
Belçika 5 zincir — tam çekimi sırayla çalıştırır; zincirler arası uzun durak (ban riskini azaltır).

Sıra (sabit): ALDI → Colruyt → Delhaize → Lidl → Carrefour
Her adım ayrı subprocess: bir zincir çökse bile sonrakine geçebilirsiniz.

Önkoşullar: Colruyt cookie.txt; Carrefour ilk seferde gerekirse --headed ile profil.
Lidl: lidl_cookie.txt + lidl_be_api_categories.txt doluysa Mindshift API; yoksa Playwright --mode categories
"""
from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
import time
from typing import List, Tuple

ChainSpec = Tuple[str, List[str]]


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


def chain_commands(script_dir: str, *, lidl_mode: str) -> List[ChainSpec]:
    py = sys.executable
    if _lidl_use_mindshift_api(script_dir):
        lidl_cmd = [py, "lidl_be_mindshift_api_cek.py", "--no-pause"]
    else:
        lidl_cmd = [py, "lidl_be_playwright_cek.py", "--mode", lidl_mode, "--no-pause"]
    return [
        (
            "aldi",
            [
                py,
                "aldi_tum_yeme_icme_cek.py",
                "--human",
                "--max-pages",
                "600",
                "--no-pause",
            ],
        ),
        (
            "colruyt",
            [py, "colruyt_product_search_api_cek.py", "--no-pause"],
        ),
        (
            "delhaize",
            [py, "delhaize_be_graphql_cek.py", "--no-pause"],
        ),
        ("lidl", lidl_cmd),
        (
            "carrefour",
            [py, "carrefour_be_playwright_cek.py", "--no-pause"],
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="BE 5 zincir sıralı çekim orkestratörü")
    ap.add_argument(
        "--chains",
        type=str,
        default="aldi,colruyt,delhaize,lidl,carrefour",
        help="Virgülle zincir adları (alt küme)",
    )
    ap.add_argument(
        "--between-min-sec",
        type=float,
        default=120.0,
        help="Zincirler arası minimum bekleme (sn)",
    )
    ap.add_argument(
        "--between-max-sec",
        type=float,
        default=300.0,
        help="Zincirler arası maksimum bekleme (sn)",
    )
    ap.add_argument(
        "--lidl-mode",
        choices=("search", "categories"),
        default="categories",
        help="Lidl adımı: categories=tam katalogya yakın (yavas); search=hizli ornek",
    )
    ap.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Bir zincir hata verse bile sonrakine geç",
    )
    args = ap.parse_args()

    want = {s.strip().lower() for s in args.chains.split(",") if s.strip()}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    all_specs = chain_commands(script_dir, lidl_mode=args.lidl_mode)
    specs = [s for s in all_specs if s[0] in want]
    if not specs:
        print("HATA: --chains ile eslesen zincir yok.")
        return 1

    print(f"Calisacak zincirler: {[s[0] for s in specs]}")
    if _lidl_use_mindshift_api(script_dir):
        print("Lidl: Mindshift API")
    else:
        print(f"Lidl Playwright modu: {args.lidl_mode}")
    print(f"Zincirler arasi: {args.between_min_sec:.0f}–{args.between_max_sec:.0f} sn\n")

    rc_all = 0
    for i, (name, cmd) in enumerate(specs):
        print("=" * 60)
        print(f"[{i + 1}/{len(specs)}] {name}: {' '.join(cmd[1:])}")
        print("=" * 60)
        p = subprocess.run(cmd, cwd=script_dir)
        if p.returncode != 0:
            print(f"\nUYARI: {name} cikis kodu {p.returncode}")
            rc_all = p.returncode
            if not args.continue_on_error:
                return p.returncode
        if i < len(specs) - 1:
            sec = random.uniform(args.between_min_sec, args.between_max_sec)
            print(f"\nSonraki zincir icin {sec:.0f} sn bekleniyor...\n")
            time.sleep(sec)

    print("\nTum secili zincir adimlari tamamlandi.")
    return rc_all


if __name__ == "__main__":
    raise SystemExit(main())
