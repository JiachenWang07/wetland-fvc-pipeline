"""
trend_analysis.py

Sen's slope + Mann-Kendall trend testing on the region-level 36-year FVC
time series (one mean value per region per year — NOT per-pixel; the
per-pixel trend screening lives in gee_scripts/trend_classification.js and
uses OLS, a different method for a different purpose — see
docs/architecture.md).

Method note, carried over from docs/methodology_notes.md: full-period
(1985-2020) Mann-Kendall testing was formally abandoned after
fixed-endmember cross-validation showed the result was sensitive to
endmember choice. It is still computed here and included in the output,
labeled as deprecated, so the record of *why* it was abandoned stays
attached to the actual numbers that motivated abandoning it — deleting it
outright would have made that methodological decision harder to audit
later. The segmented test (1985-2005 / 2005-2020) is the result actually
used in reporting.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pymannkendall as mk

from data_loader import DEFAULT_DATA_DIR, REGIONS, load_all_regions, validate_endmembers

# Indicator columns tested, matching what fvc_dynamic_endmember.js exports.
INDICATOR_COLUMNS = ["FVC_Dynamic", "FVC_Fixed1985", "EVI_Dynamic", "NDMI_Dynamic"]

# The single, official breakpoint for segmented testing. Not derived from
# the data — chosen a priori based on the wetland-policy history motivating
# this study, and applied identically across all three regions and all
# indicator columns.
SEGMENT_BREAKPOINT = 2005
MIN_SERIES_LENGTH = 5  # Mann-Kendall is unreliable on very short series


def run_mk_test(series: pd.Series) -> dict | None:
    """Runs pymannkendall's original (non-seasonal) test on a 1D series.
    Returns None if the series is too short to test meaningfully, rather
    than letting pymannkendall raise or return a degenerate result.
    """
    values = series.dropna().values
    if len(values) < MIN_SERIES_LENGTH:
        return None
    result = mk.original_test(values)
    return {
        "sen_slope": result.slope,
        "trend": result.trend,
        "p_value": result.p,
        "significant": result.h,
        "tau": result.Tau,
        "n": len(values),
    }


def compute_regional_trends(indices_df: pd.DataFrame, region: str) -> pd.DataFrame:
    """Computes both the deprecated full-period test and the primary
    segmented tests for every indicator column, for one region.
    """
    df = indices_df.sort_values("year")
    rows = []

    periods = [
        ("1985-2020", df, "deprecated — sensitive to endmember choice, see methodology_notes.md"),
        ("1985-2005", df[df["year"] <= SEGMENT_BREAKPOINT], "primary"),
        (f"{SEGMENT_BREAKPOINT}-2020", df[df["year"] >= SEGMENT_BREAKPOINT], "primary"),
    ]

    for period_name, period_df, status in periods:
        for column in INDICATOR_COLUMNS:
            if column not in period_df.columns:
                continue
            result = run_mk_test(period_df[column])
            if result is None:
                continue
            rows.append({
                "region": region,
                "indicator": column,
                "period": period_name,
                "status": status,
                **result,
            })

    return pd.DataFrame(rows)


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    indices_dfs = load_all_regions("indices_36years", data_dir)

    if len(indices_dfs) < len(REGIONS):
        missing = set(REGIONS) - set(indices_dfs)
        print(f"[WARN] Proceeding with {len(indices_dfs)}/{len(REGIONS)} regions — missing: {missing}")

    print("\n" + "=" * 60)
    print("ENDMEMBER VALIDATION")
    print("=" * 60)
    for region, df in indices_dfs.items():
        validate_endmembers(df, region)

    print("\n" + "=" * 60)
    print("TREND ANALYSIS (Sen's slope + Mann-Kendall)")
    print("=" * 60)
    all_results = []
    for region, df in indices_dfs.items():
        region_results = compute_regional_trends(df, region)
        all_results.append(region_results)

    combined = pd.concat(all_results, ignore_index=True)

    print("\nPrimary (segmented) results:")
    print(combined[combined["status"] == "primary"].to_string(index=False))
    print("\nDeprecated (full-period) results — for audit trail only, not used in reporting:")
    print(combined[combined["status"] != "primary"].to_string(index=False))

    out_path = Path(data_dir) / "MK_Sen_Results.csv"
    combined.to_csv(out_path, index=False)
    print(f"\n[OK] Saved combined results to {out_path}")

    return combined


if __name__ == "__main__":
    main()
