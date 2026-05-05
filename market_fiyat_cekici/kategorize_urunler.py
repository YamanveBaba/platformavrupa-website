"""
Supabase'deki market_chain_products ürünlerine otomatik L1-L4 kategori atar.

Mantık:
  1. Ürün adı (name) + mevcut category alanları normalize edilir
  2. Kural tablosu (KURALLAR) ile eşleştirilir — kural öncelik sırasıyla çalışır
  3. Eşleşen ilk kural kategori atar
  4. Supabase'e PATCH ile güncellenir

Çalıştırma:
  python kategorize_urunler.py              # tümünü kategorize et
  python kategorize_urunler.py --chain colruyt_be   # tek market
  python kategorize_urunler.py --limit 500          # test: ilk 500 ürün
  python kategorize_urunler.py --dry-run            # güncelleme yapma, sadece say
"""

from __future__ import annotations
import os
import sys
import json
import re
import argparse
import urllib.request
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from json_to_supabase_yukle import load_secrets

# ─────────────────────────────────────────────────────────────────────────────
# KATEGORİZASYON KURALLARI
# Her kural: (anahtar_kelimeler, dept_id, l2, l3, l4_ipucu)
# Kural sırası önemli — daha spesifik kurallar önce gelmeli.
# Anahtar kelimeler ürün adında (küçük harf) aranır — tümü bulunmalı (AND mantığı).
# | ile ayırırsanız OR mantığı olur: "trappist|abdijbier"
# ─────────────────────────────────────────────────────────────────────────────

