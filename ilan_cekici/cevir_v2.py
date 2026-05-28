# -*- coding: utf-8 -*-
"""
Platform Avrupa — Akıllı Çeviri Sistemi v2
Cache-first yaklaşım: aynı başlık bir kez çevrilir, sonraki ilanlar cache'den alır.

API: DeepL Free (500K karakter/ay, kayıt: deepl.com/pro-api)
     Yoksa Gemini Flash fallback (mevcut cevir.py mantığı)

Kullanım:
  python cevir_v2.py                    # Tüm çevrilmemiş başlıklar
  python cevir_v2.py --limit 1000       # Test: 1000 ilan
  python cevir_v2.py --dry-run          # DB'ye yazma, sadece say
  python cevir_v2.py --stats            # Cache istatistiklerini göster
  python cevir_v2.py --setup-cache      # title_cache tablosunu oluştur (Supabase SQL)

Kurulum:
  pip install requests
  DeepL API key: https://www.deepl.com/pro-api → Free tier → DEEPL_API_KEY env değişkeni
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("HATA: pip install requests"); sys.exit(1)

try:
    from deep_translator import GoogleTranslator
    GOOGLE_TRANSLATE_OK = True
except ImportError:
    GOOGLE_TRANSLATE_OK = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# NLLB-200 (Meta AI) — HuggingFace Inference API
NLLB_URL        = "https://api-inference.huggingface.co/models/facebook/nllb-200-distilled-600M"
NLLB_BATCH      = 1     # Tek seferde 1 metin (API kısıtı)
DELAY_NLLB      = 0.5   # İstekler arası bekleme

# VDAB=Flemenkçe, Actiris/FOREM=Fransızca — NLLB dil kodları
NLLB_LANG = {
    "vdab":    "nld_Latn",   # Flemenkçe
    "actiris": "fra_Latn",   # Fransızca
    "forem":   "fra_Latn",   # Fransızca
}
NLLB_DEFAULT_LANG = "nld_Latn"

DEEPL_URL   = "https://api-free.deepl.com/v2/translate"
DEEPL_BATCH = 50
DELAY_DEEPL = 0.5

MYMEMORY_URL   = "https://api.mymemory.translated.net/get"
DELAY_MYMEMORY = 0.12

GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GEMINI_BATCH = 100   # 40 → 100: kısa iş başlıkları için 2K token yeterli
DELAY_GEMINI = 4.5   # 15 RPM altında (13.3 req/min)

PAGE = 1000  # 500 → 1000: daha az DB round-trip

# ─── YARDIMCI ─────────────────────────────────────────────────────────────────

def normalize_key(text: str) -> str:
    """Başlığı cache anahtarına çevir: küçük harf, aksansız, boşluk normalize."""
    t = unicodedata.normalize('NFD', text.lower()).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', t).strip()[:200]

def load_secrets() -> tuple[str, str, str, str]:
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not sb_url or not sb_key:
        path = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt"))
        if os.path.isfile(path):
            lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                     if l.strip() and not l.startswith("#")]
            if len(lines) >= 2:
                sb_url, sb_key = lines[0].rstrip("/"), lines[1]
    if not sb_url or not sb_key:
        print("HATA: Supabase credentials bulunamadı."); sys.exit(1)

    deepl_key  = os.environ.get("DEEPL_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return sb_url, sb_key, deepl_key, gemini_key

# ─── SUPABASE ─────────────────────────────────────────────────────────────────

def sb_headers(key: str) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Connection": "close"}

def fetch_pending(sb_url: str, sb_key: str, limit: int) -> list[dict]:
    """title_tr IS NULL olan aktif ilanları çek — source da lazım (dil tespiti için)."""
    for deneme in range(4):
        r = requests.get(
            f"{sb_url}/rest/v1/ilanlar",
            params={"select": "id,title,source", "source": "neq.user", "title_tr": "is.null",
                    "status": "eq.active", "order": "id.desc", "limit": str(limit)},
            headers=sb_headers(sb_key), timeout=30,
        )
        if r.status_code == 500:
            bekle = 15 * (deneme + 1)
            print(f"  Supabase 500, {bekle}sn bekleniyor (deneme {deneme+1}/4)...")
            time.sleep(bekle)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()  # 4. denemede de 500 gelirse hata fırlat
    return []

def count_pending(sb_url: str, sb_key: str) -> int:
    """Bekleyen ilan sayısını çek — hata olursa 999999 döndür (çalışmaya devam et)."""
    for deneme in range(3):
        try:
            hdrs = {**sb_headers(sb_key), "Prefer": "count=estimated", "Range": "0-0"}
            r = requests.get(f"{sb_url}/rest/v1/ilanlar",
                             params={"select": "id", "source": "neq.user",
                                     "title_tr": "is.null", "status": "eq.active"},
                             headers=hdrs, timeout=20)
            if r.status_code == 200:
                m = re.search(r"/(\d+)", r.headers.get("Content-Range", ""))
                if m:
                    n = int(m.group(1))
                    if n > 0:
                        return n
        except Exception:
            pass
        time.sleep(3)
    # count çalışmıyorsa büyük değer döndür — fetch_pending 0 dönünce durur
    return 999_999

def cache_fetch(sb_url: str, sb_key: str, keys: list[str]) -> dict[str, str]:
    """Cache tablosundan verilen anahtarlar için çevirileri al — 100'lük parçalar halinde."""
    if not keys:
        return {}
    result = {}
    for i in range(0, len(keys), 100):
        chunk = keys[i:i + 100]
        try:
            in_val = "({})".format(",".join(f'"{k}"' for k in chunk))
            r = requests.get(
                f"{sb_url}/rest/v1/title_cache",
                params={"select": "original_normalized,translation_tr",
                        "original_normalized": f"in.{in_val}"},
                headers=sb_headers(sb_key), timeout=(5, 15),
            )
            if r.status_code == 200:
                for row in r.json():
                    result[row["original_normalized"]] = row["translation_tr"]
        except Exception:
            pass
    return result

