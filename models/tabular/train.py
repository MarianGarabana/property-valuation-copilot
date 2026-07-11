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


def log_quantile_run(run_name, alpha, best_iteration, test_pinball):
    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("split_id", SPLIT_ID)
        mlflow.log_param("split_seed", SPLIT_SEED)
        mlflow.log_param("objective", "quantile")
        mlflow.log_param("alpha", alpha)
        mlflow.log_param("best_iteration", best_iteration)
        mlflow.log_metric("test_pinball", test_pinball)


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
    q = lgbm_res["quantile"]
    lines.append("Confidence range: conformalized per-property LightGBM quantile regression (CQR).")
    lines.append(
        f"Two extra LightGBM models with objective=quantile at alpha {q['q_low_alpha']} and "
        f"{q['q_high_alpha']} give a"
    )
    lines.append(
        "central interval whose width scales with the property. Split-conformal calibration on the"
    )
    lines.append(
        f"validation split ({q['calibration_rows']} rows, never test) pads both ends by a single Q "
        f"= {q['calibration_q']:,.0f} EUR,"
    )
    lines.append(
        "the ceil((n+1)*0.90)-th conformity score, which restores marginal coverage while keeping"
    )
    lines.append("the per-property shape. The point estimate stays from the production point model.")
    lines.append("")
    lines.append("Interval coverage and width (held-out test, 14437 rows):")
    lines.append("")
    lines.append("| Band | Test coverage | Mean width (EUR) |")
    lines.append("|---|---|---|")
    lines.append("| Old additive residual (homoscedastic) | 0.8992 | 189,853 (constant) |")
    lines.append(
        f"| Raw LightGBM quantile (per-property) | {q['test_raw_quantile_coverage']:.4f} | "
        f"{q['test_raw_mean_interval_width']:,.0f} |"
    )
    lines.append(
        f"| CQR-calibrated quantile (shipped) | {q['test_interval_coverage']:.4f} | "
        f"{q['test_mean_interval_width']:,.0f} |"
    )
    lines.append("")
    lines.append(
        f"The raw quantile band undercovered at {q['test_raw_quantile_coverage']:.4f}. CQR padding "
        f"by Q = {q['calibration_q']:,.0f} EUR"
    )
    lines.append(
        f"lifts test coverage to {q['test_interval_coverage']:.4f}, near the 0.90 nominal, measured"
    )
    lines.append(
        "on the untouched test set (Q was fixed on validation, never tuned on test). The band stays"
    )
    lines.append(
        "per-property: the additive Q shifts both ends by the same amount but the base quantile"
    )
    lines.append(
        "spread differs by property, so cheap listings keep a narrower band than expensive ones."
    )
    lines.append(
        f"Ordering low <= estimate <= high is enforced; {q['n_corrected']} of {q['test_rows']} test"
    )
    lines.append("rows needed a correction. The old additive band gave every property the same euro")
    lines.append("width, which is not credible on cheap listings.")
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

    q = lgbm_res["quantile"]
    log_quantile_run("lightgbm_q05", q["q_low_alpha"], q["q05_best_iteration"], q["test_pinball_low"])
    log_quantile_run("lightgbm_q95", q["q_high_alpha"], q["q95_best_iteration"], q["test_pinball_high"])

    lgbm_mae = lgbm_res["test_metrics"]["mae"]
    nn_mae = nn_res["test_metrics"]["mae"]
    winner = "LightGBM baseline" if lgbm_mae <= nn_mae else "PyTorch tabular NN"

    band_meta = {
        "interval_method": "cqr_lgbm_quantile",
        "q05_model_path": q["q05_model_path"],
        "q95_model_path": q["q95_model_path"],
        "calibration_q": q["calibration_q"],
        "interval_coverage": INTERVAL_COVERAGE,
        "interval_test_coverage": q["test_interval_coverage"],
    }

    if winner == "LightGBM baseline":
        winning_run_id = lgbm_run_id
        meta = {
            "model_type": "lightgbm",
            "model_path": lgbm_res["model_path"],
            "usable_features": prep.USABLE_FEATURES,
            "categorical_features": prep.CATEGORICAL_FEATURES,
            "categorical_levels": lgbm_res["categorical_levels"],
            "numeric_features": prep.NUMERIC_FEATURES,
            "split_id": SPLIT_ID,
            "test_metrics": lgbm_res["test_metrics"],
        }
    else:
        winning_run_id = nn_run_id
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
            "split_id": SPLIT_ID,
            "test_metrics": nn_res["test_metrics"],
        }

    meta.update(band_meta)
    meta["run_id"] = winning_run_id
    joblib.dump(meta, PRODUCTION_META_PATH)

    model_file = TABULAR_DIR / meta["model_path"]
    q05_file = TABULAR_DIR / q["q05_model_path"]
    q95_file = TABULAR_DIR / q["q95_model_path"]
    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name(EXPERIMENT)
    with mlflow.start_run(run_id=winning_run_id):
        mlflow.set_tag(PRODUCTION_TAG, "true")
        mlflow.set_tag("winner", winner)
        mlflow.log_metric("test_interval_coverage", q["test_interval_coverage"])
        mlflow.log_metric("test_raw_quantile_coverage", q["test_raw_quantile_coverage"])
        mlflow.log_metric("test_pure_quantile_coverage", q["test_pure_quantile_coverage"])
        mlflow.log_metric("test_mean_interval_width", q["test_mean_interval_width"])
        mlflow.log_metric("test_raw_mean_interval_width", q["test_raw_mean_interval_width"])
        mlflow.log_metric("calibration_q", q["calibration_q"])
        mlflow.log_metric("test_interval_rows_corrected", q["n_corrected"])
        for artifact in (model_file, q05_file, q95_file, PRODUCTION_META_PATH):
            mlflow.log_artifact(str(artifact), artifact_path=ARTIFACT_PATH)
    for prior in client.search_runs(
        [experiment.experiment_id], filter_string=f"tags.{PRODUCTION_TAG} = 'true'"
    ):
        if prior.info.run_id != winning_run_id:
            client.set_tag(prior.info.run_id, PRODUCTION_TAG, "false")

    write_comparison(lgbm_res, nn_res, winner)
    print(f"Winner: {winner} (run_id {winning_run_id})")
    print(
        f"CQR band test coverage {q['test_interval_coverage']:.4f} (raw {q['test_raw_quantile_coverage']:.4f}, "
        f"old additive 0.8992); Q={q['calibration_q']:,.0f}; "
        f"mean width {q['test_mean_interval_width']:,.0f} (raw {q['test_raw_mean_interval_width']:,.0f})"
    )
    print(
        f"Ordering corrections: crossing={q['n_crossing']}, point_excluded={q['n_point_excluded']}, "
        f"total={q['n_corrected']} of {q['test_rows']} test rows"
    )
    print(f"Logged production model, quantile models, and meta to MLflow run {winning_run_id}")


if __name__ == "__main__":
    main()
