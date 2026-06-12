"""
health_check.py — Market scraper sağlık kontrolü + Telegram alarm.

Her scraper çalışması SONUNDA çağrılır. Beklenen minimum satır
sayısının altına düşen veya 3 günden eski veri olan marketler için
anında Telegram alarmı gönderir.

KULLANIM (workflow'un son adımında):
  python health_check.py

ENV:
  SUPABASE_URL, SUPABASE_SERVICE_KEY
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import requests

EXPECTED_MIN = {
    "colruyt_be":   17000,
    "delhaize_be":  11000,
    "carrefour_be": 10000,
    "lidl_be":       7800,
    "aldi_be":       2200,
}

MAX_AGE_DAYS = 3


def check_chain(supabase, chain_slug: str) -> dict:
    resp = (
        supabase.table("market_chain_products")
        .select("captured_at", count="exact")
        .eq("chain_slug", chain_slug)
        .order("captured_at", desc=True)
        .limit(1)
        .execute()
    )
    count = resp.count or 0
    newest = None
    if resp.data:
        newest = _parse_dt(resp.data[0].get("captured_at"))

    problems = []
    expected = EXPECTED_MIN.get(chain_slug, 0)
    if count < expected:
        problems.append(f"satır sayısı düşük: {count} < beklenen {expected}")
    if newest is None:
        problems.append("hiç veri yok")
    elif newest < datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS):
        age = (datetime.now(timezone.utc) - newest).days
        problems.append(f"veri bayat: {age} gün önce ({newest.date()})")

    return {
        "chain": chain_slug,
        "count": count,
        "newest": newest.isoformat() if newest else None,
        "ok": len(problems) == 0,
        "problems": problems,
    }


def check_all(supabase, send_alerts: bool = True) -> list:
    results = [check_chain(supabase, c) for c in EXPECTED_MIN]
    broken = [r for r in results if not r["ok"]]

    print("\n=== MARKET SAĞLIK RAPORU ===")
    for r in results:
        flag = "✅" if r["ok"] else "🔴"
        print(f"{flag} {r['chain']:15} {r['count']:>7} satır  son: {r['newest']}")
        for p in r["problems"]:
            print(f"      ↳ {p}")

    if not send_alerts:
        return results

    if broken:
        lines = ["🔴 *Market scraper SORUNU*", ""]
        for r in broken:
            lines.append(f"*{r['chain']}*: {', '.join(r['problems'])}")
        alert("\n".join(lines))
        return results

    ok_lines = [f"✅ {r['chain']}: {r['count']} satır" for r in results]
    alert("✅ *Tüm marketler sağlıklı*\n\n" + "\n".join(ok_lines))
    return results


def alert(message: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"[ALARM — Telegram env yok]\n{message}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
        print("[ALARM gönderildi]")
    except Exception as e:
        print(f"[ALARM gönderilemedi: {e}]\n{message}")


def _parse_dt(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


if __name__ == "__main__":
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("HATA: SUPABASE_URL veya SUPABASE_SERVICE_KEY eksik")
        sys.exit(1)

    sb = create_client(url, key)
    results = check_all(sb)
    broken = [r for r in results if not r["ok"]]
    sys.exit(1 if broken else 0)
