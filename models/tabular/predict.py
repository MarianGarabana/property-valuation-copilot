import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import joblib
import numpy as np
import pandas as pd

TABULAR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TABULAR_DIR))

import prep  # noqa: E402
from train import ARTIFACT_PATH, EXPERIMENT, MLRUNS_DIR, PRODUCTION_TAG  # noqa: E402

_BUNDLE = None


def _resolve_production_dir():
    import mlflow
    from mlflow.tracking import MlflowClient

    tracking_uri = f"file:{MLRUNS_DIR}"
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(EXPERIMENT)
    if experiment is None:
        raise FileNotFoundError(
            f"MLflow experiment '{EXPERIMENT}' not found in {MLRUNS_DIR}; run models/tabular/train.py first"
        )
    runs = client.search_runs(
        [experiment.experiment_id],
        filter_string=f"tags.{PRODUCTION_TAG} = 'true'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
    )
    if not runs:
        raise FileNotFoundError(
            "no MLflow run tagged as production; run models/tabular/train.py first"
        )
    run_id = runs[0].info.run_id
    local_dir = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path=ARTIFACT_PATH, tracking_uri=tracking_uri
    )
    return run_id, Path(local_dir)


def _load_bundle():
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE
    run_id, production_dir = _resolve_production_dir()
    meta = joblib.load(production_dir / "production_meta.joblib")
    meta["run_id"] = run_id
    model_file = production_dir / meta["model_path"]
    if meta["model_type"] == "lightgbm":
        import lightgbm as lgb

        meta["_booster"] = lgb.Booster(model_file=str(model_file))
        meta["_q05"] = lgb.Booster(model_file=str(production_dir / meta["q05_model_path"]))
        meta["_q95"] = lgb.Booster(model_file=str(production_dir / meta["q95_model_path"]))
    elif meta["model_type"] == "pytorch_mlp":
        raise NotImplementedError(
            "production model is pytorch_mlp; the LightGBM quantile band cannot share a process "
            "with torch on this platform (OpenMP conflict). Isolate the band before serving a "
            "torch point model."
        )
    else:
        raise ValueError(f"unknown model_type {meta['model_type']}")
    _BUNDLE = meta
    return _BUNDLE


def _to_frame(rows, meta):
    if isinstance(rows, pd.DataFrame):
        frame = rows.copy()
    elif isinstance(rows, dict):
        frame = pd.DataFrame([rows])
    else:
        frame = pd.DataFrame(list(rows))
    for col in meta["usable_features"]:
        if col not in frame.columns:
            frame[col] = np.nan
    return frame[meta["usable_features"]]


def _lgbm_frame(frame, meta):
    x = frame.copy()
    for col in meta["categorical_features"]:
        x[col] = pd.Categorical(x[col], categories=meta["categorical_levels"][col])
    for col in meta["numeric_features"]:
        x[col] = pd.to_numeric(x[col], errors="coerce")
    return x


def predict(rows):
    meta = _load_bundle()
    frame = _to_frame(rows, meta)
    x = _lgbm_frame(frame, meta)
    point = np.asarray(meta["_booster"].predict(x), dtype="float64")
    q05 = np.asarray(meta["_q05"].predict(x), dtype="float64")
    q95 = np.asarray(meta["_q95"].predict(x), dtype="float64")

    q = meta["calibration_q"]
    padded_low = q05 - q
    padded_high = q95 + q
    low = np.minimum(padded_low, padded_high)
    high = np.maximum(padded_low, padded_high)
    low = np.minimum(low, point)
    high = np.maximum(high, point)

    results = []
    for est, lo, hi in zip(point, low, high):
        results.append(
            {
                "estimate": float(est),
                "low": float(lo),
                "high": float(hi),
                "interval_coverage": meta["interval_coverage"],
                "interval_test_coverage": meta["interval_test_coverage"],
            }
        )
    return results


def predict_one(row):
    return predict([row])[0]


def model_info():
    meta = _load_bundle()
    return {
        "model_type": meta["model_type"],
        "run_id": meta["run_id"],
        "interval_method": meta["interval_method"],
        "interval_coverage": meta["interval_coverage"],
        "interval_test_coverage": meta["interval_test_coverage"],
        "calibration_q": meta["calibration_q"],
        "split_id": meta["split_id"],
        "test_metrics": meta["test_metrics"],
    }


if __name__ == "__main__":
    print(model_info())
