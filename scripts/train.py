"""Modeli gerçek tarihsel Süper Lig sonuçlarıyla eğitir ve data/model_params.json dosyasına yazar.

Kullanım:  python scripts/train.py --seasons 2022 2023 2024 2025
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toto import config  # noqa: E402
from toto.data.historical import load_seasons  # noqa: E402
from toto.model import fit_dixon_coles  # noqa: E402


def main():
    now = datetime.now(timezone.utc)
    current = now.year if now.month >= 7 else now.year - 1
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, nargs="+", default=[current - 3, current - 2, current - 1, current])
    ap.add_argument("--out", default=str(config.MODEL_PARAMS_PATH))
    args = ap.parse_args()

    matches = []
    for s in args.seasons:
        try:
            matches.extend(load_seasons([s]))
        except Exception as exc:  # henüz yayınlanmamış sezon vb.
            print(f"Sezon {s} atlandı: {exc}")
    print(f"{len(matches)} maç yüklendi")
    params = fit_dixon_coles(matches)
    params.meta.update({"seasons": args.seasons, "trained_at": now.isoformat(),
                        "source": "football-data.co.uk T1"})
    Path(args.out).write_text(json.dumps(params.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Parametreler yazıldı: {args.out} ({params.meta})")


if __name__ == "__main__":
    main()
