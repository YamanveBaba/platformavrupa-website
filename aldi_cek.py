# -*- coding: utf-8 -*-
"""
Aldi BE — SingleFile Otomatik Çekim
Tüm kategori sayfalarını tarayıcıda açar.
SingleFile extension (auto-save=ON) her sayfayı otomatik kaydeder.

Kullanım:
  python aldi_cek.py          # Tüm kategorileri aç
  python aldi_cek.py --bekleme 15  # Sayfa başına 15sn bekle (yavaş internet için)
"""
import argparse
import subprocess
import time
import requests
from bs4 import BeautifulSoup

# Chrome yolları (Windows)
CHROME_YOLLARI = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(
        __import__('os').environ.get('USERNAME', '')
    ),
]

def chrome_bul():
    import os
    for yol in CHROME_YOLLARI:
        if os.path.isfile(yol):
            return yol
    return None

def chrome_ac(url):
    chrome = chrome_bul()
    if chrome:
        subprocess.Popen([chrome, url])
    else:
        print("  UYARI: Chrome bulunamadı, varsayılan tarayıcı kullanılıyor.")
        import webbrowser
        webbrowser.open(url)

ALDI_BASE = "https://www.aldi.be"

# Bilinen Aldi BE kategori URL'leri (ana sayfadan bulunamazsa fallback)
BILINEN_KATEGORILER = [
    "/nl/producten/assortiment/broodbeleg.html",
    "/nl/producten/assortiment/brood-bakkerij.html",
    "/nl/producten/assortiment/zuivel-eieren.html",
    "/nl/producten/assortiment/vlees-vis-gevogelte.html",
    "/nl/producten/assortiment/groenten-fruit.html",
    "/nl/producten/assortiment/dranken.html",
    "/nl/producten/assortiment/diepvries.html",
    "/nl/producten/assortiment/snacks-snoep.html",
    "/nl/producten/assortiment/koek-gebak.html",
    "/nl/producten/assortiment/koffie-thee.html",
    "/nl/producten/assortiment/ontbijtgranen-beleg.html",
    "/nl/producten/assortiment/pasta-rijst-granen.html",
    "/nl/producten/assortiment/sauzen-kruiden.html",
    "/nl/producten/assortiment/conserven-soepen.html",
    "/nl/producten/assortiment/biologisch.html",
    "/nl/producten/assortiment/huishouden.html",
    "/nl/producten/assortiment/wasmiddelen-reinigingsmiddelen.html",
    "/nl/producten/assortiment/persoonlijke-verzorging.html",
    "/nl/producten/assortiment/baby-kind.html",
    "/nl/producten/assortiment/dierenvoeding.html",
]


def kategorileri_bul():
    """Aldi ana sayfasından kategori URL'lerini çek."""
    print("[Kategoriler] Aldi ana sayfası taranıyor...")
    try:
        r = requests.get(
            f"{ALDI_BASE}/nl/",
            headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0"},
            timeout=15,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        kategoriler = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/nl/producten/assortiment/" in href and href.endswith(".html"):
                url = href if href.startswith("http") else ALDI_BASE + href
                if url not in kategoriler:
                    kategoriler.append(url)
        if kategoriler:
            print(f"  {len(kategoriler)} kategori bulundu.")
            return kategoriler
    except Exception as e:
        print(f"  Ana sayfa taranamadı: {e}")

    # Fallback: bilinen liste
    print(f"  Fallback: {len(BILINEN_KATEGORILER)} bilinen kategori kullanılıyor.")
    return [ALDI_BASE + k for k in BILINEN_KATEGORILER]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bekleme", type=int, default=12,
                    help="Her sayfa için bekleme süresi saniye (varsayılan: 12)")
    args = ap.parse_args()

    kategoriler = kategorileri_bul()

    print(f"\n{len(kategoriler)} kategori sayfası açılacak.")
    print(f"Her sayfa arası {args.bekleme} saniye bekleme.")
    print("SingleFile auto-save açık olduğundan emin ol!")
    print("\nBaşlamak için Enter'a bas...")
    input()

    for i, url in enumerate(kategoriler, 1):
        print(f"[{i}/{len(kategoriler)}] Açılıyor: {url}")
        chrome_ac(url)
        if i < len(kategoriler):
            time.sleep(args.bekleme)

    print(f"\nTamamlandı! {len(kategoriler)} sayfa açıldı.")
    print("Downloads klasöründe Aldi HTML dosyaları olmalı.")
    print("Şimdi: python aldi_parse.py")


if __name__ == "__main__":
    main()
