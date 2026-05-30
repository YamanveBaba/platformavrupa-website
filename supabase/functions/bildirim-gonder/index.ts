// Supabase Edge Function: bildirim-gonder
// Web Push ile hedefli bildirim gönderir.
// POST /functions/v1/bildirim-gonder
// Body: { title, body, url?, hedef: 'herkese'|'ulke'|'sehir'|'bireysel', ulke?, sehir?, user_id? }
import webpush from 'npm:web-push';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const VAPID_PUBLIC  = Deno.env.get('VAPID_PUBLIC_KEY')!;
const VAPID_PRIVATE = Deno.env.get('VAPID_PRIVATE_KEY')!;

webpush.setVapidDetails('mailto:admin@platformavrupa.com', VAPID_PUBLIC, VAPID_PRIVATE);

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization,content-type' } });
  }
  if (req.method !== 'POST') return new Response('Method Not Allowed', { status: 405 });

  const sb = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const { title, body, url = '/', hedef = 'herkese', ulke, sehir, user_id } = await req.json();
  if (!title || !body) return new Response(JSON.stringify({ error: 'title ve body zorunlu' }), { status: 400 });

  let query = sb.from('push_subscriptions').select('endpoint, p256dh, auth');
  if      (hedef === 'ulke'      && ulke)    query = query.eq('country', ulke);
  else if (hedef === 'sehir'     && sehir)   query = query.eq('city', sehir);
  else if (hedef === 'bireysel'  && user_id) query = query.eq('user_id', user_id);

  const { data: subs, error } = await query;
  if (error) return new Response(JSON.stringify({ error: error.message }), { status: 500 });

  const payload   = JSON.stringify({ title, body, url });
  let gonderildi  = 0, hata = 0;
  const gecersizEndpoints: string[] = [];

  for (const sub of (subs || [])) {
    try {
      await webpush.sendNotification(
        { endpoint: sub.endpoint, keys: { p256dh: sub.p256dh, auth: sub.auth } },
        payload
      );
      gonderildi++;
    } catch (e: any) {
      hata++;
      if (e.statusCode === 410 || e.statusCode === 404) {
        gecersizEndpoints.push(sub.endpoint);
      }
    }
  }

  // Süresi dolan abonelikleri temizle
  for (const ep of gecersizEndpoints) {
    await sb.from('push_subscriptions').delete().eq('endpoint', ep);
  }

  return new Response(JSON.stringify({
    ok: true, toplam: subs?.length || 0, gonderildi, hata, temizlenen: gecersizEndpoints.length
  }), { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } });
});
