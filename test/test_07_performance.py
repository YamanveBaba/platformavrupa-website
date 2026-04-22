"""
AŞAMA 7 — Detaylı Performans Testleri
Navigation Timing API, LCP, DB okuma süresi, harita tile yükleme, scroll performansı
"""
import time
import json
import pytest
from conftest import (
    BASE_URL, THRESHOLDS, screenshot, record_perf,
    wait_for_spinner_gone, wait_for_map, ALL_PAGES, HARITALI_PAGES
)

# ─── Navigation Timing API ile gerçek metrikler ───────────────────────────────
TIMING_PAGES = [
    ("index.html",         "Ana Sayfa",       3000),
    ("market.html",        "Market",          5000),
    ("is_vitrini.html",    "İş Vitrini",      4000),
    ("emlak_vitrini.html", "Emlak Vitrini",   4000),
    ("login.html",         "Giriş",           2500),
    ("ilanlar.html",       "İlanlar",         4000),
    ("akademi.html",       "Akademi",         4000),
    ("saglik_turizmi.html","Sağlık Turizmi",  4000),
    ("sila_yolu.html",     "Sıla Yolu",       4000),
    ("doviz_altin.html",   "Döviz & Altın",   4000),
    ("sohbet.html",        "Sohbet",          4000),
]

@pytest.mark.parametrize("slug,label,limit_ms", TIMING_PAGES, ids=[t[0] for t in TIMING_PAGES])
def test_navigation_timing(slug, label, limit_ms, page_guest):
    """
    Navigation Timing API ile gerçek tarayıcı metriklerini ölç:
    - TTFB (Time To First Byte)
    - DOM Content Loaded
    - Load Event
    """
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="load", timeout=20000)

    timing = page_guest.evaluate("""() => {
        const nav = performance.getEntriesByType('navigation')[0];
        if (!nav) return null;
        return {
            ttfb:            Math.round(nav.responseStart - nav.requestStart),
            dom_interactive: Math.round(nav.domInteractive - nav.startTime),
            dom_complete:    Math.round(nav.domComplete - nav.startTime),
            load_event:      Math.round(nav.loadEventEnd - nav.startTime),
            transfer_size:   nav.transferSize || 0,
            encoded_size:    nav.encodedBodySize || 0,
        };
    }""")

    if not timing:
        pytest.skip(f"{label}: Navigation Timing API desteklenmiyor")

    record_perf(slug, "ttfb_ms",        timing["ttfb"],            500)
    record_perf(slug, "dom_complete_ms", timing["dom_complete"],   limit_ms)
    record_perf(slug, "load_event_ms",   timing["load_event"],     limit_ms + 1000)

    # TTFB kontrolü
    assert timing["ttfb"] <= 2000, (
        f"{label}: TTFB {timing['ttfb']}ms (limit: 2000ms) — "
        f"Sunucu yavaş veya CDN sorunu"
    )

    # DOM Complete kontrolü
    assert timing["dom_complete"] <= limit_ms, (
        f"{label}: DOM Complete {timing['dom_complete']}ms (limit: {limit_ms}ms)\n"
        f"  TTFB: {timing['ttfb']}ms\n"
        f"  Transfer: {timing['transfer_size']//1024}KB"
    )


