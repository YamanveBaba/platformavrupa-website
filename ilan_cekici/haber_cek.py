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

# RSS kaynakları — Avrupa Türkleri ve gurbetçi odaklı
RSS_KAYNAKLAR = [
    # Kaliteli Türk medyası (seçilmiş)
    {"url": "https://www.aa.com.tr/tr/rss/default.aspx",         "kaynak": "Anadolu Ajansı"},
    {"url": "http://rss.dw.com/rdf/rss-tur-all",                 "kaynak": "DW Türkçe"},
    {"url": "https://www.bbc.com/turkce/index.xml",              "kaynak": "BBC Türkçe"},
    # Uluslararası Türkçe
    {"url": "https://www.france24.com/tr/rss",                   "kaynak": "France24 Türkçe"},
    {"url": "https://tr.euronews.com/rss",                       "kaynak": "Euronews Türkçe"},
    {"url": "https://bianet.org/bianet/rss",                     "kaynak": "Bianet"},
    # Avrupa Türk medyası
    {"url": "https://www.avrupahaber.net/feed",                  "kaynak": "Avrupa Haber"},
    {"url": "https://www.almanyabulteni.de/feed",                "kaynak": "Almanya Bülteni"},
    # Gurbetçi odaklı site
    {"url": "https://mobesekamerasi.com/feed",                   "kaynak": "Kapıkule Canlı Haber"},
    # Resmi Türk kurumları
    {"url": "https://www.gumruk.gov.tr/rss/haberler.xml",        "kaynak": "Gümrük Bakanlığı"},
    {"url": "https://ytb.gov.tr/haberler/rss",                   "kaynak": "YTB Yurtdışı Türkler"},
    # AB haberleri (Euractiv çıkarıldı — İngilizce içerik)
    # Google News — Mevcut gurbetçi aramaları
    {"url": "https://news.google.com/rss/search?q=Avrupa+Türkler&hl=tr&gl=TR&ceid=TR:tr",                       "kaynak": "Google News TR"},
    {"url": "https://news.google.com/rss/search?q=Almanya+Türk+ikamet&hl=tr&gl=TR&ceid=TR:tr",                  "kaynak": "Google News DE"},
    {"url": "https://news.google.com/rss/search?q=Belçika+Türk+vize&hl=tr&gl=TR&ceid=TR:tr",                    "kaynak": "Google News BE"},
    {"url": "https://news.google.com/rss/search?q=vatandaşlık+başvurusu+Avrupa&hl=tr&gl=TR&ceid=TR:tr",         "kaynak": "Google News Vatandaşlık"},
    {"url": "https://news.google.com/rss/search?q=oturma+izni+Avrupa+Türkiye&hl=tr&gl=TR&ceid=TR:tr",           "kaynak": "Google News Oturma"},
    {"url": "https://news.google.com/rss/search?q=Avrupa+emekli+Türkiye+SGK&hl=tr&gl=TR&ceid=TR:tr",            "kaynak": "Google News Emekli"},
    # Google News — YENİ: Sıla yolu ve gümrük aramaları
    {"url": "https://news.google.com/rss/search?q=kapıkule+gümrük+2026&hl=tr&gl=TR&ceid=TR:tr",                 "kaynak": "Google News Kapıkule"},
    {"url": "https://news.google.com/rss/search?q=sıla+yolu+gurbetçi&hl=tr&gl=TR&ceid=TR:tr",                   "kaynak": "Google News Sıla"},
    {"url": "https://news.google.com/rss/search?q=yabancı+plakalı+araç+türkiye+gümrük&hl=tr&gl=TR&ceid=TR:tr",  "kaynak": "Google News Araç Gümrük"},
    {"url": "https://news.google.com/rss/search?q=Bulgaristan+vignette+e-vinyet+2026&hl=tr&gl=TR&ceid=TR:tr",   "kaynak": "Google News Vignette"},
    {"url": "https://news.google.com/rss/search?q=gurbetçi+gümrük+araç+ceza&hl=tr&gl=TR&ceid=TR:tr",            "kaynak": "Google News Gümrük Ceza"},
    {"url": "https://news.google.com/rss/search?q=çifte+vatandaşlık+2026&hl=tr&gl=TR&ceid=TR:tr",               "kaynak": "Google News Çifte Vatandaşlık"},
    {"url": "https://news.google.com/rss/search?q=engelli+araç+ithalat+gümrük&hl=tr&gl=TR&ceid=TR:tr",          "kaynak": "Google News Engelli Araç"},
    {"url": "https://news.google.com/rss/search?q=Avrupa+Türk+emeklilik+sigorta&hl=tr&gl=TR&ceid=TR:tr",        "kaynak": "Google News Emeklilik"},
]

