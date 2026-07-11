import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

import joblib
import mlflow
import numpy as np

TABULAR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TABULAR_DIR))

import prep  # noqa: E402
from split import SPLIT_ID, SPLIT_PATH, SPLIT_SEED  # noqa: E402

REPO_ROOT = TABULAR_DIR.parents[1]
MLRUNS_DIR = REPO_ROOT / "mlruns"
EXPERIMENT = "phase2_tabular"
PRODUCTION_META_PATH = TABULAR_DIR / "production_meta.joblib"
LGBM_RESULT_PATH = TABULAR_DIR / "_lgbm_result.joblib"
NN_RESULT_PATH = TABULAR_DIR / "_nn_result.joblib"
COMPARISON_PATH = TABULAR_DIR / "comparison.md"
INTERVAL_COVERAGE = 0.90
SPLIT_SIZES = {"train": 46198, "val": 11550, "test": 14437}


def run_worker(script_name):
    print(f"running worker {script_name} in isolated process")
    result = subprocess.run(
        [sys.executable, "-u", str(TABULAR_DIR / script_name)],
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"worker {script_name} exited with code {result.returncode}")


def residual_interval(residuals):
    low = float(np.quantile(residuals, (1.0 - INTERVAL_COVERAGE) / 2.0))
    high = float(np.quantile(residuals, 1.0 - (1.0 - INTERVAL_COVERAGE) / 2.0))
    return low, high


PRODUCTION_TAG = "is_production"
ARTIFACT_PATH = "production"


def log_run(run_name, params, val_metrics, test_metrics, extra):
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("split_id", SPLIT_ID)
        mlflow.log_param("split_seed", SPLIT_SEED)
        mlflow.log_param("split_path", str(SPLIT_PATH))
        mlflow.log_param("n_usable_features", len(prep.USABLE_FEATURES))
        mlflow.log_param("dropped_null_placeholders", ",".join(prep.PLACEHOLDER_NULL_FEATURES))
        for k, v in params.items():
            mlflow.log_param(k, v)
        for k, v in extra.items():
            mlflow.log_param(k, v)
        for split_name, m in (("val", val_metrics), ("test", test_metrics)):
            for metric_name, value in m.items():
                mlflow.log_metric(f"{split_name}_{metric_name}", value)
        return run.info.run_id


def write_comparison(lgbm_res, nn_res, winner):
    lm = lgbm_res["test_metrics"]
    nm = nn_res["test_metrics"]
    lines = []
    lines.append("# Phase 2 tabular model comparison")
    lines.append("")
    lines.append("Data: idealista18 2018 Madrid asking prices (historical prototype).")
    lines.append(
        f"Split: {SPLIT_ID} (seed {SPLIT_SEED}). "
        f"Train {SPLIT_SIZES['train']} / val {SPLIT_SIZES['val']} / test {SPLIT_SIZES['test']}."
    )
    lines.append("Metrics below are on the held-out test split only.")
    lines.append("")
    lines.append("| Model | MAE (EUR) | RMSE (EUR) | MAPE (%) |")
    lines.append("|---|---|---|---|")
    lines.append(f"| LightGBM baseline | {lm['mae']:,.0f} | {lm['rmse']:,.0f} | {lm['mape']:.2f} |")
    lines.append(f"| PyTorch tabular NN | {nm['mae']:,.0f} | {nm['rmse']:,.0f} | {nm['mape']:.2f} |")
    lines.append("")
    lines.append(f"Winner (lowest test MAE): {winner}. Saved as the production artifact.")
    lines.append("")
    lines.append("Confidence range: residual-based. The interval is the point estimate plus the")
    lines.append(
        f"empirical {int(INTERVAL_COVERAGE * 100)}% quantile band of the winning model's "
        "validation-set"
    )
    lines.append("residuals (y_true minus y_pred), so the band reflects real out-of-sample error")
    lines.append("rather than a model-reported variance.")
    lines.append("")
    lines.append("Top LightGBM feature importances (gain share):")
    for name, share in lgbm_res["importance_shares"][:8]:
        lines.append(f"- {name}: {share * 100:.1f}%")
    COMPARISON_PATH.write_text("\n".join(lines) + "\n")


