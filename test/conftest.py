"""
Platform Avrupa — Test Konfigürasyonu
Tüm testlerin ortak ayarları, fixtures ve yardımcı fonksiyonlar
"""
import pytest
import time
import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# ─── Ayarlar ──────────────────────────────────────────────────────────────────
BASE_URL    = "https://www.platformavrupa.com"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Hız eşikleri (ms)
THRESHOLDS = {
    "page_load":     8000,   # Sayfa yüklenmesi (Cloudflare CDN + Supabase init dahil)
    "content_ready": 8000,   # Spinner kapanması / içerik gözükmesi
    "map_ready":     10000,  # Leaflet harita init
    "form_submit":   8000,   # Form gönderim sonucu
    "db_read":       6000,   # Supabase SELECT
    "db_write":      8000,   # Supabase INSERT/UPDATE
}

# Test kullanıcısı — Supabase'de önceden oluşturulmuş
TEST_EMAIL    = "test_otomasyon@platformavrupa.com"
TEST_PASSWORD = "TestAuto2026!"

# Tüm sayfalar
ALL_PAGES = [
    # Genel
    ("index.html",              "Ana Sayfa",              False),
    ("login.html",              "Giriş",                  False),
    ("kayit.html",              "Kayıt",                  False),
    ("sifre_unuttum.html",      "Şifre Unut",             False),
    ("sifre_yenile.html",       "Şifre Yenile",           False),
    # Vitrinler
    ("ilanlar.html",            "İlanlar Vitrini",        False),
    ("is_vitrini.html",         "İş Vitrini",             False),
    ("emlak_vitrini.html",      "Emlak Vitrini",          False),
    ("vasita_vitrini.html",     "Vasıta Vitrini",         False),
    ("esya_vitrini.html",       "Eşya Vitrini",           False),
    ("hizmet_vitrini.html",     "Hizmet Vitrini",         False),
    ("yemek_vitrini.html",      "Yemek Vitrini",          False),
    ("diger_vitrini.html",      "Diğer Vitrin",           False),
    ("topluluk_vitrini.html",   "Topluluk Vitrini",       False),
    ("hukuk_vitrini.html",      "Hukuk Vitrini",          False),
    # İlan Detay & Giriş
    ("ilan_detay.html",         "İlan Detay",             False),
    ("ilan_giris.html",         "İlan Giriş",             False),
    # İlan Formları
    ("ilan_is.html",            "İş İlanı Formu",         False),
    ("ilan_emlak.html",         "Emlak İlanı Formu",      False),
    ("ilan_araba.html",         "Araç İlanı Formu",       False),
    ("ilan_esya.html",          "Eşya İlanı Formu",       False),
    ("ilan_hizmet.html",        "Hizmet İlanı Formu",     False),
    ("ilan_yemek.html",         "Yemek İlanı Formu",      False),
    ("ilan_diger.html",         "Diğer İlan Formu",       False),
    ("ilan_hukuk.html",         "Hukuk Başvurusu",        False),
    # Özel Modüller
    ("market.html",             "Market",                 False),
    ("doviz_altin.html",        "Döviz & Altın",          False),
    ("duyurular.html",          "Duyurular",              False),
    ("duyuru_detay.html",       "Duyuru Detay",           False),
    ("akademi.html",            "Akademi",                True ),
    ("akademi_kategori.html",   "Akademi Kategori",       True ),
    ("akademi_video.html",      "Akademi Video",          True ),
    ("saglik_turizmi.html",     "Sağlık Turizmi",         False),
    ("saglik_basvurularim.html","Sağlık Başvurularım",    True ),
    ("sila_yolu.html",          "Sıla Yolu",              False),
    ("yol_arkadasi.html",       "Yol Arkadaşı",           False),
    ("yol_ilan_ver.html",       "Yol İlan Ver",           False),
    ("yol_yardim.html",         "Yol Yardım",             False),
    ("kargo_emanet.html",       "Kargo Emanet",           False),
    ("kargo_talep.html",        "Kargo Talep",            False),
    ("sohbet.html",             "Sohbet",                 True ),
    ("profil.html",             "Profil",                 True ),
    ("favorilerim.html",        "Favorilerim",            True ),
    ("ilanlarim.html",          "İlanlarım",              True ),
    ("otel_rezervasyon.html",   "Otel Rezervasyon",       False),
    ("tatil_paketleri.html",    "Tatil Paketleri",        False),
    ("ucak_bileti.html",        "Uçak Bileti",            False),
    ("arac_kiralama.html",      "Araç Kiralama",          False),
    ("galeri.html",             "Galeri",                 False),
    ("firsatlar.html",          "Fırsatlar",              False),
    ("indirim_paylas.html",     "İndirim Paylaş",         False),
    ("yeni_gonderi.html",       "Yeni Gönderi",           False),
    ("avukat_detay.html",       "Avukat Detay",           False),
    ("admin.html",              "Admin",                  False),
]

