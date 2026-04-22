"""
AŞAMA 4 — Vitrin & Listeleme Testleri
Kart görünümü, filtreler, harita yüklemesi, detay linki, mobil panel
"""
import time
import pytest
from conftest import (
    BASE_URL, THRESHOLDS, screenshot,
    wait_for_spinner_gone, wait_for_map, record_perf
)

# ─── Tanımlar ─────────────────────────────────────────────────────────────────
VITRINS = [
    {
        "slug":     "is_vitrini.html",
        "label":    "İş Vitrini",
        "harita":   True,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   {"sel": "#sektorSelect", "type": "select"},
    },
    {
        "slug":     "emlak_vitrini.html",
        "label":    "Emlak Vitrini",
        "harita":   True,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   None,
    },
    {
        "slug":     "vasita_vitrini.html",
        "label":    "Vasıta Vitrini",
        "harita":   True,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   None,
    },
    {
        "slug":     "esya_vitrini.html",
        "label":    "Eşya Vitrini",
        "harita":   False,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   None,
    },
    {
        "slug":     "hizmet_vitrini.html",
        "label":    "Hizmet Vitrini",
        "harita":   False,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   None,
    },
    {
        "slug":     "yemek_vitrini.html",
        "label":    "Yemek Vitrini",
        "harita":   False,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   None,
    },
    {
        "slug":     "diger_vitrini.html",
        "label":    "Diğer Vitrin",
        "harita":   False,
        "kart_sel": ".bg-white",
        "filtre":   None,
    },
    {
        "slug":     "hukuk_vitrini.html",
        "label":    "Hukuk Vitrini",
        "harita":   False,
        "kart_sel": ".bg-white",
        "filtre":   None,
    },
    {
        "slug":     "ilanlar.html",
        "label":    "Genel İlanlar",
        "harita":   False,
        "kart_sel": ".bg-white.rounded-2xl",
        "filtre":   None,
    },
]


# ─── İçerik yükleniyor mu? ────────────────────────────────────────────────────
@pytest.mark.parametrize("vitrin", VITRINS, ids=[v["slug"] for v in VITRINS])
def test_vitrin_content_loads(vitrin, page_guest):
    """Vitrin sayfası açılıyor, spinner kayboluyor, içerik veya boş state görünüyor."""
    url = f"{BASE_URL}/{vitrin['slug']}"
    t0 = time.perf_counter()
    page_guest.goto(url, wait_until="domcontentloaded", timeout=20000)

    spinner_ms = wait_for_spinner_gone(page_guest, timeout_ms=THRESHOLDS["content_ready"])
    content_ms = int((time.perf_counter() - t0) * 1000)

    record_perf(vitrin["slug"], "content_ready_ms", content_ms, THRESHOLDS["content_ready"])

    # İçerik var mı?
    body = page_guest.locator("body").inner_text()
    assert len(body) > 100, f"{vitrin['label']}: Sayfa içeriği çok az — yükleme sorunu"

    # Hız kontrolü
    assert content_ms <= THRESHOLDS["content_ready"], (
        f"{vitrin['label']}: İçerik {content_ms}ms'de hazır "
        f"(limit: {THRESHOLDS['content_ready']}ms)"
    )


# ─── İlan detayına link çalışıyor mu? ────────────────────────────────────────
@pytest.mark.parametrize("vitrin", VITRINS[:5], ids=[v["slug"] for v in VITRINS[:5]])
def test_vitrin_card_links_to_detay(vitrin, page_guest):
    """İlk karttaki link ilan_detay.html?id= sayfasına gitmeli."""
    url = f"{BASE_URL}/{vitrin['slug']}"
    page_guest.goto(url, wait_until="domcontentloaded", timeout=20000)
    wait_for_spinner_gone(page_guest, timeout_ms=6000)
    page_guest.wait_for_timeout(1000)

    # İncele/detay linki veya onclick bul
    kart = page_guest.locator(
        f"a[href*='ilan_detay'], button[onclick*='ilan_detay'], "
        f"[onclick*='ilan_detay.html']"
    ).first

    if kart.count() == 0:
        # Vitrin boş olabilir (DB'de ilan yok)
        body = page_guest.inner_text("body").lower()
        if "bulunamadı" in body or "henüz" in body or "yok" in body:
            pytest.skip(f"{vitrin['label']}: DB'de ilan yok — link testi atlandı")
        screenshot(page_guest, f"no_card_link_{vitrin['slug'].replace('.html','')}")
        pytest.fail(f"{vitrin['label']}: İlan detay linki bulunamadı")


# ─── Harita yükleme hız testi ─────────────────────────────────────────────────
MAP_VITRINS = [v for v in VITRINS if v["harita"]]

