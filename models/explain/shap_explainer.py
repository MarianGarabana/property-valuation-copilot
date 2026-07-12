import io
import sys
import threading
from pathlib import Path

EXPLAIN_DIR = Path(__file__).resolve().parent
TABULAR_DIR = EXPLAIN_DIR.parents[0] / "tabular"
for p in (str(TABULAR_DIR), str(EXPLAIN_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

import predict as tabular_predict
from labels import describe_feature

_PLOT_LOCK = threading.Lock()

_EXPLAINER = None
_EXPLAINER_RUN_ID = None


def _get_meta():
    return tabular_predict._load_bundle()


def _get_explainer():
    global _EXPLAINER, _EXPLAINER_RUN_ID
    meta = _get_meta()
    if meta["model_type"] != "lightgbm":
        raise NotImplementedError(
            f"SHAP TreeExplainer only supports the lightgbm production model; "
            f"current production model_type is '{meta['model_type']}'"
        )
    if _EXPLAINER is None or _EXPLAINER_RUN_ID != meta["run_id"]:
        _EXPLAINER = shap.TreeExplainer(meta["_booster"])
        _EXPLAINER_RUN_ID = meta["run_id"]
    return _EXPLAINER, meta


def _prepare_frame(rows, meta):
    frame = tabular_predict._to_frame(rows, meta)
    x = frame.copy()
    for col in meta["categorical_features"]:
        x[col] = pd.Categorical(x[col], categories=meta["categorical_levels"][col])
    for col in meta["numeric_features"]:
        x[col] = pd.to_numeric(x[col], errors="coerce")
    return x


def compute_shap(rows):
    explainer, meta = _get_explainer()
    x = _prepare_frame(rows, meta)
    shap_values = np.asarray(explainer.shap_values(x), dtype="float64")
    base_value = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    predictions = np.asarray(meta["_booster"].predict(x), dtype="float64")
    return shap_values, base_value, predictions, meta["usable_features"], x


def top_drivers_from_shap(shap_row, feature_names, raw_row, top_n=5, neighborhood_name=None):
    order = np.argsort(-np.abs(shap_row))[:top_n]
    drivers = []
    for idx in order:
        name = feature_names[idx]
        value = raw_row.get(name)
        drivers.append(
            {
                "feature": name,
                "value": value,
                "shap_eur": float(shap_row[idx]),
                "description": describe_feature(name, value, neighborhood_name=neighborhood_name),
            }
        )
    return drivers


def build_driver_text(estimate, top_drivers):
    clauses = []
    for d in top_drivers:
        verb = "adds" if d["shap_eur"] >= 0 else "subtracts"
        clauses.append(f"{d['description']} {verb} {abs(d['shap_eur']):,.0f} euros")
    body = ", ".join(clauses)
    if body:
        body = body[0].upper() + body[1:]
    return f"Estimated value is {estimate:,.0f} euros. {body}."


def render_waterfall_png(shap_row, base_value, feature_names, raw_row, top_n=10):
    explanation = shap.Explanation(
        values=shap_row,
        base_values=base_value,
        data=np.array([raw_row.get(name) for name in feature_names]),
        feature_names=feature_names,
    )
    with _PLOT_LOCK:
        fig = plt.figure()
        shap.plots.waterfall(explanation, max_display=top_n, show=False)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
