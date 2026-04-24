const CACHE_NAME = 'platform-avrupa-v5';
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

// Kurulum: Yeni cache aç, hemen aktive et
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    }).then(() => self.skipWaiting())
  );
});

// Aktive: Eski cache versiyonlarını sil
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
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

  // HTML sayfaları: her zaman önce ağdan çek (stale cache sorunu yaşanmasın)
  if (request.destination === 'document' ||
      requestUrl.pathname.endsWith('.html') ||
      requestUrl.pathname === '/' ||
      requestUrl.pathname === '') {
    event.respondWith(
      fetch(request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        return response;
      }).catch(() => caches.match(request))
    );
    return;
  }

  // JS/CSS/resimler: cache first
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

// ── Push Bildirimleri (PWA) ───────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'Platform Avrupa', {
      body: data.body || 'Yeni bildirim var',
      icon: '/logo.png',
      badge: '/logo.png',
      tag: data.tag || 'pa-notif',
      data: { url: data.url || '/admin.html' }
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((list) => {
      for (const client of list) {
        if (client.url.includes(event.notification.data.url) && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(event.notification.data.url || '/admin.html');
    })
  );
});