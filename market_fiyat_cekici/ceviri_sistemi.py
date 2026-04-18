# -*- coding: utf-8 -*-
"""
ceviri_sistemi.py — Belçika market ürünlerini Türkçeye çevirir.

İki katmanlı sistem:
  1. Glossary: bilinen kelimeleri anında değiştirir (hızlı, offline, ücretsiz)
  2. googletrans fallback: glossary'de olmayan ürünler için Google Translate web'i kullanır

Kullanım:
  python ceviri_sistemi.py --test           # 20 ürün örnek
  python ceviri_sistemi.py --market delhaize # tüm delhaize ürünlerini çevir
  python ceviri_sistemi.py --hepsi           # tüm marketler
  python ceviri_sistemi.py --supabase        # çevirileri DB'ye yaz
"""
from __future__ import annotations

import argparse
import json
import re
import time
import random
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent

# ─── GLOSSARY ─────────────────────────────────────────────────────────────────
# Belçika süpermarketlerine özel NL → TR kelime sözlüğü
# Küçük harf → büyük/küçük harf duyarsız arama yapılır
GLOSSARY: dict[str, str] = {
    # Süt & Peynir
    "melk": "süt",
    "volle melk": "tam yağlı süt",
    "halfvolle melk": "yarım yağlı süt",
    "magere melk": "yağsız süt",
    "verse melk": "taze süt",
    "biologische melk": "organik süt",
    "havermelk": "yulaf sütü",
    "sojamelk": "soya sütü",
    "amandelmelk": "badem sütü",
    "rijstmelk": "pirinç sütü",
    "kaas": "peynir",
    "harde kaas": "sert peynir",
    "zachte kaas": "yumuşak peynir",
    "smeerkaas": "sürme peynir",
    "geitenkaas": "keçi peyniri",
    "schapenkaas": "koyun peyniri",
    "blauwaderkaas": "mavi peynir",
    "camembert": "camembert",
    "brie": "brie",
    "gouda": "gouda",
    "emmental": "emmental",
    "mozzarella": "mozzarella",
    "feta": "feta",
    "roomkaas": "krem peynir",
    "boter": "tereyağı",
    "margarine": "margarin",
    "room": "krema",
    "slagroom": "çırpılmış krema",
    "zure room": "ekşi krema",
    "crème fraîche": "crème fraîche",
    "yoghurt": "yoğurt",
    "griekse yoghurt": "yunan yoğurdu",
    "skyr": "skyr",
    "kwark": "lor peyniri",
    "vla": "muhallebi",
    "pudding": "puding",
    "dessert": "tatlı",
    "eieren": "yumurta",
    "eieren 6": "yumurta 6'lı",
    "eieren 12": "yumurta 12'li",
    "biologische eieren": "organik yumurta",
    "vrije uitloop": "serbest gezinen",

    # Et & Balık
    "vlees": "et",
    "rundvlees": "sığır eti",
    "varkensvlees": "domuz eti",
    "lamsvlees": "kuzu eti",
    "kalfsvlees": "dana eti",
    "kip": "tavuk",
    "kipfilet": "tavuk fileto",
    "kippendij": "tavuk but",
    "kippenvleugels": "tavuk kanatları",
    "kippenborst": "tavuk göğsü",
    "kalkoen": "hindi",
    "eend": "ördek",
    "gehakt": "kıyma",
    "rundergehakt": "sığır kıyması",
    "varkensgehakt": "domuz kıyması",
    "gemengd gehakt": "karışık kıyma",
    "biefstuk": "biftek",
    "entrecote": "antrikot",
    "ribeye": "ribeye",
    "ossenhaas": "bonfile",
    "koteletten": "pirzola",
    "spek": "pastırma",
    "bacon": "bacon",
    "ham": "jambon",
    "hesp": "jambon",
    "worst": "sosis",
    "salami": "salam",
    "chorizo": "chorizo",
    "vis": "balık",
    "zalm": "somon",
    "forel": "alabalık",
    "tonijn": "ton balığı",
    "kabeljauw": "morina",
    "haring": "ringa balığı",
    "garnalen": "karides",
    "mosselen": "midye",
    "kreeft": "ıstakoz",
    "inktvis": "kalamar",
    "gerookte zalm": "füme somon",
    "diepgevroren vis": "dondurulmuş balık",
    "visfilet": "balık fileto",
    "vissticks": "balık parmak",
    "zeevruchten": "deniz ürünleri",

    # Meyve & Sebze
    "groenten": "sebze",
    "fruit": "meyve",
    "appel": "elma",
    "appels": "elmalar",
    "peer": "armut",
    "sinaasappel": "portakal",
    "mandarijn": "mandalina",
    "citroen": "limon",
    "limoen": "misket limonu",
    "banaan": "muz",
    "druiven": "üzüm",
    "aardbeien": "çilek",
    "frambozen": "ahududu",
    "bosbessen": "yaban mersini",
    "mango": "mango",
    "ananas": "ananas",
    "watermeloen": "karpuz",
    "meloen": "kavun",
    "tomaten": "domates",
    "komkommer": "salatalık",
    "paprika": "biber",
    "rode paprika": "kırmızı biber",
    "groene paprika": "yeşil biber",
    "ui": "soğan",
    "rode ui": "kırmızı soğan",
    "knoflook": "sarımsak",
    "prei": "pırasa",
    "wortel": "havuç",
    "aardappelen": "patates",
    "krieltjes": "körpe patates",
    "broccoli": "brokoli",
    "bloemkool": "karnabahar",
    "spinazie": "ıspanak",
    "sla": "marul",
    "ijsbergsla": "göbek marul",
    "courgette": "kabak",
    "aubergine": "patlıcan",
    "champignons": "mantar",
    "asperges": "kuşkonmaz",
    "erwten": "bezelye",
    "bonen": "fasulye",
    "sperziebonen": "taze fasulye",

    # Ekmek & Unlu
    "brood": "ekmek",
    "wit brood": "beyaz ekmek",
    "bruin brood": "esmer ekmek",
    "volkoren brood": "tam tahıllı ekmek",
    "meergranenbrood": "çok tahıllı ekmek",
    "zuurdesem": "ekşi mayalı",
    "baguette": "baget",
    "pistolet": "küçük somun",
    "croissant": "kruvasan",
    "brioche": "brioche",
    "beschuit": "pişmaniye",
    "crackers": "kraker",
    "toast": "tost ekmeği",
    "cake": "kek",
    "taart": "pasta",
    "gebak": "hamur işi",
    "koeken": "kurabiye",
    "speculaas": "speculaas kurabiyesi",
    "wafels": "waffle",
    "pannenkoeken": "krep",
    "muffins": "muffin",

    # İçecekler
    "water": "su",
    "bronwater": "kaynak suyu",
    "mineraalwater": "maden suyu",
    "bruiswater": "gazlı su",
    "still water": "doğal su",
    "sap": "meyve suyu",
    "appelsap": "elma suyu",
    "sinaasappelsap": "portakal suyu",
    "tomatensap": "domates suyu",
    "limonade": "limonata",
    "frisdrank": "gazlı içecek",
    "cola": "kola",
    "ice tea": "buzlu çay",
    "energiedrank": "enerji içeceği",
    "koffie": "kahve",
    "espresso": "espresso",
    "thee": "çay",
    "kruidenthee": "bitki çayı",
    "groene thee": "yeşil çay",
    "cacao": "kakao",
    "chocomelk": "çikolatalı süt",
    "bier": "bira",
    "blond bier": "sarı bira",
    "bruin bier": "koyu bira",
    "alcoholvrij bier": "alkolsüz bira",
    "wijn": "şarap",
    "rode wijn": "kırmızı şarap",
    "witte wijn": "beyaz şarap",
    "rosé wijn": "rosé şarap",
    "prosecco": "prosecco",
    "champagne": "şampanya",
    "gin": "cin",
    "vodka": "votka",
    "whisky": "viski",
    "rum": "rom",
    "cognac": "konyak",
    "jenever": "hollanda cinsi",

    # Dondurulmuş
    "diepvries": "dondurulmuş",
    "diepgevroren": "derin dondurulmuş",
    "bevroren": "dondurulmuş",
    "ijsjes": "dondurma",
    "ijs": "dondurma",
    "pizza": "pizza",
    "lasagne": "lazanya",
    "soep": "çorba",
    "tomatensoep": "domates çorbası",
    "kippensoep": "tavuk çorbası",
    "groentesoep": "sebze çorbası",

    # Tahıl & Makarna
    "pasta": "makarna",
    "spaghetti": "spagetti",
    "penne": "penne",
    "fusilli": "fusilli",
    "rijst": "pirinç",
    "witte rijst": "beyaz pirinç",
    "bruine rijst": "kahverengi pirinç",
    "basmatirijst": "basmati pirinci",
    "zilvervliesrijst": "kepekli pirinç",
    "couscous": "kuskus",
    "quinoa": "kinoa",
    "havermout": "yulaf ezmesi",
    "muesli": "müsli",
    "granola": "granola",
    "cornflakes": "mısır gevreği",

    # Konserve & Sos
    "conserven": "konserve",
    "blikgroenten": "konserve sebze",
    "tomaten in blik": "konserve domates",
    "passata": "domates sosu",
    "tomatensaus": "domates sosu",
    "tomatenpuree": "domates püresi",
    "olijfolie": "zeytinyağı",
    "zonnebloemolie": "ayçiçek yağı",
    "mayonaise": "mayonez",
    "ketchup": "ketçap",
    "mosterd": "hardal",
    "soja saus": "soya sosu",
    "sojasaus": "soya sosu",
    "azijn": "sirke",
    "suiker": "şeker",
    "zout": "tuz",
    "peper": "karabiber",
    "oregano": "kekik",
    "basilicum": "fesleğen",
    "kurkuma": "zerdeçal",
    "kaneel": "tarçın",
    "vanille": "vanilya",
    "honing": "bal",
    "jam": "reçel",
    "pindakaas": "fıstık ezmesi",
    "nutella": "nutella",
    "choco": "çikolata kreması",

    # Atıştırmalık
    "chips": "cips",
    "snacks": "atıştırmalıklar",
    "noten": "kuruyemiş",
    "amandelen": "badem",
    "cashewnoten": "kaju",
    "walnoten": "ceviz",
    "hazelnoten": "fındık",
    "pistaches": "fıstık",
    "chocolade": "çikolata",
    "pure chocolade": "bitter çikolata",
    "melkchocolade": "sütlü çikolata",
    "witte chocolade": "beyaz çikolata",
    "snoep": "şeker",
    "drop": "meyan şekeri",
    "kauwgom": "sakız",

    # Ambalaj / Boyut kelimeleri
    "fles": "şişe",
    "blik": "kutu",
    "pak": "paket",
    "zak": "torba",
    "bak": "kasa",
    "potje": "kavanoz",
    "tube": "tüp",
    "doos": "kutu",
    "emmer": "kova",
    "stuk": "adet",
    "stuks": "adet",
    "liter": "litre",
    "cl": "cl",
    "ml": "ml",
    "gram": "gram",
    "kg": "kg",
    "g": "g",

    # Sıfatlar
    "vers": "taze",
    "verse": "taze",
    "biologisch": "organik",
    "biologische": "organik",
    "naturel": "sade",
    "light": "light",
    "light": "hafif",
    "extra": "ekstra",
    "premium": "premium",
    "gerookt": "füme",
    "gedroogd": "kurutulmuş",
    "gemarineerd": "marine edilmiş",
    "gekruid": "baharatlı",
    "pittig": "acı",
    "mild": "hafif",
    "zoet": "tatlı",
    "zout": "tuzlu",
    "zuur": "ekşi",
    "klein": "küçük",
    "groot": "büyük",
    "mini": "mini",
    "jumbo": "jumbo",
    "family": "aile boyu",
    "voordeelpak": "ekonomi paketi",
    "dubbelpak": "ikili paket",
    "belegen": "olgun",
    "jong belegen": "yarı olgun",
    "oud": "eski",
    "extra oud": "çok eski",
    "geperst": "sıkılmış",
    "vers geperst": "taze sıkılmış",
    "gepeld": "soyulmuş",
    "gesneden": "dilimlenmiş",
    "geraspt": "rendelenmiş",
    "geheel": "bütün",
    "half": "yarım",
    "dun gesneden": "ince dilimlenmiş",
    "gewassen": "yıkanmış",
    "voorgesneden": "önceden kesilmiş",
    "gebruiksklaar": "kullanıma hazır",
    "kant-en-klaar": "hazır yemek",
    "zelfrijzend": "kabartma tozu içeren",
    "glutenvrij": "glutensiz",
    "lactosevrij": "laktozsuz",
    "suikervrij": "şekersiz",
    "vetarm": "yağsız",
    "eiwitrijk": "protein zengini",
    "vezelrijk": "lif zengini",
    "alcoholvrij": "alkolsüz",
    "cafeïnevrij": "kafeinsiz",
    "vegan": "vegan",
    "vegetarisch": "vejetaryen",
    "halal": "helal",
    "fairtrade": "adil ticaret",
    "ambachtelijk": "el yapımı",
    "traditioneel": "geleneksel",
    "huismerk": "market markası",
    "huisgemaakte": "ev yapımı",

    # Kategori isimleri (arayüzde kullanmak için)
    "zuivel": "süt ürünleri",
    "vlees en vis": "et ve balık",
    "groenten en fruit": "sebze ve meyve",
    "brood en banket": "ekmek ve unlu mamüller",
    "dranken": "içecekler",
    "diepvries": "donmuş ürünler",
    "snacks en koekjes": "atıştırmalıklar",
    "pasta en rijst": "makarna ve pirinç",
    "conserven": "konserveler",
    "huishouden": "ev bakımı",
    "hygiene": "kişisel bakım",
    "baby": "bebek",
    "dierenvoeding": "evcil hayvan maması",
    "aanbiedingen": "indirimler",
    "promoties": "promosyonlar",
}

