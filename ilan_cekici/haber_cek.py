# -*- coding: utf-8 -*-
"""
Platform Avrupa — Otomatik Haber Cekici
Avrupa'daki Turkleri ilgilendiren haberleri RSS'ten ceker,
Gemini ile filtreler/skorlar, Supabase announcements tablosuna yazar.

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

ULKE_MAP = {
    "almanya": "DE",
    "hollanda": "NL",
    "belcika": "BE",
    "fransa": "FR",
    "avusturya": "AT",
    "ingiltere": "GB",
    "italya": "IT",
    "ispanya": "ES",
    "genel": None,
}

# RSS kaynakları — Avrupa Türkleri için
RSS_KAYNAKLAR = [
    # Türk medyası
    {"url": "https://www.aa.com.tr/tr/rss/default.aspx",               "kaynak": "Anadolu Ajansı"},
    {"url": "https://www.ntv.com.tr/son-dakika.rss",                   "kaynak": "NTV"},
    {"url": "https://www.cnnturk.com/feed/rss/main/news",              "kaynak": "CNN Türk"},
    {"url": "http://rss.dw.com/rdf/rss-tur-all",                       "kaynak": "DW Türkçe"},
    {"url": "https://www.bbc.com/turkce/index.xml",                    "kaynak": "BBC Türkçe"},
    {"url": "https://www.trthaber.com/anasayfa.rss",                   "kaynak": "TRT Haber"},
    {"url": "https://www.sabah.com.tr/rss/anasayfa.xml",               "kaynak": "Sabah"},
    {"url": "https://www.milliyet.com.tr/rss/rssnew/gundemrss.xml",    "kaynak": "Milliyet"},
    {"url": "https://www.hurriyet.com.tr/rss/gundem",                  "kaynak": "Hürriyet"},
    {"url": "https://www.haberler.com/rss/",                           "kaynak": "Haberler.com"},
    {"url": "https://www.ensonhaber.com/rss.xml",                      "kaynak": "En Son Haber"},
    # Uluslararası Türkçe
    {"url": "https://www.france24.com/tr/rss",                   "kaynak": "France24 Türkçe"},
    {"url": "https://tr.euronews.com/rss",                       "kaynak": "Euronews Türkçe"},
    {"url": "https://www.t24.com.tr/rss",                        "kaynak": "T24"},
    {"url": "https://bianet.org/bianet/rss",                     "kaynak": "Bianet"},
    # Reddit
    {"url": "https://www.reddit.com/r/gurbetci.rss",            "kaynak": "Reddit r/gurbetci"},
    {"url": "https://www.reddit.com/r/Turkey.rss",              "kaynak": "Reddit r/Turkey"},
    {"url": "https://www.reddit.com/r/europe.rss",              "kaynak": "Reddit r/europe"},
    # Avrupa Türk medyası
    {"url": "https://www.avrupahaber.net/feed",                  "kaynak": "Avrupa Haber"},
    {"url": "https://www.almanyabulteni.de/feed",                "kaynak": "Almanya Bülteni"},
    {"url": "https://www.dailysabah.com/rss",                    "kaynak": "Daily Sabah"},
    {"url": "https://www.hurriyetdailynews.com/rss",             "kaynak": "Hürriyet Daily News"},
    # AB haberleri
    {"url": "https://www.euractiv.com/feed/",                    "kaynak": "Euractiv"},
    # Google News — Avrupa Türkleri araması
    {"url": "https://news.google.com/rss/search?q=Avrupa+Türkler&hl=tr&gl=TR&ceid=TR:tr",                   "kaynak": "Google News TR"},
    {"url": "https://news.google.com/rss/search?q=Almanya+Türk+ikamet&hl=tr&gl=TR&ceid=TR:tr",              "kaynak": "Google News DE"},
    {"url": "https://news.google.com/rss/search?q=Belçika+Türk+vize&hl=tr&gl=TR&ceid=TR:tr",                "kaynak": "Google News BE"},
    {"url": "https://news.google.com/rss/search?q=Hollanda+Türk+vatandaş&hl=tr&gl=TR&ceid=TR:tr",           "kaynak": "Google News NL"},
    {"url": "https://news.google.com/rss/search?q=Fransa+Türk+ikamet&hl=tr&gl=TR&ceid=TR:tr",               "kaynak": "Google News FR"},
    {"url": "https://news.google.com/rss/search?q=vatandaşlık+başvurusu+Avrupa&hl=tr&gl=TR&ceid=TR:tr",     "kaynak": "Google News Vatandaşlık"},
    {"url": "https://news.google.com/rss/search?q=oturma+izni+Avrupa+Türkiye&hl=tr&gl=TR&ceid=TR:tr",       "kaynak": "Google News Oturma"},
    {"url": "https://news.google.com/rss/search?q=Avrupa+emekli+Türkiye+SGK&hl=tr&gl=TR&ceid=TR:tr",        "kaynak": "Google News Emekli"},
]

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

def load_secrets() -> tuple[str, str, str, str, str]:
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    if not sb_url or not sb_key:
        path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt"))
        if os.path.isfile(path):
            lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                     if l.strip() and not l.strip().startswith("#")]
            if len(lines) >= 2:
                sb_url, sb_key = lines[0].rstrip("/"), lines[1]

    if not sb_url or not sb_key:
        print("HATA: Supabase credentials bulunamadi."); sys.exit(1)

    return sb_url.rstrip("/"), sb_key, gemini_key, tg_token, tg_chat

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def mevcut_hash_ler(sb_url: str, sb_key: str) -> set[str]:
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    r = requests.get(
        f"{sb_url}/rest/v1/announcements?select=source_hash&source=eq.otomatik&limit=2000",
        headers=headers, timeout=15
    )
    if r.status_code != 200:
        return set()
    return {row["source_hash"] for row in r.json() if row.get("source_hash")}

def rss_cek() -> list[dict]:
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
    metin = (haber["baslik"] + " " + haber["ozet"]).lower()
    for k in ALAKALI_KELIMELER:
        if k.lower() in metin:
            for a in ALAKASIZ_KELIMELER:
                if a.lower() in metin:
                    return False
            return True
    return False

def gemini_filtrele(haber: dict, gemini_key: str) -> dict | None:
    if not gemini_key:
        return {
            "alakali": True,
            "ozet": haber["ozet"][:300] or haber["baslik"],
            "kategori": "genel",
            "ulke": "genel",
            "skor": 5,
        }

    prompt = f"""Avrupa'daki Türkler için çalışan bir haber editörüsün.

