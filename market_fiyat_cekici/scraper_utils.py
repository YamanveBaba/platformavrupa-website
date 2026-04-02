# -*- coding: utf-8 -*-
"""
Ortak scraper yardımcıları — tüm market scriptlerinde kullanılır.
  - Ban tespiti (içerik + başlık)
  - Exponential backoff
  - Graceful shutdown
  - Dosya loglama
  - JSON-LD structured data çıkarma
  - Proxy yükleme
  - robots.txt kontrolü
"""
from __future__ import annotations
import json, logging, os, random, re, signal, sys, time
from pathlib import Path
from typing import Callable, List, Optional


# ─── Loglama ──────────────────────────────────────────────────────────────────
def log_olustur(name: str, log_dir: Path = None) -> logging.Logger:
    """
    Hem konsola hem dosyaya yazan logger.
    log_dir belirtilmezse script_dir/cikti/logs/ kullanılır.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Konsol — INFO ve üzeri
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Dosya — DEBUG ve üzeri
    if log_dir is None:
        log_dir = Path(__file__).parent / "cikti" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{name}.log"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ─── Ban tespiti ──────────────────────────────────────────────────────────────
BAN_SINYALLERI = (
    "captcha", "robot", "i am not a robot", "are you a robot",
    "blocked", "access denied", "403 forbidden", "unusual traffic",
    "verify you are human", "cloudflare", "just a moment",
    "attention required", "ddos-guard", "security check",
    "please wait", "checking your browser", "enable cookies",
    "you have been blocked", "too many requests",
)


def ban_tespit(page, logger: logging.Logger = None) -> bool:
    """
    Sayfa başlığı + içeriği tarayarak ban/challenge var mı diye bakar.
    Bulursa True döner ve opsiyonel olarak loglar.
    """
    try:
        title   = (page.title() or "").lower()
        url_low = page.url.lower()

        # Önce hızlı başlık kontrolü
        for sinyal in BAN_SINYALLERI:
            if sinyal in title or sinyal in url_low:
                if logger:
                    logger.warning(f"Ban sinyali (başlık/URL): '{sinyal}'")
                return True

        # Sayfa içeriği kontrolü (ilk 8KB yeterli)
        content = ""
        try:
            content = (page.evaluate(
                "() => document.body ? document.body.innerText.slice(0, 8000).toLowerCase() : ''"
            ) or "").lower()
        except Exception:
            pass

        for sinyal in BAN_SINYALLERI:
            if sinyal in content:
                if logger:
                    logger.warning(f"Ban sinyali (içerik): '{sinyal}'")
                return True

    except Exception:
        pass
    return False


# ─── Exponential backoff ──────────────────────────────────────────────────────
BACKOFF_BASE = 12   # saniye
BACKOFF_MAX  = 150  # saniye


def backoff_bekle(attempt: int, logger: logging.Logger = None):
    """
    attempt=0 → ~12s, attempt=1 → ~24s, attempt=2 → ~48s, max 150s
    %20 jitter eklenir.
    """
    baz  = min(BACKOFF_BASE * (2 ** attempt), BACKOFF_MAX)
    sure = baz + random.uniform(0, baz * 0.20)
    if logger:
        logger.warning(f"Backoff: {sure:.1f}s bekleniyor (deneme {attempt + 1})")
    time.sleep(sure)


# ─── Graceful shutdown ────────────────────────────────────────────────────────
class StopSinyali:
    """Script içinde kontrol edilen durdurma bayrağı."""
    def __init__(self):
        self._dur = False

    @property
    def dur(self) -> bool:
        return self._dur

    def durdur(self):
        self._dur = True

    def sinyal_kaydet(self, logger: logging.Logger = None):
        """SIGINT / SIGTERM → graceful shutdown."""
        def _handler(signum, frame):
            if logger:
                logger.info("Durdurma sinyali alındı — mevcut kategori bittikten sonra çıkılacak.")
            else:
                print("\nDurdurma sinyali — checkpoint kaydediliyor…")
            self._dur = True

        signal.signal(signal.SIGINT,  _handler)
        signal.signal(signal.SIGTERM, _handler)


# ─── JSON-LD structured data ──────────────────────────────────────────────────
def jsonld_urun_cikart(page) -> List[dict]:
    """
    Sayfadaki tüm application/ld+json blokları.
    Product tipli olanları parse edip liste döner.
    Boş liste gelirse hiç ürün yok demektir.
    """
    urunler = []
    try:
        blocks = page.evaluate("""
            () => [...document.querySelectorAll('script[type="application/ld+json"]')]
                  .map(s => s.textContent || '')
                  .filter(t => t.includes('"Product"') || t.includes('"product"'))
        """)
        for block in (blocks or []):
            try:
                data = json.loads(block)
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    if data.get("@type") in ("Product", "product"):
                        items = [data]
                    else:
                        items = data.get("@graph", [])
                else:
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("@type") not in ("Product", "product"):
                        continue
                    offers = item.get("offers") or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}

                    price = None
                    try:
                        price = float(str(offers.get("price") or "0").replace(",", "."))
                    except Exception:
                        pass

                    barcode = (item.get("gtin13") or item.get("gtin8") or
                               item.get("sku") or item.get("productID") or "")

                    availability = (offers.get("availability") or "").lower()
                    in_stock = "instock" in availability or availability == ""

                    urunler.append({
                        "name":      (item.get("name") or "")[:300],
                        "brand":     (str((item.get("brand") or {}).get("name", "") or
                                          item.get("brand") or ""))[:120],
                        "price":     price,
                        "image_url": (item.get("image") or
                                      (item.get("image") or [{}])[0] if isinstance(item.get("image"), list) else
                                      item.get("image") or "")[:400],
                        "barcode":   str(barcode)[:100],
                        "in_stock":  in_stock,
                        "url":       (offers.get("url") or "")[:400],
                    })
            except Exception:
                continue
    except Exception:
        pass
    return urunler


# ─── Proxy yükleme ────────────────────────────────────────────────────────────
def proxy_yukle(dosya: str = "proxies.txt") -> List[Optional[str]]:
    """
    proxies.txt'den proxy listesi yükle.
    Format: http://user:pass@ip:port (her satır bir proxy)
    Dosya yoksa [None] döner (proxy'siz çalış).
    """
    yol = Path(__file__).parent / dosya
    if not yol.exists():
        return [None]
    satirlar = [s.strip() for s in yol.read_text(encoding="utf-8").splitlines()
                if s.strip() and not s.startswith("#")]
    return satirlar if satirlar else [None]


# ─── robots.txt kontrolü ─────────────────────────────────────────────────────
def robotstxt_kontrol(page, base_url: str, logger: logging.Logger = None) -> bool:
    """
    robots.txt'i kontrol eder, Disallow: / varsa uyarı loglar.
    Script'i durdurmaz — bilgilendirme amaçlı.
    True = dikkat et, False = temiz.
    """
    try:
        robots_url = base_url.rstrip("/") + "/robots.txt"
        page.goto(robots_url, wait_until="domcontentloaded", timeout=15_000)
        icerik = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
        # Bizim bot'u veya tüm bot'u engelliyor mu?
        if re.search(r"Disallow:\s*/(?:\s|$)", icerik):
            if logger:
                logger.warning(f"robots.txt Disallow: / içeriyor — {robots_url}")
            return True
        if "User-agent: *" in icerik and "Disallow" in icerik:
            if logger:
                logger.info(f"robots.txt bazı kısıtlamalar içeriyor — {robots_url}")
    except Exception:
        pass
    return False


# ─── HTTP durum kodu sınıflandırma ────────────────────────────────────────────
HARD_STOP_KODLARI  = {401, 403}   # Bu kodlarda dur, zorla
SOFT_RETRY_KODLARI = {429, 500, 502, 503, 504}  # Backoff uygula, devam et


def http_durum_isle(status: int, url: str, logger: logging.Logger = None) -> str:
    """
    Döner: 'devam' | 'backoff' | 'dur'
    """
    if status in HARD_STOP_KODLARI:
        if logger:
            logger.error(f"HTTP {status} — HARD STOP: {url[:80]}")
        return "dur"
    if status in SOFT_RETRY_KODLARI:
        if logger:
            logger.warning(f"HTTP {status} — backoff: {url[:80]}")
        return "backoff"
    return "devam"
