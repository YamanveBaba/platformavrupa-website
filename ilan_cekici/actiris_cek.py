# -*- coding: utf-8 -*-
"""
Platform Avrupa — Actiris İş İlanı Çekici
Kaynak: Actiris Brussels — dahili POST API
        https://www.actiris.brussels/Umbraco/api/OffersApi/GetAllOffers
Bölge: Brüksel Başkent Bölgesi (~33.000 aktif ilan)

Kullanım:
  python actiris_cek.py                  # Tüm ilanları çek
  python actiris_cek.py --max 500        # Maksimum 500 ilan
  python actiris_cek.py --dry-run        # Supabase'e yazma
  python actiris_cek.py --quick          # İlk 50 ilan (smoke test)
  python actiris_cek.py --temizle        # Süresi dolan ilanları expired yap

NOT: Actiris'in resmi public API'si yoktur; bu script dahili API uç noktasını kullanır.
     Sunucu kısıtlamalarına saygı için istek araları uygulanır.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPIRY_GUN = 30

ACTIRIS_API = "https://www.actiris.brussels/Umbraco/api/OffersApi/GetAllOffers"
ACTIRIS_SEARCH = "https://www.actiris.brussels/fr/citoyens/offres-d-emploi/"
PAGE_SIZE = 50   # API 100'e kadar destekler, 50 daha kararlı

# ─── SEKTÖR EŞLEMELERİ (Fransızca / Flemenkçe — Brüksel ağırlıklı) ───────────

SEKTOR_ESLEME = {
    "Restoran":  ["cuisinier", "chef", "cuisine", "restaurant", "horeca", "boulanger",
                  "boucher", "traiteur", "serveur", "catering", "kok", "keukenhulp"],
    "Insaat":    ["construction", "electricien", "plombier", "monteur", "architecte",
                  "charpentier", "maçon", "couvreur", "carreleur", "soudeur"],
    "Lojistik":  ["chauffeur", "transport", "logistique", "magasinier", "entrepot",
                  "coursier", "livreur", "cariste", "manutentionnaire"],
    "Temizlik":  ["nettoyage", "agent d'entretien", "proprete", "schoonmaak", "poetsen"],
    "Saglik":    ["infirmier", "soins", "medecin", "docteur", "pharmacien",
                  "kinesitherapeute", "aide soignant", "verpleeg", "zorg", "arts"],
    "Satis":     ["vendeur", "vente", "commercial", "magasin", "retail",
                  "conseiller vente", "verkoop", "verkoops"],
    "Bilisim":   ["developpeur", "logiciel", "informatique", "data", "cloud",
                  "programmeur", "analyste", "ingenieur it", "devops", "ict",
                  "software", "developer", "cybersecurite"],
    "Guvenlik":  ["securite", "gardien", "agent de securite", "vigile", "bewaking"],
    "Ofis":      ["administratif", "secretaire", "comptable", "ressources humaines",
                  "manager", "directeur", "assistant", "receptionniste",
                  "juriste", "coordinateur", "charge de", "administrateur"],
    "Egitim":    ["enseignant", "professeur", "formateur", "educateur", "animateur",
                  "instituteur", "leerkracht", "leraar", "begeleider"],
    "Uretim":    ["production", "operateur", "usine", "assemblage", "soudeur",
                  "controleur qualite", "technicien de production"],
}

def sektor_bul(text: str) -> str:
    t = text.lower()
    for sektor, kelimeler in SEKTOR_ESLEME.items():
        if any(k in t for k in kelimeler):
            return sektor
    return "Diger"

def pozisyon_bul(type_contrat: str, regime: str) -> str:
    t = (type_contrat or "").lower()
    r = (regime or "").lower()
    if "teletravail" in t or "domicile" in t:
        return "Uzaktan"
    if "partiel" in r or "mi-temps" in r or "deeltijds" in r:
        return "Yari Zamanli"
    return "Ofis"

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def load_secrets() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if url and key:
        return url.rstrip("/"), key
    secrets_path = os.path.normpath(
        os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
    )
    if os.path.isfile(secrets_path):
        lines = [l.strip() for l in open(secrets_path, encoding="utf-8", errors="ignore")
                 if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 2:
            return lines[0].rstrip("/"), lines[1]
    print("HATA: Supabase credentials bulunamadı.")
    sys.exit(1)

def upsert_ilanlar(sb_url: str, sb_key: str, rows: list[dict], dry_run: bool) -> int:
    if dry_run or not rows:
        return len(rows)
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    url = f"{sb_url}/rest/v1/ilanlar?on_conflict=source,source_id"
    r = requests.post(url, json=rows, headers=headers, timeout=120)
    if r.status_code in (200, 201, 204):
        return len(rows)
    if len(rows) > 1:
        yari = len(rows) // 2
        return (upsert_ilanlar(sb_url, sb_key, rows[:yari], dry_run) +
                upsert_ilanlar(sb_url, sb_key, rows[yari:], dry_run))
    print(f"  UYARI: upsert {r.status_code}: {r.text[:300]}")
    return 0

def expired_yap(sb_url: str, sb_key: str, dry_run: bool) -> int:
    sinir = (datetime.now(timezone.utc) - timedelta(days=EXPIRY_GUN)).isoformat()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    params = {"source": "eq.actiris", "status": "eq.active",
              "created_at": f"lt.{sinir}", "select": "id"}
    r = requests.get(f"{sb_url}/rest/v1/ilanlar", params=params, headers=headers, timeout=30)
    m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
    toplam = int(m.group(1)) if m else 0
    if toplam == 0:
        print("  Süresi dolan Actiris ilanı yok.")
        return 0
    if dry_run:
        print(f"  [dry-run] {toplam} Actiris ilanı expired yapılacaktı.")
        return toplam
    patch = requests.patch(
        f"{sb_url}/rest/v1/ilanlar?source=eq.actiris&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"},
        headers={**headers, "Content-Type": "application/json", "Prefer": "return=minimal"},
        timeout=60,
    )
    if patch.status_code not in (200, 204):
        print(f"  UYARI: expired güncelleme hatası {patch.status_code}")
        return 0
    print(f"  {toplam} Actiris ilanı expired yapıldı.")
    return toplam

# ─── ACTIRIS API ──────────────────────────────────────────────────────────────

_ACTIRIS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr",
    "Origin": "https://www.actiris.brussels",
    "Referer": "https://www.actiris.brussels/fr/citoyens/offres-d-emploi/",
    # Chromium client hints — sunucu bunları kontrol ediyor
    "sec-ch-ua": '"Not:A-Brand";v="99", "Chromium";v="124"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

def _actiris_payload(page: int, from_idx: int) -> dict:
    return {
        "pageOption": {
            "page": page,
            "from": from_idx,
            "pageSize": PAGE_SIZE,
        },
        "offreFilter": {
            "texte": None,
            "regimesTravail": None,
            "dateDerniereModification": None,
            "langue": None,
            "codesPostal": [],
            "codesContrat": [],
            "domainesImt": [],
            "secteursPanorama": [],
            "references": None,
            "localisation": "Tout",
            "keywordSearchType": "Partout",
            "isOffreActiris": False,
            "isOffreVdabForem": False,
            "isOfferPartner": False,
            "isOffreHandicap": False,
            "employerFilter": [],
        }
    }

def _ilan_donustur(item: dict) -> Optional[dict]:
    """Actiris API öğesini ilanlar tablosu satırına çevir."""
    ref = str(item.get("reference", "")).strip()
    if not ref:
        return None

    # Başlık — Fransızca önce, Flemenkçe fallback
    baslik = (item.get("titreFr") or item.get("titreNl") or "").strip()
    if not baslik:
        return None

    # Firma adı
    emp = item.get("employeur") or {}
    firma = (emp.get("nomFr") or emp.get("nomNl") or "").strip()

    # Şehir — posta kodu + Brüksel
    code_postal = str(item.get("codePostal") or "").strip()
    commune_fr = (item.get("communeFr") or "").strip()
    commune_nl = (item.get("communeNl") or "").strip()
    sehir = commune_fr or commune_nl or (f"Brüksel {code_postal}" if code_postal else "Brüksel")

    # Sözleşme
    type_cont = (item.get("typeContratLibelle") or item.get("typeContrat") or "").strip()
    regime = (item.get("regimeTravail") or "").strip()

    # URL
    source_url = ACTIRIS_SEARCH

    # Açıklama
    aciklama_parts = []
    if type_cont:
        aciklama_parts.append(f"Contrat: {type_cont}")
    if item.get("dureeContratLibelle"):
        aciklama_parts.append(f"Durée: {item['dureeContratLibelle']}")
    aciklama_parts.append("Source: Actiris (Brüksel Bölgesi)")
    aciklama = " | ".join(aciklama_parts)

    return {
        "title":        baslik[:300],
        "description":  aciklama[:2000],
        "category":     "Is Ilani",
        "sub_category": "Tam Zamanli",
        "status":       "active",
        "source":       "actiris",
        "source_id":    ref,
        "source_url":   source_url,
        "owner_name":   firma[:200],
        "city":         sehir[:100],
        "country":      "BE",
        "sektor":       sektor_bul(baslik + " " + firma),
        "pozisyon":     pozisyon_bul(type_cont, regime),
        "price":        "",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "expires_at":   (datetime.now(timezone.utc) + timedelta(days=EXPIRY_GUN)).isoformat(),
    }

def actiris_cek(max_ilan: int = 40000) -> list[dict]:
    """Actiris API'sinden tüm aktif Brüksel ilanlarını çek."""
    print(f"\n[Actiris] Çekiliyor... (max={max_ilan})")
    ilanlar = []
    hata_sayac = 0
    sayfa = 1
    from_idx = 0

    # İlk çağrıda toplam sayıyı öğren
    toplam_api = None

    session = requests.Session()
    session.headers.update(_ACTIRIS_HEADERS)

    while len(ilanlar) < max_ilan:
        try:
            r = session.post(
                ACTIRIS_API,
                json=_actiris_payload(sayfa, from_idx),
                timeout=30,
            )
        except Exception as e:
            hata_sayac += 1
            print(f"  İstek hatası (sayfa={sayfa}): {e}")
            if hata_sayac >= 5:
                print("  Çok fazla hata, duruldu.")
                break
            time.sleep(5)
            continue

        if r.status_code == 429:
            print(f"  Rate limit (sayfa={sayfa}), 60sn bekleniyor...")
            time.sleep(60)
            continue

        if r.status_code != 200:
            print(f"  HTTP {r.status_code} sayfa={sayfa}, duruldu.")
            break

        hata_sayac = 0
        data = r.json()

        if toplam_api is None:
            toplam_api = data.get("total", 0)
            print(f"  Actiris toplam ilan: {toplam_api:,}")

        items = data.get("items", [])
        if not items:
            print("  Öğe kalmadı, tamamlandı.")
            break

        yeni = 0
        for item in items:
            ilan = _ilan_donustur(item)
            if ilan:
                ilanlar.append(ilan)
                yeni += 1
            if len(ilanlar) >= max_ilan:
                break

        print(f"  Sayfa {sayfa}: {yeni} yeni ilan | Toplam: {len(ilanlar)}/{min(max_ilan, toplam_api or max_ilan)}")

        if len(items) < PAGE_SIZE:
            print("  Son sayfa, tamamlandı.")
            break

        if len(ilanlar) >= max_ilan:
            break

        sayfa += 1
        from_idx += PAGE_SIZE
        time.sleep(random.uniform(0.5, 1.0))

    print(f"  Actiris toplam: {len(ilanlar)} ilan")
    return ilanlar

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Platform Avrupa — Actiris İş İlanı Çekici")
    parser.add_argument("--max", type=int, default=40000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--temizle", action="store_true")
    parser.add_argument("--quick", action="store_true", help="İlk 50 ilan (smoke test)")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN MODU]\n")
    if args.quick:
        args.max = 50
        print("[QUICK — 50 ilan]\n")

    start = time.time()
    toplam_eklenen = 0

    if args.temizle:
        print("\n[Temizlik] Süresi dolan Actiris ilanları...")
        expired_yap(sb_url, sb_key, args.dry_run)

    tum_ilanlar = actiris_cek(max_ilan=args.max)

    if not tum_ilanlar:
        print("\nHiç ilan çekilemedi.")
        return

    print(f"\nToplam çekilen: {len(tum_ilanlar)} ilan")

    BATCH = 300
    for i in range(0, len(tum_ilanlar), BATCH):
        batch = tum_ilanlar[i:i + BATCH]
        n = upsert_ilanlar(sb_url, sb_key, batch, args.dry_run)
        toplam_eklenen += n
        if not args.dry_run:
            print(f"  Upsert: {min(i + BATCH, len(tum_ilanlar))} / {len(tum_ilanlar)}")
        time.sleep(0.2)

    elapsed = time.time() - start
    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Tamamlandı.")
    print(f"  Upsert edilen: {toplam_eklenen} ilan")
    print(f"  Süre: {elapsed:.1f} sn")

if __name__ == "__main__":
    main()
