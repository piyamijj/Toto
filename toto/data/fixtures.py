"""Bülten ve oran kaynakları.

Öncelik sırası:
1. data/bulten.json – resmi Spor Toto bülteni (sportoto.gov.tr) haftalık olarak elle girilir.
   Spor Toto Teşkilatı'nın herkese açık resmi bir API'si yoktur; site kazınmaz.
2. API-Football (api-sports.io, lisanslı) – Süper Lig haftalık fikstürü.
Oranlar: The Odds API (lisanslı) – ev/beraberlik/deplasman, bahisçi ortalaması.
"""
import json

from toto import config
from toto.cache import ttl_cache
from toto.data.http import DataSourceError, get_json
from toto.teams import normalize


def load_bulletin_file(path=None):
    path = path or config.BULLETIN_PATH
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = data["maclar"] if isinstance(data, dict) else data
    out = []
    for m in matches:
        odds = (m.get("odds_1"), m.get("odds_X"), m.get("odds_2"))
        out.append({"home_team": m["home_team"], "away_team": m["away_team"],
                    "odds": odds if all(odds) else None})
    return {"kaynak": "Spor Toto resmi bülten (elle girilmiş)", "hafta": data.get("hafta") if isinstance(data, dict)
            else None, "maclar": out}


@ttl_cache(config.CACHE_TTL_SECONDS)
def api_football_round(week: int):
    if not config.API_FOOTBALL_KEY:
        raise DataSourceError("API_FOOTBALL_KEY tanımlı değil")
    data = get_json(f"{config.API_FOOTBALL_BASE}/fixtures",
                    {"league": config.API_FOOTBALL_LEAGUE, "season": config.API_FOOTBALL_SEASON,
                     "round": f"Regular Season - {week}"},
                    {"x-apisports-key": config.API_FOOTBALL_KEY})
    if data.get("errors"):
        raise DataSourceError(f"API-Football hatası: {data['errors']}")
    return [{"home_team": f["teams"]["home"]["name"], "away_team": f["teams"]["away"]["name"],
             "kickoff": f["fixture"]["date"], "status": f["fixture"]["status"]["short"],
             "goals": (f["goals"]["home"], f["goals"]["away"])}
            for f in data.get("response", [])]


@ttl_cache(config.CACHE_TTL_SECONDS)
def odds_api_h2h():
    """{(ev, dep): (o1, ox, o2)} – bahisçi ortalaması. Anahtar yoksa boş sözlük."""
    if not config.ODDS_API_KEY:
        return {}
    events = get_json(f"{config.ODDS_API_BASE}/sports/{config.ODDS_API_SPORT}/odds",
                      {"apiKey": config.ODDS_API_KEY, "regions": config.ODDS_API_REGIONS,
                       "markets": "h2h", "oddsFormat": "decimal"})
    result = {}
    for ev in events:
        home, away = ev["home_team"], ev["away_team"]
        acc = {"h": [], "d": [], "a": []}
        for bm in ev.get("bookmakers", []):
            for mk in bm.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                for o in mk.get("outcomes", []):
                    key = "h" if o["name"] == home else "a" if o["name"] == away else "d"
                    acc[key].append(float(o["price"]))
        if all(acc.values()):
            result[(normalize(home), normalize(away))] = tuple(sum(v) / len(v) for v in (acc["h"], acc["d"], acc["a"]))
    return result


def get_bulletin(week: int):
    bulletin = load_bulletin_file()
    if bulletin is None:
        bulletin = {"kaynak": "API-Football (Süper Lig fikstürü)", "hafta": week,
                    "maclar": [dict(m, odds=None) for m in api_football_round(week)]}
    try:
        odds = odds_api_h2h()
    except DataSourceError:
        odds = {}
    for m in bulletin["maclar"]:
        if m.get("odds") is None:
            m["odds"] = odds.get((normalize(m["home_team"]), normalize(m["away_team"])))
    return bulletin
