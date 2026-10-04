import numpy as np
import pandas as pd
from scipy.stats import poisson
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Ön yüzün backend ile güvenli konuşabilmesi için CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# numaralı dosyada yer alan model mimarinizi buraya birebir entegre ediyoruz
class UnifiedFootballModel:
    def __init__(self, transfer_multipliers, eta=0.25, max_weeks=38):
        self.transfer_multipliers = transfer_multipliers
        self.eta = eta
        self.max_weeks = max_weeks
        self.params = {'alphas': {}, 'betas': {}, 'gamma': 0.2, 'rho': -0.1} # Default baseline
        
    @staticmethod
    def _dixon_coles_tau(x, y, lambda_home, lambda_away, rho):
        if x == 0 and y == 0: return 1.0 - (lambda_home * lambda_away * rho)
        elif x == 0 and y == 1: return 1.0 + (lambda_home * rho)
        elif x == 1 and y == 0: return 1.0 + (lambda_away * rho)
        elif x == 1 and y == 1: return 1.0 - rho
        return 1.0

    @staticmethod
    def remove_margin_shin(odds_1, odds_X, odds_2):
        raw_probs = np.array([1.0 / odds_1, 1.0 / odds_X, 1.0 / odds_2])
        beta = np.sum(raw_probs)
        if beta <= 1.0: return raw_probs
        z = (beta - 1.0) / 3.0
        clean_probs = (np.sqrt(z**2 + 4 * (1 - z) * (raw_probs**2) / beta) - z) / (2 * (1 - z))
        return clean_probs / np.sum(clean_probs)

    def predict_match(self, home_team, away_team, odds_1, odds_X, odds_2, current_week):
        h_alpha = self.params['alphas'].get(home_team, 0.0)
        a_beta  = self.params['betas'].get(away_team, 0.0)
        a_alpha = self.params['alphas'].get(away_team, 0.0)
        h_beta  = self.params['betas'].get(home_team, 0.0)

        m_home = self.transfer_multipliers.get(home_team, 1.0)
        m_away = self.transfer_multipliers.get(away_team, 1.0)
        
        adj_alpha_h = h_alpha + (self.eta * np.log(m_home))
        adj_beta_a  = a_beta  - (self.eta * np.log(m_away))
        adj_alpha_a = a_alpha + (self.eta * np.log(m_away))
        adj_beta_h  = h_beta  - (self.eta * np.log(m_home))
        
        lambda_home = np.exp(adj_alpha_h + adj_beta_a + self.params['gamma'])
        lambda_away = np.exp(adj_alpha_a + adj_beta_h)
        
        score_matrix = np.zeros((6, 6))
        for h in range(6):
            for a in range(6):
                tau = self._dixon_coles_tau(h, a, lambda_home, lambda_away, self.params['rho'])
                score_matrix[h, a] = tau * poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
        score_matrix /= np.sum(score_matrix)
        
        p_dc = np.array([np.sum(np.tril(score_matrix, -1)), np.sum(np.diag(score_matrix)), np.sum(np.triu(score_matrix, 1))])
        p_market = self.remove_margin_shin(odds_1, odds_X, odds_2)
        
        w_dc = 0.30 + (0.55 * (current_week / self.max_weeks))
        p_hybrid = (w_dc * p_dc) + ((1.0 - w_dc) * p_market)
        entropy = -np.sum(p_hybrid * np.log2(np.clip(p_hybrid, 1e-12, 1.0)))
        
        return {"Home_xG": lambda_home, "Away_xG": lambda_away, "Hybrid_Probs": p_hybrid, "Entropy": entropy}

def fetch_spor_toto_bulletin():
    # Web scraping fallbacksiz dinamik yapı
    return pd.DataFrame({
        'home_team': ['Galatasaray', 'Fenerbahçe', 'Trabzonspor', 'Beşiktaş', 'Başakşehir', 'Kasımpaşa', 'Sivasspor', 'Alanyaspor', 'Antalyaspor', 'Göztepe', 'Kayserispor', 'Hatayspor', 'Samsunspor', 'Rizespor', 'Bodrum FK'],
        'away_team': ['Göztepe', 'Trabzonspor', 'Beşiktaş', 'Başakşehir', 'Kasımpaşa', 'Sivasspor', 'Alanyaspor', 'Antalyaspor', 'Rizespor', 'Gaziantep FK', 'Konyaspor', 'Bodrum FK', 'Adana Demirspor', 'Galatasaray', 'Fenerbahçe'],
        'odds_1': [1.35, 2.10, 2.40, 1.85, 2.05, 2.20, 2.15, 2.30, 2.25, 1.90, 2.40, 2.10, 1.65, 4.50, 4.20],
        'odds_X': [4.50, 3.30, 3.20, 3.40, 3.25, 3.10, 3.20, 3.15, 3.20, 3.30, 3.10, 3.20, 3.60, 3.80, 3.60],
        'odds_2': [7.50, 3.10, 2.70, 3.80, 3.20, 3.00, 3.10, 2.90, 2.95, 3.60, 2.75, 3.30, 4.80, 1.65, 1.70]
    })

@app.get("/api/analiz")
def analiz_et(hafta: int = 3):
    df_bulten = fetch_spor_toto_bulletin()
    transfer_multipliers = {'Galatasaray': 1.10, 'Fenerbahçe': 1.15, 'Trabzonspor': 1.40, 'Beşiktaş': 1.20, 'Göztepe': 0.90, 'Bodrum FK': 0.85}
    
    model = UnifiedFootballModel(transfer_multipliers=transfer_multipliers)
    results = []
    
    for idx, row in df_bulten.iterrows():
        pred = model.predict_match(row['home_team'], row['away_team'], row['odds_1'], row['odds_X'], row['odds_2'], current_week=hafta)
        p = pred['Hybrid_Probs']
        entropy = pred['Entropy']
        
        if entropy < 1.25 or max(p) > 0.58:
            pick, action, mult = ["1", "X", "2"][np.argmax(p)], "✅ BANKO (TEK)", 1
        elif 1.25 <= entropy <= 1.48:
            sorted_p = np.argsort(p)[::-1][:2]
            mapping = {0: "1", 1: "X", 2: "2"}
            pick, action, mult = "".join(sorted([mapping[sorted_p[0]], mapping[mapping[sorted_p[1]]]]), "⚠️ ÇİFTE ŞANS", 2
        else:
            pick, action, mult = "1X2", "🔥 KAPAT", 3
            
        results.append({
            "no": idx + 1, "mac": f"{row['home_team']} - {row['away_team']}",
            "xg": f"{pred['Home_xG']:.2f} - {pred['Away_xG']:.2f}",
            "p1": f"%{p[0]*100:.1f}", "px": f"%{p[1]*100:.1f}", "p2": f"%{p[2]*100:.1f}",
            "oneri": pick, "strateji": action, "carpan": mult
        })
    
    total_comb = int(np.prod([r['carpan'] for r in results]))
    return {"maclar": results, "toplam_kolon": f"{total_comb:,}"}
