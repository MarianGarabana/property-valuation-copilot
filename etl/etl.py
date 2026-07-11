"""Polars ETL: raw idealista18 Madrid Parquet -> cleaned processed Parquet.

Steps, in order:
1. Load the raw Parquet written by source.py.
2. Rename raw columns to the snake_case names in schema.COLUMN_MAP.
3. Derive condition (from BUILTTYPEID one-hot), property_type (from studio/duplex
   flags), property_age, and the cnn_condition_score null placeholder.
4. Cast types and clean construction_year (values outside 1900-2018 -> null).
5. Dedupe to one row per asset_id, keeping the latest 2018 quarter.
6. Drop hard-invalid rows (price/area/unit_price <= 0, coordinates outside the
   Madrid bounding box).
7. Drop outliers: rows whose price, area_m2, or unit_price_m2 fall outside the
   [1%, 99%] sample quantiles (schema.OUTLIER_QUANTILES / OUTLIER_COLUMNS).
8. Assign neighborhood_id/neighborhood_name by point-in-polygon against the
   Madrid_Polygons barrios (135 zone-level-8 polygons). Points outside every
   barrio stay null.
9. Write data/processed/listings.parquet with columns in schema.FEATURE_NAMES order.

All numbers are 2018 asking prices, not closed sales.
"""

import subprocess
import tempfile
from pathlib import Path

import polars as pl
from shapely import STRtree, points
from shapely import wkt as shp_wkt

import schema

ETL_DIR = Path(__file__).resolve().parent
POLYGONS_RDA = schema.RAW_PARQUET_PATH.parent / "Madrid_Polygons.rda"
POLYGONS_R_HELPER = ETL_DIR / "polygons_to_wkt.R"


def _load_barrios() -> pl.DataFrame:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
    try:
        subprocess.run(
            ["Rscript", str(POLYGONS_R_HELPER), str(POLYGONS_RDA),
             "Madrid_Polygons", str(csv_path)],
            check=True, capture_output=True, text=True,
        )
        return pl.read_csv(csv_path)
    finally:
        csv_path.unlink(missing_ok=True)


def _assign_neighborhoods(df: pl.DataFrame) -> pl.DataFrame:
    barrios = _load_barrios()
    geoms = [shp_wkt.loads(w) for w in barrios["wkt"]]
    loc_id = barrios["LOCATIONID"].to_list()
    loc_name = barrios["LOCATIONNAME"].to_list()
    tree = STRtree(geoms)

    pts = points(df["longitude"].to_numpy(), df["latitude"].to_numpy())
    pt_idx, tree_idx = tree.query(pts, predicate="within")

    nid = [None] * df.height
    nname = [None] * df.height
    for p, t in zip(pt_idx.tolist(), tree_idx.tolist()):
        if nid[p] is None:  # first match wins for the few shared-edge points
            nid[p] = loc_id[t]
            nname[p] = loc_name[t]

    return df.with_columns(
        pl.Series("neighborhood_id", nid, dtype=pl.Utf8),
        pl.Series("neighborhood_name", nname, dtype=pl.Utf8),
    )


def _derive(df: pl.DataFrame) -> pl.DataFrame:
    condition = (
        pl.when(pl.col("BUILTTYPEID_1") == 1).then(pl.lit("new"))
        .when(pl.col("BUILTTYPEID_2") == 1).then(pl.lit("needs_renovation"))
        .otherwise(pl.lit("good"))
        .alias("condition")
    )
    property_type = (
        pl.when(pl.col("ISSTUDIO") == 1).then(pl.lit("studio"))
        .when(pl.col("ISDUPLEX") == 1).then(pl.lit("duplex"))
        .otherwise(pl.lit("flat"))
        .alias("property_type")
    )
    return df.with_columns(condition, property_type)


def run() -> pl.DataFrame:
    raw = pl.read_parquet(schema.RAW_PARQUET_PATH)
    raw_rows = raw.height

    df = _derive(raw)
    df = df.rename(schema.COLUMN_MAP)

    df = df.with_columns(
        pl.col("asset_id").cast(pl.Utf8),
        pl.col("period").cast(pl.Int64),
        pl.col("construction_year")
        .cast(pl.Int64)
        .pipe(
            lambda c: pl.when(
                (c >= schema.CONSTRUCTION_YEAR_MIN) & (c <= schema.CONSTRUCTION_YEAR_MAX)
            ).then(c).otherwise(None)
        )
        .alias("construction_year"),
    )
    df = df.with_columns(
        (schema.REFERENCE_YEAR - pl.col("construction_year")).alias("property_age"),
        pl.lit(None, dtype=pl.Float64).alias("cnn_condition_score"),
    )

    # Dedupe: same property re-listed across 2018 quarters. Keep the latest.
    df = df.sort("period").unique(subset="asset_id", keep="last", maintain_order=True)
    deduped_rows = df.height

    # Hard validity.
    bbox = schema.MADRID_BBOX
    df = df.filter(
        (pl.col("price") > 0)
        & (pl.col("area_m2") > 0)
        & (pl.col("unit_price_m2") > 0)
        & pl.col("latitude").is_between(bbox["lat_min"], bbox["lat_max"])
        & pl.col("longitude").is_between(bbox["lon_min"], bbox["lon_max"])
    )
    valid_rows = df.height

    # Outliers: quantile bounds on price, area, and unit price.
    lo = schema.OUTLIER_QUANTILES["lower"]
    hi = schema.OUTLIER_QUANTILES["upper"]
    mask = pl.lit(True)
    for col in schema.OUTLIER_COLUMNS:
        low = df[col].quantile(lo)
        high = df[col].quantile(hi)
        mask = mask & pl.col(col).is_between(low, high)
    df = df.filter(mask)
    final_rows = df.height

    # Point-in-polygon barrio assignment on the final rows (order preserved).
    df = _assign_neighborhoods(df)
    matched_rows = df["neighborhood_id"].drop_nulls().len()

    df = df.select(schema.FEATURE_NAMES)
    schema.PROCESSED_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(schema.PROCESSED_PARQUET_PATH)

    print(f"raw rows:            {raw_rows}")
    print(f"after dedupe:        {deduped_rows}")
    print(f"after hard validity: {valid_rows}")
    print(f"after outliers:      {final_rows}")
    print(f"neighborhood match:  {matched_rows} / {final_rows}")
    print(f"wrote {schema.PROCESSED_PARQUET_PATH}")
    return df


if __name__ == "__main__":
    run()