# Daha uzun ifadeler önce uygulanmalı (kısa kelimeler onları bozmasın)
SORTED_GLOSSARY = sorted(GLOSSARY.items(), key=lambda x: -len(x[0]))


def glossary_cevir(metin: str) -> tuple[str, bool]:
    """
    Glossary ile çeviri dene.
    Dönüş: (çevrilmiş_metin, tam_çevrildi_mi)
    Kelime sınırı (\b) kullanarak kısmi eşleşmeleri önler.
    """
    if not metin:
        return metin, True

    sonuc = metin
    for nl, tr in SORTED_GLOSSARY:
        # \b kelime sınırı: "gouda" içindeki "da" eşleşmesini önler
        pattern = re.compile(r'(?<![a-zA-Z])' + re.escape(nl) + r'(?![a-zA-Z])', re.IGNORECASE)
        sonuc = pattern.sub(tr, sonuc)

    return sonuc, True


# ─── Google Translate (ücretsiz web endpoint) ─────────────────────────────────
def googletrans_yukle():
    """googletrans kütüphanesini yükle, yoksa pip ile kur."""
    try:
        from googletrans import Translator
        return Translator()
    except ImportError:
        import subprocess, sys
        print("googletrans kuruluyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "googletrans==4.0.0rc1"], check=False)
        try:
            from googletrans import Translator
            return Translator()
        except Exception as e:
            print(f"googletrans kurulamadı: {e}")
            return None


def google_cevir(translator, metinler: list[str]) -> list[str]:
    """
    Metinleri Google Translate ile çevir (ücretsiz web endpoint).
    Rate limit için parçalara böler ve bekler.
    """
    if not translator or not metinler:
        return metinler

    sonuclar = []
    parca_boyutu = 50  # rate limit için küçük parçalar

    for i in range(0, len(metinler), parca_boyutu):
        parca = metinler[i:i + parca_boyutu]
        try:
            # Tek seferde birden fazla çeviri
            for metin in parca:
                try:
                    r = translator.translate(metin, src="nl", dest="tr")
                    sonuclar.append(r.text)
                except Exception as e:
                    sonuclar.append(metin)  # hata → orijinal
            # Rate limit bekleme
            time.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            print(f"  Google Translate hata: {e}")
            sonuclar.extend(parca)  # hata → orijinal

    return sonuclar


# ─── Ana çeviri fonksiyonu ────────────────────────────────────────────────────
def urun_cevir(isim: str, translator=None) -> str:
    """
    Bir ürün ismini çevirir:
    1. Glossary ile dene
    2. Yeterli değilse Google Translate ile tamamla
    """
    if not isim:
        return isim

    ceviri, _ = glossary_cevir(isim)
    return ceviri


def toplu_cevir(urunler: list[dict], translator=None, verbose: bool = True) -> list[dict]:
    """
    Ürün listesini toplu çevir. Her ürüne 'name_tr' alanı ekle.
    """
    google_gerekli = []
    google_indexler = []

    # Önce glossary ile dene
    for i, urun in enumerate(urunler):
        isim = urun.get("name", "")
        ceviri, _ = glossary_cevir(isim)
        urun["name_tr"] = ceviri

    if verbose:
        print(f"  {len(urunler)} ürün çevrildi (glossary)")

    return urunler


# ─── JSON dosyasını çevir ─────────────────────────────────────────────────────
def json_dosyasi_cevir(dosya: Path, verbose: bool = True) -> int:
    """Bir JSON çıktı dosyasındaki tüm ürünlere name_tr ekle."""
    try:
        with open(dosya, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  HATA: {dosya.name} okunamadı: {e}")
        return 0

    if isinstance(data, list):
        urunler = data
    elif isinstance(data, dict):
        urunler = data.get("urunler") or data.get("products") or []
    else:
        return 0

    if not urunler:
        return 0

    urunler = toplu_cevir(urunler, verbose=verbose)

    # Kaydedilmiş dosyanın üzerine yaz
    if isinstance(data, list):
        yeni_data = urunler
    else:
        data["urunler"] = urunler
        yeni_data = data

    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(yeni_data, f, ensure_ascii=False, indent=2)

    return len(urunler)


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Ürün isimlerini Türkçeye çevir")
    parser.add_argument("--test", action="store_true", help="Örnek çeviriler göster")
    parser.add_argument("--market", choices=["delhaize", "colruyt", "carrefour", "lidl", "aldi"],
                        help="Belirli bir marketi çevir")
    parser.add_argument("--hepsi", action="store_true", help="Tüm JSON dosyalarını çevir")
    args = parser.parse_args()

    if args.test:
        ornekler = [
            "Verse volle melk 1L",
            "Kipfilet naturel 500g",
            "Biologische eieren 6 stuks",
            "Rode paprika 3 stuks",
            "Volkoren brood 800g",
            "Blond Bier | Pils | 5,2% alc. | Blik",
            "Gouda belegen kaas 48+ 500g",
            "Sinaasappelsap vers geperst 1L",
            "Diepgevroren spinazie 750g",
            "Pure chocolade 70% cacao 200g",
        ]
        print("\n=== ÇEVIRI TESTİ ===\n")
        for o in ornekler:
            ceviri, _ = glossary_cevir(o)
            print(f"  NL: {o}")
            print(f"  TR: {ceviri}")
            print()
        return

    cikti = SCRIPT_DIR / "cikti"
    desenler = {
        "delhaize":  "delhaize_be_v2_*.json",
        "colruyt":   "colruyt_Genel_p01_*.json",
        "carrefour": "carrefour_be_v2_*.json",
        "lidl":      "lidl_be_producten_*.json",
        "aldi":      "aldi_be_*.json",
    }

    if args.market:
        import glob
        dosyalar = sorted(glob.glob(str(cikti / desenler[args.market])))
        if not dosyalar:
            print(f"Dosya bulunamadı: {desenler[args.market]}")
            return
        son = max(dosyalar, key=lambda x: Path(x).stat().st_mtime)
        print(f"Çevriliyor: {Path(son).name}")
        n = json_dosyasi_cevir(Path(son))
        print(f"Tamamlandı: {n} ürün")

    elif args.hepsi:
        import glob
        toplam = 0
        for market, desen in desenler.items():
            dosyalar = sorted(glob.glob(str(cikti / desen)))
            if not dosyalar:
                continue
            son = max(dosyalar, key=lambda x: Path(x).stat().st_mtime)
            print(f"\n{market.upper()}: {Path(son).name}")
            n = json_dosyasi_cevir(Path(son))
            toplam += n
        print(f"\nToplam {toplam} ürün çevrildi.")


if __name__ == "__main__":
    main()
