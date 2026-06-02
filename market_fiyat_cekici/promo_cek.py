# -*- coding: utf-8 -*-
"""
promo_cek.py — Platform Avrupa Haftalik Promosyon Cekici
=========================================================
5 Belcika marketi icin SADECE indirimli urunleri ceker.
GitHub Actions (Ubuntu) ve lokal ortamda calisir.

Auth ortam degiskenleri:
  COLRUYT_API_KEY   — colruyt_auth.txt KEY= satiri
  COLRUYT_COOKIE    — colruyt_auth.txt COOKIE= satiri
  LIDL_COOKIE       — lidl_cookie.txt icerigi
  SUPABASE_URL      — Supabase proje URL'si
  SUPABASE_SERVICE_ROLE_KEY
  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID

Calisma suresi hedefi: ~20-40 dakika (eski sistemde 4-6 saat)
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CIKTI_DIR  = SCRIPT_DIR / "cikti"
CIKTI_DIR.mkdir(exist_ok=True)

PY = sys.executable


# ─── Telegram ────────────────────────────────────────────────────────────────
def telegram(msg: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat  = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    try:
        data = urllib.parse.urlencode(
            {"chat_id": chat, "text": msg, "parse_mode": "HTML"}
        ).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data, timeout=10,
        )
    except Exception:
        pass


# ─── Auth dosyalarini ortam degiskenlerinden olustur ─────────────────────────
def auth_hazirla() -> None:
    colruyt_key    = os.environ.get("COLRUYT_API_KEY", "").strip()
    colruyt_cookie = os.environ.get("COLRUYT_COOKIE", "").strip()
    if colruyt_key or colruyt_cookie:
        auth_path = SCRIPT_DIR.parent / "colruyt_auth.txt"
        lines: list[str] = []
        if colruyt_key:
            lines.append(f"KEY={colruyt_key}")
        if colruyt_cookie:
            lines.append(f"COOKIE={colruyt_cookie}")
        auth_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[auth] colruyt_auth.txt yazildi")

    lidl_cookie = os.environ.get("LIDL_COOKIE", "").strip()
    if lidl_cookie:
        (SCRIPT_DIR / "lidl_cookie.txt").write_text(lidl_cookie, encoding="utf-8")
        print("[auth] lidl_cookie.txt yazildi")


# ─── En son cikti JSON'unu bul ───────────────────────────────────────────────
def en_son_json(pattern: str) -> Path | None:
    dosyalar = sorted(
        CIKTI_DIR.glob(pattern),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return dosyalar[0] if dosyalar else None


# ─── inPromo filtrele ve yeni JSON yaz ───────────────────────────────────────
def promo_filtrele(json_path: Path, market_isim: str) -> Path | None:
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  JSON okuma hatasi: {e}")
        return None

    urunler = raw.get("urunler", raw if isinstance(raw, list) else [])
    if not isinstance(urunler, list):
        print(f"  Beklenmedik format, atlaniyor")
        return None

    promo = [
        u for u in urunler
        if u.get("inPromo") is True
        or u.get("isPromoActive") == "Y"
        or (u.get("promoPrice") is not None and u.get("promoPrice") != u.get("basicPrice"))
    ]

    print(f"  Toplam {len(urunler)} urun → {len(promo)} indirimli")

    if not promo:
        return None

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    chain = raw.get("chain_slug", market_isim)
    out_path = CIKTI_DIR / f"{chain}_promo_{ts}.json"

    out_data = {k: v for k, v in raw.items() if k != "urunler"}
    out_data["urunler"]          = promo
    out_data["urun_sayisi"]      = len(promo)
    out_data["promo_filtrelendi"] = True

    out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Kaydedildi: {out_path.name}")
    return out_path


# ─── Supabase yukle ───────────────────────────────────────────────────────────
def supabase_yukle(json_path: Path) -> bool:
    yukle_script = SCRIPT_DIR / "json_to_supabase_yukle.py"
    if not yukle_script.exists():
        print("  UYARI: json_to_supabase_yukle.py bulunamadi")
        return False
    ret = subprocess.run(
        [PY, str(yukle_script), str(json_path)],
        cwd=str(SCRIPT_DIR),
        timeout=300,
    )
    return ret.returncode == 0


# ─── Scraper calistir ─────────────────────────────────────────────────────────
def scraper_calistir(
    script_adi: str,
    args: list[str],
    timeout_sn: int,
) -> bool:
    path = SCRIPT_DIR / script_adi
    if not path.exists():
        print(f"  UYARI: {script_adi} bulunamadi, atlaniyor")
        return False
    cmd = [PY, str(path)] + args
    print(f"  Komut: {' '.join(str(c) for c in cmd)}")
    try:
        ret = subprocess.run(cmd, cwd=str(SCRIPT_DIR), timeout=timeout_sn)
        ok = ret.returncode == 0
        print(f"  Bitis kodu: {ret.returncode}")
        return ok
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT ({timeout_sn // 60} dk) — mevcut veriyle devam")
        return True   # timeout olsa bile JSON ciktisi olabilir
    except Exception as e:
        print(f"  HATA: {e}")
        return False


# ─── Marketler ───────────────────────────────────────────────────────────────
MARKETLER = [
    {
        "isim":    "colruyt",
        "script":  "colruyt_product_search_api_cek.py",
        # max-products=6000 → ~100 sayfa × 2-4 sn ≈ 5-7 dk; promo dagitimi buyuk olasilikla ilk sayfalarda
        "args":    ["--no-pause", "--max-products", "6000"],
        "timeout": 20 * 60,
        "pattern": "colruyt_be_producten_*.json",
    },
    {
        "isim":    "delhaize",
        "script":  "delhaize_be_graphql_cek.py",
        "args":    ["--no-pause"],
        "timeout": 45 * 60,
        "pattern": "delhaize_be_producten_*.json",
    },
    {
        "isim":    "lidl",
        "script":  "lidl_be_mindshift_api_cek.py",
        "args":    ["--no-pause"],
        "timeout": 40 * 60,
        "pattern": "lidl_be_producten_*.json",
    },
    {
        "isim":    "carrefour",
        "script":  "carrefour_be_playwright_cek.py",
        "args":    ["--no-pause"],
        "timeout": 20 * 60,
        "pattern": "carrefour_be_producten_*.json",
    },
    {
        "isim":    "aldi",
        "script":  "aldi_tum_yeme_icme_cek.py",
        "args":    ["--no-pause"],
        "timeout": 30 * 60,
        "pattern": "aldi_be_tum_yeme_icme_*.json",
    },
]


# ─── Ana akis ─────────────────────────────────────────────────────────────────
def main() -> int:
    baslangic = datetime.now()
    print(f"\n{'='*60}")
    print(f"promo_cek.py — {baslangic.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    auth_hazirla()

    sonuclar: dict[str, dict] = {}

    for m in MARKETLER:
        print(f"\n{'─'*60}")
        print(f">>> {m['isim'].upper()} basliyor...")
        t0 = time.time()

        scraper_calistir(m["script"], m["args"], m["timeout"])
        sure = time.time() - t0

        json_path = en_son_json(m["pattern"])
        if not json_path:
            print(f"  {m['isim']}: JSON ciktisi bulunamadi")
            sonuclar[m["isim"]] = {"ok": False, "urun": 0, "sure": round(sure / 60, 1)}
            continue

        promo_path = promo_filtrele(json_path, m["isim"])
        if not promo_path:
            sonuclar[m["isim"]] = {"ok": False, "urun": 0, "sure": round(sure / 60, 1)}
            continue

        yukle_ok    = supabase_yukle(promo_path)
        promo_sayisi = json.loads(promo_path.read_text(encoding="utf-8")).get("urun_sayisi", 0)

        sonuclar[m["isim"]] = {
            "ok":   yukle_ok,
            "urun": promo_sayisi,
            "sure": round(sure / 60, 1),
        }
        print(f"  {m['isim']}: {promo_sayisi} promo urun yuklendi")

        time.sleep(5)

    # ── Ozet ──
    print(f"\n{'='*60}")
    print("OZET")
    print(f"{'='*60}")
    toplam = 0
    for isim, s in sonuclar.items():
        durum = "OK  " if s["ok"] else "HATA"
        print(f"  {durum} {isim:12} {s.get('urun', 0):5} promo  ({s.get('sure', 0)} dk)")
        toplam += s.get("urun", 0)

    sure_dk = round((datetime.now() - baslangic).total_seconds() / 60, 1)
    print(f"\n  Toplam: {toplam} promo urun — {sure_dk} dk")

    basarili = sum(1 for s in sonuclar.values() if s["ok"])

    telegram(
        f"🛒 <b>Market Promosyon Guncelleme</b>\n"
        f"Toplam: <b>{toplam} indirimli urun</b>\n"
        + "\n".join(
            f"{'✅' if s['ok'] else '❌'} {n}: {s.get('urun', 0)} urun ({s.get('sure', 0)} dk)"
            for n, s in sonuclar.items()
        )
        + f"\n⏱ Toplam: {sure_dk} dk"
    )

    return 0 if basarili >= 3 else 1


if __name__ == "__main__":
    sys.exit(main())
