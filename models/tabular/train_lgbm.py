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
LGBM_RESULT_PATH = TABULAR_DIR / "_lgbm_result.joblib"
RANDOM_SEED = 42


def metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)
    return {"mae": mae, "rmse": rmse, "mape": mape}


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

    result = {
        "params": params,
        "best_iteration": int(model.best_iteration_),
        "val_metrics": metrics(y_val, val_pred),
        "test_metrics": metrics(y_test, test_pred),
        "val_residuals": np.asarray(y_val - val_pred),
        "importance_shares": shares,
        "model_path": LGBM_MODEL_PATH.name,
        "categorical_levels": cat_levels,
    }
    joblib.dump(result, LGBM_RESULT_PATH)

    print("LightGBM top feature importance shares (gain):")
    for name, share in shares[:8]:
        print(f"  {name}: {share*100:.1f}%")
    if shares[0][1] > 0.9:
        print(f"WARNING: top feature explains {shares[0][1]*100:.1f}% of gain; possible residual leakage.")
    print("LightGBM test metrics:", result["test_metrics"])


if __name__ == "__main__":
    main()
