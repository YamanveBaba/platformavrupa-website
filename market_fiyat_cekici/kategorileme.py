# -*- coding: utf-8 -*-
"""
market_chain_products tablosundaki ürünlere category_tr atar.

Adımlar:
  1. Supabase SQL Editor'da bir kez çalıştır:
       ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS category_raw TEXT;
       ALTER TABLE market_chain_products ADD COLUMN IF NOT EXISTS category_tr  TEXT;

  2. Import scriptini güncelle (aşağıdaki güncellemeyi yap, sonra tüm JSON'ları tekrar yükle).
     Alternatif: bu scripti çalıştır — mevcut JSON dosyalarından category_raw doldurup DB'ye yazar.

Kullanım:
  python kategorileme.py                # tüm ürünleri kategorile
  python kategorileme.py --dry-run      # DB'ye yazma, sadece istatistik göster
  python kategorileme.py --zincir aldi  # tek market
"""

from __future__ import annotations
import argparse, os, sys, json, glob, re
try:
    import requests
except ImportError:
    print("HATA: pip install requests"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CIKTI_DIR  = os.path.join(SCRIPT_DIR, "cikti")
BATCH_SIZE = 500

# ─── SUPABASE ────────────────────────────────────────────────────────────────

def _clean(s: str, is_url: bool) -> str:
    s = s.strip().strip("\ufeff").strip('"').strip("'")
    prefix = "SUPABASE_URL=" if is_url else "SUPABASE_SERVICE_ROLE_KEY="
    if s.upper().startswith(prefix.upper()):
        s = s.split("=", 1)[1].strip()
    if not is_url and s.lower().startswith("bearer "):
        s = s[6:].strip()
    return s

def load_secrets():
    url = _clean(os.environ.get("SUPABASE_URL", ""), True)
    key = _clean(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""), False)
    if url and key:
        return url.rstrip("/"), key
    path = os.path.join(SCRIPT_DIR, "supabase_import_secrets.txt")
    lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
             if l.strip() and not l.strip().startswith("#")]
    return _clean(lines[0], True).rstrip("/"), _clean(lines[1], False)

