"""
translation_cache.py
====================
Cache-first çeviri katmanı. Supabase translations tablosunda saklar.
Ürün adları tekrar ettiği için ~%90 cache'ten gelir.

ENV: AZURE_TRANSLATE_KEY, AZURE_TRANSLATE_REGION (varsayılan: westeurope)
     TRANSLATE_PROVIDER (varsayılan: "azure")
"""

import os
import re

PROTECTED_BRANDS = {
    "Boni", "Everyday", "365", "Coca-Cola", "Pepsi", "Nutella", "Danone",
    "Alpro", "Côte d'Or", "Lay's", "Président", "Barilla", "Delhaize",
    "Colruyt", "Carrefour", "Aldi", "Lidl",
}

SOURCE_LANG = "nl"
TARGET_LANG = "tr"


def translate_products(supabase, products: list[dict]) -> list[dict]:
    """Her ürüne name_tr / description_tr ekler (cache-first)."""
    to_translate = {}
    for p in products:
        for field in ("name", "description"):
            raw = p.get(field)
            if not raw:
                continue
            masked, _ = _mask_brands(raw)
            to_translate[masked] = None

    texts = list(to_translate.keys())
    cached = _cache_get(supabase, texts)
    misses = [t for t in texts if t not in cached]

    if misses:
        try:
            fresh = _translate_batch(misses)
            _cache_put(supabase, fresh)
            cached.update(fresh)
        except Exception as e:
            print(f"[translation_cache] çeviri hatası: {e}")

    out = []
    for p in products:
        p2 = dict(p)
        if p.get("name"):
            masked, mapping = _mask_brands(p["name"])
            p2["name_tr"] = _unmask_brands(cached.get(masked, p["name"]), mapping)
        if p.get("description"):
            masked, mapping = _mask_brands(p["description"])
            p2["description_tr"] = _unmask_brands(cached.get(masked, p["description"]), mapping)
        out.append(p2)
    return out


def translate_text(supabase, text: str, source_lang: str = "nl") -> str:
    """Tek metin çevir (promo text için)."""
    if not text:
        return text
    masked, mapping = _mask_brands(text)
    cached = _cache_get(supabase, [masked], src=source_lang)
    if masked in cached:
        return _unmask_brands(cached[masked], mapping)
    try:
        fresh = _translate_batch([masked], src=source_lang)
        _cache_put(supabase, fresh, src=source_lang)
        return _unmask_brands(fresh.get(masked, text), mapping)
    except Exception as e:
        print(f"[translation_cache] tek metin çeviri hatası: {e}")
        return text


def _mask_brands(text: str) -> tuple:
    mapping = {}
    masked = text
    for i, brand in enumerate(sorted(PROTECTED_BRANDS, key=len, reverse=True)):
        if brand.lower() in masked.lower():
            ph = f"__B{i}__"
            masked = re.sub(re.escape(brand), ph, masked, flags=re.IGNORECASE)
            mapping[ph] = brand
    return masked, mapping


def _unmask_brands(text: str, mapping: dict) -> str:
    for ph, brand in mapping.items():
        text = text.replace(ph, brand)
    return text


def _cache_get(supabase, texts: list[str], src: str = None) -> dict:
    if not texts:
        return {}
    src = src or SOURCE_LANG
    result = {}
    for chunk in _chunks(texts, 200):
        resp = (
            supabase.table("translations")
            .select("source_text,target_text")
            .eq("source_lang", src)
            .eq("target_lang", TARGET_LANG)
            .in_("source_text", chunk)
            .execute()
        )
        for row in (resp.data or []):
            result[row["source_text"]] = row["target_text"]
    return result


def _cache_put(supabase, mapping: dict, src: str = None):
    src = src or SOURCE_LANG
    rows = [
        {
            "source_text": s,
            "source_lang": src,
            "target_lang": TARGET_LANG,
            "target_text": t,
        }
        for s, t in mapping.items()
    ]
    for chunk in _chunks(rows, 200):
        supabase.table("translations").upsert(chunk).execute()


def _translate_batch(texts: list[str], src: str = None) -> dict:
    src = src or SOURCE_LANG
    provider = os.environ.get("TRANSLATE_PROVIDER", "azure")
    if provider == "azure":
        return _azure_translate(texts, src)
    raise RuntimeError(f"bilinmeyen provider: {provider}")


def _azure_translate(texts: list[str], src: str = "nl") -> dict:
    import requests
    key = os.environ.get("AZURE_TRANSLATE_KEY")
    if not key:
        print("[translation_cache] AZURE_TRANSLATE_KEY eksik, çeviri atlandı")
        return {}
    region = os.environ.get("AZURE_TRANSLATE_REGION", "westeurope")
    endpoint = "https://api.cognitive.microsofttranslator.com/translate"

    out = {}
    for chunk in _chunks(texts, 100):
        body = [{"text": t} for t in chunk]
        resp = requests.post(
            endpoint,
            params={"api-version": "3.0", "from": src, "to": TARGET_LANG},
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Ocp-Apim-Subscription-Region": region,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        for src_text, item in zip(chunk, resp.json()):
            out[src_text] = item["translations"][0]["text"]
    return out


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
