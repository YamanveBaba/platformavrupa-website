"""
product_matching.py
===================
Eşleştirme motoru — 3 katmanlı: EAN tam → kanonik anahtar → fuzzy (rapidfuzz).

pip install rapidfuzz
"""

from collections import defaultdict
from rapidfuzz import fuzz
from product_normalize import canonical_key, unit_price, norm_text

FUZZY_THRESHOLD = 86
QTY_TOLERANCE = 0.12


def group_offers(offers: list[dict], mode: str = "exact") -> list[dict]:
    """
    offers listesini eşleştir, grupla.
    mode: "exact" | "equivalent" | "line"
    """
    enriched = []
    for o in offers:
        ck = canonical_key(o.get("name", ""), o.get("brand"))
        up, up_label = unit_price(_eff_price(o), o.get("name", ""))
        enriched.append({**o, "_ck": ck, "_unit_price": up, "_unit_label": up_label})

    buckets: dict[str, list[dict]] = defaultdict(list)
    leftovers: list[dict] = []

    for o in enriched:
        ean = (o.get("ean") or "").strip()
        ck = o["_ck"]
        if mode == "line":
            if ck["brand"] or ck["core"]:
                buckets[f"line:{ck['brand']}|{ck['core']}"].append(o)
            else:
                leftovers.append(o)
        else:
            if ean:
                buckets[f"ean:{ean}"].append(o)
            elif ck["qty"] and ck["core"]:
                buckets[f"key:{ck['key']}"].append(o)
            else:
                leftovers.append(o)

    groups = [list(v) for v in buckets.values()]

    for o in leftovers:
        placed = False
        for g in groups:
            if _fuzzy_same(o, g[0]):
                g.append(o)
                placed = True
                break
        if not placed:
            groups.append([o])

    if mode == "equivalent":
        groups = _merge_equivalents(groups)
    elif mode == "line":
        groups = _merge_lines(groups)

    result = []
    for g in groups:
        by_chain = {}
        for o in g:
            c = o.get("chain")
            if c not in by_chain or (_eff_price(o) or 9e9) < (_eff_price(by_chain[c]) or 9e9):
                by_chain[c] = o
        members = list(by_chain.values())

        if mode == "line":
            valid = [m for m in members if m.get("_unit_price") is not None]
            cheapest = min(valid or members, key=lambda x: x.get("_unit_price") or 9e9)
            cheapest_price = cheapest.get("_unit_price")
            cheapest_label = cheapest.get("_unit_label")
        else:
            cheapest = min(members, key=lambda x: _eff_price(x) or 9e9)
            cheapest_price = _eff_price(cheapest)
            cheapest_label = None

        rep = max(members, key=lambda x: len((x.get("name") or "")))

        result.append({
            "product": {
                "brand": rep["_ck"]["brand"] or rep.get("brand"),
                "name": rep.get("name"),
                "qty_str": rep["_ck"]["qty_str"] or rep.get("quantity_str"),
                "category": rep.get("category"),
                "image_url": next((m.get("image_url") for m in members if m.get("image_url")), None),
                "ean": next((m.get("ean") for m in members if m.get("ean")), None),
            },
            "offers": sorted(
                [{
                    "chain": m.get("chain"),
                    "price": m.get("price"),
                    "promo_price": m.get("promo_price"),
                    "in_promo": bool(m.get("promo_price")),
                    "qty_str": m["_ck"]["qty_str"] or m.get("quantity_str"),
                    "unit_price": m.get("_unit_price"),
                    "unit_label": m.get("_unit_label"),
                    "source_url": m.get("source_url"),
                } for m in members],
                key=lambda x: x.get("unit_price") or x.get("price") or 9e9,
            ),
            "cheapest_chain": cheapest.get("chain"),
            "cheapest_price": cheapest_price,
            "cheapest_label": cheapest_label,
            "chain_count": len(members),
        })

    result.sort(key=lambda x: x["chain_count"], reverse=True)
    return result


def search_products(offers: list[dict], query: str, limit: int = 50) -> list[dict]:
    """Sorguya göre teklifleri sırala, sonra grupla."""
    q = norm_text(query)
    q_tokens = set(q.split())

    scored = []
    for o in offers:
        name_n = norm_text(o.get("name", ""))
        if q and q in name_n:
            score = 100
        elif q_tokens and q_tokens <= set(name_n.split()):
            score = 90
        else:
            score = fuzz.token_set_ratio(q, name_n)
        if score >= 60:
            scored.append((score, o))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_offers = [o for _, o in scored[: limit * 5]]
    groups = group_offers(top_offers)
    return groups[:limit]


def _merge_lines(groups):
    def info(g):
        rep = max(g, key=lambda x: len(x.get("name") or ""))
        return rep["_ck"]["brand"], rep["_ck"]["core"]

    merged, used = [], [False] * len(groups)
    for i, gi in enumerate(groups):
        if used[i]:
            continue
        bi, ci = info(gi)
        combined = list(gi)
        used[i] = True
        if bi:
            for j in range(i + 1, len(groups)):
                if used[j]:
                    continue
                bj, cj = info(groups[j])
                if bj != bi:
                    continue
                compatible = (not ci) or (not cj) or ci in cj or cj in ci \
                    or fuzz.token_sort_ratio(ci, cj) >= 82
                if compatible:
                    combined.extend(groups[j])
                    used[j] = True
        merged.append(combined)
    return merged


def _merge_equivalents(groups):
    def sig(group):
        rep = max(group, key=lambda x: len(x.get("name") or ""))
        ck = rep["_ck"]
        return ck["core"], ck["qty"], ck["unit"]

    merged = []
    used = [False] * len(groups)
    for i, gi in enumerate(groups):
        if used[i]:
            continue
        core_i, qty_i, unit_i = sig(gi)
        combined = list(gi)
        used[i] = True
        if core_i and qty_i:
            for j in range(i + 1, len(groups)):
                if used[j]:
                    continue
                core_j, qty_j, unit_j = sig(groups[j])
                if not core_j or not qty_j:
                    continue
                same_qty = (unit_i == unit_j and abs(qty_i - qty_j) / max(qty_i, qty_j) <= QTY_TOLERANCE)
                if same_qty and fuzz.token_sort_ratio(core_i, core_j) >= 90:
                    combined.extend(groups[j])
                    used[j] = True
        merged.append(combined)
    return merged


def _eff_price(o):
    p = o.get("promo_price") or o.get("price")
    return float(p) if p is not None else None


def _fuzzy_same(a: dict, b: dict) -> bool:
    ca, cb = a["_ck"], b["_ck"]
    if a.get("category") and b.get("category"):
        if fuzz.ratio(str(a["category"]).lower(), str(b["category"]).lower()) < 70:
            return False
    if ca["qty"] and cb["qty"] and ca["unit"] == cb["unit"]:
        diff = abs(ca["qty"] - cb["qty"]) / max(ca["qty"], cb["qty"])
        if diff > QTY_TOLERANCE:
            return False
    sa = f"{ca['brand']} {ca['core']}".strip()
    sb = f"{cb['brand']} {cb['core']}".strip()
    return fuzz.token_sort_ratio(sa, sb) >= FUZZY_THRESHOLD
