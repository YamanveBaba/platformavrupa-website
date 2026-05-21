// Platform Avrupa — Telegram Webhook Edge Function
// Haber onay/red + /haber <url> komutu
// Deploy: supabase functions deploy telegram-webhook

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const TG_TOKEN    = Deno.env.get("TELEGRAM_BOT_TOKEN")!;
const GEMINI_KEY  = Deno.env.get("GEMINI_API_KEY") || "";

const sb = createClient(SUPABASE_URL, SUPABASE_KEY);

async function tgSend(chatId: number, text: string, extra: Record<string, unknown> = {}) {
  const r = await fetch(`https://api.telegram.org/bot${TG_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML", ...extra }),
  });
  const data = await r.json();
  if (!data.ok) console.error("tgSend hata:", data);
  return data;
}

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
    body: JSON.stringify({ chat_id: chatId, message_id: messageId, text, parse_mode: "HTML" }),
  });
}

// URL'den içerik çek ve Gemini ile Türkçe haber oluştur
async function urldenHaberOlustur(url: string): Promise<{baslik: string, icerik: string, resim: string} | null> {
  try {
    // URL'yi fetch et
    const r = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 PlatformAvrupa/1.0" },
      signal: AbortSignal.timeout(10000),
    });
    if (!r.ok) return null;
    const html = await r.text();

    // Başlık ve metin çıkar (basit regex)
    const titleM = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    const title = titleM ? titleM[1].trim().replace(/\s+/g, ' ') : "";

    // og:description veya meta description
    const descM = html.match(/og:description[^>]*content="([^"]+)"/i)
                || html.match(/name="description"[^>]*content="([^"]+)"/i);
    const desc = descM ? descM[1].trim() : "";

    // og:image
    const imgM = html.match(/og:image[^>]*content="([^"]+)"/i);
    const resim = imgM ? imgM[1] : "";

    if (!title && !desc) return null;

    // Gemini ile Türkçe haber oluştur
    if (GEMINI_KEY) {
      const prompt = `Aşağıdaki haberi Avrupa'daki Türk gurbetçiler için Türkçe'ye çevir ve düzenle.
Başlık: ${title}
Özet: ${desc}

SADECE JSON döndür:
{"baslik": "Türkçe başlık (max 100 karakter)", "ozet": "Türkçe 2-3 cümle özet"}`;

      const gr = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
            generationConfig: { maxOutputTokens: 300, temperature: 0.2 },
          }),
        }
      );
      const gdata = await gr.json();
      const metin = gdata?.candidates?.[0]?.content?.parts?.[0]?.text || "";
      const jsonM = metin.match(/\{[\s\S]*\}/);
      if (jsonM) {
        const parsed = JSON.parse(jsonM[0]);
        return {
          baslik: parsed.baslik || title,
          icerik: parsed.ozet || desc,
          resim,
        };
      }
    }

    return { baslik: title, icerik: desc, resim };
  } catch (e) {
    console.error("URL fetch hata:", e);
    return null;
  }
}

serve(async (req) => {
  if (req.method !== "POST") return new Response("OK", { status: 200 });

  try {
    const update = await req.json();
    console.log("Webhook update:", JSON.stringify(update).slice(0, 200));

    // ── Buton tıklaması ──────────────────────────────────────────────────────
    const cb = update.callback_query;
    if (cb) {
      const data   = cb.data as string;
      const chatId = cb.message.chat.id;
      const msgId  = cb.message.message_id;
      const baslik = cb.message.text?.split("\n")[0] || "Haber";
      const [action, idStr] = data.split("_");
      const id = parseInt(idStr);

      if (!id || isNaN(id)) {
        await tgAnswer(cb.id, "❌ Geçersiz ID");
        return new Response("ok");
      }

      if (action === "onayla") {
        const { error } = await sb.from("announcements").update({ status: "published" }).eq("id", id);
        console.log("Onayla sonuc:", error ? error.message : "OK");
        if (error) {
          await tgAnswer(cb.id, "❌ DB Hata: " + error.message);
        } else {
          await tgAnswer(cb.id, "✅ Yayınlandı!");
          await tgEditMessage(chatId, msgId, `✅ <b>YAYINLANDI</b>\n${baslik}`);
        }

      } else if (action === "reddet") {
        const { error } = await sb.from("announcements").delete().eq("id", id);
        console.log("Reddet sonuc:", error ? error.message : "OK");
        if (error) {
          await tgAnswer(cb.id, "❌ DB Hata: " + error.message);
        } else {
          await tgAnswer(cb.id, "🗑️ Silindi");
          await tgEditMessage(chatId, msgId, `🗑️ <b>SİLİNDİ</b>\n${baslik}`);
        }
      }

      return new Response("ok", { status: 200 });
    }

    // ── Mesaj — /haber <url> komutu ─────────────────────────────────────────
    const msg = update.message;
    if (msg?.text) {
      const chatId = msg.chat.id;
      const text = msg.text.trim();

      if (text.startsWith("/haber ") || text.startsWith("/haber\n")) {
        const url = text.replace(/^\/haber\s*/, "").trim();
        if (!url.startsWith("http")) {
          await tgSend(chatId, "❌ Geçerli bir URL girin.\nÖrnek: /haber https://...");
          return new Response("ok");
        }

        await tgSend(chatId, "⏳ URL işleniyor...");

        const haber = await urldenHaberOlustur(url);
        if (!haber) {
          await tgSend(chatId, "❌ URL'den içerik alınamadı.");
          return new Response("ok");
        }

        // Announcements tablosuna draft olarak ekle
        const { data: inserted, error } = await sb.from("announcements").insert({
          title: haber.baslik.slice(0, 500),
          content: `<p>${haber.icerik}</p>\n<p><a href="${url}">Kaynağa git →</a></p>`,
          source: "otomatik",
          source_url: url,
          source_hash: btoa(url).slice(0, 32),
          image_url: haber.resim || null,
          status: "draft",
          kategori: "gurbetci",
          ai_skor: 8,
        }).select("id").single();

        if (error || !inserted) {
          await tgSend(chatId, "❌ DB kayıt hatası: " + (error?.message || "bilinmiyor"));
          return new Response("ok");
        }

        const haberMesaj =
          `📰 <b>${haber.baslik}</b>\n\n${haber.icerik}\n\n` +
          `🔗 <a href="${url}">Orijinal kaynak</a>`;

        await tgSend(chatId, haberMesaj, {
          reply_markup: {
            inline_keyboard: [[
              { text: "✅ Yayınla", callback_data: `onayla_${inserted.id}` },
              { text: "🗑️ Sil",    callback_data: `reddet_${inserted.id}` },
            ]],
          },
          disable_web_page_preview: true,
        });

        return new Response("ok");
      }

      // Bilinmeyen mesaj
      if (text.startsWith("/")) {
        await tgSend(chatId,
          "Platform Avrupa Bot\n\n/haber <url> — URL'den Türkçe haber oluştur");
      }
    }

    return new Response("ok", { status: 200 });
  } catch (err) {
    console.error("Webhook hata:", err);
    return new Response("error", { status: 200 });
  }
});
