import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "models" / "tabular"))

from etl import schema  # noqa: E402
import split as split_module  # noqa: E402
from mlops import drift  # noqa: E402


@pytest.fixture(scope="module")
def reference() -> pl.DataFrame:
    if not schema.PROCESSED_PARQUET_PATH.exists():
        pytest.skip("processed parquet missing; run etl/etl.py first")
    if not split_module.SPLIT_PATH.exists():
        pytest.skip("split assignment missing; run models/tabular/split.py first")
    return drift.load_reference()


def test_numeric_features_exclude_id_target_and_null(reference):
    features = drift.numeric_reference_features(reference)
    assert "neighborhood_id" not in features
    assert schema.TARGET not in features
    for leak in schema.LEAKAGE_COLUMNS:
        assert leak not in features
    assert "cnn_condition_score" not in features
    assert "area_m2" in features


def test_self_drift_reports_no_drift(reference):
    current = reference.sample(fraction=0.25, seed=7)
    result = drift.compute_drift(current, reference=reference)
    assert result["any_drift"] is False
    assert result["drifted_features"] == []
    for row in result["features"]:
        assert row["psi"] < drift.PSI_FLAG_THRESHOLD


def test_injected_shift_is_flagged(reference):
    features = drift.numeric_reference_features(reference)
    assert "area_m2" in features
    shifted = reference.with_columns(pl.col("area_m2") * 3.0)
    result = drift.compute_drift(shifted, reference=reference)
    flagged = {r["feature"]: r for r in result["features"]}
    assert flagged["area_m2"]["drifted"] is True
    assert flagged["area_m2"]["psi"] > drift.PSI_FLAG_THRESHOLD
    assert flagged["area_m2"]["ks_p_value"] < 0.05


def test_psi_zero_for_identical_arrays():
    values = np.arange(1000, dtype="float64")
    assert drift.psi(values, values) == pytest.approx(0.0, abs=1e-9)
