"""Tarihsel Süper Lig sonuçları – football-data.co.uk sezon CSV dosyaları.

Kaynak: https://www.football-data.co.uk/turkeym.php (ücretsiz, indirilebilir CSV; kazıma değil).
Kullanım koşulları için siteyi kontrol edin.
"""
import csv
import io
from datetime import datetime

from toto.data.http import get_text

BASE = "https://www.football-data.co.uk/mmz4281/{code}/T1.csv"


def season_code(start_year: int) -> str:
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def _parse_date(s):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _num(row, *keys):
    for k in keys:
        try:
            v = float(row.get(k) or "")
            if v > 1.0:
                return v
        except ValueError:
            continue
    return None


def parse_csv(text):
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        d = _parse_date(row.get("Date", ""))
        if not d or row.get("FTHG", "") == "" or row.get("FTAG", "") == "":
            continue
        out.append({
            "date": d, "home": row["HomeTeam"], "away": row["AwayTeam"],
            "hg": int(float(row["FTHG"])), "ag": int(float(row["FTAG"])),
            "odds": (_num(row, "AvgH", "B365H"), _num(row, "AvgD", "B365D"), _num(row, "AvgA", "B365A")),
        })
    return out


def load_seasons(start_years):
    matches = []
    for y in start_years:
        matches.extend(parse_csv(get_text(BASE.format(code=season_code(y)))))
    return sorted(matches, key=lambda m: m["date"])
