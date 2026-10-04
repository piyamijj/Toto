"""Geriye dönük test: modeli önceki sezonlarla eğitip hedef sezonu tahmin eder."""
import numpy as np

from toto.model import HybridModel, fit_dixon_coles, remove_margin_shin

OUTCOME = {"H": 0, "D": 1, "A": 2}


def result_index(m):
    return 0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2


def evaluate(train, test, week_of=lambda i, n: max(1, round(38 * (i + 1) / n))):
    """Model, piyasa ve hibrit için Brier, log-loss ve isabet döndürür."""
    model = HybridModel(fit_dixon_coles(train))
    rows = {"model": [], "piyasa": [], "hibrit": []}
    for i, m in enumerate(test):
        y = np.zeros(3)
        y[result_index(m)] = 1
        pred = model.predict(m["home"], m["away"], m["odds"] if all(m["odds"]) else None, week_of(i, len(test)))
        rows["model"].append((pred["model_probs"], y))
        rows["hibrit"].append((pred["probs"], y))
        if all(m["odds"]):
            rows["piyasa"].append((remove_margin_shin(*m["odds"]), y))
    out = {}
    for k, pairs in rows.items():
        if not pairs:
            continue
        P = np.array([p for p, _ in pairs])
        Y = np.array([y for _, y in pairs])
        out[k] = {"n": len(pairs), "brier": float(((P - Y) ** 2).sum(1).mean()),
                  "log_loss": float(-np.log(np.clip((P * Y).sum(1), 1e-12, 1)).mean()),
                  "isabet": float((P.argmax(1) == Y.argmax(1)).mean())}
    return out
