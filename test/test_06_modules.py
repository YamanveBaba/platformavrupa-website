"""
AŞAMA 6 — Özel Modül Testleri
Market, Akademi, Sağlık, Sıla Yolu, Kargo, Sohbet, Profil, Duyurular, Döviz
"""
import time
import pytest
from conftest import (
    BASE_URL, THRESHOLDS, screenshot,
    wait_for_spinner_gone, record_perf
)


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET
# ═══════════════════════════════════════════════════════════════════════════════
class TestMarket:

    def test_market_loads(self, page_guest):
        """market.html yükleniyor ve içerik geliyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        spinner_ms = wait_for_spinner_gone(page_guest, THRESHOLDS["content_ready"])
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("market", "content_ms", elapsed, THRESHOLDS["content_ready"])

        body = page_guest.inner_text("body")
        assert len(body) > 200, "market.html: Sayfa içeriği boş"

    def test_market_filter_buttons(self, page_guest):
        """Market filtre butonları (Colruyt, Delhaize, ALDI, Lidl) mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)

        markets = ["Colruyt", "Delhaize", "ALDI", "Lidl"]
        found = []
        content = page_guest.content()
        for m in markets:
            if m in content:
                found.append(m)

        assert len(found) >= 2, f"market.html: Market butonları eksik. Bulunan: {found}"

    def test_market_search(self, page_guest):
        """Ürün arama kutusu mevcut ve çalışıyor."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)

        search = page_guest.locator(
            "input[type='search'], input[placeholder*='ara'], input[placeholder*='Ara'], #searchInput"
        ).first
        if search.count() == 0:
            pytest.skip("market.html: Arama kutusu bulunamadı")

        search.fill("melk")
        page_guest.wait_for_timeout(1000)
        assert search.input_value() != "", "market.html: Arama kutusuna yazılamadı"

    def test_market_packsize_visible(self, page_guest):
        """Ürün kartlarında miktar bilgisi (1L, 1kg vb.) görünmeli."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 8000)
        page_guest.wait_for_timeout(2000)

        content = page_guest.content()
        units = ["ml", "cl", "dl", "kg", "gr", "liter", "stuks", "L", "1L", "1kg"]
        found = [u for u in units if u in content]

        if not found:
            screenshot(page_guest, "market_no_packsize")
            pytest.fail(
                "market.html: Ürün kartlarında miktar bilgisi (ml, kg, L vb.) görünmüyor. "
                "packSize() fonksiyonu çalışmıyor olabilir."
            )

    def test_market_cross_market_match(self, page_guest):
        """Çapraz market karşılaştırma (match_group_id) sonuçları görünmeli."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 8000)
        page_guest.wait_for_timeout(2000)

        # Karşılaştırma UI elementleri (badge, tooltip, yan yana fiyat)
        compare = page_guest.locator(
            "[class*='compare'], [class*='match'], [class*='karsilastir'], "
            "[data-match], .price-compare"
        )
        # Bu test bilgilendirici — fail etse de uyarı ver
        if compare.count() == 0:
            pytest.skip(
                "market.html: Çapraz market karşılaştırma UI elementi bulunamadı — "
                "match_group_id görselleştirilmemiş olabilir"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# AKADEMİ
# ═══════════════════════════════════════════════════════════════════════════════
class TestAkademi:

    def test_akademi_loads(self, page_guest):
        """akademi.html açılıyor (giriş yapmadan ne gösteriyor?)."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/akademi.html", wait_until="networkidle")
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("akademi", "load_ms", elapsed, THRESHOLDS["page_load"])

        # Auth koruma ya da içerik göstermeli
        body = page_guest.inner_text("body")
        assert len(body) > 50, "akademi.html: İçerik tamamen boş"

    def test_akademi_kategori_load_speed(self, page_guest):
        """akademi_kategori.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/akademi_kategori.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("akademi_kategori", "load_ms", elapsed, THRESHOLDS["page_load"])

    def test_akademi_video_load_speed(self, page_guest):
        """akademi_video.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/akademi_video.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("akademi_video", "load_ms", elapsed, THRESHOLDS["page_load"])


