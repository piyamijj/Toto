"""Modeli gerçek tarihsel Süper Lig sonuçlarıyla eğitir ve data/model_params.json dosyasına yazar.

Kullanım:  python scripts/train.py --seasons 2022 2023 2024 2025 [--espn-since auto|none|YYYY-MM-DD]
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toto import config  # noqa: E402
from toto.data.espn import load_since as espn_load_since  # noqa: E402
from toto.data.historical import load_seasons  # noqa: E402
from toto.model import fit_dixon_coles  # noqa: E402
from toto.teams import normalize  # noqa: E402


def merge_espn(matches, since):
    """Güncel sezon biten maçlarını tekrarları eleyerek ekler. (eklenen, atlanan_gün)"""
    extra, skipped = espn_load_since(since)
    seen = {(m["date"], normalize(m["home"]), normalize(m["away"])) for m in matches}
    added = 0
    for m in extra:
        key = (m["date"], normalize(m["home"]), normalize(m["away"]))
        if key not in seen:
            seen.add(key)
            matches.append(m)
            added += 1
    return added, skipped


def main():
    now = datetime.now(timezone.utc)
    current = now.year if now.month >= 7 else now.year - 1
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, nargs="+", default=[current - 3, current - 2, current - 1, current])
    ap.add_argument("--espn-since", default="auto",
                    help="'auto' (sezon başı 1 Ağustos), YYYY-MM-DD veya 'none'")
    ap.add_argument("--out", default=str(config.MODEL_PARAMS_PATH))
    args = ap.parse_args()

    matches = []
    for s in args.seasons:
        try:
            matches.extend(load_seasons([s]))
        except Exception as exc:  # henüz yayınlanmamış sezon vb.
            print(f"Sezon {s} atlandı: {exc}")
    print(f"{len(matches)} maç yüklendi")

    if args.espn_since != "none":
        try:
            since = date(current, 8, 1) if args.espn_since == "auto" else datetime.strptime(
                args.espn_since, "%Y-%m-%d").date()
            added, skipped = merge_espn(matches, since)
            print(f"ESPN güncel sezon: +{added} maç ({skipped} gün atlandı)")
        except Exception as exc:
            print(f"ESPN atlandı: {exc}")

    params = fit_dixon_coles(matches)
    params.meta.update({"seasons": args.seasons, "trained_at": now.isoformat(),
                        "source": "football-data.co.uk T1"})
    Path(args.out).write_text(json.dumps(params.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Parametreler yazıldı: {args.out} ({params.meta})")


if __name__ == "__main__":
    main()
