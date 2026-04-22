# -*- coding: utf-8 -*-
"""
Platform Avrupa — Otomatik Haber Cekici
Avrupa'daki Turkleri ilgilendiren haberleri RSS'ten ceker,
Gemini ile filtreler, Supabase announcements tablosuna yazar.

Kullanim:
  python haber_cek.py
  python haber_cek.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
import random
from datetime import datetime, timezone, timedelta

try:
    import requests
    import feedparser
except ImportError:
    print("HATA: pip install requests feedparser"); sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# RSS kaynakları — Avrupa Türkleri için
RSS_KAYNAKLAR = [
    # Türk medyası
    {"url": "https://www.aa.com.tr/tr/rss/default.aspx",         "kaynak": "Anadolu Ajansı"},
    {"url": "https://www.ntv.com.tr/son-dakika.rss",             "kaynak": "NTV"},
    {"url": "http://rss.dw.com/rdf/rss-tur-all",                 "kaynak": "DW Türkçe"},
    {"url": "https://www.bbc.com/turkce/index.xml",              "kaynak": "BBC Türkçe"},
    {"url": "https://www.trthaber.com/anasayfa.rss",             "kaynak": "TRT Haber"},
    # Avrupa Türk medyası
    {"url": "https://www.avrupahaber.net/feed",                  "kaynak": "Avrupa Haber"},
    {"url": "https://www.almanyabulteni.de/feed",                "kaynak": "Almanya Bülteni"},
    {"url": "https://www.dailysabah.com/rss",                    "kaynak": "Daily Sabah"},
    {"url": "https://www.hurriyetdailynews.com/rss",             "kaynak": "Hürriyet Daily News"},
    # AB haberleri
    {"url": "https://www.euractiv.com/feed/",                    "kaynak": "Euractiv"},
    # Google News — Avrupa Türkleri araması
    {"url": "https://news.google.com/rss/search?q=Avrupa+Türkler&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News TR"},
    {"url": "https://news.google.com/rss/search?q=Almanya+Türk+ikamet&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News DE"},
    {"url": "https://news.google.com/rss/search?q=Belçika+Türk+vize&hl=tr&gl=TR&ceid=TR:tr",   "kaynak": "Google News BE"},
    {"url": "https://news.google.com/rss/search?q=Hollanda+Türk+vatandaş&hl=tr&gl=TR&ceid=TR:tr", "kaynak": "Google News NL"},
]

# Alakalı anahtar kelimeler (Gemini olmadan hızlı ön filtre)
ALAKALI_KELIMELER = [
    "avrupa", "almanya", "hollanda", "belçika", "fransa", "avusturya",
    "gurbetçi", "diaspora", "ikamet", "oturma izni", "vize", "vatandaşlık",
    "pasaport", "sgk", "emekli", "yurt dışı", "ab ", "avrupa birliği",
    "schengen", "işçi", "göçmen", "mülteci", "sığınmacı",
    "döviz", "euro", "türk lirası", "vergi", "sigorta",
    "belçika", "brüksel", "berlin", "paris", "amsterdam", "viyana",
    "türkiye-ab", "türkiye-avrupa", "türkiye-almanya",
    "çifte vatandaşlık", "bürokratik", "konsolosluk", "büyükelçilik",
    "eğitim", "burs", "üniversite", "okul",
    "konut", "kira", "satın alma", "tapu",
]

ALAKASIZ_KELIMELER = [
    "futbol skoru", "maç sonucu", "şampiyon", "transfer",
    "magazin", "ünlü", "evlendi", "boşandı", "dizi", "film",
    "reklam", "indirim kampanyası", "satılık", "kiralık",
]

def load_secrets() -> tuple[str, str, str]:
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not sb_url or not sb_key:
        path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt"))
        if os.path.isfile(path):
            lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                     if l.strip() and not l.strip().startswith("#")]
            if len(lines) >= 2:
                sb_url, sb_key = lines[0].rstrip("/"), lines[1]

    if not sb_url or not sb_key:
        print("HATA: Supabase credentials bulunamadi."); sys.exit(1)

    return sb_url.rstrip("/"), sb_key, gemini_key

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def mevcut_hash_ler(sb_url: str, sb_key: str) -> set[str]:
    """DB'deki mevcut haber hash'lerini cek (duplicate kontrolu)."""
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    r = requests.get(
        f"{sb_url}/rest/v1/announcements?select=source_hash&source=eq.otomatik&limit=2000",
        headers=headers, timeout=15
    )
    if r.status_code != 200:
        return set()
    return {row["source_hash"] for row in r.json() if row.get("source_hash")}

def rss_cek() -> list[dict]:
    """Tum RSS kaynaklarindan haberleri cek."""
    haberler = []
    iki_gun_once = datetime.now(timezone.utc) - timedelta(days=2)

    for kaynak in RSS_KAYNAKLAR:
        try:
            feed = feedparser.parse(kaynak["url"])
            for entry in feed.entries[:20]:
                baslik = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                ozet = entry.get("summary", entry.get("description", "")).strip()

                if not baslik or not link:
                    continue

                # Tarih kontrolu — son 2 gun
                tarih = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        tarih = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                if tarih and tarih < iki_gun_once:
                    continue

                haberler.append({
                    "baslik": baslik,
                    "link": link,
                    "ozet": ozet[:500],
                    "kaynak": kaynak["kaynak"],
                    "hash": url_hash(link),
                    "tarih": tarih.isoformat() if tarih else datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            print(f"  RSS hata ({kaynak['kaynak']}): {str(e)[:60]}")

    return haberler

def on_filtre(haber: dict) -> bool:
    """Gemini'ye gitmeden once hizli keyword filtresi."""
    metin = (haber["baslik"] + " " + haber["ozet"]).lower()
    # Herhangi bir alakali kelime varsa gecir
    for k in ALAKALI_KELIMELER:
        if k.lower() in metin:
            # Alakasiz kelimeler yoksa
            for a in ALAKASIZ_KELIMELER:
                if a.lower() in metin:
                    return False
            return True
    return False

