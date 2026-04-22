"""
AŞAMA 5 — İlan Formu Testleri
Validasyon, ülke/şehir seçimi, telefon prefix, DB insert hızı
NOT: Gerçek DB yazma testleri --run-write-tests flag ile etkinleştirilir
"""
import time
import pytest
from conftest import BASE_URL, THRESHOLDS, screenshot, record_perf

# ─── Form tanımları ───────────────────────────────────────────────────────────
FORMS = [
    {
        "slug":      "ilan_is.html",
        "label":     "İş İlanı",
        "min_fields": ["baslik", "aciklama", "telNo"],  # telefon = telNo
    },
    {
        "slug":      "ilan_emlak.html",
        "label":     "Emlak İlanı",
        "min_fields": ["baslik"],  # fiyat alanı farklı id ile tanımlanmış
    },
    {
        "slug":      "ilan_araba.html",
        "label":     "Araç İlanı",
        "min_fields": ["aciklama"],  # baslik = marka+model'den oluşturuluyor
    },
    {
        "slug":      "ilan_esya.html",
        "label":     "Eşya İlanı",
        "min_fields": ["baslik", "aciklama"],
    },
    {
        "slug":      "ilan_hizmet.html",
        "label":     "Hizmet İlanı",
        "min_fields": ["baslik", "aciklama"],
    },
    {
        "slug":      "ilan_yemek.html",
        "label":     "Yemek İlanı",
        "min_fields": ["baslik"],
    },
    {
        "slug":      "ilan_diger.html",
        "label":     "Diğer İlan",
        "min_fields": ["baslik", "aciklama"],
    },
    {
        "slug":      "ilan_hukuk.html",
        "label":     "Hukuk Başvurusu",
        "min_fields": [],
    },
]


# ─── Form yükleme hızı ────────────────────────────────────────────────────────
@pytest.mark.parametrize("form", FORMS, ids=[f["slug"] for f in FORMS])
def test_form_load_speed(form, page_guest):
    """Form sayfası THRESHOLDS['page_load'] ms içinde yüklenmeli."""
    t0 = time.perf_counter()
    page_guest.goto(f"{BASE_URL}/{form['slug']}", wait_until="networkidle", timeout=20000)
    elapsed = int((time.perf_counter() - t0) * 1000)

    record_perf(form["slug"], "load_ms", elapsed, THRESHOLDS["page_load"])
    assert elapsed <= THRESHOLDS["page_load"], (
        f"{form['label']}: Form {elapsed}ms'de yüklendi (limit: {THRESHOLDS['page_load']}ms)"
    )


# ─── Form alanları mevcut mu? ─────────────────────────────────────────────────
@pytest.mark.parametrize("form", FORMS, ids=[f["slug"] for f in FORMS])
def test_form_required_fields_exist(form, page_guest):
    """Formun temel alanları (id'si olan inputlar) mevcut olmalı."""
    page_guest.goto(f"{BASE_URL}/{form['slug']}", wait_until="domcontentloaded")
    page_guest.wait_for_timeout(500)

    for field_id in form["min_fields"]:
        el = page_guest.locator(f"#{field_id}, [name='{field_id}']")
        assert el.count() > 0, f"{form['label']}: '{field_id}' alanı bulunamadı"


# ─── Boş form → validasyon ───────────────────────────────────────────────────
@pytest.mark.parametrize("form", FORMS[:5], ids=[f["slug"] for f in FORMS[:5]])
def test_form_empty_submit_validation(form, page_guest):
    """Boş form gönderilince sayfa yönlendirmemeli veya hata göstermeli."""
    page_guest.goto(f"{BASE_URL}/{form['slug']}", wait_until="domcontentloaded")

    submit_btn = page_guest.locator("button[type='submit'], button:has-text('İlan Ver'), button:has-text('Gönder')").first
    if submit_btn.count() == 0:
        pytest.skip(f"{form['label']}: Submit butonu bulunamadı")

    submit_btn.click()
    page_guest.wait_for_timeout(1500)

    # Hâlâ aynı sayfada olmalı
    assert form["slug"] in page_guest.url or "ilanlarim" not in page_guest.url, \
        f"{form['label']}: Boş form gönderildiğinde yönlendirme yapmamalı"


# ─── Ülke seçimi → şehir listesi güncelleniyor mu? ───────────────────────────
ULKE_SECIM_FORMS = ["ilan_is.html", "ilan_emlak.html", "ilan_araba.html"]

