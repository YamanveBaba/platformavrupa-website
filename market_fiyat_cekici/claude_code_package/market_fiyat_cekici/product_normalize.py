"""
product_normalize.py
====================
Ürün adlarını normalize eden ve miktar/birim ayıklayan temel modül.
"""

import re
import unicodedata

_UNIT_MAP = {
    "kg": ("g", 1000), "g": ("g", 1), "gr": ("g", 1), "gram": ("g", 1),
    "l": ("ml", 1000), "liter": ("ml", 1000), "litre": ("ml", 1000),
    "cl": ("ml", 10), "ml": ("ml", 1),
    "stuk": ("stuk", 1), "stuks": ("stuk", 1), "st": ("stuk", 1),
    "stk": ("stuk", 1), "pieces": ("stuk", 1), "x": ("stuk", 1),
}
_UNIT_PATTERN = r"(?:kg|gram|gr|g|liter|litre|l|cl|ml|stuks|stuk|stk|st)"

_MULTI_RE = re.compile(
    rf"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*({_UNIT_PATTERN})\b", re.IGNORECASE
)
_SINGLE_RE = re.compile(
    rf"(\d+(?:[.,]\d+)?)\s*({_UNIT_PATTERN})\b", re.IGNORECASE
)

KNOWN_BRANDS = {
    "boni", "everyday", "365", "coca-cola", "coca cola", "pepsi", "delhaize",
    "colruyt", "carrefour", "aldi", "lidl", "nutella", "danone", "alpro",
    "milcobel", "côte d'or", "cote d'or", "lay's", "lays", "président", "president",
}


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def norm_text(text: str) -> str:
    if not text:
        return ""
    t = strip_accents(text.lower())
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_quantity(text: str) -> tuple:
    if not text:
        return None, None, None

    m = _MULTI_RE.search(text)
    if m:
        count = float(m.group(1).replace(",", "."))
        size = float(m.group(2).replace(",", "."))
        base_unit, mult = _UNIT_MAP.get(m.group(3).lower(), (None, 1))
        if base_unit:
            return count * size * mult, base_unit, m.group(0)

    m = _SINGLE_RE.search(text)
    if m:
        val = float(m.group(1).replace(",", "."))
        base_unit, mult = _UNIT_MAP.get(m.group(2).lower(), (None, 1))
        if base_unit:
            return val * mult, base_unit, m.group(0)

    return None, None, None


def extract_brand(name: str, given_brand: str | None = None) -> tuple:
    nm = name or ""
    if given_brand:
        b = norm_text(given_brand)
        core = re.sub(re.escape(given_brand), "", nm, flags=re.IGNORECASE)
        return b, core
    low = norm_text(nm)
    for brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
        bnorm = norm_text(brand)
        if bnorm and bnorm in low:
            core = low.replace(bnorm, "", 1)
            return bnorm, core
    return "", nm


def canonical_key(name: str, brand: str | None = None) -> dict:
    brand_norm, name_wo_brand = extract_brand(name, brand)
    qty, unit, qty_str = parse_quantity(name)

    core = name_wo_brand
    if qty_str:
        core = core.replace(qty_str, " ")
    core = norm_text(core)

    qty_part = f"{int(qty)}{unit}" if qty and unit else "?"
    key = f"{brand_norm}|{core}|{qty_part}"

    return {
        "brand": brand_norm,
        "core": core,
        "qty": qty,
        "unit": unit,
        "qty_str": qty_str,
        "key": key,
    }


def unit_price(price: float | None, name: str) -> tuple:
    if price is None:
        return None, None
    qty, unit, _ = parse_quantity(name)
    if not qty or not unit:
        return None, None
    if unit == "g":
        return round(price / (qty / 1000), 2), "€/kg"
    if unit == "ml":
        return round(price / (qty / 1000), 2), "€/L"
    if unit == "stuk":
        return round(price / qty, 2), "€/adet"
    return None, None