def gemini_filtrele(haber: dict, gemini_key: str) -> dict | None:
    """Gemini Flash ile haber filtrele ve ozet cikart."""
    if not gemini_key:
        # Gemini key yoksa keyword filtresine guvun
        return {
            "alakali": True,
            "ozet": haber["ozet"][:300] or haber["baslik"],
            "kategori": "genel",
            "ulke": "genel",
        }

    prompt = f"""Avrupa'daki Türkler için çalışan bir haber editörüsün.

Şu haberi analiz et ve SADECE JSON döndür:

BAŞLIK: {haber['baslik']}
ÖZET: {haber['ozet'][:400]}
KAYNAK: {haber['kaynak']}

JSON format:
{{"alakali": true/false, "ozet": "2 cümle Türkçe özet", "ulke": "almanya/hollanda/belcika/fransa/genel"}}

Alakalı = Avrupa'daki Türklerin günlük hayatını etkiler (vize, ikamet, vatandaşlık, iş, eğitim, sosyal haklar, Türkiye-AB ilişkileri, gurbetçi haberleri).
Alakasız = spor skoru, magazin, reklam, Türkiye iç siyaseti (Avrupa'yı etkilemiyorsa)."""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_key}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 150, "temperature": 0.1}},
            timeout=15
        )
        if r.status_code == 429:  # Rate limit
            print("  Gemini rate limit — keyword filtresi kullanilacak")
            return {"alakali": True, "ozet": haber["ozet"][:300] or haber["baslik"], "ulke": "genel"}

        if r.status_code != 200:
            return None

        metin = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # JSON'u parse et
        import json, re
        json_match = re.search(r'\{.*\}', metin, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"  Gemini hata: {str(e)[:60]}")

    return None

def supabase_kaydet(sb_url: str, sb_key: str, haberler: list[dict], dry_run: bool) -> int:
    if dry_run:
        return len(haberler)

    headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal",
    }

    basarili = 0
    for h in haberler:
        row = {
            "title": h["baslik"][:500],
            "content": f'<p>{h["ozet"]}</p>\n<p><a href="{h["link"]}" target="_blank" rel="noopener">Kaynağa git: {h["kaynak"]}</a></p>',
            "type": "genel" if h.get("ulke", "genel") == "genel" else "ulke",
            "country_code": None if h.get("ulke", "genel") == "genel" else h["ulke"][:2].upper(),
            "source": "otomatik",
            "source_url": h["link"],
            "source_hash": h["hash"],
            "created_at": h["tarih"],
        }
        r = requests.post(
            f"{sb_url}/rest/v1/announcements",
            json=[row], headers=headers, timeout=15
        )
        if r.status_code in (200, 201, 204):
            basarili += 1
        else:
            print(f"  UYARI: Kayit hatasi {r.status_code}: {r.text[:100]}")

    return basarili

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb_url, sb_key, gemini_key = load_secrets()
    print(f"Supabase: {sb_url}")
    if not gemini_key:
        print("UYARI: GEMINI_API_KEY yok — sadece keyword filtresi kullanilacak")
    if args.dry_run:
        print("[DRY-RUN]\n")

    # Mevcut hash'leri cek (duplicate kontrolu)
    print("Mevcut haberler kontrol ediliyor...")
    mevcut = mevcut_hash_ler(sb_url, sb_key)
    print(f"  DB'de {len(mevcut)} otomatik haber var\n")

    # RSS cek
    print("RSS kaynakları taranıyor...")
    haberler = rss_cek()
    print(f"  {len(haberler)} haber çekildi\n")

    # Duplicate filtresi
    haberler = [h for h in haberler if h["hash"] not in mevcut]
    print(f"  {len(haberler)} yeni haber (duplicate'ler cıkarıldı)\n")

    # On filtre (keyword)
    haberler = [h for h in haberler if on_filtre(h)]
    print(f"  {len(haberler)} haber keyword filtresini gecti\n")

    if not haberler:
        print("Yeni alakali haber yok.")
        return

    # Gemini filtresi
    print("Gemini ile filtreleniyor...")
    gecenler = []
    for i, h in enumerate(haberler):
        if gemini_key:
            time.sleep(random.uniform(0.5, 1.5))  # Rate limit icin bekle
        sonuc = gemini_filtrele(h, gemini_key)
        if sonuc and sonuc.get("alakali"):
            h["ozet"] = sonuc.get("ozet", h["ozet"])
            h["ulke"] = sonuc.get("ulke", "genel")
            gecenler.append(h)
            print(f"  ✓ [{h['kaynak']}] {h['baslik'][:70]}")
        else:
            print(f"  ✗ [{h['kaynak']}] {h['baslik'][:70]}")

    print(f"\n  {len(gecenler)}/{len(haberler)} haber filtreyi gecti\n")

    # Kaydet
    if gecenler:
        print("Supabase'e kaydediliyor...")
        yazilan = supabase_kaydet(sb_url, sb_key, gecenler, args.dry_run)
        print(f"  {yazilan} haber kaydedildi.")
    else:
        print("Kaydedilecek haber yok.")

    print("\nTamamlandi.")

if __name__ == "__main__":
    main()
