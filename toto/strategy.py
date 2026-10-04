"""Entropi tabanlı kupon stratejisi."""
import numpy as np

from toto import config

LABELS = ("1", "X", "2")


def pick_strategy(p, entropy):
    """(öneri, strateji, kolon çarpanı) döndürür."""
    p = np.asarray(p)
    if entropy < config.ENTROPY_BANKO or p.max() > config.PROB_BANKO:
        return LABELS[int(p.argmax())], "BANKO (TEK)", 1
    if entropy <= config.ENTROPY_DOUBLE:
        top2 = sorted(np.argsort(p)[::-1][:2])
        return "".join(LABELS[i] for i in top2), "ÇİFTE ŞANS", 2
    return "1X2", "KAPAT", 3
