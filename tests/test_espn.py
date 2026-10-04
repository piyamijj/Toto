"""ESPN skor tablosu çekici testleri (ağ taklit edilir, gerçek istek yok)."""
from datetime import date

from toto.data import espn
from toto.data.http import DataSourceError

DAY = {
    "events": [
        {"date": "2025-09-14T14:00Z", "name": "Goztepe at Kayserispor",
         "competitions": [{"status": {"type": {"completed": True, "shortDetail": "FT"}},
                           "competitors": [
                               {"homeAway": "home", "score": "1",
                                "team": {"displayName": "Kayserispor", "shortDisplayName": "Kayserispor"}},
                               {"homeAway": "away", "score": "1",
                                "team": {"displayName": "Goztepe", "shortDisplayName": "Goztepe"}}]}]},
        {"date": "2025-09-14T17:00Z", "name": "Fenerbahce at Galatasaray",
         "competitions": [{"status": {"type": {"completed": False, "shortDetail": "19:00"}},
                           "competitors": [
                               {"homeAway": "home", "score": "0",
                                "team": {"displayName": "Galatasaray"}},
                               {"homeAway": "away", "score": "0",
                                "team": {"displayName": "Fenerbahce"}}]}]},
        {"date": "2025-09-14T18:00Z", "name": "bozuk kayit",
         "competitions": [{"status": {}, "competitors": []}]},
    ]
}


def test_parse_day_keeps_only_finished():
    rows = espn.parse_day(DAY, date(2025, 9, 14))
    assert len(rows) == 1
    m = rows[0]
    assert (m["home"], m["away"], m["hg"], m["ag"]) == ("Kayserispor", "Goztepe", 1, 1)
    assert m["date"] == date(2025, 9, 14) and m["odds"] == (None, None, None)


def test_parse_day_empty_payload():
    assert espn.parse_day({}, date(2025, 9, 14)) == []
    assert espn.parse_day(None, date(2025, 9, 14)) == []


def test_load_since_iterates_and_tolerates(monkeypatch):
    calls = []

    def fake_fetch(day):
        calls.append(day)
        if day == date(2025, 9, 15):
            raise DataSourceError("ağ hatası")
        return [{"date": day, "home": "A", "away": "B", "hg": 1, "ag": 0,
                 "odds": (None, None, None)}]

    monkeypatch.setattr(espn, "fetch_day", fake_fetch)
    monkeypatch.setattr(espn.time, "sleep", lambda s: None)
    matches, skipped = espn.load_since(date(2025, 9, 14), date(2025, 9, 16))
    assert [c.day for c in calls] == [14, 15, 16]
    assert len(matches) == 2 and skipped == 1
    assert [m["date"].day for m in matches] == [14, 16]
