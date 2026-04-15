# -*- coding: utf-8 -*-
"""
sayfa_kaydet.py — Kategori sayfalarını Playwright ile kaydeder.

Her market için tanımlı kategorileri sırayla ziyaret eder,
ürünler yüklendikten sonra tam HTML'i dosyaya kaydeder.
Sonra html_analiz.py ile parse edilir.

Kullanım:
  python sayfa_kaydet.py                    # tüm marketler
  python sayfa_kaydet.py --market delhaize  # sadece Delhaize
  python sayfa_kaydet.py --market aldi
  python sayfa_kaydet.py --market colruyt
  python sayfa_kaydet.py --market carrefour
  python sayfa_kaydet.py --market lidl
"""
from __future__ import annotations
import argparse, json, os, shutil, socket, subprocess, sys, tempfile, time, random, re
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("pip install playwright && playwright install chromium")
    sys.exit(1)

SCRIPT_DIR  = Path(__file__).parent
CIKTI_DIR   = SCRIPT_DIR / "cikti" / "html_pages"
CIKTI_DIR.mkdir(parents=True, exist_ok=True)

# ─── Market kategori tanımları ────────────────────────────────────────────────

KATEGORILER = {
    "delhaize": {
        "base": "https://www.delhaize.be",
        "lang": "nl-BE",
        "urun_selector": "product-tile, [class*='product-tile'], [class*='productTile']",
        "sonraki_selector": "[aria-label='Volgende pagina'], [class*='next'], button[aria-label*='next']",
        "kategoriler": [
            ("Zuivel_Kaas_Eieren",   "https://www.delhaize.be/nl-BE/c/v2DAI"),
            ("Vlees_Vis",            "https://www.delhaize.be/nl-BE/c/v2MEA"),
            ("Brood_Banket",         "https://www.delhaize.be/nl-BE/c/v2BAK"),
            ("Groenten_Fruit",       "https://www.delhaize.be/nl-BE/c/v2FRU"),
            ("Snacks_Koekjes",       "https://www.delhaize.be/nl-BE/c/v2SWE"),
            ("Dranken",              "https://www.delhaize.be/nl-BE/c/v2DRI"),
            ("Kruidenierswaren",     "https://www.delhaize.be/nl-BE/c/v2CON"),
            ("Schoonmaak",           "https://www.delhaize.be/nl-BE/c/v2CLE"),
            ("Hygiene",              "https://www.delhaize.be/nl-BE/c/v2HYG"),
            ("Diepvries",            "https://www.delhaize.be/nl-BE/c/v2FRO"),
        ],
    },
    "aldi": {
        "base": "https://www.aldi.be",
        "lang": "nl-BE",
        "urun_selector": "[class*='product-tile'], [class*='ProductTile'], [class*='product-card']",
        "sonraki_selector": "[class*='next'], [aria-label*='next'], [aria-label*='volgende']",
        "kategoriler": [
            # Haftalık fırsatlar
            ("Aanbiedingen_week",    "https://www.aldi.be/nl/onze-aanbiedingen.html"),
            ("Aanbiedingen_volgend", "https://www.aldi.be/nl/aanbiedingen-volgende-week.html"),
            # Mevsimsel / özel (sezonluk)
            ("Zomerassortiment",     "https://www.aldi.be/nl/producten/zomerassortiment.html"),
            # Taze & Et & Vis
            ("Verse_producten",      "https://www.aldi.be/nl/producten/assortiment/verse-producten.html"),
            ("Groenten",             "https://www.aldi.be/nl/producten/assortiment/groenten.html"),
            ("Fruit",                "https://www.aldi.be/nl/producten/assortiment/fruit.html"),
            ("Vlees",                "https://www.aldi.be/nl/producten/assortiment/vlees.html"),
            ("Vis_Zeevruchten",      "https://www.aldi.be/nl/producten/assortiment/vis-zeevruchten.html"),
            # Zuivel & Brood
            ("Melkproducten_Kaas",   "https://www.aldi.be/nl/producten/assortiment/melkproducten-kaas.html"),
            ("Brood_Banket",         "https://www.aldi.be/nl/producten/assortiment/brood-en-banket.html"),
            ("Broodbeleg",           "https://www.aldi.be/nl/producten/assortiment/broodbeleg.html"),
            # Dranken
            ("Alcoholvrije_Dranken", "https://www.aldi.be/nl/producten/assortiment/alcoholvrije-dranken.html"),
            ("Alcoholische_Dranken", "https://www.aldi.be/nl/producten/assortiment/alcoholische-dranken.html"),
            # Diepvries & Kant-en-klaar
            ("Diepvrieskost",        "https://www.aldi.be/nl/producten/assortiment/diepvrieskost.html"),
            ("IJsjes",               "https://www.aldi.be/nl/producten/assortiment/ijsjes.html"),
            ("Kant_en_klaar",        "https://www.aldi.be/nl/producten/assortiment/kant-en-klaar.html"),
            ("Vegetarisch_Vegan",    "https://www.aldi.be/nl/producten/assortiment/vegetarisch-vegan.html"),
            # Droog
            ("Pasta_Rijst",          "https://www.aldi.be/nl/producten/assortiment/pasta-rijst.html"),
            ("Conserven",            "https://www.aldi.be/nl/producten/assortiment/conserven.html"),
            ("Bakken_Koken",         "https://www.aldi.be/nl/producten/assortiment/bakken-en-koken.html"),
            ("Koffie_Thee",          "https://www.aldi.be/nl/producten/assortiment/koffie-thee-cacao.html"),
            ("Muesli_Cornflakes",    "https://www.aldi.be/nl/producten/assortiment/muesli-cornflakes-granen.html"),
            ("Snacks_Zoetigheden",   "https://www.aldi.be/nl/producten/assortiment/snacks-zoetigheden.html"),
            ("Sauzen_Kruiden",       "https://www.aldi.be/nl/producten/assortiment/sauzen-kruiden-specerijen.html"),
            # Hygiene & Huishouden
            ("Cosmetica_Verzorging", "https://www.aldi.be/nl/producten/assortiment/cosmetica-verzorging.html"),
            ("Huishouden",           "https://www.aldi.be/nl/producten/assortiment/huishouden.html"),
            # Overig
            ("Dierenvoeding",        "https://www.aldi.be/nl/producten/assortiment/dierenvoeding.html"),
            ("Babyproducten",        "https://www.aldi.be/nl/producten/assortiment/babyproducten.html"),
        ],
    },
    "colruyt": {
        "base": "https://www.colruyt.be",
        "lang": "nl-BE",
        "urun_selector": "[class*='product'], [class*='ProductCard'], article",
        "sonraki_selector": "[aria-label*='next'], [aria-label*='volgende'], [class*='next']",
        "kategoriler": [
            ("Zuivel_Eieren",        "https://www.colruyt.be/nl/producten/zuivel-eieren"),
            ("Vlees_Vis",            "https://www.colruyt.be/nl/producten/vlees-vis-veggie"),
            ("Groenten_Fruit",       "https://www.colruyt.be/nl/producten/groenten-fruit"),
            ("Brood_Gebak",          "https://www.colruyt.be/nl/producten/brood-gebak-viennoisserie"),
            ("Dranken",              "https://www.colruyt.be/nl/producten/dranken"),
            ("Pasta_Rijst",          "https://www.colruyt.be/nl/producten/pasta-rijst-granen"),
            ("Conserven_Sauzen",     "https://www.colruyt.be/nl/producten/conserven-sauzen-soepen"),
            ("Snacks_Koekjes",       "https://www.colruyt.be/nl/producten/snacks-koekjes-gebak"),
            ("Hygieneproducten",     "https://www.colruyt.be/nl/producten/hygieneproducten"),
            ("Schoonmaak",           "https://www.colruyt.be/nl/producten/schoonmaak"),
        ],
    },
    "carrefour": {
        "base": "https://www.carrefour.be",
        "lang": "nl-BE",
        "urun_selector": "[class*='product'], [class*='Product'], article",
        "sonraki_selector": "[aria-label*='next'], [aria-label*='Volgende'], [class*='next']",
        "kategoriler": [
            ("Zuivel_Eieren",        "https://www.carrefour.be/nl/c/8000"),
            ("Vlees",                "https://www.carrefour.be/nl/c/6000"),
            ("Groenten_Fruit",       "https://www.carrefour.be/nl/c/9000"),
            ("Brood_Bakkerij",       "https://www.carrefour.be/nl/c/4000"),
            ("Dranken",              "https://www.carrefour.be/nl/c/11000"),
        ],
    },
    "lidl": {
        "base": "https://www.lidl.be",
        "lang": "nl-BE",
        "urun_selector": "[class*='product'], [class*='Product'], article",
        "sonraki_selector": "[aria-label*='next'], [class*='next']",
        "kategoriler": [
            ("Vers",                 "https://www.lidl.be/c/verse-producten/a10078940"),
            ("Zuivel",               "https://www.lidl.be/c/zuivel-kaas-en-eieren/a10063448"),
            ("Vlees",                "https://www.lidl.be/c/vlees-en-vis/a10063449"),
            ("Groenten_Fruit",       "https://www.lidl.be/c/groenten-en-fruit/a10063450"),
            ("Dranken",              "https://www.lidl.be/c/dranken/a10063453"),
        ],
    },
}

# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def sl(lo=1.5, hi=3.5):
    """Rastgele bekleme — insan gibi görünmek için."""
    time.sleep(random.uniform(lo, hi))


def temiz_dosya_adi(market: str, kategori: str, sayfa: int) -> Path:
    tarih = datetime.now().strftime("%Y-%m-%d")
    return CIKTI_DIR / f"{market}_{kategori}_p{sayfa:02d}_{tarih}.html"


def urun_sayisi_bekle(page, selector: str, min_count: int = 3, timeout: int = 20000):
    """Sayfada ürünler yüklenene kadar bekle, lazy-load için tam scroll yap."""
    try:
        page.wait_for_selector(selector, timeout=timeout)
    except PWTimeout:
        pass  # Selector bulunamadı, yine de devam

    sl(1.5, 2.5)

    # Sayfanın tamamını yavaşça kaydır — lazy load ve infinite scroll tetikle
    scroll_adim = 600
    son_yukseklik = 0
    dongu = 0
    while dongu < 30:  # max 30 adım (güvenlik)
        page.evaluate(f"window.scrollBy(0, {scroll_adim})")
        sl(0.6, 1.2)
        yeni_yukseklik = page.evaluate("document.body.scrollHeight")
        konum = page.evaluate("window.scrollY + window.innerHeight")
        dongu += 1
        if konum >= yeni_yukseklik:
            # Sayfa sonu — biraz bekle, yeni içerik yüklenebilir
            sl(1.5, 2.5)
            yeni_yukseklik2 = page.evaluate("document.body.scrollHeight")
            if yeni_yukseklik2 == yeni_yukseklik:
                break  # Gerçekten bitti
        son_yukseklik = yeni_yukseklik

    # Başa dön
    page.evaluate("window.scrollTo(0, 0)")
    sl(0.5, 1.0)


