from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
LISTINGS_PATH = REPO_ROOT / "data" / "processed" / "listings.parquet"
SPLIT_PATH = REPO_ROOT / "models" / "tabular" / "split_assignment.parquet"
TILE_ASSIGNMENT_PATH = Path(__file__).resolve().parent / "tile_assignment.parquet"
SUBSET_MANIFEST_PATH = Path(__file__).resolve().parent / "subset_manifest.parquet"

TILE_DECIMALS = 4
TILE_HALF_LAT = 0.00054
TILE_HALF_LON = 0.00071
TILE_PX = 256

SUBSET_TRAIN_TILES = 16000
SUBSET_EVAL_TILES = 4000
SEED = 42

POSITIVE_CONDITIONS = ("good", "new")


def build_tile_assignment() -> pl.DataFrame:
    listings = pl.read_parquet(LISTINGS_PATH, columns=["asset_id", "latitude", "longitude", "condition"])
    split = pl.read_parquet(SPLIT_PATH)
    df = listings.join(split, on="asset_id", how="inner")
    assert df.height == listings.height

    df = df.with_columns(
        tile_lat=pl.col("latitude").round(TILE_DECIMALS),
        tile_lon=pl.col("longitude").round(TILE_DECIMALS),
        label=pl.col("condition").is_in(POSITIVE_CONDITIONS).cast(pl.Int8),
    ).with_columns(
        tile_id=(
            pl.col("tile_lat").map_elements(lambda v: f"{v:.4f}", return_dtype=pl.String)
            + "_"
            + pl.col("tile_lon").map_elements(lambda v: f"{v:.4f}", return_dtype=pl.String)
        )
    )

    tile_purity = df.group_by("tile_id").agg(
        has_val_or_test=(pl.col("split") != "train").any(),
        n_listings=pl.len(),
    ).with_columns(
        cnn_trainable=~pl.col("has_val_or_test"),
    )

    out = df.join(tile_purity, on="tile_id", how="left")
    out.write_parquet(TILE_ASSIGNMENT_PATH)
    return out


def build_subset_manifest(assignment: pl.DataFrame) -> pl.DataFrame:
    train_tiles = (
        assignment.filter(pl.col("cnn_trainable") & (pl.col("split") == "train"))
        .group_by("tile_id")
        .agg(
            tile_lat=pl.col("tile_lat").first(),
            tile_lon=pl.col("tile_lon").first(),
            tile_label=(pl.col("label").mean() >= 0.5).cast(pl.Int8),
        )
    )
    sampled_train = (
        train_tiles.sort("tile_id")
        .with_columns(
            rank=pl.int_range(pl.len()).shuffle(seed=SEED).over("tile_label"),
            n_class=pl.len().over("tile_label"),
        )
        .filter(pl.col("rank") < (pl.col("n_class") / train_tiles.height * SUBSET_TRAIN_TILES).ceil())
        .drop("rank", "n_class")
        .head(SUBSET_TRAIN_TILES)
        .with_columns(role=pl.lit("train"))
    )

    val_tiles = (
        assignment.filter(pl.col("split") == "val")
        .group_by("tile_id")
        .agg(
            tile_lat=pl.col("tile_lat").first(),
            tile_lon=pl.col("tile_lon").first(),
            tile_label=(pl.col("label").mean() >= 0.5).cast(pl.Int8),
        )
    )
    overlap = set(sampled_train["tile_id"]) & set(val_tiles["tile_id"])
    assert not overlap
    sampled_eval = (
        val_tiles.sort("tile_id")
        .with_columns(
            rank=pl.int_range(pl.len()).shuffle(seed=SEED).over("tile_label"),
            n_class=pl.len().over("tile_label"),
        )
        .filter(pl.col("rank") < (pl.col("n_class") / val_tiles.height * SUBSET_EVAL_TILES).ceil())
        .drop("rank", "n_class")
        .head(SUBSET_EVAL_TILES)
        .with_columns(role=pl.lit("eval"))
    )

    manifest = pl.concat([sampled_train, sampled_eval])
    manifest.write_parquet(SUBSET_MANIFEST_PATH)
    return manifest


if __name__ == "__main__":
    assignment = build_tile_assignment()
    n_tiles = assignment["tile_id"].n_unique()
    pure = assignment.filter(pl.col("cnn_trainable"))["tile_id"].n_unique()
    mixed = n_tiles - pure
    straddle = assignment.filter(pl.col("has_val_or_test") & (pl.col("split") == "train")).height
    print(f"listings: {assignment.height}")
    print(f"tiles: {n_tiles}  pure_train_tiles: {pure}  tiles_with_val_or_test: {mixed}")
    print(f"train listings excluded from CNN training (straddling tiles): {straddle}")
    manifest = build_subset_manifest(assignment)
    print(manifest.group_by("role", "tile_label").len().sort("role", "tile_label"))
