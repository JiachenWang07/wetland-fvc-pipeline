"""
endmember_method_sensitivity.py

The real dynamic-endmember vs. fixed-endmember sensitivity experiment —
distinct from (and a correction of) the earlier FVC_Dynamic vs.
FVC_Fixed1985 comparison in data_diagnostics.py, which actually compared
two different WETLAND MASKS (current-year vs. 1985), not two different
ENDMEMBER methods, both under the dynamic endmember. That comparison's
large GBA divergence was a mask/pixel-population effect, not an
endmember-method effect — see docs/methodology_notes.md for the full
history of that earlier (differently-scoped) finding.

This experiment instead holds the MASK constant (current-year dynamic
wetland mask, in both source files) and varies only the ENDMEMBER method:

  - FVC_Dynamic (from {region}_Indices_36Years.csv): per-year dynamic
    endmember + current-year dynamic wetland mask
  - FVC_FixedEndmember_Pixel (from
    {region}_FVC_FixedEndmember_PixelLevel_v4.csv, a historical export —
    validated as machine-precision identical to a from-scratch rerun for
    YRD, so treated as a trustworthy stand-in for all three regions
    pending the same check for GBA/BTH): fixed (region-specific 36-year
    mean) endmember + the SAME current-year dynamic wetland mask

This isolates the endmember-method effect from the mask effect.

Classification (robust / sensitive / unstable) is based on explicit,
stated criteria in classify_region() below — not a subjective call.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from data_loader import DEFAULT_DATA_DIR, REGIONS, REGION_FULL_NAMES, load_csv
from trend_analysis import run_mk_test

REGION_COLORS = {"YRD": "#00A087", "GBA": "#8491B4", "BTH": "#E64B35"}
DIVERGENCE_THRESHOLDS = [0.02, 0.03, 0.05]
SEGMENT_BREAKPOINT = 2005
SWITCH_YEAR = 2013


def load_and_merge(region: str, data_dir: Path | str) -> pd.DataFrame | None:
    """Loads FVC_Dynamic from Indices_36Years.csv and FVC_FixedEndmember_Pixel
    from the historical v4-suffixed export, merges on year."""
    dynamic_df = load_csv("indices_36years", region, data_dir)
    if dynamic_df is None:
        return None

    fixed_path = Path(data_dir) / f"{region}_FVC_FixedEndmember_PixelLevel_v4.csv"
    if not fixed_path.exists():
        print(f"[WARN] {region}: missing {fixed_path}")
        return None
    fixed_df = pd.read_csv(fixed_path)

    merged = dynamic_df[["year", "FVC_Dynamic"]].merge(
        fixed_df[["year", "FVC_FixedEndmember_Pixel"]], on="year", how="inner"
    ).sort_values("year")

    if len(merged) != 36:
        print(f"[WARN] {region}: expected 36 merged years, got {len(merged)} — check for gaps")

    merged["diff"] = merged["FVC_Dynamic"] - merged["FVC_FixedEndmember_Pixel"]
    merged["abs_diff"] = merged["diff"].abs()
    merged["region"] = region
    return merged


def compute_metrics(merged: pd.DataFrame) -> dict:
    pearson_r = merged["FVC_Dynamic"].corr(merged["FVC_FixedEndmember_Pixel"], method="pearson")
    spearman_r, _ = spearmanr(merged["FVC_Dynamic"], merged["FVC_FixedEndmember_Pixel"])

    metrics = {
        "n_years": len(merged),
        "mean_diff": merged["diff"].mean(),
        "mae": merged["abs_diff"].mean(),
        "rmse": np.sqrt((merged["diff"] ** 2).mean()),
        "max_abs_diff": merged["abs_diff"].max(),
        "pearson_r": pearson_r,
        "spearman_r": spearman_r,
    }
    for threshold in DIVERGENCE_THRESHOLDS:
        metrics[f"n_years_over_{threshold}"] = int((merged["abs_diff"] > threshold).sum())
    return metrics


def top_divergent_years(merged: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return merged.nlargest(n, "abs_diff")[["year", "FVC_Dynamic", "FVC_FixedEndmember_Pixel", "diff", "abs_diff"]]


def segmented_stats(merged: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, sub in [
        ("1985-2005", merged[merged["year"] <= SEGMENT_BREAKPOINT]),
        (f"{SEGMENT_BREAKPOINT}-2020", merged[merged["year"] >= SEGMENT_BREAKPOINT]),
    ]:
        rows.append({
            "period": label,
            "mean_diff": sub["diff"].mean(),
            "mae": sub["abs_diff"].mean(),
            "rmse": np.sqrt((sub["diff"] ** 2).mean()),
        })
    return pd.DataFrame(rows)


def trend_comparison(merged: pd.DataFrame) -> pd.DataFrame:
    """Runs Sen's slope + MK for both methods, each segment, for direct comparison."""
    rows = []
    for label, sub in [
        ("1985-2005", merged[merged["year"] <= SEGMENT_BREAKPOINT]),
        (f"{SEGMENT_BREAKPOINT}-2020", merged[merged["year"] >= SEGMENT_BREAKPOINT]),
    ]:
        for method_label, col in [("Dynamic", "FVC_Dynamic"), ("FixedEndmember", "FVC_FixedEndmember_Pixel")]:
            result = run_mk_test(sub[col])
            if result:
                rows.append({"period": label, "method": method_label, **result})
    return pd.DataFrame(rows)


