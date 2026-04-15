# -*- coding: utf-8 -*-
"""
Platform Avrupa — ürünleri 'kullanıcı karşılaştırıyormuş' gibi duman testi.

Her satır: erişim gecikmesi, ham sonuç, olası sorun ipuçları.
Çıktıyı kaydedip hangi üründe ne kırılıyor hızlıca görün.

  python platform_karsi_lastir_tani.py
  python platform_karsi_lastir_tani.py --no-supabase   # sadece dış API'ler

Video ozet icin: python platform_rapor_videosu.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any, Callable, Optional

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def _sure(fun: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.perf_counter()
    try:
        out = fun()
        return out, (time.perf_counter() - t0) * 1000
    except Exception as e:
        return e, (time.perf_counter() - t0) * 1000


def satir_yaz(r: dict) -> None:
    ok = r.get("ok")
    durum = "OK " if ok else "HATA"
    print(f"[{durum}] {r.get('urun')}")
    print(f"      sure_ms={r.get('sure_ms', 0):.0f}  | {r.get('ozet', '')}")
    if r.get("not"):
        print(f"      not: {r['not']}")
    if r.get("detay"):
        print(f"      detay: {r['detay'][:500]}")
    print()


def tani_arbeitnow() -> dict:
    def job():
        r = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"page": 1},
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa-Tani/1.0"},
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        return len(data), data[0].get("title", "")[:50] if data else ""

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Arbeitnow API (sayfa 1)",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": "Ag, TLS, 429 veya JSON bozuk.",
        }
    n, baslik = out
    return {
        "urun": "Arbeitnow API (sayfa 1)",
        "ok": n > 0,
        "sure_ms": ms,
        "ozet": f"{n} ilan ornek_baslik={baslik!r}",
        "not": None if n else "Bos sayfa — filtreniz veya API degisimi.",
    }


def tani_adzuna(app_id: str, app_key: str) -> dict:
    def job():
        r = requests.get(
            "https://api.adzuna.com/v1/api/jobs/be/search/1",
            params={"app_id": app_id, "app_key": app_key, "results_per_page": 5},
            timeout=20,
        )
        if r.status_code == 401 or r.status_code == 403:
            r.raise_for_status()
        r.raise_for_status()
        res = r.json().get("results", [])
        return len(res), (res[0].get("title", "")[:50] if res else "")

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Adzuna API (BE, 5 sonuc)",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": "app_id/app_key kotasi veya anahtar hatasi.",
        }
    n, baslik = out
    return {
        "urun": "Adzuna API (BE, 5 sonuc)",
        "ok": n > 0,
        "sure_ms": ms,
        "ozet": f"{n} ilan ornek={baslik!r}",
        "not": None,
    }


def tani_bundesagentur() -> dict:
    from is_ilani_cekici import bundesagentur_token_al

    t0 = time.perf_counter()

    def tam():
        tok, err = bundesagentur_token_al()
        if not tok:
            raise RuntimeError(err)
        r = requests.get(
            "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs",
            params={"angebotsart": 1, "page": 1, "size": 5},
            headers={
                "Authorization": f"Bearer {tok}",
                "User-Agent": "Jobsuche/2.9.2",
            },
            timeout=20,
        )
        r.raise_for_status()
        st = r.json().get("stellenangebote", [])
        return len(st)

    out, _ = _sure(tam)
    ms = (time.perf_counter() - t0) * 1000
    if isinstance(out, Exception):
        msg = str(out)
        return {
            "urun": "Bundesagentur (token + jobs sayfa 1)",
            "ok": False,
            "sure_ms": ms,
            "ozet": msg,
            "not": "Token JSON/HTML veya ilan API; mesaja bakin.",
        }
    return {
        "urun": "Bundesagentur (token + jobs sayfa 1)",
        "ok": out > 0,
        "sure_ms": ms,
        "ozet": f"{out} ilan (size=5 istegi)",
        "not": None,
    }


def tani_jobicy() -> dict:
    def job():
        r = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 5, "geo": "europe"},
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa-Tani/1.0"},
        )
        r.raise_for_status()
        jobs = r.json().get("jobs", [])
        return len(jobs)

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Jobicy API",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": None,
        }
    return {
        "urun": "Jobicy API",
        "ok": out > 0,
        "sure_ms": ms,
        "ozet": f"{out} ilan",
        "not": None,
    }


def tani_remotive() -> dict:
    def job():
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"limit": 5},
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa-Tani/1.0"},
        )
        r.raise_for_status()
        jobs = r.json().get("jobs", [])
        return len(jobs)

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Remotive API",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": None,
        }
    return {
        "urun": "Remotive API",
        "ok": out > 0,
        "sure_ms": ms,
        "ozet": f"{out} ilan",
        "not": None,
    }


def tani_supabase() -> dict:
    from is_ilani_cekici import load_secrets

    def job():
        sb_url, sb_key = load_secrets()
        r = requests.get(
            f"{sb_url}/rest/v1/ilanlar",
            params={"select": "id", "status": "eq.active"},
            headers={
                "apikey": sb_key,
                "Authorization": f"Bearer {sb_key}",
                "Prefer": "count=exact",
                "Range": "0-0",
            },
            timeout=30,
        )
        r.raise_for_status()
        cr = r.headers.get("Content-Range", "")
        m = re.search(r"/(\d+)", cr)
        n = int(m.group(1)) if m else -1
        return sb_url, n

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Supabase (aktif ilan sayisi)",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": "secrets dosyasi, RLS veya ag.",
        }
    url, n = out
    return {
        "urun": "Supabase (aktif ilan sayisi)",
        "ok": n >= 0,
        "sure_ms": ms,
        "ozet": f"count={n} url={url[:48]}...",
        "not": None,
    }


def tani_cevirmen() -> dict:
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        return {
            "urun": "Baslik cevirisi (GoogleTranslator)",
            "ok": False,
            "sure_ms": 0,
            "ozet": "deep-translator yuklu degil",
            "not": "pip install deep-translator",
        }

    def job():
        return GoogleTranslator(source="en", target="tr").translate("Software developer")

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Baslik cevirisi (GoogleTranslator)",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": "Rate limit, IP blok veya baglanti.",
        }
    return {
        "urun": "Baslik cevirisi (GoogleTranslator)",
        "ok": bool(out and len(str(out)) > 2),
        "sure_ms": ms,
        "ozet": f'en "Software developer" -> tr {out!r}',
        "not": None,
    }


def tani_upsert_dry() -> dict:
    """Merge-duplicates URL'inin varligi — tek sahte satir gondermeden sadece baglanti."""

    from is_ilani_cekici import load_secrets

    def job():
        sb_url, sb_key = load_secrets()
        r = requests.post(
            f"{sb_url}/rest/v1/ilanlar?on_conflict=source,source_id",
            json=[],
            headers={
                "apikey": sb_key,
                "Authorization": f"Bearer {sb_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            timeout=30,
        )
        return r.status_code

    out, ms = _sure(job)
    if isinstance(out, Exception):
        return {
            "urun": "Supabase upsert endpoint (bos POST)",
            "ok": False,
            "sure_ms": ms,
            "ozet": str(out),
            "not": None,
        }
    ok = out in (200, 201, 204)
    return {
        "urun": "Supabase upsert endpoint (bos POST)",
        "ok": ok,
        "sure_ms": ms,
        "ozet": f"HTTP {out}",
        "not": None if ok else "PostgREST on_conflict veya Yetki sorunu.",
    }


def main():
    parser = argparse.ArgumentParser(description="Tum urunleri tek tek dumanla")
    parser.add_argument("--no-supabase", action="store_true", help="Supabase adimlarini atla")
    parser.add_argument("--json", action="store_true", help="Ozeti JSON stdout")
    args = parser.parse_args()

    print("=" * 64)
    print(" PLATFORM AVRUPA — Karsi lastirma / saglik turu")
    print(" Her bolum bagimsiz; biri duserse digerleri calisir.")
    print("=" * 64 + "\n")

    raporlar: list[dict] = []

    raporlar.append(tani_arbeitnow())
    raporlar.append(tani_adzuna("c0c66624", "5a2d86df68a24e6fe8b1e9b4319347f0"))
    raporlar.append(tani_bundesagentur())
    raporlar.append(tani_jobicy())
    raporlar.append(tani_remotive())

    if not args.no_supabase:
        raporlar.append(tani_supabase())
        raporlar.append(tani_upsert_dry())

    raporlar.append(tani_cevirmen())

    if args.json:
        print(json.dumps(raporlar, ensure_ascii=False, indent=2))
        return

    for r in raporlar:
        satir_yaz(r)

    toplam = len(raporlar)
    basari = sum(1 for x in raporlar if x.get("ok"))
    print("-" * 64)
    print(f"Ozet: {basari}/{toplam} bolum sorunsuz")
    print("Oneri: HATA satirlarindaki 'not' alanini once duzeltin; sonra")
    print("       python is_ilani_cekici.py --quick --dry-run")
    print("-" * 64)


if __name__ == "__main__":
    main()
