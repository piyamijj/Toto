"""Kullanım: python scripts/backtest.py --test-season 2024 --train-seasons 2021 2022 2023"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toto.backtest import evaluate  # noqa: E402
from toto.data.historical import load_seasons  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-season", type=int, required=True)
    ap.add_argument("--train-seasons", type=int, nargs="+", required=True)
    ap.add_argument("--out", default="data/backtest.json")
    a = ap.parse_args()
    report = evaluate(load_seasons(a.train_seasons), load_seasons([a.test_season]))
    report["test_season"], report["train_seasons"] = a.test_season, a.train_seasons
    Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
