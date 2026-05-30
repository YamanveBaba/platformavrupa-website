// Platform Avrupa — Service Worker v1
// Push bildirimleri alır ve gösterir

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));

self.addEventListener('push', function(event) {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch(e) {}

    const title   = data.title  || 'Platform Avrupa';
    const options = {
        body:    data.body   || '',
        icon:    '/favicon.ico',
        badge:   '/favicon.ico',
        tag:     data.tag    || 'pa-bildirim',
        data:  { url: data.url || '/' },
        vibrate: [200, 100, 200],
        requireInteraction: false,
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data?.url || '/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
            for (const c of list) {
                if (c.url === url && 'focus' in c) return c.focus();
            }
            if (clients.openWindow) return clients.openWindow(url);
        })
    );
});
