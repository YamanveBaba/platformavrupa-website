# -*- coding: utf-8 -*-
"""
Lidl BE — Mindshift arama API (/q/api/search) ile kategori bazli urun + fiyat.

Tarayicidan kopyalanan calisan istek: offset/fetchsize + category.id + Cookie + Referer.
API yanit govdesinde (Preview/Response JSON) cerez yok; F12 Network -> q/api/search ->
Headers -> Request Headers -> cookie satirini kopyalayin.
GTM /google analytics istekleri (t/gtm/g/collect) urun kaynagi degildir; kullanmayin.

Oncelik:
1) Script ile ayni klasorde lidl_cookie.txt (tek satir Cookie: degeri veya ham cerez stringi)
2) lidl_be_api_categories.txt — satir basina tam kategori liste URL'si, ornek:
   https://www.lidl.be/c/nl-BE/voeding-drank/s10068374

Cikti: cikti/lidl_be_producten_*.json — json_to_supabase_yukle.py ile uyumlu alanlar.
Kapsam: (1) Kok API (category.id yok) ile facet'ten kok kategoriler (2) Her kategori ilk sayfasinda
facet agaci ozyinelemeli gezilir (3) lidl_be_api_categories.txt tohumlari. --no-bootstrap ile (1) kapali.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import requests
except ImportError:
    raise SystemExit("HATA: pip install requests")

CONFIG = {
    "base": "https://www.lidl.be",
    "api_path": "/q/api/search",
    "fetchsize": 12,
    "version": "2.1.0",
    "locale": "nl_BE",
    "assortment": "BE",
    "request_timeout": 45,
    "delay": (0.9, 2.4),
    "delay_slow": (3.0, 6.5),
}


def human_delay() -> None:
    if random.random() < 0.08:
        time.sleep(random.uniform(*CONFIG["delay_slow"]))
    else:
        time.sleep(random.uniform(*CONFIG["delay"]))


def load_cookie(script_dir: str) -> Optional[str]:
    path = os.path.join(script_dir, "lidl_cookie.txt")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("cookie:"):
                line = line[7:].strip()
            if len(line) > 15 and "=" in line:
                return line
    return None


def load_category_urls(script_dir: str) -> List[str]:
    path = os.path.join(script_dir, "lidl_be_api_categories.txt")
    if not os.path.isfile(path):
        return []
    out: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#"):
                out.append(s.split("?")[0])
    return out


def category_id_from_url(url: str) -> Optional[int]:
    """Lidl /c/.../s123 ve /h/.../h123 son segment."""
    matches = list(re.finditer(r"/[sh](\d+)(?=/|$|\?)", url, re.I))
    if not matches:
        return None
    try:
        return int(matches[-1].group(1))
    except ValueError:
        return None


def referer_for_offset(base_list_url: str, offset: int) -> str:
    b = base_list_url.split("?")[0].rstrip("/")
    return f"{b}?offset={int(offset)}"


def collect_dict_lists(obj: Any, depth: int = 0, out: Optional[List[List[dict]]] = None) -> List[List[dict]]:
    if out is None:
        out = []
    if depth > 18:
        return out
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj):
            out.append(obj)
        for x in obj:
            collect_dict_lists(x, depth + 1, out)
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_dict_lists(v, depth + 1, out)
    return out


def price_like_in_dict(d: dict) -> bool:
    blob = json.dumps(d, ensure_ascii=False)[:8000]
    if re.search(r'"price"\s*:\s*(\{|[\d"])', blob, re.I):
        return True
    if re.search(r'"finalPrice"|"salesPrice"|"displayPrice"|"strike"', blob, re.I):
        return True
    if re.search(r'\d+[.,]\d{2}', blob):
        return True
    return False


def score_product_list(lst: List[dict]) -> int:
    if len(lst) < 1:
        return 0
    sample = lst[: min(5, len(lst))]
    sc = len(lst)
    for it in sample:
        if not isinstance(it, dict):
            continue
        if price_like_in_dict(it):
            sc += 8
        keys = " ".join(it.keys()).lower()
        if any(k in keys for k in ("name", "title", "product", "label", "brand")):
            sc += 3
    return sc


def pick_product_list(root: Any) -> List[dict]:
    lists = collect_dict_lists(root)
    if not lists:
        return []
    best = max(lists, key=score_product_list)
    if score_product_list(best) < 8:
        return []
    return best


def _facet_category_walk(
    nodes: List[dict],
    skip_id: Optional[int],
    seen: Set[int],
    out: List[Tuple[int, str]],
    depth: int,
) -> None:
    if depth > 24:
        return
    for n in nodes:
        if not isinstance(n, dict):
            continue
        raw_v = n.get("value")
        scid: Optional[int] = None
        if raw_v is not None:
            try:
                scid = int(str(raw_v).strip())
            except (TypeError, ValueError):
                scid = None
        try:
            cnt = int(n.get("count") or 0)
        except (TypeError, ValueError):
            cnt = 0
        lab = str(n.get("label") or scid or "").strip() or "?"
        if (
            scid is not None
            and (skip_id is None or scid != skip_id)
            and scid not in seen
            and cnt > 0
        ):
            seen.add(scid)
            out.append((scid, lab))
        ch = n.get("children")
        if isinstance(ch, list):
            chd = [x for x in ch if isinstance(x, dict)]
            if chd:
                _facet_category_walk(chd, skip_id, seen, out, depth + 1)


def discover_category_ids_from_facets(data: dict, skip_id: Optional[int]) -> List[Tuple[int, str]]:
    """category facet: topvalues+values kokunden tum agac (count>0 olan id'ler)."""
    out: List[Tuple[int, str]] = []
    seen: Set[int] = set()
    facets = data.get("facets")
    if not isinstance(facets, list):
        return out
    for fc in facets:
        if not isinstance(fc, dict) or fc.get("code") != "category":
            continue
        roots: List[dict] = []
        for key in ("topvalues", "values"):
            v = fc.get(key)
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, dict):
                        roots.append(x)
        _facet_category_walk(roots, skip_id, seen, out, 0)
    return out


