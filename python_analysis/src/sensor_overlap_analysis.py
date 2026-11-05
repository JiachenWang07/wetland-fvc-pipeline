"""Summarize same-year Landsat 7/8 common-support validation exports."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = {
    "region", "year", "l7_scenes", "l8_scenes", "common_valid_fraction",
    "ndvi_l8_minus_l7", "fvc_l8_minus_l7",
}


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    valid = frame.dropna(subset=["fvc_l8_minus_l7", "ndvi_l8_minus_l7"]).copy()
    if valid.empty:
        raise ValueError("no valid paired L7/L8 observations")
    rows = []
    for region, group in list(valid.groupby("region")) + [("ALL", valid)]:
        fvc = group["fvc_l8_minus_l7"].to_numpy()
        ndvi = group["ndvi_l8_minus_l7"].to_numpy()
        rows.append({
            "region": region,
            "paired_years": len(group),
            "year_min": int(group["year"].min()),
            "year_max": int(group["year"].max()),
            "mean_common_valid_fraction": group["common_valid_fraction"].mean(),
            "mean_fvc_bias_l8_minus_l7": fvc.mean(),
            "mae_fvc": np.abs(fvc).mean(),
            "rmse_fvc": np.sqrt(np.mean(fvc ** 2)),
            "max_abs_fvc_difference": np.abs(fvc).max(),
            "mean_ndvi_bias_l8_minus_l7": ndvi.mean(),
            "mae_ndvi": np.abs(ndvi).mean(),
            "both_sensors_present_all_pairs": bool(((group["l7_scenes"] > 0) & (group["l8_scenes"] > 0)).all()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="GEE common-support CSV")
    parser.add_argument("output", type=Path, help="summary CSV")
    args = parser.parse_args()
    summary = summarize(pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output, index=False)
    print(summary.to_string(index=False))
    print("\nDiagnostic only: do not apply a correction without inspecting yearly and regional stability.")


if __name__ == "__main__":
    main()
