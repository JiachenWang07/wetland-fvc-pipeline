"""
report_comparison.py

Automates what was previously a manual, one-off comparison: checks the
live pipeline's Sen's slope / Mann-Kendall results (trend_analysis.py)
against the values reported in the team's final report, section 3.1
("三区域FVC分段趋势"), FVC_Dynamic indicator only (the only one reported
in that table).

REPORTED values below are transcribed directly from the report table —
if the report is ever revised, this dict is the single place to update.
Only p-value and direction are reported in the source table; sen_slope
and tau are not available for comparison (would require the report's
original CSV, which is not part of this repository).

This is not a replacement for the manual cross-check already documented
in docs/methodology_notes.md ("第四轮：真实数据验证") — it's a
reproducible version of the same check, so it doesn't have to be redone
by hand if the pipeline is re-run after future code changes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_loader import DEFAULT_DATA_DIR, load_all_regions
from trend_analysis import compute_regional_trends

# Transcribed from the final report, section 3.1 table. p_value_is_upper_bound
# marks the one cell reported as "p<0.001" rather than an exact value.
REPORTED = [
    {"region": "YRD", "period": "1985-2005", "direction": "decreasing", "p_value": 0.004, "p_is_upper_bound": False},
    {"region": "YRD", "period": "2005-2020", "direction": "increasing", "p_value": 0.001, "p_is_upper_bound": True},
    {"region": "GBA", "period": "1985-2005", "direction": "no trend", "p_value": 0.075, "p_is_upper_bound": False},
    {"region": "GBA", "period": "2005-2020", "direction": "increasing", "p_value": 0.003, "p_is_upper_bound": False},
    {"region": "BTH", "period": "1985-2005", "direction": "decreasing", "p_value": 0.002, "p_is_upper_bound": False},
    {"region": "BTH", "period": "2005-2020", "direction": "no trend", "p_value": 0.753, "p_is_upper_bound": False},
]


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    indices_dfs = load_all_regions("indices_36years", data_dir)

    live_rows = []
    for region, df in indices_dfs.items():
        region_trends = compute_regional_trends(df, region)
        subset = region_trends[
            (region_trends["indicator"] == "FVC_Dynamic") & (region_trends["status"] == "primary")
        ]
        for _, row in subset.iterrows():
            live_rows.append({
                "region": row["region"],
                "period": row["period"],
                "live_direction": row["trend"],
                "live_p_value": row["p_value"],
                "live_sen_slope": row["sen_slope"],
            })
    live_df = pd.DataFrame(live_rows)

    reported_df = pd.DataFrame(REPORTED)
    comparison = reported_df.merge(live_df, on=["region", "period"], how="left")

    comparison["direction_match"] = comparison["direction"] == comparison["live_direction"]

    def p_matches(row):
        if pd.isna(row["live_p_value"]):
            return None
        if row["p_is_upper_bound"]:
            return row["live_p_value"] < row["p_value"]
        return abs(row["live_p_value"] - row["p_value"]) < 0.02

    comparison["p_value_consistent"] = comparison.apply(p_matches, axis=1)

    print("=" * 90)
    print("Report vs. live pipeline comparison — FVC_Dynamic, segmented Sen's slope / Mann-Kendall")
    print("=" * 90)
    display_cols = ["region", "period", "direction", "live_direction", "direction_match",
                     "p_value", "live_p_value", "p_value_consistent", "live_sen_slope"]
    print(comparison[display_cols].to_string(index=False))

    n_total = len(comparison)
    n_dir_match = comparison["direction_match"].sum()
    n_p_match = comparison["p_value_consistent"].sum()
    print(f"\nDirection match: {n_dir_match}/{n_total}")
    print(f"P-value consistent (within tolerance, or below reported upper bound): {n_p_match}/{n_total}")

    if n_dir_match < n_total:
        print("\n[ATTENTION] At least one direction mismatch — this is a real discrepancy "
              "worth investigating before trusting the reproduction, not something to wave away.")

    out_path = Path(data_dir) / "ReportComparison_Section3_1.csv"
    comparison.to_csv(out_path, index=False)
    print(f"\n[OK] Saved to {out_path}")

    return comparison


if __name__ == "__main__":
    main()
