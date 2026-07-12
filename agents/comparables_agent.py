import math
import statistics
import sys
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.data import load_listings

EARTH_RADIUS_KM = 6371.0
AREA_SCALE_M2 = 20.0
ROOMS_WEIGHT = 0.7
TOP_K = 5

COMP_FIELDS = [
    "asset_id",
    "price",
    "area_m2",
    "rooms",
    "bathrooms",
    "property_type",
    "neighborhood_name",
    "distance_km",
    "area_diff_m2",
    "rooms_diff",
    "score",
]


def run(subject, top_k=TOP_K):
    pool = load_listings().filter(pl.col("property_type") == subject["property_type"])
    if subject.get("asset_id"):
        pool = pool.filter(pl.col("asset_id") != subject["asset_id"])
    if pool.height == 0:
        raise ValueError(f"no listings share property_type {subject['property_type']!r}")

    lat0 = math.radians(float(subject["latitude"]))
    lon0 = math.radians(float(subject["longitude"]))
    lat = pl.col("latitude").radians()
    lon = pl.col("longitude").radians()
    half_dlat = (lat - lat0) / 2.0
    half_dlon = (lon - lon0) / 2.0
    a = half_dlat.sin().pow(2) + math.cos(lat0) * lat.cos() * half_dlon.sin().pow(2)
    distance_km = 2.0 * EARTH_RADIUS_KM * a.sqrt().arcsin()

    scored = (
        pool.with_columns(
            distance_km=distance_km,
            area_diff_m2=(pl.col("area_m2") - float(subject["area_m2"])).abs(),
            rooms_diff=(pl.col("rooms") - int(subject["rooms"])).abs(),
        )
        .with_columns(
            score=pl.col("distance_km")
            + pl.col("area_diff_m2") / AREA_SCALE_M2
            + ROOMS_WEIGHT * pl.col("rooms_diff")
        )
        .sort(["score", "asset_id"])
        .head(top_k)
    )

    comps = []
    for row in scored.select(COMP_FIELDS).iter_rows(named=True):
        row["why"] = (
            f"{row['distance_km']:.2f} km from the subject, "
            f"{row['area_m2']:.0f} m2 vs {float(subject['area_m2']):.0f} m2, "
            f"{int(row['rooms'])} rooms vs {int(subject['rooms'])}, "
            f"same property type ({row['property_type']})"
        )
        comps.append(row)

    prices = [c["price"] for c in comps]
    return {
        "method": (
            f"same property_type as the subject, ranked by "
            f"score = distance_km + area_diff_m2/{AREA_SCALE_M2:g} + {ROOMS_WEIGHT:g}*rooms_diff, "
            f"top {top_k} kept"
        ),
        "comps": comps,
        "n": len(comps),
        "price_min": min(prices),
        "price_max": max(prices),
        "price_median": statistics.median(prices),
        "max_distance_km": max(c["distance_km"] for c in comps),
    }
