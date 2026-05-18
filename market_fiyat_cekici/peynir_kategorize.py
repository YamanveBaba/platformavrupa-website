# -*- coding: utf-8 -*-
"""
D:\MARKET\PEYNİR klasöründeki tüm HTML dosyalarını parse eder.
- Klasör adı = kategori (kategorili dosyalar)
- Karışık dosyalar = keyword ile otomatik kategori
- Dutch + Türkçe çiftleri birleştirir
- Philadelphia dahil tüm sürülebilirler → SÜRÜLEBİLİR PEYNİR
- Dilimlenmiş ve sürülebilir karışık dosyasını böler
Çıktı: D:\MARKET\peynir_data.json
"""
import sys, re, json, os, shutil
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

PEYNIR_DIR  = Path(r"D:\MARKET\PEYNİR")
IMG_DEST    = Path(r"C:\Users\yaman\Desktop\platformavrupa-website\img\peynir")
CIKTI_JSON  = Path(r"D:\MARKET\peynir_data.json")

IMG_DEST.mkdir(parents=True, exist_ok=True)

# ── Kategori → slug eşlemesi ──────────────────────────────────────────────────
KLASOR_KAT = {
    "BLOK PEYNİRLER":                   "blok",
    "CAMEMBERT ve BRIE PEYNİRLERİ":     "camembert",
    "DAMARLI PEYNİRLER":                "damarli",
    "DİLİMLENMİŞ PEYNİR":              "dilimlenmiş",
    "FETA, KEÇİ ve KOYUN PEYNİRLERİ":  "feta",
    "MOZZARELLA, MASCARPONE ve RICOTTA":"mozzarella",
    "MUNSTER ve MAROILLES":             "munster",
    "PEYNİR TABAKLARI":                 "tabaklar",
    "RACLETTE ve FONDÜ":                "raclette",
    "RENDELENMİŞ PEYNİRLER":           "rendelenmis",
    "SALATA ve MEZE PEYNİRLERİ":       "salata",
    "SERVIS LIK PEYNIRLER":            "servislik",
    "SÜRÜLEBİLİR PEYNİR":             "surulebilir",
    "ÇOCUKLAR İÇİN":                   "cocuklar",
}

KAT_ETIKET = {
    "blok":        "Blok Peynirler",
    "camembert":   "Camembert & Brie",
    "damarli":     "Damarlı Peynirler",
    "dilimlenmiş": "Dilimlenmiş Peynir",
    "feta":        "Feta, Keçi & Koyun",
    "mozzarella":  "Mozzarella, Mascarpone & Ricotta",
    "munster":     "Munster & Maroilles",
    "tabaklar":    "Peynir Tabakları",
    "raclette":    "Raclette & Fondü",
    "rendelenmis": "Rendelenmiş Peynirler",
    "salata":      "Salata & Meze Peynirleri",
    "servislik":   "Servislik Peynirler",
    "surulebilir": "Sürülebilir Peynir",
    "cocuklar":    "Çocuklar İçin",
    "diger":       "Diğer Peynirler",
}

# ── Otomatik kategori kuralları (uzun keyword = öncelikli) ────────────────────
ANAHTAR = {
    "blok":        ["parmigiano reggiano","comté aop","gruyère aoc","gouda blok","emmental blok","manchego","cheddar blok","in blok","kaas in blok","blok peynir","blokjes","engellemek"],
    "camembert":   ["brie de meaux","brie de normandie","camembert","brie","caprice des dieux","chaource","neufchâtel","coulommiers","zachte kaas","yumuşak peynir"],
    "damarli":     ["gorgonzola","roquefort","bleukaas","blauwe","bleu","stilton","fourme","rokfor","damarlı","schimmelkaas"],
    "feta":        ["schapenkaas","geitenkaas","feta","halloumi","pérail","ossau","myzithra","manouri","keçi","koyun sütü","geiten","schapen","chevre","chèvre","brebis"],
    "mozzarella":  ["mozzarella","mascarpone","ricotta","burrata","stracciatella","scamorza"],
    "munster":     ["munster","maroilles","livarot","époisses","reblochon","taleggio"],
    "raclette":    ["raclette","fondue","fondü","tartiflette"],
    "rendelenmis": ["geraspt","geraspte","rendelenmiş","râpé","geraspt"],
    "tabaklar":    ["kaasschotel","plateau","peynir tabak","selection kaas","assortiment"],
    "salata":      ["aperitief","aperitiefkaas","fagotin","apéricube","salade","meze peynir","snacking kaas","dippi"],
    "servislik":   ["in bediening","portie","buche","bûche","pyramide","mini portie","queso iberico","chevré"],
    "surulebilir": ["smeerkaas","philadelphia","boursin","st môret","kiri smeer","chalet","fromage à tartiner","verse kaas smeer","sürülebilir","lactosevrij smeer","lactosevrije smeer","lodge"],
    "cocuklar":    ["babybel","kiri snacking","la vache qui rit","mini babybel","kinderkaas","voor kinderen","çocuk için"],
}

