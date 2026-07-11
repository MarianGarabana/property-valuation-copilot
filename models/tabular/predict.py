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
    elif meta["model_type"] == "pytorch_mlp":
        import torch

        from nn_model import TabularMLP

        model = TabularMLP(meta["input_dim"])
        model.load_state_dict(torch.load(model_file))
        model.eval()
        meta["_torch_model"] = model
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


def _point_estimate(frame, meta):
    if meta["model_type"] == "lightgbm":
        x = frame.copy()
        for col in meta["categorical_features"]:
            x[col] = pd.Categorical(x[col], categories=meta["categorical_levels"][col])
        for col in meta["numeric_features"]:
            x[col] = pd.to_numeric(x[col], errors="coerce")
        return np.asarray(meta["_booster"].predict(x), dtype="float64")
    import torch

    x = prep.transform_nn(frame, meta["preproc"])
    with torch.no_grad():
        z = meta["_torch_model"](torch.tensor(x, dtype=torch.float32)).cpu().numpy()
    return np.exp(z * meta["target_std"] + meta["target_mean"]).astype("float64")


def predict(rows):
    meta = _load_bundle()
    frame = _to_frame(rows, meta)
    point = _point_estimate(frame, meta)
    low = point + meta["interval_low"]
    high = point + meta["interval_high"]
    results = []
    for est, lo, hi in zip(point, low, high):
        results.append(
            {
                "estimate": float(est),
                "low": float(lo),
                "high": float(hi),
                "interval_coverage": meta["interval_coverage"],
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
        "interval_coverage": meta["interval_coverage"],
        "interval_low": meta["interval_low"],
        "interval_high": meta["interval_high"],
        "split_id": meta["split_id"],
        "test_metrics": meta["test_metrics"],
    }


if __name__ == "__main__":
    print(model_info())
