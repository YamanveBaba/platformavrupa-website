// Platform Avrupa — Push Bildirim Aboneliği
// index.html ve diğer sayfalara defer ile eklenir

const PA_VAPID_PUBLIC = 'BFry9OTqrb_XYsh1c19Vo2jgd5CQY8D6jXttcDNiYg5iaiXWjnipzP6UcNkx1oRaTsfilUERK9zRekMGpicTsjM';

function _vapidKey(b64url) {
    const pad  = '='.repeat((4 - b64url.length % 4) % 4);
    const b64  = (b64url + pad).replace(/-/g, '+').replace(/_/g, '/');
    const raw  = atob(b64);
    return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

async function _saveSub(sub) {
    if (!window.sb) return;
    const s = sub.toJSON();
    let country = null, city = null, userId = null;
    try {
        const { data: { session } } = await sb.auth.getSession();
        if (session?.user) {
            userId = session.user.id;
            const { data: p } = await sb.from('profiles').select('country,city').eq('id', userId).single();
            country = p?.country || null;
            city    = p?.city    || null;
        }
    } catch(e) {}

    try {
        await sb.from('push_subscriptions').upsert({
            user_id:    userId,
            endpoint:   s.endpoint,
            p256dh:     s.keys.p256dh,
            auth:       s.keys.auth,
            country,
            city,
            updated_at: new Date().toISOString(),
        }, { onConflict: 'endpoint' });
    } catch(e) {}
}

function _showBanner() {
    if (localStorage.getItem('pa_push_dismissed') || document.getElementById('pa-push-banner')) return;
    const d = document.createElement('div');
    d.id = 'pa-push-banner';
    d.innerHTML = `
        <div style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
            background:#1e293b;color:#fff;padding:14px 18px;border-radius:18px;
            display:flex;align-items:center;gap:12px;z-index:99999;
            box-shadow:0 8px 40px rgba(0,0,0,0.35);max-width:440px;width:92%;
            animation:slideUp .35s ease">
            <span style="font-size:22px;flex-shrink:0">🔔</span>
            <div style="flex:1;min-width:0">
                <div style="font-weight:700;font-size:13px;margin-bottom:2px">Bildirimlerden haberdar ol</div>
                <div style="color:#94a3b8;font-size:11px;line-height:1.4">Yeni ilanlar, sınır yoğunluğu ve önemli duyurular</div>
            </div>
            <button onclick="paBildirimIzin()" style="background:#6366f1;color:#fff;border:none;
                padding:8px 14px;border-radius:10px;font-weight:700;font-size:12px;
                cursor:pointer;white-space:nowrap;flex-shrink:0">İzin Ver</button>
            <button onclick="paBildirimReddet()" style="background:none;border:none;
                color:#64748b;cursor:pointer;font-size:18px;padding:4px;flex-shrink:0;line-height:1">✕</button>
        </div>
        <style>@keyframes slideUp{from{transform:translateX(-50%) translateY(80px);opacity:0}to{transform:translateX(-50%) translateY(0);opacity:1}}</style>`;
    document.body.appendChild(d);
}

async function paBildirimIzin() {
    document.getElementById('pa-push-banner')?.remove();
    try {
        const perm = await Notification.requestPermission();
        if (perm !== 'granted') { localStorage.setItem('pa_push_dismissed','1'); return; }
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: _vapidKey(PA_VAPID_PUBLIC),
        });
        await _saveSub(sub);
    } catch(e) { console.warn('Push abonelik hatası:', e); }
}

function paBildirimReddet() {
    document.getElementById('pa-push-banner')?.remove();
    localStorage.setItem('pa_push_dismissed', '1');
}

async function _initPush() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    if (Notification.permission === 'denied') return;

    try {
        const reg = await navigator.serviceWorker.register('/sw.js');
        const existing = await reg.pushManager.getSubscription();
        if (existing) { await _saveSub(existing); return; }
        if (Notification.permission === 'granted') {
            const sub = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: _vapidKey(PA_VAPID_PUBLIC),
            });
            await _saveSub(sub);
        } else {
            setTimeout(_showBanner, 5000);
        }
    } catch(e) { console.warn('SW hatası:', e); }
}

window.paBildirimIzin    = paBildirimIzin;
window.paBildirimReddet  = paBildirimReddet;

document.addEventListener('DOMContentLoaded', _initPush);