def cache_save(sb_url: str, sb_key: str, rows: list[dict], dry_run: bool) -> int:
    """Cache tablosuna yeni çevirileri upsert et."""
    if dry_run or not rows:
        return len(rows)
    hdrs = {**sb_headers(sb_key), "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal"}
    r = requests.post(f"{sb_url}/rest/v1/title_cache?on_conflict=original_normalized",
                      json=rows, headers=hdrs, timeout=60)
    if r.status_code not in (200, 201, 204):
        print(f"  Cache upsert hatası {r.status_code}: {r.text[:200]}")
        return 0
    return len(rows)

def ilan_update(sb_url: str, sb_key: str, updates: list[dict], dry_run: bool) -> int:
    """İlan tablosuna title_tr güncelle."""
    if dry_run:
        return len(updates)
    hdrs = {**sb_headers(sb_key), "Content-Type": "application/json", "Prefer": "return=minimal"}
    ok = 0
    for u in updates:
        r = requests.patch(f"{sb_url}/rest/v1/ilanlar?id=eq.{u['id']}",
                           json={"title_tr": u["title_tr"]}, headers=hdrs, timeout=15)
        if r.status_code in (200, 204):
            ok += 1
    return ok

# ─── DEEPL ────────────────────────────────────────────────────────────────────

def deepl_cevir(basliklar: list[str], deepl_key: str) -> list[str]:
    """DeepL Free API ile NL/FR → TR çeviri (otomatik dil tespiti)."""
    if not deepl_key or not basliklar:
        return basliklar

    # DeepL batch: her metin ayrı 'text' parametresi
    try:
        r = requests.post(
            DEEPL_URL,
            data={
                "auth_key": deepl_key,
                "text": basliklar,         # liste → çoklu text parametresi
                "target_lang": "TR",
                "source_lang": "",         # otomatik tespit
                "formality": "default",
            },
            timeout=30,
        )
        if r.status_code == 456:
            print("  DeepL: Aylık karakter limiti doldu.")
            return basliklar
        if r.status_code != 200:
            print(f"  DeepL HTTP {r.status_code}: {r.text[:200]}")
            return basliklar
        translations = r.json().get("translations", [])
        return [t.get("text", b) for t, b in zip(translations, basliklar)]
    except Exception as e:
        print(f"  DeepL hata: {e}")
        return basliklar

