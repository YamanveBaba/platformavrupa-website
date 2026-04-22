"""
AŞAMA 1 — Statik Kod Analizi (Playwright gerekmez)
Dosyaları okuyarak hatalı referans, eksik import, kırık link tespiti
"""
import re
import pytest
from pathlib import Path

SRC = Path(__file__).parent.parent  # 04.01.2026 klasörü
# test_raporu.html ve diğer araç/rapor dosyaları hariç
_EXCLUDED_HTML = {"test_raporu.html", "emlak_ulke_test.html"}
HTML_FILES = sorted(f for f in SRC.glob("*.html") if f.name not in _EXCLUDED_HTML)

# ─── Yardımcılar ──────────────────────────────────────────────────────────────
def read(path): return path.read_text(encoding="utf-8", errors="ignore")
def html_list(): return [(f,) for f in HTML_FILES]

KNOWN_MISSING_OK = {
    "emlak_ulke_test.html",  # test/geliştirme dosyası
    "admin_chat.html",
    "admin_listings.html",
    "video_yonetim.html",
}

# Admin/dahili araç sayfaları — SEO meta gerekmez
INTERNAL_PAGES = {
    "admin.html", "admin_chat.html", "admin_listings.html",
    "video_yonetim.html", "emlak_ulke_test.html",
}

# ─── S1: Her sayfada <title> ve meta description ──────────────────────────────
@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s1_title_and_meta(html_file):
    if html_file.name in INTERNAL_PAGES:
        pytest.skip("Dahili araç sayfası — SEO meta gerekmez")
    content = read(html_file)
    assert "<title>" in content, f"{html_file.name}: <title> eksik"
    assert 'name="description"' in content, f"{html_file.name}: meta description eksik"


# ─── S2: Kırık iç linkler ─────────────────────────────────────────────────────
@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s2_broken_internal_links(html_file):
    content = read(html_file)
    links = re.findall(r'href=["\']([^"\'#?]+\.html)', content)
    broken = []
    for link in links:
        # Sadece lokal referanslar
        if link.startswith("http") or link.startswith("//"):
            continue
        target = SRC / link
        if not target.exists() and link not in KNOWN_MISSING_OK:
            broken.append(link)
    assert not broken, f"{html_file.name}: Kırık iç linkler: {broken}"


# ─── S3: 'listings' tablosu kalıntısı ────────────────────────────────────────
@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s3_no_listings_table(html_file):
    content = read(html_file)
    # Admin sayfaları listings kullanabilir, onları atla
    if html_file.name.startswith("admin"):
        pytest.skip("Admin sayfası — listings beklenen")
    matches = re.findall(r"from\(['\"]listings['\"]", content)
    assert not matches, (
        f"{html_file.name}: Hâlâ 'listings' tablosu kullanıyor ({len(matches)} adet). "
        f"'ilanlar' tablosuna geçirilmeli."
    )


# ─── S4: Supabase key tutarlılığı ─────────────────────────────────────────────
EXPECTED_URL = "https://vhietrqljahdmloazgpp.supabase.co"

@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s4_supabase_key_consistency(html_file):
    content = read(html_file)
    if "supabase" not in content.lower():
        pytest.skip("Supabase kullanmıyor")
    urls = re.findall(r"https://[a-z0-9]+\.supabase\.co", content)
    for u in urls:
        assert u == EXPECTED_URL, (
            f"{html_file.name}: Yanlış Supabase URL: {u} (beklenen: {EXPECTED_URL})"
        )


# ─── S5: utils.js kullanan ama import etmeyen sayfalar ───────────────────────
UTILS_FUNCTIONS = ["formatDate", "formatMoney", "formatRelativeTime"]

@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s5_utils_js_imported(html_file):
    content = read(html_file)
    used = [fn for fn in UTILS_FUNCTIONS if f"{fn}(" in content]
    if not used:
        pytest.skip("utils.js fonksiyonu kullanmıyor")
    # Kendi içinde tanımlamışsa sorun yok
    self_defined = [fn for fn in used if f"function {fn}" in content]
    if self_defined:
        pytest.skip(f"Kendi içinde tanımlı: {self_defined}")
    has_import = "utils.js" in content
    assert has_import, (
        f"{html_file.name}: {used} kullanıyor ama utils.js import edilmemiş ve kendi tanımı da yok"
    )


# ─── S6: auth.js gerektiren ama import etmeyen sayfalar ──────────────────────
AUTH_FUNCTIONS = ["requireAuth", "getSession", "signInWithPassword"]

