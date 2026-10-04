"""Haftalik bulteni Odds API yaklasan maclariyla yeniler (data/bulten.json yazar).

Kullanim:  ODDS_API_KEY=... python scripts/refresh_bulletin.py
Anahtar yoksa sessizce atlar (CI kirilmaz).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toto import config  # noqa: E402
from toto.data.http import DataSourceError, get_json  # noqa: E402


def main():
    if not config.ODDS_API_KEY:
        print("ODDS_API_KEY yok, bulten yenileme atlandi.")
        return
    try:
        events = get_json(f"{config.ODDS_API_BASE}/sports/{config.ODDS_API_SPORT}/odds",
                          {"apiKey": config.ODDS_API_KEY, "regions": config.ODDS_API_REGIONS,
                           "markets": "h2h", "oddsFormat": "decimal"})
    except DataSourceError as exc:
        print(f"Odds API hatasi, bulten korunuyor: {exc}")
        return
    maclar = []
    for ev in events:
        acc = {"h": [], "d": [], "a": []}
        for bm in ev.get("bookmakers", []):
            for mk in bm.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                for oc in mk.get("outcomes", []):
                    k = ("h" if oc["name"] == ev["home_team"]
                         else "a" if oc["name"] == ev["away_team"] else "d")
                    acc[k].append(float(oc["price"]))
        m = {"home_team": ev["home_team"], "away_team": ev["away_team"],
             "commence_time": ev.get("commence_time")}
        if all(acc.values()):
            m.update({"odds_1": round(sum(acc["h"]) / len(acc["h"]), 2),
                      "odds_X": round(sum(acc["d"]) / len(acc["d"]), 2),
                      "odds_2": round(sum(acc["a"]) / len(acc["a"]), 2)})
        maclar.append(m)
    maclar.sort(key=lambda m: m.get("commence_time") or "")
    if not maclar:
        print("Yaklasan mac yok, bulten korunuyor.")
        return
    now = datetime.now(timezone.utc)
    out = {"hafta": None,
           "kaynak": "The Odds API (Super Lig yaklasan maclari, bahisci ortalamasi)",
           "tarih": now.date().isoformat(), "maclar": maclar}
    config.BULLETIN_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Bulten yazildi: {len(maclar)} mac ({config.BULLETIN_PATH})")


if __name__ == "__main__":
    main()
