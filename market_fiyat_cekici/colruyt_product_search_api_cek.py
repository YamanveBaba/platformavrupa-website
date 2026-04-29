# -*- coding: utf-8 -*-
"""
Colruyt Belçika - product-search-prs API ile tüm ürün + fiyat çekici
Platform Avrupa - Market Fiyat Modülü

İnsan benzeri davranış: rastgele bekleme süreleri, bazen uzun ara, retry ve yumuşak hata yönetimi.
API: apip.colruyt.be/gateway/.../product-search-prs?placeId=&size=&skip=...
"""

import argparse
import json
import os
import random
import re
import time
from datetime import datetime
from typing import List

# -----------------------------------------------------------------------------
# AYARLAR (gerekirse değiştir)
# -----------------------------------------------------------------------------
CONFIG = {
    "base_url": "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc/cg/nl/api/product-search-prs",
    "place_id": "762",           # Mağaza (tarayıcıdan kopyaladığın placeId)
    "cg_api_key": "a8ylmv13-b285-4788-9e14-0f79b7ed2411",  # Site güncellenirse tarayıcı isteğinden kopyalayın
    "page_size": 20,             # Sayfa başına ürün (sitedeki gibi 20; bazen 18–24 arası random)
    "max_products": 50000,       # Tam katalog için yüksek tavan (API totalProductsFound ile de sınırlanır)
    "request_timeout": 25,       # İstek zaman aşımı (saniye)
    "max_retries": 4,           # Hata durumunda deneme sayısı
    "checkpoint_every_pages": 5, # Kaç sayfada bir ara kayıt
    "stale_page_limit": 3,       # Üst üste yeni ürün gelmeyen sayfa limiti
}

# Tarayıcıya benzeyen sabit header'lar (API anahtarı CONFIG["cg_api_key"] ile eklenir)
_HEADERS_WITHOUT_API_KEY = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.colruyt.be/nl/producten",
    "Origin": "https://www.colruyt.be",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}


def build_api_headers_base():
    """X-CG-APIKey tek kaynak: CONFIG['cg_api_key']."""
    h = dict(_HEADERS_WITHOUT_API_KEY)
    h["X-CG-APIKey"] = str(CONFIG.get("cg_api_key") or "").strip()
    return h


# Cookie: script ile aynı klasörde cookie.txt oluşturup tarayıcıdan kopyaladığınız değeri yapıştırın
API_HEADERS_BASE = build_api_headers_base()

# Ara sıra User-Agent değiştir (her istekte değil; oturum tutarlılığı için sayfa bazlı)
CHROME_UA_POOL = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
)

def sanitize_place_id(raw) -> str:
    """
    curl/cmd kopyasında placeId sonuna sıkışan ^, boşluk vb. temizlenir.
    Colruyt placeId sayısal; baştaki rakam bloğu alınır.
    """
    if raw is None:
        return ""
    s = str(raw).strip().rstrip("^").strip()
    s = re.sub(r"[\s\x00]+$", "", s)
    m = re.match(r"^(\d+)", s)
    if m:
        return m.group(1)
    return s


# İnsan benzeri bekleme aralıkları (saniye)
DELAY_NORMAL = (2.2, 5.5)        # Her istek sonrası
DELAY_SLOW = (7.0, 16.0)         # Bazen "sayfayı okuyor" (yaklaşık %12)
DELAY_COFFEE = (28.0, 72.0)      # Nadiren "kısa mola" (yaklaşık %3)
DELAY_LONG = (95.0, 185.0)       # Çok nadiren "uzun ara" (yaklaşık %0.8)


def human_like_delay():
    """
    Rastgele insan benzeri bekleme: çoğunlukla kısa, bazen orta, nadiren uzun.
    Süre önemli değil dediğin için gerekirse uzun bekleyebilir.
    """
    r = random.random()
    if r < 0.008:
        sec = random.uniform(*DELAY_LONG)
        print(f"  [uzun ara] {sec:.0f} sn bekleniyor...")
    elif r < 0.03:
        sec = random.uniform(*DELAY_COFFEE)
        print(f"  [molada] {sec:.0f} sn bekleniyor...")
    elif r < 0.12:
        sec = random.uniform(*DELAY_SLOW)
        print(f"  [yavaş] {sec:.1f} sn...")
    else:
        sec = random.uniform(*DELAY_NORMAL)
    time.sleep(sec)


