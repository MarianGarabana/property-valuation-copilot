import sys
from pathlib import Path

import polars as pl
from sklearn.model_selection import train_test_split

TABULAR_DIR = Path(__file__).resolve().parent
REPO_ROOT = TABULAR_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from etl import schema  # noqa: E402

SPLIT_SEED = 42
TEST_FRACTION = 0.20
VAL_FRACTION_OF_REMAINDER = 0.20
SPLIT_ID = "random_seed42_train64_val16_test20"
SPLIT_PATH = TABULAR_DIR / "split_assignment.parquet"


def build_split() -> pl.DataFrame:
    df = pl.read_parquet(schema.PROCESSED_PARQUET_PATH)
    asset_ids = df[schema.IDENTIFIER_COLUMNS[0]].to_list()

    train_val_ids, test_ids = train_test_split(
        asset_ids, test_size=TEST_FRACTION, random_state=SPLIT_SEED, shuffle=True
    )
    train_ids, val_ids = train_test_split(
        train_val_ids,
        test_size=VAL_FRACTION_OF_REMAINDER,
        random_state=SPLIT_SEED,
        shuffle=True,
    )

    label = {aid: "train" for aid in train_ids}
    label.update({aid: "val" for aid in val_ids})
    label.update({aid: "test" for aid in test_ids})

    assignment = pl.DataFrame(
        {
            "asset_id": asset_ids,
            "split": [label[aid] for aid in asset_ids],
        }
    )
    assignment.write_parquet(SPLIT_PATH)
    return assignment


def load_split() -> pl.DataFrame:
    if not SPLIT_PATH.exists():
        raise FileNotFoundError(
            f"split assignment missing at {SPLIT_PATH}; run models/tabular/split.py first"
        )
    return pl.read_parquet(SPLIT_PATH)


if __name__ == "__main__":
    assignment = build_split()
    counts = assignment.group_by("split").len().sort("split")
    print(f"split_id: {SPLIT_ID}")
    print(f"seed: {SPLIT_SEED}")
    print(counts)
    print(f"written to {SPLIT_PATH}")
