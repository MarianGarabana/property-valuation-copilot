import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

TABULAR_DIR = Path(__file__).resolve().parent
ETL_DIR = TABULAR_DIR.parents[1] / "etl"
sys.path.insert(0, str(ETL_DIR))

import schema  # noqa: E402
from split import load_split  # noqa: E402

PLACEHOLDER_NULL_FEATURES = ["cnn_condition_score"]
USABLE_FEATURES = [f for f in schema.MODEL_FEATURE_NAMES if f not in PLACEHOLDER_NULL_FEATURES]
CATEGORICAL_FEATURES = ["property_type", "condition", "neighborhood_id"]
NUMERIC_FEATURES = [f for f in USABLE_FEATURES if f not in CATEGORICAL_FEATURES]
YEAR_MISSING_SOURCE = "construction_year"


def load_split_frames():
    df = pl.read_parquet(schema.PROCESSED_PARQUET_PATH)
    assignment = load_split()
    df = df.join(assignment, on="asset_id", how="inner")
    frames = {}
    for name in ("train", "val", "test"):
        frames[name] = df.filter(pl.col("split") == name)
    return frames


def categorical_levels(frame: pl.DataFrame):
    levels = {}
    for col in CATEGORICAL_FEATURES:
        values = frame[col].drop_nulls().unique().to_list()
        levels[col] = sorted(values)
    return levels


def to_pandas_xy(frame: pl.DataFrame, categories=None):
    pdf = frame.select(USABLE_FEATURES + [schema.TARGET]).to_pandas()
    x = pdf[USABLE_FEATURES].copy()
    for col in CATEGORICAL_FEATURES:
        if categories is not None:
            x[col] = pd.Categorical(x[col].astype("object"), categories=categories[col])
        else:
            x[col] = x[col].astype("category")
    y = pdf[schema.TARGET].to_numpy()
    return x, y


def fit_nn_preprocessor(x_train):
    numeric = x_train[NUMERIC_FEATURES].apply(lambda c: c.astype("float64"))
    medians = numeric.median()
    imputed = numeric.fillna(medians)
    means = imputed.mean()
    stds = imputed.std(ddof=0).replace(0.0, 1.0)
    categories = {col: sorted(x_train[col].dropna().unique().tolist()) for col in CATEGORICAL_FEATURES}
    return {
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "medians": medians.to_dict(),
        "means": means.to_dict(),
        "stds": stds.to_dict(),
        "categories": categories,
        "year_missing_source": YEAR_MISSING_SOURCE,
    }


def transform_nn(x, preproc):
    numeric = x[preproc["numeric_features"]].apply(lambda c: c.astype("float64"))
    year_missing = numeric[preproc["year_missing_source"]].isna().astype("float64").to_numpy()
    medians = np.array([preproc["medians"][c] for c in preproc["numeric_features"]])
    means = np.array([preproc["means"][c] for c in preproc["numeric_features"]])
    stds = np.array([preproc["stds"][c] for c in preproc["numeric_features"]])
    values = numeric.to_numpy()
    values = np.where(np.isnan(values), medians, values)
    values = (values - means) / stds

    onehot_blocks = [values, year_missing.reshape(-1, 1)]
    for col in preproc["categorical_features"]:
        cats = preproc["categories"][col]
        col_values = x[col].astype("object").to_numpy()
        block = np.zeros((len(x), len(cats) + 1), dtype="float64")
        matched = np.zeros(len(x), dtype=bool)
        for j, cat in enumerate(cats):
            hit = col_values == cat
            block[:, j] = hit.astype("float64")
            matched |= hit
        block[:, len(cats)] = (~matched).astype("float64")
        onehot_blocks.append(block)
    return np.concatenate(onehot_blocks, axis=1).astype("float32")


def nn_input_dim(preproc):
    dim = len(preproc["numeric_features"]) + 1
    for col in preproc["categorical_features"]:
        dim += len(preproc["categories"][col]) + 1
    return dim
