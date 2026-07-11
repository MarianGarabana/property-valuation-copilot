"""Data validation for the processed idealista18 Madrid listings.

Checks row counts, null rates per key column, and value ranges (price/area > 0,
coordinates inside the Madrid bounding box). Data is 2018 asking prices.
"""

import sys
from pathlib import Path

import polars as pl
import pytest

ETL_DIR = Path(__file__).resolve().parents[1] / "etl"
sys.path.insert(0, str(ETL_DIR))

import schema  # noqa: E402

CONDITIONS = {"new", "needs_renovation", "good"}
PROPERTY_TYPES = {"studio", "duplex", "flat"}
PERIODS_2018 = {201803, 201806, 201809, 201812}
ROW_MIN, ROW_MAX = 60_000, 80_000


@pytest.fixture(scope="module")
def df() -> pl.DataFrame:
    if not schema.PROCESSED_PARQUET_PATH.exists():
        pytest.skip("processed parquet missing; run etl/etl.py first")
    return pl.read_parquet(schema.PROCESSED_PARQUET_PATH)


def test_columns_match_schema(df):
    assert df.columns == schema.FEATURE_NAMES


def test_row_count_in_bounds(df):
    assert ROW_MIN <= df.height <= ROW_MAX


def test_asset_id_unique(df):
    assert df["asset_id"].n_unique() == df.height


def test_key_columns_have_no_nulls(df):
    for col in schema.KEY_COLUMNS:
        assert df[col].null_count() == 0, f"{col} has nulls"


def test_construction_year_null_rate_bounded(df):
    # ~60% of idealista18 rows lack a construction year; guard against total loss.
    rate = df["construction_year"].null_count() / df.height
    assert rate < 0.7


def test_placeholders_are_null(df):
    assert df["cnn_condition_score"].null_count() == df.height
    assert df["neighborhood_name"].null_count() == df.height


def test_price_and_area_positive(df):
    assert df["price"].min() > 0
    assert df["area_m2"].min() > 0
    assert df["unit_price_m2"].min() > 0


def test_coordinates_inside_madrid_bbox(df):
    b = schema.MADRID_BBOX
    assert df["latitude"].min() >= b["lat_min"]
    assert df["latitude"].max() <= b["lat_max"]
    assert df["longitude"].min() >= b["lon_min"]
    assert df["longitude"].max() <= b["lon_max"]


def test_counts_non_negative(df):
    assert df["rooms"].min() >= 0
    assert df["bathrooms"].min() >= 0


def test_categoricals_in_allowed_sets(df):
    assert set(df["condition"].unique()) <= CONDITIONS
    assert set(df["property_type"].unique()) <= PROPERTY_TYPES
    assert set(df["period"].unique()) <= PERIODS_2018


def test_construction_year_range_when_present(df):
    present = df["construction_year"].drop_nulls()
    assert present.min() >= schema.CONSTRUCTION_YEAR_MIN
    assert present.max() <= schema.CONSTRUCTION_YEAR_MAX