ALAKALI_KELIMELER = [
    # Ülkeler ve şehirler
    "avrupa", "almanya", "hollanda", "belçika", "fransa", "avusturya",
    "brüksel", "berlin", "paris", "amsterdam", "viyana", "sırbistan",
    "bulgaristan", "macaristan", "romanya", "polonya", "çekya",
    # Gurbetçi ve diaspora
    "gurbetçi", "diaspora", "ikamet", "oturma izni", "vize", "vatandaşlık",
    "çifte vatandaşlık", "pasaport", "schengen", "yurt dışı",
    "işçi", "göçmen", "konsolosluk", "büyükelçilik",
    # Sıla yolu ve sınır — YENİ
    "kapıkule", "sıla yolu", "sıla", "kapitan andreevo", "hamzabeyli",
    "dereköy", "ipsala", "pazarkule", "sınır kapısı", "sınır geçişi",
    "bekleme süresi",
    # Gümrük ve araç — YENİ
    "gümrük", "yabancı plakalı", "geçici ithalat", "araç gümrük",
    "öTV muafiyeti", "engelli araç", "vignette", "e-vinyet",
    "otoyol ücreti", "otoban", "trafik cezası",
    # Ekonomi ve sosyal
    "sgk", "emekli", "sigorta", "döviz", "euro", "türk lirası", "vergi",
    "ab ", "avrupa birliği", "türkiye-ab", "türkiye-avrupa",
    "eğitim", "burs", "üniversite", "konut", "kira", "tapu",
    # Pratik gurbetçi bilgileri — YENİ
    "konsolosluk randevu", "vergi kimlik", "emekli maaşı yurt dışı",
    "banka hesabı yurt dışı", "ikametgah belgesi",
]