def auto_kat(isim_nl: str, isim_tr: str = "") -> str:
    """Ürün isminden kategori belirle. Philadelphia her zaman sürülebilir."""
    n = (isim_nl + " " + isim_tr).lower()
    if "philadelphia" in n:
        return "surulebilir"
    skoru = {}
    for kat, keywords in ANAHTAR.items():
        for kw in keywords:
            if kw in n:
                skoru[kat] = skoru.get(kat, 0) + len(kw)
    return max(skoru, key=skoru.get) if skoru else "diger"

def is_surulebilir(isim: str) -> bool:
    n = isim.lower()
    return any(k in n for k in [
        "philadelphia","smeerkaas","smeer","boursin","st môret","verse kaas",
        "kiri","sürülebilir","fromage à tartiner","chalet","lodge","lactosevrij"
    ])

# ── Resim kopyalama ───────────────────────────────────────────────────────────
def kopya_img(src: Path, dest_fname: str) -> str:
    if not src or not src.exists():
        return ""
    dst = IMG_DEST / dest_fname
    if not dst.exists():
        shutil.copy2(src, dst)
    return f"img/peynir/{dest_fname}"

# ── Delhaize parser ───────────────────────────────────────────────────────────
UNIT_PAT = re.compile(
    r'(?:Prijs per|Adet fiyat[^:]*:)\s*(?:[^0-9]*)(\d+)\s*euro[,\s]+(?:[^0-9]*)?(\d+)\s*(?:cent|sent)',
    re.IGNORECASE
)
PRICE_PAT = re.compile(r'(?:Prijs|Fiyat):\s*(\d+)\s*euro[,\s]+(\d+)\s*(?:cent|sent)', re.IGNORECASE)
UNIT_TYPE_PAT = re.compile(r'(?:Prijs per|Adet fiyat[^:]*:)\s*(kilogram|stuk|100 gram|liter|adet)', re.IGNORECASE)

def parse_delhaize(html: str, files_dir: Path, kat_override: str = None) -> list:
    blocks = re.split(r'(?=<[^>]+data-testid="product-block-image-link")', html)
    urunler = []
    for blk in blocks[1:]:
        nm = re.search(r'aria-label="([^"]{5,150})"', blk)
        if not nm:
            continue
        isim = re.sub(r'^Delhaize\s+', '', nm.group(1).strip())
        if any(x in isim for x in ['alışveriş','Bilgi','Sepete','boodschappenlijst','Voeg','tooltip']):
            continue

        price_m = PRICE_PAT.search(blk)
        unit_m  = UNIT_PAT.search(blk)
        utype_m = UNIT_TYPE_PAT.search(blk)
        nutri_m = re.search(r'Nutri-Score:\s*([A-E])', blk)
        img_m   = re.search(r'src="(\./[^"]+_files/(\d+\.jpg))"', blk)
        promo_m = re.search(r'(?:Eerder|Voordeel|actie|promo|indirim|Önceki|Sale)', blk, re.I)
        content_m = re.search(r'aria-label="(\d+\s*(?:g|kg|ml|st|stuk|adet|cl)[^"]{0,20})"', blk)

        price = float(price_m.group(1)) + float(price_m.group(2)) / 100 if price_m else None
        unit  = float(unit_m.group(1))  + float(unit_m.group(2))  / 100 if unit_m  else None

        img_url = ""
        if img_m and files_dir and files_dir.exists():
            fname = img_m.group(2)
            img_url = kopya_img(files_dir / fname, fname)

        # Kategori belirle
        if kat_override:
            kat = kat_override
        else:
            kat = auto_kat(isim)
        # Philadelphia override
        if "philadelphia" in isim.lower():
            kat = "surulebilir"

        urunler.append({
            "name_nl":  isim,
            "name_tr":  None,
            "chain_slug": "delhaize_be",
            "price":    price,
            "unit_price": unit,
            "unit_type":  utype_m.group(1).lower() if utype_m else None,
            "in_promo": bool(promo_m),
            "currency": "EUR",
            "image_url": img_url,
            "nutriscore": nutri_m.group(1) if nutri_m else None,
            "content":  content_m.group(1) if content_m else None,
            "kategori": kat,
        })
    return urunler

