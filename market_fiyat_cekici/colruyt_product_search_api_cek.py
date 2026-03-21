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

# -----------------------------------------------------------------------------
# AYARLAR (gerekirse değiştir)
# -----------------------------------------------------------------------------
CONFIG = {
    "base_url": "https://apip.colruyt.be/gateway/emec.colruyt.protected.bffsvc/cg/nl/api/product-search-prs",
    "place_id": "762",           # Mağaza (tarayıcıdan kopyaladığın placeId)
    "page_size": 20,             # Sayfa başına ürün (sitedeki gibi 20; bazen 18–24 arası random)
    "max_products": 15000,       # Maksimum toplanacak ürün (12.000+ için yeterli)
    "request_timeout": 25,       # İstek zaman aşımı (saniye)
    "max_retries": 4,           # Hata durumunda deneme sayısı
    "checkpoint_every_pages": 5, # Kaç sayfada bir ara kayıt
    "stale_page_limit": 3,       # Üst üste yeni ürün gelmeyen sayfa limiti
}

# API key ve tarayıcıya benzeyen header'lar
# Cookie: script ile aynı klasörde cookie.txt oluşturup tarayıcıdan kopyaladığınız değeri yapıştırın
API_HEADERS_BASE = {
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
    "X-CG-APIKey": "a8ylmv13-b285-4788-9e14-0f79b7ed2411",
}

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
    Tarayıcıda: Network → isteğe sağ tık → Copy → Copy as cURL (bash) → curl.txt içine yapıştır.
    """
    path = os.path.join(script_dir, "curl.txt")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        # -H 'Cookie: ...' veya -H "Cookie: ..." ara
        for pattern in [
            r"-H\s+['\"]Cookie:\s*([^'\"]+)['\"]",
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
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

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
                    params[key] = value[0]

        # -H "key: value" ve -H 'key: value'
        for m in re.finditer(r"-H\s+['\"]([^'\"]+)['\"]", text, re.IGNORECASE):
            hv = m.group(1)
            if ":" not in hv:
                continue
            k, v = hv.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k and v:
                headers[k] = v

        cookie_match = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", text, re.IGNORECASE)
        if cookie_match:
            headers["Cookie"] = cookie_match.group(1).strip()

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
    for attempt in range(CONFIG["max_retries"]):
        try:
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
                print(f"  Sunucu hatası {resp.status_code}; {wait:.0f} sn sonra tekrar...")
                time.sleep(wait)
                continue
            if resp.status_code == 401:
                print("  401 Unauthorized: API anahtarı veya oturum gerekebilir (tarayıcıdan Cookie kopyala).")
                return None
            if resp.status_code == 406:
                print("  406 Not Acceptable: Oturum (Cookie) gerekli.")
                print("  Token süresi dolmuş olabilir (~6 dk). Yeni token alıp token.txt güncelleyin VEYA tarayıcıdan tam Cookie kullanın:")
                print("  F12 → Network → product-search-prs isteğine sağ tık → Copy → Copy as cURL (bash) → curl.txt dosyasına yapıştırın.")
                try:
                    body = resp.text[:500] if resp.text else ""
                    if body:
                        print(f"  Sunucu yanıtı (kısaca): {body[:300]}...")
                except Exception:
                    pass
                return None
            print(f"  HTTP {resp.status_code}")
            return None
        except Exception as e:
            wait = 15 * (2 ** attempt) + random.uniform(0, 10)
            print(f"  İstek hatası: {e}; {wait:.0f} sn sonra tekrar...")
            time.sleep(wait)
    return None


def product_to_platform(p):
    """API ürün objesini platformda kullanacağın sade formata çevirir."""
    price = p.get("price") or {}
    promo = p.get("promotion") or []
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
        "promoPublicationEnd": promo[0].get("publicationEndDate") if promo else None,
        "topCategoryName": p.get("topCategoryName"),
        "topCategoryId": p.get("topCategoryId"),
        "nutriScore": p.get("nutriScore"),
        "countryOfOrigin": p.get("countryOfOrigin"),
        "isPriceAvailable": p.get("isPriceAvailable"),
        "isAvailable": p.get("isAvailable"),
    }


def main():
    try:
        import requests
    except ImportError:
        print("HATA: requests yüklü değil. Lütfen: pip install requests")
        input("\nÇıkmak için Enter'a basın...")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)
    checkpoint_path = os.path.join(cikti_dir, "colruyt_checkpoint.json")

    print("Colruyt Belçika - API ile ürün + fiyat çekimi")
    print("İnsan benzeri aralıklarla istek atılıyor (bazen yavaş, nadiren uzun mola).\n")

    headers = dict(API_HEADERS_BASE)
    curl_headers, curl_params = load_headers_and_params_from_curl(script_dir)
    if curl_headers:
        headers.update(curl_headers)
        print("  curl.txt bulundu; header/cookie bilgileri yüklendi.")
    cookie = load_cookie_from_file(script_dir) or load_cookie_from_curl(script_dir)
    token = load_token_from_file(script_dir)
    if token:
        # Colruyt: token'ı sadece Cookie olarak gönder (Bearer bazen 406 tetikliyor)
        cookie_part = f"token={token}"
        headers["Cookie"] = (cookie or "") + ("; " if cookie else "") + cookie_part
        print("  token.txt bulundu; token ile istek atılıyor.\n")
    elif cookie:
        headers["Cookie"] = cookie
        print("  Oturum (Cookie) bulundu; istek atılıyor.\n")
    else:
        print("  token.txt / cookie.txt / curl.txt yok; oturum olmadan denenecek (406 alırsanız token veya cookie gerekir).\n")

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

    if curl_params.get("placeId"):
        CONFIG["place_id"] = str(curl_params["placeId"])
        print(f"  placeId curl.txt üzerinden alındı: {CONFIG['place_id']}\n")

    extra_params = {}
    if "sort" in curl_params:
        extra_params["sort"] = curl_params["sort"]
    if "isAvailable" in curl_params:
        extra_params["isAvailable"] = curl_params["isAvailable"]
    start_time = time.time()

    while len(all_products) < CONFIG["max_products"]:
        page_num += 1
        size = random_page_size()
        data = fetch_page(session, skip, size, headers, extra_params=extra_params)

        if data is None:
            print("  Sayfa alınamadı; çıkılıyor.")
            break

        products = data.get("products") or []
        if total_reported is None and "totalProductsFound" in data:
            total_reported = data["totalProductsFound"]
            print(f"  Toplam ürün (API): {total_reported}\n")

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
        "yontem": "product-search-prs API",
        "placeId": CONFIG["place_id"],
        "cekilme_tarihi": datetime.now().isoformat(),
        "sure_dakika": round(elapsed / 60, 1),
        "urun_sayisi": len(all_products),
        "not_fiyat_gecerliligi": "Fiyatlar activationDate ile güncellenir; mağaza (placeId) bazlıdır.",
        "not_indirim": "inPromo / isPromoActive alanları kampanya bilgisini verir.",
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
