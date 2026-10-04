"""Spor Toto Hibrit Entropi Analizörü – FastAPI uygulaması (Vercel serverless)."""
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toto import config  # noqa: E402
from toto.data.fixtures import get_bulletin  # noqa: E402
from toto.data.http import DataSourceError  # noqa: E402
from toto.model import HybridModel, ModelParams  # noqa: E402
from toto.optimizer import optimise_coupon  # noqa: E402
from toto.ratelimit import RateLimiter  # noqa: E402
from toto.strategy import pick_strategy  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("toto")

if os.getenv("SENTRY_DSN"):
    import sentry_sdk

    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], traces_sample_rate=0.1)

app = FastAPI(title="Toto Analiz API", version="3.0.0")
limiter = RateLimiter(int(os.getenv("TOTO_RATE_LIMIT_PER_MIN", "30")))


@app.middleware("http")
async def guard(request: Request, call_next):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0]
    if request.url.path.startswith("/api/analiz") and not limiter.allow(ip.strip()):
        return JSONResponse({"detail": "Çok fazla istek, lütfen biraz bekleyin."}, status_code=429)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/analiz"):
        response.headers["Cache-Control"] = "public, s-maxage=900, stale-while-revalidate=600"
    return response


def load_model() -> HybridModel:
    tm = {}
    if config.TRANSFER_PATH.exists():
        tm = json.loads(config.TRANSFER_PATH.read_text(encoding="utf-8"))
    return HybridModel(ModelParams.load(), tm)


@app.get("/api/health")
def health():
    params = ModelParams.load()
    return {"status": "ok", "model_trained": params.trained, "model_meta": params.meta,
            "sources": {"api_football": bool(config.API_FOOTBALL_KEY), "odds_api": bool(config.ODDS_API_KEY),
                        "bulten_dosyasi": config.BULLETIN_PATH.exists()}}


def analyse(bulletin, week, model):
    results = []
    for i, m in enumerate(bulletin["maclar"], start=1):
        pred = model.predict(m["home_team"], m["away_team"], m.get("odds"), week)
        p = pred["probs"]
        pick, action, mult = pick_strategy(p, pred["entropy"])
        results.append({
            "no": i, "mac": f"{m['home_team']} - {m['away_team']}",
            "xg": f"{pred['xg'][0]:.2f} - {pred['xg'][1]:.2f}",
            "p1": f"%{p[0]*100:.1f}", "px": f"%{p[1]*100:.1f}", "p2": f"%{p[2]*100:.1f}",
            "oneri": pick, "strateji": action, "carpan": mult, "oran_var": m.get("odds") is not None,
            "olasiliklar": [round(float(x), 4) for x in p],
        })
    return results


@app.get("/api/analiz")
def analiz_et(hafta: int = Query(..., ge=1, le=config.MAX_WEEKS, description="Sezon haftası (1-38)"),
             butce: int | None = Query(None, ge=1, le=100000, description="Maks. kolon sayısı")):
    model = load_model()
    if not model.params.trained:
        raise HTTPException(503, "Model henüz eğitilmedi. 'python scripts/train.py' çalıştırın.")
    try:
        bulletin = get_bulletin(hafta)
    except DataSourceError as exc:
        logger.warning("Veri kaynağı hatası: %s", exc)
        raise HTTPException(503, f"Bülten alınamadı: {exc}") from exc
    if not bulletin["maclar"]:
        raise HTTPException(404, f"{hafta}. hafta için maç bulunamadı")
    try:
        results = analyse(bulletin, hafta, model)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    total = int(np.prod([r["carpan"] for r in results]))
    optimised = None
    if butce:
        optimised = optimise_coupon([r["olasiliklar"] for r in results], butce)
        for r, sel in zip(results, optimised["secimler"]):
            r["butce_secimi"] = sel
    return {"maclar": results, "toplam_kolon": f"{total:,}", "veri_kaynagi": bulletin["kaynak"],
            "model": model.params.meta, "butce_kuponu": optimised}


@app.get("/api/model")
def model_info():
    params = ModelParams.load()
    backtest_path = config.DATA_DIR / "backtest.json"
    backtest = json.loads(backtest_path.read_text(encoding="utf-8")) if backtest_path.exists() else None
    return {"trained": params.trained, "meta": params.meta, "gamma": params.gamma, "rho": params.rho,
            "takim_sayisi": len(params.alphas), "backtest": backtest}


# GECICI TANI: Vercel'in uygulamaya ulastirdigi gercek yolu gosterir (kaldirilacak).
@app.api_route("/__debug_path", methods=["GET"])
def debug_path(request: Request):
    return {"path": request.url.path, "root_path": request.scope.get("root_path")}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def debug_catchall(request: Request):
    return {"seen_path": request.url.path, "note": "catchall"}
