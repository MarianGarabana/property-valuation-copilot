"""Input-distribution drift check for the Madrid valuation model.

Honest framing (read before trusting any number here). The training data is
idealista18: 2018 Madrid asking prices, a static historical snapshot. There is
no live feed of closed sale prices, so label drift (the target distribution
shifting over time) cannot be measured at all. The only drift signal that is
observable in this prototype is input drift: whether the properties a user
queries or enters differ in their numeric-feature distribution from the 2018
training population. That is what this module measures, and nothing more. A
"no drift" result does not mean the model is accurate today; it means the
queried properties look like the ones the model was trained on.

Method: for each continuous numeric input feature, Population Stability Index
(PSI) with reference-quantile bins plus a two-sample Kolmogorov-Smirnov test.
A feature is flagged drifted when PSI > 0.2 (the standard moderate-shift
threshold). Reference = the train split of the committed processed parquet;
current = whatever batch of properties the caller passes in.
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
from scipy.stats import ks_2samp

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from etl import schema  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "models" / "tabular"))
from split import load_split  # noqa: E402

PSI_FLAG_THRESHOLD = 0.2
PSI_BINS = 10


def numeric_reference_features(df: pl.DataFrame) -> list[str]:
    """Continuous numeric model inputs suitable for a distribution comparison.

    Excludes the categorical neighborhood_id, identifiers, target, leakage
    columns, and any all-null column (cnn_condition_score).
    """
    numeric = []
    for feature in schema.FEATURES:
        if feature.name not in schema.MODEL_FEATURE_NAMES:
            continue
        if feature.name == "neighborhood_id":
            continue
        if feature.dtype not in ("int", "float"):
            continue
        col = df[feature.name]
        if col.null_count() == df.height:
            continue
        numeric.append(feature.name)
    return numeric


def load_reference() -> pl.DataFrame:
    """Train-split rows of the committed processed parquet."""
    df = pl.read_parquet(schema.PROCESSED_PARQUET_PATH)
    assignment = load_split()
    return df.join(assignment, on="asset_id", how="inner").filter(
        pl.col("split") == "train"
    )


def _clean(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype="float64")
    return values[~np.isnan(values)]


def psi(reference: np.ndarray, current: np.ndarray, bins: int = PSI_BINS) -> float:
    reference = _clean(reference)
    current = _clean(current)
    if reference.size == 0 or current.size == 0:
        return float("nan")
    edges = np.unique(np.quantile(reference, np.linspace(0.0, 1.0, bins + 1)))
    if edges.size < 2:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(reference, bins=edges)
    cur_counts, _ = np.histogram(current, bins=edges)
    eps = 1e-6
    ref_frac = np.clip(ref_counts / ref_counts.sum(), eps, None)
    cur_frac = np.clip(cur_counts / cur_counts.sum(), eps, None)
    return float(np.sum((cur_frac - ref_frac) * np.log(cur_frac / ref_frac)))


def compute_drift(current: pl.DataFrame, reference: pl.DataFrame | None = None) -> dict:
    """PSI + KS per numeric feature between a current batch and the reference.

    Returns a dict with the per-feature table and a summary. Only input drift
    is measured; label drift is impossible on this static 2018 data.
    """
    if reference is None:
        reference = load_reference()
    features = [f for f in numeric_reference_features(reference) if f in current.columns]

    rows = []
    for feature in features:
        ref_vals = _clean(reference[feature].to_numpy())
        cur_vals = _clean(current[feature].to_numpy())
        feature_psi = psi(ref_vals, cur_vals)
        if ref_vals.size and cur_vals.size:
            ks_stat, ks_p = ks_2samp(ref_vals, cur_vals)
        else:
            ks_stat, ks_p = float("nan"), float("nan")
        rows.append(
            {
                "feature": feature,
                "psi": feature_psi,
                "ks_statistic": float(ks_stat),
                "ks_p_value": float(ks_p),
                "drifted": bool(feature_psi > PSI_FLAG_THRESHOLD),
            }
        )

    drifted = [r["feature"] for r in rows if r["drifted"]]
    return {
        "n_reference": reference.height,
        "n_current": current.height,
        "psi_threshold": PSI_FLAG_THRESHOLD,
        "features": rows,
        "drifted_features": drifted,
        "any_drift": len(drifted) > 0,
        "note": (
            "Input drift only. Label drift is not measurable: idealista18 is "
            "static 2018 asking prices with no live sale feed."
        ),
    }


def _format_report(result: dict) -> str:
    lines = [
        "# Input-drift report",
        "",
        result["note"],
        "",
        f"Reference rows: {result['n_reference']}  Current rows: {result['n_current']}",
        f"PSI flag threshold: {result['psi_threshold']}",
        "",
        "| feature | psi | ks_statistic | ks_p_value | drifted |",
        "|---|---|---|---|---|",
    ]
    for row in result["features"]:
        lines.append(
            f"| {row['feature']} | {row['psi']:.4f} | {row['ks_statistic']:.4f} "
            f"| {row['ks_p_value']:.4g} | {row['drifted']} |"
        )
    lines.append("")
    if result["any_drift"]:
        lines.append("Drifted features: " + ", ".join(result["drifted_features"]))
    else:
        lines.append("No feature crossed the PSI threshold.")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Self-drift demonstration: reference vs a random subsample of itself.

    With no live query stream, the honest demo runs the check against a sample
    of the training population, which should report no drift (PSI near zero).
    That shows the mechanism works and does not raise false positives.
    """
    import json

    reference = load_reference()
    current = reference.sample(fraction=0.25, seed=42)
    result = compute_drift(current, reference=reference)

    report_dir = Path(__file__).resolve().parent
    (report_dir / "drift_report.md").write_text(_format_report(result))
    (report_dir / "drift_report.json").write_text(json.dumps(result, indent=2))
    print(_format_report(result))


if __name__ == "__main__":
    main()
