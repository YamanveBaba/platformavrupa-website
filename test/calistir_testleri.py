"""
Platform Avrupa — Test Koşucu
Tüm testleri sırayla çalıştırır, renkli özet ve HTML rapor üretir.

Kullanım:
    python calistir_testleri.py             # Tüm testler
    python calistir_testleri.py --sadece-hizli   # Sadece statik + sayfa yükleme
    python calistir_testleri.py --sadece-guvenlik  # Sadece güvenlik
    python calistir_testleri.py --verbose    # Ayrıntılı çıktı
"""
import subprocess
import sys
import os
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)

KIRMIZI = "\033[91m"
YESIL   = "\033[92m"
SARI    = "\033[93m"
MAVI    = "\033[94m"
KOYU    = "\033[1m"
RESET   = "\033[0m"

def baslik(metin):
    print(f"\n{KOYU}{MAVI}{'═'*60}{RESET}")
    print(f"{KOYU}{MAVI}  {metin}{RESET}")
    print(f"{KOYU}{MAVI}{'═'*60}{RESET}\n")

ASAMA_GRUPLARI = [
    {
        "ad":    "AŞAMA 1 — Statik Kod Analizi",
        "dosya": "test_01_static.py",
        "acik":  "Kırık linkler, tablo isimleri, utils.js importları",
    },
    {
        "ad":    "AŞAMA 2 — Sayfa Yükleme & Hız",
        "dosya": "test_02_page_load.py",
        "acik":  "55 sayfanın yükleme süresi, spinner, mobil",
    },
    {
        "ad":    "AŞAMA 3 — Auth Akışları",
        "dosya": "test_03_auth.py",
        "acik":  "Giriş, kayıt, şifre sıfırlama, korumalı sayfalar",
    },
    {
        "ad":    "AŞAMA 4 — Vitrin Testleri",
        "dosya": "test_04_vitrins.py",
        "acik":  "Kart görünümü, filtreler, harita, arama",
    },
    {
        "ad":    "AŞAMA 5 — Form Testleri",
        "dosya": "test_05_forms.py",
        "acik":  "İlan formları, validasyon, ülke/şehir, telefon prefix",
    },
    {
        "ad":    "AŞAMA 6 — Özel Modüller",
        "dosya": "test_06_modules.py",
        "acik":  "Market, Akademi, Sağlık, Kargo, Sohbet, Döviz",
    },
    {
        "ad":    "AŞAMA 7 — Detaylı Performans",
        "dosya": "test_07_performance.py",
        "acik":  "Navigation Timing, LCP, harita tile, DB hızı, scroll jank",
    },
    {
        "ad":    "AŞAMA 8 — Güvenlik",
        "dosya": "test_08_security.py",
        "acik":  "XSS, SQL injection, admin koruması, HTTPS, mixed content, security headers",
    },
    {
        "ad":    "AŞAMA 9 — PWA, Profil, Admin, Detay Modüller",
        "dosya": "test_09_pwa.py",
        "acik":  "manifest.json, service worker, profil alanları, sohbet odaları, avukat, döviz detay, market detay",
    },
]