def sb_get(url, key, endpoint, params):
    r = requests.get(f"{url}/rest/v1/{endpoint}", params=params,
                     headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    return r.json()

def save_all(url, key, updates: list[dict], dry_run: bool):
    """
    (category_raw, category_tr) çiftine göre gruplar.
    Her grup için tek PATCH id=in.(...) — toplamda ~80 istek.
    """
    if dry_run:
        print(f"  [dry-run] {len(updates)} satır yazılacaktı")
        return

    # Grupla: (raw, tr) -> [id, id, ...]
    groups: dict[tuple, list] = {}
    for r in updates:
        key_ = (r["category_raw"] or "", r["category_tr"])
        groups.setdefault(key_, []).append(r["id"])

    print(f"  {len(groups)} farklı (category_raw, category_tr) grubu — {len(groups)} istek atılacak")
    done = 0
    # Supabase id=in.() max ~2000 karakter — büyük grupları böl
    MAX_IDS = 400
    for (raw, tr), ids in groups.items():
        for i in range(0, len(ids), MAX_IDS):
            chunk = ids[i:i+MAX_IDS]
            id_list = ",".join(str(x) for x in chunk)
            resp = requests.patch(
                f"{url}/rest/v1/market_chain_products?id=in.({id_list})",
                json={"category_raw": raw, "category_tr": tr},
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=60,
            )
            if resp.status_code not in (200, 204):
                print(f"  UYARI [{tr}]: {resp.status_code} {resp.text[:150]}")
            done += len(chunk)
        print(f"  [{done}/{len(updates)}] {tr[:30]}", end="\r")
    print(f"\n  Tamamlandı.")

# ─── KATEGORİ EŞLEŞTİRME TABLOSU ────────────────────────────────────────────
# Her market'in kendi kategori adı -> Türkçe ana kategori
# Kural: küçük harfe çevir, tam eşleşme yoksa keyword arama yapar

KATEGORI_MAP: dict[str, str] = {

    # ── SÜT ÜRÜNLERİ ──────────────────────────────────────────────────────
    "zuivel":                               "Süt Ürünleri",
    "melk-en-melkvervangers":               "Süt Ürünleri",
    "melk en melkvervangers":               "Süt Ürünleri",
    "yoghurt-verse-kaas-en-desserts":       "Süt Ürünleri",
    "yoghurt verse kaas en desserts":       "Süt Ürünleri",
    "kaas-zuivel":                          "Süt Ürünleri",  # Lidl
    "kaas":                                 "Süt Ürünleri",
    "melk":                                 "Süt Ürünleri",
    "categorie v2dai":                      "Süt Ürünleri",  # Delhaize dairy
    "categorie v2kaz":                      "Süt Ürünleri",  # Delhaize kaas

    # ── ET & ŞARKÜTER ─────────────────────────────────────────────────────
    "vlees":                                "Et & Şarküteri",
    "vlees-worst":                          "Et & Şarküteri",  # Lidl
    "bereidingen/charcuterie/vis/veggie":   "Et & Şarküteri",
    "bereidingen charcuterie vis veggie":   "Et & Şarküteri",
    "charcuterie":                          "Et & Şarküteri",
    "colruyt-beenhouwerij":                 "Et & Şarküteri",
    "gehakt":                               "Et & Şarküteri",
    "varkensvlees-vers":                    "Et & Şarküteri",
    "rundsvlees-vers":                      "Et & Şarküteri",
    "lamsvlees":                            "Et & Şarküteri",
    "rund":                                 "Et & Şarküteri",
    "vlees":                                "Et & Şarküteri",
    "bbq-vers":                             "Et & Şarküteri",
    "zomer-bbq":                            "Et & Şarküteri",
    "zomer-koudbuffet":                     "Et & Şarküteri",
    "antipasti-en-aperitiefhapjes":         "Et & Şarküteri",
    "categorie v2mea":                      "Et & Şarküteri",  # Delhaize meat
    "categorie v2ape":                      "Et & Şarküteri",  # Delhaize aperitif

    # ── TAVUK ─────────────────────────────────────────────────────────────
    "gevogelte-vers":                       "Tavuk & Kümes",

    # ── BALIK & DENİZ ──────────────────────────────────────────────────────
    "vis":                                  "Balık & Deniz Ürünleri",
    "verse-vis":                            "Balık & Deniz Ürünleri",
    "diepvries-vis":                        "Balık & Deniz Ürünleri",
    "witte-vis":                            "Balık & Deniz Ürünleri",
    "zalm":                                 "Balık & Deniz Ürünleri",
    "zeevruchten":                          "Balık & Deniz Ürünleri",
    "eoy-vis":                              "Balık & Deniz Ürünleri",
    "meer-vis":                             "Balık & Deniz Ürünleri",
    "vis-zeevruchten":                      "Balık & Deniz Ürünleri",  # Lidl
    "categorie v2sal":                      "Balık & Deniz Ürünleri",  # Delhaize zalm?

    # ── SEBZE & MEYVE ──────────────────────────────────────────────────────
    "groenten en fruit":                    "Sebze & Meyve",
    "groenten-en-fruit":                    "Sebze & Meyve",
    "agf-fruit":                            "Sebze & Meyve",
    "agf-fruit-los":                        "Sebze & Meyve",
    "agf-groenten":                         "Sebze & Meyve",
    "agf-groenten-los":                     "Sebze & Meyve",
    "groenten":                             "Sebze & Meyve",
    "fruit":                                "Sebze & Meyve",
    "fruit-groenten":                       "Sebze & Meyve",  # Lidl
    "categorie v2fru":                      "Sebze & Meyve",  # Delhaize

    # ── EKMEK & UNLU MAMÜLLER ──────────────────────────────────────────────
    "brood":                                "Ekmek & Unlu Mamüller",
    "brood/ontbijt":                        "Ekmek & Unlu Mamüller",
    "brood-broodjes-en-viennoiserie":       "Ekmek & Unlu Mamüller",
    "broodbeleg":                           "Ekmek & Unlu Mamüller",
    "brood-bakker":                         "Ekmek & Unlu Mamüller",  # Lidl
    "v-spreads":                            "Ekmek & Unlu Mamüller",
    "categorie v2bak":                      "Ekmek & Unlu Mamüller",  # Delhaize bakkerij
    "categorie v2spo":                      "Ekmek & Unlu Mamüller",  # Delhaize spread

    # ── DONMUŞ ÜRÜNLER ─────────────────────────────────────────────────────
    "diepvries":                            "Donmuş Ürünler",
    "eenpans-en-microgolfgerechten":        "Donmuş Ürünler",
    "categorie v2fro":                      "Donmuş Ürünler",  # Delhaize frozen

    # ── TAHILLAR & MAKARNA ──────────────────────────────────────────────────
    "pasta-en-rijst":                       "Tahıllar & Makarna",
    "musli-cornflakes-en-granen":           "Tahıllar & Makarna",
    "ontbijtgranen":                        "Tahıllar & Makarna",
    "pasta":                                "Tahıllar & Makarna",
    "rijst":                                "Tahıllar & Makarna",
    "eieren-droogwaren":                    "Tahıllar & Makarna",  # Lidl droge voeding
    "kruidenierswaren/droge voeding":       "Tahıllar & Makarna",
    "conserven":                            "Konserve & Hazır Yemek",
    "categorie v2can":                      "Konserve & Hazır Yemek",  # Delhaize

    # ── YAĞ, SOS & BAHARAT ─────────────────────────────────────────────────
    "vetten-olie-en-azijn":                 "Yağ, Sos & Baharat",
    "dips-sauzen-en-dressing":              "Yağ, Sos & Baharat",
    "sauzen":                               "Yağ, Sos & Baharat",
    "sauzen-kruiden":                       "Yağ, Sos & Baharat",  # Lidl
    "conserven-olie":                       "Yağ, Sos & Baharat",  # Lidl
    "azijn":                                "Yağ, Sos & Baharat",
    "olie":                                 "Yağ, Sos & Baharat",
    "confituur":                            "Yağ, Sos & Baharat",

    # ── ATIŞTIPRMALIK & TATLIL ─────────────────────────────────────────────
    "chips/borrelhapjes":                   "Atıştırmalık & Tatlı",
    "chips":                                "Atıştırmalık & Tatlı",
    "koeken/chocolade/snoep":               "Atıştırmalık & Tatlı",
    "koeken":                               "Atıştırmalık & Tatlı",
    "snoep":                                "Atıştırmalık & Tatlı",
    "chips-snoep":                          "Atıştırmalık & Tatlı",  # Lidl
    "snacks":                               "Atıştırmalık & Tatlı",
    "noten":                                "Atıştırmalık & Tatlı",
    "categorie v2swe":                      "Atıştırmalık & Tatlı",  # Delhaize sweet
    "categorie v2con":                      "Atıştırmalık & Tatlı",  # Delhaize confiserie

    # ── DONDURMA & DESSERT ─────────────────────────────────────────────────
    "desserts":                             "Dondurma & Tatlı",
    "ijs":                                  "Dondurma & Tatlı",
    "zomer-ijs":                            "Dondurma & Tatlı",
    "ijshoorntjes":                         "Dondurma & Tatlı",
    "waterijs":                             "Dondurma & Tatlı",

    # ── İÇECEKLER (alkolsüz) ────────────────────────────────────────────────
    "dranken":                              "İçecekler",
    "frisdrank":                            "İçecekler",
    "water":                                "İçecekler",
    "soep":                                 "İçecekler",
    "categorie v2dri":                      "İçecekler",  # Delhaize
    "koffie-thee":                          "Kahve & Çay",  # Lidl
    "koffie-thee-cacao":                    "Kahve & Çay",
    "koffie":                               "Kahve & Çay",
    "thee":                                 "Kahve & Çay",

    # ── ALKOL ──────────────────────────────────────────────────────────────
    "bier":                                 "Alkol",
    "wijn":                                 "Alkol",
    "wijn-gedistilleerde-dranken":          "Alkol",  # Lidl
    "bieren,alcohol & alcoholvrij":         "Alkol",  # Delhaize
    "categorie v2alc":                      "Alkol",  # Delhaize
    "categorie v2win":                      "Alkol",  # Delhaize wijn
    "categorie v2winexc":                   "Alkol",
    "categorie v2winwhi":                   "Alkol",
    "feestwijn":                            "Alkol",
    "kanjers-wijn":                         "Alkol",

    # ── YUMURTA ────────────────────────────────────────────────────────────
    "eieren":                               "Yumurta",

    # ── BEBEK ──────────────────────────────────────────────────────────────
    "baby":                                 "Bebek Ürünleri",
    "babyvoeding":                          "Bebek Ürünleri",
    "babyproducten":                        "Bebek Ürünleri",
    "baby-0":                               "Bebek Ürünleri",
    "baby-1":                               "Bebek Ürünleri",
    "baby-half":                            "Bebek Ürünleri",
    "categorie v2bab":                      "Bebek Ürünleri",  # Delhaize
    "baby-en-kinderspullen":                "Bebek Ürünleri",  # Lidl

    # ── TEMİZLİK ───────────────────────────────────────────────────────────
    "huishouden":                           "Temizlik & Ev Bakımı",
    "onderhoud/huishouden":                 "Temizlik & Ev Bakımı",
    "wasmiddel":                            "Temizlik & Ev Bakımı",
    "schoonmaken":                          "Temizlik & Ev Bakımı",  # Lidl
    "wassen-strijken":                      "Temizlik & Ev Bakımı",  # Lidl
    "categorie v2cle":                      "Temizlik & Ev Bakımı",  # Delhaize

    # ── KİŞİSEL BAKIM ──────────────────────────────────────────────────────
    "verzorging":                           "Kişisel Bakım",
    "lichaamsverzorging/parfumerie":        "Kişisel Bakım",
    "gezondheid":                           "Kişisel Bakım",
    "shampoo":                              "Kişisel Bakım",
    "tandpasta":                            "Kişisel Bakım",
    "drogisterij":                          "Kişisel Bakım",  # Lidl
    "categorie v2hyg":                      "Kişisel Bakım",  # Delhaize

    # ── EVCİL HAYVAN ────────────────────────────────────────────────────────
    "huisdieren":                           "Evcil Hayvan",
    "hondenvoer":                           "Evcil Hayvan",
    "kattenvoer":                           "Evcil Hayvan",
    "categorie v2pet":                      "Evcil Hayvan",  # Delhaize

    # ── ÇOCUK & OYUNCAK ─────────────────────────────────────────────────────
    "speelgoed":                            "Oyuncak & Çocuk",
    "luiers":                               "Oyuncak & Çocuk",

    # ── GİYİM (Lidl) ────────────────────────────────────────────────────────
    "dameskleding":                         "Giyim",
    "herenkleding":                         "Giyim",
    "kinderkleding-2-8-jaar":               "Giyim",
    "kinderkleding-9-15-jaar":              "Giyim",
    "mode-accessoires":                     "Giyim",
    "schoenen-dames":                       "Giyim",
    "sportkleding":                         "Giyim",
    "sportkleding-heren":                   "Giyim",

    # ── EV & BAHÇE (Lidl) ───────────────────────────────────────────────────
    "tuin-terras":                          "Ev & Bahçe",
    "tuinmeubelen":                         "Ev & Bahçe",
    "doe-het-zelf-tuin":                    "Ev & Bahçe",
    "keuken-huishouden":                    "Ev & Bahçe",
    "slaapkamer":                           "Ev & Bahçe",
    "wonen-interieur":                      "Ev & Bahçe",
    "verlichting":                          "Ev & Bahçe",

    # ── SPOR (Lidl) ─────────────────────────────────────────────────────────
    "sport-vrije-tijd":                     "Spor & Outdoor",
    "fitness":                              "Spor & Outdoor",
    "kamperen-outdoor":                     "Spor & Outdoor",

    # ── TEKNOLOJİ (Lidl) ────────────────────────────────────────────────────
    "multimedia-technologie":               "Teknoloji",
    "smartphones":                          "Teknoloji",
}

# Keyword bazlı fallback — tam eşleşme yoksa bu anahtar kelimelere bak
KEYWORD_FALLBACK: list[tuple[str, str]] = [
    # (keyword, kategori)
    ("melk",        "Süt Ürünleri"),
    ("zuivel",      "Süt Ürünleri"),
    ("kaas",        "Süt Ürünleri"),
    ("yoghurt",     "Süt Ürünleri"),
    ("vlees",       "Et & Şarküteri"),
    ("charcuterie", "Et & Şarküteri"),
    ("gehakt",      "Et & Şarküteri"),
    ("varken",      "Et & Şarküteri"),
    ("rund",        "Et & Şarküteri"),
    ("lam",         "Et & Şarküteri"),
    ("kip",         "Tavuk & Kümes"),
    ("gevogelte",   "Tavuk & Kümes"),
    ("vis",         "Balık & Deniz Ürünleri"),
    ("zalm",        "Balık & Deniz Ürünleri"),
    ("zeevruchten", "Balık & Deniz Ürünleri"),
    ("groenten",    "Sebze & Meyve"),
    ("fruit",       "Sebze & Meyve"),
    ("agf",         "Sebze & Meyve"),
    ("brood",       "Ekmek & Unlu Mamüller"),
    ("bakker",      "Ekmek & Unlu Mamüller"),
    ("pasta",       "Tahıllar & Makarna"),
    ("rijst",       "Tahıllar & Makarna"),
    ("granen",      "Tahıllar & Makarna"),
    ("conserven",   "Konserve & Hazır Yemek"),
    ("diepvries",   "Donmuş Ürünler"),
    ("ijs",         "Dondurma & Tatlı"),
    ("dessert",     "Dondurma & Tatlı"),
    ("snoep",       "Atıştırmalık & Tatlı"),
    ("chocolade",   "Atıştırmalık & Tatlı"),
    ("koek",        "Atıştırmalık & Tatlı"),
    ("chips",       "Atıştırmalık & Tatlı"),
    ("drank",       "İçecekler"),
    ("water",       "İçecekler"),
    ("frisdrank",   "İçecekler"),
    ("koffie",      "Kahve & Çay"),
    ("thee",        "Kahve & Çay"),
    ("bier",        "Alkol"),
    ("wijn",        "Alkol"),
    ("alcohol",     "Alkol"),
    ("baby",        "Bebek Ürünleri"),
    ("huishoud",    "Temizlik & Ev Bakımı"),
    ("wasmiddel",   "Temizlik & Ev Bakımı"),
    ("schoon",      "Temizlik & Ev Bakımı"),
    ("verzorg",     "Kişisel Bakım"),
    ("shampoo",     "Kişisel Bakım"),
    ("tand",        "Kişisel Bakım"),
    ("hond",        "Evcil Hayvan"),
    ("kat",         "Evcil Hayvan"),
    ("huisdier",    "Evcil Hayvan"),
    ("speelgoed",   "Oyuncak & Çocuk"),
    ("kleding",     "Giyim"),
    ("schoenen",    "Giyim"),
    ("sport",       "Spor & Outdoor"),
    ("tuin",        "Ev & Bahçe"),
    ("wonen",       "Ev & Bahçe"),
    ("keuken",      "Ev & Bahçe"),
    ("technologie", "Teknoloji"),
    ("eieren",      "Yumurta"),
    ("olie",        "Yağ, Sos & Baharat"),
    ("saus",        "Yağ, Sos & Baharat"),
    ("azijn",       "Yağ, Sos & Baharat"),
    ("soep",        "İçecekler"),
    ("gezondheid",  "Kişisel Bakım"),
]

# Promo/kampanya tag'leri — bunları atla, ürünün başka kategorisi yoksa "Diğer" koy
PROMO_TAGS = {
    "alle promoties", "promoties", "einstein", "promo",
    "n/a", "voeding", "verse producten", "niet-voeding",
    "tuin", "speelgoed", "lente-tuin",
}

def map_category(raw: str) -> str:
    """Ham kategori adını Türkçe ana kategoriye çevir."""
    if not raw:
        return "Diğer"
    lower = raw.lower().strip()
    # api: veya cat: prefix'ini temizle
    lower = re.sub(r"^(api:|cat:)", "", lower)
    # Lidl'de ">" ile alt kategori — sadece ilk kısmı al
    lower = lower.split(">")[0].strip()
    # Tam eşleşme
    if lower in KATEGORI_MAP:
        return KATEGORI_MAP[lower]
    # Promo/reklam tag'i
    if lower in PROMO_TAGS:
        return "Diğer"
    # Keyword fallback
    for kw, cat in KEYWORD_FALLBACK:
        if kw in lower:
            return cat
    return "Diğer"

# ─── JSON'LARDAN KATEGORİ ÇEK ────────────────────────────────────────────────

def load_category_map_from_jsons() -> dict[str, str]:
    """
    Tüm JSON çıktı dosyalarından pid -> category_raw eşlemesi oluşturur.
    Bu sayede mevcut kayıtları yeniden import etmeden güncelleyebiliriz.
    """
    pid_to_cat: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(CIKTI_DIR, "*.json"))):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                d = json.load(f)
            urunler = d.get("urunler", [])
            slug = str(d.get("chain_slug", "")).lower()
            for u in urunler:
                # pid alanı market'e göre farklı
                pid = (str(u.get("aldiPid") or u.get("delhaizePid") or
                           u.get("carrefourPid") or u.get("lidlProductKey") or
                           u.get("retailProductNumber") or
                           u.get("productCode") or u.get("productID") or "")).strip()
                cat = (u.get("topCategoryName") or u.get("categoryName") or "").strip()
                if pid and cat:
                    # slug + pid kombinasyonu
                    key = f"{slug}|{pid}"
                    pid_to_cat[key] = cat
        except Exception as e:
            pass
    print(f"JSON'lardan {len(pid_to_cat)} ürün kategori bilgisi yüklendi.")
    return pid_to_cat

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--zincir", help="aldi, carrefour_be, colruyt_be ...")
    args = parser.parse_args()

    SB_URL, SB_KEY = load_secrets()

    # Tüm ürünleri çek (id, chain_slug, external_product_id)
    print("Ürünler Supabase'den çekiliyor...")
    all_rows = []
    offset = 0
    while True:
        params = {
            "select": "id,chain_slug,external_product_id",
            "order": "id.asc",
            "limit": str(BATCH_SIZE),
            "offset": str(offset),
        }
        if args.zincir:
            params["chain_slug"] = f"ilike.{args.zincir}*"
        batch = sb_get(SB_URL, SB_KEY, "market_chain_products", params)
        if not batch:
            break
        all_rows.extend(batch)
        offset += BATCH_SIZE
        if len(batch) < BATCH_SIZE:
            break
    print(f"{len(all_rows)} ürün çekildi.")

    # JSON'lardan pid -> kategori eşlemesini yükle
    pid_to_cat = load_category_map_from_jsons()

    # Her ürüne kategori ata
    updates = []
    stats: dict[str, int] = {}
    no_match = 0

    for row in all_rows:
        slug = str(row.get("chain_slug", "")).lower()
        pid  = str(row.get("external_product_id", "")).strip()
        key  = f"{slug}|{pid}"
        raw  = pid_to_cat.get(key, "")
        cat  = map_category(raw)
        stats[cat] = stats.get(cat, 0) + 1
        if not raw:
            no_match += 1
        updates.append({"id": row["id"], "category_raw": raw, "category_tr": cat})

    # İstatistik
    print(f"\nKategori dağılımı ({len(updates)} ürün):")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<30} {count:>6}")
    print(f"\nJSON'da bulunamayan (category_raw boş): {no_match}")

    if args.dry_run:
        print("\n[dry-run] DB'ye yazılmadı.")
        return

    # DB'ye yaz — gruplu PATCH
    print("\nDB'ye yazılıyor...")
    save_all(SB_URL, SB_KEY, updates, args.dry_run)

    print(f"\nTamamlandı. {len(updates)} ürün güncellendi.")

if __name__ == "__main__":
    main()
