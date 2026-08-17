"""
data_diagnostics.py

Three exploratory diagnostics on {region}_Indices_36Years.csv, run together
because they all interrogate the same input and inform each other:

  1. Endmember stability — does NDVI_p5_soil / NDVI_p95_veg move smoothly
     year to year, or does it jump around? Jumps are worth cross-checking
     against fallback usage (#2) before assuming they reflect real land-
     cover change.
  2. Fallback (actual_imagery_year) usage — how often, and in which
     years, did the 4-level composite fallback in
     gee_scripts/region_pipeline.js substitute a different year's imagery.
     A year with substituted imagery is a natural first place to look if
     its endmembers or FVC value looks anomalous.
  3. Dynamic vs. fixed-1985-mask FVC consistency — FVC_Dynamic and
     FVC_Fixed1985 share the same endmember, differing only in which
     wetland mask was applied. They should track each other reasonably
     closely in most years; a year where they diverge sharply is worth a
     second look (means one of the two wetland extents changed a lot that
     year, not universally a problem, but worth knowing about rather than
     assuming away).

None of these are formal statistical tests — they're screening checks, in
the same spirit as sensor_switch_check.py.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from data_loader import DEFAULT_DATA_DIR, REGIONS, REGION_FULL_NAMES, load_all_regions

REGION_COLORS = {"YRD": "#00A087", "GBA": "#8491B4", "BTH": "#E64B35"}


def plot_endmember_stability(indices_dfs: dict[str, pd.DataFrame], out_path: Path) -> None:
    """Two-panel plot: soil endmember (top) and vegetation endmember
    (bottom), one line per region. Years where actual_imagery_year !=
    year are marked with a hollow marker instead of a filled one, so a
    jump that coincides with a substituted year is visually obvious."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        is_substituted = df["actual_imagery_year"] != df["year"]
        color = REGION_COLORS[region]

        for ax, col, title in [
            (axes[0], "NDVI_p5_soil", "Soil Endmember (NDVI 5th percentile)"),
            (axes[1], "NDVI_p95_veg", "Vegetation Endmember (NDVI 95th percentile)"),
        ]:
            ax.plot(df["year"], df[col], color=color, linewidth=1.3, alpha=0.7,
                     label=REGION_FULL_NAMES[region])
            ax.scatter(df.loc[~is_substituted, "year"], df.loc[~is_substituted, col],
                       color=color, s=18, zorder=3)
            ax.scatter(df.loc[is_substituted, "year"], df.loc[is_substituted, col],
                       facecolors="none", edgecolors=color, s=50, linewidths=1.5, zorder=4)
            ax.set_title(title, loc="left", fontsize=10)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

    axes[0].legend(loc="best", frameon=False, fontsize=8)
    axes[1].set_xlabel("Year")
    fig.suptitle("Dynamic Endmember Stability, 1985-2020\n"
                 "(hollow markers = year used substituted/fallback imagery)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def fallback_usage_stats(indices_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per substituted year, across all regions."""
    rows = []
    for region, df in indices_dfs.items():
        substituted = df[df["actual_imagery_year"] != df["year"]]
        for _, row in substituted.iterrows():
            gap = int(row["actual_imagery_year"] - row["year"])
            rows.append({
                "region": region,
                "requested_year": int(row["year"]),
                "actual_imagery_year": int(row["actual_imagery_year"]),
                "gap_years": gap,
                "fallback_level": (
                    "next-year growing season" if gap > 0 else "previous-year growing season"
                ),
            })
    result = pd.DataFrame(rows)
    total_years = sum(len(df) for df in indices_dfs.values())
    print(f"\nFallback substitution: {len(result)} / {total_years} region-years "
          f"({100 * len(result) / total_years:.1f}%) used substituted imagery.")
    if len(result):
        print(result.to_string(index=False))
    else:
        print("No substitutions found — every region-year used its own requested year's imagery.")
    return result


def dynamic_vs_fixed_consistency(
    indices_dfs: dict[str, pd.DataFrame],
    indicators: tuple[str, ...] = ("FVC", "EVI", "NDMI"),
    divergence_threshold: float = 0.03,
) -> pd.DataFrame:
    """Flags region-years where the Dynamic and Fixed1985 versions of each
    indicator diverge by more than divergence_threshold.

    Checking all three indicators together (not just FVC) is the point:
    Dynamic and Fixed1985 share the same wetland-status year's underlying
    Landsat composite and NDVI — they differ ONLY in which pixels the mask
    selects, and (for FVC specifically) the same endmember. If a region's
    divergence shows up consistently across FVC, EVI, AND NDMI, that
    points toward the masks selecting genuinely different pixel
    populations (a spatial/area explanation). If divergence is large for
    FVC but small for EVI/NDMI, that points toward something specific to
    the FVC computation (e.g. endmember handling) rather than the mask
    itself — a different explanation requiring a different next step.
    Absolute divergence_threshold (0.03) is calibrated for FVC's natural
    [0,1] range; EVI and NDMI don't necessarily share that scale, so the
    same absolute cutoff isn't equally meaningful across all three —
    mean_abs_diff_pct_of_mean is reported alongside the absolute numbers
    so cross-indicator comparisons don't implicitly assume they're on the
    same scale.
    """
    rows = []
    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        for indicator in indicators:
            dyn_col, fixed_col = f"{indicator}_Dynamic", f"{indicator}_Fixed1985"
            if dyn_col not in df.columns or fixed_col not in df.columns:
                continue
            corr = df[dyn_col].corr(df[fixed_col])
            diff = (df[dyn_col] - df[fixed_col]).abs()
            mean_dyn = df[dyn_col].mean()
            flagged_years = df.loc[diff > divergence_threshold, "year"].tolist()
            rows.append({
                "region": region,
                "indicator": indicator,
                "correlation": round(corr, 3),
                "mean_abs_diff": round(diff.mean(), 4),
                "mean_abs_diff_pct_of_mean": round(100 * diff.mean() / abs(mean_dyn), 1) if mean_dyn else None,
                "max_abs_diff": round(diff.max(), 4),
                "n_years_over_threshold": len(flagged_years),
                "years_over_threshold": flagged_years,
            })
    result = pd.DataFrame(rows)

    print(f"\nDynamic vs. Fixed1985 consistency, all indicators (divergence threshold = {divergence_threshold}):")
    print(result[["region", "indicator", "correlation", "mean_abs_diff", "mean_abs_diff_pct_of_mean",
                   "max_abs_diff", "n_years_over_threshold"]].to_string(index=False))

    print("\nInterpretation guide:")
    print("- If a region's n_years_over_threshold is high for ALL THREE indicators similarly:")
    print("  points toward the two masks covering genuinely different pixel populations (area-driven).")
    print("- If high for FVC only, low for EVI/NDMI: points toward something specific to the FVC")
    print("  computation itself (e.g. endmember handling), not the mask/area difference.")

    return result


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
    indices_dfs = load_all_regions("indices_36years", data_dir)

    if not indices_dfs:
        raise RuntimeError(
            "No regions had usable indices_36years data — cannot run diagnostics. "
            f"Checked data_dir={data_dir}. See the [WARN] messages above for which "
            "files were missing."
        )

    out_dir = Path(data_dir)

    print("=" * 70)
    print("DIAGNOSTIC 1 — Endmember stability")
    print("=" * 70)
    plot_endmember_stability(indices_dfs, out_dir / "Fig_Endmember_Stability.png")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC 2 — Fallback (actual_imagery_year) usage")
    print("=" * 70)
    fallback_df = fallback_usage_stats(indices_dfs)
    fallback_df.to_csv(out_dir / "FallbackUsage_Diagnostic.csv", index=False)

    print("\n" + "=" * 70)
    print("DIAGNOSTIC 3 — Dynamic vs. fixed-mask consistency (FVC, EVI, NDMI)")
    print("=" * 70)
    consistency_df = dynamic_vs_fixed_consistency(indices_dfs)
    consistency_df.to_csv(out_dir / "DynamicFixedConsistency_Diagnostic.csv", index=False)


if __name__ == "__main__":
    main()