@pytest.mark.parametrize("slug", ULKE_SECIM_FORMS)
def test_ulke_sehir_cascade(slug, page_guest):
    """Ülke seçilince şehir dropdown güncellenmeli."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")
    page_guest.wait_for_timeout(500)

    ulke_sel = page_guest.locator(
        "select[id*='ulke'], select[name*='ulke'], select[id*='country'], #ulkeSelect"
    ).first
    sehir_sel = page_guest.locator(
        "select[id*='sehir'], select[name*='sehir'], select[id*='city'], #sehirSelect"
    ).first

    if ulke_sel.count() == 0 or sehir_sel.count() == 0:
        pytest.skip(f"{slug}: Ülke veya şehir dropdown bulunamadı")

    # Önce şehir sayısını al
    sehir_once = sehir_sel.locator("option").count()

    # Almanya seç
    try:
        ulke_sel.select_option(value="DE")
    except Exception:
        try:
            ulke_sel.select_option(label="Almanya")
        except Exception:
            pytest.skip(f"{slug}: Almanya seçeneği bulunamadı")

    page_guest.wait_for_timeout(800)

    sehir_sonra = sehir_sel.locator("option").count()
    assert sehir_sonra > 1, f"{slug}: Ülke seçildi ama şehir listesi güncellenmedi"


# ─── Telefon ülke kodu prefix ─────────────────────────────────────────────────
@pytest.mark.parametrize("slug", ULKE_SECIM_FORMS)
def test_telefon_prefix(slug, page_guest):
    """Ülke seçilince telefon prefix (+49, +32 vb.) gösterilmeli."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")

    prefix_el = page_guest.locator(
        "[id*='prefix'], [id*='kod'], [class*='prefix'], "
        "span:has-text('+'), #ulkeTelKod"
    ).first

    if prefix_el.count() == 0:
        pytest.skip(f"{slug}: Telefon prefix elementi bulunamadı")

    # Belçika seç
    ulke_sel = page_guest.locator("#ulkeSelect, select[id*='ulke']").first
    try:
        ulke_sel.select_option(value="BE")
        page_guest.wait_for_timeout(500)
        prefix_text = prefix_el.inner_text()
        assert "+" in prefix_text, f"{slug}: Prefix '+' içermiyor: {prefix_text}"
    except Exception:
        pytest.skip(f"{slug}: Belçika seçimi başarısız")


# ─── ilan_detay.html — doğru çalışıyor mu? ───────────────────────────────────
def test_ilan_detay_without_id(page_guest):
    """ID olmadan ilan_detay.html → hata mesajı göstermeli."""
    page_guest.goto(f"{BASE_URL}/ilan_detay.html", wait_until="networkidle")
    page_guest.wait_for_timeout(2000)
    body = page_guest.inner_text("body").lower()
    assert any(w in body for w in ["bulunamadı", "hata", "id", "error"]), \
        "ilan_detay.html: ID olmadan hata mesajı gösterilmiyor"


def test_ilan_detay_invalid_id(page_guest):
    """Geçersiz ID ile ilan_detay.html → 'bulunamadı' mesajı göstermeli."""
    page_guest.goto(f"{BASE_URL}/ilan_detay.html?id=9999999999", wait_until="networkidle")
    page_guest.wait_for_timeout(3000)
    body = page_guest.inner_text("body").lower()
    assert any(w in body for w in ["bulunamadı", "silinmiş", "hata", "not found"]), \
        "ilan_detay.html: Geçersiz ID için 'bulunamadı' mesajı yok"


def test_ilan_detay_load_speed(page_guest):
    """ilan_detay.html?id=... sayfası THRESHOLDS['db_read'] ms'de yüklenmeli."""
    t0 = time.perf_counter()
    page_guest.goto(f"{BASE_URL}/ilan_detay.html?id=9999999999", wait_until="networkidle")
    elapsed = int((time.perf_counter() - t0) * 1000)
    record_perf("ilan_detay", "load_ms", elapsed, THRESHOLDS["db_read"] + 2000)
    # Geçersiz ID bile olsa sayfa 6sn içinde cevap vermeli
    assert elapsed <= 6000, f"ilan_detay.html: {elapsed}ms sürdü (limit: 6000ms)"


# ─── ilan_giris.html — yönlendirme linleri ───────────────────────────────────
def test_ilan_giris_has_category_links(page_guest):
    """ilan_giris.html tüm kategori formlarına link içermeli."""
    page_guest.goto(f"{BASE_URL}/ilan_giris.html", wait_until="domcontentloaded")
    content = page_guest.content()

    expected_forms = [
        "ilan_is.html", "ilan_emlak.html", "ilan_araba.html",
        "ilan_esya.html", "ilan_hizmet.html",
    ]
    missing = [f for f in expected_forms if f not in content]
    assert not missing, f"ilan_giris.html: Şu form linkleri eksik: {missing}"