def switch_year_jump(merged: pd.DataFrame) -> dict:
    row_2012 = merged[merged["year"] == 2012]
    row_2013 = merged[merged["year"] == SWITCH_YEAR]
    if row_2012.empty or row_2013.empty:
        return {"dynamic_jump": None, "fixed_endmember_jump": None}
    return {
        "dynamic_jump": float(row_2013["FVC_Dynamic"].iloc[0] - row_2012["FVC_Dynamic"].iloc[0]),
        "fixed_endmember_jump": float(
            row_2013["FVC_FixedEndmember_Pixel"].iloc[0] - row_2012["FVC_FixedEndmember_Pixel"].iloc[0]
        ),
    }


def classify_region(metrics: dict, trends: pd.DataFrame) -> tuple[str, str]:
    """Explicit classification criteria:

    🔴 unstable — trend DIRECTION or significance differs between the two
       methods in either segment (this would mean the reported conclusion
       itself depends on which endmember method was used).
    🟡 sensitive — trend direction/significance agree, but absolute
       divergence is notable: MAE > 0.015, OR more than 1/3 of years
       (12/36) exceed the 0.03 threshold.
    🟢 robust — trend direction/significance agree AND absolute
       divergence is small by both criteria above.

    These thresholds are stated explicitly here so the classification is
    reproducible and can be argued with, not just asserted.
    """
    for period in trends["period"].unique():
        period_rows = trends[trends["period"] == period]
        dynamic_row = period_rows[period_rows["method"] == "Dynamic"]
        fixed_row = period_rows[period_rows["method"] == "FixedEndmember"]
        if dynamic_row.empty or fixed_row.empty:
            continue
        if dynamic_row["trend"].iloc[0] != fixed_row["trend"].iloc[0]:
            return "unstable", f"Trend direction differs in {period}: Dynamic={dynamic_row['trend'].iloc[0]}, FixedEndmember={fixed_row['trend'].iloc[0]}"
        if dynamic_row["significant"].iloc[0] != fixed_row["significant"].iloc[0]:
            return "unstable", f"Significance differs in {period}: Dynamic={dynamic_row['significant'].iloc[0]}, FixedEndmember={fixed_row['significant'].iloc[0]}"

    if metrics["mae"] > 0.015 or metrics["n_years_over_0.03"] > 12:
        return "sensitive", f"Trends agree, but MAE={metrics['mae']:.4f} and/or {metrics['n_years_over_0.03']}/36 years exceed 0.03 divergence"

    return "robust", f"Trends agree across both segments; MAE={metrics['mae']:.4f}, only {metrics['n_years_over_0.03']}/36 years exceed 0.03"