def calistir_asama(grup: dict, verbose: bool = False) -> dict:
    print(f"{KOYU}▶ {grup['ad']}{RESET}")
    print(f"  {grup['acik']}\n")

    cmd = [
        sys.executable, "-X", "utf8", "-m", "pytest",
        grup["dosya"],
        "--tb=short",
        f"--html=rapor_{grup['dosya'].replace('.py','')}.html",
        "--self-contained-html",
        "-q" if not verbose else "-v",
        "--no-header",
    ]

    t0 = time.perf_counter()
    result = subprocess.run(
        cmd,
        capture_output=not verbose,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - t0

    # Sonuçları parse et
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    output = stdout + stderr

    passed = failed = skipped = error = 0
    for line in output.split("\n"):
        if "passed" in line:
            try:
                parts = line.strip().split()
                for i, p in enumerate(parts):
                    if "passed" in p and i > 0:
                        passed = int(parts[i-1])
                    if "failed" in p and i > 0:
                        failed = int(parts[i-1])
                    if "skipped" in p and i > 0:
                        skipped = int(parts[i-1])
                    if "error" in p and i > 0:
                        error = int(parts[i-1])
            except (ValueError, IndexError):
                pass

    status = YESIL + "✓ GEÇTI" + RESET if result.returncode == 0 else KIRMIZI + "✗ HATALI" + RESET
    print(f"  {status}  |  {passed} geçti  {failed} hata  {skipped} atlandı  ({elapsed:.1f}s)")

    if result.returncode != 0 and not verbose:
        # Hataları göster
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "FAILED" in line or "AssertionError" in line or "ERROR" in line:
                print(f"  {KIRMIZI}{line}{RESET}")

    print()
    return {
        "ad": grup["ad"],
        "returncode": result.returncode,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "elapsed": elapsed,
    }


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sadece_hizli = "--sadece-hizli" in sys.argv
    sadece_guvenlik = "--sadece-guvenlik" in sys.argv

    if sadece_hizli:
        gruplar = ASAMA_GRUPLARI[:2]
    elif sadece_guvenlik:
        gruplar = [ASAMA_GRUPLARI[-1]]
    else:
        gruplar = ASAMA_GRUPLARI

    baslik("PLATFORM AVRUPA — KAPSAMLI TEST PAKETI")
    print(f"  Toplam aşama: {len(gruplar)}")
    print(f"  Hedef: {MAVI}https://www.platformavrupa.com{RESET}")
    print(f"  Raporlar: test_raporu_*.html\n")

    toplam_baslangic = time.perf_counter()
    sonuclar = []

    for grup in gruplar:
        sonuc = calistir_asama(grup, verbose)
        sonuclar.append(sonuc)

    toplam_sure = time.perf_counter() - toplam_baslangic

    # ─── Özet ─────────────────────────────────────────────────────────────────
    baslik("GENEL ÖZET")
    toplam_passed  = sum(s["passed"]  for s in sonuclar)
    toplam_failed  = sum(s["failed"]  for s in sonuclar)
    toplam_skipped = sum(s["skipped"] for s in sonuclar)

    print(f"  {YESIL}{KOYU}Geçen:     {toplam_passed}{RESET}")
    print(f"  {KIRMIZI}{KOYU}Başarısız: {toplam_failed}{RESET}")
    print(f"  {SARI}Atlanan:   {toplam_skipped}{RESET}")
    print(f"  Toplam süre: {toplam_sure:.1f}s\n")

    if toplam_failed > 0:
        print(f"{KIRMIZI}{KOYU}BAŞARISIZ AŞAMALAR:{RESET}")
        for s in sonuclar:
            if s["returncode"] != 0:
                print(f"  {KIRMIZI}✗ {s['ad']} ({s['failed']} hata){RESET}")

    print(f"\n{YESIL}Rapor dosyaları:{RESET}")
    for grup in gruplar:
        rapor = SCRIPT_DIR / f"rapor_{grup['dosya'].replace('.py','')}.html"
        if rapor.exists():
            print(f"  {rapor}")

    # Birleşik raporu da göster
    birlesik = SCRIPT_DIR / "test_raporu.html"

    # Birleşik raporu tüm testleri yeniden çalıştırarak oluştur
    if not ("--sadece-hizli" in sys.argv or "--sadece-guvenlik" in sys.argv):
        print(f"\n{MAVI}Birleşik HTML rapor oluşturuluyor...{RESET}")
        dosyalar = [g["dosya"] for g in gruplar]
        birlestir_cmd = [
            sys.executable, "-X", "utf8", "-m", "pytest",
            *dosyalar,
            "--tb=line",
            f"--html={birlesik}",
            "--self-contained-html",
            "-q",
            "--no-header",
        ]
        subprocess.run(birlestir_cmd, capture_output=True)

    if birlesik.exists():
        print(f"\n{KOYU}Birleşik rapor: {birlesik}{RESET}")

    return 0 if toplam_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
