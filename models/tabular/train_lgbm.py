import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

TABULAR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TABULAR_DIR))

import prep  # noqa: E402

LGBM_MODEL_PATH = TABULAR_DIR / "production_lgbm.txt"
LGBM_Q05_PATH = TABULAR_DIR / "production_lgbm_q05.txt"
LGBM_Q95_PATH = TABULAR_DIR / "production_lgbm_q95.txt"
LGBM_RESULT_PATH = TABULAR_DIR / "_lgbm_result.joblib"
RANDOM_SEED = 42
Q_LOW_ALPHA = 0.05
Q_HIGH_ALPHA = 0.95


def metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)
    return {"mae": mae, "rmse": rmse, "mape": mape}


def pinball_loss(y_true, y_pred, alpha):
    diff = y_true - y_pred
    return float(np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff)))


def main():
    frames = prep.load_split_frames()
    cat_levels = prep.categorical_levels(frames["train"])
    x_train, y_train = prep.to_pandas_xy(frames["train"], cat_levels)
    x_val, y_val = prep.to_pandas_xy(frames["val"], cat_levels)
    x_test, y_test = prep.to_pandas_xy(frames["test"], cat_levels)

    params = {
        "objective": "regression",
        "n_estimators": 2000,
        "learning_rate": 0.03,
        "num_leaves": 63,
        "min_child_samples": 40,
        "subsample": 0.8,
        "subsample_freq": 1,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
        "verbose": -1,
    }
    model = lgb.LGBMRegressor(**params)
    model.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        eval_metric="l1",
        categorical_feature=prep.CATEGORICAL_FEATURES,
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
    )

    importance = model.booster_.feature_importance(importance_type="gain")
    total = importance.sum()
    shares = sorted(
        zip(model.booster_.feature_name(), (importance / total).tolist()),
        key=lambda kv: kv[1],
        reverse=True,
    )

    val_pred = model.predict(x_val)
    test_pred = model.predict(x_test)
    model.booster_.save_model(str(LGBM_MODEL_PATH))

    def train_quantile(alpha, save_path):
        q_params = dict(params)
        q_params["objective"] = "quantile"
        q_params["alpha"] = alpha
        q_model = lgb.LGBMRegressor(**q_params)
        q_model.fit(
            x_train,
            y_train,
            eval_set=[(x_val, y_val)],
            eval_metric="quantile",
            categorical_feature=prep.CATEGORICAL_FEATURES,
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
        )
        q_model.booster_.save_model(str(save_path))
        return q_model

    q_low = train_quantile(Q_LOW_ALPHA, LGBM_Q05_PATH)
    q_high = train_quantile(Q_HIGH_ALPHA, LGBM_Q95_PATH)
    q05_test = q_low.predict(x_test)
    q95_test = q_high.predict(x_test)

    raw_lo = np.minimum(q05_test, q95_test)
    raw_hi = np.maximum(q05_test, q95_test)
    pure_coverage = float(np.mean((y_test >= raw_lo) & (y_test <= raw_hi)))
    raw_lo_e = np.minimum(raw_lo, test_pred)
    raw_hi_e = np.maximum(raw_hi, test_pred)
    raw_coverage = float(np.mean((y_test >= raw_lo_e) & (y_test <= raw_hi_e)))
    raw_width = float(np.mean(raw_hi_e - raw_lo_e))

    q05_val = q_low.predict(x_val)
    q95_val = q_high.predict(x_val)
    scores = np.maximum(q05_val - y_val, y_val - q95_val)
    n_cal = len(scores)
    k = min(int(np.ceil((n_cal + 1) * (Q_HIGH_ALPHA - Q_LOW_ALPHA))), n_cal)
    calibration_q = float(np.sort(scores)[k - 1])

    low = q05_test - calibration_q
    high = q95_test + calibration_q
    crossing = low > high
    lo = np.minimum(low, high)
    hi = np.maximum(low, high)
    point_excluded = (test_pred < lo) | (test_pred > hi)
    corrected = crossing | point_excluded
    lo = np.minimum(lo, test_pred)
    hi = np.maximum(hi, test_pred)
    cal_coverage = float(np.mean((y_test >= lo) & (y_test <= hi)))
    cal_width = float(np.mean(hi - lo))

    quantile = {
        "q_low_alpha": Q_LOW_ALPHA,
        "q_high_alpha": Q_HIGH_ALPHA,
        "q05_model_path": LGBM_Q05_PATH.name,
        "q95_model_path": LGBM_Q95_PATH.name,
        "q05_best_iteration": int(q_low.best_iteration_),
        "q95_best_iteration": int(q_high.best_iteration_),
        "calibration_q": calibration_q,
        "calibration_rows": int(n_cal),
        "test_interval_coverage": cal_coverage,
        "test_mean_interval_width": cal_width,
        "test_raw_quantile_coverage": raw_coverage,
        "test_pure_quantile_coverage": pure_coverage,
        "test_raw_mean_interval_width": raw_width,
        "test_pinball_low": pinball_loss(y_test, q05_test, Q_LOW_ALPHA),
        "test_pinball_high": pinball_loss(y_test, q95_test, Q_HIGH_ALPHA),
        "test_rows": int(len(y_test)),
        "n_crossing": int(crossing.sum()),
        "n_point_excluded": int(point_excluded.sum()),
        "n_corrected": int(corrected.sum()),
    }

    result = {
        "params": params,
        "best_iteration": int(model.best_iteration_),
        "val_metrics": metrics(y_val, val_pred),
        "test_metrics": metrics(y_test, test_pred),
        "val_residuals": np.asarray(y_val - val_pred),
        "importance_shares": shares,
        "model_path": LGBM_MODEL_PATH.name,
        "categorical_levels": cat_levels,
        "quantile": quantile,
    }
    joblib.dump(result, LGBM_RESULT_PATH)

    print("LightGBM top feature importance shares (gain):")
    for name, share in shares[:8]:
        print(f"  {name}: {share*100:.1f}%")
    if shares[0][1] > 0.9:
        print(f"WARNING: top feature explains {shares[0][1]*100:.1f}% of gain; possible residual leakage.")
    print("LightGBM test metrics:", result["test_metrics"])
    print(
        f"Raw quantile band test coverage: pure [q05,q95] {pure_coverage:.4f}, "
        f"delivered {raw_coverage:.4f}, mean width {raw_width:,.0f}"
    )
    print(
        f"CQR calibration Q={calibration_q:,.0f} on {n_cal} validation rows -> "
        f"test coverage {cal_coverage:.4f} (vs raw {raw_coverage:.4f}, old additive 0.8992), "
        f"mean width {cal_width:,.0f} (vs raw {raw_width:,.0f})"
    )
    print(
        f"Ordering corrections on {len(y_test)} test rows (calibrated band): "
        f"crossing={int(crossing.sum())}, point_excluded={int(point_excluded.sum())}, "
        f"total={int(corrected.sum())}"
    )


if __name__ == "__main__":
    main()