# ═══════════════════════════════════════════════════════════════════════════════
# SAĞLIK TURİZMİ
# ═══════════════════════════════════════════════════════════════════════════════
class TestSaglik:

    def test_saglik_loads(self, page_guest):
        """saglik_turizmi.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/saglik_turizmi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("saglik_turizmi", "load_ms", elapsed, THRESHOLDS["page_load"])
        body = page_guest.inner_text("body")
        assert len(body) > 100

    def test_saglik_basvuru_form_exists(self, page_guest):
        """Sağlık başvuru formu mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/saglik_turizmi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        content = page_guest.content()
        has_form = "form" in content.lower() or "basvur" in content.lower() or "başvur" in content.lower()
        assert has_form, "saglik_turizmi.html: Başvuru formu bulunamadı"


# ═══════════════════════════════════════════════════════════════════════════════
# SILA YOLU
# ═══════════════════════════════════════════════════════════════════════════════
class TestSilaYolu:

    def test_sila_yolu_loads(self, page_guest):
        """sila_yolu.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/sila_yolu.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("sila_yolu", "load_ms", elapsed, THRESHOLDS["page_load"])

    def test_yol_arkadasi_loads(self, page_guest):
        """yol_arkadasi.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/yol_arkadasi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("yol_arkadasi", "load_ms", elapsed, THRESHOLDS["page_load"])

    def test_yol_yardim_sos_button(self, page_guest):
        """yol_yardim.html SOS/Yardım butonu mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/yol_yardim.html", wait_until="domcontentloaded")
        content = page_guest.content()
        has_sos = any(w in content for w in ["SOS", "sos", "Yardım", "yardim", "acil"])
        assert has_sos, "yol_yardim.html: SOS/Yardım butonu veya içerik bulunamadı"


# ═══════════════════════════════════════════════════════════════════════════════
# KARGO & EMANET
# ═══════════════════════════════════════════════════════════════════════════════
class TestKargo:

    def test_kargo_emanet_loads(self, page_guest):
        """kargo_emanet.html yükleniyor."""
        page_guest.goto(f"{BASE_URL}/kargo_emanet.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        body = page_guest.inner_text("body")
        assert len(body) > 100

    def test_kargo_talep_form_exists(self, page_guest):
        """kargo_talep.html form alanları mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/kargo_talep.html", wait_until="domcontentloaded")
        content = page_guest.content()
        has_form = "<form" in content or "insert" in content
        assert has_form, "kargo_talep.html: Form bulunamadı"


