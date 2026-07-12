import sys
from pathlib import Path

import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TABULAR_DIR = REPO_ROOT / "models" / "tabular"
sys.path.insert(0, str(TABULAR_DIR))
sys.path.insert(0, str(REPO_ROOT))

from etl import schema  # noqa: E402
import split as split_module  # noqa: E402

EXPECTED_TEST_FRACTION = 0.20
FRACTION_TOLERANCE = 0.01

pytestmark = pytest.mark.local_only


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


def _test_rows(listings, assignment, predict_module, limit=None):
    meta = predict_module._load_bundle()
    test_ids = _split_ids(assignment, "test")
    test_df = listings.filter(pl.col("asset_id").is_in(list(test_ids)))
    if limit is not None:
        test_df = test_df.head(limit)
    pdf = test_df.to_pandas()
    return pdf[list(meta["usable_features"])].to_dict(orient="records")


def test_interval_ordering_invariant_on_test_split(predict_module, listings, assignment):
    rows = _test_rows(listings, assignment, predict_module, limit=2000)
    results = predict_module.predict(rows)
    assert len(results) == 2000
    for r in results:
        assert r["low"] <= r["estimate"] <= r["high"]


def test_calibrated_interval_coverage_on_test(predict_module, listings, assignment):
    meta = predict_module._load_bundle()
    test_ids = list(_split_ids(assignment, "test"))
    test_df = listings.filter(pl.col("asset_id").is_in(test_ids)).to_pandas()
    rows = test_df[list(meta["usable_features"])].to_dict(orient="records")
    results = predict_module.predict(rows)
    y = test_df["price"].to_numpy()
    covered = sum(
        1 for r, yi in zip(results, y) if r["low"] <= yi <= r["high"]
    ) / len(y)
    assert 0.88 <= covered <= 0.92


def test_interval_widens_with_price(predict_module, listings, assignment):
    meta = predict_module._load_bundle()
    test_ids = list(_split_ids(assignment, "test"))
    test_df = listings.filter(pl.col("asset_id").is_in(test_ids))
    cheap = test_df.sort("price").head(1).to_pandas().iloc[0]
    expensive = test_df.sort("price", descending=True).head(1).to_pandas().iloc[0]
    cheap_row = {f: cheap[f] for f in meta["usable_features"]}
    expensive_row = {f: expensive[f] for f in meta["usable_features"]}
    cheap_res = predict_module.predict_one(cheap_row)
    expensive_res = predict_module.predict_one(expensive_row)
    cheap_width = cheap_res["high"] - cheap_res["low"]
    expensive_width = expensive_res["high"] - expensive_res["low"]
    assert expensive_res["estimate"] > cheap_res["estimate"]
    assert expensive_width > cheap_width