KURALLAR: list[tuple[list[str], str, str, str, str]] = [

    # ── D01 Süt, Yumurta & Peynir ─────────────────────────────────────────
    # Özel önce
    (["herve"],                     "D01","Peynir","Belçika Peynirleri","Herve (AOP)"),
    (["chimay","kaas|fromage|cheese"],"D01","Peynir","Belçika Peynirleri","Chimay Peyniri"),
    (["passendale"],                "D01","Peynir","Belçika Peynirleri","Passendale"),
    (["orval","kaas|fromage"],      "D01","Peynir","Belçika Peynirleri","Orval Peyniri"),
    (["mozzarella"],                "D01","Peynir","Yumuşak & Taze Peynir","Mozzarella"),
    (["brie"],                      "D01","Peynir","Yumuşak & Taze Peynir","Brie"),
    (["camembert"],                 "D01","Peynir","Yumuşak & Taze Peynir","Camembert"),
    (["feta"],                      "D01","Peynir","Yumuşak & Taze Peynir","Feta"),
    (["gouda"],                     "D01","Peynir","Sert Peynir","Gouda"),
    (["emmental"],                  "D01","Peynir","Sert Peynir","Emmental"),
    (["parmesan|parmigiano"],       "D01","Peynir","Sert Peynir","Parmesan"),
    (["cheddar"],                   "D01","Peynir","Sert Peynir","Cheddar"),
    (["kaas|fromage|cheese"],       "D01","Peynir","Sert Peynir",""),
    (["luierbroekjes|couches-culottes|training pants"],"D13","Bebek Bakım","Bez & Islak Mendil","Bebek Bezi (5-6)"),
    (["eieren|oeufs|eggs|ei "],     "D01","Yumurta","Tavuk Yumurtası",""),
    (["kefir"],                     "D01","Yoğurt & Fermente","Fermente İçecekler","Kefir (İnek)"),
    (["skyr"],                      "D01","Yoğurt & Fermente","Fermente İçecekler","Skyr"),
    (["yogurt|yoğurt|yaourt"],      "D01","Yoğurt & Fermente","Yoğurt",""),
    (["boter|beurre|butter"],       "D01","Tereyağı & Yağlar","Tereyağı",""),
    (["ghee"],                      "D01","Tereyağı & Yağlar","Tereyağı","Ghee"),
    (["margarine|margarin"],        "D01","Tereyağı & Yağlar","Margarin & Bitkisel Yağ Spreadleri",""),
    (["room|crème|cream","slagroom|chantilly|whipped"],"D01","Krema & Tatlı Süt Ürünleri","Krema","Krem Şanti"),
    (["room|crème|cream"],          "D01","Krema & Tatlı Süt Ürünleri","Krema",""),
    (["havermelk|avoine|oat milk|oat drink"],"D01","Süt & Süt Alternatifleri","Bitki Bazlı Süt","Yulaf Sütü"),
    (["sojamelk|lait de soja|soy milk"],"D01","Süt & Süt Alternatifleri","Bitki Bazlı Süt","Soya Sütü"),
    (["amandelmelk|lait d'amande"],  "D01","Süt & Süt Alternatifleri","Bitki Bazlı Süt","Badem Sütü"),
    (["melk|lait|milk"],            "D01","Süt & Süt Alternatifleri","İnek Sütü",""),

    # ── D02 Et, Kümes & Balık ─────────────────────────────────────────────
    (["zalm|saumon|salmon"],        "D02","Balık & Deniz Ürünleri","Taze & Soğutmalı Balık","Somon"),
    (["kabeljauw|cabillaud|cod"],   "D02","Balık & Deniz Ürünleri","Taze & Soğutmalı Balık","Morina (Kabeljauw)"),
    (["heek|merlu"],                "D02","Balık & Deniz Ürünleri","Taze & Soğutmalı Balık",""),
    (["tonijn|thon|tuna"],          "D02","Balık & Deniz Ürünleri","Konserve & Marine","Ton Konservesi (Su)"),
    (["garnalen|crevettes|shrimp"], "D02","Balık & Deniz Ürünleri","Dondurulmuş Balık","Kariyer (Shrimp)"),
    (["mosselen|moules|mussels"],   "D02","Balık & Deniz Ürünleri","Dondurulmuş Balık","Midye"),
    (["vis|poisson|fish"],          "D02","Balık & Deniz Ürünleri","Taze & Soğutmalı Balık",""),
    (["ardennes|ardense","ham|jambon"],"D02","Domuz Eti","Şarküteri","Ardenne Jambon (IGP)"),
    (["filet américain|americain"], "D02","Domuz Eti","Şarküteri","Filet Américain"),
    (["salami"],                    "D02","Domuz Eti","Şarküteri","Salami"),
    (["ham|jambon"],                "D02","Domuz Eti","Şarküteri",""),
    (["gehakt|haché|minced","rund|boeuf|beef"],"D02","Sığır Eti","Taze Sığır","Kıyma (%20)"),
    (["gehakt|haché|minced"],       "D02","Domuz Eti","Taze Domuz","Kıyma"),
    (["biefstuk|entrecôte|steak"], "D02","Sığır Eti","Taze Sığır","Biftek (Entrecôte)"),
    (["kip|poulet|chicken"],        "D02","Kümes Hayvanları","Tavuk",""),
    (["kalkoen|dinde|turkey"],      "D02","Kümes Hayvanları","Diğer Kümes","Hindi Fileto"),
    (["frankfurters|knakworsten|knakworst|saucisse de francfort"],"D02","Domuz Eti","Taze Domuz","Sosis"),
    (["worsten|worstjes|saucisse|saucisson|worst "],"D02","Domuz Eti","Taze Domuz","Sosis"),
    (["haring|hareng|herring"],     "D02","Balık & Deniz Ürünleri","Konserve & Marine","Ringa (Haring)"),
    (["makreel|maquereau|mackerel"],"D02","Balık & Deniz Ürünleri","Konserve & Marine",""),
    (["sardines|sardiines"],        "D02","Balık & Deniz Ürünleri","Konserve & Marine","Sardalye"),
    (["ansjovis|anchois|anchovy"],  "D02","Balık & Deniz Ürünleri","Konserve & Marine","Hamsi"),
    (["paling|anguille|eel"],       "D02","Balık & Deniz Ürünleri","Kuzey Denizi Özel","Paling (Yılan Balığı)"),
    (["corned beef"],               "D02","Sığır Eti","Hazır Sığır",""),
    (["vlees|viande|meat"],         "D02","Sığır Eti","Taze Sığır",""),

    # ── D03 Meyve & Sebze ────────────────────────────────────────────────
    (["witloof|chicon|endive"],     "D03","Taze Sebze","Belçika Özgün Sebzeler","Witloof (Chicon/Belgian Endive)"),
    (["spruitjes|choux de bruxelles"],"D03","Taze Sebze","Belçika Özgün Sebzeler","Brüksel Lahanası"),
    (["champignons|paddenstoelen|mushroom"],"D03","Taze Sebze","Mantar","Beyaz Mantar"),
    (["shiitake"],                  "D03","Taze Sebze","Mantar","Shiitake"),
    (["tomaten|tomates|tomatoes"],  "D03","Taze Sebze","Meyve Sebze","Domates"),
    (["komkommer|concombre|cucumber"],"D03","Taze Sebze","Meyve Sebze","Salatalık"),
    (["paprika|poivron|pepper"],    "D03","Taze Sebze","Meyve Sebze","Biber"),
    (["courgette|zucchini"],        "D03","Taze Sebze","Meyve Sebze","Kabak"),
    (["wortelen|carottes|carrots"], "D03","Taze Sebze","Kök Sebze","Havuç"),
    (["aardappelen|pommes de terre|potato"],"D03","Taze Sebze","Kök Sebze","Patates"),
    (["uien|oignons|onion"],        "D03","Taze Sebze","Soğansılar","Soğan"),
    (["look|ail|garlic"],           "D03","Taze Sebze","Soğansılar","Sarımsak"),
    (["spinazie|épinards|spinach"], "D03","Taze Sebze","Yapraklı Sebze","Ispanak"),
    (["sla|laitue|salade","blad|feuille|leaf"],"D03","Taze Sebze","Yapraklı Sebze","Marul"),
    (["avocado"],                   "D03","Taze Sebze","Meyve Sebze","Avokado"),
    (["aardbeien|fraises|strawberry"],"D03","Taze Meyve","Mevsim Meyveleri","Çilek"),
    (["frambozen|framboises|raspberry"],"D03","Taze Meyve","Mevsim Meyveleri","Ahududu"),
    (["appels|pommes|apples"],      "D03","Taze Meyve","Mevsim Meyveleri","Elma"),
    (["peren|poires|pears"],        "D03","Taze Meyve","Mevsim Meyveleri","Armut"),
    (["bananen|bananes|banana"],    "D03","Taze Meyve","Tropikal & Egzotik","Muz"),
    (["mango"],                     "D03","Taze Meyve","Tropikal & Egzotik","Mango"),
    (["sinaasappel|orange"],        "D03","Taze Meyve","Turunçgiller","Portakal"),
    (["citroen|citron|lemon"],      "D03","Taze Meyve","Turunçgiller","Limon"),
    (["asperges|asparagus|spargelkohl"],"D03","Taze Sebze","Meyve Sebze",""),
    (["augurken|cornichons|gherkins|augurk"],"D03","Taze Sebze","Meyve Sebze","Salatalık"),
    (["sperziebonen|haricots verts|green beans"],"D03","Taze Sebze","Yapraklı Sebze",""),
    (["doperwten|petits pois|garden peas"],"D03","Taze Sebze","Meyve Sebze",""),
    (["rodekool|chou rouge|red cabbage"],"D03","Taze Sebze","Yapraklı Sebze","Kırmızı Lahana"),
    (["zuurkool|choucroute|sauerkraut"],"D03","Taze Sebze","Yapraklı Sebze",""),
    (["brocoli|broccoli"],          "D03","Taze Sebze","Yapraklı Sebze",""),
    (["bloemkool|choufleur|cauliflower"],"D03","Taze Sebze","Yapraklı Sebze","Karnabahar"),
    (["prinsessenbonen|haricots princesse"],"D03","Taze Sebze","Yapraklı Sebze",""),
    (["ananas|pineapple|ananas"],   "D03","Taze Meyve","Tropikal & Egzotik","Ananas"),
    (["perziken|pêches|peaches"],   "D03","Taze Meyve","Mevsim Meyveleri",""),
    (["abrikozen|abricots|apricots"],"D03","Taze Meyve","Mevsim Meyveleri",""),
    (["pruimen|prunes|plums"],      "D03","Taze Meyve","Mevsim Meyveleri","Erik"),
    (["groenten|légumes|vegetables"],"D03","Taze Sebze","Yapraklı Sebze",""),
    (["fruit"],                     "D03","Taze Meyve","Mevsim Meyveleri",""),

    # ── D04 Ekmek & Fırın ────────────────────────────────────────────────
    (["wafel|gaufre|waffle"],       "D04","Belçika Fırın","Belçika Waffle",""),
    (["pistolet"],                  "D04","Belçika Fırın","Pistolet & Brioche","Pistolet (Sert)"),
    (["brioche"],                   "D04","Belçika Fırın","Pistolet & Brioche","Brioche"),
    (["croissant"],                 "D04","Belçika Fırın","Pistolet & Brioche","Croissant"),
    (["pain au chocolat|chocoladebroodje"],"D04","Belçika Fırın","Pistolet & Brioche","Pain au Chocolat"),
    (["volkoren|complet|whole wheat"],"D04","Ekmek","Tam Buğday & Çok Tahıllı","Tam Buğday Ekmeği"),
    (["glutenvrij|sans gluten","brood|pain|bread"],"D04","Ekmek","Glutensiz & Özel","Glutensiz Ekmek"),
    (["stokbrood|baguette"],        "D04","Ekmek","Beyaz Ekmek","Baget"),
    (["brood|pain|bread"],          "D04","Ekmek","Beyaz Ekmek",""),
    (["cake|gâteau","slice|tranche|punt"],"D04","Pasta & Kek","Dilimli Kek",""),
    (["taart|tarte|torte"],         "D04","Pasta & Kek","Özel Pasta",""),

    # ── D05 Temel Bakkaliye ──────────────────────────────────────────────
    (["rijst|riz|rice","basmati"],  "D05","Tahıl & Makarna","Pirinç","Basmati"),
    (["rijst|riz|rice","jasmine"],  "D05","Tahıl & Makarna","Pirinç","Jasmine"),
    (["rijst|riz|rice"],            "D05","Tahıl & Makarna","Pirinç",""),
    (["pasta|spaghetti|penne|fusilli|tagliatelle","gluten"],"D05","Tahıl & Makarna","Makarna","Glutensiz Makarna"),
    (["spaghetti"],                 "D05","Tahıl & Makarna","Makarna","Spagetti"),
    (["penne"],                     "D05","Tahıl & Makarna","Makarna","Penne"),
    (["fusilli"],                   "D05","Tahıl & Makarna","Makarna","Fusilli"),
    (["pasta|pâtes"],               "D05","Tahıl & Makarna","Makarna",""),
    (["linzen|lentilles|lentils"],  "D05","Tahıl & Makarna","Tahıllar & Bakliyat","Mercimek (Kırmızı)"),
    (["kikkererwten|pois chiches|chickpeas"],"D05","Tahıl & Makarna","Tahıllar & Bakliyat","Nohut"),
    (["quinoa"],                    "D05","Tahıl & Makarna","Tahıllar & Bakliyat","Kinoa"),
    (["bulgur"],                    "D05","Tahıl & Makarna","Tahıllar & Bakliyat","Bulgur"),
    (["olijfolie|huile d'olive|olive oil"],"D05","Yağ & Sos","Bitkisel Yağlar","Zeytinyağı (Sızma)"),
    (["zonnebloemolie|tournesol|sunflower oil"],"D05","Yağ & Sos","Bitkisel Yağlar","Ayçiçek Yağı"),
    (["tomatensaus|sauce tomate|tomato sauce"],"D05","Yağ & Sos","Sos & Dressing","Domates Sosu"),
    (["pesto"],                     "D05","Yağ & Sos","Sos & Dressing","Pesto"),
    (["sojasaus|sauce soja|soy sauce"],"D05","Yağ & Sos","Sos & Dressing","Soya Sosu"),
    (["mosterd|moutarde|mustard"],  "D05","Yağ & Sos","Sirke & Hardal","Dijon Hardalı"),
    (["azijn|vinaigre|vinegar"],    "D05","Yağ & Sos","Sirke & Hardal",""),
    (["tomaten","blik|boîte|can"],  "D05","Konserve & Kavanoz","Domates Konserve",""),
    (["maïs|mais|corn","blik|boîte"],"D05","Konserve & Kavanoz","Sebze & Baklagil Konserve","Mısır Konserve"),
    (["olijven|olives"],            "D05","Konserve & Kavanoz","Sebze & Baklagil Konserve","Zeytin (Yeşil)"),
    (["kidneybonen|haricots rouges|kidney beans"],"D05","Konserve & Kavanoz","Sebze & Baklagil Konserve","Fasulye Konserve"),
    (["witte bonen|haricots blancs|white beans"],"D05","Konserve & Kavanoz","Sebze & Baklagil Konserve","Fasulye Konserve"),
    (["bruine bonen|haricots bruns"],"D05","Konserve & Kavanoz","Sebze & Baklagil Konserve","Fasulye Konserve"),
    (["erwtjes|pois|peas","blik|boîte|conserve"],"D05","Konserve & Kavanoz","Sebze & Baklagil Konserve","Bezelye Konserve"),
    (["passata|gezeefde tomaten|tomates passées"],"D05","Konserve & Kavanoz","Domates Konserve",""),
    (["ravioli","blik|boîte|conserve|ingeblikte"],"D05","Konserve Çorba & Hazır Fon","Çorba Konserve",""),
    (["appelcompote|compote de pommes|appelmoes"],"D09","Reçel & Bal","Reçel",""),
    (["nutella"],                   "D09","Süt Ürünleri Kahvaltı","Kahvaltılık Peynir & Ezmeler","Fıstık Ezmesi"),
    (["speculoospasta|pâte speculoos"],"D09","Süt Ürünleri Kahvaltı","Kahvaltılık Peynir & Ezmeler",""),
    (["zout|sel|salt"],             "D05","Baharat & Çeşni","Tuz & Şeker","Deniz Tuzu"),
    (["suiker|sucre|sugar"],        "D05","Baharat & Çeşni","Tuz & Şeker","Beyaz Şeker"),
    (["peper|poivre|pepper","kruid|épice|spice"],"D05","Baharat & Çeşni","Baharat","Kara Biber"),
    (["soep|soupe|soup"],           "D05","Konserve Çorba & Hazır Fon","Çorba Konserve",""),

    # ── D06 İçecekler ────────────────────────────────────────────────────
    # Bira — spesifik önce
    (["westvleteren"],              "D06","Bira","Trappist","Westvleteren 8"),
    (["westmalle","dubbel"],        "D06","Bira","Trappist","Westmalle Dubbel"),
    (["westmalle","tripel"],        "D06","Bira","Trappist","Westmalle Tripel"),
    (["westmalle"],                 "D06","Bira","Trappist","Westmalle Dubbel"),
    (["rochefort","10"],            "D06","Bira","Trappist","Rochefort 10"),
    (["rochefort","8"],             "D06","Bira","Trappist","Rochefort 8"),
    (["rochefort"],                 "D06","Bira","Trappist","Rochefort 6"),
    (["orval"],                     "D06","Bira","Trappist","Orval"),
    (["chimay","bleue|blauw|blue"], "D06","Bira","Trappist","Chimay Bleue"),
    (["chimay","rouge|rood|red"],   "D06","Bira","Trappist","Chimay Rouge"),
    (["chimay","triple|tripel"],    "D06","Bira","Trappist","Chimay Triple"),
    (["chimay"],                    "D06","Bira","Trappist","Chimay Rouge"),
    (["cantillon","gueuze"],        "D06","Bira","Lambic & Zuur","Gueuze (Cantillon)"),
    (["boon","gueuze"],             "D06","Bira","Lambic & Zuur","Gueuze (Boon)"),
    (["gueuze|geuze"],              "D06","Bira","Lambic & Zuur","Gueuze (Boon)"),
    (["kriek"],                     "D06","Bira","Lambic & Zuur","Kriek (Mariage Parfait)"),
    (["lambiek|lambic"],            "D06","Bira","Lambic & Zuur",""),
    (["leffe","tripel|triple"],     "D06","Bira","Abbij & Dubbel/Tripel","Leffe Tripel"),
    (["leffe","brune|bruin"],       "D06","Bira","Abbij & Dubbel/Tripel","Leffe Brune"),
    (["leffe"],                     "D06","Bira","Abbij & Dubbel/Tripel","Leffe Blonde"),
    (["tripel karmeliet"],          "D06","Bira","Özel & Artisanal","Tripel Karmeliet"),
    (["duvel","0.0|na|alcoholvrij"],"D06","Bira","Alkolsüz Bira","Duvel NA"),
    (["duvel"],                     "D06","Bira","Özel & Artisanal","Duvel (Strong Golden Ale)"),
    (["hoegaarden","0.0|alcoholvrij"],"D06","Bira","Alkolsüz Bira","Hoegaarden 0.0"),
    (["hoegaarden|blanche de bruxelles"],"D06","Bira","Wit & Saison","Hoegaarden Wit"),
    (["saison dupont"],             "D06","Bira","Wit & Saison","Saison Dupont"),
    (["grimbergen"],                "D06","Bira","Abbij & Dubbel/Tripel","Grimbergen"),
    (["jupiler","0.0|na|alcoholvrij"],"D06","Bira","Alkolsüz Bira","Jupiler NA"),
    (["jupiler"],                   "D06","Bira","Pilsner & Lager","Jupiler (Pils)"),
    (["stella artois","0.0|free"],  "D06","Bira","Alkolsüz Bira","Stella Artois Free"),
    (["stella artois"],             "D06","Bira","Pilsner & Lager","Stella Artois"),
    (["maes"],                      "D06","Bira","Pilsner & Lager","Maes"),
    (["primus"],                    "D06","Bira","Pilsner & Lager","Primus"),
    (["bier|bière|beer","alcoholvrij|0.0|sans alcool"],"D06","Bira","Alkolsüz Bira",""),
    (["bier|bière|beer"],           "D06","Bira","Pilsner & Lager",""),
    # Şarap
    (["wijn|vin|wine","rood|rouge|red"],"D06","Şarap","Kırmızı Şarap",""),
    (["wijn|vin|wine","wit|blanc|white"],"D06","Şarap","Beyaz Şarap",""),
    (["rosé|rosé wijn"],            "D06","Şarap","Rosé & Köpüklü","Provence Rosé"),
    (["champagne"],                 "D06","Şarap","Rosé & Köpüklü","Champagne"),
    (["prosecco"],                  "D06","Şarap","Rosé & Köpüklü","Prosecco"),
    (["cava"],                      "D06","Şarap","Rosé & Köpüklü","Cava"),
    (["crémant|cremant"],           "D06","Şarap","Rosé & Köpüklü","Crémant de Bourgogne"),
    (["wijn|vin|wine"],             "D06","Şarap","Kırmızı Şarap",""),
    # Spirits
    (["genever|jenever"],           "D06","Spirits & Likör","Jenever & Gin","Genever (Jong)"),
    (["gin"],                       "D06","Spirits & Likör","Jenever & Gin","Belgian Gin"),
    (["whisky|whiskey"],            "D06","Spirits & Likör","Whisky & Vodka","Scotch Whisky"),
    (["vodka"],                     "D06","Spirits & Likör","Whisky & Vodka","Vodka"),
    (["elixir d'anvers"],           "D06","Spirits & Likör","Likör & Aperitif","Elixir d'Anvers"),
    (["aperol"],                    "D06","Spirits & Likör","Likör & Aperitif","Aperol"),
    (["campari"],                   "D06","Spirits & Likör","Likör & Aperitif","Campari"),
    # İçecekler
    (["koffie|café|coffee","capsule|pods|kapsul"],"D06","Sıcak İçecek","Kahve","Espresso Kapsül (Nespresso)"),
    (["koffie|café|coffee"],        "D06","Sıcak İçecek","Kahve","Filtre Kahve"),
    (["thee|thé|tea"],              "D06","Sıcak İçecek","Çay","Siyah Çay"),
    (["rooibos"],                   "D06","Sıcak İçecek","Çay","Rooibos"),
    (["warme chocolade|chocolat chaud|hot chocolate"],"D06","Sıcak İçecek","Sıcak Çikolata & Malt",""),
    (["cola","0%|light|zero"],      "D06","Gazlı İçecek","Kola & Cola","Cola Light/Zero"),
    (["cola"],                      "D06","Gazlı İçecek","Kola & Cola","Cola Normal"),
    (["limonade|limonata|lemonade"],"D06","Gazlı İçecek","Limonata & Meyve Gazlı","Limonata"),
    (["energy drink|energiedrank"], "D06","Gazlı İçecek","Enerji & Spor","Enerji İçeceği"),
    (["sinaasappelsap|jus d'orange|orange juice"],"D06","Meyve Suyu","Taze & Soğutmalı","Portakal Suyu (Taze)"),
    (["appelsap|jus de pomme"],     "D06","Meyve Suyu","Uzun Ömürlü","Elma Suyu"),
    (["fruitsap|jus de fruit|fruit juice"],"D06","Meyve Suyu","Uzun Ömürlü",""),
    (["bruiswater|eau pétillante|sparkling water"],"D06","Su & Maden Suyu","Maden Suyu","Sparkling (Büyük)"),
    (["water|eau"],                 "D06","Su & Maden Suyu","Maden Suyu","Still (Büyük)"),

    # ── D07 Dondurulmuş ─────────────────────────────────────────────────
    (["diepvries|surgelé|frozen","pizza"],"D07","Dondurulmuş Hazır Yemek","Pizza",""),
    (["kroketten|croquettes|kroket"],"D07","Dondurulmuş Hazır Yemek","Kroket & Fritür","Belçika Kroket (Kabeljauw)"),
    (["friet|frites|fries","diepvries|surgelé|frozen"],"D07","Dondurulmuş Hazır Yemek","Kroket & Fritür","Frites (Dondurulmuş)"),
    (["ijs|glace|ice cream"],       "D07","Dondurulmuş Tatlı & Dondurma","Dondurma",""),
    (["diepvries|surgelé|frozen","groenten|légumes"],"D07","Dondurulmuş Sebze","Karışık & Tek",""),
    (["diepvries|surgelé|frozen","vis|poisson|fish"],"D07","Dondurulmuş Et & Balık","Dondurulmuş Balık",""),
    (["diepvries|surgelé|frozen"],  "D07","Dondurulmuş Et & Balık","Dondurulmuş Et",""),

    # ── D08 Atıştırmalık & Şekerleme ────────────────────────────────────
    (["neuhaus","praline|chocolade|chocolat"],"D15","Belçika Çikolatası","Pralineler & Kutu Çikolata","Neuhaus Selection"),
    (["leonidas"],                  "D15","Belçika Çikolatası","Pralineler & Kutu Çikolata","Leonidas Pralineler"),
    (["godiva"],                    "D15","Belçika Çikolatası","Pralineler & Kutu Çikolata","Godiva Pralineler"),
    (["marcolini"],                 "D15","Belçika Çikolatası","Pralineler & Kutu Çikolata","Markolini Pralineler"),
    (["côte d'or|cote d or"],       "D08","Çikolata","Tablet Çikolata",""),
    (["praline|pralinés"],          "D15","Belçika Çikolatası","Pralineler & Kutu Çikolata",""),
    (["chocolade|chocolat|chocolate","tablet|bar|reep"],"D08","Çikolata","Tablet Çikolata",""),
    (["speculoos|speculaas"],       "D15","Belçika Bisküvi & Waffle","Geleneksel Bisküvi","Speculoos (Lotus)"),
    (["jules destrooper"],          "D15","Belçika Bisküvi & Waffle","Geleneksel Bisküvi","Jules Destrooper"),
    (["biscuit|koek|cookie","gluten"],"D08","Bisküvi & Kek","Belçika Bisküvileri",""),
    (["chips|crisps|cipsi"],        "D08","Cips & Tuzlu Atıştırmalık","Patates Cipsi",""),
    (["popcorn"],                   "D08","Cips & Tuzlu Atıştırmalık","Mısır & Diğer","Popcorn"),
    (["noten|noix|nuts"],           "D08","Fındık & Kuru Meyve","Fındık Karışımı",""),
    (["rozijnen|raisins|kuru üzüm"],"D08","Fındık & Kuru Meyve","Kuru Meyve","Kuru Üzüm"),
    (["snoep|bonbon|candy"],        "D08","Şekerleme & Gummy","Şekerleme & Gummy",""),
    (["biscuit|koek|bisküvi|koekjes"],"D08","Bisküvi & Kek","Belçika Bisküvileri",""),
    (["wafels|gaufres|waffles"],    "D08","Bisküvi & Kek","Belçika Bisküvileri",""),
    (["rijstwafels|galettes de riz"],"D08","Cips & Tuzlu Atıştırmalık","Mısır & Diğer","Pirinç Galeti"),
    (["marsepein|massepain|marzipan"],"D08","Şekerleme & Gummy","Şekerleme & Gummy",""),
    (["drop|réglisse|licorice"],    "D08","Şekerleme & Gummy","Şekerleme & Gummy",""),

    # ── D09 Kahvaltılık ─────────────────────────────────────────────────
    (["granola"],                   "D09","Mısır Gevreği","Yetişkin Gevrekleri","Granola"),
    (["muesli"],                    "D09","Mısır Gevreği","Yetişkin Gevrekleri","Muesli"),
    (["cornflakes|corn flakes|special k|all-bran"],"D09","Mısır Gevreği","Yetişkin Gevrekleri",""),
    (["graanvlokken|céréales|cereal"],"D09","Mısır Gevreği","Çocuk Gevrekleri",""),
    (["havermout|flocons d'avoine|oat"],"D09","Yulaf & Sıcak Tahıl","Yulaf Ezmesi","Rolled Oats"),
    (["confituur|confiture|jam"],   "D09","Reçel & Bal","Reçel",""),
    (["honing|miel|honey"],         "D09","Reçel & Bal","Bal & Şurup","Çiçek Balı"),
    (["ahornsiroop|sirop d'érable|maple"],"D09","Reçel & Bal","Bal & Şurup","Akçaağaç Şurubu"),
    (["pindakaas|beurre de cacahuètes|peanut butter"],"D09","Süt Ürünleri Kahvaltı","Kahvaltılık Peynir & Ezmeler","Fıstık Ezmesi"),
    (["tahin|tahina|sesampasta"],   "D09","Süt Ürünleri Kahvaltı","Kahvaltılık Peynir & Ezmeler","Tahin"),

    # ── D10 Hazır Yemek ─────────────────────────────────────────────────
    (["waterzooi"],                 "D10","Soğutmalı Hazır Yemek","Belçika Geleneksel","Waterzooi"),
    (["stoemp"],                    "D10","Soğutmalı Hazır Yemek","Belçika Geleneksel","Stoemp"),
    (["chicons","gratin"],          "D10","Soğutmalı Hazır Yemek","Belçika Geleneksel","Chicons au Gratin"),
    (["carbonnade|stoofvlees"],     "D10","Soğutmalı Hazır Yemek","Belçika Geleneksel","Carbonnade Flamande"),
    (["sushi"],                     "D10","Soğutmalı Hazır Yemek","Uluslararası","Sushi"),
    (["ravioli|tortellini|gnocchi"],"D10","Soğutmalı Hazır Yemek","Uluslararası",""),
    (["quiche"],                    "D10","Soğutmalı Hazır Yemek","Belçika Geleneksel",""),
    (["maaltijd|plat|meal","gekoeld|réfrigéré"],"D10","Soğutmalı Hazır Yemek","Uluslararası",""),
    (["sandwich|boterham","klaargem|prêt"],"D10","Sandviç & Wrap","Hazır Sandviç",""),
    (["salade|salad","verse|frais|fresh"],"D10","Salata & Meze","Hazır Salata",""),
    (["raclette"],                  "D10","Soğutmalı Spesiyaller","Raclette & Fondue","Raclette Peyniri (Dilimli)"),
    (["fondue"],                    "D10","Soğutmalı Spesiyaller","Raclette & Fondue","Fondue Fromage Karışımı"),

    # ── D11 Ev Temizliği ────────────────────────────────────────────────
    (["wasmiddel|lessive|laundry","capsule|pods"],"D11","Çamaşır","Çamaşır Deterjanı","Kapsül (Pods)"),
    (["wasmiddel|lessive|laundry","vloeibaar|liquide|liquid"],"D11","Çamaşır","Çamaşır Deterjanı","Sıvı Deterjan"),
    (["wasmiddel|lessive|laundry"], "D11","Çamaşır","Çamaşır Deterjanı","Toz Deterjan"),
    (["wasverzachter|adoucissant|fabric softener"],"D11","Çamaşır","Yumuşatıcı & Ek","Kumaş Yumuşatıcı"),
    (["wc reiniger|nettoyant wc|toilet cleaner"],"D11","Ev Temizliği","Özel Yüzey","Tuvalet Temizleyici"),
    (["allesreiniger|nettoyant multi|multipurpose"],"D11","Ev Temizliği","Çok Amaçlı Temizleyici",""),
    (["wc papier|papier wc|toilet paper"],"D11","Kağıt & Tek Kullanım","Kağıt Ürünleri","Tuvalet Kağıdı"),
    (["keukenpapier|essuie-tout|kitchen roll"],"D11","Kağıt & Tek Kullanım","Kağıt Ürünleri","Kağıt Havlu"),

    # ── D12 Kişisel Bakım ────────────────────────────────────────────────
    (["shampoo|shampooing"],        "D12","Saç Bakımı","Şampuan & Saç Kremi","Normal Şampuan"),
    (["conditioner|après-shampoing"],"D12","Saç Bakımı","Şampuan & Saç Kremi","Saç Kremi"),
    (["tandpasta|dentifrice|toothpaste"],"D12","Diş & Ağız","Diş Bakımı","Diş Macunu (Florürlü)"),
    (["deodorant|deo"],             "D12","Deodorant & Parfüm","Deodorant","Roll-On"),
    (["douchegel|gel douche|shower gel"],"D12","Vücut Bakımı","Duş & Banyo","Duş Jeli"),
    (["bodylotion|lotion corporelle|body lotion"],"D12","Vücut Bakımı","Nemlendirici & Losyon","Vücut Losyonu"),
    (["handcrème|crème mains|hand cream"],"D12","Vücut Bakımı","Nemlendirici & Losyon","El Kremi"),
    (["scheergel|gel à raser|shaving gel"],"D12","Hijyen","Tıraş & Erkek Bakımı","Tıraş Jeli"),
    (["maandverband|serviette hygiénique|pad"],"D12","Hijyen","Feminen Hijyen","Ped"),
    (["gezichtscrème|crème visage|face cream"],"D12","Makyaj & Güzellik","Cilt Bakımı","Nemlendirici Krem"),
    (["zonnebrand|crème solaire|sunscreen"],"D12","Vücut Bakımı","Nemlendirici & Losyon","Güneş Koruma (SPF30)"),

    # ── D13 Bebek & Çocuk ───────────────────────────────────────────────
    (["babymelk|lait pour bébé|baby formula"],"D13","Bebek Gıda","Bebek Sütü & Formül","Başlangıç Formülü (0-6ay)"),
    (["babypuree|purée bébé|baby puree"],"D13","Bebek Gıda","Mama & Püreler","Sebze Püresi (4ay+)"),
    (["luiers|couches|diapers"],    "D13","Bebek Bakım","Bez & Islak Mendil","Bebek Bezi (3-4)"),
    (["snoetenpoetsers|nettoyants visage bébé"],"D13","Bebek Bakım","Bebek Bakım Ürünleri",""),
    (["babydoekjes|lingettes bébé|baby wipes"],"D13","Bebek Bakım","Bez & Islak Mendil","Islak Mendil"),
    (["babyshampoo|shampoo bébé"],  "D13","Bebek Bakım","Bebek Bakım Ürünleri","Bebek Şampuanı"),

    # ── D14 Evcil Hayvan ───────────────────────────────────────────────
    (["kattenvoer|nourriture chat|cat food","droog|sec|dry"],"D14","Kedi","Kedi Maması","Kuru Mama (Yetişkin)"),
    (["kattenvoer|nourriture chat|cat food","nat|humide|wet"],"D14","Kedi","Kedi Maması","Yaş Mama (Küçük Kap)"),
    (["kattenvoer|nourriture chat|cat food"],"D14","Kedi","Kedi Maması",""),
    (["kattenbak|litière|cat litter"],"D14","Aksesuar & Kum","Kedi Kumu & Temizlik","Topaklanan Kum"),
    (["hondenvoer|nourriture chien|dog food","droog|sec|dry"],"D14","Köpek","Köpek Maması","Kuru Mama (Yetişkin)"),
    (["hondenvoer|nourriture chien|dog food"],"D14","Köpek","Köpek Maması",""),

    # ── D15 Belçika Özgün ───────────────────────────────────────────────
    (["sinterklaas","chocolade|snoep|koek"],"D15","Mevsimsel Ürünler","Sinterklaas (5-6 Aralık)",""),
    (["kerstmis|noël|noel","chocolade|koek|biscuit"],"D15","Mevsimsel Ürünler","Noel & Yılbaşı",""),
    (["pasen|pâques|easter","chocolade|ei"],"D15","Mevsimsel Ürünler","Paskalya",""),
    (["belge|belgique|belgian","chocolade|chocolat|chocolate"],"D15","Belçika Çikolatası","Tablet & Bar",""),
    (["jenever","appel|peer|framboos"],"D15","Belçika Jenever & Likörü","Jenever","Appeljenever"),
    (["jenever|genever"],           "D15","Belçika Jenever & Likörü","Jenever","Genever Jong"),
    (["elixir d'anvers"],           "D15","Belçika Jenever & Likörü","Belçika Likörleri","Elixir d'Anvers"),
    (["mandarine napoléon"],        "D15","Belçika Jenever & Likörü","Belçika Likörleri","Mandarine Napoléon"),
    (["hageland","wijn|vin"],       "D15","Belçika Şarabı & Cidre","Belçika Şarabı","Hageland Chardonnay"),
    (["stassen|elmer|liefmans","cidre|cider"],"D15","Belçika Şarabı & Cidre","Belçika Elma Şarabı",""),

    # ── D16 Etnik & Uluslararası ─────────────────────────────────────────
    (["kombucha"],                  "D16","Fermente & Fonksiyonel","Kombucha & Kefir","Kombucha (Original)"),
    (["kimchi"],                    "D16","Fermente & Fonksiyonel","Miso & Natto","Kimchi"),
    (["miso"],                      "D16","Fermente & Fonksiyonel","Miso & Natto","Shiro Miso (Beyaz)"),
    (["tempeh"],                    "D16","Fermente & Fonksiyonel","Miso & Natto","Tempeh"),
    (["nori|zeewier|algue"],        "D16","Asya","Japon & Kore Gıdası","Nori (Deniz Yosunu)"),
    (["gochujang"],                 "D16","Asya","Japon & Kore Gıdası","Gochujang"),
    (["sushi","rijst|riz|rice"],    "D16","Asya","Japon & Kore Gıdası","Sushi Pirinci"),
    (["wasabi"],                    "D16","Asya","Japon & Kore Gıdası","Wasabi"),
    (["hoisin|oyster sauce|oestersaus"],"D16","Asya","Çin & Thai Gıdası","Oyster Sosu"),
    (["fish sauce|vissaus|nuoc mam"],"D16","Asya","Çin & Thai Gıdası","Fish Sauce"),
    (["noodles|noedels","ramen|udon|soba"],"D16","Asya","Japon & Kore Gıdası","Ramen Noodle"),
    (["couscous"],                  "D16","Kuzey Afrika","Fas & Tunus & Cezayir Gıdası","Kuskus (İnce)"),
    (["harissa"],                   "D16","Kuzey Afrika","Kuzey Afrika","Harissa (Acı)"),
    (["ras el hanout"],             "D16","Kuzey Afrika","Fas Baharat & Soslar","Ras El Hanout"),
    (["medjool|dadels|dattes"],     "D16","Kuzey Afrika","Fas & Tunus & Cezayir Gıdası","Medjool Hurması"),
    (["pide|lavash|lavaş"],         "D16","Türk & Orta Doğu","Türk Gıda Ürünleri","Pide Ekmeği"),
    (["helva|halva"],               "D16","Türk & Orta Doğu","Türk Gıda Ürünleri","Helva (Susam)"),
    (["lokum|loukoum|turkish delight"],"D16","Türk & Orta Doğu","Türk Gıda Ürünleri","Lokum (Gül)"),
    (["tahini|tahin","sesam"],      "D16","Türk & Orta Doğu","Baharat & Sos (Türk/Orta Doğu)","Tahini"),
    (["hummus|houmous"],            "D16","Türk & Orta Doğu","Baharat & Sos (Türk/Orta Doğu)","Humus (Hazır)"),
    (["tortilla","mais|maïs|corn"], "D16","Latin Amerika","Meksika & Orta Amerika","Tortilla (Mısır)"),
    (["tortilla"],                  "D16","Latin Amerika","Meksika & Orta Amerika","Tortilla (Buğday)"),
    (["yerba mate|yerba maté"],     "D16","Latin Amerika","Güney Amerika","Yerba Mate"),
    (["garam masala|tandoori|curry paste"],"D16","Asya","Hint Gıdası","Garam Masala"),
    (["basmati","premium|hindi|india"],"D16","Asya","Hint Gıdası","Basmati Pirinci (Premium)"),
    (["kielbasa|kabanosy"],         "D16","Doğu Avrupa & Balkan","Polonya & Çek Gıdası","Kielbasa Sosis"),
    (["ajvar|ayvar"],               "D16","Doğu Avrupa & Balkan","Balkan & Türk Türevi","Ayvar (Kırmızı)"),
    (["burek|börek"],               "D16","Doğu Avrupa & Balkan","Balkan & Türk Türevi","Burek (Dondurulmuş)"),
]