def sayfa_kaydet_ve_logla(page, dosya: Path, market: str, kategori: str, sayfa_no: int):
    """Sayfanın tam HTML içeriğini kaydet."""
    html = page.content()
    dosya.write_text(html, encoding="utf-8")
    kb = len(html) // 1024
    print(f"  [{market}] {kategori} sayfa-{sayfa_no:02d} -> {dosya.name} ({kb} KB)")


def sonraki_sayfa_var_mi(page, selector: str) -> bool:
    """Sonraki sayfa butonu aktif mi?"""
    try:
        btn = page.query_selector(selector)
        if btn and btn.is_visible() and btn.is_enabled():
            return True
    except Exception:
        pass
    return False


# ─── Chrome CDP yardımcıları (Colruyt antibot bypass) ────────────────────────

def _chrome_yolu_bul() -> str:
    """Windows'ta Chrome yürütülebilir dosyasını bul."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "chrome"  # PATH'te varsa çalışır


def _cdp_acik(port: int = 9222) -> bool:
    """Chrome'un CDP portunu dinleyip dinlemediğini kontrol et."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        r = s.connect_ex(("localhost", port))
        s.close()
        return r == 0
    except Exception:
        return False


def _colruyt_cookies_yukle() -> list[dict]:
    """colruyt_cookies.json'dan Playwright formatına çevir."""
    cookie_dosya = SCRIPT_DIR / "colruyt_cookies.json"
    if not cookie_dosya.exists():
        return []
    try:
        ham = json.loads(cookie_dosya.read_text(encoding="utf-8"))
        pw_cookies = []
        for c in ham:
            domain = c.get("domain", "")
            # Playwright domain'i nokta olmadan ister
            clean_domain = domain.lstrip(".")
            entry = {
                "name":   c["name"],
                "value":  c["value"],
                "domain": clean_domain,
                "path":   c.get("path", "/"),
            }
            if not c.get("session", True) and c.get("expirationDate"):
                entry["expires"] = int(c["expirationDate"])
            if c.get("secure"):
                entry["secure"] = True
            if c.get("httpOnly"):
                entry["httpOnly"] = True
            pw_cookies.append(entry)
        return pw_cookies
    except Exception as e:
        print(f"  [UYARI] Cookie yukleme hatasi: {e}")
        return []