ALAKASIZ_KELIMELER = [
    "futbol skoru", "maç sonucu", "şampiyon", "transfer",
    "magazin", "ünlü", "evlendi", "boşandı", "dizi", "film",
    "reklam", "indirim kampanyası", "satılık", "kiralık",
    "spor toto", "bahis", "casino",
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

                # Görsel URL — enclosure veya media thumbnail
                gorsel = None
                if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    gorsel = entry.media_thumbnail[0].get("url")
                elif hasattr(entry, "media_content") and entry.media_content:
                    gorsel = entry.media_content[0].get("url")
                elif hasattr(entry, "enclosures") and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("image/"):
                            gorsel = enc.get("href") or enc.get("url")
                            break
                if not gorsel:
                    import re as _re
                    m = _re.search(r'<img[^>]+src=["\']([^"\']+)["\']', ozet)
                    if m:
                        gorsel = m.group(1)

                haberler.append({
                    "baslik": baslik,
                    "link": link,
                    "ozet": ozet[:500],
                    "kaynak": kaynak["kaynak"],
                    "hash": url_hash(link),
                    "tarih": tarih.isoformat() if tarih else datetime.now(timezone.utc).isoformat(),
                    "gorsel": gorsel,
                })
        except Exception as e:
            print(f"  RSS hata ({kaynak['kaynak']}): {str(e)[:60]}")

    return haberler

_TR_INGILIZCE = [" the ", " of ", " and ", " for ", " in ", " to ", " is ", " are ", " on ", " at ",
                  " with ", " from ", " this ", " that ", " have ", " has ", " will "]

def ingilizce_mi(text: str) -> bool:
    """Başlık büyük ölçüde İngilizce ise True döner."""
    t = " " + text.lower() + " "
    return sum(1 for k in _TR_INGILIZCE if k in t) >= 3

def on_filtre(haber: dict) -> bool:
    baslik = haber["baslik"]
    # İngilizce haberler kabul edilmez
    if ingilizce_mi(baslik):
        return False
    metin = (baslik + " " + haber["ozet"]).lower()
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

    prompt = f"""Avrupa'daki Türk gurbetçiler için haber editörüsün. Haberi puanla ve kategorize et.

BAŞLIK: {haber['baslik']}
ÖZET: {haber['ozet'][:400]}
KAYNAK: {haber['kaynak']}

SADECE JSON döndür:
{{"ozet": "2 cümle Türkçe özet", "ulke": "almanya/hollanda/belcika/fransa/avusturya/ingiltere/italya/ispanya/genel", "kategori": "sila_yolu|gumruk_arac|vignette|sinir_mevzuat|vize_ikamet|vatandaslik|egitim_burs|is_ekonomi|kultur_toplum|turkiye|avrupa_politika|diger", "skor": 1-10}}

Skor rehberi (geniş tut — şüphe durumunda 5 ver):
8-10: KRİTİK — sıla yolu/Kapıkule bilgisi, gümrük değişikliği, vignette/e-vinyet fiyatı, araç mevzuatı,
      yabancı plakalı araç cezası, sınır bekleme süresi, vize/ikamet değişikliği, vatandaşlık,
      engelli araç ithalat, AB-Türkiye ilişkileri
5-7: ÖNEMLİ — Avrupa Türkleri haberleri, SGK/emeklilik, eğitim, ekonomi, kültür, konsolosluk
3-4: Az alakalı ama yayınlanabilir
1-2: Spor skoru, magazin, reklam, genel haber (gurbetçiyle ilgisiz)"""

    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
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
    """Düz metin Telegram mesajı gönder (özet bildirimler için)."""
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


def telegram_haber_gonder(token: str, chat_id: str, haber_id: int,
                           baslik: str, ozet: str, kaynak: str,
                           skor: int, kategori: str, url: str,
                           gorsel_url: str = ""):
    """Haberi onay/red butonlarıyla Telegram'a gönder."""
    if not token or not chat_id:
        return

    kategori_emoji = {
        "sila_yolu": "🚗", "gumruk_arac": "🛃", "vignette": "🛣️",
        "sinir_mevzuat": "🛂", "vize_ikamet": "📋", "vatandaslik": "🇹🇷",
        "egitim_burs": "🎓", "is_ekonomi": "💼", "kultur_toplum": "🏛️",
        "avrupa_politika": "🇪🇺", "turkiye": "🇹🇷", "diger": "📰",
    }.get(kategori, "📰")

    skor_bar = "⭐" * min(skor, 5)
    mesaj = (
        f"{kategori_emoji} <b>{baslik[:120]}</b>\n\n"
        f"{ozet[:300]}\n\n"
        f"📡 {kaynak}  |  {skor_bar} ({skor}/10)\n"
        f'<a href="{url}">Orijinal habere git →</a>'
    )

    klavye = {
        "inline_keyboard": [[
            {"text": "✅ Yayınla", "callback_data": f"onayla_{haber_id}"},
            {"text": "🗑️ Sil",    "callback_data": f"reddet_{haber_id}"},
            {"text": "✏️ Düzenle", "url": f"https://www.platformavrupa.com/admin.html#haber_{haber_id}"},
        ]]
    }

    try:
        # Resim varsa fotoğraflı mesaj gönder
        if gorsel_url:
            caption = mesaj[:1024]  # Telegram caption max 1024 karakter
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                json={
                    "chat_id": chat_id,
                    "photo": gorsel_url,
                    "caption": caption,
                    "parse_mode": "HTML",
                    "reply_markup": klavye,
                },
                timeout=10,
            )
            # Resim yüklenemezse düz mesaja düş
            if r.status_code != 200:
                raise Exception(f"sendPhoto {r.status_code}")
        else:
            raise Exception("resim yok")
    except Exception:
        # Resim yoksa veya hata varsa düz metin gönder
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": mesaj,
                    "parse_mode": "HTML",
                    "reply_markup": klavye,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
        except Exception as e:
            print(f"  Telegram haber gönderme hata: {e}")

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
    status = "draft"
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
            "status": status,
            "kategori": h.get("kategori", "genel"),
            "ai_skor": ai_skor,
            "image_url": h.get("gorsel"),
        }
        r = requests.post(
            f"{sb_url}/rest/v1/announcements",
            json=[row], headers=headers, timeout=15
        )
        if r.status_code in (200, 201, 204):
            basarili += 1
            # Kaydedilen haberin ID'sini al
            haber_id = None
            try:
                # ID'yi source_hash ile sorgula
                id_r = requests.get(
                    f"{sb_url}/rest/v1/announcements",
                    params={"select": "id", "source_hash": f"eq.{h['hash']}", "limit": "1"},
                    headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
                    timeout=10,
                )
                if id_r.status_code == 200 and id_r.json():
                    haber_id = id_r.json()[0]["id"]
            except Exception:
                pass

            # Tüm haberler (skor >= 5) Telegram'a inline butonlarla gider
            if isinstance(ai_skor, int) and ai_skor >= 5 and tg_token and tg_chat and haber_id:
                telegram_haber_gonder(
                    tg_token, tg_chat, haber_id,
                    h["baslik"], h["ozet"], h["kaynak"],
                    ai_skor, h.get("kategori", "diger"), h["link"],
                    gorsel_url=h.get("gorsel", "")
                )
                time.sleep(0.3)  # Telegram rate limit
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
        if sonuc:
            h["ozet"] = sonuc.get("ozet", h["ozet"])
            h["ulke"] = sonuc.get("ulke", "genel")
            h["kategori"] = sonuc.get("kategori", "genel")
            h["ai_skor"] = sonuc.get("skor", 5)
            if h["ai_skor"] >= 3:
                gecenler.append(h)
                print(f"  OK [skor:{h['ai_skor']}] [{h['kaynak']}] {h['baslik'][:70]}")
            else:
                print(f"  -- [skor:{h['ai_skor']}] [{h['kaynak']}] {h['baslik'][:70]}")
        else:
            h["ai_skor"] = 5
            gecenler.append(h)
            print(f"  OK [skor:5/fallback] [{h['kaynak']}] {h['baslik'][:70]}")

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