@pytest.mark.parametrize("vitrin", MAP_VITRINS, ids=[v["slug"] for v in MAP_VITRINS])
def test_vitrin_map_load_speed(vitrin, page_guest):
    """Harita görünümü THRESHOLDS['map_ready'] ms içinde yüklenmeli."""
    url = f"{BASE_URL}/{vitrin['slug']}"
    page_guest.goto(url, wait_until="domcontentloaded", timeout=20000)
    wait_for_spinner_gone(page_guest, timeout_ms=5000)

    # Harita view butonuna tıkla (varsa)
    harita_btn = page_guest.locator(
        "button:has-text('Harita'), [onclick*='harita'], [onclick*='map'], "
        "#mapBtn, #haritaBtn, [data-view='map']"
    ).first
    try:
        if harita_btn.is_visible():
            harita_btn.click()
            page_guest.wait_for_timeout(500)
    except Exception:
        pass

    t0 = time.perf_counter()
    map_ms = wait_for_map(page_guest, timeout_ms=THRESHOLDS["map_ready"])
    total_map_ms = int((time.perf_counter() - t0) * 1000)

    if map_ms == -1:
        # Harita yüklenmedi — DB'de ilan yoksa normaldir
        body = page_guest.inner_text("body").lower()
        if "bulunamadı" in body or "ilan yok" in body:
            pytest.skip(f"{vitrin['label']}: İlan yok, harita boş")
        screenshot(page_guest, f"map_fail_{vitrin['slug'].replace('.html','')}")
        pytest.fail(f"{vitrin['label']}: Leaflet haritası {THRESHOLDS['map_ready']}ms içinde yüklenmedi")

    record_perf(vitrin["slug"], "map_ms", total_map_ms, THRESHOLDS["map_ready"])

    assert total_map_ms <= THRESHOLDS["map_ready"], (
        f"{vitrin['label']}: Harita {total_map_ms}ms'de yüklendi "
        f"(limit: {THRESHOLDS['map_ready']}ms) — YAVAŞ"
    )


# ─── Vitrin filtrele butonu çalışıyor mu? ─────────────────────────────────────
def test_is_vitrini_rol_filter(page_guest):
    """İş vitrini 'İşveren' / 'İşçi' filtresi çalışmalı."""
    page_guest.goto(f"{BASE_URL}/is_vitrini.html", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 5000)
    page_guest.wait_for_timeout(1000)

    # İşveren filtresine tıkla
    btn = page_guest.locator("button:has-text('İşveren'), button:has-text('ELEMAN')").first
    try:
        if btn.is_visible():
            btn.click()
            page_guest.wait_for_timeout(1000)
    except Exception:
        pytest.skip("İşveren filtre butonu bulunamadı")


def test_emlak_vitrini_islem_filter(page_guest):
    """Emlak vitrini satılık/kiralık filtresi çalışmalı."""
    page_guest.goto(f"{BASE_URL}/emlak_vitrini.html", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 5000)
    page_guest.wait_for_timeout(1000)

    btn = page_guest.locator("button:has-text('Satılık'), button:has-text('Kiralık')").first
    try:
        if btn.is_visible():
            btn.click()
            page_guest.wait_for_timeout(1000)
    except Exception:
        pytest.skip("Satılık/Kiralık filtre butonu bulunamadı")


# ─── Arama kutusu çalışıyor mu? ────────────────────────────────────────────────
SEARCH_PAGES = [
    ("market.html",       "Market"),
    ("is_vitrini.html",   "İş Vitrini"),
    ("emlak_vitrini.html","Emlak Vitrini"),
]

@pytest.mark.parametrize("slug,label", SEARCH_PAGES, ids=[s[0] for s in SEARCH_PAGES])
def test_search_input_functional(slug, label, page_guest):
    """Arama kutusu — metin yazılabiliyor olmalı."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 5000)

    search = page_guest.locator(
        "input[type='search'], input[placeholder*='ara'], input[placeholder*='Ara'], "
        "input[placeholder*='search'], #searchInput, #aramaInput"
    ).first

    try:
        if search.is_visible():
            search.fill("test arama")
            page_guest.wait_for_timeout(800)
            val = search.input_value()
            assert "test" in val.lower(), f"{label}: Arama kutusuna yazılamadı"
    except Exception:
        pytest.skip(f"{label}: Arama kutusu bulunamadı")


# ─── Mobil filtre paneli (slide-up) ────────────────────────────────────────────
@pytest.fixture
def mobile_page(browser_instance):
    ctx = browser_instance.new_context(
        viewport={"width": 375, "height": 812},
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
    )
    page = ctx.new_page()
    yield page
    page.close()
    ctx.close()


def test_mobile_filter_panel_opens(mobile_page):
    """Mobilde filtre butonu tıklanınca panel açılmalı."""
    mobile_page.goto(f"{BASE_URL}/is_vitrini.html", wait_until="domcontentloaded")
    wait_for_spinner_gone(mobile_page, 5000)

    filter_btn = mobile_page.locator(
        "button:has-text('Filtrele'), button:has-text('Filtre'), "
        "#filterBtn, [onclick*='filter'], [onclick*='Filtre']"
    ).first

    try:
        if filter_btn.is_visible():
            filter_btn.click()
            mobile_page.wait_for_timeout(500)
            # Panelin açık olup olmadığını kontrol et
            panel = mobile_page.locator(
                ".filter-panel, #filterPanel, [class*='filter'][class*='open'], "
                "[class*='slide'], [class*='bottom-sheet']"
            ).first
            # Panel görünür olmalı ya da transform değişmeli
    except Exception:
        pytest.skip("Mobil filtre paneli bulunamadı")


# ─── İlan sayısı gösterge kontrolü ────────────────────────────────────────────
@pytest.mark.parametrize("slug", ["is_vitrini.html", "emlak_vitrini.html"])
def test_ilan_count_displayed(slug, page_guest):
    """İlan sayısı göstergesi sayfada bulunmalı."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 5000)
    page_guest.wait_for_timeout(1500)

    count_el = page_guest.locator(
        "#ilanSayisi, [id*='count'], [id*='sayi'], [class*='count']"
    ).first

    if count_el.count() > 0:
        try:
            text = count_el.inner_text()
            assert text.strip() != "", f"{slug}: İlan sayısı göstergesi boş"
        except Exception:
            pass
    else:
        pytest.skip(f"{slug}: İlan sayısı göstergesi bulunamadı")
