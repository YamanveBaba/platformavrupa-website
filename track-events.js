// Custom Analytics Events — Platform Avrupa
(function () {
  if (typeof gtag === 'undefined') return;

  // Href → modül adı haritası
  var MODULE_NAMES = {
    'is_vitrini': 'İş İlanları',
    'emlak_vitrini': 'Emlak',
    'vasita_vitrini': 'Vasıta',
    'hizmet_vitrini': 'Hizmetler',
    'esya_vitrini': 'İkinci El',
    'yemek_vitrini': 'Mutfak',
    'market': 'Market Fiyatları',
    'doviz_altin': 'Döviz & Altın',
    'sila_yolu': 'Sıla Yolu',
    'yol_arkadasi': 'Yol Arkadaşı',
    'kargo_emanet': 'Kargo & Emanet',
    'yol_yardim': 'Yol Yardım',
    'ucak_bileti': 'Uçak Bileti',
    'otel_rezervasyon': 'Otel',
    'arac_kiralama': 'Araç Kiralama',
    'tatil_paketleri': 'Tatil Paketleri',
    'saglik_turizmi': 'Sağlık Turizmi',
    'hukuk_vitrini': 'Hukuk & Danışma',
    'akademi': 'Akademi',
    'sohbet': 'Sohbet',
    'duyurular': 'Duyurular',
    'ilan_giris': 'İlan Ver',
    'login': 'Giriş Yap',
    'is_vitrini': 'İş İlanları'
  };

  function moduleFromHref(href) {
    if (!href) return null;
    var clean = href.replace(/^.*\//, '').replace(/\.html.*$/, '').replace(/[?#].*$/, '');
    return MODULE_NAMES[clean] || clean || null;
  }

  // 1. Modül tıklama takibi — tüm ana linkler
  document.addEventListener('click', function (e) {
    var el = e.target.closest('a[href]');
    if (!el) return;
    var href = el.getAttribute('href') || '';
    var mod = moduleFromHref(href);
    if (!mod) return;

    // Sadece .html sayfaları veya yerel bağlantılar
    if (href.startsWith('http') && !href.includes('platformavrupa.com')) return;

    gtag('event', 'module_click', {
      module_name: mod,
      page_location: window.location.pathname
    });
  }, true);

  // 2. İlan Ver CTA takibi (ayrıca)
  document.addEventListener('click', function (e) {
    var el = e.target.closest('a[href*="ilan_giris"]');
    if (el) {
      gtag('event', 'cta_click', { cta_label: 'İlan Ver' });
    }
  }, true);

  // 3. Scroll derinliği takibi (25% / 50% / 75% / 100%)
  var scrollMilestones = { 25: false, 50: false, 75: false, 100: false };
  function onScroll() {
    var scrolled = window.scrollY + window.innerHeight;
    var total = document.documentElement.scrollHeight;
    var pct = Math.round((scrolled / total) * 100);
    [25, 50, 75, 100].forEach(function (m) {
      if (!scrollMilestones[m] && pct >= m) {
        scrollMilestones[m] = true;
        gtag('event', 'scroll_depth', { depth_percent: m, page: window.location.pathname });
      }
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });

  // 4. Sayfa görüntülenme süresi (kullanıcı ayrılırken)
  var startTime = Date.now();
  function sendEngagement() {
    var seconds = Math.round((Date.now() - startTime) / 1000);
    if (seconds < 2) return;
    gtag('event', 'page_engagement', {
      time_on_page_seconds: seconds,
      page: window.location.pathname
    });
  }
  window.addEventListener('beforeunload', sendEngagement);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') sendEngagement();
  });
})();
