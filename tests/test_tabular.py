import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TABULAR_DIR = REPO_ROOT / "models" / "tabular"
ETL_DIR = REPO_ROOT / "etl"
sys.path.insert(0, str(TABULAR_DIR))
sys.path.insert(0, str(ETL_DIR))

import schema  # noqa: E402
import split as split_module  # noqa: E402

EXPECTED_TEST_FRACTION = 0.20
FRACTION_TOLERANCE = 0.01


@pytest.fixture(scope="module")
def assignment() -> pl.DataFrame:
    if not split_module.SPLIT_PATH.exists():
        pytest.skip("split assignment missing; run models/tabular/split.py first")
    return split_module.load_split()


@pytest.fixture(scope="module")
def listings() -> pl.DataFrame:
    if not schema.PROCESSED_PARQUET_PATH.exists():
        pytest.skip("processed parquet missing; run etl/etl.py first")
    return pl.read_parquet(schema.PROCESSED_PARQUET_PATH)


def _split_ids(assignment, name):
    return set(assignment.filter(pl.col("split") == name)["asset_id"].to_list())


def test_splits_are_disjoint(assignment):
    train = _split_ids(assignment, "train")
    val = _split_ids(assignment, "val")
    test = _split_ids(assignment, "test")
    assert train.isdisjoint(val)
    assert train.isdisjoint(test)
    assert val.isdisjoint(test)


def test_split_covers_all_assets(assignment, listings):
    assigned = set(assignment["asset_id"].to_list())
    all_ids = set(listings["asset_id"].to_list())
    assert assigned == all_ids
    assert assignment.height == assignment["asset_id"].n_unique()


def test_test_size_as_expected(assignment):
    total = assignment.height
    test_n = assignment.filter(pl.col("split") == "test").height
    fraction = test_n / total
    assert abs(fraction - EXPECTED_TEST_FRACTION) < FRACTION_TOLERANCE


def test_leakage_columns_excluded_from_features():
    for col in schema.LEAKAGE_COLUMNS:
        assert col not in schema.MODEL_FEATURE_NAMES
    assert schema.TARGET not in schema.MODEL_FEATURE_NAMES


@pytest.fixture(scope="module")
def predict_module():
    import predict

    try:
        predict._load_bundle()
    except FileNotFoundError:
        pytest.skip("production artifact missing; run models/tabular/train.py first")
    return predict


def _sample_row(listings, predict_module):
    meta = predict_module._load_bundle()
    row = listings.head(1).to_pandas().iloc[0]
    return {feat: row[feat] for feat in meta["usable_features"]}


def test_predict_returns_estimate_and_range(predict_module, listings):
    row = _sample_row(listings, predict_module)
    result = predict_module.predict_one(row)
    assert set(result) >= {"estimate", "low", "high", "interval_coverage"}
    for key in ("estimate", "low", "high"):
        assert result[key] == result[key]
    assert result["estimate"] > 0
    assert result["low"] <= result["estimate"] <= result["high"]


def test_predict_batch_matches_length(predict_module, listings):
    rows = listings.head(5).to_pandas().to_dict(orient="records")
    results = predict_module.predict(rows)
    assert len(results) == 5
    for r in results:
        assert r["low"] <= r["estimate"] <= r["high"]
