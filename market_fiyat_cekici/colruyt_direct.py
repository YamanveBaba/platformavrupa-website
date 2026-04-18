# -*- coding: utf-8 -*-
"""
colruyt_direct.py — Colruyt ürünlerini doğrudan API ile çeker.
Browser yok, Playwright yok. Sadece requests.
Çalıştır: python colruyt_direct.py
"""
import json, time, random
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"])
    import requests

SCRIPT_DIR = Path(__file__).parent
CIKTI_DIR  = SCRIPT_DIR / "cikti" / "html_pages"
CIKTI_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc/cg/nl/api/product-search-prs"
API_KEY  = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
PLACE_ID = 710
PAGE_SIZE = 48
MIN_DELAY = 2.5
MAX_DELAY = 4.5

HEADERS = {
    "accept": "*/*",
    "accept-language": "nl-BE,nl;q=0.9",
    "cache-control": "no-cache",
    "origin": "https://www.colruyt.be",
    "referer": "https://www.colruyt.be/",
    "x-cg-apikey": API_KEY,
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}


def load_cookies() -> dict:
    """colruyt_state.json'dan cookie dict yükle."""
    state_file = SCRIPT_DIR / "colruyt_state.json"
    if not state_file.exists():
        print("  colruyt_state.json bulunamadi! colruyt_cookies.json deneniyor...")
        # Fallback: colruyt_cookies.json
        cookie_file = SCRIPT_DIR / "colruyt_cookies.json"
        if not cookie_file.exists():
            print("  HATA: Cookie dosyasi yok!")
            return {}
        raw = json.loads(cookie_file.read_text(encoding="utf-8"))
        return {c["name"]: c["value"] for c in raw}

    saved = json.loads(state_file.read_text(encoding="utf-8"))
    cookies_list = saved.get("cookies", [])
    return {c["name"]: c["value"] for c in cookies_list}


def fetch_all(session: requests.Session) -> list:
    """
    Tüm Colruyt ürünlerini sayfalayarak çeker (kategori filtresi yok).
    category= parametresi aslında tüm kataloğu döndürüyor.
    Yavaş ilerle — reese84 cookie rate-limit (HTTP 456) yapar.
    """
    tum_urunler = []
    skip = 0
    MAX_RETRY = 3

    # Toplam ürün sayısını öğren
    try:
        r = session.get(API_BASE,
                        params={"placeId": PLACE_ID, "size": 1, "skip": 0, "isAvailable": "true"},
                        headers=HEADERS, timeout=15)
        total = r.json().get("totalProductsFound", 0)
        print(f"  Toplam katalog: {total} urun")
    except Exception as e:
        print(f"  Toplam sorgulama hatasi: {e}")
        total = 99999

    while skip < total:
        params = {
            "placeId": PLACE_ID,
            "size": PAGE_SIZE,
            "skip": skip,
            "isAvailable": "true",
        }

        retry = 0
        while retry < MAX_RETRY:
            try:
                r = session.get(API_BASE, params=params, headers=HEADERS, timeout=20)
                if r.status_code == 456:
                    bekleme = 30 + retry * 30
                    print(f"  HTTP 456 (antibot) — {bekleme}s bekleniyor...")
                    time.sleep(bekleme)
                    retry += 1
                    continue
                if r.status_code != 200:
                    print(f"  HTTP {r.status_code} — duruyorum")
                    return tum_urunler
                data = r.json()
                break
            except Exception as e:
                print(f"  Hata: {e}")
                retry += 1
                time.sleep(5)
        else:
            print("  Max retry asild, duruyorum")
            return tum_urunler

        prods = data.get("products", [])
        if not prods:
            break

        tum_urunler.extend(prods)
        total = data.get("totalProductsFound") or total
        print(f"  skip={skip} -> +{len(prods)} ({len(tum_urunler)}/{total})")

        skip += PAGE_SIZE
        # Sadece gerçekten bitmişse dur — API bazen PAGE_SIZE'dan az döner
        # ama toplam henüz tükenmemiş olabilir (erken durma bug fix)
        if not prods or skip >= total:
            break

        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    return tum_urunler


def colruyt_cek():
    cookies = load_cookies()
    if not cookies:
        print("Cookie yüklenemedi, çıkıyorum.")
        return

    print(f"  {len(cookies)} cookie yüklendi")

    session = requests.Session()
    session.cookies.update(cookies)

    # Önce test: parametresiz basit istek
    print("\n  --- API TEST ---")
    try:
        r = session.get(
            API_BASE,
            params={"placeId": PLACE_ID, "size": 2, "skip": 0, "isAvailable": "true"},
            headers=HEADERS, timeout=15
        )
        print(f"  Test isteği: HTTP {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            print(f"  Test yanıtı keys: {list(d.keys())[:8]}")
            print(f"  Test ürün sayısı: {len(d.get('products', []))}")
        else:
            print(f"  Test yanıt: {r.text[:200]}")
    except Exception as e:
        print(f"  Test hatası: {e}")
        return
    print("  --- TEST BITTI ---\n")

    print("\n  Tum katalog cekiliyor (yavash, 456 riski var)...")
    tum_urunler = fetch_all(session)

    print(f"\n  Toplam urun: {len(tum_urunler)}")

    if tum_urunler:
        tarih = datetime.now().strftime("%Y-%m-%d")
        dosya = CIKTI_DIR / f"colruyt_Genel_p01_{tarih}.json"
        dosya.write_text(
            json.dumps({"products": tum_urunler}, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"  Kaydedildi: {dosya.name}")
    else:
        print("  UYARI: Hic urun alinamadi!")
        print("  Colruyt sitesine gir, colruyt_cookies.json guncelle.")


if __name__ == "__main__":
    colruyt_cek()