# ── Carrefour parser ──────────────────────────────────────────────────────────
def parse_carrefour(html: str, files_dir: Path, kat_override: str = None, lang: str = "nl") -> list:
    dl = re.search(r'(?:const dlDataItems|dataLayer\.push)\s*[=(]\s*(\[.*?\])\s*[;)]', html, re.DOTALL)
    if not dl:
        return []
    try:
        evs = json.loads(re.sub(r'&#x27;', "'", dl.group(1)))
    except Exception:
        return []

    # _files içindeki resimler: 420_{id}*.webp
    img_map = {}
    if files_dir and files_dir.exists():
        for f in files_dir.iterdir():
            m = re.search(r'420_(\d+)', f.name)
            if m:
                img_map[m.group(1).lstrip('0')] = f

    urunler = []
    seen = set()
    for ev in evs:
        items = ev.get('ecommerce', {}).get('items', [])
        for it in items:
            isim = it.get('item_name', '').strip()
            if not isim or isim in seen:
                continue
            seen.add(isim)
            price = it.get('price')
            iid   = it.get('item_id', '').lstrip('0')
            brand = it.get('item_brand', '')

            img_url = ""
            if iid in img_map:
                img_url = kopya_img(img_map[iid], img_map[iid].name)

            # Kategori
            if kat_override:
                kat = kat_override
            else:
                kat = auto_kat(isim)
            if "philadelphia" in isim.lower():
                kat = "surulebilir"

            # Adet sayısı → unit price
            adet_m = re.search(r'(\d+)\s*(?:stuks?|st\.?\b|stuk\b|g\b|sneden)', isim, re.I)
            unit_price = None
            if adet_m and price:
                n = int(adet_m.group(1))
                if 2 <= n <= 50:
                    unit_price = round(price / n, 4)

            urunler.append({
                "name_nl":   isim if lang == "nl" else None,
                "name_tr":   isim if lang == "tr" else None,
                "chain_slug": "carrefour_be",
                "price":     price,
                "unit_price": unit_price,
                "unit_type": "stuk",
                "in_promo":  bool(it.get('discount')),
                "currency":  "EUR",
                "image_url": img_url,
                "nutriscore": None,
                "content":   None,
                "brand":     brand,
                "kategori":  kat,
            })
    return urunler

# ── Dosya → (market, dil, kat_override) tespiti ──────────────────────────────
def dosya_bilgi(rel_path: str, dosya_adi: str) -> tuple:
    """(market, lang, kat_override_slug) döner"""
    adi = dosya_adi.lower()

    # Market
    if 'carrefour' in adi:
        market = 'carrefour'
    elif any(x in adi for x in ['kaas','smeerkaas','geraspte','fondue','kinderkaas',
                                 'dilimlenmiş','sürülebilir','karışık','kaas mix']):
        market = 'delhaize'
    else:
        market = 'delhaize'

    # Dil: "Belçika" = Türkçe, "België" = Dutch, "dutch" = Dutch, Türkçe sözcük = Türkçe
    if 'belgië' in adi or '.d.' in adi or 'dutch' in adi:
        lang = 'nl'
    elif 'belçika' in adi or any(c in adi for c in ['ı','ğ','ş','ç','ü','ö']):
        lang = 'tr'
    else:
        lang = 'nl'  # Varsayılan: dutch

    # Klasör → kat_override
    klasor = Path(rel_path).parent.name
    kat_override = KLASOR_KAT.get(klasor, None)

    # Özel: "Dilimlenmiş ve sürülebilir" → None (her ürün için ayrı bakılacak)
    if 'dilimlenmiş ve sürülebilir' in adi:
        kat_override = None  # ürün bazında split

    return market, lang, kat_override

# ── Ana parse döngüsü ─────────────────────────────────────────────────────────
print("Tüm peynir dosyaları parse ediliyor...\n")

tum_urunler = []  # {name_nl, name_tr, chain_slug, price, ...}

for root, dirs, files in os.walk(PEYNIR_DIR):
    dirs.sort()
    for f in sorted(files):
        if not f.endswith('.html'):
            continue
        if any(x in f.lower() for x in ['activity', 'saved_resource', 'anchor']):
            continue

        tam    = Path(root) / f
        rel    = str(tam)[len(str(PEYNIR_DIR))+1:]
        market, lang, kat_override = dosya_bilgi(rel, f)

        # _files klasörü
        files_dir_name = f.replace('.html', '_files')
        files_dir = Path(root) / files_dir_name

        try:
            with open(tam, encoding='utf-8', errors='ignore') as fh:
                html = fh.read()
        except Exception:
            continue

        if market == 'delhaize':
            urunler = parse_delhaize(html, files_dir, kat_override)
        else:
            urunler = parse_carrefour(html, files_dir, kat_override, lang)

        if urunler:
            print(f"  [{lang.upper()}][{market[:3].upper()}] {f[:60]:<60} → {len(urunler)} ürün")
            tum_urunler.extend(urunler)

