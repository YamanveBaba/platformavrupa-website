# -*- coding: utf-8 -*-
"""
ALDI Belçika - "Bu haftanın fırsatları" sayfasından teklifleri çıkarır (kaydedilmiş HTML).
Tarih başlıklarını (validFrom) ve ürün kartlarındaki data-article JSON'unu parse eder.
Çıktı: cikti/aldi_be_teklifler_*.json (platformda indirim listesi yayınlamak için).
"""

import json
import os
import re
import sys
from datetime import datetime

def parse_teklifler_html(html_path):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("HATA: beautifulsoup4 yüklü değil. Komut: pip install beautifulsoup4")
        return None

    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    teklifler = []
    seen_ids = set()

    # Tarih blokları: mod-offers__day with data-rel="2026-03-11" vb.
    day_sections = soup.find_all("div", class_="mod-offers__day", attrs={"data-rel": True})
    for section in day_sections:
        valid_from = section.get("data-rel", "").strip()  # "2026-03-11"
        if not re.match(r"\d{4}-\d{2}-\d{2}", valid_from):
            continue
        # Bu bloktaki tüm data-article'lı kartlar
        tiles = section.find_all(attrs={"data-article": True})
        for tile in tiles:
            raw = tile.get("data-article")
            if not raw:
                continue
            try:
                json_str = raw.replace("&quot;", '"')
                data = json.loads(json_str)
                info = data.get("productInfo") or {}
                pid = info.get("productID")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                # Kampanya tarihi (insan okunur) - aynı tile içinde olabilir
                promo_div = tile.find(class_="mod-article-tile__promotionData")
                valid_from_label = None
                if promo_div and promo_div.get("data-promotion-date-formatted-with-prefix"):
                    valid_from_label = promo_div["data-promotion-date-formatted-with-prefix"].strip()
                teklifler.append({
                    "productID": pid,
                    "productName": info.get("productName", ""),
                    "brand": info.get("brand", ""),
                    "priceWithTax": info.get("priceWithTax"),
                    "inPromotion": True,
                    "promotionDateMillis": info.get("promotionDate"),
                    "validFrom": valid_from,
                    "validFromLabel": valid_from_label,
                })
            except (json.JSONDecodeError, TypeError):
                continue

    # Eğer mod-offers__day yoksa veya boşsa, sayfadaki tüm data-article'ları topla (tarih bilinmez)
    if not teklifler:
        for tile in soup.find_all(attrs={"data-article": True}):
            raw = tile.get("data-article")
            if not raw:
                continue
            try:
                json_str = raw.replace("&quot;", '"')
                data = json.loads(json_str)
                info = data.get("productInfo") or {}
                pid = info.get("productID")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                if not info.get("inPromotion"):
                    continue
                promo_div = tile.find(class_="mod-article-tile__promotionData")
                valid_from_label = promo_div.get("data-promotion-date-formatted-with-prefix") if promo_div else None
                teklifler.append({
                    "productID": pid,
                    "productName": info.get("productName", ""),
                    "brand": info.get("brand", ""),
                    "priceWithTax": info.get("priceWithTax"),
                    "inPromotion": True,
                    "promotionDateMillis": info.get("promotionDate"),
                    "validFrom": None,
                    "validFromLabel": valid_from_label,
                })
            except (json.JSONDecodeError, TypeError):
                continue

    return teklifler

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    if len(sys.argv) >= 2:
        html_path = sys.argv[1]
    else:
        # Varsayılan: Downloads'taki dosya adı
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        html_path = os.path.join(downloads, "Bu haftanın fırsatları – ALDI Belçika.html")
        if not os.path.isfile(html_path):
            print("Kullanım: python parse_aldi_teklifler_html.py <kaydedilmis_teklifler.html>")
            print("Örnek: python parse_aldi_teklifler_html.py \"C:\\Users\\yaman\\Downloads\\Bu haftanın fırsatları – ALDI Belçika.html\"")
            input("\nÇıkmak için Enter...")
            return

    if not os.path.isfile(html_path):
        print("Dosya bulunamadı:", html_path)
        input("\nÇıkmak için Enter...")
        return

    print("HTML okunuyor:", html_path)
    teklifler = parse_teklifler_html(html_path)
    if teklifler is None:
        input("\nÇıkmak için Enter...")
        return

    print(f"Toplam {len(teklifler)} teklif bulundu.")

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya_adi = f"aldi_be_teklifler_{tarih}.json"
    dosya_yolu = os.path.join(cikti_dir, dosya_adi)

    cikti = {
        "kaynak": "ALDI Belçika - Bu haftanın fırsatları",
        "kaynak_url": "https://www.aldi.be/nl/onze-aanbiedingen.html",
        "cekilme_tarihi": datetime.now().isoformat(),
        "teklif_sayisi": len(teklifler),
        "not_gecerlilik": "validFrom: teklifin geçerli olduğu başlangıç tarihi (YYYY-MM-DD). validFromLabel: sayfadaki insan okunur metin.",
        "teklifler": teklifler,
    }

    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    print("Kaydedildi:", dosya_yolu)
    input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    main()
