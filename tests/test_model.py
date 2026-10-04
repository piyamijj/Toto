from datetime import date, timedelta

import numpy as np
import pytest

from toto.model import (HybridModel, ModelParams, dixon_coles_tau, fit_dixon_coles, outcome_probs,
                        remove_margin_shin, score_matrix)
from toto.strategy import pick_strategy


def test_shin_sums_to_one():
    p = remove_margin_shin(2.1, 3.3, 3.1)
    assert np.isclose(p.sum(), 1.0) and np.all(p > 0)


def test_shin_rejects_invalid_odds():
    with pytest.raises(ValueError):
        remove_margin_shin(1.0, 3.0, 3.0)


def test_tau_values():
    assert np.isclose(dixon_coles_tau(1, 1, 1.5, 1.0, -0.1), 1.1)
    assert np.isclose(dixon_coles_tau(2, 3, 1.5, 1.0, -0.1), 1.0)


def test_score_matrix_normalised():
    m = score_matrix(1.6, 1.1, -0.05)
    assert np.isclose(m.sum(), 1.0)
    p = outcome_probs(m)
    assert p[0] > p[2]


def test_predict_without_odds_uses_model():
    out = HybridModel().predict("A", "B", None, 5)
    assert np.isclose(out["probs"].sum(), 1.0)
    assert np.allclose(out["probs"], out["model_probs"])


def test_untrained_model_falls_back_to_market():
    out = HybridModel().predict("A", "B", (2.0, 3.4, 3.6), 20)
    assert np.allclose(out["probs"], remove_margin_shin(2.0, 3.4, 3.6))


def _synthetic(seed=1):
    rng = np.random.default_rng(seed)
    strength = {"Guclu": 0.5, "Orta1": 0.1, "Orta2": 0.0, "Orta3": -0.1, "Zayif1": -0.3, "Zayif2": -0.4}
    teams, matches, d = list(strength), [], date(2024, 8, 1)
    for _ in range(6):
        for h in teams:
            for a in teams:
                if h == a:
                    continue
                lam = np.exp(strength[h] - strength[a] * 0.8 + 0.25)
                mu = np.exp(strength[a] - strength[h] * 0.8)
                matches.append({"date": d, "home": h, "away": a, "hg": int(rng.poisson(lam)),
                                "ag": int(rng.poisson(mu))})
                d += timedelta(days=1)
    return matches


def test_fit_recovers_strength_order():
    params = fit_dixon_coles(_synthetic())
    assert params.trained and params.meta["converged"]
    assert params.alphas["guclu"] > params.alphas["zayif2"]
    assert params.betas["guclu"] < params.betas["zayif2"]
    assert 0 < params.gamma < 0.6


def test_fit_requires_data():
    with pytest.raises(ValueError):
        fit_dixon_coles(_synthetic()[:10])


def test_params_roundtrip(tmp_path):
    p = ModelParams({"a": 0.1}, {"a": -0.1}, 0.3, -0.05, {"x": 1})
    f = tmp_path / "p.json"
    import json
    f.write_text(json.dumps(p.to_json()))
    assert ModelParams.load(f).alphas == {"a": 0.1}
    assert not ModelParams.load(tmp_path / "yok.json").trained


def test_strategy():
    assert pick_strategy(np.array([0.7, 0.2, 0.1]), 1.1) == ("1", "BANKO (TEK)", 1)
    assert pick_strategy(np.array([0.30, 0.25, 0.45]), 1.40)[0] == "12"
    assert pick_strategy(np.array([0.34, 0.33, 0.33]), 1.58)[0] == "1X2"


def test_shrinkage_tames_single_match_wonder(monkeypatch):
    import toto.model as M
    freak = {"date": date(2024, 8, 1), "home": "Tek", "away": "Guclu", "hg": 8, "ag": 0}
    data = _synthetic() + [freak]
    monkeypatch.setattr(M, "SHRINK_LAMBDA", 0.0)
    raw = fit_dixon_coles(data).alphas["tek"]
    monkeypatch.setattr(M, "SHRINK_LAMBDA", 2.0)
    shrunk = fit_dixon_coles(data).alphas["tek"]
    assert abs(shrunk) < abs(raw) and raw > 1.0
