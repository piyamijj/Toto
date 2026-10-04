"""Kolon bütçesi altında kupon optimizasyonu.

Her maç için kapsanan sonuç kümesi seçilir; amaç tüm maçların doğru tahmin edilme olasılığını
(kapsanan olasılıkların çarpımı) en büyüklemek, kısıt ise toplam kolon sayısı ≤ bütçe.
Açgözlü yaklaşım: her adımda log-olasılık kazancı / log-kolon maliyeti en yüksek genişletme seçilir.
"""
import math

import numpy as np

LABELS = ("1", "X", "2")


def optimise_coupon(probs, budget):
    if budget < 1:
        raise ValueError("Bütçe en az 1 kolon olmalı")
    order = [list(np.argsort(p)[::-1]) for p in probs]
    sizes = [1] * len(probs)
    cover = [float(p[o[0]]) for p, o in zip(probs, order)]
    total = 1
    while True:
        best, best_score = None, 0.0
        for i, p in enumerate(probs):
            if sizes[i] == 3:
                continue
            new_total = total // sizes[i] * (sizes[i] + 1)
            if new_total > budget:
                continue
            new_cover = cover[i] + float(p[order[i][sizes[i]]])
            score = math.log(new_cover / max(cover[i], 1e-12)) / math.log((sizes[i] + 1) / sizes[i])
            if score > best_score:
                best, best_score = i, score
        if best is None:
            break
        total = total // sizes[best] * (sizes[best] + 1)
        cover[best] += float(probs[best][order[best][sizes[best]]])
        sizes[best] += 1
    picks = ["".join(LABELS[j] for j in sorted(o[:s])) for o, s in zip(order, sizes)]
    return {"secimler": picks, "kolon": total, "tutma_olasiligi": float(np.prod(cover))}
