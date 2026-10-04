import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.index import UnifiedFootballModel, app, pick_strategy

client = TestClient(app)


def test_shin_sums_to_one():
    p = UnifiedFootballModel.remove_margin_shin(2.1, 3.3, 3.1)
    assert np.isclose(p.sum(), 1.0)
    assert np.all(p > 0)


def test_shin_rejects_invalid_odds():
    with pytest.raises(ValueError):
        UnifiedFootballModel.remove_margin_shin(1.0, 3.0, 3.0)


def test_prediction_probabilities_valid():
    m = UnifiedFootballModel({})
    out = m.predict_match("A", "B", 2.0, 3.4, 3.6, current_week=10)
    p = out["Hybrid_Probs"]
    assert np.isclose(p.sum(), 1.0)
    assert np.all(p >= 0)
    assert 0 <= out["Entropy"] <= np.log2(3) + 1e-9


def test_strategy_banko():
    assert pick_strategy(np.array([0.7, 0.2, 0.1]), 1.1)[2] == 1


def test_strategy_double_order():
    pick, _, mult = pick_strategy(np.array([0.30, 0.25, 0.45]), 1.40)
    assert mult == 2 and pick == "12"


def test_strategy_cover_all():
    assert pick_strategy(np.array([0.34, 0.33, 0.33]), 1.58)[0] == "1X2"


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


@pytest.mark.parametrize("week", [0, -1, 39])
def test_invalid_week_rejected(week):
    assert client.get(f"/api/analiz?hafta={week}").status_code == 422


def test_analiz_ok():
    r = client.get("/api/analiz?hafta=5")
    assert r.status_code == 200
    assert len(r.json()["maclar"]) == 15