def random_page_size():
    """Bazen sayfa boyutunu hafif değiştir (robot gibi hep 20 istememek)."""
    base = CONFIG["page_size"]
    r = random.random()
    if r < 0.05:
        return max(10, base + random.randint(-4, 4))
    if r < 0.15:
        return max(10, base + random.randint(-2, 2))
    return base


def load_cookie_from_file(script_dir):
    """cookie.txt varsa okuyup Cookie değerini döndürür (yoksa None)."""
    path = os.path.join(script_dir, "cookie.txt")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            line = f.read().strip().split("\n")[0].strip()
        if not line:
            return None
        if line.lower().startswith("cookie:"):
            line = line[7:].strip()
        return line if line else None
    except Exception:
        return None


def normalize_curl_line_continuations(text: str) -> str:
    """
    Windows cmd: satır sonu ^ ile devam. Bash: \\ ile devam. PowerShell: ` ile devam.
    Tek satıra yaklaştırır ki -H "cookie: ..." regex ile yakalansın.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    parts: List[str] = []
    buf = ""
    for line in lines:
        s = line.rstrip()
        if not s:
            continue
        if s.endswith("^"):
            buf = (buf + " " + s[:-1].rstrip()).strip()
            continue
        if len(s) > 1 and s.endswith("\\") and not s.endswith("\\\\"):
            buf = (buf + " " + s[:-1].rstrip()).strip()
            continue
        if s.endswith("`"):
            buf = (buf + " " + s[:-1].rstrip()).strip()
            continue
        line_merged = (buf + " " + s).strip() if buf else s
        buf = ""
        parts.append(line_merged)
    if buf:
        parts.append(buf)
    return " ".join(parts)


def extract_cookie_header_value(text: str):
    """
    -H "cookie: ...." veya -H 'cookie: ....' — değer içinde kaçış olabilir.
    Kısa [^'\"]+ ile uzun gerçek tarayıcı cookie'leri kaçabiliyor (çok satır/^).
    """
    for m in re.finditer(r"(?i)(?:-H|--header)\s*([\'\"])cookie\s*:\s*", text):
        q = m.group(1)
        i = m.end()
        out: List[str] = []
        while i < len(text):
            c = text[i]
            if c == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if c == q:
                val = "".join(out).strip()
                if len(val) > 15:
                    return val
                break
            out.append(c)
            i += 1
    return None


def load_token_from_file(script_dir):
    """
    token.txt varsa Colruyt auth token'ı döndürür.
    İçerik: sadece token string VEYA {"token": "...", "renewInSec": 376, "cookieDomain": "..."} JSON.
    """
    path = os.path.join(script_dir, "token.txt")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read().strip()
        if not raw:
            return None
        # JSON mu?
        if raw.startswith("{"):
            data = json.loads(raw)
            return data.get("token") or data.get("accessToken")
        # Tek satır token
        return raw.split("\n")[0].strip()
    except Exception:
        return None


def load_cookie_from_curl(script_dir):
    """
    curl.txt varsa içindeki cURL komutundan Cookie'yi çıkarır.
    Tarayıcıda: Network -> isteğe sağ tık -> Copy -> Copy as cURL (bash) -> curl.txt içine yapıştır.
    """
    path = os.path.join(script_dir, "curl.txt")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = normalize_curl_line_continuations(f.read())
        ck = extract_cookie_header_value(text)
        if ck:
            return ck
        for pattern in [
            r"-H\s+['\"][Cc][Oo][Oo][Kk][Ii][Ee]:\s*([^'\"]+)['\"]",
            r"--cookie\s+['\"]?([^'\"]+)['\"]?",
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None
    except Exception:
        return None


def load_headers_and_params_from_curl(script_dir):
    """
    curl.txt içinden:
    - URL query parametreleri (placeId, sort, isAvailable)
    - header'lar (x-cg-apikey, accept-language, user-agent vb.)
    - cookie (-b / --cookie)
    çıkarır.
    """
    path = os.path.join(script_dir, "curl.txt")
    if not os.path.isfile(path):
        return {}, {}
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = normalize_curl_line_continuations(f.read())

        headers = {}
        params = {}

        url_match = re.search(r"https?://[^\s\"']+", text)
        if url_match:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(url_match.group(0))
            query = parse_qs(parsed.query)
            for key in ("placeId", "sort", "isAvailable"):
                value = query.get(key)
                if value and value[0]:
                    v = value[0]
                    if key == "placeId":
                        v = sanitize_place_id(v) or v
                    params[key] = v

        # -H / --header "key: value" — cookie satırı uzun olabilir; cookie için ayrıca extract_cookie_header_value
        for m in re.finditer(r"(?:-H|--header)\s+['\"]([^'\"]+)['\"]", text, re.IGNORECASE):
            hv = m.group(1)
            if ":" not in hv:
                continue
            k, v = hv.split(":", 1)
            k, v = k.strip(), v.strip()
            if not k or not v:
                continue
            if k.lower() == "cookie":
                headers["Cookie"] = v
            else:
                headers[k] = v

        cookie_match = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
        if cookie_match and not headers.get("Cookie"):
            headers["Cookie"] = cookie_match.group(1).strip()

        if not headers.get("Cookie"):
            loose = extract_cookie_header_value(text)
            if loose:
                headers["Cookie"] = loose

        if "x-cg-apikey" in headers and "X-CG-APIKey" not in headers:
            headers["X-CG-APIKey"] = headers["x-cg-apikey"]
        if "accept" in headers and "Accept" not in headers:
            headers["Accept"] = headers["accept"]
        if "user-agent" in headers and "User-Agent" not in headers:
            headers["User-Agent"] = headers["user-agent"]
        if "accept-language" in headers and "Accept-Language" not in headers:
            headers["Accept-Language"] = headers["accept-language"]
        if "referer" in headers and "Referer" not in headers:
            headers["Referer"] = headers["referer"]
        if "origin" in headers and "Origin" not in headers:
            headers["Origin"] = headers["origin"]

        return headers, params
    except Exception:
        return {}, {}


def apply_place_id_from_curl(curl_params: dict, args) -> None:
    """curl.txt placeId; komut satırında --place-id varsa onu koru."""
    pid = curl_params.get("placeId")
    if not pid:
        return
    if getattr(args, "place_id", None) and str(args.place_id).strip():
        return
    CONFIG["place_id"] = sanitize_place_id(pid) or str(pid).strip().rstrip("^").strip()
    print(f"  placeId curl.txt üzerinden alındı: {CONFIG['place_id']}\n")


def setup_colruyt_http(script_dir: str, args):
    """
    Cookie / token / curl.txt birleşimi ve sorgu ekleri.
    Dönüş: (headers, curl_params, extra_params).

    curl.txt'te tam tarayıcı Cookie'si varken token.txt eklemek, eski token ile çakışıp 406 üretebilir;
    varsayılan: curl Cookie tek başına ( --merge-token ile eski birleştirme ).
    """
    headers = build_api_headers_base()
    curl_path = os.path.join(script_dir, "curl.txt")
    curl_file_ok = os.path.isfile(curl_path)
    curl_headers, curl_params = load_headers_and_params_from_curl(script_dir)
    # Chrome Windows: cookie başlığı kaçarsa aynı dosyadan tekrar dene
    if curl_file_ok and not (curl_headers.get("Cookie") or "").strip():
        cj = load_cookie_from_curl(script_dir)
        if cj:
            curl_headers["Cookie"] = cj
    if curl_file_ok and (curl_headers or curl_params):
        headers.update(curl_headers)
        print("  curl.txt bulundu; header/cookie (varsa) ve URL parametreleri yüklendi.\n")
        if not (headers.get("Cookie") or "").strip():
            print(
                "  UYARI: curl.txt içinden Cookie çıkarılamadı (çok satırlı/^ ile cmd kopyası bazen bozulur). "
                "Şunlardan biri: (1) Chrome/Edge -> Copy as cURL (**bash**), tek seferde yapıştırın. "
                "(2) Request Headers -> Cookie değerini doğrudan cookie.txt dosyasına tek satır yapıştırın.\n"
            )
    cookie_from_curl = bool((curl_headers.get("Cookie") or "").strip())
    cookie = load_cookie_from_file(script_dir) or load_cookie_from_curl(script_dir)
    token = load_token_from_file(script_dir)
    cookie_base = (headers.get("Cookie") or "").strip() or (cookie or "").strip()
    merge_token = bool(getattr(args, "merge_token", False))

    if token:
        if cookie_from_curl and not merge_token:
            headers["Cookie"] = cookie_base
            print(
                "  curl.txt Cookie tek başına kullanılıyor; token.txt eklenmedi "
                "(ek token sık 406 yapar). Zorunluysanız: --merge-token\n"
            )
        elif cookie_base:
            if "token=" in cookie_base.lower():
                headers["Cookie"] = cookie_base
                print("  token.txt bulundu; mevcut Cookie içinde token= zaten var (curl/cookie öncelikli).\n")
            else:
                cookie_part = f"token={token}"
                headers["Cookie"] = f"{cookie_base.rstrip(';')}; {cookie_part}"
                print("  token.txt bulundu; tarayıcı Cookie'sine token eklendi.\n")
        else:
            headers["Cookie"] = f"token={token}"
            print(
                "  token.txt bulundu; ancak tarayıcı oturum çerezi YOK.\n"
                "  Colruyt çoğu zaman sadece token= ile 406 döner — lütfen curl.txt veya cookie.txt ekleyin:\n"
                "  F12 -> Network -> product-search-prs -> Copy as cURL -> market_fiyat_cekici/curl.txt\n"
            )
    elif cookie_base:
        headers["Cookie"] = cookie_base
        print("  Oturum (Cookie) bulundu; istek atılıyor.\n")
    else:
        print("  token.txt / cookie.txt / curl.txt yok; oturum olmadan denenecek (406 alırsanız token veya cookie gerekir).\n")

    extra_params = {}
    if args.minimal_query:
        print("  --minimal-query: İstekte yalnızca placeId + skip + size + isAvailable=true.\n")
    else:
        if "sort" in curl_params:
            extra_params["sort"] = curl_params["sort"]
            print("  curl.txt sort parametresi kullanılıyor; tam katalog için: --minimal-query\n")
        if "isAvailable" in curl_params:
            extra_params["isAvailable"] = curl_params["isAvailable"]

    apply_place_id_from_curl(curl_params, args)
    return headers, curl_params, extra_params


def _probe_response_hint(resp) -> None:
    """Hata gövdesinden kısa özet (PII içermemeli; genelde JSON/HTML hata metni)."""
    try:
        t = (resp.text or "")[:420].replace("\n", " ").strip()
        if t:
            print(f"  Yanıt gövdesi (kısaltılmış): {t}...")
    except Exception:
        pass


def run_probe_once(session, headers: dict, extra_params: dict) -> int:
    """Tek sayfa dener; başarıda 0, aksi 1. JSON çıktı dosyası yazılmaz."""
    size = 10
    skip = 0
    params = {
        "placeId": CONFIG["place_id"],
        "size": size,
        "skip": skip,
        "isAvailable": "true",
    }
    if extra_params:
        params.update(extra_params)
        params["size"] = size
        params["skip"] = skip

    max_r = int(CONFIG.get("max_retries") or 4)
    for attempt in range(1, max_r + 1):
        try:
            print(
                f"  [probe] Deneme {attempt}/{max_r}: placeId={CONFIG['place_id']} size={size} skip={skip}"
            )
            resp = session.get(
                CONFIG["base_url"],
                params=params,
                headers=headers,
                timeout=min(35, int(CONFIG.get("request_timeout") or 25)),
            )
            print(f"  [probe] HTTP {resp.status_code}")
            if resp.status_code == 406:
                print(
                    "  406 ipuçları: (1) curl.txt’i tarayıcıdan AZ ÖNCE yeniden kopyalayın. "
                    "(2) İstekteki X-CG-APIKey ile betikteki CONFIG aynı mı kontrol edin. "
                    "(3) token.txt’yi geçici taşıyıp yalnız curl ile deneyin (varsayılan artık curl Cookie tek başına)."
                )
            if resp.status_code == 429:
                wait = 45 + random.uniform(0, 25)
                print(f"  Rate limit; {wait:.0f} sn bekleniyor...")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                _probe_response_hint(resp)
                return 1
            data = resp.json()
        except Exception as e:
            print(f"  [probe] İstek/parse hatası: {e}")
            return 1
        prods = data.get("products") or []
        tf = data.get("totalProductsFound")
        print(f"  [probe] OK — sayfadaki ürün: {len(prods)}, totalProductsFound: {tf}")
        if prods:
            p0 = prods[0]
            pr = p0.get("price") or {}
            print(
                f"  [probe] Örnek: retailProductNumber={p0.get('retailProductNumber')!r} "
                f"basicPrice={pr.get('basicPrice')!r} name={(p0.get('name') or '')[:60]!r}"
            )
        return 0
    return 1


def load_checkpoint(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_checkpoint(path, skip, page_num, products, seen_ids, total_reported):
    payload = {
        "saved_at": datetime.now().isoformat(),
        "skip": skip,
        "page_num": page_num,
        "total_reported": total_reported,
        "products": products,
        "seen_ids": list(seen_ids),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def fetch_page(session, skip, size, headers, extra_params=None):
    """Tek bir sayfa döndürür (dict) veya hata durumunda None."""
    params = {
        "placeId": CONFIG["place_id"],
        "size": size,
        "skip": skip,
        "isAvailable": "true",
    }
    if extra_params:
        params.update(extra_params)
        params["size"] = size
        params["skip"] = skip
    url = CONFIG["base_url"]
    max_r = int(CONFIG["max_retries"] or 4)
    for attempt in range(max_r):
        try:
            if attempt > 0:
                print(f"  Yeniden deneme {attempt + 1}/{max_r} (skip={skip}, size={size})...")
            resp = session.get(
                url,
                params=params,
                headers=headers,
                timeout=CONFIG["request_timeout"],
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait = 60 * (2 ** attempt) + random.uniform(0, 30)
                print(f"  Rate limit (429); {wait:.0f} sn bekleniyor...")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                wait = 30 * (2 ** attempt) + random.uniform(0, 20)
                print(f"  Sunucu hatası {resp.status_code}; {wait:.0f} sn sonra tekrar (deneme {attempt + 1}/{max_r})...")
                time.sleep(wait)
                continue
            if resp.status_code == 401:
                print("  401 Unauthorized: Oturum veya API anahtarı geçersiz olabilir.")
                print("  cookie.txt / curl.txt içeriğini tarayıcıdan yenileyin (COOKIE_NASIL_BULUNUR.txt).")
                _probe_response_hint(resp)
                return None
            if resp.status_code == 403:
                print("  403 Forbidden: Erişim reddedildi — genelde süresi dolmuş veya eksik Cookie.")
                print("  colruyt.be'de giriş yapıp Network'ten product-search-prs -> Copy as cURL -> curl.txt güncelleyin.")
                _probe_response_hint(resp)
                return None
            if resp.status_code == 406:
                print("  406 Not Acceptable: Oturum (Cookie) gerekli veya istek reddedildi.")
                print("  Token süresi dolmuş olabilir (~6 dk). Yeni token alıp token.txt güncelleyin VEYA tarayıcıdan tam Cookie kullanın:")
                print("  F12 -> Network -> product-search-prs isteğine sağ tık -> Copy -> Copy as cURL (bash) -> curl.txt dosyasına yapıştırın.")
                _probe_response_hint(resp)
                return None
            print(f"  HTTP {resp.status_code}")
            _probe_response_hint(resp)
            return None
        except Exception as e:
            wait = 15 * (2 ** attempt) + random.uniform(0, 10)
            print(f"  İstek hatası: {e}; {wait:.0f} sn sonra tekrar (deneme {attempt + 1}/{max_r})...")
            time.sleep(wait)
    return None


def _first_promotion_dict(promo_list):
    if not promo_list or not isinstance(promo_list, list):
        return None
    pr0 = promo_list[0]
    return pr0 if isinstance(pr0, dict) else None


def _pick_promo_date(pr: dict, *candidates: str):
    """İlk dolu alanı döndür (Colruyt BFF alan adları sürüme göre değişebilir)."""
    if not pr:
        return None
    for key in candidates:
        v = pr.get(key)
        if v is not None and str(v).strip():
            return v
    return None


def product_to_platform(p):
    """API ürün objesini platformda kullanacağın sade formata çevirir."""
    price = p.get("price") or {}
    promo = p.get("promotion") or []
    pr0 = _first_promotion_dict(promo)
    promo_start = _pick_promo_date(
        pr0,
        "publicationStartDate",
        "validFrom",
        "startDate",
        "promotionStartDate",
        "fromDate",
        "beginDate",
    )
    promo_end = _pick_promo_date(
        pr0,
        "publicationEndDate",
        "validTo",
        "endDate",
        "promotionEndDate",
        "toDate",
    )
    return {
        "retailProductNumber": p.get("retailProductNumber"),
        "technicalArticleNumber": p.get("technicalArticleNumber"),
        "name": p.get("name"),
        "brand": p.get("brand"),
        "seoBrand": p.get("seoBrand"),
        "LongName": p.get("LongName"),
        "content": p.get("content"),
        "basicPrice": price.get("basicPrice"),
        "quantityPrice": price.get("quantityPrice"),
        "quantityPriceQuantity": price.get("quantityPriceQuantity"),
        "pricePerUOM": price.get("pricePerUOM"),
        "measurementUnit": price.get("measurementUnit"),
        "activationDate": price.get("activationDate"),
        "isRedPrice": price.get("isRedPrice"),
        "isPromoActive": price.get("isPromoActive"),
        "inPromo": p.get("inPromo", False),
        "promoPublicationStart": promo_start,
        "promoPublicationEnd": promo_end,
        "topCategoryName": p.get("topCategoryName"),
        "topCategoryId": p.get("topCategoryId"),
        "nutriScore": p.get("nutriScore"),
        "countryOfOrigin": p.get("countryOfOrigin"),
        "isPriceAvailable": p.get("isPriceAvailable"),
        "isAvailable": p.get("isAvailable"),
    }


def _parse_args():
    ap = argparse.ArgumentParser(description="Colruyt BE — product-search-prs ile katalog + fiyat")
    ap.add_argument("--no-pause", action="store_true", help="Bitince Enter bekleme")
    ap.add_argument("--max-products", type=int, default=None, help="CONFIG max_products üzerine yazar")
    ap.add_argument("--place-id", type=str, default=None, help="Mağaza placeId (curl.txt yoksa)")
    ap.add_argument(
        "--fast",
        action="store_true",
        help="Daha kısa gecikme aralıkları (dikkat: rate limit riski)",
    )
    ap.add_argument(
        "--minimal-query",
        action="store_true",
        help="curl.txt'ten yalnızca placeId kullanılır; sort/isAvailable ekleri eklenmez (tam katalog için önerilir).",
    )
    ap.add_argument(
        "--probe",
        action="store_true",
        help="Tek sayfa dene; HTTP ve örnek ürün yazdır, JSON dosyası oluşturma (hızlı 200/403/406 testi).",
    )
    ap.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="X-CG-APIKey (varsayılan CONFIG['cg_api_key']; site değiştiyse tarayıcı isteğinden kopyalayın).",
    )
    ap.add_argument(
        "--merge-token",
        action="store_true",
        help="curl.txt Cookie olsa bile token.txt ekle (varsayılan: curl Cookie tek başına — ek token sık 406 yapar).",
    )
    return ap.parse_args()


def main():
    global DELAY_NORMAL, DELAY_SLOW, DELAY_COFFEE, DELAY_LONG

    args = _parse_args()
    if args.max_products is not None and args.max_products > 0:
        CONFIG["max_products"] = int(args.max_products)
    if args.place_id:
        CONFIG["place_id"] = sanitize_place_id(args.place_id) or str(args.place_id).strip().rstrip("^").strip()
    if args.api_key and str(args.api_key).strip():
        CONFIG["cg_api_key"] = str(args.api_key).strip()
    # Playwright aynı dict referansını import edebilir; anahtar güncellenince senkron tut
    API_HEADERS_BASE.clear()
    API_HEADERS_BASE.update(build_api_headers_base())

    if args.fast:
        DELAY_NORMAL = (0.6, 1.6)
        DELAY_SLOW = (2.0, 4.5)
        DELAY_COFFEE = (8.0, 18.0)
        DELAY_LONG = (25.0, 55.0)

    try:
        import requests
    except ImportError:
        print("HATA: requests yüklü değil. Lütfen: pip install requests")
        if not args.no_pause:
            input("\nÇıkmak için Enter'a basın...")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    checkpoint_path = os.path.join(cikti_dir, "colruyt_checkpoint.json")

    if args.probe:
        print("Colruyt Belçika — PROBE (tek sayfa, çıktı JSON yazılmaz)\n")
        headers, _, extra_params = setup_colruyt_http(script_dir, args)
        session = requests.Session()
        code = run_probe_once(session, headers, extra_params)
        if not args.no_pause:
            input("\nÇıkmak için Enter'a basın...")
        raise SystemExit(code)

    print("Colruyt Belçika - API ile ürün + fiyat çekimi")
    print("İnsan benzeri aralıklarla istek atılıyor (bazen yavaş, nadiren uzun mola).\n")

    headers, _, extra_params = setup_colruyt_http(script_dir, args)

    session = requests.Session()
    all_products = []
    seen_ids = set()
    skip = 0
    page_num = 0
    total_reported = None
    stale_pages = 0
    checkpoint = load_checkpoint(checkpoint_path)
    if checkpoint:
        all_products = checkpoint.get("products") or []
        seen_ids = set(checkpoint.get("seen_ids") or [])
        skip = int(checkpoint.get("skip") or 0)
        page_num = int(checkpoint.get("page_num") or 0)
        total_reported = checkpoint.get("total_reported")
        print(f"  Checkpoint bulundu; kaldığı yerden devam: skip={skip}, ürün={len(all_products)}\n")

    start_time = time.time()

    while len(all_products) < CONFIG["max_products"]:
        # Nadiren UA değiştir (aynı oturumda tamamen rastgele değil)
        if page_num > 0 and random.random() < 0.07:
            headers["User-Agent"] = random.choice(CHROME_UA_POOL)

        page_num += 1
        size = random_page_size()
        data = fetch_page(session, skip, size, headers, extra_params=extra_params)

        if data is None:
            print("  Sayfa alınamadı; çıkılıyor.")
            break

        products = data.get("products") or []
        if "totalProductsFound" in data:
            try:
                tf_new = int(data["totalProductsFound"])
            except (TypeError, ValueError):
                tf_new = None
            if tf_new is not None and tf_new >= 0:
                if total_reported is None:
                    total_reported = tf_new
                    if tf_new > 0:
                        print(f"  Toplam ürün (API): {total_reported}\n")
                else:
                    try:
                        old_tf = int(total_reported)
                        if tf_new > old_tf:
                            total_reported = tf_new
                            print(f"  Toplam ürün (API) güncellendi: {total_reported}\n")
                    except (TypeError, ValueError):
                        pass

        if not products:
            print(f"  Sayfa {page_num}: 0 ürün (liste bitti).")
            break

        added = 0
        for p in products:
            rpn = p.get("retailProductNumber")
            if rpn and rpn not in seen_ids:
                seen_ids.add(rpn)
                all_products.append(product_to_platform(p))
                added += 1

        print(f"  Sayfa {page_num} (skip={skip}, size={size}): +{added} ürün, toplam {len(all_products)}")

        if added == 0:
            stale_pages += 1
            print(f"  Uyarı: yeni ürün yok ({stale_pages}/{CONFIG['stale_page_limit']})")
            if stale_pages >= CONFIG["stale_page_limit"]:
                print("  Üst üste yeni ürün gelmedi; güvenli çıkış yapılıyor.")
                break
        else:
            stale_pages = 0

        if total_reported is not None:
            try:
                tr = int(total_reported)
                if tr > 0 and len(all_products) >= tr:
                    print(f"  Hedef ürün sayısına ulaşıldı ({tr} benzersiz).")
                    break
            except (TypeError, ValueError):
                pass

        if len(products) < size:
            break

        skip += len(products)
        if page_num % CONFIG["checkpoint_every_pages"] == 0:
            save_checkpoint(checkpoint_path, skip, page_num, all_products, seen_ids, total_reported)
            print("  Ara kayıt alındı (checkpoint).")
        human_like_delay()

    elapsed = time.time() - start_time
    print(f"\nToplam: {len(all_products)} benzersiz ürün, {elapsed/60:.1f} dakika.")

    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dosya_adi = f"colruyt_be_producten_{tarih}.json"
    dosya_yolu = os.path.join(cikti_dir, dosya_adi)

    cikti = {
        "kaynak": "Colruyt Belçika",
        "chain_slug": "colruyt_be",
        "country_code": "BE",
        "yontem": "product-search-prs API",
        "placeId": CONFIG["place_id"],
        "cekilme_tarihi": datetime.now().isoformat(),
        "sure_dakika": round(elapsed / 60, 1),
        "urun_sayisi": len(all_products),
        "not_fiyat_gecerliligi": "Fiyatlar activationDate ile güncellenir; mağaza (placeId) bazlıdır.",
        "not_indirim": "inPromo / isPromoActive; promoPublicationStart / promoPublicationEnd kampanya geçerlilik başlangıç ve bitiş (API alan adlarına bağlı).",
        "urunler": all_products,
    }

    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2)

    if os.path.isfile(checkpoint_path):
        try:
            os.remove(checkpoint_path)
        except Exception:
            pass

    print(f"Kaydedildi: {dosya_yolu}")
    if not args.no_pause:
        input("\nÇıkmak için Enter'a basın...")


if __name__ == "__main__":
    main()
