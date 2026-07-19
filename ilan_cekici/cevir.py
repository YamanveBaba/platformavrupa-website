# -*- coding: utf-8 -*-
"""
Platform Avrupa — Otomatik Çeviri (Flemenkçe/Fransızca → Türkçe)
Gemini Flash ile 40 başlık/15 açıklama tek istekte çevrilir.

Kullanım:
  python cevir.py                  # ilanlar: title + description
  python cevir.py --mode title     # sadece başlıklar
  python cevir.py --mode desc      # sadece açıklamalar
  python cevir.py --limit 5000     # maksimum 5000 ilan
  python cevir.py --tablo market   # market_chain_products tablosu
"""
import os, sys, time, re, argparse, requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
TITLE_BATCH = 40   # kısa metinler — 40 başlık/istek
DESC_BATCH  = 15   # uzun metinler — 15 açıklama/istek
SLEEP_SEC   = 4.2  # 15 RPM sınırının altında (14.3 req/dk)
PAGE        = 500  # Supabase'den bir seferde kaç satır çekilir


def load_secrets():
    sb_url  = os.environ.get("SUPABASE_URL", "").strip()
    sb_key  = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    gm_key  = os.environ.get("GEMINI_API_KEY", "").strip()

    if not sb_url or not sb_key:
        path = os.path.normpath(
            os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
        )
        if os.path.isfile(path):
            lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                     if l.strip() and not l.startswith("#")]
            if len(lines) >= 2:
                sb_url, sb_key = lines[0].rstrip("/"), lines[1]

    if not sb_url or not sb_key:
        print("HATA: Supabase credentials bulunamadı"); sys.exit(1)
    if not gm_key:
        print("HATA: GEMINI_API_KEY bulunamadı"); sys.exit(1)

    return sb_url.rstrip("/"), sb_key, gm_key


def sb_get(sb_url, sb_key, tablo, filtre, select, limit=PAGE):
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    url = f"{sb_url}/rest/v1/{tablo}?select={select}&{filtre}&limit={limit}&order=id.asc"
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"  DB okuma hata {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"  DB bağlantı hata: {e}")
    return []


def sb_patch(sb_url, sb_key, tablo, row_id, guncelle: dict) -> bool:
    headers = {
        "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json", "Prefer": "return=minimal",
    }
    try:
        r = requests.patch(
            f"{sb_url}/rest/v1/{tablo}?id=eq.{row_id}",
            headers=headers, json=guncelle, timeout=15
        )
        return r.status_code in (200, 204)
    except Exception:
        return False


def gemini_cevir(metinler: list, gm_key: str, alan: str = "başlık") -> list:
    """Metinler listesini Gemini ile Türkçeye çevirir. Numaralı liste döndürür."""
    n = len(metinler)
    if n == 0:
        return []

    numlu   = "\n".join(f"{i+1}. {m[:400]}" for i, m in enumerate(metinler))
    max_tok = min(100 * n, 2000)

    if alan == "ürün adı":
        prompt = (
            f"Bu {n} adet Hollandaca veya Fransızca market ürünü adını Türkçeye çevir.\n"
            "Kurallar:\n"
            "1. Marka adlarını değiştirme (Lidl, Carrefour, Delhaize, Colruyt, Aldi vb.)\n"
            "2. Miktar ve boyutu koru: '6 stuks'→'6 adet', '1L'→'1L', '500g'→'500g'\n"
            "3. Ürün adı önce, miktar sonda: 'Eieren 6 stuks'→'Yumurta 6 adet'\n"
            "4. Kısa ve doğal Türkçe kullan, kelimesi kelimesine çevirme\n"
            "Örnekler:\n"
            "  'Halfvolle melk 1L' → 'Yarım yağlı süt 1L'\n"
            "  'Verse eieren 6 stuks' → 'Taze yumurta 6 adet'\n"
            "  'Biologische kipfilet 500g' → 'Organik tavuk göğsü 500g'\n"
            "  'Witte rijst langkorrel 1kg' → 'Uzun taneli beyaz pirinç 1kg'\n"
            f"SADECE numaralı liste döndür, başka hiçbir şey yazma.\n\n{numlu}"
        )
    else:
        prompt = (
            f"Bu {n} adet Flemenkçe veya Fransızca iş ilanı {alan}ını Türkçeye çevir.\n"
            f"SADECE numaralı liste döndür, başka hiçbir şey yazma.\n\n{numlu}"
        )

    for deneme in range(3):
        try:
            r = requests.post(
                f"{GEMINI_URL}?key={gm_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tok, "temperature": 0.1},
                },
                timeout=40,
            )
            if r.status_code == 429:
                bekle = 60 + deneme * 30
                print(f"  Rate limit — {bekle}s bekleniyor...")
                time.sleep(bekle)
                continue
            if r.status_code != 200:
                print(f"  Gemini HTTP {r.status_code}")
                return metinler

            metin   = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            satirlar = re.findall(r"^\d+\.\s*(.+)$", metin, re.MULTILINE)

            if len(satirlar) == n:
                return [s.strip() for s in satirlar]

            # Kısmi parse — eksikleri orijinalle tamamla
            sonuc = metinler[:]
            for i, s in enumerate(satirlar[:n]):
                sonuc[i] = s.strip()
            return sonuc

        except Exception as e:
            print(f"  Gemini istisna: {str(e)[:80]}")
            if deneme < 2:
                time.sleep(5)

    return metinler  # tüm denemeler başarısız → orijinali döndür


