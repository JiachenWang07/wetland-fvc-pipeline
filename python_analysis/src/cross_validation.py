"""
cross_validation.py

Cross-validates the six-category area-function map (six_category_area_stats.py)
against the land-cover transition matrix (from wetland_transition_structure.js)
by comparing net wetland-area change computed two independent ways. This is
the verification step behind docs/methodology_notes.md's "调试记录 #4":
a ~1.7-2.2x discrepancy between the two products was traced not to a
computation error, but to comparing two statistics that were never meant
to be equal.

Both versions of the comparison are computed here, deliberately, rather
than only the one that matches:
  - water-excluded transition net: this is what produced the original
    1.7-2.2x mismatch, because the six-category map's "lost"/"gained"
    counts are NOT restricted to the same high-confidence human-driven
    subset (cropland + built-up) that the water-excluded transition
    number represents.
  - all-class transition net (water included): this is the statistic that
    actually corresponds to the six-category map's scope, and converges
    to <10% error once compared correctly.
Keeping both in the output preserves the diagnostic trail rather than
just asserting the final number was always right.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_loader import DEFAULT_DATA_DIR, REGIONS, load_all_regions

WATER_BODY_CODE = 210


def six_category_net_change(six_cat_df: pd.DataFrame) -> float:
    by_class = six_cat_df.set_index("class_label")["area_km2"]
    lost = by_class.get("Wetland Lost", 0.0)
    gained = (
        by_class.get("New Low-Cover Wetland (<45%)", 0.0)
        + by_class.get("New High-Cover Wetland (>=45%)", 0.0)
    )
    return gained - lost


def transition_net_change(trans_df: pd.DataFrame, exclude_water: bool) -> float:
    df = trans_df
    if exclude_water:
        df = df[df["converted_class_code"] != WATER_BODY_CODE]
    net_in = df[df["direction"] == "in"]["area_km2"].sum()
    net_out = df[df["direction"] == "out"]["area_km2"].sum()
    return net_in - net_out


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    six_cat_dfs = load_all_regions("six_category_area_stats", data_dir)
    trans_dfs = load_all_regions("transition_structure", data_dir)

    rows = []
    for region in REGIONS:
        if region not in six_cat_dfs or region not in trans_dfs:
            print(f"[WARN] {region}: missing six-category or transition data, skipping")
            continue

        six_net = six_category_net_change(six_cat_dfs[region])
        trans_net_water_excluded = transition_net_change(trans_dfs[region], exclude_water=True)
        trans_net_all_classes = transition_net_change(trans_dfs[region], exclude_water=False)

        error_water_excluded = abs(six_net - trans_net_water_excluded) / abs(six_net) * 100 if six_net else float("nan")
        error_all_classes = abs(six_net - trans_net_all_classes) / abs(six_net) * 100 if six_net else float("nan")

        rows.append({
            "region": region,
            "six_category_net_km2": round(six_net, 1),
            "transition_water_excluded_net_km2": round(trans_net_water_excluded, 1),
            "error_vs_water_excluded_pct": round(error_water_excluded, 1),
            "transition_all_classes_net_km2": round(trans_net_all_classes, 1),
            "error_vs_all_classes_pct": round(error_all_classes, 1),
        })

    result = pd.DataFrame(rows)

    print("=" * 70)
    print("Cross-validation: six-category map vs. transition matrix")
    print("=" * 70)
    print(result.to_string(index=False))
    print(
        "\nExpected pattern: 'error_vs_water_excluded_pct' should be large "
        "(the historical 1.7-2.2x mismatch), 'error_vs_all_classes_pct' "
        "should be small (<10%) — this is what confirms the two products "
        "are consistent once compared on the same scope."
    )

    out_path = Path(data_dir) / "CrossValidation_SixCategory_vs_Transition.csv"
    result.to_csv(out_path, index=False)
    print(f"\n[OK] Saved to {out_path}")

    return result


if __name__ == "__main__":
    main()
