import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _p in (
    str(REPO_ROOT),
    str(REPO_ROOT / "models" / "explain"),
    str(REPO_ROOT / "models" / "tabular"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import explain as _explain
import predict as _predict


def run(subject):
    interval = _predict.predict_one(subject)
    explained = _explain.explain(subject)
    return {
        "estimate": interval["estimate"],
        "low": interval["low"],
        "high": interval["high"],
        "interval_coverage": interval["interval_coverage"],
        "interval_test_coverage": interval["interval_test_coverage"],
        "top_drivers": explained["top_drivers"],
        "driver_text": explained["driver_text"],
    }