def market_kaydet_colruyt(cfg: dict):
    """
    Colruyt: doğrudan requests ile API çağrısı.
    colruyt_direct.py'nin mantığını burada çağırır.
    """
    # colruyt_direct modülündeki fonksiyonu import et ve çağır
    import importlib.util
    direct_path = SCRIPT_DIR / "colruyt_direct.py"
    spec = importlib.util.spec_from_file_location("colruyt_direct", direct_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.colruyt_cek()


def _json_urun_iceriyor(data) -> bool:
    """JSON verisi ürün listesi içeriyor mu?"""
    if not isinstance(data, dict):
        return False
    # Colruyt API formatları: {products:[...]}, {productDetails:[...]}, {results:[...]}
    for key in ("products", "productDetails", "results", "items", "data"):
        val = data.get(key)
        if isinstance(val, list) and len(val) > 0:
            # İlk elemanın ürün gibi görünüp görünmediğini kontrol et
            first = val[0]
            if isinstance(first, dict) and any(
                k in first for k in ("name", "description", "price", "prices", "productCode", "id")
            ):
                return True
    return False


def _urun_sayisi_tah(data) -> int:
    """JSON'dan tahmini ürün sayısını çıkar."""
    if not isinstance(data, dict):
        return 0
    for key in ("products", "productDetails", "results", "items", "data"):
        val = data.get(key)
        if isinstance(val, list):
            return len(val)
    return 0


# ─── Ana akış ─────────────────────────────────────────────────────────────────

def market_kaydet_carrefour(cfg: dict):
    """Carrefour: Playwright ile dogrudan urun verisi cekme (carrefour_direct.py)."""
    import importlib.util
    direct_path = SCRIPT_DIR / "carrefour_direct.py"
    spec = importlib.util.spec_from_file_location("carrefour_direct", direct_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.carrefour_cek()


def market_kaydet_lidl(cfg: dict):
    """Lidl: Playwright ile dogrudan urun verisi cekme (lidl_direct.py)."""
    import importlib.util
    direct_path = SCRIPT_DIR / "lidl_direct.py"
    spec = importlib.util.spec_from_file_location("lidl_direct", direct_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.lidl_cek()


def market_kaydet(market: str, cfg: dict, headless: bool = True):
    # Colruyt: CDP ile gerçek Chrome kullan (antibot bypass)
    if market == "colruyt":
        market_kaydet_colruyt(cfg)
        return

    # Carrefour: Playwright ile JSON olarak cek
    if market == "carrefour":
        market_kaydet_carrefour(cfg)
        return

    # Lidl: Playwright ile JSON olarak cek
    if market == "lidl":
        market_kaydet_lidl(cfg)
        return

    print(f"\n{'='*60}")
    print(f"  {market.upper()} — {len(cfg['kategoriler'])} kategori")
    print(f"{'='*60}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale=cfg["lang"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        # Cookie banner'ları kapat
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        for kat_ad, kat_url in cfg["kategoriler"]:
            print(f"\n  >> {kat_ad}: {kat_url}")
            sayfa_no = 1

            try:
                page.goto(kat_url, wait_until="domcontentloaded", timeout=45000)
                sl(2.0, 4.0)

                # Cookie/consent butonu varsa kapat
                for consent_sel in [
                    "button#onetrust-accept-btn-handler",
                    "button[data-testid='accept-all']",
                    "button[id*='accept']",
                    "[class*='cookie'] button[class*='accept']",
                    "button[class*='CookieAccept']",
                    # ALDI BE
                    "button.button--filled:has-text('Alle cookies aanvaarden')",
                    "button:has-text('Alle cookies aanvaarden')",
                    "button:has-text('Alles accepteren')",
                    # Delhaize
                    "button:has-text('Alles accepteren')",
                    "button:has-text('Accept all')",
                ]:
                    try:
                        btn = page.query_selector(consent_sel)
                        if btn and btn.is_visible():
                            btn.click()
                            sl(1.0, 2.0)
                            break
                    except Exception:
                        pass

                # Ürünleri bekle
                urun_sayisi_bekle(page, cfg["urun_selector"])

                # İlk sayfayı kaydet
                dosya = temiz_dosya_adi(market, kat_ad, sayfa_no)
                sayfa_kaydet_ve_logla(page, dosya, market, kat_ad, sayfa_no)

                # Pagination — sonraki sayfalara geç
                while sayfa_no < 20:  # max 20 sayfa güvenlik limiti
                    if not sonraki_sayfa_var_mi(page, cfg["sonraki_selector"]):
                        break

                    try:
                        page.click(cfg["sonraki_selector"])
                        sl(2.5, 4.5)
                        urun_sayisi_bekle(page, cfg["urun_selector"])
                        sayfa_no += 1
                        dosya = temiz_dosya_adi(market, kat_ad, sayfa_no)
                        sayfa_kaydet_ve_logla(page, dosya, market, kat_ad, sayfa_no)
                    except Exception as e:
                        print(f"    Sonraki sayfa hatası: {e}")
                        break

                    # Sayfalar arası ekstra bekleme
                    sl(3.0, 6.0)

            except Exception as e:
                print(f"  HATA [{kat_ad}]: {e}")

            # Kategoriler arası bekleme
            sl(4.0, 8.0)

        browser.close()

    print(f"\n  {market.upper()} tamamlandı.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=list(KATEGORILER.keys()) + ["hepsi"],
                        default="hepsi", help="Hangi market kaydedilsin")
    parser.add_argument("--headless", action="store_true", default=False,
                        help="Tarayıcıyı gizli aç (varsayılan: görünür)")
    args = parser.parse_args()

    hedefler = (
        list(KATEGORILER.items())
        if args.market == "hepsi"
        else [(args.market, KATEGORILER[args.market])]
    )

    print(f"Kaydedilecek: {[k for k,_ in hedefler]}")
    print(f"Çıktı klasörü: {CIKTI_DIR}")

    for market, cfg in hedefler:
        market_kaydet(market, cfg, headless=args.headless)

    print(f"\nTum sayfalar kaydedildi: {CIKTI_DIR}")
    print("Şimdi html_analiz.py çalıştırabilirsiniz.")


if __name__ == "__main__":
    main()
