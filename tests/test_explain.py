import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TABULAR_DIR = REPO_ROOT / "models" / "tabular"
EXPLAIN_DIR = REPO_ROOT / "models" / "explain"
ETL_DIR = REPO_ROOT / "etl"
for p in (TABULAR_DIR, EXPLAIN_DIR, ETL_DIR):
    sys.path.insert(0, str(p))

import schema  # noqa: E402
import predict as predict_module  # noqa: E402
import shap_explainer  # noqa: E402
import cache as cache_module  # noqa: E402
from explain import explain  # noqa: E402
from labels import BOOL_FEATURES  # noqa: E402

BANNED_WORDS = [
    "leverage", "utilize", "robust", "foster", "seamless", "empower", "enhance",
    "facilitate", "streamline", "crucial", "pivotal", "vital", "showcase", "delve",
    "realm", "landscape", "testament", "underscore",
]


@pytest.fixture(scope="module")
def listings():
    if not schema.PROCESSED_PARQUET_PATH.exists():
        pytest.skip("processed parquet missing; run etl/etl.py first")
    return pl.read_parquet(schema.PROCESSED_PARQUET_PATH)


@pytest.fixture(scope="module")
def meta():
    try:
        return predict_module._load_bundle()
    except FileNotFoundError:
        pytest.skip("production artifact missing; run models/tabular/train.py first")


@pytest.fixture(scope="module")
def sample_rows(listings, meta):
    return listings.head(5).to_pandas().to_dict(orient="records")


def test_shap_additivity(sample_rows):
    shap_values, base_value, predictions, feature_names, _ = shap_explainer.compute_shap(sample_rows)
    reconstructed = shap_values.sum(axis=1) + base_value
    assert np.allclose(reconstructed, predictions, atol=1e-4)


def test_top_drivers_extraction_known_row():
    feature_names = ["area_m2", "has_lift", "condition", "floor"]
    shap_row = np.array([40000.0, -2000.0, 15000.0, -500.0])
    raw_row = {"area_m2": 80, "has_lift": 0, "condition": "good", "floor": 3}
    drivers = shap_explainer.top_drivers_from_shap(shap_row, feature_names, raw_row, top_n=2)
    assert len(drivers) == 2
    assert drivers[0]["feature"] == "area_m2"
    assert drivers[0]["shap_eur"] == 40000.0
    assert drivers[1]["feature"] == "condition"
    assert drivers[1]["shap_eur"] == 15000.0
    assert drivers[1]["description"] == "condition (good)"


def test_top_drivers_bool_feature_description():
    feature_names = ["has_lift"]
    shap_row = np.array([-2000.0])
    raw_row = {"has_lift": 0}
    drivers = shap_explainer.top_drivers_from_shap(shap_row, feature_names, raw_row, top_n=1)
    present, absent = BOOL_FEATURES["has_lift"]
    assert drivers[0]["description"] == absent


def test_driver_text_has_numbers_and_no_banned_words():
    drivers = [
        {"feature": "area_m2", "description": "size (80 m2)", "shap_eur": 40000.0},
        {"feature": "condition", "description": "condition (needs_renovation)", "shap_eur": -15000.0},
    ]
    text = shap_explainer.build_driver_text(340000.0, drivers)
    assert "40,000" in text
    assert "15,000" in text
    assert "340,000" in text
    lowered = text.lower()
    for word in BANNED_WORDS:
        assert word not in lowered
    assert "—" not in text
    assert "–" not in text


def test_explain_returns_range_and_drivers(sample_rows, meta):
    row = sample_rows[0]
    result = explain(row, top_n=5, use_cache=False)
    assert set(result) >= {
        "estimate", "low", "high", "interval_coverage", "base_value",
        "shap_values", "top_drivers", "driver_text", "plot",
    }
    assert result["low"] <= result["estimate"] <= result["high"]
    assert len(result["top_drivers"]) == 5
    assert isinstance(result["plot"], (bytes, bytearray))
    assert len(result["plot"]) > 0
    assert result["driver_text"].count(",") >= 1


def test_cache_round_trip(sample_rows, tmp_path):
    shap_path = tmp_path / "shap_values.parquet"
    importance_path = tmp_path / "global_importance.parquet"
    asset_ids = [r["asset_id"] for r in sample_rows]

    build_result = cache_module.build_cache(
        asset_ids=asset_ids, shap_path=shap_path, importance_path=importance_path
    )
    assert build_result["n_rows"] == len(asset_ids)
    assert shap_path.exists()
    assert importance_path.exists()

    cache_module._CACHE_TABLE = None
    cache_module._CACHE_TABLE_PATH = None
    cached = cache_module.get_cached_row(asset_ids[0], shap_path=shap_path)
    assert cached is not None

    direct_shap_values, direct_base_value, direct_predictions, direct_feature_names, _ = (
        shap_explainer.compute_shap([sample_rows[0]])
    )
    assert np.allclose(cached["shap_row"], direct_shap_values[0], atol=1e-6)
    assert cached["feature_names"] == direct_feature_names
    assert abs(cached["base_value"] - direct_base_value) < 1e-6
    assert abs(cached["prediction"] - direct_predictions[0]) < 1e-6

    importance = cache_module.load_global_importance(importance_path=importance_path)
    assert importance is not None
    assert set(importance.columns) >= {"feature", "mean_abs_shap", "share"}
    assert abs(importance["share"].sum() - 1.0) < 1e-6

    missing = cache_module.get_cached_row("not-a-real-asset-id", shap_path=shap_path)
    assert missing is None


def test_shipped_cache_files_readable():
    if not cache_module.SHAP_VALUES_PATH.exists():
        pytest.skip("shipped SHAP cache missing; run the cache build first")
    table = cache_module._load_cache_table()
    importance = cache_module.load_global_importance()
    assert len(table) > 70_000
    assert len(importance) == 38
