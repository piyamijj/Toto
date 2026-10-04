from toto.data import fixtures
from toto.data.historical import parse_csv, season_code
from toto.teams import normalize

CSV = """Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,AvgH,AvgD,AvgA
T1,09/08/2024,19:00,Galatasaray,Hatayspor,2,1,H,1.26,6.17,9.74
T1,10/08/2024,17:15,Kasimpasa,Konyaspor,2,3,A,2.1,3.5,3.35
T1,11/08/2024,17:15,Rizespor,Buyuksehyr,,,,2.0,3.4,3.5
"""


def test_parse_csv_skips_unplayed():
    rows = parse_csv(CSV)
    assert len(rows) == 2
    assert rows[0]["hg"] == 2 and rows[0]["odds"] == (1.26, 6.17, 9.74)


def test_season_code():
    assert season_code(2024) == "2425" and season_code(2099) == "9900"


def test_normalize_across_sources():
    assert normalize("Fenerbahçe") == normalize("Fenerbahce")
    assert normalize("Kasımpaşa") == normalize("Kasimpasa")
    assert normalize("Başakşehir") == normalize("Buyuksehyr")
    assert normalize("Çaykur Rizespor") == normalize("Rizespor")
    assert normalize("Gaziantep FK") == normalize("Gaziantep")


def test_bulletin_file(tmp_path, monkeypatch):
    f = tmp_path / "b.json"
    f.write_text('{"hafta": 3, "maclar": [{"home_team": "A", "away_team": "B", "odds_1": 2, "odds_X": 3, '
                 '"odds_2": 4}, {"home_team": "C", "away_team": "D"}]}', encoding="utf-8")
    b = fixtures.load_bulletin_file(f)
    assert b["hafta"] == 3 and b["maclar"][0]["odds"] == (2, 3, 4) and b["maclar"][1]["odds"] is None


def test_no_keys_means_no_odds(monkeypatch):
    monkeypatch.setattr(fixtures.config, "ODDS_API_KEY", "")
    fixtures.odds_api_h2h.cache_clear()
    assert fixtures.odds_api_h2h() == {}
