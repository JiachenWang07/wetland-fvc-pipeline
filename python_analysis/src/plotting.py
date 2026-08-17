"""
plotting.py

Figure generation using the unified NPG-style color convention (PALETTE)
that was standardized late in the project after multiple earlier scripts
each defined their own ad-hoc color dicts (visible in the history of the
notebooks this module replaces — the same PALETTE literal was pasted at
the top of the plotting cells repeatedly rather than defined once).

Covers the four figures with a clear "final version" in the project
history: regional FVC trend, fate-group FVC comparison, six-category
stacked/share bars, and net cropland/built-up flow by interval.

NOT yet covered (left as future work rather than a rushed partial
version): the area-vs-quality four-quadrant plot (needs an additional
city-level join not yet wired into data_loader.py) and the BNU
independent-endmember comparison plot (compares against a separate
third-party dataset, not a gee_scripts/ product, so it doesn't fit the
load_csv() pattern used here).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from data_loader import DEFAULT_DATA_DIR, REGIONS, REGION_FULL_NAMES, load_all_regions

# Standardized color convention — single source of truth for this module.
# 1985=navy, 2000=orange, 2020=green is the project's YEAR_COLORS convention
# for figures keyed by year; PALETTE is the broader set used for
# categorical figures (fate groups, land-cover categories, regions).
PALETTE = {
    "red": "#E64B35",
    "blue": "#4DBBD5",
    "green": "#00A087",
    "navy": "#3C5488",
    "orange": "#F39B7F",
    "purple": "#8491B4",
    "teal": "#91D1C2",
    "gray": "#B0B0B0",
}
YEAR_COLORS = {1985: "#3C5488", 2000: "#F39B7F", 2020: "#00A087"}

REGION_COLORS = {"YRD": PALETTE["green"], "GBA": PALETTE["purple"], "BTH": PALETTE["red"]}
FATE_COLORS = {"persistent": PALETTE["navy"], "gained": PALETTE["green"], "lost": PALETTE["red"]}
SIX_CATEGORY_COLORS = {
    "Wetland Lost": PALETTE["gray"],
    "Vegetation Degraded": PALETTE["red"],
    "Basically Stable": PALETTE["orange"],
    "Vegetation Improved": PALETTE["green"],
    "New Low-Cover Wetland (<45%)": PALETTE["teal"],
    "New High-Cover Wetland (>=45%)": PALETTE["navy"],
}
INTERVAL_ORDER = ["1985-1990", "1990-1995", "1995-2000", "2000-2005", "2005-2010", "2010-2015", "2015-2020"]


def plot_regional_fvc_trend(indices_dfs: dict[str, pd.DataFrame], out_path: Path) -> None:
    """36-year FVC trend, one line per region. Does not annotate a
    full-period slope on the plot itself — that statistic is deprecated
    (see trend_analysis.py); only the segmented breakpoint at 2005 is
    marked, as a visual reference, not a claimed statistical result."""
    fig, ax = plt.subplots(figsize=(10, 6))
    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        ax.plot(df["year"], df["FVC_Dynamic"], color=REGION_COLORS[region],
                 marker="o", markersize=3, linewidth=1.8, label=REGION_FULL_NAMES[region])

    ax.axvline(x=2005, color="gray", linestyle=":", alpha=0.4, linewidth=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("FVC (Fractional Vegetation Cover)")
    ax.set_title("Regional FVC Trend, Three Urban Agglomerations (1985-2020)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def plot_fate_group_fvc(fate_dfs: dict[str, pd.DataFrame], out_path: Path) -> None:
    """FVC by wetland fate group (persistent/gained/lost) across the 7
    adjacent intervals. Note in the figure caption: this compares fate
    categories WITHIN the same interval endpoint, not across years — see
    docs/methodology_notes.md and gee_scripts/wetland_fate_group.js for why
    persistent/gained are measured at the interval's end year while lost
    is measured at the start year."""
    all_vals = pd.concat([df["FVC_mean"] for df in fate_dfs.values()])
    y_min, y_max = all_vals.min() - 0.02, all_vals.max() + 0.02

    fig, axes = plt.subplots(1, len(fate_dfs), figsize=(5 * len(fate_dfs), 5), sharey=True)
    if len(fate_dfs) == 1:
        axes = [axes]

    for ax, (region, df) in zip(axes, fate_dfs.items()):
        for fate_type, color in FATE_COLORS.items():
            sub = df[df["type"] == fate_type].set_index("interval").reindex(INTERVAL_ORDER).reset_index()
            ax.plot(sub["interval"], sub["FVC_mean"], marker="o", markersize=5,
                     color=color, label=fate_type.capitalize(), linewidth=1.8)
        ax.set_title(REGION_FULL_NAMES[region], loc="left", fontweight="bold")
        ax.set_xlabel("Interval")
        ax.tick_params(axis="x", rotation=45)
        ax.set_ylim(y_min, y_max)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Mean FVC")
    axes[0].legend(loc="upper left", frameon=False, fontsize=8)
    fig.suptitle("FVC by Wetland Fate Group Across Adjacent Intervals (1985-2020)")
    fig.text(0.5, -0.04,
              "Note: comparisons are within the same interval endpoint across fate categories, "
              "not a cross-year comparison. 'Lost' FVC is measured at the earlier endpoint.",
              ha="center", fontsize=8, style="italic", color="#555555")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def plot_six_category_stacked(six_cat_df: pd.DataFrame, out_path: Path, as_share: bool = False) -> None:
    """Stacked bar of the six-category area-function transition, one bar
    per region. Set as_share=True for the percentage-of-total version."""
    categories = list(SIX_CATEGORY_COLORS.keys())
    regions_present = [r for r in REGIONS if r in six_cat_df["region"].unique()]

    fig, ax = plt.subplots(figsize=(9, 7))
    bottom = [0.0] * len(regions_present)

    for cat in categories:
        vals = []
        for region in regions_present:
            sub = six_cat_df[(six_cat_df["region"] == region) & (six_cat_df["class_label"] == cat)]
            v = sub["area_km2"].values[0] if len(sub) else 0.0
            if as_share:
                total = six_cat_df[six_cat_df["region"] == region]["area_km2"].sum()
                v = 100 * v / total if total > 0 else 0.0
            vals.append(v)
        ax.bar([REGION_FULL_NAMES[r] for r in regions_present], vals, bottom=bottom,
               label=cat, color=SIX_CATEGORY_COLORS[cat], edgecolor="white", linewidth=0.6, width=0.55)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.set_ylabel("Share of Total Wetland-Related Area (%)" if as_share else "Area (km²)")
    ax.set_title("Six-Category Structure by Share (1985-2020)" if as_share
                 else "Six-Category Wetland Area-Function Transition (1985-2020)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9)
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def plot_net_flow_by_interval(trans_dfs: dict[str, pd.DataFrame], out_path: Path) -> None:
    """Net cropland/built-up <-> wetland flow per interval — the
    high-confidence human-driven subset only. Water-body transitions are
    excluded here by construction (only Cropland/Built-up categories are
    plotted), consistent with docs/methodology_notes.md's water-noise
    filtering rationale.

    Matches on `converted_class_code` (the GLC_FCS30D numeric class code),
    not `converted_class_name` — the exported name strings are English
    (see LANDCOVER_CLASS_NAMES in gee_scripts/wetland_transition_structure.js,
    e.g. "Rainfed Cropland", "Impervious Surface"), and an earlier version
    of this function matched against hardcoded Chinese substrings that
    never matched the actual export, silently returning an empty plot.
    Codes are stable across any future relabeling of the display names.
    """
    # Cropland codes 10/11/12/20 (rainfed/herbaceous/tree-shrub/irrigated);
    # built-up is code 190 (impervious surface). See docs/data_schema.md
    # and gee_scripts/wetland_transition_structure.js for the full class list.
    CROPLAND_CODES = {10, 11, 12, 20}
    BUILTUP_CODE = 190

    interval_to_x = {iv: i for i, iv in enumerate(INTERVAL_ORDER)}
    regions_present = [r for r in trans_dfs]

    fig, axes = plt.subplots(1, len(regions_present), figsize=(6 * len(regions_present), 5.2))
    if len(regions_present) == 1:
        axes = [axes]

    for ax, region in zip(axes, regions_present):
        df = trans_dfs[region].copy()
        is_cropland = df["converted_class_code"].isin(CROPLAND_CODES)
        is_builtup = df["converted_class_code"] == BUILTUP_CODE
        df = df[is_cropland | is_builtup]
        df["category"] = df["converted_class_code"].apply(
            lambda code: "Cropland" if code in CROPLAND_CODES else "Built-up"
        )

        pivot = df.groupby(["interval", "direction", "category"])["area_km2"].sum().reset_index()
        net_flow = pivot.pivot_table(index=["interval", "category"], columns="direction",
                                       values="area_km2", fill_value=0).reset_index()
        net_flow["net_km2"] = net_flow.get("in", 0) - net_flow.get("out", 0)
        net_flow["x_pos"] = net_flow["interval"].map(interval_to_x)

        for category, color in [("Cropland", PALETTE["green"]), ("Built-up", PALETTE["red"])]:
            sub = net_flow[net_flow["category"] == category].sort_values("x_pos")
            ax.plot(sub["x_pos"], sub["net_km2"], marker="o", markersize=5, color=color, label=category, linewidth=1.8)

        ax.axhline(0, color="gray", linewidth=0.8)
        ax.set_xticks(range(len(INTERVAL_ORDER)))
        ax.set_xticklabels(INTERVAL_ORDER, rotation=45)
        ax.set_title(REGION_FULL_NAMES[region], loc="left", fontweight="bold")
        ax.set_xlabel("Interval")
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)

    axes[0].set_ylabel("Net Flow into Wetland (km²)")
    axes[0].legend(loc="best", frameon=False, fontsize=8)
    fig.suptitle("Net Cropland/Built-up <-> Wetland Flow by Interval (High-Confidence Transitions Only)")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
    out_dir = Path(data_dir)

    indices_dfs = load_all_regions("indices_36years", data_dir)
    if indices_dfs:
        plot_regional_fvc_trend(indices_dfs, out_dir / "Fig_FVC_Trend.png")

    fate_dfs = load_all_regions("fate_group", data_dir)
    if fate_dfs:
        plot_fate_group_fvc(fate_dfs, out_dir / "Fig_FateGroup_FVC.png")

    six_cat_dfs = load_all_regions("six_category_area_stats", data_dir)
    if six_cat_dfs:
        combined = pd.concat(six_cat_dfs.values(), ignore_index=True)
        plot_six_category_stacked(combined, out_dir / "Fig_SixCategory_Stacked.png", as_share=False)
        plot_six_category_stacked(combined, out_dir / "Fig_SixCategory_Share.png", as_share=True)

    trans_dfs = load_all_regions("transition_structure", data_dir)
    if trans_dfs:
        plot_net_flow_by_interval(trans_dfs, out_dir / "Fig_NetFlow_ByInterval.png")


if __name__ == "__main__":
    main()
