"""
╔══════════════════════════════════════════════════════════════╗
║  PLATFORM AVRUPA — ANA ÇALIŞTIRICI                          ║
║  Tüm marketleri sırayla çalıştırır                          ║
╚══════════════════════════════════════════════════════════════╝

Kullanım:
    python main.py                    # Tüm marketler
    python main.py --market colruyt   # Sadece Colruyt
    python main.py --market aldi      # Sadece ALDI
    python main.py --market lidl      # Sadece Lidl
    python main.py --market delhaize  # Sadece Delhaize
    python main.py --market carrefour # Sadece Carrefour
    python main.py --test             # Bağlantı testi

Kurulum:
    pip install -r requirements.txt
    playwright install chromium
"""

import asyncio
import argparse
import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import io
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MAIN] %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)


def test_connection():
    """Supabase bağlantısını test eder."""
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        log.error("❌ .env dosyasında SUPABASE_URL ve SUPABASE_SERVICE_KEY eksik!")
        log.info("💡 .env.example dosyasını kopyala: cp .env.example .env")
        return False

    try:
        sb     = create_client(url, key)
        result = sb.table("market_chain_products").select("id").limit(1).execute()
        log.info("✅ Supabase bağlantısı OK")
        log.info(f"   URL: {url[:40]}...")
        return True
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            log.error("❌ 'market_chain_products' tablosu yok!")
            log.info("💡 Supabase SQL Editor'da 'supabase_market_schema.sql' dosyasını çalıştır")
        else:
            log.error(f"❌ Bağlantı hatası: {e}")
        return False


def run_colruyt():
    from colruyt_scraper import run
    return run()


def run_aldi():
    from aldi_scraper import run
    return run()


def run_lidl():
    from lidl_scraper import run
    return run()


def run_delhaize():
    from delhaize_scraper import run
    return run()


def run_carrefour():
    from carrefour_scraper import run
    return run()


SCRAPERS = {
    "colruyt":  ("Colruyt BE",  run_colruyt),
    "aldi":     ("ALDI BE",     run_aldi),
    "lidl":     ("Lidl BE",     run_lidl),
    "delhaize": ("Delhaize BE", run_delhaize),
    "carrefour":("Carrefour BE",run_carrefour),
}


def main():
    parser = argparse.ArgumentParser(description="Platform Avrupa Market Scraper")
    parser.add_argument("--market", type=str, help="Belirli bir marketi çalıştır")
    parser.add_argument("--test",   action="store_true", help="Bağlantı testi yap")
    args = parser.parse_args()

    log.info("╔" + "═" * 58 + "╗")
    log.info("║  PLATFORM AVRUPA — MARKET SCRAPER v2.0                  ║")
    log.info(f"║  Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M')}                            ║")
    log.info("╚" + "═" * 58 + "╝")

    if args.test:
        ok = test_connection()
        sys.exit(0 if ok else 1)

    if not test_connection():
        sys.exit(1)

    results = {}

    if args.market:
        market_key = args.market.lower()
        if market_key not in SCRAPERS:
            log.error(f"Bilinmeyen market: {market_key}")
            log.info(f"Geçerli seçenekler: {', '.join(SCRAPERS.keys())}")
            sys.exit(1)

        name, fn = SCRAPERS[market_key]
        log.info(f"\n🛒 {name} başlıyor...")
        t0 = time.time()
        try:
            count = fn()
            elapsed = time.time() - t0
            results[market_key] = count
            log.info(f"✅ {name}: {count} ürün ({elapsed:.0f}s)")
        except Exception as e:
            log.error(f"❌ {name} hatası: {e}")
            results[market_key] = 0
    else:
        # Tüm marketler — sırayla
        for key, (name, fn) in SCRAPERS.items():
            log.info(f"\n{'='*60}")
            log.info(f"🛒 {name} başlıyor...")
            t0 = time.time()
            try:
                count = fn()
                elapsed = time.time() - t0
                results[key] = count
                log.info(f"✅ {name}: {count} ürün ({elapsed:.0f}s)")
            except Exception as e:
                log.error(f"❌ {name} hatası: {e}", exc_info=True)
                results[key] = 0

            # Marketler arası bekleme (ban riski minimizasyonu)
            import random
            wait = random.uniform(30, 90)
            log.info(f"⏱️  Sonraki market için {wait:.0f}s bekleniyor...")
            time.sleep(wait)

    # Özet
    log.info("\n" + "╔" + "═" * 58 + "╗")
    log.info("║  ÖZET                                                    ║")
    log.info("╠" + "═" * 58 + "╣")
    total = 0
    for key, count in results.items():
        name = SCRAPERS[key][0]
        log.info(f"║  {name:<20} {count:>8} ürün                    ║")
        total += (count or 0)
    log.info("╠" + "═" * 58 + "╣")
    log.info(f"║  TOPLAM               {total:>8} ürün                    ║")
    log.info("╚" + "═" * 58 + "╝")


if __name__ == "__main__":
    main()
