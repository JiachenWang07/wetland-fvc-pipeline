"""
six_category_area_stats.py

Computes the six-category area-function transition statistics from local
raster files (downloaded from the gee_scripts/ Drive exports, not
committed to this repo — see .gitignore). This is an offline/local
computation rather than a GEE-side one because the full-resolution,
multi-year pixel comparison this needs previously caused GEE server-side
memory exhaustion when attempted as a single reduceRegion call; reading
and processing the exported GeoTIFFs locally in windowed blocks avoids
that.

Two bugs from earlier iterations of this computation are deliberately NOT
reproduced here (see docs/methodology_notes.md, "调试记录" #4 and #5 for
the full history):
  1. Wetland extent must be defined from land-cover class codes (181-187),
     not from FVC-raster nodata presence/absence. Using FVC nodata as a
     stand-in for "is this wetland" conflated missing/cloud-masked pixels
     with genuinely non-wetland pixels, and produced area totals that
     diverged from the transition-matrix cross-check by 1.7-2.2x.
  2. Pixel area must be computed from actual latitude-dependent ground
     distance, not from raw degree² treated as km². The source rasters are
     in geographic (degree-based) coordinates; a fixed degree-to-km²
     conversion factor is wrong by orders of magnitude and varies with
     latitude within a single region.
"""

from __future__ import annotations

import gc
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from data_loader import DEFAULT_DATA_DIR, REGIONS

# Must match WETLAND_CODES in gee_scripts/region_pipeline.js — kept as a
# separate constant here (not imported, since this is a different
# language/runtime) rather than assumed to stay in sync automatically.
WETLAND_CODES = [181, 182, 183, 184, 185, 186, 187]

EARTH_RADIUS_KM = 6371.0088
DEG_TO_RAD = np.pi / 180.0

# New-wetland low/high cover split — see docs/limitations.md for the
# citation-confidence caveat on this specific number (SL 190-2007,
# confirmed via secondary academic citation, not primary-text verified).
NEW_WETLAND_FVC_THRESHOLD = 0.45

SIX_CATEGORY_LABELS = [
    "Wetland Lost",
    "Vegetation Degraded",
    "Basically Stable",
    "Vegetation Improved",
    "New Low-Cover Wetland (<45%)",
    "New High-Cover Wetland (>=45%)",
]


def _raster_path(data_dir: Path, region: str, product: str) -> Path:
    filenames = {
        "landcover_1985": f"{region}_RawLandCover_1985.tif",
        "landcover_2020": f"{region}_RawLandCover_2020.tif",
        "fvc_2020": f"{region}_FVC_2020_30m.tif",
        "trend_class": f"{region}_FVC_TrendClass_5Level.tif",
    }
    return Path(data_dir) / filenames[product]


def _pixel_area_km2_per_row(transform, row_start: int, n_rows: int) -> np.ndarray:
    """Latitude-dependent pixel area (km²) for each row in a raster window.
    Longitude spacing shrinks with cos(latitude); latitude spacing does
    not. Returns a 1D array of length n_rows.
    """
    deg_lon = abs(transform.a)
    deg_lat = abs(transform.e)
    row_indices = np.arange(row_start, row_start + n_rows)
    lats = np.array([transform * (0, r + 0.5) for r in row_indices])[:, 1]
    lat_km = deg_lat * DEG_TO_RAD * EARTH_RADIUS_KM
    lon_km_per_row = deg_lon * DEG_TO_RAD * EARTH_RADIUS_KM * np.cos(lats * DEG_TO_RAD)
    return lat_km * lon_km_per_row