# ── İlanlar: Başlık (TEKİL MOD — benzersiz başlık = 1 API çağrısı) ──────────

def cevir_ilanlar_title(sb_url, sb_key, gm_key, limit):
    """
    Benzersiz başlıkları bir kez çevirip tüm eşleşen satırlara toplu yazar.
    Örnek: 'Verpleegkundige' 4000 ilanda geçse, 1 Gemini isteğiyle 4000 satır güncellenir.
    """
    import urllib.parse

    headers_ro = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    headers_rw = {**headers_ro, "Content-Type": "application/json", "Prefer": "return=minimal"}

    # 1. Tüm benzersiz çevrilmemiş başlıkları topla (sadece title sütunu, sayfalanmış)
    print("\n[BAŞLIK ÇEVİRİSİ — TEKİL MOD]")
    print("  Benzersiz başlıklar toplanıyor...")
    baslik_sayac: dict[str, int] = {}
    offset = 0
    FETCH = 2000
    while True:
        url = (f"{sb_url}/rest/v1/ilanlar?select=title&title_tr=is.null"
               f"&status=eq.active&order=created_at.desc&limit={FETCH}&offset={offset}")
        try:
            r = requests.get(url, headers=headers_ro, timeout=30)
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            rows = []
        for row in rows:
            t = (row.get("title") or "").strip()
            if t:
                baslik_sayac[t] = baslik_sayac.get(t, 0) + 1
        if len(rows) < FETCH:
            break
        offset += FETCH

    # En sık görülenden en aza doğru sırala
    sirali = sorted(baslik_sayac, key=lambda k: baslik_sayac[k], reverse=True)
    toplam_satir = sum(baslik_sayac.values())
    print(f"  {toplam_satir:,} satır → {len(sirali):,} benzersiz başlık bulundu")

    if not sirali:
        print("  Çevrilecek başlık kalmadı.")
        return 0

    # 2. Benzersiz başlıkları çevir (limit = en fazla kaç benzersiz başlık)
    hedef = sirali[:limit]
    cevrildi = 0
    guncellenen_satir = 0

    for i in range(0, len(hedef), TITLE_BATCH):
        batch     = hedef[i : i + TITLE_BATCH]
        ceviriler = gemini_cevir(batch, gm_key, "başlık")
        time.sleep(SLEEP_SEC)

        for orijinal, ceviri in zip(batch, ceviriler):
            if not ceviri or ceviri.strip() == orijinal.strip():
                continue
            # Bu başlığa sahip TÜM satırları tek PATCH ile güncelle
            enc = urllib.parse.quote(orijinal, safe="")
            try:
                resp = requests.patch(
                    f"{sb_url}/rest/v1/ilanlar?title=eq.{enc}",
                    headers=headers_rw,
                    json={"title_tr": ceviri.strip()},
                    timeout=20,
                )
                if resp.status_code in (200, 204):
                    sayi = baslik_sayac.get(orijinal, 1)
                    guncellenen_satir += sayi
                    cevrildi += 1
            except Exception as e:
                print(f"  PATCH hatası: {str(e)[:60]}")

        print(f"  [{i + len(batch):,}/{len(hedef):,} benzersiz] ~{guncellenen_satir:,} satır güncellendi")

    print(f"  ✓ {cevrildi:,} benzersiz başlık → ~{guncellenen_satir:,} satır güncellendi")
    return guncellenen_satir


