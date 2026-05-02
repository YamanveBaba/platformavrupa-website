# -*- coding: utf-8 -*-
"""
Market ürünlerine Türkçe kategori atar (category_tr sütunu).

Supabase'den name + category_name okur, KATEGORI_MAP + KEYWORD_FALLBACK ile
Türkçe kategori hesaplar, toplu PATCH ile geri yazar.

Kullanım:
  python market_kategorile.py              # tüm ürünler
  python market_kategorile.py --dry-run    # DB'ye yazma, sadece istatistik
  python market_kategorile.py --limit 500  # test amaçlı
"""
import argparse, os, re, sys
try:
    import requests
except ImportError:
    print("HATA: pip install requests"); sys.exit(1)

BATCH_SIZE = 500
MAX_IDS    = 400

# ─── Supabase ────────────────────────────────────────────────────────────────
def load_secrets():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        print("HATA: SUPABASE_URL veya SUPABASE_SERVICE_ROLE_KEY eksik"); sys.exit(1)
    return url, key

# ─── Kategori Haritası (Hollandaca scraper kategori adı → Türkçe) ─────────────
KATEGORI_MAP = {
    # Süt Ürünleri
    "zuivel": "Süt Ürünleri",
    "melk-en-melkvervangers": "Süt Ürünleri",
    "melk en melkvervangers": "Süt Ürünleri",
    "yoghurt-verse-kaas-en-desserts": "Süt Ürünleri",
    "yoghurt verse kaas en desserts": "Süt Ürünleri",
    "kaas-zuivel": "Süt Ürünleri",
    "kaas": "Süt Ürünleri",
    "melk": "Süt Ürünleri",
    "categorie v2dai": "Süt Ürünleri",
    "categorie v2kaz": "Süt Ürünleri",
    # Et & Şarküteri
    "vlees": "Et & Şarküteri",
    "vlees-worst": "Et & Şarküteri",
    "bereidingen/charcuterie/vis/veggie": "Et & Şarküteri",
    "bereidingen charcuterie vis veggie": "Et & Şarküteri",
    "charcuterie": "Et & Şarküteri",
    "colruyt-beenhouwerij": "Et & Şarküteri",
    "gehakt": "Et & Şarküteri",
    "varkensvlees-vers": "Et & Şarküteri",
    "rundsvlees-vers": "Et & Şarküteri",
    "lamsvlees": "Et & Şarküteri",
    "rund": "Et & Şarküteri",
    "bbq-vers": "Et & Şarküteri",
    "antipasti-en-aperitiefhapjes": "Et & Şarküteri",
    "categorie v2mea": "Et & Şarküteri",
    "categorie v2ape": "Et & Şarküteri",
    # Tavuk
    "gevogelte-vers": "Tavuk & Kümes",
    # Balık
    "vis": "Balık & Deniz Ürünleri",
    "verse-vis": "Balık & Deniz Ürünleri",
    "diepvries-vis": "Balık & Deniz Ürünleri",
    "witte-vis": "Balık & Deniz Ürünleri",
    "zalm": "Balık & Deniz Ürünleri",
    "zeevruchten": "Balık & Deniz Ürünleri",
    "vis-zeevruchten": "Balık & Deniz Ürünleri",
    "categorie v2sal": "Balık & Deniz Ürünleri",
    # Sebze & Meyve
    "groenten en fruit": "Sebze & Meyve",
    "groenten-en-fruit": "Sebze & Meyve",
    "agf-fruit": "Sebze & Meyve",
    "agf-fruit-los": "Sebze & Meyve",
    "agf-groenten": "Sebze & Meyve",
    "agf-groenten-los": "Sebze & Meyve",
    "groenten": "Sebze & Meyve",
    "fruit": "Sebze & Meyve",
    "fruit-groenten": "Sebze & Meyve",
    "categorie v2fru": "Sebze & Meyve",
    # Ekmek
    "brood": "Ekmek & Unlu Mamüller",
    "brood/ontbijt": "Ekmek & Unlu Mamüller",
    "brood-broodjes-en-viennoiserie": "Ekmek & Unlu Mamüller",
    "broodbeleg": "Ekmek & Unlu Mamüller",
    "brood-bakker": "Ekmek & Unlu Mamüller",
    "v-spreads": "Ekmek & Unlu Mamüller",
    "categorie v2bak": "Ekmek & Unlu Mamüller",
    "categorie v2spo": "Ekmek & Unlu Mamüller",
    # Donmuş Ürünler
    "diepvries": "Donmuş Ürünler",
    "eenpans-en-microgolfgerechten": "Donmuş Ürünler",
    "categorie v2fro": "Donmuş Ürünler",
    # Tahıllar & Makarna
    "pasta-en-rijst": "Tahıllar & Makarna",
    "musli-cornflakes-en-granen": "Tahıllar & Makarna",
    "ontbijtgranen": "Tahıllar & Makarna",
    "pasta": "Tahıllar & Makarna",
    "rijst": "Tahıllar & Makarna",
    "eieren-droogwaren": "Tahıllar & Makarna",
    "kruidenierswaren/droge voeding": "Tahıllar & Makarna",
    # Konserve & Hazır Yemek
    "conserven": "Konserve & Hazır Yemek",
    "categorie v2can": "Konserve & Hazır Yemek",
    # Yağ, Sos & Baharat
    "vetten-olie-en-azijn": "Yağ, Sos & Baharat",
    "dips-sauzen-en-dressing": "Yağ, Sos & Baharat",
    "sauzen": "Yağ, Sos & Baharat",
    "sauzen-kruiden": "Yağ, Sos & Baharat",
    "conserven-olie": "Yağ, Sos & Baharat",
    "azijn": "Yağ, Sos & Baharat",
    "olie": "Yağ, Sos & Baharat",
    "confituur": "Yağ, Sos & Baharat",
    # Atıştırmalık & Tatlı
    "chips/borrelhapjes": "Atıştırmalık & Tatlı",
    "chips": "Atıştırmalık & Tatlı",
    "koeken/chocolade/snoep": "Atıştırmalık & Tatlı",
    "koeken": "Atıştırmalık & Tatlı",
    "snoep": "Atıştırmalık & Tatlı",
    "chips-snoep": "Atıştırmalık & Tatlı",
    "snacks": "Atıştırmalık & Tatlı",
    "noten": "Atıştırmalık & Tatlı",
    "categorie v2swe": "Atıştırmalık & Tatlı",
    "categorie v2con": "Atıştırmalık & Tatlı",
    # Dondurma & Tatlı
    "desserts": "Dondurma & Tatlı",
    "ijs": "Dondurma & Tatlı",
    "zomer-ijs": "Dondurma & Tatlı",
    # İçecekler
    "dranken": "İçecekler",
    "frisdrank": "İçecekler",
    "water": "İçecekler",
    "soep": "İçecekler",
    "categorie v2dri": "İçecekler",
    # Kahve & Çay
    "koffie-thee": "Kahve & Çay",
    "koffie-thee-cacao": "Kahve & Çay",
    "koffie": "Kahve & Çay",
    "thee": "Kahve & Çay",
    # Alkol
    "bier": "Alkol",
    "wijn": "Alkol",
    "wijn-gedistilleerde-dranken": "Alkol",
    "bieren,alcohol & alcoholvrij": "Alkol",
    "categorie v2alc": "Alkol",
    "categorie v2win": "Alkol",
    "categorie v2winexc": "Alkol",
    "categorie v2winwhi": "Alkol",
    "feestwijn": "Alkol",
    # Yumurta
    "eieren": "Yumurta",
    # Bebek
    "baby": "Bebek Ürünleri",
    "babyvoeding": "Bebek Ürünleri",
    "babyproducten": "Bebek Ürünleri",
    "categorie v2bab": "Bebek Ürünleri",
    "baby-en-kinderspullen": "Bebek Ürünleri",
    # Temizlik
    "huishouden": "Temizlik & Ev Bakımı",
    "onderhoud/huishouden": "Temizlik & Ev Bakımı",
    "wasmiddel": "Temizlik & Ev Bakımı",
    "schoonmaken": "Temizlik & Ev Bakımı",
    "wassen-strijken": "Temizlik & Ev Bakımı",
    "categorie v2cle": "Temizlik & Ev Bakımı",
    # Kişisel Bakım
    "verzorging": "Kişisel Bakım",
    "lichaamsverzorging/parfumerie": "Kişisel Bakım",
    "gezondheid": "Kişisel Bakım",
    "shampoo": "Kişisel Bakım",
    "tandpasta": "Kişisel Bakım",
    "drogisterij": "Kişisel Bakım",
    "categorie v2hyg": "Kişisel Bakım",
    # Evcil Hayvan
    "huisdieren": "Evcil Hayvan",
    "hondenvoer": "Evcil Hayvan",
    "kattenvoer": "Evcil Hayvan",
    "categorie v2pet": "Evcil Hayvan",
    # Giyim (Lidl)
    "dameskleding": "Giyim",
    "herenkleding": "Giyim",
    "kinderkleding-2-8-jaar": "Giyim",
    "mode-accessoires": "Giyim",
    "schoenen-dames": "Giyim",
    "sportkleding": "Giyim",
    # Ev & Bahçe (Lidl)
    "tuin-terras": "Ev & Bahçe",
    "keuken-huishouden": "Ev & Bahçe",
    "wonen-interieur": "Ev & Bahçe",
    # Spor (Lidl)
    "sport-vrije-tijd": "Spor & Outdoor",
    "fitness": "Spor & Outdoor",
    # Teknoloji (Lidl)
    "multimedia-technologie": "Teknoloji",
}

