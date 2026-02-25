const CACHE_NAME = 'platform-avrupa-v1';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './ilan_giris.html',
  './genel_veriler.js',
  './config.js',
  './vasita_vitrini.html',
  './emlak_vitrini.html',
  './is_vitrini.html',
  './hizmet_vitrini.html',
  './esya_vitrini.html',
  './yemek_vitrini.html',
  './hukuk_vitrini.html',
  './sila_yolu.html',
  './akademi.html',
  './logo.png'
];

// Kurulum: Dosyaları önbelleğe al
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Çalıştırma: Önce önbellekten, yoksa internetten çek
// NOT: API isteklerini ve external linkleri (market broşür siteleri) bypass et
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const requestUrl = new URL(request.url);

  // Supabase Edge Function URL'ini tamamen bypass et (service worker hiç müdahale etmesin)
  const supabaseEdgeFunctionHost = 'vhietrqljahdmloazgpp.supabase.co';
  if (requestUrl.hostname === supabaseEdgeFunctionHost && requestUrl.pathname.startsWith('/functions/v1/')) {
    // Service worker hiç intercept etmesin, direkt fetch'e bırak (CORS için gerekli)
    event.respondWith(fetch(request));
    return;
  }

  // Harici API'leri ve CORS proxy'leri bypass et
  const externalApiHosts = [
    'api.allorigins.win',
    'api.metals.live',
    'freegoldapi.com',
    'www.tcmb.gov.tr',
    'api.exchangerate-api.com',
    'api.frankfurter.app',
    'corsproxy.io',
    'api.codetabs.com',
    'apiportal.vakifbank.com.tr',
    'anlikaltinfiyatlari.com' // Edge Function içinde scraping yapılıyor
  ];

  if (externalApiHosts.some(host => requestUrl.hostname.includes(host))) {
    event.respondWith(fetch(request));
    return;
  }

  // Market broşür agregator sitelerini bypass et (normal link navigasyonu için)
  const brochureSites = [
    'kaufda.de',
    'wogibtswas.at',
    'folder.be',
    'reclamefolder.nl',
    'bonial.fr',
    'tiendeo.com',
    'tiendeo.it',
    'tiendeo.pt',
    'tiendeo.pl',
    'tiendeo.cz',
    'tiendeo.hu',
    'tiendeo.ro',
    'tiendeo.bg',
    'tiendeo.gr',
    'tiendeo.hr',
    'tiendeo.si',
    'tiendeo.sk',
    'tiendeo.ch',
    'tiendeo.se',
    'tiendeo.no',
    'tiendeo.fi',
    'tiendeo.ee',
    'tiendeo.lv',
    'tiendeo.lt',
    'tiendeo.lu',
    'tiendeo.ie',
    'tiendeo.co.uk',
    'tilbudsavis.dk',
    'aktuelkatolog.com'
  ];

  if (brochureSites.some(site => requestUrl.hostname.includes(site))) {
    event.respondWith(fetch(request));
    return;
  }

  // Sadece kendi origin'imizdeki dosyaları cache'le
  if (requestUrl.origin === location.origin) {
    event.respondWith(
      caches.match(request).then((response) => {
        return response || fetch(request);
      })
    );
  } else {
    // Diğer tüm harici istekleri direkt ağdan çek
    event.respondWith(fetch(request));
  }
});