# ─── NLLB-200 (Meta AI — HuggingFace, ücretsiz, en iyi kalite) ───────────────

def nllb_cevir(basliklar: list[str], kaynak_diller: list[str], hf_token: str = "") -> list[str]:
    """
    Meta NLLB-200 ile çeviri — HuggingFace Inference API.
    Token olmadan: 1,000 istek/gün
    Ücretsiz HF token ile: 50,000+ istek/gün
    """
    hdrs = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    sonuclar = []

    for metin, kaynak in zip(basliklar, kaynak_diller):
        if not metin.strip():
            sonuclar.append(metin)
            continue

        src_lang = NLLB_LANG.get(kaynak, NLLB_DEFAULT_LANG)

        for deneme in range(4):
            try:
                r = requests.post(
                    NLLB_URL,
                    headers=hdrs,
                    json={
                        "inputs": metin.strip()[:500],
                        "parameters": {
                            "src_lang": src_lang,
                            "tgt_lang": "tur_Latn",
                        }
                    },
                    timeout=60,
                )

                if r.status_code == 503:
                    # Model yükleniyor — bekleme süresi API'den gelir
                    bekleme = r.json().get("estimated_time", 30)
                    print(f"  NLLB yükleniyor, {bekleme:.0f}sn bekleniyor...")
                    time.sleep(min(bekleme + 5, 60))
                    continue

                if r.status_code == 429:
                    print("  NLLB rate limit, 60sn bekleniyor...")
                    time.sleep(60)
                    continue

                if r.status_code != 200:
                    sonuclar.append(metin)
                    break

                data = r.json()
                if isinstance(data, list) and data:
                    tr = data[0].get("translation_text", metin)
                    sonuclar.append(tr.strip() if tr else metin)
                else:
                    sonuclar.append(metin)
                break

            except Exception as e:
                if deneme < 3:
                    time.sleep(5)
                else:
                    sonuclar.append(metin)

        time.sleep(DELAY_NLLB)

    return sonuclar


# ─── GOOGLE TRANSLATE (gayri resmi, ücretsiz) ─────────────────────────────────

GOOGLE_LANG = {
    "vdab":    "nl",   # Flemenkçe
    "actiris": "fr",   # Fransızca
    "forem":   "fr",   # Fransızca
}

def google_cevir(basliklar: list[str], kaynak_diller: list[str]) -> list[str]:
    """
    deep-translator → translate.google.com üzerinden çeviri.
    Kaynak dili otomatik yerine kaynaktan belirle (nl/fr) — daha güvenilir.
    """
    if not GOOGLE_TRANSLATE_OK:
        print("  HATA: pip install deep-translator")
        return basliklar
    sonuclar = []
    for metin, kaynak in zip(basliklar, kaynak_diller):
        if not metin.strip():
            sonuclar.append(metin); continue
        src_lang = GOOGLE_LANG.get(kaynak, "nl")
        for deneme in range(3):
            try:
                tr = GoogleTranslator(source=src_lang, target="tr").translate(metin.strip()[:500])
                sonuclar.append(tr if tr else metin)
                break
            except Exception as e:
                if deneme < 2:
                    time.sleep(2 + deneme * 2)
                else:
                    sonuclar.append(metin)
        time.sleep(0.5)
    return sonuclar


# ─── MYMEMORY (ücretsiz, kayıt gerektirmez) ───────────────────────────────────