PROMO_TAGS = {
    "alle promoties", "promoties", "einstein", "promo",
    "n/a", "voeding", "verse producten", "niet-voeding",
}

# Keyword fallback — tam eşleşme yoksa ürün adında bu kelimelere bak
KEYWORD_FALLBACK = [
    ("eieren",      "Yumurta"),
    ("melk",        "Süt Ürünleri"),
    ("kaas",        "Süt Ürünleri"),
    ("yoghurt",     "Süt Ürünleri"),
    ("boter",       "Süt Ürünleri"),
    ("vlees",       "Et & Şarküteri"),
    ("gehakt",      "Et & Şarküteri"),
    ("charcuterie", "Et & Şarküteri"),
    ("worst",       "Et & Şarküteri"),
    ("spek",        "Et & Şarküteri"),
    ("kip",         "Tavuk & Kümes"),
    ("gevogelte",   "Tavuk & Kümes"),
    ("zalm",        "Balık & Deniz Ürünleri"),
    ("tonijn",      "Balık & Deniz Ürünleri"),
    ("vis",         "Balık & Deniz Ürünleri"),
    ("groenten",    "Sebze & Meyve"),
    ("appel",       "Sebze & Meyve"),
    ("banaan",      "Sebze & Meyve"),
    ("tomaat",      "Sebze & Meyve"),
    ("aardappel",   "Sebze & Meyve"),
    ("brood",       "Ekmek & Unlu Mamüller"),
    ("bakker",      "Ekmek & Unlu Mamüller"),
    ("pasta",       "Tahıllar & Makarna"),
    ("rijst",       "Tahıllar & Makarna"),
    ("granen",      "Tahıllar & Makarna"),
    ("diepvries",   "Donmuş Ürünler"),
    ("snoep",       "Atıştırmalık & Tatlı"),
    ("chocolade",   "Atıştırmalık & Tatlı"),
    ("koek",        "Atıştırmalık & Tatlı"),
    ("chips",       "Atıştırmalık & Tatlı"),
    ("noten",       "Atıştırmalık & Tatlı"),
    ("ijs",         "Dondurma & Tatlı"),
    ("dessert",     "Dondurma & Tatlı"),
    ("koffie",      "Kahve & Çay"),
    ("thee",        "Kahve & Çay"),
    ("bier",        "Alkol"),
    ("wijn",        "Alkol"),
    ("water",       "İçecekler"),
    ("frisdrank",   "İçecekler"),
    ("drank",       "İçecekler"),
    ("soep",        "Konserve & Hazır Yemek"),
    ("conserven",   "Konserve & Hazır Yemek"),
    ("olie",        "Yağ, Sos & Baharat"),
    ("saus",        "Yağ, Sos & Baharat"),
    ("azijn",       "Yağ, Sos & Baharat"),
    ("baby",        "Bebek Ürünleri"),
    ("wasmiddel",   "Temizlik & Ev Bakımı"),
    ("schoon",      "Temizlik & Ev Bakımı"),
    ("huishoud",    "Temizlik & Ev Bakımı"),
    ("shampoo",     "Kişisel Bakım"),
    ("tandpasta",   "Kişisel Bakım"),
    ("verzorg",     "Kişisel Bakım"),
    ("hond",        "Evcil Hayvan"),
    ("huisdier",    "Evcil Hayvan"),
    ("kleding",     "Giyim"),
    ("schoenen",    "Giyim"),
    ("sport",       "Spor & Outdoor"),
    ("tuin",        "Ev & Bahçe"),
    ("keuken",      "Ev & Bahçe"),
]


