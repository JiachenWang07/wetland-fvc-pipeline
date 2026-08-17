"""
Exploratory diagnostic — NOT a formal statistical test. Checks whether the
2005-2020 upward trend shows a level jump or slope discontinuity around
2013 (the Landsat 5/7 -> Landsat 8 switch), which would be consistent with
the unresolved 🟡 "sensor harmonization" risk in docs/limitations.md.

This does not confirm or rule out sensor contamination on its own — it's a
first look to decide whether the full overlap-year validation (comparing
actual sensor data, not just this region-mean series) is worth prioritizing.
"""

from pathlib import Path

import pandas as pd

from data_loader import DEFAULT_DATA_DIR, load_all_regions
from trend_analysis import run_mk_test

SWITCH_YEAR = 2013


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    indices_dfs = load_all_regions("indices_36years", data_dir)

    print("=" * 70)
    print("STEP 1 — Raw FVC_Dynamic values around the 2013 sensor switch")
    print("=" * 70)
    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        window = df[(df["year"] >= 2008) & (df["year"] <= 2017)][["year", "FVC_Dynamic", "actual_imagery_year"]]
        print(f"\n{region}:")
        print(window.to_string(index=False))

    print("\n" + "=" * 70)
    print("STEP 2 — Level check: mean FVC before vs. after the switch (within 2005-2020)")
    print("=" * 70)
    print("Not a formal test — just eyeballing whether there's a jump at the switch,")
    print("separate from the already-fitted 2005-2020 trend line.\n")
    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        pre = df[(df["year"] >= 2005) & (df["year"] < SWITCH_YEAR)]["FVC_Dynamic"]
        post = df[(df["year"] >= SWITCH_YEAR) & (df["year"] <= 2020)]["FVC_Dynamic"]
        jump = post.mean() - pre.mean()
        print(f"{region}: 2005-2012 mean={pre.mean():.4f} (n={len(pre)})  "
              f"2013-2020 mean={post.mean():.4f} (n={len(post)})  "
              f"level jump={jump:+.4f}")

    print("\n" + "=" * 70)
    print("STEP 3 — Split the 2005-2020 trend at the switch: does the slope hold on each side?")
    print("=" * 70)
    print("If the 2005-2020 trend is a real, continuous recovery, both sub-periods")
    print("should show the SAME direction. If the trend only appears in one sub-period")
    print("(or reverses), that's a warning sign the 2005-2020 result may be an artifact")
    print("of the sensor switch rather than a continuous process.\n")

    rows = []
    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        for label, sub in [
            ("2005-2012 (L5/7 only)", df[(df["year"] >= 2005) & (df["year"] < SWITCH_YEAR)]),
            ("2013-2020 (L8 only)", df[(df["year"] >= SWITCH_YEAR) & (df["year"] <= 2020)]),
        ]:
            result = run_mk_test(sub["FVC_Dynamic"])
            if result:
                rows.append({"region": region, "sub_period": label, **result})

    result_df = pd.DataFrame(rows)
    print(result_df.to_string(index=False))

    print("\n" + "=" * 70)
    print("Interpretation guide (not an automated conclusion):")
    print("=" * 70)
    print("- If both sub-periods show 'increasing' with similar Sen's slope: the")
    print("  2005-2020 recovery trend looks continuous, lower priority to re-check.")
    print("- If only one sub-period drives the trend, or slopes differ a lot: worth")
    print("  prioritizing the full overlap-year sensor validation in limitations.md.")
    print("- Small n (as few as 7-8 points per sub-period) makes MK unreliable on")
    print("  its own — treat this as a screening step, not a final answer.")

    return result_df


if __name__ == "__main__":
    main()