def plot_time_series(all_merged: dict[str, pd.DataFrame], out_path: Path) -> None:
    fig, axes = plt.subplots(len(all_merged), 1, figsize=(10, 4 * len(all_merged)), sharex=True)
    if len(all_merged) == 1:
        axes = [axes]
    for ax, (region, df) in zip(axes, all_merged.items()):
        ax.plot(df["year"], df["FVC_Dynamic"], color=REGION_COLORS[region], linewidth=1.6, label="Dynamic endmember")
        ax.plot(df["year"], df["FVC_FixedEndmember_Pixel"], color=REGION_COLORS[region], linewidth=1.6,
                linestyle="--", alpha=0.7, label="Fixed endmember")
        ax.set_title(REGION_FULL_NAMES[region], loc="left", fontweight="bold")
        ax.legend(loc="best", frameon=False, fontsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[-1].set_xlabel("Year")
    fig.suptitle("Dynamic vs. Fixed Endmember FVC — Same Mask, Different Endmember Method")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def plot_yearly_diff(all_merged: dict[str, pd.DataFrame], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for region, df in all_merged.items():
        ax.plot(df["year"], df["diff"], color=REGION_COLORS[region], marker="o", markersize=3,
                linewidth=1.4, label=REGION_FULL_NAMES[region])
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.axvline(SWITCH_YEAR, color="gray", linestyle=":", alpha=0.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Dynamic − FixedEndmember (FVC)")
    ax.set_title("Per-Year Endmember-Method Divergence")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="best", frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def plot_method_agreement_scatter(all_merged: dict[str, pd.DataFrame], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 7))
    for region, df in all_merged.items():
        ax.scatter(df["FVC_FixedEndmember_Pixel"], df["FVC_Dynamic"], color=REGION_COLORS[region],
                   alpha=0.7, s=30, label=REGION_FULL_NAMES[region])
    lims = [
        min(ax.get_xlim()[0], ax.get_ylim()[0]),
        max(ax.get_xlim()[1], ax.get_ylim()[1]),
    ]
    ax.plot(lims, lims, color="gray", linestyle="--", linewidth=1, label="y = x")
    ax.set_xlabel("FVC (Fixed Endmember)")
    ax.set_ylabel("FVC (Dynamic Endmember)")
    ax.set_title("Method Agreement: Dynamic vs. Fixed Endmember FVC")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="best", frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_merged = {}
    summary_rows = []
    per_year_rows = []

    for region in REGIONS:
        merged = load_and_merge(region, data_dir)
        if merged is None:
            continue
        all_merged[region] = merged
        per_year_rows.append(merged)

        metrics = compute_metrics(merged)
        trends = trend_comparison(merged)
        jump = switch_year_jump(merged)
        label, reason = classify_region(metrics, trends)

        print("\n" + "=" * 80)
        print(f"{region} — {REGION_FULL_NAMES[region]}")
        print("=" * 80)
        print(f"MAE={metrics['mae']:.4f}  RMSE={metrics['rmse']:.4f}  max|diff|={metrics['max_abs_diff']:.4f}  "
              f"Pearson r={metrics['pearson_r']:.4f}  Spearman r={metrics['spearman_r']:.4f}")
        print(f"Years over threshold: >0.02: {metrics['n_years_over_0.02']}  "
              f">0.03: {metrics['n_years_over_0.03']}  >0.05: {metrics['n_years_over_0.05']}")
        print(f"\nTop 10 most divergent years:")
        print(top_divergent_years(merged).to_string(index=False))
        print(f"\nSegmented stats:")
        print(segmented_stats(merged).to_string(index=False))
        print(f"\nTrend comparison (Dynamic vs. FixedEndmember, both segments):")
        print(trends[["period", "method", "sen_slope", "trend", "p_value", "significant"]].to_string(index=False))
        print(f"\n2012->2013 jump — Dynamic: {jump['dynamic_jump']:+.4f}  "
              f"FixedEndmember: {jump['fixed_endmember_jump']:+.4f}")
        print(f"\n>>> CLASSIFICATION: {label.upper()} — {reason}")

        summary_rows.append({
            "region": region, "classification": label, "reason": reason,
            **metrics,
            "dynamic_jump_2012_2013": jump["dynamic_jump"],
            "fixed_endmember_jump_2012_2013": jump["fixed_endmember_jump"],
        })

    if not summary_rows:
        raise RuntimeError(
            "No regions produced endmember-method sensitivity results — required "
            "both Indices_36Years.csv and the historical FixedEndmember_PixelLevel_v4.csv "
            f"under data_dir={data_dir}. See the [WARN] messages above for which "
            "files were missing."
        )

    summary_df = pd.DataFrame(summary_rows)
    per_year_df = pd.concat(per_year_rows, ignore_index=True) if per_year_rows else pd.DataFrame()

    out_dir = Path(data_dir)
    summary_df.to_csv(out_dir / "EndmemberMethod_Sensitivity_Summary.csv", index=False)
    per_year_df.to_csv(out_dir / "EndmemberMethod_Sensitivity_PerYear.csv", index=False)

    if all_merged:
        plot_time_series(all_merged, out_dir / "Fig_EndmemberMethod_TimeSeries.png")
        plot_yearly_diff(all_merged, out_dir / "Fig_EndmemberMethod_YearlyDiff.png")
        plot_method_agreement_scatter(all_merged, out_dir / "Fig_EndmemberMethod_Agreement.png")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY — all regions")
    print("=" * 80)
    print(summary_df[["region", "classification", "mae", "rmse", "max_abs_diff", "pearson_r"]].to_string(index=False))

    return summary_df, per_year_df


if __name__ == "__main__":
    main()
