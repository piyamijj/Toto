"""Spor Toto Hibrit Entropi Analizörü – FastAPI uygulaması (Vercel serverless)."""
import logging

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from scipy.stats import poisson

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("toto")

# --- Yapılandırma (sihirli sayılar tek yerde) ---
MAX_WEEKS = 38
MAX_GOALS = 6
ETA = 0.25
DEFAULT_GAMMA = 0.2  # ev sahibi avantajı (log ölçeği)
DEFAULT_RHO = -0.1  # Dixon-Coles düşük skor düzeltmesi
W_DC_BASE, W_DC_SLOPE = 0.30, 0.55
ENTROPY_BANKO, ENTROPY_DOUBLE = 1.25, 1.48
PROB_BANKO = 0.58

app = FastAPI(title="Toto Analiz API", version="1.1.0")


class UnifiedFootballModel:
    def __init__(self, transfer_multipliers, eta=ETA, max_weeks=MAX_WEEKS, params=None):
        self.transfer_multipliers = transfer_multipliers
        self.eta = eta
        self.max_weeks = max_weeks
        self.params = params or {"alphas": {}, "betas": {}, "gamma": DEFAULT_GAMMA, "rho": DEFAULT_RHO}

    @staticmethod
    def _dixon_coles_tau(x, y, lambda_home, lambda_away, rho):
        if x == 0 and y == 0:
            return 1.0 - (lambda_home * lambda_away * rho)
        if x == 0 and y == 1:
            return 1.0 + (lambda_home * rho)
        if x == 1 and y == 0:
            return 1.0 + (lambda_away * rho)
        if x == 1 and y == 1:
            return 1.0 - rho
        return 1.0

    @staticmethod
    def remove_margin_shin(odds_1, odds_x, odds_2):
        odds = np.array([odds_1, odds_x, odds_2], dtype=float)
        if np.any(odds <= 1.0):
            raise ValueError("Oranlar 1.0'dan büyük olmalı")
        raw_probs = 1.0 / odds
        beta = np.sum(raw_probs)
        if beta <= 1.0:
            return raw_probs / beta
        z = (beta - 1.0) / 3.0
        clean = (np.sqrt(z**2 + 4 * (1 - z) * (raw_probs**2) / beta) - z) / (2 * (1 - z))
        return clean / np.sum(clean)

    def market_weight(self, current_week):
        week = min(max(int(current_week), 1), self.max_weeks)
        return W_DC_BASE + W_DC_SLOPE * (week / self.max_weeks)

    def predict_match(self, home_team, away_team, odds_1, odds_x, odds_2, current_week):
        p = self.params
        m_home = self.transfer_multipliers.get(home_team, 1.0)
        m_away = self.transfer_multipliers.get(away_team, 1.0)
        adj_alpha_h = p["alphas"].get(home_team, 0.0) + self.eta * np.log(m_home)
        adj_beta_a = p["betas"].get(away_team, 0.0) - self.eta * np.log(m_away)
        adj_alpha_a = p["alphas"].get(away_team, 0.0) + self.eta * np.log(m_away)
        adj_beta_h = p["betas"].get(home_team, 0.0) - self.eta * np.log(m_home)

        lambda_home = float(np.exp(adj_alpha_h + adj_beta_a + p["gamma"]))
        lambda_away = float(np.exp(adj_alpha_a + adj_beta_h))

        matrix = np.zeros((MAX_GOALS, MAX_GOALS))
        for h in range(MAX_GOALS):
            for a in range(MAX_GOALS):
                tau = self._dixon_coles_tau(h, a, lambda_home, lambda_away, p["rho"])
                matrix[h, a] = max(tau, 0.0) * poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
        matrix /= np.sum(matrix)

        p_dc = np.array([np.sum(np.tril(matrix, -1)), np.sum(np.diag(matrix)), np.sum(np.triu(matrix, 1))])
        p_market = self.remove_margin_shin(odds_1, odds_x, odds_2)
        w_dc = self.market_weight(current_week)
        p_hybrid = w_dc * p_dc + (1.0 - w_dc) * p_market
        p_hybrid /= p_hybrid.sum()
        entropy = float(-np.sum(p_hybrid * np.log2(np.clip(p_hybrid, 1e-12, 1.0))))
        return {"Home_xG": lambda_home, "Away_xG": lambda_away, "Hybrid_Probs": p_hybrid, "Entropy": entropy}


