# -*- coding: utf-8 -*-
"""
haftalik_tam.py — Akıllı haftalık fiyat güncelleme orchestrator.

Özellikler:
  ✓ Her market için beklenen minimum ürün eşiği
  ✓ Başarısız marketi 1 kez otomatik retry
  ✓ Delhaize/Carrefour için process timeout (takılma koruması)
  ✓ Lidl cookie süresi kontrolü — süreli ise uyarı
  ✓ Sonunda özet rapor (hangi market kaç ürün, ne kadar sürdü)
  ✓ Tüm loglar haftalik_log_YYYY-MM-DD.txt dosyasına

Kullanım:
  python haftalik_tam.py            # tüm marketler
  python haftalik_tam.py --market lidl carrefour
  python haftalik_tam.py --dry-run  # sadece kontrol, çekim yok
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
LOG_DIR    = SCRIPT_DIR / "loglar"
LOG_DIR.mkdir(exist_ok=True)

# ─── Minimum beklenen ürün eşikleri (bu sayının altındaysa başarısız sayılır) ──
ESIKLER = {
    "delhaize":  10_000,
    "colruyt":    8_000,
    "carrefour":  8_000,
    "lidl":       5_000,
    "aldi":         800,
}

# ─── Process timeout (saniye) — bu süreyi aşarsa zorla durdurulur ──────────────
TIMEOUT = {
    "delhaize":  14400,  # 4 saat (34 kategori × ~7 dk)
    "colruyt":    1800,  # 30 dk
    "carrefour":  9000,  # 2.5 saat
    "lidl":       3600,  # 1 saat
    "aldi":       3600,  # 1 saat
}

# ─── Renk kodları ──────────────────────────────────────────────────────────────
YESIL  = "\033[92m"
KIRMIZI = "\033[91m"
SARI   = "\033[93m"
RESET  = "\033[0m"

renkli_destegi = sys.platform != "win32" or os.environ.get("WT_SESSION")

def R(s: str, renk: str) -> str:
    return f"{renk}{s}{RESET}" if renkli_destegi else s


# ─── Lidl cookie kontrol ───────────────────────────────────────────────────────
def lidl_cookie_kontrol() -> tuple[bool, str]:
    """Cookie geçerli mi? (True, '') veya (False, uyarı mesajı)."""
    cookie_dosya = SCRIPT_DIR / "lidl_cookie.txt"
    if not cookie_dosya.exists():
        return False, "lidl_cookie.txt bulunamadı"
    with open(cookie_dosya, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#") and "=" in s and len(s) > 20:
                # OptanonConsent içinden tarihi çek
                if "datestamp=" in s:
                    try:
                        part = s.split("datestamp=")[1].split("&")[0]
                        # "Sun+Apr+12+2026+..." formatı
                        yil_str = part.split("+")[3] if "+" in part else part.split("%")[0]
                        yil = int(yil_str) if yil_str.isdigit() else datetime.now().year
                        # Basit kontrol: yıl geçmişte mi
                        if yil < datetime.now().year:
                            return False, f"Cookie {yil} yılına ait — muhtemelen süresi dolmuş"
                    except Exception:
                        pass
                return True, ""
    return False, "Cookie dosyası boş veya sadece yorum satırı"


# ─── Subprocess çalıştır + timeout ────────────────────────────────────────────
def calistir(cmd: list[str], timeout_sn: int, log_dosya: Path) -> tuple[int, str]:
    """
    Komutu çalıştır, çıktıyı logla ve döndür.
    timeout_sn sonra process zorla durdurulur.
    Dönüş: (return_code, son_satir)
    """
    son_satir = ""
    try:
        with open(log_dosya, "a", encoding="utf-8") as lf:
            proc = subprocess.Popen(
                cmd,
                cwd=str(SCRIPT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            bitis = time.time() + timeout_sn
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    print(line, end="")
                    lf.write(line)
                    son_satir = line.strip() or son_satir
                if time.time() > bitis:
                    proc.kill()
                    msg = f"\n[TIMEOUT] {timeout_sn}s aşıldı — process durduruldu\n"
                    print(msg)
                    lf.write(msg)
                    return -1, "TIMEOUT"
            return proc.returncode, son_satir
    except Exception as e:
        return -2, str(e)


# ─── Çıktı klasöründen son JSON'u bul ve ürün sayısını al ─────────────────────
def son_json_urun_sayisi(market: str) -> int:
    """En son üretilen JSON dosyasındaki ürün sayısını döndür."""
    cikti      = SCRIPT_DIR / "cikti"
    html_pages = cikti / "html_pages"
    # Colruyt ve ALDI html_pages/ altına kaydeder
    desenleri = {
        "delhaize":  (cikti,      "delhaize_be_v2_*.json"),
        "colruyt":   (html_pages, "colruyt_Genel_p01_*.json"),
        "carrefour": (cikti,      "carrefour_be_v2_*.json"),
        "lidl":      (cikti,      "lidl_be_producten_*.json"),
        "aldi":      (cikti,      "aldi_be_*.json"),
    }
    klasor, desen = desenleri.get(market, (cikti, f"{market}_*.json"))
    dosyalar = glob.glob(str(klasor / desen))
    if not dosyalar:
        return 0
    son = max(dosyalar, key=os.path.getmtime)
    try:
        with open(son, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            for key in ("products", "urunler", "items", "data"):
                if isinstance(data.get(key), list):
                    return len(data[key])
    except Exception:
        pass
    return 0


def urun_sayisi_stdout_parse(son_satir: str) -> int:
    """html_analiz.py çıktısından ürün sayısını parse eder: 'TAMAMLANDI — Toplam 1990 ürün ...'"""
    import re
    m = re.search(r"Toplam\s+(\d+)\s+ürün", son_satir)
    return int(m.group(1)) if m else 0


# ─── Market çekim fonksiyonları ────────────────────────────────────────────────
def cek_delhaize(log: Path) -> int:
    ret, _ = calistir([sys.executable, "haftalik_delhaize_supabase.py"], TIMEOUT["delhaize"], log)
    return ret


def cek_colruyt(log: Path) -> tuple[int, int]:
    calistir([sys.executable, "colruyt_cookie_yenile.py"], 120, log)
    ret, _ = calistir([sys.executable, "colruyt_direct.py"], TIMEOUT["colruyt"], log)
    urun = 0
    if ret == 0:
        ret2, son = calistir([sys.executable, "html_analiz.py", "--market", "colruyt"], 300, log)
        urun = urun_sayisi_stdout_parse(son)
        if ret2 != 0:
            ret = ret2
    return ret, urun


def cek_carrefour(log: Path) -> int:
    ret, _ = calistir([sys.executable, "haftalik_carrefour_supabase.py"], TIMEOUT["carrefour"], log)
    return ret


def cek_lidl(log: Path) -> int:
    gecerli, uyari = lidl_cookie_kontrol()
    if not gecerli:
        print(R(f"\n[UYARI] Lidl cookie: {uyari}", SARI))
        print(R("  → F12 > Network > q/api/search > Request Headers > Cookie satırını lidl_cookie.txt'ye kopyala", SARI))
        with open(log, "a", encoding="utf-8") as lf:
            lf.write(f"[UYARI] Lidl cookie: {uyari}\n")
    ret, _ = calistir([sys.executable, "haftalik_lidl_supabase.py"], TIMEOUT["lidl"], log)
    return ret


def cek_aldi(log: Path) -> tuple[int, int]:
    ret1, _ = calistir([sys.executable, "sayfa_kaydet.py", "--market", "aldi"], TIMEOUT["aldi"] // 2, log)
    if ret1 != 0:
        return ret1, 0
    ret2, son = calistir([sys.executable, "html_analiz.py", "--market", "aldi"], 600, log)
    urun = urun_sayisi_stdout_parse(son)
    return ret2, urun


# Hangi marketler eski fiyat (üstü çizili) gösteriyor
ESKI_FIYAT_DESTEGI = {"lidl", "delhaize", "carrefour", "aldi"}  # colruyt API vermiyor

CEKICILER = {
    "delhaize":  cek_delhaize,
    "colruyt":   cek_colruyt,
    "carrefour": cek_carrefour,
    "lidl":      cek_lidl,
    "aldi":      cek_aldi,
}

# Önerilen çalıştırma sırası (ağır işler önce, paralel değil)
SIRALAMA = ["delhaize", "carrefour", "lidl", "colruyt", "aldi"]


# ─── Ana akış ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Akıllı haftalık fiyat güncelleyici")
    parser.add_argument("--market", nargs="+", choices=list(CEKICILER.keys()),
                        help="Sadece bu marketleri çek")
    parser.add_argument("--dry-run", action="store_true",
                        help="Sadece kontrol et, çekim yapma")
    args = parser.parse_args()

    hedefler = args.market if args.market else SIRALAMA
    bugun    = date.today().isoformat()
    log_dosya = LOG_DIR / f"haftalik_log_{bugun}.txt"

    print(f"\n{'='*60}")
    print(f"  HAFTALIK FİYAT GÜNCELLEME — {bugun}")
    print(f"  Marketler: {', '.join(hedefler)}")
    print(f"  Log: {log_dosya.name}")
    print(f"{'='*60}\n")

    with open(log_dosya, "a", encoding="utf-8") as lf:
        lf.write(f"\n{'='*60}\n")
        lf.write(f"Başlangıç: {datetime.now().isoformat()}\n")
        lf.write(f"Marketler: {', '.join(hedefler)}\n")
        lf.write(f"{'='*60}\n\n")

    if args.dry_run:
        print("[DRY-RUN] Sadece kontrol yapılıyor...\n")
        gecerli, uyari = lidl_cookie_kontrol()
        if gecerli:
            print(R("  Lidl cookie: geçerli görünüyor", YESIL))
        else:
            print(R(f"  Lidl cookie: {uyari}", KIRMIZI))
        print("\nMevcut cikti/ dosyaları:")
        for m in hedefler:
            n = son_json_urun_sayisi(m)
            esik = ESIKLER.get(m, 0)
            durum = R(f"{n} ürün ✓", YESIL) if n >= esik else R(f"{n} ürün ✗ (eşik: {esik})", KIRMIZI)
            print(f"  {m:12s}: {durum}")
        return

    ozet = {}  # market → {urun, sure, durum}

    for market in hedefler:
        print(f"\n{'─'*60}")
        print(f"  [{market.upper()}] başlıyor...")
        print(f"{'─'*60}")

        baslangic = time.time()
        cekici = CEKICILER[market]

        sonuc = cekici(log_dosya)
        if isinstance(sonuc, tuple):
            ret, stdout_urun = sonuc
        else:
            ret, stdout_urun = sonuc, 0
        sure = time.time() - baslangic

        # Ürün sayısı: stdout parse varsa kullan, yoksa JSON dosyasından al
        urun_sayisi = stdout_urun if stdout_urun > 0 else son_json_urun_sayisi(market)
        esik        = ESIKLER.get(market, 0)
        basarili    = ret == 0 and urun_sayisi >= esik

        # Başarısız ise 1 kez retry
        if not basarili and ret != -1:  # timeout değilse
            print(R(f"\n  [RETRY] {market}: {urun_sayisi} ürün (eşik: {esik}) — tekrar deneniyor...", SARI))
            with open(log_dosya, "a", encoding="utf-8") as lf:
                lf.write(f"[RETRY] {market}: {urun_sayisi} ürün, retry başlıyor\n")
            sonuc2 = cekici(log_dosya)
            if isinstance(sonuc2, tuple):
                ret2, stdout_urun2 = sonuc2
            else:
                ret2, stdout_urun2 = sonuc2, 0
            sure = time.time() - baslangic
            urun_sayisi = stdout_urun2 if stdout_urun2 > 0 else son_json_urun_sayisi(market)
            basarili = ret2 == 0 and urun_sayisi >= esik

        ozet[market] = {
            "urun":     urun_sayisi,
            "sure_dk":  round(sure / 60, 1),
            "basarili": basarili,
            "esik":     esik,
        }

    # ─── Özet rapor ─────────────────────────────────────────────────────────
    print(f"\n\n{'='*60}")
    print(f"  ÖZET RAPOR — {bugun}")
    print(f"{'='*60}")

    toplam_urun = 0
    sorunlar    = []

    for market, bilgi in ozet.items():
        simge = R("✓", YESIL) if bilgi["basarili"] else R("✗", KIRMIZI)
        renk  = YESIL if bilgi["basarili"] else KIRMIZI
        print(
            f"  {simge} {market:12s} "
            f"{R(str(bilgi['urun']), renk):>8} ürün  "
            f"({bilgi['sure_dk']} dk)"
        )
        if bilgi["basarili"]:
            toplam_urun += bilgi["urun"]
        else:
            sorunlar.append(market)

    print(f"{'─'*60}")
    print(f"  Toplam (başarılı): {toplam_urun:,} ürün")

    if sorunlar:
        print(R(f"\n  SORUNLU MARKETLER: {', '.join(sorunlar)}", KIRMIZI))
        print(R("  → BAKIM_KILAVUZU.md dosyasına bak", SARI))
    else:
        print(R("\n  Tüm marketler başarıyla güncellendi! ✓", YESIL))

    # Eski fiyat (üstü çizili) desteği
    print(f"\n  Eski fiyat gösterimi (market.html):")
    for m in hedefler:
        if m in ESKI_FIYAT_DESTEGI:
            print(R(f"    ✓ {m:12s} — eski fiyat + üstü çizili gösterir", YESIL))
        else:
            print(f"    ✗ {m:12s} — API eski fiyat vermiyor (sadece güncel fiyat)")

    print(f"\n  Log: {log_dosya}")
    print(f"{'='*60}\n")

    # Özeti log'a yaz
    with open(log_dosya, "a", encoding="utf-8") as lf:
        lf.write(f"\n{'='*60}\nÖZET\n{'='*60}\n")
        for market, bilgi in ozet.items():
            durum = "OK" if bilgi["basarili"] else "HATA"
            lf.write(f"  {market}: {durum}, {bilgi['urun']} ürün, {bilgi['sure_dk']} dk\n")
        if sorunlar:
            lf.write(f"\nSOrunlu: {', '.join(sorunlar)}\n")
        lf.write(f"Bitiş: {datetime.now().isoformat()}\n")

    # ─── Ürün eşleştirme (urun_eslestir.py) ─────────────────────────────────
    # Sadece tüm marketler başarılıysa çalıştır (kısmi güncelleme sonrası da çalışabilir)
    eslestir_script = SCRIPT_DIR / "urun_eslestir.py"
    if eslestir_script.exists() and not sorunlar:
        print(f"\n{'─'*60}")
        print("  [EŞLEŞTIRME] Marketler arası ürün eşleştirmesi başlıyor...")
        print(f"{'─'*60}")
        ret_e, _ = calistir([sys.executable, str(eslestir_script)], 600, log_dosya)
        if ret_e == 0:
            print(R("  Ürün eşleştirmesi tamamlandı. ✓", YESIL))
        else:
            print(R(f"  Ürün eşleştirmesi başarısız (kod: {ret_e})", KIRMIZI))
    elif sorunlar:
        print(R("\n  [EŞLEŞTIRME] Bazı marketler başarısız olduğu için atlandı.", SARI))


if __name__ == "__main__":
    main()