# ── İlanlar: Açıklama ────────────────────────────────────────────────────────

def cevir_ilanlar_desc(sb_url, sb_key, gm_key, limit):
    print(f"\n[AÇIKLAMA ÇEVİRİSİ] — Hedef: {limit:,} ilan")
    toplam = 0

    while toplam < limit:
        kalan  = min(PAGE, limit - toplam)
        satırlar = sb_get(
            sb_url, sb_key, "ilanlar",
            "description_tr=is.null&description=not.is.null",
            "id,description", limit=kalan,
        )
        if not satırlar:
            print("  Çevrilecek açıklama kalmadı.")
            break

        for i in range(0, len(satırlar), DESC_BATCH):
            batch       = satırlar[i : i + DESC_BATCH]
            ids         = [r["id"] for r in batch]
            aciklamalar = [(r.get("description") or "")[:600] for r in batch]

            ceviriler = gemini_cevir(aciklamalar, gm_key, "açıklama")
            time.sleep(SLEEP_SEC)

            for row_id, ceviri, orig in zip(ids, ceviriler, aciklamalar):
                if not ceviri or ceviri.strip() == orig.strip():
                    continue
                if sb_patch(sb_url, sb_key, "ilanlar", row_id, {"description_tr": ceviri}):
                    toplam += 1

            print(f"  +{len(batch)} açıklama → toplam {toplam:,}")

            if toplam >= limit:
                break

    print(f"  ✓ Toplam {toplam:,} açıklama çevrildi.")
    return toplam


# ── Market Ürünleri ──────────────────────────────────────────────────────────

def cevir_market(sb_url, sb_key, gm_key, limit):
    print(f"\n[MARKET ÜRÜNLERİ] — Hedef: {limit:,} ürün")
    toplam = 0

    while toplam < limit:
        kalan  = min(PAGE, limit - toplam)
        satırlar = sb_get(
            sb_url, sb_key, "market_chain_products",
            "name_tr=is.null",
            "id,name", limit=kalan,
        )
        if not satırlar:
            print("  Çevrilecek ürün kalmadı.")
            break

        for i in range(0, len(satırlar), TITLE_BATCH):
            batch  = satırlar[i : i + TITLE_BATCH]
            ids    = [r["id"] for r in batch]
            isimler = [r.get("name") or "" for r in batch]

            ceviriler = gemini_cevir(isimler, gm_key, "ürün adı")
            time.sleep(SLEEP_SEC)

            for row_id, ceviri, orig in zip(ids, ceviriler, isimler):
                if not ceviri or ceviri.strip() == orig.strip():
                    continue
                if sb_patch(sb_url, sb_key, "market_chain_products", row_id, {"name_tr": ceviri}):
                    toplam += 1

            print(f"  +{len(batch)} ürün → toplam {toplam:,}")

            if toplam >= limit:
                break

    print(f"  ✓ Toplam {toplam:,} ürün çevrildi.")
    return toplam


# ── Ana ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode",  choices=["title", "desc", "both"], default="both")
    ap.add_argument("--tablo", choices=["ilanlar", "market"],     default="ilanlar")
    ap.add_argument("--limit", type=int, default=999_999)
    args = ap.parse_args()

    sb_url, sb_key, gm_key = load_secrets()
    print(f"Çeviri başlıyor | tablo={args.tablo} | mode={args.mode} | limit={args.limit:,}")

    if args.tablo == "market":
        cevir_market(sb_url, sb_key, gm_key, args.limit)
    else:
        if args.mode in ("title", "both"):
            cevir_ilanlar_title(sb_url, sb_key, gm_key, args.limit)
        if args.mode in ("desc", "both"):
            cevir_ilanlar_desc(sb_url, sb_key, gm_key, args.limit)


if __name__ == "__main__":
    main()
