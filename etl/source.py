"""Source idealista18 Madrid sale listings into a raw Parquet file.

The idealista18 Madrid sale table ships as an R `.rda` sf object, which pyreadr
cannot parse (the geometry list-column is an unsupported feature). This step
uses R (already free and installed) only to drop the geometry column and dump a
plain CSV, then Polars reads that CSV and writes the raw Parquet. Coordinates
survive as the LONGITUDE/LATITUDE columns, so nothing geographic is lost.

Input:  data/raw/Madrid_Sale.rda  (downloaded from github.com/paezha/idealista18)
Output: data/raw/idealista18_madrid.parquet
"""

import subprocess
import tempfile
from pathlib import Path

import polars as pl

from schema import RAW_PARQUET_PATH

ETL_DIR = Path(__file__).resolve().parent
RAW_DIR = RAW_PARQUET_PATH.parent
RDA_PATH = RAW_DIR / "Madrid_Sale.rda"
R_OBJECT = "Madrid_Sale"
R_HELPER = ETL_DIR / "rda_to_csv.R"


def source_listings() -> pl.DataFrame:
    if not RDA_PATH.exists():
        raise FileNotFoundError(
            f"{RDA_PATH} not found. Download Madrid_Sale.rda from "
            "github.com/paezha/idealista18 (data/ directory) first."
        )

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
    try:
        subprocess.run(
            ["Rscript", str(R_HELPER), str(RDA_PATH), R_OBJECT, str(csv_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        df = pl.read_csv(csv_path, infer_schema_length=None)
    finally:
        csv_path.unlink(missing_ok=True)

    RAW_PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(RAW_PARQUET_PATH)
    return df


if __name__ == "__main__":
    frame = source_listings()
    print(f"raw rows: {frame.height}")
    print(f"raw cols: {frame.width}")
    print(f"wrote {RAW_PARQUET_PATH}")