print(f"\nHam toplam: {len(tum_urunler)}")

# ── Dutch / Türkçe çift birleştirme ──────────────────────────────────────────
# Key: normalize edilmiş isim + chain + kategori
def norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9àáâãäçèéêëìíîïñòóôõöùúûü]', '', s)
    return s[:25]

# Önce Dutch'ları kaydet, sonra Türkçe isimlerini ekle
dutch_map: dict = {}   # norm_key → ürün
merged: list = []

for u in tum_urunler:
    nl = u.get('name_nl') or ''
    tr = u.get('name_tr') or ''
    key = norm(nl or tr) + "|" + u.get('chain_slug','') + "|" + u.get('kategori','')

    if nl:  # Dutch versiyonu
        if key not in dutch_map:
            dutch_map[key] = u
        else:
            # Fiyat veya resim güncelle
            existing = dutch_map[key]
            if not existing.get('price') and u.get('price'):
                existing['price'] = u['price']
            if not existing.get('image_url') and u.get('image_url'):
                existing['image_url'] = u['image_url']
    else:  # Türkçe versiyonu
        # Eşleşen Dutch var mı?
        matched = False
        for k, existing in dutch_map.items():
            if u.get('chain_slug') == existing.get('chain_slug') and u.get('kategori') == existing.get('kategori'):
                if not existing.get('name_tr') and tr:
                    existing['name_tr'] = tr
                    matched = True
                    break
        if not matched:
            dutch_map[norm(tr) + "|" + u.get('chain_slug','') + "|" + u.get('kategori','')] = u

# Sonuç listesi
for u in dutch_map.values():
    # name_nl yoksa name_tr'yi nl'ye taşı
    if not u.get('name_nl') and u.get('name_tr'):
        u['name_nl'] = u['name_tr']
    # Boş kategori fix
    if not u.get('kategori'):
        u['kategori'] = auto_kat(u.get('name_nl',''), u.get('name_tr',''))
    # Philadelphia her zaman sürülebilir
    if 'philadelphia' in (u.get('name_nl') or '').lower():
        u['kategori'] = 'surulebilir'
    merged.append(u)

print(f"Birleştirilmiş tekil ürün: {len(merged)}")

# ── Özet rapor ────────────────────────────────────────────────────────────────
gruplar = defaultdict(list)
for u in merged:
    gruplar[u['kategori']].append(u)

print(f"\n{'='*60}")
print(f"KATEGORİ DAĞILIMI")
print(f"{'='*60}")
for kat in list(KLASOR_KAT.values()) + ['diger']:
    urunler = gruplar.get(kat, [])
    if not urunler:
        continue
    chain_say = defaultdict(int)
    for u in urunler:
        chain_say[u['chain_slug']] += 1
    fiyatli = sum(1 for u in urunler if u.get('price'))
    resimli = sum(1 for u in urunler if u.get('image_url'))
    chains_str = ' | '.join(f"{k.split('_')[0]}: {v}" for k,v in chain_say.items())
    print(f"  {KAT_ETIKET.get(kat, kat):<35} {len(urunler):>3} ürün  ({chains_str})  fiyat:{fiyatli} resim:{resimli}")

# ── JSON kaydet ───────────────────────────────────────────────────────────────
# market.html uyumlu format
output = []
for u in merged:
    output.append({
        "chain_slug":   u.get('chain_slug'),
        "name":         u.get('name_nl') or u.get('name_tr') or '',
        "name_tr":      u.get('name_tr'),
        "price":        u.get('price'),
        "unit_price":   u.get('unit_price'),
        "unit_type":    u.get('unit_type'),
        "in_promo":     u.get('in_promo', False),
        "currency":     "EUR",
        "image_url":    u.get('image_url', ''),
        "nutriscore":   u.get('nutriscore'),
        "content":      u.get('content'),
        "brand":        u.get('brand', ''),
        "kategori":     u.get('kategori'),
    })

with open(CIKTI_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nJSON kaydedildi: {CIKTI_JSON}")
print(f"img/peynir klasöründe: {len(list(IMG_DEST.iterdir()))} resim")