@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s6_auth_js_imported(html_file):
    content = read(html_file)
    used = [fn for fn in AUTH_FUNCTIONS if f"{fn}(" in content or f"{fn}." in content]
    if not used:
        pytest.skip("auth.js fonksiyonu kullanmıyor")
    # Supabase'i doğrudan kullanıyorsa (sb.auth.getSession) auth.js gerekmez
    uses_sb_auth = "sb.auth." in content or "supabase.auth." in content
    if uses_sb_auth:
        pytest.skip("Supabase auth doğrudan kullanılıyor — auth.js wrapper gerekmez")
    has_import = "auth.js" in content
    assert has_import, (
        f"{html_file.name}: {used} kullanıyor ama auth.js import edilmemiş"
    )


# ─── S7: İlan formlarının kategori değerleri vitrinle uyumlu mu? ──────────────
FORM_KATEGORI_MAP = {
    "ilan_is.html":      "is",
    "ilan_emlak.html":   "Emlak",
    "ilan_araba.html":   "vasita",
    "ilan_esya.html":    "esya",
    "ilan_hizmet.html":  "hizmet",
    "ilan_yemek.html":   "mutfak",
    "ilan_diger.html":   "diger",
    "ilan_hukuk.html":   "HukukBasvuru",
}
VITRIN_KATEGORI_MAP = {
    "is_vitrini.html":      "is",
    "emlak_vitrini.html":   "Emlak",
    "vasita_vitrini.html":  "vasita",
    "esya_vitrini.html":    "esya",
    "hizmet_vitrini.html":  "hizmet",
    "yemek_vitrini.html":   "mutfak",
    "diger_vitrini.html":   "diger",
}

@pytest.mark.parametrize("form,expected_kat", list(FORM_KATEGORI_MAP.items()))
def test_s7_form_kategori_matches_vitrin(form, expected_kat):
    form_file = SRC / form
    if not form_file.exists():
        pytest.skip(f"{form} bulunamadı")
    content = read(form_file)
    assert f"'{expected_kat}'" in content or f'"{expected_kat}"' in content, (
        f"{form}: kategori değeri '{expected_kat}' bulunamadı. "
        f"Vitrinlerdeki .eq('kategori',...) ile uyumsuz olabilir."
    )


# ─── S8: Tüm sayfalarda viewport meta etiketi ────────────────────────────────
@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s8_viewport_meta(html_file):
    content = read(html_file)
    assert 'name="viewport"' in content, f"{html_file.name}: viewport meta etiketi eksik (mobil uyumsuz)"


# ─── S9: Script src'lerinde HTTP (HTTPS olmalı) ───────────────────────────────
@pytest.mark.parametrize("html_file", [f for f in HTML_FILES], ids=[f.name for f in HTML_FILES])
def test_s9_no_http_scripts(html_file):
    content = read(html_file)
    http_srcs = re.findall(r'src=["\']http://[^"\']+["\']', content)
    assert not http_srcs, f"{html_file.name}: HTTP (güvensiz) script kaynakları: {http_srcs}"


# ─── S10: Form'larda required alan kontrolü ───────────────────────────────────
FORM_FILES = [f for f in HTML_FILES if f.name.startswith("ilan_") and f.name != "ilan_detay.html" and f.name != "ilan_giris.html"]

@pytest.mark.parametrize("html_file", FORM_FILES, ids=[f.name for f in FORM_FILES])
def test_s10_form_has_required_fields(html_file):
    content = read(html_file)
    # En az bir required input olmalı
    has_required = "required" in content
    assert has_required, f"{html_file.name}: Hiç 'required' attribute yok — form validasyonu eksik olabilir"


# ─── S11: Korumalı sayfalar auth guard içeriyor mu? ──────────────────────────
PROTECTED_FILES = [
    "akademi.html",
    "akademi_kategori.html",
    "akademi_video.html",
    "profil.html",
    "ilanlarim.html",
    "favorilerim.html",
    "saglik_basvurularim.html",
    # sohbet.html atlandı — giriş yap linki ile farklı auth pattern kullanıyor
]

@pytest.mark.parametrize("filename", PROTECTED_FILES)
def test_s11_protected_pages_have_auth_guard(filename):
    """Korumalı sayfalar giriş kontrolü içermeli (login yönlendirmesi veya requireAuth)."""
    html_file = SRC / filename
    if not html_file.exists():
        pytest.skip(f"{filename} bulunamadı")
    content = read(html_file)
    auth_guards = [
        "requireAuth()",
        "window.location.href = 'login.html'",
        'window.location.href = "login.html"',
        "getSession",
        "getCurrentUser",
        "isLoggedIn",
    ]
    has_guard = any(g in content for g in auth_guards)
    assert has_guard, (
        f"{filename}: Korumalı sayfa ama auth guard bulunamadı. "
        f"requireAuth() çağrısı veya login yönlendirmesi eklenmeli."
    )
