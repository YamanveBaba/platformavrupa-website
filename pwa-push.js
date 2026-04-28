// PWA Push Bildirimleri — Abone ol / çık
const VAPID_PUBLIC_KEY = 'BJc9U12xVx-72F4aY6cevEOaom7Vanefxmzlj7hD7JbJjx9RwcAubXLxRgA0YLMEd4XFqB3_0BSYPWKNrP7FMxw';

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
}

async function getPushSubscription() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return null;
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

async function subscribeToPush() {
  try {
    const reg = await navigator.serviceWorker.ready;
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return null;

    const existing = await reg.pushManager.getSubscription();
    if (existing) return existing;

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
    });
    return sub;
  } catch (e) {
    console.error('Push subscribe hata:', e);
    return null;
  }
}

async function saveSubscription(sub) {
  if (!sub || !window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) return false;
  const j = sub.toJSON();
  const res = await fetch(`${window.SUPABASE_URL}/rest/v1/push_subscriptions`, {
    method: 'POST',
    headers: {
      'apikey': window.SUPABASE_ANON_KEY,
      'Authorization': `Bearer ${window.SUPABASE_ANON_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': 'resolution=ignore-duplicates'
    },
    body: JSON.stringify({
      endpoint: j.endpoint,
      p256dh: j.keys.p256dh,
      auth: j.keys.auth
    })
  });
  return res.ok || res.status === 409;
}

async function unsubscribeFromPush() {
  const sub = await getPushSubscription();
  if (!sub) return;
  await sub.unsubscribe();
  // Supabase'den de sil
  if (window.SUPABASE_URL && window.SUPABASE_ANON_KEY) {
    await fetch(`${window.SUPABASE_URL}/rest/v1/push_subscriptions?endpoint=eq.${encodeURIComponent(sub.endpoint)}`, {
      method: 'DELETE',
      headers: {
        'apikey': window.SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${window.SUPABASE_ANON_KEY}`
      }
    });
  }
}

// Buton durumunu güncelle
async function updatePushButton(btn) {
  if (!btn) return;
  if (!('Notification' in window) || !('PushManager' in window)) {
    btn.style.display = 'none';
    return;
  }
  const sub = await getPushSubscription();
  if (sub) {
    btn.innerHTML = '<i class="fa-solid fa-bell-slash mr-1.5"></i><span class="hidden sm:inline">Bildirim Kapat</span>';
    btn.title = 'Bildirimleri kapat';
    btn.dataset.subscribed = '1';
  } else {
    btn.innerHTML = '<i class="fa-solid fa-bell mr-1.5"></i><span class="hidden sm:inline">Bildirimler</span>';
    btn.title = 'Yeni ilan bildirimlerini aç';
    btn.dataset.subscribed = '0';
  }
}

// Buton tıklaması
async function handlePushButton(btn) {
  if (btn.dataset.subscribed === '1') {
    await unsubscribeFromPush();
  } else {
    const sub = await subscribeToPush();
    if (sub) await saveSubscription(sub);
  }
  await updatePushButton(btn);
}

// Sayfa yüklenince başlat
document.addEventListener('DOMContentLoaded', async () => {
  const btn = document.getElementById('pushBtn');
  if (!btn) return;
  await updatePushButton(btn);
  btn.addEventListener('click', () => handlePushButton(btn));
});
