import sys
from pathlib import Path

EXPLAIN_DIR = Path(__file__).resolve().parent
TABULAR_DIR = EXPLAIN_DIR.parents[0] / "tabular"
REPO_ROOT = EXPLAIN_DIR.parents[1]
for p in (str(TABULAR_DIR), str(REPO_ROOT), str(EXPLAIN_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd
import polars as pl

from etl import schema
from split import load_split
import shap_explainer

CACHE_DIR = EXPLAIN_DIR / "cache"
SHAP_VALUES_PATH = CACHE_DIR / "shap_values.parquet"
GLOBAL_IMPORTANCE_PATH = CACHE_DIR / "global_importance.parquet"


def _load_rows(split_names):
    df = pl.read_parquet(schema.PROCESSED_PARQUET_PATH)
    if split_names is not None:
        assignment = load_split()
        df = df.join(assignment, on="asset_id", how="inner").filter(
            pl.col("split").is_in(split_names)
        )
    return df.to_pandas()


def build_cache(split_names=None, asset_ids=None, shap_path=SHAP_VALUES_PATH, importance_path=GLOBAL_IMPORTANCE_PATH):
    shap_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_ids is not None:
        df = pl.read_parquet(schema.PROCESSED_PARQUET_PATH).filter(pl.col("asset_id").is_in(list(asset_ids)))
        rows = df.to_pandas()
    else:
        rows = _load_rows(split_names)
    shap_values, base_value, predictions, feature_names, _ = shap_explainer.compute_shap(rows)

    out = pd.DataFrame(shap_values, columns=[f"shap__{f}" for f in feature_names])
    out.insert(0, "asset_id", rows["asset_id"].to_numpy())
    out["base_value"] = base_value
    out["prediction"] = predictions
    out.to_parquet(shap_path, index=False)

    mean_abs = np.abs(shap_values).mean(axis=0)
    total = mean_abs.sum()
    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_abs_shap": mean_abs,
            "share": mean_abs / total if total > 0 else 0.0,
        }
    ).sort_values("mean_abs_shap", ascending=False, ignore_index=True)
    importance.to_parquet(importance_path, index=False)

    return {
        "n_rows": len(out),
        "shap_values_path": str(shap_path),
        "global_importance_path": str(importance_path),
    }


_CACHE_TABLE = None
_CACHE_TABLE_PATH = None


def _load_cache_table(shap_path=SHAP_VALUES_PATH):
    global _CACHE_TABLE, _CACHE_TABLE_PATH
    if _CACHE_TABLE is None or _CACHE_TABLE_PATH != shap_path:
        if not shap_path.exists():
            return None
        _CACHE_TABLE = pl.read_parquet(shap_path).to_pandas().set_index("asset_id")
        _CACHE_TABLE_PATH = shap_path
    return _CACHE_TABLE


def load_global_importance(importance_path=GLOBAL_IMPORTANCE_PATH):
    if not importance_path.exists():
        return None
    return pl.read_parquet(importance_path).to_pandas()


def get_cached_row(asset_id, shap_path=SHAP_VALUES_PATH):
    table = _load_cache_table(shap_path=shap_path)
    if table is None or asset_id not in table.index:
        return None
    record = table.loc[asset_id]
    feature_names = [c[len("shap__") :] for c in table.columns if c.startswith("shap__")]
    shap_row = record[[f"shap__{f}" for f in feature_names]].to_numpy(dtype="float64")
    return {
        "shap_row": shap_row,
        "feature_names": feature_names,
        "base_value": float(record["base_value"]),
        "prediction": float(record["prediction"]),
    }


if __name__ == "__main__":
    import os

    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    result = build_cache(split_names=None)
    print(result)