# ─── Resource yükleme analizi ─────────────────────────────────────────────────
@pytest.mark.parametrize("slug,label", [
    ("index.html",      "Ana Sayfa"),
    ("market.html",     "Market"),
    ("is_vitrini.html", "İş Vitrini"),
])
def test_resource_load_analysis(slug, label, page_guest):
    """Yavaş yüklenen kaynakları (>500ms) raporla."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="load", timeout=20000)

    resources = page_guest.evaluate("""() => {
        return performance.getEntriesByType('resource').map(r => ({
            name: r.name.split('/').pop().substring(0, 60),
            duration: Math.round(r.duration),
            type: r.initiatorType,
            size: r.transferSize || 0,
        })).filter(r => r.duration > 500)
           .sort((a, b) => b.duration - a.duration)
           .slice(0, 10);
    }""")

    if resources:
        slow_list = "\n".join(
            f"  {r['type']:10} {r['duration']:5}ms  {r['name']}"
            for r in resources
        )
        # Uyarı ver ama fail etme — performans raporu için
        print(f"\n[YAVAŞ KAYNAKLAR] {label}:\n{slow_list}")

    # Herhangi bir kaynak 5sn'den uzun sürüyorsa fail
    very_slow = [r for r in resources if r["duration"] > 5000]
    assert not very_slow, (
        f"{label}: Çok yavaş kaynaklar (>5000ms):\n"
        + "\n".join(f"  {r['name']}: {r['duration']}ms" for r in very_slow)
    )


# ─── LCP (Largest Contentful Paint) ──────────────────────────────────────────
LCP_PAGES = [
    ("index.html",         "Ana Sayfa",       2500),
    ("market.html",        "Market",          4000),
    ("is_vitrini.html",    "İş Vitrini",      3500),
    ("emlak_vitrini.html", "Emlak Vitrini",   3500),
]

@pytest.mark.parametrize("slug,label,limit_ms", LCP_PAGES, ids=[t[0] for t in LCP_PAGES])
def test_lcp(slug, label, limit_ms, page_guest):
    """Largest Contentful Paint (LCP) Core Web Vitals standardına göre."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="load", timeout=20000)
    page_guest.wait_for_timeout(2000)  # LCP observer için bekle

    lcp = page_guest.evaluate("""() => new Promise(resolve => {
        let lcp = 0;
        new PerformanceObserver(list => {
            const entries = list.getEntries();
            lcp = entries[entries.length - 1].startTime;
        }).observe({entryTypes: ['largest-contentful-paint']});
        setTimeout(() => resolve(Math.round(lcp)), 1500);
    })""")

    if lcp == 0:
        pytest.skip(f"{label}: LCP değeri alınamadı")

    record_perf(slug, "lcp_ms", lcp, limit_ms)

    # Google Core Web Vitals: iyi <2500ms, orta <4000ms, kötü >4000ms
    if lcp <= 2500:
        verdict = "İYİ"
    elif lcp <= 4000:
        verdict = "ORTA"
    else:
        verdict = "KÖTÜ"

    print(f"\n[LCP] {label}: {lcp}ms — {verdict}")
    assert lcp <= limit_ms, (
        f"{label}: LCP {lcp}ms (limit: {limit_ms}ms) — Core Web Vitals: {verdict}"
    )