def kategori_bul(category_name: str, name: str) -> str:
    raw = (category_name or "").lower().strip()
    raw = re.sub(r"^(api:|cat:)", "", raw).split(">")[0].strip()

    if raw and raw not in PROMO_TAGS:
        if raw in KATEGORI_MAP:
            return KATEGORI_MAP[raw]
        # Keyword fallback önce category_name'de ara
        for kw, cat in KEYWORD_FALLBACK:
            if kw in raw:
                return cat

    # Ürün adında ara
    name_low = (name or "").lower()
    for kw, cat in KEYWORD_FALLBACK:
        if kw in name_low:
            return cat

    return "Diğer"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="DB'ye yazma")
    parser.add_argument("--limit", type=int, default=0, help="Sadece N ürün")
    args = parser.parse_args()

    url, key = load_secrets()
    base_headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    # Tüm ürünleri çek
    print("Ürünler Supabase'den çekiliyor...")
    all_rows, offset = [], 0
    while True:
        params = {
            "select": "id,name,category_name",
            "order":  "id.asc",
            "limit":  str(BATCH_SIZE),
            "offset": str(offset),
        }
        r = requests.get(f"{url}/rest/v1/market_chain_products",
                         headers=base_headers, params=params, timeout=30)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_rows.extend(batch)
        offset += BATCH_SIZE
        if len(batch) < BATCH_SIZE:
            break
        if args.limit and len(all_rows) >= args.limit:
            all_rows = all_rows[:args.limit]
            break

    print(f"{len(all_rows)} ürün çekildi. Kategoriler hesaplanıyor...")

    stats: dict[str, int] = {}
    updates_by_cat: dict[str, list] = {}
    for row in all_rows:
        cat = kategori_bul(row.get("category_name") or "", row.get("name") or "")
        stats[cat] = stats.get(cat, 0) + 1
        updates_by_cat.setdefault(cat, []).append(row["id"])

    print("\nKategori dağılımı:")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<35} {count:>6}")
    print(f"\nToplam: {len(all_rows)} ürün, {len(stats)} kategori")

    if args.dry_run:
        print("\n[dry-run] DB'ye yazılmadı.")
        return

    print("\nDB güncelleniyor (category_tr)...")
    patch_headers = {**base_headers, "Content-Type": "application/json",
                     "Prefer": "return=minimal"}
    done = 0
    for cat, ids in updates_by_cat.items():
        for i in range(0, len(ids), MAX_IDS):
            chunk = ids[i:i + MAX_IDS]
            id_list = ",".join(str(x) for x in chunk)
            resp = requests.patch(
                f"{url}/rest/v1/market_chain_products?id=in.({id_list})",
                json={"category_tr": cat},
                headers=patch_headers, timeout=60,
            )
            if resp.status_code not in (200, 204):
                print(f"\n  UYARI [{cat}]: HTTP {resp.status_code} — {resp.text[:100]}")
            done += len(chunk)
        print(f"  [{done}/{len(all_rows)}] {cat:<30}", end="\r")

    print(f"\nTamamlandı. {done} ürün güncellendi.")


if __name__ == "__main__":
    main()