def pick_strategy(p, entropy):
    """Olasılık ve entropiye göre (öneri, strateji, kolon çarpanı) döndürür."""
    labels = ["1", "X", "2"]
    if entropy < ENTROPY_BANKO or max(p) > PROB_BANKO:
        return labels[int(np.argmax(p))], "BANKO (TEK)", 1
    if entropy <= ENTROPY_DOUBLE:
        top2 = np.argsort(p)[::-1][:2]
        order = {"1": 0, "X": 1, "2": 2}
        pick = "".join(sorted((labels[i] for i in top2), key=order.get))
        return pick, "ÇİFTE ŞANS", 2
    return "1X2", "KAPAT", 3


def fetch_spor_toto_bulletin():
    """ÖRNEK VERİ – Faz 2'de gerçek veri kaynağıyla değiştirilecek."""
    home = ["Galatasaray", "Fenerbahçe", "Trabzonspor", "Beşiktaş", "Başakşehir", "Kasımpaşa", "Sivasspor",
            "Alanyaspor", "Antalyaspor", "Göztepe", "Kayserispor", "Hatayspor", "Samsunspor", "Rizespor", "Bodrum FK"]
    away = ["Göztepe", "Trabzonspor", "Beşiktaş", "Başakşehir", "Kasımpaşa", "Sivasspor", "Alanyaspor",
            "Antalyaspor", "Rizespor", "Gaziantep FK", "Konyaspor", "Bodrum FK", "Adana Demirspor", "Galatasaray", "Fenerbahçe"]
    o1 = [1.35, 2.10, 2.40, 1.85, 2.05, 2.20, 2.15, 2.30, 2.25, 1.90, 2.40, 2.10, 1.65, 4.50, 4.20]
    ox = [4.50, 3.30, 3.20, 3.40, 3.25, 3.10, 3.20, 3.15, 3.20, 3.30, 3.10, 3.20, 3.60, 3.80, 3.60]
    o2 = [7.50, 3.10, 2.70, 3.80, 3.20, 3.00, 3.10, 2.90, 2.95, 3.60, 2.75, 3.30, 4.80, 1.65, 1.70]
    return [
        {"home_team": h, "away_team": a, "odds_1": x, "odds_X": y, "odds_2": z}
        for h, a, x, y, z in zip(home, away, o1, ox, o2)
    ]


TRANSFER_MULTIPLIERS = {"Galatasaray": 1.10, "Fenerbahçe": 1.15, "Trabzonspor": 1.40,
                        "Beşiktaş": 1.20, "Göztepe": 0.90, "Bodrum FK": 0.85}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/analiz")
def analiz_et(hafta: int = Query(3, ge=1, le=MAX_WEEKS, description="Sezon haftası (1-38)")):
    model = UnifiedFootballModel(transfer_multipliers=TRANSFER_MULTIPLIERS)
    results = []
    try:
        for idx, row in enumerate(fetch_spor_toto_bulletin()):
            pred = model.predict_match(row["home_team"], row["away_team"], row["odds_1"], row["odds_X"],
                                       row["odds_2"], current_week=hafta)
            p = pred["Hybrid_Probs"]
            pick, action, mult = pick_strategy(p, pred["Entropy"])
            results.append({
                "no": idx + 1, "mac": f"{row['home_team']} - {row['away_team']}",
                "xg": f"{pred['Home_xG']:.2f} - {pred['Away_xG']:.2f}",
                "p1": f"%{p[0]*100:.1f}", "px": f"%{p[1]*100:.1f}", "p2": f"%{p[2]*100:.1f}",
                "oneri": pick, "strateji": action, "carpan": mult,
            })
    except ValueError as exc:
        logger.exception("Analiz hatası")
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    total = int(np.prod([r["carpan"] for r in results]))
    return {"maclar": results, "toplam_kolon": f"{total:,}", "veri_kaynagi": "ornek"}