Şu haberi analiz et ve SADECE JSON döndür:

BAŞLIK: {haber['baslik']}
ÖZET: {haber['ozet'][:400]}
KAYNAK: {haber['kaynak']}

JSON format:
{{"alakali": true/false, "ozet": "2 cümle Türkçe özet", "ulke": "almanya/hollanda/belcika/fransa/avusturya/ingiltere/italya/ispanya/genel", "kategori": "vize_ikamet|vatandaslik|egitim_burs|is_ekonomi|kultur_toplum|turkiye|avrupa_politika", "skor": 1-10}}

Alakalı = Avrupa'daki Türklerin günlük hayatını etkiler (vize, ikamet, vatandaşlık, iş, eğitim, sosyal haklar, Türkiye-AB ilişkileri, gurbetçi haberleri).
Alakasız = spor skoru, magazin, reklam, Türkiye iç siyaseti (Avrupa'yı etkilemiyorsa).

Skor rehberi:
8-10: Kritik (vize değişikliği, vatandaşlık hakkı, iş imkânı, yasal değişiklik)
5-7: Önemli (kültürel etkinlik, topluluk haberi, ekonomi)
1-4: Düşük öncelik"""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_key}",
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 200, "temperature": 0.1}},
            timeout=15
        )
        if r.status_code == 429:
            print("  Gemini rate limit — keyword filtresi kullanilacak")
            return {"alakali": True, "ozet": haber["ozet"][:300] or haber["baslik"], "ulke": "genel", "kategori": "genel", "skor": 5}

        if r.status_code != 200:
            return None

        metin = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        import json, re
        json_match = re.search(r'\{.*\}', metin, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"  Gemini hata: {str(e)[:60]}")

    return None

def telegram_gonder(token: str, chat_id: str, mesaj: str):
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mesaj, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception:
        pass

def supabase_kaydet(sb_url: str, sb_key: str, haberler: list[dict], dry_run: bool,
                    tg_token: str = "", tg_chat: str = "") -> int:
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
        ulke_str = h.get("ulke", "genel")
        country_code = ULKE_MAP.get(ulke_str, None)
        ai_skor = h.get("ai_skor", 5)

        row = {
            "title": h["baslik"][:500],
            "content": f'<p>{h["ozet"]}</p>\n<p><a href="{h["link"]}" target="_blank" rel="noopener">Kaynağa git: {h["kaynak"]}</a></p>',
            "type": "ulke" if country_code else "genel",
            "country_code": country_code,
            "source": "otomatik",
            "source_url": h["link"],
            "source_hash": h["hash"],
            "created_at": h["tarih"],
            "status": "draft",
            "kategori": h.get("kategori", "genel"),
            "ai_skor": ai_skor,
        }
        r = requests.post(
            f"{sb_url}/rest/v1/announcements",
            json=[row], headers=headers, timeout=15
        )
        if r.status_code in (200, 201, 204):
            basarili += 1
            # Kritik haberler (skor >= 8) anında Telegram'a gider
            if isinstance(ai_skor, int) and ai_skor >= 8 and tg_token and tg_chat:
                tg_mesaj = (
                    f"🔴 <b>Önemli Haber</b> (skor: {ai_skor}/10)\n"
                    f"{h['baslik']}\n\n"
                    f"{h['ozet']}\n\n"
                    f"<a href='{h['link']}'>Kaynağa Git</a>"
                )
                telegram_gonder(tg_token, tg_chat, tg_mesaj)
        else:
            print(f"  UYARI: Kayit hatasi {r.status_code}: {r.text[:100]}")

    return basarili

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb_url, sb_key, gemini_key, tg_token, tg_chat = load_secrets()
    print(f"Supabase: {sb_url}")
    if not gemini_key:
        print("UYARI: GEMINI_API_KEY yok — sadece keyword filtresi kullanilacak")
    if args.dry_run:
        print("[DRY-RUN]\n")

    print("Mevcut haberler kontrol ediliyor...")
    mevcut = mevcut_hash_ler(sb_url, sb_key)
    print(f"  DB'de {len(mevcut)} otomatik haber var\n")

    print("RSS kaynakları taranıyor...")
    haberler = rss_cek()
    print(f"  {len(haberler)} haber çekildi\n")

    haberler = [h for h in haberler if h["hash"] not in mevcut]
    print(f"  {len(haberler)} yeni haber (duplicate'ler çıkarıldı)\n")

    haberler = [h for h in haberler if on_filtre(h)]
    print(f"  {len(haberler)} haber keyword filtresini geçti\n")

    if not haberler:
        print("Yeni alakali haber yok.")
        return

    print("Gemini ile filtreleniyor...")
    gecenler = []
    for i, h in enumerate(haberler):
        if gemini_key:
            time.sleep(random.uniform(0.5, 1.5))
        sonuc = gemini_filtrele(h, gemini_key)
        if sonuc and sonuc.get("alakali"):
            h["ozet"] = sonuc.get("ozet", h["ozet"])
            h["ulke"] = sonuc.get("ulke", "genel")
            h["kategori"] = sonuc.get("kategori", "genel")
            h["ai_skor"] = sonuc.get("skor", 5)
            gecenler.append(h)
            print(f"  ✓ [skor:{h['ai_skor']}] [{h['kaynak']}] {h['baslik'][:70]}")
        else:
            print(f"  ✗ [{h['kaynak']}] {h['baslik'][:70]}")

    print(f"\n  {len(gecenler)}/{len(haberler)} haber filtreyi geçti\n")

    if gecenler:
        print("Supabase'e kaydediliyor...")
        yazilan = supabase_kaydet(sb_url, sb_key, gecenler, args.dry_run, tg_token, tg_chat)
        print(f"  {yazilan} haber kaydedildi (status=draft, admin onayı bekliyor).")
    else:
        print("Kaydedilecek haber yok.")

    print("\nTamamlandi.")

if __name__ == "__main__":
    main()
