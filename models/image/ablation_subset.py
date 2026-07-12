import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.preprocessing import StandardScaler

IMAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = IMAGE_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT / "models" / "tabular"))
sys.path.insert(0, str(IMAGE_DIR))

import prep  # noqa: E402
from tiles import SUBSET_MANIFEST_PATH, TILE_ASSIGNMENT_PATH  # noqa: E402

FEATURES_PATH = IMAGE_DIR / "features_subset.npz"
SEED = 42
N_FOLDS = 5
PROBE_C = 0.1
STOP_FRACTION = 0.1


def probe_scores() -> pl.DataFrame:
    cached = np.load(FEATURES_PATH, allow_pickle=False)
    feats, ids = cached["features"], [str(t) for t in cached["tile_ids"]]
    row_of = {t: i for i, t in enumerate(ids)}
    manifest = pl.read_parquet(SUBSET_MANIFEST_PATH).filter(pl.col("tile_id").is_in(ids))
    manifest = manifest.with_columns(pl.col("tile_id").replace_strict(row_of).alias("row"))

    train = manifest.filter(pl.col("role") == "train")
    ev = manifest.filter(pl.col("role") == "eval")
    x_all = feats[train["row"].to_numpy()]
    y_all = train["tile_label"].to_numpy()

    rng = np.random.default_rng(SEED)
    fold = rng.integers(0, N_FOLDS, size=len(y_all))
    oof = np.full(len(y_all), np.nan)
    for k in range(N_FOLDS):
        mask = fold == k
        scaler = StandardScaler().fit(x_all[~mask])
        clf = LogisticRegression(max_iter=3000, C=PROBE_C, class_weight="balanced", random_state=SEED)
        clf.fit(scaler.transform(x_all[~mask]), y_all[~mask])
        oof[mask] = clf.predict_proba(scaler.transform(x_all[mask]))[:, 1]
    assert not np.isnan(oof).any()
    print(f"train-tile OOF AUC: {roc_auc_score(y_all, oof):.4f} (chance 0.5, {N_FOLDS}-fold by tile)")

    scaler = StandardScaler().fit(x_all)
    clf = LogisticRegression(max_iter=3000, C=PROBE_C, class_weight="balanced", random_state=SEED)
    clf.fit(scaler.transform(x_all), y_all)
    p_eval = clf.predict_proba(scaler.transform(feats[ev["row"].to_numpy()]))[:, 1].astype(np.float64)

    return pl.concat(
        [
            train.select("tile_id").with_columns(cnn_condition_score=pl.Series(oof), role=pl.lit("train")),
            ev.select("tile_id").with_columns(cnn_condition_score=pl.Series(p_eval), role=pl.lit("eval")),
        ]
    )


def metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)
    return {"mae": mae, "rmse": rmse, "mape": mape}


def fit_and_eval(frames, cat_levels, with_score: bool):
    def make_xy(frame):
        x, y = prep.to_pandas_xy(frame, cat_levels)
        if with_score:
            x = x.copy()
            score = frame["cnn_condition_score"].to_numpy()
            assert not np.isnan(score).any()
            x["cnn_condition_score"] = score
        return x, y

    x_fit, y_fit = make_xy(frames["fit"])
    x_stop, y_stop = make_xy(frames["stop"])
    x_eval, y_eval = make_xy(frames["eval"])

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
        "random_state": SEED,
        "n_jobs": -1,
        "verbose": -1,
    }
    model = lgb.LGBMRegressor(**params)
    model.fit(
        x_fit,
        y_fit,
        eval_set=[(x_stop, y_stop)],
        eval_metric="l1",
        categorical_feature=prep.CATEGORICAL_FEATURES,
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
    )
    importance = model.booster_.feature_importance(importance_type="gain")
    shares = dict(zip(model.booster_.feature_name(), importance / importance.sum()))
    return metrics(y_eval, model.predict(x_eval)), model.best_iteration_, shares


def main():
    scores = probe_scores()
    assignment = pl.read_parquet(TILE_ASSIGNMENT_PATH).drop("condition", "label")
    listings = pl.read_parquet(prep.schema.PROCESSED_PARQUET_PATH).drop("cnn_condition_score").join(
        assignment.select("asset_id", "tile_id", "split"), on="asset_id", how="inner"
    )
    df = listings.join(scores, on="tile_id", how="inner")

    train_df = df.filter((pl.col("split") == "train") & (pl.col("role") == "train"))
    eval_df = df.filter((pl.col("split") == "val") & (pl.col("role") == "eval"))

    tile_ids = train_df["tile_id"].unique().sort()
    rng = np.random.default_rng(SEED)
    stop_tiles = set(
        np.array(tile_ids.to_list())[rng.random(len(tile_ids)) < STOP_FRACTION].tolist()
    )
    fit_df = train_df.filter(~pl.col("tile_id").is_in(stop_tiles))
    stop_df = train_df.filter(pl.col("tile_id").is_in(stop_tiles))

    frames = {"fit": fit_df, "stop": stop_df, "eval": eval_df}
    print(f"fit listings: {fit_df.height}  stop listings: {stop_df.height}  eval listings: {eval_df.height}")
    cat_levels = prep.categorical_levels(fit_df)

    results = {}
    for label, with_score in (("without_cnn", False), ("with_cnn", True)):
        m, best_iter, shares = fit_and_eval(frames, cat_levels, with_score)
        results[label] = m
        cnn_share = shares.get("cnn_condition_score", 0.0)
        print(
            f"{label}: MAE {m['mae']:,.0f}  RMSE {m['rmse']:,.0f}  MAPE {m['mape']:.2f}%  "
            f"best_iter {best_iter}  cnn_gain_share {cnn_share*100:.2f}%"
        )

    for key in ("mae", "rmse", "mape"):
        base, with_ = results["without_cnn"][key], results["with_cnn"][key]
        print(f"delta {key}: {with_ - base:+,.4f} ({(with_ - base) / base * 100:+.3f}%)")


if __name__ == "__main__":
    main()
