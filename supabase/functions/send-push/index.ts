// Supabase Edge Function: send-push
// Tüm abone cihazlara web push bildirimi gönderir.
// Çağrı: POST /functions/v1/send-push  { title, body, url }
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const VAPID_PRIVATE_KEY = Deno.env.get('VAPID_PRIVATE_KEY')!;
const VAPID_PUBLIC_KEY  = 'BJc9U12xVx-72F4aY6cevEOaom7Vanefxmzlj7hD7JbJjx9RwcAubXLxRgA0YLMEd4XFqB3_0BSYPWKNrP7FMxw';
const VAPID_SUBJECT     = 'mailto:info@platformavrupa.com';

function b64ToUint8(b64: string): Uint8Array {
  const pad = '='.repeat((4 - b64.length % 4) % 4);
  const bin = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(bin, c => c.charCodeAt(0));
}

async function importPrivateKey(b64: string): Promise<CryptoKey> {
  const raw = b64ToUint8(b64);
  // PKCS8 wrapper for P-256 private key
  const pkcs8Header = new Uint8Array([
    0x30,0x41,0x02,0x01,0x00,0x30,0x13,0x06,0x07,0x2a,0x86,0x48,0xce,0x3d,0x02,
    0x01,0x06,0x08,0x2a,0x86,0x48,0xce,0x3d,0x03,0x01,0x07,0x04,0x27,0x30,0x25,
    0x02,0x01,0x01,0x04,0x20
  ]);
  const pkcs8 = new Uint8Array(pkcs8Header.length + raw.length);
  pkcs8.set(pkcs8Header); pkcs8.set(raw, pkcs8Header.length);
  return crypto.subtle.importKey('pkcs8', pkcs8, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
}

async function makeJWT(endpoint: string): Promise<string> {
  const url = new URL(endpoint);
  const aud = `${url.protocol}//${url.host}`;
  const exp = Math.floor(Date.now() / 1000) + 12 * 3600;

  const header  = btoa(JSON.stringify({ typ: 'JWT', alg: 'ES256' })).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
  const payload = btoa(JSON.stringify({ aud, exp, sub: VAPID_SUBJECT })).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
  const msg     = `${header}.${payload}`;

  const key = await importPrivateKey(VAPID_PRIVATE_KEY);
  const sig  = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, key, new TextEncoder().encode(msg));
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
  return `${msg}.${sigB64}`;
}

async function sendPush(sub: { endpoint: string; p256dh: string; auth: string }, payload: string): Promise<boolean> {
  const jwt = await makeJWT(sub.endpoint);
  const res = await fetch(sub.endpoint, {
    method: 'POST',
    headers: {
      'Authorization': `vapid t=${jwt},k=${VAPID_PUBLIC_KEY}`,
      'Content-Type': 'application/octet-stream',
      'Content-Encoding': 'aes128gcm',
      'TTL': '86400',
    },
    body: new TextEncoder().encode(payload),
  });
  return res.status === 201 || res.status === 200;
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization,content-type' } });
  }

  const authHeader = req.headers.get('Authorization') || '';
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

  // Sadece servis rolü veya internal çağrıya izin ver
  if (!authHeader.includes(serviceKey) && req.headers.get('x-internal-token') !== Deno.env.get('INTERNAL_TOKEN')) {
    return new Response('Unauthorized', { status: 401 });
  }

  const { title, body, url } = await req.json();

  const sb = createClient(Deno.env.get('SUPABASE_URL')!, serviceKey);
  const { data: subs, error } = await sb.from('push_subscriptions').select('endpoint,p256dh,auth');

  if (error || !subs?.length) {
    return new Response(JSON.stringify({ sent: 0, error: error?.message }), { status: 200 });
  }

  const payload = JSON.stringify({ title: title || 'Platform Avrupa', body, url: url || '/', tag: 'pa-notif' });

  let sent = 0, failed = 0;
  for (const sub of subs) {
    try {
      const ok = await sendPush(sub, payload);
      if (ok) sent++; else failed++;
    } catch { failed++; }
  }

  return new Response(JSON.stringify({ sent, failed, total: subs.length }), {
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
  });
});
