import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.data import load_listings
from agents.graph import run_copilot

SAMPLE_QUANTILES = [("cheap", 0.10), ("mid", 0.50), ("expensive", 0.90)]


def pick_samples():
    frame = load_listings().filter(pl.col("neighborhood_id").is_not_null())
    picks = []
    for label, quantile in SAMPLE_QUANTILES:
        target = frame["price"].quantile(quantile)
        row = (
            frame.with_columns((pl.col("price") - target).abs().alias("_gap"))
            .sort(["_gap", "asset_id"])
            .drop("_gap")
            .row(0, named=True)
        )
        picks.append((label, row))
    return picks


def main():
    for label, subject in pick_samples():
        result = run_copilot(subject)
        print("=" * 72)
        print(
            f"[{label}] asset_id={subject['asset_id']} "
            f"asking_price={subject['price']:,.0f} "
            f"area={subject['area_m2']} m2 barrio={subject['neighborhood_name']}"
        )
        print(f"narrative_source: {result['narrative_source']}")
        for note in result.get("errors", []):
            print(f"note: {note}")
        print()
        print(result["narrative"])
        print()


if __name__ == "__main__":
    main()