# ─────────────────────────────────────────────────────────────────────────────
# KURAL EŞLEŞTİRME
# ─────────────────────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", (text or "").lower())


# ── Katman 2: category_name haritalama ────────────────────────────────────────
# (alt_dize_listesi, dept_id, l2, l3, l4)
# category_name alanındaki değerlere göre eşleştirme.
CATEGORY_NAME_MAP: list[tuple[list[str], str, str, str, str]] = [
    # Aldi v2 kodları
    (["v2can"],  "D05","Konserve & Kavanoz","Domates Konserve",""),
    (["v2alc"],  "D06","Bira","Pilsner & Lager",""),
    (["v2ape"],  "D06","Spirits & Likör","Likör & Aperitif",""),
    (["v2con"],  "D08","Bisküvi & Kek","Belçika Bisküvileri",""),
    (["v2cle"],  "D11","Ev Temizliği","Çok Amaçlı Temizleyici",""),
    (["v2bab"],  "D13","Bebek Bakım","Bez & Islak Mendil",""),
    (["v2bak"],  "D04","Ekmek","Beyaz Ekmek",""),
    (["v2hyg"],  "D12","Kişisel Bakım & Hijyen","Duş & Banyo",""),
    (["v2dri"],  "D06","Su & Maden Suyu","Maden Suyu",""),
    (["v2win"],  "D06","Şarap","Kırmızı Şarap",""),
    (["v2sal"],  "D10","Salata & Meze","Hazır Salata",""),
    (["v2non"],  "D11","Ev Temizliği","Kağıt & Tek Kullanım",""),
    (["v2mea"],  "D02","Et, Kümes & Balık","Kümes Hayvanları",""),
    (["v2swe"],  "D08","Şekerleme & Gummy","Şekerleme & Gummy",""),
    (["v2fru"],  "D03","Taze Meyve","Mevsim Meyveleri",""),
    (["v2fro"],  "D07","Dondurulmuş Et & Balık","Dondurulmuş Et",""),
    (["v2dai"],  "D01","Süt & Süt Alternatifleri","İnek Sütü",""),
    (["v2bre"],  "D04","Ekmek","Beyaz Ekmek",""),
    (["v2veg"],  "D03","Taze Sebze","Yapraklı Sebze",""),
    (["v2chk"],  "D02","Kümes Hayvanları","Tavuk",""),
    (["v2snk"],  "D08","Cips & Tuzlu Atıştırmalık","Patates Cipsi",""),
    (["v2pet"],  "D14","Köpek","Köpek Maması",""),
    (["v2cer"],  "D09","Mısır Gevreği","Yetişkin Gevrekleri",""),
    (["v2oil"],  "D05","Yağ & Sos","Bitkisel Yağlar",""),
    (["v2pas"],  "D05","Tahıl & Makarna","Makarna",""),
    (["v2ric"],  "D05","Tahıl & Makarna","Pirinç",""),
    (["v2spr"],  "D08","Cips & Tuzlu Atıştırmalık","Mısır & Diğer",""),
    (["v2san"],  "D10","Sandviç & Wrap","Hazır Sandviç",""),
    (["v2egg"],  "D01","Yumurta","Tavuk Yumurtası",""),
    (["v2che"],  "D01","Peynir","Sert Peynir",""),
    # Okunabilir NL kategori isimleri
    (["zuivel"],                 "D01","Süt & Süt Alternatifleri","İnek Sütü",""),
    (["eieren"],                 "D01","Yumurta","Tavuk Yumurtası",""),
    (["kaas","verse"],           "D01","Peynir","Yumuşak & Taze Peynir",""),
    (["kaas"],                   "D01","Peynir","Sert Peynir",""),
    (["vlees","charcuterie"],    "D02","Domuz Eti","Şarküteri",""),
    (["colruyt-beenhouwerij"],   "D02","Sığır Eti","Taze Sığır",""),
    (["vlees"],                  "D02","Sığır Eti","Taze Sığır",""),
    (["bereidingen","vis"],      "D02","Balık & Deniz Ürünleri","Taze & Soğutmalı Balık",""),
    (["groenten en fruit"],      "D03","Taze Sebze","Yapraklı Sebze",""),
    (["groenten"],               "D03","Taze Sebze","Yapraklı Sebze",""),
    (["fruit"],                  "D03","Taze Meyve","Mevsim Meyveleri",""),
    (["brood","bakkerij"],       "D04","Ekmek","Beyaz Ekmek",""),
    (["bakkerij"],               "D04","Belçika Fırın","Pistolet & Brioche",""),
    (["kruidenierswaren","droge voeding"], "D05","Tahıl & Makarna","Makarna",""),
    (["dips","sauzen","dressing"],"D05","Yağ & Sos","Sos & Dressing",""),
    (["kruiden","smaakversterkers"],"D05","Baharat & Çeşni","Baharat",""),
    (["pasta","sauzen"],         "D05","Yağ & Sos","Sos & Dressing",""),
    (["dranken"],                "D06","Su & Maden Suyu","Maden Suyu",""),
    (["wijn"],                   "D06","Şarap","Kırmızı Şarap",""),
    (["rode-wijn","rode wijn"],  "D06","Şarap","Kırmızı Şarap",""),
    (["witte-wijn","witte wijn"],"D06","Şarap","Beyaz Şarap",""),
    (["bier"],                   "D06","Bira","Pilsner & Lager",""),
    (["frisdrank"],              "D06","Gazlı İçecek","Kola & Cola",""),
    (["koffie"],                 "D06","Sıcak İçecek","Kahve",""),
    (["thee"],                   "D06","Sıcak İçecek","Çay",""),
    (["diepvries","pizza"],      "D07","Dondurulmuş Hazır Yemek","Pizza",""),
    (["diepvries"],              "D07","Dondurulmuş Et & Balık","Dondurulmuş Et",""),
    (["koeken","chocolade"],     "D08","Çikolata","Tablet Çikolata",""),
    (["koeken","snoep"],         "D08","Şekerleme & Gummy","Şekerleme & Gummy",""),
    (["chips","snacks"],         "D08","Cips & Tuzlu Atıştırmalık","Patates Cipsi",""),
    (["ontbijt","granen"],       "D09","Mısır Gevreği","Yetişkin Gevrekleri",""),
    (["koelvers","bereid"],      "D10","Soğutmalı Hazır Yemek","Uluslararası",""),
    (["onderhoud","huishouden"], "D11","Ev Temizliği","Çok Amaçlı Temizleyici",""),
    (["wasmiddelen"],            "D11","Çamaşır","Çamaşır Deterjanı",""),
    (["papier","hygiene"],       "D11","Kağıt & Tek Kullanım","Kağıt Ürünleri",""),
    (["lichaamsverzorging","parfumerie"],"D12","Vücut Bakımı","Duş & Banyo",""),
    (["mondverzorging"],         "D12","Diş & Ağız","Diş Bakımı",""),
    (["haarverzorging"],         "D12","Saç Bakımı","Şampuan & Saç Kremi",""),
    (["baby"],                   "D13","Bebek Bakım","Bez & Islak Mendil",""),
    (["dierenvoeding","huisdieren"],"D14","Köpek","Köpek Maması",""),
    (["promoties"],              "D08","Şekerleme & Gummy","Şekerleme & Gummy",""),  # fallback
    # Non-food: sport, outdoor, bike, DIY → D99
    (["sport","vrije tijd"],     "D99","Diğer / Non-Food","Spor & Outdoor",""),
    (["fietsen"],                "D99","Diğer / Non-Food","Ulaşım",""),
    (["kamperen"],               "D99","Diğer / Non-Food","Spor & Outdoor",""),
    (["doe-het-zelf","tuin"],    "D99","Diğer / Non-Food","Bahçe & Yapı",""),
    (["motor","auto"],           "D99","Diğer / Non-Food","Ulaşım",""),
]