def main():
    MLRUNS_DIR.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(f"file:{MLRUNS_DIR}")
    mlflow.set_experiment(EXPERIMENT)

    run_worker("train_lgbm.py")
    run_worker("train_nn.py")

    lgbm_res = joblib.load(LGBM_RESULT_PATH)
    nn_res = joblib.load(NN_RESULT_PATH)

    print("LightGBM test metrics:", lgbm_res["test_metrics"])
    print("NN test metrics:", nn_res["test_metrics"])
    top_share = lgbm_res["importance_shares"][0][1]
    if top_share > 0.9:
        print(f"WARNING: top LightGBM feature explains {top_share*100:.1f}% of gain; possible leakage.")

    lgbm_run_id = log_run(
        "lightgbm_baseline",
        lgbm_res["params"],
        lgbm_res["val_metrics"],
        lgbm_res["test_metrics"],
        {"best_iteration": lgbm_res["best_iteration"]},
    )
    nn_run_id = log_run(
        "pytorch_tabular_nn",
        nn_res["params"],
        nn_res["val_metrics"],
        nn_res["test_metrics"],
        {"best_epoch": nn_res["best_epoch"]},
    )

    lgbm_mae = lgbm_res["test_metrics"]["mae"]
    nn_mae = nn_res["test_metrics"]["mae"]
    winner = "LightGBM baseline" if lgbm_mae <= nn_mae else "PyTorch tabular NN"

    if winner == "LightGBM baseline":
        winning_run_id = lgbm_run_id
        low, high = residual_interval(lgbm_res["val_residuals"])
        meta = {
            "model_type": "lightgbm",
            "model_path": lgbm_res["model_path"],
            "usable_features": prep.USABLE_FEATURES,
            "categorical_features": prep.CATEGORICAL_FEATURES,
            "categorical_levels": lgbm_res["categorical_levels"],
            "numeric_features": prep.NUMERIC_FEATURES,
            "interval_low": low,
            "interval_high": high,
            "interval_coverage": INTERVAL_COVERAGE,
            "split_id": SPLIT_ID,
            "test_metrics": lgbm_res["test_metrics"],
        }
    else:
        winning_run_id = nn_run_id
        low, high = residual_interval(nn_res["val_residuals"])
        meta = {
            "model_type": "pytorch_mlp",
            "model_path": nn_res["model_path"],
            "usable_features": prep.USABLE_FEATURES,
            "categorical_features": prep.CATEGORICAL_FEATURES,
            "categorical_levels": lgbm_res["categorical_levels"],
            "numeric_features": prep.NUMERIC_FEATURES,
            "preproc": nn_res["preproc"],
            "target_mean": nn_res["target_mean"],
            "target_std": nn_res["target_std"],
            "input_dim": nn_res["input_dim"],
            "interval_low": low,
            "interval_high": high,
            "interval_coverage": INTERVAL_COVERAGE,
            "split_id": SPLIT_ID,
            "test_metrics": nn_res["test_metrics"],
        }

    meta["run_id"] = winning_run_id
    joblib.dump(meta, PRODUCTION_META_PATH)

    model_file = TABULAR_DIR / meta["model_path"]
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT)
    for prior in client.search_runs(
        [experiment.experiment_id], filter_string=f"tags.{PRODUCTION_TAG} = 'true'"
    ):
        if prior.info.run_id != winning_run_id:
            client.set_tag(prior.info.run_id, PRODUCTION_TAG, "false")
    with mlflow.start_run(run_id=winning_run_id):
        mlflow.set_tag(PRODUCTION_TAG, "true")
        mlflow.set_tag("winner", winner)
        mlflow.log_artifact(str(model_file), artifact_path=ARTIFACT_PATH)
        mlflow.log_artifact(str(PRODUCTION_META_PATH), artifact_path=ARTIFACT_PATH)

    write_comparison(lgbm_res, nn_res, winner)
    print(f"Winner: {winner} (run_id {winning_run_id})")
    print(f"Interval ({int(INTERVAL_COVERAGE*100)}%): [{low:,.0f}, {high:,.0f}] EUR around point estimate")
    print(f"Logged production model + meta to MLflow run {winning_run_id} under '{ARTIFACT_PATH}/'")


if __name__ == "__main__":
    main()
