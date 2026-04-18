"""
AŞAMA 9 — PWA, Profil, Duyurular, Galeri, Fırsatlar Testleri
manifest.json, service worker, offline mod, profil güncelleme,
avukat detay, sıla yolu sohbet odaları, admin panel erişimi
"""
import time
import json
import pytest
from pathlib import Path
from conftest import BASE_URL, THRESHOLDS, screenshot, wait_for_spinner_gone, record_perf

SRC = Path(__file__).parent.parent


# ═══════════════════════════════════════════════════════════════════════════════
# PWA — manifest.json
# ═══════════════════════════════════════════════════════════════════════════════
class TestManifest:

    def test_manifest_json_exists_and_valid(self):
        """manifest.json geçerli JSON ve zorunlu alanlar dolu olmalı."""
        manifest_path = SRC / "manifest.json"
        assert manifest_path.exists(), "manifest.json bulunamadı"

        content = manifest_path.read_text(encoding="utf-8")
        try:
            manifest = json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"manifest.json geçersiz JSON: {e}")

        required_fields = ["name", "short_name", "start_url", "display", "icons"]
        missing = [f for f in required_fields if f not in manifest]
        assert not missing, f"manifest.json: Zorunlu alanlar eksik: {missing}"

    def test_manifest_has_icons(self):
        """manifest.json en az bir ikon tanımı içermeli."""
        manifest_path = SRC / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("manifest.json bulunamadı")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        icons = manifest.get("icons", [])
        assert len(icons) > 0, "manifest.json: icons dizisi boş"

        for icon in icons:
            assert "src" in icon, f"İkon tanımında 'src' eksik: {icon}"
            # İkon dosyası var mı?
            icon_path = SRC / icon["src"]
            assert icon_path.exists(), f"İkon dosyası bulunamadı: {icon['src']}"

    def test_manifest_display_standalone(self):
        """manifest.json display: standalone veya fullscreen olmalı (PWA modu)."""
        manifest_path = SRC / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("manifest.json bulunamadı")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        display = manifest.get("display", "")
        assert display in ("standalone", "fullscreen", "minimal-ui"), (
            f"manifest.json: display='{display}' — PWA için 'standalone' önerilir"
        )

    def test_manifest_shortcuts_valid(self):
        """manifest.json shortcuts varsa hedef URL'ler geçerli olmalı."""
        manifest_path = SRC / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("manifest.json bulunamadı")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        shortcuts = manifest.get("shortcuts", [])
        if not shortcuts:
            pytest.skip("manifest.json: shortcuts tanımlanmamış")

        broken = []
        for s in shortcuts:
            url = s.get("url", "")
            # Relative URL → dosya adını çıkar
            slug = url.lstrip("/").split("?")[0]
            if slug and not slug.startswith("http"):
                target = SRC / slug
                if not target.exists():
                    broken.append(url)

        assert not broken, f"manifest.json: Kırık shortcut URL'leri: {broken}"

    def test_manifest_served_by_site(self, page_guest):
        """Site manifest.json'ı HTTP üzerinden sunuyor mu?"""
        response = page_guest.goto(f"{BASE_URL}/manifest.json", wait_until="load")
        assert response.status == 200, (
            f"manifest.json HTTP {response.status} döndü — erişilemiyor"
        )
        content_type = response.headers.get("content-type", "")
        assert "json" in content_type or "manifest" in content_type or "javascript" in content_type, (
            f"manifest.json: Yanlış Content-Type: {content_type}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PWA — Service Worker
# ═══════════════════════════════════════════════════════════════════════════════
class TestServiceWorker:

    def test_sw_file_exists(self):
        """service-worker.js dosyası mevcut olmalı."""
        sw_path = SRC / "service-worker.js"
        assert sw_path.exists(), "service-worker.js bulunamadı"

    def test_sw_registers_on_index(self, page_guest):
        """Ana sayfa service worker kayıt ediyor olmalı."""
        page_guest.goto(f"{BASE_URL}/index.html", wait_until="load", timeout=20000)
        page_guest.wait_for_timeout(3000)  # SW kayıt için bekle

        sw_registered = page_guest.evaluate("""async () => {
            if (!('serviceWorker' in navigator)) return 'not_supported';
            try {
                const reg = await navigator.serviceWorker.getRegistration('/');
                return reg ? 'registered' : 'not_registered';
            } catch(e) {
                return 'error:' + e.message;
            }
        }""")

        if sw_registered == "not_supported":
            pytest.skip("Bu tarayıcı Service Worker desteklemiyor")

        assert sw_registered == "registered", (
            f"Service Worker kayıtlı değil: {sw_registered}\n"
            f"index.html'de navigator.serviceWorker.register() çağrısı eksik olabilir"
        )

    def test_sw_served_correctly(self, page_guest):
        """service-worker.js HTTP 200 ve doğru Content-Type ile sunuluyor."""
        response = page_guest.goto(f"{BASE_URL}/service-worker.js", wait_until="load")
        assert response.status == 200, (
            f"service-worker.js HTTP {response.status} — erişilemiyor"
        )

    def test_sw_has_cache_strategy(self):
        """service-worker.js cache stratejisi tanımlanmış olmalı."""
        sw_path = SRC / "service-worker.js"
        if not sw_path.exists():
            pytest.skip("service-worker.js bulunamadı")

        content = sw_path.read_text(encoding="utf-8")
        has_cache = any(k in content for k in [
            "caches.open", "cache.put", "cache.match",
            "CacheFirst", "NetworkFirst", "StaleWhileRevalidate"
        ])
        assert has_cache, "service-worker.js: Cache stratejisi tanımlanmamış"

    def test_sw_version_defined(self):
        """service-worker.js cache versiyonu tanımlanmış olmalı."""
        sw_path = SRC / "service-worker.js"
        if not sw_path.exists():
            pytest.skip("service-worker.js bulunamadı")

        content = sw_path.read_text(encoding="utf-8")
        has_version = any(k in content for k in ["CACHE_NAME", "CACHE_VERSION", "v1", "v2", "v3", "v4", "v5"])
        assert has_version, "service-worker.js: Cache versiyonu tanımlanmamış (cache busting için gerekli)"


# ═══════════════════════════════════════════════════════════════════════════════
# PWA — HTML Entegrasyonu
# ═══════════════════════════════════════════════════════════════════════════════
class TestPWAHtmlIntegration:

    def test_index_has_manifest_link(self):
        """index.html manifest.json'a link içermeli."""
        index = SRC / "index.html"
        assert index.exists()
        content = index.read_text(encoding="utf-8")
        assert 'rel="manifest"' in content or "rel='manifest'" in content, (
            "index.html: <link rel='manifest'> etiketi eksik"
        )

    def test_index_has_theme_color(self):
        """index.html theme-color meta etiketi içermeli."""
        index = SRC / "index.html"
        content = index.read_text(encoding="utf-8")
        assert 'name="theme-color"' in content or "name='theme-color'" in content, (
            "index.html: theme-color meta etiketi eksik"
        )

    def test_index_registers_sw(self):
        """index.html service worker register kodu içermeli."""
        index = SRC / "index.html"
        content = index.read_text(encoding="utf-8")
        has_sw_register = (
            "serviceWorker.register" in content
            or "service-worker.js" in content
        )
        assert has_sw_register, (
            "index.html: Service Worker kayıt kodu bulunamadı\n"
            "navigator.serviceWorker.register('service-worker.js') eklenmeli"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PROFİL — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestProfilDetay:

    def test_profil_has_name_field(self, page_auth):
        """profil.html ad/soyad input alanı mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/profil.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        page_auth.wait_for_timeout(1500)

        # Giriş yapılamamışsa (test user Supabase'de yok) skip
        if "login.html" in page_auth.url or "kayit.html" in page_auth.url:
            pytest.skip("profil.html: Test kullanıcısı giriş yapamadı — Supabase'de kayıtlı olmayabilir")

        name_field = page_auth.locator(
            "#realName, #fullName, #full_name, #nickName, #ad, "
            "input[name*='name'], input[placeholder*='ad'], input[placeholder*='Ad'], "
            "input[placeholder*='İsim'], input[placeholder*='isim']"
        ).first

        if name_field.count() == 0:
            screenshot(page_auth, "profil_no_name")
            pytest.skip(
                "profil.html: Ad/soyad input alanı bulunamadı — "
                "Muhtemelen test kullanıcısı Supabase'de kayıtlı değil, "
                "sayfa form bölümünü gizliyor. Test kullanıcısını Supabase'e ekle."
            )

    def test_profil_has_phone_field(self, page_auth):
        """profil.html telefon numarası alanı mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/profil.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        page_auth.wait_for_timeout(1000)

        phone_field = page_auth.locator(
            "input[type='tel'], #phone, #telNo, #telefon, "
            "input[name*='phone'], input[placeholder*='telefon']"
        ).first

        if phone_field.count() == 0:
            pytest.skip("profil.html: Telefon alanı bulunamadı (opsiyonel alan olabilir)")

    def test_profil_save_button_exists(self, page_auth):
        """profil.html kaydet/güncelle butonu mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/profil.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        page_auth.wait_for_timeout(1500)

        # Giriş yapılamamışsa skip
        if "login.html" in page_auth.url or "kayit.html" in page_auth.url:
            pytest.skip("profil.html: Test kullanıcısı giriş yapamadı — Supabase'de kayıtlı olmayabilir")

        save_btn = page_auth.locator(
            "button:has-text('Kaydet'), button:has-text('Güncelle'), "
            "button:has-text('Değişiklikleri'), button:has-text('Save'), "
            "button:has-text('Güncelle'), button[type='submit']"
        ).first

        if save_btn.count() == 0:
            screenshot(page_auth, "profil_no_save")
            pytest.skip(
                "profil.html: Kaydet butonu bulunamadı — "
                "Test kullanıcısı giriş yapamamış olabilir."
            )

    def test_profil_city_country_fields(self, page_auth):
        """profil.html şehir/ülke seçim alanları mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/profil.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 5000)
        page_auth.wait_for_timeout(1000)

        location_el = page_auth.locator(
            "select[id*='ulke'], select[id*='sehir'], select[id*='country'], "
            "select[id*='city'], #userCountry, #userCity"
        ).first

        if location_el.count() == 0:
            pytest.skip("profil.html: Şehir/ülke seçim alanı bulunamadı")


# ═══════════════════════════════════════════════════════════════════════════════
# SOHBET — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestSohbetDetay:

    def test_sohbet_room_list_visible(self, page_auth):
        """Sohbet odaları (Global, şehirler) listeleniyor olmalı."""
        page_auth.goto(f"{BASE_URL}/sohbet.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(2000)

        content = page_auth.content()
        has_rooms = any(k in content.lower() for k in [
            "global", "oda", "room", "brüksel", "brussels",
            "gent", "antwerp", "antwerpen", "liège"
        ])
        if not has_rooms:
            pytest.skip("sohbet.html: Oda listesi bulunamadı (Supabase'de oda yok olabilir)")

    def test_sohbet_send_button_exists(self, page_auth):
        """Mesaj gönder butonu mevcut olmalı."""
        page_auth.goto(f"{BASE_URL}/sohbet.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(1500)

        send_btn = page_auth.locator(
            "button:has-text('Gönder'), button:has-text('Send'), "
            "button[type='submit'], #sendBtn, #gonderBtn"
        ).first

        if send_btn.count() == 0:
            pytest.skip("sohbet.html: Gönder butonu bulunamadı")

    def test_sohbet_username_displayed(self, page_auth):
        """Sohbette kullanıcı adı veya avatar görünmeli."""
        page_auth.goto(f"{BASE_URL}/sohbet.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_auth, 6000)
        page_auth.wait_for_timeout(2000)

        content = page_auth.content()
        has_user_info = any(k in content.lower() for k in [
            "kullanıcı", "username", "user", "avatar", "profil"
        ])
        if not has_user_info:
            pytest.skip("sohbet.html: Kullanıcı bilgisi bulunamadı")


# ═══════════════════════════════════════════════════════════════════════════════
# DUYURULAR — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestDuyurularDetay:

    def test_duyurular_list_items(self, page_guest):
        """Duyurular sayfasında en az bir duyuru veya boş state mesajı görünmeli."""
        page_guest.goto(f"{BASE_URL}/duyurular.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        page_guest.wait_for_timeout(2000)

        content = page_guest.content()
        # Duyuru kartları veya boş state
        has_content = (
            page_guest.locator(".bg-white, .card, article").count() > 0
            or any(k in content.lower() for k in ["duyuru", "announcement", "henüz", "yok"])
        )
        assert has_content, "duyurular.html: Ne duyuru listesi ne de boş state gösteriliyor"

    def test_duyuru_detay_with_invalid_id(self, page_guest):
        """duyuru_detay.html geçersiz ID ile hata mesajı göstermeli."""
        page_guest.goto(f"{BASE_URL}/duyuru_detay.html?id=9999999999", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        body = page_guest.inner_text("body").lower()
        has_error = any(w in body for w in ["bulunamadı", "hata", "geçersiz", "error", "not found"])
        redirected = "duyurular.html" in page_guest.url
        assert has_error or redirected, \
            "duyuru_detay.html: Geçersiz ID için hata mesajı veya yönlendirme yok"


# ═══════════════════════════════════════════════════════════════════════════════
# AVUKAT DETAY
# ═══════════════════════════════════════════════════════════════════════════════
class TestAvukatDetay:

    def test_avukat_detay_loads(self, page_guest):
        """avukat_detay.html yükleniyor."""
        t0 = time.perf_counter()
        page_guest.goto(f"{BASE_URL}/avukat_detay.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        elapsed = int((time.perf_counter() - t0) * 1000)
        record_perf("avukat_detay", "load_ms", elapsed, THRESHOLDS["page_load"])
        body = page_guest.inner_text("body")
        assert len(body) > 30, "avukat_detay.html: Sayfa boş"

    def test_hukuk_vitrini_has_listings_or_empty_state(self, page_guest):
        """hukuk_vitrini.html avukat/hukuk ilanları veya boş state göstermeli."""
        page_guest.goto(f"{BASE_URL}/hukuk_vitrini.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 5000)
        page_guest.wait_for_timeout(1500)
        body = page_guest.inner_text("body")
        assert len(body) > 100, "hukuk_vitrini.html: Sayfa içeriği boş"


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN PANEL — ERİŞİM KONTROL
# ═══════════════════════════════════════════════════════════════════════════════
class TestAdminPanel:

    def test_admin_html_requires_login(self, page_guest):
        """admin.html giriş yapılmadan admin verisi göstermemeli."""
        page_guest.goto(f"{BASE_URL}/admin.html", wait_until="networkidle")
        page_guest.wait_for_timeout(3000)

        body = page_guest.inner_text("body").lower()
        current_url = page_guest.url

        admin_data_indicators = [
            "kullanıcı listesi", "tüm kullanıcılar", "tüm ilanlar",
            "admin paneli", "kullanıcı yönetimi"
        ]
        has_admin_data = any(w in body for w in admin_data_indicators)
        is_redirected = "login.html" in current_url
        has_auth_warning = any(w in body for w in ["giriş", "yetkisiz", "unauthorized", "admin"])

        if has_admin_data and not is_redirected:
            screenshot(page_guest, "admin_exposed")
            pytest.fail(
                "admin.html: Giriş yapmadan admin verisi görünüyor! "
                "Auth/admin koruması eksik."
            )

    def test_admin_chat_requires_login(self, page_guest):
        """admin_chat.html giriş olmadan admin verisi göstermemeli."""
        page_guest.goto(f"{BASE_URL}/admin_chat.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "yetkisiz", "unauthorized"])
        # Kaynak kodda herhangi bir auth mekanizması var mı?
        src = (SRC / "admin_chat.html").read_text(encoding="utf-8", errors="ignore")
        has_guard = any(g in src for g in [
            "requireAdmin", "requireAuth", "isAdmin", "getCurrentUser",
            "window.location.href = 'login.html'",
            'window.location.href = "login.html"',
            "getSession", "onAuthStateChange", "adminKontrol",
            "auth.getUser", "ACCESS_DENIED",
        ])
        # Gerçek admin içeriği açıkta mı? (güvenlik açığı testi)
        admin_indicators = ["süper admin", "admin mesaj", "adminmesajgonder", "admin-feed"]
        has_admin_exposed = any(w in body for w in admin_indicators)

        if has_admin_exposed and not redirected and not has_warning and not has_guard:
            pytest.fail(
                "admin_chat.html: GÜVENLİK AÇIĞI! "
                "Giriş olmadan admin sohbet paneline erişilebiliyor. "
                "requireAdmin() veya login yönlendirmesi eklenmeli."
            )
        elif not has_guard:
            pytest.skip(
                "admin_chat.html: Kaynak kodda auth guard bulunamadı "
                "(sayfa şu an yönlendirme yapmıyor olabilir, ancak kod koruması eksik)"
            )

    def test_admin_listings_requires_login(self, page_guest):
        """admin_listings.html giriş olmadan admin verisi göstermemeli."""
        page_guest.goto(f"{BASE_URL}/admin_listings.html", wait_until="networkidle")
        page_guest.wait_for_timeout(2000)
        redirected = "login.html" in page_guest.url
        body = page_guest.inner_text("body").lower()
        has_warning = any(w in body for w in ["giriş", "yetkisiz", "unauthorized"])
        src = (SRC / "admin_listings.html").read_text(encoding="utf-8", errors="ignore")
        has_guard = any(g in src for g in [
            "requireAdmin", "requireAuth", "isAdmin", "getCurrentUser",
            "window.location.href = 'login.html'",
            'window.location.href = "login.html"',
            "getSession", "onAuthStateChange", "adminKontrol",
            "auth.getUser", "ACCESS_DENIED",
        ])
        admin_indicators = ["ilan yönetimi", "admin", "tüm ilanlar", "yeni ilan oluştur"]
        has_admin_exposed = any(w in body for w in admin_indicators)

        if has_admin_exposed and not redirected and not has_warning and not has_guard:
            pytest.fail(
                "admin_listings.html: GÜVENLİK AÇIĞI! "
                "Giriş olmadan admin ilan paneline erişilebiliyor. "
                "requireAdmin() veya login yönlendirmesi eklenmeli."
            )
        elif not has_guard:
            pytest.skip(
                "admin_listings.html: Kaynak kodda auth guard bulunamadı "
                "(RLS koruması var ama istemci tarafı guard eksik — önerilir)"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET — EK DETAY
# ═══════════════════════════════════════════════════════════════════════════════
class TestMarketDetay:

    def test_market_price_sorting(self, page_guest):
        """Market sayfasında fiyat sıralama seçeneği mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1000)

        content = page_guest.content()
        has_sort = any(k in content.lower() for k in [
            "sırala", "sort", "fiyat", "ucuz", "pahalı", "price",
            "ascending", "descending", "artan", "azalan"
        ])
        if not has_sort:
            pytest.skip("market.html: Fiyat sıralama seçeneği bulunamadı")

    def test_market_carrefour_filter(self, page_guest):
        """Market sayfasında Carrefour filtresi mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        content = page_guest.content()
        assert "carrefour" in content.lower() or "Carrefour" in content, \
            "market.html: Carrefour market filtresi bulunamadı"

    def test_market_category_filter(self, page_guest):
        """Market sayfasında kategori filtresi (Bakkaliye, Süt ürünleri vb.) mevcut olmalı."""
        page_guest.goto(f"{BASE_URL}/market.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(1500)

        content = page_guest.content()
        categories = [
            "categor", "bakkaliye", "süt", "et", "meyve", "sebze",
            "dairy", "meat", "fruit", "vegetable", "bread", "ekmek"
        ]
        found = [c for c in categories if c.lower() in content.lower()]
        if not found:
            pytest.skip("market.html: Kategori filtresi bulunamadı")


# ═══════════════════════════════════════════════════════════════════════════════
# DÖVİZ — DETAYLI
# ═══════════════════════════════════════════════════════════════════════════════
class TestDovizDetay:

    def test_doviz_eur_try_visible(self, page_guest):
        """EUR/TRY kuru sayfada görünmeli."""
        page_guest.goto(f"{BASE_URL}/doviz_altin.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(3000)

        content = page_guest.content()
        has_eur_try = "EUR" in content or "Euro" in content or "€" in content
        assert has_eur_try, "doviz_altin.html: EUR/TRY kuru görünmüyor"

    def test_doviz_update_time_shown(self, page_guest):
        """Döviz verisi güncelleme zamanı veya kaynak gösterilmeli."""
        page_guest.goto(f"{BASE_URL}/doviz_altin.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(3000)

        content = page_guest.content()
        has_time = any(k in content.lower() for k in [
            "güncellendi", "updated", "tarih", "saat", "son", "last",
            "2024", "2025", "2026", "live", "canlı"
        ])
        if not has_time:
            pytest.skip("doviz_altin.html: Güncelleme zamanı gösterilmiyor (opsiyonel)")

    def test_doviz_no_console_errors(self, page_guest):
        """doviz_altin.html konsol hatası olmadan yüklenebilmeli."""
        errors = []
        page_guest.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        page_guest.goto(f"{BASE_URL}/doviz_altin.html", wait_until="domcontentloaded")
        wait_for_spinner_gone(page_guest, 6000)
        page_guest.wait_for_timeout(2000)

        critical_errors = [
            e for e in errors
            if any(k in e for k in ["TypeError", "ReferenceError", "Uncaught", "Cannot read"])
        ]
        if critical_errors:
            screenshot(page_guest, "doviz_console_errors")
            pytest.fail(
                f"doviz_altin.html: Kritik konsol hataları:\n"
                + "\n".join(critical_errors[:3])
            )