# Zincire göre genel fallback (hiçbir kural uymasa bile)
CHAIN_FALLBACK = {
    "colruyt_be":  ("D05","Temel Bakkaliye","Konserve & Kavanoz",""),
    "delhaize_be": ("D05","Temel Bakkaliye","Konserve & Kavanoz",""),
    "carrefour_be":("D05","Temel Bakkaliye","Konserve & Kavanoz",""),
    "lidl_be":     ("D05","Temel Bakkaliye","Konserve & Kavanoz",""),
    "aldi_be":     ("D05","Temel Bakkaliye","Konserve & Kavanoz",""),
}
GENEL_FALLBACK = ("D05","Temel Bakkaliye","Konserve & Kavanoz","")


def kategorize_et(name: str, extra: str = "", category_name: str = "", chain: str = "") -> tuple[str, str, str, str]:
    """
    3 katmanlı kategorizasyon. Her zaman bir sonuç döner (fallback sayesinde).
    Katman 1: ürün adı keyword eşleşmesi
    Katman 2: category_name alanı haritalama
    Katman 3: zincir fallback
    """
    # Katman 1
    hay = normalize_text(name + " " + extra)
    for anahtar_list, d_id, l2, l3, l4 in KURALLAR:
        tum_eslesti = True
        for anahtar in anahtar_list:
            alternatifler = [a.strip() for a in anahtar.split("|")]
            if not any(alt in hay for alt in alternatifler if alt):
                tum_eslesti = False
                break
        if tum_eslesti:
            return (d_id, l2, l3, l4)

    # Katman 2: category_name haritalama
    cat_hay = normalize_text(category_name)
    for anahtar_list, d_id, l2, l3, l4 in CATEGORY_NAME_MAP:
        tum_eslesti = True
        for anahtar in anahtar_list:
            if anahtar not in cat_hay:
                tum_eslesti = False
                break
        if tum_eslesti:
            return (d_id, l2, l3, l4)

    # Katman 3: zincir fallback
    return CHAIN_FALLBACK.get(chain, GENEL_FALLBACK)


# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────────────────────

def supabase_get(url: str, key: str, path: str, params: dict) -> list:
    query = urllib.parse.urlencode(params)
    req_url = f"{url}/rest/v1/{path}?{query}"
    req = urllib.request.Request(
        req_url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Prefer": "count=exact",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def supabase_patch_batch(url: str, key: str, rows: list[dict]) -> int:
    """
    Kategori değerlerine göre gruplar, her grup için tek PATCH:
      PATCH /market_chain_products?id=in.(1,2,3)
      Body: {category_l1, category_l2, category_l3, category_l4}
    Bu yöntem NOT NULL kısıtlaması sorununu önler.
    """
    if not rows:
        return 0

    # (l1, l2, l3, l4) → [id listesi]
    gruplar: dict[tuple, list[int]] = {}
    for row in rows:
        key_tuple = (
            row.get("category_l1", ""),
            row.get("category_l2", ""),
            row.get("category_l3", ""),
            row.get("category_l4") or "",
        )
        gruplar.setdefault(key_tuple, []).append(row["id"])

    toplam = 0
    for (l1, l2, l3, l4), id_list in gruplar.items():
        # PostgREST: id=in.(1,2,3)
        id_str = ",".join(str(i) for i in id_list)
        patch_url = f"{url}/rest/v1/market_chain_products?id=in.({id_str})"
        body = {"category_l1": l1, "category_l2": l2, "category_l3": l3}
        if l4:
            body["category_l4"] = l4
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            patch_url,
            data=payload,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                toplam += len(id_list)
        except urllib.error.HTTPError as e:
            body_err = e.read().decode(errors="replace")
            print(f"  [ERR] PATCH: HTTP {e.code} — {body_err[:200]}")
    return toplam


# ─────────────────────────────────────────────────────────────────────────────
# ANA DÖNGÜ
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", default=None, help="Belirli bir market (örn. colruyt_be)")
    parser.add_argument("--limit", type=int, default=0, help="Maksimum ürün sayısı (0=tümü)")
    parser.add_argument("--dry-run", action="store_true", help="Güncelleme yapma, sadece say")
    parser.add_argument("--force", action="store_true", help="Zaten kategorize edilenleri de işle")
    args = parser.parse_args()

    url, key = load_secrets(SCRIPT_DIR)
    print(f"Supabase: {url}")

    # Ürünleri sayfalı çek
    SAYFA = 1000
    offset = 0
    tum_urunler: list[dict] = []

    while True:
        params: dict = {
            "select": "id,external_product_id,chain_slug,name,category_name",
            "order": "id.asc",
            "offset": offset,
            "limit": SAYFA,
        }
        if args.chain:
            params["chain_slug"] = f"eq.{args.chain}"
        if not args.force and not args.dry_run:
            # category_l1 sutunu varsa sadece null olanlari al
            params["category_l1"] = "is.null"

        try:
            sayfa = supabase_get(url, key, "market_chain_products", params)
        except Exception as e:
            print(f"Supabase okuma hatasi: {e}")
            break

        if not sayfa:
            break
        tum_urunler.extend(sayfa)
        print(f"  Yuklendi: {len(tum_urunler)} urun...", end="\r")

        if args.limit and len(tum_urunler) >= args.limit:
            tum_urunler = tum_urunler[:args.limit]
            break
        if len(sayfa) < SAYFA:
            break
        offset += SAYFA

    print(f"\nToplam isleme alinacak: {len(tum_urunler)} urun")
    if not tum_urunler:
        print("Kategorize edilecek urun yok.")
        return

    # Kategorize et
    katman1 = 0
    katman2 = 0
    katman3 = 0
    guncelle_batch: list[dict] = []
    BATCH_BOYUT = 200

    for urun in tum_urunler:
        name = urun.get("name", "")
        chain = urun.get("chain_slug", "")
        cat_name = urun.get("category_name", "") or ""

        # Katman 1: sadece isim
        hay = normalize_text(name)
        k1_sonuc = None
        for anahtar_list, d_id, l2, l3, l4 in KURALLAR:
            tum_eslesti = True
            for anahtar in anahtar_list:
                alternatifler = [a.strip() for a in anahtar.split("|")]
                if not any(alt in hay for alt in alternatifler if alt):
                    tum_eslesti = False
                    break
            if tum_eslesti:
                k1_sonuc = (d_id, l2, l3, l4)
                break

        if k1_sonuc:
            d_id, l2, l3, l4 = k1_sonuc
            katman1 += 1
        else:
            # Katman 2: category_name
            cat_hay = normalize_text(cat_name)
            k2_sonuc = None
            for anahtar_list, d_id, l2, l3, l4 in CATEGORY_NAME_MAP:
                tum_eslesti = True
                for anahtar in anahtar_list:
                    if anahtar not in cat_hay:
                        tum_eslesti = False
                        break
                if tum_eslesti:
                    k2_sonuc = (d_id, l2, l3, l4)
                    break

            if k2_sonuc:
                d_id, l2, l3, l4 = k2_sonuc
                katman2 += 1
            else:
                # Katman 3: fallback
                d_id, l2, l3, l4 = CHAIN_FALLBACK.get(chain, GENEL_FALLBACK)
                katman3 += 1

        if not args.dry_run:
            guncelle_batch.append({
                "id": urun["id"],
                "category_l1": d_id,
                "category_l2": l2,
                "category_l3": l3,
                "category_l4": l4 or None,
                "chain_slug": chain,
                "external_product_id": urun["external_product_id"],
            })
            if len(guncelle_batch) >= BATCH_BOYUT:
                guncellenen = supabase_patch_batch(url, key, guncelle_batch)
                print(f"  [OK] {guncellenen} urun guncellendi (K1:{katman1} K2:{katman2} K3:{katman3})")
                guncelle_batch = []

    # Kalan batch
    if guncelle_batch and not args.dry_run:
        guncellenen = supabase_patch_batch(url, key, guncelle_batch)
        print(f"  [OK] {guncellenen} urun guncellendi (son batch)")

    toplam = len(tum_urunler)
    print()
    print(f"Sonuc ({toplam} urun):")
    print(f"  Katman 1 (isim kurali): {katman1} urun ({100*katman1/toplam:.1f}%)")
    print(f"  Katman 2 (category_name): {katman2} urun ({100*katman2/toplam:.1f}%)")
    print(f"  Katman 3 (fallback): {katman3} urun ({100*katman3/toplam:.1f}%)")
    print(f"  TOPLAM kategorize: {katman1+katman2+katman3} urun (%100)")
    if args.dry_run:
        print("  (dry-run modu — hicbir guncelleme yapilmadi)")


if __name__ == "__main__":
    main()