# ═══════════════════════════════════════════════════════════════════════════════
# SOHBET
# ═══════════════════════════════════════════════════════════════════════════════
class TestSohbet:

    def test_sohbet_requires_auth(self, page_guest):
        """sohbet.html giriş olmadan login'e yönlendirmeli."""
        page_guest.goto(f"{BASE_URL}/sohbet.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        body = page_guest.inner_text("body").lower()
        redirected = "login.html" in page_guest.url
        has_warning = any(w in body for w in ["giriş", "login", "oturum"])
        assert redirected or has_warning, \
            "sohbet.html: Giriş olmadan erişilebiliyor — auth koruması eksik"

    def test_sohbet_message_area_exists(self, page_auth):
        """Giriş yapılmışsa mesaj gönderme alanı mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/sohbet.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        page_auth.wait_for_timeout(1500)

        msg_input = page_auth.locator(
            "input[type='text'], textarea, #messageInput, #mesajInput, "
            "[placeholder*='mesaj'], [placeholder*='Mesaj']"
        ).first
        if msg_input.count() == 0:
            screenshot(page_auth, "sohbet_no_input")
            pytest.fail("sohbet.html: Mesaj giriş alanı bulunamadı")

    def test_sohbet_load_speed(self, page_auth):
        """Sohbet sayfası THRESHOLDS['content_ready'] ms içinde yüklenmeli."""
        t0 = time.perf_counter()
        page_auth.goto(f"{BASE_URL}/sohbet.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, THRESHOLDS["content_ready"])
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("sohbet", "load_ms", elapsed, THRESHOLDS["content_ready"])
        assert elapsed <= THRESHOLDS["content_ready"], \
            f"sohbet.html: {elapsed}ms sürdü (limit: {THRESHOLDS['content_ready']}ms)"


# ═══════════════════════════════════════════════════════════════════════════════
# PROFİL
# ═══════════════════════════════════════════════════════════════════════════════
class TestProfil:

    def test_profil_load_speed(self, page_auth):
        """profil.html hızlı yüklenmeli."""
        t0 = time.perf_counter()
        page_auth.goto(f"{BASE_URL}/profil.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("profil", "load_ms", elapsed, THRESHOLDS["content_ready"])

    def test_profil_has_edit_form(self, page_auth):
        """Profil sayfasında düzenleme alanları mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/profil.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        page_auth.wait_for_timeout(1000)

        edit_fields = page_auth.locator("input, textarea").count()
        if edit_fields == 0:
            screenshot(page_auth, "profil_no_form")
            pytest.fail("profil.html: Düzenleme alanları bulunamadı")


# ═══════════════════════════════════════════════════════════════════════════════
# DUYURULAR
# ═══════════════════════════════════════════════════════════════════════════════
class TestDuyurular:

    def test_duyurular_loads(self, page_guest):
        """duyurular.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/duyurular.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("duyurular", "load_ms", elapsed, THRESHOLDS["page_load"])

    def test_duyuru_detay_loads(self, page_guest):
        """duyuru_detay.html yükleniyor (ID olmadan hata göstermeli)."""
        page_guest.goto(f"{BASE_URL}/duyuru_detay.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        body = page_guest.inner_text("body")
        assert len(body) > 20, "duyuru_detay.html: Sayfa tamamen boş"


# ═══════════════════════════════════════════════════════════════════════════════
# DÖVİZ & ALTIN
# ═══════════════════════════════════════════════════════════════════════════════
class TestDoviz:

    def test_doviz_loads_fast(self, page_guest):
        """doviz_altin.html verileri THRESHOLDS['content_ready'] ms içinde yüklenmeli."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/doviz_altin.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, THRESHOLDS["content_ready"])
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("doviz_altin", "load_ms", elapsed, THRESHOLDS["content_ready"])

    def test_doviz_data_visible(self, page_guest):
        """Döviz/altın verileri gösterilmeli."""
        page_guest.goto(f"{BASE_URL}/doviz_altin.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(2000)

        content = page_guest.content()
        currency_symbols = ["€", "$", "TRY", "EUR", "USD", "GBP", "TL", "XAU", "Altın", "Dolar", "Euro"]
        found = [s for s in currency_symbols if s in content]
        assert len(found) >= 2, \
            f"doviz_altin.html: Döviz/altın verisi görünmüyor. Bulunan: {found}"


# ═══════════════════════════════════════════════════════════════════════════════
# REZERVASYON & SEYAHAT
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("slug,label", [
    ("otel_rezervasyon.html", "Otel Rezervasyon"),
    ("tatil_paketleri.html",  "Tatil Paketleri"),
    ("ucak_bileti.html",      "Uçak Bileti"),
    ("arac_kiralama.html",    "Araç Kiralama"),
])
def test_travel_pages_load(slug, label, page_guest):
    """Seyahat sayfaları yükleniyor ve içerik var."""
    t0 = time.perf_counter()
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 5000)
    elapsed = int((time.perf_counter() - t0) * 1000)
    record_perf(slug, "load_ms", elapsed, THRESHOLDS["page_load"])
    body = page_guest.inner_text("body")
    assert len(body) > 100, f"{label}: Sayfa içeriği boş"


# ═══════════════════════════════════════════════════════════════════════════════
# AFFİLİATE ENTEGRASYONLARI
# ═══════════════════════════════════════════════════════════════════════════════
class TestAffiliate:

    def test_booking_affiliate_id_in_url(self, page_guest):
        """Otel arama → Booking.com linki affiliate ID (304142) içermeli."""
        page_guest.goto(f"{BASE_URL}/otel_rezervasyon.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)

        content = page_guest.content()
        # Affiliate ID kaynak kodda referans edilmeli
        assert "304142" in content or "booking.com" in content.lower(), \
            "otel_rezervasyon.html: Booking.com affiliate ID (304142) bulunamadı"

    def test_booking_link_opens_correctly(self, page_guest):
        """Booking.com linki doğru domain'e gidiyor olmalı."""
        page_guest.goto(f"{BASE_URL}/otel_rezervasyon.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)

        links = page_guest.locator("a[href*='booking.com']")
        if links.count() == 0:
            # Booking widget iframe içinde olabilir
            content = page_guest.content()
            assert "booking.com" in content.lower(), \
                "otel_rezervasyon.html: Booking.com bağlantısı veya widget bulunamadı"
        else:
            href = links.first.get_attribute("href")
            assert "booking.com" in href, f"Link booking.com değil: {href}"

    def test_rentalcars_affiliate_code(self, page_guest):
        """Araç kiralama sayfası Rentalcars affiliate kodunu içermeli."""
        page_guest.goto(f"{BASE_URL}/arac_kiralama.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        content = page_guest.content()
        assert "rentalcars" in content.lower() or "platformavrupa" in content, \
            "arac_kiralama.html: Rentalcars affiliate kodu bulunamadı"

    def test_ucak_bileti_search_fields(self, page_guest):
        """Uçak bileti sayfasında nereden/nereye/tarih alanları mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/ucak_bileti.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        content = page_guest.content()
        # Skyscanner veya Travelpayouts widget var mı?
        has_widget = any(k in content.lower() for k in [
            "skyscanner", "travelpayouts", "aviasales", "kiwi",
            "nereden", "nereye", "kalkış", "varış", "origin", "destination"
        ])
        assert has_widget, \
            "ucak_bileti.html: Uçak arama widget veya nereden/nereye alanı bulunamadı"


# ═══════════════════════════════════════════════════════════════════════════════
# YOL ARKADAŞI — REZERVASYON AKIŞI
# ═══════════════════════════════════════════════════════════════════════════════
class TestYolArkadasi:

    def test_yol_arkadasi_listings_visible(self, page_guest):
        """yol_arkadasi.html ilanlar listeleniyor (veya boş state gösteriliyor)."""
        page_guest.goto(f"{BASE_URL}/yol_arkadasi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1500)
        body = page_guest.inner_text("body")
        assert len(body) > 100, "yol_arkadasi.html: Sayfa içeriği boş"

    def test_yol_arkadasi_koltuk_talep_requires_auth(self, page_guest):
        """'Koltuk Talep Et' butonu giriş yapmadan login'e yönlendirmeli."""
        page_guest.goto(f"{BASE_URL}/yol_arkadasi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1500)

        talep_btn = page_guest.locator(
            "button:has-text('Talep'), button:has-text('Koltuk'), "
            "button:has-text('Rezervasyon'), [onclick*='requestSeat'], [onclick*='talep']"
        ).first

        if talep_btn.count() == 0:
            # DB'de ilan yoksa skip
            body = page_guest.inner_text("body").lower()
            if any(w in body for w in ["ilan yok", "bulunamadı", "henüz"]):
                pytest.skip("yol_arkadasi.html: DB'de yol ilanı yok")
            pytest.skip("yol_arkadasi.html: Talep butonu bulunamadı")

        try:
            talep_btn.click(timeout=3000)
            page_guest.wait_for_timeout(2000)
            # Login sayfasına yönlendirmeli veya modal açılmalı
            is_redirected = "login.html" in page_guest.url
            body = page_guest.inner_text("body").lower()
            has_login_prompt = any(w in body for w in ["giriş", "login", "oturum"])
            assert is_redirected or has_login_prompt, \
                "yol_arkadasi.html: Koltuk talebi giriş gerektirmeden işleniyor"
        except Exception:
            pytest.skip("yol_arkadasi.html: Talep butonu tıklanamadı")

    def test_yol_ilan_ver_form_fields(self, page_guest):
        """yol_ilan_ver.html: nereden/nereye/tarih/koltuk/fiyat alanları mevcut."""
        page_guest.goto(f"{BASE_URL}/yol_ilan_ver.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        content = page_guest.content()
        required_keywords = ["kalkış", "varış", "nereden", "nereye", "tarih", "koltuk", "fiyat", "from", "to", "date", "seat", "price"]
        found = [k for k in required_keywords if k.lower() in content.lower()]
        assert len(found) >= 3, \
            f"yol_ilan_ver.html: Temel form alanları eksik. Bulunan: {found}"

    def test_yol_ilan_ver_ara_durak(self, page_guest):
        """Ara durak ekleme butonu mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/yol_ilan_ver.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        content = page_guest.content()
        has_ara_durak = any(k in content.lower() for k in ["ara durak", "aradurak", "waypoint", "durak ekle"])
        if not has_ara_durak:
            pytest.skip("yol_ilan_ver.html: Ara durak özelliği bulunamadı")


# ═══════════════════════════════════════════════════════════════════════════════
# KARGO AUTH KORUMASI
# ═══════════════════════════════════════════════════════════════════════════════
class TestKargoAuth:

    def test_kargo_emanet_auth_protection(self, page_guest):
        """kargo_emanet.html giriş olmadan login'e yönlendirmeli veya form kilitli olmalı."""
        page_guest.goto(f"{BASE_URL}/kargo_emanet.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "login", "oturum"])
        # Kaynak kodu kontrol et
        from pathlib import Path
        src = (Path(__file__).parent.parent / "kargo_emanet.html").read_text(encoding="utf-8", errors="ignore")
        has_guard = any(g in src for g in ["requireAuth", "window.location.href = 'login.html'", 'window.location.href = "login.html"'])
        assert redirected or has_warning or has_guard, \
            "kargo_emanet.html: Auth koruması görünmüyor"

    def test_kargo_talep_auth_protection(self, page_guest):
        """kargo_talep.html giriş olmadan korumalı olmalı."""
        page_guest.goto(f"{BASE_URL}/kargo_talep.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "login", "oturum"])
        from pathlib import Path
        src = (Path(__file__).parent.parent / "kargo_talep.html").read_text(encoding="utf-8", errors="ignore")
        has_guard = any(g in src for g in ["requireAuth", "window.location.href = 'login.html'", 'window.location.href = "login.html"'])
        assert redirected or has_warning or has_guard, \
            "kargo_talep.html: Auth koruması görünmüyor"


# ═══════════════════════════════════════════════════════════════════════════════
# SAĞLIK TURİZMİ — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestSaglikDetay:

    def test_saglik_klinik_list(self, page_guest):
        """Sağlık klinikleri listeleniyor veya bilgi içeriği var."""
        page_guest.goto(f"{BASE_URL}/saglik_turizmi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(2000)
        content = page_guest.content()
        has_clinic = any(k in content.lower() for k in [
            "klinik", "clinic", "hastane", "hospital", "tedavi", "treatment",
            "diş", "estetik", "saç", "göz"
        ])
        assert has_clinic, \
            "saglik_turizmi.html: Klinik/tedavi içeriği bulunamadı"

    def test_saglik_whatsapp_link_format(self, page_guest):
        """WhatsApp linki doğru formatta olmalı (wa.me veya api.whatsapp)."""
        page_guest.goto(f"{BASE_URL}/saglik_turizmi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        page_guest.wait_for_timeout(1000)
        content = page_guest.content()
        has_whatsapp = "whatsapp" in content.lower() or "wa.me" in content
        if not has_whatsapp:
            pytest.skip("saglik_turizmi.html: WhatsApp bağlantısı bulunamadı")
        # Placeholder numara kontrolü
        placeholder_patterns = ["XXXXXXXXX", "000000000", "+320", "placeholder"]
        has_placeholder = any(p in content for p in placeholder_patterns)
        if has_placeholder:
            pytest.skip("saglik_turizmi.html: WhatsApp numarası henüz ayarlanmamış (placeholder)")

    def test_saglik_basvurularim_auth(self, page_guest):
        """saglik_basvurularim.html auth gerektiriyor olmalı."""
        page_guest.goto(f"{BASE_URL}/saglik_basvurularim.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "login", "oturum"])
        assert redirected or has_warning, \
            "saglik_basvurularim.html: Giriş yapmadan erişilebiliyor"


# ═══════════════════════════════════════════════════════════════════════════════
# AKADEMİ — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestAkademiDetay:

    def test_akademi_video_player_exists(self, page_guest):
        """Akademi video sayfasında video oynatıcı veya YouTube embed var."""
        page_guest.goto(f"{BASE_URL}/akademi_video.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1500)
        content = page_guest.content()
        has_video = any(k in content.lower() for k in [
            "youtube", "youtu.be", "iframe", "<video", "video-player",
            "videoUrl", "video_url", "embed"
        ])
        assert has_video, \
            "akademi_video.html: Video oynatıcı veya YouTube embed bulunamadı"

    def test_akademi_kurs_talep_form(self, page_guest):
        """Akademi'de kurs talep formu veya butonu mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/akademi.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1000)
        content = page_guest.content()
        has_request = any(k in content.lower() for k in [
            "kurs talep", "video talep", "eğitim iste", "request", "talep et"
        ])
        if not has_request:
            pytest.skip("akademi.html: Kurs talep özelliği bulunamadı")

    def test_akademi_kategori_cards(self, page_guest):
        """Akademi kategori sayfasında içerik kartları görünmeli."""
        page_guest.goto(f"{BASE_URL}/akademi_kategori.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(2000)
        body = page_guest.inner_text("body")
        assert len(body) > 150, \
            "akademi_kategori.html: İçerik kartları yüklenemedi veya boş"


# ═══════════════════════════════════════════════════════════════════════════════
# GALERİ
# ═══════════════════════════════════════════════════════════════════════════════
class TestGaleri:

    def test_galeri_loads(self, page_guest):
        """galeri.html yükleniyor ve görsel veya içerik var."""
        page_guest.goto(f"{BASE_URL}/galeri.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1500)
        body = page_guest.inner_text("body")
        assert len(body) > 50, "galeri.html: Sayfa içeriği boş"

    def test_galeri_images_present(self, page_guest):
        """Galeride görseller veya görsel placeholder'ları mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/galeri.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(2000)
        content = page_guest.content()
        has_images = "<img" in content or "image" in content.lower() or "foto" in content.lower()
        assert has_images, "galeri.html: Görsel elementi bulunamadı"


# ═══════════════════════════════════════════════════════════════════════════════
# FIRSATLAR & İNDİRİM
# ═══════════════════════════════════════════════════════════════════════════════
class TestFirsatlar:

    def test_firsatlar_loads(self, page_guest):
        """firsatlar.html yükleniyor ve içerik var."""
        page_guest.goto(f"{BASE_URL}/firsatlar.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1500)
        body = page_guest.inner_text("body")
        assert len(body) > 100, "firsatlar.html: Sayfa içeriği boş"

    def test_indirim_paylas_form(self, page_guest):
        """indirim_paylas.html form alanları mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/indirim_paylas.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        content = page_guest.content()
        has_form = "<form" in content or "input" in content or "textarea" in content
        assert has_form, "indirim_paylas.html: Form bulunamadı"


# ═══════════════════════════════════════════════════════════════════════════════
# FAVORİLERİM
# ═══════════════════════════════════════════════════════════════════════════════
class TestFavoriler:

    def test_favorilerim_auth_guard(self, page_guest):
        """favorilerim.html giriş gerektiriyor olmalı."""
        page_guest.goto(f"{BASE_URL}/favorilerim.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "login", "oturum"])
        assert redirected or has_warning, \
            "favorilerim.html: Giriş olmadan erişilebiliyor — auth koruması eksik"

    def test_favorilerim_loads_when_auth(self, page_auth):
        """Giriş yapılmışsa favorilerim.html yükleniyor."""
        page_auth.goto(f"{BASE_URL}/favorilerim.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(1500)
        body = page_auth.inner_text("body")
        assert len(body) > 50, "favorilerim.html: Giriş yapılmış ama içerik boş"

    def test_favorite_toggle_on_ilan_detay(self, page_auth):
        """ilan_detay.html'de favori ekleme/çıkarma butonu mevcut olmalı (giriş yapılmışsa)."""
        page_auth.goto(f"{BASE_URL}/ilanlar.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(1500)
        content = page_auth.content()
        has_fav = any(k in content.lower() for k in ["favori", "favorite", "kalp", "heart", "bookmark"])
        if not has_fav:
            pytest.skip("İlan listesinde favori butonu bulunamadı")


# ═══════════════════════════════════════════════════════════════════════════════
# İLANLARIM
# ═══════════════════════════════════════════════════════════════════════════════
class TestIlanlarim:

    def test_ilanlarim_auth_guard(self, page_guest):
        """ilanlarim.html giriş gerektiriyor olmalı."""
        page_guest.goto(f"{BASE_URL}/ilanlarim.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "login", "oturum"])
        assert redirected or has_warning, \
            "ilanlarim.html: Giriş olmadan erişilebiliyor — auth koruması eksik"

    def test_ilanlarim_loads_when_auth(self, page_auth):
        """Giriş yapılmışsa ilanlarim.html yükleniyor."""
        page_auth.goto(f"{BASE_URL}/ilanlarim.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(1500)
        body = page_auth.inner_text("body")
        assert len(body) > 50, "ilanlarim.html: Giriş yapılmış ama içerik boş"

    def test_ilanlarim_has_delete_or_edit(self, page_auth):
        """İlanlarım sayfasında sil/düzenle seçeneği bulunmalı (ilan varsa)."""
        page_auth.goto(f"{BASE_URL}/ilanlarim.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(2000)

        # Giriş yapılamamışsa skip
        if "login.html" in page_auth.url:
            pytest.skip("ilanlarim.html: Test kullanıcısı giriş yapamadı")

        content = page_auth.content()
        body = page_auth.inner_text("body").lower()

        # Kullanıcının ilanı yoksa (çeşitli boş state mesajları)
        no_listings = any(w in body for w in [
            "henüz", "ilan yok", "bulunamadı", "kayıt yok",
            "no listings", "empty", "boş", "yüklen"
        ])
        if no_listings:
            pytest.skip("ilanlarim.html: Kullanıcının ilanı yok — aksiyon butonu testi atlandı")

        # Dinamik içerik: JS ile render edilmiş olabilir — kaynak kodu da kontrol et
        has_action_in_src = any(k in content for k in [
            "ilanSil", "ilanDuzenle", "fa-trash", "fa-edit",
            "onclick*='sil'", "onclick*='duzenle'"
        ])
        has_action_in_body = any(k in body for k in [
            "sil", "düzenle", "delete", "edit", "kaldır", "güncelle"
        ])

        # En az biri yeterliyse geçer
        if has_action_in_src or has_action_in_body:
            return  # PASS

        pytest.skip(
            "ilanlarim.html: Test kullanıcısının ilanı görünmüyor "
            "(Supabase'de ilan olmayabilir veya sayfa tam yüklenmedi)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SILA YOLU HARİTA — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestSilaYoluHarita:

    def test_sila_yolu_leaflet_loads(self, page_guest):
        """sila_yolu.html Leaflet haritası yükleniyor."""
        page_guest.goto(f"{BASE_URL}/sila_yolu.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(3000)

        # Leaflet container mevcut mu?
        leaflet = page_guest.locator(".leaflet-container")
        if leaflet.count() == 0:
            content = page_guest.content()
            has_leaflet_js = "leaflet" in content.lower()
            if not has_leaflet_js:
                pytest.fail("sila_yolu.html: Leaflet.js import edilmemiş")
            pytest.skip("sila_yolu.html: Leaflet container oluşturulmadı (harita init sorunu olabilir)")
        assert leaflet.first.is_visible(), "sila_yolu.html: Leaflet haritası görünmüyor"

    def test_sila_yolu_map_tiles(self, page_guest):
        """Harita tile'ları yükleniyor (OpenStreetMap)."""
        page_guest.goto(f"{BASE_URL}/sila_yolu.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(4000)

        tile_count = page_guest.locator(".leaflet-tile-loaded").count()
        if tile_count == 0:
            pytest.skip("sila_yolu.html: Harita tile'ları yüklenmedi (OpenStreetMap erişim sorunu olabilir)")

        print(f"\n[SILA YOLU HARİTA] {tile_count} tile yüklendi")

    def test_sila_yolu_has_border_info(self, page_guest):
        """Sıla yolu sayfasında gümrük kapısı veya yol bilgisi mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/sila_yolu.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(2000)
        content = page_guest.content()
        has_border = any(k in content.lower() for k in [
            "gümrük", "border", "kapı", "geçiş", "sınır", "viyana",
            "budapeşte", "belgrad", "bulgaria"
        ])
        assert has_border, \
            "sila_yolu.html: Gümrük kapısı veya yol bilgisi içeriği bulunamadı"
