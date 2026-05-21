# -*- coding: utf-8 -*-
"""
Platform Avrupa — Günlük İndirim Bildirimi
Her gün en iyi indirimleri Telegram'a gönderir.

Kullanım:
  python indirim_bildir.py              # Bugünkü indirimleri gönder
  python indirim_bildir.py --dry-run    # Sadece listele, gönderme
  python indirim_bildir.py --limit 5   # En iyi 5 ürün
"""
import argparse, os, sys, requests, re
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

MARKET_EMOJI = {
    'aldi_be':      '🟡 ALDI',
    'delhaize_be':  '🔴 Delhaize',
    'lidl_be':      '🔵 Lidl',
    'carrefour_be': '🟠 Carrefour',
    'colruyt_be':   '🟢 Colruyt',
}

def load_secrets():
    sb_url = os.environ.get("SUPABASE_URL", "").strip()
    sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not sb_url or not sb_key:
        path = os.path.normpath(
            os.path.join(SCRIPT_DIR, "..", "market_fiyat_cekici", "supabase_import_secrets.txt")
        )
        if os.path.isfile(path):
            lines = [l.strip() for l in open(path, encoding="utf-8", errors="ignore")
                     if l.strip() and not l.startswith("#")]
            if len(lines) >= 2:
                sb_url, sb_key = lines[0].rstrip("/"), lines[1]
    if not sb_url or not sb_key:
        print("HATA: Supabase credentials bulunamadı."); sys.exit(1)
    return sb_url, sb_key, tg_token, tg_chat


def indirimli_urunler_cek(sb_url: str, sb_key: str, limit: int) -> list[dict]:
    """Supabase'den aktif indirimleri çek, indirim % göre sırala."""
    hdrs = {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"}
    bugun = datetime.now(timezone.utc).date().isoformat()

    r = requests.get(
        f"{sb_url}/rest/v1/market_chain_products",
        params={
            "select": "name,name_tr,chain_slug,price,promo_price,image_url,promo_valid_until",
            "in_promo": "eq.true",
            "promo_price": "not.is.null",
            "price": "gt.0",
            "order": "promo_price.asc",
            "limit": str(limit * 3),  # fazla çek, filtrele
        },
        headers=hdrs, timeout=20,
    )
    if r.status_code != 200:
        print(f"  Supabase hata: {r.status_code}")
        return []

    urunler = []
    goruldu = set()

    for u in r.json():
        price = float(u.get("price") or 0)
        promo = float(u.get("promo_price") or 0)
        if price <= 0 or promo <= 0 or promo >= price:
            continue
        pct = round((price - promo) / price * 100)
        if pct < 5:
            continue

        isim = u.get("name_tr") or u.get("name") or ""
        key = f"{u.get('chain_slug')}_{isim[:20]}"
        if key in goruldu:
            continue
        goruldu.add(key)

        urunler.append({
            "isim": isim,
            "market": u.get("chain_slug", ""),
            "fiyat": price,
            "indirimli": promo,
            "pct": pct,
            "resim": u.get("image_url") or "",
            "bitis": u.get("promo_valid_until") or "",
        })

    # İndirim % göre sırala, her marketten max 2 al
    urunler.sort(key=lambda x: x["pct"], reverse=True)
    sonuc = []
    market_sayac: dict[str, int] = {}
    for u in urunler:
        m = u["market"]
        if market_sayac.get(m, 0) >= 2:
            continue
        market_sayac[m] = market_sayac.get(m, 0) + 1
        sonuc.append(u)
        if len(sonuc) >= limit:
            break

    return sonuc


def telegram_gonder(token: str, chat_id: str, mesaj: str):
    if not token or not chat_id:
        print("  Telegram credentials eksik.")
        return False
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": mesaj, "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=15,
    )
    if r.status_code == 200:
        print("  Telegram bildirimi gönderildi.")
        return True
    print(f"  Telegram hata: {r.status_code}: {r.text[:100]}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    sb_url, sb_key, tg_token, tg_chat = load_secrets()
    tarih = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    print(f"[İndirim Bildirimi] {tarih}")
    urunler = indirimli_urunler_cek(sb_url, sb_key, args.limit)

    if not urunler:
        print("  Aktif indirim bulunamadı.")
        return

    print(f"  {len(urunler)} indirimli ürün bulundu.")

    # Telegram mesajı oluştur
    satırlar = [f"🛒 <b>Bugünkü En İyi İndirimler</b> — {tarih}\n"]
    for u in urunler:
        market = MARKET_EMOJI.get(u["market"], u["market"])
        bitis = f" (bitis: {u['bitis'][:10]})" if u["bitis"] else ""
        satırlar.append(
            f"{market}\n"
            f"  <b>{u['isim'][:50]}</b>\n"
            f"  <s>{u['fiyat']:.2f}€</s> → <b>{u['indirimli']:.2f}€</b> "
            f"  (<b>-%{u['pct']}</b>){bitis}\n"
        )

    satırlar.append(f"\n🔗 <a href=\"https://www.platformavrupa.com/market.html\">Tüm indirimler →</a>")
    mesaj = "\n".join(satırlar)

    print(mesaj)

    if not args.dry_run:
        telegram_gonder(tg_token, tg_chat, mesaj)


if __name__ == "__main__":
    main()
