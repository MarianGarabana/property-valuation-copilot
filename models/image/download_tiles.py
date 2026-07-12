import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import polars as pl

from tiles import REPO_ROOT, SUBSET_MANIFEST_PATH, TILE_HALF_LAT, TILE_HALF_LON, TILE_PX

TILE_DIR = REPO_ROOT / "data" / "images" / "tiles"
WMS_URL = "https://www.ign.es/wms-inspire/pnoa-ma"
ATTRIBUTION = "Obra derivada de PNOA CC-BY 4.0 scne.es"
WORKERS = 4
RETRIES = 3
MIN_BYTES = 3000


def tile_url(lat: float, lon: float) -> str:
    bbox = f"{lat - TILE_HALF_LAT:.6f},{lon - TILE_HALF_LON:.6f},{lat + TILE_HALF_LAT:.6f},{lon + TILE_HALF_LON:.6f}"
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": "OI.OrthoimageCoverage",
        "STYLES": "",
        "CRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": str(TILE_PX),
        "HEIGHT": str(TILE_PX),
        "FORMAT": "image/jpeg",
    }
    return f"{WMS_URL}?{urllib.parse.urlencode(params)}"


def fetch_one(row: dict) -> str:
    out_path = TILE_DIR / f"{row['tile_id']}.jpg"
    if out_path.exists() and out_path.stat().st_size >= MIN_BYTES:
        return "cached"
    url = tile_url(row["tile_lat"], row["tile_lon"])
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "avm-prototype-tile-fetch"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            if resp.headers.get_content_type() == "image/jpeg" and len(data) >= MIN_BYTES:
                out_path.write_bytes(data)
                return "ok"
        except Exception:
            pass
        time.sleep(2**attempt)
    return "failed"


def main() -> None:
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = pl.read_parquet(SUBSET_MANIFEST_PATH)
    rows = manifest.select("tile_id", "tile_lat", "tile_lon").to_dicts()
    counts = {"ok": 0, "cached": 0, "failed": 0}
    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, status in enumerate(pool.map(fetch_one, rows), 1):
            counts[status] += 1
            if i % 1000 == 0:
                rate = i / (time.time() - start)
                print(f"{i}/{len(rows)} counts={counts} rate={rate:.1f}/s", flush=True)
    print(f"done {counts} elapsed={time.time() - start:.0f}s")
    if counts["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
