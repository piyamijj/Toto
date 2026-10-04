"""Guncel Super Lig sonuclari – ESPN skor tablosu (resmi olmayan, anahtarsiz).

API-Football free plani guncel sezona erisemedigi icin haftalik egitimin
guncel sezon biten maclari buradan tamamlanir. ESPN semasi degisirse
bozuk gunler tek tek atlanir, egitim eski veriyle surer.
"""
import time
from datetime import date, timedelta

from toto.data.http import DataSourceError, get_json

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/tur.1/scoreboard"
_PAUSE = 0.2


def _team_name(entry):
    team = entry.get("team") or {}
    return team.get("displayName") or team.get("shortDisplayName") or ""


def parse_day(payload, day):
    """Bitmis maclari tarihsel formata cevirir: [{date, home, away, hg, ag, odds}]."""
    out = []
    for ev in (payload or {}).get("events", []):
        try:
            comp = (ev.get("competitions") or [{}])[0]
            if not (comp.get("status") or {}).get("type", {}).get("completed"):
                continue
            sides = {}
            for c in comp.get("competitors", []):
                sides[c.get("homeAway")] = (_team_name(c), c.get("score"))
            (home, hs), (away, aws) = sides["home"], sides["away"]
            out.append({"date": day, "home": home, "away": away,
                        "hg": int(hs), "ag": int(aws), "odds": (None, None, None)})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def fetch_day(day):
    return parse_day(get_json(BASE, {"dates": day.strftime("%Y%m%d")}), day)


def load_since(since, until=None):
    """[since, until] araligindaki biten maclari dondurur (gunluk hata toleransli).

    Donus: (maclar, atlanan_gun_sayisi). Tarihe gore sirali.
    """
    until = until or date.today()
    matches, skipped = [], 0
    day = since
    while day <= until:
        try:
            matches.extend(fetch_day(day))
        except DataSourceError:
            skipped += 1
        day += timedelta(days=1)
        time.sleep(_PAUSE)
    return sorted(matches, key=lambda m: m["date"]), skipped