def extract_gridbox_rows(data: dict) -> List[dict]:
    """Gercek API: kok 'items' -> her urun 'gridbox.data'."""
    items = data.get("items")
    if not isinstance(items, list):
        return []
    rows: List[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("type") != "product" and it.get("resultClass") != "product":
            continue
        gb = it.get("gridbox")
        if not isinstance(gb, dict):
            continue
        row = gb.get("data")
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _to_price_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v <= 0 or v > 5000:
        return None
    return v


def _promo_dates_from_mindshift_dict(blob: Any) -> Tuple[Optional[str], Optional[str]]:
    """İndirim/kampanya objesinden metin tarih alanları (API sürümüne göre değişebilir)."""
    if not isinstance(blob, dict):
        return None, None

    def pick(d: dict, *keys: str) -> Optional[str]:
        for k in keys:
            v = d.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return None

    start = pick(
        blob,
        "validFrom",
        "startDate",
        "fromDate",
        "promotionStart",
        "promotionStartDate",
        "beginDate",
        "discountStart",
    )
    end = pick(
        blob,
        "validTo",
        "endDate",
        "toDate",
        "promotionEnd",
        "promotionEndDate",
        "discountEnd",
    )
    if start or end:
        return start, end

    start_g, end_g = None, None
    for k, v in blob.items():
        if not isinstance(v, (str, int, float)):
            continue
        vs = str(v).strip()
        if not vs:
            continue
        kl = k.lower()
        if start_g is None and "start" in kl and ("promo" in kl or "discount" in kl or "valid" in kl):
            start_g = vs
        if end_g is None and ("end" in kl or "until" in kl) and ("promo" in kl or "discount" in kl or "valid" in kl):
            end_g = vs
    return start_g, end_g


def normalize_gridbox_data(data: dict, category_label: str) -> Optional[dict]:
    """gridbox.data (Mindshift ldt-searcher) -> json_to_supabase satiri."""
    pid = data.get("productId") if data.get("productId") is not None else data.get("itemId")
    if pid is None:
        return None
    try:
        pkey = f"p{int(pid)}"
    except (TypeError, ValueError):
        return None

    name = (data.get("fullTitle") or data.get("title") or "").strip() or pkey

    brand = None
    b = data.get("brand")
    if isinstance(b, dict) and b.get("name"):
        brand = str(b.get("name") or "").strip() or None

    path = data.get("canonicalUrl") or data.get("canonicalPath") or ""
    url_s = ""
    if isinstance(path, str):
        if path.startswith("http"):
            url_s = path[:2000]
        elif path.startswith("/"):
            url_s = (CONFIG["base"] + path)[:2000]

    unit_content = None
    kf = data.get("keyfacts")
    if isinstance(kf, dict):
        unit_content = (str(kf.get("supplementalDescription") or "").strip() or None)
        if unit_content:
            unit_content = unit_content[:200]

    pb = data.get("price")
    basic_f: Optional[float] = None
    promo_f: Optional[float] = None
    in_promo = False

    promo_start_s: Optional[str] = None
    promo_end_s: Optional[str] = None

    if isinstance(pb, dict):
        cur = _to_price_float(pb.get("price"))
        old = _to_price_float(pb.get("oldPrice"))
        disc = pb.get("discount") if isinstance(pb.get("discount"), dict) else {}
        deleted = _to_price_float(disc.get("deletedPrice"))
        show_disc = bool(disc.get("showDiscount"))
        pct = disc.get("percentageDiscount")

        ps, pe = _promo_dates_from_mindshift_dict(disc)
        if ps:
            promo_start_s = ps
        if pe:
            promo_end_s = pe

        strike = old if old and old > 0 else None
        if strike is None and deleted and deleted > 0:
            strike = deleted

        if cur is not None:
            if strike is not None and strike > cur and (show_disc or (pct and int(pct or 0) > 0)):
                basic_f, promo_f, in_promo = strike, cur, True
            elif strike is not None and strike > cur:
                basic_f, promo_f, in_promo = strike, cur, True
            else:
                basic_f = cur

    if basic_f is None and isinstance(data.get("lidlPlus"), list) and data["lidlPlus"]:
        lp0 = data["lidlPlus"][0]
        if isinstance(lp0, dict):
            lpp = lp0.get("price")
            if isinstance(lpp, dict):
                po = _to_price_float(lpp.get("oldPrice"))
                pc = _to_price_float(lpp.get("price"))
                if po and pc and po >= pc:
                    basic_f, promo_f, in_promo = po, pc, True

    if basic_f is None:
        return None

    if not promo_start_s and not promo_end_s:
        for blob in (data.get("promotion"), data.get("promotions")):
            if isinstance(blob, list) and blob and isinstance(blob[0], dict):
                ps, pe = _promo_dates_from_mindshift_dict(blob[0])
                if ps:
                    promo_start_s = promo_start_s or ps
                if pe:
                    promo_end_s = promo_end_s or pe
            elif isinstance(blob, dict):
                ps, pe = _promo_dates_from_mindshift_dict(blob)
                if ps:
                    promo_start_s = promo_start_s or ps
                if pe:
                    promo_end_s = promo_end_s or pe

    out: Dict[str, Any] = {
        "lidlProductKey": pkey[:120],
        "lidlUrlPath": url_s,
        "name": name[:2000],
        "brand": brand,
        "basicPrice": basic_f,
        "promoPrice": promo_f if in_promo else None,
        "inPromo": in_promo,
        "topCategoryName": f"api:{category_label}"[:500],
        "unitContent": unit_content,
    }
    if promo_start_s:
        out["promotionStartDate"] = promo_start_s
    if promo_end_s:
        out["promotionEndDate"] = promo_end_s
    return out


def first_float_in_obj(obj: Any, max_val: float = 500.0) -> Optional[float]:
    if isinstance(obj, (int, float)) and 0.02 < float(obj) < max_val:
        return float(obj)
    if isinstance(obj, str):
        try:
            v = float(obj.replace(",", ".").replace("€", "").strip())
            if 0.02 < v < max_val:
                return v
        except ValueError:
            pass
    if isinstance(obj, dict):
        for v in obj.values():
            r = first_float_in_obj(v, max_val)
            if r is not None:
                return r
    if isinstance(obj, list):
        for v in obj:
            r = first_float_in_obj(v, max_val)
            if r is not None:
                return r
    return None


def get_nested(d: dict, *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def normalize_mindshift_item(raw: dict, category_label: str) -> Optional[dict]:
    name = (
        str(
            get_nested(raw, "label", "headline")
            or get_nested(raw, "title")
            or get_nested(raw, "name")
            or get_nested(raw, "productName")
            or ""
        ).strip()
    )
    brand = None
    b = get_nested(raw, "brand", "name") or raw.get("brand")
    if isinstance(b, str):
        brand = b.strip() or None
    elif isinstance(b, dict):
        brand = str(b.get("name") or "").strip() or None

    pid = (
        raw.get("productId")
        or raw.get("id")
        or raw.get("masterId")
        or get_nested(raw, "meta", "productId")
    )
    if pid is None:
        return None
    pkey = str(pid).strip()
    if not pkey:
        return None
    if not pkey.lower().startswith("p") and pkey.isdigit():
        pkey = f"p{pkey}"

    price_block = raw.get("price") or raw.get("priceInfo") or raw.get("pricing")
    basic_f: Optional[float] = None
    promo_f: Optional[float] = None
    in_promo = False
    promo_start_s: Optional[str] = None
    promo_end_s: Optional[str] = None

    if isinstance(price_block, dict):
        disc_pb = price_block.get("discount")
        if isinstance(disc_pb, dict):
            ps, pe = _promo_dates_from_mindshift_dict(disc_pb)
            promo_start_s, promo_end_s = ps, pe
        strike = first_float_in_obj(
            price_block.get("strikePrice")
            or price_block.get("wasPrice")
            or price_block.get("strikethroughPrice")
            or get_nested(price_block, "discount", "oldPrice")
        )
        cur = first_float_in_obj(
            price_block.get("finalPrice")
            or price_block.get("salesPrice")
            or price_block.get("displayPrice")
            or price_block.get("price")
            or get_nested(price_block, "discount", "price")
        )
        if cur is None:
            cur = first_float_in_obj(price_block)
        if strike is not None and cur is not None and strike > cur:
            basic_f, promo_f, in_promo = strike, cur, True
        elif cur is not None:
            basic_f, promo_f, in_promo = cur, None, False
    if basic_f is None:
        basic_f = first_float_in_obj(raw)
    if basic_f is None:
        return None

    href = raw.get("url") or raw.get("href") or raw.get("link")
    url_s = ""
    if isinstance(href, str) and href.startswith("http"):
        url_s = href[:2000]
    elif isinstance(href, str) and href.startswith("/"):
        url_s = (CONFIG["base"] + href)[:2000]

    if not promo_start_s and not promo_end_s:
        for blob in (raw.get("promotion"), raw.get("promotions")):
            if isinstance(blob, list) and blob and isinstance(blob[0], dict):
                ps, pe = _promo_dates_from_mindshift_dict(blob[0])
                promo_start_s = promo_start_s or ps
                promo_end_s = promo_end_s or pe
            elif isinstance(blob, dict):
                ps, pe = _promo_dates_from_mindshift_dict(blob)
                promo_start_s = promo_start_s or ps
                promo_end_s = promo_end_s or pe

    out_ms: Dict[str, Any] = {
        "lidlProductKey": pkey[:120],
        "lidlUrlPath": url_s,
        "name": name[:2000] or pkey,
        "brand": brand,
        "basicPrice": basic_f,
        "promoPrice": promo_f if in_promo else None,
        "inPromo": in_promo,
        "topCategoryName": f"api:{category_label}"[:500],
        "unitContent": None,
    }
    if promo_start_s:
        out_ms["promotionStartDate"] = promo_start_s
    if promo_end_s:
        out_ms["promotionEndDate"] = promo_end_s
    return out_ms


def fetch_search_page(
    session: requests.Session,
    *,
    category_id: Optional[int],
    offset: int,
    fetchsize: int,
    referer: str,
) -> dict:
    url = CONFIG["base"] + CONFIG["api_path"]
    params: Dict[str, Any] = {
        "offset": offset,
        "fetchsize": fetchsize,
        "locale": CONFIG["locale"],
        "assortment": CONFIG["assortment"],
        "version": CONFIG["version"],
    }
    if category_id is not None:
        params["category.id"] = category_id
    headers = {
        "accept": "application/mindshift.search+json;version=2",
        "accept-language": "nl-BE,nl;q=0.9,en;q=0.8",
        "referer": referer,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
    }
    last_exc: Optional[Exception] = None
    for attempt in range(4):
        r = session.get(url, params=params, headers=headers, timeout=CONFIG["request_timeout"])
        if r.status_code == 401:
            raise RuntimeError(
                "401: lidl_cookie.txt gerekli (tarayicidan DevTools -> istek -> Cookie kopyala)."
            )
        if r.status_code in (429, 502, 503, 504):
            wait = (2.5 + attempt * 2.0) + random.uniform(0.4, 1.8)
            time.sleep(wait)
            last_exc = RuntimeError(f"HTTP {r.status_code}")
            continue
        r.raise_for_status()
        return r.json()
    if last_exc:
        raise last_exc
    raise RuntimeError("API istegi basarisiz")


def run(
    *,
    category_urls: List[str],
    dry_run: bool,
    dump_raw: str,
    no_pause: bool,
    fetchsize: int,
    no_bootstrap: bool,
) -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cikti_dir = os.path.join(script_dir, "cikti")
    os.makedirs(cikti_dir, exist_ok=True)

    cookie = load_cookie(script_dir)
    if not cookie:
        print("HATA: lidl_cookie.txt yok veya bos.")
        print("  Tarayici -> F12 -> Network -> q/api/search -> Cookie header -> dosyaya yapistir.")
        return 1

    session = requests.Session()
    session.headers["Cookie"] = cookie

    by_key: Dict[str, dict] = {}
    dumped = False

    # (category_id, etiket, referer taban URL — alt kategoriler icin ebeveyn sayfasi)
    work: deque = deque()
    queued_ids: Set[int] = set()
    done_ids: Set[int] = set()
    max_queued = 12000
    queue_full_warned = False

    def schedule(cid: int, lab: str, ref_base: str) -> None:
        nonlocal queue_full_warned
        if cid in queued_ids:
            return
        if len(queued_ids) >= max_queued:
            if not queue_full_warned:
                print("UYARI: Kategori kuyrugu limiti dolu; bazi id'ler atlaniyor.")
                queue_full_warned = True
            return
        queued_ids.add(cid)
        work.append((cid, lab, ref_base))

    root_ref = f"{CONFIG['base']}/c/nl-BE/"
    if not dry_run and not no_bootstrap:
        human_delay()
        try:
            root_data = fetch_search_page(
                session,
                category_id=None,
                offset=0,
                fetchsize=min(fetchsize, 24),
                referer=root_ref,
            )
            boot = discover_category_ids_from_facets(root_data, skip_id=None)
            if boot:
                print(f"\nBootstrap (kok API, category.id yok): +{len(boot)} kategori kuyruga")
            for bid, blab in boot:
                schedule(bid, f"bootstrap>{blab}", root_ref.rstrip("/"))
        except Exception as e:
            print(f"\nBootstrap atlaniyor: {e}")

    for list_url in category_urls:
        cid = category_id_from_url(list_url)
        if cid is None:
            print(f"Atlaniyor (sXXXXXX/hXXXXXX yok): {list_url}")
            continue
        label = list_url.rstrip("/").split("/")[-2] if "/" in list_url else str(cid)
        ref_b = list_url.split("?")[0].rstrip("/")
        schedule(cid, label, ref_b)

    while work:
        cid, label, ref_base = work.popleft()
        if cid in done_ids:
            continue
        print(f"\nKategori id={cid} ({label})")

        offset = 0
        pages = 0
        while True:
            human_delay()
            ref = referer_for_offset(ref_base, offset)
            try:
                data = fetch_search_page(
                    session,
                    category_id=cid,
                    offset=offset,
                    fetchsize=fetchsize,
                    referer=ref,
                )
            except Exception as e:
                print(f"  HATA offset={offset}: {e}")
                break

            if dump_raw and not dumped:
                p = os.path.join(cikti_dir, dump_raw)
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  Ilk yanit ornek: {p}")
                dumped = True

            if offset == 0 and not dry_run and isinstance(data, dict):
                subs = discover_category_ids_from_facets(data, skip_id=cid)
                if subs:
                    print(f"  facet agaci +{len(subs)} kategori kuyruga")
                for sub_cid, sub_lab in subs:
                    schedule(sub_cid, f"{label}>{sub_lab}", ref_base)

            rows = extract_gridbox_rows(data)
            chunk_len = 0
            if rows:
                n_new = 0
                for row in rows:
                    rec = normalize_gridbox_data(row, label)
                    if rec:
                        k = rec["lidlProductKey"]
                        if k not in by_key:
                            n_new += 1
                        by_key[k] = rec
                chunk_len = len(rows)
                print(
                    f"  offset={offset} numFound={data.get('numFound')} parca={chunk_len} "
                    f"yeni_anahtar={n_new} toplam_benzersiz={len(by_key)}"
                )
            else:
                legacy = pick_product_list(data)
                n_new = 0
                for raw in legacy:
                    if not isinstance(raw, dict):
                        continue
                    rec = normalize_mindshift_item(raw, label)
                    if rec:
                        k = rec["lidlProductKey"]
                        if k not in by_key:
                            n_new += 1
                        by_key[k] = rec
                chunk_len = len(legacy)
                print(
                    f"  offset={offset} (legacy) parca={chunk_len} yeni_anahtar={n_new} "
                    f"toplam_benzersiz={len(by_key)}"
                )
                if not legacy:
                    print("  urun listesi yok (items/gridbox bekleniyor).")
                    if dry_run:
                        break
                    break

            if dry_run:
                break
            if chunk_len < fetchsize:
                break
            nf_i = int(data.get("numFound") or 0)
            if nf_i and offset + chunk_len >= nf_i:
                break
            offset += fetchsize
            pages += 1
            if pages > 5000:
                break

        done_ids.add(cid)

    urunler = list(by_key.values())
    tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = os.path.join(cikti_dir, f"lidl_be_producten_{tarih}.json")
    payload = {
        "kaynak": "Lidl Belçika Mindshift API (/q/api/search)",
        "chain_slug": "lidl_be",
        "country_code": "BE",
        "cekilme_tarihi": datetime.now().isoformat(),
        "urun_sayisi": len(urunler),
        "dry_run": dry_run,
        "lidl_mode": "mindshift_api",
        "urunler": urunler,
    }

    if dry_run:
        print(f"\n[DRY-RUN] {len(urunler)} urun; dosya yazilmadi.")
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nTamam: {len(urunler)} urun -> {out_path}")

    if not no_pause:
        input("\nCikmak icin Enter...")
    return 0 if urunler else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Lidl BE Mindshift API (cookie + kategori URL)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-pause", action="store_true")
    ap.add_argument(
        "--categories-file",
        type=str,
        default="",
        help="Kategori liste URL dosyasi (varsayilan: lidl_be_api_categories.txt)",
    )
    ap.add_argument(
        "--dump-raw",
        type=str,
        default="",
        help="Ilk JSON yanitini cikti/ altina bu dosya adiyla yaz (ornek: lidl_mindshift_raw.json)",
    )
    ap.add_argument("--fetchsize", type=int, default=0, help="0=12")
    ap.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Kok API (category.id olmadan) ile facet tohumlamayi kapat",
    )
    args = ap.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cf = args.categories_file.strip()
    if not cf:
        cf = os.path.join(script_dir, "lidl_be_api_categories.txt")
    elif not os.path.isabs(cf):
        cf = os.path.join(script_dir, cf)
    urls: List[str] = []
    if os.path.isfile(cf):
        with open(cf, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                s = ln.strip()
                if s and not s.startswith("#"):
                    urls.append(s.split("?")[0])
    if not urls and args.no_bootstrap:
        print(f"HATA: Kategori URL dosyasi yok veya bos: {cf}")
        print("  Ornek satir: https://www.lidl.be/c/nl-BE/voeding-drank/s10068374")
        return 1
    if not urls:
        print("BILGI: Kategori dosyasi bos; yalnizca kok API bootstrap + facet genislemesi.")

    fs = args.fetchsize if args.fetchsize > 0 else int(CONFIG["fetchsize"])
    return run(
        category_urls=urls,
        dry_run=args.dry_run,
        dump_raw=args.dump_raw.strip(),
        no_pause=args.no_pause,
        fetchsize=fs,
        no_bootstrap=args.no_bootstrap,
    )


if __name__ == "__main__":
    raise SystemExit(main())