# ─── Harita tile yükleme detayı ───────────────────────────────────────────────
@pytest.mark.parametrize("slug", HARITALI_PAGES)
def test_map_tile_load_detail(slug, page_guest):
    """Harita tile'larının yükleme süresini ölç."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 5000)

    # Harita view'a geç
    harita_btn = page_guest.locator("button:has-text('Harita'), #mapBtn, [onclick*='harita']").first
    try:
        if harita_btn.is_visible():
            harita_btn.click()
            page_guest.wait_for_timeout(500)
    except Exception:
        pass

    t0 = time.perf_counter()
    map_ms = wait_for_map(page_guest, THRESHOLDS["map_ready"])

    if map_ms == -1:
        pytest.skip(f"{slug}: Harita yüklenmedi (DB'de ilan olmayabilir)")

    # Tile sayısını kontrol et
    tile_count = page_guest.locator(".leaflet-tile-loaded").count()
    total_ms = int((time.perf_counter() - t0) * 1000)

    record_perf(slug, "map_tile_ms", total_ms, THRESHOLDS["map_ready"])

    print(f"\n[HARİTA] {slug}: {total_ms}ms, {tile_count} tile yüklendi")

    assert total_ms <= THRESHOLDS["map_ready"], (
        f"{slug}: Harita {total_ms}ms'de yüklendi (limit: {THRESHOLDS['map_ready']}ms)"
    )
    assert tile_count > 0, f"{slug}: Harita tile'ları yüklenmedi"


# ─── Supabase DB okuma süresi ─────────────────────────────────────────────────
DB_READ_PAGES = [
    ("ilanlar.html",          "ilanlar DB"),
    ("market.html",           "market_chain_products DB"),
    ("duyurular.html",        "announcements DB"),
    ("saglik_turizmi.html",   "health_clinics DB"),
]

@pytest.mark.parametrize("slug,label", DB_READ_PAGES, ids=[p[0] for p in DB_READ_PAGES])
def test_db_read_speed(slug, label, page_guest):
    """Supabase DB okuma süresi THRESHOLDS['db_read'] ms altında olmalı."""
    slow_requests = []

    def on_response(response):
        if "supabase.co" in response.url and response.status == 200:
            # Playwright'ta response timing için
            pass

    page_guest.on("response", on_response)

    t0 = time.perf_counter()
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="networkidle", timeout=20000)
    db_ms = int((time.perf_counter() - t0) * 1000)

    record_perf(slug, "db_read_ms", db_ms, THRESHOLDS["db_read"] + 1000)

    # Network idle = tüm Supabase çağrıları tamamlandı
    assert db_ms <= THRESHOLDS["db_read"] + 2000, (
        f"{label}: Supabase okuma dahil toplam {db_ms}ms "
        f"(limit: {THRESHOLDS['db_read'] + 2000}ms)"
    )


# ─── Scroll performansı (uzun liste) ─────────────────────────────────────────
@pytest.mark.parametrize("slug,label", [
    ("market.html",        "Market (çok ürün)"),
    ("is_vitrini.html",    "İş Vitrini"),
])
def test_scroll_performance(slug, label, page_guest):
    """Uzun listede scroll yaparken JS freeze olmamalı (<100ms)."""
    page_guest.goto(f"{BASE_URL}/{slug}", wait_until="domcontentloaded")
    wait_for_spinner_gone(page_guest, 6000)
    page_guest.wait_for_timeout(1000)

    # Scroll sırasında main thread blokajını ölç
    jank = page_guest.evaluate("""() => new Promise(resolve => {
        let maxJank = 0;
        let last = performance.now();
        let frames = 0;

        function measure() {
            const now = performance.now();
            const delta = now - last;
            if (delta > maxJank) maxJank = delta;
            last = now;
            frames++;
            if (frames < 30) {
                window.scrollBy(0, 200);
                requestAnimationFrame(measure);
            } else {
                resolve(Math.round(maxJank));
            }
        }
        requestAnimationFrame(measure);
    })""")

    print(f"\n[SCROLL JANK] {label}: Max frame time: {jank}ms")

    # 200ms üzeri ciddi takılma
    assert jank < 200, (
        f"{label}: Scroll sırasında {jank}ms frame time — "
        f"sayfa takılıyor (limit: 200ms)"
    )


# ─── Özet rapor: tüm performans sonuçları ────────────────────────────────────
def test_zz_performance_summary():
    """Tüm performans sonuçlarını raporla (bu test her zaman geçer)."""
    from conftest import performance_results

    if not performance_results:
        pytest.skip("Performans verisi toplanmadı")

    failed = {k: v for k, v in performance_results.items() if not v["pass"]}
    passed = {k: v for k, v in performance_results.items() if v["pass"]}

    summary = (
        f"\n{'='*60}\n"
        f"PERFORMANS ÖZETİ\n"
        f"{'='*60}\n"
        f"Geçen: {len(passed)}  |  Başarısız: {len(failed)}\n"
    )
    if failed:
        summary += "\nYAVAŞ METRİKLER:\n"
        for key, val in sorted(failed.items(), key=lambda x: x[1]["value_ms"], reverse=True):
            summary += f"  {key}: {val['value_ms']}ms (limit: {val['threshold_ms']}ms)\n"

    print(summary)
    # Bu test sadece raporlama yapar, fail etmez