def mymemory_cevir(basliklar: list[str], email: str = "") -> list[str]:
    """
    MyMemory ücretsiz çeviri API — günde 10K istek, API key gerekmez.
    Email verirsen limit 2 katına çıkar (isteğe bağlı).
    """
    sonuclar = []
    for metin in basliklar:
        if not metin.strip():
            sonuclar.append(metin)
            continue
        try:
            params = {"q": metin[:500], "langpair": "nl|tr"}
            if email:
                params["de"] = email
            r = requests.get(MYMEMORY_URL, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                tr = data.get("responseData", {}).get("translatedText", "")
                # Fransızca fallback: eğer NL→TR başarısız olursa FR→TR dene
                if not tr or tr == metin or "MYMEMORY WARNING" in tr:
                    params2 = {"q": metin[:500], "langpair": "fr|tr"}
                    if email:
                        params2["de"] = email
                    r2 = requests.get(MYMEMORY_URL, params=params2, timeout=10)
                    if r2.status_code == 200:
                        tr = r2.json().get("responseData", {}).get("translatedText", metin)
                sonuclar.append(tr if tr and "MYMEMORY WARNING" not in tr else metin)
            else:
                sonuclar.append(metin)
        except Exception:
            sonuclar.append(metin)
        time.sleep(DELAY_MYMEMORY)
    return sonuclar


# ─── GEMINI FALLBACK ──────────────────────────────────────────────────────────

def gemini_cevir(basliklar: list[str], gemini_key: str) -> list[str]:
    """Gemini Flash fallback — DeepL yoksa kullanılır."""
    if not gemini_key or not basliklar:
        return basliklar
    n = len(basliklar)
    numlu = "\n".join(f"{i+1}. {t[:300]}" for i, t in enumerate(basliklar))
    prompt = (f"Bu {n} adet Flemenkçe veya Fransızca iş ilanı başlığını Türkçeye çevir.\n"
              f"SADECE numaralı liste döndür, başka hiçbir şey yazma.\n\n{numlu}")
    for deneme in range(3):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={gemini_key}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"maxOutputTokens": min(150 * n, 8000), "temperature": 0.1}},
                timeout=40,
            )
            if r.status_code == 429:
                time.sleep(60 + deneme * 30); continue
            if r.status_code != 200:
                return basliklar
            metin = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            satirlar = re.findall(r"^\d+\.\s*(.+)$", metin, re.MULTILINE)
            if len(satirlar) == n:
                return [s.strip() for s in satirlar]
            sonuc = basliklar[:]
            for i, s in enumerate(satirlar[:n]):
                sonuc[i] = s.strip()
            return sonuc
        except Exception as e:
            print(f"  Gemini hata: {e}")
            if deneme < 2: time.sleep(5)
    return basliklar

# ─── ANA DÖNGÜ ────────────────────────────────────────────────────────────────

