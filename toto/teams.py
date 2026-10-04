"""Farklı veri kaynaklarındaki takım adlarını ortak bir anahtara indirger."""
import re
import unicodedata

_TR = str.maketrans({"ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
                     "ç": "c", "Ç": "c", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u"})
_SUFFIXES = ("kulubu", "spor", "sk", "fk", "as", "jk")
_ALIASES = {
    "buyuksehyr": "basaksehir", "istanbulbasaksehir": "basaksehir", "ibasaksehir": "basaksehir",
    "basaksehirfutbolkulubu": "basaksehir", "fbahce": "fenerbahce", "gsaray": "galatasaray",
    "karagumruk": "fatihkaragumruk", "ankaragucu": "mkeankaragucu", "erzurumbb": "erzurum", "caykurrize": "rize", "adanademir": "adanademirspor",
}


def normalize(name: str) -> str:
    s = (name or "").translate(_TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    changed = True
    while changed:
        changed = False
        for suf in _SUFFIXES:
            if s.endswith(suf) and len(s) > len(suf) + 2:
                s, changed = s[: -len(suf)], True
    return _ALIASES.get(s, s)
