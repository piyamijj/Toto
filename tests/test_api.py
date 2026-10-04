import pytest
from fastapi.testclient import TestClient

import api.index as api
from toto.data.http import DataSourceError
from toto.model import HybridModel, ModelParams

client = TestClient(api.app)
TRAINED = ModelParams({"a": 0.3, "b": -0.2}, {"a": -0.2, "b": 0.1}, 0.25, -0.05, {"n_matches": 100})
BULLETIN = {"kaynak": "test", "hafta": 5, "maclar": [
    {"home_team": "A", "away_team": "B", "odds": (1.8, 3.6, 4.5)},
    {"home_team": "B", "away_team": "A", "odds": None},
]}


@pytest.fixture
def trained(monkeypatch):
    monkeypatch.setattr(api, "load_model", lambda: HybridModel(TRAINED))


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.parametrize("week", [0, -1, 39])
def test_invalid_week(week):
    assert client.get(f"/api/analiz?hafta={week}").status_code == 422


def test_untrained_returns_503(monkeypatch):
    monkeypatch.setattr(api, "load_model", lambda: HybridModel(ModelParams()))
    assert client.get("/api/analiz?hafta=5").status_code == 503


def test_analiz_ok(trained, monkeypatch):
    monkeypatch.setattr(api, "get_bulletin", lambda w: BULLETIN)
    body = client.get("/api/analiz?hafta=5").json()
    assert len(body["maclar"]) == 2 and body["veri_kaynagi"] == "test"
    assert body["maclar"][1]["oran_var"] is False


def test_source_error_503(trained, monkeypatch):
    def boom(w):
        raise DataSourceError("anahtar yok")
    monkeypatch.setattr(api, "get_bulletin", boom)
    assert client.get("/api/analiz?hafta=5").status_code == 503