def ceviri_yap(sb_url: str, sb_key: str, deepl_key: str, gemini_key: str,
               max_ilan: int, dry_run: bool, mymemory_email: str = "",
               hf_token: str = "") -> None:
    if deepl_key:
        api = "DeepL"
    elif gemini_key:
        api = "Gemini Flash"
    elif GOOGLE_TRANSLATE_OK:
        api = "Google Translate (ücretsiz, cache ile güvenli)"
    elif hf_token:
        api = "NLLB-200 (Meta AI, HF token ile — 50K/gün)"
    else:
        api = "NLLB-200 (Meta AI, token yok — 1K/gün)"
    print(f"\nÇeviri başlıyor | API: {api} | Max: {max_ilan:,} | dry-run: {dry_run}")

    bekleyen = count_pending(sb_url, sb_key)
    hedef = min(bekleyen, max_ilan)
    print(f"Çevrilecek ilan: {hedef:,} / {bekleyen:,} toplam\n")
    if hedef == 0:
        print("Çevrilecek ilan yok."); return

    toplam_ceviri = 0
    toplam_cache_hit = 0
    toplam_yeni = 0
    start = time.time()

    while toplam_ceviri < hedef:
        batch_size = min(PAGE, hedef - toplam_ceviri) if hedef < 999_999 else PAGE
        print(f"  [adim 1/4] ilanlar cekiliyor...", flush=True)
        try:
            rows = fetch_pending(sb_url, sb_key, batch_size)
        except Exception as e:
            print(f"  fetch_pending hata: {e} — 60sn bekleniyor...")
            time.sleep(60)
            continue
        if not rows:
            break

        # 1. Cache lookup
        print(f"  [adim 2/4] cache sorgulanıyor ({len(rows)} baslik)...", flush=True)
        basliklar = [r["title"] or "" for r in rows]
        anahtarlar = [normalize_key(b) for b in basliklar]
        cache_map = cache_fetch(sb_url, sb_key, anahtarlar)
        print(f"  [adim 3/4] ceviri basliyor...", flush=True)

        cache_hit_ids = []
        cevrilecek_idx = []

        for i, (row, anahtar) in enumerate(zip(rows, anahtarlar)):
            if anahtar in cache_map:
                cache_hit_ids.append({"id": row["id"], "title_tr": cache_map[anahtar]})
                toplam_cache_hit += 1
            else:
                cevrilecek_idx.append(i)

        # 2. Cache hit'leri direkt yaz
        if cache_hit_ids:
            ilan_update(sb_url, sb_key, cache_hit_ids, dry_run)

        # 3. Cache miss'leri API ile çevir (batch halinde)
        batch_boyutu = DEEPL_BATCH if deepl_key else GEMINI_BATCH
        delay = DELAY_DEEPL if deepl_key else DELAY_GEMINI

        for i in range(0, len(cevrilecek_idx), batch_boyutu):
            idx_batch = cevrilecek_idx[i:i + batch_boyutu]
            orijinaller = [basliklar[j] for j in idx_batch]
            anahtarlar_batch = [anahtarlar[j] for j in idx_batch]

            kaynak_diller = [rows[j].get("source", "vdab") for j in idx_batch]

            if deepl_key:
                ceviriler = deepl_cevir(orijinaller, deepl_key)
            elif gemini_key:
                ceviriler = gemini_cevir(orijinaller, gemini_key)
            elif GOOGLE_TRANSLATE_OK:
                ceviriler = google_cevir(orijinaller, kaynak_diller)
            else:
                ceviriler = nllb_cevir(orijinaller, kaynak_diller, hf_token)

            # SADECE başarılı çevirileri güncelle (orijinalden farklıysa)
            ilan_updates = [
                {"id": rows[j]["id"], "title_tr": c}
                for j, c, o in zip(idx_batch, ceviriler, orijinaller)
                if c and c.strip() and c.strip().lower() != o.strip().lower()
            ]
            if ilan_updates:
                ilan_update(sb_url, sb_key, ilan_updates, dry_run)

            # Cache'e kaydet — batch içi tekrarları temizle
            cache_dict = {}
            for k, c, o in zip(anahtarlar_batch, ceviriler, orijinaller):
                if c and c.strip() and c.strip().lower() != o.strip().lower():
                    cache_dict[k] = c  # aynı anahtar tekrarlanırsa son çeviri kazanır
            cache_rows = [
                {"original_normalized": k, "translation_tr": v,
                 "created_at": datetime.now(timezone.utc).isoformat()}
                for k, v in cache_dict.items()
            ]
            cache_save(sb_url, sb_key, cache_rows, dry_run)
            toplam_yeni += len(cache_rows)

            time.sleep(delay)

        toplam_ceviri += len(rows)
        gecen = time.time() - start
        rate = toplam_ceviri / gecen if gecen > 0 else 1
        kalan_dk = (hedef - toplam_ceviri) / rate / 60
        hit_pct = toplam_cache_hit / toplam_ceviri * 100 if toplam_ceviri else 0
        print(f"  [{toplam_ceviri:,}/{hedef:,}] "
              f"cache hit: %{hit_pct:.0f} | yeni çeviri: {toplam_yeni} | ~{kalan_dk:.0f} dk kaldı")

    gecen = time.time() - start
    print(f"\nTamamlandı: {toplam_ceviri:,} ilan | "
          f"cache hit: {toplam_cache_hit:,} (%{toplam_cache_hit/max(toplam_ceviri,1)*100:.0f}) | "
          f"yeni API çevirisi: {toplam_yeni:,} | süre: {gecen/60:.1f} dk")

