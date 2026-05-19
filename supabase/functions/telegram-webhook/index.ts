// Platform Avrupa — Telegram Webhook Edge Function
// Haber onay/red buton tıklamalarını işler
// Deploy: supabase functions deploy telegram-webhook

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const TG_TOKEN    = Deno.env.get("TELEGRAM_BOT_TOKEN")!;

const sb = createClient(SUPABASE_URL, SUPABASE_KEY);

async function tgAnswer(callbackQueryId: string, text: string) {
  await fetch(`https://api.telegram.org/bot${TG_TOKEN}/answerCallbackQuery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: callbackQueryId, text, show_alert: false }),
  });
}

async function tgEditMessage(chatId: number, messageId: number, text: string) {
  await fetch(`https://api.telegram.org/bot${TG_TOKEN}/editMessageText`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      message_id: messageId,
      text,
      parse_mode: "HTML",
    }),
  });
}

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("OK", { status: 200 });
  }

  try {
    const update = await req.json();

    // Buton tıklaması
    const cb = update.callback_query;
    if (cb) {
      const data     = cb.data as string;          // "onayla_123" veya "reddet_123"
      const chatId   = cb.message.chat.id;
      const msgId    = cb.message.message_id;
      const baslik   = cb.message.text?.split("\n")[0] || "Haber";

      const [action, idStr] = data.split("_");
      const id = parseInt(idStr);

      if (!id || isNaN(id)) {
        await tgAnswer(cb.id, "❌ Geçersiz ID");
        return new Response("ok");
      }

      if (action === "onayla") {
        const { error } = await sb
          .from("announcements")
          .update({ status: "published" })
          .eq("id", id);

        if (error) {
          await tgAnswer(cb.id, "❌ Hata: " + error.message);
        } else {
          await tgAnswer(cb.id, "✅ Yayınlandı!");
          await tgEditMessage(chatId, msgId,
            `✅ <b>YAYINLANDI</b>\n${baslik}`);
        }

      } else if (action === "reddet") {
        const { error } = await sb
          .from("announcements")
          .delete()
          .eq("id", id);

        if (error) {
          await tgAnswer(cb.id, "❌ Hata: " + error.message);
        } else {
          await tgAnswer(cb.id, "🗑️ Silindi");
          await tgEditMessage(chatId, msgId,
            `🗑️ <b>SİLİNDİ</b>\n${baslik}`);
        }

      } else if (action === "erteله") {
        // Şimdilik sadece bildirim
        await tgAnswer(cb.id, "⏳ Erteklendi (draft'ta kaldı)");
      }

      return new Response("ok", { status: 200 });
    }

    return new Response("ok", { status: 200 });
  } catch (err) {
    console.error("Webhook hata:", err);
    return new Response("error", { status: 200 }); // Telegram 200 bekliyor
  }
});
