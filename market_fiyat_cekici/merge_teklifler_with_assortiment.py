# -*- coding: utf-8 -*-
"""
Teklifler (bu haftanın indirimleri) ile tam ürün listesini birleştirir.
- Platform için: Tüm ürünler + indirimde olanlara promo alanları (arama/karşılaştırma için tam fiyat listesi).
- Ayrı yayın için: Sadece indirimde olanlar listesi (geçerlilik tarihiyle).
"""

import json
import os
import glob
import sys
from datetime import datetime

def find_latest_json(pattern, cikti_dir):
    files = glob.glob(os.path.join(cikti_dir, pattern))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def find_latest_json_any(patterns, cikti_dir):
    """Birden fazla glob; en yeni değiştirilmiş dosyayı döndürür (tam katalog / eski ad)."""
    best = None
    best_mtime = -1.0
    for pat in patterns:
        for path in glob.glob(os.path.join(cikti_dir, pat)):
            try:
                m = os.path.getmtime(path)
            except OSError:
                continue
            if m > best_mtime:
                best_mtime = m
                best = path
    return best

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    # Girdi dosyaları: argüman veya en son çekilen
    teklifler_path = sys.argv[1] if len(sys.argv) >= 2 else find_latest_json("aldi_be_teklifler_*.json", cikti_dir)
    assortiment_path = (
        sys.argv[2]
        if len(sys.argv) >= 3
        else find_latest_json_any(
            ("aldi_be_tum_yeme_icme_*.json", "aldi_be_tam_katalog_*.json"),
            cikti_dir,
        )
    )

    if not teklifler_path or not os.path.isfile(teklifler_path):
        print("Teklifler JSON bulunamadı. Önce parse_aldi_teklifler_html.py çalıştırın.")
        input("\nÇıkmak için Enter...")
        return
    if not assortiment_path or not os.path.isfile(assortiment_path):
        print("Assortiment JSON bulunamadı. Önce aldi_tum_yeme_icme_cek.py çalıştırın.")
        input("\nÇıkmak için Enter...")
        return

    with open(teklifler_path, "r", encoding="utf-8") as f:
        teklif_data = json.load(f)
    with open(assortiment_path, "r", encoding="utf-8") as f:
        assortiment_data = json.load(f)

    teklifler = teklif_data.get("teklifler", [])
    urunler = list(assortiment_data.get("urunler", []))

    # productID -> teklif kaydı
    teklif_by_id = {t["productID"]: t for t in teklifler}

    # Platform için: tüm ürünler, indirimde olanlara ek alanlar
    indirimde_olanlar = []
    for u in urunler:
        pid = u.get("productID")
        t = teklif_by_id.get(pid)
        if t:
            u["inPromotion"] = True
            u["promoPrice"] = t.get("priceWithTax")
            u["promoValidFrom"] = t.get("validFrom")
            u["promoValidFromLabel"] = t.get("validFromLabel")
            indirimde_olanlar.append({**u})
        else:
            u["inPromotion"] = u.get("inPromotion", False)

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # 1) Tüm ürünler (platform: arama/karşılaştırma - herkes fiyat görsün)
    platform_path = os.path.join(cikti_dir, f"aldi_be_tum_urunler_platform_{tarih}.json")
    platform_out = {
        "kaynak": "ALDI Belçika",
        "chain_slug": "aldi_be",
        "country_code": "BE",
        "aciklama": "Tüm ürün fiyatları; indirimde olanlarda promo alanları dolu. Platformda arama ve karşılaştırma için kullanılır.",
        "cekilme_tarihi": assortiment_data.get("cekilme_tarihi"),
        "teklif_birlestirme_tarihi": datetime.now().isoformat(),
        "toplam_urun": len(urunler),
        "indirimde_olan_sayisi": len(indirimde_olanlar),
        "urunler": urunler,
    }
    with open(platform_path, "w", encoding="utf-8") as f:
        json.dump(platform_out, f, ensure_ascii=False, indent=2)
    print("Platform (tüm fiyatlar):", platform_path)

    # 2) Sadece indirimde olanlar (ayrı yayın: "Bu haftanın indirimleri")
    indirim_path = os.path.join(cikti_dir, f"aldi_be_indirimde_olanlar_{tarih}.json")
    indirim_out = {
        "kaynak": "ALDI Belçika - Bu haftanın fırsatları",
        "chain_slug": "aldi_be",
        "country_code": "BE",
        "aciklama": "Sadece bu hafta indirimde olan ürünler; geçerlilik tarihiyle. Platformda ayrı liste olarak yayınlanır.",
        "gecerlilik_notu": "validFrom / promoValidFrom: teklifin geçerli olduğu başlangıç tarihi.",
        "guncelleme_tarihi": datetime.now().isoformat(),
        "adet": len(indirimde_olanlar),
        "urunler": indirimde_olanlar,
    }
    with open(indirim_path, "w", encoding="utf-8") as f:
        json.dump(indirim_out, f, ensure_ascii=False, indent=2)
    print("İndirimde olanlar (yayın listesi):", indirim_path)

    print(f"\nToplam {len(urunler)} ürün, {len(indirimde_olanlar)} tanesi bu hafta indirimde.")
    input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    main()
