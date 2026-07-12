import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from etl.schema import PROCESSED_PARQUET_PATH

_LISTINGS = None


def load_listings():
    global _LISTINGS
    if _LISTINGS is None:
        _LISTINGS = pl.read_parquet(PROCESSED_PARQUET_PATH)
    return _LISTINGS


def get_subject(asset_id):
    row = load_listings().filter(pl.col("asset_id") == asset_id)
    if row.height == 0:
        raise KeyError(f"asset_id {asset_id} not found in listings")
    return row.row(0, named=True)
