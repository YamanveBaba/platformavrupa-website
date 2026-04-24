# -*- coding: utf-8 -*-
"""
Cekum tamamlandiktan sonra Telegram bildirimi gonder.
Is ilanlari, market urunleri ve haber sayilarini Supabase'den cekip ozet gonderir.
"""
import os
import requests
from datetime import datetime, timezone

def load_secrets():
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return sb_url.rstrip("/"), sb_key, tg_token, tg_chat

def supabase_say(sb_url, sb_key, tablo, filtre=""):
    if not sb_url or not sb_key:
        return "?"
    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}",
                "Range-Unit": "items", "Range": "0-0", "Prefer": "count=exact"}
    r = requests.get(f"{sb_url}/rest/v1/{tablo}?select=id{filtre}",
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
    sb_url, sb_key, tg_token, tg_chat = load_secrets()

    # Is ilanlari
    actiris = supabase_say(sb_url, sb_key, "ilanlar", "&source=eq.actiris&status=eq.active")
    forem   = supabase_say(sb_url, sb_key, "ilanlar", "&source=eq.forem&status=eq.active")
    vdab    = supabase_say(sb_url, sb_key, "ilanlar", "&source=eq.vdab&status=eq.active")
    try:
        ilan_toplam = actiris + forem + vdab
    except Exception:
        ilan_toplam = "?"

    # Market urunleri
    colruyt  = supabase_say(sb_url, sb_key, "market_chain_products", "&chain=eq.colruyt")
    delhaize = supabase_say(sb_url, sb_key, "market_chain_products", "&chain=eq.delhaize")
    lidl     = supabase_say(sb_url, sb_key, "market_chain_products", "&chain=eq.lidl")
    carrefour= supabase_say(sb_url, sb_key, "market_chain_products", "&chain=eq.carrefour")
    aldi     = supabase_say(sb_url, sb_key, "market_chain_products", "&chain=eq.aldi")
    try:
        market_toplam = colruyt + delhaize + lidl + carrefour + aldi
    except Exception:
        market_toplam = "?"

    # Haberler
    haber_toplam = supabase_say(sb_url, sb_key, "announcements", "&source=eq.otomatik")

    saat = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    def fmt(v):
        try:
            return f"{v:,}"
        except Exception:
            return str(v)

    # Bekleyen ilanlar detayi
    pending_count = supabase_say(sb_url, sb_key, "listings", "&status=eq.pending")
    pending_detay = ""
    if sb_url and sb_key and isinstance(pending_count, int) and pending_count > 0:
        headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
        try:
            r = requests.get(
                f"{sb_url}/rest/v1/listings?status=eq.pending&select=id,title,city&limit=5&order=created_at.asc",
                headers=headers, timeout=15
            )
            if r.status_code == 200:
                for ilan in r.json():
                    pending_detay += f"\n  ▸ #{ilan.get('id','')} {ilan.get('title','')[:40]} ({ilan.get('city','')})"
                    pending_detay += f"\n    /onayla_{ilan.get('id','')}  /reddet_{ilan.get('id','')}"
        except Exception:
            pass

    mesaj = (
        f"✅ <b>Platform Avrupa — Günlük Güncelleme</b>\n"
        f"📅 {saat}\n\n"
        f"💼 <b>İş İlanları</b>\n"
        f"  🟦 Actiris (Brüksel):  <b>{fmt(actiris)}</b>\n"
        f"  🟩 FOREM (Valoniya):   <b>{fmt(forem)}</b>\n"
        f"  🟧 VDAB (Flandriya):   <b>{fmt(vdab)}</b>\n"
        f"  📊 Toplam:             <b>{fmt(ilan_toplam)}</b>\n\n"
        f"🛒 <b>Market Ürünleri</b>\n"
        f"  Colruyt:   <b>{fmt(colruyt)}</b>\n"
        f"  Delhaize:  <b>{fmt(delhaize)}</b>\n"
        f"  Lidl:      <b>{fmt(lidl)}</b>\n"
        f"  Carrefour: <b>{fmt(carrefour)}</b>\n"
        f"  Aldi:      <b>{fmt(aldi)}</b>\n"
        f"  📊 Toplam: <b>{fmt(market_toplam)}</b>\n\n"
        f"📰 <b>Haberler</b>\n"
        f"  Otomatik:  <b>{fmt(haber_toplam)}</b>\n"
    )

    if isinstance(pending_count, int) and pending_count > 0:
        mesaj += (
            f"\n⚠️ <b>Onay Bekleyen İlanlar: {pending_count}</b>"
            f"{pending_detay}\n"
            f"\n<i>Onaylamak için komutu Telegram'a gönderin.</i>"
        )

    print(mesaj)
    telegram_gonder(tg_token, tg_chat, mesaj)

if __name__ == "__main__":
    main()
