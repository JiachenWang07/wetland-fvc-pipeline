"""
data_loader.py

Shared data-loading utilities for python_analysis/. Every other script in
this directory reads CSVs produced by gee_scripts/ through the functions
here, rather than each re-implementing its own read-with-fallback logic —
the four historical exploratory notebooks this module replaces each wrote
a slightly different version of "try to read this CSV, print a warning if
missing" inline, which made it hard to tell which version's error handling
was actually correct.

Default data directory: ../outputs/ (relative to this file), matching the
repository's convention of putting reviewed, de-identified CSVs there. Set
WETLAND_DATA_DIR as an environment variable, or pass data_dir explicitly,
to point at a different location (e.g. a local copy of the Drive export
folder before it has been reviewed into outputs/).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

REGIONS = ["YRD", "GBA", "BTH"]
REGION_FULL_NAMES = {
    "YRD": "Yangtze River Delta",
    "GBA": "Greater Bay Area",
    "BTH": "Beijing-Tianjin-Hebei",
}

DEFAULT_DATA_DIR = Path(
    os.environ.get(
        "WETLAND_DATA_DIR",
        Path(__file__).resolve().parent.parent.parent / "outputs",
    )
)

# Filenames as produced by gee_scripts/ — see docs/data_schema.md for the
# full column-level schema of each of these.
FILE_PATTERNS = {
    "indices_36years": "{region}_Indices_36Years.csv",
    "city_fvc_8nodes": "{region}_City_FVC_8Nodes.csv",
    "fixed_endmember_pixel": "{region}_FVC_FixedEndmember_PixelLevel.csv",
    "city_fixed_fvc_8nodes": "{region}_City_FixedFVC_8Nodes.csv",
    "fate_group": "{region}_FateGroup_FVC.csv",
    "trend_class_area_stats": "{region}_FVC_TrendClass_AreaStats.csv",
    "six_category_area_stats": "{region}_SixCategory_AreaStats.csv",
    "transition_structure": "{region}_WetlandTransitionStructure.csv",
    "city_wetland_area_8nodes": "{region}_City_WetlandArea_8Nodes.csv",
    "fvc_by_wetland_type": "{region}_FVC_ByWetlandType.csv",
}


def load_csv(
    product: str,
    region: str,
    data_dir: Path | str = DEFAULT_DATA_DIR,
) -> pd.DataFrame | None:
    """Load one product for one region. Returns None (with a printed
    warning) rather than raising, so a missing file doesn't halt an
    analysis that only needs the other two regions — this mirrors the
    historical scripts' `try/except FileNotFoundError` pattern, but in one
    place instead of copy-pasted at every read site.
    """
    if product not in FILE_PATTERNS:
        raise ValueError(
            f"Unknown product '{product}'. Known products: {sorted(FILE_PATTERNS)}"
        )
    path = Path(data_dir) / FILE_PATTERNS[product].format(region=region)
    if not path.exists():
        print(f"[WARN] Missing file for {region} / {product}: {path}")
        return None
    df = pd.read_csv(path)
    print(f"[OK] Loaded {region} / {product}: {len(df)} rows")
    return df


def load_all_regions(
    product: str,
    data_dir: Path | str = DEFAULT_DATA_DIR,
    regions: list[str] = REGIONS,
) -> dict[str, pd.DataFrame]:
    """Load one product for all regions. Regions with a missing file are
    silently omitted from the returned dict (a warning is still printed by
    load_csv) rather than raising — callers that need all three regions
    present should check `len(result) == len(regions)` themselves.
    """
    result = {}
    for region in regions:
        df = load_csv(product, region, data_dir)
        if df is not None:
            result[region] = df
    return result


def validate_endmembers(indices_df: pd.DataFrame, region: str, std_threshold: float = 0.005) -> bool:
    """Sanity check that dynamic endmembers (NDVI_p5_soil, NDVI_p95_veg)
    actually vary year to year rather than being accidentally constant —
    a near-zero standard deviation would mean the dynamic-endmember logic
    silently fell back to a fixed value somewhere upstream, which was worth
    catching early in the original exploratory analysis and is worth
    keeping as an explicit check here rather than assuming it's fine.

    Returns True if both endmembers vary meaningfully, False otherwise
    (with a printed warning either way).
    """
    required_cols = {"NDVI_p5_soil", "NDVI_p95_veg"}
    if not required_cols.issubset(indices_df.columns):
        print(f"[WARN] {region}: endmember columns missing, found {list(indices_df.columns)}")
        return False

    soil_std = indices_df["NDVI_p5_soil"].std()
    veg_std = indices_df["NDVI_p95_veg"].std()
    varies = soil_std > std_threshold and veg_std > std_threshold

    status = "varies year-to-year" if varies else "near-constant, check upstream pipeline"
    print(f"[{'OK' if varies else 'WARN'}] {region}: soil_std={soil_std:.5f}, veg_std={veg_std:.5f} ({status})")
    return varies
