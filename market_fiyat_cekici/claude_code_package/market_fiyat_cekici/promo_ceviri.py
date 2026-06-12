"""
promo_ceviri.py
==============
NL/FR promo ifadelerini Türkçeye çeviren modül.
3 katman: regex kurallar → glossary → LLM yedek.
"""

import re

_RULES = [
    (re.compile(r"(?:le\s*)?(?:2e|2de|2ème|tweede|deuxième)\s*(?:aan|à)?\s*(?:halve prijs|moitié prix)", re.I),
     lambda m: "2.si yarı fiyat"),
    (re.compile(r"(?:le\s*)?(?:2e|2de|2ème|tweede|deuxième)\s*(?:aan|à)?\s*-?\s*(\d+)\s*%", re.I),
     lambda m: f"2.si %{m.group(1)} indirim"),
    (re.compile(r"(\d+)\s*\+\s*(\d+)\s*(?:gratis|gratuit)", re.I),
     lambda m: f"{m.group(1)} alana {m.group(2)} bedava"),
    (re.compile(r"van\s*€?\s*(\d+(?:[.,]\d+)?)\s*voor\s*€?\s*(\d+(?:[.,]\d+)?)", re.I),
     lambda m: f"€{m.group(1).replace('.', ',')} yerine €{m.group(2).replace('.', ',')}"),
    (re.compile(r"€?\s*(\d+(?:[.,]\d+)?)\s*au lieu de\s*€?\s*(\d+(?:[.,]\d+)?)", re.I),
     lambda m: f"€{m.group(2).replace('.', ',')} yerine €{m.group(1).replace('.', ',')}"),
    (re.compile(r"(\d+)\s*(?:voor|pour)\s*€?\s*(\d+(?:[.,]\d+)?)\s*(?:euro|€)?", re.I),
     lambda m: f"{m.group(1)} adet €{m.group(2).replace('.', ',')}"),
    (re.compile(r"(?:tot|jusqu['']?\s*à?)\s*-?\s*(\d+)\s*%(?:\s*(?:de\s+)?(?:korting|réduction|remise))?", re.I),
     lambda m: f"en fazla %{m.group(1)} indirim"),
    (re.compile(r"(?:korting|réduction|remise)\s*-?\s*(\d+)\s*%", re.I),
     lambda m: f"%{m.group(1)} indirim"),
    (re.compile(r"-?\s*(\d+)\s*%\s*(?:de\s+)?(?:korting|réduction|remise)", re.I),
     lambda m: f"%{m.group(1)} indirim"),
    (re.compile(r"-\s*(\d+)\s*%", re.I),
     lambda m: f"%{m.group(1)} indirim"),
    (re.compile(r"\+\s*(\d+)\s*%", re.I),
     lambda m: f"+%{m.group(1)} bedava"),
    (re.compile(r"lot de\s*(\d+)", re.I),
     lambda m: f"{m.group(1)}'li paket"),
    (re.compile(r"max(?:imum)?\s*(\d+)\s*(?:stuks\s*)?(?:per klant|par client)", re.I),
     lambda m: f"müşteri başına en fazla {m.group(1)}"),
]

PROMO_GLOSSARY = {
    "halve prijs": "yarı fiyat",
    "voordeelverpakking": "avantaj paketi",
    "voordeelpak": "avantaj paketi",
    "weekendactie": "hafta sonu kampanyası",
    "weekactie": "haftanın kampanyası",
    "stapelkorting": "kademeli indirim",
    "volumekorting": "miktar indirimi",
    "kassakorting": "kasada indirim",
    "extra korting": "ekstra indirim",
    "zolang de voorraad strekt": "stoklarla sınırlı",
    "op=op": "stoklarla sınırlı",
    "prijsknaller": "süper fırsat",
    "topdeal": "süper fırsat",
    "laagste prijs": "en düşük fiyat",
    "per stuk": "adet başına",
    "per liter": "litre başına",
    "per kg": "kilo başına",
    "geldig tot": "şu tarihe kadar geçerli",
    "geldig van": "şu tarihten itibaren",
    "korting": "indirim",
    "voordeel": "avantaj",
    "weekend": "hafta sonu",
    "actie": "kampanya",
    "gratis": "bedava",
    "vanaf": "itibaren",
    "à moitié prix": "yarı fiyat",
    "moitié prix": "yarı fiyat",
    "pack avantage": "avantaj paketi",
    "par pièce": "adet başına",
    "par litre": "litre başına",
    "jusqu'à épuisement des stocks": "stoklarla sınırlı",
    "valable jusqu'au": "şu tarihe kadar geçerli",
    "valable": "geçerli",
    "réduction": "indirim",
    "remise": "indirim",
    "promotion": "kampanya",
    "offre": "kampanya",
    "gratuit": "bedava",
    "le moins cher": "en ucuz",
    "dès": "itibaren",
}


def promo_ceviri(text: str) -> str:
    """Promo ifadesini Türkçeye çevir."""
    if not text:
        return text
    out = text
    for pattern, repl in _RULES:
        out = pattern.sub(repl, out)
    for k in sorted(PROMO_GLOSSARY, key=len, reverse=True):
        pattern = r"(?<![a-zA-ZçğıöşüÇĞİÖŞÜ])" + re.escape(k) + r"(?![a-zA-Z])"
        out = re.sub(pattern, PROMO_GLOSSARY[k], out, flags=re.I)
    out = re.sub(r"(indirim)(\s+indirim)+", r"\1", out, flags=re.I)
    return re.sub(r"\s+", " ", out).strip()


def eksik_ifadeler(texts: list[str]) -> list[str]:
    """Sözlük/kural hiç değiştirmediyse 'bilinmeyen' promo ifadesidir."""
    out = []
    for t in texts:
        if t and promo_ceviri(t) == t and not t.replace(" ", "").replace("/", "").isdigit():
            out.append(t)
    return sorted(set(out))