def goster_stats(sb_url: str, sb_key: str) -> None:
    """Cache ve ilan çeviri istatistiklerini göster."""
    hdrs = {**sb_headers(sb_key), "Prefer": "count=exact", "Range": "0-0"}

    r1 = requests.get(f"{sb_url}/rest/v1/title_cache", params={"select": "original_normalized"},
                      headers=hdrs, timeout=15)
    m1 = re.search(r"/(\d+)", r1.headers.get("Content-Range", ""))
    cache_adet = int(m1.group(1)) if m1 else 0

    r2 = requests.get(f"{sb_url}/rest/v1/ilanlar",
                      params={"select": "id", "source": "neq.user", "title_tr": "not.is.null", "status": "eq.active"},
                      headers=hdrs, timeout=15)
    m2 = re.search(r"/(\d+)", r2.headers.get("Content-Range", ""))
    cevrilmis = int(m2.group(1)) if m2 else 0

    r3 = requests.get(f"{sb_url}/rest/v1/ilanlar",
                      params={"select": "id", "source": "neq.user", "title_tr": "is.null", "status": "eq.active"},
                      headers=hdrs, timeout=15)
    m3 = re.search(r"/(\d+)", r3.headers.get("Content-Range", ""))
    bekleyen = int(m3.group(1)) if m3 else 0

    print(f"\n{'─'*40}")
    print(f"  Cache tablosu     : {cache_adet:>8,} benzersiz başlık")
    print(f"  Çevrilmiş ilanlar : {cevrilmis:>8,}")
    print(f"  Bekleyen ilanlar  : {bekleyen:>8,}")
    print(f"  Toplam            : {cevrilmis+bekleyen:>8,}")
    print(f"{'─'*40}\n")

# ─── SETUP SQL ────────────────────────────────────────────────────────────────

SETUP_SQL = """
-- Supabase SQL Editor'de çalıştır:

CREATE TABLE IF NOT EXISTS title_cache (
    original_normalized TEXT PRIMARY KEY,
    translation_tr      TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_title_cache_key ON title_cache (original_normalized);

-- ilanlar tablosuna postal_code kolonu (henüz yoksa):
ALTER TABLE ilanlar ADD COLUMN IF NOT EXISTS postal_code TEXT DEFAULT '';

-- RLS (title_cache okuma herkese açık, yazma sadece service role):
ALTER TABLE title_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Herkes okuyabilir" ON title_cache FOR SELECT USING (true);
"""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Platform Avrupa — Akıllı Çeviri v2")
    ap.add_argument("--limit",       type=int, default=999_999)
    ap.add_argument("--dry-run",     action="store_true")
    ap.add_argument("--stats",       action="store_true", help="İstatistikleri göster")
    ap.add_argument("--setup-cache", action="store_true", help="Gerekli SQL'i yazdır")
    ap.add_argument("--email",       default="", help="MyMemory için e-posta (günlük limiti artırır)")
    ap.add_argument("--hf-token",    default="", help="HuggingFace token (NLLB limiti 1K→50K/gün)")
    args = ap.parse_args()

    if args.setup_cache:
        print(SETUP_SQL)
        return

    sb_url, sb_key, deepl_key, gemini_key = load_secrets()
    print(f"Supabase: {sb_url}")

    hf_token = args.hf_token or os.environ.get("HF_TOKEN", "")

    if not deepl_key and not gemini_key:
        print("ℹ  NLLB-200 (Meta AI) kullanılacak — ücretsiz, Google Translate kalitesinde")
        if not hf_token:
            print("   Limiti 1K→50K/gün artırmak için ücretsiz HF token al:")
            print("   https://huggingface.co/settings/tokens → python cevir_v2.py --hf-token TOKEN")

    if args.stats:
        goster_stats(sb_url, sb_key)
        return

    ceviri_yap(sb_url, sb_key, deepl_key, gemini_key, args.limit, args.dry_run, args.email, hf_token)

if __name__ == "__main__":
    main()
