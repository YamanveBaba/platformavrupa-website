# -*- coding: utf-8 -*-
"""
colruyt_auth_kontrol.py — Colruyt API key geçerliliğini tek istekle test eder.

Çıkış kodu:
  0 = API key geçerli veya test atlandı (429 / bağlantı hatası)
  1 = API key GEÇERSİZ (401/406) → Telegram alert gönderildi

Kullanım:
  python colruyt_auth_kontrol.py
  (haftalik_tam.py ve auth_monitor.py tarafından da çağrılır)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("HATA: pip install requests")
    sys.exit(0)  # Bağımlılık yoksa sessizce geç — scraper'ı engelleme

SCRIPT_DIR = Path(__file__).parent
AUTH_PATH  = SCRIPT_DIR.parent / "colruyt_auth.txt"
PROBE_URL  = (
    "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc"
    "/cg/nl/api/product-search-prs?placeId=710&size=1"
)
STATUS_FILE = SCRIPT_DIR / "loglar" / "colruyt_api_durum.txt"


def _key_oku() -> str:
    key = "a8ylmv13-b285-4788-9e14-0f79b7ed2411"
    if AUTH_PATH.exists():
        try:
            for line in open(AUTH_PATH, encoding="utf-8", errors="ignore"):
                line = line.strip()
                if line.startswith("KEY=") and not line.startswith("#"):
                    v = line[4:].strip()
                    if v:
                        key = v
        except Exception:
            pass
    return key


def _telegram_gonder(mesaj: str) -> None:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
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


def _durum_yaz(durum: str) -> None:
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(durum, encoding="utf-8")
    except Exception:
        pass


def kontrol() -> int:
    """API key'i test eder. 0 = OK, 1 = GEÇERSİZ."""
    key = _key_oku()
    headers = {
        "X-CG-APIKey":   key,
        "Accept":        "application/json",
        "User-Agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0",
        "Origin":        "https://www.colruyt.be",
        "Referer":       "https://www.colruyt.be/nl/producten",
    }
    try:
        r = requests.get(PROBE_URL, headers=headers, timeout=20)
    except requests.RequestException as e:
        print(f"[UYARI] Colruyt API bağlantı hatası: {e}")
        _durum_yaz(f"UYARI bağlantı hatası: {e}")
        return 0  # Bağlantı sorunu — API key sorunsuz olabilir, geç

    if r.status_code == 200:
        print(f"[OK] Colruyt API key geçerli ({key[:12]}...)")
        _durum_yaz(f"OK")
        return 0

    if r.status_code in (401, 406):
        mesaj = (
            f"⚠️ <b>Colruyt API Key GEÇERSİZ</b>\n"
            f"HTTP {r.status_code} — colruyt.be F12 &gt; Network &gt; product-search-prs\n"
            f"Yeni key'i <code>colruyt_auth.txt</code>'e KEY=... olarak yazın."
        )
        print(f"[HATA] Colruyt API key geçersiz (HTTP {r.status_code})")
        _durum_yaz(f"HATA HTTP {r.status_code}")
        _telegram_gonder(mesaj)
        return 1

    if r.status_code == 429:
        print(f"[UYARI] Rate limit (429) — key geçerli kabul ediliyor")
        _durum_yaz("UYARI rate-limit 429")
        return 0

    print(f"[UYARI] Beklenmedik HTTP {r.status_code} — devam ediliyor")
    _durum_yaz(f"UYARI HTTP {r.status_code}")
    return 0


if __name__ == "__main__":
    sys.exit(kontrol())
