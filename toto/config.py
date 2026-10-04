"""Tüm ayarlar ortam değişkenlerinden okunur. Anahtarlar asla koda yazılmaz."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_PARAMS_PATH = Path(os.getenv("TOTO_MODEL_PARAMS", DATA_DIR / "model_params.json"))
BULLETIN_PATH = Path(os.getenv("TOTO_BULLETIN_FILE", DATA_DIR / "bulten.json"))
TRANSFER_PATH = DATA_DIR / "transfer_multipliers.json"

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
API_FOOTBALL_LEAGUE = int(os.getenv("API_FOOTBALL_LEAGUE", "203"))  # Trendyol Süper Lig
API_FOOTBALL_SEASON = int(os.getenv("API_FOOTBALL_SEASON", "2026"))

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_SPORT = os.getenv("ODDS_API_SPORT", "soccer_turkey_super_league")
ODDS_API_REGIONS = os.getenv("ODDS_API_REGIONS", "eu")

CACHE_TTL_SECONDS = int(os.getenv("TOTO_CACHE_TTL", "1800"))
HTTP_TIMEOUT = float(os.getenv("TOTO_HTTP_TIMEOUT", "10"))

# Model / strateji sabitleri
MAX_WEEKS = 38
MAX_GOALS = 10
ETA = 0.25
DEFAULT_GAMMA = 0.25
DEFAULT_RHO = -0.05
W_DC_BASE, W_DC_SLOPE = 0.30, 0.55
ENTROPY_BANKO, ENTROPY_DOUBLE = 1.25, 1.48
PROB_BANKO = 0.58
