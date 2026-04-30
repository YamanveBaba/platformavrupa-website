# -*- coding: utf-8 -*-
"""
Cekum tamamlandiktan sonra Telegram bildirimi gonder.
Is ilanlari, market urunleri ve haber sayilarini Supabase'den cekip ozet gonderir.
"""
import os
import time
import requests
from datetime import datetime, timezone

def load_secrets():
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return sb_url.rstrip("/"), sb_key, tg_token, tg_chat

_hatalar: list[str] = []  # Biriktirilen hata açıklamaları

def supabase_say(sb_url, sb_key, tablo, filtre=""):
    """Supabase'den COUNT döner. Başarısız olursa "?" + hata nedenini _hatalar listesine ekler."""
    if not sb_url:
        _hatalar.append("SUPABASE_URL tanımlı değil")
        return "?"
    if not sb_key:
        _hatalar.append("SUPABASE_SERVICE_ROLE_KEY tanımlı değil")
        return "?"

    headers = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}",
               "Range-Unit": "items", "Range": "0-0", "Prefer": "count=exact"}
    url = f"{sb_url}/rest/v1/{tablo}?select=id{filtre}"

    son_hata = ""
    for deneme in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 401:
                son_hata = f"{tablo}: 401 Unauthorized (API key geçersiz?)"
                break
            if r.status_code == 404:
                son_hata = f"{tablo}: 404 Tablo bulunamadı"
                break
            if r.status_code >= 400:
                son_hata = f"{tablo}: HTTP {r.status_code} — {r.text[:60]}"
                break
            cr = r.headers.get("Content-Range", "")
            if not cr:
                son_hata = f"{tablo}: Content-Range header yok (Supabase uyanıyor olabilir)"
                if deneme < 2:
                    time.sleep(8)
                    continue
                break
            return int(cr.split("/")[-1])
        except requests.exceptions.Timeout:
            son_hata = f"{tablo}: timeout (Supabase yanıt vermedi)"
            if deneme < 2:
                time.sleep(8)
        except requests.exceptions.ConnectionError as e:
            son_hata = f"{tablo}: bağlantı hatası — {str(e)[:60]}"
            if deneme < 2:
                time.sleep(8)
        except Exception as e:
            son_hata = f"{tablo}: {type(e).__name__} — {str(e)[:60]}"
            break

    if son_hata and son_hata not in _hatalar:
        _hatalar.append(son_hata)
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
    haber_toplam   = supabase_say(sb_url, sb_key, "announcements", "&source=eq.otomatik&status=eq.published")
    draft_haberler = supabase_say(sb_url, sb_key, "announcements", "&source=eq.otomatik&status=eq.draft")

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
        hdrs = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
        try:
            r = requests.get(
                f"{sb_url}/rest/v1/listings?status=eq.pending&select=id,title,city&limit=5&order=created_at.asc",
                headers=hdrs, timeout=15
            )
            if r.status_code == 200:
                for ilan in r.json():
                    pending_detay += f"\n  ▸ #{ilan.get('id','')} {ilan.get('title','')[:40]} ({ilan.get('city','')})"
                    pending_detay += f"\n    /onayla_{ilan.get('id','')}  /reddet_{ilan.get('id','')}"
        except Exception:
            pass

    # Draft haberler detayı
    draft_haber_detay = ""
    if sb_url and sb_key and isinstance(draft_haberler, int) and draft_haberler > 0:
        hdrs = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
        try:
            r = requests.get(
                f"{sb_url}/rest/v1/announcements?source=eq.otomatik&status=eq.draft"
                f"&select=id,title,ai_skor&order=ai_skor.desc&limit=5",
                headers=hdrs, timeout=15
            )
            if r.status_code == 200:
                for h in r.json():
                    skor = h.get('ai_skor') or 0
                    yildiz = '★' * min(round(skor/2), 5)
                    draft_haber_detay += f"\n  {yildiz} {h.get('title','')[:60]}"
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
        f"  Yayında:          <b>{fmt(haber_toplam)}</b>\n"
        f"  Onay bekleyen:    <b>{fmt(draft_haberler)}</b>\n"
    )

    if isinstance(draft_haberler, int) and draft_haberler > 0:
        mesaj += (
            f"\n📋 <b>Onay Bekleyen {draft_haberler} Haber:</b>"
            f"{draft_haber_detay}\n"
            f"\n🔗 <a href=\"https://www.platformavrupa.com/admin.html#haberler\">Admin paneli → Haber Kuyruğu</a>"
        )

    if isinstance(pending_count, int) and pending_count > 0:
        mesaj += (
            f"\n⚠️ <b>Onay Bekleyen İlanlar: {pending_count}</b>"
            f"{pending_detay}\n"
            f"\n<i>Onaylamak için komutu Telegram'a gönderin.</i>"
        )

    # Hata özeti — sadece "?" olan şeyler varsa
    if _hatalar:
        benzersiz = list(dict.fromkeys(_hatalar))  # sıra koruyarak tekrarsız
        mesaj += f"\n\n🔴 <b>Veri alınamayan alanlar ({len(benzersiz)} hata):</b>\n"
        for h in benzersiz[:5]:
            mesaj += f"  • {h}\n"

    print(mesaj)
    telegram_gonder(tg_token, tg_chat, mesaj)
    web_push_gonder(sb_url, sb_key, ilan_toplam)

def web_push_gonder(sb_url, sb_key, ilan_toplam):
    """Tüm PWA abonelerine günlük güncelleme bildirimi gönder."""
    if not sb_url or not sb_key:
        return
    edge_url = f"{sb_url}/functions/v1/send-push"
    headers = {
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
    }
    try:
        toplam_str = f"{ilan_toplam:,}" if isinstance(ilan_toplam, int) else str(ilan_toplam)
        r = requests.post(edge_url, headers=headers, json={
            "title": "Platform Avrupa",
            "body": f"Bugün {toplam_str} iş ilanı güncellendi.",
            "url": "/is_vitrini.html"
        }, timeout=30)
        print(f"Web push: {r.status_code} — {r.text[:80]}")
    except Exception as e:
        print(f"Web push hata: {e}")

if __name__ == "__main__":
    main()