def compute_six_category_for_region(region: str, data_dir: Path | str = DEFAULT_DATA_DIR) -> pd.DataFrame | None:
    """Windowed (block-by-block) computation to keep memory usage bounded
    regardless of raster size — the original single-array-in-memory
    attempt on the GEE side is what caused the timeout/crash this was
    written to avoid.
    """
    paths = {
        key: _raster_path(Path(data_dir), region, key)
        for key in ["landcover_1985", "landcover_2020", "fvc_2020", "trend_class"]
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        print(f"[WARN] {region}: missing raster(s), skipping: {missing}")
        return None

    with rasterio.open(paths["landcover_1985"]) as src_lc1985, \
         rasterio.open(paths["landcover_2020"]) as src_lc2020, \
         rasterio.open(paths["fvc_2020"]) as src_fvc2020, \
         rasterio.open(paths["trend_class"]) as src_trend:

        shapes = {(s.width, s.height) for s in [src_lc1985, src_lc2020, src_fvc2020, src_trend]}
        if len(shapes) > 1:
            print(f"[WARN] {region}: raster grids don't match ({shapes}), needs reprojection first — skipping")
            return None

        nodata_lc1985 = src_lc1985.nodata
        nodata_lc2020 = src_lc2020.nodata
        nodata_fvc2020 = src_fvc2020.nodata
        nodata_trend = src_trend.nodata
        transform = src_lc1985.transform

        counts = {label: 0.0 for label in SIX_CATEGORY_LABELS}

        for _, window in src_lc1985.block_windows(1):
            lc1985 = src_lc1985.read(1, window=window)
            lc2020 = src_lc2020.read(1, window=window)
            fvc2020 = src_fvc2020.read(1, window=window)
            trend = src_trend.read(1, window=window)

            valid_lc1985 = (lc1985 != nodata_lc1985) if nodata_lc1985 is not None else np.ones_like(lc1985, dtype=bool)
            valid_lc2020 = (lc2020 != nodata_lc2020) if nodata_lc2020 is not None else np.ones_like(lc2020, dtype=bool)
            wetland1985 = np.isin(lc1985, WETLAND_CODES) & valid_lc1985
            wetland2020 = np.isin(lc2020, WETLAND_CODES) & valid_lc2020

            valid_fvc2020 = (fvc2020 != nodata_fvc2020) if nodata_fvc2020 is not None else ~np.isnan(fvc2020)
            valid_trend = (trend != nodata_trend) if nodata_trend is not None else (trend > 0)

            lost = wetland1985 & ~wetland2020
            gained = ~wetland1985 & wetland2020
            persistent = wetland1985 & wetland2020

            area_weight = _pixel_area_km2_per_row(transform, window.row_off, window.height)[:, np.newaxis]

            counts["Wetland Lost"] += np.sum(lost * area_weight)
            counts["Vegetation Degraded"] += np.sum((persistent & valid_trend & (trend <= 2)) * area_weight)
            counts["Basically Stable"] += np.sum((persistent & valid_trend & (trend == 3)) * area_weight)
            counts["Vegetation Improved"] += np.sum((persistent & valid_trend & (trend >= 4)) * area_weight)
            counts["New Low-Cover Wetland (<45%)"] += np.sum(
                (gained & valid_fvc2020 & (fvc2020 < NEW_WETLAND_FVC_THRESHOLD)) * area_weight
            )
            counts["New High-Cover Wetland (>=45%)"] += np.sum(
                (gained & valid_fvc2020 & (fvc2020 >= NEW_WETLAND_FVC_THRESHOLD)) * area_weight
            )

            del lc1985, lc2020, fvc2020, trend
            del valid_lc1985, valid_lc2020, wetland1985, wetland2020, valid_fvc2020, valid_trend
            del lost, gained, persistent, area_weight

    gc.collect()
    return pd.DataFrame([{"region": region, "class_label": k, "area_km2": v} for k, v in counts.items()])


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    results = []
    for region in REGIONS:
        df = compute_six_category_for_region(region, data_dir)
        if df is not None:
            results.append(df)
            print(f"[OK] {region}: six-category area stats computed")

    combined = pd.concat(results, ignore_index=True)
    out_path = Path(data_dir) / "SixCategory_AreaStats.csv"
    combined.to_csv(out_path, index=False)
    print(f"\n[OK] Saved combined results to {out_path}")
    print(combined.pivot(index="class_label", columns="region", values="area_km2").reindex(SIX_CATEGORY_LABELS))

    return combined


if __name__ == "__main__":
    main()
