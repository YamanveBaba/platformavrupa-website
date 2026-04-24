/**
 * Platform Avrupa — Telegram Bot Webhook (Cloudflare Worker)
 *
 * Kurulum:
 *   1. Cloudflare Dashboard → Workers → New Worker → Bu kodu yapıştır
 *   2. Settings → Variables → Şu environment variable'ları ekle:
 *      - TELEGRAM_BOT_TOKEN
 *      - TELEGRAM_CHAT_ID   (sadece bu chat ID'den gelen komutlar kabul edilir)
 *      - SUPABASE_URL
 *      - SUPABASE_SERVICE_ROLE_KEY
 *   3. Worker URL'ini kopyala, ardından webhook kaydı için terminalde şunu çalıştır:
 *      curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://{WORKER_URL}"
 *
 * Komutlar:
 *   /onayla_123  → listings tablosunda id=123 satırını status='active' yapar
 *   /reddet_123  → listings tablosunda id=123 satırını status='rejected' yapar
 *   /bekleyen    → Bekleyen tüm ilanları listeler
 *   /durum       → Özet istatistik
 */

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Platform Avrupa Telegram Bot aktif.', { status: 200 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response('Bad Request', { status: 400 });
    }

    const message = body.message || body.callback_query?.message;
    if (!message) return new Response('OK');

    const chatId = String(message.chat?.id);
    const text = (body.message?.text || '').trim();

    // Sadece yetkili chat'ten gelen komutları işle
    if (chatId !== String(env.TELEGRAM_CHAT_ID)) {
      await telegramSend(env, chatId, '⛔ Yetkisiz erişim.');
      return new Response('OK');
    }

    // ── Komut işleme ─────────────────────────────────────────────
    const onayla = text.match(/^\/onayla_(\d+)/i);
    const reddet = text.match(/^\/reddet_(\d+)/i);

    if (onayla) {
      const id = onayla[1];
      const result = await supabasePatch(env, id, 'active');
      if (result.ok) {
        await telegramSend(env, chatId, `✅ <b>#${id}</b> onaylandı ve yayına alındı.`);
      } else {
        await telegramSend(env, chatId, `❌ Hata: ${result.error}`);
      }

    } else if (reddet) {
      const id = reddet[1];
      const result = await supabasePatch(env, id, 'rejected');
      if (result.ok) {
        await telegramSend(env, chatId, `🚫 <b>#${id}</b> reddedildi.`);
      } else {
        await telegramSend(env, chatId, `❌ Hata: ${result.error}`);
      }

    } else if (text === '/bekleyen') {
      const data = await supabaseFetch(env, 'listings?status=eq.pending&select=id,title,city&limit=10&order=created_at.asc');
      if (!data || data.length === 0) {
        await telegramSend(env, chatId, '✅ Bekleyen ilan yok!');
      } else {
        let msg = `⏳ <b>Bekleyen İlanlar (${data.length})</b>\n\n`;
        data.forEach(l => {
          msg += `▸ <b>#${l.id}</b> ${l.title?.slice(0, 50)} (${l.city || '—'})\n`;
          msg += `  /onayla_${l.id}  |  /reddet_${l.id}\n\n`;
        });
        await telegramSend(env, chatId, msg);
      }

    } else if (text === '/durum') {
      const [active, pending, users] = await Promise.all([
        supabaseCount(env, 'listings?status=eq.active'),
        supabaseCount(env, 'listings?status=eq.pending'),
        supabaseCount(env, 'profiles'),
      ]);
      const msg = `📊 <b>Platform Avrupa Durumu</b>\n\n` +
        `👥 Üyeler: <b>${active ?? '?'}</b>\n` +
        `✅ Aktif İlan: <b>${active ?? '?'}</b>\n` +
        `⏳ Bekleyen: <b>${pending ?? '?'}</b>\n`;
      await telegramSend(env, chatId, msg);

    } else if (text === '/yardim' || text === '/start') {
      const help = `🤖 <b>Platform Avrupa Admin Bot</b>\n\n` +
        `/bekleyen — Bekleyen ilanları listele\n` +
        `/onayla_ID — İlanı onayla\n` +
        `/reddet_ID — İlanı reddet\n` +
        `/durum — Özet istatistik\n` +
        `/yardim — Bu menü`;
      await telegramSend(env, chatId, help);
    }

    return new Response('OK');
  }
};

// ── Supabase Helpers ──────────────────────────────────────────────────────────

async function supabasePatch(env, id, status) {
  try {
    const res = await fetch(`${env.SUPABASE_URL}/rest/v1/listings?id=eq.${id}`, {
      method: 'PATCH',
      headers: {
        'apikey': env.SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({ status })
    });
    if (!res.ok) {
      const err = await res.text();
      return { ok: false, error: err.slice(0, 100) };
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

async function supabaseFetch(env, path) {
  try {
    const res = await fetch(`${env.SUPABASE_URL}/rest/v1/${path}`, {
      headers: {
        'apikey': env.SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`
      }
    });
    return res.ok ? res.json() : null;
  } catch {
    return null;
  }
}

async function supabaseCount(env, path) {
  try {
    const res = await fetch(`${env.SUPABASE_URL}/rest/v1/${path}&select=id`, {
      headers: {
        'apikey': env.SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        'Range-Unit': 'items',
        'Range': '0-0',
        'Prefer': 'count=exact'
      }
    });
    const cr = res.headers.get('Content-Range') || '';
    return parseInt(cr.split('/')[1]) || 0;
  } catch {
    return null;
  }
}

async function telegramSend(env, chatId, text) {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: 'HTML' })
  });
}
