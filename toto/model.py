"""Dixon-Coles skor modeli, Shin marj temizleme ve hibrit olasılık."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

from toto import config
from toto.teams import normalize


@dataclass
class ModelParams:
    alphas: dict[str, float] = field(default_factory=dict)
    betas: dict[str, float] = field(default_factory=dict)
    gamma: float = config.DEFAULT_GAMMA
    rho: float = config.DEFAULT_RHO
    meta: dict = field(default_factory=dict)

    @property
    def trained(self) -> bool:
        return bool(self.alphas)

    def to_json(self) -> dict:
        return {"alphas": self.alphas, "betas": self.betas, "gamma": self.gamma, "rho": self.rho, "meta": self.meta}

    @classmethod
    def from_json(cls, d: dict) -> "ModelParams":
        return cls(d.get("alphas", {}), d.get("betas", {}), d.get("gamma", config.DEFAULT_GAMMA),
                   d.get("rho", config.DEFAULT_RHO), d.get("meta", {}))

    @classmethod
    def load(cls, path: Path = config.MODEL_PARAMS_PATH) -> "ModelParams":
        if not Path(path).exists():
            return cls()
        return cls.from_json(json.loads(Path(path).read_text(encoding="utf-8")))


def dixon_coles_tau(x, y, lam, mu, rho):
    x, y = np.asarray(x), np.asarray(y)
    tau = np.ones(np.broadcast(x, y, lam, mu).shape, dtype=float)
    tau = np.where((x == 0) & (y == 0), 1.0 - lam * mu * rho, tau)
    tau = np.where((x == 0) & (y == 1), 1.0 + lam * rho, tau)
    tau = np.where((x == 1) & (y == 0), 1.0 + mu * rho, tau)
    tau = np.where((x == 1) & (y == 1), 1.0 - rho, tau)
    return tau


def remove_margin_shin(odds_1, odds_x, odds_2):
    odds = np.array([odds_1, odds_x, odds_2], dtype=float)
    if np.any(~np.isfinite(odds)) or np.any(odds <= 1.0):
        raise ValueError("Oranlar 1.0'dan büyük olmalı")
    raw = 1.0 / odds
    beta = raw.sum()
    if beta <= 1.0:
        return raw / beta
    z = (beta - 1.0) / 3.0
    clean = (np.sqrt(z**2 + 4 * (1 - z) * raw**2 / beta) - z) / (2 * (1 - z))
    return clean / clean.sum()


def score_matrix(lam, mu, rho, max_goals=config.MAX_GOALS):
    g = np.arange(max_goals)
    m = np.outer(poisson.pmf(g, lam), poisson.pmf(g, mu))
    m *= np.clip(dixon_coles_tau(g[:, None], g[None, :], lam, mu, rho), 0.0, None)
    return m / m.sum()


def outcome_probs(matrix):
    return np.array([np.tril(matrix, -1).sum(), np.trace(matrix), np.triu(matrix, 1).sum()])


def entropy_bits(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1.0)
    return float(-(p * np.log2(p)).sum())


class HybridModel:
    def __init__(self, params: ModelParams | None = None, transfer_multipliers: dict | None = None):
        self.params = params or ModelParams()
        self.tm = {normalize(k): v for k, v in (transfer_multipliers or {}).items()}

    def expected_goals(self, home, away):
        h, a = normalize(home), normalize(away)
        p = self.params
        mh, ma = self.tm.get(h, 1.0), self.tm.get(a, 1.0)
        lam = np.exp(p.alphas.get(h, 0.0) + config.ETA * np.log(mh) + p.betas.get(a, 0.0) - config.ETA * np.log(ma)
                     + p.gamma)
        mu = np.exp(p.alphas.get(a, 0.0) + config.ETA * np.log(ma) + p.betas.get(h, 0.0) - config.ETA * np.log(mh))
        return float(lam), float(mu)

    @staticmethod
    def model_weight(week):
        week = min(max(int(week), 1), config.MAX_WEEKS)
        return config.W_DC_BASE + config.W_DC_SLOPE * week / config.MAX_WEEKS

    def predict(self, home, away, odds=None, week=1):
        """odds: (o1, ox, o2) veya None. Oran yoksa yalnız model olasılığı kullanılır."""
        lam, mu = self.expected_goals(home, away)
        p_dc = outcome_probs(score_matrix(lam, mu, self.params.rho))
        if odds is not None and all(o is not None for o in odds):
            p_mkt = remove_margin_shin(*odds)
            w = self.model_weight(week) if self.params.trained else 0.0
            p = w * p_dc + (1 - w) * p_mkt
        else:
            p = p_dc
        p = p / p.sum()
        return {"xg": (lam, mu), "probs": p, "entropy": entropy_bits(p), "model_probs": p_dc}


# Az maçlı takımların uç değerlere savrulmasını engelleyen büzüşme (shrinkage):
# gözlem sayısı azaldıkça takım gücü lig ortalamasına (0) çekilir.
SHRINK_C = 25.0
SHRINK_LAMBDA = 2.0


def fit_dixon_coles(matches, xi=0.0019, ref_date: date | None = None) -> ModelParams:
    """Zaman ağırlıklı Dixon-Coles maksimum olabilirlik kestirimi.

    matches: [{"date": date, "home": str, "away": str, "hg": int, "ag": int}, ...]
    xi: günlük zaman sönümü (Dixon & Coles 1997; ~yarı ömür 1 yıl).
    """
    if len(matches) < 50:
        raise ValueError("Eğitim için en az 50 maç gerekli")
    teams = sorted({normalize(m["home"]) for m in matches} | {normalize(m["away"]) for m in matches})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = np.array([idx[normalize(m["home"])] for m in matches])
    ai = np.array([idx[normalize(m["away"])] for m in matches])
    hg = np.array([m["hg"] for m in matches])
    ag = np.array([m["ag"] for m in matches])
    ref = ref_date or max(m["date"] for m in matches)
    w = np.exp(-xi * np.array([(ref - m["date"]).days for m in matches], dtype=float))
    obs = np.bincount(hi, minlength=n) + np.bincount(ai, minlength=n)
    shrink = SHRINK_C / (SHRINK_C + obs)

    def unpack(x):
        a = x[:n] - x[:n].mean()
        return a, x[n:2 * n], x[2 * n], x[2 * n + 1]

    def nll(x):
        a, b, gamma, rho = unpack(x)
        lam = np.exp(a[hi] + b[ai] + gamma)
        mu = np.exp(a[ai] + b[hi])
        tau = np.clip(dixon_coles_tau(hg, ag, lam, mu, rho), 1e-10, None)
        ll = np.log(tau) + poisson.logpmf(hg, lam) + poisson.logpmf(ag, mu)
        penalty = SHRINK_LAMBDA * ((shrink * a ** 2).sum() + (shrink * b ** 2).sum())
        return -(w * ll).sum() + penalty

    x0 = np.concatenate([np.zeros(2 * n), [0.25, -0.05]])
    bounds = [(-3, 3)] * (2 * n) + [(-1, 1), (-0.2, 0.2)]
    res = minimize(nll, x0, method="L-BFGS-B", bounds=bounds, options={"maxiter": 2000})
    a, b, gamma, rho = unpack(res.x)
    return ModelParams(
        alphas={t: round(float(a[i]), 5) for t, i in idx.items()},
        betas={t: round(float(b[i]), 5) for t, i in idx.items()},
        gamma=round(float(gamma), 5), rho=round(float(rho), 5),
        meta={"n_matches": len(matches), "n_teams": n, "converged": bool(res.success),
              "ref_date": ref.isoformat(), "xi": xi,
              "shrinkage": {"c": SHRINK_C, "lambda": SHRINK_LAMBDA}},
    )
