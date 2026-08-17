"""
endmember_behavior_check.py

Debugging-budget Level 2 for the GBA Dynamic-vs-Fixed1985 divergence
investigation (see docs/methodology_notes.md, "第四轮：真实数据验证").
Level 1 (total wetland-area change magnitude) was tested and disconfirmed
as an explanation — this only ruled out that specific coarse proxy, not
the finer-grained "pixel composition" mechanism (see docs/limitations.md
for the precise scope of what was and wasn't ruled out).

This checks whether GBA's dynamic endmembers (NDVI_p5_soil, NDVI_p95_veg)
behave differently — more volatile year to year, or a narrower/wider
soil-vegetation span — than YRD/BTH's, which would point toward the
endmember computation itself as a contributor to GBA's FVC/EVI
divergence, rather than (or in addition to) mask/pixel-population
differences.

Per the agreed debugging budget: if this level is also inconclusive, the
GBA anomaly should be recorded as unresolved rather than investigated
further — the more scientifically consequential open question is the
YRD 2013 sensor-switch discontinuity (see sensor_switch_check.py),
not this GBA data-quality curiosity.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_loader import DEFAULT_DATA_DIR, load_all_regions


def endmember_summary(indices_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per-region summary of endmember level and year-to-year volatility."""
    rows = []
    for region, df in indices_dfs.items():
        df = df.sort_values("year")
        span = df["NDVI_p95_veg"] - df["NDVI_p5_soil"]
        rows.append({
            "region": region,
            "soil_mean": round(df["NDVI_p5_soil"].mean(), 4),
            "soil_std": round(df["NDVI_p5_soil"].std(), 4),
            "soil_cv_pct": round(100 * df["NDVI_p5_soil"].std() / df["NDVI_p5_soil"].mean(), 1),
            "veg_mean": round(df["NDVI_p95_veg"].mean(), 4),
            "veg_std": round(df["NDVI_p95_veg"].std(), 4),
            "veg_cv_pct": round(100 * df["NDVI_p95_veg"].std() / df["NDVI_p95_veg"].mean(), 1),
            "span_mean": round(span.mean(), 4),
            "span_std": round(span.std(), 4),
            "span_min": round(span.min(), 4),
            "span_max": round(span.max(), 4),
        })
    return pd.DataFrame(rows)


def divergence_endmember_correlation(indices_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """For each region, correlates |FVC_Dynamic - FVC_Fixed1985| against
    that year's endmember span. If GBA's divergence years line up with
    unusually narrow/wide spans, that's a concrete lead; if there's no
    correlation, the endmember-volatility explanation weakens too.
    """
    rows = []
    for region, df in indices_dfs.items():
        df = df.sort_values("year").copy()
        df["fvc_divergence"] = (df["FVC_Dynamic"] - df["FVC_Fixed1985"]).abs()
        df["endmember_span"] = df["NDVI_p95_veg"] - df["NDVI_p5_soil"]
        corr_span = df["fvc_divergence"].corr(df["endmember_span"])
        corr_soil = df["fvc_divergence"].corr(df["NDVI_p5_soil"])
        corr_veg = df["fvc_divergence"].corr(df["NDVI_p95_veg"])
        rows.append({
            "region": region,
            "corr_divergence_vs_span": round(corr_span, 3),
            "corr_divergence_vs_soil": round(corr_soil, 3),
            "corr_divergence_vs_veg": round(corr_veg, 3),
        })
    return pd.DataFrame(rows)


def main(data_dir: Path | str = DEFAULT_DATA_DIR) -> None:
    indices_dfs = load_all_regions("indices_36years", data_dir)

    print("=" * 80)
    print("Endmember level and volatility, by region")
    print("=" * 80)
    summary = endmember_summary(indices_dfs)
    print(summary.to_string(index=False))
    print(
        "\nIf GBA's soil_cv_pct / veg_cv_pct / span variability is clearly higher than "
        "YRD/BTH's, that supports endmember volatility as a contributor to GBA's "
        "FVC/EVI divergence. If GBA looks similar to or calmer than the other two "
        "regions, this level of investigation doesn't support the endmember explanation "
        "either — record as unresolved per the debugging budget."
    )

    print("\n" + "=" * 80)
    print("Correlation: |FVC_Dynamic - FVC_Fixed1985| vs. that year's endmember values")
    print("=" * 80)
    corr = divergence_endmember_correlation(indices_dfs)
    print(corr.to_string(index=False))
    print(
        "\nA meaningfully non-zero correlation (roughly |r| > 0.3, treated as a loose "
        "screening threshold, not a formal test) for GBA specifically — but not for "
        "YRD/BTH — would support the endmember explanation. Weak/inconsistent "
        "correlation across all three regions does not."
    )

    out_path = Path(data_dir) / "EndmemberBehavior_Diagnostic.csv"
    summary.merge(corr, on="region").to_csv(out_path, index=False)
    print(f"\n[OK] Saved to {out_path}")


if __name__ == "__main__":
    main()
