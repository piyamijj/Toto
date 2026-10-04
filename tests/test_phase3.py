from datetime import date, timedelta

import numpy as np
from fastapi.testclient import TestClient

import api.index as api
from tests.test_api import BULLETIN, TRAINED
from toto.backtest import evaluate
from toto.model import HybridModel
from toto.optimizer import optimise_coupon
from toto.ratelimit import RateLimiter


def test_optimiser_respects_budget():
    rng = np.random.default_rng(0)
    probs = [rng.dirichlet([2, 1.5, 1.5]) for _ in range(15)]
    for budget in (1, 8, 96, 500):
        out = optimise_coupon(probs, budget)
        assert out["kolon"] <= budget
        assert np.prod([len(s) for s in out["secimler"]]) == out["kolon"]
    assert optimise_coupon(probs, 1)["secimler"] == ["1X2"[int(np.argmax(p))] for p in probs]


def test_optimiser_full_cover():
    out = optimise_coupon([np.array([0.4, 0.3, 0.3])] * 2, 9)
    assert out["kolon"] == 9 and np.isclose(out["tutma_olasiligi"], 1.0)


def test_rate_limiter():
    rl = RateLimiter(2, 60)
    assert rl.allow("x") and rl.allow("x") and not rl.allow("x") and rl.allow("y")


def _season(start, seed):
    rng = np.random.default_rng(seed)
    s = {"A": 0.4, "B": 0.1, "C": 0.0, "D": -0.2, "E": -0.3}
    out, d = [], start
    for _ in range(4):
        for h in s:
            for a in s:
                if h != a:
                    out.append({"date": d, "home": h, "away": a, "hg": int(rng.poisson(np.exp(s[h] - s[a] + 0.2))),
                                "ag": int(rng.poisson(np.exp(s[a] - s[h]))), "odds": (2.0, 3.4, 3.6)})
                    d += timedelta(days=2)
    return out


def test_backtest_metrics():
    rep = evaluate(_season(date(2023, 8, 1), 1), _season(date(2024, 8, 1), 2))
    for k in ("model", "piyasa", "hibrit"):
        assert 0 <= rep[k]["brier"] <= 2 and 0 <= rep[k]["isabet"] <= 1
    assert rep["model"]["brier"] < rep["piyasa"]["brier"] + 0.1


def test_api_budget(monkeypatch):
    monkeypatch.setattr(api, "load_model", lambda: HybridModel(TRAINED))
    monkeypatch.setattr(api, "get_bulletin", lambda w: BULLETIN)
    body = TestClient(api.app).get("/api/analiz?hafta=5&butce=4").json()
    assert body["butce_kuponu"]["kolon"] <= 4
    assert "butce_secimi" in body["maclar"][0]


def test_model_endpoint():
    r = TestClient(api.app).get("/api/model")
    assert r.status_code == 200 and "trained" in r.json()
