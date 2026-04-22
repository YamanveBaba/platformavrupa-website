# -*- coding: utf-8 -*-
"""
Cekum tamamlandiktan sonra Telegram bildirimi gonder.
Supabase'den kaynak bazli ilan sayilarini ceker.

Kullanim:
  python bildir.py --mesaj "FOREM bitti" --kaynak forem --yeni 1240
"""
import argparse
import os
import sys
import requests
from datetime import datetime, timezone

def load_secrets():
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return sb_url.rstrip("/"), sb_key, tg_token, tg_chat

def supabase_say(sb_url, sb_key, kaynak):
    """Supabase'den kaynak bazli aktif ilan sayisini cek."""
    if not sb_url or not sb_key:
        return "?"
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}",
                "Range-Unit": "items", "Range": "0-0", "Prefer": "count=exact"}
    r = requests.get(f"{sb_url}/rest/v1/ilanlar?select=id&source=eq.{kaynak}&status=eq.active",
                     headers=headers, timeout=15)
    cr = r.headers.get("Content-Range", "")
    try:
        return int(cr.split("/")[-1])
    except Exception:
        return "?"

def telegram_gonder(token, chat_id, mesaj):
    if not token or not chat_id:
        print("TELEGRAM credentials eksik, bildirim atlanıyor.")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": mesaj, "parse_mode": "HTML"}, timeout=15)
    if r.status_code == 200:
        print("Telegram bildirimi gonderildi.")
    else:
        print(f"Telegram hata: {r.status_code} {r.text[:100]}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ozet", default="", help="Ek ozet satiri")
    args = parser.parse_args()

    sb_url, sb_key, tg_token, tg_chat = load_secrets()

    actiris = supabase_say(sb_url, sb_key, "actiris")
    forem   = supabase_say(sb_url, sb_key, "forem")
    vdab    = supabase_say(sb_url, sb_key, "vdab")

    try:
        toplam = actiris + forem + vdab
    except Exception:
        toplam = "?"

    saat = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    mesaj = (
        f"✅ <b>Platform Avrupa — Günlük Güncelleme</b>\n"
        f"📅 {saat}\n\n"
        f"🟦 Actiris (Brüksel): <b>{actiris:,}</b> ilan\n"
        f"🟩 FOREM (Valoniya):  <b>{forem:,}</b> ilan\n"
        f"🟧 VDAB (Flandriya):  <b>{vdab:,}</b> ilan\n"
        f"────────────────────\n"
        f"📊 Toplam DB: <b>{toplam:,}</b> ilan\n"
    )
    if args.ozet:
        mesaj += f"\n📝 {args.ozet}"

    print(mesaj)
    telegram_gonder(tg_token, tg_chat, mesaj)

if __name__ == "__main__":
    main()
