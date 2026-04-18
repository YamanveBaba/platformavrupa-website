# -*- coding: utf-8 -*-
"""
Platform Avrupa — FOREM İş İlanı Çekici
Kaynak: Le Forem (Wallonia) OpenDataSoft açık API
Lisans: CC BY-SA 4.0 — ticari kullanım serbest, atıf gerekli
API: https://leforem-digitalwallonia.opendatasoft.com

Kullanım:
  python forem_cek.py                  # Tüm ilanları çek
  python forem_cek.py --max 500        # Maksimum 500 ilan
  python forem_cek.py --dry-run        # Supabase'e yazma, sadece say
  python forem_cek.py --quick          # İlk 100 ilan (smoke test)
  python forem_cek.py --temizle        # Süresi dolan forem ilanlarını expired yap
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPIRY_GUN = 45  # FOREM ilanları genellikle daha uzun süre aktif

FOREM_API = "https://leforem-digitalwallonia.opendatasoft.com/api/explore/v2.1/catalog/datasets/offres-d-emploi-forem/records"
BATCH_LIMIT = 100  # OpenDataSoft max per request

# Alan isimleri (OpenDataSoft gerçek alan adları):
# numerooffreforem → source_id
# titreoffre       → title
# nomemployeur     → owner_name (firma)
# lieuxtravaillocalite → city (liste olabilir, ilk eleman alınır)
# lieuxtravailregion   → province fallback (liste)
# typecontrat      → pozisyon tespiti + description
# regimetravail    → pozisyon tespiti
# url              → source_url
# datedebutdiffusion → yayın tarihi (description)
# metier           → sektör tespiti için ek metin

# ─── SEKTÖR EŞLEMELERİ (Fransızca) ───────────────────────────────────────────

SEKTOR_ESLEME = {
    "Restoran":  ["cuisinier", "chef", "cuisine", "restaurant", "horeca", "boulanger",
                  "boucher", "traiteur", "serveur", "catering", "patissier"],
    "Insaat":    ["construction", "electricien", "plombier", "monteur", "architecte",
                  "charpentier", "maçon", "soudeur bati", "couvreur", "carreleur"],
    "Lojistik":  ["chauffeur", "transport", "logistique", "magasinier", "entrepot",
                  "coursier", "livreur", "cariste", "manutentionnaire", "expediteur"],
    "Temizlik":  ["nettoyage", "technicien de surface", "agent d'entretien", "femme de chambre",
                  "proprete", "entretien menager"],
    "Saglik":    ["infirmier", "soins", "medecin", "docteur", "pharmacien", "kinesitherapeute",
                  "aide soignant", "auxiliaire", "sage-femme", "medic", "paramedic"],
    "Satis":     ["vendeur", "vente", "commercial", "magasin", "retail", "conseiller vente",
                  "agent commercial", "technico-commercial"],
    "Bilisim":   ["developpeur", "logiciel", "informatique", "data", "cloud", "programmeur",
                  "analyste", "ingenieur it", "systeme", "reseau", "devops", "frontend",
                  "backend", "fullstack", "cybersecurite"],
    "Guvenlik":  ["securite", "gardien", "agent de securite", "vigile", "surveillance"],
    "Ofis":      ["administratif", "secretaire", "comptable", "ressources humaines",
                  "manager", "directeur", "assistant", "office", "receptionniste",
                  "juriste", "coordinateur", "charg"],
    "Egitim":    ["enseignant", "professeur", "formateur", "educateur", "coach",
                  "animateur", "instituteur", "pedagogique"],
    "Uretim":    ["production", "operateur", "usine", "assemblage", "soudeur",
                  "technicien de production", "machiniste", "controleur qualite"],
}

def sektor_bul(text: str) -> str:
    t = text.lower()
    for sektor, kelimeler in SEKTOR_ESLEME.items():
        if any(k in t for k in kelimeler):
            return sektor
    return "Diger"

def _ilk_eleman(val) -> str:
    """Liste veya string değerden ilk anlamlı stringi al."""
    if isinstance(val, list):
        for v in val:
            if v and str(v).strip():
                return str(v).strip()
        return ""
    return str(val).strip() if val else ""

def sehir_temizle(localite, region) -> str:
    """Şehir adını temizle — localite önce, region fallback."""
    s = _ilk_eleman(localite)
    if s:
        return s[:100]
    s = _ilk_eleman(region)
    if s and s.upper() not in ("BELGIQUE", "RÉGION WALLONNE", "WALLONIE"):
        return s[:100]
    return "Belçika"

def contrat_tipi(type_contrat: str, regime: str) -> str:
    """Sözleşme tipini pozisyon alanına çevir."""
    t = (type_contrat or "").lower()
    r = (regime or "").lower()
    if "teletravail" in t or "domicile" in t:
        return "Uzaktan"
    if "partiel" in r or "mi-temps" in r:
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
    # Yarıya böl ve tekrar dene
    if len(rows) > 1:
        yari = len(rows) // 2
        return (upsert_ilanlar(sb_url, sb_key, rows[:yari], dry_run) +
                upsert_ilanlar(sb_url, sb_key, rows[yari:], dry_run))
    print(f"  UYARI: upsert {r.status_code}: {r.text[:300]}")
    return 0

def expired_yap(sb_url: str, sb_key: str, dry_run: bool) -> int:
    import re
    sinir = (datetime.now(timezone.utc) - timedelta(days=EXPIRY_GUN)).isoformat()
    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    params = {
        "source": "eq.forem",
        "status": "eq.active",
        "created_at": f"lt.{sinir}",
        "select": "id"
    }
    r = requests.get(f"{sb_url}/rest/v1/ilanlar", params=params, headers=headers, timeout=30)
    m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
    toplam = int(m.group(1)) if m else 0
    if toplam == 0:
        print("  Süresi dolan FOREM ilanı yok.")
        return 0
    if dry_run:
        print(f"  [dry-run] {toplam} FOREM ilanı expired yapılacaktı.")
        return toplam
    patch = requests.patch(
        f"{sb_url}/rest/v1/ilanlar?source=eq.forem&status=eq.active&created_at=lt.{sinir}",
        json={"status": "expired"},
        headers={**headers, "Prefer": "return=minimal"},
        timeout=60,
    )
    if patch.status_code not in (200, 204):
        print(f"  UYARI: expired güncelleme hatası {patch.status_code}")
        return 0
    print(f"  {toplam} FOREM ilanı expired yapıldı.")
    return toplam

def _yeni_ilan(record: dict) -> Optional[dict]:
    """OpenDataSoft kaydını ilanlar tablosu satırına çevir.

    Gerçek alan isimleri (API'den doğrulandı):
      numerooffreforem, titreoffre, nomemployeur, lieuxtravaillocalite,
      lieuxtravailregion, typecontrat, regimetravail, url,
      datedebutdiffusion, metier
    """
    source_id = str(record.get("numerooffreforem", "")).strip()
    if not source_id:
        return None
    baslik = (record.get("titreoffre") or "").strip()
    if not baslik:
        return None

    firma      = (record.get("nomemployeur") or "").strip()
    localite   = record.get("lieuxtravaillocalite")   # liste veya str
    region     = record.get("lieuxtravailregion")     # liste veya str
    type_cont  = (record.get("typecontrat") or "").strip()
    regime     = (record.get("regimetravail") or "").strip()
    lien       = (record.get("url") or "").strip()
    date_pub   = (record.get("datedebutdiffusion") or "").strip()
    metier     = _ilk_eleman(record.get("metier") or "")
    secteurs   = _ilk_eleman(record.get("secteurs") or "")

    sehir = sehir_temizle(localite, region)

    if not lien:
        lien = f"https://www.leforem.be/offres-d-emploi/detail/{source_id}"

    aciklama_parts = []
    if type_cont:
        aciklama_parts.append(f"Contrat: {type_cont}")
    if regime:
        aciklama_parts.append(f"Régime: {regime}")
    if metier:
        aciklama_parts.append(f"Métier: {metier}")
    if date_pub:
        aciklama_parts.append(f"Publié: {date_pub[:10]}")
    aciklama_parts.append("Source: FOREM (Wallonie)")
    aciklama = " | ".join(aciklama_parts)

    sektor_metin = baslik + " " + firma + " " + metier + " " + secteurs

    return {
        "title":        baslik[:300],
        "description":  aciklama[:2000],
        "category":     "Is Ilani",
        "sub_category": "Tam Zamanli",
        "status":       "active",
        "source":       "forem",
        "source_id":    source_id,
        "source_url":   lien[:500],
        "owner_name":   firma[:200],
        "city":         sehir,
        "country":      "BE",
        "sektor":       sektor_bul(sektor_metin),
        "pozisyon":     contrat_tipi(type_cont, regime),
        "price":        "",
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "expires_at":   (datetime.now(timezone.utc) + timedelta(days=EXPIRY_GUN)).isoformat(),
    }

# ─── FOREM API ────────────────────────────────────────────────────────────────

# OpenDataSoft max offset = 10.000. Daha fazlası için where filtresiyle
# tarihe göre böleriz — her pencere 10.000'den az kayıt olacak şekilde.

def _tarih_pencereler() -> list[tuple[str, str]]:
    """
    2024-10-01'den bugüne kadar haftalık/aylık pencereler üret.
    Her pencere <10.000 ilan içerecek şekilde tasarlandı:
      - 2024-10 .. 2026-02: aylık (az kayıt)
      - 2026-03: haftalık bölünmüş
      - 2026-04: her 7 gün
    """
    bugun = datetime.now(timezone.utc).date()
    pencereler = []

    # Aylık pencereler: 2024-10 → 2026-02
    from datetime import date
    d = date(2024, 10, 1)
    bitis_aylik = date(2026, 3, 1)
    while d < bitis_aylik:
        ay = d.month + 1
        yil = d.year + (1 if ay > 12 else 0)
        ay = ay if ay <= 12 else 1
        son = date(yil, ay, 1)
        pencereler.append((d.isoformat(), son.isoformat()))
        d = son

    # 2026-03 başından bugüne kadar: 7 günlük pencereler
    d = date(2026, 3, 1)
    adim = timedelta(days=7)
    while d <= bugun:
        son = min(d + adim, bugun + timedelta(days=1))
        pencereler.append((d.isoformat(), son.isoformat()))
        d = son

    return pencereler

def _forem_pencere_cek(
    bas: str,
    bit: str,
    gorduler: set,
    max_kalan: int,
) -> list[dict]:
    """Belirli tarih aralığındaki FOREM ilanlarını çek (offset < 10.000 güvenceli)."""
    ilanlar = []
    offset = 0
    hata = 0
    where = f'datedebutdiffusion >= "{bas}" AND datedebutdiffusion < "{bit}"'

    while len(ilanlar) < max_kalan:
        try:
            r = requests.get(
                FOREM_API,
                params={
                    "limit": BATCH_LIMIT,
                    "offset": offset,
                    "where": where,
                    "order_by": "datedebutdiffusion desc",
                },
                headers={"User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0"},
                timeout=30,
            )
        except Exception as e:
            hata += 1
            if hata >= 5:
                break
            time.sleep(5)
            continue

        if r.status_code == 429:
            time.sleep(60)
            continue
        if r.status_code != 200:
            break

        hata = 0
        data = r.json()
        records = data.get("results", [])
        if not records:
            break

        for rec in records:
            ilan = _yeni_ilan(rec)
            if ilan and ilan["source_id"] not in gorduler:
                gorduler.add(ilan["source_id"])
                ilanlar.append(ilan)
            if len(ilanlar) >= max_kalan:
                break

        if len(records) < BATCH_LIMIT or offset + BATCH_LIMIT >= 10000:
            break

        offset += BATCH_LIMIT
        time.sleep(random.uniform(0.3, 0.6))

    return ilanlar

def forem_cek(max_ilan: int = 30000) -> list[dict]:
    """FOREM ilanlarını tarih pencerelere bölerek çek (10.000 offset limitini aşar)."""
    print("\n[FOREM] Çekiliyor (tarih pencereleri ile)...")
    tum_ilanlar: list[dict] = []
    gorduler: set = set()
    pencereler = _tarih_pencereler()

    for bas, bit in pencereler:
        if len(tum_ilanlar) >= max_ilan:
            break
        kalan = max_ilan - len(tum_ilanlar)
        onceki = len(tum_ilanlar)
        yeniler = _forem_pencere_cek(bas, bit, gorduler, kalan)
        tum_ilanlar.extend(yeniler)
        if yeniler:
            print(f"  {bas} → {bit}: {len(yeniler)} ilan | Toplam: {len(tum_ilanlar)}")
        time.sleep(random.uniform(0.2, 0.5))

    print(f"  FOREM toplam: {len(tum_ilanlar)} ilan")
    return tum_ilanlar

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Platform Avrupa — FOREM İş İlanı Çekici")
    parser.add_argument("--max", type=int, default=30000, help="Maksimum çekilecek ilan sayısı")
    parser.add_argument("--dry-run", action="store_true", help="Supabase'e yazma")
    parser.add_argument("--temizle", action="store_true", help="Süresi dolan FOREM ilanlarını expired yap")
    parser.add_argument("--quick", action="store_true", help="İlk 100 ilan (smoke test)")
    args = parser.parse_args()

    sb_url, sb_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if args.dry_run:
        print("[DRY-RUN MODU]\n")
    if args.quick:
        print("[QUICK — ilk 100 ilan]\n")
        args.max = 100

    start = time.time()
    toplam_eklenen = 0

    if args.temizle:
        print("\n[Temizlik] Süresi dolan FOREM ilanları...")
        expired_yap(sb_url, sb_key, args.dry_run)

    tum_ilanlar = forem_cek(max_ilan=args.max)

    if not tum_ilanlar:
        print("\nHiç ilan çekilemedi.")
        return

    print(f"\nToplam çekilen: {len(tum_ilanlar)} ilan")

    # Upsert — 300'er batch
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
