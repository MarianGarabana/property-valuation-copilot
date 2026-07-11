import sys
from pathlib import Path

EXPLAIN_DIR = Path(__file__).resolve().parent
TABULAR_DIR = EXPLAIN_DIR.parents[0] / "tabular"
for p in (str(TABULAR_DIR), str(EXPLAIN_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import predict as tabular_predict
import cache
import shap_explainer


def explain(row, top_n=5, plot_top_n=10, use_cache=True):
    if isinstance(row, dict):
        raw_row = row
    else:
        raw_row = dict(row)

    asset_id = raw_row.get("asset_id")
    cached = cache.get_cached_row(asset_id) if (use_cache and asset_id is not None) else None

    if cached is not None:
        shap_row = cached["shap_row"]
        feature_names = cached["feature_names"]
        base_value = cached["base_value"]
        estimate = cached["prediction"]
        from_cache = True
    else:
        shap_values, base_value, predictions, feature_names, _ = shap_explainer.compute_shap(
            [raw_row]
        )
        shap_row = shap_values[0]
        estimate = float(predictions[0])
        from_cache = False

    interval = tabular_predict.predict_one(raw_row)
    neighborhood_name = raw_row.get("neighborhood_name")
    drivers = shap_explainer.top_drivers_from_shap(
        shap_row, feature_names, raw_row, top_n=top_n, neighborhood_name=neighborhood_name
    )
    driver_text = shap_explainer.build_driver_text(estimate, drivers)
    plot_png = shap_explainer.render_waterfall_png(
        shap_row, base_value, feature_names, raw_row, top_n=plot_top_n
    )

    return {
        "estimate": estimate,
        "low": interval["low"],
        "high": interval["high"],
        "interval_coverage": interval["interval_coverage"],
        "base_value": base_value,
        "shap_values": dict(zip(feature_names, shap_row.tolist())),
        "top_drivers": drivers,
        "driver_text": driver_text,
        "plot": plot_png,
        "from_cache": from_cache,
    }
