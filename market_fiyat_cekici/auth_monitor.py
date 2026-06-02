# -*- coding: utf-8 -*-
"""
auth_monitor.py — Günlük kimlik doğrulama ve veri tazelik kontrolü.

Her gün 07:00'de çalışır (Task Scheduler). Tüm market auth sistemlerini
kontrol eder, sorun varsa haftalık çekim BAŞLAMADAN önce Telegram bildirimi gönderir.

Kontroller:
  1. Colruyt API key geçerliliği (1 probe isteği)
  2. Colruyt reese84 cookie süresi (colruyt_state.json)
  3. Lidl cookie geçerliliği (lidl_cookie.txt tarih kontrolü)
  4. Delhaize veri tazeliği (son JSON dosyası 8 günden eskiyse uyarı)
  5. Carrefour veri tazeliği (aynı)

Kullanım:
  python auth_monitor.py
  python auth_monitor.py --quiet   # Sadece Telegram, konsol çıktısı yok
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(0)

SCRIPT_DIR  = Path(__file__).parent
LOG_DIR     = SCRIPT_DIR / "loglar"
STATUS_FILE = LOG_DIR / "auth_status.json"


# ─── Telegram ─────────────────────────────────────────────────────────────────

def _telegram_gonder(mesaj: str) -> None:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mesaj, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


# ─── Kontrol fonksiyonları ────────────────────────────────────────────────────

def kontrol_colruyt_api() -> dict:
    """colruyt_auth_kontrol.py'yi import ederek API key probe çalıştırır."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "colruyt_auth_kontrol",
            SCRIPT_DIR / "colruyt_auth_kontrol.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Telegram'ı buradan göndermek yerine sadece sonucu al
        auth_path = SCRIPT_DIR.parent / "colruyt_auth.txt"
        key = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
        if auth_path.exists():
            for line in open(auth_path, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line.startswith("KEY=") and not line.startswith("#"):
                    v = line[4:].strip()
                    if v:
                        key = v

        r = requests.get(
            mod.PROBE_URL,
            headers={"X-CG-APIKey": key, "Accept": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            return {"kontrol": "colruyt_api", "ok": True, "detay": "OK"}
        return {"kontrol": "colruyt_api", "ok": False,
                "detay": f"HTTP {r.status_code} — API key güncellenmeli"}
    except Exception as e:
        return {"kontrol": "colruyt_api", "ok": True, "detay": f"atlandı: {e}"}


def kontrol_colruyt_cookie() -> dict:
    """colruyt_state.json'dan reese84 cookie süresini kontrol eder."""
    state_path = SCRIPT_DIR / "colruyt_state.json"
    if not state_path.exists():
        return {"kontrol": "colruyt_cookie", "ok": True, "detay": "colruyt_state.json yok — atlandı"}
    try:
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
        cookies = state.get("cookies") or []
        if isinstance(state, list):
            cookies = state
        simdi = time.time()
        for c in cookies:
            if isinstance(c, dict) and c.get("name") == "reese84":
                exp = c.get("expires") or c.get("expiry") or 0
                try:
                    exp = float(exp)
                except (TypeError, ValueError):
                    continue
                kalan_gun = (exp - simdi) / 86400
                if kalan_gun < 3:
                    return {
                        "kontrol": "colruyt_cookie",
                        "ok": False,
                        "detay": f"reese84 cookie {kalan_gun:.1f} gün içinde doluyor!",
                    }
                return {
                    "kontrol": "colruyt_cookie",
                    "ok": True,
                    "detay": f"reese84 {kalan_gun:.1f} gün geçerli",
                }
        return {"kontrol": "colruyt_cookie", "ok": True, "detay": "reese84 bulunamadı"}
    except Exception as e:
        return {"kontrol": "colruyt_cookie", "ok": True, "detay": f"okunamadı: {e}"}


def kontrol_lidl_cookie() -> dict:
    """lidl_cookie.txt'deki tarih damgasını kontrol eder."""
    cookie_path = SCRIPT_DIR / "lidl_cookie.txt"
    if not cookie_path.exists():
        return {"kontrol": "lidl_cookie", "ok": False, "detay": "lidl_cookie.txt yok"}
    try:
        for line in open(cookie_path, encoding="utf-8", errors="ignore"):
            s = line.strip()
            if s and not s.startswith("#") and "=" in s and len(s) > 20:
                if "datestamp=" in s:
                    part = s.split("datestamp=")[1].split("&")[0]
                    yil_str = part.split("+")[3] if "+" in part else ""
                    if yil_str.isdigit():
                        yil = int(yil_str)
                        if yil < datetime.now().year:
                            return {
                                "kontrol": "lidl_cookie",
                                "ok": False,
                                "detay": f"Cookie {yil} yılına ait — yenilenecek",
                            }
                return {"kontrol": "lidl_cookie", "ok": True, "detay": "geçerli görünüyor"}
        return {"kontrol": "lidl_cookie", "ok": True, "detay": "tarih bulunamadı"}
    except Exception as e:
        return {"kontrol": "lidl_cookie", "ok": True, "detay": f"okunamadı: {e}"}


def kontrol_veri_tazelik(market: str, desen: str, max_gun: int = 8) -> dict:
    """En son JSON dosyasının kaç günlük olduğunu kontrol eder."""
    cikti = SCRIPT_DIR / "cikti"
    dosyalar = glob.glob(str(cikti / desen))
    if not dosyalar:
        return {"kontrol": f"{market}_veri", "ok": False, "detay": "JSON dosyası bulunamadı"}
    son = max(dosyalar, key=os.path.getmtime)
    son_tarih = datetime.fromtimestamp(os.path.getmtime(son))
    yas_gun = (datetime.now() - son_tarih).days
    if yas_gun > max_gun:
        return {
            "kontrol": f"{market}_veri",
            "ok": False,
            "detay": f"Son veri {yas_gun} gün önce — yenilenecek",
        }
    return {"kontrol": f"{market}_veri", "ok": True, "detay": f"{yas_gun} gün önce güncellendi"}


# ─── Ana fonksiyon ────────────────────────────────────────────────────────────

def main():
    quiet = "--quiet" in sys.argv

    sonuclar = [
        kontrol_colruyt_api(),
        kontrol_colruyt_cookie(),
        kontrol_lidl_cookie(),
        kontrol_veri_tazelik("delhaize",  "delhaize_be_v2_*.json",   max_gun=8),
        kontrol_veri_tazelik("carrefour", "carrefour_be_v2_*.json",  max_gun=8),
        kontrol_veri_tazelik("aldi",      "aldi_be_v2_*.json",       max_gun=8),
        kontrol_veri_tazelik("colruyt",   "colruyt_be_producten_*.json", max_gun=8),
        kontrol_veri_tazelik("lidl",      "lidl_be_producten_*.json", max_gun=8),
    ]

    hatalar = [s for s in sonuclar if not s["ok"]]

    # Durumu dosyaya yaz
    LOG_DIR.mkdir(exist_ok=True)
    STATUS_FILE.write_text(
        json.dumps(
            {"tarih": datetime.now().isoformat(), "sonuclar": sonuclar},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )

    if not quiet:
        print(f"Auth Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        for s in sonuclar:
            simge = "OK" if s["ok"] else "HATA"
            print(f"  [{simge}] {s['kontrol']:25s} {s['detay']}")

    if hatalar:
        satirlar = [f"⚠️ <b>Günlük Auth Kontrolü — {datetime.now().strftime('%d.%m.%Y')}</b>\n"]
        for h in hatalar:
            satirlar.append(f"• {h['kontrol']}: {h['detay']}")
        satirlar.append("\nDüzeltmeden sonra scraper normal çalışmaya devam eder.")
        _telegram_gonder("\n".join(satirlar))
        if not quiet:
            print(f"\n  Telegram uyarısı gönderildi ({len(hatalar)} sorun).")
    else:
        if not quiet:
            print("\n  Tüm kontroller geçti — sorun yok.")


if __name__ == "__main__":
    main()