HARITALI_PAGES = [
    "is_vitrini.html",
    "emlak_vitrini.html",
    "vasita_vitrini.html",
    "sila_yolu.html",
    "yol_arkadasi.html",
]


# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────
def screenshot(page: Page, name: str):
    """Ekran görüntüsü al."""
    path = SCREENSHOT_DIR / f"{name}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass
    return str(path)


def measure_navigation(page: Page, url: str) -> dict:
    """
    Sayfaya git, yükleme sürelerini ölç.
    Döner: {total_ms, dom_ready_ms, network_idle_ms, js_errors}
    """
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    t0 = time.perf_counter()
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    dom_ms = int((time.perf_counter() - t0) * 1000)

    try:
        # networkidle yerine load event — daha gerçekçi, 3rd-party isteklerini beklemez
        page.wait_for_load_state("load", timeout=10000)
    except Exception:
        pass
    total_ms = int((time.perf_counter() - t0) * 1000)

    status = response.status if response else 0
    return {
        "url":          url,
        "status":       status,
        "dom_ms":       dom_ms,
        "total_ms":     total_ms,
        "js_errors":    errors,
    }


def wait_for_spinner_gone(page: Page, timeout_ms: int = 8000) -> int:
    """
    Yükleme spinnerının kaybolmasını bekle.
    Döner: bekleme süresi (ms). Spinner yoksa 0.
    """
    t0 = time.perf_counter()
    spinners = [
        ".fa-spin", ".fa-circle-notch", "#loading",
        "[class*='spin']", "[class*='loading']"
    ]
    for sel in spinners:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.wait_for(state="hidden", timeout=timeout_ms)
                return int((time.perf_counter() - t0) * 1000)
        except Exception:
            continue
    return 0


def wait_for_map(page: Page, timeout_ms: int = 10000) -> int:
    """
    Leaflet haritasının yüklenmesini bekle.
    Döner: yükleme süresi (ms). Harita yoksa -1.
    """
    t0 = time.perf_counter()
    try:
        page.wait_for_selector(".leaflet-container", timeout=timeout_ms)
        # Tile'ların gelmesini bekle
        page.wait_for_function(
            "() => document.querySelectorAll('.leaflet-tile-loaded').length > 0",
            timeout=timeout_ms
        )
        return int((time.perf_counter() - t0) * 1000)
    except Exception:
        return -1


def collect_console_errors(page: Page) -> list:
    """Konsol hatalarını topla."""
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    return errors


# ─── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def context_guest(browser_instance):
    """Giriş yapmamış kullanıcı context."""
    ctx = browser_instance.new_context(
        viewport={"width": 1280, "height": 800},
        locale="tr-TR",
    )
    yield ctx
    ctx.close()


@pytest.fixture(scope="session")
def context_logged_in(browser_instance):
    """Giriş yapmış kullanıcı context (session-level login)."""
    ctx = browser_instance.new_context(
        viewport={"width": 1280, "height": 800},
        locale="tr-TR",
    )
    page = ctx.new_page()
    page.goto(f"{BASE_URL}/login.html", wait_until="networkidle", timeout=20000)
    try:
        page.fill("input[type='email']", TEST_EMAIL)
        page.fill("input[type='password']", TEST_PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_url(f"**/{BASE_URL}/**", timeout=10000)
    except Exception:
        pass
    page.close()
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page_guest(context_guest):
    page = context_guest.new_page()
    yield page
    page.close()


@pytest.fixture(scope="function")
def page_auth(context_logged_in):
    page = context_logged_in.new_page()
    yield page
    page.close()


# ─── Paylaşılan sonuçlar ──────────────────────────────────────────────────────
performance_results = {}

def record_perf(test_name: str, metric: str, value_ms: int, threshold_ms: int):
    """Performans sonucunu kaydet."""
    performance_results[f"{test_name}::{metric}"] = {
        "value_ms":    value_ms,
        "threshold_ms": threshold_ms,
        "pass":        value_ms <= threshold_ms,
    }
